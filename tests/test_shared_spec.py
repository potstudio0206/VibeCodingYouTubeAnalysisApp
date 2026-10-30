# -*- coding: utf-8 -*-
"""共通指標仕様書（shared/metrics-spec.md）への適合テスト。

基準データ shared/golden/*.json と、in App版の実装（hl_chat / hl_analyze）が一致することを確かめる。
in Chrome版にも同じ基準データを使う適合テストがあり、両版の値が揃うことを保証する。

実行: python -m unittest discover -s tests -v
"""
import json
import math
import os
import tempfile
import types
import unittest

import _paths  # noqa: F401  app/ を読み込めるようにする
import config
from hl_analyze import analyze
from hl_chat import chat_bins, parse_chat

GOLDEN = os.path.join(_paths.SHARED, "golden")
TOL = 0.0011


def load(name):
    with open(os.path.join(GOLDEN, name), encoding="utf-8") as f:
        return json.load(f)


def run_app_metrics(items, duration, bin_sec):
    """highlight.py と同じ手順で、in App版の指標を計算する"""
    items = [tuple(x) for x in items]
    cfg = types.SimpleNamespace(**{k: getattr(config, k) for k in dir(config) if k.isupper()})
    cfg.BIN_SEC = bin_sec
    d = duration or (items[-1][0] if items else 0)
    nb = max(1, math.ceil(d / bin_sec))
    chat = chat_bins(items, nb, bin_sec, cfg.KEYWORDS) if items else None
    res = analyze(cfg, {"duration": duration, "heatmap": []}, chat, None, None, d)
    s = res["series"]
    return res["bins"], s["count"], s["accel"], s["same"]


class SharedSpecTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parse = load("parse_cases.json")
        cls.metrics = load("metrics_cases.json")

    def test_golden_matches_spec_version(self):
        with open(os.path.join(_paths.SHARED, "VERSION"), encoding="utf-8") as f:
            version = f.read().strip()
        self.assertEqual(self.parse["spec_version"], version)
        self.assertEqual(self.metrics["spec_version"], version)

    def test_parse(self):
        for case in self.parse["cases"]:
            with self.subTest(case=case["name"]):
                with tempfile.TemporaryDirectory() as d:
                    path = os.path.join(d, "x.live_chat.json")
                    with open(path, "w", encoding="utf-8") as f:
                        for a in case["actions"]:
                            f.write(json.dumps(a, ensure_ascii=False) + "\n")
                    got = [list(x) for x in parse_chat(path)]
                self.assertEqual(got, case["expected"])

    def test_metrics(self):
        for case in self.metrics["cases"]:
            with self.subTest(case=case["name"]):
                exp = case["expected"]
                bins, count, accel, same = run_app_metrics(case["items"], case["duration"], case["bin_sec"])
                self.assertEqual(bins, exp["bins"])
                self.assertEqual(count, exp["count"])
                self.assertEqual(len(accel), len(exp["accel"]))
                self.assertEqual(len(same), len(exp["same_rate"]))
                for i, (a, b) in enumerate(zip(accel, exp["accel"])):
                    self.assertLessEqual(abs(a - b), TOL, f"accel[{i}] {a} != {b}")
                for i, (a, b) in enumerate(zip(same, exp["same_rate"])):
                    self.assertLessEqual(abs(a - b), TOL, f"same_rate[{i}] {a} != {b}")


if __name__ == "__main__":
    unittest.main()
