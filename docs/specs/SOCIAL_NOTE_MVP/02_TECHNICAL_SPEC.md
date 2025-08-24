# SNS画像・note記事 出力MVP 技術仕様

## 1. モジュール構成
- 設定
  - `src/config/app_config.py`: 
    - `feature_flags.enable_social_images: bool`
    - `feature_flags.enable_note_md: bool`
    - `retention_policy: str`（`keep|archive|delete`）
- レンダラー
  - `src/renderers/markdown_renderer.py`
    - 役割: note用Markdown生成（Jinja2）
    - テンプレ: `assets/templates/note/post.md.j2`
  - `src/renderers/image_renderer.py`
    - 役割: SNS画像生成（Pillow）
    - アセット: `assets/brand/logo_mn_square.png`, フォント `assets/brand/fonts/NotoSansJP-Regular.ttf` 他
- トピック選定
  - `src/personalization/topic_selector.py`
    - 役割: 感情スコア非依存の上位トピック抽出

## 2. データフロー
1) `NewsProcessor.run()` 最終段: 現セッション記事を整形
2) トピック選定: `topic_selector.select_top(articles, k=3, now_jst)`
3) note生成: `markdown_renderer.render(date, topics, integrated_summary, output_dir)`
4) 画像生成: `image_renderer.render_16x9(date, title, topics, brand, output_dir)`
5) ログ/成果物パスを記録

## 3. I/F詳細
- `topic_selector.select_top(articles: List[dict], k: int, now_jst: datetime) -> List[Topic]`
  - 入力: `title, summary, published_jst, source, category, region`
  - 算法（例）:
    - 新規性スコア: `exp(-Δt / τ)`（τ=6–12h）
    - キーフレーズ: TF-IDF/キーワード辞書でスコア化（上限2フレーズ）
    - ソース優先: `Reuters/Bloomberg`に重み +α
    - カバレッジ: 同カテゴリ/地域の重複を抑制
  - 出力: `{headline, blurb, url, source}` ×k

- `markdown_renderer.render(date, topics, integrated_summary, output_dir) -> Path`
  - テンプレ変数: `{date, title, lead, points, market_overview, topics, images}`
  - 出力: `build/note/YYYYMMDD.md`

- `image_renderer.render_16x9(date, title, topics, brand, output_dir) -> Path`
  - レイアウト: 1920x1080、余白96、フォントサイズ（見出し64/本文36）
  - 出力: `build/social/YYYYMMDD/news_01_16x9.png`

## 4. テンプレ/アセット
- 追加予定:
  - `assets/templates/note/post.md.j2`
  - `assets/brand/logo_mn_square.png`
  - `assets/brand/fonts/NotoSansJP-{Regular,Bold}.ttf`

## 5. 出力ディレクトリ規約
- SNS: `build/social/YYYYMMDD/`
- note: `build/note/YYYYMMDD.md`

## 6. テスト方針
- トピック選定: 入力固定で上位3件の決定が安定するかユニットテスト。
- Markdown: スナップショット比較（行数/見出し/箇条書き）。
- 画像: スモーク（生成成功/解像度/フォント存在）。必要なら画像差分（許容誤差）。

## 7. エラーハンドリング
- フォント/ロゴ欠如: フォールバック（システムフォント/テキストロゴ）。
- テンプレ欠如: デフォルトテンプレを内蔵（最小限）。
- 出力ディレクトリ未作成: 自動作成。

## 8. リスクと対策
- 日本語改行/禁則: 長文を自動折返し、最大行数制限。
- 見出しの文字数超過: 省略記号付トリム。
- 後日Playwright方式へ切替: `image_renderer`は抽象I/F維持で差し替え容易に。
