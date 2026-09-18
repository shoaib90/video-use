"""The concat must stream-copy video but re-encode audio once, continuously.

Video stream-copy is Hard Rule 2: the concat adds no second video generation.

Audio is the opposite. Each segment is its own AAC stream, and AAC carries
encoder delay (priming samples at the head, padding at the tail). Stream-copying
the segments concatenates those artefacts into the timeline, putting a few ms of
silence and a discontinuity at every cut — an audible click that the 30ms fades
of Rule 3 cannot prevent, because the container creates it after the fades.

These tests pin the generated ffmpeg command so a future edit cannot quietly
restore a blanket `-c copy`.
"""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "helpers" / "render.py"
SPEC = importlib.util.spec_from_file_location("video_use_render", MODULE_PATH)
assert SPEC and SPEC.loader
render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render)


def _pairs(cmd: list[str]) -> list[tuple[str, str]]:
    """Adjacent (flag, value) pairs, for asserting on flag/value together."""
    return list(zip(cmd, cmd[1:]))


class ConcatCommandTests(unittest.TestCase):
    def _concat_cmd(self, n_segments: int = 3) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            edit_dir = Path(tmp)
            segments = [edit_dir / f"seg_{i}.mp4" for i in range(n_segments)]
            for s in segments:
                s.write_bytes(b"")
            result = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            with patch.object(render.subprocess, "run", return_value=result) as run:
                render.concat_segments(segments, edit_dir / "base.mp4", edit_dir)
            return list(run.call_args.args[0])

    def test_video_is_stream_copied(self):
        self.assertIn(("-c:v", "copy"), _pairs(self._concat_cmd()))

    def test_audio_is_reencoded_once_as_aac(self):
        pairs = _pairs(self._concat_cmd())
        self.assertIn(("-c:a", "aac"), pairs)
        self.assertIn(("-b:a", "192k"), pairs)
        self.assertIn(("-ar", "48000"), pairs)

    def test_channel_layout_is_forced_stereo(self):
        """A mono source among stereo ones breaks the concat's re-encode.

        Without an explicit -ac every segment inherits its source's channel
        count. One mono clip then gives one segment a different layout, and the
        concat demuxer decodes everything after it wrongly — while still
        producing a file of the correct duration, so it is easy to miss.
        """
        self.assertIn(("-ac", "2"), _pairs(self._concat_cmd()))

    def test_no_blanket_stream_copy(self):
        """A bare `-c copy` would stream-copy audio too and reintroduce the clicks."""
        cmd = self._concat_cmd()
        self.assertNotIn(("-c", "copy"), _pairs(cmd))
        self.assertNotIn("-c", cmd)

    def test_audio_is_not_stream_copied(self):
        self.assertNotIn(("-c:a", "copy"), _pairs(self._concat_cmd()))

    def test_still_uses_the_concat_demuxer(self):
        pairs = _pairs(self._concat_cmd())
        self.assertIn(("-f", "concat"), pairs)
        self.assertIn(("-safe", "0"), pairs)

    def test_concat_audio_settings_match_the_extract(self):
        """The concat re-encodes what the extract produced; the two must agree.

        If they drift (say the extract moves to 256k and the concat stays at
        192k) the finished audio silently changes bitrate at the concat step.
        """
        concat = _pairs(self._concat_cmd())
        for pair in _pairs(render.AAC_ARGS):
            if pair[0].startswith("-"):
                self.assertIn(pair, concat)

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src.mp4"
            src.write_bytes(b"")
            result = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            with patch.object(render, "is_hdr_source", return_value=False), \
                 patch.object(render, "is_portrait_source", return_value=False), \
                 patch.object(render, "probe_scaled_dims", return_value=(1920, 1080)), \
                 patch.object(render.subprocess, "run", return_value=result) as run:
                render.extract_segment(src, 0.0, 1.0, "", Path(tmp) / "out.mp4", rate="30")
            extract = _pairs(list(run.call_args.args[0]))

        for pair in _pairs(render.AAC_ARGS):
            if pair[0].startswith("-"):
                self.assertIn(pair, extract)


