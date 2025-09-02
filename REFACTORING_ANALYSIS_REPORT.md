# プロジェクト構成改善レポート

## 1. 目的と概要

このレポートは、現在のプロジェクト構造を分析し、よりクリーンでメンテナンスしやすい構成へと改善するための具体的な手順を提示するものです。

### 分析結果の概要
- **ルートディレクトリの散乱**: プロジェクトのルートに、ドキュメント、一時的なスクリプト、旧設定ファイルなどが多数散在しており、見通しが悪くなっています。
- **不要なファイルの存在**: `Archive` や `legacy` といった、現在は使用されていないディレクトリやファイルがリポジトリ内に残り、肥大化の原因となっています。
- **コード内のパスのハードコード**: 一部のソースコードや設定ファイル内に、ファイルシステムへのパスが直接書き込まれています。これにより、将来的なファイル移動が困難になったり、特定の環境でしか動作しないといった問題を引き起こす可能性があります。

このレポートで提案する手順を実行することで、これらの問題点を解消し、プロジェクトの健全性を高めることを目指します。

---

## 2. ファイルの整理・移動計画

ルートディレクトリをクリーンにするため、以下のファイルをそれぞれの役割に応じたディレクトリに移動します。

#### 2.1. ドキュメント類 (`.md` ファイル)
- **移動先**: `docs/project_management/` （新規作成）
- **対象ファイル**:
  - `EXECUTION_CONDITION_PLAN.md`
  - `FUTURE_IMPROVEMENTS.md`
  - `GOOGLE_DRIVE_STORAGE_ISSUE_RESOLUTION_PLAN.md`
  - `IMPLEMENTATION_PLAN.md`
  - `IMPLEMENTATION_REPORT.md`
  - `PODCAST_SETUP_TASKS.md`
  - `RELIABILITY_IMPROVEMENT_PLAN.md`
  - `REQUIREMENTS_SPECIFICATION.md`
  - `SHARED_DRIVE_INTEGRATION_PLAN.md`
  - `スクレイピング処理時間長期化調査レポート.md`
    - **注意**: この日本語ファイル名は、AIエージェントのツールでは文字コードの問題で移動できませんでした。お手数ですが、手動での移動をお願いします。

#### 2.2. スクリプト類 (`.py` ファイル)
- **移動先 (マイグレーション)**: `scripts/migrations/`
  - `migrate_add_category_region.py`
  - `migrate_ai_analysis.py`
- **移動先 (手動テスト)**: `scripts/manual_tests/` （新規作成）
  - `manual_test.py`
  - `test_category_region_fix.py`
  - `test_classification_fix.py`
  - `test_flash_lite_accuracy.py`

#### 2.3. Web公開用ファイル
- **移動先**: `public/`
- **対象ファイル**:
  - `index.html`
  - `favicon.ico`
  - `manifest.json`

---

## 3. 不要ファイルの削除リスト

以下のファイルおよびディレクトリは、旧式であるか、特定の環境でしか動作しないため、削除を強く推奨します。

- **ディレクトリ (中身ごと削除)**:
  - `Archive/`: 過去のドキュメントや非推奨テストなど、プロジェクトの歴史的遺物。
  - `src/legacy/`: 新アーキテクチャ導入前の古いソースコード。
  - `scripts/legacy/`: 古い補助スクリプト。
- **個別ファイル (削除)**:
  - `market_news_config.py`: 古い設定ファイル。現在は `src/config/app_config.py` で管理。
  - `scripts/utilities/run_program.sh`: 特定の個人PCの絶対パスがハードコードされており、汎用性がないため。

---

## 4. 修正が必要なコード (ハードコードされたパス)

上記のファイル移動に伴い、以下のファイルのコード修正が**必須**となります。

#### 4.1. `public/index.html` のためのパス修正
- **対象ファイル**: `src/html/template_engine.py`
- **理由**: `index.html` がルートから `public/` に移動するため、そこから参照されるCSS, JS, データファイルへの相対パスを変更する必要があります。
- **修正内容**: パスの先頭に `../` を追加します。

