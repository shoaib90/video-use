# Worklog

Newest first. Records local divergence from upstream and *why*, so a future session doesn't
re-derive it or mistake a deliberate change for a bug.

---

## 2026-10-01 (end) — glass cards wired into the EDL (`cards` block, `helpers/cards.py`)

Shoaib approved the look ("this is just sick") and asked for it in every future video, wired into
the EDL and written into the script's edit section.

**Built:** `helpers/cards.py` + `helpers/cards_runtime/{glass.js,glass.css}`. Two kinds, the two
proven by hand: `list` (rows on phrases, grows then scrolls by whole rows, chips, tag, footer)
and `stat` (value flips, accent = change, stackable). Python resolves every phrase against the
KEPT words using measured segment durations, searching forward, and raises on a cut phrase;
it also resolves all geometry, so the runtime only draws. render.py renders card + mask through
HyperFrames at the base's own size and fps (cached by content hash under
`<edit>/animations/cards/<id>/`), runs `hyperframes check` and fails on errors, then composites
after overlays / before graphics + subtitles, with the quarter-res blur, `tpad`-padded mask and
601->709 conversion. EDL `brand` points an episode at a brand.json (Episode 2 -> YT1's).
Also fixed: demotions with nothing else drawn mapped `[0:v]` and dropped the demotion output.

**Verified:** 21 new tests (anchors forward + raising, measured-duration shift, scroll snapping,
growth, stage independence, 601->709, mask padding, layer order); suite 198 passing. End to end:
Episode 2 `edl.json` (backup `edl.pre_cards.json`; only `brand` + `cards` added) rendered with
`--preview` to `preview_cards.mp4` (1080p, 9:00.37, 20 overlays + 1 card + subtitles), the card
resolved to the same words as the hand-built test, frames checked inside and outside the window.
`local()` fonts pixel-identical to extracted TTFs (0 / 377,912 px). `final.mp4` untouched.

**Docs:** SKILL.md "Glass cards" (when / two kinds / anchoring rules / placement / what render.py
does), kb/helpers.md, index line, gotchas #10-11. channel-kb (private): playbook §7 + rule 11 +
checklist line; Episode 3's edit-direction section rewritten as glass-card specs.
**Not built:** the shrink-to-corner tracker Episode 3's pillars card asks for; SFX on landings.

---

## 2026-10-01 (later still) — HyperFrames test 2: Episode 2 routine as a glass timeline, at 4K

Shoaib asked for the routine clip next. project.md records that Scene 4's routine was
deliberately made "a montage, not a list" (GFX_ROUTINE dropped), so the test COMBINES them
rather than overriding that: one glass timeline card that builds the day row by row on the
spoken word and persists across the five montage cutaways (cycle, road, bus, nets, books).

Window: output 92.60-157.19, rebuilt in render.py's layer order from `base.mp4` + the EDL's
b-roll overlays + glass + cards + `master.srt` (shifted) LAST, with `final.mp4`'s mix. Anchors
are IMG_3657_110 / IMG_3658_110 words mapped through `build/actual_bounds.json` — they matched
the caption cue starts to the millisecond. Exit lands on "that routine is" (154.9). Delivered
`routine_glass_2160.mp4` + `routine_compare.mp4` (delivered above, glass below). Verified with
two QC sheets at every landing, over every cutaway, the scroll steps, payoff and exit; mask
growth measured from snapshots. Four more traps in gotchas.md (#6-#9). First pass rejected on
its own QC: type too small for a list, and an empty full-height panel for 10 s.

---

## 2026-10-01 (later) — first HyperFrames graphics: glass stat cards, Detour-3 body-fat passage

Shoaib approved installing Node and testing on his own footage. Chose Detour-3 IMG_3321
114.25-148.00 (in the cut) because the same window already carries the current approach, a
baked InBody screenshot card, so the test is a true before/after.

Built in `Detour-3/edit/animations/slot_glass_bodycomp/`: three brand-palette glass cards (body
fat, muscle mass, weight) in the upper third (his hands own the lower half all window), each
landing on its spoken number from Deepgram word times, with delta -> absolute flips (the
two-week change, then the current reading; figures kept out of this public repo). Rule adopted: **accent = change**, absolutes in cream, which keeps <=2 accents.
Delivered `glass_after_1080.mp4` + `glass_compare.mp4` (stacked before/after), 33.77 s, audio
copied, every pass exactly 1013 frames. Verified by contact sheets at each anchor and the exit,
and by measuring the accent colour in the final.

Five traps written to gotchas.md (BT.601 untagged MOV, glass needs a mask pass, one root per
project, static guard ignores external scripts, clipped glyphs). Not yet done: SFX on card
landings, burned captions in the test, 4K, and wiring HyperFrames into the EDL `graphics` block.

---

## 2026-10-01 — reference: Nate Herk, "Opus 5.5 Just Changed Video Editing Forever" (motion graphics)

Shoaib supplied <https://www.youtube.com/watch?v=7jHXoPGnA4c> (19:22) as the motion-graphics
look he wants. Method: `yt-dlp` 720p (captions 429'd again, as gotchas.md predicts), local
whisper `small.en`, 3 s contact sheets for the whole video + 2 fps sheets for the 0:00-0:46 intro.

**What the outputs are made with:** every edit is HyperFrames (HTML/CSS/GSAP rendered
frame-by-frame), written by the model per prompt, plus fetched assets (logos, site screenshots,
screen recordings), Kling image-to-video, music/SFX, and a self-check loop on rendered frames.

**Talking-head vocabulary in the intro (the transferable part):** icon+label glass cards placed
on the side the speaker POINTS to, on the spoken word (0:05 / 0:06.5); a lower-third phrase with
words highlighting as spoken, on a dark scrim (0:09-0:10); a typed prompt bar (0:10.5, 0:41);
paired left/right proof cards with a caption tag ("Screen recording", "Screenshot", "Generated
image") that swap contents as the list is spoken (0:31-0:37); a full-screen showreel takeover
cut into the talking head (0:12-0:27). Other edits: hand-drawn whiteboard + split-screen,
rounded-crop face cam over a dark slide, a 9:16 reel with a step tracker, a product spec ad.

**Gap against this repo (verified by grep):** our graphics are PIL components; nothing does
backdrop blur (glass), SVG/logos, or asset fetching, and HyperFrames — documented in SKILL.md —
has never been used in any episode. **Node is no longer installed**, so HyperFrames cannot run
at all right now (environment.md corrected).


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

## 2026-09-24 — episode2 delivered at 4K

`final.mp4`, 3840x2160, 9:01.8, -14.2 LUFS. Full record in the project's `project.md`.
**Superseded the same day** by a 9:00.37 re-delivery — see the next entry.

- Cut went 12:55 -> 12:27 -> 9:18 -> 9:02 across three sessions, the last on Shoaib's
  own five-act brief. His brief was written from the SCRIPT not the transcript — about a
  third of its lines are not in the footage — so the structure was taken and the words
  came from the takes.
- **Selective 1.10x on the expository takes only**, built as prepped sources with
  rescaled transcripts. New gotcha: a per-range `setpts` drifts every caption inside the
  range by the rate. 31% of the episode is sped; everything emotional is not.
- Sound design built from the library plus the b-roll's own audio. The best beat is
  Shoaib's: the bed stops dead under the hang-up beeps when the coach refuses.
- Two measurement lessons recorded: an effect 9 dB under the programme cannot be
  detected by RMS at all (0.5 dB), and subtracting two renders leaves a uniform ~2.5 dB
  limiter/codec residual so it isolates nothing. Floor-against-a-control works for beds;
  peak is useless once a limiter pins every window.
- A supplied b-roll clip was 848x478 among 1280x720 siblings, which broke a hardcoded
  watermark box. Watermark geometry is now a fraction of frame.
- Held an editorial line twice: a generated "Childhood Uniform Photo" was refused, and
  the replacement height-chart clip was trimmed to its face-free section. Environments
  and objects; the real photographs carry the people.

## 2026-09-24 — episode2 re-delivered at 9:00.37, and five gotchas from the delivery

`final.mp4`, 3840x2160, 9:00.37, 40.7 Mbps, -14.2 LUFS, 2.75 GB. Supersedes the
9:01.8 file above. Full record in the project's `project.md`, session 5.

- **A pad pulled untranscribed Hinglish into the cut.** Shoaib asked for 4:47-4:50
  ("matlab mereko") to go. The cause is the interesting part: a lone segment holding
  the word "But" carried a 0.80s pad, and the take had been transcribed with
  `--language en`, so Deepgram returned "But" and showed *nothing* of the Hinglish
  that followed. The words were audible in the render and absent from the transcript
  — invisible in the surface the cut is reasoned from. This is a second, quieter cost
  of the `--language en` trap already in `gotchas.md`: not just wrong captions, but
  material entering the cut unseen. Shoaib's other two reported missing-word spots may
  well be the same class.
- **`resume_render.py`** — new pattern, after the 4K render was killed mid-composite.
  Segments, base and SRT all survive a kill; only the output mp4 is unrecoverable (no
  moov atom). Verify freshness against `edl.json`, neutralise extract and concat, hand
  to `render.py`'s own composite path. Minutes instead of ~18.
- **`pgrep -f` self-match deadlock.** Three chained waiters all watching `render.py`
  matched their own command lines and hung ~10 minutes past the job's completion. Now
  waiting on a printed marker instead. This one is not video-specific and will recur
  anywhere in this repo.
- **`freezedetect` logs at INFO**, so a hand-rolled `-v error` re-check reported 0
  freezes where there were 9 — a false negative on a delivery check. Also confirmed
  that a black cold open with burned captions yields back-to-back freeze spans, one
  per caption change; 9 of episode2's 12 are that, and none are in the picture.
- **A hardcoded self-eval probe became a fake defect.** `selfeval.py` probed 700s on a
  540s cut and printed `-999 dB` beside the real levels. Re-anchored to the end card.
- **The bed-vs-control diff reads backwards.** A *scored* window lands ~1 dB *below* a
  known-naked reference, because a bed gives the limiter more to take back. Measured
  global gain +11.09 dB against the mix log's +11.10, which validates the method; the
  zenith at -0.19 and the 20cm window at -0.02 are naked, the two known beds at -1.21
  and -0.94. Reading the sign the obvious way would have certified a scored zenith.

Also written: `episode2/edit/community_posts.md`, six posts to `kb/distribution.md`'s
rule (the value that did not fit in the thumbnail, never "watch my video"), and
`build/check_overlays.py` / `build/check_beds.py` as reusable delivery checks.

## 2026-09-24 — b-roll analysis of a reference cut, into storytelling.md §6

Shoaib supplied <https://www.youtube.com/watch?v=uV3CW2zBznE> ("Rebrand your Entire
Life before 2027", Sankho kun, 16:31) with the observation that the b-roll seems
unrelated to the narration, and asked what I made of it.

Method, worth reusing for any reference cut: `yt-dlp` at 480p plus auto-captions,
`select='gt(scene,0.3)'` for cut detection, one frame extracted 0.35s **after** each
cut (sampling at the cut is what makes the sheet answer "what did he cut TO"), tiled
into 36-up contact sheets, then aligned against caption timings to compare word
against picture.

Findings, now in `kb/storytelling.md` §6:

- 205 cuts / 991s = **12.4 cuts/min**, median shot **2.67s**, 57% under 3s, longest
  hold 62.4s. Our Ep2 is 7.3 events/min for comparison.
- The premise is **half wrong**. B-roll tiers: **literal** whenever the sentence
  contains something concrete ("lose 10 kgs" → treadmill, "a camera or a gaming PC" →
  both, "all-nighters" → a bloodshot eye, a 4-item list each illustrated), and
  **texture** only when the line is abstract.
- Why the texture tier works there and does not transfer: every shot is **him**, so
  the footage is evidence for the claim rather than decoration over it. Stock in the
  same slots collapses it. The test for a mismatched cutaway is "evidence or
  wallpaper?".
- The actionable lesson is upstream of the edit — **a standing library of yourself
  doing ordinary things**. Ep2's 106s with nothing changing was an asset problem, not
  a cutting one.

Two ffmpeg notes from doing this: no ImageMagick on this machine, and the `tile`
fallback with `-pattern_type glob` takes **every** frame, so six "different" contact
sheets came out byte-identical. Stage each group into its own directory with
sequential names and use the `%03d` demuxer instead.

## 2026-09-26 — integrating an externally made motion graphic beside the talking head

Shoaib supplied `routine_10s.mp4`, a 4K routine card generated in a chat session, and
asked whether it could run beside his talking head. Built
`episode2/edit/build/routine_card_demo.py` → `routine_card_demo.mp4` (11.4s, 1080p
preview): split-screen push, the card used as a recap on "So that was my routine",
time-remapped with two frame holds so Sleep / Every day / For 3 years land on
"sleep" / "repeat" / "three years". Verified by contact sheets at the reveal times and
against word times from `gfx.output_time`. Three fixes after the first QC pass: the
payoff was unreadable over the ghosted list (extra dim), the dim's hard edge showed as a
band (gradient instead), and the caption sat off-centre after the panel left (`\move`).
Technique recorded in `gotchas.md`.

## 2026-09-27 — Detour-3 (Goa) inventory + transcription

180 a-roll clips / 158 min, 672 dashcam files. Transcribed 175 clips ≥1s with Deepgram
`multi` after confirming Hinglish on one clip first. Two things learned:

- **The KB's Spanish-drift grep never worked.** It grepped `transcripts/*.json`, which the
  helpers write ASCII-escaped (`¿`), so it matches nothing. Grepping `takes_packed.md`
  found 4 Spanish lines. Corrected in `index.md` and `gotchas.md`.
- **macOS `xargs -I{}` fails with "command line cannot be assembled, too long"** on a long
  per-file command, and exits 0 — the batch appeared to finish with 1 of 175 files done.
  Use a Python `ThreadPoolExecutor` driver instead (scratch `tx.py`), which also logs per file.

## 2026-09-27 — Detour-3 pass-1 story cut

Built `Detour-3/edit/build/`: `spec.py` (beats as phrase times) → `build_edl.py` (word snap,
contiguous-edge energy refine, beep list, `__nc` alias for caption-less picture ranges, prose
read-back) → `edl.json`; `prep.py` (4K SDR preps); `render_cut.py` (render.py wrapper: 4-way
parallel extraction + master.srt corrections); `selfeval.py`. 105 ranges, 30.8 min.

- **Parallel extraction** via monkeypatching `render.extract_segment` into a pool: serial ran
  ~2.3 segments/min on 4K HLG sources, 4 workers ran ~5/min (106 segments in ~21 min).
- **Beeps as one `aeval` per range** (`if(between(t,a,b)+…, 0.18*sin(2π·1000t), val(ch))`,
  segment-relative because render seeks with `-ss` before `-i`). Verified by FFT on the
  render: 100% of energy at 1000 Hz in all 3 windows. Captions masked in the SRT post-pass.
- **Deepgram dropped 15 s** of IMG_3571 (53.4-68.3s) outright; whisper small caught it. Patched as
  two caption cues at the measured segment offset.
- v2 self-eval: 0 freezes, uniform 1920x1080@30, duration within 0.1 s, 0 real pops.
  New traps in `gotchas.md`: contiguous-token clicks, box-label serials, WhatsApp forwards.

## 2026-09-27 — Paddy Galloway masterclass read in full; Ep2's opening measured against it

Source: <https://www.youtube.com/watch?v=Z2uoA3bhJT0> (Open Residency, 2h45m), read in
full from auto-captions (~39.6k words) via `yt-dlp` + the VTT flattener.

Filed as `storytelling.md` §7 (intro rules, core/casual/new, stakes, the pendulum) and
`distribution.md` §10 (packaging workflow, title rules, reading performance, outliers,
topic overlap). Index updated, including a stale line: it still said the cricket photo
was spent at 1:00, which was true at picture lock but not in the delivered cut (5:03).

The finding that matters, **measured on the delivered Ep2** (`blackdetect`, the burned
captions, `actual_bounds.json`): 22 s of black, a brand card 0:22–0:25, first face at
0:25.3 opening on "Last time I told you…", and "cricket" first said at 0:28.6 against a
thumbnail reading "WHY I QUIT". That breaks his first intro rule (deliver the promise in
~10 s) and his core/casual/new rule at once. It also resolves a contradiction in our own
KB: withhold the *reveal* (the photograph), never the *subject*.

Caught in passing: the Ep. 3 draft in channel-kb (v2, 2026-09-27) repeats all three —
"Visual: Black. Total silence", a brand card before the first scene, and Scene 2 opening
"In the last episode, I told you…" — citing learnings rule 1 as permission. Partly our
fault: the 2026-09-25 rewording had a prescriptive headline and an "unresolved" sub-bullet,
which read as licence. Rewritten in channel-kb to separate what Ep. 1 proved from what
Ep. 2 is still testing. The script itself was left untouched — it's Shoaib's work in
progress.

## 2026-09-29 — Detour-2 day-3 analytics

First performance data this channel has fed back into the KB. Recorded in
[distribution.md](distribution.md) §11, which until now was entirely an
unverified model from one podcast.

Headline: 125 views / 746 impressions / 1.88% CTR / 4:10 AVD (15.32%) / ~1h14m
watch time, at day 3.

**The numbers contradict each other.** `impressions x CTR` = 14 views and
`watch time / AVD` = 18 views, against a reported 125 — and ">95% of views from
Home" cannot coexist with 746 impressions, since Home is an impression surface.
AVD alone is internally consistent (250/1634 = 15.30% vs reported 15.32%). So
the real audience so far is ~15-18 people, not 125, and §3's "do not read the
first 24-48 hours" now has our own evidence behind it rather than just a claim.

**The one actionable signal** is AVD 4:10 against a turn at 16:46 — the average
viewer leaves 12.6 min before the episode's point. Detour-2's runtime grew
17:20 -> 27:14 during the edit to keep content; this is that decision showing up
downstream. Per §5 the response is Detour-3 built turn-first, not a re-cut of Detour-2.

Also logged: three places YouTube's auto-generated feedback was wrong about our
own video (recommended chapters we had already written, put the turn at ~18:00
when it starts at 16:46, advised teasing the reflection in the first 30-45s when
the cold open already carries one line from the turn by design). Diff platform
advice against the EDL before treating it as a finding.

Not done, and not derivable from what was supplied: new-vs-returning split,
Detour-1's first-three-days comparison, the retention graph.

## 2026-09-29 — Learn By Leo's "addictive editing" video, into storytelling.md §8

Source: <https://youtu.be/sLgHqZSe2o0> (14:32, 5.8M views), read in full from auto-captions.
Note: the link Shoaib pasted *displayed* the Galloway URL but pointed here.

Recorded only what is new or corrective: style follows the experience the viewer came for;
a motion graphic should carry an essential-but-boring beat and the speech should be *cut*
to match (which reverses how the routine card demo was built: it stretched the graphic);
eye trace across cuts; music as structure (stop spotlights, a fade reads as an ending,
changes land on topic shifts); his three-words-at-a-time caption rule, marked *test, don't
adopt*; and what not to take.

**Verified against our own code:** `episode2/edit/build/mix_music.py` places spot effects
by anchor word but music beds by hardcoded output time. That's why every bed after ~4:48
needed a manual −1.40s shift when "matlab mereko" was cut (the comment is still in `BEDS`).

**Open work, not built:**
- Pin music bed entries/exits to spoken words, as the spot effects already are.
- An eye-trace check: per cut, the distance between the speaker's centroid on the
  out-frame (`matte.py`) and the subject position on the in-frame, flagged above a
  threshold.

`gotchas.md` was deliberately left untouched: it carried uncommitted Detour-3 findings from
another session at the time, which aren't this entry's to commit.

## 2026-09-29 — Competitor study: Akshath Sharma, into storytelling.md §9

Shoaib asked for a study of <https://www.youtube.com/@akshathsharma/videos>, a same-niche,
talking-head-only channel with recent 1M/514K/288K hits. **Verified how:** `yt-dlp -J` plus
per-video metadata for all 324 long-form uploads (views, likes, comments, duration, date,
description), full auto-captions for 4 videos, storyboard sprites (`-f sb0`) for 4, and
thumbnails for 24. I also read the top comments on the 1M video in the browser pane. The
channel-specific study and its recommendations are in the private channel-kb,
`07-research/akshath-sharma.md`. Only the craft is here.

**Tooling notes** (verified this session; not yet promoted to gotchas.md, which carried
someone else's uncommitted work):
- Running the metadata pass and caption downloads at the same time got the caption endpoint
  **HTTP 429** for the rest of the session. `--sleep-subtitles` and the `tv` player client
  didn't clear it. Storyboards and thumbnails (i.ytimg.com) kept working. Next time, pull
  captions **first**, before any bulk metadata pass.
- YouTube's transcript panel never loads in a signed-out browser pane, and a caption
  `baseUrl` fetched from the page returns an empty body.
- The storyboard `.mhtml` is a MIME bundle. Unpack it with `email.message_from_bytes` and
  re-tile the 3×3 sheets (320×180 frames) to see a whole video's shot pattern at once.
- **Rescoped the same day, by Shoaib:** learn the *types of video* that blow up, not editing.
  The editing takeaways were removed (the coverage.py calibration, "stay minimal for short
  pieces", caption language), and §9 now records only script and packaging. I got the 1M
  video's Hindi auto-captions on a retry (English still returned 429) and analysed them line by
  line in the channel-kb study, along with a topic and title-angle table for 160 videos and
  seven video ideas drawn from our own story notes.

## 2026-09-30 — correcting yesterday's analytics reading

Yesterday's §11 concluded Detour-2's day-3 figures "do not reconcile" and that
the real audience was "~15-18 people, not 125". **Wrong, and now corrected in
place** rather than caveated.

The missing mechanism: **feed autoplay logs a view but not a thumbnail click.**
A muted auto-play in the Home feed, dwelled on for a few seconds, counts as a
view attributed to Home and never enters CTR. Studio's own funnel card says it
excludes autoplay views, direct traffic and some notification surfaces. Plus the
two pipelines run at different speeds — views near-real-time, impressions/CTR
lagging 24-48 h behind verification and spam filtering.

Verified against day-4 figures (921 impressions / 2.06% CTR / ~157 views /
4:10 AVD / 1 h 14 m): `impressions x CTR` = 19.0 and `watch time / AVD` = 17.8,
agreeing within 1.2 views. AVD over the clicked views alone predicts 1.32 h
against 1.23 h reported; over all 157 views it predicts 10.91 h, 7x out. So AVD
and watch time describe the ~19 who clicked, and ~138 views are autoplay.
Impressions also moved 746 -> 921 in a day, confirming the lag directly.

**What the correction changes:**

- The reconciliation rule is now "`watch time / AVD` against `impressions x CTR`
  — they share a denominator", not "distrust the view count".
- A new and better packaging signal falls out: **15.0% autoplay-view rate against
  a 2.06% click rate**. The footage sells ~7x better than the still, so the
  thumbnail is the weak link, not the opening seconds.
- The AVD finding gets *stronger*: 4:10 is the behaviour of people who actively
  chose to watch, and they still leave 12.6 min before the turn at 16:46.

Source: explanation supplied by the user from YouTube's own analytics guidance,
checked here against the numbers rather than taken on trust.
- **2026-09-30: the learnings were moved into channel-kb for scripting**, at Shoaib's request.
  Scripts are written in that repo, so its new `08-script-playbook.md` gathers every
  script-stage rule from this KB (storytelling §1–8, ideation, distribution §10–11) together with
  `04-learnings.md` and the Akshath study, tagged by where each came from, and ends in a
  pre-shoot checklist. Also added: `03-formats/short-advice.md` (the 2–3 min format and its
  skeleton), `01-roadmap/idea-bank.md` (seven ideas from the story notes), and a `CLAUDE.md`
  there. Rule from now on: a script-stage lesson goes in the playbook too; editing lessons
  stay here.

## 2026-10-01 — Detour-3 v3 (Shoaib's 20 notes + title-driven opening)

Packaging chosen before edit feedback: title "I Drove 621 km to Goa and Came Back Without My Car",
thumbnail A (ghats selfie + 621 KM). On Detour-2, 15.0% autoplay views vs 2.06% CTR showed the
packaging undersold the ride. The cut was then restructured to show "Goa" by 0:06 (it had been
2:45) and to seed the car line in a 34 s cold open. v3: 31:58, 113 ranges. Self-eval clean.
New in `gotchas.md`: ASR spells Hindi cuss words in English, phone numbers in screenshots,
plates in multiple clips, and baking cards into prepped sources.

## 2026-10-01 — Detour-3 v4: second-iteration notes, dashcam, graphics, music

12 notes from Shoaib, applied. New pieces in `Detour-3/edit/build/`:
- `plate_track.py`: CSRT plate masks; hand-keys where CSRT fails.
- `prep3.py`: masked blur.
- `gfx.py` + `prep4.py`: animated corner cards, Project December card, labels, dual-capture
  inset, dashcam cutaway, time-lapse. All baked into prepped sources in source time.
- `mix_music.py`: beds on picture-only runs, ambience ducking, two-pass loudnorm.

The dashcam clock matched the phone to ~1 s, and the OSD speed decided which takes get the
inset: only 1 of 7 in-car takes was actually moving. Three new gotchas: CSRT on small plates,
relative bed levels, and image-sequence holes.

## 2026-10-01 — Detour-3 v5 / 4K final

- Body-comp section (5:27–6:01): the InBody machine card was replaced by Shoaib's HyperFrames glass
  stat cards (`animations/slot_glass_bodycomp`), re-rendered natively at 4K and baked into the
  IMG_3321 prep by `prep4.py` (`kind: glass`).
- The 1.25x badge from Episode 2 is reused for 5 s at 0:34.7, with a dark backing for the white
  wall (`build/gfx_badge.py`, baked into the IMG_3279 prep, `kind: movie`).
- Final: render.py final mode at `--height 2160`, then `mix_music.py` on `clips_graded`.

## 2026-10-03 — James Jani study (craft only)

Two 17–19 min James Jani essays taken apart shot by shot (`yt-dlp` 720p, `scene>0.25`, contact
sheets of every shot, caption word timings, librosa hit/silence pass). The craft went into
`storytelling.md` §10 and the index. The detector overcounted ~2× on 24 fps film in a 60 fps
file and on particle effects, a new gotcha. The script findings and beat tables live in the
private channel-kb (`07-research/james-jani/`).

Same day: added Saqlain Khan's "The Education Trap" (Hindi, 6.1M views) as `storytelling.md`
§11, the face-led counterpart: question-led face cuts, slow digital pushes, and in-shot change
instead of cuts. Tool gaps it exposed: an animated push (`zoom_to`), a one-word `stamp` card
kind, a seam template in the mix, and a structural SFX palette (`effects/` is all foley today).

**Built the same day: `ranges[].zoom_to`**, an animated push-in in `render.py`. It uses
`zoompan` on a 2× frame, so a whole-pixel window lands as 0.5 px and a ~1%/s push doesn't
step. The output matches static siblings exactly (size, frames, rate, SAR), so the `-c copy`
concat holds. Measured on Episode 2's IMG_3665 (16.1 s, 1.00→1.15): 1.035 / 1.075 / 1.110 /
1.150 at 4 / 8 / 12 / 16 s against 1.037 / 1.075 / 1.112 / 1.149 expected, and it concats
with a static range. Two traps: `crop` can't animate w/h (evaluated once), and an explicit
`setsar=1` made the pushed segment's SAR differ from its unset-SAR siblings, so don't set it.
Tests: `tests/test_render_push.py` (201 pass).

**Also built: the `stamp` card kind** (`helpers/cards.py`, `cards_runtime/`). It's one word or figure in a
glass pill. It lands as its phrase is said (`LEAD`, not `CARD_LEAD`), holds 1.8 s, and can sit
top-left, top-right or top-center. The width comes from a Helvetica Neue Bold advance table in
Python, because the mask pass draws no text and must still match the silhouette. Rendered on
Episode 2's IMG_3665 with a 1.00→1.12 push: the HyperFrames check passed and the pills sit clear
of the face. Tests: `StampTests` (208 pass).


## 2026-10-03 — Podcast Episode 1: inventory, transcription, story read (no cut yet)

First reconnection-podcast episode (two-hander, ~2h35m of conversation in three 4K HLG clips
plus a re-shot 14s welcome). Language checked first (whisper `-l auto` on a mid slice → `hi`
p=0.94), then Deepgram `--language multi` on all 8 clips (~$0.80). Found and verified a new
trap: **Deepgram dropped ~20 min of real speech** (63 gaps of 5s or more at speech-level RMS). The
gaps were filled for content with whisper translate, and the gap-file pattern is recorded in
`gotchas.md`. Also: the diarization label for the same person flipped between clips (S0 was the
host in clip 1 and the guest in clips 2-3). Strategy proposed to the user and not yet approved
(Hard Rule 11). Story notes are in the session's `edit/project.md`, not here, because this repo
is public.

Same day, later, while Shoaib was away (he asked me to make the cut decisions myself):
- **The gap-fill worked.** Re-running Deepgram `multi` on the dropped gaps as short slices
  recovered 3379 words, and a second pass on the remaining holes added 735 more. The text matched
  the whisper translations. Two holes in the cut remain, about 30 s with no transcript.
- **render.py: a static `zoom` now crops the SOURCE before the downscale, and `zoom_y` was
  added.** Before, a 2x single from 4K at 1080p was an upscaled 960x540. New tests in
  `tests/test_render_zoom_crop.py`: the new order scores 60.3 dB PSNR against a direct crop and
  the old order 35.1 dB, with the bound at 50. The tests fail on the old code. 212 tests pass.
- **Cut v1 (309 shots, 69.7 min):** speaker-following singles and a two-shot carved from the 4K
  wide. QC found 50 camera cuts with speech under the fades. Fixed by placing cuts only in quiet
  fade zones and merging back-to-back story ranges (gotchas.md). v2 has 307 shots, and all 194
  camera cuts have a fade-zone level of −32 dB or lower.
- v1 QC also found an odd output rate, `114057/3802`, carried from the iPhone source. v2 renders
  with `--fps 30`.

## 2026-10-03 — Two YouTube-growth videos (The Studio, Think Media) → distribution.md §12

Shoaib asked what could be learned from <https://youtu.be/Puny-2wkMZA> (The Studio, MKBHD's
team) and <https://www.youtube.com/watch?v=AV4r2Qixb1Y> (Think Media). **Verified how:** the
caption endpoint returned 429 again (json3 and vtt, default and `web_safari` clients), and the
signed-out transcript panel never loaded. So, with Shoaib's OK, I downloaded the audio and
transcribed it with local whisper-cli (`ggml-small.en`, 3.0K and 6.2K words).

**Tooling note:** The Studio's video carries auto-dubbed audio tracks (Hebrew, Malayalam), so
plain `-f 139` fails ("Requested format is not available"). Select the original with
`-f "ba[ext=m4a][format_note*=original]/ba[ext=m4a][language^=en]/ba[ext=m4a]"`. That picked
the 128 kbps `140-*` tracks (13.7 MB and 30 MB), more than estimated. Fine for whisper.

The channel-specific reading (the strategy triangle, applying outlier inversion and trend
theory to our own stories, unfair advantages, brand foundational words) went to channel-kb:
`07-research/youtube-growth-advice.md`, plus the playbook (§1.12–14, §3.26), the idea bank, the
short-advice format and `04-learnings.md`.
- **v2 QC, then v3:** v2 rendered clean (306 cuts, no clicks, only the slate frozen, −14.0
  LUFS). Then a caption-style sample showed "…designer. Senior". The quiet-spot search for
  touching tokens could step past the next word's timestamp, so it is now bounded by the
  neighbouring word. A speaker-motion check found 3 singles (45 s) showing the wrong person
  (gotchas.md). Both fixed for v3.
- **render.py: caption word selection.** A word is captioned only if at least half of it is in
  the cut, after clamping same-speaker timestamp overlaps. `tests/test_render_caption_words.py`.
  213 tests pass.
- **Captions:** made a Devanagari vs Roman Hinglish A/B of the cold open for Shoaib. Wrote a
  hand transliteration of all 804 Devanagari words in the cut (`edit/captions/roman_map.py`),
  with ASR place-name fixes (कपूर तला → Kapurthala, रोत तक → Rohtak). The builder is
  `edit/captions/build_captions.py A|B`.
- **Evening: Shoaib picked caption style A** (Devanagari + Latin) and added 45 DSLR clips. Built
  `ranges[].video` in render.py (picture from a second camera, audio stays on the iPhone source;
  `tests/test_render_video_source.py`, 216 tests pass). Synced with audio cross-correlation and
  validated against the camera clocks; 38 clips usable. Then subject/steadiness per 0.5 s, and a
  colour-matrix fit on matched materials. The cut uses the DSLR for 30 shots (4.9 min) from 18
  clips. Captions are now built before the render from frame-snapped durations
  (`max(1, round(d × fps)) / fps`, which is exactly what extract_segment does), to be checked
  against the real segments.
- **2026-10-04: context pass after Shoaib's review of v4.** Statements were starting mid-thought.
  A mechanical edge audit (31 starts and 24 ends flagged of 112) plus a full source-context read
  (~20 lines answering cut material) led to merging back-to-back pieces, starting at true thought
  starts and finishing sentences. 112 → 94 story ranges; 69.7 → 80.5 min. paper.py anchor
  matching now ignores nukta (Deepgram's precomposed ज़ vs typed ज+़ failed 3 anchors). Lesson in
  gotchas.md.
- **render.py: true-peak limiter after loudnorm** (`TP_LIMITER`, −3 dBFS). v4 and v5 both
  overshot to about +1 dBTP after AAC. `tests/test_render_loudness_peak.py`; 218 tests pass. v5's
  audio was re-normalised from `base_preview.mp4` without a re-render.

## 2026-10-04 — Figuring Out FO556 study (podcast craft), into storytelling.md §12

Shoaib asked what a big podcast does that podcast Episode 1's preview (no music, sound effects
or graphics) lacks. Took Raj Shamani × Huberman (2:46:56) apart:
- 720p `yt-dlp`. The en-orig auto-captions downloaded fine this time, with no 429.
- Frame-diff cut detection at 12 fps.
- Contact sheets: 1 fps over the intro, one frame per shot over a full chapter.
- Overlay scans: bright pixels, and content in the normally black corners.
- Pause-floor audio pass, and high-band energy at overlay onsets against 40 random moments.

Finding: the intro holds all the production, and the body is plain multicam with no music.
New gotcha: `scene>0.25` *under*counts on a dark set (62 vs 802 cuts). Our v5 already cuts at
4.4/min against their 4.0–4.8. The proposed intro rebuild and body additions are in the episode's
`edit/reference_FO556.md`, awaiting Shoaib's go-ahead (Hard Rule 11).

## 2026-10-05 — Episode 3: inventory and transcription

Inventory of `Editing/episode3`. 51 A-roll clips, 15.6 min, all 4K HLG at 29.97 fps, single
chair frame, upright (a frame was checked per clip). One byte-identical duplicate (`IMG_3783 2.mov`,
md5) was excluded. There's no separate tight cold-open take, so the close-up will be a 4K crop.
Deepgram `en` ran on 50 clips, with whisper small.en as the cross-check in a separate edit dir
(new note in helpers.md: the shared `transcripts/` path makes `--force` overwrite the paid
transcript). Word counts agree, and there's no Hindi or Spanish. Both engines misheard the same 5
words ("thought of the day" came out as "third of the day"), so whisper agreement does not clear
a caption: Indian-English school vocabulary still needs a human read. Per-episode notes are in
`episode3/edit/project.md`.

## 2026-10-05 — Podcast Episode 1 v6: FO556 intro + body grammar, the show's graphics

Shoaib approved the FO556-derived plan (storytelling.md §12). Built:
- **A produced 2:32 intro.** Hook → white flash → credentials (Shoaib to camera, plus his
  voice-over over Deepak b-roll via `ranges[].video` from the conversation sources) → 8-teaser
  question/answer montage, ending on a line that lands on silence → Shoaib's name line →
  flash → the welcome hug under an UNFINISHED title card.
- **Kinetic captions** in the hook and montage only, two-tier, with the key phrase in the
  brand accent. One `.ass` file shared with Captions A (see gotchas.md).
- **Body:** 24 reaction cutaways (Shoaib's backchannel when there is one, else a silent
  listening beat; never inside the turn) and 7 wides on laughs (see gotchas.md, laughs).
- **Graphics:** stamps on the credentials; name lower thirds and the title card as PIL
  ProRes 4444 overlays at 1080; a 16 s end-screen source clip (`build/podcast_gfx.py`).
- **Music:** one track for the intro bed, title sting and end bed, from Episode 2's mixer
  method (`build/mix_music.py`). Nothing under the conversation.
- **21 chapters.**

Found: Deepgram's duplicate-phrase ghost clipped "designer" at the Microsoft reveal in v5
(gotchas.md). Renders and QC are in the episode's `project.md`.
- **2026-10-05, later: Episode 3 picture lock v1.** Shoaib approved the strategy. The cut has 52
  ranges and runs 8:20.7: Scene 4 at 1.10x from prepped sources, slow pushes at ~1%/s capped at
  1.18x, 3 punch-ins, the 2019 clip for 3.13 s ungraded, and a 6.5 s end card. **render.py now
  takes a per-range `grade`** (`segment_grade()`; `tests/test_render_segment_grade.py`, 5 pass).
  Self-eval on the 1080p preview: all 52 segments are 1920x1080, with 0 frame-count mismatches,
  0/51 pops and one freeze, the end card (expected). Reading the cut back as prose caught a
  dropped "me". The range table caught two same-take split bugs (new note in gotchas.md, under
  the camera-angles entry). `coverage.py` shows 2.0 events/min with the longest static stretch at
  67.5 s, as expected before cutaways and cards.
- **2026-10-05: Episode 3 v2, from Shoaib's review.** Leaning-in takes were optically soft, which
  was verified 1:1 in the source. Fixed with `cas` at output size, push caps and a gentler
  cold-open crop. Three holds showed him reaching for the mic, and the motion profile placed
  `out_at`. Both lessons are in gotchas.md and index.md. Re-checked on the render: 0/51 pops,
  and every hold measures motion ≤0.6.
- **2026-10-05: Episode 3 v4, the full visual and sound pass.** It has 16 word-anchored cutaways,
  11 cards (a new list `scale` option, used for a BODY · MIND · VOICE corner tracker), 2
  locators, the badge, and music beds with three seam thuds. Lost in Thought's own melody stem
  is the Scene 5 "thin pad". Re-composited from the existing segments (`build/recomposite.py`
  refuses if `ranges` changed), which takes minutes instead of 25. Verified 0/51 pops, and
  unscored windows checked against the no-music control by pause floor. **coverage.py does not
  count glass cards, stamps or graphics as events**: it reported an 82.9 s static stretch that
  held 3 stamps, a stat card and a locator. (Suspicion, not fixed: worth teaching it the `cards`
  and `graphics` blocks.)
- **2026-10-05: Episode 3 delivered at 4K** (`final.mp4`, 8:15.7, 2.49 GB, −14.2 LUFS, 0/51
  pops). Shoaib dropped a filler cutaway; that rule is now in memory: a cutaway must show the
  line, otherwise ask for a picture or use a stamp. New `build/resume_extract.py` for stopped
  renders, plus a gotcha on the background-job limit and the ffprobe trailing comma.
- **2026-10-05: fixed the glass-card spine overflow** (Shoaib's note on Episode 3). Each spine now
  grows with the next row instead of appearing with its own. Verified on a HyperFrames render of
  a 3-row card; `SpineTests` added; 230 tests pass. Episode 3's delivered `final.mp4` was rendered
  before the fix and still shows it (Shoaib: fine for this one).

## 2026-10-05 — Pre-delivery review + cross-video mistakes ledger

Shoaib: three full rewatches of a 90-minute cut cost about 4.5 hours, and he still misses
things on the second and third watch. He asked for (1) automation, so a delivered preview is
near-final, and (2) a common memory of every mistake, across all videos, to check against.

Built:
- **`kb/mistakes.md`**: 26 entries from podcast Episode 1, Episode 2, Detour-2 and Detour-3,
  each with Saw / Cause / Check (AUTO id or READ item).
- **`helpers/review.py`**: render checks T1-T7, story-edge checks C1-C10, graphics G1-G2,
  a watch-list, and a changes reel against the previous version. 13 tests.
- **Rules** in CLAUDE.md ("Before any preview reaches Shoaib"), SKILL.md step 7, and the
  kb/index.md map.

First real run, on podcast Episode 1 v7:
- 60 HIGH flags before calibration, mostly false positives.
- After calibration, 15 HIGH. Of those, 2 were genuine misses Shoaib had not reported yet:
  the second half of a question at 6:10, and a clipped "है" at 34:32 (M007).
- 5 were accepted with a written reason.
- The rest were reclassified (filler trims, punctuated endings), then 0 HIGH.
- 23 changed edges went into the reel for Shoaib, instead of an 89-minute rewatch.

## 2026-10-06 — Editing study: Aprilynne Alter and Kallaway → storytelling.md §13

Shoaib asked for the concept *and* the editing (motion graphics, music, sound effects) of
<https://youtu.be/659t-D3e0Z0> and of Kallaway's <https://youtu.be/3y-WiiUaqb4> (concept
studied 2026-10-05). Both were downloaded at 720p with his OK (137 MB and 82 MB, scratchpad only).

**Verified how:** the method is in §13. Two traps hit and fixed along the way:
- `librosa.load()` on the `.mp4` fell back to audioread and **silently returned 86 s of a 21-min
  file**. Every level from that run was wrong. Decode to WAV with ffmpeg first, then load the WAV.
- A transient detector fires ~88/min on speech consonants alone, so "40% of cuts have a
  transient" is chance (~35%). Measure the **lift against random moments** instead; the real
  answer was no lift at all.

Channel-specific reading in channel-kb: `07-research/aprilynne-alter.md` (new) and
`07-research/kallaway.md` §7. Script-stage rules in its playbook.

## 2026-10-06 — Built the Kallaway graphics language: keyline, deck, annotate, silhouettes

Shoaib adopted Kallaway's style as the house look and asked for all four missing pieces before
Episode 4.

**Built:**
- `cards.py` and `cards_runtime/glass.{js,css}` gained three kinds: `keyline` (a typed key
  sentence + sub-line + glow bar, with no glass and so an empty mask), `deck` (a returning chapter
  deck: done dimmed, current lit on its phrase) and `annotate` (an image with box / highlight /
  callout marks in image fractions). There is a new brand key, `glow` (default `#8B5CF6`), so
  `accent` and Episode 3's existing cards are untouched.
- `render.py` gained `silhouettes` (`resolve_silhouettes`, `build_silhouette_filter`): a black
  figure plus a rim built from the matte, an optional crowd, and one 16×16 `geq` alpha ramp.

**Verified how:**
- 270 tests pass (new: `test_cards_kallaway.py`, 19; `test_render_silhouette.py`, 7).
- Real HyperFrames renders of all three kinds on 24 s of 1080p footage: the layout audit passed,
  every element landed on its phrase per `report()`, and frames were read.
- A real silhouette on a real `matte.py` matte (6.5 s for 24 s; 8.8 s with the crowd).
- A burned two-line caption in Episode 3's exact `force_style` under a keyline: no collision.

**Found along the way:**
- **House captions are NOT where the render.py default says.** Our episodes use `MarginV=30`
  (not the default 90, which is tuned for vertical) with 8 words per chunk, so a two-line cue
  occupies y ≈ 856–968 at 1080. Kallaway's lower-left spot (≈ 840–970) collides with it, hence
  the keyline's default bottom of 800. Check caption geometry before placing anything low.
- render.py's composite always maps `0:a`, so a test base without audio fails with ffmpeg
  exit 234 and no visible message (stderr is captured). Give test bases a silent track.
- The crowd silhouettes read as blobs on a matte that includes the mic and chair (Kallaway's
  footage). Expect better on a clean head-and-shoulders, but look before keeping `crowd_at`.
- zsh: `rm -f f_*.png` with no matches aborts the whole `&&` chain (`no matches found`).

## 2026-10-06 — Podcast Episode 1 final: the goodbye and the end screen (M027, M028)

Shoaib, on the final:
- **The pool clip on the end screen, and why it was there.** Replaced by the episode's own
  handshake (IMG_3464 @ 3795.6), held as a still with a slow push.
- **1:29:20 to the end was all on his single.** The goodbye now moves to the wide from "So from
  me, from him" (`wide_from`). It holds past "Let's go" to 3799.5, through the handshake and
  standing up (`hold_to`, asserted to stop before the next word).

New check G3 in review.py: a multi-person piece must not end on a single. It flags the old
final and passes the fix, and is pinned by 2 tests (15 in the file). READ item R8: the last
30 s and the end screen.

The final was re-rendered with the resume wrapper. A segment is reused when its range is
identical to the approved final's range at the same index and its source has not changed.

## 2026-10-07 — False-start check C11 (M029)

Shoaib caught a restart at 1:29:05 of the podcast Episode 1 final. A first version of C11 (any
4-word repeat within 12 s) flagged 80 places on the full cut, nearly all natural Hinglish
emphasis or one speaker echoing the other. That was useless. It was narrowed to the same
speaker, a pause of 1.5 s or more between the attempts, and a repeat within 15 s. That flags
exactly Shoaib's one case. Pinned by 4 tests (19 in `test_review_edges.py`).

The cut: 3770.18 → 3778.18, keeping Deepak's "बक्चोदी करो यार." and resuming on "So yeah, as he
said…". The final was re-rendered via resume_final (PREV = review/final2), under `caffeinate`.

## 2026-10-11 — HDR audit: how iPhone HLG footage is handled (no code changes)

Shoaib asked how the repo handles iPhone 17 Pro HDR (HLG). Read-only audit of every encode
site, plus ffprobe and matched frames on two deliveries: podcast Episode 1
(`IMG_3464` @ 251.397 vs `Unfinished_Ep1_Deepak_FINAL.mp4` @ 3154.233) and Episode 2
(`IMG_3664` @ 8.86 vs `final.mp4` @ 201.196). Each frame pair was matched against the rendered
segment.

- Every iPhone source is HLG (`arib-std-b67`, `bt2020`, 10-bit). render.py tone-maps it to Rec.709
  per segment via `TONEMAP_CHAIN` (zscale `npl=100` + hable). This is a real conversion, not a
  relabel: saturation 0.32 → 0.47 on the podcast frame.
- Podcast export: tags `bt709` ×3, consistent with the pixels.
- Episode 2 export: `transfer` and `primaries` are **unknown**. Cause: ffmpeg 9 ignores
  `-color_trc/-color_primaries` (new gotchas.md entry, with verified fixes), and the concat
  copies segment 0's header from an untagged prepped card.
- Look: `npl=100` puts midtones ~10-15 luma below a reference conversion (`npl=203`, mobius):
  133.7 vs 144.7 on the podcast frame, 129.3 vs 143.8 on Episode 2. Not changed; it is a look
  decision for Shoaib.
- Comparison PNGs were written to the session scratchpad only.

## 2026-10-11 — Colour decisions: new tone-map, no default grade, exposure check, bt709 stamp

Shoaib's decisions after the HLG audit and the IMG_3833 / IMG_3836 comparison:

1. **`TONEMAP_CHAIN` changed to `npl=203` + `tonemap=mobius`**. The rest of the chain is
   unchanged. Midtones are ~10-15 luma brighter on every shoot measured, and red clipping went
   from 0.9-2.0% to 0.1-0.3%.
2. **The Episode 2 grade is retired as a default.** Indoor talking heads get no grade, or a
   light one inside guardrails: p5 >= 20, white balance never from clothing, saturation <= 1.0,
   red clipping < 0.5%. Written into SKILL.md "Color grade" and gotchas.md. The code default
   was already no grade; the Episode 2 string had spread by copying it into Episode 3's EDL.
   Episode 3's EDL was not touched (delivered).
3. **New `helpers/exposure.py`**, called by render.py after the first segment (of up to 6) that
   shows a face. It reports frame mean/p5/p95, face luma (mediapipe face detector in
   `retouch-env`) and red clipping. It warns on p5 < 20, a face > 15 luma under the frame mean,
   red clipping > 0.5% and grade saturation > 1.0. It never fails a render. `--no-exposure-check`
   turns it off. On the old-chain test segments it flagged exactly what the comparison showed:
   p5 3.7 / 8.1 under the Episode 2 grade, and 0.5% / 1.0% red clipping with no grade.
4. **bt709 stamped on every output.** The concat and the copy path add `h264_metadata`, and the
   composite ends in `setparams` after the subtitles (Rule 1 holds: it is tags only). This
   replaces output flags, which ffmpeg 9 ignores.

Verified:
- Full suite 297 passed (21 new in `tests/test_render_color.py`, including real-ffmpeg tagging
  tests).
- An end-to-end render in the scratchpad (untagged lavfi card as segment 0, then both test
  clips): `base.mp4` and `final.mp4` bt709 ×3, base and final framemd5-identical. The exposure
  report ran after segment 1 (p5 23.3, face 113.9 vs frame 102.5, red 0.32%, ok).

Not yet done: no real episode has been re-rendered with the new chain. Re-renders of old
projects will look brighter, and must re-extract every segment rather than resume.

## 2026-10-11 — Episode 4 test frame (IMG_3837), checked before the shoot

Shoaib's proposed Episode 4 setup. Rendered three 2 s segments through render.py
(new tone-map, no grade).
- Exposure check `ok` on all three: frame mean 117-121, p5 29-33, face 128-133 (brighter than
  the frame), red clipping 0%.
- Audio clean: noise floor -66 dB, peaks -10 dB, no spatial track.
- **Captured at 1920x1080, where IMG_3833 and IMG_3836 (same phone, same day) were 3840x2160.**
  No room for push-ins or punch-ins without upscaling, and no 4K delivery.
- Face sharpness (Laplacian variance on the face, resized to 256 px, measured at 1080 output;
  method in gotchas.md "Locked focus"): IMG_3837 median 30.6, IMG_3833 31.7, IMG_3836 80.6.
  The two softer clips have the larger face (~265 px vs ~240), i.e. a closer camera.
  *Unproven: focus or distance vs. resolution as the cause.* IMG_3833 is 4K and just as soft.
- Both clips carry `com.apple.quicktime.cinematic-video-intent=1`, so that tag does not tell
  Cinematic mode apart.

IMG_3838, the 4K retake (3840x2160 HLG + DV8, 16 s):
- Exposure `ok` three times (p5 26-32, face 121-127 against a frame mean ~118, red 0%).
- Audio: noise floor -66 dB.
- **Face sharpness is still about half of IMG_3836's.** Same measure at 1080, 16 samples per
  clip: IMG_3838 median 33 (26-44), IMG_3836 median 65 (30-109). Compared at the same face
  width (~238 px), IMG_3838 scores 36 and IMG_3836 66, so distance alone does not explain it.
  Within each clip, the smaller the face (further from the lens), the sharper it is: IMG_3836
  scores 98-109 at 214-222 px and 30-37 at 250-254 px. That is the Episode 3 locked-focus
  pattern. Suspected cause: focus set behind the speaking position. *Unproven* until a
  focus-locked retake measures better.
- **Correction:** the first pass reported "75 when leaning back". That list dropped frames
  with no detected face, so the 75 was matched to the wrong timestamp. Always print the
  timestamp next to each sample.

## 2026-10-12 — Episode 4 footage sorted into a-roll / b-roll / outtakes

The folder was delivered twice. The first delivery was 106 files (53 MOV + 53 AAE, Cinematic
`IMG_`/`IMG_E` pairs). It was sorted, then **replaced**: by 11:24 the folder held a flat 45
files with no subfolders, no `IMG_E` twins, no AAE, and no Core Media Auxiliary (depth) stream.
That is the set sorted here. The earlier `edit/inventory.md` was gone too.

Classified by 3 frames per clip (contact sheet) plus a free whisper pass
(`ggml-small.bin -l en`, 4 in parallel, ~37 min of audio). No paid transcription.
- `a-roll/` 36 desk takes, 26.4 min. `b-roll/` 4: IMG_3898 note at the desk, IMG_3899 bed +
  laptop (29.97 fps), IMG_3901 overhead of the notes (extra `apac` track), Flow_VID 6 s portrait
  SDR wall from another camera. `outtakes/` 5: setup tests 3837 (1080p)/3838/3840, false starts
  3842/3883. Count checked: 36+4+5 = 45.
- Per-clip table, retake groups in story order, and edit notes in `episode4/edit/inventory.md`.
  Flagged there: 3893 teases the back injury for the *next* episode, but 3872/3874 tell it in
  this one; the monitor shows a Golden Gate wallpaper in 3850-3854 and code everywhere else.
- Setup tests and false starts were put in `outtakes/` without asking, to keep them out of a
  batch transcription. Swappable by moving files.

## 2026-10-12 — Episode 4 a-roll transcribed (Deepgram `en`), Hindi asides dropped

Shoaib OK'd transcribing `a-roll/`. `transcribe_batch.py` is wired to ElevenLabs (unconfigured),
so `transcribe_deepgram.py --language en --edit-dir episode4/edit` ran per clip, 4 in parallel.
36/36 succeeded; `takes_packed.md` packed 186 phrases, 22m49s. No Spanish, no Devanagari, one
speaker per clip.
- **`en` was the wrong choice.** It was picked because the whisper `-l en` pass read as fluent
  English, but that mode translates Hindi. A loudness scan of every pause of 1.5 s or more
  found 20 at speech level (−23 to −37 dB) in 8 clips: 3848, 3853, 3854, 3861, 3877, 3878,
  3887 and 3890. Six were checked with whisper `-l hi`; four are Hindi ("arey ye solve kaise
  hogi", "ab bahut ho gaya"…). Lesson folded into gotchas.md and index.md.
- **Fixed, with Shoaib's OK:** re-ran those 8 with `--language multi --force`. The `en`
  versions are kept in `edit/transcripts_en_backup/`. Words: 1765 → 1949 (+184; 3854 34 → 53,
  3853 438 → 499). 7 of 8 rose; 3848 lost two "uh"s and nothing else. 22 packed lines now
  carry Devanagari, and there is still no Spanish. The gap re-scan left 4 at speech level, and
  all 4 are hesitations or breaths: whisper `-l hi` gave noise or a held "aaa", and Deepgram's
  words either side are identical in both versions.
- Caption fixes noted in `episode4/edit/inventory.md`: "internचाला" → Internshala,
  "उत्तराय" → Uttarayan, garbled "फिर मैं विशाह" at 3877 ~2:09.
- Residual risk, *unverified*: the other 28 clips stayed `en`. The gap scan found no holes in
  them, but a Hindi word transcribed *in place* as English would not leave a hole.

## 2026-10-12 — Episode 4 v1 picture lock: plan, cut, captions, review

Shoaib asked for the plan and then the edit, without a pause between them. The plan is in
`episode4/edit/plan.md`; each content default in it is marked and reversible.
- **Cut:** `episode4/edit/build/cut.py`, from Episode 3's, with every edge derived from word
  timings. 93 ranges, 14:54 plus the end card. The zenith (Suma's note) lands at 11:15. The script
  targeted ~8 min: 1,370 written words became ~15 min of kept speech once fumbles were out. That
  ratio is now a data point for the script playbook.
- **New in the cut builder:** each edge snaps to the quietest 10 ms within 0.25 s, without
  passing the neighbouring word's midpoint. Ranges that abut in the source are merged. Loud edges
  (> −32 dB) went 40 → 13, and the render then showed **0 pops (T4)**, so those 13 were
  touching-word joins, not clicks.
- **Every cut changes scale** (1.00 ↔ 1.12, push ~1%/s capped at 1.18). The zenith is static
  at 1.12. The cold open is a 1.25 crop from 4K. Holds were set from frame-difference motion
  scans: 3884 holds still until 9.1 s, so the locked line got its ~2 s silence.
- **Face sharpness:** 34–56 on every take (Episode 3's soft takes were 13–20). The setup test's
  softness did not carry into the shoot. No grade, and exposure `ok` (p5 36, face 132).
- **Captions:** `build/captions.py` copies the transcripts to `build/caption_src/`, swaps Hindi
  for English, fixes names and writes numerals, then calls `render.build_master_srt` on the
  real segments. The paid transcripts are untouched. Found the nukta NFC trap (gotchas.md).
- **B-roll:** two `ranges[].video` inserts. IMG_3899 (bed) under "lying down on bed,
  slouching" is reframed 1.3x right, because R4 found a readable whiteboard ("…— Kapil…") at
  1080. IMG_3901 shows Suma's note under "she wrote it on 19th January 2020". IMG_3901's first
  ~25 s shows the 2020 journal, which is held back for its own video, so that stretch is unused.
- **review.py v1:** T1/T2/T4/T6 pass; T3 is the end card; T5 is −14.9 LUFS (one-pass preview
  loudnorm). 4 HIGH edges were read and accepted (`review/accepted.json`).
- Re-rendered after the R4 reframe: review v1 has **HIGH 0** (4 accepted with reasons), T4 0 pops,
  and master.srt is byte-identical when rebuilt on the new segments. Delivered
  `episode4_v1_NO_MUSIC_do_not_upload.mp4` and `review/v1/watchlist.md` (editorial calls only).
  Not in v1: cards and stamps, music, the chapter deck.

## 2026-10-12 — Episode 4 v2: re-cut after Shoaib's review of v1

Shoaib on v1: cuts at bad places and mid-sentence, not natural; the best of the repeated lines
not picked; the note scene opens on waiting. Then, mid-rework: "not cutting sentences does not
mean you should not cut the fillers, it should look like a final product."
- **Ledger:** M042-M045 and READ R10 (retakes). review.py gained monologue mode, C12 sliver,
  C13 dead lead-in, C14 said twice, C15 edge-on-speech and `downgrade_tightening`, with tests
  (304 pass). On the v1 cut the new checks fire on exactly the problems he heard.
- **Rebuilt `episode4/edit/build/cut.py`.** Ranges are (take, first sentence, last sentence) from
  `build/sentences.py`. Edges sit in measured pauses with 0.20 s of air before and 0.28 s after.
  Long ranges get camera splits only at sentence pauses. A take table records every retake
  choice and why. v1's builder is kept as `cut_v1.py`.
- **`build/tighten.py`** removes fillers, stutters, listed restarts and dead pauses, only at
  quiet points. 125 removals. 18 fillers glued to a word were kept (no dip). Nine cuts were
  placed by hand from `build/valley.py`, because Deepgram's times were off. Two of my
  hand cuts were wrong and were caught by `build/verify_joins.py` (whisper at every join):
  "It…" (it removed "feeling") and "everything everything" (it cut inside the word). Fixed,
  and the stutter is kept.
- **Picture:** `build/jumps.py` measured jumps at a median of 4.0 against 0.44 for continuous
  motion. Visible jumps (≥ 3.0) alternate framings 10% apart. The note scene now opens on his
  first word (14.82 s, not 12.0).
- **Result:** 164 segments, 15:48 plus the end card (v1 was 14:54). review HIGH 0: 13 flags were
  checked by listening and recorded with reasons. The listening pass found no real word lost.

## 2026-10-12 — Episode 4 v3: Shoaib's notes on v2

Notes: 7:20 "started" missing; 9:19 a jump after "third interview"; 9:31 "What" missing; 11:21
the caption said "2020 one"; still frames at 11:43 and 12:22, and anywhere else; 14:12 "क्यों काम
करती है" cut early; the intro not crisp; why English-only captions instead of Hinglish.
- **Root causes.** 7:20, 9:31 and 14:12 were hand cuts at dips INSIDE words. v2's verifier
  transcribed both sides together, so whisper filled the gaps back in (M048). 9:19: removing the
  company name tore a run-on sentence, so the name is now kept as said. The still frames were
  scripted holds plus "beat" pauses (M046). The captions followed the script's "English
  captions" over the house Hinglish convention (M047; channel-kb playbook corrected). The 2021
  bug: Deepgram writes "twenty twenty one," with a comma, so the "2021" pattern missed it.
- **Changes in `episode4/edit/build`.** No holds, no beat pauses. Joins keep 0.15/0.20 s of
  air. Pauses shrink to 0.25 s (in a sentence) or 0.35 s (between sentences). A breath at −38 dB
  or quieter counts as dead air. The pause halves at picture splits are trimmed. Camera blocks
  (~22 s, alternating 1.00/1.12) are formed AFTER tightening. Cold open: a framing per line
  (1.25, 1.0, 1.40) with tight air. `stills.py` measures every quiet stretch: 24 over 0.7 s
  became 5 (section breaks, ~0.8 s). New `verify_sides.py`: 251 joins, each side transcribed
  alone. Every flag was a whisper mishearing of a short clip, confirmed from the levels. Result:
  253 segments, 14:54 + the end card.
- **review.py:** C16 still frame (audio-confirmed via `confirm_stills`), with tests (306 pass).
  On v2 it fires at both of Shoaib's timestamps plus four more holds. On v3: HIGH 0, with 17
  flags accepted after listening.

## 2026-10-12 — Episode 4 v4: grade, graphics, music, b-roll; the full ledger walk

Shoaib: keep the company name; add graphics and music; take b-roll from the global folder and
elsewhere (the MRI); a pasted note that the skin read oversaturated orange-red. He also asked
whether previews were checked against the mistakes list. **They were only partly checked:**
review.py ran every time, but the READ items were not walked, and Episode 3's own feedback
(holds, "random stuff", a readable book title, the card spine) had never reached the ledger.
Added M046 (first raised on Episode 3) and M049-M052, plus READ R11.
- **Grade** (`build/skin.py`, a vectorscope measure): skin was ON the skin line (123-125°) but
  chroma 37-41 under a warm balance. colortemperature 7200 + colorbalance gm 0.02 + saturation
  0.9 + a soft highlight curve gives skin 123-126° at chroma 29-33. Cooling alone swung skin to
  118° (magenta).
- **Cards:** 15 (4 decks, 6 stamps, a day list, an offers stat, a keyline, a three-things
  tracker), each read on a contact sheet. **B-roll** (`build/visuals.py`, overlays): 2017 college
  photo, Awaken reading clip, the MRI with its patient header cropped. The journal pages were
  not used (the journal has its own video).
- **Music** (`build/mix.py`): 7 beds and 4 hits, all phrase-anchored; the zenith, cold open and
  dark stretch are unscored. R6 found the beds ~8-10 dB too low; fixed (gotchas.md).
- **Captions** R2: five audible words dropped; fixed with `keep_drifted` (gotchas.md).
- Final: `episode4_v4_preview.mp4`, −14.2 LUFS / −1.3 dBTP, HIGH 0, 0 pops, one freeze (the end
  card). The ledger walk is recorded in `review/v4/ledger_walk.md`.

## 2026-10-13 — skills/motion-graphics-pass (from Episode 2's final_mgx.mp4)

Episode 2's motion-graphics pass was built in a claude.ai session on 2026-10-12 (39 cue sprites in pycairo,
the routine glass card, 14 caption cues replaced by patches from `base.mp4`, 75 SFX from
`effects/structural/`, composited in 20 s chunks onto `final.mp4` → `final_mgx.mp4`). Shoaib asked for the
same process in this repo, so it is now a vendored skill: `SKILL.md` (process + the design judgment),
`scripts/mgx.py` (pipeline CLI), `scripts/mglib.py` (primitives + components), `examples/episode2/cues.py`
(the full pass), `references/` (as-built record, blueprint, format, toolkit).

Verified by re-running the generalized scripts against Episode 2 (Linux VM, ffmpeg 4.4, python 3.10):
sprites byte-identical to the delivered ones (fork and spawn), a composed chunk PSNR ∞ against the delivered
chunk, the SFX bus sample-identical, `verify` on final_mgx.mp4: 16194/16194 frames, 540.340 s, A/V offset
0.0334/0.0330, −14.2/−14.2 LUFS. **Not yet run on this Mac** (ffmpeg 9, uv, macOS spawn): first use should
run `still` and one `compose --chunks` before a full pass. New finding while building it: the audibility
check (M052) shows 42 of Episode 2's 75 effects buried under the voice.

## 2026-10-13 — Epidemic Sound sourcing added to the motion-graphics skill

Shoaib connected the Epidemic Sound connector and asked that SFX and music always be the apt one: local library
first, connector when nothing local fits. Added `mgx.py library` (name/tag search over effects/ + music/, sidecars
included) and `mgx.py fetch` (downloads a signed asset URL, measures duration / hit / peak / centroid, writes an id
sidecar, prints the SFX_LIB line), plus `references/sourcing-audio.md`. Verified: connector search for SFX and music
works and DownloadSoundEffect returns a signed WAV URL on audiocdn.epidemicsound.com; `fetch` + `library` tested
with a file:// URL in the Linux VM (its proxy blocks the CDN, 403). **The real CDN download has not been run on
the Mac yet.**


## 2026-10-13 — Episode 4 v5: new b-roll + first motion-graphics pass on a new episode

- **B-roll (Shoaib's notes):**
  - book cutaway → `global-b-rolls/book_reading2.mov`;
  - the LinkedIn and GitHub screen recordings (`episode4/b-roll/`) are a new `screen` kind in
    `build/visuals.py`: cropped windows of one recording, joined, each pushing in slowly about a
    fixed point;
  - the 2017 hostel photo returns on "in that hostel room" (Shoaib confirmed it is the hostel).
- **Privacy (R4):** the GitHub sidebar email is cropped out of both shots. LinkedIn's
  "Open to work" and analytics boxes are cropped out.
- **Screen recordings read as freezes.** v5's first review flagged T3 at 0:27.8, 0:30.3, 0:31.9 and
  3:02.5: the recordings sit perfectly still for seconds at a time. A 1.03–1.08 push per part
  fixed it; the re-run flags only the end card.
- **motion-graphics-pass, run on Episode 4** (`edit/mgx/cues.py`, `edit/motion_graphics_blueprint.md`):
  - 22 cues + 1 vignette + 34 SFX;
  - no caption replacements; every cue carries unspoken information;
  - three motifs: the semester chart, the confidence meter, the note glyph;
  - anchors use a `T(phrase, near)` helper over `cards.kept_words` that refuses an anchor that
    moved more than 1.5 s.
  - **The stills loop caught three problems:** "Solved" clipped, an empty chart card, and the
    figure's head over its label. It also caught a zero-scale cairo matrix on the first frame of
    a pop, now fixed by a `scl()` guard.
- **mgx.py fixes:** `count_frames` (ffprobe 9 trailing comma) and vignette fades across chunk
  seams. Both are in gotchas.md.
- **SFX ceiling 0.93 → 0.84 for this episode:** 0.93 measured −0.4 dBTP after AAC (T5); 0.84
  gives −1.3. The skill default may want the same change. Unproven on other episodes.
- **Lost a render to a stray ffmpeg** after `pkill` on the Python wrapper (gotchas.md).
- **Caption fix:** "Nisway" → "Niswey" (his LinkedIn spelling) in `build/captions.py`.
- **Delivered:**
  - `episode4_v5_preview.mp4`;
  - `review/v5/reel.mp4` (3:24 of changes, 720p, under the 30 MB phone limit);
  - `review/v5/watchlist_shoaib.md` and `ledger_walk.md`.
  - review.py: HIGH 0, T1–T6 pass except the end-card freeze. mgx verify: frames, duration and
    sync identical to the master, −14.2 LUFS.
- **4K final (Shoaib approved v5, 2026-10-13):**
  - Steps: `visuals.py 2160`, then `render.py --height 2160 --fps 30 --no-loudnorm`, then `mix.py`,
    then the mgx pass in a separate work dir (`edit/mgx_final/`, cues copied with MASTER/BASE/OUTPUT
    switched to the 4K files). The v5 preview's `mgx/` stays intact.
  - Timings on this Mac: 4K segment extraction ~2 h for 253 segments (sequential, ~50% CPU);
    4K cards + composite ~50 min; mgx at S=2: 12 s sprites, ~10 min compose.
  - Delivered `episode4_final.mp4`: 3840x2160 30 fps, 37.6 Mbps, bt709 x3. mgx verify: 26829/26829
    frames, identical sync, −14.2 LUFS. review.py: HIGH 0, T5 −1.3 dBTP, T3 only the end card.
  - R4 rescanned at 4K: LinkedIn and GitHub crops show only public profile fields, no email.
- **Speed badge (Shoaib, 2026-10-13):** "SWITCH TO 1.25X", Episode 3's `gfx_badge.py` at 5.0 s, from 0:11.8 (the first line after the cold
  open). Added to the 4K final through a new mgx `MOVIE_LAYERS` option, then `compose --dirty speed_badge`.
  That recomposed one 20 s chunk (10 s), then mux. Verify passed again. Frames checked at 11.9 / 12.6 / 15.0 / 16.7: readable over
  both the hostel photo and the face, gone before the first graphic at 17.2.
- **Cleanup:** the intermediates went to `~/.Trash/episode4_intermediates_2026-10-13` (30 GB), not a hard delete:
  - the 4K no-music and pre-mgx files, `base*.mp4`, `clips_*`, the v1–v5 renders, the mgx work dirs (cues.py kept)
    and the card `renders/*.mov`, which render.py regenerates.
  - Kept: `episode4_final.mp4`, the EDL, build/, transcripts, master.srt, prepped/, the card projects, review/, the blueprint.
- **Music remix (Shoaib, 2026-10-13: "background music little on the higher side"):** measured two Kallaway references against
  Episode 4 with a demucs split (storytelling.md §8b). Beds went from 16 to ~28 dB under the voice, with a hook lift to ~12 dB.
  The final's audio was swapped with the picture untouched. The previous final is in the Trash as
  `episode4_final_v5levels_music16dB.mp4`.

## 2026-10-14 — kb/shooting.md: the camera and lighting setup

Shoaib asked why his face looked unclear on the published videos. Tested 2026-10-09 to 10-11 on
clips IMG_3632–IMG_3838 (setup walkthrough, monitor on/off, five light placements, 1x vs 2x,
1080p vs 4K), measuring face vs frame luma on matched regions. Result: a diffused key at ~45°,
2x lens, 4K 30, dark monitor, mid-tone top. Written up as `kb/shooting.md`; the tone-map and grade
side was already in gotchas.md (2026-10-11).


## 2026-10-14 — Episode 4 Shorts: the first two, cut from the 4K a-roll

Shoaib confirmed two moments from Episode 4 (channel-kb `03-formats/shorts.md` candidates, and the
script's own `[SHORT]` marks), and chose **English captions for Shorts** (asked first because it
contradicts M047; recorded as the Shorts exception in mistakes.md and memory). The note reading
(the zenith) was left out: it stays out of Shorts while the long video is new.

- **`episode4_short_interview.mp4`** 55.2 s: "I got my first shot at the interview" → LeetCode
  medium never seen, solved → "never done programming" → CEO "कितने चाहिए?" → 15k → "this is the
  first step." Hook text "3 years. Zero code."
- **`episode4_short_money.mp4`** 59.4 s: 12 LPA ask → rejected → "It was because of the money" →
  6 LPA → 7.5 LPA two days later → "I never called them back." Hook "My first salary negotiation".
- Both 1080x1920 30 fps bt709, -14.0/-14.1 LUFS, review.py HIGH 0 / MED 0 (18 flags checked and
  written to each Short's `review/accepted.json`), T1-T6 pass.
- **Build:** `episode4/edit/shorts/build.py` (ranges + face-centred crop → `<name>/edl.json`),
  `captions.py` (English SRT on the draft's measured cue times), `finish.sh` (render, gain to
  -14 LUFS, review). Rebuilt from the a-roll, not cropped from `episode4_final.mp4`: the final
  has captions and side cards burned in, and a 9:16 crop catches pieces of them.
- **Edges:** reused the long cut's approved ranges where whole. Seven new edges, each placed in
  the quietest 10 ms (`build/valley.py`) and checked by whispering each side alone (M048). Two
  needed it: "so I got" has no valley, and the start that reads "I got" exists only in a
  50 ms window (95.55-95.60); and "Then I called" moved from a -27 dB start to a -35 dB one
  0.2 s earlier, which still opens on "Then".
- **Length:** money was 63 s on the first EDL, then 60.4 s after frame rounding. Brought under 60
  with cuts, not speed: a repeated "second day as well" line, a 0.7 s pause inside a range, and
  an audible "uh" that Deepgram does not list (found because review's C16 said the "held" tail
  was not quiet).
- Phone previews (720p, ~19 MB) as `phone_preview_*_do_not_upload.mp4`.

## 2026-10-14 — Episode 4 Shorts v2: "they look very plain" (M053), and the interview re-cut

Shoaib called v1 plain. True, and I had called it fine on a clean review.py. The long video carries
cards, effects and a bed in exactly these windows, and the Shorts dropped all of it (M053). He then
sent four notes for the interview Short. All four are applied in `episode4/edit/shorts/build_v2.py`:
the strongest line first ("Throughout my three years…"), a big thumbnail-style plate held 3 s
("FIRST INTERVIEW. / NEVER CODED."), the Hindi repeat and the restart cut, and two versions to test.
- `interview/episode4_short_interview.mp4` 24.4 s, ends on "offer in December" (punch-in 1.25).
- `interview_long/episode4_short_interview_long.mp4` 45.4 s, to "this is the first step".
- Treatment (both): glass stamps from the long video (LEETCODE · MEDIUM, NEVER SEEN IT,
  SOLVED · 30-35 MIN, ₹15K A MONTH) at scale 0.68; the long video's bed for the scene (Felt Like
  November), +14 dB under the plate, dead stop on the punch-in line with a soft hit; the long
  video's click and hit on LeetCode/solved; 2-3 word ASS captions in Avenir Next Heavy with the key
  word in #F25435 and a small pop (`captions_v2.py`); alternating 1.0/1.12 framing.
- review.py: HIGH 0 / MED 0 on both, G4 pass, -14.1/-14.2 LUFS. Every join was read back by
  whispering the render. That caught "So yeah, he he said": a repeated "he" sat after the pause
  I had cut. Fixed by starting on "said" (200.25).
- **Repo changes, with tests (314 pass):**
  - `cards.py`: stamps take `scale`, and a stamp wider than the frame now raises. On 9:16 the
    1080-unit stage is 607 units wide, so v2's first draft clipped "LEETCODE · MEDIUM" off the left edge.
  - `review.py` G4: an EDL with `parent` flags any parent card whose phrase it keeps without
    carrying a card. Replayed on money v1, it flags the dropped Offers stat.
- Money Short v2 is not cut yet: the matching re-cut was proposed to Shoaib first (Hard Rule 11).
- **Money Short v2** (Shoaib confirmed the plan and chose the hook, 2026-10-14):
  `money/episode4_short_money.mp4`, 56.6 s.
  - It opens on his push-back ("नहीं, my interviews were very good. If it was because of money,
    please tell me."), which is then dropped from the story so it is not said twice. Plate:
    "I ASKED FOR 12 LPA. / REJECTED."
  - Punch-in 1.25 on "It was because of the money." The split points sit in -65/-67 dB valleys,
    so render.py's 30 ms fades on the abutting ranges fall in silence.
  - The long video's cards for these moments: a 12 LPA stamp (anchored on Deepgram's "well LPA"),
    REJECTED, and the Offers stat 6 → 7.5 at scale 0.75 (G4 checks it).
  - The long video's S6 bed: Power of Freedom, out from "Then next day she called me back"
    through the payoff, back in sync on "I still remember" with a soft hit. Its drop sound on
    "I'm rejected".
  - Review: HIGH 0 / MED 0, -14.2 LUFS. Whisper read the whole render back cleanly. A doubled
    "I just left it" at the end was the English model hallucinating on the Hindi line; the
    multilingual model confirms "फिर इनको call नहीं किया कभी मैंने".
- **Shorts cleanup (Shoaib approved, 2026-10-14):** he picked the 24 s interview version. 1.1 GB of
  intermediates went to `~/.Trash/episode4_shorts_intermediates_2026-10-14` (not a hard delete): bases,
  clips, drafts, no-music controls, v1 renders, phone previews, card render caches and the unused
  45 s interview render. Kept: the two upload files, and every EDL, caption file, plate, script and
  review report, so either Short (or the 45 s version) can be re-rendered.

## 2026-10-14 — `skills/shorts/`: the Shorts build turned into a reusable skill

Shoaib asked for the Shorts build scripts to be pushed. They lived in `episode4/edit/shorts/`
(not a repo, and full of Episode 4's lines), so they became `skills/shorts/` (general code only)
plus one `short.json` per Short in the edit dir.
- `scripts/shorts.py`: `words | build | plate | captions | render | mix | review | preview | all`.
  It derives the render geometry from the source (not hardcoded 4K), takes HDR or SDR, reads
  effect names from the motion-graphics-pass table, resolves phrase anchors with `after`/`shift`,
  and supports `"src": "sync"` bed drop-outs.
- **Equivalence, verified:** rebuilding Episode 4's three Shorts from their specs gave identical
  EDL ranges, cards and captions, byte-identical plates, a byte-identical interview mix, and a
  money mix whose audio matches the delivered file exactly.
- **Found on the way (verified, cause unproven):** the mix's ffmpeg graph is not bit-reproducible
  run to run after the LAST effect's stream ends. Running the ORIGINAL v2 script twice on one input
  gave two different tails: one -80 dB, one a -29 dB peak / -54 dB RMS from 53.27 s. It is
  identical before that point. Recorded in gotchas.md.
- `tests/test_shorts.py` (11). The old per-episode scripts and artifacts went to
  `~/.Trash/episode4_shorts_intermediates_2026-10-14/old_scripts/`.

## 2026-10-14 — skills/shorts now hands picking, writing and titles to the youtube-agent plugin

Shoaib pointed out that `/youtube-agent:yt-shorts` already exists. It is writing guidance only (no
scripts); our skill builds the video. `skills/shorts` SKILL.md step 1 now hands picking, the opening
line, the on-screen text and the loop to yt-shorts. It notes our one difference: no new
recordings, so the strongest line already said is moved to the front. It also scores openings with
yt-script's `hookscore.py`, and lints the title against the plate with yt-package's `title.py`.
- **title.py caught my own mistake:** the interview title I suggested ("…in my first interview") repeated
  the plate's words, which the channel rules forbid. The replacement "3 years without code, then a
  LeetCode medium in 35 minutes" scores 98/100.
- hookscore ranked all five Episode 4 opening candidates WEAK (21-40), and Shoaib's chosen money
  hook scored lowest of the openings (25). The tool says it barely separates hits from misses, so it is
  recorded as a relative signal only, with no change made.
- environment.md maps all 11 plugin skills, and which ones have scripts, onto our workflow.
- **Shipped (Shoaib, 2026-10-14):** both Shorts handed over for upload, with titles linted by
  `title.py` against their plates. Interview: "3 years without code, then a LeetCode medium in 35
  minutes" (98). Money: "HR said my interviews were bad. 2 days later: a better offer" (84). The
  rejected money candidate "Lost an offer over money" claimed more than happened.

## 2026-10-14/15 — Shorts for Episode 2, Episode 3 and podcast Episode 1 (six, awaiting review)

Shoaib picked the moments from my candidates (Hard Rule 11; zeniths and withheld images excluded):
Episode 2 "the 20 cm", Episode 3 "6 AM gym", and four from the podcast (Kapurthala, merit list,
6 AM → Microsoft, Bangalore lift); "fuck it" is bleeped (his choice). Specs in each parent's
`edit/shorts/<name>/short.json`. Every Short: review.py HIGH 0 / MED 0 after `accepted.json`, T1-T5
pass, G4 pass, whisper readback (English model, or Hindi `-tr` for the podcast), a frame sheet, and
titles linted by yt-package `title.py` (80-98).
- **Episode 2** `episode2_short_height.mp4` 45.1 s. Moved hook "The detail that still gets me…";
  the long video's ruler cue carried as a 150 → 170 cm stat; Breathing Woods bed (the parent's,
  synced) drops out under the reveal, as in the long cut.
- **Episode 3** `episode3_short_gym.mp4` 40.7 s. Hook "Most of the people around me… asleep by
  ten"; the 2019 gym clip re-cut vertical; 10 PM / 6 AM / 8 AM stamps; alarm effect and bed from
  the parent; punch on "not over them, but over myself".
- **Podcast** 32-40 s each, framed per speaker at 1.6/1.8 (punch 2.0) from the 4K wide, English
  captions translated from the Hinglish, Kikoru bed from the episode's intro.
- **skills/shorts changes** (tests 11 → 18, all 18 pass; full suite passes): relative parent source
  paths; per-range filter/grade/audio_filter inheritance (nearest own-camera range when only a DSLR
  range overlaps); a spec range's own audio_filter now wins (it was silently dropped, so the first
  bleep render still had the word at -22 dB); `who: left|right` speaker framing, half-frame only;
  vertical `broll`; a build-time stop when a card would land under the opening plate (it did on
  three podcast Shorts); `edges` (tight edges to read); `sfx` (per-frame effect audibility vs an
  effect-free control). `exposure.detect_faces` returns every face.
- **Found while checking (verified):** six clipped Hindi words ("लिए", "academy", "पकड़ी", "था",
  "secondary", "सीधा") from snapping to the EARLIEST quiet zone after a Deepgram word end that ran
  early; caught by the edges scan plus level profiles, each fixed and re-checked. One fix was wrong
  ("रगड़ा होगा" extended into Shoaib's "तो guys") and was reverted after a whisper of the join.
- **Not proven:** effect audibility on the podcast Shorts. The bed fills the conversation's gaps,
  so the effect-free control runs +20 to +35 dB and `sfx` can't separate effects from it. Levels
  match the Episode 2-4 Shorts' settings; judge them by ear.
