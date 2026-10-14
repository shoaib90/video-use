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
    def test_broll_window_centres_on_the_subject_and_clamps(self):
        self.assertEqual(shorts.broll_crop(0.5, 1280, 720), 436)          # 405 wide, centred
        self.assertEqual(shorts.broll_crop(0.0, 1280, 720), 0)
        self.assertEqual(shorts.broll_crop(1.0, 1280, 720), 874)          # 1280 - 405, even
        self.assertEqual(shorts.broll_crop(0.23, 1280, 720) % 2, 0)

    def test_inherits_the_overlapping_parent_range_settings(self):
        P = [{"source": "A", "start": 0, "end": 10, "filter": "cas=strength=0.6"},
             {"source": "A", "start": 10, "end": 30, "filter": "cas=strength=0.35", "grade": "none"},
             {"source": "A", "start": 30, "end": 40, "video": {"source": "CAM2"}, "filter": "x"},
             {"source": "B", "start": 0, "end": 40, "filter": "y"}]
        self.assertEqual(shorts.inherited(P, "A", 8, 20), {"filter": "cas=strength=0.35", "grade": "none"})
        self.assertEqual(shorts.inherited(P, "A", 2, 9), {"filter": "cas=strength=0.6"})
        self.assertEqual(shorts.inherited(P, "A", 31, 39), {"filter": "cas=strength=0.35", "grade": "none"})  # nearest own-camera range
        self.assertEqual(shorts.inherited(P, "A", 300, 310), {})        # nothing within 120 s
        self.assertEqual(shorts.inherited(P, "C", 0, 5), {})

    def test_pick_face_by_side_ignores_a_small_third_face(self):
        deepak, shoaib, poster = (300, 120, 60, 70, .9), (560, 125, 58, 68, .9), (900, 40, 20, 22, .6)
        boxes = [shoaib, poster, deepak]
        self.assertEqual(shorts.pick_face(boxes, "left"), deepak[:4])
        self.assertEqual(shorts.pick_face(boxes, "right"), shoaib[:4])
        self.assertEqual(shorts.pick_face(boxes, None), deepak[:4])     # largest
        self.assertIsNone(shorts.pick_face([], "left"))
        self.assertIsNone(shorts.pick_face([deepak], "right"))          # the speaker turned away: no frame

    def test_band_db_hears_a_click_and_not_a_low_hum(self):
        import numpy as np
        t = np.arange(48000) / 48000
        hum = 0.1 * np.sin(2 * np.pi * 100 * t)
        click = hum.copy(); click[24000:24480] += 0.1 * np.sin(2 * np.pi * 3000 * t[:480])
        self.assertGreater(shorts.excess(click, hum, 0.5, 0.0), 20.0)
        self.assertLess(shorts.excess(hum, hum, 0.5, 0.0), 0.1)

    def test_cards_under_the_plate_are_caught(self):
        T = {"three interviews": 0.68, "six am": 6.24, "first": 2.9}.get
        cards = [{"id": "three", "at": "three interviews"}, {"id": "six", "at": "six am"},
                 {"id": "stat", "steps": [{"at": "first"}]}]
        self.assertEqual(shorts.cards_under_plate(cards, T, 3.0), ["three at 0.68 s", "stat at 2.90 s"])

    def test_tight_edges_skip_contiguous_ranges(self):
        speech = [(10.0, 11.05), (12.5, 13.0)]          # speech spans; quiet elsewhere
        level = lambda src, t: -20.0 if any(a <= t < b for a, b in speech) else -60.0
        R = [{"source": "A", "start": 9.5, "end": 11.0, "quote": "…के"},       # clips: speech to 11.05
             {"source": "A", "start": 12.6, "end": 13.0, "quote": "x"},        # IN inside speech
             {"source": "A", "start": 13.0, "end": 14.0, "quote": "y"}]        # contiguous with #1
        got = tight_edges = shorts.tight_edges(R, level)
        self.assertEqual([g[:8] for g in got], ["#00 OUT ", "#01 IN  "])

    def test_relative_parent_sources_resolve_against_the_parent_folder(self):
        parent = Path("/videos/episode2/edit")
        self.assertEqual(shorts.source_path(parent, "../IMG_3672.mov"), "/videos/episode2/IMG_3672.mov")
        self.assertEqual(shorts.source_path(parent, "prepped/A.mp4"), "/videos/episode2/edit/prepped/A.mp4")
        self.assertEqual(shorts.source_path(parent, "/abs/B.mov"), "/abs/B.mov")

    def test_sfx_names_come_from_the_motion_graphics_table(self):
        lib = shorts.sfx_lib()
        self.assertIn("hit_soft", lib)
        rel, off, _ = lib["hit_soft"]
        self.assertTrue(rel.startswith("structural/"))
        self.assertAlmostEqual(off, 1.858)


if __name__ == "__main__":
    unittest.main()
