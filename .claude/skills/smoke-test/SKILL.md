---
name: "smoke-test"
description: "実際のYouTube配信アーカイブでin App版が動くかを確かめ、運用記録を残す手順（保守運用課）。定期実行で使う。"
---

# 実配信での動作確認（スモークテスト）

※ YouTube に繋ぐ作業なので、このPC（Windows）でしか実行できません。

部長は、保守運用課長（app-ops-kacho）に次を依頼します。

1. ops/smoke-urls.txt から、前回の次のURLを1本選ぶ（前回の記録は docs/07_ops/logs/ の最新）。URLが1本も無ければ、社長に追加を頼む判断待ちIssueを立てて終わる。
2. 実行する：python app/highlight.py <アーカイブのURL> --no-open
   - 実行前に依存の新しい版を確かめる：`python -m pip index versions yt-dlp` と `python -m yt_dlp --version`。新しい版があれば `python -m pip install -U "yt-dlp[default]"` で更新し、速いテスト（python -m unittest discover -s tests）を実行してから続ける。
   - 確かめる点：最後に「完了」と出るか、app/output/<動画ID>/見どころレポート.html ができるか、コメント数・試合数・見どころの数が前回と大きく違わないか。
3. 記録する：docs/07_ops/logs/YYYY-MM-DD.md に、日時・URL・結果（成功/失敗）・コメント数・所要時間・見どころの数・エラーの文言を書き、前回と比べる。
4. 失敗・大きな変化があれば、不具合として部長に報告する（部長が /bugfix-pipeline を回す）。
