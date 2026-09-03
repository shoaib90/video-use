# video-use

Conversation-driven video editor. Upstream: [browser-use/video-use](https://github.com/browser-use/video-use).
`SKILL.md` is the authoritative editing guide; `helpers/` holds the scripts.

## Knowledge base

@kb/index.md

`kb/` is the maintained knowledge base for how this repo actually behaves on this machine —
architecture, the transcript data contract, helper reference, environment state, verified
gotchas, and a worklog of local changes.

**Read `kb/index.md` at the start of every task here**, and follow its pointers into the topic
files as needed. Do not re-derive things it already records.

**At the end of a task, update it.** Append what happened to `kb/worklog.md`, and fold any
durable, reusable lesson into the topic file where it belongs — a new trap into
`kb/gotchas.md`, a version or path change into `kb/environment.md`, and so on. Rules:

- Record only what was **verified**, and say how it was verified.
- Distinguish confirmed findings from unproven suspicions. Mark the latter clearly.
- Keep `kb/index.md` short — it loads into every session.
- Correct or delete entries that turn out to be wrong rather than stacking caveats.

## Working rules

- Run helpers as `uv run python helpers/<name>.py`. There are no console scripts.
- **All session output goes to `<videos_dir>/edit/`** — never write inside this repo (Hard Rule 12).
  Scratch and test artifacts belong in the session scratchpad.
- Transcription is **paid per call** and cached per source. Never re-transcribe unless the
  source file itself changed. Don't transcribe as install verification.
- Secrets live only in `.env` at the repo root (mode 600, gitignored). Never echo key values
  into tool output.
- Confirm the plain-English edit strategy with the user **before** touching the cut (Hard Rule 11).
- Parallel animation sub-agents need the `Agent` tool; the user asked that it not be used
  unless they request it, so ask first.

## Git

Local changes live on branch `local`. `main` tracks upstream and stays clean so
`git pull --ff-only` keeps working — rebase `local` onto `main` after pulling.
