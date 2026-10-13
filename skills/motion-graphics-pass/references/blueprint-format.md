# Blueprint format (Shoaib's spec)

Write `<edit>/motion_graphics_blueprint.md` in this shape. Shoaib's brief is that the video is
at **picture lock**: no re-editing, trimming, rearranging or runtime changes. The work is an
overlay motion-graphics layer that lifts engagement, anchors abstract ideas visually, and holds
retention without overwhelming the frame. The reference styles are Vox, Johnny Harris and Ali
Abdaal.

## Header: fill these in from the project, don't ask for them
- **Topic / niche**
- **Target audience & tone**
- **Total runtime**: measured from the master
- **Visual style**: Minimalist & Modern / Paper & Analog Collage / High-Tech & Clean UI /
  Cinematic Documentary. The channel's house look is Minimalist & Modern glass (the routine
  card, the locators).
- **Brand colours / fonts**: from `brand.json` or the existing cards. Say where you took them
  from.

## Design principles the plan must satisfy
1. **Purpose-driven motion.** Each graphic either (a) clarifies an abstract concept,
   (b) emphasizes a high-impact punchline or thesis, or (c) resets attention during a
   talking-head stretch longer than 4–6 s.
2. **Cognitive load control.** Graphics never compete with speech. When dense information is
   spoken, the graphic simplifies rather than adding noise.
3. **Professional animation mechanics.** Real easing (ease-in/out, overshoot, smooth
   damping), spatial placement (rule of thirds, face and eyes clear), and clean in/out
   transitions.
4. **Audio synergy.** Every visual pop or transition has a paired SFX cue, and that cue must
   be audible (see the audibility report).

## The table, chronological, one row per cue

| Timestamp (In - Out) | Spoken Line / Scene Context | Motion Graphic Concept & Placement | Animation Details (In / Hold / Out & Easing) | Paired SFX Cue |
| :--- | :--- | :--- | :--- | :--- |
| 00:04 - 00:07 | "Most people get this completely backwards." | Kinetic type: "COMPLETELY BACKWARDS" flips 180°, lower-third right. | Scale 0→105→100% (cubic-bezier ease-out). Holds 1.5 s, dissolves via horizontal blur. | Low sub-drop on the pop, crisp whoosh on the exit. |

Rules for rows:
- Timestamps are output time, anchored to word onsets.
- Say when a row **replaces a caption cue**.
- Mark deliberate rests and holds as rows too ("NONE — the zenith").

## After the table
1. **Asset checklist.** Shapes, icons and illustrations to build; copy to write; SFX to
   source. Say what already exists (built cards, renders, library sounds).
2. **Pacing review.** Graphics density per minute. Flag the stretches that are too sparse and
   the ones that are over-saturated, with what to cut first if a stretch feels heavy.
