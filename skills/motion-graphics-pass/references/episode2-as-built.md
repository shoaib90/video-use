# Episode 2: the pass as built (the quality bar)

"I Gave Up My Biggest Dream at 15" · `final.mp4` 3840×2160, 29.97 fps, 9:00.37, picture
locked at session 5 → `final_mgx.mp4`, delivered 2026-10-12. The cues are
`examples/episode2/cues.py`; the approved plan is `episode2-blueprint.md`.

Shoaib's reaction: *"you have taken the video from where it was to a level where I was not
thinking of."* This file records what produced that, so the next pass starts from it.

## What shipped

- **39 cue sprites.** Kinetic type, cards, locators, stamps, motifs and the call pill.
- **The routine glass card.** It was built 2026-10-01 but never composited into a delivery.
  This pass added it from `animations/slot_glass_routine/renders/`, with real blurred glass
  under it.
- **14 caption cues replaced, in 8 windows:** the cold open, "religion", "I can't fail", the
  two label cues, “responsible”, the coach's quote, and "It's okay to fail".
- **The "The academy, 15 km away" locator was removed** and replaced by the Home → Academy
  route graphic.
- **One vignette:** "it just emotionally crashed me".
- **75 sound effects** from `effects/structural/`, mixed under the existing mix.

## The design spine (the part to copy)

1. **The cold open became typography.** The black-frame captions were replaced by centred
   kinetic type built word by word on each onset, with "gave up" in the accent. On
   "responsible", quote marks drop around the word. That sets up the episode's argument, that
   the "responsible" choice was the lie, before the title card.
2. **The thesis stamp and its payoff.**
   - "I can't **fail**." hard-cuts in at 3:15 in red, on dark glass in the left third.
   - At 7:25 the same stamp returns in the same place. On "okay", "can't" is struck out,
     "It's okay to" writes in, and "fail" turns from red to cream.
   - This is the move that makes the episode feel designed rather than decorated.
3. **The motifs:**
   - quotes around “responsible” (0:09 → 5:10);
   - lone dot → two dots (3:16 "no one to put a hand around my shoulder" → 8:07 "find a
     person");
   - Confidence meter 60→0 (3:43) → 0→100 (8:43 "how I built that back");
   - weight slabs: Expectations (3:09), then Class 10 boards (4:15).
4. **Unspoken information instead of repeated words:**
   - "Gandhinagar, 2004";
   - "13 years" running 2013 → 2026;
   - "Matches watched 0 0 0";
   - the relatives as Hinglish bubbles that crowd the frame edges, then jitter and collapse
     on "That started to mess with my head";
   - Papa's single warm bubble, "Continue." That beat keeps the family from reading as
     uniformly against him.
5. **Animating to existing sound.** The coach call pill rings with the existing ring, runs a
   timer, and turns red ("Call ended") on the existing hang-up beeps.
6. **Restraint:**
   - the zenith (8:16.34–8:24.66) has nothing;
   - the 20 cm window has only the ruler and one tick;
   - "emotionally crashed me" has only a vignette;
   - the photographs stay full-frame and untouched.

## Changes from the blueprint, and why

- **Dropped:** the battery icon inside the routine card (that would have meant changing the
  card's render), crowd murmur and a piano note (not in the library), and real backdrop blur
  on the new cards (only the routine card's glass is real blur).
- **The dot field moved into a glass card** and starts on "stand in front" instead of
  "hundreds". On the wall it was illegible, and it was only visible for 0.5 s.
- **The cricket ball is a glyph, not the photo** (project.md: the photo is withheld until 5:03).
- **The ₹5 coin reads "5 RUPEES".** Helvetica Neue has no ₹ glyph.

## QC that the stills loop caught (fix list from the real pass)

- Quote marks sat on top of the neighbouring words. Fixed by padding the quoted word
  (`kinetic(pad=…)`).
- The stat card was clipped by its sprite box. Fixed with a taller `TOPR`.
- The ruler's red marker crossed its own scale labels.
- The cricket-ball seam was drawn outside the ball. Fixed by clipping to the circle.
- The dot field was illegible on the wall and on screen too briefly.
- The `no_rest` cue referenced a variable inside the wrong scope and crashed. Stills catch
  code errors too.

## Delivery checks (measured on final_mgx.mp4)

- **Picture:**
  - frames 16194 / 16194;
  - video duration 540.340 s, both files;
  - A/V offset 0.0334 / 0.0330 s.
- **Sound:** loudness −14.2 / −14.2 LUFS; audio present.
- **Encode:**
  - 35 Mbps H.264 (the master is 40.7);
  - x264 `faster` at CRF 15, 20 s chunks;
  - PSNR ∞ against an independent re-run of the same chunk.

## Sound effects: what the audibility check found afterwards

Run after delivery: effect energy against the programme, in the bins holding 70% of the
effect's energy. **33 of 75 effects cleared −10 dB.** Median per kind:

| clearly audible | borderline | buried under the voice |
|---|---|---|
| pluck +48, drop +34, hit_soft +32, boom +26, thud_soft +17, thud_heavy +17, whoosh_dry +8, whoosh_soft +6, riser_soft +4, dip +3 | tick −1, drain −6, click −9, swell_rev −11 | scratch −17, tap −18, paper_slide −20, pop_ui −21, tick_soft −24, knock_soft −26, stamp −27, whoosh_air −34, paper_tear −35, riser −43, shimmer −47, pop_glass −56 |

**The lesson:** under continuous speech, a UI-type effect at −18..−30 dB peak is gone.
- Impacts work at those levels because they live below the voice's band.
- For the rest, either raise them to roughly −6..−10 dB peak, move them into a breath, or
  cut them.
- Fixing this is a `sfx` + `mux` job with no video re-encode.

## Timings (cloud VM, 4 cores, ffmpeg 4.4)

| step | time |
|---|---|
| 39 sprites | about 2 min at 4 workers |
| card glass, 1936 frames | 83 s |
| caption patches | 15 s |
| compose, 27 chunks | about 12 min; card chunks ~110 s each, the rest ~28 s |
| mux | 80 s |
