# Gotchas

Verified traps only. Each entry says how it was confirmed.

---

## `brew install ffmpeg` gives you a binary that cannot burn subtitles

**Symptom:** `render.py --build-subtitles` dies at the composite step with ffmpeg exit 234.
`master.srt` is generated correctly — only the burn-in fails. Error text is misleading:
`No option name near '/path/to/master.srt'`, which reads like a quoting bug but isn't.

**Cause:** Homebrew split ffmpeg. The `ffmpeg` formula has 11 deps and **libass is not one of
them**; libass moved to `ffmpeg-full` (47 deps). Without libass the `subtitles` and `ass`
filters do not exist in the binary at all.

**Confirm:**
```bash
ffmpeg -hide_banner -filters | awk '{print $2}' | grep -x 'subtitles\|ass'   # empty ⇒ broken
ffmpeg -hide_banner -version | grep -o enable-libass                        # empty ⇒ broken
```

**Fix:** install `ffmpeg-full` and link it over the slim build (it's keg-only, so it won't take
over `$PATH` on its own). See [environment.md](environment.md) for this machine's state.

**Note:** `install.md` upstream says `brew install ffmpeg`, which is now wrong on macOS for any
project needing subtitles. Everything else in the pipeline works fine on the slim build.

---

## Establish the spoken language BEFORE transcribing — `en` silently destroys code-switched audio

The single most expensive mistake so far. A Bangalore vlog was transcribed with
`--language en`. The speaker was actually speaking **Hinglish** — Hindi and English mixed
mid-sentence. Deepgram did not error, warn, or return low confidence. It produced fluent,
plausible English nonsense:

| `--language en` | `--language multi` (truth) |
|---|---|
| "Within me a golf course car" | "एक भी दिन नहीं लेके गया मैं अभी तक office car" |
| "A beach a very rare thing" | "अभी छब्बीस kilometer या छब्बीस minute ही दिखा रहा है" |
| "It's Cape Cod, hopefully" | "इसके बाद hopefully" |

Re-transcribing with `multi` recovered **+37% more words** (983 → 1352 across 14 clips).

**Why it matters far beyond captions:** the cut is *reasoned from the transcript*. Mistranscribed
passages were judged as "garbled, drop it" or read with the wrong meaning entirely — one was
planned as a scenery beat when it was actually a joke about the navigation ETA. An entire
narrative thread (rain, set up four clips before its payoff) was invisible, so the first cut plan
missed the spine of the video and came out 3:05 instead of 4:26.

**Rules:**
- On the first clip of any new source, **check what language is actually being spoken** before
  transcribing the batch. One clip's transcript read against a frame is enough.
- For code-switched audio use `--language multi`. **`detect_language=true` does not work** for
  this: it commits to a single language per file (it picked `en` and mangled the Hindi).
- Treat fluent-but-nonsensical output as a language-mismatch signal, not speaker error. Real
  speech disfluency looks like repetition and false starts; a language mismatch looks like
  confident, grammatical gibberish.
- `language` is part of the transcript's cache identity (`_language`), so a re-run with a
  different language is refused rather than silently returning the old file.

**Captions for mixed script work fine.** Devanagari + Latin in one cue renders correctly through
libass; `FontName=Kohinoor Devanagari` balances the two scripts best, and Helvetica falls back
correctly but renders Devanagari slightly small against the Latin. macOS has plenty of
Devanagari faces (`fc-list :lang=hi family`).

---

## render.py scales portrait and landscape sources to DIFFERENT sizes, so mixing them breaks concat

`extract_segment` picks its scale axis from `is_portrait_source()`: a portrait source becomes
2160×3840, a landscape one 3840×2160. Put both in one EDL and the `-c copy` concat (Rule 2)
fails, because segments must share dimensions.

This is not hypothetical — a phone shoot will mix orientations the moment the user turns the
phone, and on the trip that produced this note the *arrival payoff* was the portrait clip.

Fix without touching render.py: pre-render the odd-orientation clips to the majority geometry
into `<edit>/prepped/`, pillarboxed over a blurred scaled copy of themselves:

```
split[bg][fg];[bg]scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,gblur=sigma=32[b];
[fg]scale=-2:2160[f];[b][f]overlay=(W-w)/2:0
```

Then point the EDL `sources` entry at the prepped file **under the original source name**, so
`render.py`'s caption lookup (`transcripts/<source_key>.json`) still resolves and the word
timings still line up — the prep must not retime or trim.

---

## iPhone rotation metadata is not always consistent within one shoot

On a 14-clip shoot, thirteen clips carried `rotation=-90` and one carried `+90` — a 180°
difference. Both are quarter-turns, so both *display* as landscape and any width/height check
passes; the odd one just comes out **upside down**. Nothing in `ffprobe`'s dimensions reveals it.

Look at a frame from every clip during inventory. It is the only way to catch this, and it is
cheap next to discovering it in a finished render.

---

## Each ASR provider has a different characteristic flaw

Measured 2026-09-03 on one clip of macOS `say` TTS. Ground truth:
*"Um, so ninety percent of what a web agent does is, uh, completely wasted. We fixed this."*

| Provider | Output | Flaw |
|---|---|---|
| Deepgram nova-3 | `So ninety percent … is, uh, completely wasted.` | **dropped the leading `Um,`** (absorbed into a 0.72s `So` token) |
| whisper `small.en` | `Um, so 90% … is, ah, completely wasted,` | keeps `Um,`; **normalizes** `ninety percent`→`90%`; `uh`→`ah` |
| whisper `base.en` | `Um, so 90% … completely w usted.` | as above **plus a real word error** ("w usted") |

