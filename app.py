#!/usr/bin/env python3
"""Web UI lokal untuk download audio YouTube — 1 video atau 1 playlist.

Alur 1 video:   tempel URL video -> Tampilkan Pilihan Kualitas -> klik Download
Alur playlist:  tempel URL playlist (atau centang "Ini playlist") -> tombolnya
                menampilkan daftar semua video di playlist -> pilih kualitas
                di tabel -> klik Download, semua video terunduh sekaligus
                dengan kualitas itu.

Tabel kualitasnya:
    File type          Format   Action
    MP3 - 320kbps      Auto     [ Download ]
    MP3 - 256kbps      Auto     [ Download ]
    MP3 - 192kbps      Auto     [ Download ]
    MP3 - 128kbps      Auto     [ Download ]

Jalankan:  python3 app.py
Lalu buka:  http://localhost:8000

Tidak butuh library tambahan — hanya Python standar + yt-dlp + ffmpeg.
Hanya gunakan untuk video milikmu sendiri, berlisensi bebas / Creative Commons,
atau yang kamu punya izin untuk mengunduhnya.
"""
import html
import json
import os
import shutil
import subprocess
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS = os.path.join(HERE, "downloads")
PORT = int(os.environ.get("PORT", "8000"))

QUALITIES = ["320", "256", "192", "128"]

state = {"status": "Siap. Tempel URL video atau playlist, lalu klik Tampilkan Pilihan Kualitas.",
         "video": None,      # {url, title, uploader, duration, best_abr}
         "playlist": None}   # {url, title, count, entries: [{title, duration}]}
lock = threading.Lock()


def find_ytdlp():
    for venv_path in (
        os.path.join(HERE, ".venv", "Scripts", "yt-dlp.exe"),
        os.path.join(HERE, ".venv", "bin", "yt-dlp"),
    ):
        if os.path.isfile(venv_path):
            return venv_path
    return shutil.which("yt-dlp")


def set_status(msg):
    with lock:
        state["status"] = msg


def fmt_duration(seconds):
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return ""
    return f"{s // 60}:{s % 60:02d}"


def is_playlist_url(url):
    return "list=" in url or "/playlist?" in url


