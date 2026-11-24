#!/usr/bin/env python3
"""Download audio dari YouTube — CLI sederhana.

Cara pakai:
    python3 download.py "https://www.youtube.com/watch?v=VIDEO_ID"
    python3 download.py "URL" --format mp3 --quality 192
    python3 download.py "URL" --format m4a --output-dir ./musik

Format: mp3, m4a, wav, opus, flac
Kualitas (mp3/opus): 128, 192, 320

Hanya gunakan untuk video milikmu sendiri, berlisensi bebas / Creative Commons,
atau yang kamu punya izin untuk mengunduhnya.
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_ytdlp():
    # 1) venv di folder ini, 2) yt-dlp di PATH
    for venv_path in (
        os.path.join(HERE, ".venv", "Scripts", "yt-dlp.exe"),
        os.path.join(HERE, ".venv", "bin", "yt-dlp"),
    ):
        if os.path.isfile(venv_path):
            return venv_path
    found = shutil.which("yt-dlp")
    if found:
        return found
    return None


def main():
    p = argparse.ArgumentParser(description="Download audio dari YouTube")
    p.add_argument("url", help="URL video / playlist YouTube")
    p.add_argument("--format", default="mp3", choices=["mp3", "m4a", "wav", "opus", "flac"],
                   help="Format audio (default: mp3)")
    p.add_argument("--quality", default="192", choices=["128", "192", "256", "320"],
                   help="Kualitas kbps untuk mp3/opus (default: 192)")
    p.add_argument("--output-dir", default=os.path.join(HERE, "downloads"),
                   help="Folder hasil (default: ./downloads)")
    p.add_argument("--playlist", action="store_true",
                   help="Izinkan download seluruh playlist (default: hanya 1 video)")
    p.add_argument("--items", default=None,
                   help="Batasi video yang diunduh dari playlist, contoh: 1-5 atau 1,3,7 (default: semua)")
    args = p.parse_args()

    ytdlp = find_ytdlp()
    if not ytdlp:
        print("yt-dlp tidak ditemukan. Jalankan dulu:  ./setup.sh", file=sys.stderr)
        sys.exit(1)
    if not shutil.which("ffmpeg"):
        print("ffmpeg tidak ditemukan. Install dulu ffmpeg.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    out = os.path.join(args.output_dir, "%(title)s.%(ext)s")

    cmd = [
        ytdlp,
        # Hanya stream audio yang diunduh, video TIDAK diunduh sama sekali.
        "-f", "bestaudio",
        "-x", "--audio-format", args.format,
        "--audio-quality", args.quality,
        "-o", out,
        "--no-playlist" if not args.playlist else "--yes-playlist",
        "--embed-metadata",
        args.url,
    ]
    if args.items:
        cmd += ["--playlist-items", args.items]
    print("Menjalankan:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"\nSelesai. File ada di: {args.output_dir}")
    else:
        print(f"\nGagal (kode {result.returncode}). Coba update yt-dlp: ./setup.sh", file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
