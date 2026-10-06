"""Caption word selection: a word is captioned only if at least half of it is in the cut.

Deepgram spans touch or overlap, so a cut placed at the kept word's end can still
overlap the next word by a few hundred ms. Selecting on any overlap burned that
next word into the captions although none of it is heard.
"""
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "helpers" / "render.py"
SPEC = importlib.util.spec_from_file_location("video_use_render_capwords", MODULE_PATH)
assert SPEC and SPEC.loader
render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render)


def _tr(*spans):
    return {"words": [{"type": "word", "text": t, "start": a, "end": b} for t, a, b in spans]}


class CaptionWordSelectionTests(unittest.TestCase):
    def test_overlapping_next_word_is_not_captioned(self):
        tr = _tr(("kar", 1182.95, 1183.12), ("leta.", 1183.12, 1183.76), ("woh", 1183.40, 1184.04))
        got = [w["text"] for w in render._words_in_range(tr, 1180.0, 1183.755)]
        self.assertEqual(got, ["kar", "leta."])

    def test_kept_word_trimmed_by_a_few_ms_is_still_captioned(self):
        tr = _tr(("designer.", 2853.415, 2853.495))
        got = [w["text"] for w in render._words_in_range(tr, 2850.0, 2853.48)]
        self.assertEqual(got, ["designer."])

    def test_word_straddling_the_start_follows_its_majority(self):
        tr = _tr(("a", 9.0, 10.2), ("b", 9.9, 10.5))
        got = [w["text"] for w in render._words_in_range(tr, 10.0, 12.0)]
        self.assertEqual(got, ["b"])


if __name__ == "__main__":
    unittest.main()
