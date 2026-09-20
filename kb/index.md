# video-use knowledge base — index

Working knowledge of how this repo actually behaves on **this machine**. Maintained by Claude.
Read this at the **start** of any video-use task; append findings at the **end**.

Upstream: [browser-use/video-use](https://github.com/browser-use/video-use). Clone lives at `~/Documents/video-use`.

## Read this first

The one-line mental model: **the LLM never watches the video, it reads it.** A word-level
transcript is the primary surface; PNG composites are pulled only at decision points.
Cuts are chosen in text, then executed by ffmpeg.

```
Transcribe ──> Pack ──> reason over text ──> EDL ──> Render ──> Self-eval ──┐
                                                        ^                  │
                                                        └── fix + re-render ┘ (max 3)
```

## Map

| File | What's in it | Read when |
|---|---|---|
| [architecture.md](architecture.md) | Pipeline stages, data flow, why each artifact exists | Orienting, or changing pipeline shape |
| [data-contract.md](data-contract.md) | **The transcript JSON schema** — the repo's real seam | Swapping ASR providers, debugging captions |
| [helpers.md](helpers.md) | Per-script reference: flags, behaviour, EDL schema | Before invoking any helper |
| [environment.md](environment.md) | This machine: paths, keys, versions, what's installed | Cold start, "is X available?" |
| [gotchas.md](gotchas.md) | Verified traps that cost real debugging time | Anything fails unexpectedly |
| [worklog.md](worklog.md) | Dated log of local changes + why | Understanding a local divergence |
| [check-env.sh](check-env.sh) | Re-verifies everything in environment.md | Cold start, or something broke |
| [new-machine.md](new-machine.md) | Cloning onto another laptop; what doesn't travel | Setting up a second machine |
| [bootstrap.sh](bootstrap.sh) | Idempotent installer for a fresh macOS machine | Same |

## Hard rules (never violate — these cause silent failures)

Full list in `SKILL.md`. The four that bite hardest:

1. **Subtitles applied LAST** in the filter chain, after every overlay. Otherwise overlays hide captions.
2. **Per-segment extract → lossless `-c copy` concat.** Not a single-pass filtergraph, or you double-encode.
3. **30ms audio fades at every boundary.** Otherwise audible pops at each cut.
4. **Never cut inside a word.** Snap to word boundaries; pad 30–200ms for ASR timestamp drift.

Plus: all outputs go to `<videos_dir>/edit/`, **never** inside this repo.

## Fast facts

- Run helpers as `uv run python helpers/<name>.py` — there are no console scripts.
- `pytest` is not a declared dep: `uv run --with pytest python -m pytest tests/`.
- **`main` is the working branch** and this fork's copy of the tool (`local` is a synonym at the
  same commit). `pr/*` branches alone are based on upstream `main`, for the open PRs.
- Three ASR providers wired up: Deepgram (default, diarizes), whisper.cpp (free, local, no
  diarization), ElevenLabs (unconfigured). Each has a different flaw — see [gotchas.md](gotchas.md).
- Paid transcription is cached per source. Never re-transcribe unnecessarily; iterate with whisper.
- All three animation engines installed: Manim, HyperFrames, Remotion.
- Piping to `tail` masks exit codes. Use `set -o pipefail`.
- **Check what language is actually spoken before transcribing a batch.** `--language en` on
  code-switched (e.g. Hinglish) audio returns confident English gibberish and drops ~a third of
  the words — and since the cut is reasoned from the transcript, it corrupts the *edit*, not just
  the captions. Use `--language multi`; `detect_language` picks one language and fails at this.
- **On a first transcription, run the free whisper pass alongside the paid one.** It has caught
  real errors (names, opening lines) that would otherwise be burned into captions. On Hinglish
  use multilingual `ggml-small.bin` with **`-l en`** (it renders Hindi into English and can be
  compared for meaning); `-l hi`/`-l auto` garble it, and word-level `-ml 1` output is unusable
  for Devanagari, so whisper checks *wording only* — never timings. See gotchas.md.
- **Grep a `--language multi` transcript for Spanish before burning captions**
  (`grep -lE '[¿¡áéíóúñ]' <edit>/transcripts/*.json`) — Deepgram drifts into Spanish on short
  or low-content clips. Hit 3 of 38 on Detour-2, one of them 47% of the clip.
