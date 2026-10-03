"""Glass cards: anchoring, geometry, and the composite chain.

What these pin is what fails silently:

1. A phrase must resolve FORWARD from the previous event, or a repeated word lands on the
   wrong occurrence ("bus stand" vs "this bus"), and a phrase that was cut must RAISE — a card
   clamped to a surviving word sits on a silent frame and nothing looks wrong.
2. A list scrolls by whole rows (never a half-clipped row) and the card grows with its content
   instead of opening as an empty full-height panel.
3. HyperFrames' MOV is BT.601 and untagged; without the conversion every card colour shifts
   (measured: #F25435 -> (255,98,50)). And cards sit after overlays, before subtitles (Rule 1).
"""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HELPERS = Path(__file__).parents[1] / "helpers"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HELPERS / filename)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cards = _load("video_use_cards", "cards.py")
render = _load("video_use_render_cards", "render.py")

SPOKEN = ("till two pm school is there and by two ten two fifteen you come home then lunch "
          "then I used to bicycle to bus stand forty degrees heavy kit bag cycle to the bus "
          "stand and then this bus for fifteen kilometers so sleep so that was on repeat for "
          "almost three years I am telling you because that routine is where")


class _Edit:
    """A one-range cut over a synthetic transcript, words 0.4 s apart from t=1.0."""

    def __init__(self, text=SPOKEN, range_=(0.0, 60.0)):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "transcripts").mkdir()
        self.words = [{"type": "word", "text": t, "start": 1.0 + i * 0.4, "end": 1.3 + i * 0.4}
                      for i, t in enumerate(text.split())]
        (self.dir / "transcripts" / "A.json").write_text(json.dumps({"words": self.words}))
        self.edl = {"ranges": [{"source": "A", "start": range_[0], "end": range_[1]}],
                    "sources": {"A": "a.mp4"}}
        self.durs = [range_[1] - range_[0]]

    def t(self, word, nth=1):
        hits = [w["start"] for w in self.words if w["text"] == word]
        return hits[nth - 1]


def _routine(**over):
    c = {"id": "routine", "kind": "list", "label": "The routine", "icon": "clock",
         "rows": [{"time": "2 PM", "text": "School ends", "at": "till two pm"},
                  {"time": "2:15", "text": "Home", "at": "two fifteen"},
                  {"time": "2:30", "text": "Lunch", "at": "lunch"},
                  {"time": "2 km", "text": "Cycle to bus stand", "at": "bicycle",
                   "chips": [{"text": "40C", "at": "forty degrees"},
                             {"text": "Heavy kit bag", "at": "heavy kit bag"}]},
                  {"time": "15 km", "text": "Bus", "at": "bus for fifteen"},
                  {"text": "Sleep", "at": "so sleep"}],
         "tag": {"text": "Every day", "at": "on repeat"},
         "footer": {"text": "On repeat for", "at": "on repeat", "value": "3 years",
                    "value_at": "three years"},
         "out": {"word": "that routine is"}}
    c.update(over)
    return c


