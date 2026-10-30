"""Sync clips from a second camera to a master recording, and prove it with the camera clocks.

Both cameras hear the same room, so a clip's offset is where its audio lines up against the
master. Coarse: 100 Hz log-RMS envelopes, FFT cross-correlation. Fine: raw 8 kHz audio within
300 ms of the coarse peak. Clips over 2 minutes are measured again on their last minute, which
reports clock drift.

A correlation peak alone is not proof: on podcast Episode 1 every short clip that matched
elsewhere was thousands of seconds out, however good its peak looked. So each offset is turned
into the difference it implies between the two camera clocks. Strong matches agree on one
difference; anything else is searched again near where that difference says it belongs. A clip
the clocks place outside every master is b-roll, not a failed sync.

Usage:
    python helpers/sync_cameras.py --master IMG_1.MOV IMG_2.MOV --clips dslr/ -o sync.json

Output, per clip, with master_time = clip_time + offset:
    {"master", "offset", "conf", "dur", "drift_ms", "clock_s", "status"}
status: synced (peak and clocks agree) | relocked (found by the clocks) | no_clock (peak only,
no capture time to check it) | outside (clocks put it outside every master) | unmatched
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

SR = 8000
ENV_HZ = 100
STRONG_CONF = 8.0        # a coarse peak this far above the correlation's noise can vote on the clock
MIN_VOTES = 3            # fewer strong matches than this cannot establish a clock difference
CLOCK_TOLERANCE_S = 3.0  # the Episode 1 matches agreed to within 1.7 s of each other
RESEARCH_S = 30.0
FINE_S = 0.3             # a coarse peak at 100 Hz can sit this far from the true one on sparse audio
MIN_CLIP_S = 3.0
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mxf"}


def load_audio(path: Path, ss: float | None = None, t: float | None = None) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error", "-nostdin"]
    if ss is not None:
        cmd += ["-ss", f"{max(0.0, ss):.3f}"]
    cmd += ["-i", str(path)]
    if t is not None:
        cmd += ["-t", f"{t:.3f}"]
    cmd += ["-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, "<f4").astype(np.float32)


def envelope(x: np.ndarray) -> np.ndarray:
    hop = SR // ENV_HZ
    n = len(x) // hop
    if n == 0:
        return np.zeros(0)
    e = np.log(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12))
    return (e - e.mean()) / (e.std() + 1e-9)


def xcorr(short: np.ndarray, long: np.ndarray) -> np.ndarray:
    """Correlation of `short` at every position inside `long`."""
    n = 1 << int(np.ceil(np.log2(len(short) + len(long))))
    c = np.fft.irfft(np.fft.rfft(long, n) * np.conj(np.fft.rfft(short, n)), n)
    return c[: len(long) - len(short) + 1]


def coarse_peak(clip_env: np.ndarray, master_env: np.ndarray) -> tuple[float, float]:
    """(seconds into the master, confidence). Confidence is the peak in std-devs above the median."""
    if len(clip_env) == 0 or len(master_env) < len(clip_env):
        return 0.0, 0.0
    c = xcorr(clip_env, master_env)
    k = int(np.argmax(c))
    return k / ENV_HZ, float((c[k] - np.median(c)) / (np.std(c) + 1e-9))


def fine_offset(clip: np.ndarray, master: Path, estimate: float) -> float:
    """Refine on raw audio: 20 s from the clip's middle, within FINE_S of the estimate."""
    mid = max(0.0, len(clip) / SR / 2 - 10)
    a = clip[int(mid * SR): int((mid + 20) * SR)]
    start = max(0.0, estimate + mid - FINE_S)
    b = load_audio(master, ss=start, t=len(a) / SR + 2 * FINE_S)
    if len(b) < len(a) or len(a) == 0:
        return estimate
    return start - mid + int(np.argmax(xcorr(a - a.mean(), b - b.mean()))) / SR


def drift_ms(clip: np.ndarray, master: Path, offset: float) -> float | None:
    dur = len(clip) / SR
    if dur <= 120:
        return None
    tail = clip[int((dur - 60) * SR):]
    b = load_audio(master, ss=offset + dur - 60 - 0.15, t=60.3)
    if len(b) < len(tail):
        return None
    off_tail = offset - 0.15 + int(np.argmax(xcorr(tail - tail.mean(), b - b.mean()))) / SR
    return round((off_tail - offset) * 1000, 1)


def capture_time(path: Path) -> float | None:
    """Epoch seconds at capture. `creationdate` is the real one on iPhone; `creation_time`
    there is the file-write time, wrong by up to 2h24m (see gotchas.md)."""
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags", "-of", "json", str(path)],
                         capture_output=True, text=True).stdout
    try:
        tags = json.loads(out).get("format", {}).get("tags", {})
    except json.JSONDecodeError:
        return None
    raw = tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time")
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    if len(raw) > 5 and raw[-3] != ":" and raw[-5] in "+-":  # +0530 -> +05:30
        raw = f"{raw[:-2]}:{raw[-2:]}"
    try:
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return None