- **Don't transcribe clips under ~1s** — both engines return pure hallucination for them.
- **A 0-word transcript is not evidence of silence.** Check with whisper before writing a clip
  off; loud music reads as "empty" and the −60 dBFS silence guard never trips. See gotchas.md.
- **Capture time is `com.apple.quicktime.creationdate`, never `creation_time`** — the latter is
  the file-write time and was wrong by up to 2h24m on Detour-2, on *some* clips only. A wrong
  file start puts every dashcam cutaway on the wrong minute. See gotchas.md.
- **Deepgram word spans are ~87% contiguous**, so snap-to-word-boundary usually cannot apply the
  Rule 4 pad, and a naive neighbour clamp pushes the cut *into* the word. See gotchas.md.
- **Dashcam OSD burns in GPS** — crop it before publishing; its speed readout is also free
  ground truth for locating a traffic jam.
- **Look at one frame from every clip during inventory — and again from every clip you PREPPED.**
  Catches upside-down rotation metadata, mixed orientations, and clips that are sideways with *no*
  rotation metadata at all, none of which show up in `ffprobe` dimensions. Sideways content wants
  a `transpose`, upright portrait wants a pillarbox; `ffprobe` reports both as 1080x1920 and the
  uniform-dimension check passes either way, so only a frame tells you which you have.
- **Self-eval audio numerically**, not by eye: compare the max sample-to-sample step at each cut
  boundary against a continuous-speech reference. A pop shows as a step well above it.
- Default shell is zsh — it does **not** word-split unquoted `$var`, and it reads `$var:x`
  as a history modifier. Brace **any** variable followed by `:`, not just in ffmpeg filter
  strings: `git show "${b}:path/file"` silently returns nothing without the braces (zsh applies
  `:h`/`:helpers…` as a modifier), which reads as "the feature is absent" rather than an error.
- **The concat must stream-copy VIDEO but re-encode audio once** (`-c:v copy` + one continuous
  AAC pass, `-ac 2`). A blanket `-c copy` inserts ~30 ms of AAC priming at every cut; a lone
  mono source corrupts everything after it. Both in gotchas.md, both pinned by tests.
- **Segment durations must be snapped to whole output frames**, or audio and video drift apart
  by ~13 ms per segment and it accumulates. See gotchas.md.
- **Measure a denoise chain on your own footage** — the aggressive chain recorded here is 3 dB
  *worse* on an outdoor monologue than a gentler one.
- **For speech under broadband noise use `arnndn`, not `afftdn`** — 12-24 dB better on real
  footage. Models: `~/.cache/rnnoise-models/`. And judge the result by the **absolute noise floor
  of the render**, not by separation: loudnorm puts ~4 dB straight back. See gotchas.md.
- **But for WIND use `helpers/denoise.py` (DeepFilterNet3), not `arnndn`** — wind is
  low-frequency and it *gusts*, which is `arnndn`'s weak case: 8 dB vs **23 dB** on the same
  clip, beating a commercial cloud service by 1 dB at 24x realtime, locally. Both SpeechBrain
  enhancement models were *worse than `arnndn`* here, and are 16 kHz. It builds a prepped
  source; set `audio_filter: ""` on those ranges. See gotchas.md.
- **To restore "outdoors" after denoising, blend back the residual high-passed at ~500 Hz**
  (`--ambience`), never the raw signal: 84% of what the model removes is wind below 300 Hz, so
  a 10% raw blend hands back the entire gain.
- **Parse `ffprobe -show_entries` output by KEY, never by position** — it prints `sample_rate`
  before `channels` whatever order you ask for, so a stereo clip reads as 48000 channels.
- **Noise is per-location, so denoise is per-segment** — `ranges[].audio_filter` overrides the
  EDL-level one.
- **Where dual-capture is the default look, build it as a prepped SOURCE** (under the original
  source key) rather than as overlays — captions and audio then resolve for free.
- **Verify every rendered segment has the same dimensions before compositing.** A portrait
  source that slipped the prep does NOT fail the `-c:v copy` concat — it plays stretched.
- **Clamp EDL range ends to `source_duration - 0.05`** (>1 frame): the frame-snap rounds the
  duration up, and a range flush with the source then overruns its audio.
- **PiP inset dimensions must be even** — `force_original_aspect_ratio` rounds to even and
  `alphamerge` then fails on the 1px mismatch.
