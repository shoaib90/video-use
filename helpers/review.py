"""Pre-delivery review: catch the mistakes Shoaib has already had to catch by eye.

Every check here maps to an entry in kb/mistakes.md (the ledger). Run it on every render
BEFORE a preview reaches Shoaib, clear the HIGH flags, walk the ledger's READ items, then
deliver with the watch-list and (when there is a previous version) the changes reel.

    review.py <edit_dir> --render <final.mp4> --label v7
              [--prev <edit_dir>/review/v6]   # diff against a previous review -> changes reel
              [--raw <no-music render.mp4> --music-ok "0-125.6,145.9-155.3"]
              [--no-reel] [--fps 30]

Writes <edit_dir>/review/<label>/:
    report.md     every check, PASS/FLAG, flags ranked HIGH > MED > LOW
    edges.md      each flagged story edge with the source speech around it, for reading
    watchlist.md  the timestamps Shoaib should look at (changed edges + anything flagged)
    reel.mp4      ~14 s around every CHANGED edge, labelled (only with --prev)
    ranges.json   this version's story ranges, for the next --prev
    sheet_*.jpg   overlay / card contact sheets

Story ranges are reconstructed from the EDL: consecutive ranges on the same source that abut
in source time are one story range split into camera shots. Their edges are the real cuts.

Checks:
  T1 segments uniform + fresh   T2 caption/segment timing drift   T3 freezes (d=1.0)
  T4 clicks at cuts             T5 loudness -14 +-0.5 LUFS, TP <= -1 dBTP
  T6 black / silent opening     T7 music outside allowed windows (needs --raw)
  C1 IN after a non-final word  C2 answer without its question   C3 opener with a cut referent
  C4 long setup cut             C5 OUT mid-sentence             C6 dangling edge word
  C7 ghost duplicate words      C8 transcript gap inside cut    C9 lowest-confidence words
  C10 Spanish drift             G1 overlay/card contact sheets  G2 caps-unsafe card text
  C11 false start / restart     G3 goodbye on a single
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

import numpy as np

FINAL = re.compile(r"[.?!।]$")
OPENERS = {"तो", "और", "but", "so", "and", "मतलब", "फिर", "because", "क्योंकि", "उससे", "इसलिए",
           "then", "also", "वो", "वह", "यह", "वही", "अब"}
DANGLING = {"हर", "कि", "the", "a", "an", "and", "to", "of", "में", "से", "का", "की", "के", "जो",
            "या", "or", "but", "और", "तो", "with", "for", "is"}
FILLERS = {"मतलब", "तो", "so", "and", "but", "yeah", "like", "ok", "okay", "अच्छा", "हां", "हाँ", "यार",
           "भाई", "because", "क्योंकि", "only", "point", "on", "that", "फिर", "और", "but", "uh", "um"}
SPANISH = re.compile(r"[¿¡áéíóúñ]")
TURN_GAP = 1.5          # s; a longer pause ends a turn
JOIN_WINDOW = 60.0      # s; a neighbouring story range on the same source this close is a deliberate join
# tag questions ("…, correct?", "…, है ना?", "ठीक है?") are fillers, not questions to be answered
TAGS = {"correct", "right", "ok", "okay", "na", "ना", "no", "हां", "हाँ", "yes", "न", "huh", "बोलिए"}


def is_real_question(ws, n):
    w = norm(ws[n]["text"])
    if w in TAGS:
        return False
    if w == "है" and n > 0 and norm(ws[n - 1]["text"]) in {"ठीक", "ना"}:
        return False
    return True
SEV = {"HIGH": 0, "MED": 1, "LOW": 2}


# ---------------------------------------------------------------------------- helpers
def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s).replace("़", "")
    return re.sub(r"[.,?!।\"']", "", s).lower()


def frames(d: float, fps: float) -> float:
    return max(1, round(d * fps)) / fps


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe_dur(p: Path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).stdout)


def fmt(t: float) -> str:
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:04.1f}" if t >= 3600 else f"{int(t // 60)}:{t % 60:04.1f}"


def load_words(edit: Path, src: str):
    p = edit / "transcripts" / f"{src}.json"
    if not p.exists():
        return None
    ws = [w for w in json.loads(p.read_text())["words"] if w.get("type", "word") == "word" and w.get("start") is not None]
    return sorted(ws, key=lambda w: w["start"])


# ------------------------------------------------------------------- story ranges
def story_ranges(edl: dict, fps: float):
    """[(src, a, b, out_start, out_end, first_range_idx)] — shots that abut in source time merge."""
    R = edl["ranges"]
    durs = [frames(r["end"] - r["start"], fps) for r in R]
    starts = np.concatenate([[0.0], np.cumsum(durs)[:-1]])
    out = []
    for i, r in enumerate(R):
        if out and out[-1][0] == r["source"] and abs(out[-1][2] - r["start"]) < 0.02:
            s = out[-1]
            out[-1] = (s[0], s[1], r["end"], s[3], starts[i] + durs[i], s[5])
        else:
            out.append((r["source"], r["start"], r["end"], starts[i], starts[i] + durs[i], i))
    return out, durs, starts


def covered(stories, src, t0, t1) -> bool:
    return any(s[0] == src and s[1] - 0.05 <= t0 and t1 <= s[2] + 0.05 for s in stories)


# ------------------------------------------------------------------- content checks
def edge_checks(edit: Path, stories, words_of, exempt=lambda k: False):
    """Return flags [(sev, id, story_idx, edge 'IN'|'OUT', message)] and context per story."""
    flags, ctx = [], {}
    for k, (src, a, b, o0, o1, _) in enumerate(stories):
        ws = words_of(src)
        if not ws:
            continue
        inside = [n for n, w in enumerate(ws) if w["start"] >= a - 0.05 and w["end"] <= b + 0.05]
        if not inside:
            continue
        i, j = inside[0], inside[-1]
        first, last = ws[i], ws[j]
        # the uncut turn before the IN
        before, n = [], i - 1
        while n >= 0 and len(before) < 80:
            gap = ws[n + 1]["start"] - ws[n]["end"]
            if gap >= TURN_GAP or covered(stories, src, ws[n]["start"], ws[n]["end"]):
                break
            before.insert(0, ws[n]); n -= 1
        after, n = [], j + 1
        while n < len(ws) and len(after) < 30:
            gap = ws[n]["start"] - ws[n - 1]["end"]
            if gap >= TURN_GAP or covered(stories, src, ws[n]["start"], ws[n]["end"]):
                break
            after.append(ws[n]); n += 1
        ctx[k] = (before, ws[i:i + 18], ws[max(i, j - 14):j + 1], after)
        prev_in_cut = i > 0 and covered(stories, src, ws[i - 1]["start"], ws[i - 1]["end"])
        if exempt(k):        # a teaser/cold-open line: starting mid-story is the point
            before = []
        gap_in = first["start"] - ws[i - 1]["end"] if i > 0 else 99
        # C1 IN after a non-final word in the same breath
        prev_story = stories[k - 1] if k > 0 else None
        next_story = stories[k + 1] if k + 1 < len(stories) else None
        joined_from = prev_story and prev_story[0] == src and 0 <= a - prev_story[2] < JOIN_WINDOW
        joined_to = next_story and next_story[0] == src and 0 <= next_story[1] - b < JOIN_WINDOW
        if i > 0 and not prev_in_cut and not exempt(k) and gap_in < 1.0 and not FINAL.search(ws[i - 1]["text"]):
            lead, n = [], i - 1
            while n >= 0 and not FINAL.search(ws[n]["text"]) and not covered(stories, src, ws[n]["start"], ws[n]["end"]):
                lead.insert(0, ws[n]); n -= 1
            if len(lead) <= 4 and all(norm(w["text"]) in FILLERS for w in lead):
                flags.append(("LOW", "C1", k, "IN", f"lead-in filler trimmed (“{' '.join(w['text'] for w in lead)}”)"))
            elif joined_from:
                flags.append(("MED", "C1", k, "IN", f"joins #{k - 1} mid-sentence (after “{ws[i - 1]['text']}”, "
                                                    f"{a - prev_story[2]:.1f} s cut): read the join"))
            else:
                flags.append(("HIGH", "C1", k, "IN", f"starts mid-sentence after “{ws[i - 1]['text']}”"))
        # C2 answer without its question: a '?' in the uncut speech just before
        base = i - len(before)
        qidx = [m for m in range(len(before)) if before[m]["text"].endswith("?") and is_real_question(ws, base + m)]
        first_sentence_is_q = any(w["text"].endswith("?") for w in ws[i:i + 25])
        if qidx and not first_sentence_is_q:
            m = qidx[-1]
            words_after = len(before) - 1 - m
            qs = " ".join(w["text"] for w in before[max(0, m - 12):m + 1])
            if words_after <= 3:
                flags.append(("HIGH", "C2", k, "IN", f"answers a question that is cut: “…{qs}”"))
            elif words_after <= 25:
                flags.append(("MED", "C2", k, "IN", f"a question {words_after} words before the IN is cut: “…{qs}”"))
        # C3 opener whose referent was cut
        if before and len(before) >= 6 and norm(first["text"]) in OPENERS:
            flags.append(("MED", "C3", k, "IN", f"opens on “{first['text']}” after {len(before)} cut words of the same turn"))
        # C4 long setup cut
        elif len(before) >= 20:
            flags.append(("LOW", "C4", k, "IN", f"{len(before)} words of the same turn cut just before (setup?)"))
        # C5 OUT mid-sentence
        nxt = ws[j + 1] if j + 1 < len(ws) else None
        if nxt and not FINAL.search(last["text"]) and nxt["start"] - last["end"] < 0.8 \
                and not covered(stories, src, nxt["start"], nxt["end"]):
            if joined_to and next_story[1] - b < 3.0:
                flags.append(("LOW", "C5", k, "OUT", f"tightened inside a sentence (drops “{nxt['text']}…”, resumes at #{k + 1})"))
            elif joined_to:
                flags.append(("MED", "C5", k, "OUT", f"sentence continues at #{k + 1} after {next_story[1] - b:.1f} s cut: read the join"))
            else:
                flags.append(("HIGH", "C5", k, "OUT", f"ends mid-sentence on “{last['text']}”, next: “{nxt['text']}…”"))
        # C6 dangling edge word
        if norm(last["text"]) in DANGLING and not FINAL.search(last["text"]):
            flags.append(("HIGH", "C6", k, "OUT", f"ends on a dangling “{last['text']}”"))
        if norm(first["text"]) in {"कि", "the", "of", "to"}:
            flags.append(("HIGH", "C6", k, "IN", f"starts on a dangling “{first['text']}”"))
        # C7 ghost duplicates near either edge
        for edge, t in (("IN", a), ("OUT", b)):
            near = [n for n, w in enumerate(ws) if w["start"] - 0.3 <= t <= w["end"] + 0.3]
            for n in near:
                w = ws[n]
                if w["end"] - w["start"] < 0.1 and any(norm(ws[m]["text"]) == norm(w["text"])
                                                      for m in range(n + 1, min(len(ws), n + 5))):
                    flags.append(("HIGH", "C7", k, edge, f"ghost duplicate “{w['text']}” ({(w['end'] - w['start']) * 1000:.0f} ms) at {w['start']:.2f}: check RMS"))
                    break
        # C11 false start / restart (M029): the SAME speaker says a 4-word run, stops (a pause of
        # 1.5 s or more), and says it again within 15 s: the first try was abandoned ("यार तो as
        # he said बक्चोदी करो and हम भी. [pause] So yeah, as he said बक्चोदी करो और…"). Echoes by the
        # other person and emphatic repeats with no pause ("Tier three, Tier four. Tier three,
        # Tier four.") are natural speech and are not flagged.
        toks = [norm(w["text"]) for w in ws[i:j + 1]]
        p_ = 0
        while p_ < len(toks) - 3:
            gram, hit = tuple(toks[p_:p_ + 4]), None
            if all(len(g) >= 2 for g in gram):
                for q_ in range(p_ + 4, len(toks) - 3):
                    a0, b0 = ws[i + p_], ws[i + q_]
                    if b0["start"] - a0["start"] > 15:
                        break
                    if tuple(toks[q_:q_ + 4]) != gram or a0.get("speaker_id") != b0.get("speaker_id"):
                        continue
                    pause = max(ws[i + m + 1]["start"] - ws[i + m]["end"] for m in range(p_ + 3, q_))
                    if pause >= 1.5:
                        hit = q_
                        break
            if hit is not None:
                flags.append(("MED", "C11", k, "IN", f"false start? “{' '.join(w['text'] for w in ws[i + p_:i + p_ + 4])}” "
                                                     f"restarted after a pause, src {ws[i + p_]['start']:.1f} → {ws[i + hit]['start']:.1f}"))
                p_ = hit
            p_ += 1
        # C8 transcript gap inside the cut
        for n in range(i, j):
            g = ws[n + 1]["start"] - ws[n]["end"]
            if g >= 5:
                flags.append(("MED", "C8", k, "IN", f"{g:.1f} s with no transcript inside the cut at src {ws[n]['end']:.1f} (dropped speech? no captions)"))
    return flags, ctx


def word_checks(stories, words_of, starts_of_story):
    """C9 lowest-confidence words, C10 Spanish drift — over the words that are in the cut."""
    lowc, span = [], []
    for k, (src, a, b, o0, o1, _) in enumerate(stories):
        ws = words_of(src) or []
        for w in ws:
            if w["start"] >= a - 0.05 and w["end"] <= b + 0.05:
                t = o0 + (w["start"] - a)
                if w.get("confidence") is not None and not w.get("_gapfill"):
                    lowc.append((w["confidence"], t, w["text"], src))
                if SPANISH.search(w["text"]):
                    span.append((t, w["text"], src))
    lowc.sort()
    return lowc[:25], span


# ------------------------------------------------------------------- render checks
def render_checks(edit: Path, edl: dict, render: Path, durs, fps):
    res = []
    R = edl["ranges"]
    clips = None
    for d in ("clips_graded", "clips_preview", "clips_draft"):
        cand = [edit / d / f"seg_{i:02d}_{r['source']}.mp4" for i, r in enumerate(R)]
        if all(c.exists() for c in cand):
            if clips is None or cand[0].stat().st_mtime > clips[0].stat().st_mtime:
                clips = cand
    if clips:
        dims = {}
        for c in clips:
            s = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height,r_frame_rate", "-of", "json", str(c)]).stdout)["streams"][0]
            key = f"{s['width']}x{s['height']}@{s['r_frame_rate']}"
            dims[key] = dims.get(key, 0) + 1
        res.append(("T1", len(dims) == 1, f"{len(clips)} segments in {clips[0].parent.name}: {dims}"))
        real = np.array([probe_dur(c) for c in clips])
        drift = np.abs(real - np.array(durs))
        res.append(("T2", drift.max() < 0.002 and abs((real - durs).sum()) < 0.05,
                    f"max per-segment {drift.max() * 1000:.1f} ms, cumulative {(real - durs).sum() * 1000:+.1f} ms"))
        seg_bounds = np.cumsum(real)[:-1]
    else:
        res.append(("T1", False, "no complete segment folder matches this EDL"))
        seg_bounds = np.cumsum(durs)[:-1]
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-v", "info", "-i", str(render), "-vf",
               "scale=320:-2,freezedetect=n=-60dB:d=1.0", "-an", "-f", "null", "-"]).stderr
    fr = [float(l.split("freeze_start: ")[1]) for l in err.splitlines() if "freeze_start" in l]
    res.append(("T3", not fr, f"{len(fr)} freezes ≥1 s {[fmt(x) for x in fr[:10]]}"))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(render), "-vn", "-af", "pan=mono|c0=c0",
                          "-ar", "48000", "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, "<f4")
    clicks = []
    for t in seg_bounds:
        i = int(t * 48000)
        win, ref = a[max(0, i - 480):i + 480], a[max(0, i - 48000):max(0, i - 4800)]
        if len(win) > 10 and len(ref) > 10:
            step = np.abs(np.diff(win)).max()
            base = np.percentile(np.abs(np.diff(ref)), 99.9) + 1e-6
            if step > 2.5 * base and step > 0.02:
                clicks.append(fmt(t))
    res.append(("T4", not clicks, f"{len(clicks)} cut(s) with a step spike {clicks[:12]}"))
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(render), "-af", "ebur128=peak=true:framelog=quiet",
               "-f", "null", "-"]).stderr
    I = [float(l.split("I:")[1].split("LUFS")[0]) for l in err.splitlines() if "I:" in l and "LUFS" in l]
    P = [float(l.split("Peak:")[1].split("dBFS")[0]) for l in err.splitlines() if "Peak:" in l and "dBFS" in l]
    if I and P:
        res.append(("T5", abs(I[-1] + 14) <= 0.5 and P[-1] <= -1.0, f"{I[-1]:.1f} LUFS, true peak {P[-1]:.1f} dBTP"))
    head = a[:2 * 48000]
    rms = 20 * math.log10(float(np.sqrt((head ** 2).mean())) + 1e-9) if len(head) else -99
    err = run(["ffmpeg", "-hide_banner", "-v", "info", "-t", "2", "-i", str(render), "-vf",
               "blackdetect=d=0.3:pix_th=0.10", "-an", "-f", "null", "-"]).stderr
    black = [l for l in err.splitlines() if "black_start" in l]
    res.append(("T6", not black and rms > -45, f"first 2 s: {'black ' if black else ''}audio {rms:.1f} dBFS"))
    return res


def music_check(render: Path, raw: Path, ok_windows):
    """T7: music in speech pauses outside the allowed windows (mix vs the no-music render)."""
    SR = 16000
    def load(p):
        return np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", str(SR),
                                             "-f", "f32le", "-"], capture_output=True).stdout, "<f4").astype(np.float64)
    m, r = load(render), load(raw)
    seg = slice(600 * SR, 630 * SR) if len(r) > 640 * SR else slice(0, min(len(r), len(m)))
    n = seg.stop - seg.start
    c = np.fft.irfft(np.fft.rfft(m[seg], 2 * n) * np.conj(np.fft.rfft(r[seg], 2 * n)))
    lag = int(np.argmax(c)); lag = lag if lag < n else lag - 2 * n
    m = m[lag:] if lag >= 0 else m
    r = r if lag >= 0 else r[-lag:]
    n = min(len(m), len(r)); m, r = m[:n], r[:n]
    g = float(np.dot(m, r) / (np.dot(r, r) + 1e-9))
    h = SR // 10; bad = []
    for i in range(0, n - h, h):
        t = i / SR
        if any(a <= t <= b for a, b in ok_windows):
            continue
        rr = 20 * math.log10(np.sqrt((r[i:i + h] ** 2).mean()) + 1e-9)
        mm = 20 * math.log10(np.sqrt((m[i:i + h] ** 2).mean()) / max(g, 1e-6) + 1e-9)
        if rr < -45 and mm - rr > 6:
            bad.append(t)
    return ("T7", len(bad) < 3, f"{len(bad)} pauses outside the allowed windows carry music {[fmt(x) for x in bad[:8]]}")


def graphics_checks(edl: dict):
    out = []
    # G3 (M027): a multi-person conversation's goodbye must show everyone. Only EDLs that carry
    # framing labels (`frame`) can be checked; singles are named after a person, the shared
    # framings are TWO / WIDE.
    R = edl.get("ranges", [])
    framed = [r for r in R if r.get("frame") and r.get("frame") not in ("END", "SLATE")
              and not r["frame"].startswith(("TOCAM", "BROLL"))]
    if framed and any(r["frame"].startswith(("TWO", "WIDE")) for r in framed):
        last = framed[-1]
        if not last["frame"].startswith(("TWO", "WIDE")):
            out.append(("HIGH", "G3", f"the last talking shot ({last['source']} {last['start']:.1f}-{last['end']:.1f}) "
                                      f"is a single ({last['frame']}): the goodbye should show everyone"))
    for c in (edl.get("cards") or []):
        for txt in [c.get("text", "")] + [s.get("value", "") for s in c.get("steps", [])] + [r.get("text", "") for r in c.get("rows", [])]:
            if c.get("kind") == "stamp" and re.search(r"[A-Z]{2,}s\b|\d+[a-z]+s\b", txt):
                out.append(("HIGH", "G2", f"card '{c.get('id')}' text “{txt}” renders in caps as “{txt.upper()}”"))
    return out


def contact_sheet(render: Path, items, out: Path, title: str):
    """One frame per (time, label), tiled 4 wide."""
    if not items:
        return None
    tmp = out.parent / f"_{out.stem}"
    tmp.mkdir(exist_ok=True)
    for n, (t, lab) in enumerate(items):
        lab = re.sub(r"[^A-Za-z0-9 :._-]", "", lab)[:48]
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(render), "-frames:v", "1", "-vf",
             f"scale=480:-2,drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:text='{fmt(t).replace(':', chr(92) + ':')} {lab}'"
             ":x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.7", str(tmp / f"{n:03d}.jpg")])
    run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(tmp / "%03d.jpg"), "-vf",
         "tile=4x6:padding=2", str(out.with_name(out.stem + "_%02d.jpg"))])
    shutil.rmtree(tmp)
    return sorted(out.parent.glob(out.stem + "_*.jpg"))


# ------------------------------------------------------------------- changes reel
def changed_edges(stories, prev):
    """Edges of this version's story ranges that do not exist in the previous version."""
    out = []
    for k, (src, a, b, o0, o1, _) in enumerate(stories):
        same_in = any(p[0] == src and abs(p[1] - a) < 0.3 for p in prev)
        same_out = any(p[0] == src and abs(p[2] - b) < 0.3 for p in prev)
        if not same_in:
            out.append((o0, k, "IN"))
        if not same_out:
            out.append((o1, k, "OUT"))
    return out


