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


class SpanSegmentsTests(unittest.TestCase):
    """A camera switch inside a sentence splits it across two segments. Chunked per segment,
    each side becomes its own cue ("and I went to" / "the doctor."); with span_segments the
    sentence is chunked once across the switch (Episode 5, 2026-10-21)."""

    def _srt(self, style, ranges):
        import json
        import tempfile
        d = Path(tempfile.mkdtemp())
        (d / "transcripts").mkdir()
        words = [("And", 0.0, 0.2), ("then", 0.2, 0.4), ("I", 0.4, 0.5), ("went", 0.5, 0.8),
                 ("to", 0.8, 0.9), ("the", 0.9, 1.0), ("doctor.", 1.0, 1.5)]
        (d / "transcripts" / "A.json").write_text(json.dumps(_tr(*words)))
        edl = {"sources": {"A": "a.mp4"}, "ranges": ranges, "subtitle_style": style}
        render.build_master_srt(edl, d, d / "m.srt")
        blocks = (d / "m.srt").read_text().strip().split("\n\n")
        return [" ".join(b.split("\n")[2:]) for b in blocks]

    def test_default_chunks_each_segment_alone(self):
        style = {"words_per_chunk": 8, "break_on": ".!?", "case": "sentence"}
        cues = self._srt(style, [{"source": "A", "start": 0.0, "end": 0.9},
                                 {"source": "A", "start": 0.9, "end": 1.6}])
        self.assertEqual(cues, ["And then I went to", "the doctor."])

    def test_span_segments_keeps_the_sentence_in_one_cue(self):
        style = {"words_per_chunk": 8, "break_on": ".!?", "case": "sentence", "span_segments": True}
        cues = self._srt(style, [{"source": "A", "start": 0.0, "end": 0.9},
                                 {"source": "A", "start": 0.9, "end": 1.6}])
        self.assertEqual(cues, ["And then I went to the doctor."])

    def test_a_segment_without_transcript_still_breaks(self):
        style = {"words_per_chunk": 8, "break_on": ".!?", "case": "sentence", "span_segments": True}
        cues = self._srt(style, [{"source": "A", "start": 0.0, "end": 0.9},
                                 {"source": "CARD", "start": 0.0, "end": 1.0},
                                 {"source": "A", "start": 0.9, "end": 1.6}])
        self.assertEqual(len(cues), 2)


if __name__ == "__main__":
    unittest.main()
