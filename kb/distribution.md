# Distribution — how the video travels after it is rendered

Everything else in this KB stops at the render. This file is about what happens
next, because several of the decisions we make while editing are really bets
about distribution, and because the analytics we already read (`coverage.py`
takes a retention export) are easy to read wrongly.

Primary source: **"Ex-YouTube Employee Explains the Algorithm"**, Gimbal Podcast
with **Nastia Gorbachevskaya**, 28 min, 2026 — a former YouTube Partner Manager
describing how the recommendation system was explained internally.
<https://www.youtube.com/watch?v=VpKYkZr-1oQ>

**These are her claims, not our measurements.** Nothing here has been verified
against this channel. Where something is checkable against our own analytics,
it is marked. Treat the whole file as a model to test, not as fact — the same
standard the rest of this KB holds itself to.

---

## 1. Impressions are the system's confidence, not a reward it withholds

The model she describes: YouTube serves a video in widening waves. It shows it
to the people most likely to want it — the loyal audience — and if they respond,
it takes more risk and offers it to people less connected to the channel. Each
successful wave licenses a bigger, less-certain one.

So impressions stop growing when a wave stops converting. Not because the
platform declined to promote the video, and not because a feature went unused.

The practical consequence is the diagnostic below, and a general one: **stop
reading low impressions as a punishment.** It is the system reporting where its
confidence ran out.

## 2. The diagnostic for "good CTR, good retention, low impressions"

This is the exact case she is asked about — 7% CTR, 7 minutes average view
duration on a 15–20 minute video, and only 10,000 impressions — and it maps
onto a small channel closely.

Her answer: **break the video down by new vs returning viewers.** If the
new-viewer count is very small, the video never escaped the loyal base. The CTR
and retention look good precisely *because* only people who already like the
channel ever saw it. Good numbers from a small, self-selected audience are not
evidence that the video would travel.

That is checkable in YouTube Studio per video, and it is the first thing to look
at before concluding a cut underperformed.

## 3. Do not read the first 24–48 hours

She will not look at real-time data at all for the first two days, unless the
video is news. YouTube's own labelling calls early figures estimates; view
counting runs through a pipeline that reconciles later.

For us this is a discipline point: **do not re-cut, re-title or panic on day-one
numbers**, and do not let them into a decision about the next episode.

## 4. Compare like with like, in the same window

Two errors she names:

- Comparing against the **channel average** instead of against a comparable
  video. If the channel has content pillars, compare a video to another video in
  the same pillar.
- Comparing against **another channel's totals** without matching the time
  window. A million views may have taken a year, or come from a channel that
  publishes quarterly while you publish weekly.

YouTube Studio lets you set the comparison window manually — compare the *first
week* of this video against the *first week* of the other one. The word she uses
is **velocity**: performance per unit time, not the absolute number.

Directly applicable here: Episode 2 should be judged against Episode 1's first
week, not against Episode 1's total.

## 5. Put the energy into the next episode, not into rescuing the last

On hot-swapping thumbnails and titles in the first hours: worth it only when the
video is **high-stakes, expensive and infrequent** — a monthly flagship. For
weekly or lower-stakes publishing, she would analyse and spend the effort on the
next one, and says this was the internal line at YouTube too.

This is the opposite of the instinct to keep fiddling with a delivered file, and
it is worth holding to, because our own process makes re-rendering cheap enough
to be a trap.

## 6. There is no blueprint — find the channel's own Pareto

YouTube does not look for a universal formula; teams study what already happened
and synthesise. For an individual channel the whole method is: **find what
worked, do more of that.** Identify the small share of content doing most of the
work and double down; for what is not working, decide honestly whether to fix it
or stop spending there.

This is the same claim `ideation.md` records from a different direction —
repetition builds identity — and it is why consistency across episodes beats
novelty within one.

## 7. Using new features does not buy impressions

A common belief, and she is explicit that it is false. The recommendation system
is optimised to make YouTube worth watching; it has no reason to boost weaker
content because it used a new feature. Likewise, **having a Partner Manager does
not make a channel grow faster** — they are a data-driven advisor with no
decision rights and no access to your creative process.

Useful mainly as a way to *not* spend effort.

## 8. Community posts are the most underused surface

Her strongest specific claim: on one client's channel, **1 million of 10 million
channel impressions came from community posts** — about 10%. YouTube distributes
them on the home feed as content in their own right.

How to use them, and this part matters:

- **Never post "here's my new video, go watch it."** She calls this the worst
  way to promote anything — the viewer has already seen the video offered
  elsewhere.
