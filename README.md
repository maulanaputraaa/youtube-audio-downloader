# YouTube Audio Downloader

Tools sederhana untuk download **audio saja** dari YouTube (mp3 / m4a / wav / opus / flac). **Video tidak diunduh** — tools ini hanya mengambil stream audio (`-f bestaudio`), lalu meng-convert-nya ke format pilihan. Jadi file hasilnya jauh lebih kecil dan download-nya lebih cepat daripada download video.

## Yang dibutuhkan
- Python 3.10+
- ffmpeg (sudah ada di kebanyakan sistem; di Ubuntu: `sudo apt install ffmpeg`)

## Install (sekali saja)
```bash
./setup.sh
```

## Cara pakai — lewat web (paling gampang)
```bash
python3 app.py
```
Buka http://localhost:8000, tempel URL video, klik **Tampilkan Pilihan Kualitas**. Muncul tabel seperti ini — klik **Download** di baris kualitas yang kamu mau:

| File type | Format | Action |
|---|---|---|
| MP3 - 320kbps | Auto | Download |
| MP3 - 256kbps | Auto | Download |
| MP3 - 192kbps | Auto | Download |
| MP3 - 128kbps | Auto | Download |
| M4A - Original (kualitas asli) | Auto | Download |

Halaman juga menampilkan kualitas audio asli videonya, supaya kamu tahu kalau pilih 320kbps dari video yang aslinya 128kbps tidak menambah kualitas suara. File tersimpan di folder `downloads/` dan bisa diunduh dari halaman itu juga.

## Cara pakai — playlist (banyak video sekaligus)
**Lewat web:** tempel URL playlist (`.../playlist?list=...`), centang "Ini playlist", klik Tampilkan Pilihan Kualitas. Muncul daftar semua video di playlist, lalu pilih kualitas di tabel — klik Download sekali, semua video terunduh dengan kualitas itu.

**Lewat terminal:**
```bash
python3 download.py "URL_PLAYLIST" --playlist
python3 download.py "URL_PLAYLIST" --playlist --format mp3 --quality 256
python3 download.py "URL_PLAYLIST" --playlist --items 1-5   # hanya 5 video pertama
```

## Cara pakai — lewat terminal (1 video)
```bash
python3 download.py "https://www.youtube.com/watch?v=VIDEO_ID"
python3 download.py "URL" --format mp3 --quality 320
python3 download.py "URL" --format m4a --output-dir ./musik
```

## File
- `download.py` — CLI
- `app.py` — web UI lokal (tanpa library tambahan)
- `setup.sh` — install yt-dlp ke venv lokal `.venv/`

## Catatan penting
Gunakan hanya untuk video milikmu sendiri, video berlisensi bebas / Creative Commons, atau yang kamu punya izin untuk mengunduhnya. Mengunduh musik/video berhak cipta tanpa izin melanggar ketentuan YouTube dan hukum hak cipta.
