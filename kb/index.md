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
| [storytelling.md](storytelling.md) | **Retention craft for talking-head cuts** — contrast, rhythm, withholding, the zenith | Planning a cut; before picture lock |
| [ideation.md](ideation.md) | **Where ideas come from** — recombination, the A+B=C identity formula, constraints | Deciding what to make; choosing a style |
| [distribution.md](distribution.md) | **After the render** — how the algorithm distributes, reading a flop, community posts | Judging performance; deciding what to fix |
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
- **`main` is the working branch** and this fork's copy of the tool — and now the only one.
  `pr/*` branches alone are based on upstream `main`, for the open PRs.
- Three ASR providers wired up: Deepgram (default, diarizes), whisper.cpp (free, local, no
  diarization), ElevenLabs (unconfigured). Each has a different flaw — see [gotchas.md](gotchas.md).
- Paid transcription is cached per source. Never re-transcribe unnecessarily; iterate with whisper.
- All three animation engines installed: Manim, HyperFrames, Remotion.
- Piping to `tail` masks exit codes. Use `set -o pipefail`. It also **hides the whole head of
  the output** — a `| tail -30` on a self-eval report silently dropped its pops section.
- **Never wait on a job with `pgrep -f "script.py"`** — `-f` matches full command lines, so the
  waiting shell matches *itself* and hangs forever after the job finishes. Wait on a marker the
  job prints, or on the output file. Cost ~10 idle minutes on an already-finished 4K render.
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
- **B-roll tiers: literal when the line is concrete, texture when it is abstract** — and the
  texture tier is only licensed when the footage is **you**. Footage of your own life is
  *evidence* for the claim; anything else in that slot is wallpaper, and 12 cuts/min of
  wallpaper reads as panic. The transferable lesson is upstream of the edit: **keep a standing
  library of yourself doing ordinary things**, so abstract lines have somewhere to go. Measured
  on a 16:31 reference cut in [storytelling.md](storytelling.md) §6.
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
  known-moving control first. It logs at **INFO**, so a hand-rolled check with `-v error`
  reports zero freezes — a false negative. Back-to-back spans (each end == the next start)
  over a static background are **caption changes**, not a stuck picture.
- **Never hardcode a timestamp in a self-eval probe.** When the cut shortens, the probe lands
  past the end of the file and reports `-999 dB` in the same column as every real level —
  indistinguishable from a scene that lost its audio. Anchor to the end card or a spoken word,
  like graphics and overlays. Cost us a scare on episode2's delivery.
- **Motion graphics are three layers**: `motion.py` (curves + per-role WEIGHTS + stagger),
  `brand.py` (a palette derived from delivered work), `components.py` (the archetypes).
  Author a **role**, never a duration — a hero landing and an aside fading must not match.
- **Speaker demotion** (`demotions` in the EDL) shrinks the talking head so a graphic owns the
  frame. `pad` cannot place it — its x/y evaluate once and the picture collapses to the
  top-left; use `overlay` with `eval=frame` on both the scale and the overlay. It is a
  *pairing*: the graphic must move into the vacated area or it lands on the card.
- **Run `helpers/coverage.py` on any finished cut.** It reports visual events/min, median hold,
  and every stretch with nothing changing — with what is said there, the unused b-roll you own,
  and insertion points on sentence boundaries. A delivered 3m34s episode had **124.9s (58%)**
  with no visual change while 9 b-roll assets sat unused.
- **Pacing is a ceiling, not a target.** Format decides pace — do not copy an explainer's
  8.6 events/min onto a personal essay. The rule is: no stretch beyond ~25-30s without
  something changing, unless the hold is deliberate. And this measures CHANGE, not INTEREST;
  a retention export replaces the whole guess.
- **UI motion numbers are wrong for video.** Web guidance (150 ms default, <500 ms) exists
  because the user is *waiting*; a video viewer is not. `motion.WEIGHTS` is deliberately 2-4x
  slower. What does transfer: curve for opacity, spring for transforms — a spring on alpha
  overshoots past opaque and dips back, which pulses. See gotchas.md.
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

- **`zoompan`'s `d` is output-frames-per-INPUT-frame**, so under `-loop 1` every looped frame
  gets expanded — a 3.6s Ken Burns still came out **389s / 382MB**. Cap with `-frames:v`, and
  probe the duration of anything built with it. See gotchas.md.
- **A grade does not travel between episodes if the colour space changed.** Ep2 is HLG where
  Ep1 was SDR; the tone-map already supplies the punch, so Ep1's grade string measured sat
  0.407 vs its own delivered 0.29. White-balance off a **known white in frame** (the t-shirt),
  not a global R/B ratio, and set desaturation *after* the contrast curve.
- **`coverage.py` counts 75 jump cuts on one locked-off frame as 5 visual events — correctly.**
  Push-ins below ~1.1x stop a splice reading as a glitch but are invisible as *events*; only
  something that replaces the frame moves the number. Run it on the picture lock, before
  building graphics.
- **Anchor graphics to spoken words and RAISE when the word was cut.** A resolver that clamps
  to the nearest survivor puts the graphic on a silent frame and nothing looks wrong in the
  render. Print the words each overlay actually covers, and read them.
