# GitHub Actionsワークフロー一覧

| 表示名 | ファイル | 主なトリガー | 役割 | 現状 | 補足 |
| --- | --- | --- | --- | --- | --- |
| Market News Scraper | `.github/workflows/main.yml` | `push` (master)、`schedule` (UTC 22:00)、`workflow_dispatch` | ニュース収集・DB更新・HTML/PDF 等の生成と GitHub Pages への公開を行うメインパイプライン | **稼働中** | 実行後に `market_news.db` をアーティファクトとして保存。オプションでポッドキャスト生成やGoogle連携も実施。 |
| Social Content Integration | `.github/workflows/social-content.yml` | `schedule` (UTC 22:40) ※変数 `ENABLE_SOCIAL_AUTORUN` が true のとき／`workflow_dispatch` | 最新DBからSNS画像・note記事を生成し、成果物をアーティファクト化 | **条件付き稼働** | 既定では自動停止。手動または `ENABLE_SOCIAL_AUTORUN` 有効化で動作。 |
| Daily Podcast Broadcast | `.github/workflows/podcast-broadcast.yml` | `workflow_dispatch`（任意入力）※スケジュールはコメントアウト | ニュースDBまたはGoogle Docを元にポッドキャスト台本/音源を生成・配信 | **手動専用** | データソースに最新DBアーティファクトを優先使用。音声生成のため FFmpeg / TTS 認証をチェック。 |
| CI Tests | `.github/workflows/test.yml` | `push`（特定ブランチ）、`workflow_dispatch` | 単体テストと RAG スモークテストを走らせ、ログをアーティファクトに保存 | **稼働中** | 現状は `feature/social-workflow-disable-podcast-20250915` ブランチ向け。必要に応じて対象ブランチを調整。 |
| Monitoring (DISABLED) | `.github/workflows/monitoring.yml` | （手動のみ／実行すると失敗で終了） | 旧監視ワークフローのプレースホルダー | **無効化済み** | 機能はメインワークフローへ統合済み。ファイルは GitHub キャッシュ対策のため残存。 |
| Economic Indicator (DISABLED) | `.github/workflows/economic-indicator.yml` | （手動のみ／実行すると失敗で終了） | 旧経済指標ワークフローのプレースホルダー | **無効化済み** | 処理は `main.yml` に統合済み。 |
| Staging Deployment (DISABLED) | `.github/workflows/staging-deployment.yml` | （手動のみ／実行すると失敗で終了） | 旧ステージングデプロイフローのプレースホルダー | **無効化済み** | デプロイはメインワークフロー側で対応。 |
| pages-build-deployment | （GitHub自動生成） | `workflow_run`（Pages公開時に GitHub が自動起動） | GitHub Pages への公開処理 | **GitHub管理** | リポジトリには設定ファイルなし。`main.yml` が `public/` 配下を出力すると自動的に発火。 |

## 備考
- 上記以外の名称（例: "Chart Analyst Tests", "Economic Indicators System", "Enhanced Content Processing Workflow" 等）が GitHub UI に残っている場合は、過去のワークフローや手動ジョブの履歴です。現在リポジトリ内に該当ファイルはなく、必要であれば `.github/workflows` 配下に新規作成するか、不要なら GitHub の "Disable"/"Delete workflow file" を実施してください。
- ワークフロー整理の第一歩として、**無効化済み3件**を削除するか名称に `[LEGACY]` 等を付けると一覧が簡潔になります。合わせて `CI Tests` の対象ブランチや `Social Content Integration` の自動化条件も見直すと混乱を減らせます。
