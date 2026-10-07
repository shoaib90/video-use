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
**As a cross-check, give it its own `--edit-dir`** (e.g. `<edit>/whisper_check`): every
transcriber writes `<edit>/transcripts/<stem>.json`, so on the same dir it refuses ("written by
deepgram") — and the obvious fix, `--force`, overwrites the *paid* transcript. (Episode 3, 2026-10-05.)

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
- **`--height`** output height (2160/1440/1080…); default 1080, 720 with `--draft`
- **`--crf`** x264 CRF for the *extract*, i.e. the quality ceiling. Default 16 final / 22 preview
  / 28 draft. The composite encode is derived as `crf - 2`. See gotchas.md on the two-generation
  encode — this flag is the one that actually controls output quality.
- `--build-subtitles` generates `master.srt` from transcripts + EDL offsets inline. A word
  is captioned only if **at least half of it** falls inside the cut. Before that test, a word that
  starts before the same speaker's previous word ended is clamped to that end, because Deepgram
  overlaps make the next word look half-heard. Added 2026-10-03 and pinned by
  `tests/test_render_caption_words.py`. Before, any overlap at all captioned a word the viewer
  never hears.
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
- **`ranges[].zoom`** (number ≥ 1.0, plus optional **`zoom_x`** 0–1 horizontal bias, default
  0.45, and **`zoom_y`** 0–1 vertical bias, default 0.5) — per-segment push-in to disguise jump
  cuts, or a single carved out of a wide two-shot. Resolution-independent, and since 2026-10-03
  the crop is taken on the **source frame before the downscale**, so a 2.6x single from a 4K
  wide is native detail at 1080p (it used to crop after the scale: an upscaled 960x540 at 2x).
  `zoom_y` was added for the same podcast job, where faces sit at about 35% of frame height, not
  the middle. Pinned by `tests/test_render_zoom_crop.py`. **Prefer this over a raw `filter`.**
- **`ranges[].video`** `{"source": <key>, "offset": <s>}` (added 2026-10-03): take this range's
  **picture** from a second, synced camera, at `start - offset` in that file. The **audio,
  transcript and captions stay on `source`**. The picture is resampled to the output rate
  before any zoom or push, so a 25 or 100 fps camera keeps real-time speed under a 30 fps
  render. HDR handling and crop geometry use the picture file, and the output size is still
  measured from `source`, so the concat holds. The key must be in `sources`. Pinned by
  `tests/test_render_video_source.py`. Sync, subject and colour tooling for a real shoot is in
  podcast Episode 1's `edit/build/dslr_*.py` (see gotchas.md).
- **`ranges[].grade`** (added 2026-10-05) — overrides the EDL `grade` for one range. The key's
  presence is what counts: `"none"`, `null` or `""` turns grading off. Built for archival SDR
  footage inside a graded HLG shoot (Episode 3's 2019 clip, "it should look like the past"),
  and also used on the black end card. `tests/test_render_segment_grade.py`.
- **`ranges[].filter`** — raw per-segment video filter, applied *after* the grade and after any
  zoom. Escape hatch. **Output dimensions must be identical across every segment** or the
  `-c copy` concat (Rule 2) fails — so a `crop` must always be followed by a `scale` back to the
  common size, which also makes it resolution-specific.
- **`subtitle_style`** — `words_per_chunk` (default 2), `case` (`"upper"` default, or
  `"sentence"`), and `force_style` (ASS override string). `"sentence"` keeps the ASR's own
  capitalization but capitalizes any cue that opens the file or follows sentence-final
  punctuation — needed because a cut can make a mid-sentence word start a sentence.
- **`cards`** + **`brand`** — glass cards (`helpers/cards.py`, added 2026-10-01). Word-anchored
  `list` / `stat` specs; rendered by HyperFrames into `<edit>/animations/cards/<id>/` (card + mask
  MOVs, cached by content hash) and composited after `overlays`, before `graphics` and subtitles.
  `brand` is an optional path to a `brand.json` when the episode has none of its own (Episode 2
  points at YT1's). Full guide: `SKILL.md`, "Glass cards". Resolve before rendering:
  `uv run python helpers/cards.py <edl> --clips clips_graded`. Needs Node.
  `scale` (0.4–1.0, list and stat; added 2026-10-05) is a static CSS scale on a wrapper
  ("holder") around the card. It leaves the card's own entrance and exit tweens alone, and the
  mask pass runs the same wrapper, so the glass stays under the card. The bound check uses the
  SCALED height. Tests are in `tests/test_cards.py` `ScaleTests`.
  **`keyline`, `deck`, `annotate`** (added 2026-10-06; the Kallaway look, `storytelling.md` §13)
  use the brand's new `glow` key (default `#8B5CF6`), not `accent`. A keyline's mask is empty (no
  glass); deck and annotate are full frame over the frosted picture, and fade their container
  by opacity only. An `annotate` image is inlined as a data URI at the pixels it occupies.
  `decks` (EDL level) names chapter lists that `deck` cards point at. Tests:
  `tests/test_cards_kallaway.py`.
- **`silhouettes`** — rim-lit speaker silhouettes (added 2026-10-06). Needs `matte`; anchored
  like cards (`at`, `crowd_at`, `out`/`hold`, `fade`); refuses demotions. Built in ffmpeg from
  the matte by `build_silhouette_filter`; its generated layers use the BASE's probed fps, not
  the nominal `fps` argument. The matte input is now split only when both the behind-subject cut
  and a silhouette use it, and the base is split for the behind cut only when a behind overlay
  exists (an unconnected split output is an ffmpeg error). Tests:
  `tests/test_render_silhouette.py`.
- `force_style`'s `MarginV` is relative to `PlayResY=288`. The shipped default of 90 is tuned
  for **vertical** video; for 16:9 landscape ~28 sits the caption about 10% up from the bottom.

## review.py — pre-delivery review *(local addition, 2026-10-05)*
```
review.py <edit_dir> --render <final.mp4> --label v8 [--prev <edit>/review/v7]
          [--raw <no-music render> --music-ok "0-126,146-156"] [--exempt-beats "^0 "]
          [--accepted <json>] [--skip-render] [--no-reel]
```
Runs every check in [mistakes.md](mistakes.md) that can be automated, and writes
`<edit>/review/<label>/`:
- `report.md`: PASS/FLAG per check, flags ranked HIGH > MED > LOW
- `edges.md`: each flagged or changed story edge, with the source speech before and after it
- `watchlist.md`: the timestamps Shoaib needs
- `reel.mp4`: ~14 s around every edge changed since `--prev`
- `ranges.json`: the next run's `--prev`
- `sheet_overlays_*.jpg`: one frame per overlay

What it needs and does:
- **Story ranges** are rebuilt from the EDL: abutting shots on one source merge, so camera
  cuts are not mistaken for edits.
- **Edge checks** need `<edit>/transcripts/<source>.json`.
- **`--exempt-beats`** marks teasers and cold opens, which skip the context checks C1-C4.
- **`accepted.json`** entries are flags that were checked and judged fine. Each needs a `why`.
  They are listed in the report, not counted.

Calibrated on podcast Episode 1 v7, where 60 HIGH flags fell to 3 genuine:
- tag questions ("correct?", "है ना?", "ठीक है?") are not questions
- a join to the next range on the same source within 60 s is MED ("read the join"), and LOW
  under 3 s (a tightening cut)
- a trimmed lead-in of 4 words or fewer, all fillers, is LOW
- C7 fires only when the edge sits on the ghost word

Pinned by `tests/test_review_edges.py` (13 tests). Render checks reuse the episode QC methods:
- freezedetect at d=1.0
- step spikes at the cuts
- ebur128 loudness
- music presence measured in pauses against the aligned no-music render
