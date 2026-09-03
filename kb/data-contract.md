# The transcript data contract

**This is the most useful thing in this KB.** The repo looks ElevenLabs-coupled but isn't.
Only `transcribe.py` ever touches the ElevenLabs API. Everything downstream reads a narrow
JSON contract from `<edit>/transcripts/<source_stem>.json`.

## What downstream code actually reads

Verified by reading every consumer (`pack_transcripts.py`, `render.py`):

```json
{
  "words": [
    {"type": "word",    "text": "ninety", "start": 1.60, "end": 1.94, "speaker_id": "speaker_0"},
    {"type": "spacing", "text": " ",      "start": 1.94, "end": 2.40},
    {"type": "audio_event", "text": "(laughter)", "start": 2.40, "end": 3.10}
  ]
}
```

Five fields. That's the whole seam. Everything else in an ASR response is unused.

| Field | Consumed by | Notes |
|---|---|---|
| `type` | both | `"word"` \| `"spacing"` \| `"audio_event"`. `render.py` keeps **only** `"word"` for captions. `pack_transcripts.py` puts `word` + `audio_event` in phrase text. |
| `text` | both | Should carry punctuation — `render.py` breaks caption chunks on trailing `.,!?;:`. |
| `start` / `end` | both | Seconds, float. Missing `start` ⇒ token skipped. |
| `speaker_id` | `pack_transcripts.py` | A `"speaker_"` prefix is stripped for display, so `"speaker_0"` → `S0`. |

## Two behaviours worth knowing

**`spacing` tokens are optional.** `pack_transcripts.py` breaks phrases on silence ≥ 0.5s
via *either* a long `spacing` token *or* `start - prev_end` between kept tokens. The second
path means a provider that emits no spacing tokens still groups phrases correctly.

**Caption timing is Hard Rule 5.** `render.py` computes
`output_time = word.start - segment_start + segment_offset`, where `segment_offset` accumulates
segment durations. Get this wrong and captions drift after concat. It reads
`transcripts/<source_key>.json` where `source_key` is the EDL `sources` key — so **the transcript
filename must match the EDL source name.**

## Consequence: providers are swappable

Anything that yields word-level timestamps can drive this pipeline. Implemented:

| Provider | Helper | Key | Audio events |
|---|---|---|---|
| ElevenLabs Scribe | `transcribe.py` | `ELEVENLABS_API_KEY` | yes — `(laughter)`, `(applause)`, `(sigh)` |
| Deepgram nova-3 | `transcribe_deepgram.py` | `DEEPGRAM_API_KEY` | **no** |

### Deepgram mapping (as implemented)

From `results.channels[0].alternatives[0].words[]`:

| Deepgram | → contract |
|---|---|
| `punctuated_word` (fallback `word`) | `text` |
| `start` / `end` | passthrough |
| `speaker: 0` | `speaker_id: "speaker_0"` |
| *(no discriminator)* | `type: "word"` |
| *(none)* | `type: "spacing"` synthesized for gaps ≥ `--spacing-threshold` (0.05s) |

Request params: `model=nova-3`, `diarize=true`, `punctuate=true`, `filler_words=true`.
`smart_format` is deliberately **off** — it rewrites numbers/dates, which is precisely the
normalization Hard Rule 8 forbids.

`--convert <deepgram.json>` runs the mapping offline with no API call. Use it to test changes
for free.

## Adding a third provider

Write `helpers/transcribe_<name>.py` emitting the schema above. Reuse
`transcribe.py`'s `extract_audio`, `peak_dbfs`, `count_audio_tracks`, `transcript_path` —
import them rather than copying, so the audio front-end can't drift. Keep the
"cached: return early if the output exists" behaviour; transcription costs money.
