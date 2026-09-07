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

**Caveat:** one clip, synthetic TTS speech. `say`'s "Um," is a poor proxy for a human one.
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

## Never write inside this repo

Hard Rule 12: all session output goes to `<videos_dir>/edit/`. The scratch/test artifacts from
setup verification live in the session scratchpad, not here.
