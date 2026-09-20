"""Declarative on-screen text graphics: titles, lower thirds, chapter cards.

Why this exists as a first-class thing rather than a hand-written `drawtext`:

1. **Anchors, not timestamps.** A graphic is pinned to a *source*, a *segment* or
   a *spoken phrase*, and its output time is resolved from the measured segment
   durations. Anything positional in the output timeline has to be measured from
   a real render — extracts are frame-quantised, so summed EDL floats drift — and
   a hardcoded time additionally rots the moment any earlier range changes. On
   the edit this was built for, a late round of cut repairs moved every boundary
   by ~9 s; anchored cues re-resolved correctly with no re-measurement.

2. **Resolution independence.** Every size is a fraction of the output height, so
   one entry is correct in a 720p draft and a 2160p final. A hardcoded pixel size
   is only right at one output height.

3. **Escaping.** The text goes through `textfile=`, never `text=`. Filter values
   are comma- and colon-delimited and are also read through a shell in some
   paths; Devanagari, apostrophes and commas in a title all break `text=` in
   different ways. A file sidesteps every one of them.

Graphics are drawn AFTER overlays and BEFORE subtitles, so captions stay on top
of them (Hard Rule 1).

EDL block:

    "graphics": [
      {"type": "title", "text": "Quick fit check",
       "anchor": {"source": "b-roll1"}, "offset": 0.35, "duration": 2.8,
       "position": "top-right"},
      {"type": "lower_third", "text": "Shoaib", "subtitle": "HSR to Filter Coffee",
       "anchor": {"word": "my name is"}, "duration": 4.0}
    ]
"""
from __future__ import annotations

import json
from pathlib import Path

# Sizes are fractions of the output HEIGHT; see the module docstring.
TYPE_DEFAULTS = {
    "title": {
        "font_frac": 1 / 30,
        "margin_frac": 1 / 20,
        "position": "top-right",
        "box": True,
        "fade": 0.45,
        "duration": 3.0,
    },
    "chapter": {
        "font_frac": 1 / 14,
        "margin_frac": 1 / 12,
        "position": "center",
        "box": False,
        "fade": 0.6,
        "duration": 3.0,
    },
    "lower_third": {
        "font_frac": 1 / 24,
        "sub_font_frac": 1 / 40,
        "margin_frac": 1 / 22,
        "y_frac": 0.70,
        "box": True,
        "fade": 0.45,
        "duration": 4.0,
    },
}

DEFAULT_FONT = "/System/Library/Fonts/Helvetica.ttc"
DEFAULT_COLOR = "white"
DEFAULT_BOX_COLOR = "black@0.40"

# x/y expressions per named position. `tw`/`th` are the rendered text box.
POSITIONS = {
    "top-left": ("{m}", "{m}"),
    "top-right": ("w-tw-{m}", "{m}"),
    "top-center": ("(w-tw)/2", "{m}"),
    "bottom-left": ("{m}", "h-th-{m}"),
    "bottom-right": ("w-tw-{m}", "h-th-{m}"),
    "bottom-center": ("(w-tw)/2", "h-th-{m}"),
    "center": ("(w-tw)/2", "(h-th)/2"),
}


_WARNED_UNCHECKED: list[bool] = []      # warn once per process, not per entry


class GraphicsError(ValueError):
    """An unusable `graphics` entry. Raised rather than skipped: a title that
    silently does not appear is worse than a render that refuses to start."""


# -------- anchor resolution --------------------------------------------------


def _segment_starts(segment_durations: list[float]) -> list[float]:
    starts, t = [], 0.0
    for d in segment_durations:
        starts.append(t)
        t += d
    return starts


def _word_time(edl: dict, edit_dir: Path, starts: list[float], phrase: str) -> float | None:
    """Output time of the first kept word sequence matching `phrase`.

    Matched against the words each range actually keeps, using the same overlap
    test the caption builder uses, so an anchor can never resolve to a word that
    was cut.
    """
    needle = " ".join(phrase.lower().split())
    cache: dict[str, list[dict]] = {}
    for i, r in enumerate(edl.get("ranges", [])):
        key = r["source"]
        if key not in cache:
            f = Path(edit_dir) / "transcripts" / f"{key}.json"
            if not f.exists():
                cache[key] = []
            else:
                cache[key] = [w for w in json.loads(f.read_text()).get("words", [])
                              if w.get("type") == "word"]
        kept = [w for w in cache[key]
                if w["end"] > r["start"] + 1e-3 and w["start"] < r["end"] - 1e-3]
        if not kept:
            continue
        texts = [w["text"].lower().strip(".,!?;:\"'") for w in kept]
        for j in range(len(texts)):
            window = " ".join(texts[j:j + len(needle.split())])
            if window == needle:
                return starts[i] + (kept[j]["start"] - r["start"])
    return None


