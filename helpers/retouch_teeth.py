"""Whiten one person's teeth over a time window in a rendered segment.

Scope, deliberately narrow
--------------------------
This runs on a window you name, on ONE face you name, inside an already-rendered
segment. It is not a "beautify the whole film" pass, for two reasons found by
measuring the footage rather than guessing:

  * Teeth are tiny. Across a sample of every full-frame segment of a 27-minute
    vlog, visible enamel was a median 0.013% of the frame — a patch roughly
    16 px across. Over most of the film, whitening is invisible and only risks
    flicker.
  * The clearest teeth in a two-hander are usually not the person who asked.
    On Detour-2 the best-scoring frames were all the passenger, not the
    presenter. A mouth detector treats whoever is in frame, so the face has to
    be chosen explicitly — retouching someone else's appearance is not a
    decision this script should make silently.

Where the subject IS smiling wide the effect is clear and worth doing: the mouth
was ~100x23 px and the yellow plainly visible.

    uv run python helpers/retouch_teeth.py seg.mp4 -o out.mp4 --window 2.5 7.5
    uv run python helpers/retouch_teeth.py seg.mp4 -o out.mp4 --window 0 49 --face left

Needs the mediapipe environment; see `helpers/denoise.py` for the same pattern
and kb/environment.md for the pins.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

TOOL_PYTHON = "3.11"
# mediapipe 1.x dropped `mp.solutions` and its Tasks API aborts on this machine
# with "Check failed: service_ Service is unavailable" from the Metal helper,
# on CPU delegate too. 0.10.x keeps the classic FaceMesh and works.
TOOL_PACKAGES = ["mediapipe==0.10.14", "opencv-python-headless", "numpy<2"]
TOOL_ENV = Path.home() / ".cache" / "video-use" / "retouch-env"

# Inner-lip ring from the FaceMesh topology — the mouth opening, not the lips.
INNER_LIP = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415,
             310, 311, 312, 13, 82, 81, 80, 191]

WORKER = r'''
import cv2, mediapipe as mp, numpy as np, subprocess, sys, json
seg, out, t0, t1, crf, face, desat, lift, W, H, FPS = (
    sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5],
    sys.argv[6], float(sys.argv[7]), float(sys.argv[8]),
    int(sys.argv[9]), int(sys.argv[10]), float(sys.argv[11]))
INNER = json.loads(sys.argv[12])
RAMP, HOLD = 0.25, 3
ysz, csz = W*H, (W//2)*(H//2)

# ffmpeg hands over yuv420p and takes yuv420p back. An earlier version piped
# bgr24 and it was NOT harmless: yuv420p -> bgr24 -> yuv420p is not idempotent
# and dropped the whole segment to 34 dB PSNR against its own source, where a
# plain re-encode scores 55 dB. Every pixel was altered to retouch 600 of them.
dec = subprocess.Popen(["ffmpeg","-v","error","-i",seg,"-f","rawvideo",
                        "-pix_fmt","yuv420p","-"], stdout=subprocess.PIPE)
# The rawvideo INPUT must be tagged. Raw frames carry no colour metadata, so
# ffmpeg assumes full range and inserts a full->limited conversion on the way to
# the encoder: 33.8 dB with the tags missing, 52.4 dB with them present.
enc = subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","yuv420p",
                        "-color_range","tv","-colorspace","bt709",
                        "-s",f"{W}x{H}","-r",str(FPS),"-i","-","-i",seg,
                        "-map","0:v","-map","1:a","-c:v","libx264","-preset","slow",
                        "-crf",crf,"-pix_fmt","yuv420p","-color_range","tv",
                        "-colorspace","bt709","-color_primaries","bt709",
                        "-color_trc","bt709","-c:a","copy","-movflags","+faststart",
                        out], stdin=subprocess.PIPE)

mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=False, max_num_faces=3,
                                       refine_landmarks=True,
                                       min_detection_confidence=0.3,
                                       min_tracking_confidence=0.3)

def mask_for(bgr):
    h, w = bgr.shape[:2]
    res = mesh.process(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    if not res.multi_face_landmarks:
        return None
    cands = []
    for fl in res.multi_face_landmarks:
        lm = fl.landmark
        pts = np.array([[lm[i].x*w, lm[i].y*h] for i in INNER], np.int32)
        cands.append((pts[:,0].mean(), pts))
    cands.sort(key=lambda t: t[0])
    pts = (cands[-1] if face == "right" else cands[0])[1]
    mouth = np.zeros((h, w), np.uint8); cv2.fillPoly(mouth, [pts], 255)
    inside = mouth > 0
    if inside.sum() < 30:
        return None
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    # named Hue, not H: H is the frame height everywhere else in this worker,
    # and shadowing it here is a trap waiting for the next edit
    Hue = hsv[:,:,0].astype(np.int16)
    V = hsv[:,:,2].astype(np.int16); S = hsv[:,:,1].astype(np.int16)
    # Enamel is the brighter part of the mouth opening; the rest is lip, tongue
    # and shadow, which sit around hue 165 (pink).
    #
    # A plain "bright and desaturated" rule is the obvious test and it selects
    # the WRONG teeth. Measured on a real smile: 656 bright pixels failed an
    # S<90 cut, and their mean saturation was 99 at hue 23 — that is precisely
    # the yellow enamel the retouch exists to fix. The rule kept the teeth that
    # were already white and skipped the discoloured ones, which is why the
    # first pass read as "barely any difference".
    #
    # So: bright AND (yellow-ish at moderate saturation, OR near-neutral).
    enamel = (inside & (V >= np.percentile(V[inside], 45))
              & (((S < 115) & (Hue >= 8) & (Hue <= 45)) | (S < 70)))
    if enamel.sum() < 20:
        return None
    return np.clip(cv2.GaussianBlur(enamel.astype(np.float32)*255, (0,0), 2.0)/255.0, 0, 1)

n = applied = held = lost = 0
last, age = None, 99
sizes = []
while True:
    raw = dec.stdout.read(ysz + 2*csz)
    if len(raw) < ysz + 2*csz:
        break
    t = n / FPS
    if t0 <= t <= t1:
        bgr = cv2.cvtColor(np.frombuffer(raw, np.uint8).reshape(H*3//2, W),
                           cv2.COLOR_YUV2BGR_I420)
        m = mask_for(bgr)
        if m is None and last is not None and age < HOLD:
            m, age = last, age + 1; held += 1      # brief dropout: hold the mask
        elif m is None:
            lost += 1
        else:
            last, age = m, 0
        s = max(0.0, min(1.0, (t-t0)/RAMP, (t1-t)/RAMP))
        if m is not None and s > 0:
            mm = m * s
            mc = cv2.resize(mm, (W//2, H//2), interpolation=cv2.INTER_AREA)
            Y = np.frombuffer(raw[:ysz], np.uint8).reshape(H, W).astype(np.float32)
            U = np.frombuffer(raw[ysz:ysz+csz], np.uint8).reshape(H//2, W//2).astype(np.float32)
            V2 = np.frombuffer(raw[ysz+csz:], np.uint8).reshape(H//2, W//2).astype(np.float32)
            Y = np.clip(Y + lift*mm, 0, 255)
            U = np.clip(128 + (U-128)*(1 - desat*mc), 0, 255)
            V2 = np.clip(128 + (V2-128)*(1 - desat*mc), 0, 255)
            raw = (Y.astype(np.uint8).tobytes() + U.astype(np.uint8).tobytes()
                   + V2.astype(np.uint8).tobytes())
            applied += 1; sizes.append(float((m > 0.05).sum()))
    enc.stdin.write(raw)
    n += 1
enc.stdin.close(); enc.wait(); dec.wait()
print(json.dumps({"frames": n, "applied": applied, "held": held,
                  "no_detection": lost,
                  "mask_px_median": float(np.median(sizes)) if sizes else 0.0}))
'''


def ensure_tool_env(env_dir: Path = TOOL_ENV) -> Path:
    py = env_dir / "bin" / "python"
    if py.exists():
        return py
    if not shutil.which("uv"):
        sys.exit("uv is required to create the retouch environment")
    print(f"first run: creating {env_dir} (python {TOOL_PYTHON}, mediapipe)")
    env_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["uv", "venv", "--python", TOOL_PYTHON, str(env_dir)], check=True)
    subprocess.run(["uv", "pip", "install", "--python", str(py), *TOOL_PACKAGES],
                   check=True)
    return py


def probe_video(path: Path) -> tuple[int, int, float]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height,r_frame_rate",
                          "-of", "default=nw=1", str(path)],
                         capture_output=True, text=True, check=True).stdout
    f = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
    num, _, den = f["r_frame_rate"].partition("/")
    return int(f["width"]), int(f["height"]), float(num) / float(den or 1)


def count_frames(path: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-count_frames", "-show_entries", "stream=nb_read_frames",
                          "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return int(out.strip())


def main() -> None:
    ap = argparse.ArgumentParser(description="Whiten one face's teeth over a window")
    ap.add_argument("segment", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--window", nargs=2, type=float, required=True,
                    metavar=("START", "END"),
                    help="seconds within the segment, not the output timeline")
    ap.add_argument("--face", choices=["left", "right"], default="right",
                    help="which face to treat, by horizontal position (default right). "
                         "Everyone else in frame is left alone.")
    ap.add_argument("--desat", type=float, default=0.90,
                    help="how far to pull the yellow out, 0-1 (default 0.90). Past ~1.0 with a high lift the teeth go uniformly white and read as fake.")
    ap.add_argument("--lift", type=float, default=18.0,
                    help="luma lift in 8-bit levels (default 18)")
    ap.add_argument("--crf", default="12",
                    help="re-encode quality; keep BELOW the segment's own CRF so "
                         "the added generation stays transparent (default 12)")
    args = ap.parse_args()

    seg = args.segment.resolve()
    if not seg.exists():
        sys.exit(f"segment not found: {seg}")
    t0, t1 = args.window
    if t1 <= t0:
        sys.exit(f"empty window: {t0} to {t1}")

    w, h, fps = probe_video(seg)
    py = ensure_tool_env()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    worker = Path(TOOL_ENV) / "worker.py"
    worker.write_text(WORKER)
    proc = subprocess.run(
        [str(py), str(worker), str(seg), str(args.output), str(t0), str(t1),
         args.crf, args.face, str(args.desat), str(args.lift),
         str(w), str(h), str(fps), json.dumps(INNER_LIP)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"retouch failed:\n{proc.stderr[-2000:]}")
    stats = json.loads(proc.stdout.strip().splitlines()[-1])

    # A retouch that changes the frame count moves every cut after it, and the
    # render would still succeed. Check, do not assume.
    before, after = count_frames(seg), count_frames(args.output)
    if before != after:
        args.output.unlink(missing_ok=True)
        sys.exit(f"frame count changed {before} -> {after}; refusing to keep the output")

    print(f"{seg.name}: {stats['applied']} frames retouched "
          f"({stats['held']} held through dropouts, {stats['no_detection']} with no face)")
    print(f"  median mask {stats['mask_px_median']:.0f} px, frame count unchanged ({after})")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
