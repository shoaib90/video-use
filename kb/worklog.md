# Worklog

Newest first. Records local divergence from upstream and *why*, so a future session doesn't
re-derive it or mistake a deliberate change for a bug.


---

## 2026-09-20 (later) — evaluated two reference repos, took three things

User supplied two repos and asked how much was usable.

**balarabetahir/-Build-AI-Motion-Graphics-with-Claude-and-Remotion** — a README and its PDF
export, no source. A tutorial describing lower-thirds, title cards and animated diagrams in
Remotion. Nothing to take as code, and in two places its approach is the weaker one: a
hand-written theme file where ours is derived from the delivered grade, and `<Sequence
from={90}>` frame offsets where ours anchor to spoken words. Hardcoded offsets are exactly what
rotted when the Detour-1 repairs moved every boundary ~9 s. Remotion itself was NOT adopted: it
needs Node plus a headless Chrome render per frame, where the PIL -> ProRes path does 322 4K
frames in seconds and is already wired into anchoring, brand, matte and demotion. SKILL.md
already lists it for bespoke one-off slots, which is the right place for it.

**nexu-io/open-design** (Apache-2.0, 443 MB Electron app) — `apps/`, `packages/`, `shells/`
are the product and irrelevant. Useful: `craft/` (13 well-sourced design docs), 165 skills
(mostly web/deck), 154 `DESIGN.md` brand systems.

The important caveat, now in gotchas.md: **`craft/` is about UI motion, where the user is
waiting.** Its 150 ms default and sub-500 ms ceiling are wrong for graphics synced to speech,
and `motion.WEIGHTS` is deliberately 2-4x slower.

**Taken:**

- **Curve for opacity, spring for transforms.** This found a real defect: `hero` used a spring
  for alpha too, peaking at 1.205 — clamped to 255, then dipping to 96% before settling, so
  every hero element pulsed as it arrived. `Weight` now carries `alpha_curve`; transform
  overshoot is the point, alpha overshoot is a bug.
- **Accent capped** at ~2 visible uses per frame; a list with a heading and an accented last
  item yields the heading to muted.
- **Tversky 2002** as the citation behind the restraint rule we had already derived empirically
  from the reference edit.

**Built:** `node_diagram` — nodes appearing in sequence with connections drawing themselves,
the one genuine gap both repos pointed at (the tutorial builds one; the reference video uses
one for basic -> intermediate -> advanced). An edge waits for BOTH endpoints, because a line
arriving at nothing reads as a glitch; cards are clamped inside the canvas, the same failure
class as unfitted type.

Suite 150 -> 159.

---

## 2026-09-20 — a motion graphics system, built from two reference videos

User called the first graphics attempt "very basic" and pointed at two YouTube videos, then
downloaded them locally. Both were analysed properly: the 35 s showreel sampled at 1.4 fps for
vocabulary, the 11:44 tutorial transcribed AND read frame-by-frame *against its own script* to
recover the mapping from spoken line to graphic.

That mapping is the valuable artefact and is now in `SKILL.md`. The tutorial's framework —
design first, then timing / weight / rhythm / intention — named exactly what was wrong with the
first attempt: one curve, one duration, one colour, everywhere.

**Built, in dependency order:**

- `helpers/script_scan.py` — the decision layer. Reads transcripts, reports where a graphic
  earns its place with confidence and evidence. Validated against the reference, where the
  ground truth is known: it independently rediscovered essentially every graphic decision that
  edit made. On the user's own scripts it found `"Thirteen years"` (the YT1 hook, and its
  thumbnail) and Detour-1's `"two parts of your brain"` / `"three parts"`, with no noise.
- `helpers/motion.py` — curves (spring, back_out, anticipate), per-role `WEIGHTS`, stagger with
  acceleration bias, sub-frame motion blur, ProRes 4444 sequence rendering + alpha verifier.
- `helpers/brand.py` — `derive()` measures a palette off delivered work. YT1: `#0A0A0A` /
  `#DED3BD` / accent `#F25435` / cool `#3554F2`, which matches the thumbnail's own device.
- `helpers/components.py` — `big_number`, `opposing_chips`, `staggered_items`, `kinetic_type`,
  `sliding_carousel`.
- `demotions` in the EDL + `build_demotion_filter` in render.py — speaker demotion.

**Findings worth the KB** (all in gotchas.md): grouping a script on silence fails on already-
edited footage (11 groups for 2267 words); a figure detector without a salience model buries the
real hits 5:1; `pad` evaluates x/y once so it cannot place a shrinking picture; PIL's ImageDraw
replaces rather than blends, which made a correct component look broken in preview; component
timing must be absolute or a late component silently draws nothing; unfitted type is clipped by
the canvas pad without any error.

Suite 82 -> 144 tests. Demonstrated on the IMG_3052 beat, rebuilt three times.

**Not built:** subject masking (type passing behind the speaker) needs a person matte.

---

## 2026-09-19 — Detour-1 session 2: 4:26 drive vlog -> 15:14 three-act film

The user added everything the first cut never had: 207 dashcam clips covering the whole day,
b-roll, the cafe monologue, and a studio re-record. Nothing about the tool changed; this entry
is about what the material and the checks taught.

