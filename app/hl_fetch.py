# -*- coding: utf-8 -*-
"""YouTubeからチャット・音声・映像を取得（取得済みなら再利用）"""
import glob
import json
import os
import re
import sys


def video_id_from_url(url):
    m = re.search(r"(?:v=|youtu\.be/|/live/|/shorts/|/embed/)([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
        return url.strip()
    return None


def ffmpeg_exe():
    """pipで入れた imageio-ffmpeg 同梱の ffmpeg を優先して使う"""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _ydl():
    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        print("yt-dlp が入っていません。先に setup.bat を実行してください。")
        sys.exit(1)


def _find(vdir, stem):
    hits = [p for p in glob.glob(os.path.join(vdir, stem + ".*"))
            if not p.endswith((".part", ".ytdl", ".json"))]
    return hits[0] if hits else None


def fetch_info_and_chat(url, outdir):
    vid = video_id_from_url(url)
    if vid:
        vdir = os.path.join(outdir, vid)
        chat = os.path.join(vdir, f"{vid}.live_chat.json")
        info_p = os.path.join(vdir, "info.json")
        if os.path.exists(chat) and os.path.exists(info_p):
            print("・チャット：取得済みのデータを再利用します")
            with open(info_p, encoding="utf-8") as f:
                return vdir, chat, json.load(f)

    yt_dlp = _ydl()
    tmp = os.path.join(outdir, vid or "_tmp")
    os.makedirs(tmp, exist_ok=True)
    opts = {
        "skip_download": True,
        "writesubtitles": True,
        "subtitleslangs": ["live_chat"],
        "outtmpl": os.path.join(tmp, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }
    print("・チャットを取得中…（5時間の配信だと数分かかります）")
    with yt_dlp.YoutubeDL(opts) as ydl:
        raw = ydl.extract_info(url, download=True)

    vid = raw.get("id") or vid
    vdir = os.path.join(outdir, vid)
    os.makedirs(vdir, exist_ok=True)
    if os.path.abspath(tmp) != os.path.abspath(vdir):
        for fn in os.listdir(tmp):
            os.replace(os.path.join(tmp, fn), os.path.join(vdir, fn))
    info = {
        "id": vid,
        "title": raw.get("title") or "",
        "channel": raw.get("channel") or raw.get("uploader") or "",
        "duration": raw.get("duration") or 0,
        "heatmap": raw.get("heatmap") or [],
    }
    with open(os.path.join(vdir, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False)
    chat = os.path.join(vdir, f"{vid}.live_chat.json")
    if not os.path.exists(chat):
        chat = None
        print("  チャットリプレイが見つかりませんでした（チャット無効・メンバー限定・アーカイブ処理中など）。")
        print("  音声と画面の解析だけ行います。")
    return vdir, chat, info


def download_media(vid, vdir, want_audio, want_video, height):
    """音声（低ビットレート）と映像（低画質・音声なし）を取得。戻り値: (audio_path, video_path)"""
    audio = _find(vdir, "audio") if want_audio else None
    video = _find(vdir, "video") if want_video else None
    need_a = want_audio and not audio
    need_v = want_video and not video
    if not (need_a or need_v):
        return audio, video

    yt_dlp = _ydl()
    url = f"https://www.youtube.com/watch?v={vid}"
    base = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": False,
        "concurrent_fragment_downloads": 4,
        "ffmpeg_location": ffmpeg_exe(),
        "retries": 10,
        "fragment_retries": 10,
    }
    if need_a:
        print("・音声をダウンロード中…（解析用の低音質。5時間で100MB前後）")
        o = dict(base, format="worstaudio[acodec!=none]/bestaudio",
                 outtmpl=os.path.join(vdir, "audio.%(ext)s"))
        try:
            with yt_dlp.YoutubeDL(o) as ydl:
                ydl.download([url])
            audio = _find(vdir, "audio")
        except Exception as e:
            print(f"  音声を取得できませんでした：{e}")
    if need_v:
        print(f"・映像をダウンロード中…（{height}pの低画質・音声なし。5時間で数百MB）")
        fmt = (f"bv*[height<={height}][vcodec^=avc1]/bv*[height<={height}]/"
               f"bv*[height<={max(height, 480)}]/wv*")
        o = dict(base, format=fmt, outtmpl=os.path.join(vdir, "video.%(ext)s"))
        try:
            with yt_dlp.YoutubeDL(o) as ydl:
                ydl.download([url])
            video = _find(vdir, "video")
        except Exception as e:
            print(f"  映像を取得できませんでした：{e}")
    return audio, video
