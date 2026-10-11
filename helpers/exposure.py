"""Exposure check for talking-head renders: shadow floor, face vs frame, red clipping.

render.py runs this on the first rendered segment that contains a face, so a dark
or crushed look is reported minutes into a render instead of after the whole thing.
It reads ONE frame of an already-rendered segment and warns when:

- the darkest 5% of the frame (p5) is below 20: shadows are crushed, eyes and beard
  go to black. Episode 2's grade put p5 at 5 on the 2026-10-11 test clips.
- the face is more than 15 luma darker than the frame average: the subject is
  under-lit relative to the room.
- more than 0.5% of strongly red/orange pixels sit at R=255: clothing has clipped
  and lost its fabric detail. The old npl=100 tone-map clipped a red jersey 2.0%.
- the grade sets saturation above 1.0: the HLG tone-map already adds saturation.

Luma is BT.709 (0.2126 R + 0.7152 G + 0.0722 B) on the decoded 8-bit RGB frame, the
same measure kb/gotchas.md records its numbers in.

The face box comes from mediapipe's bundled face detector, run in the
`retouch-env` interpreter that helpers/retouch_teeth.py builds (mediapipe has no
wheel for the repo's own Python). The check never builds that env itself, and
never fails a render: with no env, or no face found, the face rule is skipped and
the report says so.

Usage:
    uv run python helpers/exposure.py <video> [--at SECONDS] [--grade '<filter>'] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

P5_FLOOR = 20.0
FACE_DARKER_LIMIT = 15.0
RED_CLIP_LIMIT = 0.005
SATURATION_LIMIT = 1.0

WORK_W, WORK_H = 1280, 720
FACE_ENV_PYTHON = Path.home() / ".cache" / "video-use" / "retouch-env" / "bin" / "python"

FACE_WORKER = r'''
import sys, json
import numpy as np, mediapipe as mp
W, H = int(sys.argv[1]), int(sys.argv[2])
rgb = np.frombuffer(sys.stdin.buffer.read(), np.uint8).reshape(H, W, 3)
# model_selection=1 is the full-range model: a seated talking head at 1-3 m
with mp.solutions.face_detection.FaceDetection(model_selection=1,
                                               min_detection_confidence=0.5) as fd:
    res = fd.process(np.ascontiguousarray(rgb))
boxes = []
for d in res.detections or []:
    b = d.location_data.relative_bounding_box
    boxes.append([b.xmin * W, b.ymin * H, b.width * W, b.height * H, d.score[0]])
print(json.dumps(boxes))
'''


def read_frame(video: Path, t: float | None = None) -> np.ndarray:
    """One frame as HxWx3 uint8 RGB at the working size; the middle frame by default."""
    if t is None:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
            capture_output=True, text=True, check=True)
        t = float(out.stdout.strip()) / 2
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{t:.3f}", "-i", str(video),
         "-frames:v", "1", "-vf", f"scale={WORK_W}:{WORK_H}",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True).stdout
    if len(raw) < WORK_W * WORK_H * 3:
        raise ValueError(f"no frame decoded from {video} at {t:.3f}s")
    return np.frombuffer(raw[:WORK_W * WORK_H * 3], np.uint8).reshape(WORK_H, WORK_W, 3)


def luma(rgb: np.ndarray) -> np.ndarray:
    f = rgb.astype(np.float32)
    return 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]


def frame_stats(rgb: np.ndarray) -> dict:
    y = luma(rgb)
    return {"mean": float(y.mean()),
            "p5": float(np.percentile(y, 5)),
            "p95": float(np.percentile(y, 95))}


def red_clip(rgb: np.ndarray) -> dict:
    """Share of strongly red/orange pixels, and the fraction of those clipped at R=255."""
    r, g, b = (rgb[..., i].astype(np.int32) for i in range(3))
    red = (r > 150) & (r > 2 * g) & (r > 2 * b)
    n_red = int(red.sum())
    clipped = int((red & (r >= 254)).sum())
    return {"red_share": n_red / red.size,
            "clipped": clipped / n_red if n_red else 0.0}


def detect_face(rgb: np.ndarray, python: Path = FACE_ENV_PYTHON) -> tuple[list | None, str]:
    """(x, y, w, h) of the largest face in working-size pixels, or None with the reason."""
    if not python.exists():
        return None, f"face not measured: {python.parent.parent} missing (built by retouch_teeth.py)"
    try:
        out = subprocess.run([str(python), "-c", FACE_WORKER, str(rgb.shape[1]), str(rgb.shape[0])],
                             input=np.ascontiguousarray(rgb).tobytes(),
                             capture_output=True, check=True, timeout=120)
        boxes = json.loads(out.stdout.decode().strip().splitlines()[-1])
    except (subprocess.SubprocessError, ValueError, IndexError, OSError) as e:
        return None, f"face not measured: detector failed ({type(e).__name__})"
    if not boxes:
        return None, "no face in frame"
    x, y, w, h, _score = max(boxes, key=lambda b: b[2] * b[3])
    return [x, y, w, h], ""


def face_luma(rgb: np.ndarray, box: list) -> float:
    """Mean luma over the central 60% of the face box, which keeps hair, beard edge
    and background out of a box that the detector draws generously."""
    x, y, w, h = box
    x0, x1 = int(x + 0.2 * w), int(x + 0.8 * w)
    y0, y1 = int(y + 0.2 * h), int(y + 0.8 * h)
    H, W = rgb.shape[:2]
    x0, x1 = max(0, x0), min(W, x1)
    y0, y1 = max(0, y0), min(H, y1)
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"face box {box} falls outside the frame")
    return float(luma(rgb[y0:y1, x0:x1]).mean())


def grade_saturation(grade: str) -> float | None:
    """The highest `saturation=` an eq/hue filter in the grade sets, or None."""
    vals = [float(v) for v in re.findall(r"saturation=([0-9]*\.?[0-9]+)", grade or "")]
    return max(vals) if vals else None


def evaluate(stats: dict, red: dict, face_mean: float | None, grade: str = "") -> list[str]:
    """The warnings for one measured frame. Pure, so the thresholds are testable."""
    warns = []
    if stats["p5"] < P5_FLOOR:
        warns.append(f"shadows crushed: p5 {stats['p5']:.1f} < {P5_FLOOR:.0f} "
                     "(eyes and beard go to black; lift the black point)")
    if face_mean is not None and stats["mean"] - face_mean > FACE_DARKER_LIMIT:
        warns.append(f"face under-lit: face {face_mean:.1f} is "
                     f"{stats['mean'] - face_mean:.1f} below the frame mean {stats['mean']:.1f} "
                     f"(limit {FACE_DARKER_LIMIT:.0f})")
    if red["clipped"] > RED_CLIP_LIMIT:
        warns.append(f"red clipping: {red['clipped']:.2%} of red/orange pixels at R=255 "
                     f"(limit {RED_CLIP_LIMIT:.1%})")
    sat = grade_saturation(grade)
    if sat is not None and sat > SATURATION_LIMIT:
        warns.append(f"grade saturation {sat:g} > {SATURATION_LIMIT:g} "
                     "(the HLG tone-map already adds saturation)")
    return warns


def check(video: Path, grade: str = "", t: float | None = None,
          python: Path = FACE_ENV_PYTHON) -> dict:
    rgb = read_frame(video, t)
    stats = frame_stats(rgb)
    red = red_clip(rgb)
    box, why = detect_face(rgb, python)
    face_mean = face_luma(rgb, box) if box else None
    return {"video": str(video), "frame": stats, "red": red,
            "face_box": box, "face_mean": face_mean, "face_note": why,
            "warnings": evaluate(stats, red, face_mean, grade)}


def report(res: dict) -> str:
    s = res["frame"]
    face = (f"face {res['face_mean']:.1f}" if res["face_mean"] is not None
            else res["face_note"])
    lines = [f"exposure check: {Path(res['video']).name}",
             f"  frame mean {s['mean']:.1f}  p5 {s['p5']:.1f}  p95 {s['p95']:.1f}  |  {face}"
             f"  |  red clipped {res['red']['clipped']:.2%}"]
    lines += [f"  WARNING  {w}" for w in res["warnings"]] or ["  ok"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video", type=Path)
    ap.add_argument("--at", type=float, default=None, help="seconds into the file (default: middle)")
    ap.add_argument("--grade", default="", help="the grade filter, to check its saturation")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = check(args.video, args.grade, args.at)
    print(json.dumps(res, indent=2) if args.json else report(res))
    return 1 if res["warnings"] else 0


if __name__ == "__main__":
    sys.exit(main())
