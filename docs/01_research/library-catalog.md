# ライブラリ仕分け表（in App版）

仕分け係が管理します。ライセンス欄は初版（Claude作成）の暫定の記載です。仕分け係が公式情報で確かめたら「確認日」を入れてください。

| ライブラリ | 区分 | 用途 | ライセンス（暫定） | 確認日 | 備考 |
|---|---|---|---|---|---|
| yt-dlp | 採用中 | チャット・音声・映像の取得 | Unlicense | | YouTube側の変化で頻繁に更新される。YouTubeの取得には JavaScript ランタイム（Deno 推奨）が要る |
| imageio-ffmpeg | 採用中 | ffmpeg 本体の同梱 | 要確認（Python部分と同梱バイナリで異なる可能性） | | |
| numpy | 採用中 | 数値計算 | BSD-3-Clause | | |
| opencv-python-headless | 採用中 | 映像の縮小・テンプレート照合 | 要確認（OpenCV 本体は Apache-2.0） | | |
| rapidocr | 採用中 | 文字認識（RANKED MATCH の検知） | 要確認（Apache-2.0 と思われる） | | 初回にモデルをダウンロードする |
| onnxruntime | 採用中 | rapidocr の推論 | MIT | | Python の新しい版への対応時期に注意 |
| Tesseract | 代替 | 文字認識（rapidocr が無いとき） | Apache-2.0 | | 別途インストールが必要 |
| scipy | 開発用 | 合成配信の音声づくり（テスト） | BSD-3-Clause | | 無くても近似で動く |

## 研究の候補（未評価）
| ライブラリ | 期待する用途 |
|---|---|
| silero-vad | 「喋る量」の精度向上（音声区間検出） |
| faster-whisper | 配信者の「声のワード」（叫び・決め台詞）の検知 |
| librosa | 笑い声・歓声などの音響特徴 |
| PaddleOCR | 文字認識の精度比較 |
