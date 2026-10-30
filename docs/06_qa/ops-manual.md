---
id: OPS-MANUAL
title: 保守運用書（in App版）
status: draft          # 初版（Claude作成）。保守運用書係が確認・更新する
author: app-qa-opsdoc
updated: 2026-10-30
---
# 保守運用書（in App版）

## 1. 定期作業
| いつ | 誰が | 何を | 手順 |
|---|---|---|---|
| 毎日 | 部長 | 日報 | /daily-report |
| 毎日 | 保守運用課・運用係 | 実配信での動作確認（1本） | /smoke-test |
| 毎週 | 保守運用課・運用係 | 依存ライブラリ（特に yt-dlp）の更新確認 | 3章 |
| 毎週 | 研究課 | 動向調査 | /research-scan |
| 毎週 | プレイヤー代理課 | 試用 | /player-session |

定期実行の設定は docs/90_handbook/scheduled-tasks.md にあります。

## 2. 実配信での動作確認（スモークテスト）
1. ops/smoke-urls.txt から、前回の次のURLを選ぶ。
2. `python app/highlight.py <URL> --no-open`
3. 確かめる：最後に「完了」と出る／`app/output/<動画ID>/見どころレポート.html` ができる／コメント数・試合数・見どころの数が前回と大きく違わない。
4. docs/07_ops/logs/YYYY-MM-DD.md に記録する。

## 3. 依存ライブラリの更新
1. 新しい版の確認：`python -m pip index versions yt-dlp` と `python -m yt_dlp --version`
2. 更新：`python -m pip install -U "yt-dlp[default]"`（他のライブラリも同様）
3. 速いテスト：`python -m unittest discover -s tests`、重いテスト：`RUN_SLOW=1 python -m unittest discover -s tests -v`
4. 実配信での動作確認（2章）
5. Deno（yt-dlp が YouTube で使う JavaScript ランタイム）が無い・古い場合：`winget install --id DenoLand.Deno`

## 4. よくある障害と対応
| 症状・文言 | 原因 | 対応 |
|---|---|---|
| 取得の途中でエラーになる | YouTube 側の仕様変更 | 3章で yt-dlp を更新。Deno を入れる。直らなければ不具合として報告 |
| 「チャットリプレイが見つかりませんでした」 | チャット無効・メンバー限定・アーカイブ処理中 | 別の動画で確認。処理中なら時間をおく |
| 「RANKED MATCH」が見つからない | 文字が小さい・見た目が違う | `app/templates/ranked_match.png` にスクリーンショットを置き `--redo-media` で再実行。config.py の VIDEO_HEIGHT を 480 に |
| 試合の区切りが前の配信の手本でずれる | 配信者・画面構成が変わった | `app/templates/learned_template.png` と `.pos` を消して再実行 |
| python が見つからない | Python が PATH に入っていない | Python を入れ直し「Add python.exe to PATH」にチェック |
| RapidOCR の警告（text detection result is empty） | 文字の無い画面を読んだだけ | 無害（表示は抑えてある） |

## 5. 復旧（前の版に戻す）
- 問題のあるPRを特定し、`git revert <コミット>` でPRを作って戻す（main への直接の操作はしない）。
- 解析結果がおかしいときは、`app/output/<動画ID>/` を消すと取り直す。

## 6. 確認用URLの管理
- ops/smoke-urls.txt に、チャットリプレイのある公開アーカイブを3〜5本。社長が登録する。
- 非公開・削除になったURLは運用係が報告し、社長に差し替えを頼む。

## 7. 変更履歴
| 日付 | 内容 |
|---|---|
| 2026-10-30 | 初版 |