**The footage's own problem.** The cafe monologue — the point of the trip — was lost off the
phone. `main-clip.mov` is its surviving tail; `IMG_3629/3630` are a re-record made a month
later. So the same argument exists twice from two locations, and the edit's real decision was
which instance holds what. Resolution: the studio carries the argument, `IMG_3630`'s own wrap-up
is cut, and `main-clip` delivers the conclusion from the real cafe table. The lost footage gets
the last word.

**Dual-capture as a prepped source worked exactly as the KB says it would.** 10 driving takes
rebuilt as dashcam-full-frame + phone-interior inset, under the **original source key**, so
caption lookup and word timings resolved with no overlay bookkeeping. Prep must not retime:
verified every output against its source duration (all within 30 ms).

**Wall-clock alignment is free and worth doing.** `com.apple.quicktime.creationdate` per take vs
the dashcam filename timestamp agreed to the minute, and the dashcam independently corroborated
the whole day — including a **57-minute gap 19:35->20:32 that is exactly the cafe stop**. No
guessing which dashcam file covers a moment.

**Four classes of defect caught, all now written up in gotchas.md:**

1. **Ghost captions** — a range end rounded to 3 decimals landing microseconds past the next
   word's start, so the word was captioned but never heard. The user heard this before any
   check did. Fixed by flooring ends / ceiling starts to the millisecond.
2. **Nine Act-1 edges cutting inside a word**, inherited from session 1's *delivered* cut.
3. **Five mid-sentence joins that skipped the words carrying the meaning** — found only by
   reading the assembled cut back as prose, plus a scan for same-source joins with no sentence
   boundary either side.
4. **A "closing shot" that was a parked car** — `freezedetect` caught 2.7 s of frozen picture;
   a frame-difference scan (validated against a known-moving control first) found the real
   arrival 8 minutes earlier.

**Also measured:** `arnndn` lq is worth **+18 dB** of separation on in-car speech whose raw
separation is under 2 dB, while the treated studio room is the case where *every* chain measures
identical and the right answer is no filter at all. Caption chunking for long-form: `break_on
".!?"` + 7-word cap + `min_words 3` took 493 cues / 86 one-word orphans down to 331 / 4.

**Process note worth keeping:** reusing an interrupted run's segments is safe *only* with the
per-segment frame-count assertion the KB already prescribes — it let a killed 4K run resume at
the concat instead of re-extracting 109 segments. And cues anchored to a source's first output
occurrence, rather than to hardcoded times, survived a re-cut that moved every boundary by ~9 s.

**Delivered:** `final_s2_4k.mp4`, 3840x2160 @30, 15:14.

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

---

## 2026-09-16 — Detour-2 inventory + transcription (a-roll only)

Source: `~/Documents/Ambitious/Editing/Detour-2`. Scope was deliberately inventory +
transcription only; no strategy, no EDL. Output in `<src>/edit/`.

**Shape of the shoot.** 54 a-roll clips / 54.5 min (iPhone HEVC, HLG 10-bit); `b-roll/phone`
2 clips / 50s; `b-roll/dashcam` **405 clips / 6.70 h / 77 GB**, uniformly 2592x1944 (4:3),
30fps, aac mono — a different aspect from everything else, which any future timeline has to
reconcile. Full per-clip ffprobe tables written to `<src>/edit/inventory/{aroll,phone,dashcam}.tsv`.

**A-roll is heterogeneous in every axis that matters**: display orientation 45 landscape /
9 portrait; frame rates 29.97 (4), 30 (46), 24 (3), 15 (1); rotation metadata spanning
0 / ±90 / ±180; HLG on 51 clips but bt709 on the two Live Photo `.MP4`s. Per `kb/gotchas.md`
that means the concat needs an explicit `--fps`, and the portrait clips need prepping to the
majority geometry.

**Transcribed** all 54 a-roll files with `transcribe_deepgram.py --language multi` (Hinglish,
per the user and confirmed on a single-clip check before the batch — first clip returned
Devanagari + Latin mixed). 4689 words, 369 phrases, `takes_packed.md` 44.8 KB.

**Verified** (how): orientation by extracting one frame from all 54 clips into a contact sheet;
empty transcripts by `volumedetect` then a local-whisper presence test; durations/codecs by
`ffprobe`. Two new traps found — see [gotchas.md](gotchas.md).

**Open / not done:** diarization is poor on this footage (308 phrases S0 vs 61 S1 despite two
speakers conversing throughout — two voices are being merged into S0). `murgan-idli-3.mp4`
needs a `transpose` before use. No multilingual whisper model is installed, so the KB's
recommended free cross-check on *content* could not be run — only a presence test.

## 2026-09-16 (later) — whisper cross-check on Detour-2

Fetched multilingual `ggml-small.bin` (465 MB, HF `ggerganov/whisper.cpp`) to close the gap
noted in the previous entry, and ran the cross-check. Four new entries in
[gotchas.md](gotchas.md); `ggml-small.bin` recorded in [environment.md](environment.md).

**The footage moved mid-task.** Between the inventory and the cross-check, the 16 no-dialogue
a-roll clips were relocated to `b-roll/phone/` — exactly the 16 this session had flagged as
music/ambient. Verified as a clean move: all 16 present at byte-identical sizes, nothing lost.
Cross-check scope therefore became the **38** clips remaining in `a-roll/`. (Worth knowing that
a source tree can change under a long task; the `MISSING:` list looked alarming for a minute.)

