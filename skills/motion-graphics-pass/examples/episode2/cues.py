"""Episode 2 — "I Gave Up My Biggest Dream at 15" — the motion-graphics pass as delivered
(final_mgx.mp4, 2026-10-12). This is the worked example: copy it to <edit>/mgx/cues.py for a
new episode, keep the CONFIG block's shape, and replace every cue.

Times are absolute output times (seconds on the master's timeline) taken from
`mgx.py words` — word onsets, not caption cue starts. Design units are 1920x1080.
"""
from mglib import *

# ------------------------------------------------------------------ CONFIG
MASTER = "final.mp4"          # picture-locked, captioned, mixed master (input; never modified)
BASE = "base.mp4"             # render.py's graded base: same frames, NO captions / overlays
OUTPUT = "final_mgx.mp4"

# Fonts. Leave empty to use macOS Helvetica Neue (find_system_fonts()); Episode 2 used the copies
# that ship beside its routine card.
set_fonts(r=f"{EDIT}/animations/slot_glass_routine/fonts/HN-Regular.ttf",
          m=f"{EDIT}/animations/slot_glass_routine/fonts/HN-Medium.ttf",
          b=f"{EDIT}/animations/slot_glass_routine/fonts/HN-Bold.ttf")

# Caption replacement: master.srt cue numbers whose words a kinetic-type cue now carries.
# Their caption band is patched from BASE for exactly the cue's window.
REPLACE_CAPTIONS = [1, 2, 3, 4, 5, 35, 36, 85, 95, 97, 131, 170, 171, 185]
CAPTION_BAND = (720, 1640, 2400, 340)        # output pixels (x, y, w, h) that hold the burned captions
EXTRA_PATCHES = [                              # (x, y, w, h, start, end) — any other region to restore from BASE
    (2800, 56, 1000, 170, 88.05, 91.45),       # the old "The academy, 15 km away" locator, replaced by the route
]

# Full-frame layers that are not cues.
VIGNETTES = [(364.8, 384.45, 0.62)]            # (start, end, edge opacity): "emotionally crashed me"
GLASS_CARDS = [                                # a HyperFrames glass card + mask pair (render.py's cards)
    dict(card="animations/slot_glass_routine/renders/cards_2160.mov",
         mask="animations/slot_glass_routine/renders/mask_2160.mov",
         start=92.6, crop=(1600, 1760), bt601=True),
]

SFX_DIR = "~/Documents/Ambitious/Editing/effects"   # house library; structural/palette.json lives here
SFX_LEVEL_CEILING = 0.93                            # limiter on the final mix (linear)

# ------------------------------------------------------------------ CUES

# 1 — cold open, line 1 (replaces cues 1-2)
CO1 = [("Is", .06), ("there", .38), ("something", .62), ("you", .98), ("used", 1.10), ("to", 1.34),
       ("love", 1.58), ("that", 1.90), ("you", 2.06), ("gave", 2.46), ("up?", 2.86)]
@cue("co1", 0.0, 3.78, (0, 380, 1920, 330), sfx=[("thud_soft", 2.46, -21)])
def _(c, t):
    kinetic(c, t, [CO1[:6], CO1[6:]], 60, 515, 84, 3.45, acc=("gave", "up?"))

CO2 = [[("Not", 3.9), ("because", 4.14), ("you", 4.46), ("stopped", 4.62), ("loving", 4.94), ("it,", 5.26), ("but", 5.58)],
       [("because", 6.62), ("somewhere", 6.94), ("along", 7.34), ("the", 7.58), ("way,", 7.74), ("someone", 8.14), ("convinced", 8.62)],
       [("you", 9.34), ("it", 9.50), ("wasn't", 9.66), ("the", 10.30), ("responsible", 10.62), ("choice.", 11.10)]]
@cue("co2", 3.85, 12.25, (0, 360, 1920, 380), sfx=[("click", 10.80, -22), ("click", 10.93, -24)])
def _(c, t):
    pos = kinetic(c, t, CO2, 46, 480, 70, 11.95, pad=("responsible",))
    x, xr, yb = pos["responsible"]
    o = 1 - ei2(p(t, 11.95, .3))
    for k, (qx, ch, at) in enumerate(((x - 28, "“", 10.80), (xr + 4, "”", 10.93))):
        pr = p(t, at, .35)
        if pr <= 0:
            continue
        e = bo(pr, 1.6)
        text(c, ch, qx, yb + 14 - 40 * (1 - e), 58, "b", CREAM, cl(pr * 3) * o, sc=lerp(1.3, 1.0, cl(e)))

# 3 — thirteen-year timeline
@cue("timeline", 15.2, 22.25, (380, 560, 1160, 170), sfx=[("whoosh_air", 15.3, -24)])
def _(c, t):
    a = 1 - ei2(p(t, 21.85, .35))
    xr, xl, y = 1460, 460, 640
    pr = eio2(p(t, 15.3, 1.6))
    line(c, xr, y, lerp(xr, xl, pr), y, 1, CREAM, .75 * a, 2.5)
    for k in range(14):
        tx = lerp(xr, xl, k / 13)
        tp = p(t, 15.3 + 1.6 * k / 13, .25)
        h = 18 if k in (0, 13) else 9
        line(c, tx, y - h * eo3(tp), tx, y + h * eo3(tp), 1, CREAM, .8 * a * tp, 2)
    text(c, "2026", xr, y + 52, 24, "m", CREAM, a * eo3(p(t, 15.3, .4)), anchor="c")
    ap = eo3(p(t, 16.9, .45))
    text(c, "2013", xl, y + 52 + (1 - ap) * 6, 24, "m", CREAM, a * ap, anchor="c")
    text(c, "13 years", 960, y - 26, 18, "m", MUTED, a * eo3(p(t, 17.2, .5)), anchor="c")

