"""A page for leaving notes on exact frames of a cut, and a dump of them for the agent.

Feedback used to arrive as "the bit about halfway through". This serves a local page: scrub
the cut, press N, say what is wrong. Every note saves the moment it is made. `--dump` reads
them back in time order, each with the source file, source time and the words spoken there,
which is what turning a note into an EDL change actually needs. Nothing is applied
automatically: a note is an opinion, and acting on it is a decision.

Local only. It binds 127.0.0.1, serves one video, and writes only inside its notes folder.
A server rather than a file:// page because saving then needs no folder picker and works in
any browser, and `localhost` is a secure context, so the microphone works too.

Usage:
    python helpers/notes.py <edit>/preview_v3.mp4
    python helpers/notes.py <edit>/preview_v3.mp4 --port 8765
    python helpers/notes.py --dump <edit>/notes/preview_v3/notes.json

Notes land in <edit>/notes/<video stem>/: notes.json, voice/, and notes.md after a dump.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from render import _rate_to_float, probe_source_fps, resolve_path

PAGE = Path(__file__).resolve().parent / "notes.html"
HINGLISH_MODEL = Path.home() / ".cache" / "whisper-models" / "ggml-small.bin"
KINDS = {"cut", "shorten", "lengthen", "wrong", "note"}
MAX_NOTES_BYTES = 5 * 1024 * 1024
MAX_VOICE_BYTES = 100 * 1024 * 1024
VOICE_ID = re.compile(r"^[a-z0-9-]{1,40}$")
VOICE_TYPES = {"audio/webm": ".webm", "audio/mp4": ".m4a", "audio/ogg": ".ogg"}


def find_edit_dir(video: Path) -> Path:
    """The folder holding edl.json: the video's own, else <video folder>/edit."""
    if (video.parent / "edl.json").exists():
        return video.parent
    return video.parent / "edit"


def notes_dir_for(video: Path, edit_dir: Path) -> Path:
    return edit_dir / "notes" / video.stem


def parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    """(first, last) byte of a `Range` header. None means serve it all; raises if unsatisfiable."""
    if not header or not header.startswith("bytes="):
        return None
    first, _, last = header[6:].split(",")[0].strip().partition("-")
    if first == "":
        if not last.isdigit() or int(last) == 0:
            raise ValueError(header)
        return max(0, size - int(last)), size - 1
    if not first.isdigit() or (last and not last.isdigit()):
        raise ValueError(header)
    a, b = int(first), int(last) if last else size - 1
    if a >= size or b < a:
        raise ValueError(header)
    return a, min(b, size - 1)


def clean_notes(raw: object) -> list[dict]:
    """Validate what the page posts. Raises ValueError rather than saving something odd."""
    if not isinstance(raw, list):
        raise ValueError("notes must be a list")
    out = []
    for n in raw:
        if not isinstance(n, dict):
            raise ValueError("a note must be an object")
        t = n.get("t")
        if not isinstance(t, (int, float)) or isinstance(t, bool) or t < 0:
            raise ValueError(f"bad time {t!r}")
        if n.get("kind") not in KINDS:
            raise ValueError(f"bad kind {n.get('kind')!r}")
        if not VOICE_ID.match(str(n.get("id", ""))):
            raise ValueError(f"bad id {n.get('id')!r}")
        pin = n.get("pin")
        if pin is not None and not (isinstance(pin, list) and len(pin) == 2
                                    and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in pin)):
            raise ValueError(f"bad pin {pin!r}")
        out.append({k: n[k] for k in ("id", "t", "kind", "text", "pin", "voice", "transcript") if k in n})
    return sorted(out, key=lambda n: n["t"])


def write_atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def load_cuts(edit_dir: Path, video: Path, fps: float) -> list[float]:
    """Output times of the cuts, for the ticks on the scrubber. Only if the EDL is this video's."""
    return [s["out_start"] for s in timeline_map(edit_dir, video, fps)[1:]]


def timeline_map(edit_dir: Path, video: Path, fps: float) -> list[dict]:
    """Output-time segments of the EDL. Empty when there is none, or it is newer than the video:
    a source time from an EDL that has moved on would send a fix to the wrong place."""
    edl_path = edit_dir / "edl.json"
    if not edl_path.exists() or edl_path.stat().st_mtime > video.stat().st_mtime or fps <= 0:
        return []
    out, t = [], 0.0
    for r in json.loads(edl_path.read_text()).get("ranges") or []:
        dur = max(1, round((float(r["end"]) - float(r["start"])) * fps)) / fps
        out.append({"out_start": round(t, 3), "out_end": round(t + dur, 3), "source": r["source"],
                    "start": float(r["start"]), "beat": r.get("beat") or ""})
        t += dur
    return out


