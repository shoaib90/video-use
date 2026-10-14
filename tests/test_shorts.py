"""skills/shorts/scripts/shorts.py: the pure parts (framing, zoom alternation, captions, effects table).

Episode 4's Shorts (2026-10-14) were rebuilt through this script and matched the hand-built v2
byte for byte (EDL ranges, captions, plates; one mix's audio exactly). These tests pin the
pieces that made that true.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("shorts", ROOT / "skills/shorts/scripts/shorts.py")
shorts = importlib.util.module_from_spec(spec)
sys.modules["shorts"] = shorts
spec.loader.exec_module(shorts)


class Framing(unittest.TestCase):
    def test_centred_face_at_1x_crops_the_middle(self):
        f = shorts.framing(0.5, 0.42, 1.0, 3840, 2160)
        self.assertNotIn("zoom", f)
        # 3840x2160 renders at 3414x1920; a centred face puts the 1080 window at (3414-1080)/2
        self.assertEqual(f["filter"], "crop=1080:1920:1166:0")

    def test_pushed_in_face_stays_centred(self):
        f = shorts.framing(0.533, 0.406, 1.12, 3840, 2160)
        self.assertEqual(f["zoom"], 1.12)
        self.assertEqual(f["filter"], "crop=1080:1920:1166:0")   # the zoom crop centres the face first

    def test_episode4_value(self):   # range 00 of the v1 money Short, measured face (0.497, 0.412)
        self.assertEqual(shorts.framing(0.497, 0.412, 1.0, 3840, 2160)["filter"], "crop=1080:1920:1156:0")

    def test_face_at_the_edge_clamps_inside_the_frame(self):
        self.assertEqual(shorts.framing(0.02, 0.4, 1.0, 3840, 2160)["filter"], "crop=1080:1920:0:0")
        x = int(shorts.framing(0.99, 0.4, 1.0, 3840, 2160)["filter"].split(":")[2])
        self.assertEqual(x, 3414 - 1080)

    def test_crop_x_is_even(self):
        for fx in (0.31, 0.47, 0.5013, 0.66):
            self.assertEqual(int(shorts.framing(fx, 0.4, 1.0, 3840, 2160)["filter"].split(":")[2]) % 2, 0)

    def test_1080p_source(self):
        # a 1920x1080 source renders at 3414x1920 too: same window geometry
        self.assertEqual(shorts.framing(0.5, 0.4, 1.0, 1920, 1080)["filter"], "crop=1080:1920:1166:0")


class Zooms(unittest.TestCase):
    def test_alternation(self):
        self.assertEqual(shorts.next_zoom(None), 1.0)
        self.assertEqual(shorts.next_zoom(1.0), 1.12)
        self.assertEqual(shorts.next_zoom(1.12), 1.0)
        self.assertEqual(shorts.next_zoom(1.25), 1.0)     # after a punch-in, back to the wide


class Captions(unittest.TestCase):
    def test_accent_markup(self):
        self.assertEqual(shorts.colour("some *LeetCode*"), r"some {\c&H3554F2&}LeetCode{\c&HFFFFFF&}")
        self.assertEqual(shorts.colour("no accent"), "no accent")

    def test_ass_time(self):
        self.assertEqual(shorts.ass_time(0.03), "0:00:00.03")
        self.assertEqual(shorts.ass_time(61.256), "0:01:01.26")

    def test_bursts_run_to_the_next_burst_and_the_last_is_capped(self):
        times = [0.0, 0.5, 1.0, 1.6, 2.0]
        ev = shorts.ass_events([(0, "a b"), (2, "c *d*"), (4, "e")], times, total=2.4)
        self.assertEqual(len(ev), 3)
        self.assertIn("0:00:00.00,0:00:00.99,Burst", ev[0])     # to the next burst's onset, less 10 ms
        self.assertIn("0:00:01.00,0:00:01.99,Burst", ev[1])
        self.assertIn("0:00:02.00,0:00:02.39,Burst", ev[2])     # min(total, last word + 0.8)
        self.assertTrue(all(shorts.POP in e for e in ev))


class Effects(unittest.TestCase):
    def test_sfx_names_come_from_the_motion_graphics_table(self):
        lib = shorts.sfx_lib()
        self.assertIn("hit_soft", lib)
        rel, off, _ = lib["hit_soft"]
        self.assertTrue(rel.startswith("structural/"))
        self.assertAlmostEqual(off, 1.858)


if __name__ == "__main__":
    unittest.main()
