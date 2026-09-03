# Worklog

Newest first. Records local divergence from upstream and *why*, so a future session doesn't
re-derive it or mistake a deliberate change for a bug.

---

## 2026-09-03 — Initial setup, Deepgram provider, ffmpeg fix

**Install.** Cloned upstream into `~/Documents/video-use` (not the `~/Developer/video-use` that
`install.md` suggests — the user had already created this directory). `uv sync` → 27 packages.
Symlinked the whole repo into `~/.claude/skills/video-use`, matching the pattern already used
there by `browser-automation` and `game-development`. The skill registered and became visible
mid-session, so the Claude Code *app* discovers skills the same way the CLI does — nothing in
this repo is CLI-specific.

**Verified rather than assumed.** 16/16 tests pass. All six helpers load. Built a synthetic 12s
clip, cut it into three segments via a real EDL, rendered it: per-segment extract → auto-grade
→ lossless concat → two-pass loudnorm all worked, output 7.53s vs 7.50s expected (frame
quantization). Ran `timeline_view` on the *rendered* output and read the PNG: the cut landed at
the EDL boundary and the waveform showed a clean 30ms fade V-notch — so the self-eval loop
genuinely closes, which is the load-bearing assumption of the whole design.

**Added Deepgram as an ASR provider** (`helpers/transcribe_deepgram.py`, new file).
Motivation: user preferred Deepgram over ElevenLabs. This turned out to be an adapter, not a
rewrite — see [data-contract.md](data-contract.md) for why the seam is only five fields wide.
Verified in two stages: a hand-built fixture pushed through the *real* downstream consumers
(`pack_transcripts.py` produced correct S0/S1 phrase grouping; `render.py --build-subtitles`
produced `master.srt` with correct Hard Rule 5 offsets — cue at 3.780s = 6.08 − 5.00 + 2.70),
then a live `nova-3` call on macOS-`say` speech (16 words, 1.9s, auth and params accepted).
Found one issue: a leading filler was dropped — see [gotchas.md](gotchas.md).

**Edited `SKILL.md`** to document both providers in Setup + Helpers, so a future session reading
the skill discovers `transcribe_deepgram.py` instead of reaching for `transcribe.py` by default.

**Fixed subtitle rendering.** Diagnosed ffmpeg exit 234 on subtitle burn-in as a missing libass
in Homebrew's slim `ffmpeg` formula — not a transcription or quoting problem. Installed
`ffmpeg-full` (which carries libass) and linked it ahead of the slim build. Also installed
`yt-dlp` (upstream-optional, for URL sources).

**Created this KB** at the user's request, wired into `CLAUDE.md` via an `@kb/index.md` import.
Then caught a gap: `CLAUDE.md` only loads when the working directory is *this repo*, but real
editing happens in the user's footage folder, where it never loads. `SKILL.md` loads from any
cwd via the skill symlink, so the KB pointer went there too. That's the load-bearing one.
Added `kb/check-env.sh` to re-verify every environment claim in one command.

**Git layout.** Local work sits on branch `local`; `main` is kept clean so `git pull --ff-only`
against upstream keeps working. Rebase `local` onto `main` after pulling.

**Still open:** no real footage edited yet. `ELEVENLABS_API_KEY` is unset (only Deepgram is
configured), so audio-event tagging is unavailable. The dropped-leading-filler behaviour needs
re-checking against real human speech.
