# -*- coding: utf-8 -*-
"""チャットの読み込みと、区間ごとの集計"""
import json
import re
import unicodedata
from collections import Counter


def runs_to_text(msg):
    """本文を作る（共通指標仕様書 2.4）"""
    if not msg:
        return ""
    if msg.get("simpleText"):
        return msg["simpleText"]
    out = []
    for r in msg.get("runs", []):
        if r.get("text"):
            out.append(r["text"])
        elif "emoji" in r:
            e = r["emoji"]
            if e.get("isCustomEmoji") and e.get("shortcuts"):
                out.append(e["shortcuts"][0])
            else:
                out.append(e.get("emojiId", ""))
    return "".join(out)


KIND = {
    "liveChatTextMessageRenderer": "text",
    "liveChatPaidMessageRenderer": "money",
    "liveChatPaidStickerRenderer": "money",
    "liveChatMembershipItemRenderer": "member",
    "liveChatSponsorshipsGiftPurchaseAnnouncementRenderer": "member",
}


def parse_chat(path):
    """[(秒, 種類, 本文)]。種類: text / money / member（共通指標仕様書 2章）"""
    items, ids = [], set()
    if not path:
        return items
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            rep = obj.get("replayChatItemAction")
            if not rep:
                continue
            raw = rep.get("videoOffsetTimeMsec")
            if raw is None or raw == "":
                continue              # 時刻の無いアクションは捨てる
            try:
                ms = float(raw)
            except (TypeError, ValueError):
                continue
            if not (ms >= 0):         # 負・NaN を捨てる
                continue
            t = ms / 1000             # 丸めない
            for act in rep.get("actions", []):
                item = act.get("addChatItemAction", {}).get("item", {})
                for kind, r in item.items():
                    typ = KIND.get(kind)
                    if not typ:
                        continue
                    mid = r.get("id")
                    if mid:
                        if mid in ids:
                            continue
                        ids.add(mid)
                    text = "" if typ == "member" else runs_to_text(r.get("message"))
                    items.append((t, typ, text))
    items.sort(key=lambda x: x[0])
    return items


def normalize(text):
    s = unicodedata.normalize("NFKC", text).lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"(.)\1{3,}", r"\1\1\1", s)   # wwwww → www、88888 → 888
    return s[:30]


def chat_bins(items, nb, bin_sec, keywords):
    """区間ごとのコメント数・ワード・同一コメントなどを数える"""
    kw_re = {k: re.compile(v, re.IGNORECASE) for k, v in keywords.items()}
    count = [0] * nb
    money = [0] * nb
    kw_total = [0] * nb
    kw = [Counter() for _ in range(nb)]
    keys = [Counter() for _ in range(nb)]
    for t, typ, text in items:
        if not (t >= 0):          # 負の時刻は数えない（共通指標仕様書 3.2）
            continue
        b = min(nb - 1, int(t // bin_sec))
        if typ in ("money", "member"):
            money[b] += 1
        if typ == "member":
            continue
        count[b] += 1
        if not text:
            continue
        k = normalize(text)
        if k:
            keys[b][k] += 1
        hit = False
        for name, rx in kw_re.items():
            if rx.search(text):
                kw[b][name] += 1
                hit = True
        if hit:
            kw_total[b] += 1

    # 同じコメントが流れる確率：その区間で一番多いコメントが全体に占める割合
    same_rate = []
    for i in range(nb):
        top = keys[i].most_common(1)
        c = top[0][1] if top else 0
        same_rate.append(c / count[i] if count[i] >= 5 and c >= 3 else 0.0)

    return {
        "count": count, "money": money, "kw_total": kw_total,
        "kw": kw, "keys": keys, "same_rate": same_rate,
    }
