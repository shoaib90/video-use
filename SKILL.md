---
name: video-use
description: Edit any video by conversation. Transcribe, cut, color grade, generate overlay animations, burn subtitles — for talking heads, montages, tutorials, travel, interviews. No presets, no menus. Ask questions, confirm the plan, execute, iterate, persist. Production-correctness rules are hard; everything else is artistic freedom.
---

# Video Use

## Principle

1. **LLM reasons from raw transcript + on-demand visuals.** The only derived artifact that earns its keep is a packed phrase-level transcript (`takes_packed.md`). Everything else — filler tagging, retake detection, shot classification, emphasis scoring — you derive at decision time.
2. **Audio is primary, visuals follow.** Cut candidates come from speech boundaries and silence gaps. Drill into visuals only at decision points.
3. **Ask → confirm → execute → iterate → persist.** Never touch the cut until the user has confirmed the strategy in plain English.
4. **Generalize.** Do not assume what kind of video this is. Look at the material, ask the user, then edit.
5. **Artistic freedom is the default.** Every specific value, preset, font, color, duration, pitch structure, and technique in this document is a *worked example* from one proven video — not a mandate. Read them to understand what's possible and why each worked. Then make your own taste calls based on what the material actually is and what the user actually wants. **The only things you MUST do are in the Hard Rules section below.** Everything else is yours.
6. **Invent freely.** If the material calls for a technique not described here — split-screen, picture-in-picture, lower-third identity cards, reaction cuts, speed ramps, freeze frames, crossfades, match cuts, L-cuts, J-cuts, speed ramps over breath, whatever — build it. The helpers are ffmpeg and PIL. They can do anything the format supports. Do not wait for permission.
7. **Verify your own output before showing it to the user.** If you wouldn't ship it, don't present it.

## Hard Rules (production correctness — non-negotiable)

These are the things where deviation produces silent failures or broken output. They are not taste, they are correctness. Memorize them.

1. **Subtitles are applied LAST in the filter chain**, after every overlay. Otherwise overlays hide captions. Silent failure.
2. **Per-segment extract → lossless `-c copy` concat**, not single-pass filtergraph. Otherwise you double-encode every segment when overlays are added.
3. **30ms audio fades at every segment boundary** (`afade=t=in:st=0:d=0.03,afade=t=out:st={dur-0.03}:d=0.03`). Otherwise audible pops at every cut.
4. **Overlays use `setpts=PTS-STARTPTS+T/TB`** to shift the overlay's frame 0 to its window start. Otherwise you see the middle of the animation during the overlay window.
5. **Master SRT uses output-timeline offsets**: `output_time = word.start - segment_start + segment_offset`. Otherwise captions misalign after segment concat.
6. **Never cut inside a word.** Snap every cut edge to a word boundary from the Scribe transcript.
7. **Pad every cut edge.** Working window: 30–200ms. Scribe timestamps drift 50–100ms — padding absorbs the drift. Tighter for fast-paced, looser for cinematic.
8. **Word-level verbatim ASR only.** Never SRT/phrase mode (loses sub-second gap data). Never normalized fillers (loses editorial signal).
9. **Cache transcripts per source.** Never re-transcribe unless the source file itself changed.
10. **Parallel sub-agents for multiple animations.** Never sequential. Spawn N at once via the `Agent` tool; total wall time ≈ slowest one.
11. **Strategy confirmation before execution.** Never touch the cut until the user has approved the plain-English plan.
12. **All session outputs in `<videos_dir>/edit/`.** Never write inside the `video-use/` project directory.

Everything else in this document is a worked example. Deviate whenever the material calls for it.

## Directory layout

The skill lives in `video-use/`. User footage lives wherever they put it. All session outputs go into `<videos_dir>/edit/`.

```
<videos_dir>/
├── <source files, untouched>
└── edit/
    ├── project.md               ← memory; appended every session
    ├── takes_packed.md          ← phrase-level transcripts, the LLM's primary reading view
    ├── edl.json                 ← cut decisions
    ├── transcripts/<name>.json  ← cached raw Scribe JSON
    ├── animations/slot_<id>/    ← per-animation source + render + reasoning
    ├── clips_graded/            ← per-segment extracts with grade + fades
    ├── master.srt               ← output-timeline subtitles
    ├── downloads/               ← yt-dlp outputs
    ├── verify/                  ← debug frames / timeline PNGs
    ├── preview.mp4
    └── final.mp4
```

## Knowledge base (read this first)

This install maintains a knowledge base at `<repo>/kb/` — architecture, the transcript data
contract, a helper reference, verified gotchas, environment state, and a worklog of local
changes. The repo directory is the one containing this file (typically
`~/.claude/skills/video-use/`, a symlink to the clone).

**Read `kb/index.md` before starting**, and follow its pointers as needed — it records things
already learned the hard way on this machine, including which ASR providers are configured and
a `brew`-related trap that silently breaks subtitle burn-in.

**At the end of a task, update it:** append to `kb/worklog.md` and fold durable lessons into the
matching topic file. Record only what was verified, mark unproven suspicions as such, and keep
`kb/index.md` short. `bash kb/check-env.sh` re-verifies the environment claims.

