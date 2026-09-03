"""Transcribe a video locally with whisper.cpp — free, offline, no API key.

Emits the SAME on-disk schema as `transcribe.py` and `transcribe_deepgram.py`,
so everything downstream consumes it unchanged. See kb/data-contract.md.

Use this for iteration and drafts (it costs nothing), and for offline work.
Trade-offs vs the paid providers:

  + free, offline, unlimited re-runs
  + preserves leading filler words that Deepgram has been seen to drop
  - NO speaker diarization. Every token comes back unlabelled, so
    `takes_packed.md` has no S0/S1 tags. Bad for multi-speaker material.
  - normalizes some spoken numbers ("ninety percent" -> "90%"), which is in
    tension with Hard Rule 8. Fine for cut-finding, worth a second look before
    burning captions from it.
  - no audio-event tags.

Requires `whisper-cli` (brew install whisper-cpp — arrives with ffmpeg-full) and a
GGML model. Default model path: ~/.cache/whisper-models/ggml-small.en.bin
Download: https://huggingface.co/ggerganov/whisper.cpp

Usage:
    python helpers/transcribe_whisper.py <video>
    python helpers/transcribe_whisper.py <video> --model ~/.cache/whisper-models/ggml-small.en.bin
    python helpers/transcribe_whisper.py --convert <whisper_out.json>
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transcribe import (  # noqa: E402
    count_audio_tracks,
    extract_audio,
    peak_dbfs,
    transcript_path,
)

DEFAULT_MODEL = Path.home() / ".cache" / "whisper-models" / "ggml-small.en.bin"

# Tokens that whisper emits as standalone segments under -ml 1; they belong on
# the end of the preceding word so `text` carries punctuation (render.py breaks
# caption chunks on trailing punctuation).
_PUNCT_ONLY = set(".,!?;:%)]}\"'…-–—")


def resolve_model(explicit: Path | None) -> Path:
    model = explicit or DEFAULT_MODEL
    model = model.expanduser()
    if not model.exists():
        sys.exit(
            f"whisper model not found: {model}\n"
            "Download one, e.g.:\n"
            "  mkdir -p ~/.cache/whisper-models && curl -L -o "
            "~/.cache/whisper-models/ggml-base.en.bin \\\n"
            "    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"
        )
    return model


def call_whisper(audio_path: Path, model: Path, language: str | None, threads: int | None) -> dict:
    if not shutil.which("whisper-cli"):
        sys.exit("whisper-cli not on PATH. Install with: brew install whisper-cpp")

    out_prefix = audio_path.with_suffix("")
    cmd = [
        "whisper-cli",
        "-m", str(model),
        "-f", str(audio_path),
        "-oj",              # JSON output
        "-ml", "1",         # max segment length 1 -> one token per segment
        "-of", str(out_prefix),
    ]
    if language:
        cmd += ["-l", language]
    if threads:
        cmd += ["-t", str(threads)]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"whisper-cli failed ({proc.returncode}): {proc.stderr[-500:]}")

    json_path = Path(f"{out_prefix}.json")
    if not json_path.exists():
        raise RuntimeError(f"whisper-cli wrote no JSON at {json_path}")
    return json.loads(json_path.read_text())


def to_contract_schema(wj: dict, spacing_threshold: float = 0.05) -> dict:
    """Convert whisper.cpp JSON into the pipeline's transcript contract."""
    segments = wj.get("transcription") or []

    words: list[dict] = []
    prev_end: float | None = None

    for seg in segments:
        off = seg.get("offsets") or {}
        start_ms, end_ms = off.get("from"), off.get("to")
        raw = (seg.get("text") or "")
        text = raw.strip()
        if start_ms is None or end_ms is None or not text:
            continue

        start, end = start_ms / 1000.0, end_ms / 1000.0

        # Glue standalone punctuation onto the previous word.
        if text and all(c in _PUNCT_ONLY for c in text):
            for prior in reversed(words):
                if prior.get("type") == "word":
                    prior["text"] += text
                    prior["end"] = max(prior["end"], end)
                    prev_end = prior["end"]
                    break
            continue

        if prev_end is not None and start - prev_end >= spacing_threshold:
            words.append({"type": "spacing", "text": " ", "start": prev_end, "end": start})

        # No speaker_id: whisper.cpp does not diarize. pack_transcripts.py
        # renders an empty speaker tag when it's absent.
        words.append({"type": "word", "text": text, "start": start, "end": end})
        prev_end = end

    full_text = " ".join(w["text"] for w in words if w.get("type") == "word")

    return {
        "text": full_text,
        "words": words,
        "language_code": ((wj.get("params") or {}).get("language")),
        "_provider": "whisper.cpp",
        "_model": (wj.get("model") or {}).get("type"),
        "_no_diarization": True,
    }


