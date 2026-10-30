# VibeCodingYouTubeAnalysisApp

YouTube配信アーカイブから、切り抜きの見どころを探すPCツール **in App版** です。
チャット（コメント量・加速度・同じコメントの割合など）、音声（声の大きさ・喋る量）、画面（「RANKED MATCH」の検知）を解析し、序盤（雑談・練習）と後半（実践）の比較、試合ごとの盛り上がり、見どころ候補をレポートにします。

姉妹製品：[in Chrome版（Chrome拡張機能）](https://github.com/potstudio0206/VibeCodingYouTubeAnalysisChrome)

## 使う
Windows で `app/setup.bat`（初回のみ）→ `app/run.bat` → 配信アーカイブのURLを貼り付け。詳しくは [app/README.txt](app/README.txt)。

## 開発・運用の体制
このリポジトリは、Claude Code のエージェントによる組織（**アプリケーション部**：部長・8課の課長・係長）が開発・運用しています。
- 共通ルール：[CLAUDE.md](CLAUDE.md)
- 社長（人間）向けの使い方：[docs/90_handbook/how-to-work.md](docs/90_handbook/how-to-work.md)
- 書類：[docs/](docs/README.md)
- 両部の共通指標仕様：[shared/metrics-spec.md](shared/metrics-spec.md)

## テスト
```
python -m unittest discover -s tests                 # 速いテスト（共通指標仕様の適合テストを含む）
RUN_SLOW=1 python -m unittest discover -s tests -v   # 重いテスト（合成配信で全工程）
python shared/reference/metrics_ref.py --check       # 共通指標の基準データの確認
```
