"""Glass cards: word-anchored motion-graphic cards, rendered by HyperFrames, composited by ffmpeg.

A card is DATA in the EDL — what it says and the spoken phrase each part lands on — never a
timestamp. At render time this module:

1. **Resolves every phrase** against the words the cut actually keeps, using the MEASURED
   segment durations (extracts are frame-quantised, so summed EDL floats drift). Each phrase is
   searched after the previous one, so a repeated word ("two PM", "two fifteen") lands on the
   right occurrence. A phrase that was cut RAISES: clamping to a survivor would put the card on
   a silent frame, and nothing would look wrong in the render.
2. **Resolves all geometry in Python** — rows, scroll offsets snapped to row tops, the card
   height as it grows — so the browser runtime (`cards_runtime/glass.js`) only draws.
3. **Renders two HyperFrames passes per card** at the output's own size and frame rate: the card
   (ProRes 4444 with alpha), and its silhouette (the mask). Cached on a hash of everything that
   affects pixels.
4. **Builds the ffmpeg fragment** that render.py composites after the b-roll overlays and before
   text graphics and subtitles: the picture is blurred, cut to the mask, laid back as frosted
   glass, and the card drawn on top. Footage never goes through the browser.

Measured traps this encodes (kb/gotchas.md, "HyperFrames overlays"):
- HyperFrames' MOV is **BT.601 and untagged**; overlaid as-is on a 709 base the accent shifts
  from (242,84,53) to (255,98,50). The card stream is converted 601->709.
- One root composition per HyperFrames project, hence a separate `mask/` project.
- The static guard ignores `<script src>`, so the runtime and spec are inlined.
- Brand fonts load via `local()` system names (pixel-identical to the font files, measured), so
  no licensed font file is ever copied into a project.

EDL block (all lengths in 1080-high units; all `at` values are spoken phrases):

    "cards": [
      {"id": "routine", "kind": "list", "label": "The routine", "icon": "clock",
       "position": "top-left",
       "rows": [
         {"time": "2 PM", "text": "School ends", "at": "till two pm"},
         {"time": "2 km", "text": "Cycle to bus stand", "at": "bicycle",
          "chips": [{"text": "40°C", "at": "forty degrees"}]}
       ],
       "tag":    {"text": "Every day", "at": "on repeat"},
       "footer": {"text": "On repeat for", "at": "on repeat",
                  "value": "3 years", "value_at": "three years"},
       "out": {"word": "that routine is"}},
      {"id": "reading", "kind": "stat", "label": "Daily reading", "icon": "star",
       "position": "top-right", "stack": 0,
       "steps": [{"at": "twenty more pages", "value": "+20", "unit": "pages",
                  "tag": "this month", "accent": true},
                 {"at": "forty pages a day", "value": "40", "unit": "pages", "tag": "Now",
                  "sub": "20 pages more than June", "sub_dir": "up"}],
       "out": {"word": "and that is"}, "after": {"word": "this month"}},
      {"id": "late", "kind": "stamp", "text": "3 AM", "at": "three in the morning",
       "position": "top-right", "accent": true}
    ]

`scale` (0.4-1.0, list and stat only) shrinks the whole card toward its top corner: a compact
tracker, e.g. a three-pillar list that stays up through a scene over the talking head.

A `stamp` is one word or figure in a glass pill: it lands AS its phrase is said (no settle
lead, unlike a card), holds ~1.8 s (or exits on `out`), and is shown in caps. Use it for the
word a line turns on, 3-8 per episode, never repeating a card already on screen. Positions:
top-left, top-right or top-center; `stack` moves it down a row.

Three full-language kinds (Kallaway's look, adopted 2026-10-06; kb/storytelling.md §13):

* `keyline` — the ONE sentence an idea comes down to, typed on in the lower left with a glow
  accent bar and an optional sub-line. No glass panel: text over footage, like the reference.
  Lands as its phrase is said, holds ~3.5 s. Never running captions — one per idea.
      {"id": "k1", "kind": "keyline", "text": "Confidence is the memory of proof",
       "sub": "Not a feeling you wait for", "at": "memory of proof"}
* `deck` — the chapter device that RETURNS at every section seam: glass cards in a row, the
  finished ones dimmed, the current one centred and lit in the glow colour. Full frame, over the
  frosted, darkened picture. Define the chapters once at EDL level (`"decks": {"pillars":
  [...]}`) and point at them, or list them inline.
      {"id": "seam2", "kind": "deck", "deck": "pillars", "current": 1, "at": "second my mind"}
      "decks": {"pillars": [{"title": "Body", "icon": "bolt"}, {"title": "Mind"},
                            {"title": "Voice"}]}
  `prefix` ("Pillar", "Part"…) labels each card; default "Part".
* `annotate` — a real image (photo, screenshot, thumbnail) on the frosted, darkened picture,
  marked up as it is talked about. Each mark lands on its own phrase; `rect` is in fractions of
  the IMAGE (x, y, w, h):
      {"id": "thumb", "kind": "annotate", "image": "assets/thumb.jpg", "at": "my thumbnail",
       "title": "3 thumbnail elements",
       "marks": [{"type": "box", "rect": [0.05, 0.1, 0.4, 0.8], "at": "my face"},
                 {"type": "highlight", "rect": [0.5, 0.6, 0.45, 0.15], "at": "the views"},
                 {"type": "callout", "rect": [0.6, 0.1, 0.3, 0.3], "label": "Facial expression",
                  "side": "right", "at": "expression"}]}

Colour: these three use the brand's `glow` (default violet #8B5CF6, the purple of the set),
not `accent`, so adopting the look does not recolour the existing list/stat/stamp cards.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HF_VERSION = "0.8.105"          # pinned: a render must be reproducible
RUNTIME = Path(__file__).parent / "cards_runtime"
GSAP_URL = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"

MARGIN = 64                     # from the frame edge, 1080 units
LEAD = 0.15                     # an element is readable as its word is SAID, not after
CARD_LEAD = 0.55                # the card settles before its first word
EXIT_DUR = 0.55
HOLD = 3.0                      # default hold after the last event when no `out` is given
LIST = {"w": 600, "pad": 30, "head": 40, "head_gap": 14, "bot": 24, "foot": 72,
        "view_h": 442, "row": 64, "row_detail": 104}
STAT = {"w": 440, "h": 234, "gap": 20}
STAMP = {"h": 96, "pad": 44, "font": 52, "track": 0.04, "gap": 20, "hold": 1.8, "max_w": 1100}
# Advance widths of Helvetica Neue Bold caps, in em. The pill's width is set here, not by the
# browser, because the mask pass draws no text and must still get the identical silhouette.
# Over-estimating only adds padding; the HyperFrames check catches any clipped glyph.
_ADV = {**{c: 0.72 for c in "ABCDEFGHKNOPQRSUVXYZ"}, "I": 0.30, "J": 0.56, "L": 0.61, "M": 0.89,
        "T": 0.63, "W": 0.98, **{d: 0.58 for d in "0123456789"}, " ": 0.28, "%": 0.93, "×": 0.60,
        ".": 0.28, ",": 0.28, ":": 0.28, "-": 0.39, "–": 0.56, "'": 0.28, "&": 0.72, "+": 0.60,
        "/": 0.33, "?": 0.61, "!": 0.30, "₹": 0.60, "$": 0.58}
# bottom: above a two-line caption at the house style (MarginV=30, FontSize=15 on PlayResY 288
# = captions ~856-968 at 1080); "low" is the reference's own spot, for cuts with no burned captions
KEYLINE = {"x": 112, "bottom": 800, "bottom_low": 968, "max_w": 1250, "font": 48, "sub": 30, "hold": 3.5,
           "type_cps": 55.0, "max_chars": 90}
DECK = {"w": 340, "h": 460, "gap": 44, "visible": 5, "hold": 2.2, "max": 9}
ANNOT = {"max_w": 1500, "max_h": 720, "top": 196, "title_y": 108, "label_gap": 56, "hold": 2.5}
MARK_TYPES = ("box", "highlight", "callout")
FULL_FRAME = ("deck", "annotate")
KINDS = ("list", "stat", "stamp", "keyline", "deck", "annotate")
ICONS = {"clock", "drop", "bolt", "scale", "list", "star", None}

DEFAULT_BRAND = {"bg": "#0A0A0A", "fg": "#DED3BD", "muted": "#8A8375", "accent": "#F25435",
                 "glow": "#8B5CF6"}
DEFAULT_FONT = "Helvetica Neue"
# local() names per weight. Chrome resolves these from the installed system fonts.
FONT_FACES = {"Helvetica Neue": {400: "HelveticaNeue", 500: "HelveticaNeue-Medium",
                                 700: "HelveticaNeue-Bold"}}


class CardError(ValueError):
    """An unusable `cards` entry. Raised rather than skipped: a card that silently does not
    appear, or appears on the wrong word, is worse than a render that refuses to start."""


# -------- anchors ------------------------------------------------------------


def _norm(s: str) -> str:
    s = s.lower().replace("’", "'")
    return re.sub(r"[^\w'ऀ-ॿ]+", " ", s).strip()


def kept_words(edl: dict, edit_dir: Path, segment_durations: list[float]) -> list[tuple[float, str]]:
    """Every word the cut keeps, as (output start time, normalised text), in output order.

    Uses the same overlap test as the caption builder, so a phrase can never resolve to a word
    that was cut.
    """
    ranges = edl.get("ranges", [])
    if len(segment_durations) != len(ranges):
        raise CardError(f"{len(segment_durations)} segment durations for {len(ranges)} ranges")
    out, t, cache = [], 0.0, {}
    for r, d in zip(ranges, segment_durations):
        key = r["source"]
        if key not in cache:
            f = Path(edit_dir) / "transcripts" / f"{key}.json"
            cache[key] = ([w for w in json.loads(f.read_text()).get("words", [])
                           if w.get("type", "word") == "word"] if f.exists() else [])
        for w in cache[key]:
            if w["end"] > r["start"] + 1e-3 and w["start"] < r["end"] - 1e-3:
                text = _norm(w.get("text", w.get("word", "")))
                if text:
                    out.append((t + max(0.0, w["start"] - r["start"]), text))
        t += d
    return out


def find_phrase(words: list[tuple[float, str]], phrase: str, after: float, where: str) -> float:
    """Output time of the first occurrence of `phrase` starting at or after `after`."""
    needle = _norm(phrase).split()
    if not needle:
        raise CardError(f"{where}: empty anchor phrase")
    toks = []          # transcripts can hold "two-fifteen" as one token; match on split words
    for t, text in words:
        for part in text.split():
            toks.append((t, part))
    n = len(needle)
    for i in range(len(toks) - n + 1):
        if toks[i][0] + 1e-6 >= after and [p for _, p in toks[i:i + n]] == needle:
            return toks[i][0]
    raise CardError(f"{where}: phrase {phrase!r} is not spoken in the cut after "
                    f"{after:.2f}s (cut, misspelt, or already used by an earlier event)")


# -------- resolution ---------------------------------------------------------


def _hex_rgb(h: str) -> str:
    h = h.lstrip("#")[:6]
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def load_brand(edl: dict, edit_dir: Path) -> dict:
    cands = []
    if edl.get("brand"):
        p = Path(edl["brand"])
        cands.append(p if p.is_absolute() else Path(edit_dir) / p)
    cands += [Path(edit_dir) / "brand.json", Path(edit_dir).parent / "brand.json"]
    for p in cands:
        if p.exists():
            b = json.loads(p.read_text())
            return {**DEFAULT_BRAND, **{k: v for k, v in b.items() if k in DEFAULT_BRAND},
                    "card_font": b.get("card_font", DEFAULT_FONT), "_path": str(p)}
    return {**DEFAULT_BRAND, "card_font": DEFAULT_FONT, "_path": None}


def _list_geometry(rows: list[dict]) -> dict:
    """Row tops, scroll offsets snapped to row tops, and the card height after each row."""
    g = LIST
    view_top = g["pad"] + g["head"] + g["head_gap"]
    top = 0
    for r in rows:
        r["top"] = top
        r["h"] = g["row_detail"] if r["chips"] else g["row"]
        top += r["h"]
    for r in rows:
        need = r["top"] + r["h"] - g["view_h"]
        if need <= 0:
            r["scroll"] = 0
        else:
            snap = [q["top"] for q in rows if q["top"] >= need]
            r["scroll"] = snap[0]
        r["card_h"] = view_top + min(r["top"] + r["h"], g["view_h"]) + g["bot"]
    return {"view_top": view_top}


def stamp_width(text: str) -> int:
    """The stamp pill's width in 1080 units: measured advance widths plus tracking and padding."""
    f, track = STAMP["font"], STAMP["track"]
    em = sum(_ADV.get(ch, 0.75) for ch in text) + track * max(0, len(text) - 1)
    return int(round(em * f + 2 * STAMP["pad"]))