# 4 — tagline: per-word wipe over a black patch
@cue("tagline", 22.2, 25.2, (330, 440, 1260, 180), sfx=[("hit_soft", 22.45, -18), ("whoosh_soft", 22.45, -22)])
def _(c, t):
    c.rectangle(330, 440, 1260, 180)
    c.set_source_rgb(0, 0, 0)
    c.fill()
    words = "Become Someone You're Proud Of".split()
    size = 52
    sp = tw(" ", size, "r")
    total = sum(tw(w, size, "r") for w in words) + sp * (len(words) - 1)
    x = 960 - total / 2
    o = 1 - p(t, 24.55, .5)
    for k, w in enumerate(words):
        wd = tw(w, size, "r")
        pr = eo3(p(t, 22.45 + .14 * k, .45))
        if pr > 0:
            c.save()
            c.rectangle(x - 4, 470, (wd + 8) * pr, 110)
            c.clip()
            text(c, w, x, 548, size, "r", (.95, .95, .95), o * cl(pr * 1.6))
            c.restore()
        x += wd + sp

# 6 — Episode 1 pill with correction
@cue("ep1", 29.3, 35.35, TOPL, sfx=[("tick", 29.3, -24), ("scratch", 32.38, -18)])
def _(c, t):
    tin, tout = 29.3, 35.0
    a = eo3(p(t, tin, .4)) * (1 - ei2(p(t, tout, .3)))
    dx = (1 - eo3(p(t, tin, .4))) * -24 - ei2(p(t, tout, .3)) * 24
    x, y = 64, 58
    t1 = "The day I quit cricket"
    t2 = "The year I quit cricket"
    sw = max(tw(t1, 30, "m"), tw(t2, 30, "m"))
    wd = 52 + sw + 36
    def f():
        glass(c, x, y, wd, 96, 26)
        text(c, "EPISODE 1", x + 26, y + 34, 15, "m", MUTED)
        xf = eo3(p(t, 33.25, .35))
        text(c, t1, x + 26, y + 74, 30, "m", CREAM, 1 - xf)
        if xf < 1:
            strike(c, x + 26, x + 26 + tw("The day", 30, "m"), y + 63, eo3(p(t, 32.38, .25)), 1 - xf)
        if xf > 0:
            text(c, "The year", x + 26, y + 74 + (1 - xf) * 10, 30, "m", ACCENT, xf)
            text(c, " I quit cricket", x + 26 + tw("The year", 30, "m"), y + 74, 30, "m", CREAM, xf)
    group(c, a, f, dx=dx)

# 7/8 — clean line -> messy knot -> 12 quiet months
@cue("knot", 36.55, 52.75, LEFT, sfx=[("whoosh_soft", 36.7, -26), ("scratch", 41.9, -22)] +
     [("tick_soft", 46.7 + .36 * k, -30) for k in range(12)])
def _(c, t):
    a, dy = card_env(t, 36.6, 52.4)
    x0, x1, y = 120, 560, 470
    def f():
        glass(c, 64, 330, 560, 280, 28)
        # line / scribble
        m = eio2(p(t, 41.9, .8))
        drawn = eo3(p(t, 36.86, .6))
        fade = 1 - eo3(p(t, 46.3, .45))
        if fade > 0 and drawn > 0:
            n = 420
            c.set_line_width(4)
            c.set_line_cap(cairo.LINE_CAP_ROUND)
            c.set_line_join(cairo.LINE_JOIN_ROUND)
            for i in range(int(n * drawn) + 1):
                u = i / n
                xs = x0 + (x1 - x0) * u
                xk = x0 + (x1 - x0) * u - 34 * math.sin(2 * math.pi * 6.5 * u)
                yk = y + 52 * math.cos(2 * math.pi * 6.5 * u) * math.sin(math.pi * u) ** .6
                px, py = lerp(xs, xk, m), lerp(y, yk, m)
                (c.move_to if i == 0 else c.line_to)(px, py)
            c.set_source_rgba(*WHITE, .95 * fade)
            c.stroke()
        # twelve months
        if t > 46.2:
            for k in range(12):
                dxk = 128 + k * 38
                ap = eo3(p(t, 46.3 + k * .02, .4))
                fill = p(t, 46.7 + .36 * k, .3)
                dot(c, dxk, y, 9, mix((.42, .42, .42), CREAM, fill), ap)
            text(c, "12 months", 340, 560, 18, "m", MUTED, eo3(p(t, 47.0, .5)), anchor="c")
    group(c, a, f, dy=dy)

