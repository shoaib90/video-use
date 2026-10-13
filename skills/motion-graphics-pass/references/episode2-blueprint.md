# Episode 2 — Motion Graphics Blueprint
"I Gave Up My Biggest Dream at 15" · `final.mp4` · 3840×2160 · 29.97 fps · **9:00.37** · picture locked

Timestamps are output time in `final.mp4` and come from `master.srt` (caption drift −0.008s). Anchor each graphic to its **spoken word**, the same way your pipeline already anchors overlays, not to the raw number.

## Brief (filled in from the project)
- **Topic:** personal story / personal development. Season 1 origin arc, Ep 2.
- **Audience & tone:** ambitious young Indians, students and early-career people. Grounded, intimate, honest; a big-brother voice, not a guru.
- **Style:** **Minimalist & Modern**: frosted-glass UI cards with documentary restraint. This extends the language you already built (routine card, locator cards, speed badge) instead of introducing a new one.
- **Brand tokens (taken from `animations/cards/routine`):** white `#FFFFFF` · cream `#DED3BD` · muted `#8A8375` · accent `#F25435` · glass `rgba(20,20,22,0.55)` + 24px backdrop blur, 28px radius. Type: Helvetica Neue Bold / Medium / Regular (the `HN-*.ttf` files already in `animations/slot_glass_routine/fonts`), sentence case.

## Global rules
1. **Safe zones, measured on your frame.** Your face sits at x 41–54%, y 29–58%; hands come up to x ~31% below y 62%; captions burn at y 80–88%, centred.
   - **Primary zone = left third** (x 4–26%, y 18–62%). It's the mirror and purple wall, which your session 1 notes measured as the calmest part of the frame.
   - **Top-right** (x 70–96%, y 3–12%): locators and stats. This is where your locator cards already go.
   - **Top-centre** (x 42–68%, y 3–9%): over the dark poster, above the cap. Only the call pill goes here.
   - Never put anything in the lower-centre band.
2. **When a punchline gets kinetic type, that type replaces its caption cue.** Episode 1's bug was a graphic and a caption saying the same words at the same moment. Where a row says "replaces cue N", drop that cue from `master.srt` for the duration. Everywhere else, graphics carry information that **isn't** spoken (years, icons, Hinglish voices).
3. **Build path (runtime and cut unchanged):** HyperFrames comps like your routine card, rendered to ProRes 4444 at 3840×2160. Add them to `edl.json` `overlays`, then re-composite with `resume_render.py`. Captions burn on top, as with the speed badge.
4. **Easing tokens (GSAP / AE):**
   - `in-soft` power3.out ≈ cubic-bezier(0.22, 0.61, 0.36, 1)
   - `out-soft` power2.in ≈ cubic-bezier(0.55, 0.09, 0.68, 0.53)
   - `pop` back.out(1.6) for 5–8% overshoot
   - `slap` power4.out at 0.18s
   - `stamp` is a hard cut: no ease.
   - Default timings: in 0.35–0.45s, out 0.25–0.35s. Exits are always faster than entries.
5. **Graphic whites at 92%** (`#EBEBEB` on glass). The grade is tone-mapped HLG, so pure white glares.
6. **SFX levels:** UI ticks at −24 to −28 dB; transitions at −18 to −22 dB; punches (stamp, thud) at −14 dB. **Silent windows stay silent:** the 20 cm window, the zenith, and the post-refusal silence after 7:00.
7. **Motifs that pay off later** (build each asset once and reuse it):
   - Stamp "I can't fail." (3:14) → "It's okay to fail." (7:28)
   - Quote marks “responsible” (0:09 → 5:10)
   - Lone dot (3:16) → two dots (8:07)
   - Confidence meter: empties at 3:43, refills at 8:43
   - Weight slab (3:09 → 4:15)

## Blueprint