def deck_layout(chapters: list[dict], cur: int, prefix: str, stage_w: float, t_light: float) -> dict:
    """Card positions and states for one appearance of the chapter deck.

    The row is centred on the CURRENT chapter and shows at most `DECK["visible"]` cards, all
    fully inside the frame (a card cut by the frame edge clips its text, which the HyperFrames
    layout audit refuses). Before `t_light` the previous chapter is still lit; at `t_light` it
    goes to done and the current one lights. That hand-over is the progress the viewer reads.
    """
    w, gap = DECK["w"], DECK["gap"]
    half = DECK["visible"] // 2
    lo, hi = max(0, cur - half), min(len(chapters) - 1, cur + half)
    cx = stage_w / 2
    y = round((1080 - DECK["h"]) / 2, 3)
    cards = []
    for k in range(lo, hi + 1):
        before = "done" if k < cur - 1 else "lit" if k == cur - 1 else "next"
        after = "done" if k < cur else "lit" if k == cur else "next"
        ch = chapters[k]
        cards.append({"k": k, "x": round(cx + (k - cur) * (w + gap) - w / 2, 3), "y": y,
                      "label": f"{prefix} {k + 1}", "title": str(ch["title"]),
                      "icon": ch.get("icon"), "before": before, "after": after})
    if cards[0]["x"] < 0 or cards[-1]["x"] + w > stage_w:
        raise CardError("deck: cards do not fit the frame; lower DECK['visible']")
    return {"w": w, "h": DECK["h"], "cards": cards, "t_light": round(t_light, 3)}