- Instead, publish the **value that did not fit in the thumbnail**. A long video
  contains far more than its packaging can carry; take a piece of it out as a
  standalone post.
- A carousel works; so does the simplest possible version — **one image and a
  short text hook**, not crowded with text.

The broader habit is **"waterfalling"**: turning one long-form piece into many
assets. Most people waterfall to Instagram and LinkedIn and forget the community
tab, which is the one surface where the audience is already subscribed.

For this channel that is nearly free: an episode like Ep2 has the routine, the
20cm detail and the coach's line, any of which stands alone as a post.

## 9. There is no such thing as a bad subscriber

A subscriber who never watches **costs nothing** on YouTube. The intuition that
inactive followers hurt reach is imported from feed-based platforms and does not
apply. Every long-running channel accumulates them, because YouTube makes
subscribing easy and unsubscribing hard.

So: do not try to optimise subscriber "quality", and do not avoid a format
(shorts, community posts) on the theory that it attracts the wrong people.

---

## On the second video: metadata settings

**"The 2-Minute Algorithm Hack That Helps YouTube Recommend You"**, TubeBuddy,
4 min. <https://www.youtube.com/watch?v=wZonRKXyvzI>

It recommends three settings: channel keywords, a default description in Upload
Defaults, and default tags.

**Read this one sceptically.** It is a vendor video for a paid extension, and
the framing — "hidden settings", "secret", "most creators never touch" — is
selling. On the specifics:

- **Tags**: YouTube's own guidance has for years said tags play a *minimal* role
  in discovery. Presenting them as "massive" is the weakest claim in the video.
- **Channel keywords**: same category, low leverage.
- **Upload Defaults**: genuinely worth doing, but as a **time-saver and a
  consistency device**, not an algorithm trick. Writing the standing part of the
  description once means every upload carries a proper channel explanation
  without remembering to paste it.

The one real idea underneath it: **a brand-new channel has no watch history, so
the system leans harder on what the video says about itself.** That is why
metadata matters more at the start than later — not because there is a hidden
lever, but because there is not yet any behavioural signal to use instead.

Note the tension with the Partner Manager's account, and resolve it this way:
metadata helps the system *classify* a video; viewer behaviour decides how far
it *travels*. Filling in the description properly is ten minutes once. It is not
a substitute for the cut.

---

## 10. Packaging, and reading performance — from a strategist who does it at scale