# 9 — locator
@cue("loc_gandhinagar", 52.75, 56.0, TOPR, sfx=[("tick", 52.8, -24)])
def _(c, t):
    locator(c, "Gandhinagar, 2004", t, 52.8, 3.2)

# 10 — five rupee coin (kids b-roll 62.98-65.71)
@cue("coin", 64.85, 65.70, (1250, 470, 320, 320), sfx=[("pop_glass", 65.15, -22)])
def _(c, t):
    pr = p(t, 64.88, .6)
    e = eo3(pr)
    wob = bo(p(t, 65.30, .3), 2.0) if t > 65.30 else 1
    ang = (1 - e) * 4 * math.pi
    sy = abs(math.cos(ang)) * (wob if t > 65.30 else 1)
    cx, cy, r = 1410, 640 + (1 - e) * 60, 62
    c.save()
    c.translate(cx, cy)
    c.scale(1, max(.06, min(1.08, sy)))
    for g, al in ((10, .12), (5, .15)):
        c.arc(4, 10, r + g, 0, 2 * math.pi)
        c.set_source_rgba(0, 0, 0, al * cl(pr * 4))
        c.fill()
    gr = cairo.RadialGradient(-r * .35, -r * .4, r * .1, 0, 0, r)
    gr.add_color_stop_rgb(0, .98, .88, .58)
    gr.add_color_stop_rgb(.7, .80, .64, .30)
    gr.add_color_stop_rgb(1, .55, .40, .16)
    c.arc(0, 0, r, 0, 2 * math.pi)
    c.set_source(gr)
    c.fill()
    ring(c, 0, 0, r - 7, (.45, .32, .12), .55, 2.5)
    if math.cos(ang) > 0:
        text(c, "5", 0, 22, 62, "b", (.40, .28, .10), .9, anchor="c")
        text(c, "RUPEES", 0, 44, 11, "b", (.40, .28, .10), .8, anchor="c")
    c.restore()

# 11 — football vs cricket
@cue("bars_fc", 72.55, 79.75, LEFT, sfx=[("whoosh_air", 72.86, -26), ("riser_soft", 78.4, -22)])
def _(c, t):
    a, dy = card_env(t, 72.6, 79.4)
    def f():
        glass(c, 64, 360, 520, 210, 28)
        tx0, tx1 = 230, 540
        for k, (lab, at, val, col) in enumerate((("Football", 72.86, .72, MUTED), ("Cricket", 79.02, 1.32, CREAM))):
            y = 430 + k * 80
            text(c, lab, 96, y + 9, 24, "m", CREAM if k else (.75, .73, .70))
            rrect(c, tx0, y - 9, tx1 - tx0, 18, 9)
            c.set_source_rgba(1, 1, 1, .08)
            c.fill()
            fill = eo3(p(t, at, .9 if k else .6)) * val
            if fill > 0:
                c.save()
                if k:
                    c.rectangle(0, 0, 760, 1080)
                    c.clip()
                rrect(c, tx0, y - 9, (tx1 - tx0) * fill, 18, 9)
                c.set_source_rgba(*col, 1)
                c.fill()
                c.restore()
    group(c, a, f, dy=dy)

# 12 — hobby -> religion (replaces cues 35-36)
@cue("religion", 79.5, 83.75, LEFT, sfx=[("scratch", 81.25, -22), ("boom", 82.36, -18)])
def _(c, t):
    a, dy = card_env(t, 79.52, 83.4)
    def f():
        glass(c, 64, 330, 520, 300, 28)
        text(c, "just a hobby", 100, 410, 40, "m", MUTED)
        strike(c, 100 + tw("just a ", 40, "m"), 100 + tw("just a hobby", 40, "m"), 397, eo3(p(t, 81.25, .22)))
        text(c, "closer to", 100, 482, 26, "m", MUTED, eo3(p(t, 81.75, .35)))
        pr = p(t, 82.36, .35)
        e = bo(pr, 1.4)
        text(c, "religion.", 100, 566, 72, "b", WHITE, cl(pr * 2.5), sc=lerp(1.08, 1.0, cl(e)))
        line(c, 104, 590, 104 + tw("religion.", 72, "b") - 12, 590, eo3(p(t, 82.7, .3)), CREAM, 1, 3)
    group(c, a, f, dy=dy)

# 13 — home -> academy route (replaces the old locator)
@cue("route", 88.0, 92.62, LEFT, sfx=[("whoosh_soft", 89.3, -24)])
def _(c, t):
    a = eo3(p(t, 88.05, .35)) * (1 - ei2(p(t, 92.2, .35)))
    dy = (1 - eo3(p(t, 88.05, .35))) * 16 - ei2(p(t, 92.2, .35)) * 30
    def f():
        glass(c, 64, 360, 560, 190, 28)
        xa, xb, y = 120, 568, 470
        line(c, xa, y, xb, y, eio2(p(t, 88.3, 1.0)), CREAM, .55, 3)
        dot(c, xa, y, 10, CREAM)
        dot(c, xb, y, 10, CREAM, eo3(p(t, 89.1, .3)))
        text(c, "Home", xa, y + 50, 24, "m", CREAM, 1, anchor="l")
        text(c, "Academy", xb, y + 50, 24, "m", CREAM, eo3(p(t, 89.1, .3)), anchor="r")
        tr = sio(p(t, 89.3, 1.6))
        if t > 89.3:
            dot(c, lerp(xa, xb, tr), y, 7, ACCENT)
        text(c, "15 km", (xa + xb) / 2, y - 26, 22, "b", WHITE, eo3(p(t, 90.1, .4)), anchor="c")
    group(c, a, f, dy=dy)