def _image_data_uri(img: Path, w_px: int, h_px: int) -> str:
    """The image, scaled to the pixels it will occupy, as an inline data URI.

    Inline because HyperFrames' static guard ignores external sources in a render, and because
    the cache key then covers the image's pixels too (a replaced file re-renders the card).
    """
    import base64
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "img.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(img), "-frames:v", "1",
                        "-vf", f"scale={w_px}:{h_px}:flags=lanczos,format=rgba", str(out)],
                       check=True)
        return "data:image/png;base64," + base64.b64encode(out.read_bytes()).decode()


def annotate_layout(an: dict, stage_w: float, scale: float, loc) -> dict:
    """Fit the image, then turn each mark's image-fraction rect into stage units.

    Callouts on the left or right need room for their label, so the image narrows to leave
    it; a label is never allowed to run off the frame.
    """
    iw, ih = _dims(an["image"])
    lateral = any(m["type"] == "callout" and m.get("side", "right") in ("left", "right")
                  for m in an["marks"])
    max_w = min(ANNOT["max_w"], stage_w - 2 * (400 if lateral else 120))
    has_title = bool(an["title"])
    max_h = ANNOT["max_h"] - (0 if has_title else 0)
    k = min(max_w / iw, max_h / ih)
    dw, dh = round(iw * k, 3), round(ih * k, 3)
    x = round((stage_w - dw) / 2, 3)
    y = ANNOT["top"] if has_title else round((1080 - dh) / 2, 3)
    marks = []
    for m in an["marks"]:
        r = m["rect"]
        rx, ry, rw, rh = x + r[0] * dw, y + r[1] * dh, r[2] * dw, r[3] * dh
        mk = {"type": m["type"], "t": loc(m["w"] - LEAD),
              "x": round(rx, 3), "y": round(ry, 3), "w": round(rw, 3), "h": round(rh, 3)}
        if m["type"] == "callout":
            side, g = m.get("side", "right"), ANNOT["label_gap"]
            cxm, cym = rx + rw / 2, ry + rh / 2
            if side == "right":
                p0, p1 = (rx + rw, cym), (x + dw + g, cym)
            elif side == "left":
                p0, p1 = (rx, cym), (x - g, cym)
            elif side == "top":
                p0, p1 = (cxm, ry), (cxm, y - g)
            else:
                p0, p1 = (cxm, ry + rh), (cxm, y + dh + g)
            mk.update({"label": str(m["label"]), "side": side,
                       "line": [round(v, 3) for v in (*p0, *p1)]})
        marks.append(mk)
    src = _image_data_uri(an["image"], max(2, round(dw * scale)), max(2, round(dh * scale)))
    return {"image": {"src": src, "x": x, "y": y, "w": dw, "h": dh},
            "title": an["title"], "caption": an["caption"], "marks": marks}


