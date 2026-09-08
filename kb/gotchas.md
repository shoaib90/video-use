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

---

## Never write inside this repo

Hard Rule 12: all session output goes to `<videos_dir>/edit/`. The scratch/test artifacts from
setup verification live in the session scratchpad, not here.
