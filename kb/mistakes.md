# Mistakes ledger: every error Shoaib (or QC) caught, on every video

**Purpose.** Shoaib should not have to find the same kind of mistake twice. Every mistake that
reached him, or that QC caught late, gets an entry here. Each entry carries:
- **what he saw**
- **the root cause**
- **the check that now catches it**: `AUTO <id>`, a check in `helpers/review.py`, or
  `READ`, an item the agent must verify by eye or by reading before delivery

**The rule (CLAUDE.md, "Before any preview reaches Shoaib"):**
1. Run `helpers/review.py` on the render.
2. Clear every HIGH flag: fix it, or write down why it is fine.
3. Walk the `READ` items below.
4. Deliver with the review's watch-list, and with the changes reel when there is a previous
   version.

When Shoaib reports something new, add an entry **the same day**. If it can be automated, add
the check to review.py in the same change, with a test.

Format: `M###`, date, video, then: Saw / Cause / Check.

---

## Story & context (the cut itself)

**M001** · 2026-10-04 · podcast Episode 1 v4 · *Statements start in the middle; context lost.*
Cause: story ranges began after a non-sentence-final word, or on a line that answered material
that had been cut. Check: `AUTO C1` (IN after a non-final word) and `AUTO C3` (an opener like
तो/और/But/So whose referent was cut).