def make_handler(video: Path, notes_dir: Path, config: dict, touched: list[float]):
    voice_dir = notes_dir / "voice"
    notes_path = notes_dir / "notes.json"

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            pass

        def _send(self, code: int, body: bytes = b"", ctype: str = "text/plain; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _local_host(self) -> bool:
            # Refuses DNS rebinding: a page on another site reaching this port by a name it controls.
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            return host in ("127.0.0.1", "localhost", "[::1]")

        def _same_origin(self) -> bool:
            # Refuses a page on another site posting into the notes file.
            origin = self.headers.get("Origin")
            return origin is None or origin.split("//", 1)[-1] == self.headers.get("Host")

        def _send_file(self, path: Path, ctype: str) -> None:
            size = path.stat().st_size
            try:
                span = parse_range(self.headers.get("Range"), size)
            except ValueError:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            first, last = span or (0, size - 1)
            self.send_response(206 if span else 200)
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(last - first + 1))
            if span:
                self.send_header("Content-Range", f"bytes {first}-{last}/{size}")
            self.end_headers()
            with open(path, "rb") as f:
                f.seek(first)
                left = last - first + 1
                try:
                    while left > 0:
                        chunk = f.read(min(1024 * 1024, left))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        left -= len(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    self.close_connection = True  # the browser seeks by dropping the request

        def do_GET(self):
            touched[0] = time.time()
            if not self._local_host():
                return self._send(403, b"local only")
            path = self.path.split("?", 1)[0]
            if path == "/":
                page = PAGE.read_text().replace("/*__CONFIG__*/null", json.dumps(config).replace("<", "\\u003c"))
                return self._send(200, page.encode(), "text/html; charset=utf-8")
            if path == "/video":
                return self._send_file(video, "video/mp4")
            if path == "/notes":
                body = notes_path.read_bytes() if notes_path.exists() else b"[]"
                return self._send(200, body, "application/json")
            m = re.fullmatch(r"/voice/([a-z0-9-]{1,40})", path)
            if m:
                found = next(iter(voice_dir.glob(m.group(1) + ".*")), None)
                if found:
                    return self._send_file(found, "audio/webm")
            return self._send(404, b"not found")

        def do_POST(self):
            touched[0] = time.time()
            if not self._local_host() or not self._same_origin():
                return self._send(403, b"local only")
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                return self._send(411, b"length required")
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
            path = self.path.split("?", 1)[0]
            if path == "/notes":
                if ctype != "application/json":
                    return self._send(415, b"json only")
                if length > MAX_NOTES_BYTES:
                    return self._send(413, b"too large")
                try:
                    notes = clean_notes(json.loads(self.rfile.read(length)))
                except (ValueError, json.JSONDecodeError) as e:
                    return self._send(400, str(e).encode())
                write_atomic(notes_path, json.dumps(notes, indent=1, ensure_ascii=False))
                return self._send(200, b"saved")
            m = re.fullmatch(r"/voice/([a-z0-9-]{1,40})", path)
            if m:
                if ctype not in VOICE_TYPES:
                    return self._send(415, b"audio only")
                if length > MAX_VOICE_BYTES:
                    return self._send(413, b"too large")
                voice_dir.mkdir(parents=True, exist_ok=True)
                (voice_dir / (m.group(1) + VOICE_TYPES[ctype])).write_bytes(self.rfile.read(length))
                return self._send(200, b"saved")
            self._send(404, b"not found")

    return Handler


def serve(video: Path, edit_dir: Path, port: int, idle_exit_min: float) -> None:
    notes_dir = notes_dir_for(video, edit_dir)
    notes_dir.mkdir(parents=True, exist_ok=True)
    fps = _rate_to_float(probe_source_fps(video) or "30") or 30.0
    config = {"name": video.name, "fps": fps, "cuts": load_cuts(edit_dir, video, fps)}
    touched = [time.time()]
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(video, notes_dir, config, touched))
    server.daemon_threads = True

    def watch_idle() -> None:
        while time.time() - touched[0] < idle_exit_min * 60:
            time.sleep(5)
        print("idle, stopping")
        server.shutdown()

    threading.Thread(target=watch_idle, daemon=True).start()
    print(f"notes page: http://127.0.0.1:{server.server_address[1]}/", flush=True)
    print(f"notes file: {notes_dir / 'notes.json'}", flush=True)
    server.serve_forever()


# -------- Dump ---------------------------------------------------------------


def fmt_time(t: float) -> str:
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:05.2f}"


