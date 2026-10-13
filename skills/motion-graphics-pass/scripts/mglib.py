"""mglib — drawing primitives, the cue registry and the sprite renderer for the
motion-graphics pass. Imported by mgx.py and by each episode's <edit>/mgx/cues.py
(`from mglib import *`). Design space is 1920x1080; S scales it to the output.
See ../SKILL.md."""
import json, math, os, sys, subprocess, random
import numpy as np, cairo
from PIL import Image, ImageFont, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
EDIT = os.environ.get("MGX_EDIT", "")          # set by mgx.py before cues.py is imported
WORK = os.environ.get("MGX_WORK", "")          # <edit>/mgx by default
FPS = 30000 / 1001                             # set_fps() from the master
RATE = "30000/1001"
S = float(os.environ.get("MG_S", "2"))         # design units (1920x1080) -> output pixels
FONTS = {}                                     # {"r","m","b"} -> font file (+ "#index" for .ttc)

def set_fps(fps, rate=None):
    global FPS, RATE
    FPS = fps
    RATE = rate or RATE

def set_fonts(**kw):
    """set_fonts(r=..., m=..., b=...) — paths, or "path.ttc#index"."""
    FONTS.update(kw)
    _tc.clear()

def find_system_fonts():
    """Helvetica Neue Regular/Medium/Bold from the macOS system .ttc, matched by style name."""
    for ttc in ("/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Helvetica Neue.ttc"):
        if not os.path.exists(ttc):
            continue
        want = {"Regular": "r", "Medium": "m", "Bold": "b"}
        for i in range(20):
            try:
                fam, style = ImageFont.truetype(ttc, 20, index=i).getname()
            except Exception:
                break
            if style in want and want[style] not in FONTS:
                FONTS[want[style]] = f"{ttc}#{i}"
        if all(k in FONTS for k in "rmb"):
            return True
    return False

def _font(w, px):
    spec = FONTS[w]
    path, _, idx = spec.partition("#")
    return ImageFont.truetype(path, px, index=int(idx or 0))

WHITE = (0.93, 0.93, 0.92)
CREAM = (222 / 255, 211 / 255, 189 / 255)
MUTED = (138 / 255, 131 / 255, 117 / 255)
ACCENT = (242 / 255, 84 / 255, 53 / 255)
INK = (0.11, 0.105, 0.10)

# ---------------------------------------------------------------- easing
def cl(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def p(t, a, d): return cl((t - a) / d) if d > 0 else (1.0 if t >= a else 0.0)
def eo3(x): return 1 - (1 - x) ** 3
def eo4(x): return 1 - (1 - x) ** 4
def ei2(x): return x * x
def ei3(x): return x * x * x
def eio2(x): return 2 * x * x if x < .5 else 1 - (-2 * x + 2) ** 2 / 2
def sio(x): return -(math.cos(math.pi * x) - 1) / 2
def bo(x, s=1.6):
    c3 = s + 1
    return 1 + c3 * (x - 1) ** 3 + s * (x - 1) ** 2
def lerp(a, b, x): return a + (b - a) * x
def mix(c1, c2, x): return tuple(lerp(a, b, x) for a, b in zip(c1, c2))

def env(t, tin, tout, din=.35, dout=.3, rise=14):
    i = eo3(p(t, tin, din))
    o = ei2(p(t, tout, dout)) if tout is not None else 0.0
    return i * (1 - o), (1 - i) * rise - o * rise * .5

# ---------------------------------------------------------------- drawing
_tc = {}
def tsurf(txt, size, w="m", color=WHITE):
    key = (txt, size, w, color, S)
    if key in _tc:
        return _tc[key]
    f = _font(w, max(1, int(round(size * S))))
    asc, desc = f.getmetrics()
    adv = f.getlength(txt)
    pad = 4
    W, H = int(math.ceil(adv)) + 2 * pad + 4, asc + desc + 2 * pad
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad, pad), txt, font=f, fill=tuple(int(c * 255) for c in color) + (255,))
    a = np.asarray(im).astype(np.float32)
    al = a[..., 3:4] / 255.0
    bgra = np.empty(a.shape, np.uint8)
    bgra[..., 0] = (a[..., 2] * al[..., 0]).astype(np.uint8)
    bgra[..., 1] = (a[..., 1] * al[..., 0]).astype(np.uint8)
    bgra[..., 2] = (a[..., 0] * al[..., 0]).astype(np.uint8)
    bgra[..., 3] = a[..., 3].astype(np.uint8)
    bgra = np.ascontiguousarray(bgra)
    surf = cairo.ImageSurface.create_for_data(memoryview(bgra), cairo.FORMAT_ARGB32, W, H, W * 4)
    o = dict(s=surf, buf=bgra, pad=pad / S, asc=(asc + pad) / S, adv=adv / S, h=(asc + desc) / S)
    _tc[key] = o
    return o