**M002** · 2026-10-05 · podcast Episode 1 v6 · *At 7:20 the cut lands mid-question ("what I have
seen for you was sports") without its setup ("growing up every kid has something special").*
Cause: the v1 audit only checked the single word before the IN. The question's opening
sentences each ended in a full stop, so the IN looked clean. 29 more cases were found the same
day. Check: `AUTO C2` (a "?" in the uncut speech just before the IN means the answer starts
without its question) and `AUTO C4` (a long uncut setup in the same turn), plus `READ R1`.

**M003** · 2026-10-05 · podcast Episode 1 v6 · *Ranges ending mid-sentence ("…हर", "so hungry कि
यार").* Cause: OUT points taken where the next word in the same breath was cut. Check:
`AUTO C5` (an OUT before the sentence ends, next word within 0.8 s) and `AUTO C6` (a dangling
function word at an edge).

**M004** · 2026-09-22 · Episode 2 (delivered) · *5 broken joins in a delivered cut: an OUT on a
word's start dropped the sentence's last word, and joins skipped the words carrying the
meaning.* Check: `READ R1` (read the assembled cut as prose), plus `AUTO C5`.

**M005** · 2026-10-05 · podcast Episode 1 v5 · *"designer" cut off at the Microsoft reveal.*
Cause: Deepgram returned one spoken phrase as two copies, the first squeezed into ~0.08 s words.
The text anchor matched the ghost copy. Check: `AUTO C7` (ghost duplicate words within 1.5 s of
an edge).

**M007** · 2026-10-05 · podcast Episode 1 v7 · *(caught by review.py, before Shoaib) an OUT at
34:32 clipped Deepak's "है" mid-word.* Cause: Deepgram squeezed his "लग गई है" into ~0.08 s words
under Shoaib's overlapping echo. RMS showed continuous speech (−22 dB) at the cut. Check:
`AUTO C7`, which fired on the first real run.

**M006** · 2026-10-04 · podcast Episode 1 · *A cut put 30 s of speech missing from the
transcript inside the cut.* Cause: Deepgram `multi` drops 6-18% of long Hinglish audio.
Check: `AUTO C8` (a transcript gap of 5 s or more inside the cut, so it plays with no captions
and was never read).

**M029** · 2026-10-07 · podcast Episode 1 (final) · *A false start was left in: at 1:29:05 Shoaib
starts "यार तो as he said, बक्चोदी करो and हम भी.", stops, and 6 s later says "So yeah, as he said
बक्चोदी करो और…" properly.* Cause: the range kept the whole outro, and nothing looked for
restarts. Check: `AUTO C11`: the same speaker says a 4-word run, pauses at least 1.5 s, then says
it again within 15 s. Echoes by the other person and emphatic repeats without a pause are not
flagged. On the full 89-minute cut the check found exactly this one (an earlier, looser version
flagged 80 natural repeats).

**M042** · 2026-10-12 · Episode 4 v1 · *"Cut at bad places, in between sentences, not sounding
natural."* Cause: edges were placed at Deepgram word times, which drift by 0.1-0.7 s, so cuts
landed on onsets and tails. A one-word sliver from an abandoned attempt was spliced in, and
every jump got a scale change. review.py flagged 26 joins as MED, and they were not read.
**Then, on the v2 rework, Shoaib: "not cutting sentences does not mean you should not cut the
fillers, it should look like a final product."** So the rule is not "never cut inside a
sentence". It is: **cut fillers, stutters, restarts and dead pauses, but only at measured
silence or a sharp dip (≤ −38 dB), leaving ~0.15 s of air, and verify by listening.**
Check: `AUTO C15` (any edge where material is removed must be quiet in the source), plus
`AUTO C5` in monologue mode (real words removed inside a sentence are HIGH, a removal of only
fillers or pauses is LOW). Plus Episode 4's `build/verify_joins.py`: whisper the assembled
audio at every join, and confirm that the words beside it, and any real word Deepgram places in
the removed gap, are still heard.

**M043** · 2026-10-12 · Episode 4 v1 · *A one-word splice: "It" from an abandoned attempt + 2.6 s
cut + "was July 2019…".* Cause: the range list used word timings without noticing that the
first "It" belonged to the restart. Check: `AUTO C12` (a story range of 2 words or less, or under
1 s, is HIGH).

**M044** · 2026-10-12 · Episode 4 v1 · *The note scene opened on ~3 s of him waiting with the
note before he spoke.* Cause: `in_at` was set early, on purpose, to show the note being opened,
without checking how it plays. Check: `AUTO C13` (more than 1 s before the first word of a
range is HIGH; accept it in accepted.json only when the action is the point).

**M045** · 2026-10-12 · Episode 4 v1 · *Lines said several times; the best take was not chosen.*
Cause: retakes were chosen by first-seen or by length, without comparing the candidates.
Check: `AUTO C14` (the same 7-word run kept twice in the cut), plus `READ R10`: for every line
with a retake, compare all candidates (complete sentence, no restart or filler, delivery) and
record the pick and why in the episode's take table.

**M046** · 2026-10-12 · Episode 4 v2 (first raised on Episode 3 v2, never logged) · *Still frames: "at 11:43-11:44 there is this still frame after
the statement is complete"; 12:22-12:25 "looks like forgot the lines… these kind of things I would
not expect you to miss."* Cause: deliberate holds (`out_at` 1-2.4 s past the last word, from the
script's "hold still" marks) and "beat" pauses kept up to 1.4 s on static shots. On a locked-off
talking head a held face reads as a frozen picture, not a beat. **Rule for every video: no holds.
End each line on a clean cut (≤ 0.2 s of air), and keep no wordless stretch over ~0.7 s in a shot,
including the zenith and the close.** A pause for weight needs a picture change (a cut, a
punch, b-roll), never a held face. Check: `AUTO C16`: held more than 0.8 s past the last word, or
more than 1.2 s with no word inside a shot, confirmed against the source audio so word-time
drift doesn't fire it. On v2 it fires at both of Shoaib's timestamps and four more. Plus Episode
4's `build/stills.py`, which lists every quiet stretch over 0.7 s in the output timeline.

**M047** · 2026-10-12 · Episode 4 v1-v2 · *"Why have we kept English-only subtitles? Earlier we
were keeping Hinglish Devanagari subtitles."* Cause: the episode script said "the edit adds English
captions" for Hindi lines, and that was followed over the house convention without asking.
**Captions are Hinglish as spoken: Devanagari for Hindi words, Latin for English, in Kohinoor
Devanagari.** Fix only mishearings, names and numerals. Check: `READ R2` (captions), and a
script instruction that changes a house convention is a question for Shoaib, not a default. **Shorts are the
exception (asked, Shoaib chose 2026-10-14): English captions, Hindi translated.**

**M048** · 2026-10-12 · Episode 4 v2 · *Words clipped at hand-placed cuts: "So I start | my YouTube
channel" (7:20), "| If I can get 12 LPA" with "What" gone (9:31), "क्यों काम करती है" cut short
(14:12).* Cause: the cut points came from Deepgram word times and dips that were really *inside*
words, and the verification transcribed both sides of the join TOGETHER, so whisper's language
model filled the missing syllables back in ("So I started"). Check: Episode 4's
`build/verify_sides.py` transcribes each side of every join ALONE and requires the edge word
whole. Plus `AUTO C15`. Never trust a cut-point word timestamp: read the levels, then listen to
each side alone.

## Captions

**M010** · 2026-10-03 · podcast Episode 1 · *A caption showed a misheard word ("Sex है" for "Sexy
हां").* Check: `AUTO C9` lists the lowest-confidence words in the cut, so they are read before
delivery (`READ R2`).

**M011** · Detour-2 · *Spanish words burned into Hinglish captions* (Deepgram `multi` drift).
Check: `AUTO C10`.

**M012** · Detour-2 · *Captions drifted 0.6 s by the end of a 30-segment cut.* Cause: offsets
summed from EDL floats instead of frame-snapped segments. Check: `AUTO T2` (real vs predicted
segment durations, and cumulative drift).

**M013** · Detour-2 · *A caption showed a word that is never heard.* Cause: an end rounded past
the next word's start, and caption selection is by overlap. Check: render.py's ≥ half-a-word rule
(tests), plus `READ R1`.

## Picture & graphics

**M020** · 2026-10-05 · podcast Episode 1 v6 · *The stamp read "24 SSBS".* Cause: stamps render
in caps, so a lowercase plural becomes a typo. Check: `AUTO G2` (card or graphic text that changes
meaning when upper-cased).

**M021** · 2026-10-05 · podcast Episode 1 v6 · *Old-photo polaroids placed over a face.* Cause:
the side was chosen by the speaker's label, not measured on the framing. Check: `AUTO G1` makes a
contact sheet of every overlay and card at its midpoint, which must be looked at (`READ R3`).

**M022** · Detour-2 · *The picture froze on an overlay's last frame.* Cause: `setpts`-placed
overlays drain ahead of the timeline. Check: `AUTO T3` (freezedetect, d=1.0).

**M023** · Detour-3 · *A serial number was readable on a box label.* Check: `READ R4` (frame-scan
anything with a label at DELIVERY resolution).

**M054** · 2026-10-21 · Episode 5 v1 · *The eyebrow toward the key light rendered white; on the
iPhone both are black.* Cause: iPhone clips are Dolby Vision 8.4 (HLG base + RPU). render.py's
`TONEMAP_CHAIN` (zscale + mobius) maps the HLG base and ignores the RPU. Apple's player applies
it, so the specular sheen on the hair stays dark there. Verified on IMG_3967 @60 s, our chain vs
AVFoundation's `AVAssetImageGenerator`: ours whitens the brow and pushes skin more orange; npl
400, hable and desat do not fix it. Fix: iPhone sources go through `helpers/apple_sdr.swift` as prepped sources.
Check: `READ R13` (compare the first face segment against an AVFoundation frame of the same
time) until an automated check exists.

**M055** · 2026-10-21 · Episode 5 v1 · *The lifting cutaway showed him sitting with the dumbbells,
not pressing; the back-extension cutaway showed the machine setup, not a rep.* Cause: each
in-point was picked from 3 stills of the whole clip (20/50/80%), never from the 2-5 s actually
used. The reps were at 0:26-0:48 and 0:30-0:58. Check: `READ R3` now includes the START, MIDDLE
and END frame of every cutaway's own window (a 1 fps sheet of the source to pick the in-point).

**M024** · Episode 2 · *A graphic anchored to a word that had been cut landed on a silent frame.*
Check: graphics/cards raise on a missing anchor. Read the resolution printout (`READ R3`).

**M025** · Detour-2 · *A portrait clip played stretched in a landscape concat.* Check: `AUTO T1`
(every segment has the same dimensions and rate).

**M026** · podcast Episode 1 v3 · *3 singles (45 s) showed the wrong person.* Cause: a folded
backchannel kept its neighbour's speaker label. Check: majority-speaker relabel in the episode's
make_edl.py; `READ R5` (contact sheet of singles against who is speaking).

**M027** · 2026-10-06 · podcast Episode 1 (final) · *The goodbye ("…from me, from him, take care…
Alright, man. Thanks for coming. Let's go.") played entirely on Shoaib's single, so Deepak was not
in frame for the ending or the handshake.* Cause: speaker-following framing ran right to the last
word. A farewell is a shared moment, not a turn. Check: `AUTO G3` (the last talking shot of a
multi-person piece must be a two-shot or wide), plus `READ R8`.

**M028** · 2026-10-06 · podcast Episode 1 (final) · *"Why have we shown that pool clip at the end?"*
The end screen used post-session DSLR footage of a pool, which has nothing to do with the
episode's people. Cause: the background was chosen as "calm footage under the end-screen
elements". Check: `READ R8`. The end screen shows the episode's own people (Episode 1 now holds
their handshake as a still).

**M049** · 2026-10-05 · Episode 3 v5 (logged 2026-10-12) · *"Don't use random stuff, it should make
sense": a 2017 selfie on "I started getting some recognition".* Cause: a cutaway was picked to
break a static stretch, not because it showed the line. Check: `READ R11`: every b-roll, photo
and card must literally show or say what the line says. If nothing fits, use text (a stamp) or
ask Shoaib for an image.

**M050** · 2026-10-05 · Episode 3 (logged 2026-10-12) · *The glass list card's timeline spine
poked out below the card before its last row landed.* Fixed in cards.py the same day
(kb/gotchas.md). Check: `READ R3`, at a frame BEFORE the last row lands as well as at the midpoint.

**M051** · 2026-10-04 · Episode 3 (logged 2026-10-12) · *A book title was readable in b-roll (The
Intelligent Investor), which Shoaib didn't want on screen.* Check: `READ R4`, which covers titles
and covers as well as labels and screens.

**M053** · 2026-10-14 · Episode 4 Shorts v1 · *"They look very plain."* Both Shorts were a bare
talking head with white sentence captions and a grey drawtext hook box. The long video carries
graphics in exactly these moments: the LeetCode card, the "three years" chart, ₹15K and 12 LPA
stamps, the interview tally with the rejected X, and the 6 → 7.5 LPA offers stat, all with
effects, plus a music bed. The Shorts dropped every one of them. Cause: the Shorts were rebuilt
from the a-roll for a clean crop, and only the cut and captions were carried across. review.py
measures correctness (edges, sync, loudness), and its pass was reported as "fine". Nothing
compares a Short's treatment with its parent's. Check: a Short carries the parent's
graphics, effects and bed for the windows it keeps, re-laid out for 9:16, or the delivery says
why not. `AUTO G4` (an EDL with `parent` flags HIGH any parent card whose phrase it keeps
but carries no card for; it flags money v1's dropped Offers stat), plus `READ R12` for what G4
cannot see: mgx cues, effects and music.

**M056** · 2026-10-21 · Episode 5 v1 · *Captions broke into fragments ("go for surgery.",
"first job.", "introduced") all through the video.* Cause: render.py chunked captions per
SEGMENT, and the two-framing camera puts a segment edge at every switch, often mid-sentence:
62 of 391 cues had 3 words or fewer. Fix: `subtitle_style.span_segments` (2 of 318). Check:
`AUTO T8` (more than 5% of cues with <= 3 words).

**M058** · 2026-10-22 · Episode 5 Shorts v1 · *"They sound very slow."* Cause: the long cut tightens
every pause (build/cut.py + tighten.py), but the Shorts tool cut ranges with their pauses intact: 25-27% silence
and p90 pauses of 0.44-0.60 s, against Episode 4's Shorts (which performed) at 0.25-0.30 s with 0-1 over 0.4 s.
Speaking pace was never the issue (152-161 wpm, Episode 4's 162-183). Fix: tighten to the long cut's rules
(pattern `episode5/edit/shorts/tighten_short.py`), normal speed. Check: `AUTO P1` (review.py, derived cuts:
a pause over 0.70 s is HIGH, more than 1.5 pauses over 0.45 s per 30 s is MED; measured on the source audio,
so the bed cannot hide them). It flags both v1 Shorts and passes both v3s.

## Sound

**M052** · 2026-10-05 · Episode 3 v4 (logged 2026-10-12) · *Sound effects 17 LU under the voice were
inaudible* (no change in 2-6 kHz energy against the no-music control). Check: place an effect in
the pause before its line, or measure its band against the control (`READ R6`).
Since 2026-10-13 the motion-graphics pass measures this automatically: `mgx.py <edit> sfx` reports each
effect's energy against the programme in the effect's own bins and flags anything under −10 dB as BURIED.
On Episode 2's pass, 42 of 75 effects (UI pops, whooshes, paper, soft ticks at −18..−30 dB peak) were buried.


**M030** · podcast Episode 1 v1 · *50 camera cuts landed on speech: audible dips and clicks.*
Check: the cut-placement rule (a quiet fade zone ≤ −32 dB) plus `AUTO T4` (a sample-step spike at
each cut, compared with the segment's own interior).

**M031** · 2026-10-04 · podcast Episode 1 v5 · *True peak +1.0 dBTP, with 871 samples at 0 dBFS.*
Cause: loudnorm fell back to dynamic mode and the AAC encode overshot. Check: `AUTO T5`
(−14 ± 0.5 LUFS, true peak ≤ −1 dBTP).

**M032** · Detour-2 · *Music cues inaudible in one window and clipping in another.* Cause: one
global bed level. Check: per-window levelling in mix_music.py; `READ R6` (listen at each cue).

**M033** · 2026-10-05 · podcast Episode 1 · *(Shoaib's rule, not an error) no music or effects
under the conversation, only in the intro.* Check: `AUTO T7` (music presence in speech pauses
outside the allowed windows, measured against the no-music render) when `--raw` is given.

**M034** · 2026-10-07 · podcast Episode 1 · *Shoaib made his own small Resolve edit on
`final_raw.mp4`, believing it was the finished video. It had no music and sat at −20.5 LUFS.
He nearly uploaded it.* Cause: the pre-mix render had a name that read as final, and it sat
next to the real final. Check:
- The pre-mix render is named `*_NO_MUSIC_do_not_upload.mp4`.
- Delivery messages name the ONE file to upload.
- The edit folder never holds two files that both look final.

`READ R9`: when Shoaib edits a file himself, confirm which file it was built from.

## Openings & packaging

**M057** · 2026-10-22 · Episode 5 final · *The "SWITCH TO 1.25X" badge was missing.* Cause: it is
added in the motion-graphics pass (`MOVIE_LAYERS`), not by render.py, and Episode 5's cues.py started
from a config with no `MOVIE_LAYERS`. Check: `READ R7` now includes "the badge shows on the first
line after the cold open". Fix: Episode 4's `prepped/ov_2160/GFX_SPEED.mov`, `start=` the first line
after the cold open, then `layers`, `compose --dirty speed_badge` and `mux` (one chunk, about a minute).

**M040** · Episode 1 (talking-head series) · *95% → 52% retention in 8 s of silent black at the
open.* Check: `AUTO T6` (black or silence in the first 2 s).

**M041** · Episode 2 (delivered) · *Opened on a reference to the previous episode; the
title's subject is not said until 0:28.* Check: `READ R7` (is the title's promise on screen or
said by ~0:10?).

---

## READ items: what the agent verifies itself before delivery

- **R1** Read every story edge flagged by review.py **and** the prose of every changed join.
  Ask: does this start where the thought starts? Does it end where the sentence ends? Is the
  question it answers in the cut?
- **R2** Read the low-confidence word list (C9) against the audio or a whisper pass. Fix
  mishearings in the caption builder.
- **R3** Look at the overlay/card contact sheet (G1). Check: no face covered, text spelled
  right, the anchor landed on the right line, and every cutaway shows its ACTION at the start,
  middle and end of its own window, not just one still (M055).
- **R4** Scan frames at delivery resolution for readable labels, screens and plates.
- **R5** Look at a contact sheet of singles and check the shot shows whoever is speaking.
- **R6** Spot-listen at each music cue entry, exit and duck.
- **R8** Watch the last 30 s and the end screen. Everyone in the conversation is in frame for the
  goodbye, and the end screen shows the episode's own people or moment, never unrelated
  b-roll.
- **R9** Leave exactly one file in the edit folder that looks uploadable. Rename pre-mix and
  no-loudness renders `*_NO_MUSIC_do_not_upload*`, and name the upload file in the delivery
  message.
- **R10** Retakes (M045): for every line said more than once, list the candidates, pick the
  best (complete sentence, no restart, fewest fillers, delivery), and write the reason down.
- **R11** Every cutaway, photo and card shows or says what the line says (M049); none fills time.
- **R12** Shorts and other derived cuts (M053): list every card, mgx cue, effect and music cue
  the parent has inside the kept windows, and say for each whether it is carried, re-laid out or
  dropped, and why. A pass from review.py is not a verdict on how it looks.
- **R13** iPhone (Dolby Vision) sources: put one face frame from the render beside the same
  source frame from AVFoundation. Brows, hair and skin must match the phone (M054).
- **R7** Watch the first 30 s: picture from frame 1, the promise by ~0:10, no "last time", and the
  "SWITCH TO 1.25X" badge on the first line after the cold open (M057).
