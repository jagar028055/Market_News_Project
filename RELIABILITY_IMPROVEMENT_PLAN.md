# GitHub Actions ワークフロー信頼性向上計画

## 1. 背景

現在運用しているGitHub Actionsワークフローにおいて、潜在的な非効率性や将来的なメンテナンスリスクが確認された。具体的なエラーメッセージは不明だが、一般的なベストプラクティスに基づき、ワークフローの信頼性、効率性、メンテナンス性を向上させるための改善を実施する。

## 2. 考えられる問題点

- **デプロイ履歴の欠如**: `peaceiris/actions-gh-pages`アクションで`force_orphan: true`オプションが使用されており、デプロイのたびに`gh-pages`ブランチの履歴が失われている。これにより、問題発生時の原因調査が困難になっている。
- **実行時間の非効率性**: ワークフロー実行のたびに、pipの依存関係をゼロからインストールしているため、不要な時間とリソースを消費している。
- **アクションの旧バージョン使用**: 使用している`actions/checkout`や`actions/setup-python`などが最新バージョンではなく、潜在的なセキュリティリスクや非推奨機能を利用している可能性がある。
- **エラーハンドリングの不足**: `main.py`が`index.html`を生成しなかった場合、デプロイステップでエラーが発生する可能性がある。

## 3. 改善方針と要件

### 3.1. 要件定義

1.  **実行時間の短縮**: 依存関係のキャッシュを導入し、ワークフロー全体の実行時間を短縮する。
2.  **安定性の向上**: デプロイ履歴を保持するように変更し、問題発生時の原因究明を容易にする。また、`index.html`が存在しない場合にデプロイが失敗するのを防ぐ。
3.  **メンテナンス性の向上**: 使用しているアクションを最新バージョンに更新し、将来的な互換性問題を未然に防ぐ。

### 3.2. タスクリスト

| No. | タスク概要 | 詳細 | 担当 | 期限 |
| :-- | :--- | :--- | :--- | :--- |
| 1 | 依存関係のキャッシュ設定 | `actions/cache`アクションを追加し、pipのキャッシュを有効にする。キーには`requirements.txt`のハッシュ値を使い、依存関係の変更時のみキャッシュを更新する。 | - | - |
| 2 | GitHub Actionsのバージョン更新 | - `actions/checkout`を`v3`から`v4`に更新する。<br>- `actions/setup-python`を`v4`から`v5`に更新する。<br>- `peaceiris/actions-gh-pages`を`v3`から`v4`に更新する。 | - | - |
| 3 | デプロイ設定の見直し | `peaceiris/actions-gh-pages`の`force_orphan: true`オプションを削除し、デプロイ履歴が保持されるように変更する。 | - | - |
| 4 | `index.html`の存在確認 | `Deploy to GitHub Pages`ステップに`if`条件を追加し、`index.html`ファイルが存在する場合にのみデプロイが実行されるようにする。 | - | - |

## 4. 変更後のワークフロー（案）

```yaml
name: Market News Scraper

on:
  push:
    branches:
      - main
      - 'feature/**'
  schedule:
    - cron: '0 22 * * *' # JST 7時
    - cron: '0 4,14 * * *' # JST 13時, 23時
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Cache pip dependencies
      uses: actions/cache@v4
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run script
      env:
        GOOGLE_DRIVE_OUTPUT_FOLDER_ID: ${{ secrets.GOOGLE_DRIVE_OUTPUT_FOLDER_ID }}
        GOOGLE_OVERWRITE_DOC_ID: ${{ secrets.GOOGLE_OVERWRITE_DOC_ID }}
        GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
      run: python main.py

    - name: Create public directory and move index.html
      run: |
        mkdir -p public
        if [ -f index.html ]; then
          mv index.html public/
        else
          echo "index.html not found, skipping move."
        fi

    - name: Deploy to GitHub Pages
      if: github.ref == 'refs/heads/main' && steps.move_html.outputs.moved == 'true'
      uses: peaceiris/actions-gh-pages@v4
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./public
        publish_branch: gh-pages
        user_name: 'github-actions[bot]'
        user_email: 'github-actions[bot]@users.noreply.github.com'
