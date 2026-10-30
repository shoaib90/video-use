"""sync_cameras.py on generated audio with a known offset, a wrong peak and a wrong camera clock."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "helpers"))
import sync_cameras as sc  # noqa: E402


def speechy_noise(seconds: float, seed: int) -> np.ndarray:
    """Noise bursts with irregular gaps: an envelope with one best alignment, like speech."""
    rng = np.random.default_rng(seed)
    out, n = [], int(seconds * sc.SR)
    made = 0
    while made < n:
        chunk = rng.normal(0, rng.uniform(0.05, 0.5), int(rng.uniform(0.1, 0.6) * sc.SR))
        chunk = np.concatenate([chunk, np.zeros(int(rng.uniform(0.05, 0.4) * sc.SR))])
        out.append(chunk)
        made += len(chunk)
    return np.concatenate(out)[:n].astype(np.float32)


def write(path: Path, audio: np.ndarray, created: str | None = None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sc.SR), "-ac", "1", "-i", "pipe:0"]
    if created:
        cmd += ["-metadata", f"creation_time={created}"]
    subprocess.run(cmd + ["-c:a", "aac", "-b:a", "128k", str(path)], input=audio.tobytes(), check=True)


class SyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._t = tempfile.TemporaryDirectory()
        cls.t = Path(cls._t.name)
        cls.audio = speechy_noise(240, seed=1)
        cls.master = cls.t / "master.mp4"
        write(cls.master, cls.audio, "2026-09-13T08:00:00Z")
        # The clip camera runs 10 s ahead of the master's clock.
        cls.clips = []
        for name, at, dur in (("a", 20.0, 25.0), ("b", 70.0, 30.0), ("c", 120.0, 25.0), ("d", 170.0, 30.0)):
            p = cls.t / f"{name}.mp4"
            s = int(at * sc.SR)
            noisy = cls.audio[s: s + int(dur * sc.SR)] + np.random.default_rng(7).normal(0, 0.01, int(dur * sc.SR)).astype(np.float32)
            write(p, noisy, f"2026-09-13T08:{int((at + 10) // 60):02d}:{int((at + 10) % 60):02d}Z")
            cls.clips.append(p)
        cls.broll = cls.t / "broll.mp4"
        write(cls.broll, speechy_noise(20, seed=99), "2026-09-13T11:00:00Z")

    @classmethod
    def tearDownClass(cls):
        cls._t.cleanup()

    def test_finds_known_offsets_and_the_clock_difference(self):
        r = sc.sync([self.master], self.clips, verbose=False)
        for stem, at in (("a", 20.0), ("b", 70.0), ("c", 120.0), ("d", 170.0)):
            self.assertEqual(r[stem]["status"], "synced", r[stem])
            self.assertAlmostEqual(r[stem]["offset"], at, delta=0.08)
            self.assertAlmostEqual(r[stem]["clock_s"], -10.0, delta=1.0)

    def test_clip_the_clocks_place_elsewhere_is_outside(self):
        r = sc.sync([self.master], [*self.clips, self.broll], verbose=False)
        self.assertEqual(r["broll"]["status"], "outside")

    def test_a_wrong_peak_is_relocked_by_the_clocks(self):
        real = sc.coarse_peak
        calls = {"n": 0}

        def wrong_first_time_for_d(env, master_env):
            at, conf = real(env, master_env)
            # The global search for clip d returns a confident peak in the wrong place.
            if len(env) == int(30.0 * sc.ENV_HZ) and len(master_env) > 200 * sc.ENV_HZ and abs(at - 170) < 1:
                calls["n"] += 1
                return 5.0, 30.0
            return at, conf

        with patch.object(sc, "coarse_peak", wrong_first_time_for_d):
            r = sc.sync([self.master], self.clips, verbose=False)
        self.assertEqual(calls["n"], 1)
        self.assertEqual(r["d"]["status"], "relocked", r["d"])
        self.assertAlmostEqual(r["d"]["offset"], 170.0, delta=0.08)

    def test_without_capture_times_it_reports_the_peak_only(self):
        with patch.object(sc, "capture_time", return_value=None):
            r = sc.sync([self.master], self.clips[:1], verbose=False)
        self.assertEqual(r["a"]["status"], "no_clock")
        self.assertAlmostEqual(r["a"]["offset"], 20.0, delta=0.08)

    def test_too_short_clips_are_skipped(self):
        short = self.t / "short.mp4"
        write(short, self.audio[:sc.SR])
        self.assertEqual(sc.sync([self.master], [short], verbose=False), {})


class CaptureTimeTests(unittest.TestCase):
    def probe(self, tags):
        import json
        out = subprocess.CompletedProcess([], 0, stdout=json.dumps({"format": {"tags": tags}}), stderr="")
        with patch.object(sc.subprocess, "run", return_value=out):
            return sc.capture_time(Path("x.mov"))

    def test_iphone_creationdate_wins_over_file_write_time(self):
        t = self.probe({"com.apple.quicktime.creationdate": "2026-09-13T13:36:51+0530",
                        "creation_time": "2026-09-13T10:00:00.000000Z"})
        self.assertEqual(t, self.probe({"creation_time": "2026-09-13T08:06:51Z"}))

    def test_missing_or_unparseable(self):
        self.assertIsNone(self.probe({}))
        self.assertIsNone(self.probe({"creation_time": "yesterday"}))


if __name__ == "__main__":
    unittest.main()
