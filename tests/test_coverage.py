"""Coverage report: where a cut goes quiet, and what to put there.

The numbers this tool exists to surface were measured on a real delivered
episode: 2.8 visual events/min against 8.6 in a professional reference, and a
single 124.9s stretch — 58% of the film — with nothing changing at all, while
nine b-roll assets sat unused.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "video_use_coverage", Path(__file__).parents[1] / "helpers" / "coverage.py")
cov = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cov
SPEC.loader.exec_module(cov)


def srt(path, cues):
    def ts(x):
        h, r = divmod(x, 3600)
        m, s_ = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{s_:06.3f}".replace(".", ",")
    path.write_text("\n\n".join(
        f"{i+1}\n{ts(a)} --> {ts(b)}\n{t}" for i, (a, b, t) in enumerate(cues)))


class SrtTests(unittest.TestCase):
    def test_parses_and_selects_by_window(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.srt"
            srt(p, [(0.0, 2.0, "first line."), (10.0, 12.0, "second line."),
                    (30.0, 32.0, "third line.")])
            cues = cov.srt_cues(p)
            self.assertEqual(len(cues), 3)
            self.assertIn("second", cov.said_between(cues, 8, 20))
            self.assertNotIn("third", cov.said_between(cues, 8, 20))

    def test_missing_srt_is_not_fatal(self):
        self.assertEqual(cov.srt_cues(Path("/nope/none.srt")), [])


class InsertionPointTests(unittest.TestCase):
    def test_a_long_gap_gets_several_points_on_sentence_ends(self):
        """A 125-second hole does not want one graphic, it wants three or four."""
        cues = [(float(i) * 10, float(i) * 10 + 3, f"sentence {i}.") for i in range(14)]
        pts = cov.insertion_points(cues, 0.0, 130.0, every=30.0)
        self.assertGreaterEqual(len(pts), 3)
        gaps = [b[0] - a[0] for a, b in zip(pts, pts[1:])]
        self.assertTrue(all(g >= 29.9 for g in gaps), "points bunched together")

    def test_only_sentence_ends_qualify(self):
        cues = [(0.0, 40.0, "a clause that keeps going and going"),
                (41.0, 80.0, "and still going")]
        self.assertEqual(cov.insertion_points(cues, 0.0, 100.0), [])


class RetentionTests(unittest.TestCase):
    """YouTube's export format varies by locale and version, so the parser
    matches loosely rather than assuming a schema."""

    def _load(self, text, total=200.0):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "r.csv"
            p.write_text(text)
            return cov.load_retention(p, total)

    def test_fraction_positions_are_scaled_to_seconds(self):
        c = self._load("position,retention\n0,100\n0.5,60\n1.0,35\n")
        self.assertAlmostEqual(c[-1][0], 200.0, places=3)
        self.assertAlmostEqual(c[-1][1], 35.0, places=3)

    def test_percentage_positions_are_scaled(self):
        c = self._load("pos,ret\n0,100\n50,60\n100,30\n")
        self.assertAlmostEqual(c[-1][0], 200.0, places=3)

    def test_header_rows_and_percent_signs_survive(self):
        c = self._load("Video position,Absolute retention\n0%,100%\n100%,40%\n")
        self.assertEqual(len(c), 2)
        self.assertAlmostEqual(c[-1][1], 40.0)

    def test_lookup_picks_the_nearest_sample(self):
        c = [(0.0, 100.0), (100.0, 50.0), (200.0, 20.0)]
        self.assertEqual(cov.retention_at(c, 98.0), 50.0)
        self.assertIsNone(cov.retention_at([], 5.0))


class BrollTests(unittest.TestCase):
    def test_only_b_roll_is_offered_not_a_roll_outtakes(self):
        """Rejected takes sitting in the project root are not spare coverage,
        and offering them as b-roll is noise."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "b-roll").mkdir()
            (root / "b-roll" / "cricket.png").write_text("")
            (root / "b-roll" / "mri1.jpeg").write_text("")
            (root / "IMG_9999.MOV").write_text("")        # an a-roll outtake
            names = [p.name for p in cov.unused_broll(root, {})]
            self.assertIn("cricket.png", names)
            self.assertNotIn("IMG_9999.MOV", names)

    def test_assets_already_in_the_cut_are_excluded_and_none_repeat(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "b-roll").mkdir()
            for n in ("used.mp4", "spare.mp4"):
                (root / "b-roll" / n).write_text("")
            edl = {"sources": {"A": "/wherever/used.mp4"}}
            names = [p.name for p in cov.unused_broll(root, edl)]
            self.assertEqual(names, ["spare.mp4"])
            self.assertEqual(len(names), len(set(names)))


