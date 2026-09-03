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

## Deepgram drops a leading filler word

**Symptom:** input speech "Um, so ninety percent…" transcribed as "So ninety percent…" — the
`Um,` vanished, and the `So` token absorbed its span (0.00–0.72s, unusually long).
A mid-sentence `uh,` in the same clip **was** preserved.

**Confirmed:** live `nova-3` call with `filler_words=true`, 2026-09-03.

**Caveat — not yet proven against real footage.** The test audio was macOS `say` TTS, which
articulates "Um," poorly. A human "um" may well survive. Re-check on the first real clip
before drawing conclusions.

**Why it matters:** cutting fillers is a headline feature. If leading fillers are dropped by the
ASR, they're invisible to the cut logic — they stay in the video. Scribe tags them reliably, so
prefer `transcribe.py` for filler-heavy material if both keys are present.

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

## Never write inside this repo

Hard Rule 12: all session output goes to `<videos_dir>/edit/`. The scratch/test artifacts from
setup verification live in the session scratchpad, not here.
