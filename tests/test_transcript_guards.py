"""Same-stem refusal, the source stamp, and Deepgram keyterms. No network, no paid calls."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "helpers"))
import timeline_view  # noqa: E402
import transcribe  # noqa: E402
import transcribe_batch  # noqa: E402
import transcribe_deepgram as dg  # noqa: E402


class SameStemTests(unittest.TestCase):
    def videos(self, *names):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        for n in names:
            (Path(d.name) / n).write_bytes(b"x")
        return Path(d.name)

    def test_refuses_two_extensions_of_one_stem(self):
        with self.assertRaises(SystemExit) as e:
            transcribe_batch.find_videos(self.videos("intro.mp4", "intro.MOV", "other.mp4"))
        self.assertIn("intro.MOV + intro.mp4", str(e.exception))

    def test_refuses_stems_differing_only_by_case(self):
        with self.assertRaises(SystemExit):
            transcribe_batch.find_videos(self.videos("Intro.mp4", "intro.mov"))

    def test_cinematic_pairs_are_distinct_stems(self):
        self.assertEqual(len(transcribe_batch.find_videos(self.videos("IMG_1.MOV", "IMG_E1.MOV"))), 2)


class SourceStampTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.dir = Path(d.name)
        self.video = self.dir / "a.MOV"
        self.video.write_bytes(b"12345")
        self.out = self.dir / "a.json"

    def warned(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = transcribe.warn_if_source_changed(self.out, self.video)
        return result, err.getvalue()

    def test_unchanged_source_is_silent(self):
        self.out.write_text(json.dumps({"words": [], **transcribe.source_stamp(self.video)}))
        self.assertEqual(self.warned(), (False, ""))

    def test_transcript_from_before_the_stamp_is_silent(self):
        self.out.write_text(json.dumps({"words": []}))
        self.assertEqual(self.warned(), (False, ""))

    def test_a_different_size_warns(self):
        self.out.write_text(json.dumps({"words": [], **transcribe.source_stamp(self.video)}))
        self.video.write_bytes(b"123456789")
        changed, msg = self.warned()
        self.assertTrue(changed)
        self.assertIn("WARNING", msg)

    def test_a_cached_transcript_never_calls_the_paid_api(self):
        (self.dir / "transcripts").mkdir()
        (self.dir / "transcripts" / "a.json").write_text(json.dumps({"words": []}))
        with patch.object(transcribe, "call_scribe") as paid, contextlib.redirect_stdout(io.StringIO()):
            transcribe.transcribe_one(self.video, self.dir, "key")
        paid.assert_not_called()


class KeytermTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.dir = Path(d.name)

    def write(self, text):
        p = self.dir / "keyterms.txt"
        p.write_text(text)
        return p

    def test_file_format(self):
        p = self.write("# people\nShoaib\n\nUnfinished with Shoaib\nShoaib\n")
        self.assertEqual(dg.load_keyterms(p), ["Shoaib", "Unfinished with Shoaib"])

    def test_over_the_limit_is_refused(self):
        with self.assertRaises(RuntimeError):
            dg.load_keyterms(self.write("\n".join(f"t{i}" for i in range(dg.MAX_KEYTERMS + 1))))

    def test_each_term_is_its_own_query_parameter(self):
        # Deepgram docs: commas silently become ONE literal term.
        import requests
        audio = self.dir / "a.wav"
        audio.write_bytes(b"x")
        with patch.object(dg.requests, "post") as post:
            post.return_value.status_code = 200
            dg.call_deepgram(audio, "k", language="multi", keyterms=["Shoaib", "Unfinished with Shoaib"])
        params = post.call_args.kwargs["params"]
        url = requests.Request("POST", dg.DEEPGRAM_URL, params=params).prepare().url
        self.assertIn("keyterm=Shoaib&keyterm=Unfinished+with+Shoaib", url)
        self.assertIn("language=multi", url)

    def test_no_keyterms_leaves_the_request_unchanged(self):
        audio = self.dir / "a.wav"
        audio.write_bytes(b"x")
        with patch.object(dg.requests, "post") as post:
            post.return_value.status_code = 200
            dg.call_deepgram(audio, "k", language="multi")
        self.assertNotIn("keyterm", post.call_args.kwargs["params"])

    def cached(self, stored, requested):
        p = self.dir / "t.json"
        p.write_text(json.dumps({"_provider": dg.PROVIDER, "_model": "nova-3", "_language": "multi",
                                 "_spacing_threshold": 0.05, **stored}))
        with contextlib.redirect_stdout(io.StringIO()):
            return dg.check_cached(p, "nova-3", 0.05, "multi", False, False, requested)

    def test_old_transcript_without_keyterms_stays_valid(self):
        self.assertTrue(self.cached({}, None))

    def test_requesting_new_keyterms_refuses_the_cache(self):
        with self.assertRaises(RuntimeError):
            self.cached({}, ["Shoaib"])

    def test_same_keyterms_in_any_order_reuse(self):
        self.assertTrue(self.cached({"_keyterms": ["a", "b"]}, ["b", "a"]))


class TimelineEndTests(unittest.TestCase):
    def test_a_range_ending_at_the_clip_end_gives_every_frame(self):
        with tempfile.TemporaryDirectory() as d:
            clip = Path(d) / "c.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=160x90:r=30:d=2",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)], check=True)
            frames = timeline_view.extract_frames(clip, 1.0, 2.0, 4, Path(d) / "f")
            self.assertTrue(all(f.exists() for f in frames))


if __name__ == "__main__":
    unittest.main()
