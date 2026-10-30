# -*- coding: utf-8 -*-
"""指標の合成・パートと試合の区切り・見どころの選出"""
import bisect
import math
import statistics
from collections import Counter


def rolling_median(vals, half=10):
    out = []
    n = len(vals)
    for i in range(n):
        w = [v for v in vals[max(0, i - half):min(n, i + half + 1)] if v is not None]
        out.append(statistics.median(w) if w else 0.0)
    return out


def pct_rank(vals):
    s = sorted(vals)
    n = len(s)
    if n <= 1:
        return [0.0] * n
    return [bisect.bisect_left(s, v) / (n - 1) for v in vals]


def fmt(sec):
    sec = max(0, int(sec))
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


# ------------------------------------------------------------ 区切り
def build_segments(events, duration):
    """RANKED MATCH の時刻から、序盤／後半 と 試合ごとの区間を作る"""
    if not events:
        return [], []
    starts = sorted(events)
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    med = statistics.median(gaps) if gaps else 300
    cap = max(2 * med, 360)     # 1試合の最大長（次の試合まで長く空いたら、試合外として切る）
    matches = []
    for i, s in enumerate(starts):
        nxt = starts[i + 1] if i + 1 < len(starts) else duration
        matches.append({"no": i + 1, "start": s, "end": min(nxt, s + cap, duration)})
    phases = []
    if starts[0] > 30:
        phases.append({"key": "practice", "name": "序盤（雑談・練習）", "start": 0, "end": starts[0]})
    phases.append({"key": "ranked", "name": "後半（実践）", "start": starts[0], "end": duration})
    return phases, matches


def locate(t, phases, matches):
    ph = next((p["key"] for p in phases if p["start"] <= t < p["end"]), None)
    mt = next((m["no"] for m in matches if m["start"] <= t < m["end"]), None)
    return ph, mt