def resolve(cards: list[dict], edl: dict, edit_dir: Path, segment_durations: list[float],
            out_w: int, out_h: int) -> list[dict]:
    """Turn EDL `cards` into fully resolved runtime specs, one per card."""
    words = kept_words(edl, edit_dir, segment_durations)
    total = sum(segment_durations)
    brand = load_brand(edl, edit_dir)
    scale = out_h / 1080.0
    stage_w = round(out_w / scale, 3)
    seen_ids, specs = set(), []
    for n, c in enumerate(cards):
        cid = str(c.get("id") or f"card{n}")
        where = f"cards[{n}] ({cid})"
        if not re.fullmatch(r"[A-Za-z0-9_-]+", cid):
            raise CardError(f"{where}: id must be letters, digits, - or _")
        if cid in seen_ids:
            raise CardError(f"{where}: duplicate id")
        seen_ids.add(cid)
        kind = c.get("kind")
        if kind not in KINDS:
            raise CardError(f"{where}: kind must be one of {', '.join(KINDS)}, got {kind!r}")
        if c.get("icon") not in ICONS:
            raise CardError(f"{where}: unknown icon {c.get('icon')!r}; one of {sorted(i for i in ICONS if i)}")
        pos = c.get("position", "top-left")
        if kind in ("keyline",) + FULL_FRAME:
            pos = "top-left"            # placement is fixed by the kind, not chosen
        if pos not in ("top-left", "top-right") and not (kind == "stamp" and pos == "top-center"):
            raise CardError(f"{where}: position must be top-left or top-right"
                            + (" or top-center" if kind == "stamp" else ""))

        # `scale` shrinks a list or stat card as a whole, anchored at its own top corner — a
        # compact tracker that can stay up over a talking head. Applied to a wrapper in the
        # runtime, so the entrance/exit tweens on the card itself are untouched, and the mask
        # pass runs the same wrapper, so the frosted glass stays exactly under the card.
        card_scale = float(c.get("scale", 1.0))
        if kind not in ("list", "stat") and card_scale != 1.0:
            raise CardError(f"{where}: a {kind} has no scale")
        if not 0.4 <= card_scale <= 1.0:
            raise CardError(f"{where}: scale must be between 0.4 and 1.0, got {card_scale}")

        after = 0.0
        if c.get("after"):
            after = find_phrase(words, c["after"]["word"], 0.0, f"{where} after")
        first_word = None
        events: list[float] = []

        def at(phrase, label):
            nonlocal after, first_word
            t = find_phrase(words, phrase, after, f"{where} {label}")
            after = t + 1e-3
            first_word = t if first_word is None else first_word
            events.append(t)
            return t

        spec: dict = {"id": cid, "kind": kind, "label": str(c.get("label", "")), "icon": c.get("icon"),
                      "exit_dur": EXIT_DUR}
        if kind == "list":
            rows_in = c.get("rows") or []
            if not rows_in:
                raise CardError(f"{where}: a list needs rows")
            rows = []
            for k, r in enumerate(rows_in):
                w = at(r["at"], f"rows[{k}]")
                chips = []
                for j, ch in enumerate(r.get("chips") or []):
                    chips.append({"text": ch["text"], "w": at(ch["at"], f"rows[{k}].chips[{j}]")})
                rows.append({"time": r.get("time", ""), "text": r["text"], "w": w, "chips": chips})
            geo = _list_geometry(rows)
            last_row_w = max(events)
            tag = footer = None
            after = last_row_w + 1e-3
            if c.get("tag"):
                tag = {"text": c["tag"]["text"], "w": find_phrase(words, c["tag"]["at"], after, f"{where} tag")}
                events.append(tag["w"])
            if c.get("footer"):
                f = c["footer"]
                fw = find_phrase(words, f["at"], after, f"{where} footer")
                footer = {"text": f["text"], "w": fw, "value": f.get("value")}
                events.append(fw)
                if f.get("value"):
                    footer["value_w"] = find_phrase(words, f.get("value_at", f["at"]), fw, f"{where} footer value")
                    events.append(footer["value_w"])
            after = max(events) + 1e-3
            spec["_rows"], spec["_geo"], spec["_tag"], spec["_footer"] = rows, geo, tag, footer
            box_w, box_h0 = LIST["w"], rows[0]["card_h"]
            y = MARGIN
        elif kind == "stamp":
            text = str(c.get("text", "")).strip()
            if not text:
                raise CardError(f"{where}: a stamp needs text")
            if not c.get("at"):
                raise CardError(f"{where}: a stamp needs an 'at' phrase")
            at(c["at"], "at")
            shown = text.upper()
            box_w = stamp_width(shown)
            if box_w > STAMP["max_w"]:
                raise CardError(f"{where}: {shown!r} is too long for a stamp (one word or figure)")
            box_h0 = STAMP["h"]
            y = MARGIN + int(c.get("stack", 0)) * (STAMP["h"] + STAMP["gap"])
            spec["_stamp"] = {"text": shown, "accent": bool(c.get("accent", False))}
        elif kind == "keyline":
            text = " ".join(str(c.get("text", "")).split())
            if not text:
                raise CardError(f"{where}: a keyline needs text")
            if len(text) > KEYLINE["max_chars"]:
                raise CardError(f"{where}: a keyline is ONE sentence (≤{KEYLINE['max_chars']} "
                                f"characters); {len(text)} given")
            if not c.get("at"):
                raise CardError(f"{where}: a keyline needs an 'at' phrase")
            at(c["at"], "at")
            placement = c.get("placement", "above-captions")
            if placement not in ("above-captions", "low"):
                raise CardError(f"{where}: placement must be 'above-captions' or 'low'")
            spec["_keyline"] = {"text": text, "sub": " ".join(str(c.get("sub", "")).split()),
                                "bottom": KEYLINE["bottom_low" if placement == "low" else "bottom"]}
            box_w, box_h0, y = KEYLINE["max_w"], 1080, 0
        elif kind == "deck":
            chapters = c.get("chapters")
            if chapters is None and c.get("deck"):
                chapters = (edl.get("decks") or {}).get(c["deck"])
                if chapters is None:
                    raise CardError(f"{where}: no deck {c['deck']!r} in the EDL's `decks`")
            if not chapters or not 2 <= len(chapters) <= DECK["max"]:
                raise CardError(f"{where}: a deck needs 2-{DECK['max']} chapters")
            for k, ch in enumerate(chapters):
                if not str(ch.get("title", "")).strip():
                    raise CardError(f"{where}: chapter {k} needs a title")
                if ch.get("icon") not in ICONS:
                    raise CardError(f"{where}: chapter {k}: unknown icon {ch.get('icon')!r}")
            cur = c.get("current")
            if not isinstance(cur, int) or not 0 <= cur < len(chapters):
                raise CardError(f"{where}: current must be a chapter index 0-{len(chapters) - 1}")
            if not c.get("at"):
                raise CardError(f"{where}: a deck needs an 'at' phrase (the seam's first words)")
            at(c["at"], "at")
            spec["_deck"] = {"chapters": chapters, "current": cur,
                             "prefix": str(c.get("prefix", "Part"))}
            box_w, box_h0, y = None, 1080, 0
        elif kind == "annotate":
            if not c.get("image") or not c.get("at"):
                raise CardError(f"{where}: an annotate needs an 'image' and an 'at' phrase")
            img = Path(c["image"])
            img = img if img.is_absolute() else Path(edit_dir) / img
            if not img.exists():
                raise CardError(f"{where}: image not found: {img}")
            at(c["at"], "at")
            marks = []
            for k, m in enumerate(c.get("marks") or []):
                if m.get("type") not in MARK_TYPES:
                    raise CardError(f"{where} marks[{k}]: type must be one of {MARK_TYPES}")
                r = m.get("rect")
                if (not isinstance(r, (list, tuple)) or len(r) != 4
                        or not all(isinstance(v, (int, float)) for v in r)
                        or r[2] <= 0 or r[3] <= 0 or r[0] < 0 or r[1] < 0
                        or r[0] + r[2] > 1.0001 or r[1] + r[3] > 1.0001):
                    raise CardError(f"{where} marks[{k}]: rect must be [x, y, w, h] fractions "
                                    f"of the image, inside it")
                if m["type"] == "callout":
                    if not str(m.get("label", "")).strip():
                        raise CardError(f"{where} marks[{k}]: a callout needs a label")
                    if m.get("side", "right") not in ("left", "right", "top", "bottom"):
                        raise CardError(f"{where} marks[{k}]: side must be left/right/top/bottom")
                marks.append({**m, "w": at(m["at"], f"marks[{k}]")})
            spec["_annot"] = {"image": img, "marks": marks, "title": str(c.get("title", "")),
                              "caption": str(c.get("caption", ""))}
            box_w, box_h0, y = None, 1080, 0
        else:
            steps_in = c.get("steps") or []
            if not steps_in:
                raise CardError(f"{where}: a stat needs steps")
            steps = []
            for k, s in enumerate(steps_in):
                w = at(s["at"], f"steps[{k}]")
                st = {"value": str(s["value"]), "unit": s.get("unit", ""), "tag": s.get("tag", ""),
                      "accent": bool(s.get("accent", False)), "sub": s.get("sub", ""),
                      "sub_dir": s.get("sub_dir"), "w": w}
                if st["sub_dir"] not in (None, "up", "down"):
                    raise CardError(f"{where} steps[{k}]: sub_dir must be up, down or absent")
                if s.get("sub_at"):
                    st["sub_w"] = at(s["sub_at"], f"steps[{k}].sub_at")
                steps.append(st)
            if sum(1 for s in steps if s["accent"]) > 1:
                print(f"  note: {where} accents more than one step; accent should mean CHANGE")
            spec["_steps"] = steps
            box_w, box_h0 = STAT["w"], STAT["h"]
            y = MARGIN + int(c.get("stack", 0)) * (STAT["h"] + STAT["gap"])

        # the out point: a spoken word (preferred), else a hold after the last event
        if c.get("out"):
            exit_t = find_phrase(words, c["out"]["word"], max(events) + 1e-3, f"{where} out")
            exit_t += float(c["out"].get("offset", 0.0))
        else:
            default_hold = {"stamp": STAMP["hold"], "keyline": KEYLINE["hold"],
                            "deck": DECK["hold"], "annotate": ANNOT["hold"]}.get(kind, HOLD)
            exit_t = max(events) + float(c.get("hold", default_hold))
        exit_t = min(exit_t, total - EXIT_DUR - 0.05)
        # A card settles before its first word; a stamp IS the word, so it lands as it's said.
        card_in = max(0.0, first_word - (LEAD if kind in ("stamp", "keyline") else CARD_LEAD))
        start = max(0.0, card_in - 0.1)
        dur = round(exit_t + EXIT_DUR + 0.1 - start, 3)
        loc = lambda t: round(t - start, 3)   # noqa: E731  window-local seconds

        if kind in FULL_FRAME:
            box_w = stage_w
        x = (MARGIN if pos == "top-left" else round((stage_w - box_w) / 2, 3) if pos == "top-center"
             else round(stage_w - MARGIN - box_w, 3))
        if kind == "keyline":
            x = KEYLINE["x"]
        elif kind in FULL_FRAME:
            x = 0
        side = {"top-left": "left", "top-right": "right", "top-center": "center"}[pos]
        spec.update({
            "start": round(start, 3), "duration": dur,
            "in": loc(card_in), "exit": loc(exit_t),
            "stage": {"w": stage_w, "h": 1080, "scale": round(scale, 6)},
            "box": {"x": x, "y": y, "w": box_w, "h0": box_h0, "side": side, "k": card_scale},
            "colors": {"dot_done": f"rgba({_hex_rgb(brand['fg'])},0.45)",
                       "glow": brand["glow"]},
            "heights": [],
            "_brand": brand,
        })
        if kind == "list":
            rows, geo = spec.pop("_rows"), spec.pop("_geo")
            tag, footer = spec.pop("_tag"), spec.pop("_footer")
            time_col = any(r["time"] for r in rows)
            scrolls, scrolled = [], 0
            for k, r in enumerate(rows):
                r_t = loc(r["w"] - LEAD)
                if r["scroll"] != scrolled:
                    fade = [j for j, q in enumerate(rows) if scrolled <= q["top"] < r["scroll"]]
                    scrolls.append({"t": round(r_t - 0.35, 3), "offset": r["scroll"], "fade": fade})
                    scrolled = r["scroll"]
                if k > 0 and r["card_h"] != rows[k - 1]["card_h"]:
                    spec["heights"].append([round(r_t - 0.15, 3), r["card_h"]])
            final_h = rows[-1]["card_h"]
            if footer:
                spec["heights"].append([loc(footer["w"] - LEAD - 0.15), final_h + LIST["foot"]])
                final_h += LIST["foot"]
            if y + final_h * card_scale > 1080 - MARGIN:
                raise CardError(f"{where}: card would reach y={y + final_h * card_scale:.0f} (1080 units)")
            spec["list"] = {
                "time_col": time_col, "dot_x": 148 if time_col else 4, "text_x": 180 if time_col else 36,
                "view": {"top": geo["view_top"], "h": LIST["view_h"]},
                "rows": [{"t": loc(r["w"] - LEAD), "time": r["time"], "text": r["text"], "top": r["top"], "h": r["h"],
                          "chips": [{"t": loc(ch["w"] - 0.12), "text": ch["text"]} for ch in r["chips"]]} for r in rows],
                "scrolls": scrolls,
                "tag": {"text": tag["text"], "t": loc(tag["w"] - LEAD)} if tag else None,
                "footer": ({"text": footer["text"], "t": loc(footer["w"] - LEAD), "value": footer.get("value"),
                            "value_t": loc(footer["value_w"] - LEAD) if footer.get("value") else None}
                           if footer else None),
            }
            spec["_words"] = [(r["text"], r["w"]) for r in rows]
        elif kind == "stamp":
            st = spec.pop("_stamp")
            spec["stamp"] = {"text": st["text"], "accent": st["accent"],
                             "font": STAMP["font"], "track": STAMP["track"]}
            spec["_words"] = [(st["text"], first_word)]
        elif kind == "keyline":
            kl = spec.pop("_keyline")
            n_chars = len(kl["text"])
            type_dur = round(min(1.4, max(0.45, n_chars / KEYLINE["type_cps"])), 3)
            spec["keyline"] = {"text": kl["text"], "sub": kl["sub"], "type_dur": type_dur,
                               "sub_t": round(spec["in"] + type_dur + 0.15, 3),
                               "font": KEYLINE["font"], "sub_font": KEYLINE["sub"],
                               "bottom": kl["bottom"], "max_w": KEYLINE["max_w"]}
            spec["_words"] = [(kl["text"], first_word)]
        elif kind == "deck":
            dk = spec.pop("_deck")
            spec["deck"] = deck_layout(dk["chapters"], dk["current"], dk["prefix"], stage_w,
                                       loc(first_word - LEAD))
            spec["_words"] = [(f"{dk['prefix']} {dk['current'] + 1}: "
                               f"{dk['chapters'][dk['current']]['title']}", first_word)]
        elif kind == "annotate":
            an = spec.pop("_annot")
            spec["annotate"] = annotate_layout(an, stage_w, scale, loc)
            spec["_words"] = [("[image]", first_word)] + [
                (m.get("label") or m["type"], m["w"]) for m in an["marks"]]
        else:
            steps = spec.pop("_steps")
            spec["stat"] = {"steps": [{
                "t": loc(s["w"] - LEAD), "value": s["value"], "unit": s["unit"], "tag": s["tag"],
                "accent": s["accent"], "sub": s["sub"], "sub_dir": s["sub_dir"],
                "sub_t": loc(s["sub_w"] - 0.1) if "sub_w" in s else loc(s["w"] - LEAD + 0.4)} for s in steps]}
            spec["_words"] = [(s["value"], s["w"]) for s in steps]
        specs.append(spec)
    return specs