Source: **Paddy Galloway** on the Open Residency podcast (2h45m, 2026-09-14,
<https://www.youtube.com/watch?v=Z2uoA3bhJT0>). His intro and core/casual/new
rules are in `storytelling.md` §7; this is the packaging and measurement half.
His claims, not our measurements.

**Packaging is ~50 % of the game, and should get ~10–20 % of the time.** His
reason is that the algorithm is a multiplier: a thumbnail "maybe 20–30 % better"
took one video from 1,000 to 40,000 views a day, overnight, on an existing upload.

**The workflow, in order:**

1. **Title first**, minimum **10**. The thumbnail is then designed to *complement*
   the chosen title — never to repeat it. ("How anyone can go viral" + thumbnail
   "this is the key" complement; the same words twice do not.) This independently
   confirms the Ep. 2 critique: "WHY I QUIT" restated "I Gave Up My Biggest Dream".
2. **A thumbnail brief BEFORE the shoot**: 3–5 concepts, sketched or AI-roughed,
   so the frames get captured on the day. His biggest frustration is creators who
   "shoot the video and then afterwards be like, okay, what's the thumbnail?"
3. **Shoot the thumbnail**: hundreds of stills, varied angles and micro-expressions.
4. **Design at least 3 *differentiated* thumbnails** — not one shot in three shirt
   colours — and run YouTube's native A/B test.
5. **Before publishing, write down the expected result** (where it should rank
   against recent videos). Judge it against that, not in absolute terms: a video
   expected to be the best of the last 10 that lands 4th is a problem; a small
   topic that lands 8th is not.
6. **Change only when it underperforms expectation.** "Good data beats no data; no
   data beats bad data." Don't churn titles hourly — you lose the ability to tell
   what caused what.

**Title rules:** fewest words that are still interesting (a guide, not a hard
50–60 character cap); readable at a glance; **Title Case, not ALL CAPS** (all caps
makes every letter the same height and is read less well); **universal language** —
the "curse of knowledge" (his examples: "D1 athlete", "Goodwill", which cost a US
creator his non-US audience); human interest over SEO keyword-stuffing (search is
~5–10 % of most channels' traffic); a contradiction creates the question ("the
cheapest 911 GT3 on the market… but nobody will buy it").

**The glance test:** if the idea can't be said in one line a stranger understands
in a second, it isn't a good idea yet — and "can we title and thumbnail this?" is
his first elimination criterion, which he says removes two-thirds of ideas.

**"Click to unpause":** a thumbnail should look like a paused moment — mid-action,
mid-sentence — so the viewer clicks to resume it. A posed smile is not that.

### Reading performance

- **Views and retention *curves*, not CTR or average view duration.** CTR falls as
  a video reaches a wider audience (his lemonade stand: a 20 % conversion outside
  your house, far lower in Times Square, but more sales), and AVD rewards length.
  Views are the comprehensive metric. This supports reading Ep. 2's 5.6 % CTR on 36
  impressions as noise.
- **A retention curve drops as the audience broadens, but the drop POINTS stay
  put.** Read where people leave, not the overall level. Conclusion language ("at
  the end of the day…") triggers drops for every audience.

### Finding outliers

**An outlier is a video at ≥3× that channel's own average views** — measured against
the channel's average, not its subscriber count, which he calls close to a vanity
metric in 2026. Scan your niche *and adjacent niches* for the last year or two,
and ask "what's my twist on each?" His best example borrowed a thumbnail from a
Canadian cooking video, a title from Hormozi and a concept from a short-form creator
to make "asking millionaires how they got rich" (5M views).

Ideas come from three sources: **internal** (redo what already worked for you —
audiences forget), **external** (outliers), **innovation** (combine two things; he
suggests ~20 % of output).

### Topic overlap is smaller than you think

His estimate for Call of Duty vs Battlefield players: ~20 %. The **80 % rule**: 80 %
of videos should be topics whose audiences overlap ~80 %. Start narrow and expand
outward; "you can't really start broad and go narrow." **Open question for this
channel:** how much do the Detour viewers overlap with the essay viewers? Check it
in YouTube Studio before assuming three formats help each other.

### What not to take

The 500-ideas-a-month machine and five designers per video assume a team.
"Don't listen to your comment section" is advice for channels that already have a
core — we are still building ours. And he is candid that he is a **view
maximalist**; for a memoir channel, the audience feeling connected is the brand,
not a cost.

## What this changes for how we work

1. **Judge Episode 2 against Episode 1's first week**, in the same window — not
   against its lifetime total.
2. **Check new vs returning viewers per video** before concluding anything about
   a cut. Good CTR and retention on low impressions usually means the video
   never left the loyal audience, which is a packaging-and-topic problem, not an
   editing one.
3. **Ignore the first 48 hours.**
4. **Do not re-cut a delivered episode on early numbers** — put it into the next
   one. Our pipeline makes re-rendering cheap, which makes this trap easier to
   fall into here than for most people.
5. **Waterfall each episode into community posts** — the value that did not fit
   in the thumbnail, never "watch my video".
6. Fill in Upload Defaults once. Do not expect it to do anything dramatic.
7. **Title first, thumbnail brief before the shoot, three differentiated thumbnails,
   expected result written down before publishing** (§10). And measure outliers
   against a channel's average views (≥3×), not its subscriber count.

---

## 11. First real measurement against this model — Detour-2, day 3

Everything above this section is Gorbachevskaya's model, explicitly unverified
against this channel. This is the first set of our own numbers. Published
2026-09-26 as "Hard Work Guarantees Nothing." (27:14).

**Reported at day 3:** 125 views · 746 impressions · 1.88% CTR · 4:10 AVD
(15.32%) · ~1 h 14 min watch time · 2 likes · >95% of views attributed to Home.

### The figures reconcile once you know feed autoplay is not a click

**Corrected 2026-09-30.** This section first concluded the numbers contradicted
each other and that the real audience was "~15-18 people, not 125". That was
wrong, and the error is worth keeping because it is an easy one to repeat.

Day-4 figures: 921 impressions · 2.06% CTR · 150 Home views (95.5% of ~157
total) · 4:10 AVD · ~1 h 14 min watch time.

| derivation | implied |
|---|---|
| impressions x CTR (921 x 2.06%) | **19.0** clicked views |
| watch time / AVD (74 min / 4:10) | **17.8** views' worth of watching |

Those two agree to within 1.2 views. The reported ~157 views does not — and the
resolution is that **they are counting different things**:

- **Feed autoplay is a view but not a click.** Videos auto-play muted in the
  Home feed; dwell past a few seconds logs a **view** attributed to Home, with
  **no thumbnail click**, so it never enters CTR. Studio's "Impressions and how
  they led to watch time" funnel says this explicitly — it excludes autoplay
  views, direct/link traffic and some notification surfaces.
- **The pipelines run at different speeds.** Views and traffic sources update in
  near-real time; impressions and CTR pass through verification and spam
  filtering that lags 24-48 h. Observed here: impressions went **746 -> 921**
  between day 3 and day 4 while the view count barely moved.

Checked against the data: if AVD covers only the clicked views,
19 x 4:10 = **1.32 h** against a reported **1.23 h** — a match. If it covered all
157 views it would be **10.91 h**, seven times the reported figure. So AVD and
watch time describe the ~19 who chose to watch; the other ~138 are autoplay.

**The generalisable rule: on a small channel, `views` and `CTR` are not two
views of one funnel.** Reconcile `watch time / AVD` against `impressions x CTR`
— those two share a denominator. Never reconcile either against the headline
view count.

### What is safe to conclude anyway

- **The thumbnail is the weak link, not the opening.** 15.0% of impressions
  dwelled long enough to log an autoplay view, against a 2.06% thumbnail click
  rate. The moving footage sells the video roughly 7x better than the still
  does. That is the clearest packaging signal in this data.
- **CTR on 19 clicks carries almost no information.** Two clicks either way moves
  it ~0.2 points. Do not re-package on the percentage; re-package because of the
  autoplay/click gap above, which is a ratio and more robust.
- **AVD 4:10 is a better signal than it first looked.** It describes people who
  *actively chose* to watch, not passers-by — and they still leave **12.6 minutes
  before the turn at 16:46**. This is the one finding that survives every
  correction above.
- **Impressions were still climbing** (746 -> 921 in a day), so exposure had not
  settled. §3 holds.

### Where YouTube's own auto-feedback was wrong

Worth recording because it will recur:

- It recommended **adding chapters to the description** — 15 chapters were
  written for this upload. Either they were not pasted or the advice is
  generated without reading the description. Check before acting on it.
- It placed the philosophical section at **"around the 18-minute mark"**; the
  turn starts at **16:46**.
- It advised **teasing the core reflection in the first 30-45 s**. The cold open
  already carries exactly one line from the turn, by deliberate design
  (`notes.md`: "One line as a promise is right; more is spending it").

Generic platform feedback does not know the cut. Diff it against the EDL before
treating any of it as a finding.

### The standing lesson

Detour-2's runtime grew **17:20 -> 27:14** during the edit, to keep content the user
did not want dropped. The cost was flagged at the time; this is what it looks
like in analytics. For a format whose whole value is the turn, **the turn has to
arrive before the average viewer leaves** — either much earlier in the cut, or
the episode has to be short enough that 15% of it still reaches the turn.

Per §5, this does not mean re-cutting Detour-2. It means Detour-3 is built turn-first.

**Still to check in Studio** (none of it derivable from the numbers given):
new vs returning; Detour-1's first three days for a velocity comparison (§4); the
retention graph, which `helpers/coverage.py` can consume directly.

---

## 12. Two growth videos: The Studio (MKBHD's team) and Think Media

Sources: **"How To Start A Million Subscriber YouTube Channel"**, The Studio, 31:23, 2026-07-03
(<https://youtu.be/Puny-2wkMZA>), and **"How to Grow a YouTube Channel From Scratch in 2026!"**,
Think Media, 14:07, 2026-07-06 (<https://www.youtube.com/watch?v=AV4r2Qixb1Y>). Read in full from
local whisper transcripts; the caption endpoint returned 429. **Their claims, not our
measurements.** The channel-specific reading is in the private channel-kb
(`07-research/youtube-growth-advice.md`); only the distribution side is here.

- **"Is my channel dead?" Ask first: did I just try something new?** If yes, decide whether to
  stick it out, or carry over what worked from the last format. If no, the audience is bored:
  innovate, or borrow topics from other channels. A decline almost never means a shadowban; it's
  usually the content.
- **Choose the number by the goal.** Growth → views, and better outliers. Relationship → watch
  time (longer videos that aren't boring). Reach and connection → subscribers. Selling ads → low
  volatility between videos. Decide which before reading a dashboard.
- **Verify identity in YouTube Studio** (a government ID) on a new channel. They say it "builds
  trust with the algorithm". Unverified, but free and one-time.
- **Shorts have to be designed, not clipped.** A long-form video cut into Shorts afterwards
  doesn't work; the format must contain setups that pay off in under a minute. That makes it a
  script decision, not an edit one.
- **Batch 3–4 videos before launching a format**, so one upload's numbers can't break the habit.
- **Outliers bring views; formats bring people back.** "Nobody really cares about you when they're
  clicking." Return visits come from a consistent format, even one as plain as a person at a
  desk.
- **CTR floor (Think Media): 3–5% decent, under 2% poor packaging.** Detour-2's 2.06% sits on the
  line, consistent with §11's autoplay-vs-click finding. Still read it under §10's warning: CTR
  falls as reach widens, and on ~19 clicks it's noise.
- **AI "is a regression towards an average"** (The Studio). That's the reason the scripting
  rules require every fact to come from the creator's own notes.

## Thumbnail craft: the subject in front of the words (Shoaib's references, 2026-10-21)

Shoaib picked 12 thumbnails he would click (fitness explainers, Huberman Lab, creator-economy and
storytelling channels). Four things recur, and our v1 (Episodes 3-5) had none of them:
1. **Depth:** the person is cut out and sits IN FRONT of huge words, overlapping their edges.
2. **The words are the background:** 2-3 words fill 50-90% of the width, in a heavy, often condensed face,
   never in a caption box.
3. **The subject pops:** the background is blurred, darkened or flattened, and the subject is brighter and
   sharper, sometimes with a faint edge glow.
4. **One accent colour** on one word, and at most one graphic (a numbered muscle diagram, a glowing spine).

**Crisp comes from the SOURCE first (Episode 5 v3, 2026-10-22).** Layering alone (v2) still read
soft. The fix was a sharp, large face: an a-roll frame from the 4K source, near 1:1 (face ~500 px),
mouth closed, eyes to the lens, on a CLEAN background (a gradient, not the blurred room), with the face
filling ~85% of the height. Action stills from b-roll (motion blur, side-on, small) and dim phone
photos fail at 168 px. Pattern: `episode5/edit/build/thumbnails_v3.py`. **Poppins is installed** (`~/Library/Fonts/Poppins-*.otf`, 2026-10-22): use
Poppins Black; it is wider than Avenir Next Condensed, so fit each line's size to its room. A radial glow pasted as a
square must fade to zero inside the square, or it leaves a hard vertical edge.

How to build it locally: `helpers/subject_mask.swift` (macOS Vision "lift subject", which keeps held
objects such as dumbbells) cuts the subject out, then layer it as background (blur 16, saturation
0.55, brightness 0.42, vignette), the words with a soft shadow, a faint white halo, and the subject on
top. Pattern: `episode5/edit/build/thumbnails_v2.py`. Rule from building it: let the subject cover
a word's EDGE, never a key letter. "LATER." read "ATER." and "15 MINUTES" read "15 M…UTES"
until both moved. Unproven: whether it lifts CTR on our channel. It is the look Shoaib clicks.

**A second house option: the cinematic-essay look** (Shoaib's "BE DELUSIONAL." reference, 2026-10-22).
It has a deep red grainy field, the subject in grainy high-contrast black and white, a TIGHT head-and-chest
crop running off the bottom edge (a waist-up crop read small at 168 px and pulled chair arms into the
cutout), and a small, widely spaced serif title (Didot Bold, tracking ~0.2 em) centred at the top. It suits
an emotional or abstract title such as "MENTAL JAIL."; the bold Poppins layout suits a result or a number.
Pattern: `episode5/edit/build/thumbnails_v5.py`.


## The self-improvement niche's outlier thumbnails are paused moments, not posters (stance-04, 2026-10-26)

/yt-viral on rest guilt / hustle culture / Frankl's inverse law: vidIQ outlier search for candidates, then
`swipe.py` multiples over each channel's own median (345 public uploads, 12 channels). The top multiples
(1,150x "I Quit My Job After Burnout", 1,074x livy baker "this is why you can't enjoy anything anymore.", 118x
istheelf) are candid frames with a natural expression and 0-4 words, or the problem's own objects collaged around a
real face. None was a posed shock face on a designed poster. For stance-04 this moved the recommendation from the red
cinematic "THEY GAVE YOU HALF." to a real frame of the hook's quote wall with the centre card split
(`feel-like-hustler/edit/thumbnails/thumb_D3_quote_wall_lean`). Unproven on our channel until a CTR reads; record it.
`title.py` counts every word on a thumbnail, slogans included (12 there, ceiling 3).
- **Reference, Quam Balogun "you're broke because you're too smart" (2026-10-26):** 380K views on a 4.6K-sub channel,
  73x its 8-video median (5,200), and its shortest upload (5:17 vs 9-20 min). Pairing: the title is a flattering
  accusation (diagnosis); the thumbnail is the shocking prescription in two huge lowercase words, with a candid
  mid-gesture frame in front of them covering a non-key part of the word. The thesis is said in the first sentence.
  Its click word is a slur, which our brand would never use; the transferable parts are the pairing, the depth layout
  and the one-idea short length.