- **`drawtext` cannot take an apostrophe in `text=`** at all — use `textfile=`.

- **Overlays are resolution-specific: render.py composites them at 0:0 with no scaling.**
  A 4K overlay on a 1080p base shows its top-left quarter, which reads as bad framing rather
  than a bug. QC overlay geometry at the DELIVERY height, and name the file with its height
  the way Ep1's `TEASER_BROLL_2160.mp4` does. `ranges[].zoom` is resolution-independent;
  overlays are not.

- **Creativity is recombination, not talent** — and style is `A + B = C`: A your niche, B
  something from outside it, C your identity. B is the real decision and it is made once for a
  channel, not per video. **Repetition is what builds identity**, so consistency across episodes
  beats novelty within one — `brand.json` is a commitment, not a starting point.
  See [ideation.md](ideation.md).
- **Steal the method, never the artifact.** The reconciliation of "don't copy" and "every artist
  is a thief": lift the methodology and tweak it, not the finished piece. Same file.
- **Blocked on ideas is usually information OVERLOAD, not a shortage** — the fix is an artificial
  constraint that shrinks the option space, which is also why our decision table works. Same file.
- **Name the ZENITH before cutting** — the one moment the whole episode builds to — and then
  leave it undecorated: no graphic, no music swell, no cutaway across it. In HillierSmith's
  breakdown of a 75%-retention cut, the highest-retention moment in the video is the one where
  the editor does nothing and lets it play. Decorating the peak is backwards; decoration belongs
  on the build. See [storytelling.md](storytelling.md).
- **Decide the ONE image of the story and withhold its clear reveal.** Anticipation is the
  retention mechanism, not payoff — show it partial, obscured or brief early, and give the full
  frame only when the story turns. Ep2 spent its cricket photograph at 1:00 and had nothing left
  to reveal. Same file.
- **Wall-to-wall music has no meaning.** Contrast is what creates focus: a naked talking head
  next to a scored one. If the bed never leaves, its arrival and departure stop being signals.

- **render.py never cleans `clips_*`, so a changed EDL leaves stale segments behind.** Build
  expected filenames from the EDL, never glob. Same for any cached derived file: check
  freshness (mtime vs source), not just dimensions.
- **To prove a window is unscored, diff against a no-music control** — never read an absolute
  floor. Room tone varies up to 17 dB between takes and swamps a ducked bed. And read the
  **magnitude, not the sign**: a SCORED window lands ~1 dB *below* a known-naked reference,
  because a bed gives the limiter more to take back. The obvious reading inverts the verdict.
- **A killed render loses only the composite.** `clips_graded/`, `base.mp4` and `master.srt`
  survive; the partial output mp4 has no moov atom and is unrecoverable. Assert the segments
  and base post-date `edl.json`, then skip straight to the composite — minutes, not ~18.
  Pattern in `episode2/edit/build/resume_render.py`. See [gotchas.md](gotchas.md).
- **Generated b-roll: watermark, burned captions, 720p/24fps — and an editorial line.**
  Environments and objects, not people who could read as the subject or their family; the real
  photographs carry the people. Scan supplied clips densely, a "reference" montage may hold
  shots that exist nowhere else. See [gotchas.md](gotchas.md).

- **Selective speed-up must be a prepped SOURCE with a rescaled transcript**, never a
  per-range `setpts` — captions inside a sped range drift by the rate (2.6s on a 26s
  segment) and the frame-count check fails. Keep the SPEC in ORIGINAL times and convert at
  emit; anything resolving anchors by source name needs the same rename. See gotchas.md.
- **An effect 9 dB under the programme raises a window's RMS by 0.5 dB**, so "adds nothing"
  proves nothing — and subtracting two renders leaves a uniform ~2.5 dB limiter/codec
  residual everywhere. Floor-against-a-control works for beds; peak is useless once a
  limiter pins every window. Short effects are a mix decision, not a measurement.

- **Impressions are the system's confidence, not a reward withheld.** A video is served in
  widening waves — loyal audience first, then riskier — and impressions stop when a wave stops
  converting. So **good CTR + good retention + low impressions usually means the video never
  left the loyal base**: check new-vs-returning per video before blaming the cut.
  See [distribution.md](distribution.md).
- **Ignore the first 24-48 hours** (YouTube labels early figures estimates), compare like with
  like **in the same window** (first week vs first week, same content pillar — "velocity", not
  totals), and **put the energy into the next episode rather than rescuing the last**. Our
  pipeline makes re-rendering cheap, which makes that trap easier to fall into here.
- **Community posts are the most underused surface** — reportedly ~10% of one channel's
  impressions. Never "here's my video"; post the value that did not fit in the thumbnail.
  And a subscriber who never watches costs nothing, so do not optimise subscriber "quality".
- **Using new features does not buy impressions**, and tags are low-leverage whatever a vendor
  video claims. Metadata helps the system CLASSIFY a video; viewer behaviour decides how far it
  TRAVELS. Same file.

## Maintaining this KB

At the end of a task, append to [worklog.md](worklog.md) and fold any durable, reusable
lesson into the right topic file. Rules: record only what was **verified**, note how it was
verified, and keep this index short — it loads into every session.