class SegmentDurationTests(unittest.TestCase):
    """Each segment's audio and video must be the same length.

    Video can only end on a frame boundary. If the requested duration is not a
    whole number of frames, the video is quantised and the audio is not, so the
    two differ by up to one frame period per segment. The concat butt-joins both
    streams, so that error ACCUMULATES — measured at 13 ms/segment, reaching
    0.6 s of audio-ahead-of-picture over a 46-segment cut.
    """

    def _extract_cmd(self, duration: float, rate: str = "30") -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src.mp4"
            src.write_bytes(b"")
            result = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            with patch.object(render, "is_hdr_source", return_value=False), \
                 patch.object(render, "is_portrait_source", return_value=False), \
                 patch.object(render, "probe_scaled_dims", return_value=(1920, 1080)), \
                 patch.object(render.subprocess, "run", return_value=result) as run:
                render.extract_segment(src, 0.0, duration, "", Path(tmp) / "out.mp4",
                                       rate=rate)
            return list(run.call_args.args[0])

    def _t_value(self, cmd: list[str]) -> float:
        return float(cmd[cmd.index("-t") + 1])

    def test_duration_is_snapped_to_whole_frames(self):
        for requested, fps in ((45.28, 30.0), (7.04, 30.0), (3.317, 30.0), (2.5, 24.0)):
            with self.subTest(requested=requested, fps=fps):
                t = self._t_value(self._extract_cmd(requested, str(int(fps))))
                frames = t * fps
                self.assertAlmostEqual(frames, round(frames), delta=0.01)

    def test_t_is_biased_below_the_frame_boundary(self):
        """Exactly n/fps rounds UP as a decimal string and yields n+1 frames."""
        t = self._t_value(self._extract_cmd(45.28))
        self.assertLess(t, 1358 / 30.0)
        self.assertGreater(t, 1358 / 30.0 - 1e-4)

    def test_audio_is_padded_so_it_cannot_fall_short(self):
        cmd = self._extract_cmd(45.28)
        self.assertIn("apad", cmd[cmd.index("-af") + 1])

    def test_fade_out_follows_the_snapped_duration(self):
        """The fade must sit on the segment's real end, not the requested one."""
        cmd = self._extract_cmd(45.28)
        af = cmd[cmd.index("-af") + 1]
        start = float(af.split("afade=t=out:st=")[1].split(":")[0])
        self.assertAlmostEqual(start, 1358 / 30.0 - 0.03, places=3)

    def test_rate_parsing(self):
        self.assertAlmostEqual(render._rate_to_float("30"), 30.0)
        self.assertAlmostEqual(render._rate_to_float("30000/1001"), 29.97, places=2)
        self.assertEqual(render._rate_to_float("garbage"), 0.0)
        self.assertEqual(render._rate_to_float("1/0"), 0.0)


if __name__ == "__main__":
    unittest.main()


class PerRangeAudioFilterTests(unittest.TestCase):
    """A range may override the EDL-level `audio_filter`.

    Noise is a property of where a clip was shot, not of the edit: a windy
    outdoor take and a take inside a moving car need different denoise
    strengths, and a single global setting has to compromise between them.
    """

    def _extract_calls(self, edl: dict) -> list:
        with tempfile.TemporaryDirectory() as tmp:
            edit_dir = Path(tmp)
            (edit_dir / "src.mp4").write_bytes(b"")
            with patch.object(render, "extract_segment") as ex, \
                 patch.object(render, "probe_source_fps", return_value="30"), \
                 patch.object(render, "resolve_grade_filter", return_value=""):
                render.extract_all_segments(edl, edit_dir, preview=True, fps="30")
            return ex.call_args_list

    def _edl(self, ranges: list) -> dict:
        return {"sources": {"s": "src.mp4"}, "ranges": ranges,
                "audio_filter": "GLOBAL"}

    def test_range_without_override_uses_the_global_filter(self):
        calls = self._extract_calls(self._edl([{"source": "s", "start": 0, "end": 1}]))
        self.assertEqual(calls[0].kwargs["audio_prefilter"], "GLOBAL")

    def test_range_override_wins(self):
        calls = self._extract_calls(self._edl(
            [{"source": "s", "start": 0, "end": 1, "audio_filter": "PERSEG"}]))
        self.assertEqual(calls[0].kwargs["audio_prefilter"], "PERSEG")

    def test_empty_string_override_disables_filtering_for_that_range(self):
        """Distinct from absent: "" means deliberately no filter, not 'inherit'."""
        calls = self._extract_calls(self._edl(
            [{"source": "s", "start": 0, "end": 1, "audio_filter": ""}]))
        self.assertEqual(calls[0].kwargs["audio_prefilter"], "")

    def test_mixed_ranges_each_get_their_own(self):
        calls = self._extract_calls(self._edl([
            {"source": "s", "start": 0, "end": 1},
            {"source": "s", "start": 1, "end": 2, "audio_filter": "DAM"},
            {"source": "s", "start": 2, "end": 3, "audio_filter": "CAR"},
        ]))
        self.assertEqual([c.kwargs["audio_prefilter"] for c in calls],
                         ["GLOBAL", "DAM", "CAR"])