def tw(txt, size, w="m"):
    return tsurf(txt, size, w)["adv"]

def text(c, txt, x, y, size, w="m", color=WHITE, alpha=1.0, anchor="l", sc=1.0, rot=0.0):
    """y is the baseline."""
    o = tsurf(txt, size, w, color)
    if alpha <= 0.002:
        return o
    ax = {"l": 0, "c": o["adv"] / 2, "r": o["adv"]}[anchor]
    c.save()
    c.translate(x, y)
    if rot:
        c.rotate(rot)
    if sc != 1.0:
        c.scale(sc, sc)
    c.translate(-ax - o["pad"], -o["asc"])
    c.scale(1 / S, 1 / S)
    c.set_source_surface(o["s"], 0, 0)
    c.paint_with_alpha(min(1.0, alpha))
    c.restore()
    return o

def rrect(c, x, y, w, h, r):
    r = max(0, min(r, w / 2, h / 2))
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    c.close_path()

def glass(c, x, y, w, h, r=28, a=1.0, tint=None):
    if a <= 0.002:
        return
    for g, al in ((22, .045), (12, .06), (5, .08)):
        rrect(c, x - g, y - g + 8, w + 2 * g, h + 2 * g, r + g)
        c.set_source_rgba(0, 0, 0, al * a)
        c.fill()
    rrect(c, x, y, w, h, r)
    gr = cairo.LinearGradient(0, y, 0, y + h)
    top, bot = (.18, .18, .19), (.075, .075, .08)
    if tint:
        top, bot = mix(top, tint, .25), mix(bot, tint, .18)
    gr.add_color_stop_rgba(0, *top, .80 * a)
    gr.add_color_stop_rgba(1, *bot, .86 * a)
    c.set_source(gr)
    c.fill_preserve()
    c.set_source_rgba(1, 1, 1, .10 * a)
    c.set_line_width(1.2)
    c.stroke()

def group(c, alpha, fn, dx=0.0, dy=0.0, sc=1.0, cx=0.0, cy=0.0, rot=0.0):
    if alpha <= 0.002:
        return
    c.save()
    c.translate(dx, dy)
    if sc != 1.0 or rot:
        c.translate(cx, cy)
        if rot:
            c.rotate(rot)
        c.scale(sc, sc)
        c.translate(-cx, -cy)
    c.push_group()
    fn()
    c.pop_group_to_source()
    c.paint_with_alpha(min(1.0, alpha))
    c.restore()

def line(c, x0, y0, x1, y1, pr, color, a=1.0, wdt=4.0):
    if pr <= 0 or a <= 0:
        return
    c.set_source_rgba(*color, a)
    c.set_line_width(wdt)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(x0, y0)
    c.line_to(lerp(x0, x1, pr), lerp(y0, y1, pr))
    c.stroke()

def strike(c, x0, x1, y, pr, a=1.0, wdt=5.0):
    line(c, x0 - 6, y + 4, x1 + 6, y - 4, pr, ACCENT, a, wdt)

def dot(c, x, y, r, color, a=1.0):
    if a <= 0 or r <= 0:
        return
    c.arc(x, y, r, 0, 2 * math.pi)
    c.set_source_rgba(*color, a)
    c.fill()

def ring(c, x, y, r, color, a=1.0, wdt=2.0):
    if a <= 0 or r <= 0:
        return
    c.arc(x, y, r, 0, 2 * math.pi)
    c.set_source_rgba(*color, a)
    c.set_line_width(wdt)
    c.stroke()

