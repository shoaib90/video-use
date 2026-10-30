#!/usr/bin/env python3
"""mgx — the motion-graphics pass over a picture-locked master. Read ../SKILL.md first.

Every step reads <edit>/mgx/cues.py (the episode's cues + CONFIG) and writes only inside
<edit>/mgx/ — except `mux`, which writes the delivery (OUTPUT, default final_mgx.mp4) beside
the master. The master itself is never modified.

  mgx.py EDIT words [PHRASE ...]     output-timeline word list (mgx/words.json); look up phrases
  mgx.py EDIT frames                 contact sheets + every picture change (mgx/frames/)
  mgx.py EDIT still T [T ...]        QC: cues composited over the master at T (mgx/qc/<label>/)
  mgx.py EDIT render [CUE ...]       render cue sprites (all, or the named ones)
  mgx.py EDIT layers                 caption patches, extra patches, vignettes, card glass
  mgx.py EDIT library [TERM ...]     what is already on disk (SFX + music), searched by name/tags
  mgx.py EDIT fetch URL --kind K --id ID --title T [--type sfx|music] [--tags a,b]
                                     download an Epidemic Sound asset into the local library,
                                     measure it, write a sidecar, print the SFX_LIB line
  mgx.py EDIT sfx                    SFX bus from the cues + mix onto the master's audio
  mgx.py EDIT compose [--all|--chunks 3,4|--dirty CUE,CUE]
  mgx.py EDIT mux                    join the chunks + mixed audio -> OUTPUT
  mgx.py EDIT verify                 frames, sync, loudness, audio present, a still per cue

Run from the repo:  uv run --with pycairo python skills/motion-graphics-pass/scripts/mgx.py ...
(pycairo builds against Homebrew cairo: export PKG_CONFIG_PATH=/opt/homebrew/lib/pkgconfig)
"""
import argparse, glob, importlib.util, json, math, os, re, subprocess, sys, time, wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def sh(args, **kw):
    return subprocess.run(args, check=True, **kw)