class AnchorTests(unittest.TestCase):
    def setUp(self):
        self.e = _Edit()

    def resolve(self, c, w=1920, h=1080):
        return cards.resolve([c], self.e.edl, self.e.dir, self.e.durs, w, h)[0]

    def test_repeated_word_resolves_forward_not_to_the_first_occurrence(self):
        s = self.resolve(_routine())
        bus_row = s["list"]["rows"][4]
        # "bus" is first said in "to bus stand"; the row must land on "this bus for fifteen"
        self.assertAlmostEqual(bus_row["t"] + s["start"] + cards.LEAD, self.e.t("bus", 3), places=3)

    def test_a_cut_phrase_raises_instead_of_clamping(self):
        c = _routine()
        c["rows"].append({"text": "Tuition", "at": "tuition classes"})
        with self.assertRaises(cards.CardError) as cm:
            self.resolve(c)
        self.assertIn("tuition classes", str(cm.exception))

    def test_a_word_outside_the_kept_range_is_not_spoken(self):
        e = _Edit(range_=(0.0, 5.0))     # keeps only the first ~10 words
        with self.assertRaises(cards.CardError):
            cards.resolve([_routine()], e.edl, e.dir, e.durs, 1920, 1080)

    def test_punctuation_and_case_do_not_matter(self):
        e = _Edit(text="Till two PM, school is there. So, sleep! On repeat for three years. "
                       "That routine is")
        c = {"id": "x", "kind": "list", "rows": [{"text": "School ends", "at": "till two pm"},
                                                 {"text": "Sleep", "at": "so sleep"}]}
        s = cards.resolve([c], e.edl, e.dir, e.durs, 1920, 1080)[0]
        self.assertEqual(len(s["list"]["rows"]), 2)

    def test_times_are_window_local_and_the_window_covers_the_exit(self):
        s = self.resolve(_routine())
        first = s["list"]["rows"][0]
        self.assertAlmostEqual(first["t"] + s["start"], self.e.t("till") - cards.LEAD, places=3)
        self.assertGreater(s["in"], 0)
        self.assertLessEqual(s["exit"] + s["exit_dur"], s["duration"])
        self.assertAlmostEqual(s["exit"] + s["start"], self.e.t("that", 2), places=3)  # "that routine is", not "so that was"

    def test_measured_durations_shift_a_later_range(self):
        """Anchors follow the MEASURED segment lengths, not the EDL floats."""
        e = _Edit()
        e.edl["ranges"] = [{"source": "A", "start": 0.0, "end": 0.9},
                           {"source": "A", "start": 0.9, "end": 60.0}]
        a = cards.resolve([_routine()], e.edl, e.dir, [0.9, 59.1], 1920, 1080)[0]
        b = cards.resolve([_routine()], e.edl, e.dir, [0.9333, 59.1], 1920, 1080)[0]
        self.assertAlmostEqual(b["start"] - a["start"], 0.0333, places=3)


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.e = _Edit()

    def test_scroll_offsets_land_on_row_tops(self):
        many = [{"text": f"Step {i}", "at": w} for i, w in enumerate(
            ["till", "school", "there", "by", "ten", "fifteen", "home", "lunch", "bicycle", "degrees"])]
        s = cards.resolve([{"id": "m", "kind": "list", "rows": many}], self.e.edl, self.e.dir,
                          self.e.durs, 1920, 1080)[0]
        tops = {r["top"] for r in s["list"]["rows"]}
        self.assertTrue(s["list"]["scrolls"], "ten 64px rows must overflow a 442px view")
        for sc in s["list"]["scrolls"]:
            self.assertIn(sc["offset"], tops)
            visible = [r for r in s["list"]["rows"] if r["top"] >= sc["offset"]]
            self.assertTrue(all(r["top"] - sc["offset"] + r["h"] <= cards.LIST["view_h"]
                                for r in visible if r["top"] <= max(q["top"] for q in visible)
                                and r["t"] <= sc["t"] + 0.4))

    def test_the_card_grows_then_caps(self):
        s = cards.resolve([_routine()], self.e.edl, self.e.dir, self.e.durs, 1920, 1080)[0]
        hs = [h for _, h in s["heights"]]
        self.assertLess(s["box"]["h0"], hs[0], "a one-row card must start short")
        self.assertEqual(hs, sorted(hs), "the card only grows")
        self.assertLessEqual(s["box"]["y"] + hs[-1], 1080 - cards.MARGIN)

    def test_resolution_independent_stage(self):
        a = cards.resolve([_routine()], self.e.edl, self.e.dir, self.e.durs, 1920, 1080)[0]
        b = cards.resolve([_routine()], self.e.edl, self.e.dir, self.e.durs, 3840, 2160)[0]
        self.assertEqual(a["stage"]["w"], b["stage"]["w"])
        self.assertEqual(b["stage"]["scale"], 2.0)
        self.assertEqual(a["list"], b["list"])

    def test_top_right_hugs_the_right_margin_of_the_actual_frame(self):
        c = {"id": "s", "kind": "stat", "position": "top-right",
             "steps": [{"at": "lunch", "value": "1"}]}
        s = cards.resolve([c], self.e.edl, self.e.dir, self.e.durs, 1920, 1080)[0]
        self.assertEqual(s["box"]["x"] + s["box"]["w"], 1920 - cards.MARGIN)

    def test_stat_stack_places_cards_under_each_other(self):
        c0 = {"id": "a", "kind": "stat", "steps": [{"at": "lunch", "value": "1"}]}
        c1 = {"id": "b", "kind": "stat", "stack": 1, "steps": [{"at": "bicycle", "value": "2"}]}
        a, b = cards.resolve([c0, c1], self.e.edl, self.e.dir, self.e.durs, 1920, 1080)
        self.assertEqual(b["box"]["y"], a["box"]["y"] + cards.STAT["h"] + cards.STAT["gap"])

    def test_bad_entries_raise(self):
        for bad in ({"id": "x", "kind": "pie", "rows": []},
                    {"id": "x y", "kind": "stat", "steps": [{"at": "lunch", "value": "1"}]},
                    {"id": "x", "kind": "stat", "icon": "unicorn", "steps": [{"at": "lunch", "value": "1"}]},
                    {"id": "x", "kind": "list", "rows": []}):
            with self.assertRaises(cards.CardError):
                cards.resolve([bad], self.e.edl, self.e.dir, self.e.durs, 1920, 1080)


