# ソーシャルコンテンツ生成ワークフロー現状まとめ

## データソース
- GitHub Actions `social-content.yml` またはローカル実行で `scripts/dev/generate_from_db.py` を起動し、`market_news.db` から最新記事150件を取得。
- メイン処理 `scripts/core/main.py` (`NewsProcessor.run()`) は記事収集とDB更新まで担当。現状この流れからソーシャル生成呼び出しは無く、ソーシャル専用ワークフロー/手動実行に依存。
- オフライン検証用に `data/articles.json` を読むスクリプト (`scripts/dev/generate_from_artifacts.py`) あり。

## 指標・マーケットデータ
- `src/core/social_content_generator.py` が `build/indicators/日付.json` または `data/indicators/日付.json` を探索。
- 見つからなければ `src/indicators/fetcher.py` が Stooq API から主要指数・為替・コモディティを取得して保存。
- 単独取得は `python scripts/dev/fetch_indicators.py` で可能。

## 生成ロジック
- `SocialContentGenerator` が記事からトピック上位3件を抽出し、`logs/social/日付/topics.json` に記録。
- 統合要約は DB `integrated_summaries` を優先し、無い場合は簡易生成。
- note 記事は `MarkdownRenderer` が Jinja テンプレート (`assets/templates/note/post.md.j2`) またはデフォルト文面で生成。LLM 最適化が有効なら `LLMContentOptimizer` が優先。
- SNS画像は `ImageRenderer` が 16:9 PNG（最大3枚）を生成し、指標データがあれば1枚目に反映。

## 出力物と配置
- 既定の出力ベースは `./build` (`config.social.output_base_dir`)。
  - 画像: `build/social/YYYYMMDD/news_*.png`
  - note: `build/note/YYYY-MM-DD.md`
  - 指標: `build/indicators/YYYYMMDD.json`
  - トピックログ: `logs/social/YYYYMMDD/topics.json`
- `social-content.yml` 実行時は生成物を `social-content` アーティファクトとして5日保持。
- メインワークフローは `build/social` と `build/note` を `public/social`/`public/note` にコピーして GitHub Pages プレビューへ配置。

## 補足
- `vars.ENABLE_SOCIAL_AUTORUN` を true にしない限り `social-content.yml` のスケジュールはスキップされる。
- ローカル検証手順: 最新DBを更新 → `python scripts/dev/generate_from_db.py` を実行 → `build/social`/`build/note` を直接確認。
