# Environment — this machine

macOS (darwin 25.6.0), Apple Silicon. Last verified **2026-09-03**.
Re-verify with `bash kb/check-env.sh`.

## Paths

| What | Where |
|---|---|
| Repo / skill | `/Users/fbin-blr-0134/Documents/video-use` |
| Skill registration | `~/.claude/skills/video-use` → symlink to the above |
| Python env | `.venv/` at repo root (uv-managed) |
| Secrets | `.env` at repo root, mode `600`, gitignored |

Registration uses the same symlink pattern as the other skills in `~/.claude/skills/`.
The **whole directory** is symlinked, not just `SKILL.md` — `helpers/` must sit beside it.

## Versions

| Tool | Version | Notes |
|---|---|---|
| ffmpeg / ffprobe | **9.0.1** (`ffmpeg-full`) | libass present ⇒ subtitles work |
| Python | 3.12.13 (uv-managed) | system python3 is 3.9, too old for this repo |
| uv | 0.12.2 | |
| Node | **v26.10.0** (`brew install node`, 2026-10-01) | had silently disappeared (was v24.9.0) — `node -v` before trusting any JS engine row |
| yt-dlp | 2026.08.19 | for URL sources |

### The ffmpeg situation — important

Two formulae are installed. `ffmpeg` (8.1.2, slim, **no libass**) is **unlinked**;
`ffmpeg-full` (9.0.1, keg-only, **has libass**) is force-linked so it owns `$PATH`:

```bash
brew unlink ffmpeg && brew link --force ffmpeg-full
```

Revert with `brew unlink ffmpeg-full && brew link ffmpeg`. Do not "fix" the unlinked
`ffmpeg` — the unlink is deliberate. See [gotchas.md](gotchas.md) for why.

A `brew upgrade` may relink the slim `ffmpeg` and silently break subtitle burn-in. If
captions start failing, re-check `ffmpeg -filters | grep subtitles` first.

## Machines

There are now **two** checkouts, both on `main`:

| Machine | Path |
|---|---|
| primary | `~/Documents/video-use` |
| second  | `~/Documents/Github/video-use` |

Both were set up with [bootstrap.sh](bootstrap.sh) and report green from
[check-env.sh](check-env.sh). The path differs deliberately — nothing is hardcoded to either.

**Consequence: `git pull` before starting work.** Commits made on one machine are not on the
other until pushed and pulled, and there is no longer a single source of truth on disk. Push at
the end of a session.

**What does not sync at all:** `.env` (each machine holds its own copy), the whisper models,
`.venv/`, Claude Code session history, and — the expensive one — **footage and `edit/`
directories**, which live beside the video files rather than in the repo. `edit/transcripts/` in
particular should be copied between machines rather than regenerated, since transcription is paid
per call and those files carry hand corrections. See [new-machine.md](new-machine.md).

## Git

**The remote names differ between the two checkouts. Run `git remote -v` before pushing.**

| Checkout | `origin` | `fork` |
|---|---|---|
| primary, `~/Documents/video-use` | `browser-use/video-use` (upstream) | `shoaib90/video-use` (**ours**) |
| second, `~/Documents/Github/video-use` | `shoaib90/video-use` (**ours**) | not configured |

So `git push origin main` means **opposite things** on the two machines: ours on the second
checkout, upstream on the primary. Upstream is not configured at all on the second checkout,
which is the safer arrangement — there is nothing to push to by accident.

The `pr/*` branches live on **our** fork in both cases (a PR from a fork keeps its head branch
there); what comes from upstream is the commit they are *based* on, not where they are hosted.

This fork is not a mirror. It exists to carry our own changes, so:

- **`main`** — the working branch and this fork's copy of the tool. Carries everything: helpers,
  `kb/`, `CLAUDE.md`, tests, `uv.lock`. **Work here.**
- **`local`** — **deleted 2026-09-20.** It was meant to be a synonym of `main` but nothing kept
  it in step, so it silently fell 16 commits behind while the KB still described the two as
  identical. Verified empty before deleting: `git log main..origin/local` was clean, so every
  commit on it was already in `main`. Do not recreate it; an unmaintained alias is worse than
  no alias.
- **`pr/*`** — the exception. Each is built from **upstream** `main` (`origin/main`), not from
  ours, so the open PRs stay focused and carry no local-only files. Never reuse one of these for
  a PR against the fork: rebasing a shared head branch onto our `main` silently corrupts the
  upstream PR (it grew +82→+295 once). One branch per base — see gotchas.md.

Because `main` is now the working branch, **fork PRs are no longer part of the workflow**; commit
to `main` and push. Fork PRs #1–#4 were how the first three change-sets landed and are history.