# 16 — generations: no one had a formal education, then the first
@cue("generations", 162.3, 168.55, LEFT, sfx=[("pluck", 165.61, -20)])
def _(c, t):
    a, dy = card_env(t, 162.32, 168.15)
    def f():
        glass(c, 64, 300, 470, 300, 28)
        rows = (("Grandparents", 4), ("Parents", 6), ("Us", 5))
        for k, (lab, n) in enumerate(rows):
            y = 370 + k * 80
            ap = eo3(p(t, 162.45 + k * .09, .3))
            text(c, lab, 96, y + 7, 18, "m", MUTED, ap)
            for j in range(n):
                xx = 268 + j * 40
                lit = (k == 2 and j == 0)
                if lit:
                    lp = p(t, 165.61, .35)
                    r = 11 * (bo(lp, 1.7) if lp > 0 else 1)
                    dot(c, xx, y, r, mix((.40, .40, .40), ACCENT, cl(lp * 1.5)), ap)
                    if lp > 0:
                        rp = eo3(p(t, 165.61, .6))
                        ring(c, xx, y, 11 + 14 * rp, ACCENT, .8 * (1 - .4 * rp) * ap, 2)
                else:
                    dot(c, xx, y, 9, (.40, .40, .40), ap)
        text(c, "Formal education", 96, 575, 16, "m", MUTED, eo3(p(t, 165.9, .4)))
        dot(c, 268, 570, 6, ACCENT, eo3(p(t, 165.9, .4)))
    group(c, a, f, dy=dy)

@cue("hopes", 184.1, 192.85, LEFT, sfx=[("thud_heavy", 189.88, -14)])
def _(c, t):
    a, dy = card_env(t, 184.15, 192.5)
    group(c, a, lambda: weight_stack(c, t, [("Expectations", 189.53)]), dy=dy)

@cue("cant_fail", 195.0, 196.45, LEFT, sfx=[("boom", 195.0, -14)])
def _(c, t):
    stamp(c, t, "I can't", None, None, 195.0, 196.4, 195.0)

# 19 — the lone dot
@cue("lone_dot", 196.6, 205.88, (180, 340, 260, 260))
def _(c, t):
    a = sio(p(t, 196.7, .8)) * (1 - p(t, 205.4, .45))
    def f():
        disc(c, 1)
        ring(c, *DISC, 58, CREAM, .18, 1.5)
        dot(c, *DISC, 10, (.62, .62, .62))
    group(c, a, f)

@cue("labels", 218.05, 232.0, LEFT, sfx=[("stamp", 218.16, -18), ("stamp", 219.2, -17), ("stamp", 223.36, -16),
                                        ("drain", 224.32, -22), ("swell_rev", 225.68, -22)])
def _(c, t):
    out = 1 - p(t, 231.3, .5)
    away = p(t, 225.68, .6)
    items = (("Fearful", 218.16, -.035), ("Negative", 219.2, .03), ("Shy", 223.36, -.02))
    for k, (lab, at, rot) in enumerate(items):
        if t < at:
            continue
        sp = eo4(p(t, at, .18))
        ka = cl((1 - p(t, 225.68 + k * .06, .6)) * 1.0)
        yy = 300 + k * 70 + ei2(p(t, 225.68 + k * .06, .6)) * 140
        group(c, ka * out, lambda: chip(c, 96, yy, lab), sc=lerp(1.15, 1.0, sp), cx=200, cy=yy + 27, rot=rot * sp)
    if t >= 223.9:
        ma = eo3(p(t, 223.9, .3)) * (1 - p(t, 225.86, .6))
        frac = .6 * (1 - ei2(p(t, 224.32, .8)))
        yy = 520 + ei2(p(t, 225.86, .6)) * 140
        group(c, ma * out, lambda: meter(c, 96, yy, frac, ACCENT))
    if t >= 226.2:
        ga = sio(p(t, 226.2, .8)) * out
        def ball():
            gx, gy = 300, 440
            g = cairo.RadialGradient(gx, gy, 10, gx, gy, 120)
            g.add_color_stop_rgba(0, *CREAM, .30)
            g.add_color_stop_rgba(1, *CREAM, 0)
            c.arc(gx, gy, 120, 0, 2 * math.pi)
            c.set_source(g)
            c.fill()
            bg = cairo.RadialGradient(gx - 14, gy - 16, 4, gx, gy, 44)
            bg.add_color_stop_rgb(0, .85, .32, .22)
            bg.add_color_stop_rgb(1, .52, .12, .09)
            c.arc(gx, gy, 44, 0, 2 * math.pi)
            c.set_source(bg)
            c.fill()
            c.save()
            c.arc(gx, gy, 44, 0, 2 * math.pi)
            c.clip()
            c.set_source_rgba(*CREAM, .85)
            c.set_line_width(2)
            for off in (-5, 5):
                c.arc(gx - 62 + off, gy + 62 + off, 80, -math.pi * .6, math.pi * .1)
                c.stroke()
            c.restore()
        group(c, ga, ball, sc=lerp(.9, 1, eo3(p(t, 226.2, .8))), cx=300, cy=440)

