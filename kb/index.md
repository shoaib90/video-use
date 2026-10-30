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
| [shooting.md](shooting.md) | **Camera and lighting setup** for indoor talking heads: 2x, 4K, diffused key at 45°, dark monitor | Before a shoot; when a face looks unclear |
| [facts.md](facts.md) | **Specifics for each stage**: transcribing, cutting, rendering, sound, graphics, packaging | Before that stage |
| [gotchas.md](gotchas.md) | Verified traps that cost real debugging time | Anything fails unexpectedly |
| [storytelling.md](storytelling.md) | **Retention craft for talking-head cuts** — contrast, rhythm, withholding, the zenith | Planning a cut; before picture lock |
| [ideation.md](ideation.md) | **Where ideas come from** — recombination, the A+B=C identity formula, constraints | Deciding what to make; choosing a style |
| [distribution.md](distribution.md) | **After the render** — how the algorithm distributes, reading a flop, community posts | Judging performance; deciding what to fix |
| [mistakes.md](mistakes.md) | **Every mistake Shoaib caught, on every video, and the check that now catches it** | Before every delivery |
| [worklog.md](worklog.md) | Dated log of local changes + why | Understanding a local divergence |
| [handoff.md](handoff.md) | **Per-episode `edit/HANDOFF.md`**: state, decisions, next step, for switching accounts mid-edit | Opening or pausing any episode |
| [check-env.sh](check-env.sh) | Re-verifies everything in environment.md | Cold start, or something broke |
| [new-machine.md](new-machine.md) | Cloning onto another laptop; what doesn't travel | Setting up a second machine |
| [bootstrap.sh](bootstrap.sh) | Idempotent installer for a fresh macOS machine | Same |

## Before delivering ANY preview

Run `helpers/review.py`, clear its HIGH flags, walk the READ items in
**[mistakes.md](mistakes.md)** (the cross-video ledger of every mistake Shoaib caught), and
deliver the watch-list plus the changes reel. When Shoaib reports something new, add it to
the ledger the same day, with an automated check where possible. (CLAUDE.md has the full rule.)

## Hard rules (never violate — these cause silent failures)

Full list in `SKILL.md`. The four that bite hardest:

1. **Subtitles applied LAST** in the filter chain, after every overlay. Otherwise overlays hide captions.
2. **Per-segment extract → lossless `-c copy` concat.** Not a single-pass filtergraph, or you double-encode.
3. **30ms audio fades at every boundary.** Otherwise audible pops at each cut.
4. **Never cut inside a word.** Snap to word boundaries; pad 30–200ms for ASR timestamp drift.

Plus: all outputs go to `<videos_dir>/edit/`, **never** inside this repo.

## Facts for the stage you are in

**Before each stage, read its section of [facts.md](facts.md).** They were split out of this file on 2026-10-30 so
every session stops paying ~6K tokens for all of them.

| Stage | Section of facts.md |
|---|---|
| Before transcribing, or looking through new footage | Transcribing and inventory |
| Before planning or changing a cut | Cutting and story |
| Before changing render.py, or when a render looks wrong | Rendering |
| Before denoising or mixing | Sound |
| Before building graphics or judging pace | Graphics and pacing |
| Before writing a one-off QC probe | Self-evaluation |
| Before an idea, a title or a thumbnail | Ideas and packaging |
| Before judging how a video did | After publishing |

## Always true

- **Every render validates first, and reuses what did not change** (2026-10-30). `render.py` runs its preflight before encoding, or
  alone with `--check`: sources, ranges, sizes, captions, overlays, anchors, ffmpeg filters. Unchanged segments come from
  `clips_cache/`, hard-linked, so a notes round rebuilds only what moved. Delete `clips_cache/` freely once a cut is approved.
- **Deliver the notes page with a preview**: `helpers/notes.py <render>` gives Shoaib frame-accurate notes; `--dump` reads them
  back with source times and the words spoken there. See [helpers.md](helpers.md).
- **Second camera: `helpers/sync_cameras.py`** syncs by audio and proves it with the camera clocks.
- **Names in the script? Pass `--keyterms <edit>/keyterms.txt` to the first Deepgram run** of an episode. Not yet compared on real Hinglish.
- **No holds, no still frames (M046, Shoaib 2026-10-12).** A face held past the last word reads
  as a frozen picture, even when the script says "hold". End lines on a clean cut, and keep no
  wordless stretch over ~0.7 s in a shot. review.py C16 checks it.
