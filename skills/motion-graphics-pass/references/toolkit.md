# Toolkit: which component for which beat

Everything below is in `scripts/mglib.py` and was used on Episode 2. Each entry names the Ep 2
cue to read in `examples/episode2/cues.py`. Coordinates are design units (1920×1080). Boxes:
`LEFT` (20,140,760,690) is the left-third sprite box, `TOPL`/`TOPR` hold the corner pills and
locators, and a custom box is fine (keep it tight; it is the sprite size).

| Beat | Component | Ep 2 cue(s) | Notes |
|---|---|---|---|
| Cold open or punchline on black: the line itself | `kinetic(c, t, lines, size, y0, gap, tout, acc=, pad=)` | `co1`, `co2` | words land on their onsets; `acc` words in accent; `pad` leaves room for quote marks. Replace the caption cues. |
| A word whose meaning is the episode's argument | quote marks dropping around it (`bo` overshoot) | `co2`, `responsible` | reuse the exact treatment when it comes back |
| The thesis | `stamp(c, t, l1, l1b, swap_at, show, hide, shake_at)` | `cant_fail`, `okay_fail` | hard cut in plus a 2-frame shake. The payoff re-uses it with `l1b` and `swap_at`: strike, write-on, recolour |
| A correction ("let me correct myself") | pill + `strike` + crossfade to the corrected text | `ep1` | pairs with a YouTube i-card to the earlier episode |
| Clean vs messy, simple vs complicated | morphing path (line → scribble) | `knot` | no text; pure abstraction |
| "Over a year", accumulating time | a row of dots filling one by one | `knot` (12 months) | unhurried, linear, no overshoot |
| Place + time not said aloud | `locator(c, txt, t, tin, dur)` | `loc_gandhinagar`, `loc_college` | matches the house locator style, top-right |
| A small concrete object in the story | small illustration on the b-roll | `coin` | check glyphs; Helvetica Neue has no ₹ |
| X vs Y, "nothing came closer" | two bars, one overflowing the card | `bars_fc` | labels can be words when they are one-word chart labels |
| "Just an X, closer to a Y" | struck word → big word + underline | `religion` | replaces the caption cue |
| Distance / journey | route line with two pins and a traveller dot | `route` | can hand off into a list card |
| Generations, family, "the first one" | dot grid, one dot lit with a ring | `generations` | text labels small and muted |
| Weight, pressure, expectations | `weight_stack(c, t, slabs)` | `hopes`, `boards` | slabs drop and squash; reuse to stack more weight later |
| A lonely / unsupported moment (setup) | `disc` + a single grey dot | `lone_dot` | almost nothing; the emptiness is the point |
| Its payoff ("find a person") | the same disc, a second warm dot, ring closes | `two_dots` | must be gone before the zenith |
| Labels put on a person (fearful, shy) | `chip` stack slapped in, then a `meter` | `labels` | suppress the caption cues the chips repeat |
| "Underneath all that…" | the stack slides away and a glyph glows | `labels` (ball) | a glyph, never the withheld photo |
| Scores, before/after numbers | vertical bars + a rolling counter, colour shift on the drop | `scores` | header swaps (Year 1 → Class 9) |
| Other people's voices / pressure | `bubble` × N at the frame edges, accelerating, then jitter + collapse | `bubbles` | Hinglish, not his words; never over the face |
| One supportive voice | a single warm `bubble` with a tag | `papa` | calm: sine ease, no overshoot |
| "No rest in between" | alternating blocks whose gaps close | `no_rest` | hard cut out before the next big image |
| Height, growth, a measured change | `ruler(c, t, cm, extra)` | `ruler_a`, `ruler_b` | hide it while real b-roll shows the same thing |
| "Didn't watch a single match" | stat card of zeros | `matches` | top-right over a dark b-roll |
| A film or event as a time marker | text-only ticket stub that tears | `ticket` | never a poster or likeness |
| An emotional collapse | vignette layer (`VIGNETTES`) | n/a | the only treatment allowed on a peak |
| A phone call | call pill with ring pulse → timer → "Call ended" | `call` | animate to the existing ring and hang-up SFX |
| "120%", going past the limit | bar past a 100 tick | `over100` | |
| A quote from someone in the story | quote card, his words verbatim, attribution | `coach_quote` | replace those caption cues; hard cut on the line's sound |
| A door closing, an ending | black panels closing in over b-roll | `door` | full-frame sprite; the cut clears it |
| Chapter / section reset | `pill(c, x, y, label, t, tin, tout, tag=)` | `takeaway`, `next_ep` | use at the start of long A-roll stretches |
| "Don't X" being rejected | muted text + red `strike` | `dont_quit` | |
| Fear following him everywhere | an icon row with a red dot hopping between icons | `everywhere` | icons, not the spoken words |
| What something cost | chips that tip over and fall | `cost` | reuse the earlier chips |
| Next-episode promise | pill + meter refill + an audience of dots on glass | `next_ep` | start the dots a beat early so they read |
| End card with end-screen room | black patch + tagline lifted to y≈30% | `endcard` | match the original fades |

Animation tokens used throughout:
- entries `eo3` 0.35–0.45 s with a 10–16 px rise;
- exits `ei2` 0.25–0.35 s;
- landings `bo(x, 1.4–1.8)`;
- calm beats `sio`;
- stamps a hard cut.
