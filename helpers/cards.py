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
       "out": {"word": "and that is"}, "after": {"word": "this month"}}
    ]
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
ICONS = {"clock", "drop", "bolt", "scale", "list", "star", None}

DEFAULT_BRAND = {"bg": "#0A0A0A", "fg": "#DED3BD", "muted": "#8A8375", "accent": "#F25435"}
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
        if kind not in ("list", "stat"):
            raise CardError(f"{where}: kind must be 'list' or 'stat', got {kind!r}")
        if c.get("icon") not in ICONS:
            raise CardError(f"{where}: unknown icon {c.get('icon')!r}; one of {sorted(i for i in ICONS if i)}")
        pos = c.get("position", "top-left")
        if pos not in ("top-left", "top-right"):
            raise CardError(f"{where}: position must be top-left or top-right")

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
            exit_t = max(events) + float(c.get("hold", HOLD))
        exit_t = min(exit_t, total - EXIT_DUR - 0.05)
        card_in = max(0.0, first_word - CARD_LEAD)
        start = max(0.0, card_in - 0.1)
        dur = round(exit_t + EXIT_DUR + 0.1 - start, 3)
        loc = lambda t: round(t - start, 3)   # noqa: E731  window-local seconds

        x = MARGIN if pos == "top-left" else round(stage_w - MARGIN - box_w, 3)
        spec.update({
            "start": round(start, 3), "duration": dur,
            "in": loc(card_in), "exit": loc(exit_t),
            "stage": {"w": stage_w, "h": 1080, "scale": round(scale, 6)},
            "box": {"x": x, "y": y, "w": box_w, "h0": box_h0, "side": "left" if pos == "top-left" else "right"},
            "colors": {"dot_done": f"rgba({_hex_rgb(brand['fg'])},0.45)"},
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
            if y + final_h > 1080 - MARGIN:
                raise CardError(f"{where}: card would reach y={y + final_h} (1080 units)")
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
                 f"--bg-rgb: {_hex_rgb(b['bg'])}; --fg-rgb: {_hex_rgb(b['fg'])}; }}\n")
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