```diff
--- a/src/html/template_engine.py
+++ b/src/html/template_engine.py
@@ -62,11 +62,11 @@
         html_content = f"""
 <!DOCTYPE html>
 <html lang="ja">
 <head>
     <meta charset="UTF-8">
     <meta name="viewport" content="width=device-width, initial-scale=1.0">
-    <link rel="stylesheet" href="assets/css/custom.css">
+    <link rel="stylesheet" href="../assets/css/custom.css">
     <title>AI Market News Summary</title>
     <script>
         async function loadData() {{
             try {{
-                const response = await fetch('data/articles.json');
+                const response = await fetch('../data/articles.json');
                 const data = await response.json();
                 // ... (以下略) ...
             }} catch (error) {{
@@ -107,10 +107,10 @@
         <div id="news-container"></div>
     </div>
     <script>
         document.addEventListener('DOMContentLoaded', function() {{
             const cache_buster = new Date().getTime();
-            const script = document.createElement('script');
-            script.src = 'assets/js/app.js?v=' + cache_buster;
-            document.body.appendChild(script);
+            const script = document.createElement('script');
+            script.src = '../assets/js/app.js?v=' + cache_buster;
+            document.body.appendChild(script);
         }});
     </script>
 </body>

```

#### 4.2.【参考】その他のハードコードされたパス (今回は修正不要)
以下のファイルにもハードコードされたパスが存在しますが、今回のリファクタリング作業では直接的な影響はありません。しかし、将来的なポータビリティ（環境依存性の排除）向上のため、対応を検討する価値があります。

- **対象ファイル**:
  - `src/renderers/image_renderer.py`
  - `src/wordcloud/visualizer.py`
  - `src/wordcloud/config.py`
- **内容**: `/System/Library/Fonts/` や `/usr/share/fonts/` といった、macOSやLinuxのシステムフォントへの絶対パスが記述されています。
- **問題点**: これらのフォントが存在しないWindows等の環境では、画像生成やワードクラウド機能がエラーになります。
- **推奨される改善策**: プロジェクト内にフォントファイルを同梱し、そこへ相対パスでアクセスするように変更する。

---

## 5. 推奨作業手順 (コマンド例)

以下に、このレポートで提案した内容を実行するためのコマンド手順を示します。

```bash
# ステップ1: 不要なディレクトリとファイルを削除
rm -rf Archive/ src/legacy/ scripts/legacy/
rm market_news_config.py
rm scripts/utilities/run_program.sh # 存在しない場合はスキップ

# ステップ2: 新しいディレクトリを作成
mkdir -p docs/project_management/
mkdir -p scripts/manual_tests/

# ステップ3: ファイルを移動
# 3-1: ドキュメント類
mv EXECUTION_CONDITION_PLAN.md docs/project_management/
mv FUTURE_IMPROVEMENTS.md docs/project_management/
mv GOOGLE_DRIVE_STORAGE_ISSUE_RESOLUTION_PLAN.md docs/project_management/
mv IMPLEMENTATION_PLAN.md docs/project_management/
mv IMPLEMENTATION_REPORT.md docs/project_management/
mv PODCAST_SETUP_TASKS.md docs/project_management/
mv RELIABILITY_IMPROVEMENT_PLAN.md docs/project_management/
mv REQUIREMENTS_SPECIFICATION.md docs/project_management/
mv SHARED_DRIVE_INTEGRATION_PLAN.md docs/project_management/
# ※ 日本語ファイル名はお手数ですが手動で移動してください。
# mv "スクレイピング処理時間長期化調査レポート.md" docs/project_management/

# 3-2: スクリプト類
mv migrate_add_category_region.py migrate_ai_analysis.py scripts/migrations/
mv manual_test.py test_category_region_fix.py test_classification_fix.py test_flash_lite_accuracy.py scripts/manual_tests/

# 3-3: Web公開用ファイル
mv index.html favicon.ico manifest.json public/

# ステップ4: ソースコードのパスを修正
# `src/html/template_engine.py` を、セクション4.1のdiffを参考に修正してください。

# ステップ5: 変更をコミット
# git add .
# git commit -m "refactor: Organize project structure and remove obsolete files"
```

以上の手順で、プロジェクトの整理は完了です。
