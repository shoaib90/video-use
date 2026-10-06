"""helpers/review.py edge checks, on synthetic transcripts (kb/mistakes.md M001-M005)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "helpers"))
import review  # noqa: E402


def words(spec):
    """spec: list of (text, start, dur)."""
    return [{"type": "word", "text": t, "start": s, "end": s + d, "speaker_id": "speaker_0", "confidence": 0.9}
            for t, s, d in spec]


def seq(text, t0, step=0.3, dur=0.25):
    return [(w, t0 + n * step, dur) for n, w in enumerate(text.split())]


class EdgeChecks(unittest.TestCase):
    def run_checks(self, ws, stories, exempt=lambda k: False):
        st = [(s[0], s[1], s[2], 0.0, 0.0, 0) for s in stories]
        flags, _ = review.edge_checks(Path("."), st, lambda src: ws, exempt)
        return {(f[1], f[3]) for f in flags}

    def test_answer_without_its_question_is_flagged(self):
        # M002: the question's sentences end in full stops/'?', so C1 alone misses it
        ws = words(seq("growing up every kid has something special. what was it for you?", 0.0)
                   + seq("For me it was sports. I played every day.", 4.0))
        got = self.run_checks(ws, [("S", 3.95, 7.0)])
        self.assertIn(("C2", "IN"), got)

    def test_clean_question_start_passes(self):
        ws = words(seq("growing up every kid has something special. what was it for you?", 0.0)
                   + seq("For me it was sports.", 4.0))
        got = self.run_checks(ws, [("S", 0.0, 6.0)])
        self.assertFalse({g for g in got if g[0] in ("C1", "C2", "C3", "C5", "C6")})

    def test_in_after_non_final_word(self):  # M001
        ws = words(seq("I went to the school and then I played volleyball.", 0.0))
        got = self.run_checks(ws, [("S", 1.75, 4.0)])
        self.assertIn(("C1", "IN"), got)

    def test_out_mid_sentence_and_dangling(self):  # M003
        ws = words(seq("she always came first in every class of ours.", 0.0))
        got = self.run_checks(ws, [("S", 0.0, 1.8)])   # ends on "every"
        self.assertIn(("C5", "OUT"), got)
        got = self.run_checks(words(seq("she came first in हर class.", 0.0)), [("S", 0.0, 1.5)])  # ends on "हर"
        self.assertIn(("C6", "OUT"), got)

    def test_ghost_duplicate_near_edge(self):  # M005
        ws = words([("Senior", 10.0, 0.24), ("product", 10.24, 0.15), ("designer.", 10.39, 0.08),
                    ("Senior", 10.47, 0.4), ("product", 10.87, 0.3), ("designer.", 11.17, 0.7)])
        got = self.run_checks(ws, [("S", 10.0, 10.47)])
        self.assertIn(("C7", "OUT"), got)

    def test_exempt_teaser_skips_context_but_not_out(self):
        ws = words(seq("growing up every kid has something special. what was it for you?", 0.0)
                   + seq("For me it was sports and every", 4.0))
        got = self.run_checks(ws, [("S", 3.95, 5.6)], exempt=lambda k: True)
        self.assertNotIn(("C2", "IN"), got)
        self.assertIn(("C5", "OUT"), got)

    def test_story_ranges_merge_abutting_shots(self):
        edl = {"ranges": [{"source": "A", "start": 0.0, "end": 2.0}, {"source": "A", "start": 2.0, "end": 5.0},
                          {"source": "A", "start": 9.0, "end": 10.0}]}
        st, _, _ = review.story_ranges(edl, 30.0)
        self.assertEqual([(s[1], s[2]) for s in st], [(0.0, 5.0), (9.0, 10.0)])

    def test_caps_unsafe_stamp(self):  # M020
        g = review.graphics_checks({"cards": [{"id": "x", "kind": "stamp", "text": "24 SSBs"},
                                              {"id": "y", "kind": "stamp", "text": "SSB × 24"}]})
        self.assertEqual([x[1] for x in g], ["G2"])


if __name__ == "__main__":
    unittest.main()


class Calibration(unittest.TestCase):
    """False positives found on podcast Episode 1 v7 (2026-10-05), each pinned."""
    def flags(self, ws, stories, exempt=lambda k: False):
        st = [(s[0], s[1], s[2], 0.0, 0.0, 0) for s in stories]
        return review.edge_checks(Path("."), st, lambda src: ws, exempt)[0]

    def test_tag_question_is_not_a_question(self):
        ws = words(seq("you were a jolly kid, correct?", 0.0) + seq("Yes I was always playing.", 3.0))
        self.assertFalse([f for f in self.flags(ws, [("S", 2.95, 5.0)]) if f[1] == "C2"])

    def test_tightening_join_is_low_not_high(self):
        # "I have seen | up seen | him growing up" -> stumble removed, resumes 1 s later
        ws = words(seq("I have seen up seen him growing up playing sports.", 0.0))
        f = self.flags(ws, [("S", 0.0, 0.85), ("S", 1.5, 3.0)])
        self.assertEqual([(x[0], x[1]) for x in f if x[1] == "C5"], [("LOW", "C5")])

    def test_ghost_far_from_edge_is_not_flagged(self):
        ws = words([("Senior", 10.0, 0.24), ("product", 10.24, 0.15), ("designer.", 10.39, 0.08),
                    ("Senior", 10.47, 0.4), ("product", 10.87, 0.3), ("designer.", 11.17, 0.7), ("next", 13.0, 0.3)])
        self.assertFalse([f for f in self.flags(ws, [("S", 9.0, 11.9)]) if f[1] == "C7"])


class Calibration2(unittest.TestCase):
    def flags(self, ws, stories):
        st = [(s[0], s[1], s[2], 0.0, 0.0, 0) for s in stories]
        return review.edge_checks(Path("."), st, lambda src: ws)[0]

    def test_trimmed_filler_lead_in_is_low(self):
        ws = words(seq("we were talking. तो मतलब did you ever study?", 0.0))
        f = [x for x in self.flags(ws, [("S", 1.45, 3.0)]) if x[1] == "C1"]
        self.assertEqual([x[0] for x in f], ["LOW"])

    def test_punctuated_last_word_is_not_dangling(self):
        ws = words(seq("कुछ insight दे सकता है तो? हां.", 0.0))
        self.assertFalse([x for x in self.flags(ws, [("S", 0.0, 1.75)]) if x[1] == "C6"])
