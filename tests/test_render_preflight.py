"""render.py --check, and the crashes it was added alongside."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "helpers"))
import graphics  # noqa: E402
import render  # noqa: E402


def make_clip(path: Path, size="320x180", dur=4, silent=False):
    audio = "anullsrc=r=48000:cl=stereo" if silent else "sine=f=440:r=48000"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s={size}:r=30:d={dur}",
                    "-f", "lavfi", "-i", audio, "-t", str(dur), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", str(path)], check=True)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.edit = cls.tmp / "edit"
        cls.edit.mkdir()
        cls.src = cls.tmp / "a.mp4"
        make_clip(cls.src)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def check(self, edl, **kw):
        return render.preflight(edl, self.edit, self.edit / "out.mp4", draft=True, **kw)

    def edl(self, **extra):
        return {"sources": {"a": str(self.src)}, "grade": "none",
                "ranges": [{"source": "a", "start": 0.5, "end": 1.5}], **extra}


class PreflightTests(Base):
    def assertProblem(self, problems, text):
        self.assertTrue(any(text in p for p in problems), f"{text!r} not in {problems}")

    def test_a_good_edit_passes(self):
        self.assertEqual(self.check(self.edl()), ([], []))

    def test_no_ranges(self):
        self.assertProblem(self.check({"sources": {}, "ranges": []})[0], "no ranges")

    def test_unknown_source_key(self):
        edl = self.edl()
        edl["ranges"][0]["source"] = "b"
        self.assertProblem(self.check(edl)[0], "missing from `sources`")

    def test_missing_source_file(self):
        edl = self.edl()
        edl["sources"]["a"] = "/nope/a.mp4"
        self.assertProblem(self.check(edl)[0], "not found")

    def test_backwards_range(self):
        edl = self.edl()
        edl["ranges"][0].update(start=2, end=1)
        self.assertProblem(self.check(edl)[0], "not after start")

    def test_range_past_the_end(self):
        edl = self.edl()
        edl["ranges"][0]["end"] = 9
        self.assertProblem(self.check(edl)[0], "long")

    def test_range_flush_with_the_end_warns(self):
        edl = self.edl()
        edl["ranges"][0]["end"] = 4.0
        errors, warnings = self.check(edl)
        self.assertEqual(errors, [])
        self.assertProblem(warnings, "clamp")

    def test_missing_subtitles_is_an_error_unless_opted_out(self):
        edl = self.edl(subtitles="gone.srt")
        self.assertProblem(self.check(edl)[0], "subtitles file not found")
        self.assertEqual(self.check(edl, no_subtitles=True)[0], [])

    def test_sources_of_different_shapes_would_stretch(self):
        portrait = self.tmp / "p.mp4"
        make_clip(portrait, size="180x320")
        edl = self.edl()
        edl["sources"]["p"] = str(portrait)
        edl["ranges"].append({"source": "p", "start": 0, "end": 1})
        self.assertProblem(self.check(edl)[0], "stretched")

    def test_a_cut_anchor_phrase_is_caught_before_rendering(self):
        (self.edit / "transcripts").mkdir(exist_ok=True)
        (self.edit / "transcripts" / "a.json").write_text(json.dumps({"words": [
            {"type": "word", "text": "hello", "start": 0.6, "end": 0.9},
            {"type": "word", "text": "world", "start": 3.0, "end": 3.2}]}))
        edl = self.edl(graphics=[{"type": "lower_third", "text": "x",
                                  "anchor": {"phrase": "world"}, "duration": 1}])
        self.assertProblem(self.check(edl)[0], "graphics")

    def test_oversized_overlay_warns(self):
        big = self.tmp / "big.mp4"
        make_clip(big, size="3840x2160", dur=1)
        edl = self.edl(overlays=[{"file": str(big), "start_in_output": 0, "duration": 0.5}])
        self.assertProblem(self.check(edl)[1], "top-left corner")


class RenderRunTests(Base):
    """Through the real CLI: each of these used to crash or lose captions."""

    def render(self, folder: Path, edl: dict, *args):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "edl.json").write_text(json.dumps(edl))
        return subprocess.run(["uv", "run", "python", str(ROOT / "helpers/render.py"), str(folder / "edl.json"),
                               "-o", str(folder / "out.mp4"), "--draft", "--no-exposure-check", *args],
                              cwd=ROOT, capture_output=True, text=True)

    def test_awkward_folder_names_with_captions(self):
        folder = self.tmp / "It's, a [test]; 1:2"
        folder.mkdir()
        (folder / "m.srt").write_text("1\n00:00:00,000 --> 00:00:00,900\nhello\n")
        r = self.render(folder, self.edl(subtitles="m.srt"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreater(render.probe_duration(folder / "out.mp4"), 0.9)

    def test_missing_subtitles_stops_the_render(self):
        folder = self.tmp / "nosubs"
        r = self.render(folder, self.edl(subtitles="gone.srt"))
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((folder / "out.mp4").exists())
        self.assertFalse((folder / "clips_draft").exists())

    def test_check_renders_nothing(self):
        folder = self.tmp / "checkonly"
        r = self.render(folder, self.edl(), "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((folder / "out.mp4").exists())

    def test_ffmpeg_reason_reaches_the_user(self):
        folder = self.tmp / "badfilter"
        edl = self.edl()
        edl["ranges"][0]["filter"] = "nosuchfilter"
        r = self.render(folder, edl)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nosuchfilter", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_digital_silence_survives_loudnorm_in_both_modes(self):
        silent = self.tmp / "silent.mp4"
        make_clip(silent, silent=True)
        edl = self.edl()
        edl["sources"]["a"] = str(silent)
        for name, extra in (("sil_draft", ()), ("sil_final", ("--crf", "28"))):
            folder = self.tmp / name
            (folder).mkdir()
            (folder / "edl.json").write_text(json.dumps(edl))
            cmd = ["uv", "run", "python", str(ROOT / "helpers/render.py"), str(folder / "edl.json"),
                   "-o", str(folder / "out.mp4"), "--no-exposure-check", *extra]
            if name == "sil_draft":
                cmd.append("--draft")
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            # The draft's one-pass path survives silence on current ffmpeg, so only the
            # final is guaranteed to reach the fallback; both must produce a file.
            self.assertTrue((folder / "out.mp4").exists())
            if name == "sil_final":
                self.assertIn("digital silence", r.stdout)


class EscapeTests(Base):
    def test_filter_path_opens_with_every_awkward_character(self):
        folder = self.tmp / "a'b, c[d];e:f g"
        folder.mkdir()
        srt = folder / "m.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:00,500\nhi\n")
        r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:s=64x36:d=0.2",
                            "-vf", f"subtitles={graphics.escape_filter_path(srt)}", "-f", "null", "-"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_drawtext_textfile_opens_too(self):
        folder = self.tmp / "It's text"
        folder.mkdir()
        txt = folder / "t.txt"
        txt.write_text("hi")
        r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:s=64x36:d=0.2",
                            "-vf", f"drawtext=textfile={graphics.escape_filter_path(txt)}", "-f", "null", "-"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_concat_list_path(self):
        self.assertEqual(render.concat_list_path(Path("/x/It's.mp4")), "/x/It'\\''s.mp4")


class LoudnessTests(unittest.TestCase):
    def test_silence_is_not_measurable(self):
        m = dict(input_i="-inf", input_tp="-inf", input_lra="0.00", input_thresh="-70.00", target_offset="inf")
        self.assertFalse(render.loudness_is_measurable(m))

    def test_real_speech_is(self):
        m = dict(input_i="-21.8", input_tp="-20.4", input_lra="1.0", input_thresh="-32", target_offset="0.1")
        self.assertTrue(render.loudness_is_measurable(m))


if __name__ == "__main__":
    unittest.main()
