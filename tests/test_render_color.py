"""Colour handling: the HLG tone-map, bt709 tagging of every output, the exposure check.

Three decisions from the 2026-10-11 HDR audit (kb/gotchas.md), pinned here:

- TONEMAP_CHAIN uses HLG's reference white (npl=203) and mobius. npl=100 + hable
  put midtones ~10-15 luma low and clipped red clothing up to 2%.
- Every output is tagged bt709 on all three fields. ffmpeg 9 ignores the
  -color_trc / -color_primaries output flags, and the concat stream-copies
  segment 0's header, so one untagged title card left Episode 2's whole final
  `transfer=unknown`. The concat and the copy path use h264_metadata; the
  composite ends in setparams.
- The exposure check warns at p5 < 20, a face > 15 luma under the frame mean,
  > 0.5% red clipping and grade saturation > 1.0, and never fails a render.
"""

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

HELPERS = Path(__file__).parents[1] / "helpers"


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HELPERS / file)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


render = _load("video_use_render", "render.py")
exposure = _load("video_use_exposure", "exposure.py")

HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _tags(path: Path) -> str:
    return subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=color_space,color_transfer,color_primaries",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout.strip().rstrip(",")


class ToneMapTests(unittest.TestCase):
    def test_reference_white_and_mobius(self):
        self.assertIn("npl=203", render.TONEMAP_CHAIN)
        self.assertIn("tonemap=mobius", render.TONEMAP_CHAIN)
        self.assertNotIn("npl=100", render.TONEMAP_CHAIN)
        self.assertNotIn("hable", render.TONEMAP_CHAIN)

    def test_rest_of_chain_unchanged(self):
        """Only the white point and the curve moved; the output is still 8-bit bt709."""
        self.assertIn("zscale=p=bt709", render.TONEMAP_CHAIN)
        self.assertIn("desat=0", render.TONEMAP_CHAIN)
        self.assertTrue(render.TONEMAP_CHAIN.endswith("zscale=t=bt709:m=bt709:r=tv,format=yuv420p"))


class TagCommandTests(unittest.TestCase):
    def _run_capture(self, fn):
        result = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with patch.object(render.subprocess, "run", return_value=result) as run:
            fn()
        return [list(c.args[0]) for c in run.call_args_list]

    def test_concat_stamps_bt709_on_the_stream_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            edit = Path(tmp)
            segs = [edit / f"seg_{i}.mp4" for i in range(2)]
            for s in segs:
                s.write_bytes(b"")
            cmd = self._run_capture(lambda: render.concat_segments(segs, edit / "base.mp4", edit))[-1]
        self.assertIn("-bsf:v", cmd)
        bsf = cmd[cmd.index("-bsf:v") + 1]
        for field in ("colour_primaries=1", "transfer_characteristics=1", "matrix_coefficients=1"):
            self.assertIn(field, bsf)
        self.assertEqual(cmd[cmd.index("-c:v") + 1], "copy")   # still Hard Rule 2

    def _composite_graph(self, subs: bool) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            edit = Path(tmp)
            (edit / "base.mp4").write_bytes(b"")
            (edit / "ov.mp4").write_bytes(b"")
            subs_path = None
            if subs:
                subs_path = edit / "master.srt"
                subs_path.write_text("")
            overlays = [{"file": "ov.mp4", "start_in_output": 1.0, "duration": 2.0}]
            cmd = self._run_capture(lambda: render.build_final_composite(
                edit / "base.mp4", overlays, subs_path, edit / "out.mp4", edit))[-1]
        return cmd, cmd[cmd.index("-filter_complex") + 1]

    def test_composite_ends_in_setparams_after_subtitles(self):
        cmd, graph = self._composite_graph(subs=True)
        last = graph.split(";")[-1]
        self.assertLess(last.index("subtitles="), last.index(render.BT709_SETPARAMS),
                        "subtitles must stay the last PICTURE stage (Rule 1)")
        self.assertTrue(last.endswith(f"{render.BT709_SETPARAMS}[outv]"))
        self.assertEqual(cmd[cmd.index("-map") + 1], "[outv]")

    def test_composite_without_subtitles_still_stamps(self):
        cmd, graph = self._composite_graph(subs=False)
        self.assertTrue(graph.endswith(f"{render.BT709_SETPARAMS}[outv]"))
        self.assertEqual(cmd[cmd.index("-map") + 1], "[outv]")

    def test_copy_path_stamps_bt709(self):
        """With nothing to composite the base is copied; the copy must carry the tags too."""
        with tempfile.TemporaryDirectory() as tmp:
            edit = Path(tmp)
            (edit / "base.mp4").write_bytes(b"")
            cmd = self._run_capture(lambda: render.build_final_composite(
                edit / "base.mp4", [], None, edit / "out.mp4", edit))[-1]
        self.assertIn("-bsf:v", cmd)
        self.assertIn(("-c", "copy"), list(zip(cmd, cmd[1:])))


