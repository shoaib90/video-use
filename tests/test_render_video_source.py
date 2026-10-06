"""`ranges[].video` takes the PICTURE from a second, synced camera; audio stays put.

Podcast use: a DSLR (25 fps, its own scratch audio) shot singles while the iPhone
(30 fps) recorded the master audio. The segment must carry the iPhone's audio, the
DSLR's frames from `start - offset`, and match an ordinary segment exactly in size,
rate and frame count so the `-c copy` concat (Rule 2) still holds.
"""
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "helpers" / "render.py"
SPEC = importlib.util.spec_from_file_location("video_use_render_vsrc", MODULE_PATH)
assert SPEC and SPEC.loader
render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render)


def _probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames",
         "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(out.stdout)["streams"][0]


def _peak_hz(path: Path) -> float:
    """Dominant audio frequency, via ffmpeg's astats zero-crossing rate."""
    out = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af",
         "astats=measure_perchannel=Zero_crossings_rate:measure_overall=none", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    zcr = float(re.search(r"Zero crossings rate: ([0-9.]+)", out).group(1))
    return zcr * 48000 / 2


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class VideoSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.main = cls.tmp / "main.mp4"     # "iPhone": 30 fps, 440 Hz audio
        cls.cam = cls.tmp / "cam.mp4"       # "DSLR": 25 fps solid red, 1000 Hz scratch audio
        subprocess.run(["ffmpeg", "-v", "error", "-y",
                        "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=6",
                        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=6",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                        str(cls.main)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y",
                        "-f", "lavfi", "-i", "color=c=0xD02020:size=1280x720:rate=25:duration=6",
                        "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=6",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                        str(cls.cam)], check=True)
        kw = dict(rate="30", height=360, crf="18", preview=True)
        cls.plain = cls.tmp / "plain.mp4"
        cls.alt = cls.tmp / "alt.mp4"
        cls.alt_push = cls.tmp / "alt_push.mp4"
        render.extract_segment(cls.main, 1.0, 3.0, "", cls.plain, **kw)
        render.extract_segment(cls.main, 1.0, 3.0, "", cls.alt, video_source=cls.cam,
                               video_start=0.5, zoom=1.5, zoom_x=0.5, **kw)
        render.extract_segment(cls.main, 1.0, 3.0, "", cls.alt_push, video_source=cls.cam,
                               video_start=0.5, zoom=1.2, zoom_to=1.4, **kw)

    def test_matches_an_ordinary_segment_for_concat(self):
        p = _probe(self.plain)
        for seg in (self.alt, self.alt_push):
            q = _probe(seg)
            for k in ("width", "height", "r_frame_rate", "nb_read_frames"):
                self.assertEqual(p[k], q[k], f"{seg.name}: {k}")

    def test_audio_stays_on_the_main_source(self):
        self.assertAlmostEqual(_peak_hz(self.alt), 440, delta=40)

    def test_picture_comes_from_the_second_camera(self):
        def mean_rgb(path):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "1", "-i", str(path), "-frames:v", "1",
                                  "-vf", "scale=1:1:flags=area", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
                                 capture_output=True, check=True).stdout
            return tuple(raw[:3])
        r, g, b = mean_rgb(self.alt)
        self.assertGreater(r, 150)        # the solid-red second camera
        self.assertLess(g, 80)
        self.assertNotEqual(mean_rgb(self.plain), (r, g, b))

if __name__ == "__main__":
    unittest.main()
