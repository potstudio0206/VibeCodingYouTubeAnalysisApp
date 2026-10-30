# -*- coding: utf-8 -*-
"""テストから app/ と shared/ を読み込めるようにする（各テストの先頭で import する）"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
SHARED = os.path.join(ROOT, "shared")
if APP not in sys.path:
    sys.path.insert(0, APP)
