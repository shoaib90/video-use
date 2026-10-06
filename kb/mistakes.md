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

**M024** · Episode 2 · *A graphic anchored to a word that had been cut landed on a silent frame.*
Check: graphics/cards raise on a missing anchor. Read the resolution printout (`READ R3`).

**M025** · Detour-2 · *A portrait clip played stretched in a landscape concat.* Check: `AUTO T1`
(every segment has the same dimensions and rate).

**M026** · podcast Episode 1 v3 · *3 singles (45 s) showed the wrong person.* Cause: a folded
backchannel kept its neighbour's speaker label. Check: majority-speaker relabel in the episode's
make_edl.py; `READ R5` (contact sheet of singles against who is speaking).

## Sound

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

## Openings & packaging

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
  right, the anchor landed on the right line.
- **R4** Scan frames at delivery resolution for readable labels, screens and plates.
- **R5** Look at a contact sheet of singles and check the shot shows whoever is speaking.
- **R6** Spot-listen at each music cue entry, exit and duck.
- **R7** Watch the first 15 s: picture from frame 1, the promise by ~0:10, no "last time".
