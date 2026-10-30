"""Segment reuse and parallel extraction, on real ffmpeg output.

The promises under test: a re-render builds only what changed, parallel output is
frame-identical to serial, and nothing can write through a hard link into the cache.
"""
import contextlib
import hashlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "helpers"))
import render  # noqa: E402


def framemd5(path: Path) -> str:
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0", "-f", "framemd5", "-"],
                         capture_output=True, text=True, check=True).stdout
    lines = [l for l in out.splitlines() if not l.startswith("#")]
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


class ReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.src = cls.tmp / "a.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=30:d=6",
                        "-f", "lavfi", "-i", "sine=f=440:r=48000:d=6", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", str(cls.src)], check=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.edit = Path(tempfile.mkdtemp(dir=self.tmp))

    def edl(self, *spans):
        return {"sources": {"a": str(self.src)}, "grade": "none",
                "ranges": [{"source": "a", "start": s, "end": e} for s, e in spans]}

    def extract(self, edl, **kw):
        real = render.extract_segment
        built = []

        def spy(source, start, *a, **k):
            built.append(start)
            return real(source, start, *a, **k)

        kw.setdefault("reuse", True)
        with patch.object(render, "extract_segment", spy), contextlib.redirect_stdout(io.StringIO()):
            segs = render.extract_all_segments(edl, self.edit, preview=False, draft=True,
                                               fps="30", exposure_check=False, **kw)
        return segs, built

    def test_second_render_builds_nothing(self):
        edl = self.edl((0, 1), (2, 3))
        _, first = self.extract(edl)
        _, second = self.extract(edl)
        self.assertEqual(len(first), 2)
        self.assertEqual(second, [])

    def test_changing_one_range_builds_only_that_range(self):
        self.extract(self.edl((0, 1), (2, 3)))
        _, built = self.extract(self.edl((0, 1), (2, 3.5)))
        self.assertEqual(built, [2])

    def test_a_recut_that_shifts_positions_still_reuses(self):
        self.extract(self.edl((0, 1), (2, 3)))
        segs, built = self.extract(self.edl((4, 5), (0, 1), (2, 3)))
        self.assertEqual(built, [4])
        self.assertEqual(len(segs), 3)
        self.assertEqual(segs[1].name, "seg_01_a.mp4")

    def test_a_changed_setting_rebuilds(self):
        edl = self.edl((0, 1))
        self.extract(edl)
        edl["ranges"][0]["zoom"] = 1.2
        _, built = self.extract(edl)
        self.assertEqual(built, [0])

    def test_a_replaced_source_rebuilds(self):
        edl = self.edl((0, 1))
        self.extract(edl)
        src2 = self.edit / "b.mp4"
        shutil.copy(self.src, src2)
        with open(src2, "ab") as f:
            f.write(b"\0")
        edl["sources"]["a"] = str(src2)
        _, built = self.extract(edl)
        self.assertEqual(built, [0])

    def test_new_tool_code_rebuilds(self):
        edl = self.edl((0, 1))
        self.extract(edl)
        with patch.object(render, "tool_fingerprint", return_value="different"):
            _, built = self.extract(edl)
        self.assertEqual(built, [0])

    def test_a_file_read_by_a_filter_is_part_of_the_key(self):
        model = self.edit / "model.bin"
        model.write_text("one")
        edl = self.edl((0, 1))
        edl["audio_filter"] = f"volume=1,anull='{model}'"
        kw = {"audio_prefilter": edl["audio_filter"]}
        before = render.segment_key(self.src, 0, 1, "", kw)
        model.write_text("three")
        self.assertNotEqual(before, render.segment_key(self.src, 0, 1, "", kw))

    def test_segment_is_hard_linked_and_a_later_write_leaves_the_cache_alone(self):
        segs, _ = self.extract(self.edl((0, 1)))
        entry = next((self.edit / "clips_cache").glob("*.mp4"))
        self.assertEqual(segs[0].stat().st_ino, entry.stat().st_ino)
        before = framemd5(entry)
        render.extract_segment(self.src, 3, 1, "", segs[0], draft=True, rate="30")
        self.assertEqual(framemd5(entry), before)

    def test_a_failed_extract_publishes_nothing(self):
        edl = self.edl((0, 1))
        edl["ranges"][0]["filter"] = "nosuchfilter"
        with self.assertRaises(subprocess.CalledProcessError):
            self.extract(edl)
        self.assertEqual(list((self.edit / "clips_cache").glob("*")), [])

    def test_parallel_matches_serial_and_keeps_order(self):
        spans = [(0, 0.5), (1, 1.5), (2, 2.5), (3, 3.5), (4, 4.5)]
        serial, _ = self.extract(self.edl(*spans), jobs=1, reuse=False)
        hashes = [framemd5(p) for p in serial]
        self.edit = Path(tempfile.mkdtemp(dir=self.tmp))
        parallel, _ = self.extract(self.edl(*spans), jobs=4)
        self.assertEqual([framemd5(p) for p in parallel], hashes)
        self.assertEqual([p.name for p in parallel], [p.name for p in serial])

    def test_each_source_is_probed_once(self):
        with patch.object(render, "is_hdr_source", return_value=False) as hdr, \
             patch.object(render, "is_portrait_source", return_value=False) as portrait:
            self.extract(self.edl((0, 0.5), (1, 1.5), (2, 2.5)), reuse=False)
        self.assertEqual(hdr.call_count, 1)
        self.assertEqual(portrait.call_count, 1)


if __name__ == "__main__":
    unittest.main()
