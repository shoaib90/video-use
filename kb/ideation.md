# Ideation — where ideas come from, before the cut exists

`storytelling.md` covers how to hold attention once you have the material. This file is
**upstream of that**: how to decide what to make, and how to build a style that is
recognisably yours.

Sourced from three videos Shoaib supplied on 2026-09-23. Transcripts pulled with `yt-dlp`
(captions) and whisper.cpp where captions were rate-limited:

| # | Video | Channel | Length / views |
|---|---|---|---|
| V1 | [How to Create Content No One Else Can](https://www.youtube.com/watch?v=ttdBbHyK7yE) | Under The Radar | 9:48 / 208K |
| V2 | [Struggling With Ideas? Watch This Before You Start Editing in 2026](https://www.youtube.com/watch?v=T6VLsGIYqeQ) | Ritu Solanki | 8:52 / 94K |
| V3 | [How to generate the most Creative Ideas](https://www.youtube.com/watch?v=UZ_peeloxAA) | Nextcore | 2:00 / 1.87M |

**These are practitioner opinions, not measurements.** Nothing here is verified the way
`gotchas.md` entries are. It is recorded because all three converge, and because several
claims explain things we *did* measure on YT1. Where a claim touches our own data, the
connection is marked **[measured]**.

---

## The one claim all three make

**Creativity is recombination, not talent.** None of the three treats "be original" as
achievable, and V2 says so outright: *"originality is a lie."*

- V3's examples: Jobs combined touchscreen + phone + internet; Shakespeare borrowed plots;
  Dyson combined a vacuum with industrial cyclone mechanics.
- V1's metaphor: a cocktail from your own ingredients — **past experiences, current flow
  state, influence from the world**. Copying someone else's recipe makes it "just a drink on
  the menu."
- V2: steal the *methodology*, never the artifact.

The practical form of this is V2's formula, which is the most useful single thing in the
three videos:

> ### A + B = C
> **A** = your core niche. **B** = anything from outside it. **C** = your creative identity.
>
> | B | C |
> |---|---|
> | psychology | relatable — "this video knows me" |
> | minimalism | brutally clean, premium, confident |
> | imperfection | raw, expressive, honest |

A is fixed and boring; B is the whole decision. Picking B is a choice you make once for a
channel, not once per video.

## Constraints beat inputs

V2's first problem is **"unable to think"**, and its diagnosis is the useful part: the cause
is *information overload*, not lack of information. Its fix is to **set artificial limits** —
deliberately narrow the option space so the mind leaves the panic stage and has a direction.

V1 arrives at the same place from the other side: an **input filter**, not input volume. He
refuses any film rated below 7.5 on IMDb. *"The idea is not to consume as much as possible.
The idea is to consume only what matters."*

**[measured]** This is why the decision table in `SKILL.md` and `script_scan.py` work at all.
A treatment decision is fast because the taxonomy is small. When we had no taxonomy, the
figure detector fired 15 times where 3 were warranted.

## Start from what is already in front of you

V1's episode is built around chess because he happened to be playing a chess game on his
phone — *"it's not about searching for a very specific concept, it's more about playing around
with what is already in front of you."* The metaphor only got its weight from a **personal
memory**: his grandfather teaching him chess, and his childhood cheat of scattering the pieces
with the knight when he was losing.

So the sequence is: notice an object already in your life → find the memory that makes it
yours → the concept falls out. Not: search for a concept.

**[measured]** This is the same asset as Episode 1's strongest passage. The last 30 s of YT1
scores **+59.8 vs benchmark** and it is nothing but specifics — *"the dream that I gave up, a
body that broke, a relationship that taught me more than anything."* The channel's thesis
already is V1's thesis. See `storytelling.md`.

## Absorb, but create

V3 is explicit that consumption without output is worthless: *"there is literally no point if
you don't create and just absorb mindlessly."* Its process is three steps — gather diverse raw
material, create anyway, then hunt for **unexpected connections**: *"How can I mix these? What
happens if I apply this idea to that problem?"*

Its worked example is a good template: podcasts are recorded in a room; vlogs happen outside;
therefore — a podcast in a forest or in ruins.

## Presentation is the differentiator, not assets

V2's second problem. The complaint "I don't have unique assets" is misdiagnosed: assets are
freely available, and what is scarce is a unique *presentation* of them. Make the presentation
style distinctive and old assets read as fresh.

**[measured]** This is the argument for `brand.py`. A palette and type system derived from the
delivered work is exactly a presentation style, and it is what makes stock or repeated
material look like ours.

## Repetition is the mechanism for identity

V2's closing point, and the most easily ignored: **quantity builds identity**. You can only
recognise a creator's style after seeing several of their videos. A signature style is not
designed in one episode; it is the thing that survives across many.

**Implication for us:** consistency across episodes is worth more than novelty within one.
Changing the look every episode actively destroys the asset. `brand.json` should be treated as
a commitment, not a starting point, and a deliberate change to it is a channel-level decision.

## Don't over-fix early

V2, in passing, but it matches how our own sessions go wrong: *"many times we get stuck on
some things in the beginning and then keep fixing them for a long time"* — and on review the
problem was never that big. Get the whole thing standing, then fix. Picture lock before
graphics; the KB's own rule to run `coverage.py` **on the picture lock, before building
graphics**, is the same instinct.

---

## The tension between V1 and V2, resolved

V1 says do not use anyone else's recipe. V2 says every artist is a thief — take an existing
artwork and tweak the text, colour, placement, elements.

They are not in conflict, and the line between them is the useful bit:

> **Steal the method. Never the artifact.**

V2's own framing supports this: you steal *the methodology used in that particular thing* and
tweak it to yourself. V1's objection is to lifting the finished cocktail. V2 also suggests
crediting the source you took from — cheap, and it keeps you honest about which side of the
line you are on.

## What this means for this channel specifically

**Unproven — this is my reading, not a measurement.**

- **A is settled**: a 28-year-old telling an 18-year-old what he actually lived. **B is not
  chosen.** Choosing B deliberately is the highest-leverage open decision on the channel, and
  it should be picked once and then held for many episodes (see *repetition*).
- The retention data already says the lived-experience thesis works and the **hedging around
  it** is what costs viewers — YT1's worst window, −35.9, is 15 s of disclaimers. V1 would
  call that serving someone else's cocktail: it is the generic humility every channel opens
  with, not an ingredient only Shoaib has.
- Generated b-roll sits badly against all three videos' thesis, for the same reason it sits
  badly against the channel's own claim. See the 2026-09-23 worklog entry.