- **Shorts: `skills/shorts/`** (2026-10-14): one `short.json` per Short in `<edit>/shorts/<name>/`;
  rebuilt from the parent's sources (never a crop of the final), strongest line first, a 3 s thumbnail-style
  plate, the parent's cards and bed (review G4 checks the cards; M053). Episode 4's three are the examples;
  Episodes 2-3 and podcast Episode 1 (two speakers: `"who": "left"|"right"`) followed (2026-10-15). Run `edges` on Hinglish.
- **The youtube-agent plugin does the writing side** (`/youtube-agent:yt-shorts` picks Shorts, `hookscore.py`
  ranks hooks, `title.py` lints a title against its plate): use it instead of re-deriving. Map in environment.md.
- **Captions are Hinglish as spoken**, Devanagari for Hindi, in Kohinoor Devanagari (M047),
  whatever a script says. **Shorts are the exception: English** (Shoaib, 2026-10-14).
- **Verify a cut by transcribing each side ALONE** (M048): a joined transcription fills clipped
  words back in.
- Run helpers as `uv run python helpers/<name>.py` — there are no console scripts.
- `pytest` is not a declared dep: `uv run --with pytest python -m pytest tests/`.
- **`main` is the working branch** and this fork's copy of the tool — and now the only one.
  `pr/*` branches alone are based on upstream `main`, for the open PRs.
- Three ASR providers wired up: Deepgram (default, diarizes), whisper.cpp (free, local, no
  diarization), ElevenLabs (unconfigured). Each has a different flaw — see [gotchas.md](gotchas.md).
- Paid transcription is cached per source. Never re-transcribe unnecessarily; iterate with whisper.
- All three animation engines installed: Manim, HyperFrames, Remotion.
- **Motion-graphics pass on a locked cut: `skills/motion-graphics-pass/`** (added 2026-10-13 from Episode 2's
  `final_mgx.mp4`). `mgx.py <edit> words|frames|still|render|layers|sfx|compose|mux|verify`; outputs in
  `<edit>/mgx/`. Caption swaps are patches from `base.mp4`. Its `sfx` step prints per-effect audibility (M052).
- **Sound sourcing (Shoaib, 2026-10-13): the apt sound, always.** Local library first (`mgx.py <edit> library <terms>`), then the
  Epidemic Sound connector (`…Epidemic_Sound__SearchSoundEffects` / `SearchRecordings` → `Download*` → `mgx.py fetch`, which files
  it in `effects/epidemic/` or `music/epidemic/` with an id sidecar). Procedure: `skills/motion-graphics-pass/references/sourcing-audio.md`.
- **Glass cards are the house look for structured beats** (lists, schedules, figures): a `cards`
  block in the EDL, word-anchored, rendered by HyperFrames and composited by render.py. Guide in
  `SKILL.md` "Glass cards"; read `cards.py <edl> --clips …` output before rendering. **Anchor on
  2-4 word phrases** — search runs forward, so a lone common word lands on its NEXT occurrence.
- Piping to `tail` masks exit codes. Use `set -o pipefail`. It also **hides the whole head of
  the output** — a `| tail -30` on a self-eval report silently dropped its pops section.
- **Never wait on a job with `pgrep -f "script.py"`** — `-f` matches full command lines, so the
  waiting shell matches *itself* and hangs forever after the job finishes. Wait on a marker the
  job prints, or on the output file. Cost ~10 idle minutes on an already-finished 4K render.
- Default shell is zsh — it does **not** word-split unquoted `$var`, and it reads `$var:x`
  as a history modifier. Brace **any** variable followed by `:`, not just in ffmpeg filter
  strings: `git show "${b}:path/file"` silently returns nothing without the braces (zsh applies
  `:h`/`:helpers…` as a modifier), which reads as "the feature is absent" rather than an error.
- **Never name a zsh variable `path`** — it is tied to `$PATH` and a loop over it wipes out
  command lookup, which reads as a broken environment. See gotchas.md.

## Maintaining this KB

At the end of a task, append to [worklog.md](worklog.md) and fold any durable, reusable
lesson into the right topic file. **Script-stage lessons** (idea, packaging, opening, structure) also
go into the private channel-kb's `08-script-playbook.md`, which is where scripts are written. Rules: record only what was **verified**, note how it was
verified, and keep this index short — it loads into every session.
