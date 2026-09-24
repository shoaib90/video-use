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