# -------- HyperFrames projects -----------------------------------------------


def _font_css(brand: dict) -> str:
    faces = FONT_FACES.get(brand["card_font"])
    if not faces:
        raise CardError(f"no local() face names known for card_font {brand['card_font']!r}; "
                        f"add them to cards.FONT_FACES")
    return "".join(f'@font-face {{ font-family: "CardFont"; src: local("{n}"); font-weight: {w}; }}\n'
                   for w, n in faces.items())


def page(spec: dict, mode: str, out_w: int, out_h: int) -> str:
    """The complete HyperFrames composition for one pass. Everything is inline (static guard)."""
    b = spec["_brand"]
    public = {k: v for k, v in spec.items() if not k.startswith("_")}
    css = (RUNTIME / "glass.css").read_text()
    js = (RUNTIME / "glass.js").read_text()
    root_vars = (f":root {{ --fg: {b['fg']}; --muted: {b['muted']}; --accent: {b['accent']}; "
                 f"--bg-rgb: {_hex_rgb(b['bg'])}; --fg-rgb: {_hex_rgb(b['fg'])}; "
                 f"--glow: {b['glow']}; --glow-rgb: {_hex_rgb(b['glow'])}; }}\n")
    fonts = _font_css(b) if mode == "overlay" else ""
    if mode == "mask":     # no text in the mask, so no named family (lint requires a face for one)
        css = css.replace('font-family: "CardFont", sans-serif;', "")
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={out_w}, height={out_h}" />
    <script src="{GSAP_URL}"></script>
    <style>
{fonts}{root_vars}{css}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{spec['duration']}"
         data-width="{out_w}" data-height="{out_h}"></div>
    <script>
      window.HF_MODE = "{mode}";
      window.CARD = {json.dumps(public, ensure_ascii=False)};
{js}
    </script>
  </body>
