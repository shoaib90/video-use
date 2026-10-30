"""Overlays cover exactly the frames asked for, and meet a cut they nearly touch (M061).

Decoded from real renders, on a real concat base (which starts ~21 ms in, not at 0): the
shape of the bug was a frame or two of the shot underneath, at the edge of an overlay.
"""
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "helpers"))
import render  # noqa: E402

FPS = 30
W, H = 64, 36


def luma(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-fps_mode", "passthrough",
                          "-vf", f"scale={W}:{H},format=gray", "-an", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, W * H).mean(1)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._t = tempfile.TemporaryDirectory()
        cls.t = Path(cls._t.name)
        src = cls.t / "src.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x303030:s=320x180:r={FPS}:d=12",
                        "-f", "lavfi", "-i", "sine=f=300:r=48000:d=12", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", str(src)], check=True)
        # A real base: separately encoded segments through the real concat.
        segs = []
        for i, (a, d) in enumerate(((0, 2.0), (3, 2.0), (6, 2.0))):
            seg = cls.t / f"seg{i}.mp4"
            render.extract_segment(src, a, d, "", seg, draft=True, rate=f"{FPS}/1", height=180)
            segs.append(seg)
        cls.base = cls.t / "base.mp4"
        with contextlib.redirect_stdout(io.StringIO()):
            render.concat_segments(segs, cls.base, cls.t)
        cls.cuts = [60, 120]
        cls.overlay = cls.t / "ov.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=white:s=320x180:r={FPS}:d=3",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(cls.overlay)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls._t.cleanup()

    def covered(self, start, duration, cuts=None):
        out = self.t / "out.mp4"
        with contextlib.redirect_stdout(io.StringIO()):
            render.build_final_composite(self.base, [{"file": str(self.overlay), "start_in_output": start,
                                                      "duration": duration}], None, out, self.t,
                                         crf="28", preset="ultrafast", fps=f"{FPS}/1", cuts=cuts)
        on = np.where(luma(out) > 128)[0]
        self.assertTrue(len(on) > 0)
        self.assertEqual(int(on[-1] - on[0] + 1), len(on), "the overlay must be one unbroken run")
        return int(on[0]), int(on[-1]) + 1


class ExactFrameTests(Base):
    def test_covers_exactly_the_frames_asked_for_from_any_offset(self):
        for start in (0.5, 0.51, 0.517, 0.5245, 0.53, 0.5333, 0.549):
            first, past = self.covered(start, 1.0)
            want = round(start * FPS)
            self.assertEqual((first, past), (want, want + 30), start)

    def test_no_final_frame_is_lost_off_the_grid(self):
        self.assertEqual(self.covered(0.43, 1.2)[1] - self.covered(0.43, 1.2)[0], 36)


class SnapTests(Base):
    def test_a_late_start_is_pulled_back_to_the_cut(self):
        self.assertEqual(self.covered(61.5 / FPS, 0.5, self.cuts)[0], 60)

    def test_an_early_end_is_pushed_out_to_the_cut(self):
        first, past = self.covered(1.0, 0.95, self.cuts)
        self.assertEqual((first, past), (30, 60))

    def test_an_end_past_the_cut_is_pulled_back(self):
        self.assertEqual(self.covered(1.0, 1.05, self.cuts)[1], 60)

    def test_an_edge_away_from_a_cut_stays(self):
        self.assertEqual(self.covered(1.0, 0.5, self.cuts), (30, 45))

    def test_cuts_are_counted_in_frames(self):
        self.assertEqual(render.count_video_frames(self.base), 180)

    def test_cut_slots_on_a_clean_base(self):
        segs = [self.t / f"seg{i}.mp4" for i in range(3)]
        self.assertEqual(render.cut_slots(self.base, segs, FPS), [60, 120])

    def test_window_logic(self):
        f = render.overlay_windows
        # exposed: snaps
        self.assertEqual(f([(62, 90)], [False], [60]), [(60, 90)])
        # further than the limit: left alone
        self.assertEqual(f([(64, 90)], [False], [60]), [(64, 90)])
        # the edge sits under another opaque overlay: left alone, or it could open a gap
        self.assertEqual(f([(30, 61), (59, 90)], [False, False], [60])[0], (30, 61))
        # see-through overlays show the cut anyway
        self.assertEqual(f([(62, 90)], [True], [60]), [(62, 90)])
        # never collapses to nothing
        self.assertEqual(f([(61, 62)], [False], [60, 63]), [(60, 63)])


class TimestampHoleTests(unittest.TestCase):
    """A segment whose audio outlasts its video leaves a hole in the base's video timestamps.

    Podcast-free reproduction of the Hustler base (8328 frames across 8329 slots). Counting
    frames here put every later cut one frame early, and shipped a wrong fix for one render.
    """

    @classmethod
    def setUpClass(cls):
        cls._t = tempfile.TemporaryDirectory()
        cls.t = Path(cls._t.name)
        def seg(path, frames, audio_s, color):
            # Muxed from separate streams, so the audio really does outlast the video.
            v, au = path.with_suffix(".v.mp4"), path.with_suffix(".a.m4a")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=320x180:r={FPS}",
                            "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(v)], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=f=300:r=48000:d={audio_s}",
                            "-c:a", "aac", str(au)], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-i", str(au), "-c", "copy", str(path)], check=True)
        cls.segs = [cls.t / "a.mp4", cls.t / "b.mp4", cls.t / "c.mp4"]
        seg(cls.segs[0], 60, 2.1, "0x202020")     # audio runs ~3 frames past the video
        seg(cls.segs[1], 60, 2.0, "0x505050")
        seg(cls.segs[2], 60, 2.0, "0x202020")
        cls.base = cls.t / "base.mp4"
        with contextlib.redirect_stdout(io.StringIO()):
            render.concat_segments(cls.segs, cls.base, cls.t)
        cls.overlay = cls.t / "ov.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=white:s=320x180:r={FPS}:d=3",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(cls.overlay)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls._t.cleanup()

    def test_slots_see_the_hole_and_frame_counts_do_not(self):
        slots = render.cut_slots(self.base, self.segs, FPS)
        counted = [60, 120]
        self.assertGreater(slots[0], counted[0])
        self.assertEqual(slots[1] - slots[0], 60)

    def test_nominal_rate_ignores_the_average_the_hole_distorts(self):
        self.assertEqual(render._nominal_rate(self.base, "24"), 30.0)
        self.assertNotAlmostEqual(render._rate_to_float(render.probe_source_fps(self.base)), 30.0, places=3)

    def test_an_overlay_ending_near_the_cut_after_the_hole_leaves_no_sliver(self):
        slots = render.cut_slots(self.base, self.segs, FPS)
        cut = slots[1]
        out = self.t / "out.mp4"
        # asks to end one frame short of the second cut
        with contextlib.redirect_stdout(io.StringIO()):
            render.build_final_composite(self.base, [{"file": str(self.overlay), "start_in_output": (cut - 30) / FPS,
                                                      "duration": 29 / FPS}], None, out, self.t, crf="28",
                                         preset="ultrafast", fps=f"{FPS}/1", cuts=slots)
        y = luma(out)
        on = np.where(y > 128)[0]
        # the last white frame must be the last frame of segment b (index 119), not 118
        self.assertEqual(int(on[-1]), 119)
        self.assertEqual(int(on[-1] - on[0] + 1), 30)


if __name__ == "__main__":
    unittest.main()