class StampTests(unittest.TestCase):
    """A stamp is one word in a pill. It lands AS its phrase is said, holds briefly, and its
    width is computed in Python so the mask pass (no text) gets the same silhouette."""

    def setUp(self):
        self.e = _Edit()

    def resolve(self, **over):
        c = {"id": "deg", "kind": "stamp", "text": "40°C", "at": "forty degrees"}
        c.update(over)
        return cards.resolve([c], self.e.edl, self.e.dir, self.e.durs, 1920, 1080)[0]

    def test_lands_as_its_word_is_said_not_a_settle_lead_before(self):
        s = self.resolve()
        self.assertAlmostEqual(s["in"] + s["start"], self.e.t("forty") - cards.LEAD, places=3)

    def test_default_hold_is_short(self):
        s = self.resolve()
        self.assertAlmostEqual(s["exit"] + s["start"], self.e.t("forty") + cards.STAMP["hold"], places=3)

    def test_out_word_overrides_the_hold(self):
        s = self.resolve(out={"word": "heavy kit bag"})
        self.assertAlmostEqual(s["exit"] + s["start"], self.e.t("heavy"), places=3)

    def test_text_is_shown_in_caps_and_width_grows_with_it(self):
        a = self.resolve(text="ten")
        b = self.resolve(text="heavy kit bag")
        self.assertEqual(a["stamp"]["text"], "TEN")
        self.assertGreater(b["box"]["w"], a["box"]["w"])
        self.assertEqual(a["box"]["h0"], cards.STAMP["h"])

    def test_positions(self):
        c = self.resolve(position="top-center")
        self.assertAlmostEqual(c["box"]["x"] * 2 + c["box"]["w"], 1920, places=2)
        self.assertEqual(c["box"]["side"], "center")
        r = self.resolve(position="top-right")
        self.assertEqual(r["box"]["x"] + r["box"]["w"], 1920 - cards.MARGIN)
        st = self.resolve(stack=1)
        self.assertEqual(st["box"]["y"], cards.MARGIN + cards.STAMP["h"] + cards.STAMP["gap"])

    def test_bad_stamps_raise(self):
        for over in ({"text": ""}, {"at": ""}, {"text": "this is a whole sentence not a stamp at all"},
                     {"at": "tuition classes"}):
            with self.assertRaises(cards.CardError):
                self.resolve(**over)
        lst = {"id": "l", "kind": "list", "position": "top-center", "rows": [{"text": "x", "at": "lunch"}]}
        with self.assertRaises(cards.CardError):
            cards.resolve([lst], self.e.edl, self.e.dir, self.e.durs, 1920, 1080)

    def test_page_draws_the_text_and_the_mask_does_not(self):
        s = self.resolve(text="heavy kit bag")
        self.assertIn("stamp-text", cards.page(s, "overlay", 1920, 1080))
        self.assertIn("HEAVY KIT BAG", cards.page(s, "overlay", 1920, 1080))
        mask = cards.page(s, "mask", 1920, 1080)
        self.assertNotIn("CardFont", mask)