def pill(c, x, y, label, t, tin, tout, tag=None, dotc=ACCENT):
    a, dy = env(t, tin, tout, .4, .3, rise=0)
    dx = (1 - eo3(p(t, tin, .4))) * -24 - ei2(p(t, tout, .3)) * 24
    wd = 30 + 22 + tw(label, 26, "m") + 26 + (tw(tag, 16, "m") + 30 if tag else 0)
    def f():
        glass(c, x, y, wd, 60, 30)
        dot(c, x + 30, y + 30, 6, dotc)
        text(c, label, x + 50, y + 39, 26, "m", CREAM)
        if tag:
            tx = x + 50 + tw(label, 26, "m") + 18
            rrect(c, tx, y + 15, tw(tag, 16, "m") + 24, 30, 15)
            c.set_source_rgba(*CREAM, .14)
            c.fill()
            text(c, tag, tx + 12, y + 36, 16, "m", CREAM, .9)
    group(c, a, f, dx=dx)

def locator(c, txt, t, tin, dur):
    a, dy = env(t, tin, tin + dur - .3, .35, .3, rise=8)
    w = tw(txt, 32, "r") + 32
    def f():
        rrect(c, 1882 - w, 38, w, 65, 3)
        c.set_source_rgba(0, 0, 0, .52)
        c.fill()
        text(c, txt, 1882 - 16, 82, 32, "r", (1, 1, 1), anchor="r")
    group(c, a, f, dy=dy)

def card_env(t, tin, tout, din=.35, dout=.3):
    return env(t, tin, tout, din, dout, rise=16)


# ---------------------------------------------------------------- shared components

CUES = []
LEFT = (20, 140, 760, 690)       # left-third sprite box (design units)
TOPL = (20, 20, 760, 140)
TOPR = (1240, 20, 680, 230)
QPAD = 30                        # padding either side of a word that gets quote marks
DISC = (310, 470)                # where the lone-dot / two-dot motif sits

def cue(name, t0, t1, box, sfx=()):
    def deco(fn):
        CUES.append(dict(name=name, t0=t0, t1=t1, box=box, fn=fn, sfx=list(sfx)))
        return fn
    return deco

def kinetic(c, t, lines, size, y0, gap, tout, acc=(), w="m", pad=()):
    o = ei2(p(t, tout, .3))
    pos = {}
    for li, words in enumerate(lines):
        sp = tw(" ", size, w)
        total = sum(tw(wd, size, w) + (2 * QPAD if wd in pad else 0) for wd, _ in words) + sp * (len(words) - 1)
        x = 960 - total / 2
        for wd, tt in words:
            if wd in pad:
                x += QPAD
            a = eo3(p(t, tt - .04, .45)) * (1 - o)
            col = ACCENT if wd in acc else WHITE
            text(c, wd, x, y0 + li * gap + (1 - eo3(p(t, tt - .04, .45))) * 14, size, w, col, a)
            pos[wd] = (x, x + tw(wd, size, w), y0 + li * gap)
            x += tw(wd, size, w) + sp + (QPAD if wd in pad else 0)
    return pos

# weight stack shared by 17 / 23
def weight_stack(c, t, slabs):
    """slabs: list of (label, drop_time). Hopes tile sinks a little per landed slab."""
    landed = sum(eo3(p(t, dt, .6)) for _, dt in slabs)
    base_y = 520 + 40 * landed
    sq = 1.0
    for _, dt in slabs:
        if t > dt + .35:
            ip = p(t, dt + .35, .3)
            sq = min(sq, 1 - .06 * math.sin(math.pi * ip) * (1 - ip))
    c.save()
    c.translate(310, base_y + 90)
    c.scale(1, sq)
    c.translate(-310, -(base_y + 90))
    glass(c, 140, base_y, 340, 90, 22, tint=CREAM)
    text(c, "Hopes", 310, base_y + 58, 36, "m", CREAM, anchor="c")
    c.restore()
    top = base_y
    for k, (lab, dt) in enumerate(slabs):
        fp = ei3(p(t, dt, .35))
        if fp <= 0:
            continue
        h = 66
        y_rest = top - h - 4
        y = lerp(y_rest - 260, y_rest, fp)
        rrect(c, 130, y, 360, h, 14)
        c.set_source_rgba(.06, .06, .065, .94 * cl(fp * 3))
        c.fill_preserve()
        c.set_source_rgba(1, 1, 1, .08 * cl(fp * 3))
        c.set_line_width(1.2)
        c.stroke()
        text(c, lab, 310, y + 42, 24, "m", MUTED, cl(fp * 3), anchor="c")
        top = y_rest

