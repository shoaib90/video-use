# Setting up on another machine

macOS. Gets a second laptop to the exact state in [environment.md](environment.md).

```bash
git clone git@github.com:shoaib90/video-use.git ~/Documents/Github/video-use
cd ~/Documents/Github/video-use
bash kb/bootstrap.sh
```

**Clone it anywhere** — the path is not baked in. `bootstrap.sh` resolves the repo from its own
location and points the skill symlink at wherever you cloned, so `~/Documents/Github/video-use`,
`~/Developer/video-use` or anything else works. No branch checkout is needed: `main` is the
default and carries everything.

If HTTPS is easier than SSH on that machine, swap the URL for
`https://github.com/shoaib90/video-use.git`.

The script is idempotent, so re-run it any time to repair a machine. It ends by running
[check-env.sh](check-env.sh), so a green run means the machine really is ready.

## Which branch

**`main`.** It is this fork's copy of the tool and carries everything — helpers, `kb/`,
`CLAUDE.md`, tests, `uv.lock`. `local` points at the same commit and is kept only as a synonym.

This fork is not an upstream mirror and upstream is not tracked; the fork exists to carry our own
changes. The `pr/*` branches are the only ones based on upstream `main`, and they exist solely to
keep the open PRs to browser-use/video-use focused — do not clone those.

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
cd /path/to/your/clone          # e.g. ~/Documents/Github/video-use
printf 'DEEPGRAM_API_KEY=%s\n' 'YOUR_KEY' > .env && chmod 600 .env
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
