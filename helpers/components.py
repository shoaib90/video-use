"""Motion graphic components: the archetypes a script actually asks for.

Each one corresponds to a row of the taxonomy in `script_scan.py`, which came
from reading a reference edit frame by frame against its own script. They are
built on `motion.WEIGHTS` rather than on raw durations, so a hero number and a
supporting caption cannot accidentally animate the same way — which is the
specific thing that made an earlier hand-rolled attempt read as amateur.

Everything is sized from the output height, so one definition is correct at
720p and 2160p.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    from . import motion as mo
    from .brand import Brand
except ImportError:                       # loaded as a plain file
    import importlib.util as _ilu
    import sys as _sys

    def _load(name, fn):
        sp = _ilu.spec_from_file_location(name, Path(__file__).with_name(fn))
        m = _ilu.module_from_spec(sp)
        _sys.modules[name] = m
        sp.loader.exec_module(m)
        return m

    mo = _load("video_use_motion", "motion.py")
    Brand = _load("video_use_brand", "brand.py").Brand


# -------- text ----------------------------------------------------------------


def rgba(hexstr: str, alpha: float = 1.0):
    h = hexstr.lstrip("#")
    if len(h) == 8:
        r, g, b, a = (int(h[i:i + 2], 16) for i in (0, 2, 4, 6))
    else:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        a = 255
    return (r, g, b, int(a * alpha))


def load_font(brand: Brand, weight: str, size: int) -> ImageFont.FreeTypeFont:
    path, idx = {
        "light": (brand.font_light, brand.font_light_index),
        "regular": (brand.font_regular, brand.font_regular_index),
        "bold": (brand.font_bold, brand.font_bold_index),
        "intl": (brand.font_intl, brand.font_intl_index),
    }[weight]
    return ImageFont.truetype(path, max(6, size), index=idx)


def needs_intl(text: str) -> bool:
    """Any non-Latin character forces the international face: drawtext and PIL
    both draw a blank box rather than falling back."""
    return any(ord(c) > 0x024F for c in text)


def text_width(d: ImageDraw.ImageDraw, font, s: str, tracking_px: float) -> float:
    if not s:
        return 0.0
    return sum(d.textlength(c, font=font) + tracking_px for c in s) - tracking_px


def draw_tracked(d: ImageDraw.ImageDraw, xy, s: str, font, fill, tracking_px: float):
    x, y = xy
    for c in s:
        d.text((x, y), c, font=font, fill=fill)
        x += d.textlength(c, font=font) + tracking_px


# -------- base -----------------------------------------------------------------


@dataclass
class Component:
    """Times are ABSOLUTE output times, not relative.

    An earlier version took a relative `duration` while `draw` received an
    absolute `t`, so a component placed 11 s into the timeline computed its own
    exit fade as long finished and silently drew nothing. Absolute in, absolute
    out - there is no offset to get wrong.
    """
    brand: Brand
    height: int                      # output height, for sizing
    data: dict = field(default_factory=dict)
    start: float = 0.0
    end: float = 4.0
    fade_out: float = 0.42

    def __post_init__(self):
        self.b = self.brand
        self.pad = self.b.px(self.b.shadow_blur, self.height)

    def _out(self, t: float) -> float:
        """Exit envelope: 1 while live, ramping to 0 at `end`."""
        if t >= self.end:
            return 0.0
        return 1.0 - mo.clamp01((t - (self.end - self.fade_out)) / self.fade_out)

    def fit_size(self, lines, base_size: int, max_w: int, weight="light") -> int:
        """Largest size at which every line fits. Type that overflows the canvas
        is clipped by the pad, silently, and reads as a broken render."""
        probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
        budget = max_w - self.pad * 3          # room for the drop shadow
        size = base_size
        while size > base_size * 0.40:
            f = load_font(self.b, weight, size)
            tr = size * self.b.tracking
            if max(text_width(probe, f, str(l).upper(), tr) for l in lines) <= budget:
                break
            size -= 2
        return size

    # -- helpers shared by every component
    def _shadowed(self, img: Image.Image, fn):
        """Draw once into a blurred dark layer and once on top. Type over live
        footage needs this or it dies on a bright background."""
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        fn(ImageDraw.Draw(sh), True)
        sh = sh.filter(ImageFilter.GaussianBlur(max(2, self.pad)))
        img.alpha_composite(sh)
        fn(ImageDraw.Draw(img), False)

    def draw(self, img: Image.Image, t: float) -> None:
        raise NotImplementedError


# -------- big number ------------------------------------------------------------


@dataclass
class BigNumber(Component):
    """A figure that is the point of the sentence.

    `hero` weight: it springs, it travels, it overshoots and settles, and it
    earns motion blur. A number that fades in reads as a caption, not a claim.
    The count-up is deliberately short — long counters are a cliche and steal
    attention from the line being spoken.
    """

    def draw(self, img, t):
        b, H = self.b, self.height
        w = mo.WEIGHTS["hero"]
        p = w.at(t, start=self.start)
        if p <= 0.001:
            return
        out = self._out(t)
        if out <= 0:
            return

        value = self.data.get("value")
        display = str(self.data.get("display", value or ""))
        label = str(self.data.get("label", ""))
        # count up over the first 60% of the reveal, then hold
        if isinstance(value, (int, float)) and value:
            cp = mo.CURVES["ease_out_expo"](
                mo.clamp01((t - self.start) / (w.duration * 0.85)))
            shown = int(value * cp)
            if "-" in display:
                display = display.split("-")[0] if cp < 1 else self.data["display"]
            else:
                display = f"{shown:,}"

        size = b.px(b.size_display, H)
        font = load_font(b, "intl" if needs_intl(display) else "bold", size)
        tr = size * b.tracking * 0.5
        scale = w.scale_from + (1 - w.scale_from) * p
        dy = w.travel * size * (1 - p)

        d0 = ImageDraw.Draw(img)
        tw = text_width(d0, font, display, tr)
        x = (img.width - tw) / 2
        y = img.height * 0.30 + dy

        def paint(d, shadow):
            fill = (0, 0, 0, int(b.shadow_alpha * p * out)) if shadow \
                else rgba(b.fg, p * out)
            off = self.pad if shadow else 0
            draw_tracked(d, (x + off, y + off), display, font, fill, tr)
        self._shadowed(img, paint)

        if label:
            lsize = b.px(b.size_body, H)
            lfont = load_font(b, "light", lsize)
            ltr = lsize * b.tracking
            lp = mo.WEIGHTS["secondary"].at(t, start=self.start + 0.18)
            ld = ImageDraw.Draw(img)
            lw = text_width(ld, lfont, label.upper(), ltr)
            draw_tracked(ld, ((img.width - lw) / 2,
                              y + size * 1.16 + mo.WEIGHTS["secondary"].travel * lsize * (1 - lp)),
                         label.upper(), lfont, rgba(b.accent, lp * out), ltr)


# -------- chips -----------------------------------------------------------------


def _chip(img, d, brand, height, text, cx, cy, p, out, filled, scale=1.0):
    size = int(brand.px(brand.size_body, height) * scale)
    font = load_font(brand, "intl" if needs_intl(text) else "bold", size)
    tr = size * brand.tracking
    tw = text_width(d, font, text, tr)
    padx, pady = size * 0.62, size * 0.42
    w, h = tw + padx * 2, size * 1.34 + pady
    r = min(h / 2, brand.px(brand.radius, height) * 2)
    x0, y0 = cx - w / 2, cy - h / 2
    a = p * out
    if filled:
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=r,
                            fill=rgba(brand.accent, a))
        fg = rgba("#FFFFFF", a)
    else:
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=r,
                            fill=rgba(brand.chip_bg, a * 0.85),
                            outline=rgba(brand.fg, a * 0.55),
                            width=max(1, brand.px(brand.stroke, height)))
        fg = rgba(brand.fg, a)
    draw_tracked(d, (x0 + padx, y0 + pady * 0.42), text, font, fg, tr)
    return x0, y0, w, h


@dataclass
class OpposingChips(Component):
    """Two things the script says are not the same.

    They arrive from opposite sides — the motion itself carries the contrast —
    and the second is deliberately late so the pair reads as a comparison
    rather than a pair of labels. The left one is filled, the right outlined,
    which is hierarchy rather than symmetry.
    """

    def draw(self, img, t):
        b, H = self.b, self.height
        out = self._out(t)
        if out <= 0:
            return
        w = mo.WEIGHTS["primary"]
        left = str(self.data.get("left", "")).strip().upper()
        right = str(self.data.get("right", "")).strip().upper()
        cy = img.height * 0.5
        travel = w.travel * b.px(b.size_body, H) * 6

        d = ImageDraw.Draw(img)
        for i, (txt, filled, sign) in enumerate(((left, True, -1), (right, False, 1))):
            if not txt:
                continue
            p = w.at(t, start=self.start + mo.stagger(i, per=0.16))
            if p <= 0.001:
                continue
            cx = img.width * (0.26 if sign < 0 else 0.74) + sign * travel * (1 - p)
            _chip(img, d, b, H, txt, cx, cy, p, out, filled)


# -------- staggered list ---------------------------------------------------------


@dataclass
class StaggeredList(Component):
    """An enumeration, an attribute series, or numbered principles.

    Three things make this read as designed rather than as a list:

    * items arrive on their own spoken word where one is given, otherwise on a
      stagger that accelerates, so the group is one gesture and not a queue;
    * every item that is NOT the newest drops to the muted colour, so there is
      always exactly one focus — hierarchy, the first design pillar;
    * the last item can take the accent, because a list usually has a payoff.
    """

    def draw(self, img, t):
        b, H = self.b, self.height
        out = self._out(t)
        if out <= 0:
            return
        items = self.data.get("items") or []
        times = self.data.get("times")          # per-item reveal, output-relative
        numbered = bool(self.data.get("numbered"))
        accent_last = bool(self.data.get("accent_last", True))
        heading = self.data.get("heading")

        size = self.fit_size(items, b.px(b.size_title if len(items) <= 4
                                         else b.size_body, H),
                             img.width - (b.px(b.size_body, H) * 2 if numbered else 0))
        line_h = int(size * 1.62)
        w = mo.WEIGHTS["primary"]
        y0 = (img.height - line_h * len(items)) / 2
        d0 = ImageDraw.Draw(img)

        if heading:
            hs = b.px(b.size_caption, H)
            hf = load_font(b, "bold", hs)
            hp = mo.WEIGHTS["secondary"].at(t, start=self.start)
            draw_tracked(d0, (0, y0 - hs * 2.6), str(heading).upper(), hf,
                         rgba(b.accent, hp * out), hs * b.tracking * 2)

        # which item is newest at time t — everything older dims
        starts = [(times[i] if times and i < len(times)
                   else self.start + mo.stagger(i, b.stagger_per, 1.25))
                  for i in range(len(items))]
        newest = max((i for i, s in enumerate(starts) if t >= s), default=-1)

        for i, item in enumerate(items):
            p = w.at(t, start=starts[i])
            if p <= 0.001:
                continue
            text = str(item).upper()
            font = load_font(b, "intl" if needs_intl(text) else "light", size)
            tr = size * b.tracking
            dy = w.travel * size * (1 - p)
            y = y0 + i * line_h + dy
            x = 0.0
            focus = (i == newest)
            col = b.accent if (accent_last and i == len(items) - 1 and focus) else \
                (b.fg if focus else b.muted)
            # dimming is itself animated, or the drop reads as a glitch
            dim = 1.0 if focus else 0.55 + 0.45 * mo.clamp01((starts[min(i + 1, len(starts) - 1)] + 0.5 - t))

            if numbered:
                ns = int(size * 0.72)
                nf = load_font(b, "bold", ns)
                badge = b.px(b.size_body, H)
                d0.rounded_rectangle(
                    [x, y + size * 0.06, x + badge * 1.5, y + size * 0.06 + badge * 1.5],
                    radius=b.px(b.radius, H), fill=rgba(b.accent, p * out * dim))
                nw = d0.textlength(str(i + 1), font=nf)
                d0.text((x + badge * 0.75 - nw / 2, y + size * 0.06 + badge * 0.28),
                        str(i + 1), font=nf, fill=rgba("#FFFFFF", p * out))
                x += badge * 2.1

            def paint(d, shadow, _x=x, _y=y, _t=text, _f=font, _tr=tr, _p=p, _c=col, _dim=dim):
                fill = (0, 0, 0, int(b.shadow_alpha * _p * out)) if shadow \
                    else rgba(_c, _p * out * _dim)
                off = self.pad if shadow else 0
                draw_tracked(d, (_x + off, _y + off), _t, _f, fill, _tr)
            self._shadowed(img, paint)


# -------- kinetic type ------------------------------------------------------------


@dataclass
class KineticType(Component):
    """An emphatic line, set at mixed scale rather than as a caption.

    The reference sets the stressed words large and the connective words small,
    scattered rather than aligned, and composites the speaker in front. Size is
    the emphasis, so the words carry meaning before they are read.
    """

    def draw(self, img, t):
        b, H = self.b, self.height
        out = self._out(t)
        if out <= 0:
            return
        # [(text, scale, x_frac, y_frac, role)]
        words = self.data.get("words") or []
        times = self.data.get("times")
        base = b.px(b.size_title, H)
        d0 = ImageDraw.Draw(img)
        for i, spec in enumerate(words):
            text = str(spec.get("text", "")).upper()
            if not text:
                continue
            role = spec.get("role", "primary")
            w = mo.WEIGHTS[role]
            start = (times[i] if times and i < len(times)
                     else self.start + mo.stagger(i, b.stagger_per, 1.2))
            p = w.at(t, start=start)
            if p <= 0.001:
                continue
            face = ("intl" if needs_intl(text)
                    else "bold" if spec.get("scale", 1) >= 1.3 else "light")
            x_frac = float(spec.get("x", 0.1))
            # fit within whatever width remains to the right of its own anchor
            avail = img.width * (1 - x_frac) if not spec.get("center") else img.width
            size = self.fit_size([text], int(base * float(spec.get("scale", 1.0))),
                                 int(avail), weight=face)
            font = load_font(b, face, size)
            tr = size * b.tracking
            tw = text_width(d0, font, text, tr)
            x = img.width * x_frac - (tw / 2 if spec.get("center") else 0)
            y = img.height * float(spec.get("y", 0.5)) + w.travel * size * (1 - p)
            col = b.accent if spec.get("accent") else b.fg

            def paint(d, shadow, _x=x, _y=y, _t=text, _f=font, _tr=tr, _p=p, _c=col):
                fill = (0, 0, 0, int(b.shadow_alpha * _p * out)) if shadow \
                    else rgba(_c, _p * out)
                off = self.pad if shadow else 0
                draw_tracked(d, (_x + off, _y + off), _t, _f, fill, _tr)
            self._shadowed(img, paint)


REGISTRY = {
    "big_number": BigNumber,
    "opposing_chips": OpposingChips,
    "staggered_items": StaggeredList,
    "list_carousel": StaggeredList,
    "numbered_badge": StaggeredList,
    "kinetic_type": KineticType,
}


def build(component: str, brand: Brand, height: int, data: dict,
          start: float, end: float) -> Component:
    cls = REGISTRY.get(component)
    if cls is None:
        raise KeyError(f"unknown component {component!r}; "
                       f"have {sorted(REGISTRY)}")
    return cls(brand=brand, height=height, data=data, start=start, end=end)


# -------- sliding carousel --------------------------------------------------------


@dataclass
class SlidingCarousel(Component):
    """An enumeration walked through one item at a time.

    This is the reference's treatment for "there are five lanes… first… second…":
    a horizontal strip that SLIDES, with a giant ghosted numeral behind each
    item and dashed dividers between them. Neighbours stay partly visible, which
    is what tells the viewer this is a list being traversed rather than a series
    of unrelated cards.

    The slide is `ease_in_out` — a carousel that overshoots reads as a glitch,
    where a single element landing wants exactly that overshoot. Different jobs,
    different curves.
    """

    def draw(self, img, t):
        b, H = self.b, self.height
        out = self._out(t)
        if out <= 0:
            return
        items = self.data.get("items") or []
        if not items:
            return
        times = self.data.get("times") or [
            self.start + i * 1.6 for i in range(len(items))]
        slide = float(self.data.get("slide", 0.55))
        W, CH = img.width, img.height

        # which item is active, and how far through the move to it we are
        active = max((i for i, s in enumerate(times) if t >= s), default=0)
        prev = max(0, active - 1)
        moved = mo.clamp01((t - times[active]) / slide) if active else 1.0
        pos = prev + (active - prev) * mo.CURVES["ease_in_out"](moved)

        # Columns must be narrow enough that neighbours stay in frame - that
        # is what makes it read as a list being traversed rather than a series
        # of unrelated cards.
        step = W * 0.46
        col = step * 0.86
        title_size = self.fit_size([i.get("title", "") for i in items],
                                   b.px(b.size_title, H), int(col),
                                   weight="bold")
        bullet_size = int(b.px(b.size_caption, H) * 1.7)
        num_size = int(CH * 1.05)
        d0 = ImageDraw.Draw(img)

        for i, item in enumerate(items):
            cx = W / 2 + (i - pos) * step
            if cx < -step or cx > W + step:
                continue
            near = 1.0 - min(1.0, abs(i - pos))          # 1 when centred
            alpha = out * (0.28 + 0.72 * near)
            appeared = mo.WEIGHTS["secondary"].at(t, start=times[i] - 0.25)
            left = cx - col / 2

            # Giant ghosted numeral: bottom-anchored and very faint, so the
            # copy sits clear of it. At readable opacity it fights the bullets
            # instead of sitting behind them.
            nf = load_font(b, "bold", num_size)
            ns = str(i + 1)
            nw = d0.textlength(ns, font=nf)
            d0.text((cx - nw / 2, CH - num_size * 0.80), ns, font=nf,
                    fill=rgba(b.fg, out * (0.035 + 0.055 * near)))

            if i < len(items) - 1:
                dx = cx + step / 2
                dash, gap = CH * 0.028, CH * 0.020
                y = CH * 0.06
                while y < CH * 0.94:
                    d0.line([(dx, y), (dx, min(y + dash, CH * 0.94))],
                            fill=rgba(b.muted, out * 0.26 * (0.3 + 0.7 * near)),
                            width=max(1, b.px(b.stroke, H)))
                    y += dash + gap

            title = str(item.get("title", "")).upper()
            tf = load_font(b, "intl" if needs_intl(title) else "bold", title_size)
            tr = title_size * b.tracking
            ty = CH * 0.13 + mo.WEIGHTS["primary"].travel * title_size * (1 - appeared)
            col_fg = b.accent if near > 0.72 else (b.fg if near > 0.35 else b.muted)

            def paint(d, shadow, _x=left, _y=ty, _t=title, _f=tf, _tr=tr,
                      _a=alpha, _c=col_fg):
                fill = (0, 0, 0, int(b.shadow_alpha * _a)) if shadow \
                    else rgba(_c, _a)
                off = self.pad if shadow else 0
                draw_tracked(d, (_x + off, _y + off), _t, _f, fill, _tr)
            self._shadowed(img, paint)

            bullets = item.get("bullets") or []
            bf = load_font(b, "light", bullet_size)
            btr = bullet_size * b.tracking * 0.5
            for k, bl in enumerate(bullets):
                bp = mo.WEIGHTS["aside"].at(
                    t, start=times[i] + mo.stagger(k, b.stagger_per * 1.5))
                if bp <= 0.01:
                    continue
                by = ty + title_size * 2.0 + k * bullet_size * 1.62
                draw_tracked(d0, (left, by), str(bl), bf,
                             rgba(b.muted, alpha * bp * 0.95), btr)


REGISTRY["sliding_carousel"] = SlidingCarousel
REGISTRY["list_carousel"] = SlidingCarousel      # the reference's own treatment
