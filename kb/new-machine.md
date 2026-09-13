# Setting up on another machine

macOS. Gets a second laptop to the exact state in [environment.md](environment.md).

```bash
git clone git@github.com:shoaib90/video-use.git ~/Documents/video-use
cd ~/Documents/video-use
git checkout local          # NOT main — see "which branch" below
bash kb/bootstrap.sh
```

The script is idempotent, so re-run it any time to repair a machine. It ends by running
[check-env.sh](check-env.sh), so a green run means the machine really is ready.

## Which branch

**`local`.** That is the working branch and the one the skill runs from.

`main` on the fork has only the first three merged PRs — it is missing the caption-offset fix,
the `subtitle_style` balance fix, `transcribe_whisper.py`, the `_language` cache fix, and two
test files. Cloning `main` gets you a materially older tool.

Optionally add upstream for pulls: `git remote add origin https://github.com/browser-use/video-use.git`

## What does NOT travel with the clone, and why

| Thing | Why it's missing | Handled by |
|---|---|---|
| `.env` (`DEEPGRAM_API_KEY`) | gitignored — secrets never belong in a repo | **you, by hand** |
| whisper models (~600 MB) | too large for git | bootstrap step 5 |
| ffmpeg **with libass** | Homebrew's `ffmpeg` formula has no libass | bootstrap step 1 |
| skill symlink | machine-local path | bootstrap step 7 |
| `.venv/` | platform-specific | bootstrap step 4 (`uv.lock` is committed, so versions match exactly) |
| Claude Code session history | lives in `~/.claude`, not the repo | **nothing — and that's fine, see below** |
| Footage + `edit/` dirs | live beside the video files | **you, if you want them** |

### The API key

The only genuinely manual step. Copy `.env` from the first machine, or issue a new key:

```bash
printf 'DEEPGRAM_API_KEY=%s\n' 'YOUR_KEY' > ~/Documents/video-use/.env
chmod 600 ~/Documents/video-use/.env
```

Never commit it. `.env` is gitignored at line 2 — verify with `git check-ignore -v .env`.

### Session history does not matter

This is the reason `kb/` exists. Everything learned lives in **files in the repo**, not in a
Claude Code conversation: the transcript data contract, every verified gotcha, the environment
spec, and a dated worklog. `CLAUDE.md` and `SKILL.md` both point at `kb/index.md`, and `SKILL.md`
is what loads when the skill is invoked from *any* directory — so a fresh session on a new
laptop, with no history at all, reads the same knowledge this one has.

What is genuinely lost is Claude's per-project auto-memory under
`~/.claude/projects/…/memory/`. That is deliberately a thin pointer at `kb/` rather than a copy
of it, precisely so it can be lost without losing anything.

### Footage and transcripts — copy these, don't regenerate

Project outputs live in `<videos_dir>/edit/`, never in this repo (Hard Rule 12). If you want an
existing project on the new machine, copy the whole folder — **`edit/transcripts/` especially,
because transcription is paid per call.** Re-transcribing an hour of footage costs real money and
re-does work, and any hand corrections in those JSONs would be lost. `edit/project.md` carries
the reasoning behind each cut.

```bash
rsync -av ~/Documents/Ambitious/Editing/Detour-1/ newmachine:~/Documents/Ambitious/Editing/Detour-1/
```

The big intermediates (`clips_graded/`, `base*.mp4`, `*.prenorm.mp4`) are regenerable — skip them
if space matters. `edl.json`, `transcripts/`, `project.md` and `prepped/` are the ones worth moving.

## Verifying the two machines match

```bash
bash kb/check-env.sh          # both should report the same versions and all-green
git log --oneline -1          # same commit
uv run --with pytest python -m pytest tests/ -q
```

`uv.lock` is committed, so Python dependency versions are identical by construction. Homebrew
versions can drift between machines — `check-env.sh` prints them so a mismatch is visible.