def probe_video(url):
    """Ambil judul/durasi/kualitas audio asli 1 video via yt-dlp -J."""
    ytdlp = find_ytdlp()
    if not ytdlp:
        return None, "yt-dlp tidak ditemukan. Jalankan ./setup.sh dulu."
    r = subprocess.run([ytdlp, "-J", "--no-playlist", url],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()[-1:]
        return None, "Tidak bisa membaca video itu. " + " ".join(tail)
    try:
        info = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None, "Respons yt-dlp tidak bisa dibaca."
    best_abr = 0
    for f in info.get("formats", []):
        if f.get("vcodec") in ("none", None) and f.get("acodec") not in ("none", None):
            abr = f.get("abr") or 0
            if abr and abr > best_abr:
                best_abr = abr
    return {
        "url": url,
        "title": info.get("title") or url,
        "uploader": info.get("uploader") or info.get("channel") or "",
        "duration": fmt_duration(info.get("duration")),
        "best_abr": int(best_abr) if best_abr else None,
    }, None


def probe_playlist(url):
    """Ambil daftar video di playlist via yt-dlp -J --flat-playlist (cepat,
    tidak download apa-apa, hanya judul & durasi)."""
    ytdlp = find_ytdlp()
    if not ytdlp:
        return None, "yt-dlp tidak ditemukan. Jalankan ./setup.sh dulu."
    r = subprocess.run([ytdlp, "-J", "--flat-playlist", url],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()[-1:]
        return None, "Tidak bisa membaca playlist itu. " + " ".join(tail)
    try:
        info = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None, "Respons yt-dlp tidak bisa dibaca."
    entries = []
    for e in info.get("entries") or []:
        if not e:
            continue
        entries.append({"title": e.get("title") or e.get("id") or "?",
                        "duration": fmt_duration(e.get("duration"))})
    if not entries:
        return None, "Playlist ini kosong atau tidak bisa dibaca (mungkin privat)."
    return {
        "url": url,
        "title": info.get("title") or "Playlist",
        "uploader": info.get("uploader") or info.get("channel") or "",
        "count": len(entries),
        "entries": entries,
    }, None


def run_download(url, fmt, quality, playlist=False, count=None):
    ytdlp = find_ytdlp()
    if not ytdlp:
        set_status("yt-dlp tidak ditemukan. Jalankan ./setup.sh dulu.")
        return
    if not shutil.which("ffmpeg"):
        set_status("FFmpeg tidak ditemukan. Install FFmpeg dan pastikan tersedia di PATH agar audio bisa dikonversi.")
        return
    os.makedirs(DOWNLOADS, exist_ok=True)
    label = f"{fmt.upper()} - {quality}kbps" if quality != "0" else f"{fmt.upper()} - Original"
    if playlist:
        set_status(f"Mengunduh playlist ({count or '?'} video) — {label} ...\n"
                   f"Video diunduh satu per satu, halaman ini akan update kalau sudah selesai. "
                   f"File yang sudah jadi langsung muncul di daftar bawah.")
    else:
        set_status(f"Mengunduh {label}: {url} ...")
    # -f bestaudio: hanya stream audio yang diunduh, video TIDAK diunduh sama sekali.
    # -x: lalu audio itu di-convert ke format pilihan (mp3/m4a/dll).
    cmd = [ytdlp, "-f", "bestaudio", "-x", "--audio-format", fmt,
           "-o", os.path.join(DOWNLOADS, "%(title)s.%(ext)s"),
           "--yes-playlist" if playlist else "--no-playlist",
           "--embed-metadata", url]
    if quality != "0":
        cmd += ["--audio-quality", quality]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        if playlist:
            set_status(f"Selesai! Playlist ({count or '?'} video) sudah terunduh sebagai {label} — cek daftar file di bawah.")
        else:
            set_status(f"Selesai! {label} sudah tersimpan — cek daftar file di bawah.")
    else:
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-3:]
        set_status("Gagal: " + " | ".join(tail))


def quality_table(url, fmt_note="", playlist=False):
    """Tabel pilihan kualitas, tampilannya seperti contoh di screenshot."""
    u = html.escape(url, quote=True)
    pl = '<input type="hidden" name="playlist" value="1">' if playlist else ""
    rows = []
    for q in QUALITIES:
        rows.append(f"""<tr>
<td>MP3 - {q}kbps</td><td>Auto</td>
<td><form method="post" action="/download" style="margin:0">
<input type="hidden" name="url" value="{u}">
<input type="hidden" name="format" value="mp3">
<input type="hidden" name="quality" value="{q}">{pl}
<button type="submit" class="dl">&#11015; Download</button></form></td>
</tr>""")
    rows.append(f"""<tr>
<td>M4A - Original (kualitas asli)</td><td>Auto</td>
<td><form method="post" action="/download" style="margin:0">
<input type="hidden" name="url" value="{u}">
<input type="hidden" name="format" value="m4a">
<input type="hidden" name="quality" value="0">{pl}
<button type="submit" class="dl">&#11015; Download</button></form></td>
</tr>""")
    note = ("<p><small>Kualitas yang kamu pilih berlaku untuk <b>semua video</b> di playlist ini.</small></p>"
            if playlist else fmt_note)
    return f"""{note}
<table><tr><th>File type</th><th>Format</th><th>Action</th></tr>
{''.join(rows)}</table>"""


def playlist_list(pl):
    shown = pl["entries"][:100]
    rows = "".join(
        f"<li>{html.escape(e['title'])}"
        f"{' · ' + html.escape(e['duration']) if e['duration'] else ''}</li>"
        for e in shown)
    extra = f"<p><small>…dan {pl['count'] - 100} video lagi.</small></p>" if pl["count"] > 100 else ""
    return (f"<h2>{html.escape(pl['title'])}</h2>"
            f"<p><small>{html.escape(pl['uploader'])} · {pl['count']} video</small></p>"
            f"<ol>{rows}</ol>{extra}")


PAGE = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YouTube Audio Downloader</title>
<style>
body{font-family:system-ui,sans-serif;max-width:680px;margin:40px auto;padding:0 16px;color:#222}
input[type=text],button{font-size:16px;padding:10px;width:100%;box-sizing:border-box;margin:6px 0}
button.check{background:#c00;color:#fff;border:0;border-radius:8px;cursor:pointer}
button.check:hover{background:#a00}
label.pl{display:block;margin:4px 0;font-size:15px}
label.pl input{width:auto}
table{width:100%;border-collapse:collapse;margin:12px 0}
th,td{border:1px solid #ddd;padding:12px;text-align:left}
th{background:#f8f8f8}
button.dl{background:#4CAF50;color:#fff;border:0;border-radius:6px;padding:10px 18px;width:auto;cursor:pointer;white-space:nowrap}
button.dl:hover{background:#43A047}
.status{background:#f4f4f4;padding:12px;border-radius:8px;white-space:pre-wrap;word-break:break-word}
a{color:#c00} small{color:#666}
ol{padding-left:20px} ol li{margin:4px 0}
</style></head><body>
<h1>YouTube Audio Downloader</h1>
<p><small>1 video atau 1 playlist sekaligus. Tempel URL, klik Tampilkan Pilihan Kualitas, lalu klik Download di baris kualitas yang kamu mau.</small></p>
<form method="post" action="/check">
<input type="text" name="url" placeholder="https://www.youtube.com/watch?v=... atau .../playlist?list=..." value="__URL__" required>
<label class="pl"><input type="checkbox" name="playlist" value="1" __CHECKED__> Ini playlist — download semua video sekaligus</label>
<button type="submit" class="check">Tampilkan Pilihan Kualitas</button>
</form>
<p class="status">__STATUS__</p>
__CONTENT__
<h2>File yang sudah diunduh</h2>
__FILES__
<p><small>Gunakan hanya untuk konten milikmu sendiri, berlisensi bebas, atau yang kamu punya izin untuk mengunduhnya.</small></p>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/file/"):
            name = urllib.parse.unquote(self.path[len("/file/"):])
            path = os.path.join(DOWNLOADS, name)
            if not os.path.isfile(path) or os.path.dirname(os.path.abspath(path)) != os.path.abspath(DOWNLOADS):
                self.send_error(404); return
            data = open(path, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._send_page()

    def _send_page(self):
        files = []
        if os.path.isdir(DOWNLOADS):
            for f in sorted(os.listdir(DOWNLOADS)):
                if os.path.isfile(os.path.join(DOWNLOADS, f)):
                    q = urllib.parse.quote(f)
                    files.append(f'<li><a href="/file/{q}">{html.escape(f)}</a></li>')
        with lock:
            video, playlist, status = state["video"], state["playlist"], state["status"]
        content = ""
        if playlist:
            content = playlist_list(playlist) + quality_table(playlist["url"], playlist=True)
        elif video:
            best = video.get("best_abr")
            note = ""
            if best:
                note = (f"<p><small>Kualitas audio asli video ini sekitar <b>{best}kbps</b>. "
                        f"Pilih angka di atas itu tidak menambah kualitas suara, "
                        f"hanya memperbesar ukuran file.</small></p>")
            meta = html.escape(f"{video['uploader']} · {video['duration']}").strip(" ·")
            content = (f"<h2>{html.escape(video['title'])}</h2><p><small>{meta}</small></p>"
                       + quality_table(video["url"], fmt_note=note))
        body = PAGE.replace("__STATUS__", html.escape(status))
        body = body.replace("__URL__", html.escape((playlist or video or {}).get("url", ""), quote=True))
        body = body.replace("__CHECKED__", "checked" if playlist else "")
        body = body.replace("__CONTENT__", content)
        body = body.replace("__FILES__", "<ul>" + "".join(files) + "</ul>" if files else "<p>Belum ada file.</p>")
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        fields = urllib.parse.parse_qs(self.rfile.read(length).decode())
        url = fields.get("url", [""])[0].strip()
        if self.path == "/check":
            want_pl = fields.get("playlist", [""])[0] == "1" or is_playlist_url(url)
            if not url:
                set_status("URL kosong.")
            elif want_pl:
                set_status(f"Membaca playlist: {url} ...")
                pl, err = probe_playlist(url)
                with lock:
                    state["playlist"] = pl
                    state["video"] = None
                set_status(f"Playlist ditemukan: {pl['title']} ({pl['count']} video). Pilih kualitas di bawah — berlaku untuk semua video."
                           if pl else err)
            else:
                set_status(f"Membaca info video: {url} ...")
                video, err = probe_video(url)
                with lock:
                    state["video"] = video
                    state["playlist"] = None
                set_status(f"Pilih kualitas untuk: {video['title']}" if video else err)
        elif self.path == "/download":
            fmt = fields.get("format", ["mp3"])[0]
            quality = fields.get("quality", ["192"])[0]
            playlist = fields.get("playlist", [""])[0] == "1"
            with lock:
                count = state["playlist"]["count"] if (playlist and state["playlist"]) else None
            if not url:
                set_status("URL kosong.")
            elif fmt not in ("mp3", "m4a", "wav", "opus", "flac"):
                set_status("Format tidak dikenal.")
            elif quality not in QUALITIES + ["0"]:
                set_status("Kualitas tidak dikenal.")
            else:
                threading.Thread(target=run_download, args=(url, fmt, quality, playlist, count), daemon=True).start()
                label = f"{fmt.upper()} - {quality}kbps" if quality != "0" else f"{fmt.upper()} - Original"
                set_status(f"Memulai download {'playlist' if playlist else ''} {label} ..." if playlist
                           else f"Memulai download {label} ...")
        else:
            self.send_error(404); return
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    os.makedirs(DOWNLOADS, exist_ok=True)
    print(f"Buka http://localhost:{PORT} di browser")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
