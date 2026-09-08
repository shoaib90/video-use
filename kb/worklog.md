# Worklog

Newest first. Records local divergence from upstream and *why*, so a future session doesn't
re-derive it or mistake a deliberate change for a bug.

---

## 2026-09-08 — Addressed review on all three PRs

Automated review raised 7 findings across #158/#159/#160. **All 7 were valid** — none were
false positives, which is worth remembering before dismissing review output.

The substantive one was the scaled-dimension prediction (see gotchas.md): my arithmetic matched
ffmpeg on every case I tested, and was still the wrong approach. Fixed by measuring rather than
predicting. The other serious one was the shared transcript cache crossing providers, which meant
the Deepgram helper could return Scribe's transcript and never call Deepgram.

Smaller: `--height` accepted odd/negative values; `--crf 16.5` is valid for x264 but crashed
`main()` *after* extraction had already run; an unrecognised `subtitle_style.case` silently
emitted raw ASR capitalization; and `--language` omitted promised auto-detection without sending
`detect_language`. While fixing that last one I found Deepgram reports the detected language on
`results.channels[0].detected_language`, not `results.language` or `metadata.language` where the
code was looking — so `language_code` was null even once detection was on.

Fixes were replayed onto `local` too, and the same cache bug was ported to
`transcribe_whisper.py`, which matters for the upcoming multi-clip job: running whisper against
an edit dir that already holds Deepgram transcripts would otherwise have silently returned the
Deepgram files.

**Two process notes.** Cherry-picking the fixes onto `local` was the wrong instinct — `local`'s
`render.py` contains both change-sets combined, so the picks conflicted; replaying the edits was
cleaner. And a `git checkout local` silently *failed* (untracked `uv.lock` blocking it) while the
following cherry-picks ran on the branch I thought I had left. Always confirm the branch actually
changed before acting on it.

---

## 2026-09-07 — Forked and opened three upstream PRs

User authorised pushing to GitHub. Forked to `shoaib90/video-use`, pushed `local` as a backup
(it existed only on this disk until now), and opened PRs #158/#159/#160. Details in
[environment.md](environment.md).

**Method worth reusing.** Each PR branch was built from clean `main` and the changes *replayed*
onto it, rather than cherry-picked out of `local`'s bundled commits. `local`'s commits mix
render.py changes with `kb/` updates, and `build_final_composite`/`main()` are touched by two
different concerns, so hunk-level splitting would have produced fragile branches. Replaying from
main gave three self-contained branches, each verified independently: tests pass, `--help`
parses, and `git diff --name-only main..<branch>` shows no `kb/`, `CLAUDE.md` or `uv.lock`.

**Backward compatibility was proved, not asserted.** For the subtitle PR, the generated SRT is
byte-identical to main's implementation on the same transcript and EDL when no `subtitle_style`
is present — checked by running both versions and `diff`ing. That claim is now in the PR body,
which is much stronger than "should be compatible".

Gotcha: switching off a `pr/*` branch failed because `uv.lock` is tracked on `local` but
untracked elsewhere. `rm uv.lock` before checkout.

---

## 2026-09-07 (later) — Quality controls; user reported the output looked compressed

They were right, and the cause was structural rather than just "it's a preview": render.py
encodes the video twice and upstream hardcoded both CRFs plus a 1080p downscale, so a 4K source
had no path to a high-quality delivery. Full write-up in gotchas.md.

Added `--height` and `--crf`, moved the final default to CRF 16 / `slow`, and derived the
composite CRF as `gen1 - 2`. Re-rendered the same EDL at 2160p CRF 16: 0.451 bits/px versus
0.255 before, and a face-detail crop comparison shows clearly more beard/eyebrow detail.
960 MB for 85s though — CRF 18–20 at 2160p is the sensible default; CRF 16 is a master.

Also replaced the per-segment raw `filter` push-in with a numeric `zoom`, because the hardcoded
crop values were 1080p-only and would silently break at any other height. Relative ffmpeg
expressions can't fix it (rounding stops the crop round-tripping to exact dimensions, which
breaks the concat), so `probe_scaled_dims()` now mirrors the scale expression and the crop is
computed from that.

