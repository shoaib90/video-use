---
name: shorts
description: "BUILD a vertical 9:16 Short (20-60 s) from a finished long video, once the moment is chosen (picking and writing are /youtube-agent:yt-shorts): re-order it so the strongest line comes first, rebuild it from the long video's own sources with a face-centred crop, and give it the long video's treatment (its cards as stamps, its bed and effects), a thumbnail-style opening plate and bold 2-3 word captions. One spec file per Short; one script does build, plate, captions, render, mix, review and a phone preview. Use when Shoaib asks for Shorts, clips or verticals from a video."
version: 1.1.0
---

# Shorts

A Short is **one moment from a long video that survives without the video around it**, built so
the first two seconds stop the thumb. This skill was built on Episode 4's Shorts (2026-10-14). Its
v1 was a bare talking head with sentence captions. Shoaib called it "very plain" (kb/mistakes.md
**M053**), and the v2 lessons are written into the steps below.

**Read first, every time:** the channel's Shorts rules in the private channel-kb,
`03-formats/shorts.md`: where Shorts come from, the zenith rule, cadence, how they are judged.
Never copy channel-kb text into this repo. Then `kb/index.md` and the "Shorts (9:16)" section of
`kb/gotchas.md`.

## The process

```bash
SH="uv run python skills/shorts/scripts/shorts.py"     # from the repo root
$SH <edit> <name> <command>                          # spec: <edit>/shorts/<name>/short.json
```
`<edit>` is the long video's edit dir (it holds `edl.json` and `transcripts/`). Everything is
written to `<edit>/shorts/<name>/` (Hard Rule 12).

### 1. Pick and write it: `/youtube-agent:yt-shorts`, then confirm (Hard Rule 11)
**This skill only BUILDS.** Choosing the moment and writing it belong to the youtube-agent plugin.
Do not duplicate its rules here:
- **`/youtube-agent:yt-shorts`** picks the candidates (complete opening thought, a turn, ends on
  a line; top five with timecodes and first lines). It writes the opening line, the on-screen
  text and the loop point. For a new episode, the script's `[SHORT]` marks come first.
- **Channel difference:** yt-shorts says "write a NEW first line". Our Shorts are cut only from
  footage already shot (channel-kb rule), so the "new" first line is the strongest line Shoaib
  already said, **moved to the front**. Reordering is still "cut from the long video".
- **Score the candidate openings** with yt-script's `hookscore.py`
  (`python3 "$(dirname "$(find ~/Library/Application\ Support/Claude -name hookscore.py -path '*yt-script*' | head -1)")/hookscore.py" hooks.txt`).
  Use it to rank lines **relative to each other** only. The tool says it barely separates a
  creator's hits from misses, and every Episode 4 hook scored WEAK (21-40).
- Never the zenith while the long video is new. Show Shoaib the candidates, and cut nothing until he picks.

### 2. The editing rules (Shoaib's notes on Episode 4 v1)
- **Do not say the hook line twice.** Once it opens the Short, cut it from where it sat in the story.
- **Cut every repeat and restart:** a Hindi restatement of the English line, "I mean, when I…",
  a pause inside a phrase. Whisper each join; a cut pause can hide a repeated word
  ("he… uh… he said").