def clock_difference(results: dict[str, dict]) -> float | None:
    """The master-minus-clip clock difference the strong matches agree on, if they do."""
    votes = [r["clock_s"] for r in results.values()
             if r["conf"] >= STRONG_CONF and r["clock_s"] is not None]
    return statistics.median(votes) if len(votes) >= MIN_VOTES else None


def place_by_clock(clip_capture: float, dur: float, clock: float,
                   masters: dict[str, dict]) -> tuple[str, float] | None:
    """Which master holds this clip according to the clocks, and at what offset."""
    wall_start = clip_capture + clock
    for name, m in masters.items():
        if m["capture"] is None:
            continue
        offset = wall_start - m["capture"]
        if -RESEARCH_S < offset < m["dur"] + RESEARCH_S - min(dur, m["dur"]):
            return name, offset
    return None


def search_near(clip_env: np.ndarray, m: dict, estimate: float) -> tuple[float, float]:
    """Coarse peak restricted to RESEARCH_S around where the clocks say the clip sits."""
    a = max(0, int((estimate - RESEARCH_S) * ENV_HZ))
    b = int((estimate + RESEARCH_S) * ENV_HZ) + len(clip_env)
    at, conf = coarse_peak(clip_env, m["env"][a:b])
    return a / ENV_HZ + at, conf


def sync(master_paths: list[Path], clip_paths: list[Path], verbose: bool = True) -> dict[str, dict]:
    masters: dict[str, dict] = {}
    for p in master_paths:
        audio = load_audio(p)
        masters[p.stem] = {"path": p, "env": envelope(audio), "dur": len(audio) / SR, "capture": capture_time(p)}

    results: dict[str, dict] = {}
    clips: dict[str, tuple[np.ndarray, np.ndarray, float | None]] = {}
    for f in clip_paths:
        audio = load_audio(f)
        if len(audio) < SR * MIN_CLIP_S:
            continue
        env = envelope(audio)
        name, at, conf = max(((n, *coarse_peak(env, m["env"])) for n, m in masters.items()), key=lambda r: r[2])
        captured = capture_time(f)
        master = masters[name]
        clock = (None if captured is None or master["capture"] is None
                 else round(master["capture"] + at - captured, 2))
        clips[f.stem] = (audio, env, captured)
        results[f.stem] = {"path": str(f), "master": name, "offset": at, "conf": round(conf, 1),
                           "dur": round(len(audio) / SR, 2), "drift_ms": None, "clock_s": clock,
                           "status": "no_clock"}

    clock = clock_difference(results)
    if verbose:
        print(f"camera clocks: master - clip = {clock:.2f} s" if clock is not None
              else "camera clocks: not enough strong matches to establish a difference")

    for stem, r in results.items():
        audio, env, captured = clips[stem]
        if clock is not None and captured is not None:
            if r["clock_s"] is not None and abs(r["clock_s"] - clock) <= CLOCK_TOLERANCE_S:
                r["status"] = "synced"
            else:
                placed = place_by_clock(captured, r["dur"], clock, masters)
                if placed is None:
                    r["status"] = "outside"
                else:
                    name, estimate = placed
                    at, conf = search_near(env, masters[name], estimate)
                    r.update(master=name, offset=at, conf=round(conf, 1),
                             clock_s=round(masters[name]["capture"] + at - captured, 2))
                    # Not judged by peak height: a weak peak is why it is here. Landing
                    # on the clocks' own answer is the evidence (C0433: conf 3.3, exact).
                    r["status"] = "relocked" if abs(r["clock_s"] - clock) <= CLOCK_TOLERANCE_S else "unmatched"
        if r["status"] in ("synced", "relocked", "no_clock"):
            master_path = masters[r["master"]]["path"]
            r["offset"] = round(fine_offset(audio, master_path, r["offset"]), 4)
            r["drift_ms"] = drift_ms(audio, master_path, r["offset"])
        else:
            r["offset"] = round(r["offset"], 4)
        if verbose:
            print(f"{stem:14s} {r['status']:9s} -> {r['master']} @ {r['offset']:9.3f}s  conf {r['conf']:5.1f}  "
                  f"dur {r['dur']:7.1f}  drift {r['drift_ms']}  clock {r['clock_s']}", flush=True)
    return results


def collect_clips(items: list[Path], masters: list[Path]) -> list[Path]:
    known = {m.resolve() for m in masters}
    out: list[Path] = []
    for item in items:
        files = sorted(item.rglob("*")) if item.is_dir() else [item]
        out += [f for f in files if f.is_file() and f.suffix.lower() in VIDEO_EXTS
                and not f.name.startswith(".") and f.resolve() not in known]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Sync a second camera to a master recording by audio")
    ap.add_argument("--master", type=Path, nargs="+", required=True, help="The recording(s) audio stays on")
    ap.add_argument("--clips", type=Path, nargs="+", required=True, help="Clips to sync, or folders of them")
    ap.add_argument("-o", "--output", type=Path, required=True, help="Output JSON")
    args = ap.parse_args()
    for m in args.master:
        if not m.exists():
            sys.exit(f"master not found: {m}")
    clips = collect_clips(args.clips, args.master)
    if not clips:
        sys.exit("no clips found")
    results = sync([m.resolve() for m in args.master], clips)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=1))
    counts: dict[str, int] = {}
    for r in results.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"\n{len(results)} clips: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
