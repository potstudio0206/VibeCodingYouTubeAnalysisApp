# -*- coding: utf-8 -*-
"""
配信アーカイブ 解析ツール

YouTube配信アーカイブを解析して、見どころとパートの違いをレポートにします。
 ・チャット：コメント量、加速度、同じコメントが流れる確率、ワード、スパチャ
 ・音声　　：声の大きさ、喋る量
 ・画面　　：「RANKED MATCH」の文字を検知して、序盤（雑談・練習）／後半（実践）と試合ごとに区切る

使い方:  run.bat をダブルクリック → URLを貼り付けてEnter
設定:    config.py をメモ帳で開いて変更
"""
import argparse
import json
import math
import os
import sys
import time
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import config as cfg                      # noqa: E402
from hl_analyze import analyze, fmt       # noqa: E402
from hl_chat import chat_bins, parse_chat  # noqa: E402
from hl_fetch import download_media, fetch_info_and_chat  # noqa: E402
from hl_report import write_report        # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser(description="配信アーカイブの解析")
    ap.add_argument("url", nargs="?", help="YouTubeのURL")
    ap.add_argument("--chat-only", action="store_true", help="チャットだけ解析する（速い）")
    ap.add_argument("--redo-media", action="store_true", help="音声・画面の解析をやり直す")
    ap.add_argument("--no-open", action="store_true", help="終了後にブラウザを開かない")
    a = ap.parse_args()

    url = a.url or input("配信アーカイブのURLを貼り付けてEnter: ").strip()
    if not url:
        return
    t0 = time.time()
    outdir = os.path.join(HERE, "output")
    os.makedirs(outdir, exist_ok=True)

    print("\n[1/4] チャット")
    vdir, chat_path, info = fetch_info_and_chat(url, outdir)
    items = parse_chat(chat_path)
    duration = info.get("duration") or (items[-1][0] if items else 0)
    print(f"  コメント {sum(1 for i in items if i[1] != 'member'):,}件")

    want_audio = cfg.ANALYZE_AUDIO and not a.chat_only
    want_video = cfg.ANALYZE_VIDEO and not a.chat_only
    audio_p = os.path.join(vdir, "audio_metrics.json")
    match_p = os.path.join(vdir, "match_events.json")
    audio_m = None if a.redo_media else load_json(audio_p)
    match_m = None if a.redo_media else load_json(match_p)

    need_a = want_audio and audio_m is None
    need_v = want_video and match_m is None
    if want_audio or want_video:
        print("\n[2/4] 音声・映像の取得")
        if not (need_a or need_v):
            print("  解析済みの結果を再利用します")
        a_file = v_file = None
        if need_a or need_v:
            a_file, v_file = download_media(info["id"], vdir, need_a, need_v, cfg.VIDEO_HEIGHT)

        print("\n[3/4] 音声・画面の解析")
        from hl_media import analyze_audio, detect_matches
        if need_a and a_file:
            audio_m = analyze_audio(a_file, duration)
            if audio_m:
                save_json(audio_p, audio_m)
        if need_v and v_file:
            match_m = detect_matches(v_file, duration, cfg.VIDEO_STEP_SEC, cfg.MATCH_MERGE_SEC,
                                     cfg.MATCH_TEXT, HERE, vdir)
            if match_m is not None:
                save_json(match_p, match_m)
        if match_m is not None:
            ev = match_m.get("events") or []
            if ev:
                print(f"  「{cfg.MATCH_TEXT}」を {len(ev)}回 検知："
                      + "、".join(fmt(t) for t in ev[:8]) + ("…" if len(ev) > 8 else ""))
            else:
                print(f"  「{cfg.MATCH_TEXT}」は見つかりませんでした。")
        if not cfg.KEEP_MEDIA:
            for f in (a_file, v_file):
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except OSError:
                        pass

    print("\n[4/4] まとめ")
    nb = max(1, math.ceil(duration / cfg.BIN_SEC))
    chat = chat_bins(items, nb, cfg.BIN_SEC, cfg.KEYWORDS) if items else None
    audio = None
    if want_audio and audio_m:
        from hl_media import audio_bins
        audio = audio_bins(audio_m, nb, cfg.BIN_SEC)
    res = analyze(cfg, info, chat, audio, match_m if want_video else None, duration)
    path = write_report(res, info, vdir)

    print(f"\n完了（{int(time.time() - t0) // 60}分{int(time.time() - t0) % 60:02d}秒）")
    if res["matches"]:
        print(f"  序盤 0:00:00〜{fmt(res['matches'][0]['start'])}、試合 {len(res['matches'])}")
    print(f"  見どころ候補 {len(res['highlights'])}か所")
    print(f"  レポート: {path}")
    if not a.no_open:
        webbrowser.open("file:///" + path.replace("\\", "/"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n中止しました。")