def transcribe_one(
    video: Path,
    edit_dir: Path,
    model: Path,
    language: str | None = None,
    threads: int | None = None,
    verbose: bool = True,
    audio_track: int = 0,
    spacing_threshold: float = 0.05,
) -> Path:
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcript_path(edit_dir, video, audio_track)

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path.name}")
        return out_path

    if verbose:
        print(f"  extracting audio from {video.name}", flush=True)

    n_tracks = count_audio_tracks(video)
    if n_tracks > 1 and verbose:
        print(f"  note: {video.name} has {n_tracks} audio tracks, using track "
              f"{audio_track + 1} (--audio-track to change)", flush=True)

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        extract_audio(video, audio, audio_track)

        peak = peak_dbfs(audio)
        if peak < -60.0:
            raise RuntimeError(
                f"track {audio_track + 1} of {video.name} is silent "
                f"(peak {peak:.1f} dBFS) - not transcribing. "
                + (f"The file has {n_tracks} audio tracks; try --audio-track "
                   + " or ".join(str(i) for i in range(n_tracks) if i != audio_track) + "."
                   if n_tracks > 1 else "Check the source audio.")
            )

        if verbose:
            print(f"  transcribing locally with {model.name}", flush=True)
        raw = call_whisper(audio, model, language, threads)

    payload = to_contract_schema(raw, spacing_threshold)
    out_path.write_text(json.dumps(payload, indent=2))

    if verbose:
        n_words = sum(1 for w in payload["words"] if w.get("type") == "word")
        print(f"  saved: {out_path.name} ({out_path.stat().st_size/1024:.1f} KB) "
              f"in {time.time()-t0:.1f}s")
        print(f"    words: {n_words}  (no speaker labels - whisper.cpp does not diarize)")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe a video locally with whisper.cpp")
    ap.add_argument("video", type=Path, nargs="?", help="Path to video file")
    ap.add_argument("--edit-dir", type=Path, default=None)
    ap.add_argument("--model", type=Path, default=None,
                    help=f"GGML model path. Default: {DEFAULT_MODEL}")
    ap.add_argument("--language", type=str, default=None, help="Language code, e.g. 'en'")
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--audio-track", type=int, default=0)
    ap.add_argument("--spacing-threshold", type=float, default=0.05)
    ap.add_argument("--convert", type=Path, default=None,
                    help="Convert an existing whisper-cli JSON to the pipeline schema and print it.")
    args = ap.parse_args()

    if args.convert:
        print(json.dumps(to_contract_schema(json.loads(args.convert.read_text()),
                                            args.spacing_threshold), indent=2))
        return

    if args.video is None:
        ap.error("video is required unless --convert is used")

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    transcribe_one(
        video=video,
        edit_dir=(args.edit_dir or (video.parent / "edit")).resolve(),
        model=resolve_model(args.model),
        language=args.language,
        threads=args.threads,
        audio_track=args.audio_track,
        spacing_threshold=args.spacing_threshold,
    )


if __name__ == "__main__":
    main()