# ------------------------------------------------------------ 合成
def analyze(cfg, info, chat, audio, matches_events, duration):
    BIN = cfg.BIN_SEC
    nb = max(1, math.ceil(duration / BIN))
    has_chat = chat is not None and sum(chat["count"]) > 0
    has_audio = audio is not None
    hm = info.get("heatmap") or []

    count = chat["count"] if has_chat else [0] * nb
    money = chat["money"] if has_chat else [0] * nb
    kw_total = chat["kw_total"] if has_chat else [0] * nb
    same_rate = chat["same_rate"] if has_chat else [0.0] * nb

    base = [max(1.0, v) for v in rolling_median(count)]
    kw_base = [max(1.0, v) for v in rolling_median(kw_total)]
    speed = [c / b for c, b in zip(count, base)]
    # 加速度：前の区間からのコメント数の増え方（平常時の量で割って、配信ごとの差をならす）
    accel = [0.0] + [(count[i] - count[i - 1]) / base[i] for i in range(1, nb)]
    kwr = [k / b for k, b in zip(kw_total, kw_base)]

    heat = [0.0] * nb
    if hm:
        starts = [h.get("start_time", 0) for h in hm]
        for i in range(nb):
            j = bisect.bisect_right(starts, (i + 0.5) * BIN) - 1
            if 0 <= j < len(hm):
                heat[i] = float(hm[j].get("value") or 0)

    loud = audio["loud"] if has_audio else [None] * nb
    talk = audio["talk"] if has_audio else [None] * nb
    loud_f = [v if v is not None else -90.0 for v in loud]
    loud_base = rolling_median(loud_f)
    loud_rel = [v - b for v, b in zip(loud_f, loud_base)]

    # 使える指標だけで重みを配分しなおす
    avail = {
        "speed": has_chat, "accel": has_chat, "same": has_chat, "keyword": has_chat,
        "money": has_chat, "heat": bool(hm), "loud": has_audio,
    }
    w = {k: v for k, v in cfg.WEIGHTS.items() if avail.get(k)}
    tot = sum(w.values()) or 1
    w = {k: v / tot for k, v in w.items()}
    ranks = {
        "speed": pct_rank(speed), "accel": pct_rank([max(0, a) for a in accel]),
        "same": pct_rank(same_rate), "keyword": pct_rank(kwr), "money": pct_rank(money),
        "loud": pct_rank(loud_rel),
    }
    score = []
    for i in range(nb):
        s = 0.0
        for k, wk in w.items():
            if k == "heat":
                s += wk * heat[i]
            elif k == "money":
                s += wk * (ranks["money"][i] if money[i] else 0)
            else:
                s += wk * ranks[k][i]
        if has_chat and count[i] == 0 and not has_audio:
            s *= 0.2
        score.append(round(s * 100, 1))

    events = (matches_events or {}).get("events") or []
    phases, matches = build_segments(events, duration)

    # ---------------- 見どころ選出
    gap_bins = max(1, int(cfg.MIN_GAP_SEC // BIN))
    order = sorted(range(nb), key=lambda i: score[i], reverse=True)
    same_base = rolling_median(same_rate)
    picked = []
    for i in order:
        if len(picked) >= cfg.TOP_N:
            break
        spiky = (speed[i] >= cfg.MIN_SPEED
                 or (kwr[i] >= 3.0 and kw_total[i] >= 10)
                 or (same_rate[i] >= max(0.35, 1.8 * same_base[i]) and count[i] >= 10)
                 or money[i] >= 3 or heat[i] >= 0.6
                 or (has_audio and loud_rel[i] >= 6))
        if spiky and all(abs(i - p) > gap_bins for p in picked):
            picked.append(i)

    highlights = []
    for i in picked:
        l = r = i
        while l - 1 >= 0 and i - (l - 1) <= 2 and score[l - 1] >= score[i] * 0.85:
            l -= 1
        while r + 1 < nb and (r + 1) - i <= 2 and score[r + 1] >= score[i] * 0.85:
            r += 1
        reasons = []
        if has_chat:
            reasons.append(f"コメント速度 平常の{speed[i]:.1f}倍（{count[i]}件/{BIN}秒）")
            if accel[i] >= 1.0:
                reasons.append(f"コメント急増（直前より+{count[i] - count[i - 1] if i else count[i]}件）")
            if same_rate[i] >= 0.35:
                reasons.append(f"同じコメントが{same_rate[i] * 100:.0f}%")
            tot_kw = Counter()
            for b in range(l, r + 1):
                tot_kw.update(chat["kw"][b])
            if tot_kw:
                name, n = tot_kw.most_common(1)[0]
                reasons.append(f"{name}系ワード {n}件")
            if money[i]:
                reasons.append(f"スパチャ・メンバー {money[i]}件")
        if has_audio and loud_rel[i] >= 4:
            reasons.append(f"声が大きくなった（平常より+{loud_rel[i]:.0f}dB）")
        if heat[i] >= 0.6:
            reasons.append("よく見返されている区間")
        top = []
        if has_chat:
            tk = Counter()
            for b in range(l, r + 1):
                tk.update(chat["keys"][b])
            top = [(k, n) for k, n in tk.most_common(4) if n >= 3]
        peak = (i + 0.5) * BIN
        ph, mt = locate(peak, phases, matches)
        highlights.append({
            "rank": len(highlights) + 1,
            "start": max(0, l * BIN - cfg.LEAD_SEC), "end": (r + 1) * BIN, "peak": peak,
            "score": score[i], "reasons": reasons, "top": top, "phase": ph, "match": mt,
        })

    # ---------------- 区間ごとの集計（パート比較・試合ごと）
    def stats(start, end):
        bs = [i for i in range(nb) if start <= (i + 0.5) * BIN < end]
        if not bs:
            return None
        mins = max(1e-9, (end - start) / 60)
        c = sum(count[i] for i in bs)
        same_w = sum(same_rate[i] * count[i] for i in bs) / c if c else 0
        lv = [loud[i] for i in bs if loud[i] is not None]
        tv = [talk[i] for i in bs if talk[i] is not None]
        kwc = Counter()
        if has_chat:
            for i in bs:
                kwc.update(chat["kw"][i])
        hs = [h for h in highlights if start <= h["peak"] < end]
        return {
            "start": start, "end": end, "minutes": round(mins, 1),
            "cpm": round(c / mins, 1) if has_chat else None,
            "accel_max": round(max(accel[i] for i in bs), 2) if has_chat else None,
            "same": round(same_w * 100, 1) if has_chat else None,
            "loud": round(statistics.mean(lv), 1) if lv else None,
            "talk": round(statistics.mean(tv) * 100, 1) if tv else None,
            "score_max": max(score[i] for i in bs),
            "score_avg": round(statistics.mean(score[i] for i in bs), 1),
            "kw_top": kwc.most_common(1)[0][0] if kwc else None,
            "highlights": len(hs),
            "best": max(hs, key=lambda h: h["score"])["start"] if hs else None,
        }

    for p in phases:
        p["stats"] = stats(p["start"], p["end"])
    for m in matches:
        m["stats"] = stats(m["start"], m["end"])

    return {
        "bins": nb, "bin_sec": BIN, "duration": duration, "lead": cfg.LEAD_SEC,
        "series": {
            "count": count, "accel": [round(a, 3) for a in accel],
            "same": [round(s, 3) for s in same_rate],
            "loud": loud, "talk": talk, "score": score, "heat": heat if hm else None,
        },
        "has": {"chat": has_chat, "audio": has_audio, "heat": bool(hm), "video": matches_events is not None},
        "phases": phases, "matches": matches, "highlights": highlights,
        "total": sum(count), "ocr_frames": (matches_events or {}).get("ocr_frames"),
    }