**Two fixes to `helpers/transcribe_whisper.py`** (first local change to that file since it was
written):
1. `subprocess.run(..., errors="replace")` — whisper-cli streams recognized text to stderr and
   splits multi-byte characters, so strict decoding crashed on *any* non-Latin transcription
   before whisper even finished.
2. The JSON read now raises a RuntimeError naming the `-ml 1` byte-level-BPE cause instead of a
   bare `UnicodeDecodeError`. Deliberately **not** decoded leniently — that would return
   mojibake as the transcript.
Verified: Devanagari path fails with the explanatory message, English path still produces a
transcript, `uv run --with pytest python -m pytest tests/` 25 passed / 15 subtests.

**Cross-check result: Deepgram holds up.** 38 clips, whisper-en at 0.85–0.95× the Deepgram word
count. 7 ratio outliers inspected; 3 real findings, all recorded in gotchas.md:
- Deepgram `multi` emits **Spanish** on 3 clips (IMG_3200 47% of its words, timestamped
  17.3–22.6s — would burn into a caption).
- IMG_3196 `कपिल`(Kapil) vs whisper "couple/step three" — unresolved name, needs the speaker.
- Sub-second clips hallucinate in both engines.

The scariest-looking hit was a **false alarm**: whisper reported 4 sentences after Deepgram's
last word on IMG_3187, which looked like 32s of dropped dialogue. Speech-band level (−39 vs
−26 dB) and frames at 55/65/75s (two people sitting quietly in a car) showed it was whisper
hallucinating on ambience. Recorded as its own gotcha — the verification pattern generalises.

**Artifacts:** `<src>/edit/crosscheck-whisper.md` (side-by-side, all 38) and
`<src>/edit/crosscheck-whisper-json/` (raw whisper segment JSON).

**Still open:** diarization remains unreliable on this footage (unchanged). Whisper gives no
independent check on *timings* for Devanagari, so Deepgram's word timings are unverified.
IMG_3196's name needs human confirmation before it goes in a caption.

## 2026-09-16 (later still) — Detour-2: first real cut

The user added `notes.md` (episode) and `project.md` (standing format brief) to the footage
folder and said to start editing. Confirmed strategy first per Hard Rule 11 / `project.md`.

**Screened every clip before cutting**, as `notes.md` demands — 6-frame filmstrips for all 38
a-roll and 18 b-roll/phone clips, dashcam sampled at the anchors. This overturned four things in
`notes.md`; findings written to `<src>/edit/review-findings.md`:

1. `murgan-idli-3.mp4` is a **landscape clip stored sideways**, not portrait. `transpose=2`
   dissolved the "Unresolved — blocks the render" section entirely; the 4K target stands and
   none of its three fallbacks were needed.
2. The "unidentified silent 4K" block (3223/3224/3225 + 3182/3185/3202) is **the two of them
   singing along to in-car music** — best-looking interior footage of the day, not scenic b-roll.
3. Four return-leg clip times were ~1 h late and the closer was placed at the wrong dashcam
   block, because the timeline had been built on `creation_time`. See gotchas.md.
4. The traffic-jam speed-ramp needed a different dashcam window — found via the dashcam's
   burned-in **speed readout**, which also exposed a GPS privacy issue.

**User decisions:** two-hander (guest gets real space); both off-spec branded lines used as shot;
title asset deferred, 4 s bed left in the cut for it.

**Built:** `edit/edl.json` — 46 ranges, 16:05. Turn cut 5m54s -> 4m25s by removing only the
duplicated brain passage, keeping each half continuous so the take's pauses and restarts survive
(`project.md` says protect them). One subtle `zoom: 1.06` on the second half to disguise the
single internal jump cut, since the turn takes no cutaways. Preps in `edit/prepped/`:
transposed murgan-idli-3, pillarboxed 3214/3215, a 10s return-drive timelapse (3h29m -> 10s,
300 sampled frames, runs into dusk), and a 7.5s jam speed-ramp overlay (18.8 min of crawl).

**Verified:** 0/46 cuts inside a word (after fixing three real snapper bugs — see gotchas.md);
**0/45 boundaries showed an audio pop** (worst 1.16x vs a continuous-speech reference, threshold
1.5x), so Rule 3's fades hold; caption offsets measured from rendered segments showed
**1.082 s** of frame-quantisation drift versus the EDL float sum — the largest instance of that
trap yet recorded here, on a 46-segment cut.

**Still open:** b-roll overlay pass (L-cut on the rain exchange, J-cut into the dam, dashcam
cutaways) is deliberately a second pass — it needs the cut reviewed first, and overlays are
resolution-specific so they get rebuilt for the 4K final. Title asset not built. Guest consent
screening not done. Music cues not laid (no EDL field; custom `amix` pass).

## 2026-09-16 (cont.) — concat audio fix on `main`

User asked for: video stream-copy preserved through the concat, audio re-encoded once into a
continuous 48 kHz / 192 kbps stream to avoid per-segment AAC priming clicks, and a regression
test on the generated command. Done, plus one thing the investigation turned up.

