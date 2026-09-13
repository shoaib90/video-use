# Worklog

Newest first. Records local divergence from upstream and *why*, so a future session doesn't
re-derive it or mistake a deliberate change for a bug.


---

## 2026-09-13 (later) — `main` is now the fork's copy of the tool

The fork is not tracking upstream — it exists to carry our own changes — so the "main mirrors
upstream, work on `local`" convention was ceremony with no payoff, and it had already gone wrong:
fork `main` sat 9 commits ahead of upstream (so `git pull --ff-only` was broken anyway) while
simultaneously *missing* the caption-offset fix, the `subtitle_style` balance fix,
`transcribe_whisper.py`, the `_language` cache fix and two test files.

Fast-forwarded `main` to `local` (clean FF, 26 commits, no merge commit — `main` had nothing
`local` lacked) and pushed. `main` and `local` now point at the same commit; **`main` is the
working branch**. `local` is retained as a synonym so older notes resolve, and can be deleted.

Updated every place that stated the old convention: `CLAUDE.md`, `kb/index.md`,
`kb/environment.md` (whose Git section had become self-contradictory, calling both branches "the
working branch") and `kb/new-machine.md` (which told a fresh clone to check out `local`, the
opposite of what is now right). The historical worklog entry from 2026-09-07 was **left alone** —
it was accurate when written, and a dated log should not be rewritten to match the present.

The `pr/*` branches are unaffected and still based on `origin/main`: they are the one place the
branch-per-base rule still applies, and all four upstream PRs remain open.

---

## 2026-09-13 — Second-machine setup made reproducible

User wants the same state on another laptop, where this session's Claude Code history does not
exist. Audited what is actually where first: **`local` is byte-identical to `fork/local`**, every
working branch is pushed, nothing uncommitted, no stashes — so all work is on the fork. The
fork's `main` is the incomplete one (only the three merged PRs; missing the caption-offset fix,
the `subtitle_style` balance fix, `transcribe_whisper.py`, the `_language` cache fix and two test
files), so a clone must check out **`local`**, not `main`.

Added [bootstrap.sh](bootstrap.sh) and [new-machine.md](new-machine.md). The script was **run on
this machine to prove it is idempotent** — it detected every existing component, changed nothing,
and finished green through `check-env.sh`.

Worth recording about the `local` vs `main` diff: it looks alarming at +4,747 lines, but 58% is
`uv.lock` and 29% is `kb/` + `CLAUDE.md`. Only ~600 lines are code and tests. Size of a diff is a
bad proxy for how much real change it carries.

**What does not travel, verified:** `.env` (gitignored at `.gitignore:2`; confirmed with
`git log --all -S<key>` that the key has never been committed on any branch), the ~600 MB whisper
models, ffmpeg-with-libass, the skill symlink, `.venv/`, and `~/.claude` session history. Footage
and `edit/` dirs live outside the repo — `edit/transcripts/` should be **copied, not
regenerated**, since transcription is paid per call and those JSONs carry hand corrections.

The session-history point is the one that matters conceptually: it does not need to travel,
because `kb/` was built so the knowledge lives in files the repo carries and `SKILL.md` points
at from any directory. The per-project auto-memory is deliberately a thin pointer at `kb/` rather
than a copy, so losing it loses nothing.

---

## 2026-09-08 (later) — YT1 Ep1: first scripted talking-head cut, 25 takes → 3:34

Full decision record with the footage at `~/Documents/Ambitious/Editing/YT1/edit/project.md`.
Different job shape from Detour-1: the shoot is **script-ordered**, one script beat per clip
with 1–4 takes each, so this was take selection and dead-air trimming, not finding a story.
Every good take end-to-end came to 3:34 — the delivery is much faster than the 7–8 min the
script assumes, so nothing had to be dropped to hit the 4–5 min target.

**Two render.py bugs found by self-eval, both fixed on `local`:**

1. **Rule 5 caption offsets summed EDL floats instead of measuring the rendered segments**, so
   captions drifted progressively early — 0.598s by the closing line on a 30-segment cut. This
   is invisible on a short EDL and always correct at the first cue, which is why it survived.
   `build_master_srt` now takes an optional `segment_paths` and probes them.
2. **`subtitle_style` could not express a documentary caption**: it broke on every comma with
   no minimum, producing cues like "I mean" and "now." Added `break_on`, `min_words` and
   `balance` (split each sentence into equal cues instead of greedily filling). Defaults are
   byte-identical — verified by diffing against a previously generated SRT — and 16 tests pass.

**Three of my own errors, all caught by verification rather than by eye:**

- Several OUT points were computed from a word's **start** rather than its **end**, chopping
  "Let's build it together" mid-word. A boundary-vs-word validator found 15 collisions at once;
  boundaries are now derived programmatically from word starts with computed padding.
