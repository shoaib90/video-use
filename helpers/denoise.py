"""Neural speech denoising for a source clip, as a prepped source.

Why this exists
---------------
`render.py` applies denoising as an ffmpeg filter string (`audio_filter`), and
ffmpeg's best option there is `arnndn`. That is fine for steady broadband noise
— road drone, air conditioning, handling hiss — and it is what the EDL should
keep using for those.

It is NOT fine for wind. Wind is low-frequency and it GUSTS: on the Detour-2 dam
monologue the noise sat 72% below 300 Hz and swung through 27 dB, and `arnndn`
pulled only 8 dB out of it while leaving the gusting untouched. DeepFilterNet3
takes 23 dB out of the same clip — better than a commercial cloud service on the
same file — and it runs locally at ~24x realtime.

DeepFilterNet cannot be an ffmpeg filter, so this helper works the way the repo
already handles anything ffmpeg can't express: it builds a **prepped source**.
The output is the original video stream-copied with a cleaned audio track, so an
EDL points at it like any other source and captions, offsets and cuts all
resolve unchanged. Set `audio_filter: ""` on those ranges so `render.py` does not
denoise twice.

    uv run python helpers/denoise.py a-roll/IMG_3206.MOV -o edit/prepped/dn_IMG_3206.MOV
    uv run python helpers/denoise.py a-roll/IMG_3206.MOV --measure       # report only
    uv run python helpers/denoise.py in.MOV -o out.MOV --ambience 15     # keep some location tone

Restoring naturalness
---------------------
Full denoising of an outdoor take sounds wrong — you are visibly outside and
there is no air at all. The instinct is to mix the original back in at some low
percentage, and DeepFilterNet even offers `--atten-lim` to do exactly that. On
wind that does not work, and the reason is measurable: 84% of what the denoiser
removes from a windy take is below 300 Hz, so the original's "ambience" IS the
wind. Blending 10% of it back put the Detour-2 noise floor at -51.5 dB, which is
precisely where the old `arnndn` chain already was — the whole gain, given away.

`--ambience` instead blends back the removed material **high-passed** (default
500 Hz), which keeps water, birds and general air while leaving the rumble out.
15% measured -61.8 dB against -50.1 dB for the shipped `arnndn` chain.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from render import AAC_ARGS  # noqa: E402  — one definition of the audio encode


# DeepFilterNet needs its own interpreter, and the pins are not preferences:
#
#   * `DeepFilterLib` 0.5.6 publishes macOS arm64 wheels for cp38-cp311 only.
#     On 3.12+ the install fails trying to build the Rust extension from source.
#   * DeepFilterNet 0.5.6 imports `torchaudio.backend.common.AudioMetaData`,
#     which was deprecated in torchaudio 2.1 and REMOVED in 2.2. With a current
#     torchaudio the import raises ModuleNotFoundError before doing any work.
#
# So this is a separate env, invoked as a subprocess exactly like ffmpeg is,
# and the repo's own 3.12 environment stays free of torch.
TOOL_PYTHON = "3.11"
TOOL_PACKAGES = ["deepfilternet==0.5.6", "torch==2.1.2", "torchaudio==2.1.2",
                 "soundfile", "numpy<2"]
TOOL_ENV = Path.home() / ".cache" / "video-use" / "denoise-env"


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def ensure_tool_env(env_dir: Path = TOOL_ENV) -> Path:
    """Return the `deepFilter` executable, creating its env on first use."""
    exe = env_dir / "bin" / "deepFilter"
    if exe.exists():
        return exe
    if not shutil.which("uv"):
        sys.exit("uv is required to create the denoise environment; see kb/environment.md")
    print(f"first run: creating the DeepFilterNet environment in {env_dir}")
    print(f"  python {TOOL_PYTHON} + {', '.join(TOOL_PACKAGES)}  (~2 GB, once)")
    env_dir.parent.mkdir(parents=True, exist_ok=True)
    run(["uv", "venv", "--python", TOOL_PYTHON, str(env_dir)])
    run(["uv", "pip", "install", "--python", str(env_dir / "bin" / "python"), *TOOL_PACKAGES])
    if not exe.exists():
        sys.exit(f"environment created but {exe} is missing")
    return exe


# -------- probing -------------------------------------------------------------


def probe(path: Path) -> dict:
    # Parse key=value, never positionally. `-show_entries stream=channels,
    # sample_rate` does NOT print in the order you asked for — ffprobe uses its
    # own field order and returns sample_rate FIRST. Reading positionally gives
    # channels=48000, and the caller then loops over 48000 "channels".
    raw_out = run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                   "-show_entries", "stream=channels,sample_rate,duration",
                   "-of", "default=nw=1", str(path)]).stdout
    fields = dict(
        line.split("=", 1) for line in raw_out.splitlines() if "=" in line
    )
    if "channels" not in fields or "sample_rate" not in fields:
        sys.exit(f"no audio stream in {path}")
    channels, rate = int(fields["channels"]), int(fields["sample_rate"])
    if not 1 <= channels <= 8:
        sys.exit(f"implausible channel count {channels} for {path} — "
                 f"probe returned {fields!r}")
    has_video = bool(run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=codec_type", "-of",
                          "default=nw=1:nk=1", str(path)]).stdout.strip())
    return {"channels": channels, "rate": rate, "has_video": has_video}


def decode(path: Path, channels: int = 1, ss: float = 0.0,
           dur: float | None = None) -> np.ndarray:
    """Decode to float32 at 48 kHz. Returns shape (n,) mono or (n, channels)."""
    cmd = ["ffmpeg", "-v", "error"]
    if ss:
        cmd += ["-ss", f"{ss:.4f}"]
    cmd += ["-i", str(path)]
    if dur:
        cmd += ["-t", f"{dur:.4f}"]
    cmd += ["-f", "f32le", "-ac", str(channels), "-ar", "48000", "-"]
    buf = subprocess.run(cmd, capture_output=True).stdout
    a = np.frombuffer(buf, dtype=np.float32)
    return a if channels == 1 else a.reshape(-1, channels)


def is_dual_mono(path: Path, channels: int) -> bool:
    """True when a 'stereo' track is two identical copies of one mic.

    Phone video is usually recorded from a single capsule and written as
    stereo, and every Detour-2 a-roll clip shot on the phone came back with
    L/R correlation of exactly 1.0 (side channel at -220 dB). Detecting it
    halves the denoise work and, more importantly, keeps the result bit-identical
    across channels instead of running the model twice and getting two slightly
    different answers.
    """
    if channels != 2:
        return False
    x = decode(path, channels=2, ss=0.0, dur=30.0)
    if x.size == 0:
        return False
    return bool(np.array_equal(x[:, 0], x[:, 1]))


# -------- measurement --------------------------------------------------------


def _db(v: float) -> float:
    return 20.0 * np.log10(max(float(v), 1e-12))


def noise_stats(x: np.ndarray, window_ms: int = 50) -> tuple[float, float]:
    """(speech level, noise floor) in dBFS, from windowed RMS percentiles.

    The loud windows are speech and the quiet ones are whatever is left when he
    stops talking, so the 90th and 5th percentiles bracket the two without
    needing a VAD or word timings. (Deepgram word spans are ~87% contiguous on
    this footage, so they cannot locate the pauses — see kb/gotchas.md.)
    """
    k = int(48000 * window_ms / 1000)
    if len(x) < k * 20:
        return 0.0, 0.0
    frames = x[: len(x) // k * k].reshape(-1, k).astype(np.float64)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-20)
    return _db(np.percentile(rms, 90)), _db(np.percentile(rms, 5))


def report(before: np.ndarray, after: np.ndarray, label: str = "") -> None:
    """Print the change, with the noise floor referred to a FIXED speech level.

    Judging a denoiser by its raw noise floor flatters anything that also turns
    the voice down, and judging it by speech-to-noise separation hides what the
    listener actually hears. Normalising the speech to the same level in both
    and then comparing floors is the honest comparison — and note that loudnorm
    at the end of the render puts ~4 dB of the floor straight back, so this is
    the number to watch, not the separation.
    """
    sp_b, fl_b = noise_stats(before)
    sp_a, fl_a = noise_stats(after)
    norm_a = fl_a + (sp_b - sp_a)
    print(f"  {label}" if label else "")
    print(f"    speech level   {sp_b:7.1f} dB  ->  {sp_a:7.1f} dB")
    print(f"    noise floor    {fl_b:7.1f} dB  ->  {fl_a:7.1f} dB")
    print(f"    voice-normalised floor: {norm_a:.1f} dB  "
          f"({norm_a - fl_b:+.1f} dB vs the source)")


# -------- the denoise pass ---------------------------------------------------


def deepfilternet(wav_in: Path, wav_out: Path, exe: Path, model: str,
                  postfilter: bool, atten_lim: float | None) -> None:
    out_dir = wav_out.parent / f".dfn_{wav_out.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(exe), "-m", model, "--log-level", "error", "-o", str(out_dir)]
    if postfilter:
        cmd.append("--pf")
    if atten_lim is not None:
        cmd += ["-a", str(atten_lim)]
    cmd.append(str(wav_in))
    # DeepFilterNet writes <stem>_<model>[_pf].wav and shells out to git for a
    # version string, which prints a harmless "not a git repository" to stderr.
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    produced = sorted(out_dir.glob("*.wav"))
    if len(produced) != 1:
        sys.exit(f"expected one file from DeepFilterNet, got {produced}")
    produced[0].replace(wav_out)
    shutil.rmtree(out_dir, ignore_errors=True)


def blend_ambience(raw: Path, clean: Path, out: Path, pct: float, hp_hz: int) -> None:
    """clean + pct% of high-passed (raw - clean).

    The subtraction recovers exactly what the model removed; the high-pass drops
    the part of it that is wind. Done in ffmpeg rather than numpy so an hour-long
    source does not have to fit in memory.
    """
    gain = pct / 100.0
    graph = (
        "[1:a]volume=-1[neg];"
        "[0:a][neg]amix=inputs=2:weights=1 1:normalize=0:duration=first[resid];"
        f"[resid]highpass=f={hp_hz}:poles=2,volume={gain:.4f}[amb];"
        "[1:a][amb]amix=inputs=2:weights=1 1:normalize=0:duration=first[mix]"
    )
    run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-i", str(clean),
         "-filter_complex", graph, "-map", "[mix]",
         "-c:a", "pcm_f32le", "-ar", "48000", "-ac", "1", str(out)])


def assert_same_length(a: Path, b: Path) -> None:
    """A denoiser that changes the length silently breaks every later position.

    DeepFilterNet pads to compensate its STFT delay, and the padding is only
    removed when `--no-delay-compensation` is absent. If a future version, model
    or flag combination changes that, one shifted source would move every cut
    after it — and the render would still succeed. So this is checked, not
    assumed. Measured on DeepFilterNet3: 17,028,000 samples in, 17,028,000 out.
    """
    def n_samples(p: Path) -> int:
        return len(decode(p, channels=1))
    na, nb = n_samples(a), n_samples(b)
    if na != nb:
        sys.exit(f"length changed: {na} -> {nb} samples "
                 f"({(nb - na) / 48000 * 1000:+.2f} ms). Refusing to continue — "
                 f"this would shift every cut after this source.")


def mux(source: Path, audio: Path, out: Path, channels: int) -> None:
    """Original video stream-copied, new audio encoded to the pipeline's AAC.

    `-ac` follows the SOURCE rather than AAC_ARGS' stereo default, so the prepped
    file is a faithful drop-in for the original. `render.py`'s extract forces
    stereo later anyway (a lone mono source corrupts the concat — gotchas.md),
    but that is the extract's job, not this one's.
    """
    aac = list(AAC_ARGS)
    aac[aac.index("-ac") + 1] = str(channels)
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(source), "-i", str(audio)]
    if probe(source)["has_video"]:
        cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy"]
    else:
        cmd += ["-map", "1:a:0"]
    cmd += [*aac, "-movflags", "+faststart", str(out)]
    run(cmd)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Denoise a clip's speech with DeepFilterNet, as a prepped source")
    ap.add_argument("source", type=Path)
    ap.add_argument("-o", "--output", type=Path,
                    help="Prepped source to write (video stream-copied). "
                         "Omit with --measure to only report.")
    ap.add_argument("--model", default="DeepFilterNet3",
                    help="DeepFilterNet2 or DeepFilterNet3 (default)")
    ap.add_argument("--no-postfilter", action="store_true",
                    help="Skip the post-filter. It is ON by default: it took a "
                         "further 8.9 dB out of the Detour-2 dam take.")
    ap.add_argument("--atten-lim", type=float, default=None,
                    help="DeepFilterNet's own attenuation limit in dB. Mixes the "
                         "NOISY signal back full-band, so on wind it restores the "
                         "rumble — prefer --ambience.")
    ap.add_argument("--ambience", type=float, default=0.0,
                    help="Percent of the removed material to blend back, "
                         "high-passed (see --ambience-hp). 15 is a good start.")
    ap.add_argument("--ambience-hp", type=int, default=500,
                    help="High-pass for the blended ambience, Hz (default 500). "
                         "Below ~300 Hz is where the wind lives.")
    ap.add_argument("--measure", action="store_true",
                    help="Report the before/after noise floor")
    args = ap.parse_args()

    src = args.source.resolve()
    if not src.exists():
        sys.exit(f"source not found: {src}")
    if not args.output and not args.measure:
        sys.exit("nothing to do: pass -o/--output, or --measure to only report")

    info = probe(src)
    dual = is_dual_mono(src, info["channels"])
    print(f"{src.name}: {info['channels']}ch @ {info['rate']} Hz"
          f"{' (dual mono — one capsule)' if dual else ''}")

    exe = ensure_tool_env()
    work = Path(tempfile.mkdtemp(prefix="denoise-"))
    try:
        # A dual-mono track is one signal written twice, so denoise it once and
        # let the mux re-expand it. A genuinely stereo track has to be done per
        # channel; the model is mono-only and treats each independently, which
        # can nudge the stereo image — acceptable for a dialogue take, and worth
        # knowing before using this on music.
        n_proc = 1 if (dual or info["channels"] == 1) else info["channels"]
        cleaned: list[Path] = []
        for ch in range(n_proc):
            raw_wav = work / f"raw_{ch}.wav"
            if n_proc == 1:
                run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1",
                     "-ar", "48000", "-c:a", "pcm_s16le", str(raw_wav)])
            else:
                run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex",
                     f"[0:a]pan=mono|c0=c{ch}[m]", "-map", "[m]", "-ar", "48000",
                     "-c:a", "pcm_s16le", str(raw_wav)])
            out_wav = work / f"clean_{ch}.wav"
            print(f"  denoising channel {ch}: {args.model}"
                  f"{'' if args.no_postfilter else ' + postfilter'}")
            deepfilternet(raw_wav, out_wav, exe, args.model,
                          not args.no_postfilter, args.atten_lim)
            assert_same_length(raw_wav, out_wav)

            if args.ambience > 0:
                print(f"  blending back {args.ambience:g}% ambience, "
                      f"high-passed {args.ambience_hp} Hz")
                blended = work / f"blend_{ch}.wav"
                blend_ambience(raw_wav, out_wav, blended, args.ambience,
                               args.ambience_hp)
                assert_same_length(raw_wav, blended)
                out_wav = blended

            if args.measure:
                report(decode(raw_wav), decode(out_wav), f"channel {ch}")
            cleaned.append(out_wav)

        if args.output:
            out = args.output.resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            if n_proc == 1 and info["channels"] > 1:
                # re-expand the single processed signal to the source's layout
                joined = work / "joined.wav"
                run(["ffmpeg", "-v", "error", "-y", "-i", str(cleaned[0]),
                     "-af", f"pan={info['channels']}c|"
                            + "|".join(f"c{i}=c0" for i in range(info["channels"])),
                     "-c:a", "pcm_f32le", str(joined)])
                audio = joined
            elif n_proc > 1:
                joined = work / "joined.wav"
                cmd = ["ffmpeg", "-v", "error", "-y"]
                for p in cleaned:
                    cmd += ["-i", str(p)]
                cmd += ["-filter_complex",
                        f"{''.join(f'[{i}:a]' for i in range(len(cleaned)))}"
                        f"amerge=inputs={len(cleaned)}[a]",
                        "-map", "[a]", "-c:a", "pcm_f32le", str(joined)]
                run(cmd)
                audio = joined
            else:
                audio = cleaned[0]
            mux(src, audio, out, info["channels"])
            size = out.stat().st_size / (1024 * 1024)
            print(f"wrote {out} ({size:.1f} MB)")
            print("  point the EDL source at this file and set "
                  '`audio_filter: ""` on its ranges so render.py does not '
                  "denoise it a second time")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
