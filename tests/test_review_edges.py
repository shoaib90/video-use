"""helpers/review.py edge checks, on synthetic transcripts (kb/mistakes.md M001-M005)."""
import json
import sys
import tempfile
import unittest

import numpy as np
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

    # ---- Episode 4 v1 (M042-M045)
    def run_mono(self, ws, stories):
        st = [(s[0], s[1], s[2], 0.0, 0.0, 0) for s in stories]
        flags, _ = review.edge_checks(Path("."), st, lambda src: ws, monologue=True)
        return {(f[0], f[1], f[3]) for f in flags}

    def test_monologue_mid_sentence_join_is_high(self):  # M042
        # real words removed inside a sentence: HIGH
        ws = words(seq("So I really really was rejected in my first two interviews.", 0.0))
        got = self.run_mono(ws, [("S", 0.0, 0.6), ("S", 1.15, 3.5)])
        self.assertIn(("HIGH", "C5", "OUT"), got)
        # only a filler / a pause removed: tightening, LOW (C15 checks the edges are quiet)
        ws = words(seq("So I", 0.0) + [("uh,", 1.0, 0.3)] + seq("was rejected in my first two interviews.", 3.0))
        got = self.run_mono(ws, [("S", 0.0, 0.6), ("S", 2.95, 5.2)])
        self.assertNotIn(("HIGH", "C5", "OUT"), got)
        self.assertIn(("LOW", "C5", "OUT"), got)
        # a cut between two whole sentences is clean
        ws2 = words(seq("I was rejected.", 0.0) + seq("Then I called.", 3.0))
        self.assertNotIn(("HIGH", "C5", "OUT"), self.run_mono(ws2, [("S", 0.0, 0.9), ("S", 2.95, 4.0)]))
        # the same join in a conversation stays a deliberate tightening (not HIGH)
        st = [(x[0], x[1], x[2], 0.0, 0.0, 0) for x in [("S", 0.0, 0.6), ("S", 2.95, 5.2)]]
        flags, _ = review.edge_checks(Path("."), st, lambda src: ws)
        self.assertFalse([f for f in flags if f[1] in ("C1", "C5") and f[0] == "HIGH"])

    def test_sliver_range(self):  # M043
        ws = words([("It", 3.92, 0.3)] + seq("was July 2019 and I was in my seventh semester.", 6.56))
        got = self.run_checks(ws, [("S", 3.9, 4.3), ("S", 6.5, 9.6)])
        self.assertIn(("C12", "IN"), got)          # 2.2 s gap: a splice from another attempt
        # "So," left alone by a trimmed pause (< 1.5 s, nothing said) is not a splice
        ws = words([("So,", 1.0, 0.3)] + seq("I think around February.", 2.2))
        got = self.run_checks(ws, [("S", 0.9, 1.4), ("S", 2.1, 3.5)])
        self.assertNotIn(("C12", "IN"), got)

    def test_edge_on_speech(self):  # M042: C15
        import wave, tempfile, os
        sr = 16000
        x = np.zeros(sr * 4, dtype=np.float32)
        x[sr:2 * sr] = 0.3 * np.sin(np.arange(sr) * 2 * np.pi * 200 / sr)   # "speech" 1-2 s
        f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False); f.close()
        with wave.open(f.name, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes((x * 32767).astype("<i2").tobytes())
        edl = {"sources": {"S": f.name}}
        st = [("S", 0.0, 1.5, 0, 0, 0), ("S", 3.0, 4.0, 0, 0, 1)]     # OUT at 1.5 s is mid-"speech"
        got = {(g[1], g[3]) for g in review.edge_level_checks(edl, st, Path("."))}
        self.assertIn(("C15", "OUT"), got)
        self.assertNotIn(("C15", "IN"), got)                          # IN at 3.0 s is silent
        st = [("S", 0.0, 0.5, 0, 0, 0), ("S", 2.5, 4.0, 0, 0, 1)]
        self.assertEqual(review.edge_level_checks(edl, st, Path(".")), [])
        os.unlink(f.name)

    def test_dead_lead_in(self):  # M044
        ws = words(seq("So this one is from Suma.", 14.87))
        self.assertIn(("C13", "IN"), self.run_checks(ws, [("S", 12.0, 16.8)]))
        self.assertNotIn(("C13", "IN"), self.run_checks(ws, [("S", 14.6, 16.8)]))

    def test_said_twice_in_the_cut(self):  # M045
        a = words(seq("Looking back what she saw is what got me hired.", 0.0))
        b = words(seq("Looking back what she saw is what got me hired again.", 0.0))
        st = [("A", 0.0, 3.0, 0, 0, 0), ("B", 0.0, 3.5, 0, 0, 1)]
        flags = review.dup_checks(st, lambda src: a if src == "A" else b)
        self.assertEqual([f[1] for f in flags], ["C14"])
        self.assertEqual(review.dup_checks(st[:1], lambda src: a), [])

    def test_sentence_opening_the_is_not_dangling(self):
        ws = words(seq("The real answer is in a note.", 0.3))
        self.assertNotIn(("C6", "IN"), self.run_checks(ws, [("S", 0.2, 2.6)]))
        ws = words(seq("I went to the school.", 0.0))
        self.assertIn(("C6", "IN"), self.run_checks(ws, [("S", 0.85, 1.6)]))   # starts on "the"

    def test_tightening_downgrade(self):
        st = [("S", 0.0, 1.0, 0, 0, 0), ("S", 1.5, 3.0, 0, 0, 1), ("S", 6.0, 7.0, 0, 0, 2)]
        flags = [("HIGH", "C1", 1, "IN", "x"), ("HIGH", "C5", 1, "OUT", "y"), ("HIGH", "C15", 1, "OUT", "z")]
        quiet = {(0, "OUT"): -60, (1, "IN"): -55, (1, "OUT"): -50, (2, "IN"): -50}
        got = review.downgrade_tightening(flags, st, quiet)
        self.assertEqual(got[0][0], "LOW")      # 0.5 s removed between quiet edges
        self.assertEqual(got[1][0], "HIGH")     # 3 s removed: a story cut, read it
        self.assertEqual(got[2][0], "HIGH")     # C15 itself never downgrades
        loud = dict(quiet); loud[(1, "IN")] = -20
        self.assertEqual(review.downgrade_tightening(flags[:1], st, loud)[0][0], "HIGH")

    def test_still_frame_hold(self):  # M046
        ws = words(seq("The answer was in that stack of notes.", 0.0))     # ends at 2.35
        self.assertIn(("C16", "OUT"), self.run_checks(ws, [("S", 0.0, 3.5)]))
        self.assertNotIn(("C16", "OUT"), self.run_checks(ws, [("S", 0.0, 2.6)]))
        ws = words(seq("That was my first week.", 0.0) + seq("That's not what she saw.", 3.5))
        self.assertIn(("C16", "IN"), self.run_checks(ws, [("S", 0.0, 4.9)]))   # 2.3 s with no word

    def test_still_confirmed_by_audio(self):  # M046
        import wave, tempfile, os
        sr = 16000
        x = np.zeros(sr * 4, dtype=np.float32)
        x[:2 * sr] = 0.3 * np.sin(np.arange(2 * sr) * 2 * np.pi * 200 / sr)   # speech to 2.0 s
        f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False); f.close()
        with wave.open(f.name, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes((x * 32767).astype("<i2").tobytes())
        edl = {"sources": {"S": f.name}}
        review._AUDIO.clear()
        flag = [("HIGH", "C16", 0, "OUT", "held")]
        held = review.confirm_stills(flag, [("S", 0.0, 3.5, 0, 0, 0)], edl, Path("."))   # 1.5 s silent tail
        self.assertEqual(held[0][0], "HIGH")
        drift = review.confirm_stills(flag, [("S", 0.0, 2.3, 0, 0, 0)], edl, Path("."))  # 0.3 s: word times drifted
        self.assertEqual(drift[0][0], "LOW")
        os.unlink(f.name)

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


class GoodbyeFraming(unittest.TestCase):  # M027
    def test_goodbye_on_a_single_is_flagged(self):
        edl = {"ranges": [{"source": "A", "start": 0, "end": 5, "frame": "TWO"},
                          {"source": "A", "start": 5, "end": 9, "frame": "SHOAIB"},
                          {"source": "E", "start": 0, "end": 16, "frame": "END"}]}
        self.assertEqual([g[1] for g in review.graphics_checks(edl)], ["G3"])

    def test_goodbye_on_the_wide_passes(self):
        edl = {"ranges": [{"source": "A", "start": 0, "end": 5, "frame": "SHOAIB"},
                          {"source": "A", "start": 5, "end": 9, "frame": "WIDE"},
                          {"source": "E", "start": 0, "end": 16, "frame": "END"}]}
        self.assertEqual(review.graphics_checks(edl), [])


class FalseStart(unittest.TestCase):  # M029
    def test_restart_is_flagged(self):
        ws = words(seq("यार तो as he said बक्चोदी करो and हम भी.", 0.0)
                   + seq("So yeah, as he said बक्चोदी करो और हमारा भी time.", 7.0))
        st = [("S", 0.0, 12.0, 0.0, 0.0, 0)]
        f = review.edge_checks(Path("."), st, lambda src: ws)[0]
        self.assertIn("C11", [x[1] for x in f])

    def test_no_repeat_no_flag(self):
        ws = words(seq("he went to school and then he played volleyball every evening.", 0.0))
        f = review.edge_checks(Path("."), [("S", 0.0, 4.0, 0.0, 0.0, 0)], lambda src: ws)[0]
        self.assertNotIn("C11", [x[1] for x in f])


class FalseStartNoise(unittest.TestCase):
    def test_emphatic_repeat_without_pause_is_not_flagged(self):
        ws = words(seq("Tier three, Tier four. Tier three, Tier four.", 0.0))
        f = review.edge_checks(Path("."), [("S", 0.0, 3.0, 0.0, 0.0, 0)], lambda src: ws)[0]
        self.assertNotIn("C11", [x[1] for x in f])

    def test_echo_by_the_other_speaker_is_not_flagged(self):
        a = words(seq("मेरे को पता है कि", 0.0))
        b = words(seq("मेरे को पता है ना", 4.0))
        for w in b:
            w["speaker_id"] = "speaker_1"
        f = review.edge_checks(Path("."), [("S", 0.0, 6.0, 0.0, 0.0, 0)], lambda src: a + b)[0]
        self.assertNotIn("C11", [x[1] for x in f])


class ParentCards(unittest.TestCase):  # M053
    """A Short (or any cut with an EDL `parent`) that keeps the phrase a parent card lands on must
    carry a card there. Episode 4 Shorts v1 dropped every one, and review still passed."""

    parent = [{"id": "ask12", "kind": "stamp", "text": "12 LPA", "at": "twelve LPA package"},
              {"id": "offers", "kind": "stat", "label": "Offers",
               "steps": [{"at": "six LPA", "value": "6"}, {"at": "seven and a half LPA", "value": "7.5"}]},
              {"id": "lakh", "kind": "stamp", "text": "1 lakh", "at": "one lakh"}]
    kept = {"six LPA": 46.8, "seven and a half LPA": 55.0, "but within": 49.3}

    def find(self, p):
        return self.kept.get(p)

    def test_kept_phrase_without_a_card_is_flagged(self):
        g = review.parent_card_gaps(self.parent, [], self.find)
        self.assertEqual([x[1] for x in g], ["G4"])          # offers only: 12 LPA and lakh are not kept
        self.assertIn("offers", g[0][2])

    def test_card_near_the_phrase_satisfies_it(self):
        own = [{"id": "o", "kind": "stamp", "text": "6 LPA", "at": "six LPA"}]
        self.assertEqual(review.parent_card_gaps(self.parent, own, self.find), [])

    def test_card_elsewhere_does_not(self):
        own = [{"id": "x", "kind": "stamp", "text": "Then", "at": "but within"}]   # 2.5 s off
        self.assertEqual(len(review.parent_card_gaps(self.parent, own, self.find)), 1)

    def test_no_parent_no_check(self):
        self.assertEqual(review.parent_checks({"ranges": []}, Path("."), 30.0), [])


class CaptionFragments(unittest.TestCase):  # M056: T8
    @staticmethod
    def _srt(lines):
        return "\n\n".join(f"{i}\n00:00:0{i},000 --> 00:00:0{i},900\n{t}" for i, t in enumerate(lines, 1))

    def test_fragments_stranded_by_picture_cuts_are_counted(self):
        n, short, ex = review.caption_fragments(self._srt(
            ["And in 2023, the doctor told", "me, you are done.", "first job.", "go for surgery."]))
        self.assertEqual((n, short), (4, 2))
        self.assertIn("first job.", ex)

    def test_sentence_cues_pass_the_share(self):
        n, short, _ = review.caption_fragments(self._srt(
            ["And in 2023, the doctor told me, you are done.", "So by May 2021, I got my first job."]))
        self.assertLessEqual(short / n, review.FRAGMENT_SHARE)
