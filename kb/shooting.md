# Shooting: the camera and lighting setup for indoor talking heads

What gets decided **before** the edit: phone settings, light placement, the set. The edit can't fix
a face that was lit badly, and a grade belongs to the setup it was shot under (gotchas.md, "The
tone-map moved to npl=203 + mobius…"). Verified on an iPhone 17 Pro in the home office,
2026-10-09 to 2026-10-11, from test clips IMG_3632–IMG_3838 compared frame by frame.

## The locked setup (IMG_3838, 2026-10-11)

| | Setting | Why |
|---|---|---|
| Lens | **2x** (the 1x wide distorts hands and shows more bright wall) | IMG_3833 (2x): face **brighter** than the frame mean (112 vs 106); IMG_3836 (1x): face darker than the frame (113 vs 128), because more lit wall is in shot |
| Resolution | **4K 30 fps** | IMG_3838 (4K, ~26 Mbps) vs IMG_3837 (1080p, ~13.5 Mbps), same setup: hair strands and beard texture survive only in 4K. YouTube also gives 4K uploads a better encode at every playback size |
| HDR | Either. `render.py` tone-maps HLG correctly | Off is simpler: what the phone shows is what ships. On is fine as long as render.py's `is_hdr_source()` path runs |
| Exposure | **AE/AF lock on the face** (long-press), nudge exposure up slightly | With 2x and 4K a focus miss shows, and the lock stops a lean-back from refocusing on the monitor |
| Key light | One panel, **diffused** (softbox, or bounced off a white board), **~45° to one side, just above eye level, ~1 m** | A bare small panel is a hard source: specular shine on forehead, nose and cheekbone. Too high puts the eyes in shadow ("raccoon eyes") |
| Second light | **Not** a second frontal light. Either a rim/hair light behind, high, low power, opposite the key; or none, with a white board low on the shadow side as fill | Two equal frontal lights flatten the face (IMG_3834 was the flattest of five tests) |
| Monitor | **Off or dark**, or ~20–30% brightness with a dark, cool wallpaper | Monitor on (IMG_3666) vs off (IMG_3686), same frame region: face ~10% darker with it on (approximate: head position differed slightly between takes), because auto-exposure protects the bright rectangle. A warm orange wallpaper beside warm skin also muddies the skin |
| RGB / lamp | Accents only, ~20–30%. Purple on the wall, never on the face | Purple spill on the cheek reads as a colour cast |
| Wardrobe | **Mid-tone or dark, plain** (navy polo, IMG_3837/3838) | A white tee is the brightest thing in frame and pulls exposure down; a saturated red jersey pulls the eye and clips (gotchas.md: red clipping) |
| Skin | Blotting sheet or mattifying powder before rolling | Shine stays visible even under a diffused key, more so in 4K |

## Checking a test clip before a real shoot

Record 10 s, then compare against the last good setup with the same frame region:
- **Face mean luma ≥ frame mean** (the face should be the brightest skin in the frame).
- The shadow side of the face falls off gently; eye sockets are not black.
- `helpers/exposure.py` on a tone-mapped frame: p5 ≥ 20, red clipping < 0.5%.
- Look at it at feed size (~320 px wide): is the face still the first thing you see?

## Framing for Shorts cut from long videos

A 9:16 crop of a 16:9 4K frame is 1215 px wide at full height: **keep the head and hands inside
the centre third** while shooting, or the vertical crop cuts the gestures. Hands drifting to the
frame edges is the most common loss.
Verified on the Episode 4 Shorts (2026-10-14): the face held at 49-52% of frame width in every
range, so the crop never had to chase it. The open-palm gestures still left the 9:16 window.
