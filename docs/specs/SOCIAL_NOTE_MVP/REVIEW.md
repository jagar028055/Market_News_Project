# SOCIAL_NOTE_MVP スペックレビューと修正提案

- 対象: `docs/specs/SOCIAL_NOTE_MVP/{00_REQUIREMENTS,01_FUNCTIONAL_SPEC,02_TECHNICAL_SPEC}.md`
- 目的: 既存実装（`src/` 配下）との不整合・不足点を洗い出し、仕様/実装どちらを直すかの提案を簡潔に整理。

## 差分サマリ（不整合・不足）
- 出力パス不一致: スペックは `build/`、実装は `output/`（`AppConfig.social.output_base_dir` 既定 `./output`）。
- 日付フォーマット不統一: ディレクトリは `YYYYMMDD`（例: `20250823`）とハイフン付き（`2025-08-23`）が混在。MDファイル名も記法が混在。
- フィーチャーフラグの場所: スペックは `feature_flags.*`、実装は `AppConfig.social.enable_*`。
- `retention_policy` 未実装: スペック記載（`keep|archive|delete`）だがコードには設定・分岐なし（`cleanup_old_data(days_to_keep=30)` を固定呼び出し）。
- NewsProcessor統合: スペックにある「レンダラ呼び出し」未統合（`SocialContentGenerator` は存在するが `NewsProcessor.run()` から未呼出）。
- テンプレ/アセット不足: `assets/templates/note/post.md.j2`、`assets/brand/fonts/*`、`assets/brand/logo_mn_square.png` が未配置（フォールバック動作は実装済）。
- ログ/JSON保存: 「採択トピックと選定根拠のJSON保存」未実装（ログはあり、永続JSONなし）。
- 依存関係: `Jinja2` が `requirements.txt` に未記載（テンプレ使用時に必要）。
- I/F細部差: `image_renderer.render_16x9` の引数順・名称がスペック表記と軽微に相違。
- 日本語折返し: 画像の折返しが概算実装（`len * 20`）。CJKでの見切れリスク（スペックのQA観点）。

## 仕様修正提案（ドキュメント側の更新）
- 出力ルートを実装に合わせて統一: `output/` を既定ベースにする（将来 `build/` に変更する場合は `AppConfig.social.output_base_dir` の既定のみ差し替え可能）。
- 日付規約を明記・統一:
  - ディレクトリ: `YYYYMMDD`（例: `output/social/20250823/`）
  - MDファイル名: `YYYY-MM-DD.md`（例: `output/note/2025-08-23.md`）
- フィーチャーフラグ表記を実装に合わせる: `social.enable_social_images`, `social.enable_note_md`。
- I/F表記の微修正:
  - `image_renderer.render_16x9(date, title, topics, output_dir, brand_name, website_url, hashtags)`
  - `markdown_renderer.render(date, topics, integrated_summary, output_dir, title?, market_overview?)`
- JSON保存仕様を追記: 採択トピックと選定根拠を `logs/social/YYYYMMDD/topics.json` に保存（`headline, blurb, url, source, score, published_jst, category, region`）。
- QA項目にCJK折返しを追加: 画像中テキスト幅計測は `draw.textlength` で行い、行数・省略処理を設ける。

## 実装修正提案（コード側の最小変更）
- `NewsProcessor.run()` にソーシャル生成を統合（フラグで分岐）:
  - 位置: 統合要約処理・HTML生成の後、Google連携の前後いずれか（推奨: HTML生成直後）。
  - 例:
    - `from src.core.social_content_generator import SocialContentGenerator`
    - `if config.social.enable_social_images or config.social.enable_note_md: SocialContentGenerator(config, logger).generate_social_content(current_session_articles)`
- 出力ベースを `build/` に合わせたい場合:
  - `src/config/app_config.py` の `SocialConfig.output_base_dir` 既定値を `./build` に変更。
  - `src/renderers/markdown_renderer.py` の相対参照（`../social/{YYYYMMDD}/news_01_16x9.png`）はそのままで整合。
- `retention_policy` を追加し適用:
  - `AppConfig` もしくは `SocialConfig` に `retention_policy: Literal["keep","archive","delete"] = "keep"` を追加。
  - `NewsProcessor.run()` 終端の `cleanup_old_data(...)` を方針に応じて分岐（`keep`: 実行せず、`delete`: 従来どおり、`archive`: ファイル出力のみアーカイブ先へ移動等）。
- JSON保存の実装: `src/core/social_content_generator.py` にてトピック選定後に `logs/social/YYYYMMDD/topics.json` を保存。
- 依存関係: `requirements.txt` に `Jinja2>=3.1.0` を追加。
- 日本語折返し改善（任意の改善）:
  - `src/renderers/image_renderer.py` の `_wrap_text` を `draw.textlength` ベースに変更（CJK対応）。
  - 画像描画の薄色枠はRGBAに統一（`Image.new('RGBA', ...)` または色をタプル指定）で互換性を担保。

## 未配置アセット（要追加）
- `assets/templates/note/post.md.j2`
- `assets/brand/fonts/NotoSansJP-Regular.ttf`
- `assets/brand/fonts/NotoSansJP-Bold.ttf`
- `assets/brand/logo_mn_square.png`

## ドキュメント反映例（最小差分）
- 00_REQUIREMENTS.md
  - 出力先を `output/` に統一、日付規約を明記。
  - フィーチャーフラグ表記を `social.enable_*` に変更。
  - JSON保存の成果物を追加（`logs/social/YYYYMMDD/topics.json`）。
- 01_FUNCTIONAL_SPEC.md
  - 出力例を `output/social/YYYYMMDD/news_01_16x9.png` と `output/note/YYYY-MM-DD.md` に統一。
  - QAにCJK折返しを追加。
- 02_TECHNICAL_SPEC.md
  - I/Fの引数順・名称を実装に合わせて微修正。
  - `retention_policy` の適用先と分岐を明記。
  - 依存関係に `Jinja2` 追記。

## 次アクション（推奨）
- 仕様を上記内容で微修正（このREVIEWに沿って追記・統一）。
- 実装は以下の順で最小対応:
  1) `NewsProcessor` 統合（フラグ連動）
  2) `output_base_dir` 既定の確定（`build` or `output`）
  3) `retention_policy` 追加と分岐反映
  4) JSON保存の追加
  5) アセット配置と `Jinja2` 追加
  6) 日本語折返し改善（必要なら）

以上。実装修正の適用も必要であれば対応します。
