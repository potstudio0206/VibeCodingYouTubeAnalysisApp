---
id: SPEC-CURRENT
title: 現状仕様書（in App版）
status: draft          # 初版（Claude作成）。現状仕様係がコードと突き合わせて確定する
author: app-req-spec
reviewer:
updated: 2026-10-30
---
# 現状仕様書（in App版）

## 1. 概要
YouTube配信アーカイブのURLを渡すと、チャット・音声・映像を解析し、見どころ候補と、序盤（雑談・練習）と後半（実践）の違い、試合ごとの盛り上がりを、HTMLのレポートにまとめる Windows 向けのPCツール。

## 2. 使い方
- 初回：`app/setup.bat`（Python ライブラリ、Deno、文字認識モデル）
- 毎回：`app/run.bat` → URL を貼り付け → 完了すると Chrome でレポートが開く
- チャットだけ：`app/run_chat_only.bat`
- コマンド：`python app/highlight.py <URL または 動画ID> [--chat-only] [--redo-media] [--no-open]`

## 3. 処理の流れ
1. チャット：yt-dlp でチャットリプレイを取得（取得済みなら再利用）。動画情報（タイトル、長さ、よく再生されている部分）も保存する。
2. 音声・映像の取得：低音質の音声と、低画質（既定360p）・音声なしの映像。
3. 解析
   - 音声：1秒ごとの音量と、喋っている割合（音量・声の帯域・音量の揺れ・雑音らしさから推定）
   - 画面：「RANKED MATCH」の検知（初回は文字認識で探し、見つけた見た目を手本として学習し、以降は手本と照合）
4. まとめ：区間（既定30秒）ごとに指標を計算し、盛り上がりスコア・見どころ・パート・試合を決めて、レポートを出す。

## 4. 指標
| 指標 | 定義 |
|---|---|
| コメント量・加速度・同じコメントの流れる確率 | 共通指標仕様（shared/metrics-spec.md） |
| キーワード | config.py の KEYWORDS（笑い・驚き・称賛・かわいい・悲鳴）に一致したコメントの数 |
| スパチャ・メンバー | money・member の件数 |
| よく再生されている部分 | YouTube のヒートマップ（取得できた動画のみ） |
| 声の大きさ | 区間内の1秒ごとの音量（dB）の90パーセンタイル |
| 喋る量 | 区間内で喋っていると推定された時間の割合 |
| 盛り上がりスコア | 各指標の順位（0〜1）を WEIGHTS で重み付けして合計した値（0〜100）。取得できなかった指標の重みは、他の指標に配り直す |

## 5. 見どころの選び方
- スコアの高い区間から順に、MIN_GAP_SEC 以上離れたものを TOP_N 件まで選ぶ。
- ただし、次のどれかを満たす区間に限る：コメント速度が平常の MIN_SPEED 倍以上／キーワードの急増／同じコメントの急増／スパチャ・メンバー3件以上／よく再生されている（0.6以上）／声が平常より6dB以上大きい。
- 確認開始の時刻は、区間の LEAD_SEC 秒前。

## 6. パートと試合
- 最初の「RANKED MATCH」までを序盤（雑談・練習）、それ以降を後半（実践）とする。
- 試合は「RANKED MATCH」が映った時刻から、次に映るまで（MATCH_MERGE_SEC 以内の連続検知は1回とみなす。次の試合まで長く空いたときは、試合の長さに上限を設ける）。
- レポートに、序盤と後半の比較表と、試合ごとの一覧を出す。「RANKED MATCH」が見つからない配信では、パートと試合の区切りは出さない。

## 7. 出力（app/output/<動画ID>/）
- 見どころレポート.html：比較表、タイムライン（ヒートマップ／折れ線、表示範囲の切り替え、クリックでYouTubeを開く）、試合ごとの表、見どころ候補（序盤／後半の絞り込み）
- 見どころメモ.txt
- 再利用のための保存データ：`<動画ID>.live_chat.json`、`info.json`、`audio_metrics.json`、`match_events.json`、`match_detected_sample.png`
- 手本：学習したもの `app/templates/learned_template.png`（と `.pos`）、利用者が置くもの `app/templates/ranked_match.png`

## 8. 設定（app/config.py）
BIN_SEC=30、TOP_N=25、LEAD_SEC=30、MIN_GAP_SEC=90、MIN_SPEED=1.5、KEYWORDS、WEIGHTS（speed 0.25、accel 0.10、same 0.10、keyword 0.15、money 0.05、heat 0.10、loud 0.25）、ANALYZE_AUDIO、ANALYZE_VIDEO、KEEP_MEDIA=False、VIDEO_HEIGHT=360、MATCH_TEXT="RANKED MATCH"、VIDEO_STEP_SEC=0.5、MATCH_MERGE_SEC=20

## 9. 制約
- Windows 前提（bat）。Python 3（3.13 推奨）。YouTube の取得には Deno が推奨（yt-dlp の要件）。
- メンバー限定・年齢制限・配信中の動画は解析できない。視聴者数の推移は取れない。
- 声の大きさ・喋る量は、ゲーム音と混ざった音声からの推定値。
- 文字認識は RapidOCR（無ければ Tesseract）。どちらも無いときは、試合の区切りを省略する。

## 10. ファイル構成
| ファイル | 役割 |
|---|---|
| app/highlight.py | 入口。処理の流れ |
| app/hl_fetch.py | yt-dlp による取得 |
| app/hl_chat.py | チャットの読み取りと区間ごとの集計 |
| app/hl_media.py | 音声・画面の解析 |
| app/hl_analyze.py | 指標の合成、見どころ、パートと試合 |
| app/hl_report.py | HTMLレポートとメモの出力 |
| app/config.py | 設定 |