**`helpers/render.py`**
- New module constant `AAC_ARGS`, shared by `extract_segment` and `concat_segments` so the two
  cannot drift (the concat re-encodes what the extract produced).
- `concat_segments`: `-c copy` → `-c:v copy` + `AAC_ARGS`. Rule 2 is untouched — video is still
  stream-copied and there is still no second video generation.
- `AAC_ARGS` includes **`-ac 2`**, which was not in the original ask but turned out to be
  required: one mono source among 44 stereo ones was silently corrupting everything after it.

**`tests/test_render_concat_audio.py`** (new, 7 tests): video stream-copied, audio re-encoded at
192k/48k, stereo forced, no blanket `-c copy`, audio not stream-copied, concat demuxer still
used, and extract/concat audio settings agree. Verified the tests actually catch the regression
by temporarily reverting — 4 of 6 failed on the old code, all pass on the new. Suite 25 → 32.

**Measured, not assumed.** The premise checked out and was worse than a click: the old
`-c copy` concat added **+1.396 s of audio across 46 segments (30.4 ms per boundary)**, so audio
drifted progressively *late* against picture, ~1.4 s by the end. Envelope cross-correlation
against the corrected build matched the predicted drift at four points (corr up to 1.000).
`loudnorm`'s measured LRA fell 23.8 → 18.6 once the phantom silence was gone.

**The mono trap.** Right after the fix, the last segments could not be located in the
concatenated audio at all. A control search for segment 00 (found at 0.020 s, corr 0.986)
established the method was sound, so the result was real: `murgan-idli-3.mp4` is mono, its two
segments sat at the break, and the concat demuxer cannot carry a channel-layout change through a
re-encode. Everything after decoded wrong while the file kept the correct duration and played
fine. `-ac 2` fixes it.

**Also learned:** the KB's boundary-pop self-eval is blind to this class of bug — inserted
silence is a gap, not a step discontinuity, so it reported 0/45 clean while 30 ms was being
inserted at all 45 boundaries. Pair it with a duration check. All three lessons are in
gotchas.md, along with a confirmation that draft and preview segment durations are bit-identical
(max diff 0.0 ms over 46 segments).

**Consequence for the episode:** the delivered preview had the drift, so the cut was re-rendered.

## 2026-09-16 (cont.) — Detour-2: noise, title, dual-capture B-roll; second A/V drift fixed

User asked for dashcam B-roll on the "let me show you outside" lines (full-frame or iPhone-style
dual capture), the "Detour" title over the departure, and noise suppression.

**`helpers/render.py` — second drift bug**, found while verifying the concat fix. `extract_segment`
passed a float `-t`, so video was frame-quantised and audio was not; the error accumulated to
0.6 s of audio-ahead-of-picture over 46 segments. Now snapped to whole frames before the fades
are computed, with `apad`. Verified: max per-segment |audio − video| **33 ms → 0.00 ms**, total
**−0.631 s → +0.000 s**. Tests 32 → 37 (`SegmentDurationTests`). Two sub-traps in gotchas.md.

**Noise suppression.** Measured four chains on three acoustic settings rather than inheriting the
KB's. Chose `highpass=f=100,afftdn=nr=20:nf=-28` as the EDL `audio_filter`; the previously
recorded aggressive chain is **3 dB worse on the dam monologue**, which is the spine. Programme
LRA fell 23.8 → 11.1 across the session's fixes.

**Title.** Built as a reusable series asset in `~/Documents/Ambitious/Editing/_assets/the-detour-title/`
(ProRes 4444 with real alpha at 3840x2160, plus the PNG sequence and the generator). Screen-space
3D: Y-axis rotation easing to camera, ease_out_cubic, drift matching the car's direction. Not a
tracked solve — the shot pans and this pipeline has no tracker, per notes.md — and deliberately
flat white condensed type, no bevel/chrome/shadow. Also moved the title bed from IMG_3167 [2-6]
(reversing in the garage) to **[41-47]**, where the car actually drives out and clears frame.

**Dual-capture B-roll.** 5 PiP overlays: dashcam full-frame with a rounded, bordered inset of the
A-roll top-left. The portrait clip (IMG_3214) uses a phone-shaped inset, which is what the look
is imitating anyway. Each was checked against the line it sits under — **2 of 7 candidates were
dropped** because the dashcam OSD showed 0-8 km/h while the speaker says "clear road". See
gotchas.md.

**Also fixed:** an EDL range overran its source because Deepgram timed a word at 8.96 s on a
7.37 s clip; render.py truncated the hook silently. The EDL builder now clamps and reports.

**Still open:** 4K final; music cues; guest consent screening; the two dropped cutaways pending
a call on whether those lines are sarcastic.

## 2026-09-16 (later) — Detour-2 rebuilt to the revised brief

User replaced `project.md` and `notes.md` and asked for a rebuild from those alone. The new
brief changes the shape substantially: a 0:00–0:40 cold-open montage, **dual-capture as the
default** for driving A-roll (not an occasional effect), a standing rule that any mention of the
road/traffic/rain cuts to dashcam, text cards, and the turn cut to 3:00–3:30.

