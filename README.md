# Market News Aggregator & AI Summarizer

## 1. 概要 (Overview)

このプロジェクトは、複数の金融・経済ニュースサイトから最新ニュースを自動的に収集し、**AI（Google Gemini）が各記事を要約**。その結果を**Webページ（GitHub Pages）として公開**し、同時にGoogleドキュメントにも出力するツールです。

日々の情報収集を効率化し、AIが要約した市場ニュースのレポートをWebとドキュメントの両方で自動生成することを目的としています。

## 2. 主な機能 (Features)

- **複数サイトからのニュース収集**:
  - ロイター（日本語版）
  - ブルームバーグ（日本語版）
- **AIによる自動要約**:
  - Googleの**Gemini API**を利用して、収集した各記事の本文を簡潔な要約に変換します。
- **Webページとしての自動公開**:
  - 要約されたニュース一覧をHTMLファイルとして生成し、**GitHub Pages**を利用して自動でWeb上に公開します。
- **柔軟なフィルタリング**:
  - 収集する記事の期間（例: 過去24時間以内）を指定可能。
  - キーワード、カテゴリ、除外ワードを設定し、必要な情報だけを抽出。
- **Googleドキュメントへの自動出力**:
  - **AI要約済み記事**: 日次アーカイブとして、指定したGoogle Driveフォルダに新しいドキュメントを作成します。
  - **収集した全記事（原文）**: 指定した単一のGoogleドキュメントに、常に最新の状態で上書き保存します。
- **GitHub Actionsによる完全自動実行**:
  - スケジュール（定時実行）または`main`ブランチへのプッシュをトリガーに、一連の処理を自動で実行します。

## 3. セットアップ手順 (Setup)

### Step 1: リポジトリのクローンとライブラリのインストール

```bash
# 1. プロジェクトをクローン
git clone https://github.com/jagar028055/Market_News_Project.git
cd Market_News_Project

# 2. 必要なライブラリをインストール
pip install -r requirements.txt
```

### Step 2: 各種APIの有効化と認証情報の設定

本ツールはGoogleの各種サービスを利用します。ローカルでの手動実行と、GitHub Actionsでの自動実行で設定方法が異なります。

#### A) Google Cloud Platform (GCP) での設定

1.  **Google Cloud Console**にアクセスし、プロジェクトを選択または新規作成します。
2.  **APIライブラリ**に移動し、以下のAPIを検索して**【有効にする】**をクリックします。
    -   **Google Drive API**
    -   **Google Docs API**
3.  **サービスアカウントの作成**:
    -   GitHub Actionsで自動実行するために、サービスアカウントを利用します。
    -   `[IAMと管理]` > `[サービスアカウント]` に移動し、`[+ サービスアカウントを作成]` をクリックします。
    -   任意の名前を付け、「完了」まで進みます。
    -   作成したサービスアカウントのメールアドレスをコピーしておきます。これは後でGoogle Driveフォルダの共有設定に使います。
    -   作成したサービスアカウントを選択し、`[キー]` タブ > `[鍵を追加]` > `[新しい鍵を作成]` を選択します。
    -   キーのタイプで **[JSON]** を選択して作成します。秘密鍵のJSONファイルがダウンロードされます。**このファイルは絶対に公開しないでください。**

#### B) Google AI Studioでの設定

1.  **Google AI Studio**にアクセスします。
2.  `[Get API key]` をクリックし、新しいAPIキーを作成します。
3.  生成されたAPIキーをコピーしておきます。

### Step 3: Google Driveフォルダの準備と共有設定

1.  Google Driveで、ニュースのアーカイブを出力したいフォルダを新規作成（または選択）します。
2.  ブラウザのアドレスバーに表示されているURLの末尾部分が**フォルダID**です。これをコピーします。
3.  作成したフォルダを、**Step 2-A-3**で作成した**サービスアカウントのメールアドレス**に対して「**編集者**」権限で共有します。

### Step 4: 環境変数の設定

#### A) ローカル実行用 (`.env`ファイル)

プロジェクトのルートに`.env`ファイルを新規作成し、以下の内容を記述します。