</html>
"""


def _project_files(d: Path, name: str) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "hyperframes.json").write_text(json.dumps({
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
        "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
        "media": {"autoProxy": True}}, indent=2))
    (d / "meta.json").write_text(json.dumps({"id": name, "name": name}, indent=2))
    (d / "package.json").write_text(json.dumps({"name": name, "private": True, "type": "module"}, indent=2))


def _frames(p: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                          "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True).stdout.strip()
    return int(out or 0)


def _rate(fps: str) -> float:
    n, _, d = str(fps).partition("/")
    return float(n) / float(d or 1)


def render(specs: list[dict], edit_dir: Path, out_w: int, out_h: int, fps: str) -> list[dict]:
    """Render (or reuse) both passes of every card. Returns composite entries."""
    if specs and not shutil.which("npx"):
        raise CardError("cards need Node (npx) for HyperFrames: `brew install node`")
    entries = []
    for spec in specs:
        d = Path(edit_dir) / "animations" / "cards" / spec["id"]
        overlay_html, mask_html = page(spec, "overlay", out_w, out_h), page(spec, "mask", out_w, out_h)
        key = hashlib.sha256("\0".join([HF_VERSION, str(fps), overlay_html, mask_html]).encode()).hexdigest()[:16]
        ren = d / "renders"
        cards_mov, mask_mov = ren / f"cards_{out_h}.mov", ren / f"mask_{out_h}.mov"
        key_file = ren / f"key_{out_h}.txt"
        want = round(spec["duration"] * _rate(fps))
        if not (key_file.exists() and key_file.read_text() == key and cards_mov.exists() and mask_mov.exists()):
            _project_files(d, f"card_{spec['id']}")
            _project_files(d / "mask", f"card_{spec['id']}_mask")
            (d / "index.html").write_text(overlay_html)
            (d / "mask" / "index.html").write_text(mask_html)
            ren.mkdir(parents=True, exist_ok=True)
            # the layout audit catches clipped glyphs and overflowing text; trust it (gotchas #5).
            # Not run on the mask: a static-by-design silhouette trips `sweep_static` (gotchas #7).
            chk = subprocess.run(["npx", "--yes", f"hyperframes@{HF_VERSION}", "check", str(d)],
                                 capture_output=True, text=True)
            errors = [l.strip() for l in (chk.stdout + chk.stderr).splitlines() if l.strip().startswith("✗")]
            if errors:
                raise CardError(f"card {spec['id']}: HyperFrames check failed:\n  " + "\n  ".join(errors))
            for proj, out in ((d, cards_mov), (d / "mask", mask_mov)):
                print(f"  rendering card {spec['id']} ({'mask' if proj != d else 'card'}) @ {out_h}p {fps}")
                r = subprocess.run(["npx", "--yes", f"hyperframes@{HF_VERSION}", "render", str(proj),
                                    "--format", "mov", "--fps", str(fps), "-o", str(out)],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    raise CardError(f"card {spec['id']}: hyperframes render failed:\n{(r.stdout + r.stderr)[-2000:]}")
            for out in (cards_mov, mask_mov):
                got = _frames(out)
                if abs(got - want) > 1:
                    raise CardError(f"card {spec['id']}: {out.name} has {got} frames, expected {want}")
            key_file.write_text(key)
        entries.append({"id": spec["id"], "cards": cards_mov, "mask": mask_mov,
                        "start": spec["start"], "duration": spec["duration"]})
    return entries


# -------- ffmpeg fragment ----------------------------------------------------


def build_filter(entries: list[dict], current: str, first_input: int, out_w: int, out_h: int
                 ) -> tuple[list[str], list[str], str]:
    """Inputs and filter parts that draw every card over `current`. Returns the new label.

    The blur runs once, at quarter resolution (indistinguishable for a sigma this large, and
    ~16x cheaper), then is cut to each card's mask. Masks are padded to the window start with
    `tpad` rather than shifted, so alphamerge never has to guess what precedes the first frame;
    cards are placed with `-itsoffset` + `enable`, exactly like render.py's overlays.
    """
    if not entries:
        return [], [], current
    inputs: list[str] = []
    parts: list[str] = []
    n = len(entries)
    sigma = round(10 * out_h / 1080, 2)
    parts.append(f"{current}split=2[ck_sharp][ck_toblur]")
    parts.append(f"[ck_toblur]scale=iw/4:ih/4:flags=bicubic,gblur=sigma={sigma}:steps=2,"
                 f"eq=brightness=-0.03:saturation=1.15,scale={out_w}:{out_h}:flags=bicubic"
                 + (f",split={n}" + "".join(f"[ck_b{i}]" for i in range(n)) if n > 1 else "[ck_b0]"))
    cur = "[ck_sharp]"
    idx = first_input
    for i, e in enumerate(entries):
        s, end = float(e["start"]), float(e["start"]) + float(e["duration"])
        mi, ci = idx, idx + 1
        inputs += ["-i", str(e["mask"]), "-itsoffset", f"{s:.3f}", "-i", str(e["cards"])]
        idx += 2
        parts.append(f"[{mi}:v]alphaextract,tpad=start_duration={s:.3f}:color=black[ck_m{i}]")
        parts.append(f"[ck_b{i}][ck_m{i}]alphamerge[ck_g{i}]")
        parts.append(f"{cur}[ck_g{i}]overlay=0:0:enable='between(t,{s:.3f},{end:.3f})'"
                     f":eof_action=pass:repeatlast=0:format=auto[ck_s{i}]")
        # HyperFrames' MOV is BT.601 and untagged: convert, or every colour shifts (measured).
        parts.append(f"[{ci}:v]scale=in_color_matrix=bt601:out_color_matrix=bt709"
                     f":in_range=tv:out_range=tv,format=yuva444p[ck_c{i}]")
        parts.append(f"[ck_s{i}][ck_c{i}]overlay=0:0:enable='between(t,{s:.3f},{end:.3f})'"
                     f":eof_action=pass:repeatlast=0:format=auto[ck_o{i}]")
        cur = f"[ck_o{i}]"
    return inputs, parts, cur


def prepare(cards: list[dict], edl: dict, edit_dir: Path, segment_durations: list[float],
            base_path: Path, fps: str) -> list[dict]:
    """render.py's entry point: resolve, report, render. Returns composite entries."""
    w, h = _dims(base_path)
    specs = resolve(cards, edl, edit_dir, segment_durations, w, h)
    report(specs)
    return render(specs, edit_dir, w, h, fps)


