# -*- coding: utf-8 -*-
"""音声（声の大きさ・喋る量）と画面（RANKED MATCH の検知）の解析"""
import difflib
import os
import re
import shutil
import subprocess
import sys
import time

import numpy as np

from hl_fetch import ffmpeg_exe

POPEN_FLAGS = 0x08000000 if sys.platform == "win32" else 0   # Windowsで黒い窓を増やさない


class Progress:
    def __init__(self, label, total):
        self.label, self.total = label, max(1e-9, total)
        self.t0 = time.time()
        self.last = -1

    def update(self, done):
        pct = int(min(100, done / self.total * 100))
        if pct // 5 != self.last // 5:
            self.last = pct
            el = time.time() - self.t0
            eta = el / max(pct, 1) * (100 - pct)
            sys.stdout.write(f"\r  {self.label} {pct:3d}%  （残り約{int(eta // 60)}分{int(eta % 60):02d}秒）   ")
            sys.stdout.flush()

    def done(self):
        sys.stdout.write(f"\r  {self.label} 100%  （{int(time.time() - self.t0)}秒）                \n")
        sys.stdout.flush()


# ============================================================ 音声
SR = 16000
FRAME = 512                 # 32ms
SPEECH_LO, SPEECH_HI = 300, 3400


def analyze_audio(path, duration):
    """1秒ごとの 音量(dB) と 喋っている割合(0〜1) を返す"""
    ff = ffmpeg_exe()
    proc = subprocess.Popen(
        [ff, "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        stdout=subprocess.PIPE, creationflags=POPEN_FLAGS)
    freqs = np.fft.rfftfreq(FRAME, 1 / SR)
    band = (freqs >= SPEECH_LO) & (freqs <= SPEECH_HI)
    flat_band = (freqs >= 100) & (freqs <= 4000)
    win = np.hanning(FRAME).astype(np.float32)

    pows, ratios, flats = [], [], []
    chunk = SR * 60 * 2          # 60秒ずつ
    rest = b""
    prog = Progress("音声を解析中", duration or 1)
    read_sec = 0.0
    while True:
        buf = proc.stdout.read(chunk)
        if not buf:
            break
        buf = rest + buf
        n = len(buf) // (FRAME * 2)
        rest = buf[n * FRAME * 2:]
        if n == 0:
            continue
        x = np.frombuffer(buf[:n * FRAME * 2], dtype=np.int16).astype(np.float32) / 32768.0
        fr = x.reshape(n, FRAME)
        pows.append(np.mean(fr * fr, axis=1))
        spec = np.abs(np.fft.rfft(fr * win, axis=1)) ** 2 + 1e-12
        ratios.append(spec[:, band].sum(1) / spec.sum(1))
        sb = spec[:, flat_band]
        flats.append(np.exp(np.mean(np.log(sb), axis=1)) / np.mean(sb, axis=1))
        read_sec += n * FRAME / SR
        prog.update(read_sec)
    proc.wait()
    prog.done()
    if not pows:
        return None

    power = np.concatenate(pows)
    db = 10 * np.log10(power + 1e-10)
    ratio = np.concatenate(ratios)
    flat = np.concatenate(flats)
    t = np.arange(len(db)) * FRAME / SR

    # 静かな時の音量（ノイズの床）を30秒ごとに求め、前後5分でならす
    w30 = (t // 30).astype(int)
    nw = int(w30.max()) + 1
    floor = np.array([np.percentile(db[w30 == k], 10) if (w30 == k).any() else np.nan for k in range(nw)])
    fl = np.copy(floor)
    for k in range(nw):
        w = floor[max(0, k - 10):k + 11]
        w = w[~np.isnan(w)]
        fl[k] = np.median(w) if len(w) else -90
    floor_f = fl[w30]

    # 喋っている判定：
    #  ・静かな時より十分大きい ・声の帯域の音がある ・雑音っぽくない
    #  ・0.5秒の中で音量が細かく揺れている（音節の強弱。BGMのような一定の音を除く）
    dbc = np.maximum(db, floor_f)
    k = 15
    ker = np.ones(k) / k
    m1 = np.convolve(dbc, ker, mode="same")
    m2 = np.convolve(dbc * dbc, ker, mode="same")
    mod = np.sqrt(np.maximum(0, m2 - m1 * m1))
    raw = (db > floor_f + 6) & (ratio > 0.4) & (flat < 0.4) & (db > -55) & (mod > 4)
    k = 7
    speech = np.convolve(raw.astype(np.float32), np.ones(k) / k, mode="same") > 0.4

    sec = t.astype(int)
    ns = int(sec.max()) + 1
    cnt = np.bincount(sec, minlength=ns)
    p_sum = np.bincount(sec, weights=power, minlength=ns)
    s_sum = np.bincount(sec, weights=speech.astype(np.float64), minlength=ns)
    ok = cnt > 0
    sec_db = np.where(ok, 10 * np.log10(p_sum / np.maximum(cnt, 1) + 1e-10), -100)
    sec_talk = np.where(ok, s_sum / np.maximum(cnt, 1), 0)
    return {"sec_db": [round(float(v), 2) for v in sec_db],
            "sec_talk": [round(float(v), 3) for v in sec_talk]}


def audio_bins(a, nb, bin_sec):
    """1秒ごとの値を、集計区間ごとにまとめる"""
    db = np.asarray(a["sec_db"], dtype=float)
    tk = np.asarray(a["sec_talk"], dtype=float)
    loud, talk = [], []
    for b in range(nb):
        s, e = int(b * bin_sec), int((b + 1) * bin_sec)
        d = db[s:e]
        d = d[d > -99]
        loud.append(round(float(np.percentile(d, 90)), 2) if len(d) else None)   # 区間の大きい方の音量（叫びを拾う）
        sl = tk[s:e]
        talk.append(round(float(sl.mean()), 3) if len(sl) else None)
    return {"loud": loud, "talk": talk}


# ============================================================ 画面（文字検知）
W, H = 640, 360


def _norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def _quiet_rapidocr():
    """文字が映っていない画面のたびに出る「The text detection result is empty」などのお知らせを止める。
    RapidOCRは読み込み・起動時に表示レベルを設定し直すので、起動の後に呼ぶ"""
    import logging
    for name in ("RapidOCR", "rapidocr", "RapidOCR_ONNXRuntime"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.ERROR)
        for h in lg.handlers:
            h.setLevel(logging.ERROR)


class OCR:
    """RapidOCR（pipで入る）→ Tesseract（入っていれば）の順に使う"""

    def __init__(self):
        self.kind = None
        try:
            from rapidocr import RapidOCR
            self.eng = RapidOCR()
            self.kind = "rapidocr"
            _quiet_rapidocr()
            return
        except Exception:
            pass
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.eng = RapidOCR()
            self.kind = "rapidocr_old"
            _quiet_rapidocr()
            return
        except Exception:
            pass
        tess = shutil.which("tesseract")
        if not tess and sys.platform == "win32":
            p = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            tess = p if os.path.exists(p) else None
        if tess:
            self.tess = tess
            self.kind = "tesseract"

    def read(self, gray):
        """[(文字列, (x0,y0,x1,y1))]"""
        import cv2
        out = []
        if self.kind == "rapidocr":
            r = self.eng(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), use_cls=False)
            txts = getattr(r, "txts", None) or ()
            boxes = getattr(r, "boxes", None)
            for i, s in enumerate(txts):
                b = np.asarray(boxes[i]) if boxes is not None else None
                if b is None:
                    continue
                out.append((s, (int(b[:, 0].min()), int(b[:, 1].min()), int(b[:, 0].max()), int(b[:, 1].max()))))
        elif self.kind == "rapidocr_old":
            res, _ = self.eng(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), use_cls=False)
            for box, s, _score in res or []:
                b = np.asarray(box)
                out.append((s, (int(b[:, 0].min()), int(b[:, 1].min()), int(b[:, 0].max()), int(b[:, 1].max()))))
        elif self.kind == "tesseract":
            ok, png = cv2.imencode(".png", gray)
            p = subprocess.run([self.tess, "stdin", "stdout", "--psm", "11", "tsv"],
                               input=png.tobytes(), capture_output=True, creationflags=POPEN_FLAGS)
            for line in p.stdout.decode("utf-8", "ignore").splitlines()[1:]:
                c = line.split("\t")
                if len(c) >= 12 and c[11].strip():
                    x, y, w, h = map(int, c[6:10])
                    out.append((c[11], (x, y, x + w, y + h)))
        return out


def find_text(ocr, gray, target):
    """画面内に target（例 RANKED MATCH）があれば、その位置を返す"""
    tn = _norm(target)
    words = [w for w in _norm(target.replace(" ", "|")).split("|") if w] or [tn]
    parts = target.upper().split()
    items = ocr.read(gray)
    if not items:
        return None
    # 1行で読めた場合
    for s, box in items:
        ns = _norm(s)
        if len(ns) >= len(tn) * 0.7 and difflib.SequenceMatcher(None, ns, tn).ratio() >= 0.8:
            return box
        if tn in ns:
            return box
    # 単語ごとにバラバラに読めた場合（近くにあれば合体）
    hits = []
    for p in parts:
        pn = _norm(p)
        best = None
        for s, box in items:
            if difflib.SequenceMatcher(None, _norm(s), pn).ratio() >= 0.8:
                best = box
                break
        if best is None:
            return None
        hits.append(best)
    x0 = min(b[0] for b in hits); y0 = min(b[1] for b in hits)
    x1 = max(b[2] for b in hits); y1 = max(b[3] for b in hits)
    if (y1 - y0) > 3 * max(b[3] - b[1] for b in hits) or (x1 - x0) > W * 0.9:
        return None
    return (x0, y0, x1, y1)


def crop_template(gray, box, pad=4):
    x0, y0, x1, y1 = box
    return gray[max(0, y0 - pad):min(H, y1 + pad), max(0, x0 - pad):min(W, x1 + pad)].copy(), \
        (max(0, x0 - pad), max(0, y0 - pad))


def load_template_from_screenshot(path, ocr, target):
    """ユーザーが置いたスクリーンショットから、文字の部分を切り出して手本にする"""
    import cv2
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
    if ocr.kind is None:
        return None
    box = find_text(ocr, img, target)
    if not box:
        return None
    return crop_template(img, box)


def detect_matches(path, duration, step, merge_sec, target, tool_dir, vdir):
    """画面に target が映った時刻のリストを返す"""
    import cv2
    ocr = OCR()
    learned = os.path.join(tool_dir, "templates", "learned_template.png")
    learned_pos = learned + ".pos"
    tmpl, pos, method = None, None, None

    # 1) ユーザーのスクリーンショット → 2) 前回学習した手本 → 3) 文字認識で探して学習
    for name in ("ranked_match.png", "ranked_match.jpg", "ranked_match.jpeg"):
        p = os.path.join(tool_dir, "templates", name)
        if os.path.exists(p):
            r = load_template_from_screenshot(p, ocr, target)
            if r:
                tmpl, pos = r
                method = "スクリーンショットの手本"
                break
            print(f"  ※ {name} から「{target}」の文字を見つけられませんでした。")
    if tmpl is None and os.path.exists(learned) and os.path.exists(learned_pos):
        tmpl = cv2.imdecode(np.fromfile(learned, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        with open(learned_pos) as f:
            pos = tuple(int(v) for v in f.read().split(","))
        method = "前回学習した手本"
    if tmpl is None and ocr.kind is None:
        print("  ※ 文字認識が使えないため、試合の区切りはスキップします（setup.bat を実行してください）。")
        return None
    print(f"  試合の検知方法：{method or '文字認識で探して手本を学習'}"
          + (f"（文字認識：{ocr.kind}）" if ocr.kind else ""))

    ff = ffmpeg_exe()
    proc = subprocess.Popen(
        [ff, "-v", "error", "-i", path, "-an",
         "-vf", f"fps={1 / step:.4f},scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
        stdout=subprocess.PIPE, creationflags=POPEN_FLAGS)
    size = W * H
    prog = Progress("画面を解析中", duration or 1)

    hits = []
    confirmed = method == "スクリーンショットの手本"
    prev_small = None
    ocr_until = -1          # この時刻まで続けて文字認識する（場面転換の直後）
    last_periodic = -1e9
    n_ocr = 0
    idx = 0
    margin = 40
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        t = idx * step
        idx += 1
        g = np.frombuffer(buf, dtype=np.uint8).reshape(H, W)
        small = cv2.resize(g, (160, 90), interpolation=cv2.INTER_AREA).astype(np.int16)
        changed = prev_small is not None and float(np.mean(np.abs(small - prev_small))) > 18
        prev_small = small

        hit = False
        if tmpl is not None:
            th, tw = tmpl.shape
            x0 = max(0, pos[0] - margin); y0 = max(0, pos[1] - margin)
            x1 = min(W, pos[0] + tw + margin); y1 = min(H, pos[1] + th + margin)
            region = g[y0:y1, x0:x1]
            if region.shape[0] >= th and region.shape[1] >= tw:
                score = float(cv2.matchTemplate(region, tmpl, cv2.TM_CCOEFF_NORMED).max())
                if score >= 0.80:
                    hit = True
                elif score >= 0.60 and ocr.kind and find_text(ocr, g, target):
                    hit = True
                    n_ocr += 1
            if hit:
                hits.append(t)
                confirmed = True
        # 手本がまだ無い／前回の手本がこの配信で通用するか未確認 → 文字認識でも探す
        if not hit and not confirmed and ocr.kind:
            if changed:
                ocr_until = t + 1.5
            periodic = t - last_periodic >= 15
            if t <= ocr_until or periodic:
                if periodic:
                    last_periodic = t
                n_ocr += 1
                box = find_text(ocr, g, target)
                if box:
                    hits.append(t)
                    confirmed = True
                    tmpl, pos = crop_template(g, box)
                    os.makedirs(os.path.dirname(learned), exist_ok=True)
                    cv2.imencode(".png", tmpl)[1].tofile(learned)
                    with open(learned_pos, "w") as f:
                        f.write(f"{pos[0]},{pos[1]}")
                    cv2.imencode(".png", g)[1].tofile(os.path.join(vdir, "match_detected_sample.png"))
                    sys.stdout.write(f"\r  {_fmt(t)} で「{target}」を見つけました。以降は手本との照合で高速に探します。\n")
        prog.update(t)
    proc.wait()
    prog.done()

    events = []
    for t in hits:
        if not events or t - events[-1][-1] > merge_sec:
            events.append([t, t])
        else:
            events[-1][-1] = t
    return {"events": [round(e[0], 1) for e in events], "ocr_frames": n_ocr,
            "learned": tmpl is not None}


def _fmt(sec):
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"
