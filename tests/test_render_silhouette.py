"""Rim-lit silhouettes: anchoring, windows, and the filter wiring.

What these pin:
1. Windows anchor to spoken phrases (forward search, a cut phrase raises), never overlap, and are
   never shorter than their fades.
2. The silhouette needs a matte and refuses demotions (the matte describes the undemoted frame).
3. The matte is SPLIT only when both the behind-subject cut and the silhouette use it; an
   unconnected split output, or a stream used twice, is an ffmpeg error.
4. Generated layers run at the BASE's real frame rate, not the nominal fps argument.
"""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HELPERS = Path(__file__).parents[1] / "helpers"
spec = importlib.util.spec_from_file_location("video_use_render_sil", HELPERS / "render.py")
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)

SPOKEN = ("most people never notice this but there are people exactly like you out there "
          "thousands of them watching the same videos so the point is simple okay")


class _Edit:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "transcripts").mkdir()
        self.words = [{"type": "word", "text": t, "start": 0.6 + i * 0.32, "end": 0.9 + i * 0.32}
                      for i, t in enumerate(SPOKEN.split())]
        (self.dir / "transcripts" / "A.json").write_text(json.dumps({"words": self.words}))
        self.edl = {"ranges": [{"source": "A", "start": 0, "end": 24}], "sources": {"A": "a.mp4"}}

    def t(self, word):
        return next(w["start"] for w in self.words if w["text"] == word)


SIL = {"id": "you", "at": "people exactly like you", "crowd_at": "thousands of them",
       "out": {"word": "so the point"}}


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self.e = _Edit()

    def test_window_is_anchored_to_phrases(self):
        s = render.resolve_silhouettes([SIL], self.e.edl, self.e.dir, [24.0])[0]
        # "people" is said twice; the phrase is the SECOND one, just before "exactly"
        self.assertAlmostEqual(s["start"], self.e.t("exactly") - 0.32 - render.SIL_LEAD, places=2)
        self.assertAlmostEqual(s["end"], self.e.t("so"), places=2)
        self.assertAlmostEqual(s["crowd"], self.e.t("thousands") - render.SIL_LEAD, places=2)

    def test_default_hold_without_out(self):
        s = render.resolve_silhouettes([{"at": "people exactly like you"}], self.e.edl, self.e.dir, [24.0])[0]
        self.assertAlmostEqual(s["end"] - (s["start"] + render.SIL_LEAD), render.SIL_HOLD, places=2)
        self.assertIsNone(s["crowd"])

    def test_bad_windows_raise(self):
        CE = render.cards_mod.CardError
        with self.assertRaises(CE):
            render.resolve_silhouettes([{"at": "not spoken here"}], self.e.edl, self.e.dir, [24.0])
        with self.assertRaises(CE):
            render.resolve_silhouettes([{"at": "people", "hold": 0.5}], self.e.edl, self.e.dir, [24.0])
        with self.assertRaises(CE):
            render.resolve_silhouettes([{"at": "people", "hold": 6}, {"at": "out there"}],
                                       self.e.edl, self.e.dir, [24.0])


WIN = [{"id": "you", "start": 3.0, "end": 9.0, "crowd": 5.0, "fade": 0.45}]


class FilterTests(unittest.TestCase):
    def test_rim_is_built_from_the_matte_and_tinted_with_glow(self):
        parts, out = render.build_silhouette_filter(WIN, "[v]", "[9:v]", "#8B5CF6", 1920, 1080,
                                                    "24000/1001", 24.0)
        g = ";".join(parts)
        self.assertTrue(g.startswith("[9:v]scale=1920:1080"))
        self.assertIn("blend=all_mode=subtract", g)               # blur minus matte = outer halo
        self.assertIn("rr=0.545", g)                               # 0x8B / 255
        self.assertIn("r=24000/1001", g)
        self.assertIn("geq=lum='255*(", g)                         # one cheap alpha ramp
        self.assertIn("between(t,5.000,9.000)", g)                 # crowd window
        self.assertEqual(out, "[sl_out]")

    def test_no_crowd_means_no_crowd_chain(self):
        parts, _ = render.build_silhouette_filter([{**WIN[0], "crowd": None}], "[v]", "[9:v]",
                                                  "#8B5CF6", 1920, 1080, "30", 24.0)
        g = ";".join(parts)
        self.assertNotIn("sl_crowd", g)
        self.assertIn("split=2[sl_mf][sl_mg]", g)


class CompositeTests(unittest.TestCase):
    def _run(self, **kw):
        cmds = []
        with tempfile.TemporaryDirectory() as tmp:
            edit = Path(tmp)
            for f in ("base.mp4", "matte.mp4", "ov.mp4"):
                (edit / f).write_bytes(b"")
            with patch.object(render.subprocess, "run", side_effect=lambda c, **k: cmds.append(c)), \
                 patch.object(render.cards_mod, "_dims", return_value=(1920, 1080)), \
                 patch.object(render, "probe_duration", return_value=24.0), \
                 patch.object(render, "_video_start_time", return_value=0.0), \
                 patch.object(render, "_nominal_rate", return_value=30.0), \
                 patch.object(render, "_has_alpha", return_value=False), \
                 patch.object(render, "probe_source_fps", return_value="24000/1001"):
                render.build_final_composite(edit / "base.mp4", kw.pop("overlays", []), None,
                                             edit / "out.mp4", edit, **kw)
        return cmds[-1][cmds[-1].index("-filter_complex") + 1]

    def test_silhouette_needs_a_matte_and_refuses_demotions(self):
        with self.assertRaises(ValueError):
            self._run(silhouettes=WIN)
        with self.assertRaises(ValueError):
            self._run(silhouettes=WIN, matte=Path("/x/matte.mp4"),
                      demotions=[{"start": 1, "end": 2}])

    def test_matte_is_split_only_when_both_users_need_it(self):
        g = self._run(silhouettes=WIN, matte=Path("/x/matte.mp4"))
        self.assertNotIn("[mt_b][mt_s]", g)
        self.assertIn("[1:v]scale=1920:1080", g)
        ov = [{"file": "ov.mp4", "start_in_output": 1, "duration": 2, "behind_subject": True}]
        g = self._run(silhouettes=WIN, matte=Path("/x/matte.mp4"), overlays=ov)
        self.assertIn("split=2[mt_b][mt_s]", g)
        self.assertIn("[mt_b][b_subj]scale2ref", g)
        self.assertIn("[mt_s]scale=1920:1080", g)

    def test_generated_layers_use_the_base_rate_not_the_nominal_fps(self):
        g = self._run(silhouettes=WIN, matte=Path("/x/matte.mp4"), fps="30")
        self.assertIn("r=24000/1001", g)
        self.assertNotIn(":r=30:", g)


if __name__ == "__main__":
    unittest.main()
