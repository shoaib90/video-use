"""T10: a landscape picture sitting in bars on a portrait render. Real encodes."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "helpers"))
import review  # noqa: E402


def encode(path: Path, chain: str):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=30", "-t", "2", "-filter_complex", chain,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)


class BarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._t = tempfile.TemporaryDirectory()
        cls.t = Path(cls._t.name)

    @classmethod
    def tearDownClass(cls):
        cls._t.cleanup()

    def spans(self, name: str, chain: str):
        p = self.t / name
        encode(p, chain)
        return review.bar_spans(p)

    def test_black_bars_flagged(self):
        self.assertTrue(self.spans("black.mp4", "scale=1080:608,pad=1080:1920:0:656"))

    def test_blurred_bars_flagged(self):
        chain = ("split[a][b];[a]scale=1080:1920,gblur=sigma=40,eq=brightness=-0.25[bg];"
                 "[b]scale=1080:1080[fg];[bg][fg]overlay=0:420")
        self.assertTrue(self.spans("blur.mp4", chain))

    def test_full_frame_passes(self):
        self.assertEqual(self.spans("full.mp4", "crop=607:1080,scale=1080:1920"), [])


if __name__ == "__main__":
    unittest.main()
