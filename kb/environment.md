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

## Credentials

| Key | Status | Used by |
|---|---|---|
| `DEEPGRAM_API_KEY` | **set**, validated (HTTP 200) | `transcribe_deepgram.py` |
| `ELEVENLABS_API_KEY` | **not set** | `transcribe.py` |

Consequence: transcription works, but **audio-event tagging is unavailable** —
no `(laughter)` / `(applause)` / `(sigh)` beat markers. Ask for an ElevenLabs key if a
project needs them.

Never echo key values into tool output. Never write a key anywhere but `.env` at the repo root.

## Optional / lazy deps

Installed on first actual use, not during setup:

- **Manim** — `uv sync --extra animations`. Repo vendors `skills/manim-video/` (read its SKILL.md).
- **HyperFrames** — `npx --yes hyperframes ...` inside the animation slot dir.
- **Remotion** — `npx create-video@latest`, or install project-local inside the slot.

Install these **inside `<edit>/animations/slot_<id>/`**, never at the repo root.

## Available beyond the CLI

This runs as the Claude Code **app**, a superset of the CLI the repo targets. Extra reach:
inline file delivery to the user, publishable HTML Artifacts (cut plans, before/after
breakdowns), a separate Remotion skill, Figma/Canva connectors for branded overlay assets,
and scheduled tasks. Parallel animation sub-agents (Hard Rule 10) work via the `Agent` tool —
but **the user asked that it not be used unless they request it**, so confirm before fanning out.
