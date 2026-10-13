---
name: motion-graphics-pass
description: "Design and apply an overlay motion-graphics + sound-effects layer to a PICTURE-LOCKED video, without touching the cut or runtime: read the transcript and frames, write a timestamped Motion Graphics Blueprint, build word-anchored kinetic type, glass cards, locators, stamps and callback motifs, replace the burned caption where a graphic now carries the line, mix SFX chosen to fit each moment (local library first, then the Epidemic Sound connector), and deliver final_mgx.mp4 beside the master. Use when Shoaib asks for motion graphics, a graphics pass, a blueprint, kinetic type, overlays or SFX on a final cut."
version: 1.0.0
---

# Motion-graphics pass

This skill takes a finished, captioned, mixed master (`<edit>/final.mp4`). It returns the same cut
with a graphics-and-sound layer on top (`<edit>/final_mgx.mp4`): same frames, same runtime, same
A/V offset, and loudness within 0.5 LU. It was built from **Episode 2** ("I Gave Up My Biggest
Dream at 15", delivered 2026-10-12). That episode is the quality bar. Before designing anything,
read [references/episode2-as-built.md](references/episode2-as-built.md) and skim
[examples/episode2/cues.py](examples/episode2/cues.py).

**Model and effort.** The scripts are deterministic: same cues in, same file out, byte for
byte. The quality comes from the *choices*: which lines earn a graphic, what each one says,
where it sits, and what pays off later. Run this pass on the strongest model at high effort
(Episode 2 was made with `claude-opus-5-5`). Never skip the stills loop in step 6. That loop
is where Episode 2 went from good to right.

**What this skill never does.** It never re-edits, trims, re-orders or retimes the cut, and it
never modifies the master. If the cut is not locked, finish the edit first with the main
`SKILL.md`.

---

## The process

Every command runs from the repo root:
```bash
export PKG_CONFIG_PATH=/opt/homebrew/lib/pkgconfig      # pycairo builds against brew cairo
MGX="uv run --with pycairo python skills/motion-graphics-pass/scripts/mgx.py"
$MGX <edit> <command> …
```
Everything is written to `<edit>/mgx/` (Hard Rule 12). The only exception is the delivery,
`<edit>/final_mgx.mp4`.

### 1. Read the episode (no graphics yet)
- `<edit>/project.md`, **every session**. Look for:
  - editorial holds: the zenith, unscored windows, "lands in silence";
  - withheld imagery (Ep 2 withheld the cricket photo until "So I just quit quietly");
  - what already exists: cards, locators, speed badge, stills, b-roll;
  - Shoaib's corrections and preferences.
- `edl.json`: `overlays`, `graphics`, `cards`, `subtitles`, `brand`. Note which of these
  are actually in the delivered master. An EDL edited after the delivery can list cards the
  master doesn't have. Ep 2's routine card was like this.
- `master.srt`, read as prose, all of it. The transcript is the script you design against.
- `kb/storytelling.md` (zenith, withholding, contrast) and the READ items in
  `kb/mistakes.md`: R3, R4, R6, R9 and R11 all apply here.

### 2. Words on the output timeline
```bash
$MGX <edit> words "can't fail" "abhi" "twenty centimeter"
```
This builds `mgx/words.json` from the EDL and the cached transcripts (the `_110` sped sources
have their own rescaled transcripts), and prints each phrase's `(start, end)` on the output
timeline. **Anchor every graphic to a word onset, not a caption-cue start.** A cue starts
before the word it shows.

### 3. Look at the picture
```bash
$MGX <edit> frames        # mgx/frames/sheet_*.jpg (every 2 s), scenes_*.jpg (every picture change)
```
Read every sheet. Write down:
- **The A-roll stretches and their lengths.** These are where attention needs resetting.
  Ep 2 had a 107 s unbroken stretch in Scene 8.
- **Safe zones, measured on this framing, not assumed.** For Ep 2 at 1080 design units:
  - face x 41–54%, y 29–58%;
  - hands up to x ~31% below y 62%;
  - burned captions y 80–88%, centred.

  That gave three zones:
  - **primary: the left third** (x 4–26%, y 18–62%), the calm wall and mirror;
  - **top-right** for locators and stats;
  - **top-centre** over the dark poster, above the cap. Only the call pill went there.

  **Nothing goes in the lower-centre band.**
- What sits behind each zone. Ep 2's left third is a light cream wall, so **every text graphic
  sits on dark glass**. White type straight on that wall is illegible.

### 4. The blueprint (Shoaib reviews it)
Write `<edit>/motion_graphics_blueprint.md` in the format of
[references/blueprint-format.md](references/blueprint-format.md):
- the brief;
- the global rules;
- one table row per cue: timestamp in–out, spoken line, concept & placement, animation in /
  hold / out with easing, paired SFX;
- an asset checklist;
- a pacing review.

Ep 2's is in [references/episode2-blueprint.md](references/episode2-blueprint.md). Confirm the
plan with Shoaib before building (Hard Rule 11's spirit). If he has already said "go ahead and
apply it", build straight away and give him the blueprint alongside the result.

### 5. Author the cues
```bash
cp skills/motion-graphics-pass/examples/episode2/cues.py <edit>/mgx/cues.py
```
Keep the CONFIG block's shape and replace every cue:
- `MASTER`, `BASE`, `OUTPUT`;
- fonts: leave `set_fonts` out to use macOS Helvetica Neue;
- `REPLACE_CAPTIONS`: the `master.srt` cue numbers that a kinetic-type cue now carries;
- `CAPTION_BAND`, `EXTRA_PATCHES`, `VIGNETTES`, `GLASS_CARDS`, `SFX_DIR`;
- `MOVIE_LAYERS`: pre-rendered full-frame movies with alpha, such as the house "SWITCH TO 1.25X"
  badge (`build/gfx_badge.py`, Episodes 2–4). Use `dict(name=, file=, start=, bt601=True)`;
  `layers` refuses a movie whose width differs from the master's.

A cue is a draw function registered with its window, its sprite box (design units, 1920×1080)
and its sound effects:
```python
@cue("cant_fail", 195.0, 196.45, LEFT, sfx=[("boom", 195.0, -14)])
def _(c, t):                       # c: cairo context in design units; t: absolute output time
    stamp(c, t, "I can't", None, None, 195.0, 196.4, 195.0)
```
The library (`scripts/mglib.py`) has:
- **easing:** `eo3`, `ei2`, `bo` (back-out), `sio`, `p(t, start, dur)`, `env`;
- **primitives:** `text`, `tw`, `glass`, `rrect`, `line`, `strike`, `dot`, `ring`, `group` for
  fade/offset/scale/rotate as one;
- **components, each proven on Ep 2:** `kinetic`, `pill`, `locator`, `chip`, `meter`, `stamp`,
  `bubble`, `weight_stack`, `ruler`, `disc`, `icon`.

What each one is for is in [references/toolkit.md](references/toolkit.md). Invent new ones
freely in `cues.py`. Promote one into `mglib.py` once it has been used twice.

### 5b. Source every sound (local first, then Epidemic Sound)
Each blueprint SFX line names what happens on screen, the sound's character and its job. Then:
```bash
$MGX <edit> library paper tear        # search what is already on disk (effects/ + music/)
```
- **If nothing local fits all three, use the Epidemic Sound connector.** Search with
  `SearchSoundEffects` or `SearchSimilarToSoundEffect`, compare candidates by measuring their
  previews, get a WAV with `DownloadSoundEffect`, and run
  `$MGX <edit> fetch "<assetUrl>" --kind … --id … --title …`.
- `fetch` files it in `effects/epidemic/<kind>/` with a sidecar and prints the `SFX_LIB` line
  for `cues.py`.
- Music beds work the same way (`SearchRecordings`, `EditRecording` to fit the window), with
  one constraint: the master is already scored, so a new bed goes through the episode's music
  mix, not this pass.
- **Never use the nearest file on disk when it isn't the apt one.** If the connector isn't in
  the session, say so and list the gap.
- Full procedure: [references/sourcing-audio.md](references/sourcing-audio.md).

### 6. The stills loop (required, every cue)
```bash
MG_S=1 $MGX <edit> still 33.4 81.9 195.5 266 416.5 --label pass1   # -> mgx/qc/pass1/sheet_*.jpg
```
For every cue, check frames at its entry, its middle and just before its exit. Read every
sheet as an image and fix what you see. Then re-run. Things Ep 2's loop caught:
- quote marks colliding with the next word;
- a stat card clipped by its sprite box;
- a ruler marker crossing its own labels;
- a dot field that showed for only 0.5 s and sat illegibly on the wall;
- a cricket-ball seam drawn outside the ball.

Stills composite over the *captioned* master, so you will still see the caption under a
replacement cue. That is expected; the swap only happens at compose.

### 7. Build and deliver
```bash
$MGX <edit> render          # all cue sprites at delivery resolution (S = height/1080), in parallel
$MGX <edit> layers          # caption patches from BASE (checks BASE == MASTER first), extra patches,
                            # vignettes, glass under HyperFrames cards
$MGX <edit> sfx             # SFX bus + mix (normalize=0, limiter level=0); prints the AUDIBILITY report
$MGX <edit> compose         # 20 s chunks: overlays in order, BT.709 tags, chapters stripped
$MGX <edit> mux             # concat + mixed audio -> <edit>/final_mgx.mp4, then verify
```
`verify` fails on any of these:
- the frame count differs from the master;
- the duration differs by more than 0.05 s;
- the A/V offset differs by more than 5 ms;
- there is no audio;
- loudness moved by more than 0.5 LU.

It also writes one frame per cue *from the delivered file* to `mgx/qc/verify/`. **Read those
sheets.** They are the only view that shows the caption swaps and the card glass as the viewer
will see them.

Then the house delivery rules (CLAUDE.md):
- Run `helpers/review.py <edit> --render <edit>/final_mgx.mp4 --label mgx` and clear its HIGH
  flags.
- Walk R3, R4, R6, R9 and R11.
- **R9:** leave one file that looks uploadable. The scripts never create a second one. If you
  make a test render, name it `*_NO_AUDIO*` or `*_do_not_upload*`.
- Name the one upload file in the delivery message.
- Append a session to `<edit>/project.md`, and to `kb/worklog.md`.

### 8. Iterating on Shoaib's notes
Changing a graphic only rebuilds what it touches:
```bash
$MGX <edit> render bubbles && $MGX <edit> compose --dirty bubbles && $MGX <edit> mux
```
- `--dirty` re-encodes only the chunks that cue overlaps.
- A sound-only change is `sfx` then `mux`, with no video re-encode.

---

## The judgment (what made Episode 2 work)

These are the rules behind the choices. Every value is a worked example, not a mandate, except
where a rule says *never*.

**1. Every graphic must clarify, emphasize or reset.**
- **Clarify:** it makes an abstract idea concrete. Examples: the line that tangles into a knot on
  "much messier"; 150→170 cm on a ruler; studies dropping 80→61 while cricket stays tall.
- **Emphasize:** it lands the thesis. The "I can't **fail**." stamp.
- **Reset:** it changes the frame in a long talking-head stretch. The chapter pill at the start
  of the 107 s stretch.

If a candidate does none of these, it is a plain shot. About a third of a good pass has no
graphic.

**2. Never compete with the caption.** Pick one of two:
- **(a) The graphic carries information that is not spoken.** Years ("Gandhinagar, 2004"),
  icons, the relatives' voices in Hinglish ("Padhai pe dhyan do", "Lakhs of kids play
  cricket"), "Matches watched: 0 0 0".
- **(b) The graphic IS the line,** and its caption cue is removed for exactly that cue
  (`REPLACE_CAPTIONS`). Ep 2 did this for the cold open, "religion", both stamps, the labels,
  “responsible” and the coach's quote.

A graphic that repeats the caption at the same moment is the Episode 1 bug. Never ship it.

**3. Build callbacks: setup, then payoff.** The pass is a second script running alongside the
spoken one. Ep 2's pairs were:
- "I can't **fail**." (3:14, red) returning in the same spot as "It's okay to **fail**." (7:28,
  red turning cream);
- quote marks around “responsible” (0:09 → 5:10);
- a lone grey dot with empty space round it ("no one to put a hand around my shoulder",
  3:16), joined by a warm dot (8:07, "find a person");
- the Confidence meter emptying to 0 (3:43) and refilling to 100% ("I'll show you how I built
  that back", 8:43);
- the weight slab for expectations (3:09), with "Class 10 boards" landing on top (4:15).

**Same asset, same position, so the eye recognises it.**

**4. Protect the holds.**
- The zenith gets **no graphic and no SFX**. Ep 2: 8:16.34–8:24.66.
- Every window `project.md` calls unscored stays unscored, except one dry tick where a ruler
  lands.
- Emotional peaks ("it just emotionally crashed me") get at most a slow vignette, never type.
- A graphic must be fully gone *before* a hold starts.
- **Rests are designed too.** Ep 2 left 3:16–3:29, 4:43–4:54, 5:12–5:24 and 6:04–6:23 almost
  empty, and the stamps land harder because of it.

**5. Respect what the cut withholds.** If `project.md` says an image is held back until a
line, do not spend it early in graphic form. A glyph, a shape or a word is fine; the
photograph is not.

**6. Build to the sound that already exists.** Ep 2 had a phone ring on "I called my coach
again" and hang-up beeps on "take that much risk". The call pill was built to them:
- it rings with the ring;
- a timer runs while the coach talks;
- it turns red and says "Call ended" exactly on the beeps.

Sound design already in the mix is a timeline to animate against, not something to fight.

**7. Be specific to Shoaib's world.**
- **Hinglish** where real people would speak it.
- **Indian** specifics: the ₹5 bet, Class 10 boards, "Engineering ka socho".
- **His own words** in quote cards, typeset once, intact ("Abhi, don't make sense to take
  that much risk." — Coach).

**8. Accuracy is a hard gate.**
- Every year, figure and title on screen must be checkable against what he said or what
  `project.md` records.
- A film is named in text only. Never a poster, logo or likeness (R4).
- No generated "photos" of his life (project.md session 2).
- Say which figures you derived. Ep 2's "2013" is 2026 minus "thirteen years ago".

**9. Placement and legibility.**
- Text goes on glass: dark, ~0.8 opacity, 28 px radius, 1 px light keyline, soft shadow.
- Locators copy the existing style (black 0.52 box, white Regular 32 px, top-right, 38 px
  margin).
- Keep the face, the eyes, the gesturing hands and the caption band clear at every frame of
  every cue, not just the middle frame.

**10. Motion.**
- **Easing:**
  - entries use ease-out (`eo3`), 0.35–0.45 s;
  - exits use ease-in (`ei2`) and are always faster, 0.25–0.35 s;
  - `bo` overshoot only on things that *land* (a word, a dot, quote marks);
  - stamps are a hard cut with a 2-frame shake;
  - text never overshoots in opacity.
- **Land on the onset:** start the reveal ~0.04 s before the word.
- **One focus at a time:** accent marks only change, at most two accents in frame.
- **Palette** comes from `brand.json`: Ep 2 used white 92%, cream `#DED3BD`, muted `#8A8375`,
  accent `#F25435`. Font: Helvetica Neue R/M/B.

**11. Density.** Aim for about 5 events a minute, measured against the A-roll stretches, not
the average.
- **Flag more than ~60 s of continuous graphics.** Ep 2's 3:34–4:43 was flagged as the stretch
  to thin first.
- **Flag a static stretch over ~25–30 s unless it is a deliberate hold.**

Write both into the blueprint's pacing review.

**12. Sound effects: the apt sound, found locally or on Epidemic Sound, under the house palette rules (`effects/structural/palette.json`).** Match the sound to what physically happens: a paper ticket gets a paper tear, a stone slab gets a dry heavy drop. Episode 2 reused a page turn as its paper tear; don't repeat that.
- Thuds are felt more than heard.
- At most one whoosh per three graphics.
- One riser per episode.
- Tick on list rows and stamps, sparingly.
- **Measure, don't guess** (M052). `sfx` prints an audibility report: the effect's energy
  against the programme, in the frequencies where the effect lives. On Ep 2, impacts at
  −14..−21 dB peak cleared it easily (+13..+38 dB). UI pops, whooshes, paper and soft ticks at
  −18..−30 dB peak sat 15–55 dB *under* the voice, so they were inaudible.
- Under speech, a UI-type effect needs roughly −6..−10 dB peak, or a slot in a breath.
- **Fix every BURIED line or delete the effect.** An effect nobody hears is just clutter in
  the cue file.

---

## Technical facts (each one cost time on Ep 2; all verified)

- **The caption swap is a patch from `base.mp4`.** render.py writes `base.mp4` (graded, no
  captions, no overlays) before compositing, frame-aligned with `final.mp4`. Restoring the
  caption band from it for a cue's window removes exactly that caption.
  - `layers` refuses to run unless BASE matches MASTER (mean diff < 2 over the top 75% of the
    frame; Ep 2 measured 0.5).
  - **Patch only over A-roll.** Under b-roll, BASE has the speaker, not the b-roll. Check
    every `REPLACE_CAPTIONS` cue sits on A-roll.
- **A data track breaks the concat.** Ep 2's `final.mp4` carries a 170 s text track
  (`SubtitleHandler`, read as chapters). ffmpeg copies it into each chunk by default, so the
  chunk's *format* duration inflates and the concat demuxer spaces the chunks by it. Ep 2's first mux came out 923 s
  long. Chunks are now written with `-dn -map_chapters -1 -map_metadata -1`. `verify` checks
  the duration.
- **A/V offset.** The master's video starts one frame (0.0334 s) after its audio. `mux`
  re-applies the offset with `-itsoffset`, and `verify` compares it.
- **cairo is premultiplied BGRA.** `unpremul` converts it before encoding, or every
  anti-aliased edge goes dark.
- **RGB sprites need the BT.709 matrix** (`scale=out_color_matrix=bt709`). swscale's default
  is 601, which shifts the accent red. HyperFrames cards are BT.601 and untagged, so convert
  them 601→709 (`bt601: True`).
- **ffmpeg 9 ignores `-color_primaries/-color_trc`.** Chunks end in `setparams` and carry an
  `h264_metadata` bsf, as render.py does.
- **ffmpeg's audio defaults.** `amix` halves each input unless `normalize=0`. `alimiter`
  re-levels unless `level=0`. Either one silently changes the programme loudness.
- **Card glass** is a blur of what is under the card, cut by the card's mask. It is rendered
  once as ProRes 4444 from a crop at quarter resolution (sigma 20). The full frame isn't
  needed, which saves a lot of time.
- **Fonts:** Helvetica Neue has no ₹ glyph. Ep 2's coin says "5 / RUPEES".
- **macOS multiprocessing uses `spawn`.** `render`'s pool initializer re-loads the cues in each
  worker. Verified: spawn and fork produce byte-identical sprites.
- **`fade` with a negative `st` is an error.** A vignette that starts before the chunk skips
  its fade-in.
- **Speed:** Ep 2 in the cloud VM (4 cores) took ~3 min for sprites, ~10 min to compose and
  ~1.5 min to mux. A Mac is faster, and nothing here needs the session to stay attached.

## Files

- `scripts/mgx.py`: the pipeline CLI (words, frames, still, render, layers, library, fetch,
  sfx, compose, mux, verify).
- `scripts/mglib.py`: drawing primitives, components, the cue registry and the sprite renderer.
- `examples/episode2/cues.py`: Episode 2's complete pass, the worked example.
- `references/episode2-as-built.md`: what shipped, what changed from the blueprint, QC results
  and the SFX audibility findings.
- `references/episode2-blueprint.md`: the blueprint as approved.
- `references/blueprint-format.md`: the table format Shoaib asked for.
- `references/toolkit.md`: which component fits which kind of beat.
- `references/sourcing-audio.md`: local library first, then the Epidemic Sound connector (search, audition by measurement, download, `fetch`, place, verify), for SFX and music.