# 18 — the stamp (replaces cue 85)
def stamp(c, t, l1, l1b, swap_at, show, hide, shake_at):
    if t < show or t >= hide:
        return
    sh = 0
    if 0 <= t - shake_at < 2 / FPS:
        sh = 3 if int((t - shake_at) * FPS) % 2 == 0 else -3
    c.save()
    c.translate(sh, 0)
    rrect(c, 64, 330, 540, 250, 28)
    c.set_source_rgba(.06, .06, .065, .86)
    c.fill()
    if swap_at is None:
        text(c, l1, 100, 430, 72, "b", WHITE)
        text(c, "fail.", 100, 525, 72, "b", ACCENT)
    else:
        sp = eo3(p(t, swap_at, .25))
        xf = eo3(p(t, swap_at + .45, .6))
        text(c, l1, 100, 430, 72, "b", WHITE, 1 - xf)
        if xf < 1:
            strike(c, 100, 100 + tw(l1, 72, "b"), 404, sp, 1 - xf, 7)
        if xf > 0:
            c.save()
            c.rectangle(90, 340, (tw(l1b, 64, "b") + 30) * xf, 120)
            c.clip()
            text(c, l1b, 100, 430, 64, "b", WHITE)
            c.restore()
        col = mix(ACCENT, CREAM, eio2(p(t, swap_at + .45, .8)))
        text(c, "fail.", 100, 525, 72, "b", col)
    c.restore()

def disc(c, a):
    c.arc(*DISC, 92, 0, 2 * math.pi)
    c.set_source_rgba(.06, .06, .065, .62 * a)
    c.fill()
    c.arc(*DISC, 92, 0, 2 * math.pi)
    c.set_source_rgba(1, 1, 1, .08 * a)
    c.set_line_width(1.2)
    c.stroke()

# 20/21 — labels, empty meter, the kid underneath (patch cues 95, 97)
def chip(c, x, y, txt, a=1.0, col=CREAM):
    w = tw(txt, 28, "m") + 44
    rrect(c, x, y, w, 54, 27)
    c.set_source_rgba(.07, .07, .075, .84 * a)
    c.fill_preserve()
    c.set_source_rgba(*col, .35 * a)
    c.set_line_width(1.5)
    c.stroke()
    text(c, txt, x + 22, y + 37, 28, "m", col, a)
    return w

def meter(c, x, y, frac, col, a=1.0, label="Confidence"):
    rrect(c, x, y, 360, 92, 22)
    c.set_source_rgba(.07, .07, .075, .84 * a)
    c.fill()
    text(c, label, x + 22, y + 36, 22, "m", CREAM, a)
    text(c, f"{int(round(frac * 100))}%", x + 338, y + 36, 22, "b", col, a, anchor="r")
    rrect(c, x + 22, y + 56, 316, 14, 7)
    c.set_source_rgba(1, 1, 1, .10 * a)
    c.fill()
    if frac > 0.003:
        rrect(c, x + 22, y + 56, 316 * frac, 14, 7)
        c.set_source_rgba(*col, a)
        c.fill()

def bubble(c, x, y, txt, side, a=1.0, fill=(.97, .96, .93), col=INK, size=28, tag=None):
    w = tw(txt, size, "m") + 52
    h = 70 if not tag else 96
    rrect(c, x, y, w, h, 24)
    tx = x + 34 if side > 0 else x + w - 34
    c.move_to(tx - 12, y + h - 2)
    c.line_to(tx + 12 * side - 4 * side, y + h + 20)
    c.line_to(tx + 14, y + h - 2)
    c.close_path()
    c.set_source_rgba(*fill, .96 * a)
    c.fill()
    if tag:
        text(c, tag, x + 26, y + 34, 16, "m", MUTED, a)
        text(c, txt, x + 26, y + 74, size, "b", col, a)
    else:
        text(c, txt, x + 26, y + 46, size, "m", col, a)
    return w