def probe(path, *entries, stream="v"):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries", ",".join(entries),
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def count_frames(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-count_packets", "-show_entries",
                          "stream=nb_read_packets", "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return int(out.stdout.strip().split(",")[0])     # ffprobe 9 csv can print a trailing "," ("26829,")


def fps_of(path):
    r = probe(path, "stream=r_frame_rate")["streams"][0]["r_frame_rate"]
    a, b = r.split("/")
    return int(a) / int(b), r


def start_time(path, stream):
    s = probe(path, "stream=start_time", stream=stream)["streams"]
    return float(s[0].get("start_time") or 0) if s else 0.0


# ------------------------------------------------------------------ context
class Ctx:
    def __init__(self, edit, work=None):
        self.edit = os.path.abspath(os.path.expanduser(edit))
        self.work = os.path.abspath(work or os.path.join(self.edit, "mgx"))
        os.makedirs(self.work, exist_ok=True)
        os.environ["MGX_EDIT"], os.environ["MGX_WORK"] = self.edit, self.work
        self._cues = None

    def path(self, *p):
        return os.path.join(self.edit, *p)

    def w(self, *p):
        return os.path.join(self.work, *p)

    @property
    def cues(self):
        if self._cues is None:
            import mglib
            mglib.EDIT, mglib.WORK = self.edit, self.work
            cf = self.w("cues.py")
            if not os.path.exists(cf):
                sys.exit(f"no {cf} — copy examples/episode2/cues.py there and write this episode's cues")
            # FPS must be right before the cue module evaluates anything that uses it
            src = open(cf).read()
            m = re.search(r'^MASTER\s*=\s*"([^"]+)"', src, re.M)
            master = self.path(m.group(1) if m else "final.mp4")
            if os.path.exists(master):
                mglib.set_fps(*fps_of(master))
            spec = importlib.util.spec_from_file_location("cues", cf)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["cues"] = mod
            spec.loader.exec_module(mod)
            if not all(k in mglib.FONTS for k in "rmb") and not mglib.find_system_fonts():
                sys.exit("fonts: set_fonts(r=, m=, b=) in cues.py — no Helvetica Neue found on this system")
            self._cues = mod
        return self._cues

    def cfg(self, name, default=None):
        return getattr(self.cues, name, default)

    @property
    def master(self):
        return self.path(self.cfg("MASTER", "final.mp4"))

    @property
    def base(self):
        return self.path(self.cfg("BASE", "base.mp4"))


# ------------------------------------------------------------------ words
def norm(s):
    return "".join(ch for ch in s.lower() if ch.isalnum() or ch == "'")


def build_words(ctx):
    edl = json.load(open(ctx.path("edl.json")))
    out, t = [], 0.0
    for r in edl["ranges"]:
        s, e = float(r["start"]), float(r["end"])
        tp = ctx.path("transcripts", f"{r['source']}.json")
        words = json.load(open(tp)).get("words", []) if os.path.exists(tp) else []
        for x in words:
            if x.get("type", "word") != "word":
                continue
            if s - 0.02 <= x["start"] < e:
                out.append({"w": x["text"], "t": round(t + x["start"] - s, 3), "e": round(t + min(x["end"], e) - s, 3)})
        t += e - s
    json.dump(out, open(ctx.w("words.json"), "w"))
    return out, t


def cmd_words(ctx, a):
    words, total = build_words(ctx)
    print(f"{len(words)} words, EDL duration {total:.3f}s -> {ctx.w('words.json')}")
    nw = [norm(x["w"]) for x in words]
    for ph in a.phrases:
        toks = [norm(x) for x in ph.split()]
        hits = [(words[i]["t"], words[i + len(toks) - 1]["e"]) for i in range(len(nw) - len(toks) + 1)
                if nw[i:i + len(toks)] == toks]
        print(f"{ph!r}: {hits}")


# ------------------------------------------------------------------ frames
def cmd_frames(ctx, a):
    d = ctx.w("frames")
    os.makedirs(d, exist_ok=True)
    m = ctx.master
    vf = "fps=1/2,scale=384:-2,drawtext=text='%{pts\\:hms}':x=6:y=6:fontsize=20:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=5x4"
    for vs in (["-fps_mode", "vfr"], ["-vsync", "vfr"]):        # ffmpeg >= 5.1 / older
        try:
            sh(["ffmpeg", "-v", "error", "-y", "-skip_frame", "nokey", "-i", m, "-vf", vf, *vs, f"{d}/sheet_%02d.jpg"])
            break
        except subprocess.CalledProcessError:
            continue
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", m, "-vf", "scale=320:-2,select='gt(scene,0.22)',showinfo",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    cuts = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    json.dump(cuts, open(f"{d}/scenes.json", "w"))
    os.makedirs(f"{d}/sc", exist_ok=True)
    for i, t in enumerate(cuts):
        sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{t + 0.5:.3f}", "-i", m, "-frames:v", "1", "-vf",
            f"scale=384:-2,drawtext=text='{i + 1:03d} @ {t:.2f}':x=6:y=6:fontsize=20:fontcolor=yellow:box=1:boxcolor=black@0.6",
            f"{d}/sc/f_{i + 1:03d}.jpg"])
    if cuts:
        sh(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", f"{d}/sc/f_%03d.jpg", "-vf", "tile=5x7", f"{d}/scenes_%02d.jpg"])
    print(f"{len(glob.glob(d + '/sheet_*.jpg'))} contact sheets (every 2 s), {len(cuts)} picture changes -> {d}")
    print("picture changes at:", " ".join(f"{t:.2f}" for t in cuts))


# ------------------------------------------------------------------ stills / sheets
def sheet(d, prefix="still_"):
    from PIL import Image, ImageDraw
    fs = sorted(glob.glob(f"{d}/{prefix}*.jpg"))
    cells = [Image.open(f).resize((960, 540)) for f in fs]
    outs = []
    for k in range(0, len(cells), 4):
        s = Image.new("RGB", (1920, 1080))
        for i, im in enumerate(cells[k:k + 4]):
            ImageDraw.Draw(im).text((10, 10), os.path.basename(fs[k + i])[len(prefix):-4], fill=(255, 255, 0))
            s.paste(im, ((i % 2) * 960, (i // 2) * 540))
        o = f"{d}/sheet_{k // 4:02d}.jpg"
        s.save(o, quality=85)
        outs.append(o)
    return outs


def cmd_still(ctx, a):
    import mglib
    from PIL import Image
    mglib.S = float(os.environ.get("MG_S", "1"))
    ctx.cues
    d = ctx.w("qc", a.label)
    os.makedirs(d, exist_ok=True)
    for ts in a.times:
        t = float(ts)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", ctx.master, "-frames:v", "1",
                              "-vf", "scale=1920:1080", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        bg = Image.frombytes("RGB", (1920, 1080), raw).convert("RGBA")
        for cu in mglib.CUES:
            if cu["t0"] <= t < cu["t1"]:
                surf, W, H = mglib.draw_frame(cu, t)
                im = Image.fromarray(mglib.unpremul(surf, W, H)[..., [2, 1, 0, 3]], "RGBA")
                if mglib.S != 1:
                    im = im.resize((int(round(W / mglib.S)), int(round(H / mglib.S))), Image.LANCZOS)
                bg.alpha_composite(im, (int(cu["box"][0]), int(cu["box"][1])))
        bg.convert("RGB").save(f"{d}/still_{t:07.2f}.jpg", quality=88)
    for s in sheet(d):
        print(s)
    print("NOTE: stills are over the captioned master; caption replacement only shows after compose.")


# ------------------------------------------------------------------ render
def _worker_init(edit, work, scale):
    """Pool initializer. macOS starts workers with `spawn`, so each worker must load the cues
    itself — inheriting the parent's registry only happens under `fork` (Linux)."""
    import mglib
    if not mglib.CUES:
        mglib.S = scale
        Ctx(edit, work).cues


def _worker_render(name, out):
    import mglib
    return mglib.render_name(name, out)


def cmd_render(ctx, a):
    import mglib
    from multiprocessing import Pool
    mglib.S = float(os.environ.get("MG_S", str(probe(ctx.master, "stream=height")["streams"][0]["height"] / 1080)))
    ctx.cues
    out = ctx.w("sprites")
    os.makedirs(out, exist_ok=True)
    names = [c["name"] for c in mglib.CUES]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        sys.exit(f"duplicate cue names: {dup}")
    todo = [c for c in mglib.CUES if not a.names or c["name"] in a.names]
    todo.sort(key=lambda c: -(c["t1"] - c["t0"]))
    t0 = time.time()
    with Pool(a.jobs, initializer=_worker_init, initargs=(ctx.edit, ctx.work, mglib.S)) as pool:
        res = pool.starmap(_worker_render, [(c["name"], out) for c in todo], chunksize=1)
    mpath = ctx.w("manifest.json")
    man = {m["name"]: m for m in (json.load(open(mpath)) if os.path.exists(mpath) else [])}
    for r in res:
        man[r["name"]] = r
    man = {n: m for n, m in man.items() if n in names}          # drop cues that no longer exist
    json.dump([man[n] for n in names if n in man], open(mpath, "w"), indent=1)
    print(f"rendered {len(res)} cue(s) in {time.time() - t0:.0f}s at S={mglib.S:g}; manifest has {len(man)}/{len(names)}")


# ------------------------------------------------------------------ layers
def srt_windows(path, numbers):
    def sec(x):
        h, m, r = x.split(":")
        return int(h) * 3600 + int(m) * 60 + float(r.replace(",", "."))
    wins = {}
    for b in open(path, encoding="utf-8").read().strip().split("\n\n"):
        l = b.strip().split("\n")
        if len(l) >= 2 and "-->" in l[1]:
            a, e = [sec(x.strip()) for x in l[1].split("-->")]
            wins[int(l[0])] = (a, e)
    return [wins[n] for n in numbers]


def merge(wins, gap=0.25):
    out = []
    for a, b in sorted(wins):
        if out and a - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def cmd_layers(ctx, a):
    import numpy as np
    from PIL import Image
    fps, _ = fps_of(ctx.master)
    W = probe(ctx.master, "stream=width")["streams"][0]["width"]
    H = probe(ctx.master, "stream=height")["streams"][0]["height"]
    fa = lambda t: math.floor(t * fps) / fps
    fb = lambda t: math.ceil(t * fps) / fps
    d = ctx.w("layers")
    os.makedirs(d, exist_ok=True)
    layers = []
    # 1. caption replacement + extra patches, restored from BASE (same frames, no captions)
    patches = []
    nums = ctx.cfg("REPLACE_CAPTIONS", [])
    if nums:
        subs = json.load(open(ctx.path("edl.json"))).get("subtitles", "master.srt")
        for a0, b0 in merge(srt_windows(ctx.path(subs), nums)):
            patches.append((*ctx.cfg("CAPTION_BAND"), a0, b0))
    patches += list(ctx.cfg("EXTRA_PATCHES", []))
    if patches:
        if not os.path.exists(ctx.base):
            sys.exit(f"caption replacement needs {ctx.base}")
        # BASE must be the same picture: check one frame outside any caption band
        dur = float(probe(ctx.master, "format=duration")["format"]["duration"])
        chk = max(check_aligned(ctx, dur * q, W, H) for q in (.3, .5, .7))
        print(f"base vs master (top 75% of frame, mean abs diff, worst of 3): {chk:.2f}  (aligned if < 2)")
        if chk > 2:
            sys.exit("BASE does not match MASTER frame-for-frame — caption patches would show a seam")
    for k, (x, y, w, h, a0, b0) in enumerate(patches):
        s0 = max(0.0, fa(a0) - 1 / fps)
        n = int(round((fb(b0) + 1 / fps - s0) * fps))
        f = f"{d}/patch{k:02d}.mp4"
        sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{s0:.6f}", "-i", ctx.base, "-frames:v", str(n), "-an",
            "-vf", f"crop={w}:{h}:{x}:{y}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "6", "-pix_fmt", "yuv420p", f])
        layers.append(dict(name=f"patch{k:02d}", kind="patch", file=f, x=x, y=y, start=s0, frames=n))
    # 2. vignettes
    for k, (a0, b0, strength) in enumerate(ctx.cfg("VIGNETTES", [])):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
        img = np.zeros((H, W, 4), np.uint8)
        img[..., 3] = (np.clip((r - 0.42) / 0.58, 0, 1) ** 1.5 * strength * 255).astype(np.uint8)
        f = f"{d}/vignette{k}.png"
        Image.fromarray(img, "RGBA").save(f)
        s0 = fa(a0)
        layers.append(dict(name=f"vignette{k}", kind="vignette", file=f, x=0, y=0, start=s0,
                           frames=int(round((fa(b0) - s0) * fps))))
    # 3. glass under HyperFrames cards: blur of the master beneath, cut by the card's mask
    for k, g in enumerate(ctx.cfg("GLASS_CARDS", [])):
        card, mask = ctx.path(g["card"]), ctx.path(g["mask"])
        n = count_frames(card)
        s0 = round(g["start"] * fps) / fps
        cw, ch = g.get("crop", (W, H))
        f = f"{d}/glass{k}.mov"
        sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{s0:.6f}", "-i", ctx.master, "-i", mask, "-filter_complex",
            f"[0:v]crop={cw}:{ch}:0:0,scale={cw // 4}:{ch // 4}:flags=bicubic,gblur=sigma=20:steps=2,"
            f"eq=brightness=-0.03:saturation=1.15,scale={cw}:{ch}:flags=bicubic,format=yuva444p10le[b];"
            f"[1:v]crop={cw}:{ch}:0:0,alphaextract[m];[b][m]alphamerge[g]",
            "-map", "[g]", "-frames:v", str(n), "-c:v", "prores_ks", "-profile:v", "4", "-qscale:v", "11",
            "-pix_fmt", "yuva444p10le", f])
        layers.append(dict(name=f"glass{k}", kind="glass", file=f, x=0, y=0, start=s0, frames=n))
        layers.append(dict(name=f"card{k}", kind="card_bt601" if g.get("bt601", True) else "card", file=card,
                           x=0, y=0, start=s0, frames=n))
    # 4. pre-rendered full-frame movies with alpha (e.g. the house "SWITCH TO 1.25X" badge from
    #    build/gfx_badge.py): MOVIE_LAYERS = [dict(name=, file=, start=, bt601=True)]. motion.py's
    #    ProRes is encoded from RGB with swscale's default BT.601 matrix, like the HyperFrames cards.
    for m in ctx.cfg("MOVIE_LAYERS", []):
        f = ctx.path(m["file"])
        lw = probe(f, "stream=width")["streams"][0]["width"]
        if lw != W:
            sys.exit(f"MOVIE_LAYERS {m['name']}: {lw} px wide, master is {W} (overlays are not scaled)")
        layers.append(dict(name=m["name"], kind="card_bt601" if m.get("bt601", True) else "card", file=f,
                           x=0, y=0, start=round(m["start"] * fps) / fps, frames=count_frames(f)))
    json.dump(layers, open(ctx.w("layers.json"), "w"), indent=1)
    print(f"{len(layers)} layers -> {ctx.w('layers.json')}")


def check_aligned(ctx, t, W, H):
    import numpy as np
    def fr(src):
        b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1", "-vf",
                            "scale=480:270,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
        return np.frombuffer(b, np.uint8).reshape(270, 480).astype(int)
    return float(abs(fr(ctx.base) - fr(ctx.master))[:200].mean())


# ------------------------------------------------------------------ sfx
SFX_LIB = {  # kind: (file under SFX_DIR, hit_at seconds or None = first transient, max length)
    "thud_soft": ("structural/ES_Designed, Stinger, Cinematic Hit, Soft Impact 01 - Epidemic Sound.mp3", 1.196, 3.0),
    "hit_soft": ("structural/ES_Designed, Stinger, Cinematic Hit, Soft Impact 02 - Epidemic Sound.mp3", 1.858, 3.5),
    "boom": ("structural/ES_Designed, Boom, Impact, Dark, Cinematic, Low HIt - Epidemic Sound.mp3", 0.302, 3.0),
    "click": ("structural/ES_User Interface, Click, Hard, Short - Epidemic Sound.mp3", None, .5),
    "whoosh_air": ("structural/ES_Swooshes, Whoosh, Designed, Generic, Air - Epidemic Sound.mp3", 0.058, .6),
    "whoosh_soft": ("structural/ES_Swooshes, Whoosh, Soft, Clean - Epidemic Sound.mp3", 0.128, 1.6),
    "whoosh_dry": ("structural/ES_Swooshes, Swish, Short, Classic, Noise, Filter, Dry - Epidemic Sound.mp3", 0.058, .7),
    "tick": ("structural/ES_User Interface, Click, UI Buttons, Confirm, Menu - Epidemic Sound.mp3", 0.058, .6),
    "tick_soft": ("structural/ES_Wood, Impact, Light Hit 01 - Epidemic Sound.mp3", 0.058, .35),
    "scratch": ("structural/ES_Paper, Friction, Envelope, Slide - Epidemic Sound.mp3", None, .6),
    "pop_glass": ("structural/ES_User Interface, Click, Pops, Glass, UI, Pops - Epidemic Sound.mp3", 0.604, .7),
    "pop_ui": ("structural/ES_User Interface, Click, UI Buttons, Bubbly, Option - Epidemic Sound.mp3", 0.058, .3),
    "riser_soft": ("structural/ES_Swooshes, Whoosh, Softs - Epidemic Sound.mp3", 1.73, 2.5),
    "riser": ("structural/ES_Designed, Riser, Cymbal, Reverse, Crescendo, Suspense, Climax 02 - Epidemic Sound.mp3", 1.509, 1.65),
    "pluck": ("structural/ES_User Interface, Click, UI Buttons, Confirm, Light - Epidemic Sound.mp3", None, 1.0),
    "thud_heavy": ("structural/ES_Cloth, Impact, Duvet, Hit Hand - Epidemic Sound.mp3", None, .5),
    "stamp": ("structural/ES_Snow, Impact, Snowball With Stone Or Ice, Punch - Epidemic Sound.mp3", None, .8),
    "drain": ("structural/ES_Swooshes, Swish, Short, Tonal Flyby - Epidemic Sound.mp3", None, 1.2),
    "swell_rev": ("structural/ES_Designed, Riser, Cymbal, Reversed, Pitched Up, Suspense, Climax - Epidemic Sound.mp3", 1.196, 1.5),
    "dip": ("structural/ES_Swooshes, Whoosh, Softs - Epidemic Sound.mp3", 1.73, 2.5),
    "paper_slide": ("structural/ES_Paper, Friction, Envelope, Slide - Epidemic Sound.mp3", None, .9),
    "paper_tear": ("structural/ES_Page Turn 02 - Epidemic Sound.mp3", None, 1.1),
    "knock_soft": ("structural/ES_Wood, Impact, Light Hit 01 - Epidemic Sound.mp3", 0.058, .35),
    "tap": ("structural/ES_User Interface, Click, UI Buttons, Bubbly, Option - Epidemic Sound.mp3", 0.058, .3),
    "drop": ("structural/ES_Cloth, Impact, Duvet, Hit Hand - Epidemic Sound.mp3", None, .5),
    "shimmer": ("structural/ES_User Interface, Click, Pops, Glass, UI, Pops - Epidemic Sound.mp3", 0.604, .7),
}


def cmd_sfx(ctx, a):
    import numpy as np
    import mglib
    ctx.cues
    SR = 48000
    root = os.path.expanduser(os.environ.get("MGX_SFX_DIR") or ctx.cfg("SFX_DIR", "~/Documents/Ambitious/Editing/effects"))
    lib = dict(SFX_LIB, **ctx.cfg("SFX_LIB", {}))
    cache = {}

    def load(p):
        if p not in cache:
            raw = sh(["ffmpeg", "-v", "error", "-i", p, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
            x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
            x /= max(1e-6, np.abs(x).max()) / 0.891          # peak -1 dBFS before the cue's gain
            cache[p] = x
        return cache[p]

    dur = float(probe(ctx.master, "format=duration")["format"]["duration"])
    N = int((dur + 1) * SR)
    bus = np.zeros((N, 2), np.float32)
    placed = []
    for cu in mglib.CUES:
        for kind, t, db in cu["sfx"]:
            if kind not in lib:
                sys.exit(f"cue {cu['name']}: unknown sfx kind {kind!r} (add it to SFX_LIB in cues.py)")
            rel, hit, mx = lib[kind]
            x = load(os.path.join(root, rel))
            if hit is None:
                env = np.abs(x).max(axis=1)
                hit = int(np.argmax(env > 0.2 * env.max())) / SR
            x = x[: int((hit + mx) * SR)].copy()
            fl = min(len(x), int(.25 * SR))
            x[-fl:] *= np.linspace(1, 0, fl)[:, None]
            s = int(round((t - hit) * SR))
            if s < 0:
                x, s = x[-s:], 0
            bus[s:s + len(x)] += x[: N - s] * 10 ** (db / 20)
            placed.append((t, kind, db, cu["name"]))
    pcm = (np.clip(bus, -1, 1) * 32767).astype("<i2")
    with wave.open(ctx.w("sfx.wav"), "wb") as w:
        w.setnchannels(2), w.setsampwidth(2), w.setframerate(SR), w.writeframes(pcm.tobytes())
    print(f"{len(placed)} sfx placed; bus peak {20 * math.log10(float(np.abs(bus).max()) + 1e-9):.1f} dBFS")
    lim = ctx.cfg("SFX_LEVEL_CEILING", 0.93)
    # normalize=0 / level=0: ffmpeg's defaults would halve the programme (amix) and re-level it (alimiter)
    sh(["ffmpeg", "-v", "error", "-y", "-i", ctx.master, "-i", ctx.w("sfx.wav"), "-filter_complex",
        f"[0:a][1:a]amix=inputs=2:normalize=0:duration=first:dropout_transition=0,alimiter=limit={lim}:level=0:attack=2:release=40[a]",
        "-map", "[a]", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", ctx.w("audio_mgx.m4a")])
    print("loudness  master", lufs(ctx.master), " mixed", lufs(ctx.w("audio_mgx.m4a")))
    audibility(ctx, placed)


def audibility(ctx, placed, floor_db=-10.0):
    """M052, measured properly: an effect is heard only if it is not buried under the programme
    in the frequencies where the EFFECT lives. For each placement: take the bins holding 70% of
    the effect's energy (from the exact SFX bus) in [t-0.03, t+0.30], and compare that energy with
    the master's in the same bins. Verified on Episode 2: impacts read +13..+38 dB, while UI pops,
    whooshes and paper at -18..-26 dBFS peak read -15..-55 dB under the voice, i.e. inaudible."""
    import numpy as np
    SR = 48000
    raw = sh(["ffmpeg", "-v", "error", "-i", ctx.master, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
             capture_output=True).stdout
    m = np.frombuffer(raw, np.float32)
    with wave.open(ctx.w("sfx.wav")) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2).mean(axis=1) / 32767
    rows, quiet = [], []
    for t, kind, db, name in sorted(placed):
        i0, i1 = int((t - 0.03) * SR), int((t + 0.30) * SR)
        if i0 < 0 or i1 > min(len(m), len(x)):
            continue
        win = np.hanning(i1 - i0)
        X = np.abs(np.fft.rfft(x[i0:i1] * win)) ** 2
        M = np.abs(np.fft.rfft(m[i0:i1] * win)) ** 2
        o = np.argsort(X)[::-1]
        c = np.cumsum(X[o])
        k = o[: np.searchsorted(c, 0.7 * c[-1]) + 1]
        smr = 10 * np.log10(X[k].sum() / max(1e-12, M[k].sum()))
        rows.append((t, kind, db, name, smr))
        if smr < floor_db:
            quiet.append((t, kind, db, name, smr))
    json.dump([dict(t=round(t, 3), kind=k, gain=g, cue=c, smr_db=round(float(d), 1)) for t, k, g, c, d in rows],
              open(ctx.w("sfx_audibility.json"), "w"), indent=1)
    print(f"audibility (effect vs programme in the effect's own bins): {len(rows) - len(quiet)}/{len(rows)} "
          f"above {floor_db:g} dB")
    for t, kind, db, name, d in quiet:
        print(f"  BURIED  {t:8.2f}  {kind:12s} {db:4d} dB  [{name}]  {d:6.1f} dB  -> raise it ~{floor_db - d + 3:.0f} dB, "
              f"move it into a pause, or drop it")

def lufs(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vn", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[0-9.]+) LUFS", r)
    return float(m[-1]) if m else None


# ------------------------------------------------------------------ library / fetch
AUDIO_EXT = (".mp3", ".wav", ".aif", ".aiff", ".m4a", ".flac")


def lib_dirs(ctx):
    sfx = os.path.expanduser(os.environ.get("MGX_SFX_DIR") or ctx.cfg("SFX_DIR", "~/Documents/Ambitious/Editing/effects"))
    music = os.path.expanduser(ctx.cfg("MUSIC_DIR", os.path.join(os.path.dirname(sfx), "music")))
    return sfx, music


def audio_info(path):
    """duration, first-transient time (the hit), peak dBFS, spectral centroid (bright vs dark)."""
    import numpy as np
    SR = 48000
    raw = sh(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    if not len(x):
        return dict(duration=0.0, hit_at=0.0, peak_db=-120.0, centroid_hz=0)
    env = np.abs(x)
    pk = float(env.max())
    hit = int(np.argmax(env > 0.2 * pk)) / SR
    seg = x[: min(len(x), int(SR * 2))]
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    fr = np.fft.rfftfreq(len(seg), 1 / SR)
    cen = float((sp * fr).sum() / max(1e-12, sp.sum()))
    return dict(duration=round(len(x) / SR, 3), hit_at=round(hit, 3), peak_db=round(20 * math.log10(pk + 1e-9), 1),
                centroid_hz=int(cen))


def cmd_library(ctx, a):
    ctx.cues
    terms = [t.lower() for t in a.terms]
    for label, root in zip(("SFX", "MUSIC"), lib_dirs(ctx)):
        if not os.path.isdir(root):
            print(f"{label}: {root} (missing)")
            continue
        rows = []
        for dp, _, fs in os.walk(root):
            for fn in fs:
                if not fn.lower().endswith(AUDIO_EXT):
                    continue
                p = os.path.join(dp, fn)
                side = os.path.splitext(p)[0] + ".json"
                meta = json.load(open(side)) if os.path.exists(side) else {}
                hay = (fn + " " + " ".join(meta.get("tags", [])) + " " + meta.get("kind", "")).lower()
                if terms and not all(t in hay for t in terms):
                    continue
                rows.append((os.path.relpath(p, root), meta))
        print(f"{label}: {root}  ({len(rows)} match{'es' if len(rows) != 1 else ''})")
        for rel, meta in sorted(rows):
            tag = f"  [{meta.get('kind', '')}; epidemic {meta.get('id', '')[:8]}]" if meta.get("source") == "epidemic" else ""
            print(f"  {rel}{tag}")
    pal = os.path.join(lib_dirs(ctx)[0], "structural", "palette.json")
    if os.path.exists(pal):
        print(f"house palette rules: {pal}")


def cmd_fetch(ctx, a):
    """Download a signed Epidemic Sound URL (from the connector's DownloadSoundEffect /
    DownloadRecording / DownloadRecordingEdit) into the library, with a sidecar. Signed URLs
    expire, so fetch straight after asking the connector for one."""
    import urllib.request
    ctx.cues
    sfx_root, music_root = lib_dirs(ctx)
    root = sfx_root if a.type == "sfx" else music_root
    safe = re.sub(r"[^A-Za-z0-9 ,.&()'_-]+", "", a.title).strip() or a.id
    ext = ".wav" if ".wav" in a.url.lower().split("?")[0] else ".mp3"
    d = os.path.join(root, "epidemic", a.kind if a.type == "sfx" else "beds")
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, f"ES_{safe}{ext}")
    if not os.path.exists(out):
        try:
            with urllib.request.urlopen(a.url, timeout=120) as r, open(out + ".part", "wb") as fh:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    fh.write(b)
        except Exception as e:                      # some sandboxes only allow curl through their proxy
            print(f"urllib failed ({e}); trying curl")
            sh(["curl", "-sSfL", "-o", out + ".part", a.url])
        os.replace(out + ".part", out)
    info = audio_info(out)
    meta = dict(source="epidemic", id=a.id, title=a.title, kind=a.kind, type=a.type,
                tags=[t.strip() for t in (a.tags or "").split(",") if t.strip()],
                fetched=time.strftime("%Y-%m-%d"), **info)
    json.dump(meta, open(os.path.splitext(out)[0] + ".json", "w"), indent=1)
    print(f"-> {out}")
    print(f"   {info['duration']} s, hit at {info['hit_at']} s, peak {info['peak_db']} dBFS, centroid {info['centroid_hz']} Hz")
    if a.type == "sfx":
        rel = os.path.relpath(out, sfx_root)
        mx = round(min(info["duration"] - info["hit_at"], max(0.3, info["duration"])), 2)
        print("   add to cues.py SFX_LIB:")
        print(f'   SFX_LIB["{a.kind}"] = ("{rel}", {info["hit_at"]}, {mx})')


# ------------------------------------------------------------------ compose
def chunk_bounds(total, size):
    return [(f, min(total, f + size)) for f in range(0, total, size)]


def items(ctx):
    order = {"patch": 0, "vignette": 1, "glass": 2, "card": 3, "card_bt601": 3}
    lay = json.load(open(ctx.w("layers.json"))) if os.path.exists(ctx.w("layers.json")) else []
    man = json.load(open(ctx.w("manifest.json")))
    return sorted(lay, key=lambda x: order[x["kind"]]) + sorted(man, key=lambda m: m["start"])


def compose_chunk(ctx, i, f0, f1, fps, rate, its):
    A, B = f0 / fps, f1 / fps
    args = ["ffmpeg", "-v", "error", "-y", "-ss", f"{A:.6f}", "-i", ctx.master]
    fc, cur, n = [], "[0:v]", 1
    for it in its:
        s = it["start"]
        e = s + it["frames"] / fps
        if e <= A or s >= B:
            continue
        off, kind = s - A, it.get("kind", "sprite")
        if kind == "vignette":
            # Build the vignette's WHOLE fade curve on its own clock, then trim to this chunk. A fade
            # whose start falls before the chunk (negative st) is an ffmpeg error, and clamping it
            # would jump the alpha at the seam (Episode 4: a vignette ending 1.2 s into a chunk).
            args += ["-loop", "1", "-framerate", rate, "-t", f"{e - s:.6f}",
                     "-itsoffset", f"{max(off, 0):.6f}", "-i", it["file"]]
            z = max(off, 0.0)                      # where the vignette's own t=0 sits in this chunk's pts
            trim = f",trim=start={-off:.6f},setpts=PTS-STARTPTS" if off < 0 else ""
            src = (f"[{n}:v]format=yuva420p,fade=t=in:st={z:.4f}:d=4:alpha=1,"
                   f"fade=t=out:st={z + max(0.0, e - s - 1.5):.4f}:d=1.5:alpha=1{trim}[s{n}];")
        else:
            args += (["-itsoffset", f"{off:.6f}"] if off >= 0 else ["-ss", f"{-off:.6f}"]) + ["-i", it["file"]]
            if kind == "card_bt601":   # HyperFrames ProRes is BT.601 and untagged
                src = f"[{n}:v]scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=tv:out_range=tv,format=yuva420p[s{n}];"
            elif kind in ("patch", "glass", "card"):
                src = f"[{n}:v]null[s{n}];"
            else:                      # RGB sprites: convert with the BT.709 matrix, not swscale's 601 default
                src = f"[{n}:v]scale=out_color_matrix=bt709:out_range=tv,format=yuva420p[s{n}];"
        lo, hi = max(0, off), min(B, e) - A
        fc.append(src + f"{cur}[s{n}]overlay={it['x']}:{it['y']}:eof_action=pass:repeatlast=0"
                        f":enable='between(t,{lo - 0.001:.4f},{hi + 0.001:.4f})'[v{n}]")
        cur, n = f"[v{n}]", n + 1
    fc.append(f"{cur}setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv[vout]")
    out = ctx.w("chunks", f"c{i:03d}.mp4")
    args += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-frames:v", str(f1 - f0), "-an", "-dn",
             "-map_chapters", "-1", "-map_metadata", "-1",       # a copied chapter track breaks the concat (923 s file)
             "-c:v", "libx264", "-preset", "faster", "-crf", "15", "-pix_fmt", "yuv420p", "-g", "60", "-bf", "3",
             "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1", out]
    t = time.time()
    sh(args)
    got = count_frames(out)
    print(f"chunk {i:03d} {A:7.2f}-{B:7.2f}  layers={n - 1:2d}  frames={got}/{f1 - f0}  {time.time() - t:.0f}s", flush=True)
    if got != f1 - f0:
        sys.exit(f"chunk {i} frame count wrong")


def cmd_compose(ctx, a):
    ctx.cues
    fps, rate = fps_of(ctx.master)
    total = count_frames(ctx.master)
    size = ctx.cfg("CHUNK_FRAMES", 600)
    bounds = chunk_bounds(total, size)
    os.makedirs(ctx.w("chunks"), exist_ok=True)
    its = items(ctx)
    if a.chunks:
        todo = [int(x) for x in a.chunks.split(",")]
    elif a.dirty:
        names = set(a.dirty.split(","))
        todo = sorted({i for i, (f0, f1) in enumerate(bounds) for it in its if it["name"] in names
                       and it["start"] < f1 / fps and it["start"] + it["frames"] / fps > f0 / fps})
    else:
        todo = list(range(len(bounds)))
    json.dump(dict(total=total, size=size, n=len(bounds)), open(ctx.w("chunks", "index.json"), "w"))
    print(f"{total} frames, {len(bounds)} chunks of {size}; composing {len(todo)}")
    for i in todo:
        compose_chunk(ctx, i, *bounds[i], fps, rate, its)


def cmd_mux(ctx, a):
    ctx.cues
    idx = json.load(open(ctx.w("chunks", "index.json")))
    files = [ctx.w("chunks", f"c{i:03d}.mp4") for i in range(idx["n"])]
    missing = [f for f in files if not os.path.exists(f)]
    if missing:
        sys.exit(f"missing chunks: {missing[:5]}")
    with open(ctx.w("chunks", "concat.txt"), "w") as fh:
        fh.writelines("file '" + str(f).replace("'", "'\\''") + "'\n" for f in files)
    # keep the master's A/V offset (its video starts a frame after its audio)
    off = start_time(ctx.master, "v") - start_time(ctx.master, "a")
    out = ctx.path(ctx.cfg("OUTPUT", "final_mgx.mp4"))
    sh(["ffmpeg", "-v", "error", "-y", "-itsoffset", f"{off:.6f}", "-f", "concat", "-safe", "0", "-i", ctx.w("chunks", "concat.txt"),
        "-i", ctx.w("audio_mgx.m4a"), "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", "-map_chapters", "-1",
        "-movflags", "+faststart", out])
    print(f"-> {out}")
    cmd_verify(ctx, a)


def cmd_verify(ctx, a):
    import mglib
    ctx.cues
    out = ctx.path(ctx.cfg("OUTPUT", "final_mgx.mp4"))
    bad = []
    fm, fo = count_frames(ctx.master), count_frames(out)
    dm = float(probe(ctx.master, "stream=duration")["streams"][0]["duration"])
    do = float(probe(out, "stream=duration")["streams"][0]["duration"])
    om = start_time(ctx.master, "v") - start_time(ctx.master, "a")
    oo = start_time(out, "v") - start_time(out, "a")
    has_audio = bool(probe(out, "stream=codec_type", stream="a")["streams"])
    lm, lo = lufs(ctx.master), lufs(out)
    print(f"frames      master {fm}  output {fo}")
    print(f"duration    master {dm:.3f}  output {do:.3f}")
    print(f"A/V offset  master {om:.4f}  output {oo:.4f}")
    print(f"audio       {'present' if has_audio else 'MISSING'}   loudness master {lm}  output {lo} LUFS")
    if fm != fo: bad.append("frame count")
    if abs(dm - do) > 0.05: bad.append("duration")
    if abs(om - oo) > 0.005: bad.append("A/V offset")
    if not has_audio: bad.append("no audio")
    if lm is None or lo is None or abs(lm - lo) > 0.5: bad.append("loudness moved")
    d = ctx.w("qc", "verify")
    os.makedirs(d, exist_ok=True)
    for cu in mglib.CUES:
        t = cu["t0"] + 0.6 * (cu["t1"] - cu["t0"])
        sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", out, "-frames:v", "1", "-vf", "scale=1920:-2",
            f"{d}/still_{t:07.2f}.jpg"])
    sheets = sheet(d)
    print(f"{len(sheets)} verify sheets (one frame per cue, from the DELIVERED file) -> {d}  — READ THEM")
    if bad:
        sys.exit("VERIFY FAILED: " + ", ".join(bad))
    print("verify OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edit")
    ap.add_argument("--work", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("words"); p.add_argument("phrases", nargs="*"); p.set_defaults(fn=cmd_words)
    p = sub.add_parser("frames"); p.set_defaults(fn=cmd_frames)
    p = sub.add_parser("still"); p.add_argument("times", nargs="+"); p.add_argument("--label", default=time.strftime("%H%M%S"))
    p.set_defaults(fn=cmd_still)
    p = sub.add_parser("render"); p.add_argument("names", nargs="*"); p.add_argument("-j", "--jobs", type=int,
                                                                                       default=max(1, (os.cpu_count() or 2) - 1))
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("layers"); p.set_defaults(fn=cmd_layers)
    p = sub.add_parser("library"); p.add_argument("terms", nargs="*"); p.set_defaults(fn=cmd_library)
    p = sub.add_parser("fetch"); p.add_argument("url"); p.add_argument("--kind", required=True)
    p.add_argument("--id", required=True); p.add_argument("--title", required=True)
    p.add_argument("--type", choices=("sfx", "music"), default="sfx"); p.add_argument("--tags", default="")
    p.set_defaults(fn=cmd_fetch)
    p = sub.add_parser("sfx"); p.set_defaults(fn=cmd_sfx)
    p = sub.add_parser("compose"); g = p.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true"); g.add_argument("--chunks"); g.add_argument("--dirty")
    p.set_defaults(fn=cmd_compose)
    p = sub.add_parser("mux"); p.set_defaults(fn=cmd_mux)
    p = sub.add_parser("verify"); p.set_defaults(fn=cmd_verify)
    a = ap.parse_args()
    a.fn(Ctx(a.edit, a.work), a)


if __name__ == "__main__":
    main()
