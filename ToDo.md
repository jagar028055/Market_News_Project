# 自動ニュース要約＆Web公開パイプライン構築 ToDoリスト

## Phase 1: ローカル環境での機能拡張

### 1.1. 環境設定
- [ ] `requirements.txt`に`google-generativeai`を追加し、`pip install -r requirements.txt`を実行する。
- [ ] [Google AI Studio](https://aistudio.google.com/app/apikey)でAPIキーを取得し、`.env`ファイルに`GEMINI_API_KEY`として追記する。

### 1.2. AI要約モジュールの作成
- [ ] `ai_summarizer.py`を新規作成する。
- [ ] Gemini APIを呼び出し、与えられたテキストを約200字に要約する`summarize_text(api_key, article_text)`関数を実装する。
- [ ] APIエラーが発生した場合のフォールバック処理を実装する（例: エラーメッセージを返す）。

### 1.3. HTML生成モジュールの作成
- [ ] `html_generator.py`を新規作成する。
- [ ] 要約済みの記事リストを受け取り、`index.html`を生成する`create_html_file(articles)`関数を実装する。
- [ ] HTMLの`<head>`内で、Pico.cssなどの軽量CSSフレームワークをCDN経由で読み込み、デザインを整える。
- [ ] HTMLの構造を定義する（例: `<h1>本日のマーケットニュース</h1>`、各記事は`<article>`タグで囲む）。

### 1.4. メイン処理の修正 (`main.py`)
- [ ] `main.py`の処理フローを`記事収集 → 要約 → HTML生成`に変更する。
- [ ] スクレイピングで取得した記事リストを、新しく作成した`ai_summarizer`と`html_generator`に渡すように処理を修正する。
- [ ] Googleドキュメントへの出力は、メインの処理フローから切り離し、バックアップとしての役割に留める（処理は並行して行う）。
- [ ] 特定の記事の要約に失敗しても処理が止まらないよう、エラーハンドリングを追加する。

## Phase 2: GitHub Actionsでの自動化準備

### 2.1. 認証方法の変更 (`gdocs/client.py`)
- [ ] ローカルで`main.py`を実行し、`token.json`が生成されることを確認する。
- [ ] `gdocs/client.py`の`authenticate_google_services`関数を修正する。
    -   環境変数 `GOOGLE_TOKEN_JSON` が存在する場合、そのJSON文字列から認証情報（Credentials）を生成する処理を追加する。
    -   これにより、GitHub Actions環境では`anscombe.json`やブラウザ認証が不要になる。

### 2.2. GitHubリポジトリの設定
- [ ] リポジトリの `Settings > Secrets and variables > Actions` で、以下の3つのシークレットを登録する。
    -   `GOOGLE_DRIVE_OUTPUT_FOLDER_ID`: Google DriveのフォルダID。
    -   `GEMINI_API_KEY`: GeminiのAPIキー。
    -   `GOOGLE_TOKEN_JSON`: ローカルで生成した`token.json`ファイルの中身を全てコピーして貼り付け。

## Phase 3: 自動実行と公開

### 3.1. GitHub Actionsワークフローの作成
- [ ] `.github/workflows/daily-news-summary.yml` を作成する。
- [ ] ワークフローを定義する（`on: schedule`, `jobs`, `steps`など）。
-   - Pythonのセットアップ、依存関係のインストールを行う。
-   - `main.py`を実行するステップを追加し、`env`ブロックでGitHubシークレットを環境変数として渡す。
-   - 生成された`index.html`をリポジトリにコミット＆プッシュするステップを追加する。

### 3.2. GitHub Pagesの設定
- [ ] リポジトリの `Settings > Pages` を開く。
- [ ] `Source`を`Deploy from a branch`に設定し、ブランチを`main`（または利用中のブランチ）に指定して保存する。
- [ ] 公開されたURLを確認し、自動更新が正しく行われるかテストする。
