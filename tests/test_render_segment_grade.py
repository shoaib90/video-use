"""A range's own `grade` overrides the EDL grade; ranges without the key inherit it.

Built for Episode 3, where a 2019 SDR to-camera clip sits inside an HLG shoot and
must play ungraded ("it should look like the past"): the shoot's grade string is
tuned to the tone-mapped HLG and would push the old clip's colours a second time.
"""
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "helpers" / "render.py"
SPEC = importlib.util.spec_from_file_location("video_use_render_segment_grade", MODULE_PATH)
assert SPEC and SPEC.loader
render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render)

EDL_GRADE = "eq=contrast=1.03:saturation=0.82"


class SegmentGradeTests(unittest.TestCase):
    def test_range_without_key_inherits_edl_grade(self):
        self.assertEqual(render.segment_grade({"source": "A"}, EDL_GRADE), EDL_GRADE)

    def test_none_preset_turns_grading_off(self):
        self.assertEqual(render.segment_grade({"grade": "none"}, EDL_GRADE), "")

    def test_null_and_empty_turn_grading_off(self):
        self.assertEqual(render.segment_grade({"grade": None}, EDL_GRADE), "")
        self.assertEqual(render.segment_grade({"grade": ""}, EDL_GRADE), "")

    def test_raw_filter_replaces_edl_grade(self):
        self.assertEqual(render.segment_grade({"grade": "eq=gamma=1.1"}, EDL_GRADE), "eq=gamma=1.1")

    def test_auto_passes_through_as_sentinel(self):
        self.assertEqual(render.segment_grade({"grade": "auto"}, EDL_GRADE), "__AUTO__")


if __name__ == "__main__":
    unittest.main()