def make_reel(render: Path, marks, out: Path, pre=7.0, post=7.0):
    tmp = out.parent / "_reel"
    tmp.mkdir(exist_ok=True)
    lst = []
    for n, (t, label) in enumerate(marks):
        s = max(0.0, t - pre)
        lab = re.sub(r"[^A-Za-z0-9 :._-]", "", label)[:70].replace(":", "\\:")
        seg = tmp / f"{n:03d}.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.2f}", "-t", f"{pre + post:.2f}", "-i", str(render),
             "-vf", f"scale=1280:-2,drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:text='{n + 1}/{len(marks)}  {lab}'"
                    ":x=16:y=16:fontsize=26:fontcolor=white:box=1:boxcolor=black@0.65,fps=30",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
             "-ac", "2", str(seg)])
        lst.append(f"file '{seg}'")
    (tmp / "list.txt").write_text("\n".join(lst))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-c", "copy", str(out)])
    shutil.rmtree(tmp)


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit_dir")
    ap.add_argument("--render", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--prev")
    ap.add_argument("--raw")
    ap.add_argument("--music-ok", default="")
    ap.add_argument("--no-reel", action="store_true")
    ap.add_argument("--skip-render", action="store_true", help="content checks only (fast iteration)")
    ap.add_argument("--accepted", help="JSON list of {src, t, check, why}: flags the agent checked and "
                                       "accepted (default <edit>/review/accepted.json)")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--exempt-beats", default="",
                    help="regex on ranges[].beat: story ranges whose IN is deliberately mid-story "
                         "(teasers, cold opens) skip C1-C4; C5-C7 still apply")
    a = ap.parse_args()
    edit, render = Path(a.edit_dir).resolve(), Path(a.render).resolve()
    out = edit / "review" / a.label
    out.mkdir(parents=True, exist_ok=True)
    edl = json.loads((edit / "edl.json").read_text())
    shutil.copy(edit / "edl.json", out / "edl.json")
    stories, durs, starts = story_ranges(edl, a.fps)
    (out / "ranges.json").write_text(json.dumps([[s[0], round(s[1], 3), round(s[2], 3)] for s in stories]))
    cache = {}
    words_of = lambda src: cache.setdefault(src, load_words(edit, src))

    print("content checks…")
    ex = re.compile(a.exempt_beats) if a.exempt_beats else None
    exempt = lambda k: bool(ex and ex.search(edl["ranges"][stories[k][5]].get("beat", "")))
    flags, ctx = edge_checks(edit, stories, words_of, exempt)
    lowc, span = word_checks(stories, words_of, None)
    gflags = graphics_checks(edl)
    acc_path = Path(a.accepted) if a.accepted else edit / "review" / "accepted.json"
    accepted = json.loads(acc_path.read_text()) if acc_path.exists() else []
    def acc_of(f):
        src, sa, sb = stories[f[2]][:3]
        t = sa if f[3] == "IN" else sb
        return next((x for x in accepted if x["src"] == src and x["check"] == f[1] and abs(x["t"] - t) < 0.5), None)
    acc_flags = [(f, acc_of(f)) for f in flags if acc_of(f)]
    flags = [f for f in flags if not acc_of(f)]
    print("render checks…")
    rchecks = [] if a.skip_render else render_checks(edit, edl, render, durs, a.fps)
    if a.raw and not a.skip_render:
        ok = [tuple(float(x) for x in w.split("-")) for w in a.music_ok.split(",") if w]
        rchecks.append(music_check(render, Path(a.raw).resolve(), ok))

    # contact sheets: every overlay and card at its midpoint
    items = [(o["start_in_output"] + o["duration"] / 2, Path(o["file"]).stem) for o in edl.get("overlays") or []]
    sheets = [] if a.skip_render else (contact_sheet(render, items, out / "sheet_overlays.jpg", "overlays") or [])

    # changes since the previous version
    changes = []
    if a.prev:
        prev = json.loads((Path(a.prev) / "ranges.json").read_text())
        changes = changed_edges(stories, prev)

    # ---- write edges.md
    def txt(seq):
        return " ".join(w["text"] for w in seq)
    flagged_k = sorted({f[2] for f in flags} | {c[1] for c in changes})
    lines = [f"# Story edges to read — {a.label}\n",
             "Each block: the uncut speech BEFORE the IN, the first words, the last words, the uncut speech AFTER.\n"]
    for k in flagged_k:
        src, sa, sb, o0, o1, _ = stories[k]
        fl = [f for f in flags if f[2] == k]
        ch = [c for c in changes if c[1] == k]
        tag = " ".join(f"[{f[0]} {f[1]} {f[3]}]" for f in fl) + (" [CHANGED " + "/".join(c[2] for c in ch) + "]" if ch else "")
        lines.append(f"\n## #{k} {fmt(o0)}–{fmt(o1)}  {src} {sa:.1f}-{sb:.1f}  {tag}")
        for f in fl:
            lines.append(f"- **{f[0]} {f[1]}** ({f[3]}): {f[4]}")
        if k in ctx:
            b4, fi, la, af = ctx[k]
            lines.append(f"- BEFORE: …{txt(b4)}" if b4 else "- BEFORE: (pause / in the cut)")
            lines.append(f"- IN: {txt(fi)}")
            lines.append(f"- OUT: …{txt(la)}")
            lines.append(f"- AFTER: {txt(af)}…" if af else "- AFTER: (pause / in the cut)")
    (out / "edges.md").write_text("\n".join(lines) + "\n")

    # ---- report.md
    rep = [f"# Review {a.label} — {render.name}\n", f"{len(stories)} story ranges, {len(edl['ranges'])} shots, "
           f"{sum(durs) / 60:.1f} min. Ledger: kb/mistakes.md\n", "## Render checks\n"]
    for cid, ok, msg in rchecks:
        rep.append(f"- {'PASS' if ok else '**FLAG**'} {cid}: {msg}")
    allf = sorted(flags, key=lambda f: (SEV[f[0]], f[2]))
    counts = {s: sum(1 for f in allf if f[0] == s) for s in SEV}
    rep.append(f"\n## Story edges — HIGH {counts['HIGH']}, MED {counts['MED']}, LOW {counts['LOW']} (details: edges.md)\n")
    for f in allf:
        src, sa, sb, o0, o1, _ = stories[f[2]]
        rep.append(f"- {f[0]} {f[1]} #{f[2]} {fmt(o0 if f[3] == 'IN' else o1)} {f[3]}: {f[4]}")
    if acc_flags:
        rep.append(f"\n## Accepted after checking ({len(acc_flags)}, {acc_path.name})\n")
        rep += [f"- {f[0]} {f[1]} #{f[2]} {f[3]}: {f[4]} — **{x['why']}**" for f, x in acc_flags]
    rep.append("\n## Graphics\n")
    rep += [f"- {g[0]} {g[1]}: {g[2]}" for g in gflags] or ["- PASS G2/G3: card text caps-safe; the goodbye shows everyone"]
    rep += [f"- G1 contact sheet: {s.name}" for s in sheets]
    rep.append("\n## Words to read (C9 lowest confidence in the cut; C10 Spanish drift)\n")
    rep += [f"- {fmt(t)}  “{w}”  conf {c:.2f}  ({s})" for c, t, w, s in lowc]
    rep += [f"- **C10** {fmt(t)} “{w}” ({s})" for t, w, s in span] or ["- PASS C10: no Spanish characters"]
    if a.prev:
        rep.append(f"\n## Changed since {Path(a.prev).name}: {len(changes)} edges (reel.mp4)")
    (out / "report.md").write_text("\n".join(rep) + "\n")

    # ---- watchlist.md + reel
    marks = []
    for t, k, edge in sorted(changes):
        reason = next((f"{f[1]} " for f in flags if f[2] == k and f[3] == edge), "")
        marks.append((t, f"{fmt(t)} {edge} {reason}changed"))
    high_unc = [(stories[f[2]][3] if f[3] == "IN" else stories[f[2]][4], f) for f in flags if f[0] == "HIGH"]
    wl = [f"# Watch-list {a.label}\n", "Only these moments need eyes. Everything else passed the automated review.\n"]
    if marks:
        wl.append(f"## Changed since {Path(a.prev).name} ({len(marks)}) — all in reel.mp4\n")
        wl += [f"- {m[1]}" for m in marks]
    if high_unc:
        wl.append("\n## Still flagged HIGH (agent: fix or justify before delivery)\n")
        wl += [f"- {fmt(t)} {f[1]} {f[3]}: {f[4]}" for t, f in sorted(high_unc)]
    (out / "watchlist.md").write_text("\n".join(wl) + "\n")
    if marks and not a.no_reel:
        print(f"reel: {len(marks)} clips…")
        make_reel(render, marks, out / "reel.mp4")
    print(f"\nHIGH {counts['HIGH']}  MED {counts['MED']}  LOW {counts['LOW']}  | render checks "
          f"{sum(1 for c in rchecks if c[1])}/{len(rchecks)} pass | changed edges {len(changes)}")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
