# Architecture

## The core idea

Naive video+LLM: dump 30,000 frames, ~1,500 tokens each, 45M tokens of noise.
video-use instead builds **two reading layers**:

- **Layer 1 — audio transcript (always loaded).** One ASR call per source yields word-level
  timestamps + speaker diarization. All takes pack into a single ~12KB `takes_packed.md`.
  This is the primary surface the cut is reasoned over.
- **Layer 2 — visual composite (on demand).** `timeline_view.py` renders a filmstrip +
  waveform + word-label PNG for a time range. Pulled only at decision points: ambiguous
  pauses, retake comparison, cut-point sanity checks, and self-eval.

Same principle as browser-use handing an LLM a structured DOM instead of a screenshot.

## Stages

1. **Inventory** — `ffprobe` each source; `transcribe_batch.py` the directory;
   `pack_transcripts.py` to build `takes_packed.md`; sample a couple of `timeline_view`s.
2. **Pre-scan** — one pass over the packed transcript noting slips, mis-speaks, phrasings to avoid.
3. **Converse** — describe the material in plain English, ask questions shaped by what's
   actually there. No fixed checklist.
4. **Propose strategy** — 4–8 sentences. **Wait for explicit confirmation.**
5. **Execute** — write `edl.json`; drill into `timeline_view` at ambiguous moments; build
   animations in parallel sub-agents; grade per-segment; compose via `render.py`.
6. **Preview** — `render.py --preview`.
7. **Self-eval** — run `timeline_view` on the *rendered output* at every cut boundary (±1.5s).
   Check: visual jump, waveform spike (audio pop), subtitle hidden behind overlay, overlay
   misalignment. Also sample first 2s, last 2s, 2–3 midpoints. Cap at 3 passes, then report
   honestly rather than looping.
8. **Iterate + persist** — natural-language feedback, re-render, append to `project.md`.

## Why each artifact exists

| Artifact | Purpose |
|---|---|
| `transcripts/<name>.json` | Cached raw ASR. Expensive to produce — never regenerate blindly. |
| `takes_packed.md` | Phrase-level view at ~1/10 the tokens of raw JSON. The reading surface. |
| `edl.json` | The cut decision, as data. Cheap to edit and re-render. |
| `clips_graded/seg_NN.mp4` | Per-segment extracts w/ grade + fades. Enables lossless concat. |
| `master.srt` | Output-timeline captions (offsets already applied). |
| `verify/*.png` | Self-eval evidence. |

## Rendering internals

`render.py` deliberately does **per-segment extract → concat**, not one big filtergraph:

1. Extract each EDL range, applying the grade and 30ms in/out audio fades per segment.
   One output frame rate is resolved for the *whole* render (explicit `--fps`, else the first
   source's rate) because `-c copy` concat requires all segments to share a rate.
2. Lossless concat via the concat demuxer (`-c copy`) → `base.mp4`.
3. Composite overlays (PTS-shifted with `setpts=PTS-STARTPTS+T/TB`), then **subtitles last**.
4. Two-pass loudnorm to −14 LUFS / −1 dBTP / LRA 11 (disable with `--no-loudnorm`).

The concat-frame-rate constraint is the subtle one: mixing a 30fps and a 60fps source in one
EDL without `--fps` would otherwise break the concat.