**Takeaways.**
- Deepgram is the production default: best mid-sentence verbatim fidelity, and it diarizes.
- Its dropped leading filler matters — cutting fillers is a headline feature, and a filler the
  ASR never reports is invisible to the cut logic and survives into the video. When leading
  fillers matter, cross-check with whisper (it's free) or look at the waveform in `timeline_view`.
- Never use `base.en`; `small.en` is the floor for local work.
- whisper's number normalization is in tension with Hard Rule 8 — don't burn captions from a
  whisper transcript without reading them first.

**Confirmed on real footage (2026-09-08).** On a 25-clip talking-head shoot Deepgram
transcribed "Here's what I **do** know" as "what I **don't** know" — one word that inverts the
thesis of the whole section, and there was only one take of the line. whisper `small.en` read it
correctly, as did the script, and **the speaker later confirmed "do"** — so this is a measured
Deepgram error on real human speech, not an inference from two agreeing sources. The free local
cross-check paid for itself: without it the line would have been cut as a mis-speak, or the wrong
word burned into a caption.

**Caveat:** the table above is one clip, synthetic TTS speech. `say`'s "Um," is a poor proxy for a human one.
Re-measure on the first real footage before treating any of this as settled.

---

## Deepgram has no audio-event tokens

Scribe emits `(laughter)`, `(applause)`, `(sigh)` as `type: "audio_event"`. Deepgram's standard
STT response has no equivalent, so `transcribe_deepgram.py` emits every token as `type: "word"`.

`SKILL.md`'s cut craft leans on these as beat markers ("the laugh IS the beat"). Costs nothing
for a single talking head; a real downgrade for interviews or reaction-heavy footage. Compensate
with silence gaps and more `timeline_view` drill-downs.

*(One web source claimed Deepgram supports audio events, but cited Speechmatics/ElevenLabs docs.
Treated as unverified. Worth re-checking against the Deepgram dashboard.)*

---

## Transcript filenames must match EDL source keys

`render.py`'s SRT builder looks up `transcripts/<source_key>.json` where `source_key` is the key
in the EDL's `sources` object — not the filename of the video. Mismatch fails **soft**: it prints
`no transcript for <key>, skipping captions for this segment` and renders a caption-less segment.
Easy to miss in a long log.

---

## `pytest` is not a declared dependency

`uv run python -m pytest` fails with `No module named pytest`. Use:
```bash
uv run --with pytest python -m pytest tests/
```
16 tests, all passing as of 2026-09-03.

---

## The concat requires one frame rate for the whole render

`render.py` resolves a single output rate for every segment because the lossless `-c copy`
concat (Hard Rule 2) breaks if segments differ. If an EDL mixes a 30fps and a 60fps source,
the default (first source's rate) is applied to all — pass `--fps` explicitly when mixing.

---

## `speechnorm` destroys speech/noise separation on noisy footage

Measured on a car-interior vlog (road noise, 4.4 dB raw speech-to-noise separation):

| Chain | noise floor | speech | separation |
|---|---|---|---|
| raw | −18.9 dB | −14.5 dB | **4.4 dB** |
| `highpass=90,afftdn=nr=14` | −23.5 | −18.4 | 5.1 dB |
| `highpass=100,afftdn=nr=24` | −24.3 | −18.9 | 5.4 dB |
| `highpass=110,afftdn=nr=30,deesser` | −25.5 | −19.5 | **6.0 dB** |
| `anlmdn` | −24.1 | −18.8 | 5.3 dB |
| `afftdn + speechnorm=e=12.5` | −13.7 | −13.7 | **0.0 dB** ← |

`speechnorm` (and aggressive `dynaudnorm`) lift quiet passages toward the target, which on noisy
footage means **lifting the road noise to the same level as the voice**. Never use them to
"fix" a noisy talking head. `loudnorm` is program-level and does not have this failure mode.

Also: broadband noise that overlaps speech frequencies barely responds to spectral denoise —
the best chain here bought only **+1.6 dB**. The real win on such footage is *cutting the dead
air*, which deletes the passages where noise is exposed and unmasked. During speech the voice
masks it.

`arnndn` (RNN denoise) would likely do better but needs a `.rnnn` model file; none ships with
Homebrew's ffmpeg. Untested here.

---

## render.py encodes the video TWICE, and upstream exposes no quality control

The pipeline is **two generations of H.264**:

| Step | Action |
|---|---|
| extract per segment | **encode** (CRF 22 preview / was 20 final) |
| concat | `-c copy` — lossless |
| burn subtitles / overlays | **re-encode** (was hardcoded CRF 18) |
| loudnorm | `-c:v copy` — lossless |

The *extract* CRF is the quality ceiling; the composite encode can only add loss on top. Upstream
hardcoded both and defaulted to a `scale=1920:-2` downscale, so a 4K source lost 3/4 of its
pixels with no way to opt out. A user noticing "this looks compressed" is this, not the preview
mode alone.

Diagnostic that isolates it: compare **bits per pixel**, not bitrate. A 4K source at 50 Mbps and
a 1080p output at 12.7 Mbps are both ≈0.25 bits/px — identical per-pixel quality, so the loss was
pixels and generations, not bitrate starvation.

Local fix (branch `local`): `--height` and `--crf` flags; final defaults to CRF 16 / `slow`; the
composite CRF is derived as `gen1 - 2` so the second generation adds minimal further loss.
Rendering the same edit at `--height 2160 --crf 16` gave 0.451 bits/px — 1.8× the source's own
per-pixel budget, with no downscale generation at all.

Cost: **960 MB for 85s** (89.8 Mbps). CRF 18-20 at 2160p is the practical sweet spot; reserve
CRF 16 for masters.

---

## One head branch cannot serve two PRs once their bases diverge

The three change-sets were raised twice — once against upstream, once against the fork — reusing
the same head branch for both. That works only while both bases are identical.

When fork PR #1 was merged into the fork's `main`, fork PR #2 conflicted (both touched
`build_final_composite`'s signature and `main()`). Rebasing that shared branch onto the fork's
`main` fixed the fork PR and **silently corrupted the upstream one**: upstream #159 grew from
+82/-9 to +295/-21, absorbing #1's commits plus a fork merge commit, because upstream's `main`
does not contain #1.

Nothing warns you about this. `gh pr view <n> --json mergeable` still said MERGEABLE — the PR was
mergeable, just no longer the change it claimed to be. **After force-pushing a branch that backs
more than one PR, check every PR's diff size, not just its mergeability.**

Resolution is one branch per base:

| Branch | Base | Serves |
|---|---|---|
| `pr/<topic>` | upstream `main` | the upstream PR |
| `merge/<topic>` | fork `main` | the fork PR |

The upstream PR keeps the original branch, because review comment threads attach to the PR and
would be lost by closing it.

**Merge order matters for the rest.** Each fork merge into `main` can conflict the siblings that
touch the same functions. The conflicts here were all *additive* — each side added parameters and
neither replaced the other — so the resolution is to keep both, never to pick a side.

---

## Never predict another tool's rounding — measure it

`probe_scaled_dims()` originally computed ffmpeg's `scale=-2` width in Python as
`round(w/h*out_h/2)*2`, then used that as a hardcoded scale-back target for the zoom crop. Tested
against ffmpeg across six non-16:9 aspects at three target heights: **it agreed every time**.

It was still wrong, for a reason the test could not reach: `-2` also honours **sample aspect
ratio**, which arithmetic over coded dimensions ignores completely. Any anamorphic source would
have diverged, and a 2px mismatch between a zoomed segment and its siblings breaks the `-c copy`
concat (Rule 2).

The fix is to ask ffmpeg — one frame through the real scale filter, cached per (source, height) —
and then use that measured value as an **explicit** `scale=W:H` for every segment. Zoomed and
unzoomed siblings then match by construction rather than by agreement.

Generalisable: when correctness depends on matching another program's output, measure its output.
"My arithmetic agrees on the cases I tried" is not the same claim.

*(Test-harness trap while checking this: a `testsrc` at odd dimensions fails to encode in
yuv420p, leaving a 0-byte file, and `ffprobe` then reports the **previous** loop iteration's
value — which looks exactly like a real mismatch. Check file size before trusting a probe.)*

---

## A cache keyed only on the file path silently crosses providers

All three transcribers write to `transcripts/<stem>.json`, because everything downstream expects
exactly one transcript per source. That makes the *path* a bad cache key:

- A Scribe transcript already on disk made `transcribe_deepgram.py` print `cached:` and return
  Scribe's JSON, **never contacting Deepgram at all**. The alternative provider could not
  actually produce its own output without manually clearing the cache.
- The key also ignored `--model` and `--spacing-threshold`, so re-running with different options
  returned a stale file.

Since the path must stay shared, identity lives *in* the file: every transcript is stamped with
`_provider`, `_model` and `_spacing_threshold`, and `check_cached()` reads them back and refuses
on a mismatch (naming what differs) rather than returning the wrong file. `--force` always
re-transcribes. A missing `_provider` means Scribe, since `transcribe.py` writes its response
verbatim.

Both `transcribe_deepgram.py` and `transcribe_whisper.py` now do this. The whisper copy is
deliberately a small duplicate rather than a shared import, so the Deepgram helper stays
byte-identical to the version proposed upstream.

---

## Per-segment reframes must be a number, not a filter string

A `crop=1812:1018,scale=1920:1080` written for 1080p silently becomes wrong at any other output
height, and *any* per-segment dimension mismatch breaks the `-c copy` concat (Rule 2).

Relative expressions do **not** rescue this: `scale=iw*1.06` then `crop=iw/1.06` fails to
round-trip to the exact original size once each step is rounded to even dimensions — 1920 comes
back as 1918, and segments without a filter stay 1920, so the concat fails.

The working shape (branch `local`) is a numeric `ranges[].zoom` (plus optional `zoom_x` bias)
that render.py resolves against the *actual* post-scale dimensions via `probe_scaled_dims()`,
which mirrors the scale expression exactly. Verified: all 13 segments of a mixed
1.00×/1.06×/1.12× edit came out at exactly 3840×2160.

---

## `--draft` renders 720p, so EDL `filter` values written for 1080p break

`extract_segment` scales to `1280:-2` in draft mode but `1920:-2` for preview **and** final. A
per-segment `crop=1812:1018,...` sized for 1080p therefore fails on a 720p draft (crop larger
than input).

Preview and final share the same 1920×1080 geometry, so pixel-exact crops are safe there. To
cut-check cheaply with a draft, strip the filters first:

```python
for r in edl["ranges"]: r["filter"] = ""
```

Resolution-independent expressions are not a clean fix: `scale=iw*Z` then `crop=iw/Z` fails to
round-trip to the exact original dimensions, and any per-segment dimension mismatch breaks the
`-c copy` concat.

---

## iPhone `.MOV` files carry three traps at once

Verified on a 2026 iPhone 4K clip:

1. **Two audio tracks** — AAC stereo *and* a 4-channel `apple_apac` spatial track. ffmpeg's
   default audio selection picks the stream with the **most channels**, i.e. the spatial one.
   The `transcribe_*.py` helpers map `0:a:0` explicitly, so they get the stereo track; anything
   you write by hand must do the same or `--audio-track`.
2. **HLG HDR, 10-bit** (`color_transfer=arib-std-b67`, `bt2020`, `yuv420p10le`). `render.py`
   detects this via `is_hdr_source` and applies `TONEMAP_CHAIN`. Skip the tonemap and you get a
   washed-out grey image.
3. **Rotation metadata** — `rotation=-90` with stored dimensions 2160×3840, which *displays* as
   3840×2160 landscape. Never infer orientation from `width`/`height` alone; `is_portrait_source`
   accounts for the rotation side-data.

Plus a fistful of `codec_type=data` streams that are safe to ignore.

---

## Isolating a snippet makes ASR *worse*, not better

Tempting move when a phrase is garbled: cut out those 6 seconds and re-transcribe just them.
Measured result — the isolated pass was markedly worse than the full-file pass:

| | full file | 6s snippet alone |
|---|---|---|
| name | "Sh oa ib" (correct) | "Virak" |
| phrase | "The palace is decided, it's just that I take my car" | "For the palace I could decide it knew that I take my card" |

Language models use surrounding context. To disambiguate a phrase, run a **different** engine
over the **whole** file instead, and if two engines agree on something that makes no sense, ask
the user rather than guessing — a burned-in caption is not the place for a guess.

---

## zsh does not word-split unquoted parameter expansions

The default shell here is zsh. This bash idiom silently misbehaves:

```bash
for w in "10 8 label"; do set -- $w; echo "$3"; done   # $3 is EMPTY in zsh
```

zsh keeps `$w` as one word, so `$1` becomes the whole string. Use an explicit function with
positional args, a proper array, or `${=w}` to force splitting. Bit me twice in one session,
both times producing empty output that looked like a tool failure rather than a shell bug.

Hit again on 2026-09-22, in the `for spec in "3653 15" "3657 30"; do set -- $spec` form, this
time feeding `ffmpeg -ss $2 -i "IMG_$1.mov"` — which produced `Invalid duration for option ss:
-i` and an attempt to open `IMG_3653 15.mov`. Parallel arrays indexed with `{1..N}` are the
least error-prone fix, because unlike `${=spec}` they are also correct under bash.

---

## Piping a command to `tail` masks its exit code

Bit me during setup: `uv sync --extra animations 2>&1 | tail -25` reported **exit 0** while the
install had actually failed (`pycairo` couldn't find cairo). The 0 came from `tail`, not `uv`.

Use `set -o pipefail`, or redirect and check separately:
```bash
uv sync --extra animations > /tmp/log 2>&1; echo "EXIT=$?"; tail -6 /tmp/log
```
Relevant well beyond this repo, but especially here — several helpers shell out to ffmpeg, and a
masked non-zero status looks exactly like success.

---

## Caption offsets drifted because Rule 5 summed EDL floats, not rendered segments

**Fixed on `local`.** `build_master_srt` accumulated `seg_offset += (end - start)` from the
EDL. But an extract is quantised to whole frames, so the real segment is a fraction of a frame
longer than the float arithmetic says. The error accumulates: on a 30-segment, 3m34s edit the
captions ran **0.598s early by the closing line** (0 at the first cue, growing monotonically).

Hard Rule 5 is `output_time = word.start - segment_start + segment_offset`, and
`segment_offset` has to be where the segment *actually* starts in the concat.

`build_master_srt` now takes an optional `segment_paths` and measures them with `ffprobe`
(the clips already exist when it is called — it runs after the concat). Without that argument
it falls back to the old float sum, so nothing else changes.

Two things that made this easy to miss:
- The first cue is always correct. Only the tail is wrong, and by then nobody is checking sync.
- It is invisible in a short test EDL. It needs ~20+ segments to grow past a frame or two.

**Draft, preview and final produce bit-identical segment durations** (verified: 30 clips, max
per-segment difference 0.0 ms). So a cheap `--draft` pass is a valid way to measure boundaries
for a 4K final — which is also how to place an overlay's `start_in_output` correctly.

---

## An overlay's `start_in_output` must be measured, not summed

Same root cause as above, different symptom. The Scene-3 b-roll montage was placed at the
teaser's start computed from summed float durations: it landed **0.205s early**, sliding every
shot change off its word and the bat SFX off its hit.

Fix: render once (`--draft` is enough), measure the segment durations, feed the real boundary
back into the EDL. And set the overlay's `duration` to exactly the span you want covered while
cutting the *clip* slightly longer — an under-run silently reveals the base video, which in
this case was the take where the speaker is holding his phone.

---

## Trimming a filler word leaves it in the captions

`_words_in_range` selects any word that *overlaps* the segment, so a cut that lands inside a
word keeps that word's text while discarding its audio. Trimming "uh," by cutting at 21.97
when the token spans 21.79–22.02 removed the sound and left `uh, something that I've read…`
burned into the frame.

This is Hard Rule 6 ("never cut inside a word") having a consequence beyond audio. The fix is
to snap the edge to the word boundary — `IN = target.start - pad` clamped to `prev.end + eps`,
`OUT = last.end + pad` clamped to `next.start - eps`. Then the overlap test selects exactly the
kept words, for free.

Worth running as a standalone check over an EDL before rendering: for every edge, flag any word
with `start < edge < end`. On a 30-segment cut this found 15, including two OUT points computed
from a word's *start* instead of its *end* — one of which was chopping the last word of the
video mid-syllable.

---

## zsh treats `$VAR:x` as a history modifier

Second zsh trap in this KB (see also: no word-splitting). This silently corrupts ffmpeg filter
strings:

```zsh
F=/System/Library/Fonts/Avenir.ttc
echo "$F:textfile"     # -> Avenir.ttcextfile     (`:t` = tail of path, then "extfile")
echo "${F}:textfile"   # -> /System/Library/Fonts/Avenir.ttc:textfile
```

The resulting ffmpeg error is `Either text, a valid file, a timecode or text source must be
provided`, which reads like a drawtext quoting problem and sends you off escaping apostrophes.
It is not. **Always brace a variable that is followed by `:` in a filter string.**


---

## A post-pass that runs after a capped loop can be a silent no-op

`subtitle_style.balance` was meant to split each punctuation-delimited run into
equal-length cues. It was written as a pass over the chunk list produced by the
greedy loop — but that loop had already capped every chunk at `words_per_chunk`,
so `ceil(len(chunk)/words_per_chunk)` was always 1 and the pass did nothing.

It looked like it worked: cue count dropped 138 → 84, the one- and two-word
orphans disappeared, the frames read well. All of that came from the two *other*
options changed in the same edit (`break_on` and `min_words`). The no-op was
invisible because it was only ever measured in combination.

Two general lessons:

- **Measure a new option on its own**, not bundled with others, or you will
  attribute another option's effect to it. Isolating the three here took one
  extra minute and was the only thing that revealed it.
- A transformation placed *after* a step that already normalises its input often
  has nothing left to do. Check where in the pipeline the pass actually sits.

Caught by a unit test asserting exact cue lengths (`[7, 7]` vs `[8, 6]`). A
cue-count assertion would have passed — both shapes have two cues.

**And once fixed, it was not the better choice for that edit.** `balance` trades
even cue lengths for *more* cues, so more break points, and neither mode is
phrase-aware — the balanced output split "grew / up with" and "gave / up" across
cues where the 8-word greedy version kept them together. Use `balance` when the
greedy tail is visibly stranding words; leave it off when the cap happens to land
on phrase boundaries. Fixing a bug and shipping the fix are separate decisions.

---

## Never write inside this repo

Hard Rule 12: all session output goes to `<videos_dir>/edit/`. The scratch/test artifacts from
setup verification live in the session scratchpad, not here.

---

## A clip can be physically sideways with NO rotation metadata at all

The existing rotation notes above all assume the trap is a *wrong* rotation value. There is a
worse variant: **no rotation side-data, and content that is still 90° off.**

`a-roll/murgan-idli-3.mp4` in the Detour-2 shoot is stored 1080x1920 with no rotation
side-data, so every metadata check calls it a correctly-oriented portrait clip. The picture
inside the frame is landscape, turned 90° — the speaker lies on his side.

Its siblings do **not** settle it either way: `b-roll/phone/murgan-idli-1.mp4` (1080x1920) is
sideways in exactly the same way, while `-2.mp4` (538x954) is genuinely upright portrait. Same
session, same filename stem, opposite answers — so the batch tells you nothing, and checking one
member of it does not clear the rest. (This corrects an earlier version of this note that called
both siblings upright: `-1` was assumed from its dimensions and never looked at.)

All three are re-encodes, not camera-originals: `h264` / `yuvj420p` where the rest of the shoot
is `hevc` / HLG 10-bit. That mismatch is the only metadata hint, and it is circumstantial.

Confirmed by extracting one frame from all 54 clips into a contact sheet. `ffprobe` gives you
nothing here. This is the strongest case yet for the "look at one frame from every clip" rule —
the metadata-only check does not merely under-report this, it actively says the clip is fine.

Fix is a `transpose` in the per-segment `filter`, followed by a `scale` back to the common
size (see the `ranges[].filter` rules in helpers.md).

---

## Pillarboxing a SIDEWAYS clip is the wrong fix — it preserves the rotation and adds bars

The two portrait problems look identical in `ffprobe` and have opposite fixes:

| Stored | Content | Fix |
|---|---|---|
| 1080x1920 | genuinely upright portrait | pillarbox to 1920x1080 |
| 1080x1920 | landscape lying on its side | **`transpose`**, then scale |

`murgan-idli-1.mp4` is the second kind and was treated as the first. The pillarbox produced a
1920x1080 segment — so it passed the uniform-dimension check below, and passed a second review
that only asked "is every segment 1920x1080?" — with the picture still on its side, now framed
by black bars. The dimension check verifies geometry, not orientation; nothing downstream can
tell the two cases apart.

So the "look at one frame from every clip" rule has a second half: **look at one frame from every
clip you PREPPED, after prepping it.** Confirming the output geometry is not confirming the
output. One `ffmpeg -ss … -frames:v 1` per prepped file is seconds of work.

The user supplied a correctly-exported landscape replacement (`murgan-idli-1-new.mov`,
1920x1080 hevc/bt709), which needs no prep at all — worth asking for before building a fix,
since a re-export from the phone beats any transpose-and-rescale.

---

## An empty transcript is not evidence of silence — check before writing the clip off

16 of 54 Detour-2 a-roll clips came back with **0 words** from Deepgram. Several were long
in-car two-hander shots (IMG_3182 125s, IMG_3223/3224/3225 283s combined) where the frames
clearly show people mid-conversation. The tempting reads are both wrong:

- **Not silence.** `volumedetect` on track 0 put them at −12 to −15 dB mean, i.e. *louder*
  than clips that transcribed fine (IMG_3171 at −18.4 dB returned 313 words, IMG_3206 at
  −20.5 dB returned 927). The `transcribe.py` silence guard (−60 dBFS) is nowhere near
  tripping, so it offers no protection here.
- **Not a band-balance problem.** Comparing 80–250 Hz against 300–3400 Hz energy failed to
  separate them: IMG_3175 sits at −4.2 dB diff and transcribed 340 words, IMG_3182 at −5.5 dB
  transcribed none. Don't bother with this test; it does not discriminate.

What settled it was a **presence test with the local whisper model**: it labelled them
`[Music]` / `(singing in foreign language)` / `[Hissing sound]`. Loud music playing in the car,
not missed speech.

Two reusable points:

- **An English-only whisper model is still useful on non-English audio** as a *presence*
  detector. It cannot tell you what was said in Hinglish, but `[Music]` vs a stream of
  word tokens reliably answers "is there speech here at all", and it is free and offline.
  This is a legitimate use of `small.en` where the content cross-check is impossible.
- Only `.en` whisper models are installed on this machine (`ggml-base.en.bin`,
  `ggml-small.en.bin`). The KB's standing advice to run a free whisper pass alongside the paid
  one **cannot be followed for content on code-switched audio** until a multilingual model
  (`ggml-small.bin`) is fetched. Worth doing before the next Hinglish shoot.

---

## Deepgram diarization collapses on in-car two-handers

On Detour-2 (two people conversing throughout, 54 clips), `nova-3` returned **308 phrases as
S0 against 61 as S1**. Inspecting `takes_packed.md` shows both voices merged into S0 within a
single phrase — e.g. a question and its answer from the other person carried one S0 tag.

So the `S0`/`S1` tags in `takes_packed.md` are **not trustworthy on this footage** and must not
be used to attribute lines. Suspected cause (unverified) is the shared cabin mic plus music
bed. Note this is the *opposite* failure from the whisper helper's, which simply omits
`speaker_id`: here the tags are present and wrong, which is harder to notice.

---

## whisper.cpp cannot produce word-level timings for Devanagari (or any non-Latin script)

`transcribe_whisper.py` passes `-ml 1` to force one token per segment, which is how it
synthesises word-level timings. whisper's vocabulary is **byte-level BPE**, so a single
Devanagari character is several tokens — and splitting at token boundaries cuts multi-byte
UTF-8 sequences in half. whisper-cli then writes **invalid UTF-8 into its own JSON file**.

Verified on Detour-2 (`ggml-small.bin`, `-l hi`), one 7s clip:

| invocation | result |
|---|---|
| `-ml 1` (what the helper does) | JSON fails strict UTF-8 decode; lenient decode gives `['', ' �', '�र', 'े', ...]` — characters shredded |
| no `-ml` (segment level) | clean UTF-8: `अरे वो श्वाद तो यह ज़ सकते हैं।` |

It is intermittent at segment level too — a 45s clip still broke, because a segment boundary
can land mid-character. Short clips can pass and look fine.

**Do not "fix" this with `errors="replace"` on the JSON read.** That returns mojibake for the
transcript itself, which is far worse than an exception in a helper whose entire job is
verbatim text. `helpers/transcribe_whisper.py` now raises a RuntimeError naming this cause.
(The *stderr* capture in the same function genuinely did need `errors="replace"` — whisper-cli
streams recognized text to stderr and splits characters there too. That text is only ever used
for an error message, so lossy decoding is correct there and nowhere else.)

**Consequence:** on code-switched/Devanagari footage, whisper is a **content** cross-check only.
Deepgram remains the sole source of word-level timings, so there is no independent check on
timing for this footage — only on wording.

---

## For Hinglish, cross-check whisper with `-l en`, not `-l hi` or `-l auto`

Counter-intuitive, and the opposite of the Deepgram rule two entries up. Measured on Detour-2:

| flag | output on a Hinglish clip |
|---|---|
| `-l hi` | `अरे वो श्वाद तो यह ज़ सकते हैं।` — "start" became `श्वाद`; forces everything into Devanagari and cannot code-switch back to Latin |
| `-l auto` | detects `hi` (p=0.94), then behaves as `-l hi`, plus the UTF-8 breakage |
| **`-l en`** | `So what's up guys, today I'm going on one more ride. Luckily I went on one ride on Friday, but since next week I'm on call...` |

Against the Deepgram `multi` reference for the same span — *"So, what's up guys? आज फिर एक और
ride पर जा रहा हूं मैं. Luckily Friday छुट्टी थी तो I went on one ride already. But since next
week I am on call..."* — the `-l en` rendering matches **meaning for meaning**.

Whisper forced to English produces a genuine English *rendering* of Hindi speech, not gibberish.
That makes it an excellent semantic cross-check, and because the output is pure Latin it also
sidesteps the UTF-8 bug above entirely.

**This does not contradict the Deepgram `--language en` rule.** Deepgram `en` on Hinglish
invents phonetically-similar English nonsense ("Within me a golf course car"); whisper `en`
translates. Different engines, opposite behaviour — do not generalise one to the other.

Across 38 clips, whisper-en word counts ran **0.85–0.95×** the Deepgram Hinglish counts
(English is more compact). Ratios outside ~0.5–1.8 are worth inspecting; that rule surfaced
7 clips, of which 3 were real findings.

---

## whisper hallucinates fluent sentences in quiet audio — verify before believing a "miss"

The cross-check's most alarming hit was IMG_3187: Deepgram's last word ended at **48.4s** of an
80.7s clip, while whisper reported speech at 57.8 / 64.8 / 70.8 / 72.8s — *"There are a lot of
people here. I think there is a child behind us. How many people? A lot of people are getting
registered."* That reads exactly like 30 seconds of dropped dialogue.

It was not. Two cheap checks killed it:

- **Speech-band level**: the 62–78s window sits at −39.3 dB mean / −16.9 dB max, against
  −26.6 / −5.1 dB in the confirmed-speech region. ~13 dB quieter.
- **Frames at 55/65/75s**: two people sitting quietly in a car. No crowd, no child, nobody
  "getting registered" — the content is semantically impossible for the shot.

Deepgram was right to stop. **Treat a whisper-only tail as suspect by default**, especially when
it appears after the last Deepgram word and describes things not visible in frame. Check the
level and look at a frame before concluding the paid transcript dropped anything.

---

## Deepgram `--language multi` drifts into Spanish on short or low-content clips

Verified on Detour-2: 3 of 38 transcripts contain Spanish that is not in the audio.

| clip | duration | Deepgram output | whisper `-l en` |
|---|---|---|---|
| IMG_3200 | 26.7s | `Escalation के लिए होते हैं. किसी के connected है? ¿Qué qué hubo? Es una curiosidad.` | `It's for installation.` |
| IMG_3195 | 22.6s | `Ouch. ¿Ya, bebé, no?` | `Ouch! You wanna come here?` |
| IMG_3180 | 0.53s | `Yo por un té.` | — |

On IMG_3200 the Spanish is **7 of 15 words (47%)**, timestamped 17.3–22.6s, i.e. it would burn
straight into a caption as Spanish text over a Hindi video. `multi` is still the right flag
(see the `en` entry above — it recovered +37% of words), but it is not free of this.

**Cheap standing check** before burning captions from a `multi` transcript — grep for Spanish
orthography, which Hindi/English transliteration never produces:

```bash
grep -lE '[¿¡áéíóúñ]' <edit>/transcripts/*.json
```

Sub-second clips are worthless to both engines: IMG_3181 (0.75s) gave Deepgram `Feuilleton` and
whisper `♪ Fertile ♪`. Exclude clips under ~1s from transcription rather than reasoning about
their output.

---

## `creation_time` is the file-WRITE time; capture time is `com.apple.quicktime.creationdate`

Building a shoot timeline from `format_tags=creation_time` is wrong on iPhone footage. On
Detour-2 the two fields disagreed by up to **2h24m**:

| clip | `creation_time` (IST) | `com.apple.quicktime.creationdate` |
|---|---|---|
| IMG_3166 | 13:45:40 | **11:21:16** |
| IMG_3167 | 13:49:17 | **11:22:36** |
| IMG_3229 | 19:42:31 | 19:42:31 (agree) |

They agree on most clips and diverge on some — which is the dangerous pattern, because a
spot-check passes. The divergent ones here were a batch that had been through Photos (they were
also the only 29.97fps clips), so the moov atom was rewritten.

Always read `com.apple.quicktime.creationdate` — it also carries the **local UTC offset**, so no
timezone guessing. Fall back to `creation_time` only when the Apple tag is absent, and flag it:
a re-encode has neither (on this shoot the three `murgan-idli-*.mp4` files carried only the
export date, three weeks after the shoot).

This matters because `project.md`'s dashcam-matching formula is
`wall_clock = aroll_file_start + word_timestamp + clock_offset` — a wrong file start puts every
cutaway on the wrong minute of a 405-file dashcam set.

**Measured offset on this shoot: ~0, drift <= 5 s.** Verified three ways (departure clip vs
dashcam engine-on; engine-on falling inside a known gap; a spoken clock reading) and confirmed
by the dashcam's own burned-in OSD, which displays date/time/speed/GPS per frame.

---

## Dashcam OSD burns GPS coordinates into every frame

The 70mai dashcam renders `date time speed lat/long` into the bottom of the picture. Two
consequences:

1. **Privacy.** Any dashcam cutaway published from this footage carries the coordinates of the
   route, including the departure from home. Crop it out unless the user says otherwise.
2. **It is also a free, per-frame ground truth.** The OSD confirmed the phone/dashcam clock
   alignment to the second, and its **speed readout located the actual traffic jam** (3-7 km/h
   at 12:16-12:18) versus a later toll-plaza crawl (0 km/h at 12:31) that had been assumed to be
   the jam. Read it before guessing which dashcam file covers a moment.

For 2592x1944 (4:3), `crop=2592:1458:0:0` yields exactly 16:9, removes the OSD, and keeps the
bonnet in frame. Scales to 3840x2160 with no further cropping.

---

## Deepgram word spans are mostly contiguous, which breaks naive boundary snapping

87% of adjacent word pairs on this shoot had **zero gap** (`next.start == prev.end`); only 13%
had any gap at all. Two consequences for any snap-to-word-boundary pass:

1. **The pad usually cannot be applied.** Hard Rule 4 wants 30-200ms of padding, but where words
   are contiguous there is nowhere to put it — the edge snaps exactly to the token boundary.
   That is safe (a token absorbs the silence and breath before its word — the same behaviour
   behind Deepgram's dropped-leading-filler), but it means the cut relies entirely on the 30ms
   fades of Rule 3. Verify numerically rather than assuming.
2. **Clamping to the neighbour's edge can push the cut INTO the word you meant to keep.**
   `ns = max(target.start - pad, prev.end + eps)` overshoots `target.start` whenever
   `prev.end == target.start`. Pin it back:

   ```python
   ns = min(ns, first["start"])   # IN never past its own word's start
   ne = max(ne, last["end"])      # OUT never before its own word's end
   ```

   This produced 3 real violations on the first pass over 46 ranges.

Two further traps found while verifying this:

- **A wide lookback window grabs the previous phrase's tail token.** A +/-0.35s tolerance pulled
  in a garbage token from the preceding phrase, which was both editorially wrong and unsnappable.
  0.05s is the right tolerance when ranges are taken from `takes_packed.md` phrase boundaries.
- **The violation checker itself needs a tolerance.** `w.start < edge < w.end` on floats flags a
  cut that is exactly on a boundary, because the rounded edge can land a few ulps inside the
  stored end. Use ~2ms. Without it you chase a violation that does not exist.

---

## Mixed orientation: prep to the majority geometry, and treat the pillarbox as a design choice

Confirmed the prep approach from the entry above works, with detail worth keeping:

- Prepped files must **not retime**. Verified by comparing durations: all three preps came back
  within 27ms (under one frame at 30fps), so transcript timings and the measured segment
  boundaries stayed valid and no re-measure was needed after a re-prep.
- Prep **to the final output geometry** (3840x2160), not to 1080p — `extract_segment` then
  scales 1:1 instead of upscaling a downscale.
- Apply `TONEMAP_CHAIN` during prep and stamp `-color_primaries/-color_trc/-colorspace bt709`,
  so `is_hdr_source()` returns False on the prepped file and render does not tonemap twice.
- **Watch the map order.** `-map 0:v:0` placed before a `-filter_complex` output silently wins,
  and the filtergraph is discarded — the prep "succeeds" and produces an unprepped file. Check
  the output's dimensions, not the exit code.

**The blur-pad treatment is not neutral.** The default (`gblur=sigma=40`) leaves recognisable,
smeared faces either side of the strip and reads as a mistake. `gblur=sigma=120` plus
`eq=brightness=-0.24:saturation=0.20` reads as a deliberate dark frame and lets the subject pop.

And the arithmetic is worth stating before choosing pillarbox vs crop for a 1080x1920 source on
a 2160p timeline:

| treatment | subject width | upscale |
|---|---|---|
| full-portrait pillarbox | 1215 px | **1.125x** |
| 16:9 crop, full frame | 3840 px | 3.55x |

Pillarbox keeps the pixels; the crop throws away three quarters of them. On a phone-sourced
1080p clip the crop is visibly soft. Prefer pillarbox and spend the effort on the treatment.

---

## ffmpeg does NOT pick the spatial track by default (correction)

An earlier entry above states that ffmpeg's default audio selection "picks the stream with the
most channels, i.e. the spatial one", implying `render.py` (which passes no `-map`) would take
`apple_apac` while the transcribers take `aac`.

**Measured: it does not.** On four dual-track clips ffmpeg selected `Stream #0:1` (`aac`, 2ch)
every time, not the 4-5ch `apple_apac`. So render.py and the transcribers agree, and the audio
that gets cut is the audio that was transcribed.

Being explicit would still be safer — the two paths agree by luck of stream selection rather
than by construction — but there is no live bug here, and the original entry overstated it.

---

## `-c copy` concat inserts ~30 ms of AAC priming at EVERY cut

**Fixed on `main`.** `concat_segments` used a blanket `-c copy`. Video stream-copy is correct
and is the whole point of Hard Rule 2 — but audio must not be stream-copied.

Each segment is encoded as its own AAC stream, and AAC carries encoder delay: priming samples
at the head and padding at the tail. Concatenating the *streams* concatenates those artefacts
into the timeline.

Measured on the 46-segment Detour-2 cut, decoding both concats to PCM:

| concat | decoded audio |
|---|---|
| `-c copy` | 965.526 s |
| `-c:v copy` + one continuous AAC re-encode | 964.130 s |
| (video stream) | 964.733 s |

**+1.396 s of audio that is not in the segments — 30.4 ms per boundary**, which is ~1440 samples
at 48 kHz, squarely in AAC priming territory. Confirmed as progressive, not a one-off, by
envelope cross-correlation against the corrected build:

| point | boundaries so far | predicted drift | measured | corr |
|---|---|---|---|---|
| 10 s | ~2 | 60 ms | 70 ms | 0.86 |
| 100 s | ~9 | 270 ms | 270 ms | 0.996 |
| 200 s | ~13 | 390 ms | 400 ms | **1.000** |
| 300 s | ~19 | 570 ms | 590 ms | 0.62 |

So the symptom is not only a click at each cut — it is **audio drifting progressively late
against picture**, reaching ~1.4 s by the end of a 16-minute cut.

Secondary tell: `loudnorm` pass 1 measured **LRA 23.8 → 18.6** after the fix. The inserted
digital silence was inflating the measured loudness range, so the normalisation was being
computed from a signal that did not exist.

The fix keeps Rule 2 intact — video is still `-c:v copy`, no second video generation. Only audio
is re-encoded, once, continuously, so there is exactly one priming sequence and it sits at
t=0 where it is inaudible. Pinned by `tests/test_render_concat_audio.py`.

---

## A single mono source among stereo ones silently corrupts the concat

Found immediately after the fix above, and it is the nastier of the two.

`extract_segment` sets `-c:a aac -b:a 192k -ar 48000` but **set no channel count**, so every
segment inherited its source's. On Detour-2 one clip (`murgan-idli-3.mp4`, a re-encode) was
mono while the other 44 segments were stereo — so segments 21 and 22 were 1-channel.

The concat demuxer cannot carry a channel-layout change through a re-encode. Everything after
the odd segment decoded wrongly, while the output kept the **correct total duration** and played
without error. That is what makes it dangerous: nothing fails.

Measured by locating each segment's audio inside the concatenated track (envelope
cross-correlation, searched over the whole file):

| segment | expected | found | corr |
|---|---|---|---|
| seg 10 | 113.807 s | 113.680 s | **0.946** |
| seg 20 | 327.307 s | 327.060 s | **0.979** |
| seg 30 | 491.007 s | — | 0.036 |
| seg 40 | 868.073 s | — | 0.021 |
| seg 45 | 947.707 s | — | 0.015 |

Segments 21–22 sit exactly at the break. Fix: `-ac 2` in `AAC_ARGS`, applied to both the extract
and the concat.

**Check for it directly before rendering any multi-source EDL:**
```bash
for p in <edit>/clips_*/seg_*.mp4; do
  ffprobe -v error -select_streams a:0 -show_entries stream=channels -of csv=p=0 "$p"
done | sort -u      # more than one line ⇒ the concat will be wrong
```

---

## The boundary-pop test has a blind spot: it cannot see inserted silence

The audio self-eval in this KB compares the max sample-to-sample step at each cut against a
continuous-speech reference. On Detour-2 it reported **0 of 45 boundaries above threshold** —
while the concat was inserting 30 ms of silence at every one of those boundaries.

It is not a false result, it is the wrong instrument: a *gap* is not a step discontinuity, so a
step detector is blind to it. Pair it with a length check, which is trivial and catches exactly
this:

```
sum(segment audio durations)  vs  decoded duration of the concatenated audio
```

Any difference is silence the container inserted. Also compare the decoded audio duration
against the video stream duration — they should agree to well under a frame.

---

## Validate a measurement method on a known-good control before believing a scary result

While chasing the above, envelope correlation reported that the final segment's audio was simply
**not present** anywhere in the finished film. That is an alarming result, and it was tempting to
act on it.

The right next step was a control: search for **segment 00**, which is certainly at t=0. It came
back at 0.020 s with corr 0.986 — so the method was sound, and the seg-45 result was real
(it was the mono-channel corruption). Had the control failed, the correct conclusion would have
been "my measurement is broken", not "the render is broken".

Cheap, and it decides which of the two you are looking at. The same pass also confirmed a
standing KB claim with a bigger sample: **draft and preview segment durations are bit-identical**
— max difference 0.0 ms across all 46 segments — so boundaries measured from a cheap draft are
valid for the final.

---

## Segment audio and video must be snapped to the same frame grid, or A/V drifts

**Fixed on `main`.** Second drift bug in the same area as the AAC priming one, and it was
*hidden* by it: the priming pushed audio 1.4 s late, this pushes it 0.6 s early, and the two
partly cancelled.

`extract_segment` passed an arbitrary float `-t`. Video can only end on a frame boundary, so
the video stream was quantised to the grid and the audio was not. Per segment they differed by
up to one frame period; the concat butt-joins both streams, so it **accumulates**:

| | before | after |
|---|---|---|
| max per-segment \|audio − video\| | 33 ms | **0.00 ms** |
| total over 46 segments | −0.631 s | **+0.000 s** |
| placement error of the final segment | −0.600 s | 0 |

Fix: snap the duration to whole output frames (`n = round(duration*fps); duration = n/fps`)
*before* computing the fades, and add `apad` so audio can never fall short.

**Two traps inside the fix:**

- **`-t` as a decimal string rounds UP.** `1358/30` prints as `"45.266667"`, which is greater
  than the true value, so ffmpeg emits 1359 frames instead of 1358 and the mismatch comes
  straight back. Bias the string a hair low (1e-5 s is under one sample at 48 kHz, so the audio
  is untouched).
- **Compute the fade-out from the snapped duration**, not the requested one. The fade is 30 ms
  and the snap can move the end by up to 33 ms — otherwise the fade lands past the segment end
  and Rule 3 silently stops holding.

---

## Deepgram can time a word past the end of the media, and render.py truncates silently

On IMG_3170 the last word is timed `7.20 → 8.96` on a clip that is **7.368 s long** — Deepgram's
own returned metadata says `duration: 7.3666873`, so it contradicts itself within one response.

An EDL range built from that word end asks for 5.28 s of a clip that only has 3.69 s left.
`render.py` does not warn: the segment just comes out short, the concat still succeeds, and the
beat is quietly clipped.

Validate every range against its source before rendering — it is three lines and it caught a
truncated hook here:

```python
dur = probe_duration(source)
if r["end"] > dur: ...    # clamp, and say so
```

---

## Measure a denoise chain per clip — the aggressive one can be worse on your best audio

`gotchas.md` already records a measured chain (`highpass=110,afftdn=nr=30,deesser`) from a
car-interior vlog. Re-measured on Detour-2 across three acoustic settings, it is **the wrong
choice**, and most wrong on the footage that matters most:

| chain | dam (the 4m25s spine) | car | night arrival |
|---|---|---|---|
| raw | 21.99 dB | 10.08 | 11.23 |
| **highpass=100, afftdn=nr=20** | **25.65** | 13.23 | **16.20** |
| highpass=110, afftdn=nr=30, deesser | 22.54 | **13.51** | 15.40 |

The aggressive chain is **3 dB worse on the outdoor monologue** and only 0.3 dB better in the
car. It also pulls the speech level down (−14.0 → −16.3 dB), i.e. some of its apparent
"separation" is just attenuating everything, and `highpass=110/120` starts cutting male vocal
fundamentals.

Lesson: separation is a per-environment measurement, not a setting to inherit. Measure on the
loudest, the quietest, and the most important clip before committing an `audio_filter` — it
applies to every segment in the EDL.

---

## This ffmpeg build silently drops alpha from VP9; use ProRes 4444

`-c:v libvpx-vp9 -pix_fmt yuva420p` produced a file that ffprobe reports as **`yuv420p`**, with
every pixel opaque (sampled corner alpha 255 where it should be 0). Adding
`-metadata:s:v:0 alpha_mode=1` changed nothing. It fails silently — you get a valid file that
is simply no longer an overlay.

`-c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le` works (verified: corner alpha 0, glyph
alpha 255). Check alpha by decoding a frame to RGBA and sampling a corner, not by trusting the
encode to succeed.

---

## Validate a cutaway against what the speaker is actually saying

The dashcam OSD's **speed readout** is the cheapest way to check whether a B-roll cutaway agrees
with the line it sits under. Two of six planned cutaways on Detour-2 had to be dropped: the
speaker says *"beautiful road, सब कुछ clear"* at 18:05 and *"इतना clear road"* at 18:11, while
the OSD shows **0–8 km/h continuously from 18:04 to 18:15** — they were stuck in a jam the whole
time, and the GPS longitude barely moves.

Both the timestamps and the footage were right; the *pairing* was wrong. A cutaway that
contradicts the line reads as an editing mistake, so it is worse than no cutaway at all.
(The line may well be sarcastic, in which case the jam footage is the joke — but that is a call
for the speaker, not an inference from a transcript the KB already records as unreliable.)

Check the picture against the words for every cutaway before building it.

---

## Denoise "separation" is not what the listener hears — loudnorm puts the floor back

Reported a denoise chain as "+2.4 dB separation" and the user came back saying there was *more*
noise than before. Both were true. Separation is a **ratio**; what you hear is the **absolute**
noise floor, and `loudnorm` to −14 LUFS re-applies whatever gain the programme needs:

| | source | delivered |
|---|---|---|
| noise floor in a speech gap | −24.9 dBFS | **−21.7 dBFS** |
| programme loudness | −18.1 LUFS | −14.3 LUFS (+3.8 dB) |

A chain that buys 2–3 dB of ratio, followed by ~4 dB of normalisation gain, leaves the noise
**louder than the source**. Anything under roughly the loudnorm gain is worse than doing nothing.

So: always report (and check) the **absolute noise floor of the delivered file** against the
source, measured in a genuine speech gap. Find the gaps from the transcript — an "ambience"
sample eyeballed from the clip head is usually contaminated by speech (mine was, and it made
the car look like it had 0 dB separation in every band).

---

## `arnndn` is available and is a different order of magnitude from `afftdn`

No model ships with ffmpeg, so `arnndn` looks unusable — but models are a download away:
`https://raw.githubusercontent.com/richardpl/arnndn-models/master/{bd,cb,mp,sh,lq}.rnnn`
(~300 KB each; kept in `~/.cache/rnnoise-models/`).

Measured on Detour-2, noise floor in real speech gaps:

| chain | dam (wind) | car (road) |
|---|---|---|
| raw | 16.3 dB sep | 8.0 dB sep |
| `highpass=100,afftdn=nr=20` | 17.8 | **8.0 — no gain at all** |
| `afftdn nr=40` | 18.0 | 7.8 |
| `arnndn cb` | 28.6 | 17.9 |
| `arnndn lq` | **39.5** (floor −65.3) | **20.2** (floor −45.6) |

`afftdn` at any strength was worth ~1–2 dB on this footage; `arnndn` was worth 12–24 dB.
For speech under broadband noise (wind, road, crowd) reach for `arnndn` first and treat
`afftdn` as a finishing pass, not the main tool.

Caveats: the models attenuate the voice too (≈6–10 dB at the dam), which `loudnorm` restores —
judge by **ratio** when choosing a model but by the **absolute floor of the render** when
checking the result. And they can sound processed; that is a listening call, so build
loudness-matched A/B samples and let the person who can hear them decide.

---

## Noise belongs to the location, not the edit — so the filter has to be per-segment

**Added on `main`:** `ranges[].audio_filter` overrides the EDL-level `audio_filter`
(`""` means deliberately none, absent means inherit). Pinned by `PerRangeAudioFilterTests`.

One global setting has to compromise between a windy outdoor monologue and a take inside a
moving car, and on Detour-2 the user's own ears picked different models for the two. A single
`audio_filter` could not express that.

---

## Repainting a screen: what tracks and what doesn't

Replacing the ETA numbers on a CarPlay screen in handheld 4K. Two approaches failed before one
worked, and the failures are the useful part:

- **Accumulating NCC over the whole clip — drifted.** A template spanning the text *and* the map
  below it matched a repeating road pattern; correlation stayed high (min 0.976) while the box
  walked ~96 px off. **High correlation is not proof of a correct match** when the scene contains
  repeating texture.
- **Per-frame threshold detection — escaped.** "Dark pixels on a bright pill" grabbed map
  features once the search window grew, and the box exploded to the whole frame by frame 30.
- **What worked:** measure frame-to-frame motion first, pick the clip's most static span, and
  run a constrained NCC (±25 px) on a *small distinctive* patch — the word "ETA" alone. Over
  1.5–2 s that gave max 3 px/frame with std ≈ 1.0, smooth enough to light-smooth and use
  directly. Verified by compositing and looking, not by the correlation score.

Two finishing details that decide whether it reads: draw the replacement at 2× and downscale
with a ~1.4 px blur, and **desaturate/lighten the colours** — text drawn at full contrast is
visibly sharper than anything photographed off a screen and gives the composite away.

And the honest limit: this only works because the surface is flat, near-static for a couple of
seconds, and the plate is uniform. The second clip's strip was tilted ~5°, which would need
rotated type; not worth it for a 3 s corner inset.

---

## Build dual-capture as a prepped SOURCE, not an overlay

Where dual-capture (dashcam full-frame + interior inset) is the default presentation rather than
an occasional effect, building it per-moment as an `overlays` entry is the wrong shape: overlays
need `start_in_output` measured from a render, so every one costs a render/measure cycle, and
they only replace picture.

Building it instead as a prepped file per take — full take length, same duration and timebase,
original audio copied through — means the EDL just points `sources["IMG_3171"]` at
`prepped/dc_IMG_3171.MOV`. Keeping the **original key** is what makes it work: `render.py`
resolves captions via `transcripts/<source_key>.json`, and because the prep does not retime, the
word timings still line up. No overlay bookkeeping, no boundary measurement, audio for free.

Reserve `overlays` for things that genuinely sit *on top* of a finished timeline — titles,
speed-ramps, corner insets.

---

## A portrait source that slips the prep does NOT fail the concat — it stretches silently

`murgan-idli-1.mp4` (1080x1920) went into an EDL without being pillarboxed. `is_portrait_source`
scaled it by height, so **one segment came out 1080x1920 while the other 71 were 1920x1080**.
The `-c:v copy` concat accepted it, the file played, and the player stretched that segment to fit.
Nothing errored; the user spotted it by eye.

Add a dimension check to the pre-render validation — it is two lines and catches the whole class:

```bash
for p in <edit>/clips_*/seg_*.mp4; do
  ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$p"
done | sort -u        # more than one line ⇒ a source was not prepped
```

(Note when eyeballing this: `-of csv=p=0` emits a trailing comma, so `1920,1080` and `1920,1080,`
are the same value — compare the *set*, not a naive uniq.)

---

## `scale=…:force_original_aspect_ratio` rounds to even, so odd inset sizes break `alphamerge`

A PiP inset specified as 461x259 came back from
`scale=461:259:force_original_aspect_ratio=increase,crop=461:259` as **460x258**, and the
`alphamerge` against a 461x259 mask failed with:

```
Input frame sizes do not match (460x258 vs 461x259)
Error reinitializing filters!
```

The error names the filter but not the cause, and "Error reinitializing filters" is the same
message you get for a mid-stream property change — so it sends you looking at the inputs.

**Always choose even inset dimensions.** `int(W*0.24)` happens to be even at 1920 (460) and the
same expression at other widths may not be; round explicitly.

---

## A range ending flush with its source overruns once the duration is frame-snapped

The frame-snap fix rounds a segment's duration UP to whole frames. A range whose end sits within
one frame of the source end therefore asks for slightly more audio than exists, `apad` does not
cover it, and the segment comes out **video-longer-than-audio** (34.7 ms measured) — which then
shifts everything after it.

It also showed up as an intermittent hard failure:
`Error submitting audio frame to the encoder` / `Error flushing encoder: Invalid argument`,
which aborted a 50-segment render at segment 43. Intermittent, so re-running "fixed" it and hid
the real cause.

Clamp EDL range ends to **`source_duration - 0.05`**, not `- 0.01`: more than one frame of
headroom at 30fps. Verify afterwards that max |audio − video| across segments is 0.00 ms.

---

## Joining separately-encoded pieces with `-c copy` breaks downstream filtergraphs

Two dashcam clips encoded in separate ffmpeg runs, concatenated with `-c copy`, produced a file
that plays fine but makes any later filtergraph fail with `Error reinitializing filters!` — the
decoder reports a mid-stream property change (SAR/colour) at the join.

If the joined file is an *input to another filter* (a dual-capture background, for example),
re-encode the join instead: `scale=…,setsar=1,format=yuv420p` in one pass. Stream-copy is only
safe when the result is the final output.

---

## Cutting a repeated passage: check which instance holds the setup

`notes.md` flagged that a monologue made the same point twice and said "keep the second". Doing
that literally produced a cut the speaker immediately flagged as incomprehensible.

Reading the words rather than the phrase boundaries showed why: the **setup** was in the first
instance ("your brain consists of those two parts, right, which I talked in the last episode")
and the **completed thought** in the second ("so only one part is getting the nourishment.
Otherwise…"). Dropping the whole first block removed the premise and left the payoff dangling.

The correct cut kept the setup and dropped only the **abandoned first attempt** between them —
the stretch that trails off in "So you need to, uh,".

Generalisable: when a note says "it repeats, keep the second", diff the two instances at word
level before cutting. Repetition in speech is usually a restart, and a restart often re-states
only *part* of what came before.

---

## Manual caption corrections belong in the transcript, with the original kept

ASR errors that survive into burned-in captions ("Does he know who know" for "those who know who
know", "smooth rate" for "smooth ride", "lungs" for "long") are fixed by editing `text` in
`transcripts/<clip>.json`. Word timings stay untouched, so cuts and offsets are unaffected, and
`render.py --build-subtitles` picks the corrections up on the next render.

Copy the file to `<clip>.json.orig` first and stamp `_manual_corrections` in the JSON — the
transcript is otherwise indistinguishable from provider output, and a later re-transcribe would
silently revert the fixes.

## Reusing cached segments: verify each one against the EDL, or positions silently rot

`render.py` re-extracts everything on every run, so this cannot bite a normal render. It bites
the moment you hand-build a driver that reuses `clips_preview/` to skip the expensive stage.

On Detour-2 six ranges were clamped to `source_duration - 0.05` **after** those segments had
already been extracted. The cached segments therefore carried 1-2 frames the EDL no longer asked
for — `dc_montage` had 90 frames where `0.00-2.95 @ 30fps` asks for 88. The composite that reused
them produced a cut 0.333 s longer than its own EDL describes, and `master.srt` plus all five
overlay `start_in_output` values were measured against *that*. Everything was self-consistent, so
nothing errored and nothing looked wrong.

It only surfaced when a clean re-extract produced a file **0.304 s shorter** than the one it was
supposed to match. Had the two been compared less closely, the corrected render would have
shipped with every caption after 0:24 up to a third of a second late.

Before reusing any cached segment, assert it against the EDL:

```python
n_expected = max(1, round((r["end"] - r["start"]) * fps))   # same rounding as extract_segment
n_actual   = int(ffprobe_nb_frames(seg_path))               # -count_frames
assert n_actual == n_expected, f"{seg_path.name}: {n_actual} frames, EDL asks {n_expected}"
```

Note `round()` is banker's rounding: `round(88.5) == 88`, not 89. The check must use the same
call `extract_segment` does, or it will disagree on every exact `.5` boundary.

Corollary to the "measure positions from a real render" rule: a measurement belongs to **one
specific extraction**, not to the EDL. Edit any range and every measured position downstream of
it is stale — rebuild `master.srt` from the new segments and remap the overlay starts.

---

## `ffprobe -show_entries stream=a,b` does NOT print in the order you asked for

ffprobe uses its own field order, not the order in the query. For an audio
stream, `stream=channels,sample_rate,duration` prints:

```
sample_rate=48000
channels=2
duration=354.750000
```

Read positionally with `-of default=nw=1:nk=1`, a stereo clip therefore reports
**48000 channels** — and since that is a valid integer, nothing errors. A
helper looping over channels then quietly starts denoising "channel 44".

Always parse key=value (`-of default=nw=1`, keys kept) or `-of json`, and
sanity-check the value. Pinned by `tests/test_denoise.py`.

---

## For gusting wind, `arnndn` is the wrong tool — use DeepFilterNet

`arnndn` is fine for steady broadband noise (road drone, air conditioning,
hiss), and the KB's earlier "arnndn beats afftdn by 12-24 dB" finding still
holds for that. Wind is a different problem: it is low-frequency and it
**gusts**. On the Detour-2 dam monologue the noise sat 72% below 300 Hz and
swung through 27 dB, and `arnndn` took only 8 dB out of it while leaving the
gusting untouched (27.6 dB swing after, vs 30.4 before).

Measured on the same 25 s excerpt, noise floor with the voice normalised to a
fixed level (the number the listener hears — see the loudnorm note above):

| engine | floor | vs shipped |
|---|---|---|
| raw | −38.4 dB | +9.2 |
| `arnndn` lq (what shipped) | −47.5 dB | 0.0 |
| SpeechBrain metricgan-plus | −44.1 dB | **+3.4** |
| SpeechBrain mtl-mimic | −45.6 dB | **+1.9** |
| DeepFilterNet2 | −66.2 dB | −18.7 |
| Adobe Enhance Speech v2 @50% | −69.8 dB | −22.3 |
| **DeepFilterNet3 + `--pf`** | **−70.8 dB** | **−23.2** |

DeepFilterNet3 with the post-filter beat a commercial cloud service on the same
file by 1 dB, kept 2.6 dB more 4–10 kHz presence than it, and ran locally at
**24x realtime** (354 s of audio in 14.6 s). Both SpeechBrain enhancement models
were *worse than doing nothing new* — they are trained on VoiceBank-DEMAND
(indoor, moderate SNR) and they are **16 kHz**, so they also throw away
everything above 8 kHz. Comparison above is band-limited to 0–8 kHz so that
does not flatter them.

Use `helpers/denoise.py`, which builds a prepped source. Keep `arnndn` in the
EDL for the in-car takes: measured across all 25 sources, 3206 was the *only*
gusty one (26.6 dB swing; everything else 3.4–17 dB), and steady car drone reads
as normal even at 7 dB separation.

---

## DeepFilterNet needs its own interpreter — two independent pins

Neither is a preference; both are hard failures.

1. **`DeepFilterLib` 0.5.6 ships macOS arm64 wheels for cp38–cp311 only.** On
   3.12+ the install tries to build the Rust extension from source and fails.
   The repo's own env is 3.12, so this cannot live in it.
2. **DeepFilterNet 0.5.6 imports `torchaudio.backend.common.AudioMetaData`**,
   deprecated in torchaudio 2.1 and **removed in 2.2**. With a current
   torchaudio (2.11) the import raises `ModuleNotFoundError` before doing any
   work. Pin `torch==2.1.2 torchaudio==2.1.2`.

`helpers/denoise.py` bootstraps `~/.cache/video-use/denoise-env` (python 3.11,
~2 GB, once) and shells out to it, exactly as it shells out to ffmpeg.

---

## Restoring "outdoors" after denoising: blend the residual, high-passed

Fully denoised outdoor audio sounds wrong — you are visibly outside and there is
no air at all. The instinct is to mix a bit of the original back (DeepFilterNet
even offers `--atten-lim` for it). **On wind that does not work**: 84% of what
the model removes is below 300 Hz, so the original's "ambience" *is* the wind.
Measured: blending 10% of the raw signal back put the floor at −51.5 dB, which
is exactly where the old `arnndn` chain already was — the whole gain, given away.

Instead blend back the **residual** (`raw − clean`) **high-passed at ~500 Hz**,
which keeps water, birds and general air and leaves the rumble out:

| | floor |
|---|---|
| `arnndn` lq (shipped) | −47.5 dB |
| DFN3 + 20% high-passed ambience | −54.9 dB |
| DFN3 + 10% high-passed ambience | −59.4 dB |
| DFN3, no ambience | −73.7 dB |

`helpers/denoise.py --ambience 10 --ambience-hp 500`.

---

## A denoiser that changes the sample count moves every cut after it

SpeechBrain's `mtl-mimic-voicebank` returned 24.992 s for a 25.000 s input — 8 ms
short, silently. Since caption offsets and overlay positions are measured from
segment lengths, one shortened source shifts everything downstream and the
render still succeeds. DeepFilterNet3 is sample-exact (17,028,000 in,
17,028,000 out, 0.00 ms envelope lag), but `denoise.py` asserts it rather than
trusting it, and refuses to write a file that failed the check.

---

## Phone "stereo" is usually dual mono — check before processing twice

Every Detour-2 a-roll clip shot on the phone came back as 2-channel with L/R
correlation of exactly 1.0 and the side channel at −220 dB: one capsule, written
twice. The in-car dual-capture clips (`IMG_3178`) are genuinely stereo
(correlation 0.66). Detecting dual mono halves the denoise work and, more
importantly, keeps the channels bit-identical instead of running a mono model
twice and getting two slightly different answers.

---

## Overlays placed with `setpts` drain ahead in a long render, then freeze on their last frame

`[i:v]setpts=PTS-STARTPTS+t/TB` plus `overlay=enable='between(t,start,end)'` is the obvious way
to place a timed overlay, and it is wrong in a way that only shows up at length.

On a 27-minute cut with five overlays chained, each overlay entered its window **already some
way into its own footage** — the 4th was 48 frames (1.6 s) in, constant from its very first
displayed frame. Having started late in its own material it ran out early, and `overlay`'s
default `eof_action=repeat` then held the last frame for the remainder of the enable window.
These overlays were full-frame, so the picture froze while the audio carried on.

It hit 4 of 5 overlays and grew with position in the chain: **0.43 s, 0.77 s, 1.67 s, 1.93 s**.
The first overlay was unaffected.

What makes this expensive to find: it does **not** reproduce

- on a short clip,
- on a synthetic base (`testsrc2`) of the same length, even with all five overlays chained,
- on a slice of the real base that has been **re-encoded** (re-encoding regenerates timestamps),
- when seeking into the real base with `-ss` — the graph has to run from t=0.

The only reproduction is: real `base.mp4`, decoded from the beginning, full overlay chain.

Fix — position at the demuxer and never let an overlay repeat:

```
-itsoffset <start_in_output> -i overlay.mp4        # per overlay input, BEFORE its -i
overlay=enable='between(t,s,e)':eof_action=pass:repeatlast=0
```

Measured after: overlay frame 0 lands at 1037.500 s for a 1037.513 s cue, best frame offset
−1 (seek granularity) against +48 before, and `freezedetect` finds nothing in the whole film.
Keep `enable` — an overlay FILE may be longer than the EDL asks for (one was 7.50 s against a
declared 7.267 s). Pinned by `tests/test_render_overlay_timing.py`.

**Check every delivery with `freezedetect` over the whole file, without seeking:**

```bash
ffmpeg -i final.mp4 -vf freezedetect=n=-55dB:d=0.4 -map 0:v -f null - 2>&1 | grep freeze_
```

A frozen full-frame overlay is invisible to every other check: duration, frame count, segment
dimensions and A/V sync are all still exactly right.

---

## Piping frames through Python: two colour traps that cost ~20 dB each

Per-frame work that ffmpeg cannot express (a neural mask, a landmark detector)
means piping rawvideo out and back. Both of the obvious ways to do it wreck the
picture while producing a file that plays perfectly and passes every structural
check — duration, frame count and dimensions are all still exactly right.

**1. Do not round-trip through bgr24.** `yuv420p -> bgr24 -> yuv420p` is not
idempotent. Measured on a rendered segment: **34 dB** PSNR against its own
source, where a plain `ffmpeg -i seg -c:v libx264` re-encode of the same file
scores **55 dB**. Every pixel in the frame was being altered in order to
retouch a few hundred of them. Read and write `yuv420p`, do the work on the
planes, and convert a throwaway BGR copy only if a detector needs one.

**2. Tag the rawvideo INPUT, not just the output.** Raw frames carry no colour
metadata, so ffmpeg assumes full range and silently inserts a full->limited
conversion on the way to the encoder:

```
-f rawvideo -pix_fmt yuv420p -color_range tv -colorspace bt709 -s WxH -r FPS -i -
```

Isolated measurement of the same round trip, no processing at all:

| | PSNR |
|---|---|
| output tagged only | **33.8 dB** |
| input tagged too | **52.4 dB** |

The symptom is a subtly washed-out picture and `color_range=unknown` on the
result. Check with `ffprobe -show_entries stream=pix_fmt,color_range,color_space`.

**Always measure a Python video stage against a plain re-encode of the same
file**, not against nothing. "It looks fine" and "the duration matches" both
pass while 20 dB quietly disappears. Pinned by `tests/test_retouch_teeth.py`.

---

## Music levels are per-window, not per-film

Setting all cues to one target relative to the programme's integrated loudness
produced two inaudible cues and one that clipped. The programme level in each
cue's own window is what matters, and on Detour-2 it spanned **84 dB**:

| cue | programme in that window | peak headroom |
|---|---|---|
| title reveal | −32.4 dBFS | 1.7 dB |
| traffic jam | −23.5 dBFS (road noise) | 3.6 dB |
| restaurant | −15.7 dBFS (shop ambience) | **−0.5 dB** |
| dam gate | −99.6 dBFS (muted dashcam) | 57.8 dB |
| dusk timelapse | −59.3 dBFS | 19.8 dB |

Measure the window, then set the cue against it. Where the window has **no
headroom** no music level works — duck the programme instead, and put the duck's
ramps OUTSIDE the music window so full depth is reached before the cue enters.
Ramping from the cue's own start leaves the first half-second unducked, which is
exactly where the sum clipped.

Mix music **before** the loudnorm pass, never after: the normaliser has to see
the finished mix or the music rides on top of an already-normalised programme
and pushes it past −1 dBTP with nothing to catch it.

---

## A range end rounded to 3 decimals captions a word that is never heard

The nastiest bug of the Detour-1 session 2 cut, and the user heard it before any check did:
*"full words are coming in captions, but in speech missing one word before it and jumping to
next."*

`_words_in_range` selects caption words by **overlap**. Deepgram spans are ~87% contiguous, so a
kept word's end IS the next word's start — and rounding that edge to 3 decimals can land a few
**microseconds** past it:

| segment | range end | next word | overlap |
|---|---|---|---|
| IMG_3154 | 17.745 | `और` starts 17.744999 | **1 µs** |
| IMG_3630 | 576.59 | `So` starts 576.58997 | **30 µs** |

Both words were burned into the caption while none of their audio played. Nothing else catches
this: the cut is frame-correct, the SRT is well-formed, Hard Rule 6 is satisfied (the edge is on
a word boundary, just the wrong side of it), and the duration is right.

**Round range ENDS down and STARTS up to the millisecond**, never half-even:

```python
def ms_floor(t): return math.floor(t * 1000) / 1000   # range end
def ms_ceil(t):  return math.ceil(t * 1000) / 1000    # range start
```

That costs under 1 ms of the word being kept — inaudible, and far under one frame — and it can
never cross into a neighbour. Flooring both edges would produce the identical bug at the IN edge,
where it captions the *previous* word instead.

**Standing check before any render:**

```python
ov = min(w["end"], r["end"]) - max(w["start"], r["start"])
if ov > 0 and ov / (w["end"] - w["start"]) < 0.9:   # captioned but not heard
```

Related: a *hint* value fed into a re-snap must sit **inside** the target word, not on its
leading edge. A hint at `मतलब`'s nominal start pulled in the preceding `to`, because `to` ended
3 ms *after* `मतलब` nominally began. Aim hints at the middle of the word you want.

---

## Read the finished cut back as continuous prose — no structural check replaces it

Three real defects in one session were invisible to every automated check and obvious in one
read-through of the assembled text:

- **Five OUT points were taken from a word's START instead of its end**, silently dropping
  `week.` `again.` `special.` `future.` `sort.` — so sentences lost their last word. The EDL was
  internally consistent and every boundary was on a word edge.
- `only.` was dropped from *"today I am going to Rasta Cafe **only.**"* — the speaker's own
  idiom, and the line reads wrong without it.
- A section opened on *"**so that** I can continue my rigid routine…"*, a non-sequitur after the
  preceding cut.

Reconstruct the text from the EDL, not from the SRT — the SRT is chunked for display and hides
sentence structure:

```python
" ".join(w["text"] for w in words(r["source"])
         if w["end"] > r["start"] + EPS and w["start"] < r["end"] - EPS)
```

**And scan every same-source join that skips words without a sentence boundary on either side.**
On this cut that found 10, of which 5 were genuinely broken — all inherited from the *delivered*
session-1 edit:

| was heard as | the words that were missing |
|---|---|
| "most of the places" → *jump* | "are thirty, minimum thirty kilometers from बैंगलोर" |
| "we'll connect to this" → *jump* | "national highway which will take you to मैसूर…" |
| "…like to do that" → "relief" | "और I don't know. It just gives me a" |
| "series is all about" → "it is to maintain" | "whatever I am thinking … what has happened" |

The "relief" one is the clearest illustration: the sentence is *"it just gives me a relief"* and
only the word "relief" survived the cut.

---

## `freezedetect d=0.4` false-positives on a locked-off talking head

`freezedetect=n=-55dB:d=0.4` is the right instrument for a frozen overlay, but on a static-camera
studio shot it also flags a person simply holding still. Measured on a 15-minute cut:

| flag | duration | frame-difference around it | verdict |
|---|---|---|---|
| parked dashcam shot | **2.7 s** | 0.20 (vs 13–25 for moving footage) | **real** |
| studio, 8:49 | 0.40 s | 0.72 mean, peaks >20 | false positive |
| studio, 12:12 | 0.43 s | 0.88 mean, peaks >20 | false positive |

Both false positives sat *exactly* at the threshold. **Use `d=1.0` to discriminate**; it kept the
real one and dropped both false ones. Keep `d=0.4` only where the whole frame should be moving.

**And a dashcam clip near the end of a drive is probably a PARKED car.** `NO20260821-221031`
looked like "pulling into the garage" from a single frame and is 100% static — the dashcam keeps
recording after the engine stops. A per-clip frame-difference scan located the real arrival ~8
minutes earlier. Two things made that scan trustworthy:

- **Validate the metric on a known-moving control first.** Highway footage read 13.6 and city
  footage 25.1 against 0.21 for the parked clips. Without that control, "everything reads 0.2"
  looks like a broken measurement.
- **Scan *within* the chosen clip too.** The first replacement was still wrong — the car was
  stopped at a gate waiting for it to open for the entire window. Per-2s differences inside the
  clip found the moving stretch (47–60 s).

---

## Speech buried under road noise: measure before inheriting a chain

Re-measured on Detour-1, with the noise floor taken in real speech gaps located from the
transcript:

| setting | raw separation | `highpass=100,afftdn=nr=22` | **`arnndn` lq** |
|---|---|---|---|
| car, day (IMG_3152) | **0.9 dB** | 2.6 dB | **19.3 dB** |
| car, day (IMG_3156) | 1.7 dB | 4.0 dB | **17.7 dB** |
| car, night | 12.7 dB | 15.6 dB | 17.4 dB |
| cafe (fans running) | 9.2 dB | 9.9 dB | 11.8 dB |
| **studio (treated room)** | 7.1 dB | 7.0 dB | **7.1 dB — nothing helps** |

Two things worth carrying forward. At **under 2 dB** of raw separation the speech is genuinely
buried, not merely noisy, and the `afftdn` chain this KB recorded from an earlier shoot bought
almost nothing — consistent with the existing note that spectral denoise barely touches broadband
noise overlapping speech. And a **quiet room is the case where every chain measures identical**:
there is no broadband noise to remove, so the correct setting is `audio_filter: ""`. Applying a
chain there only attenuates the voice.

---

## Caption chunking for long-form: measure each option on its own

The shipped default breaks on `.,!?;:`, which on a 15-minute cut with a 9-minute monologue
produced **493 cues, 86 of them a single word** ("uh", "calling them", "the brain."). Each option
measured in its own run:

| style | cues | mean words | 1-word | 2-word |
|---|---|---|---|---|
| default (6 words, break on `,` too) | 493 | 4.3 | 86 | 49 |
| `break_on ".!?"` | 435 | 4.9 | 43 | 33 |
| + `words_per_chunk 7` | 377 | 5.6 | 36 | 17 |
| + `min_words 3` | **331** | **6.4** | **4** | **3** |

`break_on ".!?"` is the big win and costs nothing; commas in speech are breath marks, not clause
boundaries. Mixed Devanagari/Latin cues read correctly at 7 words.

---

## `drawtext` does no font fallback — a missing glyph ships as a blank box

Subtitles and on-screen text behave differently here, which is exactly why this is easy to miss.
libass (the `subtitles` filter) substitutes another face for a glyph the style's font lacks, so
mixed Devanagari/Latin captions render correctly. `drawtext` does not fall back at all: whatever
the chosen font is missing is drawn as tofu, silently, in a file that is otherwise perfect.

Measured on macOS with `HSR -> बढ़िया 5:30`:

| font | Latin | Devanagari |
|---|---|---|
| `Helvetica.ttc` | correct | **tofu** |
| `Kohinoor.ttc` | correct | correct |
| `DevanagariMT.ttc` | **tofu** | correct |

So a Devanagari-only face is not the safe choice either — it breaks the Latin half of a Hinglish
line. `Kohinoor.ttc` covers both and is the one to use for this footage. Note it still lacks
common symbols: `→` (U+2192) is **not** in it, at any of its five faces.

`helpers/graphics.py` checks coverage with fontTools before building the filter and refuses,
naming the characters. Two details that matter in that check:

- A `.ttc` must be inspected at **face 0**, because that is the face `fontfile=` selects —
  `drawtext` exposes no face index.
- "Could not inspect the font" must not return the same value as "checked, nothing missing".
  An earlier version returned an empty set for both, so in an environment without fontTools the
  guard silently became a no-op while still reading as a clean result. It now returns `None` for
  uncheckable and warns once.

---

## zsh: a loop variable named `path` destroys your PATH

Third zsh trap in this KB. `$path` is zsh's array form of `$PATH` — they are tied together — so
this wipes out the shell's command lookup mid-script:

```zsh
for path in /a/font.ttc /b/font.ttc; do
  ffmpeg ... "$path"        # "command not found: ffmpeg" from the FIRST iteration
done
```

The failure looks like a broken environment rather than a naming collision, and `export PATH=...`
at the top of the same command does **not** save you — the loop clobbers it again immediately.
Other tied pairs to avoid as variable names: `cdpath`, `fpath`, `manpath`.

Use any other name (`fp`, `font_path`). Bit me while comparing three font files.

---

## Grouping a script on silence fails on footage that is already edited

`script_scan.py` and anything else that reasons per phrase must split on **sentence-final
punctuation**, not only on silence gaps. An unedited rush has pauses to split on; a finished
video has had every one of them removed.

Measured on a delivered 11-minute reference edit: grouping 2267 words on gaps >= 0.55 s produced
**11 groups for the whole film** — paragraphs of ~200 words. Every detector then fired on the
same paragraph, several times over, and the reported quotes were unusable. Splitting on `.?!`
first gave proper sentences and the detections became one-to-one with what was actually on
screen.

The same applies to reading a cut back as prose, or to anything that reports "the line where X
happens": on edited material the sentence is the unit, and the silence is gone.

---

## A figure detector must model salience, or it buries the real hits

First pass over an 11-minute reference found **20 opportunities, 15 of them figures**. The
reference edit put a graphic on **three**. Everything else — "give me the next ten minutes",
"it took me four weeks" — was conversational quantity, and a detector that reports them all is
worse than no detector, because the three that matter are now in a list of twenty.

What separates them, derived by checking each against what he actually drew:

| signal | effect |
|---|---|
| not round for its magnitude (12,917) | **+0.45** — an odd number is evidence, not an aside |
| a range ("15k to 40k") | +0.30 — a range is always a claim being made |
| money/audience unit, or a money verb nearby | +0.35 / +0.25 — the unit may be "a month" while the subject is money |
| narrative anchor ("thirteen years **ago**") | +0.45 — the strongest cue in a personal essay |
| conversational framing ("give me the next…") | **−0.45** |

Three parsing traps found on real transcripts, each of which produced a confident wrong number:

- **`10**(len(str(v))-2)` as the roundness divisor makes every two-digit number round**, which
  scored "thirteen years ago" — the spine of an entire episode, and its thumbnail — at zero.
- **A comma ends a number.** "hundred, hundred and fifty kilometers" is two alternatives; without
  a comma boundary it parses as **10,050**.
- **Indian spoken idiom**: "two fifty rupees" is 250, not 2 + 50. "one twenty" is 120.

And one precision trick worth reusing: **"not X but Y" is only a real contrast when both X and Y
recur in the script.** "Motion design is not difficult, but people…" is rhetorical negation;
"difficult" occurs once. "Video editing and motion design" occur throughout. Requiring both
sides to appear at least twice removed the false positive without losing the true one.

---

## Component timing must be absolute, and type must be fitted

Two bugs from building the motion graphics layer, each of which cost a full render and each of
which produced a *valid* file with something silently missing.

**1. A relative duration compared against an absolute clock draws nothing.** Components took a
`duration` and computed their exit fade as `t - (duration - fade)`, while `draw(img, t)` receives
the ABSOLUTE output time. A component placed 11 s into the timeline therefore decided its fade
had finished nine seconds ago and painted nothing — no error, no warning, just an overlay with a
hole in it. Components now take absolute `start` and `end`, and every weight is anchored to
`self.start`. There is then no offset left to get wrong.

**2. Type with no fit is clipped by the canvas pad, silently.** "CONSTANTLY AFRAID OF FAILING"
and "FOR MY MOMENT" both ran past the edge of the overlay canvas and were cut mid-word; the
encode succeeded and the alpha check passed, because the pixels that existed were fine. Fit every
string to the available width before drawing, and leave room for the drop shadow — fitting to
exactly the canvas width still clips the shadow, which is what makes it read as an accident
rather than a tight layout.

A related one: **PIL does not fall back to another font either.** Same rule as `drawtext` —
select an international face explicitly when the string contains anything above U+024F.

---

## PIL's ImageDraw replaces the pixel, it does not blend

`ImageDraw.text`/`rectangle` with an RGBA fill writes that RGBA value straight into an RGBA
image. It does **not** alpha-composite, and `ImageDraw.Draw(img, "RGBA")` does not change this:

```python
img = Image.new("RGBA", (8, 8), (0, 0, 0, 255))
ImageDraw.Draw(img).rectangle([0, 0, 7, 7], fill=(255, 255, 255, 25))
img.getpixel((4, 4))      # (255, 255, 255, 25) - NOT (25, 25, 25, 255)
```

In the real overlay pipeline this is harmless and in fact what you want: the canvas is
transparent, each element is drawn once, the alpha lands in the PNG and **ffmpeg** composites it.

It is a trap when **previewing**. Drawing a 9%-alpha element onto an opaque background and then
`convert("RGB")` shows it at *full* brightness, because the alpha was written rather than
applied and then discarded. A correctly-ghosted background numeral previewed as a solid slab,
and chasing that cost a rebuild of a component that was already right.

Preview the way ffmpeg composites:

```python
layer = Image.new("RGBA", size, (0, 0, 0, 0))
component.draw(layer, t)
Image.alpha_composite(background, layer)
```

Corollary for authoring: where two elements overlap on one canvas, the later draw **replaces**
the earlier rather than blending over it. That happens to give the right z-order for text over a
ghosted numeral, but it is not blending, and anything that depends on real translucency between
two drawn elements has to go through its own layer and `alpha_composite`.

---

## `pad` evaluates x/y once; `overlay` can evaluate per frame

To animate a picture shrinking inside a constant-size frame — speaker demotion — the obvious
chain is `scale` with `eval=frame` into a `pad`. It does not work: **`pad` evaluates its x/y
expressions once at configuration time**, when the input is still full size, so x resolves to 0
and the picture collapses towards the top-left corner instead of staying centred.

`overlay` onto a `color` source does evaluate per frame:

```
color=c=#0A0A0A:s=1x1:r=FPS[bg_src];
[0:v]split[ref][src];
[bg_src][ref]scale2ref[bg][r];[r]nullsink;
[src]scale=w='2*floor(iw*S(t)/2)':h='2*floor(ih*S(t)/2)':eval=frame[sc];
[bg][sc]overlay=x='W*X(t)-w/2':y='H*Y(t)-h/2':eval=frame:shortest=1
```

Both `eval=frame` are required — dropping the one on `scale` freezes the size, dropping the one
on `overlay` freezes the position. Keep the scaled dimensions even (`2*floor(.../2)`) or the
encode fails in yuv420p. Verified: constant 3840x2160 output, picture easing smoothly from full
frame to a 40% card and back.

---

## A matte is a new signal, so it escapes the colour round-trip tax

The KB records that piping frames through Python costs ~20 dB for a bgr24 round trip and another
~19 for an untagged rawvideo input. That rule is about **modifying and writing back the
picture**. Generating a *matte* does not: frames go in, an 8-bit mask comes out, and every
composite stays in ffmpeg. The 4K master is never decoded into numpy at all.

So the shape that avoids the whole class of problem is:

```
frames --(downscaled)--> python --> matte.mp4       # only the mask leaves Python
[base] + behind-overlays                            # picture stays in ffmpeg
[base] + [matte] -> alphamerge -> [subject]
[with_overlays][subject] overlay -> out
```

Three details that each cost a debugging round:

- **`scale2ref` takes TWO inputs and returns two.** `[matte][ref]scale2ref[scaled][ref_out]`.
  Calling it with one input is a filtergraph error, and `alphamerge` needs the matte at exactly
  the base's size or it fails naming the filter rather than the cause.
- **Dilate the matte and smooth it over time.** A slightly generous matte hides the seam; a
  tight one eats into a shoulder. Per-frame segmentation flicker is far more visible than a
  matte that is a few pixels wrong.
- **Refine against the frame's own luma.** MediaPipe's selfie segmenter is 256x256 natively, so
  its edges are soft and do not follow the subject; a guided filter against the luma snaps them
  back. 2 ms/frame for the model, ~24 s for a 13 s 4K clip end to end.

**And the test that looks like a failure but is not:** a graphic centred behind a centred
speaker disappears completely. That is the feature working. Place the graphic so it extends
past the silhouette — the reference's own example spans the full frame width and lets the
speaker occlude the middle.

---

## UI motion numbers are wrong for video, and the two get confused constantly

Motion-design guidance on the web is almost all about **interfaces**, where the
user is *waiting on the machine*. Video graphics are the opposite case: the viewer is
watching at the speaker's pace and the motion is synced to speech. Importing one set of
numbers into the other makes the result feel wrong in a way that is hard to name.

Reference guidance (OpenDesign `craft/animation-discipline.md`, Apache-2.0; Emil Kowalski's
motion skill) converges on:

| UI rule | Why it exists | Video equivalent |
|---|---|---|
| 150 ms default, <500 ms for microinteractions | past that the user notices motion *as motion* and waits | **0.30–0.72 s.** Nobody is waiting; a 150 ms reveal on a 4K title reads as a flicker |
| "frequent animations ≤200 ms" | a hover seen 50x per session | irrelevant — a graphic plays once |
| "stagger only small groups; long staggers feel slow" | the user is blocked | staggers are *paced to speech*; a 4-item list over 4 s is correct if he takes 4 s to say it |
| `prefers-reduced-motion` | accessibility, per-user | not expressible — video is baked. Hold the frame longer instead |

`motion.WEIGHTS` is therefore deliberately 2–4x slower than any UI token set, and that is not
an oversight.

**What does transfer, and is worth taking:**

- **Curve for opacity, spring for transforms.** This one is universal and we had it wrong: a
  spring on alpha overshoots past fully-opaque and dips back — `hero` peaked at 1.205, clamped
  to 255, then fell to 96% before settling, so every hero element pulsed as it arrived. `Weight`
  now carries a separate `alpha_curve`. Transform overshoot is the point; alpha overshoot is a
  bug.
- **Animation does not aid comprehension.** Tversky/Morrison/Bétrancourt 2002 (IJHCS 57,
  247-262) found every study claiming otherwise had a broken control. The endorsed use is
  spatial/temporal reorientation. This is the citation behind the restraint rule we had already
  arrived at empirically from the reference edit — roughly a third of it carries no graphic.
- **Cap the accent.** ~2 visible uses per frame. A list with both a heading and an accented
  final item is already at the cap from one component, so the heading yields to muted.
- **~80% proven patterns + ~20% distinctive**, with the distinctive part concentrated in one
  moment rather than spread thin — the same idea as the reference's "one thing nobody has
  seen before".

---

## An EDL in a subdirectory loses its transcripts, and an empty SRT hard-fails

`render.py` takes `edit_dir` from the EDL's own parent, and `build_master_srt` reads
`<edit_dir>/transcripts/<source_key>.json`. So a scratch EDL placed in `edit/gfx_demo/`
looks for `edit/gfx_demo/transcripts/` and finds nothing.

The failure is two-stage and the first stage is quiet: a missing transcript is a soft skip
(`no transcript for X, skipping captions`), so the SRT is written with **0 cues**, and only
then does the subtitle filter fail — `ffmpeg` exits 183 on an empty subtitle file, with an
error that says nothing about transcripts.

Symlink the real directory next to the scratch EDL:

```bash
ln -sfn ../transcripts <edit>/gfx_demo/transcripts
```

Worth checking the cue count in the render log (`master SRT → master.srt (N cues)`) whenever a
demo EDL lives anywhere other than the main edit directory. `0 cues` is the tell.

---

## A graphic that repeats the caption adds nothing

The scanner reported **no opportunity** on a roadmap line — *"I'm going to show you exactly
what changed my answer and the philosophy that I use now"*. Overriding it and setting the two
promised items as `WHAT CHANGED MY ANSWER` / `THE PHILOSOPHY I USE NOW` produced a graphic
that said, word for word, what the burned caption underneath already said. Two renders of the
same sentence, one above the other.

The fix is not to drop the graphic but to **abstract it**: `① THE TURN`, `② THE PHILOSOPHY`.
Chapter markers do something the caption cannot — they announce structure and persist past the
words — and they are short enough to leave a real margin, which fixed a composition problem in
the same move.

Two rules from this:

- When a graphic and a caption occupy the same beat, one of them must be **saying something
  different**. Either abstract the graphic, or suppress the caption for that span.
- **A shorter label is usually the fix for a crowding problem too.** The verbatim version ran
  to 88 px from the frame edge and read as clipped even though it was not.

---

## A retention curve from a small channel is mostly quantisation

Verified on the Episode 1 export (`Audience retention 2026-08-16_2026-09-20`):
**every value is a multiple of 4.76 = 1/21.** The curve is 21 viewers. Each
visible "cliff" is one to four people, and the shape carries far less
information than it appears to.

`coverage.py` now infers N from the smallest non-zero step between samples and
prints a warning below 200. Do not plan an edit around a feature of a curve
smaller than 100/N points.

**Prefer `Organic.csv` over `All.csv`.** The export's third column,
"Compared to other videos (%)", is benchmark-normalised, so it survives small N
where the raw curve does not — and on this video the two columns tell opposite
stories. Raw: 95% → 52% in the first 10 s, which reads as a failed hook.
Benchmark: **+17.9 over typical across the same 10 s.** Most of that drop is
what every video experiences; only the departure from the benchmark is a
signal about *this* cut. `load_retention()` uses the third column when present
and `LAST_METRIC` records which, because a percentile printed with a `%` sign
reads as "a third of people stayed" when it means "a third worse than typical".

The one window on that video that is genuinely below benchmark — 2:32–2:47,
bottoming at **-35.9** — is 15 seconds of hedging ("I have not. I am still
learning. I'm still failing… whatever I'll share here, it will be from
something that I have actually lived"). It recovers to **+59.8** for the last
30 s, which is the specifics ("the dream that I gave up, a body that broke").
Unproven as causation, N=21 — but it is the only window worth acting on, and
it sits inside the 124.9 s no-change stretch.

---

## `zoompan`'s `d` expands EVERY input frame, so `-loop 1` multiplies the clip

A Ken Burns push on a still, written the obvious way:

```bash
ffmpeg -loop 1 -framerate 30000/1001 -t 3.6 -i photo.png \
       -vf "…,zoompan=z='1+0.07*on/108':d=108:s=3840x2160" out.mp4
```

produced a **389-second, 382 MB file** for a 3.6-second still. `d` is not the clip
length — it is how many OUTPUT frames each INPUT frame becomes. `-loop 1 -t 3.6`
feeds 108 input frames, and every one of them gets expanded to 108 output frames:
108 x 108 = 11,664 frames.

`-t` on the input does not help, because the input is what is being multiplied. Cap
the **output** instead:

```bash
ffmpeg -loop 1 -framerate 30000/1001 -i photo.png \
       -vf "…,zoompan=z='1+0.07*on/108':d=108:s=3840x2160" \
       -frames:v 108 out.mp4
```

`on` is the global output frame index, so over the first input frame's expansion it
runs 0..107 and the move completes exactly once. The file is then 5 MB.

It fails loudly only if you check: the encode succeeds, the frames are correct, and
the picture looks right in any thumbnail. Probe the duration of anything built with
`zoompan`.

To pull BACK instead of pushing in, `z` must still go from >1 down to 1 —
`z='1.087+(1-1.087)*on/N'` — because `zoompan` clamps `z` below 1.

---

## `drawtext` cannot take an apostrophe in `text=`, whatever you escape it with

`text='Become Someone You're Proud Of'` exits with code 8. The filter's own
single-quote parsing runs before any shell escaping you apply, and the usual
`\'`/`'\''` tricks do not survive both layers.

Use `textfile=` and put the string in a file — which also sidesteps `:`, `%` and
`\` in the same stroke. `fontcolor` wants `0xRRGGBB`, not the `#RRGGBB` that
`brand.json` stores, so strip the `#`.

Episode 1 already shipped `build/tagline.txt` and `build/byline.txt` for this
reason; the lesson had just not been written down.

---

## A grade tuned on SDR footage over-saturates when the source is HLG

Episode 1 was `bt709` 8-bit. Episode 2 was shot on the same phone in the same room
and is **HLG HDR** — `yuv420p10le`, `bt2020nc`, `arib-std-b67`. `render.py` detects
the transfer and tone-maps to Rec.709, which is correct and necessary (untone-mapped,
the output looks washed out and orange in anything that honours the metadata).

What is NOT safe is reusing the previous episode's grade string on top of it. The
tone-map already supplies the contrast and saturation that a grade written for flat
SDR was adding. Measured on the same frame:

| | mean luma | p5 | p95 | mean sat | frame R/B |
|---|---|---|---|---|---|
| no tone-map | 137.6 | 44.4 | 196.4 | 0.236 | — |
| tone-map only | 128.0 | 43.7 | 180.7 | 0.358 | 1.45 |
| tone-map + Ep1 grade | 129.5 | 31.0 | 192.6 | **0.407** | **1.57** |
| Ep1 as DELIVERED | 98 | 15 | 198 | **0.29** | **1.01** |

Grade the tone-mapped image on its own terms. White-balance off a **known white in
the frame** rather than a global R/B ratio — a global ratio cannot tell a warm cast
from a room that genuinely contains a lot of wood and amber. Here the white t-shirt's
brightest 2% read R/G 1.055, B/G 0.892, and — the part that makes it usable — varied
by under 0.02 across five takes, so one `colorchannelmixer=rr=0.948:bb=1.121` serves
the whole shoot and a fixed string beats `"auto"`.

Then restore what the tone-map compressed: a curve took p5 43.7 -> 19.0 and p95
180.7 -> 196.7, landing on the previous episode's delivered 15 / 198. Note that
adding contrast puts saturation back up, so the desaturation has to be set after the
curve, not before it.

---

## `coverage.py` counts 75 jump cuts as 5 visual events, and it is right

A 12m55s single-setup talking head with 75 cuts and per-segment push-ins of
1.00-1.10x measured **5 visual events, 0.4/min, median hold 204.8 s**. That is not a
bug in the detector. A cut between two segments of the same locked-off frame, at
scales 1.03 and 1.06, is not a visual change to a viewer either — the push-ins do
their job (they stop the splice reading as a glitch) but they are invisible as
*events*.

Consequences:

- Do not read a low event count as "the cutting is lazy". Read it as "the frame has
  not changed", which on a one-camera shoot is simply true.
- Push-ins are not a substitute for cutaways. Only something that replaces the frame
  — a still, a graphic, a b-roll shot — moves this number.
- Run `coverage.py` on the picture lock, BEFORE building graphics, so the stretches
  it names are what you build for. Run it again after, to see what is still bare.

---

## Anchor a graphic to a spoken word, and make the resolver RAISE when the word was cut

Placing overlays by anchoring them to words (`output_time(source, word_start(...))`)
rather than to timestamps means a re-cut re-places them for free. The load-bearing
detail is what happens when the anchor word is no longer in the episode.

`"back" #1` in one take was "cycle **back**", inside a stutter that had been trimmed.
A resolver that clamps, or picks the nearest surviving word, would have put a list
item on a silent frame 10 s away and nothing would have looked wrong in the render.
Raising instead surfaced it immediately, and it was re-anchored to "eight".

Same rule for the still cutaways: print the words each overlay actually covers and
read them. It is the only check that catches an overlay landing on the wrong half of
a sentence.

---

## An overlay must be authored at the OUTPUT height — render.py does not scale it

`build_final_composite` chains overlays as
`overlay=enable='between(...)':eof_action=pass:repeatlast=0` with no `x`/`y` and
no `scale`. Default position is 0:0, so a 3840x2160 overlay on a 1920x1080 base
shows **its top-left quarter**, full size.

It does not error, and it does not look like a geometry bug — it looks like badly
chosen framing. A centred photo cutaway came out as an empty field with the subject
off-frame; a left-hand list ran off the bottom of the picture. Both were "plausible
enough to argue about" rather than obviously broken.

Episode 1 never hit it because it built one overlay at 2160 and rendered at 2160;
the filename `prepped/TEASER_BROLL_2160.mp4` records the height, which is worth
copying as a convention.

Consequences:

- Overlays are **resolution-specific**, unlike `ranges[].zoom`. The same EDL is
  not valid at two heights once it has overlays.
- `--preview` (1080) and `--draft` (720) therefore cannot QC a 2160 delivery's
  overlays. Check overlay geometry on a render at the DELIVERY height, or build a
  set at the preview height too.
- Verify by measuring both, not by eye: the base's real width through
  `scale=-2:<height>` (never predicted — see the SAR gotcha above) against
  `ffprobe` on each overlay. They must be identical.

A `scale2ref` in the overlay chain would make overlays resolution-independent and
would be a no-op for a correctly-sized one. Not done here, because it changes
shared tool behaviour in the middle of a delivery.

---

## render.py never cleans its clips directory, so a changed EDL leaves stale segments

Segments are written as `clips_<quality>/seg_<NN>_<SOURCE>.mp4`. Nothing deletes
them. Tighten a cut from 75 ranges to 72 and the directory holds **102 files** —
the 72 new ones, plus every old name that no longer collides.

Anything that measures by globbing then reads a mix of two different cuts. The
first symptom here was `measure.py` refusing with "102 segments but EDL has 72
ranges", which is the good case. The bad case is a glob that happens to return
the right *count* and silently measures the wrong segments, putting every
overlay position out by seconds.

Build the expected names from the EDL instead, and say so when extras are found:

```python
segs = [d / f"seg_{i:02d}_{r['source']}.mp4" for i, r in enumerate(ranges)]
stale = sorted(set(d.glob("seg_*.mp4")) - set(segs))
```

Same class of bug for any *derived* file cached next to its source. A scaled
copy of an overlay must be checked for freshness, not just for dimensions —
`dst.stat().st_mtime >= src.stat().st_mtime` — or rebuilding the master silently
keeps compositing the previous version.

---

## "Is the music off in this window?" cannot be answered by an absolute level

Measuring the noise floor of a stretch that should be unscored, and comparing it
against a stretch that is scored, gives a number that looks decisive and is not.
Measured on this episode: the zenith (deliberately unscored) read **-31.5 dB**
and a scored section read **-30.7 dB** — apparently identical, apparently a bug.

It was not. The programme's own room tone varies by up to **17 dB** between
takes and between windows with different speech density, and that swamps a
ducked bed sitting 15 LU down.

The only valid test is a **control**: measure the same windows on the no-music
render and on the mix, subtract the mix's own normalisation gain, and look at
the difference.

```
window                     no-music   mixed     rise
zenith (must be naked)       -41.1    -31.5    -1.2 dB   <- confirmed silent
scene 8 opening (scored)     -58.0    -30.7   +16.4 dB
the 20cm reveal (unscored)   -48.6    -37.9    -0.1 dB   <- confirmed silent
```

Generalises to any "did this process change that region" question on audio or
picture: diff against the same source without the process, never against a
different region of the same output.

---

## Generated b-roll arrives with three problems, and one of them is editorial

From a batch of ten Gemini/Veo clips supplied for this episode:

1. **A watermark on every clip** — a 44x45px sparkle at a fixed position
   (x 1138-1181, y 577-621 at 1280x720). `delogo` removes it invisibly over
   texture and smooth gradients; it smears over hard geometry, so check each
   one rather than applying it blind. Detect it by finding pixels that are
   bright in *every* sampled frame — real content moves, the mark does not.
2. **Burned-in prompt captions** on some clips (bottom-left). A crop that
   clears the caption can be chosen to clear the watermark at the same time and
   stay 16:9: here `crop=1138:640:0:0` did both with no delogo at all.
3. **720p and 24fps** into a 2160p / 30000:1001 delivery. For the frame rate,
   map one source frame to one output frame (`setpts` x 29.97/24) so the clip
   plays 0.8x with **no judder** — for footage standing in for memory that
   reads as a choice. For resolution there is no fix, only mitigation: lanczos
   plus grain, and a treatment that makes softness look like grade.

The editorial one: a batch generated for a **memoir** included two photorealistic
children captioned "Childhood Uniform Photo" and "Chair Portrait", styled as
archival film frames. Those are fabricated photographs of the subject's own
childhood, in an episode whose premise is correcting a version of the story he
used to tell wrong — and a real photograph of exactly that already existed.

The line worth holding, and worth stating before assets are generated:
**environments and objects, not people who could read as the subject or their
family.** The real photographs carry the people; generated shots carry the world.

Also: a montage clip supplied as a contact sheet may contain shots that exist
nowhere else. Scan any supplied clip densely (0.25s intervals) rather than
sampling one frame — a 10s "reference" here held nine distinct sub-shots, four
of them wanted and unavailable separately.

---

## zsh eats `[a]` after a variable — a third form of the same trap

```bash
ffmpeg … -filter_complex "[0:a]atempo=$sp[a]" -map "[a]" …
#   -> "Output with label 'a' does not exist in any defined filter graph"
```

`$sp[a]` is **array subscripting** in zsh, so the filter label is consumed and
`atempo=` is left with no value. The error points at the `-map`, which is the
one place the bug is not.

Brace it: `atempo=${sp}[a]`.

This is the same root cause as the `$VAR:x` history-modifier entry above and the
word-splitting entry: **in a filter string, brace every variable that is
followed by punctuation** — `:`, `[`, `{`, `#`, `%`. The rule is not "brace
before a colon", it is "brace in filter strings, always".

Related, from the same session: a `-filter_complex` whose `fontfile=` path
contains a space (`…/Supplemental/Arial Bold.ttf`) fails with drawtext's
misleading "Either text, a valid file, a timecode or text source must be
provided" — it is the FONT path breaking the parse, not the text option. Use a
face whose path has no spaces (`/System/Library/Fonts/Helvetica.ttc`), or pass
the graph via a Python list with `-vf` so no shell is involved.

## An English-only whisper model on Hindi returns a REPEATING LOOP, not gibberish

Verified 2026-09-23 pulling a reference video (`T6VLsGIYqeQ`, Ritu Solanki). YouTube
rate-limited its captions (HTTP 429 on the timedtext endpoint, while the same run succeeded
for another video minutes earlier), so the audio was transcribed locally instead.

`ggml-small.en.bin -l en` on Hindi audio produced **1078 words that were one sentence repeated
~90 times** — *"It's not easy to make a penguin happen."* The danger is that this does not look
like a failure. It looks like a badly transcribed but real video, or a video that is genuinely
repetitive, and a summary written from it would be confident and entirely invented.

Two separate lessons:

- `index.md` already warns that **`--language en` on code-switched audio** returns confident
  gibberish. This is the neighbouring trap: **the `.en` MODEL cannot fall back at all.**
  `ggml-small.en.bin` is English-only; on Hindi it degenerates rather than mistranslating.
  Use multilingual `ggml-small.bin`.
- **Detect the language before transcribing an unknown source**, on a slice from the MIDDLE
  (an intro is often music or English):
  `whisper-cli -m ggml-small.bin -f slice.wav -l auto -nt 2>&1 | grep auto-detected`
  It returned `hi (p = 0.98)` in seconds and explained the whole thing.

For Hindi → English, `ggml-small.bin -l hi -tr` (translate mode) gave a clean, coherent 1531
words. Sanity-check any whisper output by counting unique lines against total lines before
reading it as content.

## yt-dlp: captions 429 long before audio does

Same session. Subtitle downloads hit `HTTP Error 429` and stayed blocked across several
retries and `--sleep-requests 8`, while `-f bestaudio -x` for the *same* videos downloaded
immediately. `--extractor-args "youtube:player_client=ios"` does not help — that client offers
no subtitle formats at all and fails with "Requested format is not available".

So when captions are rate-limited, don't wait it out: pull the audio and transcribe locally.
It is free, it is the pipeline this repo already has, and it sidesteps the limit entirely.

---

## Selective speed-up belongs in a prepped SOURCE, not a per-range filter

Delivering part of an episode faster ("1.10x on the expository scenes") looks
like a job for `ranges[].filter` with `setpts`. It is not.

render.py maps transcript word times into output time using each segment's
measured start and assumes time runs 1:1 *inside* a segment. Speed a range up
and every caption inside it drifts by the rate: 10% of the segment's length,
which on a 26s segment is **2.6s adrift by its end**. The frame-count check
fails too, because the extractor still expects `round((end-start)*fps)`.

Build the sped clip as a SOURCE instead, with its own transcript whose word
times are divided by the same rate:

```python
t = json.loads((TRANS / f"{take}.json").read_text())
for w in t["words"]:
    for k in ("start", "end"):
        w[k] = round(w[k] / RATE, 4)
```

Every downstream stage then sees an ordinary clip. Keep the hand-written SPEC in
ORIGINAL timecodes and convert at emit time, so boundary snapping still runs
against the original transcript and the spec stays readable:

```python
out.append((speed_src(src), speed_t(src, a), speed_t(src, b), z, beat))
```

Two traps found doing it:

- Anything that resolves an anchor by source name — graphics, overlays — must
  apply the same rename and rescale, or it raises "not in the cut" on a word
  that is plainly still there.
- A source-path router keyed on the `IMG_` prefix sent `IMG_3657_110` to
  `../IMG_3657_110.mov`; the retimed clips live in `prepped/` as `.mp4`.

`atempo` preserves pitch and 1.10 is well inside its transparent range. Retime
video and audio by exactly the same factor in one graph or they drift apart.

---

## An effect 9 dB under the programme cannot be detected by RMS

Checking whether a spot effect actually landed by comparing the window's RMS
before and after the mix gives "+0.3 dB — inaudible" for every cue, which looks
like a broken filtergraph and is not. The arithmetic: a signal 9 dB down adds
`10*log10(1 + 10^-0.9)` = **0.5 dB**. The test cannot resolve what it is asked
to resolve.

Subtracting the two renders does not rescue it either. The mix path carries a
limiter and an AAC encode, so `mixed/gain - dry` leaves a uniform residual —
measured **~2.5 dB in every window**, including ones that are provably silent.

What does work, per element type:

- **Beds** (music, a ticking clock): the 10th-percentile **floor** between
  sounds, against a no-music control. On this episode that read +14.8 dB where a
  bed was present and −0.0 dB at the zenith, which is the discrimination wanted.
- **Transients**: NOT peak. Once a limiter is in the chain every window's peak
  clamps to the same value — measured 2.0 dB across all six spot effects, which
  says nothing about any of them.
- The honest fallback for a short effect is to confirm the chain works with a
  bed in the same `amix`, then judge the level by ear. Some things are mix
  decisions, not measurements.

## `pgrep -f` matches the waiting shell's OWN command line, so waiters deadlock

A background waiter written the obvious way:

```zsh
until ! pgrep -f "render.py" >/dev/null; do sleep 20; done
```

never exits — because `pgrep -f` matches against **full command lines**, and this
shell's own command line contains the string `render.py`. One waiter matches
itself; two waiters watching the same job match *each other* and both hang
forever after the job is long gone.

Measured on episode2: the 4K composite finished at 13:55 and three chained
waiters were still sleeping at 13:57, costing ~10 minutes of idle wall clock on a
job that was already done. It presents as "the render is taking ages", which is
the expensive misdiagnosis — you go looking at ffmpeg.

Fixes, in order of preference:

- **Wait on the artifact, not the process.** `until grep -q DONE "$logfile"`, or
  test for the output file. A marker string the job prints on exit cannot
  self-match, because the waiter greps for it rather than containing it as a
  process name. This is what we now use.
- If you must match a process, use the bracket trick — `pgrep -f "[r]ender.py"` —
  the classic `ps | grep` dodge, which works for the same reason.
- `pgrep -f` also matches the `/bin/zsh -c source …snapshot… && eval '…'` wrapper
  the harness builds, so the whole script body is in the matched text, not just
  the command you think you ran.

## `freezedetect` logs at INFO, so `-v error` silently reports zero freezes

Re-running a freeze check with `ffmpeg -v error … -vf freezedetect` prints
nothing and reads as "clean" — the filter emits `lavfi.freezedetect.freeze_start`
as **info-level** metadata, which `-v error` discards. `selfeval.py` gets this
right with `-v info`; a hand-rolled spot check will not.

This is a false *negative*, which is the dangerous direction: it looks like the
defect you were chasing has gone away. Verified on episode2's delivery, where the
same window reported 0 freezes at `-v error` and 9 at `-v info`.

Related: a **black cold open with burned captions produces back-to-back freezes**,
one per caption change, each `freeze_end` exactly equal to the next
`freeze_start`. Nine of episode2's twelve are this. Contiguous freeze spans over
a static background are a caption sequence, not a stuck picture — check whether
the spans butt up against each other before investigating.

## A self-eval probe with a hardcoded timestamp becomes a fake defect when the cut shortens

`selfeval.py` probed "scene 8 speech" at a literal `700.0, 710.0`. That was inside
the 12:55 cut. After the recut to 9:00 it lands **past the end of the file**, where
the slice is empty and the guard returns `-999.0` — printed in the same column as
every real level, and indistinguishable from a scene that lost its audio entirely.

The cost is real: it is alarming, it is the last thing you see before delivering,
and chasing it means re-probing a 2.7 GB file. Anchor every probe to something
that moves with the cut — a segment boundary, the end card, a spoken word — the
same rule already established for graphics and overlays. A probe outside the file
must fail loudly as an error, never quietly as a measurement.

## A SCORED window reads BELOW the naked reference, not above it

The companion to "is the music off in this window?" above. Diffing the mix against
the no-music control per window, the intuition is that a bed shows up as extra
energy. It does not, once the two-pass loudness chain is in place: the mix applies
one global gain and then limits, so **adding a bed gives the limiter more to take
back** and that window's effective gain ends up *smaller* than the global one.

Measured on episode2's delivery (global gain +11.09 dB, matching the mix log's
+11.10 — which is what validates the method):

| window | delta vs the naked reference |
|---|---|
| plain talking head (reference) | 0.00 |
| zenith — must be naked | **-0.19** |
| 20cm chart — unscored | **-0.02** |
| known bed, clock | **-1.21** |
| known bed, mid | **-0.94** |

So read the **magnitude** against a known-naked reference window, and expect
scored windows to sit about 1 dB below it. Reading the sign the obvious way
inverts the conclusion and certifies a scored zenith as clean.

## A killed render loses only the composite — segments and base survive, and resuming is cheap

`render.py` has no skip-extract flag, so the reflex after an interrupted render is
to start it over. On a 9-minute 4K episode that reruns ~18 minutes of per-segment
grading and extraction for nothing.

What a mid-composite kill actually leaves:

- `clips_graded/` — **complete and valid**, every segment already finalised
- `base.mp4` — **complete**, if the concat had finished (check its mtime against
  the newest segment)
- `master.srt` — complete
- the output `.mp4` — **unrecoverable**, no moov atom, `ffprobe` says "Invalid
  data found". Delete it; there is nothing to salvage from a partial mp4.

`episode2/edit/build/resume_render.py` is the pattern: rebuild the expected
segment names **from the EDL** (never glob — stale segments from a previous EDL
live in the same directory), assert every one exists and post-dates `edl.json`,
assert `base.mp4` post-dates the newest segment, then monkeypatch
`extract_all_segments` to return that list and `concat_segments` to a no-op and
call `render.main()`. Everything downstream — subtitles, graphics anchoring,
overlay compositing, captions-last — runs through render.py's own unmodified code,
so the result is what a full run produces.

The freshness assertions are the whole safety argument. Without them this silently
composites a stale picture.

## An externally made motion graphic is opaque, full-frame and fixed-pace — integrate it by pushing and remapping, not overlaying

A graphic made outside this pipeline (here: a 10s 4K `routine_10s.mp4` generated in
a chat session) arrives as a **flat opaque render with its own pacing**. Both
properties break the obvious "put it beside the talking head":

- **Opaque and full-frame.** No alpha, and its layout uses the whole width — its
  payoff ("Every day. For 3 years.") sat at x 0.63-0.93, exactly where the
  speaker's face goes. Overlaying it hides the speaker; shrinking it whole to a
  side panel makes its type unreadable.
- **Fixed pacing.** 10s of reveals against ~59s of spoken routine: played over the
  itemised passage it would show "Tuition" while he says "lunch".

What worked, verified on `episode2/edit/routine_card_demo.mp4`:

1. **Use it as a RECAP, not an illustration.** Enter on "So that was my routine",
   after the b-roll has carried the journey. At that cue its native 10s nearly
   fitted: aligning Sleep (graphic 6.267s) to "sleep" put t=0 at 142.44 — the
   exact moment he says the recap line.
2. **Time-remap with frame holds placed in measured static windows.** Measure each
   element's reveal from region luma, and map where the graphic is animating vs
   still with `tblend=difference` + `signalstats`. Holds (`trim` + `tpad
   stop_mode=clone`) inside a still window are invisible; a hold mid-fade freezes
   a half-drawn element. Here +0.109s and +0.882s put "Every day" on "repeat"
   and "For 3 years" on "three years" exactly.
3. **Crop, don't shrink.** Take the column that carries the content (the list),
   scale by one factor so it fits a half-frame panel, and pad to full height with
   `fillborders mode=smear` — a flat pad colour shows a seam on a gradient.
4. **Split-screen PUSH, one curve for both.** The panel slides in as the talking
   head slides right by the same smoothstep (the pairing rule). Panel right edge
   (960E) stays ahead of the head's left edge (538E) at every E, so no black gap.
5. **Lift type out of an opaque render with a lighten blend.** Crush the
   background to black with `colorlevels`, place on a black canvas, then
   `blend=lighten` — only the type is added. Poor man's alpha, and it works
   because the type is brighter than everything it lands on.
6. **Captions must ride the push** (`\move` in an ASS event, anchored `\an2`),
   or they cross the panel seam or sit off-centre once the panel leaves.

Two traps hit along the way: **`metadata=print` logs at INFO**, so `-v error`
prints nothing — the same false negative as `freezedetect`, and it will be true of
any lavfi `metadata`/`showinfo` probe. And **`bc` drops the leading zero** (`.3`),
which `ffmpeg -ss` rejects; format times with `awk printf "%.2f"`.

The better long-term route is to get the graphic's SOURCE with a transparent
background and rebuild its timing here against spoken words — the flat render
only works because this one happened to have still windows in the right places.