# 22 — studies vs cricket
@cue("scores", 232.0, 253.6, LEFT, sfx=[("whoosh_air", 232.2, -26), ("dip", 248.78, -20)])
def _(c, t):
    a, dy = card_env(t, 232.05, 253.25)
    def f():
        glass(c, 64, 250, 440, 400, 28)
        ninth = eo3(p(t, 245.49, .35))
        text(c, "Year 1", 96, 300, 20, "m", MUTED, 1 - ninth)
        text(c, "Class 9", 96, 300, 20, "m", MUTED, ninth)
        base, top = 580, 360
        drop = eio2(p(t, 248.78, 1.0))
        sv = lerp(.85, .61, drop)
        cols = (("Studies", 150, sv, mix(CREAM, ACCENT, drop)), ("Cricket", 330, .9, CREAM))
        for k, (lab, x, v, col) in enumerate(cols):
            rise = eo3(p(t, 232.3 + .12 * k, .7))
            h = (base - top) * v * rise
            rrect(c, x, base - 220, 90, 220, 12)
            c.set_source_rgba(1, 1, 1, .07)
            c.fill()
            if h > 1:
                rrect(c, x, base - h, 90, h, 12)
                c.set_source_rgba(*col, 1)
                c.fill()
            text(c, lab, x + 45, base + 34, 20, "m", CREAM, 1, anchor="c")
        if t > 239.2:
            ap = eo3(p(t, 239.39, .3))
            if drop <= 0:
                lab = "80s"
            else:
                lab = f"{int(round(lerp(80, 61, drop)))}%"
            text(c, lab, 195, base - 220 * sv - 18, 30, "b", mix(WHITE, ACCENT, drop), ap, anchor="c")
    group(c, a, f, dy=dy)

@cue("boards", 256.4, 259.95, LEFT, sfx=[("thud_heavy", 258.3, -17)])
def _(c, t):
    a, dy = card_env(t, 256.42, 259.6)
    group(c, a, lambda: weight_stack(c, t, [("Expectations", 0.0), ("Class 10 boards", 257.95)]), dy=dy)

# 24 — relatives' voices
BUBBLES = [("Padhai pe dhyan do", 261.15, 110, 190, 1), ("Lakhs of kids play cricket", 263.55, 1330, 150, -1),
           ("Boards hai is saal", 266.0, 90, 470, 1), ("Cricket se kya milega?", 268.5, 1320, 420, -1),
           ("Engineering ka socho", 270.3, 1360, 640, -1)]
@cue("bubbles", 261.1, 274.35, (60, 120, 1860, 640), sfx=[("pop_ui", b[1], -21 + k) for k, b in enumerate(BUBBLES)] +
     [("whoosh_dry", 274.05, -20)])
def _(c, t):
    mess = p(t, 273.15, .6)
    col = ei3(p(t, 274.05, .25))
    rnd = random.Random(int(t * FPS))
    for k, (txt, at, x, y, side) in enumerate(BUBBLES):
        if t < at:
            continue
        pr = p(t, at, .3)
        e = bo(pr, 1.8)
        jx = jy = 0
        if mess > 0:
            jx, jy = rnd.uniform(-3, 3) * mess, rnd.uniform(-3, 3) * mess
        w = tw(txt, 28, "m") + 52
        cx, cy = (x + (34 if side > 0 else w - 34), y + 90)
        sc = max(.001, e * (1 - col))
        group(c, cl(pr * 3) * (1 - .35 * mess) * (1 - col), lambda: bubble(c, x, y, txt, side),
              dx=jx, dy=jy, sc=sc, cx=cx, cy=cy)

@cue("papa", 277.5, 284.35, LEFT, sfx=[("pluck", 277.6, -22)])
def _(c, t):
    a = sio(p(t, 277.55, .5)) * (1 - p(t, 283.8, .5))
    dy = (1 - sio(p(t, 277.55, .5))) * 10
    group(c, a, lambda: bubble(c, 96, 400, "Continue.", 1, fill=CREAM, col=INK, size=40, tag="PAPA"), dy=dy)

# 26 — no rest in between (hard cut at 302.25)
@cue("no_rest", 296.9, 302.25, LEFT, sfx=[("tick_soft", 297.26, -26), ("tick_soft", 298.94, -26), ("tick", 301.3, -22)])
def _(c, t):
    a = eo3(p(t, 296.95, .35))
    def f():
        glass(c, 64, 380, 600, 140, 28)
        labels = ("School", "Cricket", "School", "Cricket")
        gap = lerp(26, 0, ei3(p(t, 300.2, 1.2)))
        bw = 128
        total = 4 * bw + 3 * gap
        x = 364 - total / 2
        for k, lab in enumerate(labels):
            ap = eo3(p(t, 297.26 + .45 * k, .3))
            yy = 420 + (1 - ap) * 14
            rrect(c, x, yy, bw, 60, 14)
            if k % 2 == 0:
                c.set_source_rgba(.42, .41, .40, ap)
                c.fill()
                text(c, lab, x + bw / 2, yy + 39, 22, "m", WHITE, ap, anchor="c")
            else:
                c.set_source_rgba(*CREAM, ap)
                c.fill()
                text(c, lab, x + bw / 2, yy + 39, 22, "m", INK, ap, anchor="c")
            x += bw + gap
    sq = 1 + .03 * math.sin(math.pi * p(t, 301.4, .2))
    group(c, a, f, sc=sq, cx=364, cy=450)

