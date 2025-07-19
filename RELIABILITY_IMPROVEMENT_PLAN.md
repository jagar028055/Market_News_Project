# 機能信頼性向上計画：AI感情分析とダークモード

## 概要

本計画は、現在正常に機能していない「AIによる感情分析」および「ダークモード」の2つの機能を修正し、アプリケーション全体の信頼性を向上させることを目的とします。特に、AI機能の修正を最優先で実施します。

---

## フェーズ1: AI感情分析機能の抜本的修正

AI処理の失敗が機能不全の根本原因であるため、以下の手順で修正を行います。

### タスク1.1: JSON抽出ロジックの堅牢化

- **ファイル**: `ai_summarizer.py`
- **内容**: AIの応答からJSON部分をより確実に抽出するため、現在の文字列検索 (`find`, `rfind`) から正規表現を用いた方法に変更します。これにより、AIが余分なテキストを返した場合でも安定してJSONをパースできます。
- **コード変更箇所**:
  ```python
  # 変更前
  response_text: str = response.text.strip()
  json_start: int = response_text.find('{')
  json_end: int = response_text.rfind('}') + 1
  if json_start == -1 or json_end == 0:
      # ...
  json_str: str = response_text[json_start:json_end]

  # 変更後
  import re
  # ...
  response_text = response.text.strip()
  # ```json ... ``` または ``` ... ``` ブロックを探す正規表現
  match = re.search(r"```(json)?\s*({.*?})\s*```", response_text, re.DOTALL)
  if match:
      json_str = match.group(2)
  else:
      # フォールバックとして、最も内側にあるJSONオブジェクトを探す
      json_start = response_text.find('{')
      json_end = response_text.rfind('}') + 1
      if json_start != -1 and json_end != 0:
          json_str = response_text[json_start:json_end]
      else:
          logging.error(f"エラー: レスポンスに有効なJSONが含まれていません。レスポンス: {response_text}")
          return None
  ```

### タスク1.2: プロンプトの指示を強化

- **ファイル**: `market_news_config.py`
- **内容**: AIに対してJSON形式での出力をより厳密に強制するため、プロンプトの指示を強化します。
- **コード変更箇所**:
  ```python
  # 変更前
  # 回答は必ず以下のJSON形式で、他のテキストは一切含めずに返してください。
  
  # 変更後
  # 回答は必ず以下のJSONオブジェクトのみを、他のテキストは一切含めずに返してください。
  # ```json
  # { ... }
  # ```
  ```

### タスク1.3: フロントエンドのエラー表示を改善

- **ファイル**: `assets/js/app.js`
- **内容**: AI処理が失敗した場合（`sentiment_label`が "Error" または "N/A"）に、ユーザーに状態が明確に伝わるようにアイコンとスタイルを改善します。
- **コード変更箇所**:
  - `getSentimentIcon` 関数に "N/A" のケースを追加します。
  - `createArticleElement` 関数で、"N/A" の場合に専用のクラスを付与するようにします。
  - `assets/css/custom.css` に `.n-a` クラスのスタイルを追加します。

---

## フェーズ2: ダークモード機能の検証と修正

AI機能の修正後、ダークモードが正常に動作するかを確認し、問題が残る場合は修正します。

### タスク2.1: 動作再検証

- **内容**: フェーズ1完了後、ブラウザで `index.html` を開き、ダークモード切り替えボタンが正常に機能するかを確認します。AI処理に関連するJavaScriptエラーが解消されたことで、問題が自然に解決する可能性があります。

### タスク2.2: デバッグと修正

- **内容**: 問題が解決しない場合、ブラウザの開発者ツールを使用し、以下の点を調査・修正します。
  1.  コンソールに表示されるJavaScriptエラーの確認。
  2.  `theme-toggle` ボタンのクリックイベントが `toggleTheme` 関数を呼び出しているか。
  3.  `localStorage` に `theme` の値（'light'/'dark'）が正しく保存・読み込みされているか。

---

## フェーズ3: 総合テストと完了

- **内容**: 全ての修正が完了した後、`run_program.sh` を実行してシステム全体を動作させ、生成された `index.html` が以下の要件を満たしていることを確認します。
  1.  全ての記事に適切な感情分析結果（ラベル、スコア）が表示される。
  2.  AI処理に失敗した記事がある場合、その状態が明確に表示される。
  3.  ダークモードとライトモードの切り替えが問題なく動作する。
