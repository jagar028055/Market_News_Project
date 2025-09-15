# SNSコンテンツ生成スケジュール計画（案）

目的: ニュース処理フロー（main.yml）完了後に、SNS画像とnote記事の生成を自動化し、配信に耐える成果物を安定的に作る。

## 前提
- メイン処理: `.github/workflows/main.yml` が UTC 22:00（JST 7:00）に実行。
- DBアーティファクト: `market-news-db` を `actions/upload-artifact` で保存（保持2日）。
- SNS生成: `scripts/dev/generate_from_db.py` を使用し、DBから記事を取り込み `build/` 配下に成果物を出力。

## 提案スケジュール（UTC基準）
- 22:40 UTC（JST 7:40）: 1日1回の本番生成タイミング。
  - 理由: メイン処理（22:00 UTC開始）が完了し、DBアーティファクトが取得可能になるまでの待機バッファを確保（~30–40分）。

将来の拡張（必要時のみ有効化）
- 03:30 UTC（JST 12:30、平日）: 昼の更新枠（任意）。
- 09:00 UTC（JST 18:00、平日）: 夕方の更新枠（任意）。

## 実装方針
- 新規Workflow: `.github/workflows/social-content.yml`
  - デフォルトは自動実行オフ（`jobs.social-content.if: vars.ENABLE_SOCIAL_AUTORUN == 'true'`）。
  - `workflow_dispatch` で手動実行は常時可。
  - 必須ステップ:
    - DBアーティファクト取得（`workflow: main.yml`, `name: market-news-db`）
    - 生成: `python scripts/dev/generate_from_db.py`
    - 成果物アップロード: `build/social/**`, `build/note/**`

## リリース手順（提案）
1. リポジトリ Variables に `ENABLE_SOCIAL_AUTORUN=true` を追加（段階的に有効化）。
2. 本番運用で安定後、必要なら `main.yml` のデプロイジョブに `build/social` の公開コピーを追加（`public/social/` へ）。
3. 将来、LINE/Twitter等の配信連携を追加する場合は、配信ジョブを別Workflowに分離して段階配信（dry-run → limited audience → general）。

## 注意点
- 文字レンダリングのための日本語フォント（`fonts-noto-cjk`, `fonts-ipafont-*`）をインストール済み。
- `GEMINI_API_KEY` が未設定でもテンプレート生成にフォールバック。高品質化のため本番では設定推奨。
- DBアーティファクトが見つからない場合はジョブ継続するものの、内容は薄くなる可能性あり。

---
作成日: 2025-09-15  
変更履歴: 初版（Podcast自動スケジュール停止に伴いSNS生成枠を策定）

