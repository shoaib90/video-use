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

## 11. First real measurement against this model — Detour Ep2, day 3

Everything above this section is Gorbachevskaya's model, explicitly unverified
against this channel. This is the first set of our own numbers. Published
2026-09-26 as "Hard Work Guarantees Nothing." (27:14).

**Reported at day 3:** 125 views · 746 impressions · 1.88% CTR · 4:10 AVD
(15.32%) · ~1 h 14 min watch time · 2 likes · >95% of views attributed to Home.

### The figures do not reconcile, and that is itself the finding

| derivation | implied views |
|---|---|
| impressions x CTR (746 x 1.88%) | **14** |
| watch time / AVD (74 min / 4:10) | **18** |
| reported | **125** |

14 and 18 agree; 125 does not — it is 7x the watch-time figure. And ">95% of
views from Home" cannot hold alongside 746 impressions, because Home is an
impression surface: if 119 views came from Home, Home CTR would be ~16%.

AVD is internally consistent (250 s / 1634 s = 15.30% vs the reported 15.32%),
so the *duration* number is trustworthy in a way the *view* number is not.

This is §3 — "do not read the first 24-48 hours" — showing up in our own data
rather than as someone's advice. View counting runs through a reconciliation
pipeline, and at day 3 it has visibly not converged. **Treat the ~15-18 figure
as the real audience so far**, not 125.

### What is safe to conclude anyway

- **746 impressions is the headline, not the 1.88% CTR.** The video barely left
  the loyal base. §2's diagnostic — split new vs returning viewers — is the
  first thing to check, and it is a Studio lookup we have not done.
- **CTR on 14 clicks carries almost no information.** Two clicks either way
  moves it by ~0.3 points. Do not re-package on this.
- **AVD 4:10 against a turn at 16:46 is the one real signal.** The average
  viewer leaves **12.6 minutes before the thing the episode exists for**. This
  is a structural fact about the cut, independent of the reconciliation problem,
  and it is the only number here worth acting on.

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

Ep2's runtime grew **17:20 -> 27:14** during the edit, to keep content the user
did not want dropped. The cost was flagged at the time; this is what it looks
like in analytics. For a format whose whole value is the turn, **the turn has to
arrive before the average viewer leaves** — either much earlier in the cut, or
the episode has to be short enough that 15% of it still reaches the turn.

Per §5, this does not mean re-cutting Ep2. It means Ep3 is built turn-first.

**Still to check in Studio** (none of it derivable from the numbers given):
new vs returning; Ep1's first three days for a velocity comparison (§4); the
retention graph, which `helpers/coverage.py` can consume directly.
