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

| Provider | Helper | Cost | Diarization | Audio events |
|---|---|---|---|---|
| ElevenLabs Scribe | `transcribe.py` | paid | yes | yes — `(laughter)`, `(applause)`, `(sigh)` |
| Deepgram nova-3 | `transcribe_deepgram.py` | paid | yes | no |
| whisper.cpp (local) | `transcribe_whisper.py` | **free** | **no** | no |

**Which to use.** Deepgram is the configured default — it diarizes, which multi-speaker
material needs. Use whisper for free iteration, offline work, or as a cross-check: it has been
seen to preserve a leading filler that Deepgram dropped. Never use whisper alone on
multi-speaker footage — no speaker labels means no `S0`/`S1` tags in `takes_packed.md`, and
speaker handoffs become invisible.

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

### whisper.cpp mapping (as implemented)

`whisper-cli -oj -ml 1` emits one token per segment as
`transcription[].{offsets:{from,to}, text}` with offsets in **milliseconds**. The adapter
divides by 1000, and glues standalone-punctuation tokens (`-ml 1` splits `,` and `.` into their
own segments) onto the preceding word so `text` carries punctuation as the contract expects.
`speaker_id` is **omitted** — `pack_transcripts.py` renders an empty speaker tag when absent,
which is the correct degradation.

Caveats: whisper normalizes some spoken numbers ("ninety percent" → "90%"), against the spirit
of Hard Rule 8, and smaller models make real word errors (`base.en` produced "w usted" for
"wasted"). Prefer `small.en` or better; treat its transcript as a draft surface.

## Adding a third provider

Write `helpers/transcribe_<name>.py` emitting the schema above. Reuse
`transcribe.py`'s `extract_audio`, `peak_dbfs`, `count_audio_tracks`, `transcript_path` —
import them rather than copying, so the audio front-end can't drift. Keep the
"cached: return early if the output exists" behaviour; transcription costs money.
