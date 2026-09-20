"""Script-to-graphic opportunity detection.

The detector was built against a reference edit (Somrat Dutta, "If You ONLY
Watch One Motion Design Video") by reading what was on screen at each spoken
line. These tests pin the cases that were got WRONG on the way there, because
every one of them failed silently - a detector that misses is indistinguishable
from a script with nothing in it, and a detector that over-fires buries the
real hits.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "video_use_script_scan", Path(__file__).parents[1] / "helpers" / "script_scan.py")
ss = importlib.util.module_from_spec(SPEC)
# register before exec: @dataclass resolves annotations via
# sys.modules[cls.__module__], which is None for an unregistered module
sys.modules[SPEC.name] = ss
SPEC.loader.exec_module(ss)


def words(sentence, t0=0.0, rate=0.35):
    """Word list with plausible timings; punctuation is preserved because the
    sentence splitter depends on it."""
    out, t = [], t0
    for tok in sentence.split():
        out.append({"type": "word", "text": tok, "start": round(t, 3),
                    "end": round(t + rate * 0.8, 3)})
        t += rate
    return out


class NumberParsingTests(unittest.TestCase):
    def test_plain_and_compound(self):
        for text, want in [("fifteen thousand", 15000),
                           ("twelve thousand nine hundred seventeen", 12917),
                           ("one lakh", 100_000),
                           ("thirteen", 13)]:
            self.assertEqual(ss._read_number(text.split())[0], want, text)

    def test_indian_spoken_idiom(self):
        # "two fifty rupees" is 250, not 2 + 50
        self.assertEqual(ss._read_number("two fifty rupees".split())[0], 250)
        self.assertEqual(ss._read_number("one twenty".split())[0], 120)

    def test_a_comma_ends_the_number(self):
        # "hundred, hundred and fifty kilometers" is two alternatives; without
        # a comma boundary it parses as 10,050
        self.assertEqual(ss._read_number("hundred, hundred and fifty".split())[0], 100)

    def test_bare_plural_scale_is_indefinite(self):
        # "costing you lakhs every year" states no figure
        self.assertIsNone(ss._read_number("lakhs every year".split())[0])


class SalienceTests(unittest.TestCase):
    """Not every number deserves the screen. These are the reference's own calls."""

    def test_narrative_anchor_scores_high(self):
        # "Thirteen years ago" is the spine of a whole episode - and an earlier
        # roundness formula, 10**(len(str(v))-2), made every two-digit number
        # "round" and scored this zero.
        self.assertGreater(ss.salience(13, "years", False, "thirteen years ago i gave up"), 0.6)

    def test_conversational_quantity_scores_zero(self):
        self.assertEqual(ss.salience(10, "minutes", False, "give me the next ten minutes"), 0.0)

    def test_oddly_specific_proof_point_maxes_out(self):
        self.assertGreaterEqual(ss.salience(12917, "dirhams", False, "dirhams in a month"), 0.95)

    def test_money_claim_survives_a_time_unit(self):
        # the unit is "month" but the subject is money
        self.assertGreater(
            ss.salience(40000, "month", True, "editors make fifteen thousand to forty thousand a month"),
            0.6)


class DetectionTests(unittest.TestCase):
    def kinds(self, sentence):
        return {o.kind for o in ss.detect(words(sentence))}

    def test_enumeration(self):
        self.assertIn("enumeration", self.kinds("Here are the five pillars you need to master."))
        self.assertIn("enumeration", self.kinds("there are two parts of your brain."))

    def test_contrast_needs_two_recurring_topics(self):
        # a real contrast: both terms recur through the script
        ws = words("Video editing and motion design are not the same thing. "
                   "A video editor cuts footage. A motion designer builds visuals. "
                   "The market pays video editing and motion design differently.")
        self.assertIn("contrast", {o.kind for o in ss.detect(ws)})

    def test_rhetorical_negation_is_not_a_contrast(self):
        # "Motion design is not difficult, but people have made it complex" is
        # a turn of phrase, not two entities worth two chips
        ws = words("Motion design is not difficult, but people on the internet "
                   "have just made it unnecessarily complex.")
        self.assertNotIn("contrast", {o.kind for o in ss.detect(ws)})

    def test_attribute_list_ignores_a_leading_ordinal(self):
        # "Second, SaaS and product motion." is a step, not a three-item series
        kinds = self.kinds("Second, SaaS and product motion.")
        self.assertIn("step", kinds)
        self.assertNotIn("attribute_list", kinds)
        self.assertIn("attribute_list", self.kinds("Contrast, hierarchy, and balance."))

    def test_definition(self):
        self.assertIn("definition", self.kinds("I call it the post mortem method."))

    def test_quiet_narration_yields_nothing(self):
        # restraint is a real output: roughly a third of the reference has no
        # graphic, and that is what makes the rest land
        self.assertEqual(self.kinds("But I wasn't proud of myself either."), set())
        self.assertEqual(self.kinds("I was waiting for my moment to feel ready."), set())


class PhraseSplittingTests(unittest.TestCase):
    def test_splits_on_punctuation_not_only_silence(self):
        """An already-edited video has no pauses left to split on.

        Grouping the 2267-word reference on silence alone gave 11 groups for the
        whole film, so every detector fired on the same paragraph and the quotes
        were unreadable.
        """
        ws = []
        t = 0.0
        for s in ("First, motion design for social media.",
                  "Second, SaaS and product motion.",
                  "Third, three d motion."):
            w = words(s, t0=t)
            ws += w
            t = w[-1]["end"] + 0.05          # no gap big enough to split on
        self.assertEqual(len(ss.phrases(ws)), 3)

    def test_still_splits_on_a_real_silence(self):
        ws = words("one two three", t0=0.0) + words("four five six", t0=9.0)
        self.assertEqual(len(ss.phrases(ws)), 2)


class CompositionTests(unittest.TestCase):
    def test_same_kind_overlaps_are_deduped_but_different_kinds_compose(self):
        """In the reference, the 15k-40k figure is drawn ON the two chips the
        same sentence triggers. Suppressing one for the other loses half the
        graphic."""
        ws = words("Video editors make fifteen thousand to forty thousand a month, "
                   "but motion designers working with brands earn far more, so "
                   "video editors and motion designers are not paid the same.")
        kinds = [o.kind for o in ss.detect(ws)]
        self.assertIn("figure", kinds)
        self.assertEqual(len(kinds), len(set(kinds)),
                         "no two opportunities of the same kind should overlap")


if __name__ == "__main__":
    unittest.main()
