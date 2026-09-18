"""Overlays must be positioned by `-itsoffset`, and must never hold their last frame.

The bug these pin was invisible to every check the pipeline had. Overlays were
placed with `[i:v]setpts=PTS-STARTPTS+t/TB` and bounded with `enable`. That is
correct in isolation — it reproduces perfectly on a short clip, and on a
synthetic base of any length — but in a real 27-minute render with five
overlays chained, the overlay inputs drained ahead of the main timeline. The
4th overlay entered its window already 48 frames into its own footage, ran out
early, and `overlay`'s default `eof_action=repeat` then held its last frame for
the remaining 1.6 s.

These overlays are full-frame, so that reads as the picture freezing while the
audio keeps going. It hit 4 of the 5 overlays and scaled with position in the
chain: 0.43 s, 0.77 s, 1.67 s, 1.93 s of frozen tail.

Measured after the fix: overlay frame 0 lands at 1037.500 s for a 1037.513 s
cue (sub-frame), and `freezedetect` finds nothing.
"""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).parents[1] / "helpers" / "render.py"
SPEC = importlib.util.spec_from_file_location("video_use_render_ov", MODULE_PATH)
assert SPEC and SPEC.loader
render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render)


OVERLAYS = [
    {"file": "ov_title.mp4", "start_in_output": 36.567, "duration": 7.2},
    {"file": "ov_jam.mp4", "start_in_output": 507.367, "duration": 7.267},
    {"file": "ov_dam.mp4", "start_in_output": 1037.513, "duration": 12.0},
]


def _composite_cmd(overlays=OVERLAYS, subs=False) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        edit = Path(tmp)
        (edit / "base.mp4").write_bytes(b"")
        for ov in overlays:
            (edit / ov["file"]).write_bytes(b"")
        subs_path = None
        if subs:
            subs_path = edit / "master.srt"
            subs_path.write_text("")
        result = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with patch.object(render.subprocess, "run", return_value=result) as run:
            render.build_final_composite(edit / "base.mp4", overlays, subs_path,
                                         edit / "out.mp4", edit)
        return list(run.call_args.args[0])


def _graph(cmd: list[str]) -> str:
    return cmd[cmd.index("-filter_complex") + 1]


class InputOffsetTests(unittest.TestCase):
    def test_each_overlay_input_carries_its_own_itsoffset(self):
        cmd = _composite_cmd()
        offsets = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-itsoffset"]
        self.assertEqual(offsets, ["36.567", "507.367", "1037.513"])

    def test_itsoffset_precedes_the_input_it_applies_to(self):
        """`-itsoffset` after `-i` would silently apply to the NEXT input."""
        cmd = _composite_cmd()
        for i, a in enumerate(cmd):
            if a == "-itsoffset":
                self.assertEqual(cmd[i + 2], "-i", "itsoffset must sit right before its -i")

    def test_the_base_is_not_offset(self):
        cmd = _composite_cmd()
        self.assertLess(cmd.index("-i"), cmd.index("-itsoffset"),
                        "the base must be the first input and carry no offset")

    def test_setpts_is_not_used_to_place_overlays(self):
        """The formulation that caused the drift. It must not come back."""
        self.assertNotIn("setpts", _graph(_composite_cmd()))


class FreezeGuardTests(unittest.TestCase):
    def test_overlays_do_not_repeat_their_last_frame(self):
        graph = _graph(_composite_cmd())
        self.assertEqual(graph.count("repeatlast=0"), len(OVERLAYS))

    def test_overlays_pass_the_main_through_at_eof(self):
        graph = _graph(_composite_cmd())
        self.assertEqual(graph.count("eof_action=pass"), len(OVERLAYS))

    def test_default_eof_action_is_never_relied_on(self):
        """`overlay`'s default is `repeat`, which is exactly the freeze."""
        self.assertNotIn("eof_action=repeat", _graph(_composite_cmd()))


class WindowTests(unittest.TestCase):
    def test_enable_still_bounds_each_overlay(self):
        """An overlay FILE may be longer than the EDL asks for.

        ov_jam was 7.50 s on disk against a declared 7.267 s, so dropping
        `enable` in favour of the file's own length would run it 0.23 s long.
        """
        graph = _graph(_composite_cmd())
        self.assertIn("enable='between(t,36.567,43.767)'", graph)
        self.assertIn("enable='between(t,507.367,514.634)'", graph)
        self.assertIn("enable='between(t,1037.513,1049.513)'", graph)

    def test_overlays_are_chained_in_order(self):
        graph = _graph(_composite_cmd())
        self.assertIn("[0:v][1:v]overlay=", graph)
        self.assertIn("[v1][2:v]overlay=", graph)
        self.assertIn("[v2][3:v]overlay=", graph)

    def test_subtitles_are_applied_after_every_overlay(self):
        """Hard Rule 1 — otherwise overlays cover the captions."""
        graph = _graph(_composite_cmd(subs=True))
        self.assertLess(graph.rindex("overlay="), graph.index("subtitles="))


if __name__ == "__main__":
    unittest.main()
