"""Declarative text graphics: anchoring, resolution independence, chain order.

The three things these pin are the three that fail silently:

1. A graphic pinned to an absolute time rots the moment any earlier range
   changes, and a time summed from EDL floats is already wrong because extracts
   are frame-quantised. Anchors resolve against MEASURED segment durations.
2. A pixel size is correct at exactly one output height. Every size here is a
   fraction of the height, so the same entry must scale 1:1 from 720p to 2160p.
3. A title drawn after the subtitle burn covers the captions (Hard Rule 1).
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HELPERS = Path(__file__).parents[1] / "helpers"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HELPERS / filename)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


graphics = _load("video_use_graphics", "graphics.py")
render = _load("video_use_render", "render.py")


class AnchorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.edit = Path(self.tmp.name)
        (self.edit / "transcripts").mkdir()
        words = [{"type": "word", "text": t, "start": 1.0 + i * 0.4,
                  "end": 1.35 + i * 0.4}
                 for i, t in enumerate("my name is Shoaib and welcome back".split())]
        (self.edit / "transcripts" / "B.json").write_text(json.dumps({"words": words}))
        self.addCleanup(self.tmp.cleanup)
        self.edl = {
            "sources": {"A": "/tmp/A.mov", "B": "/tmp/B.mov"},
            "ranges": [
                {"source": "A", "start": 0.0, "end": 3.0},    # seg 0
                {"source": "B", "start": 0.0, "end": 5.0},    # seg 1
                {"source": "A", "start": 9.0, "end": 12.0},   # seg 2
            ],
        }
        # MEASURED durations, deliberately not equal to the EDL's float spans:
        # an extract is quantised to whole frames, so the real segment is a
        # fraction longer and the error accumulates.
        self.durations = [3.033, 5.033, 3.033]

    def resolve(self, entry):
        return graphics.resolve_anchors([entry], self.edl, self.edit, self.durations)[0]

    def test_source_anchor_uses_measured_durations_not_edl_floats(self):
        g = self.resolve({"type": "title", "text": "x", "anchor": {"source": "B"}})
        # 3.033 measured, NOT the 3.0 the EDL describes
        self.assertAlmostEqual(g["start"], 3.033, places=3)

    def test_source_anchor_nth_occurrence(self):
        g = self.resolve({"type": "title", "text": "x",
                          "anchor": {"source": "A", "nth": 2}})
        self.assertAlmostEqual(g["start"], 3.033 + 5.033, places=3)

    def test_segment_and_time_anchors(self):
        self.assertAlmostEqual(
            self.resolve({"type": "title", "text": "x",
                          "anchor": {"segment": 2}})["start"], 8.066, places=3)
        self.assertAlmostEqual(
            self.resolve({"type": "title", "text": "x",
                          "anchor": {"time": 4.5}})["start"], 4.5, places=3)

    def test_word_anchor_lands_on_the_spoken_phrase(self):
        g = self.resolve({"type": "title", "text": "x",
                          "anchor": {"word": "name is"}})
        # "name" is the 2nd word of B, starting 1.4s into it; B starts at 3.033
        self.assertAlmostEqual(g["start"], 3.033 + 1.4, places=3)

    def test_offset_applies_and_never_goes_negative(self):
        g = self.resolve({"type": "title", "text": "x", "offset": -99,
                          "anchor": {"source": "B"}})
        self.assertEqual(g["start"], 0.0)

    def test_duration_is_clamped_to_the_film(self):
        g = self.resolve({"type": "title", "text": "x", "duration": 999,
                          "anchor": {"segment": 2}})
        self.assertAlmostEqual(g["start"] + g["duration"], sum(self.durations), places=3)

    def test_unresolvable_anchors_raise_rather_than_silently_vanish(self):
        for anchor in ({"source": "ZZ"}, {"source": "A", "nth": 9},
                       {"word": "never spoken"}, {"segment": 99}, {}):
            with self.assertRaises(graphics.GraphicsError):
                self.resolve({"type": "title", "text": "x", "anchor": anchor})

    def test_a_word_that_was_cut_cannot_be_anchored_to(self):
        # "welcome back" is at 3.4-4.15s of B, outside this shortened range
        self.edl["ranges"][1]["end"] = 2.0
        with self.assertRaises(graphics.GraphicsError):
            self.resolve({"type": "title", "text": "x",
                          "anchor": {"word": "welcome back"}})


class RenderingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.g = {"type": "title", "text": "Quick fit check", "start": 0.35,
                  "duration": 2.8, **graphics.TYPE_DEFAULTS["title"]}
        self.g.update({"start": 0.35, "duration": 2.8})

    def sizes(self, height):
        f = graphics.build_filters([dict(self.g)], height, self.work)[0]
        fs = int(f.split("fontsize=")[1].split(":")[0])
        margin = int(f.split("x=w-tw-")[1].split(":")[0])
        return fs, margin

    def test_sizes_scale_exactly_with_output_height(self):
        small, big = self.sizes(720), self.sizes(2160)
        self.assertEqual(big[0], small[0] * 3)
        self.assertEqual(big[1], small[1] * 3)

    def test_text_goes_through_a_file_so_nothing_can_break_the_filter(self):
        g = dict(self.g)
        # every character class that breaks `text=`: apostrophe, colon, comma,
        # double quote, backslash, percent
        g["text"] = "it's 5:30, 100% \"go\" \\ done"
        f = graphics.build_filters([g], 1080, self.work)[0]
        self.assertIn("drawtext=textfile='", f)
        # the `text=` OPTION must never be used; note "drawtext=" itself
        # contains "text=" as a substring, so match the option form
        self.assertNotIn(":text=", f)
        written = next(self.work.glob("*_main.txt")).read_text(encoding="utf-8")
        self.assertEqual(written, g["text"])

    def test_window_and_fade(self):
        f = graphics.build_filters([dict(self.g)], 1080, self.work)[0]
        self.assertIn("enable='between(t,0.350,3.150)'", f)
        self.assertIn("alpha=", f)

    def test_fade_cannot_exceed_half_the_duration(self):
        g = dict(self.g)
        g.update({"duration": 0.4, "fade": 5.0})
        f = graphics.build_filters([g], 1080, self.work)[0]
        # a 5s fade on a 0.4s graphic would otherwise never reach full opacity
        self.assertIn("alpha=", f)
        self.assertNotIn("/5.000", f)

    def test_lower_third_emits_title_and_subtitle_clear_of_the_caption_band(self):
        g = {**graphics.TYPE_DEFAULTS["lower_third"], "type": "lower_third",
             "text": "Shoaib", "subtitle": "HSR to Filter Coffee",
             "start": 1.0, "duration": 4.0}
        fs = graphics.build_filters([g], 1080, self.work)
        self.assertEqual(len(fs), 2)
        ys = sorted(int(f.split("y=")[1].split(":")[0]) for f in fs)
        self.assertLess(ys[0], ys[1])                 # subtitle sits below title
        self.assertLess(ys[1], 1080 * 0.88)           # both clear of the captions

    def test_unresolved_or_empty_entries_raise(self):
        with self.assertRaises(graphics.GraphicsError):
            graphics.build_filters([{"type": "title", "text": "x"}], 1080, self.work)
        with self.assertRaises(graphics.GraphicsError):
            graphics.build_filters([dict(self.g, text="  ")], 1080, self.work)

    def test_unknown_position_and_type_raise(self):
        with self.assertRaises(graphics.GraphicsError):
            graphics.build_filters([dict(self.g, position="middle-ish")], 1080, self.work)
        with self.assertRaises(graphics.GraphicsError):
            graphics.resolve_anchors([{"type": "banner", "text": "x",
                                       "anchor": {"time": 0}}], {"ranges": []},
                                     self.work, [1.0])


class ChainOrderTests(unittest.TestCase):
    """Graphics must be drawn BEFORE the subtitle filter (Hard Rule 1)."""

    def test_graphics_precede_subtitles_in_the_filter_graph(self):
        captured = {}

        def fake_run(cmd, **kw):
            if "-filter_complex" in cmd:
                captured["fc"] = cmd[cmd.index("-filter_complex") + 1]
            class R:
                returncode = 0
            return R()

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        edit = Path(tmp.name)
        srt = edit / "m.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n")
        base = edit / "base.mp4"
        base.write_text("")

        orig_run, orig_h = render.subprocess.run, render.probe_video_height
        render.subprocess.run = fake_run
        render.probe_video_height = lambda p: 1080
        try:
            g = {**graphics.TYPE_DEFAULTS["title"], "type": "title",
                 "text": "T", "start": 1.0, "duration": 2.0}
            render.build_final_composite(base, [], srt, edit / "out.mp4", edit,
                                         graphics=[g])
        finally:
            render.subprocess.run, render.probe_video_height = orig_run, orig_h

        fc = captured["fc"]
        self.assertIn("drawtext", fc)
        self.assertIn("subtitles=", fc)
        self.assertLess(fc.index("drawtext"), fc.index("subtitles="),
                        "subtitles must be applied after graphics, or a title "
                        "can cover a caption")


if __name__ == "__main__":
    unittest.main()


class GlyphCoverageTests(unittest.TestCase):
    """drawtext has no font fallback, so a missing glyph ships as a blank box.

    Verified on macOS: Helvetica draws Latin but not Devanagari, DevanagariMT
    the reverse, Kohinoor both. Skipped where the system fonts are absent.
    """

    HELV = Path("/System/Library/Fonts/Helvetica.ttc")
    KOHI = Path("/System/Library/Fonts/Kohinoor.ttc")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_latin_font_reports_devanagari_as_missing(self):
        if not self.HELV.is_file():
            self.skipTest("Helvetica.ttc not present")
        self.assertTrue(graphics.missing_glyphs(str(self.HELV), "बढ़िया"))
        self.assertFalse(graphics.missing_glyphs(str(self.HELV), "Quick fit check"))

    def test_kohinoor_covers_both_scripts(self):
        if not self.KOHI.is_file():
            self.skipTest("Kohinoor.ttc not present")
        self.assertFalse(graphics.missing_glyphs(str(self.KOHI), "HSR बढ़िया 5:30"))

    def test_build_refuses_text_the_font_cannot_draw(self):
        if not self.HELV.is_file():
            self.skipTest("Helvetica.ttc not present")
        g = {**graphics.TYPE_DEFAULTS["title"], "type": "title",
             "text": "बढ़िया", "start": 0.0, "duration": 2.0,
             "font": str(self.HELV)}
        with self.assertRaises(graphics.GraphicsError) as cm:
            graphics.build_filters([g], 1080, self.work)
        self.assertIn("font fallback", str(cm.exception))

    def test_uninspectable_font_returns_None_not_an_empty_set(self):
        # "could not check" must never look like "checked, nothing missing"
        self.assertIsNone(graphics.missing_glyphs("Helvetica", "बढ़िया"))

    def test_devanagari_passes_through_a_font_that_covers_it(self):
        kohi = Path("/System/Library/Fonts/Kohinoor.ttc")
        if not kohi.is_file():
            self.skipTest("Kohinoor.ttc not present")
        g = {**graphics.TYPE_DEFAULTS["title"], "type": "title",
             "text": "बढ़िया — it's 5:30", "start": 0.0, "duration": 2.0,
             "font": str(kohi)}
        graphics.build_filters([g], 1080, self.work)
        written = next(self.work.glob("*_main.txt")).read_text(encoding="utf-8")
        self.assertEqual(written, g["text"])
