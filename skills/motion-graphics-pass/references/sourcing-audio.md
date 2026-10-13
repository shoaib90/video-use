# Sourcing sound effects and music: local library first, then Epidemic Sound

Shoaib's rule (2026-10-13): **every effect and every music bed must be the apt one for its
moment.** If the local library doesn't have it, search the Epidemic Sound connector, download
it, and use it. Never settle for the nearest file on disk.

## 0. Decide what the moment needs before searching

Write one line per sound in the blueprint's SFX column. Each line names three things:
1. **What physically happens on screen.** A slab drops. A ticket tears. A bubble pops. A call
   connects.
2. **Its character.** Heavy or light, dry or roomy, warm or digital, and its length.
3. **Its job.** Felt more than heard (a thud), a transition (a whoosh, at most one per three
   graphics), a list tick, or the episode's single riser.

A paper ticket tearing needs a paper tear, not a generic swish. The house palette rules in
`effects/structural/palette.json` still apply to anything sourced from Epidemic.

For music, the line is the window, the mood and the energy. For example: *"4:43–5:02, tired,
heavy, no melody fighting the voice, 70–80 BPM, fades out under 'so I just quit quietly'"*.

## 1. Local first

```bash
$MGX <edit> library whoosh          # name/tag search across SFX_DIR and MUSIC_DIR
$MGX <edit> library paper tear
$MGX <edit> library                 # everything
```
- **`SFX_DIR`** defaults to `~/Documents/Ambitious/Editing/effects`. It holds:
  - the house palette in `structural/`;
  - the one-off episode SFX at the root;
  - everything fetched before, in `epidemic/<kind>/`, with JSON sidecars.
- **`MUSIC_DIR`** is the sibling `music/` folder (set `MUSIC_DIR` in cues.py to override).
- **A local file is apt only if its title or tags match all three parts of the step-0 line.**
  If it matches only one or two, go to the connector. Episode 2 used the local palette for
  everything, and the paper tear was really a page turn. That is the compromise this rule
  exists to stop.

## 2. Search the connector

The connector's tools are named `…Epidemic_Sound__<Tool>`. In Claude Code they are usually
`mcp__claude_ai_Epidemic_Sound__*`; in claude.ai, `mcp__Epidemic_Sound__*`. Load them with
`ToolSearch("epidemic sound")`.

**If no Epidemic tool exists in the session, say so to Shoaib, use the best local file, and
list the sound as a gap in the delivery message.** Never silently downgrade.

**Sound effects:**
- `SearchSoundEffects`:
  - `query.term`: a short concrete phrase, e.g. "paper ticket tear", "heavy stone slab drop",
    "soft glass ui pop", "phone call connect";
  - `filter.duration`: in milliseconds, e.g. `{"max": 1500}` for UI sounds;
  - `first`: 8–10.
  - Results give `id`, `title`, `tags`, `audioFile.durationInMilliseconds` and a public
    `lqmp3Url` preview.
- `SearchSimilarToSoundEffect(id)`: once one result is close, find its siblings. It is often
  the fastest route to the right one.

**Music:**
- `SearchRecordings`:
  - `query.term` (or `topic`);
  - `filter.vocals: false` for anything under speech;
  - `filter.bpm` `{min, max}`;
  - `filter.moodSlugs` / `taxonomySlugs` / `featuredInstrumentSlugs` (`matchType` ANY or ALL);
  - `filter.duration`.
  - Results give `id`, `title`, `bpm`, tags (mood, genre, vocal type), stems and a preview.
- `SearchSimilarToRecording(id)`: matches the feel of a bed the channel already uses.
- `SearchExternalReferences(term)` → `SearchRecordings(query.externalID)`: Shoaib can name a
  commercial track ("something like X"), and this finds Epidemic music that sounds like it.
  On `RETRY_LATER`, wait `retryAfterSeconds`.

## 3. Audition by measurement (you cannot listen)

Shortlist 2–4 candidates on title, tags and duration. Then measure their previews before
committing:
```bash
curl -sSL -o /tmp/cand1.mp3 "<lqmp3Url>"
```
Measure with the same analysis `fetch` uses (`audio_info` in `mgx.py`):
- the time to the first transient (the hit);
- the total length;
- the spectral centroid. Low means a felt thud; high means bright UI.

For a bed, also check:
- the loudness envelope over the window it must cover;
- that the first 10 s isn't a build that would fight the line it sits under.

**Pick the candidate whose character matches step 0, and say why in the blueprint**
("chose 'Heavy Stone Slab Drop' over 'Rock Impact 3': drier, 0.4 s, centroid 300 Hz, so it
reads as weight").

## 4. Download into the library

- **SFX:** `DownloadSoundEffect(id, {fileType: "WAV"})` returns a signed `assetUrl`.
- **Music:**
  - `DownloadRecording(id, {fileType: "WAV", stemType: "FULL"})`.
  - Use `stemType: "INSTRUMENTS"` (no melody stem) or `"BASS"` when the full track fights
    the voice.
  - To fit a window exactly, use `EditRecording(id, {targetDurationMs, downloadAudioFormat:
    "WAV", forceDuration: true, preferenceRegions: …})`, then `PollEditRecordingJob` until
    COMPLETED, then `DownloadRecordingEdit({jobId, editId})`. The limit is 300 s.

Then fetch it straight away, because signed URLs expire:
```bash
$MGX <edit> fetch "<assetUrl>" --kind paper_tear --id <uuid> --title "<title>" --tags "paper,tear"
$MGX <edit> fetch "<assetUrl>" --type music --kind bed --id <uuid> --title "<title>" --tags "sad,piano,72bpm"
```
`fetch`:
- saves to `effects/epidemic/<kind>/ES_<title>.wav` or `music/epidemic/beds/ES_<title>.wav`;
- writes a sidecar with the Epidemic id, tags, duration, hit time, peak and centroid;
- for SFX, prints the exact `SFX_LIB` line to paste into `cues.py`.

From then on the file is local, so next episode `library` finds it and the connector isn't
needed.

## 5. Place and verify

- **SFX:** add the printed `SFX_LIB` entry, reference the kind in the cue's `sfx=[…]`, run
  `sfx`, and read the audibility report. BURIED means raise it, move it into a pause, or cut
  it (M052).
- **Music:**
  - **The pass's master is already scored.** Beds belong to the episode's own music mix
    (`build/mix_music.py`, levelled per window against the no-music render), not to `mgx.py`.
  - Adding or replacing a bed means re-mixing from `final_nomusic.mp4` with that script, then
    making the motion-graphics pass from the new master.
  - Only an unscored window that `project.md` does **not** mark as deliberate may get a new
    bed from this skill.
  - **The zenith, the post-refusal silence and every "lands in silence" window stay
    unscored, whatever the connector has.**

## Licensing note

Epidemic tracks are cleared for the channel connected to Shoaib's Epidemic account. Keep the
sidecar (it holds the id). If YouTube raises a claim, the id is what clears it. Don't use an
Epidemic file on a channel or platform that isn't connected to that account.
