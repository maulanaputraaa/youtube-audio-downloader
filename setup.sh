#!/bin/bash
# Install yt-dlp ke venv lokal (tidak butuh sudo, tidak mengganggu Python sistem).
set -e
cd "$(dirname "$0")"
python3 -m venv .venv 2>/dev/null || true
.venv/bin/pip install -q --upgrade pip yt-dlp
echo "OK. yt-dlp: $(.venv/bin/yt-dlp --version)"
echo "Cek ffmpeg: $(ffmpeg -version 2>/dev/null | head -1 || echo 'TIDAK ADA — install ffmpeg dulu')"
echo ""
echo "Pakai CLI :  python3 download.py \"URL_VIDEO\""
echo "Pakai web :  python3 app.py  -> buka http://localhost:8000"
