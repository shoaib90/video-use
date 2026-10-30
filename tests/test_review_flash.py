"""T9: a stray single frame at a cut. Real encodes, so codec behaviour is included."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "helpers"))
import review  # noqa: E402

FPS = 30


def clip(path: Path, source: str, frames: int):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"{source}{':' if '=' in source else '='}s=320x180:r={FPS}",
                    "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)


def join(out: Path, parts: list[Path]):
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)], check=True)


class FlashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._t = tempfile.TemporaryDirectory()
        cls.t = Path(cls._t.name)
        cls.a = cls.t / "a.mp4"
        cls.b = cls.t / "b.mp4"
        cls.moving = cls.t / "m.mp4"
        cls.black = cls.t / "black.mp4"
        cls.white = cls.t / "white.mp4"
        clip(cls.a, "color=c=gray", 30)
        clip(cls.b, "color=c=0x404040", 30)
        clip(cls.moving, "testsrc2", 30)
        clip(cls.black, "color=c=black", 1)
        clip(cls.white, "color=c=white", 1)

    @classmethod
    def tearDownClass(cls):
        cls._t.cleanup()

    def flashes(self, name, parts, cut_frames):
        out = self.t / name
        join(out, parts)
        return review.flash_frames(out, [f / FPS for f in cut_frames], FPS)

    def test_clean_hard_cut_is_not_a_flash(self):
        self.assertEqual(self.flashes("clean.mp4", [self.a, self.b], [30]), [])

    def test_cut_between_a_static_and_a_moving_shot_is_not_a_flash(self):
        self.assertEqual(self.flashes("mix.mp4", [self.a, self.moving], [30]), [])

    def test_cut_between_two_moving_shots_is_not_a_flash(self):
        self.assertEqual(self.flashes("mm.mp4", [self.moving, self.moving], [30]), [])

    def test_black_frame_at_a_jump_cut_is_a_flash(self):
        self.assertEqual(len(self.flashes("black_in.mp4", [self.a, self.black, self.a], [30])), 1)

    def test_two_and_three_frame_strays_are_flashes(self):
        for n in (2, 3):
            stray = self.t / f"white{n}.mp4"
            clip(stray, "color=c=white", n)
            self.assertEqual(len(self.flashes(f"white_{n}.mp4", [self.a, stray, self.b], [30])), 1, n)

    def test_a_shot_of_a_quarter_second_is_not_a_flash(self):
        stray = self.t / "white8.mp4"
        clip(stray, "color=c=white", 8)
        self.assertEqual(self.flashes("white_8.mp4", [self.a, stray, self.b], [30, 38]), [])

    def test_stray_frame_whose_brightness_sits_between_its_neighbours_is_a_flash(self):
        # The neighbours differ more from each other than from it (M061's shape).
        mid = self.t / "mid.mp4"
        clip(mid, "color=c=0x808080", 1)
        dark, bright = self.t / "dark.mp4", self.t / "bright.mp4"
        clip(dark, "color=c=0x101010", 30)
        clip(bright, "color=c=0xf0f0f0", 30)
        self.assertEqual(len(self.flashes("between.mp4", [dark, mid, bright], [30])), 1)

    def test_a_clean_cut_inside_steady_motion_is_not_a_flash(self):
        self.assertEqual(self.flashes("mcut.mp4", [self.moving, self.a], [30]), [])

    def test_constant_big_changes_are_not_a_flash(self):
        strobe = self.t / "strobe.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=320x180:r={FPS}",
                        "-vf", "geq=lum='if(mod(N,2),235,16)':cb=128:cr=128", "-frames:v", "30",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(strobe)], check=True)
        self.assertEqual(review.flash_frames(strobe, [15 / FPS], FPS), [])

    def test_white_frame_between_different_shots_is_a_flash(self):
        self.assertEqual(len(self.flashes("white_in.mp4", [self.a, self.white, self.b], [30])), 1)


if __name__ == "__main__":
    unittest.main()
