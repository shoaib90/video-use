"""Generate a person matte so a graphic can pass BEHIND the speaker.

The reference does this with its biggest figure — the number sweeps across the
frame and the speaker occludes it — and it is the difference between a graphic
sitting on the shot and one that lives in it.

**The picture never round-trips through Python.** Only the matte is computed
here; every composite stays in ffmpeg. That is deliberate: reading frames out
and writing them back costs ~20 dB through a bgr24 round trip and another ~19
if the rawvideo input is untagged, both silently (kb/gotchas.md). A matte is a
new signal rather than a modified picture, so none of that applies, and the
4K master is never decoded into numpy at all.

Three passes over the raw mask, each fixing something visible:

* **guided filter** against the frame's own luma — the model is 256x256
  natively, so its edges are soft and do not follow the subject;
* **temporal smoothing** — per-frame segmentation flickers, and a matte that
  flickers is far more noticeable than one that is slightly wrong;
* **dilate** — a matte that is a little generous hides a seam, where one that
  is a little tight eats into the shoulder. Err outward.

Usage:
    uv run python helpers/matte.py <video> -o <edit>/mattes/seg00.mp4
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

TOOL_ENV = Path.home() / ".cache" / "video-use" / "matte-env"
TOOL_PYTHON = "3.11"
# mediapipe has no macOS arm64 wheel for the repo's own 3.12+, and pulls a
# numpy of its own, so it gets its own interpreter exactly as DeepFilterNet does
TOOL_PACKAGES = ["mediapipe", "numpy", "pillow", "scipy"]

MODEL_DIR = Path.home() / ".cache" / "video-use" / "models"
MODEL = MODEL_DIR / "selfie_segmenter.tflite"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/image_segmenter/"
             "selfie_segmenter/float16/latest/selfie_segmenter.tflite")

WORK_W = 1280            # matte working width; the model is 256 native anyway


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def ensure_tool_env(env_dir: Path = TOOL_ENV) -> Path:
    py = env_dir / "bin" / "python"
    if py.exists():
        return py
    if not shutil.which("uv"):
        sys.exit("uv is required to create the matte environment; see kb/environment.md")
    print(f"creating matte env at {env_dir} (once, ~300 MB)")
    run(["uv", "venv", "--python", TOOL_PYTHON, str(env_dir)])
    run(["uv", "pip", "install", "--python", str(py), *TOOL_PACKAGES])
    return py


def ensure_model() -> Path:
    if MODEL.exists():
        return MODEL
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"fetching {MODEL.name}")
    run(["curl", "-sSfL", "-o", str(MODEL), MODEL_URL])
    return MODEL


def probe(video: Path) -> dict:
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
               "-show_entries", "format=duration", "-of", "json", str(video)]).stdout
    d = json.loads(out)
    s = d["streams"][0]
    num, den = (s["r_frame_rate"].split("/") + ["1"])[:2]
    return {"w": s["width"], "h": s["height"], "fps": float(num) / float(den),
            "duration": float(d["format"]["duration"])}


# --------------------------------------------------------------------- worker
WORKER = r'''
import sys, json, numpy as np
from scipy.ndimage import uniform_filter, grey_dilation
import mediapipe as mp
from mediapipe.tasks import python as mpy
from mediapipe.tasks.python import vision

cfg = json.loads(sys.argv[1])
W, H, MODEL = cfg["w"], cfg["h"], cfg["model"]
SMOOTH, DILATE, FEATHER = cfg["smooth"], cfg["dilate"], cfg["feather"]

seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
    base_options=mpy.BaseOptions(model_asset_path=MODEL),
    output_category_mask=False, output_confidence_masks=True))


def guided(I, p, r=8, eps=1e-3):
    """Edge-aware refinement of p using I as the guide. The model's own edges
    are 256px soft; this snaps them to the picture."""
    box = lambda x: uniform_filter(x, size=r, mode="nearest")
    mI, mp_ = box(I), box(p)
    a = (box(I * p) - mI * mp_) / (box(I * I) - mI * mI + eps)
    return box(a) * I + box(mp_ - a * mI)


prev = None
frame_bytes = W * H * 3
while True:
    buf = sys.stdin.buffer.read(frame_bytes)
    if len(buf) < frame_bytes:
        break
    rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    res = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB,
                               data=np.ascontiguousarray(rgb)))
    m = np.squeeze(res.confidence_masks[0].numpy_view()).astype(np.float32)

    luma = (rgb[:, :, 0] * 0.2126 + rgb[:, :, 1] * 0.7152
            + rgb[:, :, 2] * 0.0722).astype(np.float32) / 255.0
    m = np.clip(guided(luma, m), 0.0, 1.0)

    if DILATE > 0:                       # err outward; a tight matte clips a shoulder
        m = grey_dilation(m, size=int(DILATE))
    if FEATHER > 0:
        m = uniform_filter(m, size=int(FEATHER), mode="nearest")
    if prev is not None and SMOOTH > 0:  # per-frame flicker is worse than being slightly wrong
        m = SMOOTH * prev + (1.0 - SMOOTH) * m
    prev = m

    sys.stdout.buffer.write((np.clip(m, 0, 1) * 255).astype(np.uint8).tobytes())
sys.stdout.buffer.flush()
'''


def build_matte(video: Path, out: Path, smooth: float = 0.55,
                dilate: int = 5, feather: int = 7, quiet: bool = False) -> Path:
    py = ensure_tool_env()
    model = ensure_model()
    info = probe(video)
    w = WORK_W
    h = int(round(info["h"] * w / info["w"] / 2) * 2)
    out.parent.mkdir(parents=True, exist_ok=True)

    src = subprocess.Popen(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(video),
         "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    worker = subprocess.Popen(
        [str(py), "-c", WORKER, json.dumps(
            {"w": w, "h": h, "model": str(model), "smooth": smooth,
             "dilate": dilate, "feather": feather})],
        stdin=src.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    src.stdout.close()
    sink = subprocess.Popen(
        ["ffmpeg", "-nostdin", "-v", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}",
         "-r", f"{info['fps']:.6f}", "-i", "-",
         # the matte is data, not picture: keep it sharp and losslessly flat
         "-c:v", "libx264", "-qp", "0", "-pix_fmt", "gray",
         "-preset", "veryfast", str(out)],
        stdin=worker.stdout)
    worker.stdout.close()
    sink.communicate()
    worker.wait()
    if sink.returncode:
        raise RuntimeError("matte encode failed")

    got = probe(out)
    if not quiet:
        print(f"  matte → {out.name}  {got['w']}x{got['h']}  {got['duration']:.2f}s "
              f"(source {info['duration']:.2f}s)")
    # A matte that does not cover the whole clip silently reveals the subject
    # for the remainder, so this is checked rather than assumed.
    if abs(got["duration"] - info["duration"]) > 0.15:
        raise RuntimeError(
            f"matte is {got['duration']:.3f}s for a {info['duration']:.3f}s source")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--smooth", type=float, default=0.55,
                    help="temporal EMA, 0 = none (default 0.55)")
    ap.add_argument("--dilate", type=int, default=5)
    ap.add_argument("--feather", type=int, default=7)
    a = ap.parse_args()
    build_matte(a.video, a.output, a.smooth, a.dilate, a.feather)


if __name__ == "__main__":
    main()