# 28/29 — height ruler (hidden for the height-chart b-roll 327.47-329.74)
def ruler(c, t, cm, extra):
    x, y0, y1 = 64, 200, 740
    glass(c, x, y0 - 40, 330, y1 - y0 + 80, 28)
    def ypos(v): return lerp(y1, y0, (v - 130) / 50)
    for v in range(130, 181, 5):
        yy = ypos(v)
        L = 26 if v % 10 == 0 else 14
        line(c, x + 40, yy, x + 40 + L, yy, 1, CREAM, .55, 2)
        if v % 10 == 0:
            text(c, str(v), x + 78, yy + 8, 20, "m", MUTED)
    ym = ypos(cm)
    line(c, x + 120, ym, x + 200, ym, 1, ACCENT, 1, 4)
    text(c, f"{int(round(cm))} cm", x + 210, ym + 10, 28, "b", WHITE)
    if extra > 0:
        yb = ypos(150)
        line(c, x + 120, yb, x + 180, yb, 1, CREAM, .5 * extra, 2)
        bx = x + 300
        c.set_source_rgba(*CREAM, extra)
        c.set_line_width(2.5)
        c.move_to(bx - 12, yb)
        c.line_to(bx, yb)
        c.line_to(bx, lerp(yb, ypos(170), extra))
        c.line_to(bx - 12, lerp(yb, ypos(170), extra))
        c.stroke()
        text(c, "+20 cm", x + 210, (yb + ypos(170)) / 2 + 26, 24, "b", ACCENT, extra)
        text(c, "in 1 year", x + 210, (yb + ypos(170)) / 2 + 56, 18, "m", MUTED, extra)

# 41 — icons + fear dot
def icon(c, k, x, y, a):
    c.set_source_rgba(*CREAM, a)
    c.set_line_width(3)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    if k == 0:   # bat
        c.save()
        c.translate(x, y)
        c.rotate(-.6)
        rrect(c, -9, -6, 18, 40, 6)
        c.move_to(0, -6)
        c.line_to(0, -30)
        c.stroke()
        c.restore()
    elif k == 1:  # desk
        c.move_to(x - 30, y - 6); c.line_to(x + 30, y - 6)
        c.move_to(x - 24, y - 6); c.line_to(x - 24, y + 26)
        c.move_to(x + 24, y - 6); c.line_to(x + 24, y + 26)
        c.stroke()
        rrect(c, x - 12, y - 26, 24, 16, 3)
        c.stroke()
    elif k == 2:  # speech bubble
        rrect(c, x - 28, y - 24, 56, 40, 12)
        c.stroke()
        c.move_to(x - 10, y + 16); c.line_to(x - 16, y + 28); c.line_to(x + 2, y + 16)
        c.stroke()
    else:         # door
        rrect(c, x - 18, y - 30, 36, 60, 3)
        c.stroke()
        dot(c, x + 9, y + 2, 3, CREAM, a)


# ---------------------------------------------------------------- render
def frames_of(cu):
    f0 = int(round(cu["t0"] * FPS))
    f1 = int(round(cu["t1"] * FPS))
    return f0, max(f0 + 1, f1)

def draw_frame(cu, t):
    x, y, w, h = cu["box"]
    W, H = int(round(w * S)) // 2 * 2, int(round(h * S)) // 2 * 2
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    c.scale(S, S)
    c.translate(-x, -y)
    cu["fn"](c, t)
    surf.flush()
    return surf, W, H

def unpremul(surf, W, H):
    a = np.ndarray((H, surf.get_stride() // 4, 4), np.uint8, surf.get_data())[:, :W].astype(np.uint16)
    al = a[..., 3:4]
    rgb = np.where(al > 0, np.minimum(255, (a[..., :3] * 255 + al // 2) // np.maximum(al, 1)), 0)
    return np.concatenate([rgb, al], axis=2).astype(np.uint8)

def render(cu, outdir):
    f0, f1 = frames_of(cu)
    x, y, w, h = cu["box"]
    _, W, H = draw_frame(cu, f0 / FPS)
    path = f"{outdir}/{cu['name']}.mov"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                           "-r", RATE, "-i", "-", "-c:v", "qtrle", "-pix_fmt", "argb", path], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        surf, W, H = draw_frame(cu, f / FPS)
        ff.stdin.write(unpremul(surf, W, H).tobytes())
    ff.stdin.close()
    ff.wait()
    return dict(name=cu["name"], file=path, x=int(round(x * S)) // 2 * 2, y=int(round(y * S)) // 2 * 2,
                start=f0 / FPS, frames=f1 - f0, sfx=cu["sfx"])

def render_name(name, outdir):
    return render(next(cu for cu in CUES if cu["name"] == name), outdir)

