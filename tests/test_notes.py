"""notes.py: the server's boundaries, and the dump the agent reads. No browser, no network."""
import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "helpers"))
import notes  # noqa: E402


def note(**kw):
    return {"id": "a1", "t": 1.0, "kind": "cut", "text": "x", **kw}


class RangeTests(unittest.TestCase):
    def test_no_header_serves_everything(self):
        self.assertIsNone(notes.parse_range(None, 100))

    def test_open_ended(self):
        self.assertEqual(notes.parse_range("bytes=10-", 100), (10, 99))

    def test_bounded_and_clamped(self):
        self.assertEqual(notes.parse_range("bytes=10-20", 100), (10, 20))
        self.assertEqual(notes.parse_range("bytes=10-999", 100), (10, 99))

    def test_suffix(self):
        self.assertEqual(notes.parse_range("bytes=-10", 100), (90, 99))

    def test_unsatisfiable(self):
        for bad in ("bytes=100-", "bytes=20-10", "bytes=a-b", "bytes=-0"):
            with self.assertRaises(ValueError, msg=bad):
                notes.parse_range(bad, 100)


class CleanNotesTests(unittest.TestCase):
    def test_sorts_by_time_and_drops_unknown_fields(self):
        out = notes.clean_notes([note(id="b", t=5.0, junk=1), note(id="a", t=2.0)])
        self.assertEqual([n["id"] for n in out], ["a", "b"])
        self.assertNotIn("junk", out[1])

    def test_rejects_bad_input(self):
        for bad in ("x", [1], [note(t=-1)], [note(t=True)], [note(kind="other")],
                    [note(id="../../etc")], [note(pin=[2, 0])], [note(pin=[0])]):
            with self.assertRaises(ValueError, msg=repr(bad)):
                notes.clean_notes(bad)

    def test_a_pin_inside_the_frame_is_kept(self):
        self.assertEqual(notes.clean_notes([note(pin=[0.5, 0.25])])[0]["pin"], [0.5, 0.25])


class ServerTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.dir = Path(d.name)
        self.video = self.dir / "v.mp4"
        self.video.write_bytes(bytes(range(256)) * 40)
        self.nd = self.dir / "notes" / "v"
        self.nd.mkdir(parents=True)
        config = {"name": "v.mp4", "fps": 30.0, "cuts": []}
        handler = notes.make_handler(self.video, self.nd, config, [time.time()])
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def call(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        data = r.read()
        c.close()
        return r.status, data, dict(r.getheaders())

    def post_notes(self, payload, **h):
        headers = {"Content-Type": "application/json", **h}
        return self.call("POST", "/notes", json.dumps(payload), headers)

    def test_page_carries_the_config_without_a_cdn(self):
        status, body, _ = self.call("GET", "/")
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertIn('"name": "v.mp4"', text)
        self.assertNotIn("https://", text)

    def test_a_filename_cannot_break_out_of_the_script(self):
        config = {"name": "</script><img src=x onerror=alert(1)>", "fps": 30.0, "cuts": []}
        handler = notes.make_handler(self.video, self.nd, config, [time.time()])
        s = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        self.addCleanup(s.server_close)
        self.addCleanup(s.shutdown)
        c = http.client.HTTPConnection("127.0.0.1", s.server_address[1], timeout=5)
        c.request("GET", "/")
        text = c.getresponse().read().decode()
        c.close()
        self.assertNotIn("</script><img", text)

    def test_video_supports_ranges(self):
        status, body, headers = self.call("GET", "/video", headers={"Range": "bytes=100-199"})
        self.assertEqual(status, 206)
        self.assertEqual(len(body), 100)
        self.assertEqual(body[0], 100)
        self.assertEqual(headers["Content-Range"], f"bytes 100-199/{self.video.stat().st_size}")

    def test_bad_range_is_416(self):
        status, _, _ = self.call("GET", "/video", headers={"Range": "bytes=999999-"})
        self.assertEqual(status, 416)

    def test_notes_round_trip(self):
        self.assertEqual(self.call("GET", "/notes")[1], b"[]")
        self.assertEqual(self.post_notes([note()])[0], 200)
        self.assertEqual(json.loads(self.call("GET", "/notes")[1])[0]["kind"], "cut")
        self.assertEqual(json.loads((self.nd / "notes.json").read_text())[0]["text"], "x")

    def test_bad_notes_leave_the_file_alone(self):
        self.post_notes([note()])
        self.assertEqual(self.post_notes([note(t=-1)])[0], 400)
        self.assertEqual(json.loads((self.nd / "notes.json").read_text())[0]["t"], 1.0)

    def test_another_site_cannot_post(self):
        status, _, _ = self.post_notes([note()], Origin="https://evil.example")
        self.assertEqual(status, 403)
        self.assertFalse((self.nd / "notes.json").exists())

    def test_a_rebound_hostname_is_refused(self):
        self.assertEqual(self.call("GET", "/video", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.post_notes([note()], Host="evil.example")[0], 403)

    def test_a_cross_site_form_post_is_refused(self):
        # No preflight happens for text/plain, so the content type has to be enforced here.
        status, _, _ = self.call("POST", "/notes", json.dumps([note()]), {"Content-Type": "text/plain"})
        self.assertEqual(status, 415)

    def test_voice_saves_only_inside_its_folder(self):
        self.assertEqual(self.call("POST", "/voice/abc-1", b"a", {"Content-Type": "audio/webm"})[0], 200)
        self.assertTrue((self.nd / "voice" / "abc-1.webm").exists())
        self.assertEqual(self.call("POST", "/voice/..%2Fx", b"a", {"Content-Type": "audio/webm"})[0], 404)
        self.assertEqual(self.call("POST", "/voice/abc-2", b"a", {"Content-Type": "text/html"})[0], 415)

    def test_binds_loopback_only(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")


class DumpTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.edit = Path(d.name)
        self.video = self.edit / "preview.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=160x90:r=30:d=4",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(self.video)], check=True)
        (self.edit / "edl.json").write_text(json.dumps({"ranges": [
            {"source": "IMG_1", "start": 10.0, "end": 12.0, "beat": "open"},
            {"source": "IMG_2", "start": 50.0, "end": 52.0}]}))
        os.utime(self.edit / "edl.json", (self.video.stat().st_mtime - 60,) * 2)
        (self.edit / "transcripts").mkdir()
        (self.edit / "transcripts" / "IMG_2.json").write_text(json.dumps({"words": [
            {"type": "word", "text": "the", "start": 50.4, "end": 50.5},
            {"type": "spacing", "text": " ", "start": 50.5, "end": 50.6},
            {"type": "word", "text": "cricket", "start": 50.6, "end": 51.0},
            {"type": "word", "text": "later", "start": 90.0, "end": 90.2}]}))
        self.nd = self.edit / "notes" / "preview"
        self.nd.mkdir(parents=True)
        self.path = self.nd / "notes.json"

    def dump(self, items):
        self.path.write_text(json.dumps(items))
        return notes.dump(self.path, transcribe=False)

    def test_maps_a_note_to_source_and_words(self):
        out = self.dump([note(t=2.5, kind="wrong", text="wrong photo")])
        self.assertIn("**0:02.50** `wrong` (frame 75): wrong photo", out)
        self.assertIn('IMG_2 @ 50.50s: "the cricket"', out)
        self.assertNotIn("later", out)

    def test_includes_the_beat_and_the_pin(self):
        out = self.dump([note(t=0.5, pin=[0.62, 0.34])])
        self.assertIn("at 62% across 34% down", out)
        self.assertIn("IMG_1 @ 10.50s (open)", out)

    def test_an_edl_newer_than_the_video_gives_no_source_times(self):
        os.utime(self.edit / "edl.json", (self.video.stat().st_mtime + 60,) * 2)
        out = self.dump([note(t=2.5)])
        self.assertNotIn("IMG_2", out)
        self.assertIn("No source times", out)

    def test_time_order_and_voice_without_transcript(self):
        out = self.dump([note(id="b", t=3.0, text="", voice="v1"), note(id="a", t=1.0)])
        self.assertLess(out.index("0:01.00"), out.index("0:03.00"))
        self.assertIn("(voice note, not transcribed)", out)

    def test_a_transcript_already_made_is_not_redone(self):
        self.path.write_text(json.dumps([note(voice="v1", transcript="hold this beat")]))
        (self.nd / "voice").mkdir()
        (self.nd / "voice" / "v1.webm").write_bytes(b"x")
        from unittest.mock import patch
        with patch.object(notes, "transcribe_voice") as tv:
            out = notes.dump(self.path)
        tv.assert_not_called()
        self.assertIn("(spoken) hold this beat", out)


if __name__ == "__main__":
    unittest.main()