**Measured for planning a 12-clip batch:** ~0.74 KB of packed transcript per minute of footage,
so ~55 min of source is ~41 KB ≈ 10.5K tokens — an hour of footage fits in context comfortably.
Transcription is ~70s for that hour; **rendering is the bottleneck**, at ~15 min for one 85s 4K
output. Iterate on 720p drafts, render 4K once.

---

## 2026-09-07 — First real edit: "Weekend Rides" ep.1

First actual footage. `IMG_3156.MOV`, 3:00 iPhone 4K of the user driving and introducing a
weekend-drive vlog series. Cut to 85.5s. Full decision record lives with the footage at
`~/Downloads/edit/project.md`; only the reusable lessons are here.

**What the analysis found that mattered:** the source held *two* intro attempts — 0–75s at 28%
speech density (a false start with four silences over 6s) and 75–180s at 78%. Recognising that
split was the whole edit. Quantifying density per region, rather than reading the transcript
top to bottom, is what surfaced it.

**Provider cross-check earned its keep.** Deepgram misheard the user's name and the opening
line; whisper got both right. Running the free local pass alongside the paid one is now the
default move on any first transcription — it costs nothing and it caught two errors that would
have been burned into captions. Where both engines agreed on something nonsensical
("digital area" for "digital diary"), asking the user was the only correct move.

**Extended `render.py`** with three optional EDL fields — `ranges[].filter`,
`audio_filter`, and `subtitle_style` — needed for per-segment push-in, pre-fade denoise, and
sentence-case captions. Documented in helpers.md. Also taught the SRT builder to capitalize a
cue that opens the file or follows sentence-final punctuation, since a cut can promote a
mid-sentence word to sentence start.

**Self-eval was worth doing properly.** A numeric sample-step check across all 12 boundaries
beat eyeballing waveform PNGs for pop detection, and is now the preferred method — see below.
The visual pass still matters for captions, grade and framing.

**A verification actually changed a decision.** The plan called for trimming a 1.69s hesitation
in the opening line; `timeline_view` showed no clean silence inside the word span, so the cut
would have risked clipping a word to save 0.75s. Kept it. That is the drill-down doing its job
rather than rubber-stamping the plan.

**New traps recorded in gotchas.md:** `--draft` at 720p breaks 1080p-sized EDL filters; iPhone
MOVs carry a spatial audio track that ffmpeg's defaults prefer, HLG HDR, *and* rotation
metadata; isolating a snippet makes ASR worse; zsh does not word-split unquoted expansions.

## 2026-09-03 (later) — Fully equipped: animation engines + local ASR

User asked to install everything needed so no capability is missing mid-edit.

**All three animation engines installed and verified.** Manim 0.21.0 (rendered a real test
scene, not just imported) — it needed `brew install pkgconf cairo pango cmake` plus an exported
`PKG_CONFIG_PATH` or `pycairo` fails to build. HyperFrames v0.8.27 (npx cache warmed).
Remotion 4.0.520 confirmed reachable; it scaffolds per-slot so nothing to pre-install.

Caught a self-inflicted trap doing this: the first `uv sync --extra animations` reported exit 0
while actually failing, because I piped it to `tail`. Recorded in gotchas.md — it applies to
every ffmpeg shell-out in this repo too.

**Added a third ASR provider: `helpers/transcribe_whisper.py`** (local whisper.cpp, free,
offline, no key). Discovered `ffmpeg-full` pulls in `whisper-cpp` 1.9.2, so the binary was
already present — only models needed downloading. Probed the plumbing for free using the
bundled `for-tests-ggml-tiny.bin` before committing to a 465MB download.

**Measured all three providers against known ground truth** rather than assuming — see the
comparison table in gotchas.md. Each has a distinct flaw: Deepgram drops a leading filler,
whisper normalizes numbers, `base.en` makes outright word errors. This changed a decision:
`small.en` is now the helper's default, and the earlier "Deepgram drops fillers" note was
rewritten from speculation into a measured finding with the caveat that it's still one synthetic
clip.

**Not installed:** nothing outstanding. `ELEVENLABS_API_KEY` remains unset — that's a
credential, not an install, so audio-event tagging still needs the user.

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