**The noise complaint was correct and my earlier reporting was wrong.** I had reported "+2.4 dB
separation"; the user heard more noise, not less. Separation is a ratio — the absolute floor of
the *delivered* file was 3.2 dB **louder** than the source, because `loudnorm` re-applied ~4 dB.
Switched to `arnndn` (models fetched to `~/.cache/rnnoise-models/`), which is 12–24 dB better
than `afftdn` on this material. User chose per scene by ear: **lq at the dam, cb in car/night**.
That needed `ranges[].audio_filter` (new, 4 tests, suite 37 → 41). All in gotchas.md.

**`murgan-idli-3` resolved** — it is a landscape clip stored sideways, not portrait. `transpose=2`
gives native 1920×1080. notes.md Unresolved #1 (pillarbox / cut to 45s / re-record as VO / drop
to 1080p) needs none of its options. The user suggested rotating; that was right.

**ETA.** notes.md says not to doctor map footage from another vlog; the user asked to see a
repaint first and approved it. Built tracked repaints of the CarPlay strip: scene 9 shows this
trip's real `1:00 ETA · 26 min · 32 km`, scene 20 shows `6:46 ETA · 2:20 hrs` — **two fields, not
three, because the distance is not known from the footage** and inventing one is the exact thing
the brief warns against. Shown as a corner inset per the user's steer. Method and the two failed
tracking approaches are in gotchas.md.

**Built:** 72 ranges, 17m17s. 9 dual-capture prepped sources (dashcam full-frame + 24% interior
inset, bottom-left, consistent), 4 full-frame dashcam beats, pillarboxed portrait inserts, the
rotated shop clip, 4 overlays (title, speed-ramp, 2 ETA insets). Turn at 3:06 with all five
spine lines the brief names. Verified 0 cuts inside a word, per-segment A/V delta 0.00 ms,
uniform stereo.