## Setup

First-time install lives in `install.md` (clone, deps, ffmpeg, skill registration, API key). Don't re-run it every session; on cold start just verify:

- A transcription key resolves — either in the environment or in `.env` at the video-use repo root. If missing, ask the user to paste one and write it to `.env` (never to the user's `<videos_dir>`). Three providers are wired up:
    - `ELEVENLABS_API_KEY` → `transcribe.py` (Scribe). Tags audio events: `(laughter)`, `(applause)`, `(sigh)`.
    - `DEEPGRAM_API_KEY` → `transcribe_deepgram.py` (nova-3). Same on-disk schema, so everything downstream is identical, and it diarizes. But it returns **no audio-event tokens**, so the `(laughs)`/`(applause)` beat signals in *Cut craft* are unavailable — lean on silence gaps and `timeline_view` instead.
    - **No key needed** → `transcribe_whisper.py` (local whisper.cpp). Free and offline, same schema, but **no speaker diarization** and it normalizes some spoken numbers. Use it for free iteration, for offline work, and as a cross-check — it catches leading filler words Deepgram has been seen to drop. Never use it alone on multi-speaker footage.

    Prefer Deepgram or Scribe for the real cut (they diarize); prefer Scribe for reaction-heavy material where audio events carry the beats. Iterate with whisper to avoid burning credits. `kb/gotchas.md` records each provider's measured failure mode.

- **Establish what language is actually spoken before transcribing the batch.** Transcribe one clip, read it against a frame, and only then run the rest. A wrong `--language` does not error or flag low confidence — it returns fluent, grammatical nonsense and silently drops words. On code-switched speech (e.g. Hinglish, where Hindi and English alternate mid-sentence) pass `--language multi`; `detect_language` is no help because it commits to a single language per file. This matters far beyond captions: the cut is *reasoned from the transcript*, so a language mismatch corrupts the edit itself — mistranscribed passages get judged as "garbled, drop it", and whole narrative threads become invisible.
- `ffmpeg` + `ffprobe` on PATH.
- Python deps installed (`uv sync` or `pip install -e .` inside the repo).
- Node.js + npm available if the session needs HyperFrames or Remotion slots. HyperFrames currently requires Node.js 22+.
- `yt-dlp`, HyperFrames, Remotion, Manim installed only on first use.
- First-use animation setup happens inside the slot directory, never at the video-use repo root. HyperFrames can be invoked with `npx --yes hyperframes ...`; Remotion can be scaffolded with `npx create-video@latest` or installed as a project-local dependency before using its `remotion render` command.
- This skill vendors `skills/manim-video/`. Read its SKILL.md when building a Manim slot.

Helpers (`helpers/transcribe.py`, `helpers/render.py`, etc.) live alongside this SKILL.md. Resolve their paths relative to the directory containing this file — the skill is typically symlinked at `~/.claude/skills/video-use/` or `~/.codex/skills/video-use/`.

## Helpers

- **`transcribe.py <video>`** — single-file Scribe call. `--num-speakers N` optional. Cached.
- **`transcribe_whisper.py <video>`** — local whisper.cpp. Free, offline, no key, no diarization. Defaults to the `small.en` model.
- **`transcribe_deepgram.py <video>`** — Deepgram nova-3 alternative to the above. Emits the identical
  `{words:[{type,text,start,end,speaker_id}]}` schema, so `pack_transcripts.py` and `render.py --build-subtitles`
  consume it unchanged. `filler_words=true` and `punctuate=true`; `smart_format` deliberately off (Hard Rule 8).
  `--language multi` for code-switched speech; `--convert <deepgram.json>` maps an existing response offline with
  no API call. Cached per source **and** per provider/model/language. **No audio-event tags** — see Setup.
- **`transcribe_batch.py <videos_dir>`** — 4-worker parallel transcription. Use for multi-take.
- **`pack_transcripts.py --edit-dir <dir>`** — `transcripts/*.json` → `takes_packed.md` (phrase-level, break on silence ≥ 0.5s).
- **`timeline_view.py <video> <start> <end>`** — filmstrip + waveform PNG. On-demand visual drill-down. **Not a scan tool** — use it at decision points, not constantly.
- **`render.py <edl.json> -o <out>`** — per-segment extract → concat → overlays (PTS-shifted) → subtitles LAST. `--preview` for 720p fast. `--build-subtitles` to generate master.srt inline. `--height` sets the output height (default 1080) and `--crf` the extract quality (default 16 final / 22 preview) — see *Output quality* below.
- **`grade.py <in> -o <out>`** — ffmpeg filter chain grade. Presets + `--filter '<raw>'` for custom.
- **`coverage.py <cut.mp4> --edl … --srt … [--retention …]`** — where the timeline goes quiet:
  visual events per minute, median hold, and every stretch over `--min-gap` with nothing
  changing, alongside what is said there, unused b-roll, and candidate insertion points.
- **`script_scan.py <edit_dir>`** — reads the transcripts and reports **where a motion graphic
  earns its place**: enumerations, figures worth showing, contrasts, attribute lists, named
  concepts. Each hit carries a confidence, the evidence that produced it, and the component it
  suggests. It proposes; the editor disposes. See *Finding graphic opportunities*.
- **`motion.py`** — the motion engine: curve library (spring, overshoot, anticipation), per-role
  **weight** presets, stagger/rhythm, real sub-frame motion blur, and ProRes 4444 sequence
  rendering with an alpha verifier.
- **`brand.py`** — per-channel palette, type scale and shape language, sized as fractions of the
  output height. `derive()` measures a palette off already-delivered work rather than asserting one.
- **`components.py`** — the archetypes: `big_number`, `opposing_chips`, `staggered_items`,
  `kinetic_type`, `sliding_carousel`, `node_diagram`. Built on weights, not raw durations.
- **`matte.py <video> -o <matte.mp4>`** — a person matte so a graphic can pass BEHIND the
  speaker. Bootstraps its own interpreter (mediapipe needs one, like DeepFilterNet). The picture
  never round-trips through Python — only the matte is computed.
- **`graphics.py`** — declarative on-screen text (titles, lower thirds, chapter cards) from a
  `graphics` block on the EDL. Anchored to sources/segments/spoken phrases, sized as fractions
  of the output height, drawn in the composite pass *before* subtitles. See *Text graphics*.

For animations, create `<edit>/animations/slot_<id>/` with `Bash` and spawn a sub-agent via the `Agent` tool.

## The process

1. **Inventory.** `ffprobe` every source. `transcribe_batch.py` on the directory. `pack_transcripts.py` to produce `takes_packed.md`. Sample one or two `timeline_view`s for a visual first impression.
2. **Pre-scan for problems.** One pass over `takes_packed.md` to note verbal slips, obvious mis-speaks, or phrasings to avoid. Plain list, feed into the editor brief.
3. **Converse.** Describe what you see in plain English. Ask questions *shaped by the material*. Collect: content type, target length/aspect, aesthetic/brand direction, pacing feel, must-preserve moments, must-cut moments, animation and grade preferences, subtitle needs. Do not use a fixed checklist — the right questions are different every time.
4. **Propose strategy.** 4–8 sentences: shape, take choices, cut direction, animation plan, grade direction, subtitle style, length estimate. **Wait for confirmation.**
5. **Execute.** Produce `edl.json` via the editor sub-agent brief. Drill into `timeline_view` at ambiguous moments. Build animations in parallel sub-agents. Apply grade per-segment. Compose via `render.py`.
6. **Preview.** `render.py --preview`.
7. **Self-eval (before showing the user).** Run `timeline_view` on the **rendered output** (not the sources) at every cut boundary (±1.5s window). Check each image for:
   - Visual discontinuity / flash / jump at the cut
   - Waveform spike at the boundary (audio pop that slipped past the 30ms fade)
   - Subtitle hidden behind an overlay (Rule 1 violation)
   - Overlay misaligned or showing wrong frames (Rule 4 violation)

   Also sample: first 2s, last 2s, and 2–3 mid-points — check grade consistency, subtitle readability, overall coherence. Run `ffprobe` on the output to verify duration matches the EDL expectation.

   If anything fails: fix → re-render → re-eval. **Cap at 3 self-eval passes** — if issues remain after 3, flag them to the user rather than looping forever. Only present the preview once the self-eval passes.
8. **Iterate + persist.** Natural-language feedback, re-plan, re-render. Never re-transcribe. Final render on confirmation. Append to `project.md`.

## Cut craft (techniques)

- **Audio-first.** Candidate cuts from word boundaries and silence gaps.
- **Preserve peaks.** Laughs, punchlines, emphasis beats. Extend past punchlines to include reactions — the laugh IS the beat.
- **Speaker handoffs** benefit from air between utterances. Common values: 400–600ms. Less for fast-paced, more for cinematic. Taste call.
- **Audio events as signals.** `(laughs)`, `(sighs)`, `(applause)` mark beats. Extend past them.
- **Silence gaps are cut candidates.** Silences ≥400ms are usually the cleanest. 150–400ms phrase boundaries are usable with a visual check. <150ms is unsafe (mid-phrase).
- **Example cut padding** (the launch video shipped with this): 50ms before the first kept word, 80ms after the last. Tighter for montage energy, looser for documentary. Stay in the 30–200ms working window (Hard Rule 7).
- **Never reason audio and video independently.** Every cut must work on both tracks.

## The packed transcript (primary reading view)

`pack_transcripts.py` reads all `transcripts/*.json` and produces one markdown file where each take is a list of phrase-level lines, each prefixed with its `[start-end]` time range. Phrases break on any silence ≥ 0.5s OR speaker change. This is the artifact the editor sub-agent reads to pick cuts — it gives word-boundary precision from text alone at 1/10 the tokens of raw JSON.

Example line:
```
## C0103  (duration: 43.0s, 8 phrases)
  [002.52-005.36] S0 Ninety percent of what a web agent does is completely wasted.
  [006.08-006.74] S0 We fixed this.
```

## Editor sub-agent brief (for multi-take selection)

When the task is "pick the best take of each beat across many clips," spawn a dedicated sub-agent with a brief shaped like this. The structure is load-bearing; the pitch-shape example is not.

```
You are editing a <type> video. Pick the best take of each beat and 
assemble them chronologically by beat, not by source clip order.

INPUTS:
  - takes_packed.md (time-annotated phrase-level transcripts of all takes)
  - Product/narrative context: <2 sentences from the user>
  - Speaker(s): <name, role, delivery style note>
  - Expected structure: <pick an archetype or invent one>
  - Verbal slips to avoid: <list from the pre-scan pass>
  - Target runtime: <seconds>

Common structural archetypes (pick, adapt, or invent):
  - Tech launch / demo:   HOOK → PROBLEM → SOLUTION → BENEFIT → EXAMPLE → CTA
  - Tutorial:             INTRO → SETUP → STEPS → GOTCHAS → RECAP
  - Interview:            (QUESTION → ANSWER → FOLLOWUP) repeat
  - Travel / event:       ARRIVAL → HIGHLIGHTS → QUIET MOMENTS → DEPARTURE
  - Documentary:          THESIS → EVIDENCE → COUNTERPOINT → CONCLUSION
  - Music / performance:  INTRO → VERSE → CHORUS → BRIDGE → OUTRO
  - Or invent your own.

RULES:
  - Start/end times must fall on word boundaries from the transcript.
  - Pad cut boundaries (working window 30–200ms).
  - Prefer silences ≥ 400ms as cut targets.
  - Unavoidable slips are kept if no better take exists. Note them in "reason".
  - If over budget, revise: drop a beat or trim tails. Report total and self-correct.

OUTPUT (JSON array, no prose):
  [{"source": "C0103", "start": 2.42, "end": 6.85, "beat": "HOOK",
    "quote": "...", "reason": "..."}, ...]

Return the final EDL and a one-line total runtime check.
```

## Color grade (when requested)

Your job is to **reason about the image**, not apply a preset. Look at a frame (via `timeline_view`), decide what's wrong, adjust one thing, look again.

Mental model is ASC CDL. Per channel: `out = (in * slope + offset) ** power`, then global saturation. `slope` → highlights, `offset` → shadows, `power` → midtones.

**Example filter chains** (`grade.py` has `--list-presets`; use them as starting points or mix your own):

- **`warm_cinematic`** — retro/technical, subtle teal/orange split, desaturated. Shipped in a real launch video. Safe for talking heads.
- **`neutral_punch`** — minimal corrective: contrast bump + gentle S-curve. No hue shifts.
- **`none`** — straight copy. Default when the user hasn't asked.

For anything else — portraiture, nature, product, music video, documentary — invent your own chain. `grade.py --filter '<raw ffmpeg>'` accepts any filter string.

Hard rules: apply **per-segment during extraction** (not post-concat, which re-encodes twice). Never go aggressive without testing skin tones.

## Subtitles (when requested)

Subtitles have three dimensions worth reasoning about: **chunking** (1/2/3/sentence per line), **case** (UPPER/Title/Natural), and **placement** (margin from bottom). The right combo depends on content.

**Worked styles** — pick, adapt, or invent:

**`bold-overlay`** — short-form tech launch, fast-paced social. 2-word chunks, UPPERCASE, break on punctuation, Helvetica 18 Bold, white-on-outline, `MarginV=35`. `render.py` ships with this as `SUB_FORCE_STYLE`.

```
FontName=Helvetica,FontSize=18,Bold=1,
PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H00000000,
BorderStyle=1,Outline=2,Shadow=0,
Alignment=2,MarginV=35
```

**`natural-sentence`** (if you invent this mode) — narrative, documentary, education. 4–7 word chunks, sentence case, break on natural pauses, `MarginV=60–80`, larger font for readability, slightly wider max-width. No shipped force_style — design one if you need it.

Invent a third style if neither fits. Hard rules: subtitles LAST (Rule 1), output-timeline offsets (Rule 5).

### Driving it from the EDL

`render.py --build-subtitles` reads an optional `subtitle_style` block, so a style is data rather than a code edit:

```json
"subtitle_style": {
  "words_per_chunk": 6,
  "case": "sentence",
  "force_style": "FontName=Helvetica,FontSize=13,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=28"
}
```

Defaults reproduce the shipped `bold-overlay` look exactly: `words_per_chunk` 2, `case` `"upper"`, and `SUB_FORCE_STYLE`.

Two things worth knowing when you deviate:

- `"case": "sentence"` keeps the ASR's own capitalization, but a cut can promote a mid-sentence word to the start of a sentence. The builder capitalizes any cue that opens the file or follows sentence-final punctuation, so that case is handled.
- `force_style`'s `MarginV` is relative to `PlayResY=288`. The default of 90 is tuned for **vertical** video; for 16:9 landscape a value around 28 sits the caption roughly 10% up from the bottom.

## Deciding the treatment for a beat

Which treatment a beat gets, not just which graphic. Run `coverage.py` on any finished cut to
find where the timeline goes quiet, and use this table to decide what belongs there.

| What the beat is doing | Treatment | Why |
|---|---|---|
| states a figure, enumerates, contrasts, names a concept | **graphic** (`script_scan` finds these) | read frame-by-frame off a professional reference edit |
| references something you can actually show — a place, an object, a document, a person | **cutaway** | but it must AGREE with the line; two of seven planned cutaways were dropped on one edit because the dashcam speed readout contradicted "clear road" |
| a jump cut between consecutive takes of one source | **push-in** (`ranges[].zoom`) | makes the splice read as intent rather than a glitch |
| the graphic, not the speaker, carries the content | **demote** the speaker | the graphic owns the frame; see *Motion graphics* |
| an emotional peak — a confession, a punchline, a landing | **hold.** No treatment | Tversky 2002: animation does not aid comprehension; do not animate to fill silence |
| none of the above | **plain shot** | about a third of the reference carries nothing |

Three anti-rules, each learned the expensive way:

- **A graphic that repeats the caption adds nothing.** If both occupy a beat, one must say
  something different — abstract the graphic to chapter markers, or suppress the caption.
- **A cutaway that contradicts the line is worse than no cutaway.** It reads as an editing
  mistake. Check the picture against the words every time.
- **Do not treat a beat to fill silence.** Restraint is what makes the rest land.

### Pacing: measure it, do not inherit it

`coverage.py` reports visual events per minute, the median hold, and every stretch over
`--min-gap` with nothing changing — cross-referenced with what is being said there, the unused
b-roll you already own, and candidate insertion points on sentence boundaries.

Measured on a delivered 3m34s personal-essay episode against an 11m44s professional explainer:

| | the essay | the explainer |
|---|---|---|
| visual events | 2.8/min | 8.6/min |
| median hold | 4.3 s | 3.6 s |
| longest static stretch | **124.9 s** | 58.9 s |

**Do not copy the explainer's rate.** Format decides pace, and a reflective essay earns holds a
tutorial does not. The number that mattered was not the average but the single 125-second
stretch — 58% of that film — where nothing changed at all, while nine b-roll assets sat unused.
A working rule is a *ceiling*, not a target: no stretch beyond ~25-30 s without something
changing, unless the hold is deliberate.

And the honest limit of all of the above: this measures **change**, not **interest**. Pass
`--retention` with a YouTube Studio audience-retention export and the report shows what each
gap actually cost in viewers — which replaces every rule here with evidence from the channel's
own audience.

## Finding graphic opportunities in a script

Before building any graphic, run `script_scan.py` over the edit's transcripts. The hard part of
motion design on a talking-head script is not drawing a chip — it is noticing that *this* line
enumerates five things and *that* one states a figure, and leaving the rest alone.

The taxonomy below came from reading a reference edit frame by frame against its own script
(Somrat Dutta, *"If You ONLY Watch One Motion Design Video"*), matching what was on screen at
each spoken line:

| The line… | He put on screen |
|---|---|
| enumerates ("five pillars") | card carousel, sub-items staggering, sliding between items |
| marks a step ("First, … Second, …") | numbered badges, or giant ghosted numerals in a carousel |
| states a figure ("15,000 to 40,000 a month") | big numeral + unit, **attached to the entity it describes** |
| states an oddly specific one ("12,917 dirhams") | huge number passing **behind** the speaker |
| contrasts two topics ("X and Y are not the same") | two opposing chips, left and right |
| lists attributes ("contrast, hierarchy and balance") | staggered sub-items under a heading |
| names a concept ("I call it the post-mortem method") | term card |
| is emphatic ("the single reason some reels…") | words scattered at mixed scale, speaker composited in front |
| **is none of these** | **plain shot** |

That last row is the important one. About a third of the reference carries no graphic at all,
and the restraint is what makes the rest land. Run on a personal-narrative episode, the scanner
should return *almost nothing* — on one it returned exactly one hit, `"Thirteen years"`, which
is the line that episode's thumbnail is built on.

Two structural devices are worth copying and are not components:

- **Speaker demotion** — when the graphic carries the content, shrink the talking head to a
  corner card and let the graphic own the frame.
- **Attachment** — a figure means more drawn *on* the thing it describes than floating alone.

Detection is deliberately conservative, and the salience model is the part to tune: a figure
earns the screen when it is oddly specific, large, a range (which is always a claim), a money
claim, or a narrative anchor ("thirteen years **ago**"). It loses the screen when it is round,
small and conversational ("give me the next ten minutes").

## Motion graphics

Three layers, and the order matters — components built without the two beneath them produce
exactly the flat, uniform motion that reads as amateur.

**1. Weight, not duration.** Author a ROLE, never a time. `motion.WEIGHTS` maps
`hero / primary / secondary / aside / draw / exit` to its own curve, travel, timing and whether
it earns motion blur. The reference's test is the right one: *"a logo landing and a subtitle
fading in should not feel the same."* Never `linear` — everything lands rather than stops.

Author a role, and note that **transforms and opacity take different curves** — a spring is
what gives position and scale their mass, but on alpha it overshoots past opaque and dips back,
which reads as a pulse. `Weight.at()` for transforms, `Weight.alpha_at()` for opacity.

Do **not** import UI motion numbers here. Web guidance converges on ~150 ms because the user is
waiting on the interface; a video viewer is not, and these weights are deliberately 2-4x slower.
See `kb/gotchas.md`.

**2. A brand per channel** (`brand.json` beside the footage), all sizes as fractions of the
output height so one definition is correct at 720p and 2160p. Derive it:

```bash
uv run python helpers/brand.py <edit>/final.mp4 <thumbnail>.png -o <edit>/brand.json
```

A palette measured off the delivered grade cannot clash with the footage it has to sit on; one
invented in the abstract usually does.

**3. Components**, each corresponding to a row of the taxonomy in *Finding graphic
opportunities*. Times are **absolute output times**, never relative — a component that took a
relative duration and compared it against an absolute clock silently drew nothing at all.

**Speaker demotion** is an EDL block, because it transforms the base picture rather than
drawing on top of it:

```json
"demotions": [
  {"start": 5.67, "end": 10.53, "scale": 0.40, "anchor": "right", "transition": 0.55}
]
```

The talking head eases down into a card and the graphic takes the frame it leaves. Two things
this will get wrong if you are not careful:

- **It is a pairing, not an effect.** A graphic that stays where the head used to be ends up
  drawn on top of the card. Give the demoted beats their own canvas in the vacated area and
  leave the non-demoted beats on a side strip — that usually means two overlay files.
- `pad` cannot place the shrinking picture: its x/y are evaluated **once**, so the frame
  collapses towards the top-left and never re-centres. `overlay` with `eval=frame` is the one
  that works, and the scale needs `eval=frame` too.

**Subject masking** lets a graphic run behind the speaker — the reference's device for its
biggest figure. Build the matte once per base, then mark the overlay:

```bash
uv run python helpers/matte.py <edit>/base.mp4 -o <edit>/mattes/base.mp4
```
```json
"matte": "mattes/base.mp4",
"overlays": [{"file": "big.mov", "start_in_output": 0, "duration": 13.4,
              "behind_subject": true}]
```

The composite draws the behind-overlays on the base, then cuts the subject back out over them
with `alphamerge`. **The picture is never decoded into Python** — only the matte is, which is
why none of the colour round-trip loss in gotchas.md applies here.

Two things to expect: the matte is deliberately dilated and temporally smoothed, because a
slightly generous matte hides a seam where a tight one eats into a shoulder, and per-frame
flicker is far more noticeable than being slightly wrong. And **place the graphic so it extends
past the subject** — a centred graphic behind a centred speaker simply disappears, which looks
exactly like a broken render.

Masking and demotion do not combine: the matte describes the full-frame subject, so it will not
line up with a shrunken card. render.py warns rather than producing a silent misalignment.

**`list_carousel`** is the sliding treatment: columns narrow enough that neighbours stay in
frame (that is what makes it read as a list being traversed), a giant ghosted numeral per
column, dashed dividers, and `ease_in_out` for the slide — a carousel that overshoots reads as
a glitch, where a single element landing wants exactly that overshoot.

Three things worth copying from the reference beyond the components themselves:

- **Hierarchy over symmetry.** In a list, everything that is not the newest item drops to the
  muted colour, so there is always exactly one focus. This does more for the look than any curve.
- **Speaker demotion.** When the graphic carries the content, shrink the talking head to a corner
  card and let the graphic own the frame.
- **Restraint.** About a third of the reference has no graphic at all.

Everything renders to ProRes 4444 with alpha and composites as an `overlays` entry, drawn before
subtitles. Always check alpha on the ENCODED file (`motion.verify_alpha`) — VP9 in this build
returns a valid, fully opaque file.

## Text graphics (titles, lower thirds, chapter cards)

For on-screen *text*, use the EDL's `graphics` block rather than hand-writing `drawtext`. It
costs no extra generation — the filters ride along in the composite encode that has to happen
anyway for subtitles.

```json
"graphics": [
  {"type": "title", "text": "Quick fit check",
   "anchor": {"source": "b-roll1"}, "offset": 0.35, "duration": 2.8,
   "position": "top-right"},

  {"type": "lower_third", "text": "Shoaib", "subtitle": "HSR to Filter Coffee",
   "anchor": {"word": "my name is"}, "duration": 4.0,
   "font": "/System/Library/Fonts/Kohinoor.ttc"},

  {"type": "chapter", "text": "The drive back",
   "anchor": {"source": "IMG_3632"}, "offset": -0.5}
]
```

**Anchor to content, never to a timestamp.** `{"source": X, "nth": n}`, `{"segment": i}`,
`{"word": "some phrase"}` or `{"time": t}` as an escape hatch. The first three resolve against
the *measured* segment durations, so they stay correct when the cut changes — on a real edit a
late round of repairs moved every boundary by ~9 s and the anchored entries needed no rework,
while any hardcoded time would have been wrong. A `word` anchor only matches words the cut
actually keeps, so it can never land on a line you removed.

**Sizes are fractions of the output height** (`font_frac`, `margin_frac`, `y_frac`), so one entry
is right in a 720p draft and a 2160p final.

**Fonts do not fall back.** libass (subtitles) substitutes a face for a missing glyph; `drawtext`
does not — it draws a blank box, silently, in an otherwise perfect file. Measured on macOS:
Helvetica renders Latin but not Devanagari, `DevanagariMT` the reverse, `Kohinoor.ttc` both.
`graphics.py` checks coverage and refuses the render with the offending characters named, so this
fails loudly rather than shipping. Set `font` per entry for anything beyond ASCII.

Anything **animated** is still an `overlays` entry — see below.

## Animations (when requested)

Animations match the content and the brand. **Get the palette, font, and visual language from the conversation** — never assume a default. If the user hasn't told you, propose a palette in the strategy phase and wait for confirmation before building anything.

**Tool options:**

Pick the engine per animation slot. Do not default to Remotion just because the animation is web-adjacent.

- **HyperFrames** — Browser-native HTML/CSS/GSAP video compositions: product UI motion, website-to-video or mockup-to-video captures, kinetic typography, landing-page/storyboard promos, data-driven UI states, transparent WebM overlays, and clips that need deterministic frame capture plus HyperFrames lint/validate/render checks. Best when the animation should be authored and verified like a web composition instead of a React component tree.
- **Remotion** — React/CSS compositions with component state, reusable React primitives, or an existing Remotion brand system. Best when the user specifically asks for React/Remotion or when React composition is the simpler authoring model.
- **Manim** — formal diagrams, state machines, equation derivations, graph morphs. Read `skills/manim-video/SKILL.md` and its references for depth.
- **PIL + PNG sequence + ffmpeg** — simple overlay cards: counters, typewriter text, single bar reveals, progressive draws. Fast to iterate, any aesthetic you want. The launch video used this.

For HyperFrames slots, scaffold the slot inside `edit/animations/slot_<id>/` with `npx --yes hyperframes init . --example blank --non-interactive --skip-skills`, build the HTML composition there, run the HyperFrames checks that fit the slot (`lint`, `validate`, and a draft render when practical), then produce the final overlay video with `npx --yes hyperframes render . -o render.mp4` or `--format webm -o render.webm` when alpha is required. Point the EDL overlay `file` at the actual rendered path.

For Remotion slots, keep the Remotion project isolated inside the same slot directory, scaffold with `npx create-video@latest` or install Remotion locally there, render the composition to `render.mp4` with the project-local `remotion render` command, and verify duration and dimensions with `ffprobe`.

None is mandatory. Invent hybrids if useful (e.g., PIL background with a HyperFrames or Remotion layer on top).

**Duration rules of thumb, context-dependent:**

- **Sync-to-narration explanations.** A viewer needs to parse the content at 1×. Rough floor 3s, typical 5–7s for simple cards, 8–14s for complex diagrams. The launch video shipped at 5–7s per simple card.
- **Beat-synced accents** (music video, fast montage). 0.5–2s is fine — they're visual accents, not information. The "readable at 1×" rule becomes *"recognizable at 1×"*, not *"fully parseable."*
- **Hold the final frame ≥ 1s** before the cut (universal).
- **Over voiceover:** total duration ≥ `narration_length + 1s` (universal).
- **Never parallel-reveal independent elements** — the eye can't track two new things at once. One thing, pause, next thing.

**Animation payoff timing (rule for sync-to-narration):** get the payoff word's timestamp. Start the overlay `reveal_duration` seconds earlier so the landing frame coincides with the spoken payoff word. Without this sync the animation feels disconnected.

**Easing** (universal — never `linear`, it looks robotic):

```python
def ease_out_cubic(t):    return 1 - (1 - t) ** 3
def ease_in_out_cubic(t):
    if t < 0.5: return 4 * t ** 3
    return 1 - (-2 * t + 2) ** 3 / 2
```

`ease_out_cubic` for single reveals (slow landing). `ease_in_out_cubic` for continuous draws.

**Typing text anchor trick:** center on the FULL string's width, not the partial-string width — otherwise text slides left during reveal.

**Example palette** (the launch video — one aesthetic among infinite):
- Background `(10, 10, 10)` near-black
- Accent `#FF5A00` / `(255, 90, 0)` orange
- Labels `(110, 110, 110)` dim gray
- Font: Menlo Bold at `/System/Library/Fonts/Menlo.ttc` (index 1)
- ≤ 2 accent colors, ~40% empty space, minimal chrome
- Result: terminal / retro tech feel

This is one style. If the brand is warm and serif, use that. If it's colorful and playful, use that. If the user handed you a style guide, follow it. If they didn't, propose one and confirm.

**Parallel sub-agent brief** — each animation is one sub-agent spawned via the `Agent` tool. Each prompt is self-contained (sub-agents have no parent context). Include:

1. One-sentence goal: *"Build ONE animation: [spec]. Nothing else."*
2. Absolute output path (`<edit>/animations/slot_<id>/render.mp4`)
3. Exact technical spec: resolution, fps, codec, pix_fmt, CRF, duration
4. Style palette as concrete values (RGB tuples, hex, or reference to a design system)
5. Font path with index
6. Frame-by-frame timeline (what happens when, with easing)
7. Anti-list ("no chrome, no extras, no titles unless specified")
8. Code pattern reference (copy helpers inline, don't import across slots)
9. Deliverable checklist (script, render, verify duration via ffprobe, report)
10. **"Do not ask questions. If anything is ambiguous, pick the most obvious interpretation and proceed."**

One sub-agent = one file (unique filenames, parallel agents don't overwrite each other).

## Output spec

Match the source unless the user asked for something specific. Common targets: `1920×1080@24` cinematic, `1920×1080@30` screen content, `1080×1920@30` vertical social, `3840×2160@24` 4K cinema, `1080×1080@30` square. `render.py` defaults the scale to 1080p from any source; pass `--height` for other targets (e.g. `--height 2160` to deliver at a 4K source's own resolution, `--height 1920` for vertical). Width follows the source aspect, so `--height` is the only resolution knob you need — do not hand-edit the extract command. Worth asking the user which delivery format matters.

## EDL format

```json
{
  "version": 1,
  "sources": {"C0103": "/abs/path/C0103.MP4", "C0108": "/abs/path/C0108.MP4"},
  "ranges": [
    {"source": "C0103", "start": 2.42, "end": 6.85,
     "beat": "HOOK", "quote": "...", "reason": "Cleanest delivery, stops before slip at 38.46."},
    {"source": "C0108", "start": 14.30, "end": 28.90,
     "beat": "SOLUTION", "quote": "...", "reason": "Only take without the false start."}
  ],
  "grade": "warm_cinematic",
  "overlays": [
    {"file": "edit/animations/slot_1/render.mp4", "start_in_output": 0.0, "duration": 5.0}
  ],
  "subtitles": "edit/master.srt",
  "total_duration_s": 87.4
}
```

`grade` is a preset name or raw ffmpeg filter. `overlays` are rendered animation clips. `subtitles` is optional and applied LAST.

`audio_filter` is an optional global audio chain (denoise, EQ) applied per segment **before** the 30ms fades, so the fades stay on the true segment edges (Hard Rule 3).

`ranges[].zoom` is an optional per-segment push-in (a number ≥ 1.0, with `zoom_x` 0–1 biasing the crop horizontally, default 0.45). Use it to disguise jump cuts on a static single-camera shot: crop to 1/zoom of the frame, then scale back. It is a plain number rather than a filter string precisely so one EDL stays correct at every output resolution. `ranges[].filter` remains available as a raw per-segment escape hatch, but a hardcoded `crop` is only valid at one output height, and **any per-segment dimension mismatch breaks the lossless concat** (Hard Rule 2).

## Output quality

The video is encoded **twice**: once per segment on extract, then again to composite overlays and burn subtitles. The concat and the loudness pass are both `-c copy`, so those are lossless. This means the **extract CRF is the quality ceiling** — the composite encode can only add loss on top of it, never recover detail.

- `--crf` sets that ceiling. Defaults: 16 final, 22 `--preview`, 28 `--draft`. The composite encode is derived as `crf - 2`.
- `--height` sets the output height; the default 1080 downscales a 4K source and throws away three quarters of its pixels. Pass `--height 2160` to deliver at the source resolution and skip that generation entirely.

If someone reports the output looking soft or compressed, check **bits per pixel**, not bitrate: a 50 Mbps 4K source and a 12.7 Mbps 1080p render are both ≈0.25 bits/px, which means the loss came from discarded pixels and stacked generations rather than bitrate starvation.

## Memory — `project.md`

Append one section per session at `<edit>/project.md`:

```markdown
## Session N — YYYY-MM-DD

**Strategy:** one paragraph describing the approach
**Decisions:** take choices, cuts, grades, animations + why
**Reasoning log:** one-line rationale for non-obvious decisions
**Outstanding:** deferred items
```

On startup, read `project.md` if it exists and summarize the last session in one sentence before asking whether to continue.

## Anti-patterns

Things that consistently fail regardless of style:

- **Hierarchical pre-computed codec formats** with USABILITY / tone tags / shot layers. Over-engineering. Derive from the transcript at decision time.
- **Hand-tuned moment-scoring functions.** The LLM picks better than any heuristic you'll write.
- **Whisper SRT / phrase-level output.** Loses sub-second gap data. Always word-level verbatim.
- **Running Whisper locally on CPU.** Slow and it normalizes fillers. Use hosted Scribe.
- **Burning subtitles into base before compositing overlays.** Overlays hide them. (Hard Rule 1.)
- **Single-pass filtergraph when you have overlays.** Double re-encodes. Use per-segment extract → concat.
- **Linear animation easing.** Looks robotic. Always cubic.
- **Hard audio cuts at segment boundaries.** Audible pops. (Hard Rule 3.)
- **Typing text centered on the partial string.** Text slides left as it grows.
- **Sequential sub-agents for multiple animations.** Always parallel.
- **Editing before confirming the strategy.** Never.
- **Re-transcribing cached sources.** Immutable outputs of immutable inputs.
- **Assuming what kind of video it is.** Look first, ask second, edit last.
