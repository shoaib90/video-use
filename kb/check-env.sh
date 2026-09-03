#!/usr/bin/env bash
# Re-verify the facts in environment.md. Run from the repo root.
echo "== binaries =="
for b in ffmpeg ffprobe node uv yt-dlp; do
  printf '%-9s %s\n' "$b" "$(command -v $b >/dev/null && $b --version 2>&1 | head -1 || echo MISSING)"
done
echo
echo "== libass (subtitles) =="
if ffmpeg -hide_banner -filters 2>/dev/null | awk '{print $2}' | grep -qx subtitles; then
  echo "OK - subtitles filter present"
else
  echo "BROKEN - no subtitles filter; see kb/gotchas.md (need ffmpeg-full linked)"
fi
echo
echo "== keys =="
for k in DEEPGRAM_API_KEY ELEVENLABS_API_KEY; do
  if grep -q "^$k=.." .env 2>/dev/null; then echo "$k set (.env)"
  elif [ -n "${!k}" ]; then echo "$k set (env)"
  else echo "$k NOT set"; fi
done
echo
echo "== python deps =="
uv run python -c "import requests,librosa,matplotlib,PIL,numpy; print('core deps OK')" 2>&1 | tail -1
echo
echo "== skill registration =="
[ -L "$HOME/.claude/skills/video-use" ] && echo "registered -> $(readlink "$HOME/.claude/skills/video-use")" || echo "NOT registered"
echo
echo "== animation engines =="
uv run python -c "import manim;print('manim',manim.__version__)" 2>/dev/null || echo "manim MISSING"
printf 'hyperframes %s\n' "$(npm view hyperframes version 2>/dev/null || echo unreachable)"
printf 'remotion    %s\n' "$(npm view remotion version 2>/dev/null || echo unreachable)"
echo
echo "== local ASR =="
command -v whisper-cli >/dev/null && echo "whisper-cli present" || echo "whisper-cli MISSING"
for m in small.en base.en; do
  f="$HOME/.cache/whisper-models/ggml-$m.bin"
  [ -f "$f" ] && echo "model $m $(du -h "$f" | cut -f1)" || echo "model $m absent"
done
echo
echo "== tests =="
uv run --with pytest python -m pytest tests/ -q 2>&1 | tail -1