**Still open:** music (5 cues, custom `amix` pass — needs the user's tracks), the 4K final,
guest consent screening. Dual-capture sources are built at 1080p and would need rebuilding at
2160p for the final.

**Turn in-point caught late.** The first turn range started at 58.41 s, which the snapper resolved
to 58.66 — *inside* the preceding phrase, so the most important section of the episode opened on
the fragment "these kind of videos." Moved to 55.85 (the phrase start, "uh, मतलब coming to
recording these kind of videos"), which leads straight into "मैं पहले अकेला...". Fixed with a
targeted re-extract of that one segment plus re-concat / re-SRT / re-place overlays rather than a
72-segment re-render.

Two things worth keeping from that: **a range start chosen for "2 s of lead-in" can land inside
the previous sentence** — check the words at the in-point, not just that the snapper produced a
legal boundary. And notes.md's "at least 2 s of clean ambience before the first word" was **not
achievable**: the largest gap anywhere near the turn-in is 0.71 s because the take is continuous
speech. Reported rather than manufactured.

Caption drift on this render was **+0.033 s** (vs 1.082 s on the pre-fix cut) — the frame-snap
fix means measured and EDL durations now agree almost exactly.

## 2026-09-17 — Detour-2 v3: the user's line-by-line notes on the first cut

User reviewed v2 and gave ~24 numbered points. Nearly all were "you trimmed content I wanted",
so the through-line of this pass is **keep the take, cut less**.

**Real defect they caught:** `murgan-idli-1.mp4` was never pillarboxed, so one segment was
1080x1920 among 71 landscape ones. The `-c:v copy` concat accepted it silently and the player
stretched it. A segment-dimension check now belongs in pre-render validation — see gotchas.md.

**Content restored:** 3171 from its real opening ("So, what's up guys?") and full; 3173, 3174,
3175, 3176 from their true starts; `murgan-idli-3` full 2m55s; 3206 essentially whole.

**3206 — why the old cut read as broken.** The notes said the two-parts-of-the-brain point is
made twice, keep the second. Taken literally that removed the *setup* (which is in the first
instance) and kept only the payoff. Correct cut keeps the setup and drops just the abandoned
first attempt (217.19-228.38). Also measured: **3206 has no pause longer than 1.5 s**, so
"cut only long pauses" removes nothing there.

**New assets:** dual-capture for 3173/3187/3214 (+ 3171/3172/3183 rebuilt longer); full-frame
dashcam for the hill-and-arrival (`132141`) and the dam gate (`153549`-`153649`, with a "reached
dam entry" card); `pb_murgan-idli-1`; `murgan-idli-3` re-prepped with **BMI inserts** baked in at
the lines that name the numbers (14.0% body fat, 33.6 kg muscle mass, current InBody) — the
InBody photos were cropped to exclude a partially visible mobile number; two timelapses
(4 s evening bridge, 10 s dusk-into-night moved before the closer); title regenerated with a
4.6 s hold so the word is standing as the car clears frame.

**Caption fixes** in the transcripts, originals kept as `.orig`: "those who know who know",
"smooth ride", "long ride".

**Three engineering traps hit and recorded:** odd PiP dimensions vs `force_original_aspect_ratio`
rounding; a range flush with its source overrunning after the frame-snap (this aborted a
50-segment render at seg 43 with an intermittent AAC encoder error); and `-c copy` joins breaking
downstream filtergraphs. EDL clamp headroom is now 0.05 s.

**Result:** 50 ranges, **27m14s** (was 17m20s) — the direct cost of keeping the content. All
segments 1920x1080, max |audio-video| 0.00 ms, 0 cuts inside a word, 5 overlays.

**Open:** music (5 cues, needs the user's tracks), 4K final (dual-capture sources are 1080p and
would need rebuilding at 2160p), guest consent screening.

## 2026-09-17 — Detour-2 v4: the shop walk-in was still sideways

The user replaced `b-roll/phone/murgan-idli-1.mp4` with `murgan-idli-1-new.mov` for the
11:13-11:19 walk-in. Checking why showed the swap was fixing a **real defect, not a preference**:
the original is 1080x1920 with *landscape content lying on its side* — the same trap as
`murgan-idli-3`, which was caught. `-1` was not; it was read from its dimensions alone and
"fixed" with a pillarbox, which kept the picture sideways and merely framed it in black bars. It
then passed the uniform-dimension check (the pillarbox output is a legitimate 1920x1080) and a
second review that only asked whether every segment was 1920x1080.

Verified by extracting one frame from the raw file, the prepped `pb_` file and the new file.
Also re-checked `murgan-idli-2.mp4` (538x954): genuinely upright portrait. So within one
three-clip batch, sharing a session and a filename stem, two are sideways and one is not — an
earlier gotcha entry claiming the siblings were upright has been corrected rather than caveated.

**Change:** EDL source `murgan-idli-1` now points at `../b-roll/phone/murgan-idli-1-new.mov`
directly. It is already 1920x1080 hevc/bt709, so it needs no prep; `prepped/pb_murgan-idli-1.mp4`
is now unused. `edl.json.v3.bak` keeps the previous state.

**Rebuild was surgical.** The new segment is frame-identical to the one it replaces — 240 frames,
8.000 s video *and* audio, 1920x1080, stereo 48 kHz — so every downstream offset (overlay
`start_in_output`, caption timings) is unchanged. Only `seg_25` was re-extracted; the other 49
came from `clips_preview/` and `master.srt` was reused rather than rebuilt, which also protects
the hand-made caption corrections. Driver in the scratchpad calls `render.py`'s own
`concat_segments` / `build_final_composite` / `apply_loudnorm_two_pass` so the settings cannot
drift from a normal render.

**New gotcha:** pillarbox and transpose fix *opposite* problems that `ffprobe` reports
identically, and the dimension check cannot tell them apart. Recorded with the rule that follows
from it — look at one frame from every clip you *prepped*, after prepping it.

### Same day — 1080p final master, and a stale-cache bug it exposed

User chose a **1080p final** over 4K after seeing the numbers. Measured against what the
originals actually hold, a 2160p master would have been true 4K for 46.5% of the runtime, a
1.12x upscale for 37.6% (the 1080x1920 phone clips, pillarboxed), a 2x upscale for 13.0%
(`murgan-idli-3`, `IMG_3189`, `IMG_3207` — including the longest single block in the film) and
1.48x for the 2.9% of dashcam. It would also have meant rebuilding every `prepped/` asset at
2160p, since those are all 1080p intermediates — 57.5% of the runtime.

Final render: CRF 16 / preset `slow` segments, CRF 14 / `slow` composite, two-pass loudnorm.
27.0 Mbps video, up from 13.6. 5.3 GB.

**The clean re-extract came out 0.304 s shorter than v4, which exposed a real bug.** Six ranges
— the ones clamped to `source_duration - 0.05` after the seg-43 abort — had been clamped *after*
`clips_preview/` was extracted, and nothing re-extracted them. So v3 and v4 were built from
segments 1-2 frames longer than their own EDL asks for, and `master.srt` plus all five overlay
positions were measured against that longer timeline. Self-consistent, silent, and wrong: reusing
those positions in the final would have put every caption after 0:24 up to 0.333 s late.

Fix: rebuilt `master.srt` from `clips_graded/` (914 of 917 cues moved) and remapped the overlay
starts onto the measured boundaries, then re-composited from the existing `base.mp4` — no
re-extract needed. Recorded in gotchas.md with the frame-count assertion that catches it, and
note that `round()` is banker's rounding, so the check must use the same call `extract_segment`
does.

**Verified on the delivered file:** container 1634.262667 s, video 1634.200000 s = the exact sum
of the 50 graded segments; all 50 segments 1920x1080 and **0 disagreeing with the EDL** on frame
count; 49 cut boundaries all clean (max step within 5 ms of a join: 213, against 5685 for
continuous speech — the two boundaries that first looked hot were loud *content* either side, not
seams); all 5 overlays spot-checked in place against their cued lines.

## 2026-09-18 — `helpers/denoise.py`: neural denoising in the pipeline

User heard wind on the dam monologue (IMG_3206) from 17:00 in the final, supplied an Adobe
Enhance Speech v2 render as a target, then asked for the capability to be built into the repo
rather than importing Adobe's file — naming DeepFilterNet and SpeechBrain.

**Measurement first.** The complaint was correct and the gap was large: voice-normalised noise
floor of 3206 was −42.4 dB raw, −50.1 dB as shipped, −75.9 dB from Adobe. Our `arnndn` chain had
removed 8 dB where Adobe removed 34. Diagnosed why: wind is 72% below 300 Hz and **gusts through
27 dB**, which is `arnndn`'s weak case — it barely touched the gusting (27.6 dB swing after, vs
30.4 before). A scan of all 25 sources found 3206 is the **only** gusty clip (everything else
3.4–17 dB swing), and — counter-intuitively — it has one of the *best* raw SNRs in the film
(31.6 dB; the in-car takes are 6–11 dB). Steady drone is tolerable, gusting is not.

**Engines benchmarked** on the same 25 s excerpt, band-limited to 0–8 kHz so the 16 kHz models
are not flattered. DeepFilterNet3 + `--pf`: **−70.8 dB, 1 dB better than Adobe**, 23.2 dB better
than shipped, 2.6 dB more 4–10 kHz presence than Adobe, at 24x realtime locally. DeepFilterNet2:
−66.2. Both SpeechBrain models were **worse than the existing `arnndn`** (+3.4 and +1.9 dB) —
VoiceBank-DEMAND training, 16 kHz, wrong tool. Not installed.

**Built `helpers/denoise.py`.** Produces a prepped source (video stream-copied, cleaned audio),
which is how the repo already handles anything ffmpeg cannot express — captions and offsets then
resolve for free. Shells out to a pinned python 3.11 env it bootstraps itself, because
DeepFilterLib has no arm64 wheel above cp311 *and* DeepFilterNet needs `torchaudio<2.2`.
Detects dual-mono phone audio and denoises once. Asserts the sample count is unchanged and
refuses to write if not — SpeechBrain's mtl-mimic came back 8 ms short, which would have shifted
every cut after it.

**`--ambience` restores "outdoors" the only way that works.** The obvious approach — mix the
original back at 10% — measured −51.5 dB, i.e. exactly the old `arnndn` floor, because 84% of
what the model strips is wind below 300 Hz. Blending the **high-passed residual** instead gives
−59.4 dB at 10% and −54.9 dB at 20%, both still well ahead of what shipped.

**Bug hit and pinned:** `probe()` read ffprobe output positionally, and ffprobe prints
`sample_rate` before `channels` regardless of the requested order — so a stereo clip reported
48000 channels and the helper began denoising "channel 44". Caught by watching the process list,
not by any error. Now parsed by key with a plausibility check.

15 new tests (`tests/test_denoise.py`), suite at **56 passing**.

**Not yet applied to the cut** — waiting on the user to pick an ambience level from the A/B.

## 2026-09-18 (later) — overlay freezes, music, teeth

**Overlay freezes.** User reported the picture stopping at 17:28 and 24:19. A
full-file `freezedetect` found **four**, not two, each ending exactly where an
overlay ends (0.43 s, 0.77 s, 1.67 s, 1.93 s — growing with position in the
chain). Root cause: `setpts`-placed overlays drain ahead of the main timeline
over a long render, so each entered its window already some way into its own
footage, ran out early, and `eof_action=repeat` held the last frame. Proved by
matching delivered frames to the overlay source pixel-for-pixel: constant +48
frame offset from the first displayed frame. Only reproduces against the real
`base.mp4` decoded from t=0 — not on a short clip, not on a synthetic base, not
on a re-encoded slice, which cost time. Fixed with `-itsoffset` per input plus
`eof_action=pass:repeatlast=0`; offset now −1 frame and zero freezes film-wide.
10 tests in `tests/test_render_overlay_timing.py`.

**Music.** Five Epidemic Sound tracks supplied; mapped to the five cues by
measured tempo, percussive share, brightness and dynamic range rather than by
title. Levels set per cue against the programme in that window — a single global
target left two cues inaudible, and the restaurant window has **negative**
headroom (programme peaks at −0.5 dBFS) so that cue ducks the programme 4 dB
with the ramps outside the music. Mixed before loudnorm. The mix then pushed
true peak to +0.8 dBTP, fixed with an audio-only limiter pass (video
stream-copied): delivered at −14.5 LUFS, −0.4 dBTP.

**Teeth.** My first assessment — "not worth it, 0.013% of frame" — was wrong
because I sampled the dam monologue, where he talks rather than smiles. At the
three windows the user named he is smiling wide and the yellow is obvious.
Built `helpers/retouch_teeth.py`: explicit window and explicit face, mediapipe
inner-lip mask, enamel selected by brightness and low saturation, applied in YUV.

The interesting part was quality. Piping frames through Python cost ~20 dB
twice: a `bgr24` round trip (34 dB vs 55 dB for a plain re-encode) and an
untagged rawvideo input making ffmpeg insert a full→limited conversion (33.8 vs
52.4 dB). Both produce a file that plays correctly and passes every structural
check. After fixing, the three segments measure 50–56 dB against their
originals. Frame counts unchanged, flicker 1–6% of effect size.

**Delivered:** `detour2_final5.mp4`. Suite at 81 passing.

### Same day — teeth pushed harder, after a mask bug

User: "didn't had that much difference honestly in terms of teeth color but you
can push it." They were right, and the cause was not timidity in the settings.

The enamel mask selected "bright AND low saturation" (`S < 90`). On a real smile
that dropped **656 bright pixels averaging saturation 99 at hue 23** — the yellow
enamel itself. The rule was whitening the teeth that were already white and
skipping the discoloured ones, so the effect was real but landing in the wrong
places. Mask now keeps bright pixels that are near-neutral OR yellow at moderate
saturation (`(S<115 & 8<=Hue<=45) | S<70`); coverage 2682 -> 3211 px on the test
frame.

Strength raised from desat 0.55 / lift 10 to **0.90 / 18**, chosen from a ladder
rendered on a still: 1.0 / 22 flattens the teeth to uniform white and reads as
fake, 0.90 / 18 keeps tooth-to-tooth shading.

Also renamed `H` to `Hue` in the worker — `H` is the frame height everywhere else
in the same file. It worked by Python scoping and was a trap for the next edit.

**Delivered `detour2_final6.mp4`:** 0 freezes, −14.5 LUFS / −0.4 dBTP, duration
unchanged, music unchanged, speech within 0.04 dB, untouched picture regions
50–56 dB. Suite at 82.

## 2026-09-20 — retention grounding; `local` branch deleted

- `coverage.py` reads the benchmark column of a YouTube retention export and warns when the
  curve is built from too few viewers. Episode 1's export is **21 people** — every value a
  multiple of 4.76 — and the raw and benchmark columns disagree about the opening: raw reads
  95%→52% in ten seconds (a failed hook), benchmark reads **+17.9 over typical** (normal).
  Only 2:32–2:47 is genuinely below par (−35.9), and it is 15 s of hedging. See gotchas.md.
- Deleted the `local` branch. It was documented in four places as a synonym of `main` at the
  same commit; it was in fact 16 commits behind. Confirmed `git log main..origin/local` empty
  before deleting, so nothing was lost. CLAUDE.md, kb/index.md, environment.md and
  new-machine.md all corrected — the claim was in every one of them.

## 2026-09-22 — episode2 ("I Gave Up My Biggest Dream at 15"), cut + treatment

Second episode of the main series. 37 clips, 4K **HLG** (Ep1 was SDR — see gotchas.md),
~19m20s of usable speech against a script targeting 8–9 min. Work lives in
`~/Documents/Ambitious/Editing/episode2/edit/`; full record in its `project.md`.

- **Runtime was a real decision, not a default.** Shoaib asked to keep the off-script
  material. Measured, filler removal only buys 23 s, so "keep everything" lands at 15m30s.
  Presented that with the specific cut that fixes it — dropping `IMG_3670`, 70 s that
  restates an earlier beat — and he took it. Final 12m55s, and Scene 6 drops from 4:00 to
  2:50, which matters because Ep1's retention bottomed out at the end of a 2m50s stretch.
- **Reading the assembled cut back as prose found 8 defects** that nothing else would have:
  six segments chopping their own last word, and two wrong word picks (one join read "and I
  scored somewhere scored around sixty"). This check keeps paying for itself.
- **Deepgram inverted the thesis line again** — "I just can't *feel*" for "fail", the exact
  shape of Ep1's "what I do know". The free whisper cross-check caught it, as it did then.
- **`coverage.py` on the picture lock: 5 visual events in 12m55s.** New gotcha — 75 jump cuts
  at 1.00-1.10x read as 5 events, correctly. Drove the whole treatment plan.
- New gotchas recorded: `zoompan` `d` multiplying under `-loop 1` (389 s file for a 3.6 s
  still), `drawtext` and apostrophes, SDR grade over HLG tone-map, coverage vs push-ins,
  raising rather than clamping when a graphic's anchor word has been cut, and a third
  instance of the zsh word-splitting trap (`set -- $var`).
- Reused from Ep1 with no changes: `brand.json`, the snap-from-word-timings pattern, the
  sidechain music mixer's structure, and the self-eval's boundary-pop test.

## 2026-09-23 — Open-Higgsfield-AI evaluated; kb/ideation.md added

**Open-Higgsfield-AI** ([repo](https://github.com/Autom8AI/Open-Higgsfield-AI)) — evaluated, and
**nothing taken**. It is a Next.js/Electron front-end over the hosted Muapi.ai gateway: no local
inference, no algorithm, and its one open PR is fixing that API client silently dropping
`negative_prompt`/`video_url`/`request_id` and treating HTTP 408/429 as permanent failures.
Unlike the two design repos we mined earlier, there is no technique here that survives a rewrite
into Python — if we ever want Muapi we call its REST API in ~40 lines.

Generative b-roll as a *capability* remains open but is editorially fraught for the main channel:
Ep1's whole claim is "from something that I have actually lived, and it's not something that I've
read from somewhere" — which is, per the retention export, the exact line sitting in the worst
window. Proposed shape if we ever do it: `helpers/generate.py`, prompt + EDL anchor → writes
`<edit>/generated/` with a prefixed filename so it is auditable at picture lock. Try on a Detour
episode first, where b-roll is scenery rather than autobiography.

**`kb/ideation.md`** — new topic file, from three videos Shoaib supplied. Covers the A+B=C
identity formula, recombination over originality, constraints as the cure for creative block,
presentation over assets, and repetition as the mechanism for style. Marked throughout as
practitioner opinion rather than measurement, with **[measured]** tags where a claim explains
something we actually observed on YT1. Linked from `index.md`.

Transcript retrieval: captions via `yt-dlp` for one video, local whisper.cpp for the other two
after YouTube 429'd the timedtext endpoint. The Hindi one first came back as a hallucination
loop from the English-only model — both traps now in `gotchas.md`.
