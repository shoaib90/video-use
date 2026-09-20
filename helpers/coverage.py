"""Find the stretches of a cut where nothing happens, and say what to put there.

Not an opinion about pacing — a checklist. It detects every span over `--min-gap`
seconds with no shot change, no graphic, no overlay and no demotion, then prints
what is being SAID across that span and which unused b-roll you already own.

Measured on a delivered 3m34s episode: 2.5 visual changes/min against 8.6 in a
professional reference, and a single **124.9 s** stretch — 58% of the film —
with nothing changing at all. That stretch was a gap rather than a choice: nine
b-roll assets sat unused, including three MRI scans under a script that says
"a body that broke".

The honest limit: this measures *change*, not *interest*. A long hold can be
deliberate, and a reflective essay earns holds a tutorial does not. Pass
`--retention` with a YouTube Studio export to replace the guess with your own
audience — the report then shows how much retention each gap actually cost.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from pathlib import Path

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".jpg", ".jpeg", ".png", ".heic", ".webp"}
STOP = {"the", "and", "that", "this", "with", "have", "from", "was", "were", "for",
        "you", "your", "about", "just", "what", "when", "they", "them", "their",
        "would", "could", "there", "been", "much", "very", "then", "than", "into",
        "some", "more", "will", "want", "know", "like", "because", "which"}


def scene_changes(video: Path, threshold: float = 0.30) -> list[float]:
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(video),
         "-vf", f"select='gt(scene,{threshold})',metadata=print:file=-",
         "-an", "-f", "null", "-"], capture_output=True, text=True)
    return [float(m) for m in re.findall(r"pts_time:([0-9.]+)", r.stdout)]


def duration(p: Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(p)],
        capture_output=True, text=True).stdout or 0)


def treatment_times(edl: dict) -> list[float]:
    """Moments an overlay, graphic or demotion puts something new on screen.

    Scene detection cannot see these: a title fading in over a locked-off shot
    does not move enough pixels to register, so counting shot changes alone
    understates a graphics-heavy cut.
    """
    t = []
    for o in edl.get("overlays") or []:
        t.append(float(o.get("start_in_output", 0)))
    for g in edl.get("graphics") or []:
        if "start" in g:
            t.append(float(g["start"]))
    for d in edl.get("demotions") or []:
        t += [float(d["start"]), float(d["end"])]
    return t


def srt_cues(path: Path) -> list[tuple[float, float, str]]:
    if not path.exists():
        return []
    out = []
    for block in path.read_text().strip().split("\n\n"):
        lines = block.split("\n")
        if len(lines) < 3:
            continue
        m = re.match(r"([\d:,]+)\s*-->\s*([\d:,]+)", lines[1])
        if not m:
            continue

        def sec(s):
            h, mnt, rest = s.split(":")
            return int(h) * 3600 + int(mnt) * 60 + float(rest.replace(",", "."))
        out.append((sec(m.group(1)), sec(m.group(2)), " ".join(lines[2:])))
    return out


def said_between(cues, a: float, b: float) -> str:
    return " ".join(t for s, e, t in cues if e > a and s < b)


def load_retention(path: Path, total: float) -> list[tuple[float, float]]:
    """YouTube Studio 'Audience retention' export -> [(seconds, pct_remaining)].

    Column names vary by locale and export version, so this matches loosely
    rather than assuming a schema: the first numeric column is position (a
    fraction, a percentage, or seconds) and the next is retention.
    """
    rows = list(csv.reader(path.read_text().splitlines()))
    out = []
    for r in rows:
        nums = []
        for cell in r:
            try:
                nums.append(float(str(cell).strip().rstrip("%")))
            except ValueError:
                pass
        if len(nums) >= 2:
            out.append((nums[0], nums[1]))
    if not out:
        return []
    xmax = max(x for x, _ in out)
    if xmax <= 1.01:                       # fraction of the video
        out = [(x * total, y) for x, y in out]
    elif xmax <= 100.5 and total > 101:    # percentage
        out = [(x / 100 * total, y) for x, y in out]
    return sorted(out)


def retention_at(curve, t: float) -> float | None:
    if not curve:
        return None
    best = min(curve, key=lambda p: abs(p[0] - t))
    return best[1]


def unused_broll(videos_dir: Path, edl: dict) -> list[Path]:
    """Assets in b-roll/ that the cut does not reference.

    Deliberately NOT the whole project root: that sweeps up the a-roll
    outtakes, which are takes you rejected rather than coverage you have
    spare, and suggesting them as b-roll is noise.
    """
    used = {Path(v).name for v in (edl.get("sources") or {}).values()}
    used |= {Path(o.get("file", "")).name for o in (edl.get("overlays") or [])}
    root = videos_dir / "b-roll"
    if not root.is_dir():
        return []
    seen, found = set(), []
    for f in sorted(root.rglob("*")):
        if (f.is_file() and f.suffix.lower() in VIDEO_EXT
                and f.name not in used and f.name not in seen
                and not f.name.startswith(".")):
            seen.add(f.name)
            found.append(f)
    return found


def insertion_points(cues, a: float, b: float, every: float = 30.0) -> list:
    """Sentence boundaries inside a long gap, roughly `every` seconds apart.

    A 125-second hole does not want one graphic, it wants three or four, and
    they belong on sentence boundaries rather than at arbitrary offsets.
    """
    ends = [(e, t) for s_, e, t in cues if a < e < b and t.rstrip().endswith((".", "?", "!"))]
    picks, last = [], a
    for e, t in ends:
        if e - last >= every:
            picks.append((e, t))
            last = e
    return picks


def suggest(assets: list[Path], text: str, limit: int = 3) -> list[str]:
    """Crude filename keyword match. It is a prompt, not an answer — the point
    is to put the assets you already own next to the line that is running dry."""
    words = {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP}
    scored = []
    for a in assets:
        stem = re.sub(r"[^a-z]+", " ", a.stem.lower())
        hits = sum(1 for w in words if w[:5] in stem)
        scored.append((hits, a.name))
    scored.sort(key=lambda x: -x[0])
    top = [n for h, n in scored if h > 0][:limit]
    return top or [n for _, n in scored[:limit]]


def report(cut: Path, edl_path: Path | None, videos_dir: Path | None,
           srt: Path | None, retention: Path | None, min_gap: float) -> dict:
    total = duration(cut)
    edl = json.loads(edl_path.read_text()) if edl_path and edl_path.exists() else {}
    events = sorted(set([0.0] + scene_changes(cut) + treatment_times(edl) + [total]))
    cues = srt_cues(srt) if srt else []
    curve = load_retention(retention, total) if retention else []
    assets = unused_broll(videos_dir, edl) if videos_dir else []

    changes = [e for e in events if 0 < e < total]
    gaps = [(a, b) for a, b in zip(events, events[1:]) if b - a > min_gap]

    print(f"\n{cut.name} — {int(total // 60)}m{total % 60:04.1f}s")
    print(f"  {len(changes)} visual events   {len(changes) / (total / 60):.1f}/min")
    if changes:
        holds = [b - a for a, b in zip(events, events[1:])]
        holds.sort()
        print(f"  median hold {holds[len(holds) // 2]:.1f}s   longest {max(holds):.1f}s")
    if curve:
        print(f"  retention curve loaded: {len(curve)} points, "
              f"{curve[0][1]:.0f}% → {curve[-1][1]:.0f}%")
    if assets:
        print(f"  {len(assets)} unused b-roll asset(s)")

    print(f"\n  stretches over {min_gap:.0f}s with nothing changing:")
    if not gaps:
        print("    none")
    for a, b in gaps:
        head = f"    {int(a // 60)}:{a % 60:05.2f} → {int(b // 60)}:{b % 60:05.2f}   {b - a:6.1f}s"
        if curve:
            r0, r1 = retention_at(curve, a), retention_at(curve, b)
            if r0 is not None and r1 is not None:
                head += f"   retention {r0:.0f}% → {r1:.0f}%  ({r1 - r0:+.0f})"
        print(head)
        text = said_between(cues, a, b)
        if text:
            if len(text) > 180:
                print(f'        opens: "{text[:85].strip()}…"')
                print(f'        ends:  "…{text[-85:].strip()}"')
            else:
                print(f'        says: "{text}"')
        if assets:
            print(f"        have: {', '.join(suggest(assets, text))}")
        pts = insertion_points(cues, a, b)
        if pts:
            print(f"        {len(pts)} candidate insertion point(s) on sentence ends:")
            for e, t in pts:
                print(f'          {int(e // 60)}:{e % 60:05.2f}  after "…{t.strip()[-58:]}"')
    return {"total": total, "events": len(changes), "gaps": gaps}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cut", type=Path)
    ap.add_argument("--edl", type=Path)
    ap.add_argument("--videos-dir", type=Path,
                    help="project root, for finding unused b-roll")
    ap.add_argument("--srt", type=Path, help="master.srt, for what is being said")
    ap.add_argument("--retention", type=Path,
                    help="YouTube Studio audience-retention CSV")
    ap.add_argument("--min-gap", type=float, default=25.0)
    a = ap.parse_args()
    report(a.cut, a.edl, a.videos_dir, a.srt, a.retention, a.min_gap)


if __name__ == "__main__":
    main()