- **Re-encode, don't `-c copy`, when joining clips that feed another filtergraph** — a
  stream-copied join reports a mid-stream property change and the graph fails to reinitialise.
- **Check every B-roll cutaway against the line it sits under.** The dashcam OSD speed readout
  makes this free; it killed 2 of 7 planned cutaways on Detour-2.
- **Place overlays with `-itsoffset`, never `setpts`, and always `repeatlast=0`** — over a long
  render a `setpts`-placed overlay drains ahead of the timeline, runs out early and then freezes
  the picture on its last frame. It hit 4 of 5 overlays on Detour-2 and reproduces only against
  the real base decoded from t=0. Scan every delivery with `freezedetect`. See gotchas.md.
- **Round range ENDS down and STARTS up to the millisecond.** Deepgram spans are contiguous, so
  a normally-rounded end can land microseconds past the next word's start — and captions are
  selected by *overlap*, so that word is burned in while none of it is spoken. The user hears a
  skip. See gotchas.md.
- **Read the assembled cut back as continuous prose before rendering.** It is the only thing that
  catches an OUT point taken from a word's *start* (drops the sentence's last word) or a join
  that skips the words carrying the meaning. Found 5 broken joins in a *delivered* cut.
- **`freezedetect d=0.4` false-positives on a locked-off talking head** — use `d=1.0`. And a
  dashcam clip at the end of a drive is probably a *parked* car; validate any motion metric on a
  known-moving control first.
- **Motion graphics are three layers**: `motion.py` (curves + per-role WEIGHTS + stagger),
  `brand.py` (a palette derived from delivered work), `components.py` (the archetypes).
  Author a **role**, never a duration — a hero landing and an aside fading must not match.
- **Speaker demotion** (`demotions` in the EDL) shrinks the talking head so a graphic owns the
  frame. `pad` cannot place it — its x/y evaluate once and the picture collapses to the
  top-left; use `overlay` with `eval=frame` on both the scale and the overlay. It is a
  *pairing*: the graphic must move into the vacated area or it lands on the card.
- **Subject masking** (`helpers/matte.py` + `behind_subject` on an overlay) lets a graphic pass
  behind the speaker. Only the MATTE is computed in Python — the picture stays in ffmpeg, so the
  colour round-trip tax does not apply. A centred graphic behind a centred subject vanishes
  entirely; that is the feature working, not a bug.
- **PIL's ImageDraw replaces, it does not blend.** A 9%-alpha element previewed on an opaque
  background looks 100% opaque. Preview via `Image.alpha_composite`, as ffmpeg does.
- **On-screen text goes in the EDL's `graphics` block** (`helpers/graphics.py`), anchored to a
  source, segment or spoken phrase rather than a timestamp, and sized as a fraction of the output
  height. Anchored entries survive a re-cut; hardcoded times do not.
- **`drawtext` does NOT fall back to another font** the way libass does for subtitles — a missing
  glyph is drawn as a blank box, silently. `Kohinoor.ttc` covers Latin + Devanagari (but not `→`).
  See gotchas.md.
- **Never name a zsh variable `path`** — it is tied to `$PATH` and a loop over it wipes out
  command lookup, which reads as a broken environment. See gotchas.md.
- **Anything positional in the output timeline must be measured from a real render**, never
  summed from EDL floats — extracts are frame-quantised. This bit both caption offsets
  (0.6s drift by the end of a 30-segment cut) and an overlay's `start_in_output`. A cheap
  `--draft` pass measures boundaries valid at any output resolution.

- **Piping frames through Python? Read and write `yuv420p` and tag the rawvideo
  INPUT with `-color_range tv -colorspace bt709`.** A bgr24 round trip costs ~20 dB,
  and an untagged input costs another ~19 dB, both silently. Measure any Python video
  stage against a plain re-encode of the same file. See gotchas.md.
- **Set music levels per cue against the programme in THAT window** — on Detour-2 the
  windows spanned 84 dB, so one global target left two cues inaudible and one clipping.
  Where a window has no headroom, duck the programme with the ramps outside the cue.
  Mix before loudnorm, never after. See gotchas.md.

## Maintaining this KB

At the end of a task, append to [worklog.md](worklog.md) and fold any durable, reusable
lesson into the right topic file. Rules: record only what was **verified**, note how it was
verified, and keep this index short — it loads into every session.