class PageTests(unittest.TestCase):
    def setUp(self):
        e = _Edit()
        self.spec = cards.resolve([_routine()], e.edl, e.dir, e.durs, 3840, 2160)[0]

    def test_everything_is_inline_for_the_static_guard(self):
        html = cards.page(self.spec, "overlay", 3840, 2160)
        self.assertNotIn('<script src="glass.js"', html)
        self.assertIn('window.__timelines["main"]', html)
        self.assertIn('data-width="3840"', html)

    def test_fonts_are_local_names_never_files(self):
        html = cards.page(self.spec, "overlay", 3840, 2160)
        self.assertIn('src: local("HelveticaNeue-Bold")', html)
        self.assertNotIn(".ttf", html)

    def test_mask_has_no_named_font_family(self):
        html = cards.page(self.spec, "mask", 3840, 2160)
        self.assertNotIn("CardFont", html)
        self.assertIn('window.HF_MODE = "mask"', html)

    def test_private_keys_do_not_reach_the_page(self):
        html = cards.page(self.spec, "overlay", 3840, 2160)
        self.assertNotIn("_brand", html)
        self.assertNotIn("_words", html)


ENTRY = {"id": "routine", "cards": Path("c.mov"), "mask": Path("m.mov"), "start": 92.75, "duration": 64.4}


class FilterTests(unittest.TestCase):
    def test_card_stream_is_converted_from_601_to_709(self):
        _, parts, _ = cards.build_filter([ENTRY], "[v0]", 1, 3840, 2160)
        self.assertTrue(any("in_color_matrix=bt601:out_color_matrix=bt709" in p for p in parts))

    def test_mask_is_padded_to_the_window_not_offset(self):
        inputs, parts, _ = cards.build_filter([ENTRY], "[v0]", 1, 3840, 2160)
        self.assertTrue(any("tpad=start_duration=92.750" in p for p in parts))
        # -itsoffset applies to the CARD input only, and sits right before its -i
        i = inputs.index("-itsoffset")
        self.assertEqual(inputs[i + 2], "-i")
        self.assertEqual(inputs[i + 3], "c.mov")
        self.assertEqual(inputs.count("-itsoffset"), 1)

    def test_glass_is_drawn_before_the_card(self):
        _, parts, label = cards.build_filter([ENTRY], "[v0]", 1, 3840, 2160)
        g = next(i for i, p in enumerate(parts) if "[ck_g0]overlay" in p)
        c = next(i for i, p in enumerate(parts) if "[ck_c0]overlay" in p)
        self.assertLess(g, c)
        self.assertEqual(label, "[ck_o0]")

    def test_blur_scales_with_output_height(self):
        _, a, _ = cards.build_filter([ENTRY], "[v]", 1, 1920, 1080)
        _, b, _ = cards.build_filter([ENTRY], "[v]", 1, 3840, 2160)
        self.assertTrue(any("sigma=10.0" in p for p in a))
        self.assertTrue(any("sigma=20.0" in p for p in b))

    def test_cards_sit_after_overlays_and_before_subtitles(self):
        with tempfile.TemporaryDirectory() as tmp:
            edit = Path(tmp)
            (edit / "base.mp4").write_bytes(b"")
            (edit / "ov.mp4").write_bytes(b"")
            subs = edit / "master.srt"
            subs.write_text("")
            result = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            with patch.object(render.subprocess, "run", return_value=result) as run, \
                    patch.object(render.cards_mod, "_dims", return_value=(3840, 2160)):
                render.build_final_composite(
                    edit / "base.mp4", [{"file": "ov.mp4", "start_in_output": 100.0, "duration": 3.0}],
                    subs, edit / "out.mp4", edit, cards=[ENTRY])
            cmd = list(run.call_args.args[0])
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertLess(graph.index("[1:v]overlay"), graph.index("ck_toblur"))
        self.assertLess(graph.index("[ck_o0]"), graph.index("subtitles="))
        # input numbering: base 0, overlay 1, mask 2, card 3
        self.assertIn("[2:v]alphaextract", graph)
        self.assertIn("[3:v]scale=in_color_matrix=bt601", graph)


if __name__ == "__main__":
    unittest.main()
