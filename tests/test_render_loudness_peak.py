"""The loudness stage must hold true peak under -1 dBTP AFTER the AAC encode.

loudnorm alone cannot: fed a hot mix it falls back to dynamic mode, limits at its
target, and the AAC encode that follows overshoots past 0 dBFS (podcast Episode 1:
+1.0 dBTP, 871 samples at full scale). render.py adds a -3 dBFS limiter after it.
"""
import importlib.util
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "helpers" / "render.py"
SPEC = importlib.util.spec_from_file_location("video_use_render_peak", MODULE_PATH)
assert SPEC and SPEC.loader
render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render)


def _true_peak(path: Path) -> float:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path),
                          "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", out)[-1])


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class LoudnessPeakTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.src = cls.tmp / "hot.mp4"
        # Speech-like: a quiet bed with sparse, very loud transients (clipped plosives).
        subprocess.run(["ffmpeg", "-v", "error", "-y",
                        "-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=20",
                        "-f", "lavfi", "-i",
                        "aevalsrc='0.08*sin(2*PI*220*t)*(1+0.5*sin(2*PI*3*t))"
                        "+0.98*sin(2*PI*1500*t)*lt(mod(t,1.7),0.04)':s=48000:d=20",
                        "-c:v", "libx264", "-c:a", "aac", "-b:a", "320k", "-shortest",
                        str(cls.src)], check=True)

    def test_two_pass_holds_true_peak_after_aac(self):
        out = self.tmp / "final.mp4"
        render.apply_loudnorm_two_pass(self.src, out, preview=False)
        self.assertLessEqual(_true_peak(out), -1.0)

    def test_one_pass_holds_true_peak_after_aac(self):
        out = self.tmp / "draft.mp4"
        render.apply_loudnorm_two_pass(self.src, out, preview=True)
        self.assertLessEqual(_true_peak(out), -1.0)


if __name__ == "__main__":
    unittest.main()
