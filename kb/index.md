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
- Local changes live on git branch `local`; `main` stays clean for `git pull --ff-only`.
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
  real errors (names, opening lines) that would otherwise be burned into captions.
- **Look at one frame from every clip during inventory.** Catches upside-down rotation metadata
  and mixed orientations, neither of which shows up in `ffprobe` dimensions.
- **Self-eval audio numerically**, not by eye: compare the max sample-to-sample step at each cut
  boundary against a continuous-speech reference. A pop shows as a step well above it.
- Default shell is zsh — it does **not** word-split unquoted `$var`.

## Maintaining this KB

At the end of a task, append to [worklog.md](worklog.md) and fold any durable, reusable
lesson into the right topic file. Rules: record only what was **verified**, note how it was
verified, and keep this index short — it loads into every session.
