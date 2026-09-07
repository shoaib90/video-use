# Helper reference

All invoked as `uv run python helpers/<name>.py`. No console scripts exist.
Paths resolve relative to the directory containing `SKILL.md`.

## transcribe.py — ElevenLabs Scribe
```
transcribe.py <video> [--edit-dir D] [--language en] [--num-speakers N] [--audio-track K]
```
Extracts mono 16kHz wav → uploads to Scribe (`scribe_v1`, verbatim, diarize, audio events,
word granularity) → writes `<edit>/transcripts/<stem>.json`.
- **Cached**: returns immediately if the transcript exists.
- **Silence guard**: refuses to upload a track peaking below −60 dBFS (catches wrong-track
  selection before you pay for silence). Suggests other tracks when the file has several.
- `--audio-track` matters for OBS captures: game on track 0, mic on track 1. Track 0 keeps the
  plain filename; others get a `.trackN` suffix.

## transcribe_deepgram.py — Deepgram nova-3  *(local addition)*
```
transcribe_deepgram.py <video> [--model nova-3] [--language en] [--spacing-threshold 0.05]
transcribe_deepgram.py --convert <deepgram_response.json>
```
Drop-in for the above; emits the identical schema. See [data-contract.md](data-contract.md).
`--num-speakers` is accepted for parity but **ignored** — Deepgram auto-detects and takes no hint.
`--convert` does the mapping offline, no API call, no video needed.

## transcribe_whisper.py — local whisper.cpp  *(local addition)*
```
transcribe_whisper.py <video> [--model ~/.cache/whisper-models/ggml-small.en.bin]
                              [--language en] [--threads N]
transcribe_whisper.py --convert <whisper_cli_out.json>
```
**Free, offline, no key.** Same schema as the others. Runs `whisper-cli -oj -ml 1`, converts
millisecond offsets, and glues standalone punctuation onto the preceding word.
**No diarization** — omits `speaker_id`, so `takes_packed.md` has no S0/S1 tags. Don't use it
alone on multi-speaker footage. Defaults to `small.en`; see gotchas.md for why not `base.en`.
Good for free iteration and as a cross-check on dropped filler words.

## transcribe_batch.py
```
transcribe_batch.py <videos_dir>
```
4-worker parallel transcription. Use for multi-take shoots. Shares the cache test with
`transcribe.py` via `transcript_path()` so the two can't diverge.

## pack_transcripts.py
```
pack_transcripts.py --edit-dir <dir> [--silence-threshold 0.5] [-o out.md]
```
`transcripts/*.json` → `takes_packed.md`. Groups words into phrases, breaking on silence
≥ threshold **or** speaker change. Output shape:
```
## take01  (duration: 10.2s, 4 phrases)
  [000.72-000.98] S0 Um,
  [001.60-004.98] S0 ninety percent of what a web agent does is completely wasted.
```
Those `[start-end]` ranges are what you cite in the EDL.

## timeline_view.py
```
timeline_view.py <video> <start> <end> [-o out.png]
```
Filmstrip + waveform + word labels for a range. **Not a scan tool** — use at decision points
and for self-eval, not continuously. Readable directly; the waveform makes the 30ms boundary
fade visible as a small V-notch, which is how you confirm Hard Rule 3 held.

## grade.py
```
grade.py <in> -o <out> [--preset subtle|neutral_punch|warm_cinematic|none]
                       [--filter '<raw ffmpeg>'] [--analyze <clip>] [--list-presets]
```
Omit `--preset` for auto mode: samples frames, computes brightness/contrast/saturation stats,
emits a subtle per-clip correction. `--analyze` prints what it *would* do without writing.

## render.py
```
render.py <edl.json> -o <out> [--preview] [--draft] [--build-subtitles]
                              [--no-subtitles] [--no-loudnorm] [--fps 30]
```
- `--draft` 720p ultrafast CRF28 (cut-point checking) · `--preview` 1080p CRF22 (QC-able)
- `--build-subtitles` generates `master.srt` from transcripts + EDL offsets inline
- `--fps` forces the output rate; default preserves the first source's rate

### EDL schema
```json
{
  "sources": { "take01": "../take01.mp4" },
  "grade": "auto",
  "ranges": [
    { "source": "take01", "start": 0.50, "end": 3.20, "beat": "cold open" }
  ],
  "subtitles": "master.srt",
  "overlays": []
}
```
- `sources` paths resolve relative to the **edit dir**.
- `grade`: `"auto"` for per-segment analysis, a preset name, or a raw ffmpeg filter string.
  Prefer a **fixed string over `"auto"`** for a static single-camera shot: auto analyses each
  range independently, so in principle it can flicker between cuts.
- `ranges[].beat` / `.note` are free-text labels echoed in render logs — use them, they make
  the output readable.
- Transcript filenames must match the `sources` **keys** for captions to attach.

### Local additions to the EDL schema

These three fields are local extensions (not upstream). All optional and backward-compatible.

```json
{
  "audio_filter": "highpass=f=100,afftdn=nr=24:nf=-25",
  "subtitle_style": { "words_per_chunk": 6, "case": "sentence", "force_style": "FontName=..." },
  "ranges": [ { "…": "…", "filter": "crop=1812:1018:24:31,scale=1920:1080" } ]
}
```

- **`audio_filter`** — applied per segment *before* the 30ms fades, so the fades stay on the
  true edges (Rule 3). For denoise/EQ.
- **`ranges[].filter`** — per-segment video filter, applied *after* the grade. Built for
  push-in/reframe to disguise jump cuts on a static camera. **Output dimensions must be
  identical across every segment** or the `-c copy` concat (Rule 2) fails — so a `crop` must
  always be followed by a `scale` back to the common size.
- **`subtitle_style`** — `words_per_chunk` (default 2), `case` (`"upper"` default, or
  `"sentence"`), and `force_style` (ASS override string). `"sentence"` keeps the ASR's own
  capitalization but capitalizes any cue that opens the file or follows sentence-final
  punctuation — needed because a cut can make a mid-sentence word start a sentence.
- `force_style`'s `MarginV` is relative to `PlayResY=288`. The shipped default of 90 is tuned
  for **vertical** video; for 16:9 landscape ~28 sits the caption about 10% up from the bottom.