- **One story.** A second payoff (a figure that is also the thumbnail's hook) belongs to the long
  video. When unsure, build both and test them.
- **The payoff gets a punch-in** (`"zoom": "punch"`, 1.25) and plays **with no music**: the bed drops out under
  it and returns on the next line with a soft hit (kb/storytelling.md §10).
- Every edge goes in the quietest 10 ms nearby, and each side is checked by whisper ALONE (M048).

### 3. Write the spec: `<edit>/shorts/<name>/short.json`
```json
{
 "output": "episodeN_short_<name>",
 "parent": "../../edl.json",
 "plate": {"kicker": "SMALL YELLOW LINE.", "big": "BIG WHITE LINE.", "seconds": 3.0},
 "punch": 1.25,
 "ranges": [
  {"source": "IMG_0001", "start": 124.72, "end": 128.30, "quote": "the hook line", "zoom": 1.0},
  {"source": "IMG_0001", "start": 95.58, "end": 96.80, "quote": "…", "zoom": 1.12},
  {"source": "IMG_0001", "start": 168.87, "end": 172.97, "quote": "the payoff", "zoom": "punch"}
 ],
 "cards": [{"id": "fig", "kind": "stamp", "text": "3 AM", "at": "spoken phrase",
            "position": "top-center", "accent": true, "scale": 0.68}],
 "captions": [[0, "Three words *here*"], [3, "next burst"]],
 "mix": {
  "beds": [{"file": "ES_Track.mp3", "src": 58.0, "from": 0.0, "to": "phrase where it stops",
            "fade_in": 0.3, "fade_out": 0.06, "lift": [14, 3, 2]},
           {"file": "ES_Track.mp3", "src": "sync", "from": {"phrase": "next line", "shift": -0.05},
            "to": "end", "fade_in": 0.8, "fade_out": 2.5}],
  "hits": [{"sfx": "click", "at": "spoken phrase", "trim": -5},
           {"file": "structural/ES_….mp3", "offset": 0.0,
            "at": {"phrase": "said twice", "after": "an earlier phrase", "shift": 0.45}, "trim": -8}]
 }
}
```
- **ranges:** `zoom` is 1.0, 1.12, `"punch"`, or omitted (then it alternates with the range before).
  The build warns on two same-take ranges at the same zoom (a visible jump) and on a push-in
  below 1.1x. Add `"face": [x, y]` (frame fractions) where detection fails.
- **plate:** at most 6 words and different from the spoken line, held about 3 s. The thumbnail
  style is a yellow kicker over big white type on a dark plate.
- **cards:** carry the **parent's cards** for the kept moments; review G4 flags any you drop.
  Use stamps at `scale` 0.68 (a portrait stage is 607 units wide; cards.py refuses a stamp
  that would clip) and stats at about 0.75. Anchors are spoken phrases.
- **captions:** English for Shorts (Shoaib, 2026-10-14). English lines stay as spoken; translate the
  Hindi. Each burst is `[index of its first kept word, text]`, 2-3 words, with `*word*` in the
  brand orange: numbers, the turn word, the payoff. Get the indices from `words`. Deepgram
  lists words a cut made inaudible (a second "first", "came", "it"), so cover them with a
  neighbouring burst and never give one its own.
- **mix:** music is resolved under `$SHORTS_LIBRARY/music`, effects under `$SHORTS_LIBRARY/effects`
  (default `~/Documents/Ambitious/Editing`). `sfx` names come from the motion-graphics-pass table.
  Use the **parent's bed for that scene**: about 26 dB under the voice, lifted under the plate.
  `"src": "sync"` continues the same track in time, so it is a drop-out, not a new cue.

### 4. Build and render
```bash
$SH <edit> <name> build      # prints every range's zoom + crop; read the warnings
$SH <edit> <name> words      # author the caption bursts against these indices
$SH <edit> <name> all --label v1    # plate, captions, render, mix, review, phone preview
```
A full 1080x1920 render of about 60 s takes a few minutes on this Mac. Each step can run alone
(`plate`, `captions`, `render`, `mix`, `review`, `preview`).

### 5. Before it reaches Shoaib
1. review.py shows **HIGH 0 / MED 0 after accepted.json**. Each deliberate edge (the moved
   hook, a cut repeat) gets a `why` in `<short>/review/accepted.json`. **G4 passes.**
2. **Whisper the whole render** and read it back as prose. The English model invents words on
   Hindi lines, so check those with `ggml-small.bin -l hi`.
3. **Look at a frame sheet:** the plate is readable, every stamp sits inside the frame, the
   captions sit clear of the Shorts UI (y ~1380 of 1920), and no screen or label is legible (R4).
4. `READ R12`: everything G4 cannot see (mgx cues, effects, the bed) is carried or dropped for a
   stated reason.
5. **Lint the title against the plate** with yt-package's `title.py`
   (`python3 title.py --title "…" --thumb "<plate text>"`, from that skill's folder; find it like
   hookscore.py). The channel rule is that a Short's title never repeats its on-screen text, and
   `title.py` flags any shared word. It caught that on Episode 4: "…in my first interview" against
   "FIRST INTERVIEW. NEVER CODED.". Ignore its `thumb-length` warning: a Short's plate is not a feed thumbnail.
6. Send the phone preview (`phone_preview_*_do_not_upload.mp4`, <30 MB) and the copy block:
   file, length, plate text, the linted title, and Related video set to the long video. Post on
   a day between long uploads.

## Known traps (all measured on Episode 4)
- **Never crop the delivered final.** Its burned captions and cards land half inside the 9:16
  window. Rebuild from the parent's sources; the spec reuses its grade and brand.
- `render.py --draft` alone renders at 720 and breaks the 1080x1920 crop. This script always
  passes `--height 1920`.
- `cards.py --clips clips_graded` on a re-cut Short reads stale segments. Trust the render log.
- An empty `force_style` makes render.py fall back to Helvetica over the `.ass` styles, so the
  EDL carries `Bold=1`.
- render.py's one-pass loudnorm lands around -14.8 LUFS. The `mix` step normalises to -14 itself.
- The mix is **not bit-reproducible after the last effect ends** (an ffmpeg quirk: up to a -29 dB
  peak there, identical before it). Compare remixes by ear in that window, not by hash.
