"""A static `zoom` must crop the SOURCE before the downscale, and honour `zoom_y`.

Cropping after the downscale threw away the resolution a 4K source has to
spare: a 2x single from a 4K wide, delivered at 1080p, was an upscaled 960x540.
These render a fine-detail source at half its height with zoom=2, so the crop
should be a 1:1 copy of the source's pixels, and compare against a direct crop.
Measured: the new order scores 60.3 dB against the direct crop; the old order
(scale, then crop, then upscale) scores 35.1 dB, so the bound sits at 50.
`zoom_y` is checked by comparing top and bottom crops the same way.
"""
import importlib.util
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "helpers" / "render.py"
SPEC = importlib.util.spec_from_file_location("video_use_render_zoom", MODULE_PATH)
assert SPEC and SPEC.loader
render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render)


def _psnr(a: Path, b: Path) -> float:
    out = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(a), "-i", str(b),
         "-lavfi", "[0:v][1:v]psnr", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    m = re.search(r"average:(\S+)", out)
    return float("inf") if m and m.group(1) == "inf" else float(m.group(1))


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class ZoomCropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.src = cls.tmp / "src.mp4"
        # testsrc2 at 1280x720: dense text and edges, so a soft upscale shows.
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y",
             "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=1",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
             "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-shortest", str(cls.src)],
            check=True,
        )

    def _render(self, name, **kw):
        out = self.tmp / f"{name}.mp4"
        render.extract_segment(self.src, 0.0, 0.5, "", out, rate="30",
                               height=360, crf="10", zoom=2.0, zoom_x=0.0, **kw)
        return out

    def _direct(self, name, x, y):
        out = self.tmp / f"{name}.mp4"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(self.src), "-t", "0.5",
             "-vf", f"crop=640:360:{x}:{y}", "-c:v", "libx264", "-crf", "10",
             "-pix_fmt", "yuv420p", "-an", str(out)],
            check=True,
        )
        return out

    def test_zoom_crops_source_before_downscale(self):
        got = self._render("top", zoom_y=0.0)
        self.assertGreater(_psnr(got, self._direct("ref_top", 0, 0)), 50.0)

    def test_zoom_y_moves_the_crop_vertically(self):
        got = self._render("bottom", zoom_y=1.0)
        self.assertGreater(_psnr(got, self._direct("ref_bottom", 0, 360)), 50.0)
        self.assertLess(_psnr(got, self._direct("ref_top2", 0, 0)), 25.0)


if __name__ == "__main__":
    unittest.main()
