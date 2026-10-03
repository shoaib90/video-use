"""The animated push-in (`ranges[].zoom_to`) must stay concat-compatible.

A pushed segment goes through zoompan instead of scale/crop, so this renders a
static and a pushed segment from the same synthetic source and checks the
things the lossless `-c copy` concat (Rule 2) depends on: identical frame
size, frame count, frame rate and pixel aspect. It also checks that the push
really zooms (the last frame differs from the static one) and that it starts
where `zoom` says (the first frames match).
"""
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "helpers" / "render.py"
SPEC = importlib.util.spec_from_file_location("video_use_render_push", MODULE_PATH)
assert SPEC and SPEC.loader
render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render)


def _probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,sample_aspect_ratio,nb_read_frames",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(out.stdout)["streams"][0]


def _frame(path: Path, t: float, tmp: Path) -> bytes:
    png = tmp / f"f_{path.stem}_{t}.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(path),
                    "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", str(png)],
                   check=True)
    return png.read_bytes()


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class PushInTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.src = cls.tmp / "src.mp4"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y",
             "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=3",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
             str(cls.src)],
            check=True,
        )
        kw = dict(draft=True, rate="30", height=720)
        cls.static = cls.tmp / "static.mp4"
        cls.push = cls.tmp / "push.mp4"
        render.extract_segment(cls.src, 0.0, 2.5, "", cls.static, **kw)
        render.extract_segment(cls.src, 0.0, 2.5, "", cls.push, zoom=1.0, zoom_to=1.2, **kw)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_pushed_segment_matches_static_stream_parameters(self):
        a, b = _probe(self.static), _probe(self.push)
        for key in ("width", "height", "r_frame_rate", "nb_read_frames"):
            self.assertEqual(a[key], b[key], key)
        self.assertEqual(a.get("sample_aspect_ratio"), b.get("sample_aspect_ratio"))

    def test_push_starts_unzoomed_and_ends_zoomed(self):
        first_static = _frame(self.static, 0.0, self.tmp)
        first_push = _frame(self.push, 0.0, self.tmp)
        last_static = _frame(self.static, 2.4, self.tmp)
        last_push = _frame(self.push, 2.4, self.tmp)

        def mad(x: bytes, y: bytes) -> float:
            return sum(abs(p - q) for p, q in zip(x, y)) / len(x)

        self.assertLess(mad(first_static, first_push), 6.0)
        self.assertGreater(mad(last_static, last_push), 2 * mad(first_static, first_push) + 4.0)

    def test_zoom_to_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            render.extract_segment(self.src, 0.0, 1.0, "", self.tmp / "bad.mp4",
                                   draft=True, rate="30", height=720, zoom_to=0.9)


if __name__ == "__main__":
    unittest.main()
