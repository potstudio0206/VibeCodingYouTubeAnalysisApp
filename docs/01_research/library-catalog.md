---
status: approved
writer: 仕分け係（app-research-triage）
approver: 研究課長（app-research-kacho）
updated: 2026-10-30
---

# ライブラリ仕分け表（in App版）

- 確認日はすべて 2026-10-30。出典は各行の表の下にまとめた（PyPI の JSON は `https://pypi.org/pypi/<名前>/json`、ページは `https://pypi.org/project/<名前>/`）。
- 「未確認」は、公式情報で確かめられなかったこと。推測で埋めていない。
- 「要注意」は、GPL・AGPL・商用制限・APIキー必須、またはそれに近いもの。社長判断の基準（CLAUDE.md 6章）に当たりうる。
- 区分の「（仮）」は仕分け係の仮付けで、研究課長の承認で確定する。
- 確認時点の手元の環境は Python 3.13（Windows 11）。手元に入っている版は下の表の「版」と同じ。

## 1. 要注意の一覧（先に読む）

| # | 対象 | 内容 | 影響 | 推奨 |
|---|---|---|---|---|
| A | imageio-ffmpeg 同梱の ffmpeg | **GPL ビルド**。手元の同梱 `ffmpeg-win-x86_64-v7.1.exe` を `-version` で確認：gyan.dev の essentials ビルドで、configuration に `--enable-gpl --enable-version3`（libx264・libx265 など）。LGPL ビルドではない。Python 部分（imageio-ffmpeg）は BSD-2-Clause だが、同梱バイナリは別ライセンス | 利用者が自分の PC に pip で入れて使う限りは配布していない。ffmpeg 同梱の形で配布する（exe 化、zip に同梱など）なら GPLv3 の条件（ソース提示など）が付く | 社長判断の対象。配布の予定が出た時点で、ffmpeg を利用者に別に入れてもらう形や LGPL ビルドへの切替を検討する。現状の「pip で入れる」運用は維持 |
| B | yt-dlp[default] の依存 `mutagen` | **GPL-2.0-or-later**（PyPI 1.48.1）。`default` extra で入る | pip で入れるだけなら配布ではない。配布物に同梱すると GPL が及ぶ | 配布の予定が出た時点で再確認 |
| C | yt-dlp の配布バイナリ | PyPI の wheel は Unlicense。ただし GitHub 公式の exe 版には GPLv3+ のコードが含まれると README に書かれている | 今は pip 版を使うので影響なし | exe 版は使わない |
| D | opencv-python-headless 同梱の FFmpeg | PyPI の説明に「全 wheel に LGPLv2.1 の FFmpeg を同梱」とある（バイナリ自体の検査は未実施） | LGPL。動的リンクで配布は可能だが、同梱時は表示義務など | 配布時に再確認 |
| E | scipy（開発用） | wheel に GCC ランタイム（GPL-3.0-or-later + ランタイム例外）と libquadmath（LGPL-2.1-or-later）を同梱と PyPI に記載 | 開発用のみで配布しないため影響なし | 開発用に限る |
| F | silero-vad | 公式 README のバッジが **CC BY-NC 4.0**（非商用）、サイドバー・PyPI・LICENSE ファイルは **MIT**。表示が食い違っている | 商用制限の疑いが完全には消えない | 採用前に作者へ確認するか、LICENSE（MIT）を根拠にするかを社長判断に上げる |
| G | rapidocr の一部モデルの取得先 | 既定のモデルは wheel に同梱だが、他のモデルは `modelscope.cn`（中国のサイト）から取得する設定（default_models.yaml） | 既定のままなら外部取得は起きないはず（実行は未確認）。他モデルを選ぶと外部取得が起きる | 既定モデルのみ使う。オフライン動作は実機で確認が必要（未確認） |
| H | python-bidi（rapidocr の `rtl` 拡張のみ） | LGPL。rapidocr 本体の既定では入らない | 影響なし | `rapidocr[rtl]` は使わない |

GPL・AGPL・商用制限・APIキー必須のうち、APIキー必須のものは今回の対象にはない。AGPL もなし。

## 2. 採用中