def resolve_anchors(graphics: list[dict], edl: dict, edit_dir: Path,
                    segment_durations: list[float]) -> list[dict]:
    """Turn each entry's `anchor` into a concrete `start` in output time.

    `segment_durations` must come from the extracted segments, not from the EDL:
    an extract is quantised to whole frames, so the float sum runs early and the
    error accumulates over a long cut.
    """
    starts = _segment_starts(segment_durations)
    total = sum(segment_durations)
    out = []
    for n, g in enumerate(graphics):
        gtype = g.get("type", "title")
        if gtype not in TYPE_DEFAULTS:
            raise GraphicsError(
                f"graphics[{n}]: unknown type {gtype!r}; "
                f"expected one of {sorted(TYPE_DEFAULTS)}")
        d = dict(TYPE_DEFAULTS[gtype])
        d.update({k: v for k, v in g.items() if v is not None})

        anchor = g.get("anchor") or {}
        base: float | None = None
        if "time" in anchor:
            base = float(anchor["time"])
        elif "segment" in anchor:
            idx = int(anchor["segment"])
            if not 0 <= idx < len(starts):
                raise GraphicsError(
                    f"graphics[{n}]: segment {idx} out of range (0..{len(starts) - 1})")
            base = starts[idx]
        elif "source" in anchor:
            nth = int(anchor.get("nth", 1))
            seen = 0
            for i, r in enumerate(edl.get("ranges", [])):
                if r["source"] == anchor["source"]:
                    seen += 1
                    if seen == nth:
                        base = starts[i]
                        break
            if base is None:
                raise GraphicsError(
                    f"graphics[{n}]: source {anchor['source']!r} does not appear "
                    f"{nth} time(s) in the cut")
        elif "word" in anchor:
            base = _word_time(edl, Path(edit_dir), starts, str(anchor["word"]))
            if base is None:
                raise GraphicsError(
                    f"graphics[{n}]: phrase {anchor['word']!r} is not spoken in the cut")
        else:
            raise GraphicsError(
                f"graphics[{n}]: anchor needs one of source / segment / word / time")

        start = max(0.0, base + float(g.get("offset", 0.0)))
        dur = float(d["duration"])
        if total and start + dur > total:
            dur = max(0.1, total - start)
        d["start"], d["duration"] = round(start, 3), round(dur, 3)
        out.append(d)
    return out


# -------- filter construction ------------------------------------------------


def _escape_path(p: Path | str) -> str:
    """Escape a path for use inside an ffmpeg filter option value."""
    return str(p).replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")


def _font_opt(font: str) -> str:
    """`fontfile=` for a path, `font=` for a fontconfig family name."""
    if "/" in font or font.endswith((".ttf", ".ttc", ".otf")):
        return f"fontfile='{_escape_path(font)}'"
    return f"font='{font}'"


def missing_glyphs(font: str, text: str) -> set[str] | None:
    """Characters in `text` the font cannot draw, or None if it cannot be checked.

    The None is load-bearing. An earlier version returned an empty set when the
    font could not be inspected, which is indistinguishable from "checked, all
    present" — so in an environment without fontTools the guard silently became
    a no-op while still reading as a clean result. "Could not check" and
    "nothing missing" must not be the same value.

    `drawtext` does NOT fall back to another face the way libass does for
    subtitles — whatever the chosen font lacks is rendered as tofu, silently, in
    an otherwise perfect file. Measured on macOS with "HSR -> बढ़िया":

        Helvetica      Latin fine, Devanagari tofu
        Kohinoor       both correct          <- the one to use for mixed script
        DevanagariMT   Devanagari fine, Latin tofu

    A `.ttc` collection is checked at face 0, because that is the face
    `fontfile=` selects; drawtext exposes no face index.
    """
    p = Path(font)
    if not p.is_file():
        return None                       # fontconfig family name; can't inspect
    try:
        from fontTools.ttLib import TTCollection, TTFont
        if p.suffix.lower() == ".ttc":
            with TTCollection(str(p), lazy=True) as coll:
                cmap = coll.fonts[0].getBestCmap()
        else:
            with TTFont(str(p), lazy=True, fontNumber=0) as f:
                cmap = f.getBestCmap()
    except Exception:
        return None                       # no fontTools, or an unreadable face
    return {ch for ch in text
            if not ch.isspace() and ord(ch) not in cmap}


