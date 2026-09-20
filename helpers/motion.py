"""The motion engine: curves, weight, rhythm, and frame rendering.

Named after the four principles the reference video builds everything on —
timing, weight, rhythm, intention — because the failure mode this module exists
to prevent is the one that made an earlier attempt look amateur: *every element
animating identically*. One curve, one duration, everywhere. His example is
exact: "a logo landing and a subtitle fading in should not feel the same."

So the unit of authoring here is a ROLE, not a duration. You say a thing is a
`hero` or an `aside`, and the role carries its own curve, travel, timing and
whether it earns motion blur.

Rendering is a small canvas padded to frame by ffmpeg rather than a full 4K
draw per frame — same result, a fraction of the time — and encoded ProRes 4444,
because this ffmpeg build silently drops alpha from VP9 and hands back a valid,
fully opaque file.
"""
from __future__ import annotations

import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

# -------- curves --------------------------------------------------------------
# Never `linear` — it reads as mechanical. Everything here lands rather than
# stops.


def linear(t: float) -> float:
    return t


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_out_expo(t: float) -> float:
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def ease_in_out_cubic(t: float) -> float:
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def back_out(t: float, overshoot: float = 1.70158) -> float:
    """Overshoots the target and settles back. This is what makes something feel
    like it has mass — it is the single biggest difference between a fade and a
    landing."""
    c3 = overshoot + 1
    return 1 + c3 * (t - 1) ** 3 + overshoot * (t - 1) ** 2


def anticipate(t: float, amount: float = 0.28) -> float:
    """Pulls back slightly before moving. Reads as intent."""
    if t < 0.30:
        return -amount * ease_out_cubic(t / 0.30)
    u = (t - 0.30) / 0.70
    return -amount + (1 + amount) * ease_out_cubic(u)


def spring(t: float, damping: float = 0.55, freq: float = 3.1) -> float:
    """Decaying oscillation. Heavier than `back_out`; use for a real arrival."""
    if t >= 1:
        return 1.0
    return 1 - math.exp(-damping * freq * math.pi * t) * math.cos(freq * math.pi * t)


CURVES = {
    "linear": linear,
    "ease_out": ease_out_cubic,
    "ease_out_expo": ease_out_expo,
    "ease_in_out": ease_in_out_cubic,
    "back_out": back_out,
    "anticipate": anticipate,
    "spring": spring,
}


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


# -------- weight --------------------------------------------------------------


@dataclass(frozen=True)
class Weight:
    """How a role moves. `travel` is a fraction of the type size, so weight is
    resolution-independent like everything else.

    Transforms and opacity take DIFFERENT curves. A spring or `back_out` is
    what gives position and scale their sense of mass, but the same curve on
    alpha overshoots past fully-opaque and then dips back: `hero` peaks at
    1.205, which clamps to 255 and then falls to 96% before settling, so the
    element visibly pulses as it arrives. Opacity has no mass and wants a
    monotonic curve. (The rule is from OpenDesign's craft/animation-discipline,
    Apache-2.0: curve for opacity and colour, spring for transforms.)
    """
    duration: float
    curve: str
    travel: float = 0.0
    scale_from: float = 1.0
    blur: bool = False
    alpha_curve: str = "ease_out_expo"

    def at(self, t: float, start: float = 0.0) -> float:
        """Transform progress. May overshoot 1 - that is the point."""
        p = (t - start) / self.duration if self.duration > 0 else 1.0
        p = 0.0 if p < 0 else 1.0 if p > 1 else p
        return CURVES[self.curve](p)

    def alpha_at(self, t: float, start: float = 0.0) -> float:
        """Opacity progress. Never leaves [0, 1]."""
        p = (t - start) / self.duration if self.duration > 0 else 1.0
        p = 0.0 if p < 0 else 1.0 if p > 1 else p
        return clamp01(CURVES[self.alpha_curve](p))