| ライブラリ | 版 | 区分 | 用途 | ライセンス（確認結果） | 最終リリース | Windows | サイズ（Windows の wheel） | 確認日 | 備考 |
|---|---|---|---|---|---|---|---|---|---|
| yt-dlp | 2026.10.26 | 採用中 | チャット・音声・映像の取得 | Unlicense（PyPI の license 欄）。要注意 B・C | 2026-10-26 | 可（OS Independent、Python 3.11 以上） | 3.2 MB（any） | 2026-10-30 | YouTube 側の変化で頻繁に更新される。YouTube の取得には JavaScript ランタイム（Deno 推奨）が要る。Deno 自体のライセンスは未確認 |
| imageio-ffmpeg | 0.7.0 | 採用中 | ffmpeg 本体の同梱 | Python 部分は BSD-2-Clause。**同梱 ffmpeg は GPLv3 ビルド（要注意 A）** | 2026-10-28 | 可（win_amd64 の wheel あり、Python 3.10 以上） | 31.2 MB（ffmpeg 込み。展開後は約 84 MB） | 2026-10-30 | 同梱は ffmpeg 7.1（gyan.dev essentials ビルド）。ffmpeg の入手元・ビルド設定は README に書かれておらず、手元の実行ファイルで確認した |
| numpy | 2.5.4 | 採用中 | 数値計算 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 2026-10-10 | 可（cp312〜 の win_amd64） | 約 12.6 MB | 2026-10-30 | Python 3.12 以上が必要 |
| opencv-python-headless | 5.0.0.93 | 採用中 | 映像の縮小・テンプレート照合 | Apache-2.0（PyPI の license 欄）。スクリプト部分は MIT。FFmpeg 同梱は LGPLv2.1（要注意 D） | 2026-07-02 | 可（win_amd64） | 43.8 MB（展開後は約 113 MB） | 2026-10-30 | |
| rapidocr | 3.10.0 | 採用中 | 文字認識（RANKED MATCH の検知） | Apache-2.0（PyPI）。モデルは PaddleOCR 由来で Apache-2.0 と GitHub の README に記載（個別の MODEL_LICENSES.md は未読） | 2026-10-08 | 可（README のバッジに Windows。手元で動作） | 27.3 MB（既定モデル 3 つ約 31 MB を同梱） | 2026-10-30 | 旧メモの「初回にモデルをダウンロードする」は要見直し：3.10.0 の wheel には既定モデル（PP-OCRv6 small 検出・認識、方向分類）が入っていた。ただし setup.bat は初回の取得を前提にしており、実行時にダウンロードが起きるかは未確認。要注意 G |
| onnxruntime | 1.31.1 | 採用中 | rapidocr の推論 | MIT License | 2026-10-26 | 可（cp311〜cp314 の win_amd64） | 14.9〜15.3 MB | 2026-10-30 | Python 3.11 以上。新しい Python への対応時期に注意（3.14 までの wheel は確認、3.15 は無し） |

## 3. 代替・開発用

| ライブラリ | 区分 | 用途 | ライセンス（確認結果） | 最終リリース | Windows | サイズ | 確認日 | 備考 |
|---|---|---|---|---|---|---|---|---|
| Tesseract | 代替 | 文字認識（rapidocr が無いとき） | Apache-2.0（GitHub の README。依存の Leptonica は BSD-2-Clause） | 未確認（README は 5 系が安定版とのみ記載） | Windows 用の公式配布元は未確認（app/hl_media.py は `C:\Program Files\Tesseract-OCR\tesseract.exe` を探す） | 未確認 | 2026-10-30 | 別途インストールが必要 |
| scipy | 開発用 | 合成配信の音声づくり（テスト） | BSD 系（Enthought・SciPy Developers の文面）。GCC ランタイム・libquadmath を同梱（要注意 E） | 1.18.1：2026-08-21 | 可（cp312〜 の win_amd64） | 約 36.7 MB | 2026-10-30 | 無くても近似で動く。Python 3.12 以上 |

## 4. 候補（仮付けの区分つき）

