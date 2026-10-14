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

## Before any preview reaches Shoaib (every video, every iteration)

Shoaib's time is the scarcest resource. A preview he has to rewatch end to end to find our
mistakes is a failed delivery. So:

1. **Run `helpers/review.py`** on the render (see kb/helpers.md). Clear every HIGH flag: fix it,
   or record why it is fine in `<edit>/review/accepted.json`. Read the MED story edges too.
2. **Walk the READ items in [kb/mistakes.md](kb/mistakes.md)**, the ledger of every mistake
   Shoaib has caught on any video.
3. **Deliver the watch-list, not just the file.** When there is a previous version, deliver the
   changes reel (`review/<label>/reel.mp4`): only what changed, ~14 s each. He should not need
   to rewatch the whole video.
4. **When Shoaib reports a mistake, add it to kb/mistakes.md the same day.** If it can be
   checked automatically, add the check to review.py in the same change, with a test, so it
   can never reach him twice.

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

## Shorts

When asked to make Shorts (or "clips", "verticals") from a video:

1. **Read `~/Documents/GitHub/channel-kb/03-formats/shorts.md` first.** It holds the channel's
   rules: Shorts are only cut from long videos, how to pick a moment, the zenith rule, cadence,
   and how they are judged. If that file is missing, ask Shoaib before picking any moment.
2. **For a new episode, use the `[SHORT]` passages marked in its channel-kb script.** For a video
   already shot, propose candidates from the transcript (the `/yt-shorts` skill helps) and
   confirm them with Shoaib before cutting (Hard Rule 11 applies to Shorts too).
3. **Craft and crop rules live here:** `kb/shooting.md` ("Framing for Shorts"), plus anything
   learned while cutting them, recorded in `kb/` as usual.
4. Output goes to `<videos_dir>/edit/shorts/`, like any other session output.

channel-kb is private and this repo is public: read it, but never copy its text, story details
or episode content into this repo.

## Git

**`main` is the working branch and this fork's copy of the tool.** It is not an upstream
mirror — this fork exists to carry our own changes, and upstream is not being tracked.

There is no `local` branch — it drifted 16 commits behind `main` while pretending to be a
synonym, and was deleted on 2026-09-20. `main` is the only branch to work on.

The `pr/*` branches are the exception: each is built from **upstream** `main`
(`origin/main`) so the open PRs to browser-use/video-use stay focused and free of local-only
files (`kb/`, `CLAUDE.md`, `uv.lock`). One branch per base — never reuse a `pr/*` branch for a
PR against this fork, or rebasing it corrupts the upstream one. See `kb/gotchas.md`.