# 27 — “responsible” callback (replaces cue 131)
@cue("responsible", 310.15, 312.65, LEFT, sfx=[("click", 310.65, -22), ("click", 310.78, -24)])
def _(c, t):
    a, dy = card_env(t, 310.16, 312.3)
    def f():
        glass(c, 64, 370, 520, 160, 28)
        text(c, "responsible", 324, 472, 56, "b", WHITE, anchor="c")
        wd = tw("responsible", 56, "b")
        for qx, ch, at in ((324 - wd / 2 - 26, "“", 310.65), (324 + wd / 2 + 4, "”", 310.78)):
            pr = p(t, at, .35)
            if pr > 0:
                e = bo(pr, 1.6)
                text(c, ch, qx, 488 - 40 * (1 - e), 64, "b", CREAM, cl(pr * 3), sc=lerp(1.3, 1, cl(e)))
    group(c, a, f, dy=dy)

@cue("ruler_a", 323.9, 327.47, LEFT, sfx=[("tick", 324.4, -26)])
def _(c, t):
    a = eo3(p(t, 323.95, .4))
    cm = lerp(135, 150, eo3(p(t, 324.0, .6)))
    group(c, a, lambda: ruler(c, t, cm, 0))

@cue("ruler_b", 329.74, 342.1, LEFT, sfx=[("tick", 331.3, -26)])
def _(c, t):
    cm = lerp(150, 170, eio2(p(t, 329.9, 1.4)))
    ex = eo3(p(t, 331.3, .45))
    ruler(c, t, cm, ex)

# 30 — matches watched (TV b-roll 343.11 ->)
@cue("matches", 343.3, 348.8, TOPR, sfx=[("tick", 343.84, -24)])
def _(c, t):
    a, dy = env(t, 343.35, 348.45, .35, .3, rise=8)
    def f():
        x, y, w = 1440, 50, 420
        glass(c, x, y, w, 170, 24)
        text(c, "Matches watched", x + 26, y + 40, 20, "m", MUTED)
        for k in range(3):
            cx = x + 70 + k * 140
            ap = eo3(p(t, 343.84 + .2 * k, .3))
            text(c, "0", cx, y + 118, 56, "b", CREAM, ap, anchor="c")
            text(c, f"Year {k + 1}", cx, y + 150, 16, "m", MUTED, ap, anchor="c")
    group(c, a, f, dy=dy)

@cue("loc_college", 354.7, 358.0, TOPR, sfx=[("tick", 354.75, -24)])
def _(c, t):
    locator(c, "First year of college, 2016", t, 354.75, 3.2)

# 32 — ticket stub
@cue("ticket", 358.8, 365.3, LEFT, sfx=[("paper_slide", 359.0, -22), ("paper_tear", 362.8, -18)])
def _(c, t):
    a = eo3(p(t, 358.85, .4)) * (1 - p(t, 364.6, .5))
    dx = (1 - eo3(p(t, 358.85, .4))) * -60
    tear = ei2(p(t, 362.8, .5))
    def body():
        x, y, w, h = 90, 380, 380, 170
        rrect(c, x, y, w, h, 14)
        c.set_source_rgb(.94, .91, .84)
        c.fill()
        text(c, "CINEMA", x + 24, y + 38, 14, "b", MUTED)
        text(c, "M.S. Dhoni:", x + 24, y + 82, 30, "b", INK)
        text(c, "The Untold Story", x + 24, y + 116, 26, "m", INK)
        text(c, "2016", x + 24, y + 150, 18, "m", (.45, .42, .38))
        c.set_source_rgba(.45, .42, .38, .6)
        c.set_line_width(2)
        c.set_dash([6, 6])
        c.move_to(x + w, y + 12)
        c.line_to(x + w, y + h - 12)
        c.stroke()
        c.set_dash([])
    def stub():
        x, y, w, h = 470, 380, 110, 170
        rrect(c, x, y, w, h, 14)
        c.set_source_rgb(.94, .91, .84)
        c.fill()
        text(c, "ADMIT", x + w / 2, y + 78, 15, "b", INK, anchor="c")
        text(c, "ONE", x + w / 2, y + 100, 15, "b", INK, anchor="c")
    def f():
        group(c, 1, body)
        group(c, 1 - tear * .9, stub, dy=tear * 220, dx=tear * 30, rot=tear * .25, cx=470, cy=380)
    group(c, a, f, dx=dx, rot=-.05, cx=330, cy=465)

