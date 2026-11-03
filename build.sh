#!/usr/bin/env bash
# Builds output/Video_Kesedaran_Penyelaras_KKP.mp4 from src/ (frames via Playwright, music via numpy).
set -euo pipefail
cd "$(dirname "$0")"
WORK="${WORK:-$(mktemp -d)}"
mkdir -p output
node src/render.js "$WORK/frames" 30 4
python3 src/music.py "$WORK/music.wav"
ffmpeg -y -hide_banner -loglevel error -framerate 30 -i "$WORK/frames/f%05d.jpg" -i "$WORK/music.wav" \
  -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -c:a aac -b:a 192k -shortest output/Video_Kesedaran_Penyelaras_KKP.mp4
echo "OK: output/Video_Kesedaran_Penyelaras_KKP.mp4"