Open upstream PRs (all still open as of 2026-09-13):

| PR | Branch | Contents |
|---|---|---|
| [#158](https://github.com/browser-use/video-use/pull/158) | `pr/output-quality` | `--height`, `--crf`, derived gen-2 CRF, numeric `zoom`, `audio_filter` |
| [#159](https://github.com/browser-use/video-use/pull/159) | `pr/configurable-subtitles` | `subtitle_style` (chunking/case/force_style/balance) + sentence-case fix |
| [#160](https://github.com/browser-use/video-use/pull/160) | `pr/deepgram-transcriber` | `transcribe_deepgram.py`, provider/model/language-aware cache |
| [#161](https://github.com/browser-use/video-use/pull/161) | `pr/caption-offset-drift` | caption offsets measured from rendered segments, not summed from the EDL |

**Held back deliberately:** `transcribe_whisper.py`. `SKILL.md`'s anti-patterns list names
"running Whisper locally" explicitly, so upstream is unlikely to want it. Ours runs on Metal in
~4s and serves as a free cross-check rather than the primary — a different proposition, but it
stays ours unless upstream asks.

**Never upstream:** `kb/`, `CLAUDE.md`, `uv.lock`. Machine- and fork-specific.

#158 and #159 both touch `build_final_composite`'s signature and `main()`, so whichever merges
second upstream needs a trivial rebase.

## Credentials

| Key | Status | Used by |
|---|---|---|
| `DEEPGRAM_API_KEY` | **set**, validated (HTTP 200) | `transcribe_deepgram.py` |
| `ELEVENLABS_API_KEY` | **not set** | `transcribe.py` |

Consequence: transcription works, but **audio-event tagging is unavailable** —
no `(laughter)` / `(applause)` / `(sigh)` beat markers. Ask for an ElevenLabs key if a
project needs them.

Never echo key values into tool output. Never write a key anywhere but `.env` at the repo root.

## Animation engines — all three installed

| Engine | Status | Invoke |
|---|---|---|
| Manim | **0.21.0 installed**, render verified | `uv run manim -ql --format=mp4 scene.py Scene` |
| HyperFrames | **v0.8.105**, render verified 2026-10-01 (1013 frames ProRes 4444 in ~14 s capture) | `npx --yes hyperframes ...`; slots pin `hyperframes@0.8.105`. `init` installed 10 skills into `~/.claude/skills/` (hyperframes*, media-use): v0.8.105 prints *"--skip-skills is temporarily ignored"*. `init` also refuses a non-empty directory — init first, then add `work/` |
| Remotion | 4.0.520 reachable, scaffolded per-slot | `npx create-video@latest` |

Manim needed system libs that aren't obvious: `brew install pkgconf cairo pango cmake`, and
`PKG_CONFIG_PATH=/opt/homebrew/lib/pkgconfig` exported, or `pycairo` fails to build.
Repo vendors `skills/manim-video/` — read its SKILL.md before building a Manim slot.

Scaffold Remotion/HyperFrames **inside `<edit>/animations/slot_<id>/`**, never at the repo root.

## Local ASR models

`whisper-cpp` 1.9.2 (arrived with `ffmpeg-full`). Models in `~/.cache/whisper-models/`:

| Model | Size | Use |
|---|---|---|
| `ggml-small.en.bin` | 465 MB | **default** for `transcribe_whisper.py` |
| `ggml-base.en.bin` | 141 MB | faster, but makes word errors — see gotchas.md |
| `ggml-small.bin` | 465 MB | **multilingual**; added 2026-09-16 for the Hinglish cross-check |

`ggml-small.bin` (sha256 `1be3a9b2…fea987b`) came from
`https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin`.
Use it with **`-l en`** on Hinglish — not `-l hi`/`-l auto`, and note that word-level
(`-ml 1`) output is unusable for Devanagari. Both reasons are in gotchas.md.

ffmpeg 9 also has a built-in `whisper` filter (`-h filter=whisper`), unused so far — the
`whisper-cli` path gives cleaner word-level JSON.

## Available beyond the CLI

This runs as the Claude Code **app**, a superset of the CLI the repo targets. Extra reach:
inline file delivery to the user, publishable HTML Artifacts (cut plans, before/after
breakdowns), a separate Remotion skill, Figma/Canva connectors for branded overlay assets,
and scheduled tasks. Parallel animation sub-agents (Hard Rule 10) work via the `Agent` tool —
but **the user asked that it not be used unless they request it**, so confirm before fanning out.

### The youtube-agent plugin (11 skills) — use it, don't duplicate it

Installed as a claude.ai plugin (skills invoked as `/youtube-agent:<name>`). Its files live under a
session-specific path, so find a script with
`find ~/Library/Application\ Support/Claude -name <script>.py -path '*<skill>*'`; never hardcode it.
Verified 2026-10-14 by listing the plugin. Which skills have scripts:

| Skill | Script | Where it fits here |
|---|---|---|
| `yt-shorts` | — | **Picks and writes Shorts**; `skills/shorts` builds them (its SKILL.md step 1) |
| `yt-script` | `hookscore.py` | Ranks opening lines, **relatively only**: every Episode 4 Short hook scored WEAK (21-40) |
| `yt-package` | `title.py` | Lints a title against its thumbnail/plate text; caught a Short title repeating its plate |
| `yt-chapters` | `chapters.py` | Chapters checked against YouTube's rules |
| `yt-retention` | `retention.py` | Reads a Studio retention export (pairs with kb/distribution.md) |
| `yt-viral` | `swipe.py` | Outliers in the niche |
| `yt-edit` | `deadair.py` | Transcript to a dead-air list. **Overlaps video-use's own cut**; the cut stays in video-use |
| `yt-audit`, `yt-plan`, `yt-seo`, `yt-comment` | — | Channel audit, upload plan, description/tags, comment replies |

Channel-specific packaging still goes through `youtube-title-thumbnail-description` (Shoaib's own
skill) and the private channel-kb; `title.py` is a lint on top of it, not a replacement. Only
`hookscore.py` and `title.py` have been run here so far (on Episode 4's Shorts).

## Neural denoising — `helpers/denoise.py`

DeepFilterNet3 runs locally for wind/broadband speech denoising. It cannot live in the repo's
own environment, for two independent reasons (both in [gotchas.md](gotchas.md)): `DeepFilterLib`
0.5.6 has no macOS arm64 wheel above cp311, and DeepFilterNet 0.5.6 needs `torchaudio<2.2`.

| | |
|---|---|
| Env | `~/.cache/video-use/denoise-env` — python **3.11**, ~2 GB |
| Pins | `deepfilternet==0.5.6`, `torch==2.1.2`, `torchaudio==2.1.2`, `numpy<2` |
| Created by | `helpers/denoise.py` on first use, via `uv venv` + `uv pip install` |
| Speed | ~24x realtime on this machine (354 s of audio in 14.6 s, CPU) |
| Models | `DeepFilterNet3` (default) and `DeepFilterNet2`, auto-downloaded on first run |

The helper shells out to that interpreter the same way it shells out to ffmpeg, so nothing in
the repo's 3.12 env ever imports torch.

**SpeechBrain was evaluated and rejected** for this job — `metricgan-plus-voicebank` and
`mtl-mimic-voicebank` both scored *worse than the existing `arnndn` chain* on real footage, and
both are 16 kHz models. Numbers in gotchas.md. Not installed.

## Voice cloning — Voicebox (piloted 2026-11-06, uninstalled 2026-11-07, reinstalled 2026-11-09)

**Reinstalled 2026-11-09 for a faceless channel's narration, not for Shoaib's voice.** v0.5.0 `Voicebox_0.5.0_aarch64.dmg` from GitHub
releases (538 MB; `spctl`: Notarized Developer ID, James Pine YB4V2VA9YY) → `/Applications/Voicebox.app`. Only **Kokoro 82M** is
downloaded (312 MB, `hexgrad/Kokoro-82M`); Chatterbox is not. Kokoro has built-in **Hindi presets** with no reference audio needed:
`hm_omega`, `hm_psi` (male), `hf_alpha`, `hf_beta` (female). Make a profile with `POST /profiles`
`{"voice_type":"preset","preset_engine":"kokoro","preset_voice_id":"hm_psi","language":"hi","default_engine":"kokoro"}`,
then `POST /generate` with `"engine":"kokoro","language":"hi"`. **Generate one sentence per call** (gotchas.md). Scripts:
`<scratchpad>/kokoro_sentences.py` pattern; samples in `~/Documents/Ambitious/Editing/faceless-shorts/voice-samples/`.

[jamiepine/voicebox](https://github.com/jamiepine/voicebox) v0.5.0, piloted and then **uninstalled on 2026-11-07** (Shoaib's OK,
after two failed likeness tries): app, its 3.0 GB Chatterbox model, `~/Library/{Application Support,Caches,WebKit}/sh.voicebox.app`
all moved to the Trash. The table below is what was there. Even if used, a clone is for table-reads only, never a published cut
(channel-kb "authentic first"). Quitting the app leaves `voicebox-server` running on 17493; it must be killed separately.

| | |
|---|---|
| App | `/Applications/Voicebox.app` (528 MB), notarized Developer ID, James Pine. Must be running for the API |
| API | `http://127.0.0.1:17493` (`/docs`, `/openapi.json`); MCP at `/mcp`, **not** added to Claude Code |
| Model | Chatterbox Multilingual only, 3.0 GB in `~/.cache/huggingface/hub/models--ResembleAI--chatterbox` |
| Profiles | "Shoaib (pilot)": 14 s of Episode 5 IMG_3962. "Shoaib (final cut 4.6 min)": Episode 5 final Scenes 6-7 (EDL ranges 94-191), 11 samples |
| Pilot | `Editing/episode5/edit/voicebox-pilot/` (`listen.html`, `build/vb_*.py`): kept, 43 MB |

**Shoaib's verdict (by ear): it does not sound like him, twice.** 2026-11-06 from one 14 s sample (closest: Devanagari + `language: "hi"`);
2026-11-07 again from 4.6 min of the Episode 5 final in 11 samples, which fixed pace and dropped lines but not likeness. A longer reference
cannot help much (Chatterbox voices from its first 10 s, below), so the engine is the limit. **Don't retry Voicebox/Chatterbox for his voice.**

What the pilot measured (whisper `small.en` + `small -l hi` on every output):
- **It reads far faster than Shoaib**: 220-290 wpm against his ~161 (the same football line: 5.0 s cloned, 7.8 s real). Don't time a
  script from a clone; word count / 161 wpm stays the method (channel-kb playbook).
- **Hinglish works best as Devanagari with `language: "hi"`**: whisper heard "मडलब हो गया यही तो करना था" and "ठीक है दरद होगा तो देख लेंगे".
  Romanised Hindi with `en` comes out anglicised ("Matlab Hogaia, Yajito, Karnada").
- **It drops and repeats lines on long text**: a 122-word scene lost its last sentence; another repeated a sentence at 27.5 s (both whisper
  models agree). Generate one sentence or line per call and whisper-check each.
- **And a single sentence can run on into mumble**: "I was going to start making videos." spoke 2.4 s, then ~4 s of non-speech at -30 to -20 dB.
  Whisper's wording was perfect, so check the tail too (clip length minus whisper's last segment end; reseed over 0.6 s).
  `voicebox-pilot/build/vb_scene_fix.py` does both; 2 of 11 sentences needed a second seed.
- **Pick the language per sentence**: `hi` on an English sentence gives it a Hindi accent (whisper heard "I" as "he" in 6 of 7).
  `hi` only where the sentence has Devanagari.
- **Reference: samples cap at 30 s each, but a profile joins all its samples** (`combine_voice_prompts` concatenates them). Chatterbox then
  takes only the first **10 s** for the voice itself and 6 s for its prompt (mlx-audio `DEC_COND_LEN`/`ENC_COND_LEN`); the rest feeds only the
  speaker embedding. So a long reference must open on its cleanest 10 s. The 4.6 min reference brought pace to 166-216 wpm (14 s ref: 220-290).
  The MLX backend hard-codes `exaggeration` 0.1 (flat delivery); the API cannot change it.
- `/transcribe` returns text only, no word timings; it cannot replace Deepgram (data-contract.md).

## Obsidian + kepano/obsidian-skills (installed 2026-11-10)
- `/Applications/Obsidian.app` v1.15.0, from GitHub `obsidianmd/obsidian-releases` (`Obsidian-1.15.0.dmg`, 233 MB; `spctl`: Notarized
  Developer ID, Dynalist Inc. 6JSW4SJWN9).
- Skills copied to `~/.claude/skills/`: obsidian-markdown, obsidian-bases, json-canvas, obsidian-cli, defuddle, knap (repo commit 3ccff53,
  MIT; Markdown-only, reviewed). defuddle and knap need `npm install -g defuddle|knap` on first use (not installed). obsidian-cli needs the
  CLI enabled in Obsidian's settings (not done).
- Vault: the faceless channel's vault under `~/Documents/Ambitious/Editing/faceless-shorts/` (exact path in Claude's private memory; registered in
  `~/Library/Application Support/obsidian/obsidian.json`).
- Computer-use: Screen Recording granted 2026-11-10. Obsidian (Electron) refuses background clicks while its window is on another Space,
  and it can't be moved into a full-screen Space, so ask Shoaib to leave full-screen first. Obsidian re-saves `.base` files in its own
  YAML style (it drops quotes), so re-read before editing. Datetime properties show 12-hour time with AM/PM clipped in narrow columns:
  use a `format("ddd D MMM, h:mm A")` formula column.
