# GitHub Actions エラー時自動Issue作成機能

## 概要

GitHub Actionsワークフローが失敗した時に、自動でIssueを作成してエラー詳細をまとめる機能を実装しました。

## 実装済み機能

### 🎙️ ポッドキャスト配信ワークフロー (podcast-broadcast.yml)
- **ワークフロー名**: Daily Podcast Broadcast
- **Issue作成条件**: ワークフロー失敗時（プルリクエスト以外）
- **Issue内容**: 
  - 実行者、ブランチ、コミット情報
  - 失敗したワークフロー実行リンク
  - Google Cloud TTS関連のトラブルシューティング手順
  - 緊急対応コマンド集

### 📰 マーケットニュースワークフロー (main.yml)  
- **ワークフロー名**: Market News Scraper
- **Issue作成条件**: ワークフロー失敗時（プルリクエスト以外）
- **Issue内容**:
  - 実行者、ブランチ、コミット情報  
  - 失敗したワークフロー実行リンク
  - スクレイピング・API関連のトラブルシューティング手順
  - よくあるエラー原因解説

## 使用している Action

**Failed Build Issue Action** (jayqi/failed-build-issue-action@v1)

### 主要機能
- 既存のオープンな "CI/CD" ラベル付きIssueにコメント追加
- 該当するIssueが存在しない場合は新規Issue作成
- 重複Issue作成を防止
- カスタマイズ可能なIssueテンプレート

## Issue作成の詳細仕様

### 作成条件
```yaml
if: failure() && github.event.pull_request == null
```

- **failure()**: ワークフローが失敗した場合のみ
- **github.event.pull_request == null**: プルリクエストからの実行は除外

### 権限設定
```yaml
permissions:
  contents: write # GitHub Pages デプロイ用
  issues: write   # 失敗時Issue作成用
```

### Issue情報テンプレート変数
- `{{actor}}`: ワークフローを実行したユーザー
- `{{ref}}`: 実行されたブランチ/タグ
- `{{sha}}`: コミットハッシュ
- `{{author}}`: コミット作成者
- `{{date}}`: 実行日時
- `{{runId}}`: ワークフロー実行ID
- `{{workflowRunUrl}}`: 実行詳細URL
- `{{commitUrl}}`: コミット詳細URL

## 運用時の動作

### 初回失敗時
1. 新規Issue作成（"CI/CD"ラベル付き）
2. 詳細なエラー情報とトラブルシューティング手順を記載

### 継続失敗時  
1. 既存のオープンなIssueにコメント追加
2. 新しい失敗情報を時系列で追記

### Issue解決時
手動でIssueをクローズする必要があります

## トラブルシューティング機能

### ポッドキャストワークフロー向け
- Google Cloud TTS認証確認手順
- テストモードでの再実行方法
- 依存関係チェック方法

### マーケットニュースワークフロー向け
- スクレイピング対象サイトアクセス確認
- Gemini API制限・認証確認
- LINE Bot設定確認
- よくあるエラー原因（レート制限、構造変更等）

## 緊急対応コマンド

各Issueには以下のような実行可能なコマンドを自動記載：

```bash
# ワークフロー手動再実行
gh workflow run "ワークフロー名" --ref ブランチ名

# ローカルテスト実行
python main.py  # または test_tts_connection.py

# 接続テスト
python -c "import requests; print(requests.get('https://httpbin.org/get').status_code)"
```

## 設定のカスタマイズ

### Issue作成動作の変更
- `always-create-new-issue: false`: 既存Issue再利用（デフォルト）
- `always-create-new-issue: true`: 常に新規Issue作成

### ラベルのカスタマイズ
- `label-name: "CI/CD"`: 自動付与されるラベル名

### テンプレートのカスタマイズ
- `title-template`: Issueタイトルのテンプレート
- `body-template`: Issue本文のテンプレート

## 今後の拡張予定

1. **Slack/LINE通知連携**: Issue作成時の外部通知
2. **自動アサイン機能**: 実行者またはメンテナーへの自動アサイン
3. **エラー分類**: エラー内容に応じた自動ラベル付与
4. **修正提案**: エラー内容に基づく具体的な修正提案生成

## 参考リンク

- [Failed Build Issue Action](https://github.com/marketplace/actions/failed-build-issue)
- [GitHub Actions - Contexts](https://docs.github.com/en/actions/learn-github-actions/contexts)
- [GitHub Actions - Permissions](https://docs.github.com/en/actions/using-jobs/assigning-permissions-to-jobs)