- A filler trimmed out of the audio stayed in the caption, because caption words are selected
  by overlap (see gotchas.md).
- The b-roll overlay was placed from summed floats and landed 0.205s early.

The pattern behind all four: **summed float durations are not where things actually are.**
The existing "never predict another tool's rounding" entry was about `scale=-2`; this is the
same lesson in the time axis. Measure a real render, feed it back.

**Technique worth reusing.** A VO-over-b-roll section is a **full-frame opaque overlay** on top
of the talking-head base whose audio you want. It solved a real problem here: the speaker is
visibly holding his phone in both teaser takes, and the script wants that passage as VO anyway.
Set the overlay `duration` to exactly the span to cover but cut the clip longer — an under-run
silently exposes the base.

**Choosing music without being able to hear it.** Measured each bed's envelope in fifths and its
HF-vs-total energy, then matched: flattest/darkest under dialogue, the one that starts
near-silent and builds under the photo montage, the one that tapers at the end under the close
(using its *last* 61s so the natural resolve lands the ending). Verified afterwards that the bed
sits ~15 dB under speech, and that spot SFX actually landed — the bat hit measured +24.7 dB in a
dialogue gap. The keyboard SFX looked absent in broadband RMS (+0.4 dB) and I raised it 6.5 dB
before realising the measurement was wrong: in its own 3–9 kHz band it was already at +28 dB.
**Measure a sound in the band it occupies**, not broadband, or you will over-boost it.

**Also verified:** 0/29 audio pops; subtitles composite over the overlay in the real output;
end card truly silent (−180 dB) per the script's "no outro music"; draft/preview/final segment
durations are bit-identical, so a cheap `--draft` is a valid way to measure boundaries for a 4K
final. `warm_cinematic` was tested and rejected for already-moody lamp-lit footage — it crushes
shadows and drains skin; a lighter custom warm-punch won.

---

## 2026-09-08 — Detour-1: 14 clips into one 4:26 journey; the Hinglish lesson

First multi-clip edit. Full decision record with the footage at
`~/Documents/Ambitious/Editing/Detour-1/edit/project.md`; the reusable lessons are in
gotchas.md.

**The lesson that matters:** I transcribed 14 clips with `--language en`. The speaker was
speaking Hinglish. The ASR returned confident English nonsense rather than failing, I planned an
entire cut from it, and only found out because the user corrected three lines I had flagged as
garbled — and wrote his corrections in Hindi. Re-transcribing with `multi` recovered +37% more
words and revealed a rain thread spanning five clips that the first plan had no idea existed.
The cut went 3:05 → 4:26 and its ending changed completely.

Generalisable: when the transcript *is* the reasoning surface, a language mismatch is not a
caption bug, it is a corrupted analysis. Verify the language on clip one, not clip fourteen.

**Also caught by looking at frames rather than metadata:** one clip of fourteen had `rotation=+90`
where the rest had `-90`, so it rendered upside down while every dimension check passed. And the
arrival payoff was shot in portrait, which `render.py` scales to different output dimensions than
landscape — that silently breaks the `-c copy` concat, so those clips were pre-rendered to
pillarboxed 3840×2160 under their original source names to keep caption lookup working.

**Worked well:** per-segment `auto` grade across 90 minutes of falling light (the dark arrival got
a gamma lift the daylight clips did not) — the opposite call from the single-clip edit, for the
right reason. The numeric pop check scaled fine to 58 boundaries, all clean. And the
resolution-independent `zoom` meant the 720p draft and 2160p final shared one EDL, which the
earlier hardcoded crops would have made impossible.

---

## 2026-09-08 (later) — Resolved fork PR #2's conflicts

#1 had been merged into the fork's `main`, which conflicted #2 exactly where predicted: both
change-sets touch `build_final_composite`'s signature and `main()`. All three conflicts were
additive, so the resolution kept both sides rather than choosing one.

**The mistake worth remembering:** rebasing the shared head branch fixed the fork PR and quietly
corrupted upstream #159, which reuses that branch against a base without #1 — it went from
+82/-9 to +295/-21 and absorbed a merge commit. `mergeable` still reported MERGEABLE, so nothing
flagged it. Fixed by splitting one branch per base (`pr/*` on upstream `main`, `merge/*` on fork
`main`), keeping the original branch for the upstream PR so its review threads survive; fork #2
was closed and replaced by #4. Written up in gotchas.md.

**A verification that correctly found nothing.** The combined render put a lowercase caption
("it is to maintain") at a cut, which looked like the sentence-case fix regressing. It was my
test EDL: I had cut mid-sentence at an arbitrary 82.0s, so the preceding cue ended without
punctuation and the following one genuinely reads as a continuation. The real edit capitalizes it
correctly (previous cue ends "happened.") while keeping "past week" lowercase where the cut is a
deliberate mid-sentence trim. Left the rule alone — "fixing" it would have broken the second case.

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
