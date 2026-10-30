# -*- coding: utf-8 -*-
"""in App版の全工程テスト（重い）。合成配信を作り、highlight.py で最後まで解析して結果を確かめる。

文字認識（RapidOCR か Tesseract）と ffmpeg（imageio-ffmpeg）が必要。1〜3分かかる。
実行: RUN_SLOW=1 python -m unittest tests.test_e2e_synth -v   （Windows: set RUN_SLOW=1 の後に実行）
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

import _paths

SYNTH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "synth", "make_synth_stream.py")
VID = "SYNTHe2e001"
OUT = os.path.join(_paths.APP, "output", VID)
MATCHES = [600, 810, 1020, 1250, 1460, 1650]


def has_ocr():
    try:
        import rapidocr  # noqa: F401
        return True
    except Exception:
        pass
    return shutil.which("tesseract") is not None


@unittest.skipUnless(os.environ.get("RUN_SLOW") == "1", "重いテスト（RUN_SLOW=1 で実行）")
class EndToEndSynthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not has_ocr():
            raise unittest.SkipTest("文字認識（rapidocr か tesseract）がありません")
        shutil.rmtree(OUT, ignore_errors=True)
        subprocess.run([sys.executable, SYNTH, OUT], check=True)
        # 前回学習した手本が残っていると「初回の学習」を確かめられないので、一時的に退避する
        cls.tmpl = os.path.join(_paths.APP, "templates", "learned_template.png")
        cls.backup = []
        for p in (cls.tmpl, cls.tmpl + ".pos"):
            if os.path.exists(p):
                os.replace(p, p + ".bak")
                cls.backup.append(p)
        r = subprocess.run([sys.executable, os.path.join(_paths.APP, "highlight.py"), VID, "--no-open"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        cls.log = r.stdout + r.stderr
        if r.returncode != 0:
            raise AssertionError("highlight.py が失敗しました:\n" + cls.log[-3000:])
        with open(os.path.join(OUT, "見どころレポート.html"), encoding="utf-8") as f:
            html = f.read()
        cls.data = json.loads(re.search(r"const D = (\{.*?\});\nconst \$", html, re.S).group(1))

    @classmethod
    def tearDownClass(cls):
        for p in (cls.tmpl, cls.tmpl + ".pos"):
            if os.path.exists(p):
                os.remove(p)
        for p in getattr(cls, "backup", []):
            os.replace(p + ".bak", p)
        shutil.rmtree(OUT, ignore_errors=True)

    def test_ranked_match_detection(self):
        starts = [m["start"] for m in self.data["matches"]]
        self.assertEqual(len(starts), len(MATCHES), self.log[-2000:])
        for got, exp in zip(starts, MATCHES):
            self.assertAlmostEqual(got, exp, delta=2)

    def test_phase_comparison(self):
        phases = {p["key"]: p["stats"] for p in self.data["phases"]}
        self.assertIn("practice", phases)
        self.assertIn("ranked", phases)
        self.assertGreater(phases["practice"]["talk"], phases["ranked"]["talk"] + 30, "序盤の方がよく喋るはず")
        self.assertGreater(phases["ranked"]["cpm"], phases["practice"]["cpm"])

    def test_highlights_in_matches(self):
        peaks = [h["peak"] for h in self.data["highlights"]]
        for t in (920, 1345, 1100):
            self.assertTrue(any(abs(p - t) <= 60 for p in peaks), f"{t}秒付近の見どころが無い: {peaks}")
        self.assertTrue(all(h["match"] for h in self.data["highlights"]), "合成配信の見どころは全て試合中のはず")


if __name__ == "__main__":
    unittest.main()
