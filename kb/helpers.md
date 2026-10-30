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

## Transcript guards (all three transcribers, 2026-10-30)
New transcripts carry `_source_name` and `_source_size`. A cached transcript whose source differs prints a
WARNING and is still returned: it never re-bills, and prepped sources keep their original's transcript on
purpose. Size rather than mtime, because copying footage changes mtime. `transcribe_batch.py` refuses a
folder where two videos share a stem (`intro.mp4` + `intro.MOV`). Tests: `test_transcript_guards.py`.

## transcribe_deepgram.py — Deepgram nova-3  *(local addition)*
`--keyterms <file>`: names and terms to bias Nova-3 toward, one per line, `#` comments, max 100. Sent as one
`keyterm=` per term (Deepgram treats commas as one literal term, silently). Part of the cache identity.
Deepgram's docs say it works on multilingual. **Not yet tried on real Hinglish**: the unit test checks the
request, not the transcript. Compare one clip on the next new episode.
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
                              [--check] [--skip-check] [--jobs 4] [--no-reuse]
```
- **`--check`** validates and exits; every render runs the same checks first (`--skip-check` to bypass).
  Errors: missing source, bad or past-the-end range, sources that would come out at different sizes (they
  play stretched, the concat does not fail), missing subtitles file, missing overlay, a card or graphic
  anchor phrase that was cut, a missing ffmpeg filter. Warnings: a range within 50 ms of its source's end,
  an overlay bigger than the frame, no transcript or no audio. Pass the same `--height` as the real
  render or the overlay warning is meaningless. Costs ~1 s per source. Tests: `test_render_preflight.py`.
- **A missing `subtitles` file now stops the render** (it used to warn, exit 0 and ship no captions).
- **Segment reuse** is on by default: `clips_cache/<hash>.mp4`, hard-linked to `clips_*/seg_NN_<src>.mp4`.
  The key covers source name + size + mtime, range, all settings, any file a filter names, render.py,
  grade.py and the ffmpeg version, so editing render.py rebuilds everything, on purpose. The composite and
  loudnorm always run. Deleting `clips_cache/` is always safe. Tests: `test_render_reuse.py`.
- **Overlays are placed in whole frames (M061):** `start_in_output` and `duration` round to the frame grid, and an edge within 3
  frames of a cut moves to it, unless another opaque overlay hides that edge or it has alpha. Each move is printed. An end moved
  later holds the overlay's last frame for those few frames. Tests: `test_render_overlay_frames.py`.
- **`--jobs`** default 4; frame-identical to 1. Measured on 8 ranges of 4K HLG with captions, 24 s out:
  1 job 73 s, 4 jobs 68 s, then one range changed 39 s (~35 s of that is composite + loudnorm).
- **ffmpeg's own error is printed** on failure, no traceback.
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
- **`--no-exposure-check`** skips the exposure report. By default render.py measures the first
  segment (of the first 6) that shows a face and prints frame mean/p5/p95, face luma and red
  clipping, with a WARNING per broken guardrail. It never fails the render. See `exposure.py`.
- **Colour (2026-10-11):** HLG/PQ sources get `TONEMAP_CHAIN` (`npl=203`, `mobius`). Every output
  is tagged bt709 on all three fields: the concat and the copy path add `BT709_BSF`
  (`h264_metadata`), and the composite ends in `BT709_SETPARAMS` after the subtitles. ffmpeg 9
  ignores `-color_trc/-color_primaries`, so output flags cannot do this. Pinned by
  `tests/test_render_color.py`.

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
  **Stamps take `scale` too (2026-10-14)**: on a 1080x1920 Short the stage is 607 units wide, so a
  16:9-sized stamp is 1.78x too big; a stamp that does not fit the frame now RAISES (it used to be
  clipped by the frame edge, silently). Shorts use 0.68 for every stamp. `PortraitStampTests`.
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

## notes.py — timecoded notes on a cut *(local addition, 2026-10-30)*
```
notes.py <render> [--port N] [--idle-exit-min 240]      # prints the page's URL; run it in the background
notes.py --dump <edit>/notes/<render stem>/notes.json   # markdown, also saved as notes.md
```
Shoaib scrubs, presses N, picks cut / shorten / lengthen / wrong / note, types or records voice, and can click
the picture to pin a spot. Each note saves at once. `[` `]` jump between cuts. The dump adds the source file,
source time and words spoken at each note, and transcribes voice with whisper (free, `ggml-small.bin -l en`, so
Hindi reads as English), once. It gives no source times if `edl.json` is newer than the render. Notes are never applied
automatically. Binds 127.0.0.1, refuses other hosts and origins. Mic untested with a real voice: playback, save,
pin and reload were driven in the app's browser, and voice transcription was run on an audio file.
Tests: `test_notes.py`. Idea from upstream #178; written fresh, with a server so saving needs no folder picker.

## sync_cameras.py — second camera to a master, by audio *(local addition, 2026-10-30)*
```
sync_cameras.py --master IMG_1.MOV IMG_2.MOV --clips dslr/ -o <edit>/build/sync.json
```
Per clip: master, offset (`master_time = clip_time + offset`), confidence, drift, implied clock difference, and
status `synced` / `relocked` / `outside` (b-roll) / `unmatched` / `no_clock`. Run on podcast Episode 1's real 45
clips in 25 s: reproduced all 39 offsets that episode kept, within 20 ms, and also relocked C0461, which it
had marked invalid. Read that one by eye. Tests: `test_sync_cameras.py`.

## exposure.py — talking-head exposure check *(local addition, 2026-10-11)*
```
exposure.py <video> [--at SECONDS] [--grade '<filter>'] [--json]      # exit 1 on any warning
```
Reads one frame (the middle, by default) and warns when:
- **p5 < 20**: shadows crushed
- **the face is > 15 luma under the frame mean**: the subject is under-lit
- **> 0.5% of strongly red/orange pixels sit at R=255**: clothing has clipped
- **the grade's `saturation=` is > 1.0**

Luma is BT.709 on decoded 8-bit RGB, the measure the gotchas.md numbers use. The face box is
mediapipe's bundled face detector (full-range model), run in `~/.cache/video-use/retouch-env`
(built by `retouch_teeth.py`). The check never builds that env; without it, the face rule is
skipped and reported. render.py calls it automatically. Tests: `tests/test_render_color.py`.

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

**Added 2026-10-12 (Episode 4, M042-M045):**
- **Monologue mode** (auto: one speaker in the cut). A cut that removes real words inside a
  sentence is HIGH (C1/C5). A cut that removes only fillers or a pause is LOW. A join whose
  removal is under 1.6 s, with both edges quiet, is downgraded to LOW
  (`downgrade_tightening`): Deepgram word times drift too much to judge a fine cut.
- **C12** sliver: a story range of 2 words or less, or under 1 s, next to removed real words or a
  1.5 s+ gap (a splice from another attempt).
- **C13** dead lead-in: more than 1 s before the first word.
- **G4** (2026-10-14, M053): a derived cut whose EDL has `"parent": "<path to parent edl.json>"`
  (a Short) is flagged HIGH for every parent card whose phrase it keeps without a card of its own
  within 2 s. Cards only: mgx cues, effects and beds are `READ R12`. `tests/test_review_edges.py` `ParentCards`.
- **C14** said twice: the same 7-word run in two story ranges (a retake left in).
- **C15** edge on speech: the source audio at any edge where material is removed is louder than
  −38 dB. This is the check that judges a tightened cut.

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

**T9 (2026-10-30): a stray shot of 1-3 frames** at any cut or overlay edge: two big picture changes that close, against
how much that window otherwise moves. Compares brightness only, on a 64x36 grey copy, so a sliver matching its neighbours'
brightness can hide, and a fast handheld move just before a cut can trip it: look at the frames. ~0.3 s per cut. **T8 now also flags** an EDL naming a subtitles file that does not exist. Tests: `test_review_flash.py`.

## apple_sdr.swift — iPhone HLG / Dolby Vision to SDR with Apple's pipeline *(local addition, 2026-10-21)*
```
swiftc -O helpers/apple_sdr.swift -o ~/.cache/video-use/apple_sdr
~/.cache/video-use/apple_sdr <in.mov> <out.mov> [video Mbps, default 80]
```
AVFoundation converts to BT.709 SDR and applies the Dolby Vision RPU, which ffmpeg ignores (M054).
The output is HEVC Main10 at 80 Mb/s (a mezzanine), and the audio is copied untouched. Rotation is
baked in, so a portrait clip comes out 2160x3840. Use the output as a PREPPED SOURCE (EDL
`sources`), so render.py sees SDR and skips `TONEMAP_CHAIN`. ~4 s per 7 s of 4K on this Mac.
- **Frame grid:** output is constant 30 fps. Where the iPhone source drifts 1.7 ms off the grid
  (IMG_3984 from 6 s), frames snap to the grid, as render.py's `--fps 30` already does. Durations
  match the source to within a frame (12 Episode 5 takes).
- **A still from `AVAssetImageGenerator` tone-maps slightly flatter than this export path.**
  Judge the look on the exported file.