WEIGHTS = {
    # A number or logo arriving. Heavy: it overshoots, it travels, it blurs.
    "hero": Weight(0.72, "spring", travel=0.42, scale_from=0.86, blur=True),
    # A heading or list item taking its place.
    "primary": Weight(0.50, "back_out", travel=0.24, scale_from=0.96),
    # Supporting text following a primary.
    "secondary": Weight(0.38, "ease_out_expo", travel=0.14),
    # An aside; should barely register as motion.
    "aside": Weight(0.30, "ease_out", travel=0.06),
    # A rule, underline or strike drawing across.
    "draw": Weight(0.42, "ease_out_expo"),
    # Leaving.
    "exit": Weight(0.34, "ease_out", travel=-0.10),
}


def stagger(index: int, per: float = 0.085, curve_bias: float = 1.0) -> float:
    """Delay for the nth element of a group.

    Rhythm is the principle this serves: a group that arrives all at once has no
    pulse, and one that arrives evenly spaced is a metronome. `curve_bias` above
    1 compresses later items so the group accelerates, which reads as one
    gesture rather than a queue.
    """
    return per * (index ** curve_bias if curve_bias != 1.0 else index)


# -------- rendering -----------------------------------------------------------


@dataclass
class Canvas:
    """Where the graphic lives inside the frame. Small, then padded to frame."""
    w: int
    h: int
    x: int
    y: int
    frame_w: int = 3840
    frame_h: int = 2160


def render_sequence(draw_fn, canvas: Canvas, n_frames: int, fps: float,
                    out_path: Path, shutter: int = 1,
                    work: Path | None = None, quiet: bool = False) -> Path:
    """Render `draw_fn(img, t)` for every frame and encode ProRes 4444.

    `shutter` > 1 averages that many sub-samples within each frame interval —
    real motion blur, not a directional smear. It is off by default because it
    multiplies render time; a component asks for it via its weight.
    """
    work = Path(work or out_path.parent / f".{out_path.stem}_frames")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    for i in range(n_frames):
        if shutter > 1:
            acc = None
            for k in range(shutter):
                t = (i + k / shutter) / fps
                img = Image.new("RGBA", (canvas.w, canvas.h), (0, 0, 0, 0))
                draw_fn(img, t)
                a = img.convert("RGBA")
                acc = a if acc is None else Image.blend(acc, a, 1.0 / (k + 1))
            out = acc
        else:
            out = Image.new("RGBA", (canvas.w, canvas.h), (0, 0, 0, 0))
            draw_fn(out, i / fps)
        out.save(work / f"f{i:05d}.png")

    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error",
           "-framerate", f"{fps:.6f}", "-i", str(work / "f%05d.png"),
           "-vf", (f"pad={canvas.frame_w}:{canvas.frame_h}:{canvas.x}:{canvas.y}"
                   f":color=#00000000,format=yuva444p10le"),
           "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
           str(out_path)]
    subprocess.run(cmd, check=True)
    shutil.rmtree(work, ignore_errors=True)
    if not quiet:
        print(f"  overlay → {out_path.name}  ({n_frames} frames, shutter {shutter})")
    return out_path


def verify_alpha(path: Path, probe_t: float, box: tuple[int, int, int, int]) -> dict:
    """Alpha must be checked on the ENCODED file, not assumed from the encode
    succeeding: VP9 in this build returns a valid, fully opaque file."""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{probe_t}",
                        "-i", str(path), "-frames:v", "1", "-f", "rawvideo",
                        "-pix_fmt", "rgba", "-"], capture_output=True)
    n = len(r.stdout)
    side = int((n / 4) ** 0.5)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    # infer height from the known frame width
    for w in (3840, 1920, 1280):
        if n % (w * 4) == 0:
            h = n // (w * 4)
            a = a.reshape(h, w, 4)
            break
    else:
        a = a.reshape(side, side, 4)
    x0, y0, x1, y1 = box
    return {"corner_alpha": int(a[8, 8, 3]),
            "max_alpha_in_box": int(a[y0:y1, x0:x1, 3].max()),
            "opaque_px": int((a[y0:y1, x0:x1, 3] > 200).sum())}
