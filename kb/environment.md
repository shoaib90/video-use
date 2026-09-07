# Environment — this machine

macOS (darwin 25.6.0), Apple Silicon. Last verified **2026-09-03**.
Re-verify with `bash kb/check-env.sh`.

## Paths

| What | Where |
|---|---|
| Repo / skill | `/Users/fbin-blr-0134/Documents/video-use` |
| Skill registration | `~/.claude/skills/video-use` → symlink to the above |
| Python env | `.venv/` at repo root (uv-managed) |
| Secrets | `.env` at repo root, mode `600`, gitignored |

Registration uses the same symlink pattern as the other skills in `~/.claude/skills/`.
The **whole directory** is symlinked, not just `SKILL.md` — `helpers/` must sit beside it.

## Versions

| Tool | Version | Notes |
|---|---|---|
| ffmpeg / ffprobe | **9.0.1** (`ffmpeg-full`) | libass present ⇒ subtitles work |
| Python | 3.12.13 (uv-managed) | system python3 is 3.9, too old for this repo |
| uv | 0.12.2 | |
| Node | v24.9.0 | satisfies HyperFrames' Node 22+ requirement |
| yt-dlp | 2026.08.19 | for URL sources |

### The ffmpeg situation — important

Two formulae are installed. `ffmpeg` (8.1.2, slim, **no libass**) is **unlinked**;
`ffmpeg-full` (9.0.1, keg-only, **has libass**) is force-linked so it owns `$PATH`:

```bash
brew unlink ffmpeg && brew link --force ffmpeg-full
```

Revert with `brew unlink ffmpeg-full && brew link ffmpeg`. Do not "fix" the unlinked
`ffmpeg` — the unlink is deliberate. See [gotchas.md](gotchas.md) for why.

A `brew upgrade` may relink the slim `ffmpeg` and silently break subtitle burn-in. If
captions start failing, re-check `ffmpeg -filters | grep subtitles` first.

## Git / upstream

| Remote | URL |
|---|---|
| `origin` | `browser-use/video-use` (upstream, read-only in practice) |
| `fork` | `git@github.com:shoaib90/video-use.git` |

Branches:

- **`local`** — the working branch. Carries everything, including `kb/` and `CLAUDE.md`.
  Backed up to `fork/local`. **This is the branch to work on.**
- **`main`** — tracks upstream, kept clean so `git pull --ff-only` works. Rebase `local` onto it after pulling.
- **`pr/*`** — one focused branch per upstream PR, each built from clean `main` so no local-only
  file can leak. Verified with `git diff --name-only main..<branch> | grep -E '^(kb/|CLAUDE.md|uv.lock)'`.

Open upstream PRs (2026-09-07):

| PR | Branch | Contents |
|---|---|---|
| [#158](https://github.com/browser-use/video-use/pull/158) | `pr/output-quality` | `--height`, `--crf`, derived gen-2 CRF, numeric `zoom`, `audio_filter` |
| [#159](https://github.com/browser-use/video-use/pull/159) | `pr/configurable-subtitles` | `subtitle_style` (chunking/case/force_style) + sentence-case fix |
| [#160](https://github.com/browser-use/video-use/pull/160) | `pr/deepgram-transcriber` | `transcribe_deepgram.py` |

**Held back deliberately:** `transcribe_whisper.py`. `SKILL.md`'s anti-patterns list names
"running Whisper locally" explicitly, so upstream is unlikely to want it. Ours runs on Metal in
~4s and serves as a free cross-check rather than the primary, which is a different proposition —
but it stays local unless upstream asks.

**Never upstream:** `kb/`, `CLAUDE.md`. Machine-specific.

#158 and #159 both touch `build_final_composite`'s signature and `main()`, so whichever merges
second needs a trivial rebase.

## Credentials

| Key | Status | Used by |
|---|---|---|
| `DEEPGRAM_API_KEY` | **set**, validated (HTTP 200) | `transcribe_deepgram.py` |
| `ELEVENLABS_API_KEY` | **not set** | `transcribe.py` |

Consequence: transcription works, but **audio-event tagging is unavailable** —
no `(laughter)` / `(applause)` / `(sigh)` beat markers. Ask for an ElevenLabs key if a
project needs them.

Never echo key values into tool output. Never write a key anywhere but `.env` at the repo root.

## Animation engines — all three installed

| Engine | Status | Invoke |
|---|---|---|
| Manim | **0.21.0 installed**, render verified | `uv run manim -ql --format=mp4 scene.py Scene` |
| HyperFrames | **v0.8.27**, npx cache warmed | `npx --yes hyperframes ...` |
| Remotion | 4.0.520 reachable, scaffolded per-slot | `npx create-video@latest` |

Manim needed system libs that aren't obvious: `brew install pkgconf cairo pango cmake`, and
`PKG_CONFIG_PATH=/opt/homebrew/lib/pkgconfig` exported, or `pycairo` fails to build.
Repo vendors `skills/manim-video/` — read its SKILL.md before building a Manim slot.

Scaffold Remotion/HyperFrames **inside `<edit>/animations/slot_<id>/`**, never at the repo root.

## Local ASR models

`whisper-cpp` 1.9.2 (arrived with `ffmpeg-full`). Models in `~/.cache/whisper-models/`:

| Model | Size | Use |
|---|---|---|
| `ggml-small.en.bin` | 465 MB | **default** for `transcribe_whisper.py` |
| `ggml-base.en.bin` | 141 MB | faster, but makes word errors — see gotchas.md |

ffmpeg 9 also has a built-in `whisper` filter (`-h filter=whisper`), unused so far — the
`whisper-cli` path gives cleaner word-level JSON.

## Available beyond the CLI

This runs as the Claude Code **app**, a superset of the CLI the repo targets. Extra reach:
inline file delivery to the user, publishable HTML Artifacts (cut plans, before/after
breakdowns), a separate Remotion skill, Figma/Canva connectors for branded overlay assets,
and scheduled tasks. Parallel animation sub-agents (Hard Rule 10) work via the `Agent` tool —
but **the user asked that it not be used unless they request it**, so confirm before fanning out.