# 34 — call pill (top-centre, over the poster)
@cue("call", 384.9, 419.0, (900, 20, 600, 130))
def _(c, t):
    grow = eo3(p(t, 385.0, .45))
    ended = p(t, 418.22, .15)
    coll = ei3(p(t, 418.45, .35))
    cx, y = 1180, 46
    full = 340
    w = max(64, full * grow * (1 - coll) + 64 * coll)
    a = cl(grow * 3) * (1 - p(t, 418.75, .2))
    def f():
        rrect(c, cx - w / 2, y, w, 64, 32)
        c.set_source_rgba(*mix((.05, .05, .055), (.42, .09, .05), ended), .92)
        c.fill()
        ax = cx - w / 2 + 32
        if t < 388.45:
            for k in range(2):
                ph = ((t - 385.0) / .8 + k * .5) % 1
                ring(c, ax, y + 32, 18 + 18 * ph, CREAM, .5 * (1 - ph), 2)
        dot(c, ax, y + 32, 18, mix(CREAM, ACCENT, ended))
        text(c, "C", ax, y + 40, 20, "b", INK, 1, anchor="c")
        if w > 200:
            ia = cl((w - 200) / 100)
            text(c, "Coach", ax + 34, y + 30, 22, "m", WHITE, ia)
            if t < 388.45:
                sub = "calling…"
            elif ended > 0:
                sub = "Call ended"
            else:
                s = int(t - 388.45)
                sub = f"{s // 60:02d}:{s % 60:02d}"
            text(c, sub, ax + 34, y + 52, 16, "m", ACCENT if ended > 0 else MUTED, ia)
    group(c, a, f)

@cue("over100", 392.4, 395.9, LEFT, sfx=[("riser_soft", 393.6, -22)])
def _(c, t):
    a, dy = card_env(t, 392.45, 395.5)
    def f():
        glass(c, 64, 390, 560, 150, 28)
        fr = eo3(p(t, 392.6, 1.4)) * 1.2
        x0, w = 96, 380
        rrect(c, x0, 480, w, 16, 8)
        c.set_source_rgba(1, 1, 1, .1)
        c.fill()
        c.set_source_rgba(*CREAM, .35)
        c.set_line_width(2)
        c.set_dash([5, 5])
        c.move_to(x0 + w, 488)
        c.line_to(x0 + w * 1.2, 488)
        c.stroke()
        c.set_dash([])
        if fr > 0:
            rrect(c, x0, 480, w * min(fr, 1), 16, 8)
            c.set_source_rgb(*CREAM)
            c.fill()
        if fr > 1:
            rrect(c, x0 + w - 8, 480, w * (fr - 1) + 8, 16, 8)
            c.set_source_rgb(*ACCENT)
            c.fill()
        line(c, x0 + w, 468, x0 + w, 508, 1, WHITE, .7, 2)
        text(c, "100", x0 + w, 462, 14, "m", MUTED, 1, anchor="c")
        text(c, f"{int(round(fr * 100))}%", x0, 452, 44, "b", WHITE)
    group(c, a, f, dy=dy)

# 36 — coach quote (replaces cues 170-171), hard cut on the hang-up
@cue("coach_quote", 413.55, 418.3, LEFT)
def _(c, t):
    def f():
        glass(c, 64, 330, 640, 270, 28)
        text(c, "“", 92, 430, 90, "b", CREAM, .6)
        for k, ln in enumerate(("Abhi, don't make sense", "to take that much risk.”")):
            ap = eo3(p(t, 413.6 + k * .25, .4))
            text(c, ln, 140, 430 + k * 54 + (1 - ap) * 8, 38, "m", WHITE, ap)
        text(c, "— Coach", 140, 555, 22, "m", MUTED, eo3(p(t, 414.2, .3)))
    f()

# 37 — door closing on the ground b-roll (422.64-425.64)
@cue("door", 422.64, 425.64, (0, 0, 1920, 1080), sfx=[("knock_soft", 425.05, -18)])
def _(c, t):
    pr = eio2(p(t, 422.7, 2.4))
    w = 650 * pr
    c.rectangle(0, 0, w, 1080)
    c.rectangle(1920 - w, 0, w, 1080)
    c.set_source_rgb(0, 0, 0)
    c.fill()

@cue("takeaway", 430.6, 433.8, TOPL, sfx=[("whoosh_soft", 430.6, -24), ("tick", 430.65, -24)])
def _(c, t):
    pill(c, 64, 64, "The takeaway", t, 430.65, 433.45)

@cue("dont_quit", 434.3, 441.95, LEFT, sfx=[("scratch", 438.23, -20)])
def _(c, t):
    a, dy = card_env(t, 434.35, 441.6)
    def f():
        glass(c, 64, 390, 480, 140, 28)
        text(c, "Don't quit.", 100, 480, 56, "b", MUTED)
        strike(c, 100, 100 + tw("Don't quit.", 56, "b"), 462, eo3(p(t, 438.23, .25)), 1, 6)
    group(c, a, f, dy=dy)

# 40 — payoff (replaces cue 185)
@cue("okay_fail", 446.85, 452.7, LEFT, sfx=[("boom", 446.87, -15), ("swell_rev", 449.4, -20)])
def _(c, t):
    a = 1 - p(t, 452.0, .6)
    group(c, a, lambda: stamp(c, t, "I can't", "It's okay to", 448.95, 446.87, 460, 446.87))