| ライブラリ | 区分（仮） | 期待する用途 | ライセンス | 最終リリース | Windows | 配布サイズ | オフライン | 確認日 | 判断の理由 |
|---|---|---|---|---|---|---|---|---|---|
| silero-vad 6.2.3 | 候補（要注意 F） | 「喋る量」の精度向上（音声区間検出） | MIT（PyPI の分類・LICENSE ファイル）だが README のバッジは CC BY-NC 4.0 | 2026-09-23 | OS Independent。torch の Windows wheel は取得可（cp312 で約 126.7 MB） | モデル約 2 MB（README）。ただし本体が **torch 必須**で、実行環境が約 130 MB 以上増える。onnx 版は拡張だが torch も入る（依存の記載より） | 作者は「テレメトリなし・キー・登録なし」と記載。オフライン動作自体の記載は未確認 | 2026-10-30 | 精度向上の見込みはあるが、torch が重い。ライセンス表示の食い違いを先に解消したい。試作は研究課の融合開発係の範囲で、本体への採用は社長判断 |
| faster-whisper 1.2.1 | 候補 | 配信者の「声のワード」（叫び・決め台詞）の検知 | MIT（PyPI・GitHub）。依存の ctranslate2 4.8.4 も MIT。モデル重みのライセンスは未確認 | 2025-10-31（約1年前。更新は止まり気味） | Python 3.9 以上で可。CPU（int8）は可。GPU は CUDA 12・cuDNN 9 が別途必要で、README の pip 手順は Linux のみ | 本体 1.1 MB だが依存が大きい（ctranslate2 20.4 MB、av 28.2 MB、onnxruntime 14.9 MB など）。モデルは別途ダウンロード（サイズは README に無く未確認） | モデルは初回に Hugging Face から取得。ローカルフォルダ指定で動くと思われる（README の記載からの推測で、未確認） | 2026-10-30 | 試す価値は高いが、モデルの取得と実行時間（長時間配信）が課題。実際の速度は未計測 |
| librosa 1.0.0 | 候補（優先度低） | 笑い声・歓声などの音響特徴 | ISC | 2026-08-11 | Python 3.12 以上。Windows の記載は README に無く未確認（依存は soundfile・numba などで、numba の win_amd64 wheel は取得可） | 本体 0.3 MB。依存が多い（numba、scikit-learn、scipy、soundfile、soxr など） | ローカル計算のみ。pooch は例データ用で取得が起きうる（未確認） | 2026-10-30 | 依存が多く、numpy/scipy で自作できる範囲もある。まず必要な特徴を絞ってから判断 |
| PaddleOCR 3.7.0 | 見送り（仮） | 文字認識の精度比較 | Apache-2.0 | 2026-06-11 | 可（README のバッジ・3.2.0 の記載） | paddlepaddle 本体が別に要る可能性が高い（Windows の wheel は約 104.8 MB）。paddleocr の依存に paddlepaddle が含まれるかは未確認 | モデルは ModelScope・AIStudio・Hugging Face から選んで取得。オフラインの手順は未確認 | 2026-10-30 | rapidocr が同じ PaddleOCR 系のモデルを onnxruntime で動かしており、重いフレームワークを足す利点が薄い。精度比較をしたい場合のみ研究課の試作で |

## 5. 禁止

今のところ該当なし。次の条件のものは「禁止」とし、使う前に社長判断に上げる（CLAUDE.md 6章）。
- ライセンスが GPL・AGPL・商用制限のもの（配布物に取り込む場合）
- API キーや有料契約が必要なもの
- インターネットに画面・音声・コメントを送るもの

## 6. 出典
- yt-dlp：https://pypi.org/pypi/yt-dlp/json ／ https://pypi.org/project/yt-dlp/（README に Unlicense・exe 版の GPLv3+ の記載）。依存の mutagen：https://pypi.org/pypi/mutagen/json
- imageio-ffmpeg：https://pypi.org/pypi/imageio-ffmpeg/json ／ https://github.com/imageio/imageio-ffmpeg（README・LICENSE は BSD-2-Clause）／ 同梱バイナリの一覧：https://github.com/imageio/imageio-binaries/tree/master/ffmpeg。GPL ビルドの根拠は、手元の同梱 ffmpeg の `-version` 出力
- numpy：https://pypi.org/pypi/numpy/json
- opencv-python-headless：https://pypi.org/pypi/opencv-python-headless/json
- rapidocr：https://pypi.org/pypi/rapidocr/json ／ https://github.com/RapidAI/RapidOCR ／ 手元の rapidocr/default_models.yaml
- onnxruntime：https://pypi.org/pypi/onnxruntime/json
- scipy：https://pypi.org/pypi/scipy/json
- Tesseract：https://github.com/tesseract-ocr/tesseract
- silero-vad：https://pypi.org/pypi/silero-vad/json ／ https://github.com/snakers4/silero-vad ／ https://raw.githubusercontent.com/snakers4/silero-vad/master/LICENSE（MIT License）／ torch：https://pypi.org/pypi/torch/json
- faster-whisper：https://pypi.org/pypi/faster-whisper/json ／ https://github.com/SYSTRAN/faster-whisper ／ ctranslate2：https://pypi.org/pypi/ctranslate2/json ／ av：https://pypi.org/pypi/av/json
- librosa：https://pypi.org/pypi/librosa/json ／ https://github.com/librosa/librosa ／ numba：https://pypi.org/pypi/numba/json
- PaddleOCR：https://pypi.org/pypi/paddleocr/json ／ https://github.com/PaddlePaddle/PaddleOCR ／ paddlepaddle：https://pypi.org/pypi/paddlepaddle/json