def _alpha_expr(start: float, end: float, fade: float) -> str:
    """Linear fade in and out, clamped so a short graphic still shows."""
    fade = max(0.0, min(fade, (end - start) / 2))
    if fade <= 0.01:
        return "1"
    return (f"if(lt(t,{start + fade:.3f}),(t-{start:.3f})/{fade:.3f},"
            f"if(lt(t,{end - fade:.3f}),1,({end:.3f}-t)/{fade:.3f}))")


def _drawtext(textfile: Path, font: str, size: int, color: str, x: str, y: str,
              start: float, end: float, fade: float,
              box: bool, box_color: str, box_pad: int) -> str:
    parts = [
        f"drawtext=textfile='{_escape_path(textfile)}'",
        _font_opt(font),
        f"fontsize={size}",
        f"fontcolor={color}",
        f"x={x}", f"y={y}",
        f"enable='between(t,{start:.3f},{end:.3f})'",
        f"alpha='{_alpha_expr(start, end, fade)}'",
    ]
    if box:
        parts += [f"box=1", f"boxcolor={box_color}", f"boxborderw={box_pad}"]
    return ":".join(parts)


def build_filters(graphics: list[dict], height: int, work_dir: Path) -> list[str]:
    """ffmpeg filter strings for resolved graphics, sized against `height`.

    Text is written to files under `work_dir` and referenced with `textfile=`,
    so nothing in the text can break the filter string.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    filters: list[str] = []

    for n, g in enumerate(graphics):
        if "start" not in g:
            raise GraphicsError(
                f"graphics[{n}]: not resolved - call resolve_anchors() first")
        text = str(g.get("text", "")).strip()
        if not text:
            raise GraphicsError(f"graphics[{n}]: empty text")

        start = float(g["start"])
        end = start + float(g["duration"])
        fade = float(g.get("fade", 0.45))
        font = g.get("font") or DEFAULT_FONT
        color = g.get("color") or DEFAULT_COLOR
        box_color = g.get("box_color") or DEFAULT_BOX_COLOR
        margin = round(height * float(g["margin_frac"]))
        size = round(height * float(g["font_frac"]))
        pad = round(size * 0.45)

        for part in (text, str(g.get("subtitle", ""))):
            gone = missing_glyphs(font, part)
            if gone is None:
                if not _WARNED_UNCHECKED:
                    print(f"  note: glyph coverage of {Path(font).name!r} could not "
                          f"be checked (no fontTools, or a fontconfig family name) - "
                          f"a missing glyph will render as a blank box")
                    _WARNED_UNCHECKED.append(True)
            elif gone:
                raise GraphicsError(
                    f"graphics[{n}]: font {Path(font).name!r} cannot draw "
                    f"{''.join(sorted(gone))!r}. drawtext does no font fallback, "
                    f"so these would render as blank boxes. Set \"font\" to a "
                    f"face covering every script in the text "
                    f"(Kohinoor.ttc covers Latin + Devanagari).")

        tf = work_dir / f"g{n:02d}_main.txt"
        tf.write_text(text, encoding="utf-8")

        if g["type"] == "lower_third":
            # Anchored at a y fraction so it clears the caption band, which sits
            # about 10% up from the bottom on a 16:9 delivery.
            y0 = round(height * float(g["y_frac"]))
            filters.append(_drawtext(tf, font, size, color, f"{margin}", f"{y0}",
                                     start, end, fade, bool(g["box"]), box_color, pad))
            sub = str(g.get("subtitle", "")).strip()
            if sub:
                sub_size = round(height * float(g["sub_font_frac"]))
                sf = work_dir / f"g{n:02d}_sub.txt"
                sf.write_text(sub, encoding="utf-8")
                filters.append(_drawtext(
                    sf, font, sub_size, color, f"{margin}",
                    f"{y0 + round(size * 1.45)}", start, end, fade,
                    bool(g["box"]), box_color, round(sub_size * 0.45)))
        else:
            pos = g.get("position", "top-right")
            if pos not in POSITIONS:
                raise GraphicsError(
                    f"graphics[{n}]: unknown position {pos!r}; "
                    f"expected one of {sorted(POSITIONS)}")
            xe, ye = POSITIONS[pos]
            filters.append(_drawtext(
                tf, font, size, color, xe.format(m=margin), ye.format(m=margin),
                start, end, fade, bool(g["box"]), box_color, pad))

    return filters