```env
# --- Google Drive & Docs ---
# Step 3でコピーしたフォルダID
GOOGLE_DRIVE_OUTPUT_FOLDER_ID="YOUR_FOLDER_ID"
# 全文を上書き保存したいドキュメントのID（任意）
GOOGLE_OVERWRITE_DOC_ID="YOUR_GOOGLE_DOC_ID_FOR_OVERWRITING"
# Step 2-A-3でダウンロードしたサービスアカウントのJSONファイルの内容を「文字列として」貼り付け
GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", "project_id": ...}'

# --- AI (Gemini) ---
# Step 2-Bで取得したAPIキー
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

#### B) GitHub Actions用 (Repository secrets)

GitHubリポジトリの `[Settings]` > `[Secrets and variables]` > `[Actions]` に移動し、以下の**Repository secrets**を登録します。

-   `GOOGLE_DRIVE_OUTPUT_FOLDER_ID`: Step 3でコピーしたフォルダID。
-   `GOOGLE_OVERWRITE_DOC_ID`: 全文を上書き保存したいドキュメントのID（任意）。
-   `GEMINI_API_KEY`: Step 2-Bで取得したAPIキー。
-   `GOOGLE_SERVICE_ACCOUNT_JSON`: Step 2-A-3でダウンロードしたサービスアカウントのJSONファイルの**中身全体**をコピーして貼り付けます。

## 4. 実行方法 (Usage)

-   **自動実行**:
    -   設定したスケジュール（デフォルトでは日本時間の7時、13時、23時）になると自動で実行されます。
    -   `main`ブランチにコードをプッシュした際にも自動で実行されます。
-   **手動実行**:
    -   ローカル環境で`.env`ファイルを設定後、`python main.py`で即時実行できます。
    -   GitHubリポジトリの `[Actions]` タブから手動でワークフローをトリガーすることも可能です。

## 新しいアーキテクチャ (New Architecture)

プロジェクトは2024年にモジュール化され、以下の構造になっています：

### プロジェクト構造
```
Market_News/
├── main.py                    # エントリーポイント（簡略化）
├── src/
│   ├── core/
│   │   └── news_processor.py  # メイン処理ロジック
│   ├── config/
│   │   └── app_config.py      # 統一設定管理
│   ├── error_handling/
│   │   └── custom_exceptions.py # カスタム例外
│   ├── html/
│   │   ├── html_generator.py  # HTML生成機能
│   │   └── template_engine.py # テンプレートエンジン
│   └── logging_config.py      # ログ設定
├── tests/
│   └── unit/                  # ユニットテスト
├── assets/
│   ├── css/                   # スタイル
│   └── js/                    # 最適化されたJavaScript
└── scrapers/                  # スクレイピングモジュール
```

### 主要な改善点

1. **モジュール化**: 機能別にクラスとモジュールを分離
2. **統一設定管理**: 環境変数とデフォルト値の一元管理
3. **構造化エラーハンドリング**: カスタム例外とエラーコンテキスト
4. **テンプレートベースHTML生成**: 保守性向上のため
5. **包括的テストカバレッジ**: ユニットテストによる品質保証
6. **JavaScript最適化**: DOM操作の最適化とパフォーマンス改善

### テスト実行方法

プロジェクトにはユニットテストが含まれています：

```bash
# 全テストの実行
python -m pytest tests/ -v

# 特定のテストファイルの実行
python -m pytest tests/unit/test_news_processor.py -v

# カバレッジレポートの生成
python -m pytest tests/ --cov=src --cov-report=html
```

### 設定カスタマイズ

設定は`src/config/app_config.py`で管理されています。環境変数を使用してカスタマイズ可能：

```bash
# 記事取得時間の制限（時間）
export SCRAPING_HOURS_LIMIT=48

# ログレベル
export LOGGING_LEVEL=DEBUG

# AI関連設定
export AI_GEMINI_API_KEY="your-api-key"
export AI_MODEL_NAME="gemini-2.0-flash-lite-001"
```

## 5. 成果物 (Outputs)

このツールを実行すると、以下の3つの成果物が生成・更新されます。

1.  **公開Webページ**: `https://<あなたのユーザー名>.github.io/<リポジトリ名>/` で、AI要約ニュースが閲覧できます。
2.  **日次要約ドキュメント**: 指定したGoogle Driveフォルダ内に、`YYYYMMDD_Market_News_Summary_AI` という名前でAI要約記事が保存されます。
3.  **全文上書きドキュメント**: 指定したGoogleドキュメントが、常に最新の収集記事（原文）で上書きされます。

## 6. 注意事項 (Notes)

-   本ツールはWebスクレイピング技術を利用しています。ニュースサイトのHTML構造が変更された場合、正常に動作しなくなる可能性があります。
-   サービスアカウントのJSONキーは非常に重要な認証情報です。絶対にリポジトリに直接コミットしたり、公開したりしないでください。