def report(specs: list[dict]) -> None:
    """Print what each card covers, with the word every element lands on (read it)."""
    for s in specs:
        print(f"  card {s['id']:<12} {s['kind']:<5} {s['start']:8.3f}s +{s['duration']:.2f}s")
        for text, w in s["_words"]:
            print(f"      {w:8.3f}s  {text}")


def _dims(p: Path) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "json", str(p)], capture_output=True, text=True).stdout
    st = json.loads(out)["streams"][0]
    return int(st["width"]), int(st["height"])


def main() -> None:
    ap = argparse.ArgumentParser(description="Resolve an EDL's glass cards and print where each lands.")
    ap.add_argument("edl", type=Path)
    ap.add_argument("--clips", default="clips_graded",
                    help="segment dir to MEASURE durations from (clips_graded/clips_preview/clips_draft)")
    a = ap.parse_args()
    edl = json.loads(a.edl.read_text())
    edit = a.edl.resolve().parent
    durs = []
    for i, r in enumerate(edl["ranges"]):
        seg = edit / a.clips / f"seg_{i:02d}_{r['source']}.mp4"
        if not seg.exists():
            sys.exit(f"missing {seg}: render once so durations are measured, not summed")
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(seg)], capture_output=True, text=True).stdout
        durs.append(float(out))
    report(resolve(edl.get("cards") or [], edl, edit, durs, 1920, 1080))


if __name__ == "__main__":
    main()