| Timestamp (In - Out) | Spoken Line / Scene Context | Motion Graphic Concept & Placement | Animation Details (In / Hold / Out & Easing) | Paired SFX Cue |
| :--- | :--- | :--- | :--- | :--- |
| 00:00.0 – 00:03.4 | "Is there something you used to love that you gave up?" (cold open, black) | Editorial kinetic type, centred (black frame, nothing to protect). HN Medium 120px; "gave up" in accent. **Replaces cues 1–2.** | Each word rises 24px + fades, 0.45s `in-soft`, landing on its spoken onset (≈60ms stagger). Hold to 3.4s. Out 0.3s fade + 8px blur. | Room-tone swell; one felt sub "thump" (−20 dB) on "gave up". |
| 00:03.9 – 00:11.6 | "Not because you stopped loving it… someone convinced you it wasn't the responsible choice." | Same type system, two lines. On "responsible", two cream quote marks drop around the word: “responsible”. This is the irony the episode unpacks. **Replaces cues 3–5.** | Lines as above. Quote marks y −40→0, scale 1.3→1, `pop`, 0.35s, 4-frame offset between them. Hold 1.2s after "choice". Blur-dissolve out 0.35s. | Two dry paper clicks on the quote marks (−22 dB). |
| 00:12.6 – 00:22.1 | "…thirteen years ago, I did it… to tell this story honestly." | Hairline timeline across mid-frame (y 60%), drawn right→left: "2026" tick, 13 minor ticks, "2013" on the left (**check the year**). The years aren't spoken, so nothing duplicates the caption. | Stroke draw 1.6s power2.inOut, starting on "thirteen"; ticks pop at 30ms stagger; "2013" fades with 6px rise. Hold to "honestly". Out 0.4s fade. | Short reversed tape "zip" under the draw (−24 dB). |
| 00:22.5 – 00:25.3 | TAGLINE card "Become Someone You're Proud Of" | Swap the plain crossfade for the per-word wipe you preferred in Ep 1. Byline "— Shoaib Khan" in muted. Same 3.0s source, so nothing downstream moves. | Soft-edge mask L→R per word, 0.4s `in-soft`, 120ms stagger. Byline fades 0.3s at +1.2s. Out on the existing cut. | Low tonal brand hit + air whoosh on the first word (−16 dB). |
| 00:25.6 – 00:29.2 | Speed badge (existing) | Keep as built. | — | (existing) |
| 00:29.3 – 00:35.0 | "…the day I quit cricket. But let me correct myself." | Glass pill top-left: **Episode 1 · "The day I quit cricket"**. On "correct", a hand-drawn accent strike crosses "The day" and **"The year"** writes in above it. Pair with a YouTube i-card to Ep 1. | Pill x −24→0 + fade, 0.4s `in-soft`. Strike path 0.25s power2.in (fast and decisive). New word: 12px rise, 0.3s. Hold 1.5s. Out −24px + fade, 0.3s `out-soft`. | UI tick on entry; marker "scritch" on the strike (−18 dB). |
| 00:36.0 – 00:43.3 | "…a clean, clear moment… but it was much messier than that." | Left third: one straight 4px hairline draws on "clean, clear"; on "messier" it tangles into a looping scribble knot. No text. | Draw 0.6s power2.out. Morph to scribble 0.8s power2.inOut at "messier". Hold 0.8s. Out scale 0.95 + fade, 0.3s. | Pencil glide on the draw; quick scribble scratch on the morph. |
| 00:45.8 – 00:52.3 | "…being made quietly for over a year… regarding my family." | The knot dissolves into a row of 12 dots (months), and they fill grey→cream one by one: a quiet decision accumulating. | 12 × 0.35s fills, linear and deliberately unhurried, no overshoot. Out 0.4s fade on "family". | Near-subliminal soft clock tick per dot (−28 dB). |
| 00:52.6 – 00:55.9 | "I was six, maybe seven, second or third standard." | Locator top-right in your existing style: **Gandhinagar, 2004** (from your session 1 plan; this information isn't spoken). | Fade + 8px rise, 0.35s power2.out. Hold 2.6s. Fade out 0.3s. | Soft UI tick (−22 dB). |
| 01:03.9 – 01:05.7 | "…we used to bet five rupees." (kids b-roll) | Small ₹5 coin illustration flips in over the dusty ground, lower-right of the b-roll (x 72%, y 62%), above the caption line. | y +60→0 with a 2-turn rotateX flip, 0.6s power2.out, settling with a back.out(2) wobble. Leaves with the cut. | Coin "ting" layered just under your existing catch SFX. |
| 01:12.4 – 01:19.4 | "…I was also a very good football player… but nothing came closer to cricket." | Left third: two bars labelled with icons only (football / bat). Football fills to ~75%. Cricket passes 100% and runs off the card edge. | Football 0.6s `in-soft` on "football"; cricket 0.9s `in-soft` on "cricket", clipped at the edge. Hold 1.0s. Bars retract 0.3s `out-soft`. | Soft rise on the cricket bar, tiny pop at the overflow. |
| 01:21.0 – 01:23.6 | "It wasn't just a hobby for me. It was closer to religion." | Kinetic type, left third: "hobby" (muted) is struck; **"religion"** lands below in white bold with a cream underline. **Replaces cues 35–36.** | "hobby" fades 0.25s, strike 0.2s. "religion" scale 108→100% + fade, 0.35s `pop`; underline draws 0.3s. Hold 1.2s. Blur out 0.3s. | Low reverb boom (−18 dB). Avoid a temple bell; it's a cliché. |
| 01:28.1 – 01:33.0 | "…my father enrolled me into an academy… fourteen, fifteen kilometers away." | **Replaces** the "The academy, 15 km away" locator with a route in the left third: Home ● — 15 km — ● Academy, a dot travelling the line. On "Till two PM" it folds up into the routine card's spine. | Line draw 1.0s power2.inOut; traveller 1.6s sine.inOut; "15 km" fades in at the midpoint. Fold into the card header 0.5s power3.inOut. | Soft whoosh following the dot (−22 dB). Your cycle and bus SFX come later. |
| 01:33.2 – 02:34.9 | The routine: "Till two PM school…" → "…on repeat for almost three years… where everything else" | **Your built routine card** (`animations/cards/routine`). It's in `edl.json` since 1 Oct but **not in `final.mp4`**. Top-left glass card; rows land on their words; 40°C and Heavy kit bag chips; "Every day" tag; footer "On repeat for 3 years". It stays over the b-roll montage because it's the spine. | As built: rows 0.4s `in-soft`, list scroll power2.inOut. Exit on "where everything else": 40px up + fade, 0.4s `out-soft`. | Your clock bed carries this. Add a −26 dB UI tick per row so each landing is felt rather than heard. |
| 02:24.6 – 02:29.1 | "I didn't had anything left in terms of energy. So sleep." | Inside the card: a battery glyph next to "Sleep" drains from green to accent; the red dot pulses once on "sleep". | Battery 100→5% over 2.5s power1.in. Dot pulse scale 1→1.4→1, 0.5s sine.inOut. | Descending power-down tone (−22 dB). |
| 02:42.3 – 02:48.4 | "No one in my family had a formal education… I was the first one…" (A-roll → STILL_SCHOOL) | Left third: three rows of small grey dots (generations). One dot on the last row lights accent with a ring. Over the still, it sits in the black margin. | Rows fade up 0.3s, 90ms stagger. "First" dot scale 0→120→100%, back.out(1.7), on "first one"; ring expands 0.6s power2.out. Out 0.4s at the end of the still. | Single soft pluck on the lit dot (−20 dB). |
| 03:02.4 – 03:12.6 | "…everyone had high hopes and expectations, and I took those hopes and turned it into something heavier than it needed to be." | **Weight motif #1.** A glass tile reading "Hopes" floats in the left third from "high hopes". On "heavier", a dark slab drops onto it and it sinks 60px, squashing slightly. | Tile drifts 2px (sine yoyo). Slab y −200→0, 0.35s power3.in; impact squash scaleY 0.94→1, 0.25s elastic.out(1, 0.5); tile sinks 60px, 0.6s power2.out. Out 0.4s fade. | Heavy muffled thud with sub (−14 dB), the first real punch. |
| 03:14.4 – 03:16.4 | **"And I told myself that I just can't fail."** (the thesis) | **Stamp:** "I can't **fail**." on two lines, HN Bold, left third, "fail" in accent. **Replaces cue 85.** This sets up the payoff at 7:28. | **Hard cut in** (a stamp, not an animation); 2-frame 3px shake. Hold to the cue end + 0.3s. Hard cut out. | Dry, close stamp / door-slam thud, then nothing. |
| 03:16.3 – 03:29.2 | "There was no one to come and tell me… no one to put a hand around my shoulder…" | **Intentional rest.** Only one small grey dot appears in the left third, with a wide empty ring of space around it, alone. Setup for 8:07. | Fade in 0.8s sine.inOut, no motion. Fades at the STILL_ALONE cut. | None. The silence is the point. |
| 03:34.2 – 03:45.3 | "…more fearful, more negative about life… very shy kid with zero confidence." | Label chips slapped onto a stack in the left third, using your `stamp_test` cards: Fearful · Negative · Shy. Then a **Confidence** meter empties to 0 in accent. **Suppress cues 95–97** while the chips are up. | Each chip on its word: scale 115→100% + rotate ±2°, 0.18s `slap`. Meter 60→0%, 0.8s power2.in, on "zero". Hold. | Rubber-stamp thunk per chip, pitch stepping up; drain sweep on the meter. |
| 03:45.4 – 03:51.6 | "And underneath all of that fear was still a kid who loved cricket…" | The chip stack slides down and away, revealing a small cricket-ball **glyph** glowing cream underneath. Use a glyph, not the photo; the photograph stays withheld until 5:03. | Stack y +120 + fade, 0.6s power2.in, 60ms stagger. Glyph scale 0.9→1 + glow, 0.8s sine.out. Out 0.5s on "world". | Warm pad swell / reversed cymbal into the reveal. |
| 03:51.7 – 04:13.5 | "First year, I handled both studies and cricket… eighties… coach used to back me… ninth grade… sixty, sixty one percent" | Left third: two vertical bars, Studies and Cricket, both high, labelled "80s". On "sixty", the Studies bar drops while a rolling counter ticks 80→61 and it turns accent; Cricket stays tall. **Keep** the existing "Ninth standard" locator top-right. | Bars rise 0.7s `in-soft`, 120ms stagger. Drop 1.0s power2.inOut with a digit roll; colour tween at the same time. Hold through "tenth boards". Out 0.3s before the classroom b-roll. | Soft rise on the bars; descending tonal dip + counter ticks (−24 dB). |
| 04:14.8 – 04:18.8 | "And in India, tenth board carry a specific weight." | **Weight motif #2:** a slab labelled "Class 10 boards" drops onto the Hopes stack (the 3:09 asset). | Same drop spec, smaller impact. | Thud, 3 dB under the first. |
| 04:19.1 – 04:34.2 | "…relatives and everyone started to tell me… millions of children playing the game… focus on your studies…" / "That started to mess with my head." | The relatives' voices as speech bubbles crowding the frame edges (left, top-left, top-right), never the face: *"Padhai pe dhyan do"* · *"Lakhs of kids play cricket"* · *"Boards hai is saal"* · *"Cricket se kya milega?"*. They're Hinglish and not his words, so they don't duplicate the caption. On "mess with my head", every bubble jitters and blurs, then they collapse. | Each bubble scales 0→105→100% from its tail, `pop`, 0.3s. Spacing starts at 0.9s and accelerates to 0.5s (pressure). "Mess": 3px random jitter at 12fps + blur 0→6px over 0.6s. Collapse scale→0, 0.25s power3.in. | Muffled crowd-murmur bed building −26→−20 dB, soft pop per bubble; the murmur hard-cuts on the collapse. |
| 04:34.3 – 04:42.8 | "My father, to his credit, told me… that I should continue." | One bubble remains: warm cream, tagged "Papa": **"Continue."** Calm, in the left third. It keeps the family from reading as uniformly against you, which is why you kept the line. | Fade + 10px rise, 0.5s sine.out (gentle, no overshoot). Hold to the cue end. Fade 0.5s. | One warm piano note (−22 dB). |
| 04:54.0 – 05:02.2 | "…doing good at school and then doing good at cricket as well. So there was no rest in between." | Left third: horizontal strip of alternating School / Cricket blocks whose gaps shrink to zero on "no rest". | Blocks slide in 0.3s each. Gap shrink 1.2s power3.in, ending on "rest" with a 1.02 squash. **Hard cut out at 5:02.3**, so "So I just quit quietly" and the photo land naked. | Ticks accelerate, cut dead on the squash. |
| 05:09.9 – 05:12.5 | "I just accepted that it was the responsible thing to do." | **Callback to 0:09:** “responsible” with the same cream quote marks, left third. **Replaces cue 131.** | Word fades 0.3s; quotes drop exactly as at 0:09. Hold 1.2s. Blur out. | The same two paper clicks. The repetition is the callback. |
| 05:24.5 – 05:27.4 | "…I was one fifty centimeter something…" | Height ruler, left third: vertical scale 130–180 cm, marker at 150. **Hides** during the height-chart b-roll (5:27.5–5:29.7) so it doesn't compete with the real tape. | Ruler draws bottom→top 0.6s power2.out; marker slides to 150 in 0.4s. Leaves with the cut. | One dry tick only. This window is deliberately unscored. |
| 05:29.7 – 05:42.1 | "…I grew by twenty centimeter… one seventy… I only found out once I stopped." | Ruler returns; the marker rises 150→170 with a rolling cm counter, a "+20 cm" bracket, and an "in 1 year" label. Your **`GFX_GROWTH.mov` is already built for this**; re-anchor it to "twenty". | Rise 1.4s power2.inOut; bracket draws 0.4s; label fades 0.3s. Hold. **Hard cut out on "stopped."** | One soft tick at 170 and nothing else. Keep the silence. |
| 05:43.1 – 05:48.6 | "After that, I didn't watch a single cricket match for next three years…" (TV-off b-roll) | Small stat card top-right over the dark room: **Matches watched** with three columns (Year 1 · Year 2 · Year 3), each reading 0. | Card fades 0.35s; zeros count in at 0.2s stagger. Hold to the cut. | CRT power-off blip that matches the TV shot (−20 dB). |
| 05:54.6 – 05:58.5 | "That was the first year of my college…" (+ STILL_HOSTEL) | Locator top-right: **First year of college, 2016**. This is your `g03`, built but never used. | Existing locator spec. | Soft UI tick. |
| 05:59.3 – 06:04.8 | "…MSD Biopic came in that year itself. And I watched that movie…" | Minimal ticket stub, left third: "M.S. Dhoni: The Untold Story · 2016 · Admit one". It tears on "watched". **Text only**: no poster art, no likeness. | Slides in from the left 0.4s `in-soft` at −3° tilt. Tear: the right half drops away with 8° rotation, 0.5s power2.in. | Paper tear. |
| 06:04.8 – 06:23.3 | "…it just emotionally crashed me… I was not able to face myself…" | **Restraint:** only a slow vignette, darkening the edges ~15% and breathing in. No text. | Opacity 0→15% over 4s sine.inOut. Hold. Release over 1.5s as the photo arrives. | None. The music carries it. |
| 06:23.5 – 06:59.2 | "…I called my coach again…" → "…take that much risk." | Generic call pill top-centre (over the dark poster, above the cap): "Coach" with a ringing pulse, then a call timer running in real time while you talk. On "take that much risk" it turns accent, shows "Call ended", and collapses. Built to your existing ring and hang-up SFX. No phone-brand UI. | Grows from 0 width, 0.45s `in-soft`. Ring pulse scale 1→1.6 + fade, 0.8s loop until "told him". End: colour 0.15s, collapse to a dot 0.35s power3.in, dot fades. | Your existing ring + hang-up beeps. Add nothing. |
| 06:30.4 – 06:35.2 | "…I would put my hundred and twenty percent every day…" | Left third: a progress bar fills past its 100% tick to 120 with a counter; the overflow segment is cream. | Fill 0.9s `in-soft`, overshooting to 120; counter rolls. Hold 1.0s. Fade 0.3s. | Short rising power-up swell (−20 dB). |
| 06:39.2 – 06:58.3 | Coach: "…play for your college team… three, four years since you left… So Abhi, don't make sense to take that much risk." | Editorial quote card, left third: **"Abhi, don't make sense to take that much risk." — Coach**, landing on "Abhi". **Replaces cues 170–171**, so the Hinglish line is typeset once, intact. | Text in line by line, 8px rise, 0.4s power2.out; attribution 0.3s later. **Hard cut out on the hang-up beeps.** | None. The hang-up is the cue. |
| 07:02.6 – 07:05.6 | "So that was the second door closing for me." (ground b-roll) | Two black panels slide in from the left and right edges over the b-roll and stop at a narrow gap: a door closing on the shot. The cut back to A-roll clears them. | Panels x ±100%→±18%, 2.4s power2.inOut, stopping dead. Cleared by the cut. | Low wooden creak → soft latch click on the stop (−18 dB). |
| 07:10.7 – 07:13.7 | "Here's what I actually want you to take from this." | Chapter pill top-left: **The takeaway**. Add a YouTube chapter here too. It resets attention at the start of the 107s A-roll stretch. | Slide 0.4s `in-soft`. Hold 2.5s. Fade 0.3s. | Soft whoosh + UI tick. |
| 07:13.9 – 07:21.6 | "Not don't quit things… sometimes quitting is a reasonable choice, but something more specific." | Left third: "Don't quit." in muted grey, struck through with an accent line on "reasonable choice". | Fade 0.3s. Strike 0.25s power2.in. Hold 1.0s. Fade. | The same marker scratch as 0:32, for continuity. |
| 07:25.3 – 07:32.0 | **"…It's that no one ever told me that it's okay to fail."** (payoff) | **The 3:14 stamp returns in the same spot:** "I can't fail." On "okay", "can't" is struck and **"It's okay to"** writes in, while "fail" shifts from accent to warm cream. **Replaces cue 185.** | Stamp hard-cuts in on "no one ever told me". Strike 0.25s; new words write on 0.6s power2.out; colour tween 0.8s. Hold 2.0s. Slow fade 0.6s. | The 3:14 thud, then a warm swell as the colour turns. |
| 07:35.9 – 07:58.3 | "…that fear of failure… followed me everywhere… classroom, conversation… every room that I walked into…" | Left third: a row of icons (bat · desk · speech bubble · door), with a small accent dot (fear) hopping to sit beside each one as it appears. Icons rather than words, so nothing duplicates the caption. | Icons fade up 0.3s on their words. Dot hops on a 0.35s power2.inOut arc. On "came after me", the dot gains a soft shadow. Out 0.4s. | Soft tap per hop, like a footstep (−24 dB). |
| 08:06.8 – 08:15.8 | "So I would advise you to find a person that would tell you that it's okay to fail." | **Payoff of 3:16:** the lone grey dot reappears in the same place; a warm cream dot slides in beside it and the ring closes around both. | Grey dot fades in 0.4s. Cream dot travels 1.2s sine.inOut. Ring morph 0.6s. **Fully gone by 8:16.3.** | One soft warm note, then silence. |
| 08:16.3 – 08:24.7 | "…I am here in this video telling you as your big brother that it is completely fine to fail…" (zenith) | **None.** This is your deliberately naked, unscored window. Keep it clean. | — | — |
| 08:34.6 – 08:42.2 | "…fear didn't only cost me cricket. It cost me my confidence for years afterwards." | Left third: two chips, Cricket and Confidence (the 3:43 asset). Each tips over and falls out of frame on its word. | Chip in 0.25s. Fall: rotate 15°, y +300, 0.6s power2.in. | Two soft drops, the second lower. |
| 08:42.3 – 08:52.2 | "So next time, I'll show you exactly how I build that back… to a person who could stand in front of hundreds." | Teaser: pill top-left **Next episode**. The confidence meter from 3:43 refills 0→100% on "build that back". On "hundreds", ~300 small dots ripple out across the left third: an audience. | Meter fill 1.2s power2.out. Dots ripple out from the meter over 1.5s (2ms stagger, random 0.6–1 opacity). Hold into the end card. | Warm rising swell into the end card; quiet crowd shimmer under the dots (−26 dB). |
| 08:52.4 – 09:00.4 | End card (existing tagline + byline) | Lift the tagline to y 30% and leave two YouTube end-screen zones (video + subscribe) below it. The end screen needs ≥5s; you have ~8s. | Tagline drifts up 0.6s power2.inOut. | (existing, silent) |

## Asset checklist
**Already built: reuse or re-anchor**
- Routine card (`animations/cards/routine`)
- `GFX_GROWTH.mov` (20 cm)
- `stamp_test` chip cards (Fearful / Zero)
- Locator `g03` "First year of college, 2016"
- Speed badge
- HN fonts
- Existing SFX: thwack, catch, sprocket, bus, clock bed, ring, hang-up

**To build: shapes and UI**
- Glass pill (one component reused for Ep 1, The takeaway, and Next episode)
- Quote-mark pair
- Hand-drawn strike path
- Hairline → scribble path pair
- 12-dot month row
- Route line with 2 pins + traveller dot
- Battery glyph
- Generation dot grid
- "Hopes" tile + 2 weight slabs
- Confidence meter
- Two-bar chart with digit-roll counter
- School/Cricket block strip
- 130–180 cm ruler
- Stat card
- Ticket stub (text only)
- Vignette matte
- Call pill with ring pulse + timer
- 120% progress bar
- Editorial quote card
- Two black door panels
- Lone-dot / two-dot ring
- ~300-dot field
- End-screen layout

**To build: icons and illustrations** (one consistent 2px-stroke line set)
- ₹5 coin
- Football
- Bat
- Cricket-ball glyph
- Desk
- Speech bubble
- Door

**To build: copy**
- Four Hinglish relative bubbles
- "Papa: Continue."
- Coach quote

**SFX to source**
- Sub thump
- Paper clicks
- Tape zip
- Brand hit
- UI ticks
- Marker scratch
- Pencil glide / scribble
- Soft clock tick
- Coin ting
- Reverb boom
- Power-down tone
- Pluck
- Heavy thud
- Stamp thud
- Rubber-stamp thunks
- Drain sweep
- Reversed cymbal
- Tonal dip
- Crowd murmur
- Bubble pops
- Piano note
- CRT off
- Paper tear
- Power-up swell
- Door creak + latch
- Soft taps
- Drops
- Crowd shimmer

## Pacing review
- **Overall density is high on purpose:** 46 cues, about 5 events per minute. A graphic is on screen roughly 70% of the time. That's fine for small UI elements, but it means you should cut before you add.
- **Risk: over-saturated at 3:34 – 4:43.** There are 69 seconds of back-to-back graphics: chips → glyph → bars → slab #2 → bubbles → "Continue." If your QC pass feels it, cut the **cricket-ball glyph (3:45)** and **slab #2 (4:15)** first; the stretch still works without them.
- **Busy but justified: 1:28 – 2:35.** The routine card, b-roll montage, and clock bed all overlap. The card is the spine of that section, so add nothing more.
- **Busy but justified: 6:23 – 6:59.** The call pill, 120% bar, and quote card overlap, but they tell one event.
- **Sparse, deliberately so:**
  - 3:16 – 3:29: the lone dot only
  - 4:43 – 4:54
  - 5:12 – 5:24: lead-in to the 20 cm reveal
  - 6:04 – 6:23: vignette only
  - **8:16 – 8:34: the zenith and its aftermath.** These rests are what make the stamps and payoffs land; don't fill them.
- **Sparse, and worth a look at 2:48 – 3:02.** "My father was selling vegetables at nine… small jobs" is 14s with only the cart b-roll. If it reads slow, bring the "Hopes" tile in earlier (it's already set to enter on "high hopes" at 3:02) rather than adding a new graphic.
- **Longest single A-roll stretch: 7:05 – 8:52 (107s).** It now carries five graphic beats before the naked zenith. That replaces "longest gap 106.7s" in your coverage report with a stretch that has rhythm while still keeping the hold.
