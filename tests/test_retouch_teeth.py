"""Pins for retouch_teeth's two silent-failure modes and its opt-in scope.

The colour handling is the interesting one. Piping frames out to a Python stage
and back is the obvious way to do per-frame work, and two separate details of it
quietly destroy the picture while producing a file that plays correctly:

  * yuv420p -> bgr24 -> yuv420p is not idempotent. Measured 34 dB PSNR against
    the segment's own source, where a plain re-encode of the same file scores
    55 dB — every pixel altered in order to retouch a few hundred.
  * rawvideo carries no colour metadata, so ffmpeg assumes full range on the way
    back in and inserts a full->limited conversion. 33.8 dB untagged, 52.4 dB
    tagged. One flag between "visually lossless" and "all of it shifted".

Neither shows up as an error, a duration change, or a dimension change.
"""

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "helpers" / "retouch_teeth.py"
SPEC = importlib.util.spec_from_file_location("video_use_retouch", MODULE_PATH)
assert SPEC and SPEC.loader
retouch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(retouch)

WORKER = retouch.WORKER


class ColourPipelineTests(unittest.TestCase):
    def test_frames_never_leave_yuv(self):
        """bgr24 rawvideo I/O is the 20 dB mistake. Detection may convert a copy."""
        self.assertIn('"-pix_fmt","yuv420p","-"', WORKER.replace(" ", ""))
        self.assertNotIn('"-f","rawvideo","-pix_fmt","bgr24"', WORKER.replace(" ", ""))

    def test_rawvideo_input_is_tagged_with_range_and_matrix(self):
        flat = WORKER.replace(" ", "").replace("\n", "")
        self.assertIn('"-color_range","tv","-colorspace","bt709"', flat)

    def test_output_carries_the_colour_tags_too(self):
        flat = WORKER.replace(" ", "").replace("\n", "")
        self.assertIn('"-color_primaries","bt709"', flat)
        self.assertIn('"-color_trc","bt709"', flat)

    def test_input_tagging_precedes_the_input(self):
        """Tags after `-i -` would apply to the wrong stream."""
        flat = WORKER.replace(" ", "").replace("\n", "")
        enc = flat.split('enc=subprocess.Popen')[1]
        self.assertLess(enc.index('"-color_range","tv"'), enc.index('"-i","-"'))

    def test_audio_is_copied_not_re_encoded(self):
        self.assertIn('"-c:a","copy"', WORKER.replace(" ", ""))


class ScopeTests(unittest.TestCase):
    """The effect is opt-in per window and per face, never blanket."""

    def _args(self, argv):
        import sys
        from unittest.mock import patch
        with patch.object(sys, "argv", ["retouch_teeth.py", *argv]):
            ap = None
            try:
                retouch.main()
            except SystemExit as e:
                return e
        return ap

    def test_window_is_required(self):
        e = self._args(["seg.mp4", "-o", "out.mp4"])
        self.assertIsInstance(e, SystemExit)

    def test_an_empty_window_is_rejected(self):
        e = self._args(["missing.mp4", "-o", "out.mp4", "--window", "5", "5"])
        self.assertIsInstance(e, SystemExit)

    def test_face_defaults_to_a_single_explicit_choice(self):
        """Only one face is ever treated; everyone else in frame is untouched."""
        self.assertIn('cands[-1] if face == "right" else cands[0]', WORKER)
        self.assertNotIn("for fl in res.multi_face_landmarks:\n        apply", WORKER)


class MaskTests(unittest.TestCase):
    def test_inner_lip_ring_is_the_mouth_opening(self):
        self.assertEqual(len(retouch.INNER_LIP), 20)
        self.assertEqual(retouch.INNER_LIP[0], 78)

    def test_enamel_selection_includes_yellow_pixels(self):
        """A plain low-saturation cut selects the teeth that are ALREADY white.

        Measured on a real smile: 656 bright pixels failed an S<90 test and
        averaged saturation 99 at hue 23 — the yellow enamel itself. Excluding
        them is why the first pass looked like nothing had changed.
        """
        flat = WORKER.replace(" ", "")
        self.assertIn("(Hue>=8)&(Hue<=45)", flat)  # yellow band kept
        self.assertIn("(S<115)", flat)             # at moderate saturation
        self.assertIn("(S<70)", flat)              # plus near-neutral enamel
        self.assertNotIn("(S<90)", flat)           # the rule that dropped them

    def test_hue_does_not_shadow_the_frame_height(self):
        """`H` is the frame height in this worker; reusing it for hue is a trap."""
        self.assertNotIn("H = hsv[:,:,0]", WORKER)
        self.assertIn("Hue = hsv[:,:,0]", WORKER)

    def test_mask_is_feathered(self):
        """A hard-edged mask shows as a rectangle around the teeth."""
        self.assertIn("GaussianBlur", WORKER)

    def test_strength_ramps_at_the_window_edges(self):
        """Strength rises and falls over RAMP seconds so the effect never pops on."""
        flat = WORKER.replace(" ", "")
        self.assertIn("RAMP,HOLD=0.25,3", flat)
        self.assertIn("max(0.0,min(1.0,(t-t0)/RAMP,(t1-t)/RAMP))", flat)

    def test_brief_detection_dropouts_are_held_not_dropped(self):
        """Without this a lost frame pops the effect off for one frame."""
        self.assertIn("age < HOLD", WORKER)


class IntegrityTests(unittest.TestCase):
    def test_frame_count_is_verified_after_processing(self):
        src = MODULE_PATH.read_text()
        self.assertIn("frame count changed", src)
        self.assertIn("unlink(missing_ok=True)", src)

    def test_default_crf_is_below_a_typical_segment_crf(self):
        """The segments are CRF 16; re-encoding at 16 would compound the loss."""
        import argparse
        from unittest.mock import patch
        captured = {}
        real_add = argparse.ArgumentParser.add_argument

        def spy(self, *a, **kw):
            if a and a[0] == "--crf":
                captured["crf"] = kw.get("default")
            return real_add(self, *a, **kw)

        with patch.object(argparse.ArgumentParser, "add_argument", spy), \
             patch.object(retouch.sys, "argv", ["retouch_teeth.py"]):
            try:
                retouch.main()
            except SystemExit:
                pass
        self.assertIn("crf", captured)
        self.assertLess(int(captured["crf"]), 16)


if __name__ == "__main__":
    unittest.main()