class TreatmentTimeTests(unittest.TestCase):
    def test_graphics_and_overlays_count_as_visual_events(self):
        """Scene detection cannot see a title fading in over a locked-off shot,
        so counting shot changes alone understates a graphics-heavy cut."""
        edl = {"overlays": [{"start_in_output": 5.0, "duration": 3}],
               "graphics": [{"start": 20.0}],
               "demotions": [{"start": 40.0, "end": 50.0}]}
        self.assertEqual(sorted(cov.treatment_times(edl)), [5.0, 20.0, 40.0, 50.0])

    def test_an_edl_with_none_of_them_is_empty_not_an_error(self):
        self.assertEqual(cov.treatment_times({}), [])


if __name__ == "__main__":
    unittest.main()


class ViewerCountTests(unittest.TestCase):
    """A retention curve from a handful of viewers is mostly quantisation.

    Measured on a real export: every value was a multiple of 4.76 = 1/21, so
    each visible 'drop' was one person leaving. The report says so rather than
    letting the shape be over-read.
    """

    def test_infers_n_from_the_quantisation_step(self):
        vals = [round(k / 21 * 100, 2) for k in (21, 20, 17, 15, 11, 11, 12)]
        self.assertEqual(cov.viewer_count(vals), 21)

    def test_a_smooth_curve_implies_many_viewers(self):
        vals = [100 - i * 0.37 for i in range(50)]
        n = cov.viewer_count(vals)
        self.assertTrue(n is None or n > 200, f"got {n}")

    def test_flat_curve_is_not_a_crash(self):
        self.assertIsNone(cov.viewer_count([50.0, 50.0, 50.0]))


class BenchmarkColumnTests(unittest.TestCase):
    def test_third_column_is_preferred_over_raw_retention(self):
        """'Compared to other videos' is normalised, so it survives small n
        where the raw curve does not."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "organic.csv"
            p.write_text("Video position (%),Absolute retention (%),Compared (%)\n"
                         "0,95.24,32.23\n50,30.00,-25.40\n100,33.33,60.80\n")
            c = cov.load_retention(p, 200.0)
            self.assertEqual([v for _, v in c], [32.23, -25.40, 60.80])

    def test_two_column_export_still_uses_retention(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "all.csv"
            p.write_text("pos,ret\n0,95.24\n100,33.33\n")
            self.assertEqual([v for _, v in cov.load_retention(p, 200.0)],
                             [95.24, 33.33])


class MetricLabelTests(unittest.TestCase):
    """A percentile printed with a % sign reads as 'a third of people stayed'
    when it actually means 'a third worse than a typical video'."""

    def test_metric_is_reported_per_file(self):
        with tempfile.TemporaryDirectory() as td:
            three = Path(td) / "organic.csv"
            three.write_text("pos,ret,cmp\n0,95.2,32.2\n100,33.3,60.8\n")
            cov.load_retention(three, 200.0)
            self.assertEqual(cov.LAST_METRIC, "benchmark")

            two = Path(td) / "all.csv"
            two.write_text("pos,ret\n0,95.2\n100,33.3\n")
            cov.load_retention(two, 200.0)
            self.assertEqual(cov.LAST_METRIC, "retention")
