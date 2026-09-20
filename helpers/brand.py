"""Per-channel brand: palette, type scale, shape language.

The reference video's second design pillar is "brand system — colour and
typography", and its point is consistency: the same channel should look like
the same channel across episodes. So this is a file that lives with the
footage, not constants in a helper.

Sizes are fractions of the OUTPUT HEIGHT throughout, so one brand is correct in
a 720p draft and a 2160p master.

`derive()` measures a palette off already-delivered work rather than asserting
one. A brand invented in the abstract clashes with the footage it has to sit
on; one measured from the grade cannot.
"""
from __future__ import annotations

import colorsys
import json
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Brand:
    # colour
    bg: str = "#0B0B0C"
    fg: str = "#F2EDE4"
    muted: str = "#9A948B"
    accent: str = "#F2973C"
    accent2: str = "#3C5AF2"
    chip_bg: str = "#000000A6"

    # typography — face paths, and sizes as a fraction of output height
    font_regular: str = "/System/Library/Fonts/HelveticaNeue.ttc"
    font_regular_index: int = 0
    font_bold: str = "/System/Library/Fonts/HelveticaNeue.ttc"
    font_bold_index: int = 1
    font_light: str = "/System/Library/Fonts/HelveticaNeue.ttc"
    font_light_index: int = 7
    # a face that must cover every script the channel speaks; drawtext does no
    # fallback, so a Latin-only face renders Devanagari as blank boxes
    font_intl: str = "/System/Library/Fonts/Kohinoor.ttc"
    font_intl_index: int = 0

    size_display: float = 1 / 7          # a hero number
    size_title: float = 1 / 16
    size_body: float = 1 / 30
    size_caption: float = 1 / 44
    tracking: float = 0.06               # em

    # shape
    radius: float = 1 / 90               # corner radius as a fraction of height
    stroke: float = 1 / 540
    margin: float = 1 / 20
    shadow_blur: float = 1 / 300
    shadow_alpha: int = 190

    # motion defaults
    stagger_per: float = 0.085

    def px(self, frac: float, height: int) -> int:
        return max(1, round(frac * height))

    def save(self, path: Path) -> Path:
        Path(path).write_text(json.dumps(asdict(self), indent=1))
        return Path(path)

    @staticmethod
    def load(path: Path) -> "Brand":
        d = json.loads(Path(path).read_text())
        known = {f for f in Brand.__dataclass_fields__}
        return Brand(**{k: v for k, v in d.items() if k in known})


def _hex(rgb) -> str:
    return "#" + "".join(f"{int(max(0, min(255, c))):02X}" for c in rgb)


def derive(sources: list[Path], samples: int = 16) -> tuple[Brand, dict]:
    """Measure a palette from delivered work.

    Returns the brand and the evidence, because a derived value the caller
    cannot inspect is just a magic constant with extra steps.
    """
    import numpy as np

    px = []
    for src in sources:
        src = Path(src)
        if not src.exists():
            continue
        dur = 0.0
        try:
            dur = float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", str(src)],
                capture_output=True, text=True).stdout or 0)
        except ValueError:
            pass
        times = [dur * (i + 0.5) / samples for i in range(samples)] if dur > 1 else [0]
        for t in times:
            r = subprocess.run(
                ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t}", "-i", str(src),
                 "-frames:v", "1", "-vf", "scale=160:-2", "-f", "rawvideo",
                 "-pix_fmt", "rgb24", "-"], capture_output=True)
            if r.stdout:
                px.append(np.frombuffer(r.stdout, dtype=np.uint8).reshape(-1, 3))
    if not px:
        return Brand(), {"error": "no pixels sampled"}
    px = np.vstack(px).astype(float)

    lum = px.mean(axis=1)
    shadow = px[lum < np.percentile(lum, 4)].mean(axis=0)
    hilite = px[lum > np.percentile(lum, 96)].mean(axis=0)

    hsv = [colorsys.rgb_to_hsv(*(p / 255)) for p in px[::29]]
    sat = [h for h in hsv if h[1] > 0.35]
    hues = []
    if sat:
        import numpy as _np
        hist, edges = _np.histogram([h[0] for h in sat], bins=18, range=(0, 1))
        for idx in _np.argsort(hist)[::-1][:3]:
            h = (edges[idx] + edges[idx + 1]) / 2
            hues.append((h, int(hist[idx])))

    def from_hue(h, s=0.78, v=0.95):
        return _hex([c * 255 for c in colorsys.hsv_to_rgb(h, s, v)])

    b = Brand()
    # keep the background genuinely dark rather than the measured near-black,
    # which is often crushed to pure 0 by the grade
    b.bg = _hex([max(c, 10) for c in shadow])
    b.fg = _hex(hilite)
    b.muted = _hex([c * 0.62 for c in hilite])
    warm = next((h for h, _ in hues if h < 0.12 or h > 0.92), None)
    cool = next((h for h, _ in hues if 0.5 < h < 0.75), None)
    if warm is not None:
        b.accent = from_hue(warm)
    if cool is not None:
        b.accent2 = from_hue(cool)

    evidence = {
        "pixels": int(len(px)),
        "mean_luma": round(float(px.mean()), 1),
        "shadow": _hex(shadow), "highlight": _hex(hilite),
        "dominant_hues_deg": [[round(h * 360), n] for h, n in hues],
        "note": "accent taken from the warmest dominant hue, accent2 from the coolest",
    }
    return b, evidence


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Derive a brand from delivered work")
    ap.add_argument("sources", nargs="+", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    a = ap.parse_args()
    b, ev = derive(a.sources)
    for k, v in ev.items():
        print(f"  {k}: {v}")
    b.save(a.output)
    print(f"\nwrote {a.output}")
    for k in ("bg", "fg", "muted", "accent", "accent2"):
        print(f"  {k:<8} {getattr(b, k)}")
