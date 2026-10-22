"""Shorts: a 9:16 Short cut from a long video's own sources, driven by one spec file.

    SH="uv run python skills/shorts/scripts/shorts.py"        # from the repo root
    $SH <edit> <name> words          # kept words with indices (author the caption bursts from this)
    $SH <edit> <name> build          # spec -> <edit>/shorts/<name>/edl.json (face-centred crop)
    $SH <edit> <name> edges          # edges with speech right beside them: clipped word or meant?
    $SH <edit> <name> plate          # the thumbnail-style opening plate -> plate.mov
    $SH <edit> <name> captions       # 2-3 word bursts, key word in the accent -> captions.ass
    $SH <edit> <name> render         # render.py --no-loudnorm -> <output>_NO_MUSIC_do_not_upload.mp4
    $SH <edit> <name> mix            # bed + effects, -14 LUFS -> <output>.mp4
    $SH <edit> <name> sfx            # is each effect audible? (M052)
    $SH <edit> <name> review [--label v1]
    $SH <edit> <name> preview        # 720p phone preview, <30 MB
    $SH <edit> <name> all [--label v1]

The spec is `<edit>/shorts/<name>/short.json` (see ../SKILL.md). Everything this writes stays in
that folder (Hard Rule 12). The parent is the long video's edl.json; its sources, grade, brand and
transcripts are reused, so a Short is the long video's footage, never a crop of its final (which
has captions and cards burned in).

Built from Episode 4's Shorts (2026-10-14). Every number here was measured there: kb/gotchas.md
"Shorts (9:16) from a 16:9 4K master", kb/mistakes.md M053.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HELPERS = REPO / "helpers"
sys.path.insert(0, str(HELPERS))

FPS = 30
OUT_H, CROP_W = 1920, 1080          # render height, 9:16 crop width
ZOOMS = (1.0, 1.12)                 # alternated to hide jump cuts; 1.12 stays native from 4K
TONEMAP = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=mobius,"
           "zscale=t=bt709:m=bt709:r=tv,format=rgb24")
HDR = {"arib-std-b67", "smpte2084"}
LIBRARY = Path(os.environ.get("SHORTS_LIBRARY", "~/Documents/Ambitious/Editing")).expanduser()

# ---------------------------------------------------------------- spec + context


class Ctx:
    def __init__(self, edit: Path, name: str):
        self.edit, self.name = edit.resolve(), name
        self.dir = self.edit / "shorts" / name
        p = self.dir / "short.json"
        if not p.exists():
            sys.exit(f"no spec: {p}")
        self.spec = json.loads(p.read_text())
        self.parent_rel = self.spec.get("parent", "../../edl.json")
        self.parent_path = (self.dir / self.parent_rel).resolve()
        self.parent = json.loads(self.parent_path.read_text())
        self.output = self.spec.get("output", f"short_{name}")

    @property
    def edl(self) -> dict:
        return json.loads((self.dir / "edl.json").read_text())

    def path(self, kind: str, rel: str) -> Path:
        """A music or effects file: absolute, or relative to <library>/music or <library>/effects."""
        p = Path(rel).expanduser()
        return p if p.is_absolute() else LIBRARY / kind / rel


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


# ---------------------------------------------------------------- framing


def probe(path: str) -> tuple[int, int, bool]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,color_transfer", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"]), s.get("color_transfer") in HDR


def framing(fx: float, fy: float, zoom: float, W: int, H: int) -> dict:
    """zoom/zoom_x/zoom_y + a CROP_W x OUT_H crop centred on the face.

    render.py scales a WxH source to OW x OUT_H (OW = W/H*OUT_H, even), after any zoom crop taken
    on the SOURCE; the per-range `filter` then cuts the vertical frame from that.
    """
    ow = round(W / H * OUT_H / 2) * 2
    out: dict = {}
    cw, ch = W / zoom, H / zoom
    cx = 0.0
    if zoom > 1.0:
        bx = min(1.0, max(0.0, (fx * W - cw / 2) / (W - cw)))
        by = min(1.0, max(0.0, (fy * H - 0.36 * ch) / (H - ch)))   # face ~36% from the top
        cx = (W - cw) * bx
        out.update(zoom=zoom, zoom_x=round(bx, 3), zoom_y=round(by, 3))
    ox = (fx * W - cx) * ow / cw
    x = int(min(ow - CROP_W, max(0, ox - CROP_W / 2))) // 2 * 2
    out["filter"] = f"crop={CROP_W}:{OUT_H}:{x}:0"
    return out


def next_zoom(prev: float | None) -> float:
    """The 1.0 / 1.12 alternation: whatever the previous range was not."""
    return ZOOMS[1] if prev == ZOOMS[0] else ZOOMS[0]


def pick_face(boxes: list, who: str | None, width: int = 960):
    """The face to frame: the largest, or with two people in a wide, the largest on the `left` or
    `right` half. Only that half counts: when the speaker turns away and only the other face is
    found, picking "the rightmost face" would frame the wrong person (podcast Episode 1)."""
    if who in ("left", "right"):
        boxes = [b for b in boxes if (b[0] + b[2] / 2 < width / 2) == (who == "left")]
    if not boxes:
        return None
    return max(boxes, key=lambda b: b[2] * b[3])[:4]


def face_centre(path: str, a: float, b: float, hdr: bool, who: str | None = None) -> tuple[float, float]:
    """Median face centre over three frames of [a, b], as fractions of the frame."""
    import numpy as np
    import exposure
    vf = (TONEMAP + "," if hdr else "format=rgb24,") + "scale=960:540"
    xs, ys, why = [], [], ""
    for f in (0.25, 0.5, 0.75):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a + (b - a) * f:.3f}", "-i", path,
                              "-frames:v", "1", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        boxes, why = exposure.detect_faces(np.frombuffer(raw, np.uint8).reshape(540, 960, 3))
        box = pick_face(boxes, who)
        if box:
            x, y, w, h = box
            xs.append((x + w / 2) / 960)
            ys.append((y + h / 2) / 540)
    if not xs:
        sys.exit(f"no face in {path} {a}-{b}: {why}. Give this range an explicit \"face\": [x, y].")
    return float(np.median(xs)), float(np.median(ys))


def source_path(parent_dir: Path, path: str) -> str:
    """A parent source as an absolute path: a parent EDL may list sources relative to its own
    folder (Episode 2's `../IMG_3672.mov`), and the Short's EDL lives two levels deeper."""
    p = Path(path).expanduser()
    return str(p if p.is_absolute() else (parent_dir / p).resolve())


def inherited(parent_ranges: list, src: str, start: float, end: float) -> dict:
    """The parent range this Short range was cut from (same source, largest overlap), as the
    per-range settings a Short keeps: `filter` (sharpening, colour match), `grade`, `audio_filter`.
    A parent range that swaps in another camera (`video`) is skipped; where only those overlap
    (podcast Episode 1 cut to its DSLR there), the nearest same-source range within 120 s stands in,
    because these settings belong to the take (a colour match), not to the moment."""
    best, ov, near = None, 0.0, None
    for pr in parent_ranges:
        if pr.get("source") != src or pr.get("video"):
            continue
        a, b = float(pr["start"]), float(pr["end"])
        o = min(end, b) - max(start, a)
        if o > ov:
            best, ov = pr, o
        gap = max(a - end, start - b)
        if gap <= 120 and (near is None or gap < near[0]):
            near = (gap, pr)
    best = best or (near[1] if near else None)
    return {k: best[k] for k in ("filter", "grade", "audio_filter") if best and k in best}


def cmd_build(c: Ctx, a) -> None:
    sp, P = c.spec, c.parent
    srcs = {k: source_path(c.parent_path.parent, v) for k, v in P["sources"].items()}
    tr = c.dir / "transcripts"
    if not tr.exists():
        tr.symlink_to(c.parent_path.parent / "transcripts")
    ranges, total, prev, prev_src = [], 0.0, None, None
    punch = float(sp.get("punch", 1.25))
    for i, r in enumerate(sp["ranges"]):
        src, start, end = r["source"], float(r["start"]), float(r["end"])
        path = srcs[src]
        W, H, hdr = probe(path)
        z = r.get("zoom")
        zoom = punch if z == "punch" else float(z) if z is not None else next_zoom(prev)
        if prev_src == src and prev == zoom:
            print(f"  warning: range {i} has the same zoom ({zoom}) as the one before on {src}: a visible jump")
        if prev and zoom > prev and zoom / prev < 1.1:
            print(f"  warning: range {i} pushes in only {zoom / prev:.2f}x: below ~1.1x a cut reads as a glitch")
        fx, fy = r["face"] if r.get("face") else face_centre(path, start, end, hdr, r.get("who"))
        e = {"source": src, "start": start, "end": end, "beat": f"{c.name} {i:02d}",
             "quote": r.get("quote", "")}
        e.update(framing(fx, fy, zoom, W, H))
        inh = inherited(P["ranges"], src, start, end)
        pre = r.get("pre_filter", inh.get("filter", ""))     # e.g. the parent's `cas`, or a colour match
        if pre:
            e["filter"] = f"{pre},{e['filter']}"
        for k in ("grade", "audio_filter"):      # the spec's own value wins (a bleep's volume=0)
            if k in r:
                e[k] = r[k]
            elif k in inh:
                e[k] = inh[k]
        ranges.append(e)
        total += end - start
        prev, prev_src = zoom, src
        print(f"  {i:02d} {src} {start:8.3f}-{end:8.3f} z={zoom} {e['filter']}  {e['quote'][:50]}")
    edl = {
        "version": 1,
        "sources": {s: srcs[s] for s in dict.fromkeys(r["source"] for r in ranges)},
        "grade": P.get("grade"),
        **({"audio_filter": P["audio_filter"]} if P.get("audio_filter") else {}),
        "parent": c.parent_rel,           # review.py G4: the parent's cards this Short must carry
        "ranges": ranges,
        "subtitles": "captions.ass",
        # the .ass carries its own styles; render.py falls back to Helvetica on an empty force_style
        "subtitle_style": {"force_style": "Bold=1"},
        "cards": sp.get("cards", []),
        "total_duration_s": round(total, 3),
    }
    if P.get("brand"):
        brand = (c.parent_path.parent / P["brand"]).resolve()
        edl["brand"] = os.path.relpath(brand, c.dir)
    edl["overlays"] = []
    (c.dir / "edl.json").write_text(json.dumps(edl, indent=1, ensure_ascii=False) + "\n")
    if sp.get("plate") and edl["cards"]:
        clash = cards_under_plate(edl["cards"], resolver(kept(c)[0]), float(sp["plate"].get("seconds", 3.0)))
        if clash:
            sys.exit("cards land under the opening plate (both sit at the top): " + ", ".join(clash)
                     + ". The plate is the hook text there; drop the card or anchor it later.")
    if sp.get("broll"):
        edl["overlays"] += build_broll(c, sp["broll"])
    if sp.get("plate"):                      # last, so it sits on top
        edl["overlays"].append({"file": "plate.mov", "start_in_output": 0.0,
                                "duration": float(sp["plate"].get("seconds", 3.0))})
    (c.dir / "edl.json").write_text(json.dumps(edl, indent=1, ensure_ascii=False) + "\n")
    print(f"{c.name}: {len(ranges)} ranges, {total:.1f} s -> {c.dir / 'edl.json'}")


def cards_under_plate(cards: list, T, plate_s: float) -> list[str]:
    """Cards whose first anchor resolves before the plate has gone (+0.2 s): a top-centre stamp
    then sits on the plate (podcast Episode 1's Microsoft Short, 2026-10-14)."""
    out = []
    for k in cards:
        at = k.get("at") or (k.get("steps") or [{}])[0].get("at")
        if at is not None and T(at) < plate_s + 0.2:
            out.append(f"{k.get('id')} at {T(at):.2f} s")
    return out


def broll_crop(x: float, W: int, H: int) -> int:
    """Left edge of a full-height 9:16 window centred on x (a frame fraction), clamped, even."""
    cw = H * 9 // 16
    return int(min(W - cw, max(0, x * W - cw / 2))) // 2 * 2


def build_broll(c: Ctx, items: list) -> list[dict]:
    """The parent's cutaways, re-cut vertical: each item is {"file", "src" (seconds into it),
    "at" (spoken anchor), "duration", "x" (subject centre, frame fraction), "vf" (optional grade)}.
    Rendered full-frame 1080x1920 at 30 fps, BT.709-tagged, so render.py composites it at 0:0
    with no scaling (overlays are resolution-specific, kb/index.md)."""
    T = resolver(kept(c)[0])
    out = []
    for k, b in enumerate(items):
        f = Path(b["file"]).expanduser()
        W, H, hdr = probe(str(f))
        x0 = broll_crop(float(b.get("x", 0.5)), W, H)
        vf = ",".join(v for v in ((TONEMAP if hdr else ""), f"crop={H * 9 // 16}:{H}:{x0}:0",
                                  "scale=1080:1920:flags=lanczos", "fps=30", b.get("vf", ""),
                                  "format=yuv420p,setparams=colorspace=bt709:color_trc=bt709:"
                                  "color_primaries=bt709:range=tv") if v)
        dst = c.dir / f"broll_{k:02d}.mp4"
        dur = float(b["duration"])
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{float(b.get('src', 0.0)):.3f}", "-i", f, "-t", f"{dur:.3f}",
             "-vf", vf, "-an", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-colorspace", "bt709", dst])
        at = T(b["at"])
        print(f"  broll {k:02d} {f.name} @ {at:.2f} s for {dur:.1f} s, crop x {x0} of {W}x{H}")
        out.append({"file": dst.name, "start_in_output": round(at, 3), "duration": dur})
    return out


# ---------------------------------------------------------------- words / anchors


def kept(c: Ctx):
    import cards
    edl = c.edl
    durs = [max(1, round((r["end"] - r["start"]) * FPS)) / FPS for r in edl["ranges"]]
    return cards.kept_words(edl, c.dir, durs), sum(durs)


def cmd_words(c: Ctx, a) -> None:
    W, total = kept(c)
    print(f"{len(W)} kept words, {total:.2f} s (index:word@time; Deepgram may list words a cut made inaudible)")
    print(" ".join(f"{i}:{w[1]}@{w[0]:.2f}" for i, w in enumerate(W)))


def resolver(W):
    """anchor -> output time. An anchor is a phrase, or {"phrase", "after", "shift"}: `after` is
    another anchor the phrase is searched after (for a phrase said more than once)."""
    import cards

    def T(an) -> float:
        if isinstance(an, (int, float)):
            return float(an)
        if isinstance(an, str):
            an = {"phrase": an}
        after = T(an["after"]) if an.get("after") is not None else 0.0
        return cards.find_phrase(W, an["phrase"], after, f"shorts {an['phrase']!r}") + float(an.get("shift", 0.0))
    return T


# ---------------------------------------------------------------- plate

PLATE_FONT = "/System/Library/Fonts/Avenir Next.ttc"
HEAVY, DEMI = 8, 2
YELLOW, WHITE, PLATE_BG = (245, 184, 46), (255, 255, 255), (14, 14, 16, 225)


def plate_image(kicker: str, big: str, top: int = 175, max_w: int = 960):
    """Yellow Avenir Next Demi kicker over big white Avenir Next Heavy on a dark rounded plate:
    the Episode 4 thumbnail style, at 1080x1920. Shrinks the type until the plate fits max_w."""
    from PIL import Image, ImageDraw, ImageFont
    size = 132
    while True:
        fb = ImageFont.truetype(PLATE_FONT, size, index=HEAVY)
        fs = ImageFont.truetype(PLATE_FONT, round(size * 0.52), index=DEMI)
        d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        tw = max(d.textlength(big, font=fb), d.textlength(kicker, font=fs))
        if tw + 2 * 44 <= max_w:
            break
        size -= 4
    pad, gap = 44, 14
    ks, bs = fs.getbbox(kicker), fb.getbbox(big)
    bw, bh = tw + 2 * pad, (ks[3] - ks[1]) + gap + (bs[3] - bs[1]) + 2 * pad
    img = Image.new("RGBA", (CROP_W, OUT_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0 = (CROP_W - bw) / 2
    d.rounded_rectangle([x0, top, x0 + bw, top + bh], 26, fill=PLATE_BG)
    d.text(((CROP_W - d.textlength(kicker, font=fs)) / 2, top + pad - ks[1]), kicker, font=fs, fill=YELLOW)
    d.text(((CROP_W - d.textlength(big, font=fb)) / 2, top + pad + (ks[3] - ks[1]) + gap - bs[1]), big,
           font=fb, fill=WHITE)
    print(f"plate {bw:.0f}x{bh:.0f} at y {top}-{top + bh:.0f}, big text {size}px")
    return img


def ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def cmd_plate(c: Ctx, a) -> None:
    """ProRes 4444 with alpha, converted to BT.709 limited in the encode, so the overlay needs no
    matrix change against render.py's bt709 base (the HyperFrames 601 drift, kb/gotchas.md)."""
    from PIL import Image
    p = c.spec["plate"]
    dur, top = float(p.get("seconds", 3.0)), 175
    base = plate_image(p["kicker"], p["big"], top)
    with tempfile.TemporaryDirectory() as td:
        for f in range(round(dur * FPS)):
            t = f / FPS
            al = ease(t / 0.18) * (1 - ease((t - (dur - 0.25)) / 0.25))   # pop in, hold, fade
            k = 0.94 + 0.06 * ease(t / 0.22)                              # slight scale-up on entry
            fr = base.resize((round(CROP_W * k), round(OUT_H * k)), Image.LANCZOS)
            canvas = Image.new("RGBA", (CROP_W, OUT_H), (0, 0, 0, 0))
            canvas.paste(fr, ((CROP_W - fr.width) // 2, round(top * (1 - k))), fr)
            if al < 1:
                canvas.putalpha(canvas.getchannel("A").point(lambda v: round(v * al)))
            canvas.save(f"{td}/f{f:04d}.png")
        run(["ffmpeg", "-v", "error", "-y", "-framerate", FPS, "-i", f"{td}/f%04d.png",
             "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuva444p10le",
             "-c:v", "prores_ks", "-profile:v", "4444", "-colorspace", "bt709",
             "-color_primaries", "bt709", "-color_trc", "bt709", c.dir / "plate.mov"])
    print("->", c.dir / "plate.mov")


# ---------------------------------------------------------------- captions

ACCENT, WHITE_ASS = "&H3554F2&", "&HFFFFFF&"      # #F25435 in ASS BGR
ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Burst,Avenir Next Heavy,88,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,7,2,2,60,60,540,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
POP = r"{\fscx88\fscy88\t(0,90,\fscx100\fscy100)}"     # each burst lands with a small scale-up


def ass_time(s: float) -> str:
    cs = round(s * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def colour(text: str) -> str:
    """*word* -> the word in the brand accent."""
    return re.sub(r"\*(.+?)\*", lambda m: f"{{\\c{ACCENT}}}{m.group(1)}{{\\c{WHITE_ASS}}}", text)


def ass_events(bursts, word_times, total) -> list[str]:
    """A burst shows from its first word's onset to the next burst's onset; the last one runs
    0.8 s past its first word (or to the end). Pure, for tests."""
    out = []
    for k, (i, text) in enumerate(bursts):
        start = word_times[i]
        end = word_times[bursts[k + 1][0]] if k + 1 < len(bursts) else min(total, word_times[-1] + 0.8)
        out.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end - 0.01)},Burst,,0,0,0,,{POP}{colour(text)}")
    return out


def cmd_captions(c: Ctx, a) -> None:
    W, total = kept(c)
    bursts = [tuple(b) for b in c.spec["captions"]]
    idx = [i for i, _ in bursts]
    if idx != sorted(idx) or len(set(idx)) != len(idx):
        sys.exit("captions: burst word indices must strictly increase")
    lines = ass_events(bursts, [w[0] for w in W], total)
    (c.dir / "captions.ass").write_text(ASS_HEADER + "\n".join(lines) + "\n")
    print(f"{c.name}: {len(lines)} bursts -> captions.ass")
    for i, text in bursts:
        print(f"   {W[i][0]:6.2f}  [{W[i][1]}]  {text}")


# ---------------------------------------------------------------- render / mix / review / preview


def raw_path(c: Ctx) -> Path:
    return c.dir / f"{c.output}_NO_MUSIC_do_not_upload.mp4"


def cmd_render(c: Ctx, a) -> None:
    log = c.dir / "render.log"
    with open(log, "w") as fh:
        run(["uv", "run", "python", HELPERS / "render.py", c.dir / "edl.json", "-o", raw_path(c),
             "--height", OUT_H, "--fps", FPS, "--no-loudnorm"], cwd=REPO, stdout=fh, stderr=subprocess.STDOUT)
    print("->", raw_path(c), f"(log {log.name})")


BED_UNDER, SFX_UNDER = 26.0, 9.0          # kb/storytelling.md §8b: beds ~26-28 LU under the voice
DUCK = "sidechaincompress=threshold=0.060:ratio=2.5:attack=25:release=250:makeup=1"
TARGET_I, TARGET_TP = -14.0, -2.0   # limited at 4x (192 kHz) so inter-sample peaks are caught; the true-peak loop below is the backstop


def sfx_lib() -> dict:
    """The motion-graphics-pass effect names (one table for both skills), read without importing mgx."""
    src = (REPO / "skills/motion-graphics-pass/scripts/mgx.py").read_text()
    node = next(n for n in ast.parse(src).body if isinstance(n, ast.Assign)
                and getattr(n.targets[0], "id", "") == "SFX_LIB")
    return ast.literal_eval(node.value)


def lufs(path, ss, dur) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", str(ss), "-t", str(dur), "-i", str(path),
                        "-af", "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True, text=True).stderr
    vals = [float(l.split("I:")[1].split("LUFS")[0]) for l in r.splitlines() if "I:" in l and "LUFS" in l]
    if not vals:
        sys.exit(f"no loudness for {path} at {ss}")
    return vals[-1]


def plan_mix(c: Ctx, W, total):
    """Beds and hits from the spec, every edge resolved to output time on the kept words."""
    T, lib, m = resolver(W), None, c.spec.get("mix", {})
    beds, first = [], {}
    for b in m.get("beds", []):
        f = c.path("music", b["file"])
        t0 = T(b.get("from", 0.0))
        t1 = total if b.get("to", "end") == "end" else T(b["to"])
        if b.get("src", 0.0) == "sync":            # the same track, continuing in sync: a drop-out, not a new cue
            s0, a0 = first[f]
            src = s0 + (t0 - a0)
        else:
            src = float(b.get("src", 0.0))
            first.setdefault(f, (src, t0))
        beds.append((f, src, t0, t1, float(b.get("fade_in", 0.3)), float(b.get("fade_out", 1.0)),
                     tuple(b.get("lift", (0.0, 0.0, 0.1))), float(b.get("trim", 0.0))))
    hits = []
    for h in m.get("hits", []):
        if h.get("sfx"):
            lib = lib or sfx_lib()
            rel, off, _ = lib[h["sfx"]]
            f, off = c.path("effects", rel), (off or 0.0)
        else:
            f, off = c.path("effects", h["file"]), float(h.get("offset", 0.0))
        hits.append((f, off, T(h["at"]), float(h.get("trim", 0.0))))
    return beds, hits


def cmd_mix(c: Ctx, a) -> None:
    """Mix before loudness normalisation (kb/gotchas.md), levels per cue against the programme in
    that cue's own window, -14 LUFS, -1.5 dBTP limit. From Episode 4's build/mix.py."""
    W, total = kept(c)
    beds, hits = plan_mix(c, W, total)
    src = raw_path(c)
    out = c.dir / f"{c.output}.mp4"
    inputs, parts, bl, fl, idx = ["-i", str(src)], [], [], [], 1
    # Not bit-reproducible run to run: after the LAST effect's stream ends, ffmpeg's output varies
    # (up to a -29 dB peak, ~-54 dB RMS, measured on Episode 4's money Short with an identical
    # command). Everything before that point is identical. Compare remixes by ear there, not by hash.
    for f, ss, t0, t1, fi, fo, (lf, lh, lr), trim in beds:
        dur = t1 - t0
        gain = (lufs(src, t0, dur) - BED_UNDER) - lufs(f, ss, dur) + trim
        env = f"if(lt(t,{lh:.3f}),1,if(lt(t,{lh + lr:.3f}),({lh + lr:.3f}-t)/{lr:.3f},0))"
        vol = f"volume='pow(10,({gain:.2f}+{lf:.2f}*{env})/20)':eval=frame"
        inputs += ["-ss", f"{ss:.3f}", "-t", f"{dur:.3f}", "-i", str(f)]
        parts.append(f"[{idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,{vol},"
                     f"afade=t=in:st=0:d={fi},afade=t=out:st={max(0, dur - fo):.3f}:d={fo},"
                     f"adelay={int(t0 * 1000)}|{int(t0 * 1000)}[b{idx}]")
        bl.append(f"[b{idx}]")
        print(f"  bed  {t0:6.2f} -> {t1:6.2f}  {f.name[3:40]} from {ss:.1f} s, {gain:+.1f} dB (+{lf:.0f} lift)")
        idx += 1
    if bl:
        parts.append("".join(bl) + f"amix=inputs={len(bl)}:normalize=0:dropout_transition=0[bed]")
    for f, off, t, trim in hits:
        gain = (lufs(src, max(0, t - 1.5), 3.0) - SFX_UNDER) - lufs(f, off, 1.5) + trim
        lead = min(off, t)                  # keep the swell before the transient, which lands ON t
        st = t - lead
        inputs += ["-ss", f"{off - lead:.3f}", "-t", f"{lead + 2.0:.3f}", "-i", str(f)]
        parts.append(f"[{idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                     f"volume={gain:.2f}dB,afade=t=out:st={lead + 1.3:.3f}:d=0.7,"
                     f"adelay={int(st * 1000)}|{int(st * 1000)}[s{idx}]")
        fl.append(f"[s{idx}]")
        print(f"  sfx  {t:6.2f}  {f.name[3:60]}  {gain:+.1f} dB")
        idx += 1
    if fl:
        parts.append("".join(fl) + f"amix=inputs={len(fl)}:normalize=0:dropout_transition=0[sfx]")
    if not bl and not fl:
        sys.exit("mix: the spec has no beds or hits")
    parts.append("[0:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                 f"asplit={1 + bool(bl) + bool(fl)}[dry]" + ("[k1]" if bl else "") + ("[k2]" if fl else ""))
    mixin = ["[dry]"]
    if bl:
        parts.append(f"[bed][k1]{DUCK}[bedduck]")
        mixin.append("[bedduck]")
    if fl:
        parts.append("[sfx][k2]sidechaincompress=threshold=0.090:ratio=2:attack=20:release=250:makeup=1[sfxduck]")
        mixin.append("[sfxduck]")
    parts.append("".join(mixin) + f"amix=inputs={len(mixin)}:normalize=0:dropout_transition=0:duration=first[premix]")
    tp_limit = [TARGET_TP]

    def run_mix(g):
        limit = 10 ** (tp_limit[0] / 20)
        run(["ffmpeg", "-hide_banner", "-v", "error"] + inputs +
            ["-filter_complex", ";".join(parts + [f"[premix]volume={g:.2f}dB,aresample=192000,alimiter=limit={limit:.4f}:level=disabled,aresample=48000[out]"]),
             "-map", "0:v", "-map", "[out]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
             "-t", f"{total:.3f}", "-movflags", "+faststart", "-y", out])
        return lufs(out, 0, 10 ** 6)

    g = TARGET_I - run_mix(0.0)
    got = run_mix(g)
    if abs(got - TARGET_I) > 0.25:
        got = run_mix(g + TARGET_I - got)
    # The AAC encode overshoots a sample-peak limiter by a different amount per mix (Episode 5: +1.7 dB,
    # then +3.2 dB on a low boom: inter-sample peaks a 48 kHz sample-peak limiter cannot see). The limiter runs
    # at 192 kHz; this measures the true peak AFTER the encode and lowers the limit only if it still overshoots.
    for _ in range(3):
        tp = true_peak(out)
        if tp <= TP_CEILING:
            break
        tp_limit[0] -= tp - TP_CEILING + 0.2
        got = run_mix(g + TARGET_I - got)
    print(f"output {got:.2f} LUFS, true peak {true_peak(out):.1f} dBTP (limit {tp_limit[0]:.1f}) -> {out}")


TP_CEILING = -1.2      # review T5 passes at <= -1.0 dBTP


def true_peak(path) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
                        "ebur128=peak=true:framelog=quiet", "-f", "null", "-"], capture_output=True, text=True).stderr
    vals = [float(l.split("Peak:")[1].split("dBFS")[0]) for l in r.splitlines() if "Peak:" in l]
    return vals[-1] if vals else 0.0


def band_db(x, t: float, n: float = 0.02, lo: float = 2000, hi: float = 6000) -> float:
    """lo-hi Hz energy of mono 48 kHz samples x over [t, t+n], dB. Pure, for tests."""
    import numpy as np
    seg = x[max(0, int(t * 48000)):int((t + n) * 48000)]
    if len(seg) < 8:
        return -120.0
    f = np.fft.rfftfreq(len(seg), 1 / 48000)
    p = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    return float(10 * np.log10(p[(f >= lo) & (f <= hi)].sum() + 1e-12))


BANDS = ((2000, 6000), (60, 400))       # clicks and ticks; thuds and soft impacts


def excess(mix, dry, t: float, offset: float, band=(2000, 6000)) -> float:
    """The most a 20 ms frame of the mix rises above the dry render in one band, around t."""
    import numpy as np
    return max(band_db(mix, u, 0.02, *band) - band_db(dry, u, 0.02, *band)
               for u in np.arange(t - 0.05, t + 0.4, 0.02)) - offset


def cmd_sfx(c: Ctx, a) -> None:
    """M052: is each effect audible? Its peak 20 ms excess over the no-music render in 2-6 kHz,
    against the same number on windows with no effect (the bed and the gain make those > 0). A
    0.35 s window dilutes a 50 ms click to 'buried', so it is measured per frame. Low thuds and
    soft impacts live under 2 kHz and read low here; judge those by ear."""
    import numpy as np

    def pcm(p):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", "48000",
                              "-f", "f32le", "-"], capture_output=True, check=True).stdout
        return np.frombuffer(raw, "<f4").astype(np.float64)
    W, total = kept(c)
    _, hits = plan_mix(c, W, total)
    mix, dry = pcm(c.dir / f"{c.output}.mp4"), pcm(raw_path(c))
    ht = [t for _, _, t, _ in hits]
    far = lambda t: all(abs(t - h) > 1.5 for h in ht)
    res = {}
    for b in BANDS:     # per band: the programme offset, then the effect-free control
        off = float(np.median([band_db(mix, t, 0.35, *b) - band_db(dry, t, 0.35, *b)
                               for t in np.arange(0.5, total - 0.5, 0.37) if far(t)]))
        ctl = [excess(mix, dry, t, off, b) for t in np.arange(1.0, total - 1.0, 0.9) if far(t)]
        res[b] = (off, float(np.percentile(ctl, 90)) if ctl else 10.0)
    print("  control (90th pct, effect-free): " + ", ".join(f"{b[0]}-{b[1]} Hz {v[1]:+.1f} dB" for b, v in res.items()))
    for f, _, t, _ in hits:
        m = max(((excess(mix, dry, t, res[b][0], b) - res[b][1], b) for b in BANDS))
        print(f"  {t:6.2f}  {Path(f).name[3:50]:<47} {m[0]:+5.1f} dB over control in {m[1][0]}-{m[1][1]} Hz"
              f"{'  BURIED: raise its trim' if m[0] < 0 else ''}")


SPEECH_DB, TIGHT = -30.0, 0.25


def tight_edges(ranges: list, level) -> list[str]:
    """Edges with speech within TIGHT s on the removed side: an OUT where speech resumes right
    after, an IN where it stops right before. Either the removed word is meant to go (a "तो", the
    other speaker) or the edge clips a word of the same phrase. Loose Hinglish word times made
    the second happen six times on podcast Episode 1 ("…के | लिए"), and whisper cannot judge a
    1 s slice, so each one is read by hand. `level(src, t)` is the 10 ms dB at t. Pure."""
    out = []
    for i, r in enumerate(ranges):
        nxt = ranges[i + 1] if i + 1 < len(ranges) else None
        prv = ranges[i - 1] if i else None
        if not (nxt and nxt["source"] == r["source"] and abs(nxt["start"] - r["end"]) < 0.02):
            k = next((k for k in range(60) if level(r["source"], r["end"] + k * 0.01) >= SPEECH_DB), 60)
            if k * 0.01 < TIGHT:
                out.append(f"#{i:02d} OUT {r['end']:.3f}: speech resumes {k * 10} ms after ({r.get('quote', '')[-30:]})")
        if not (prv and prv["source"] == r["source"] and abs(prv["end"] - r["start"]) < 0.02):
            j = next((j for j in range(60) if level(r["source"], r["start"] - 0.01 - j * 0.01) >= SPEECH_DB), 60)
            if j * 0.01 < TIGHT:
                out.append(f"#{i:02d} IN  {r['start']:.3f}: speech ends {j * 10} ms before ({r.get('quote', '')[:30]})")
    return out


def cmd_edges(c: Ctx, a) -> None:
    """Print every tight edge (see tight_edges) to read against the transcript and the levels."""
    import numpy as np
    edl, cache = c.edl, {}

    def level(src, t):
        if src not in cache:
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", edl["sources"][src], "-vn", "-ac", "1",
                                  "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
            cache[src] = np.frombuffer(raw, "<f4").astype(np.float64)
        seg = cache[src][int(t * 16000):int(t * 16000) + 160]
        return float(20 * np.log10(max(np.sqrt((seg ** 2).mean()), 1e-9))) if len(seg) else -99.0
    hits = tight_edges(edl["ranges"], level)
    print(f"{c.name}: {len(hits)} tight edge(s): check each is a word meant to go, not a clipped one")
    for h in hits:
        print("  " + h)


def cmd_review(c: Ctx, a) -> None:
    label = a.label or "v1"
    run(["rm", "-rf", c.dir / "review" / label])
    log = c.dir / f"review_{label}.log"
    with open(log, "w") as fh:
        run(["uv", "run", "python", HELPERS / "review.py", c.dir, "--render", c.dir / f"{c.output}.mp4",
             "--label", label, "--no-reel"], cwd=REPO, stdout=fh, stderr=subprocess.STDOUT)
    rep = (c.dir / "review" / label / "report.md").read_text().splitlines()
    print("\n".join(l for l in rep if re.match(r"- (\*\*FLAG|PASS T5|HIGH [A-Z0-9]+ #\d+ \d|MED [A-Z0-9]+ #\d+ \d|HIGH G|PASS G)|## Story", l)))


def cmd_preview(c: Ctx, a) -> None:
    out = c.dir / f"phone_preview_{c.name}_do_not_upload.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", c.dir / f"{c.output}.mp4", "-vf", "scale=720:1280",
         "-c:v", "libx264", "-preset", "medium", "-b:v", "3000k", "-maxrate", "3500k", "-bufsize", "7000k",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out])
    print(f"-> {out} ({out.stat().st_size / 1e6:.1f} MB)")


def cmd_all(c: Ctx, a) -> None:
    for step in (cmd_build, cmd_plate, cmd_captions, cmd_render, cmd_mix, cmd_sfx, cmd_review, cmd_preview):
        if step is cmd_plate and not c.spec.get("plate"):
            continue
        print(f"== {step.__name__[4:]}")
        step(c, a)


COMMANDS = {n[4:]: f for n, f in globals().items() if n.startswith("cmd_")}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("edit", type=Path)
    ap.add_argument("name")
    ap.add_argument("command", choices=sorted(COMMANDS))
    ap.add_argument("--label")
    a = ap.parse_args()
    COMMANDS[a.command](Ctx(a.edit, a.name), a)


if __name__ == "__main__":
    main()