@unittest.skipUnless(HAVE_FFMPEG, "needs ffmpeg")
class RealTaggingTests(unittest.TestCase):
    """Against the installed ffmpeg, because the bug is ffmpeg's behaviour."""

    def _untagged_segment(self, path: Path, color: str):
        # lavfi frames carry no transfer/primaries; ffmpeg 9 then writes `unknown`
        # even when -color_trc/-color_primaries are passed (they are, here)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", f"color={color}:s=320x180:r=30:d=0.5",
                        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "0.5",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                        "-c:a", "aac", str(path)], check=True)

    def test_untagged_first_segment_no_longer_strips_the_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            edit = Path(tmp)
            segs = [edit / "seg_0.mp4", edit / "seg_1.mp4"]
            self._untagged_segment(segs[0], "black")
            self._untagged_segment(segs[1], "gray")
            self.assertEqual(_tags(segs[0]), "bt709,unknown,unknown",
                             "precondition: ffmpeg ignores the output colour flags")
            render.concat_segments(segs, edit / "base.mp4", edit)
            self.assertEqual(_tags(edit / "base.mp4"), "bt709,bt709,bt709")

    def test_setparams_tags_a_reencode(self):
        with tempfile.TemporaryDirectory() as tmp:
            edit = Path(tmp)
            self._untagged_segment(edit / "in.mp4", "black")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(edit / "in.mp4"),
                            "-filter_complex", f"[0:v]{render.BT709_SETPARAMS}[o]", "-map", "[o]",
                            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                            str(edit / "out.mp4")], check=True)
            self.assertEqual(_tags(edit / "out.mp4"), "bt709,bt709,bt709")


class ExposureRuleTests(unittest.TestCase):
    OK = {"mean": 110.0, "p5": 30.0, "p95": 200.0}
    NO_RED = {"red_share": 0.0, "clipped": 0.0}

    def test_clean_frame_has_no_warnings(self):
        self.assertEqual(exposure.evaluate(self.OK, self.NO_RED, 110.0, "eq=saturation=1.0"), [])

    def test_shadow_floor_is_20(self):
        self.assertEqual(exposure.evaluate({**self.OK, "p5": 20.0}, self.NO_RED, None), [])
        w = exposure.evaluate({**self.OK, "p5": 19.9}, self.NO_RED, None)
        self.assertEqual(len(w), 1)
        self.assertIn("shadows crushed", w[0])

    def test_face_may_sit_15_below_the_frame_mean(self):
        self.assertEqual(exposure.evaluate(self.OK, self.NO_RED, 95.0), [])
        w = exposure.evaluate(self.OK, self.NO_RED, 94.0)
        self.assertEqual(len(w), 1)
        self.assertIn("face under-lit", w[0])

    def test_unmeasured_face_is_not_a_warning(self):
        self.assertEqual(exposure.evaluate(self.OK, self.NO_RED, None), [])

    def test_red_clipping_limit_is_half_a_percent(self):
        self.assertEqual(exposure.evaluate(self.OK, {"red_share": 0.1, "clipped": 0.005}, None), [])
        w = exposure.evaluate(self.OK, {"red_share": 0.1, "clipped": 0.0051}, None)
        self.assertIn("red clipping", w[0])

    def test_grade_saturation_above_one(self):
        self.assertEqual(exposure.grade_saturation(
            "curves=master='0/0 1/1',eq=contrast=1.03:saturation=0.82"), 0.82)
        self.assertIsNone(exposure.grade_saturation(""))
        w = exposure.evaluate(self.OK, self.NO_RED, None, "eq=saturation=1.1")
        self.assertIn("saturation", w[0])

    def test_frame_measures(self):
        rgb = np.zeros((10, 10, 3), np.uint8)
        rgb[:, 5:] = 255                       # half black, half white
        s = exposure.frame_stats(rgb)
        self.assertAlmostEqual(s["mean"], 127.5, places=3)
        self.assertEqual(s["p5"], 0.0)
        self.assertAlmostEqual(s["p95"], 255.0, places=3)

    def test_red_clip_counts_only_strong_reds(self):
        rgb = np.zeros((10, 10, 3), np.uint8)
        rgb[0, :4] = (255, 20, 20)             # clipped red
        rgb[1, :6] = (200, 30, 30)             # red, not clipped
        rgb[2, :] = (255, 255, 255)            # white: R=255 but not red
        r = exposure.red_clip(rgb)
        self.assertAlmostEqual(r["clipped"], 0.4)
        self.assertAlmostEqual(r["red_share"], 0.10)

    def test_face_luma_uses_the_box_centre(self):
        rgb = np.full((100, 100, 3), 200, np.uint8)
        rgb[20:80, 20:80] = 50                 # dark face; the box edges are bright
        self.assertAlmostEqual(exposure.face_luma(rgb, [10, 10, 80, 80]), 50.0, places=3)

    def test_missing_detector_env_is_reported_not_raised(self):
        box, why = exposure.detect_face(np.zeros((4, 4, 3), np.uint8),
                                        python=Path("/nonexistent/bin/python"))
        self.assertIsNone(box)
        self.assertIn("face not measured", why)


class RenderHookTests(unittest.TestCase):
    def test_a_failing_check_never_raises_and_stops_trying(self):
        with patch.object(render.exposure_mod, "check", side_effect=RuntimeError("boom")):
            self.assertEqual(render.run_exposure_check(Path("x.mp4"), "", 1),
                             render.EXPOSURE_MAX_TRIES)

    def test_no_face_keeps_trying(self):
        res = {"video": "x.mp4", "frame": {"mean": 1, "p5": 1, "p95": 1},
               "red": {"red_share": 0, "clipped": 0}, "face_box": None, "face_mean": None,
               "face_note": "no face in frame", "warnings": []}
        with patch.object(render.exposure_mod, "check", return_value=res):
            self.assertEqual(render.run_exposure_check(Path("x.mp4"), "", 2), 2)

    def test_measured_face_stops_trying(self):
        res = {"video": "x.mp4", "frame": {"mean": 100, "p5": 30, "p95": 200},
               "red": {"red_share": 0, "clipped": 0}, "face_box": [0, 0, 1, 1], "face_mean": 100,
               "face_note": "", "warnings": []}
        with patch.object(render.exposure_mod, "check", return_value=res):
            self.assertEqual(render.run_exposure_check(Path("x.mp4"), "", 1),
                             render.EXPOSURE_MAX_TRIES)


if __name__ == "__main__":
    unittest.main()