def transcribe_voice(path: Path) -> str:
    """Whisper, free and local. `-l en` renders Hindi into English, which suits a note."""
    from transcribe_whisper import DEFAULT_MODEL, call_whisper

    model = HINGLISH_MODEL if HINGLISH_MODEL.exists() else DEFAULT_MODEL
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "voice.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-ac", "1", "-ar", "16000", str(wav)],
                       check=True)
        # The raw tokens carry their own spaces; word-joining them splits names ("Rog an").
        return "".join(seg.get("text", "") for seg in call_whisper(wav, model, "en", None)["transcription"]).strip()


def words_near(edit_dir: Path, source: str, t: float, span: float = 1.5) -> str:
    p = edit_dir / "transcripts" / f"{source}.json"
    if not p.exists():
        return ""
    words = json.loads(p.read_text()).get("words") or []
    return " ".join(w["text"] for w in words
                    if w.get("type", "word") == "word" and w.get("start") is not None
                    and t - span <= w["start"] <= t + span)


def dump(notes_path: Path, video: Path | None = None, transcribe: bool = True) -> str:
    notes_dir = notes_path.parent
    edit_dir = notes_dir.parent.parent
    notes = json.loads(notes_path.read_text())
    if video is None:
        found = [p for p in (edit_dir / f"{notes_dir.name}{ext}" for ext in (".mp4", ".mov")) if p.exists()]
        video = found[0] if found else None
    fps = (_rate_to_float(probe_source_fps(video) or "30") or 30.0) if video else 30.0
    segments = timeline_map(edit_dir, video, fps) if video else []

    if transcribe:
        changed = False
        for n in notes:
            if not n.get("voice") or n.get("transcript"):
                continue
            found = next(iter((notes_dir / "voice").glob(n["voice"] + ".*")), None)
            if found is None:
                continue
            try:
                n["transcript"] = transcribe_voice(found)
                changed = True
            except (RuntimeError, subprocess.CalledProcessError, SystemExit) as e:
                print(f"warning: could not transcribe {found.name}: {e}", file=sys.stderr)
        if changed:
            write_atomic(notes_path, json.dumps(notes, indent=1, ensure_ascii=False))

    lines = [f"# Notes on {notes_dir.name} ({len(notes)})\n"]
    if video and not segments:
        lines.append("_No source times: there is no EDL, or it has changed since this video was rendered._\n")
    for n in sorted(notes, key=lambda x: x["t"]):
        text = n.get("text") or ""
        spoken = n.get("transcript")
        if spoken:
            text = f"{text} (spoken) {spoken}".strip()
        elif n.get("voice") and not text:
            text = "(voice note, not transcribed)"
        pin = f", at {n['pin'][0]:.0%} across {n['pin'][1]:.0%} down" if n.get("pin") else ""
        lines.append(f"- **{fmt_time(n['t'])}** `{n['kind']}` (frame {round(n['t'] * fps)}{pin}): {text}")
        seg = next((s for s in segments if s["out_start"] <= n["t"] < s["out_end"]), None)
        if seg:
            src_t = seg["start"] + n["t"] - seg["out_start"]
            said = words_near(edit_dir, seg["source"], src_t)
            lines.append(f"  - {seg['source']} @ {src_t:.2f}s" + (f" ({seg['beat']})" if seg["beat"] else "")
                         + (f': "{said}"' if said else ""))
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Timecoded notes on a cut")
    ap.add_argument("video", type=Path, nargs="?", help="Render to review")
    ap.add_argument("--edit-dir", type=Path, default=None, help="Default: the folder holding edl.json")
    ap.add_argument("--port", type=int, default=0, help="Default: any free port")
    ap.add_argument("--idle-exit-min", type=float, default=240,
                    help="Stop after this many idle minutes. Default 240.")
    ap.add_argument("--dump", type=Path, default=None, help="Print a notes.json as markdown, and save notes.md")
    ap.add_argument("--no-transcribe", action="store_true", help="With --dump: leave voice notes untranscribed")
    args = ap.parse_args()

    if args.dump:
        path = args.dump.resolve()
        if not path.exists():
            sys.exit(f"notes not found: {path}")
        text = dump(path, args.video.resolve() if args.video else None, transcribe=not args.no_transcribe)
        (path.parent / "notes.md").write_text(text)
        print(text)
        return

    if args.video is None:
        ap.error("video is required unless --dump is used")
    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")
    edit_dir = (args.edit_dir.resolve() if args.edit_dir else find_edit_dir(video))
    serve(video, edit_dir, args.port, args.idle_exit_min)


if __name__ == "__main__":
    main()
