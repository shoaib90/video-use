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
