#!/usr/bin/env bash
# Bring a fresh macOS machine to the state recorded in kb/environment.md.
#
#   git clone git@github.com:shoaib90/video-use.git && cd video-use
#   git checkout local
#   bash kb/bootstrap.sh
#
# Idempotent: safe to re-run. Does NOT write any secret — see step 6.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS="$HOME/.cache/whisper-models"
ok(){ printf '  \033[32m✓\033[0m %s\n' "$1"; }
skip(){ printf '  \033[90m·\033[0m %s\n' "$1"; }
warn(){ printf '  \033[33m!\033[0m %s\n' "$1"; }
step(){ printf '\n\033[1m%s\033[0m\n' "$1"; }

step "0. prerequisites"
command -v brew >/dev/null || { echo "  Homebrew required: https://brew.sh"; exit 1; }
ok "homebrew $(brew --version | head -1 | awk '{print $2}')"
command -v uv >/dev/null || brew install uv
ok "uv $(uv --version | awk '{print $2}')"

step "1. ffmpeg WITH libass  (the trap: plain 'brew install ffmpeg' has none)"
# Homebrew split the formula. `ffmpeg` (slim) has no libass, so the subtitles
# filter does not exist and caption burn-in fails with a misleading exit 234.
# libass lives in `ffmpeg-full`, which is keg-only and must be force-linked.
if ffmpeg -hide_banner -filters 2>/dev/null | awk '{print $2}' | grep -qx subtitles; then
  ok "subtitles filter already present ($(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}'))"
else
  brew list ffmpeg-full >/dev/null 2>&1 || brew install ffmpeg-full
  brew list ffmpeg      >/dev/null 2>&1 && brew unlink ffmpeg >/dev/null 2>&1
  brew link --force --overwrite ffmpeg-full >/dev/null 2>&1
  hash -r 2>/dev/null || true
  if ffmpeg -hide_banner -filters 2>/dev/null | awk '{print $2}' | grep -qx subtitles; then
    ok "ffmpeg-full linked; subtitles filter present"
  else
    warn "subtitles filter STILL missing — captions will not burn in. See kb/gotchas.md"
  fi
fi

step "2. optional tools"
command -v yt-dlp >/dev/null && ok "yt-dlp $(yt-dlp --version)" || { brew install yt-dlp && ok "yt-dlp installed"; }
command -v node   >/dev/null && ok "node $(node --version) (HyperFrames needs 22+)" || warn "node missing — HyperFrames/Remotion slots unavailable"

step "3. build deps for Manim (pycairo fails without these)"
for f in pkgconf cairo pango cmake; do
  brew list "$f" >/dev/null 2>&1 && skip "$f already installed" || { brew install "$f" >/dev/null && ok "$f installed"; }
done

step "4. python environment"
cd "$REPO"
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:/opt/homebrew/share/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
# Do not pipe to tail: it masks the exit code (kb/gotchas.md).
if uv sync --extra animations >/tmp/_bootstrap_uv.log 2>&1; then
  ok "uv sync --extra animations ($(uv run python -c 'import manim;print("manim "+manim.__version__)' 2>/dev/null || echo 'manim missing'))"
else
  warn "uv sync failed — see /tmp/_bootstrap_uv.log"
fi

step "5. local whisper models (~600 MB, not in git)"
mkdir -p "$MODELS"
command -v whisper-cli >/dev/null || brew install whisper-cpp
for m in small.en base.en; do
  f="$MODELS/ggml-$m.bin"
  if [ -s "$f" ]; then skip "ggml-$m.bin present ($(du -h "$f" | cut -f1))"; else
    echo "  downloading ggml-$m.bin …"
    curl -fsSL -o "$f" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$m.bin" \
      && ok "ggml-$m.bin ($(du -h "$f" | cut -f1))" || warn "download failed: ggml-$m.bin"
  fi
done

step "6. secrets  (NOT in git — you must do this by hand)"
if grep -q '^DEEPGRAM_API_KEY=..' "$REPO/.env" 2>/dev/null; then
  ok ".env has DEEPGRAM_API_KEY"
else
  warn "no DEEPGRAM_API_KEY. Transcription will not work until you run:"
  echo "        printf 'DEEPGRAM_API_KEY=%s\\n' 'YOUR_KEY' > $REPO/.env && chmod 600 $REPO/.env"
  echo "      Copy the key from the other machine's .env, or re-issue one at deepgram.com."
fi

step "7. register the skill with Claude Code"
mkdir -p "$HOME/.claude/skills"
LINK="$HOME/.claude/skills/video-use"
if [ "$(readlink "$LINK" 2>/dev/null)" = "$REPO" ]; then skip "already registered -> $REPO"; else
  ln -sfn "$REPO" "$LINK" && ok "registered -> $REPO"
fi
# The whole directory must be symlinked, not just SKILL.md — helpers/ and kb/
# have to sit beside it for path resolution to work.

step "8. verify"
bash "$REPO/kb/check-env.sh"
