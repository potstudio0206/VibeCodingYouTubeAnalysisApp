# -*- coding: utf-8 -*-
"""合成配信（30分）を作る。in App版の全工程テストと、手元での動作確認に使う。

中身:
- 序盤 0:00〜10:00：雑談（声がよく出る）、5:00に紛らわしい「CASUAL MATCH」
- 後半 10:00〜30:00：試合6つ（各試合の前に「RANKED MATCH」が約2.5秒映る）、ゲーム音
- 叫び（15:15・22:20）、コメントの盛り上がり（15:20・18:20・22:25）、スパチャ集中（25:00）

使い方:
  python tests/synth/make_synth_stream.py <出力フォルダ>
出力フォルダ名が動画IDとして使われます（例 app/output/SYNTHtest01）。
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "app"))

DUR = 30 * 60
FPS = 4
W, H = 640, 360
SR = 16000
MATCHES = [600, 810, 1020, 1250, 1460, 1650]   # 試合開始（RANKED MATCH が映る時刻）
CASUAL = 300                                   # 紛らわしい表示
SHOUTS = [915, 1340]                           # 叫び
CHAT_EVENTS = [(920, "うおおおおお", 120), (1345, "草", 150), (1100, "888", 60)]
SUPERCHAT_AT = 1500


def ffmpeg():
    try:
        from hl_fetch import ffmpeg_exe
        return ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _resonate(x, fc, bw):
    """2次の共振（声のフォルマント）。scipy があれば使い、無ければ numpy で近似する"""
    r = np.exp(-np.pi * bw / SR)
    th = 2 * np.pi * fc / SR
    try:
        from scipy.signal import lfilter
        return lfilter([1 - r], [1, -2 * r * np.cos(th), r * r], x)
    except ImportError:
        n = np.arange(256)
        h = (1 - r) * r ** n * np.sin(th * (n + 1)) / np.sin(th)
        return np.convolve(x, h)[:len(x)]


def speech(rng, dur, f0=150, amp=0.25):
    m = int(dur * SR)
    tt = np.arange(m) / SR
    f = f0 * (1 + 0.15 * np.sin(2 * np.pi * 0.7 * tt)) * (1 + 0.03 * rng.standard_normal(m).cumsum() / np.sqrt(m))
    ph = np.cumsum(f / SR)
    pulse = (np.diff(np.floor(ph), prepend=0) > 0).astype(np.float32)
    y = pulse.astype(np.float64)
    for fc, bw in [(700, 110), (1200, 120), (2500, 200)]:
        y = y + _resonate(pulse, fc, bw)
    env = (0.5 + 0.5 * np.sin(2 * np.pi * 4 * tt)) ** 2     # 音節の強弱
    y = y * env
    return (y / (np.max(np.abs(y)) + 1e-9) * amp).astype(np.float32)


def make_video(out):
    import cv2

    def scene(seed, hud):
        r = np.random.default_rng(seed)
        img = np.zeros((H, W, 3), np.uint8)
        c1, c2 = r.integers(20, 200, 3), r.integers(20, 200, 3)
        for y in range(H):
            img[y] = (c1 + (c2 - c1) * y / H).astype(np.uint8)
        for _ in range(6):
            x, y = int(r.integers(0, W - 80)), int(r.integers(0, H - 80))
            cv2.rectangle(img, (x, y), (x + 60, y + 90), tuple(int(v) for v in r.integers(0, 255, 3)), -1)
        if hud:
            cv2.rectangle(img, (20, 20), (280, 36), (0, 200, 255), -1)
            cv2.rectangle(img, (360, 20), (620, 36), (0, 200, 255), -1)
            cv2.putText(img, "99", (300, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        return img

    def vs(title):
        img = np.full((H, W, 3), (40, 10, 60), np.uint8)
        cv2.rectangle(img, (0, 140), (W, 220), (90, 20, 120), -1)
        (tw, _), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_DUPLEX, 1.3, 2)
        cv2.putText(img, title, ((W - tw) // 2, 60), cv2.FONT_HERSHEY_DUPLEX, 1.3, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, "PLAYER_A", (40, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(img, "VS", (300, 190), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 220, 255), 3)
        cv2.putText(img, "PLAYER_B", (440, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        return img

    p = subprocess.Popen([ffmpeg(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                          os.path.join(out, "video.mp4")], stdin=subprocess.PIPE)
    key_prev, frame = None, None
    for f in range(DUR * FPS):
        t = f / FPS
        key = None
        for m in MATCHES:
            if m <= t < m + 2.5:
                key = ("vs", "RANKED MATCH")
        if CASUAL <= t < CASUAL + 2.5:
            key = ("vs", "CASUAL MATCH")
        if key is None:
            key = ("scene", int(t // 20), False) if t < MATCHES[0] else ("scene", int(t // 8), True)
        if key != key_prev:
            img = vs(key[1]) if key[0] == "vs" else scene(hash(key) % 10000, key[2])
            frame, key_prev = img.tobytes(), key
        p.stdin.write(frame)
    p.stdin.close()
    p.wait()


def make_audio(out, rng):
    n = DUR * SR
    t = np.arange(n) / SR
    audio = np.zeros(n, np.float32)
    pos = 0
    while pos < MATCHES[0] * SR:                     # 序盤：よく喋る
        d = rng.uniform(2, 6)
        seg = speech(rng, d, f0=rng.uniform(120, 200))
        s = int(pos)
        e = min(n, s + len(seg))
        audio[s:e] += seg[:e - s]
        pos += (d + rng.uniform(0.3, 1.5)) * SR
    bt = t[MATCHES[0] * SR:]                         # 後半：ゲーム音＋たまに喋る
    bgm = 0.04 * (np.sin(2 * np.pi * 220 * bt) + 0.5 * np.sin(2 * np.pi * 330 * bt)) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 2 * bt)))
    audio[MATCHES[0] * SR:] += bgm.astype(np.float32) + 0.01 * rng.standard_normal(len(bt)).astype(np.float32)
    pos = MATCHES[0] * SR
    while pos < n:
        d = rng.uniform(1, 3)
        seg = speech(rng, d, amp=0.15)
        s = int(pos)
        e = min(n, s + len(seg))
        audio[s:e] += seg[:e - s]
        pos += (d + rng.uniform(6, 15)) * SR
    for sh in SHOUTS:                                # 叫び
        seg = speech(rng, 6, f0=260, amp=0.9)
        audio[sh * SR:sh * SR + len(seg)] += seg
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes()
    subprocess.run([ffmpeg(), "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "aac", "-b:a", "48k", os.path.join(out, "audio.m4a")], input=pcm, check=True)


def make_chat(out, rng, vid):
    lines, mid = [], 0

    def add(tt, text, kind="liveChatTextMessageRenderer"):
        nonlocal mid
        mid += 1
        lines.append({"replayChatItemAction": {"actions": [{"addChatItemAction": {"item": {kind: {
            "id": f"m{mid}", "message": {"runs": [{"text": text}]}}}}}], "videoOffsetTimeMsec": str(int(tt * 1000))}})

    normal = ["こんばんは", "コンボ練習えらい", "それな", "わかる", "なるほど", "かわいい", "がんばれ", "ランクいこう"]
    for tt in np.arange(0, DUR, 4.0):
        add(tt + rng.random(), normal[rng.integers(len(normal))])
    for tt in np.arange(MATCHES[0], DUR, 6.0):
        add(tt + rng.random(), str(rng.choice(["ナイス", "いけ", "うまい", "おしい"])))
    for et, w, k in CHAT_EVENTS:
        for _ in range(k):
            add(et + rng.random() * 60, w)
    for _ in range(8):
        add(SUPERCHAT_AT + rng.random() * 30, "おめでとう", "liveChatPaidMessageRenderer")
    with open(os.path.join(out, f"{vid}.live_chat.json"), "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    with open(os.path.join(out, "info.json"), "w", encoding="utf-8") as f:
        json.dump({"id": vid, "title": "【合成テスト】コンボ練習→ランクマ", "channel": "テスト配信者",
                   "duration": DUR, "heatmap": []}, f, ensure_ascii=False)


def main(out):
    os.makedirs(out, exist_ok=True)
    vid = os.path.basename(os.path.normpath(out))
    rng = np.random.default_rng(3)
    make_video(out)
    make_audio(out, rng)
    make_chat(out, rng, vid)
    print("合成配信を作りました:", out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