@cue("everywhere", 461.2, 478.75, LEFT, sfx=[("tap", 461.45, -24), ("tap", 467.0, -24), ("tap", 467.85, -24), ("tap", 470.6, -24)])
def _(c, t):
    a, dy = card_env(t, 461.25, 478.4)
    at = (461.35, 466.87, 467.75, 470.53)
    def f():
        glass(c, 64, 380, 560, 160, 28)
        xs = [126 + k * 130 for k in range(4)]
        for k in range(4):
            icon(c, k, xs[k], 455, eo3(p(t, at[k], .3)))
        cur = 0
        for k in range(4):
            if t >= at[k]:
                cur = k
        if t >= at[0] + .1:
            prev = max(0, cur - 1)
            hp = eio2(p(t, at[cur] + .1, .35)) if cur > 0 else 1
            x0, x1 = xs[prev] + 40, xs[cur] + 40
            hx = lerp(x0, x1, hp)
            hy = 412 - math.sin(math.pi * hp) * 28 if cur > 0 else 412
            sh = eo3(p(t, 476.05, .6))
            if sh > 0:
                g = cairo.RadialGradient(hx, hy, 2, hx, hy, 34)
                g.add_color_stop_rgba(0, *ACCENT, .45 * sh)
                g.add_color_stop_rgba(1, *ACCENT, 0)
                c.arc(hx, hy, 34, 0, 2 * math.pi)
                c.set_source(g)
                c.fill()
            dot(c, hx, hy, 8, ACCENT, eo3(p(t, at[0] + .1, .3)))
    group(c, a, f, dy=dy)

# 42 — two dots (gone before the zenith at 496.34)
@cue("two_dots", 488.7, 496.2, (180, 340, 260, 260), sfx=[("pluck", 490.0, -22)])
def _(c, t):
    a = sio(p(t, 488.75, .4)) * (1 - p(t, 495.4, .8))
    tr = sio(p(t, 489.0, 1.2))
    def f():
        disc(c, 1)
        gx = DISC[0] - 22 * tr
        dot(c, gx, DISC[1], 10, (.62, .62, .62))
        cxp = lerp(DISC[0] + 140, DISC[0] + 22, tr)
        dot(c, cxp, DISC[1], 10, CREAM, cl(tr * 3))
        rr = eo3(p(t, 490.2, .6))
        if rr > 0:
            c.save()
            c.translate(*DISC)
            c.scale(lerp(1, 1.0, rr), lerp(1, .62, rr))
            ring(c, 0, 0, 58, CREAM, .2 + .45 * rr, 2 / lerp(1, .8, rr))
            c.restore()
        else:
            ring(c, *DISC, 58, CREAM, .18, 1.5)
    group(c, a, f)

# 44 — what fear cost
@cue("cost", 514.6, 521.6, LEFT, sfx=[("drop", 517.3, -22), ("drop", 520.6, -24)])
def _(c, t):
    for k, (lab, at, fall) in enumerate((("Cricket", 514.65, 517.3), ("Confidence", 514.8, 520.6))):
        ap = eo3(p(t, at, .25))
        fp = ei2(p(t, fall, .6))
        yy = 400 + k * 72
        group(c, ap * (1 - fp), lambda: chip(c, 96, yy, lab), dy=fp * 300, rot=fp * .26, cx=200, cy=yy + 27)

# 45 — next episode: meter refills, an audience appears
DOTS = [(112 + col * 26 + (row % 2) * 13, 600 + row * 26) for row in range(6) for col in range(12 - (1 if row % 2 else 0))]
@cue("next_ep", 522.6, 532.348, (20, 20, 760, 800), sfx=[("tick", 522.65, -24), ("riser", 525.0, -24), ("shimmer", 531.05, -22)])
def _(c, t):
    pill(c, 64, 64, "Next episode", t, 522.65, 600, tag="EP 3")
    ma = eo3(p(t, 523.3, .35))
    fr = eo3(p(t, 524.73, 1.2))
    group(c, ma, lambda: meter(c, 96, 420, fr, CREAM))
    if t > 530.85:
        ca = eo3(p(t, 530.9, .3))
        def aud():
            rrect(c, 96, 560, 360, 200, 22)
            c.set_source_rgba(.07, .07, .075, .84)
            c.fill()
            for (x, y) in DOTS:
                d = math.hypot(x - 276, y - 560)
                dp = eo3(p(t, 531.05 + d / 220 * .9, .3))
                dot(c, x, y, 6, CREAM, .9 * dp)
        group(c, ca, aud, dy=(1 - ca) * 14)

# 46 — end card: tagline lifted to leave room for end-screen elements
@cue("endcard", 532.348, 540.348, (200, 220, 1520, 460))
def _(c, t):
    c.rectangle(200, 220, 1520, 460)
    c.set_source_rgb(0, 0, 0)
    c.fill()
    a = sio(p(t, 532.9, 1.2)) * (1 - sio(p(t, 538.3, 1.1)))
    y = lerp(470, 330, eio2(p(t, 533.6, .8)))
    text(c, "Become Someone You're Proud Of", 960, y, 52, "r", (.95, .95, .95), a, anchor="c")
    text(c, "— Shoaib Khan", 960, y + 62, 22, "r", (.75, .75, .75), a * eo3(p(t, 534.2, .6)), anchor="c")
