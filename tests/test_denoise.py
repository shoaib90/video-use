"""Pins for the denoise helper's two silent-failure modes.

Both of these produce a plausible-looking result rather than an error, which is
the class of bug this repo keeps getting bitten by:

  * `probe` reading ffprobe output positionally. ffprobe does NOT honour the
    order of `-show_entries stream=channels,sample_rate` — it prints
    sample_rate first. Read positionally, a stereo clip reports 48000 channels
    and the helper starts denoising "channel 44".
  * a denoiser changing the sample count. Every caption offset and overlay
    position downstream is measured from segment lengths, so a source that
    comes back 8 ms short moves the whole cut after it, and the render still
    succeeds. (SpeechBrain's mtl-mimic does exactly this: 25.000s in,
    24.992s out.)
"""

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).parents[1] / "helpers" / "denoise.py"
SPEC = importlib.util.spec_from_file_location("video_use_denoise", MODULE_PATH)
assert SPEC and SPEC.loader
denoise = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(denoise)


def _completed(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")


class ProbeTests(unittest.TestCase):
    """ffprobe's field order is its own, not the one you asked for."""

    FFPROBE_REAL_ORDER = "sample_rate=48000\nchannels=2\nduration=354.750000\n"

    def _probe_with(self, audio_out: str, video_out: str = "video"):
        with patch.object(denoise, "run",
                          side_effect=[_completed(audio_out), _completed(video_out)]):
            return denoise.probe(Path("x.mov"))

    def test_channels_are_read_by_name_not_position(self):
        info = self._probe_with(self.FFPROBE_REAL_ORDER)
        self.assertEqual(info["channels"], 2)
        self.assertEqual(info["rate"], 48000)

    def test_order_does_not_matter(self):
        swapped = "channels=2\nduration=354.75\nsample_rate=48000\n"
        self.assertEqual(self._probe_with(swapped)["channels"], 2)

    def test_implausible_channel_count_is_rejected(self):
        """The failure mode this guards: channels=48000 looks like a valid int."""
        with self.assertRaises(SystemExit) as cm:
            self._probe_with("sample_rate=2\nchannels=48000\n")
        self.assertIn("48000", str(cm.exception))

    def test_missing_audio_stream_exits(self):
        with self.assertRaises(SystemExit):
            self._probe_with("")

    def test_video_presence_is_detected(self):
        self.assertTrue(self._probe_with(self.FFPROBE_REAL_ORDER, "video")["has_video"])
        self.assertFalse(self._probe_with(self.FFPROBE_REAL_ORDER, "")["has_video"])


class LengthGuardTests(unittest.TestCase):
    def test_equal_lengths_pass(self):
        with patch.object(denoise, "decode", side_effect=[[0] * 1000, [0] * 1000]):
            denoise.assert_same_length(Path("a.wav"), Path("b.wav"))

    def test_a_shortened_file_is_refused(self):
        with patch.object(denoise, "decode", side_effect=[[0] * 1000, [0] * 999]):
            with self.assertRaises(SystemExit) as cm:
                denoise.assert_same_length(Path("a.wav"), Path("b.wav"))
        self.assertIn("would shift every cut", str(cm.exception))

    def test_a_lengthened_file_is_refused(self):
        with patch.object(denoise, "decode", side_effect=[[0] * 1000, [0] * 1001]):
            with self.assertRaises(SystemExit):
                denoise.assert_same_length(Path("a.wav"), Path("b.wav"))


class MuxTests(unittest.TestCase):
    def _mux_cmd(self, channels: int, has_video: bool = True) -> list[str]:
        with patch.object(denoise, "probe", return_value={"has_video": has_video}), \
             patch.object(denoise, "run") as run:
            denoise.mux(Path("src.mov"), Path("a.wav"), Path("out.mov"), channels)
        return list(run.call_args.args[0])

    def test_video_is_stream_copied(self):
        cmd = self._mux_cmd(2)
        self.assertIn("-c:v", cmd)
        self.assertEqual(cmd[cmd.index("-c:v") + 1], "copy")

    def test_channel_count_follows_the_source(self):
        for n in (1, 2):
            with self.subTest(channels=n):
                cmd = self._mux_cmd(n)
                self.assertEqual(cmd[cmd.index("-ac") + 1], str(n))

    def test_audio_encode_matches_the_render_pipeline(self):
        """Drift here would change the audio again at the next stage."""
        cmd = self._mux_cmd(2)
        pairs = list(zip(cmd, cmd[1:]))
        for flag, value in zip(denoise.AAC_ARGS[::2], denoise.AAC_ARGS[1::2]):
            if flag != "-ac":            # -ac deliberately follows the source
                self.assertIn((flag, value), pairs)

    def test_audio_only_source_maps_no_video(self):
        cmd = self._mux_cmd(1, has_video=False)
        self.assertNotIn("-c:v", cmd)


class AmbienceTests(unittest.TestCase):
    """The blend is (clean + pct% of the high-passed residual), not (clean + pct% raw).

    84% of what the model strips off a windy take is below 300 Hz, so blending
    the raw signal back re-introduces the wind — measured at exactly the old
    arnndn floor, i.e. the entire benefit given away. The high-pass is the
    whole point of the feature and must not be optimised out.
    """

    def _graph(self, pct=15.0, hp=500) -> str:
        with patch.object(denoise, "run") as run:
            denoise.blend_ambience(Path("raw.wav"), Path("clean.wav"),
                                   Path("out.wav"), pct, hp)
        cmd = list(run.call_args.args[0])
        return cmd[cmd.index("-filter_complex") + 1]

    def test_residual_is_high_passed(self):
        self.assertIn("highpass=f=500", self._graph())
        self.assertIn("highpass=f=300", self._graph(hp=300))

    def test_residual_is_raw_minus_clean(self):
        g = self._graph()
        self.assertIn("volume=-1", g)          # invert the clean signal
        self.assertIn("normalize=0", g)        # amix must SUM, not average

    def test_blend_percentage_becomes_a_linear_gain(self):
        self.assertIn("volume=0.1500", self._graph(pct=15.0))
        self.assertIn("volume=0.0000", self._graph(pct=0.0))


if __name__ == "__main__":
    unittest.main()
