# SNS画像・note記事 出力MVP 要件定義

## 1. 背景・目的
- 背景: 既存のニュース収集・AI要約・HTML/Docs出力基盤はあるが、SNS用の視覚的アウトプットとnote記事の定常配信が未整備。
- 目的: 
  - 日次でSNS投稿用の画像1–3枚を自動生成（まずは16:9を1枚）。
  - 日次でnote投稿用のMarkdown本文を自動生成（手動投稿運用）。
  - 将来、チャート分析/経済指標分析の画像をSNS画像へ差し込み可能にする拡張性を確保。

## 2. スコープ
- 対象機能:
  - フィーチャーフラグ（`enable_social_images`, `enable_note_md`, `retention_policy`）。
  - トピック選定（注: 感情スコアは使用しない）。
  - note用Markdown生成（YAML Front Matterは任意）。
  - SNS画像生成（Pillowベースの16:9単枚、将来差し替え可能な抽象化）。
  - `NewsProcessor` への統合（出力ディレクトリ規約に従う）。
- 非スコープ（MVP時点）:
  - 各SNSへの自動投稿（手動運用）。
  - 画像内グラフの自動描画（将来のチャート/経済指標モジュール連携で対応）。
  - RAGやSupabaseの実装（別ドキュメントで管理）。

## 3. 成果物
- ファイル出力:
  - SNS画像: `build/social/YYYYMMDD/news_01_16x9.png`
  - note本文: `build/note/YYYYMMDD.md`
- ログ:
  - 生成ログと採択トピックの記録（生成根拠の再現性確保）。

## 4. 利用者ストーリー
- 編集者として、毎朝、画像とMarkdownが生成され、確認→そのまま投稿/貼り付けできる状態にしたい。
- デザイナーとして、テンプレの色・フォント・余白を簡単に調整したい。
- 将来のアナリストとして、チャートPNGを差し込める画像レイアウト余地がほしい。

## 5. 受け入れ基準（MVP）
- 16:9画像が日次で1枚以上生成される（タイトル＋3トピック＋日付＋ブランド要素）。
- note用Markdownが日次で生成される（章立て・箇条書きが整形）
- フィーチャーフラグで各出力のON/OFFが可能。
- 感情スコア非依存でトピック選定が成立する。

## 6. KPI（初期）
- 生成成功率（> 99%）。
- 作業短縮（編集作業時間の削減）。
- SNSクリック率/インプレッション（定性モニタ）。

## 7. 将来拡張
- チャート/経済指標PNGの差し込み。
- 1:1/9:16などサイズ展開、Playwright方式のテンプレ切替。
- 自動投稿、A/Bデザイン、RAG連携（類似過去事例の差し込み）。

## 8. タスク分解（WBS）

### A) 設定・フラグ・方針
- [ ] `src/config/app_config.py` に `feature_flags.enable_social_images` を追加
- [ ] 同 `feature_flags.enable_note_md` を追加
- [ ] 同 `retention_policy` を追加（`keep|archive|delete`、既定`keep`）
- [ ] 既存の削除処理を設定駆動化（`cleanup_old_data`の停止/分岐）
- [ ] `.env.sample`/READMEの設定項目を更新

### B) トピック選定ユーティリティ（感情非依存）
- [ ] `src/personalization/topic_selector.py` を新規作成
- [ ] 新規性スコア（公開時刻基準、τ=6–12h）を実装
- [ ] キーフレーズ抽出（TF-IDF or ルールベース辞書）を実装
- [ ] ソース優先度（Reuters/Bloombergに+α）とカテゴリ/地域カバレッジ抑制
- [ ] 出力フォーマット統一：`[{headline, blurb, url, source}]`
- [ ] ユニットテスト（同一入力で安定選定、件数不足時のフォールバック）

### C) note用Markdownレンダラ
- [ ] テンプレ: `assets/templates/note/post.md.j2` を追加
- [ ] 実装: `src/renderers/markdown_renderer.py`（Jinja2で生成）
- [ ] 章立て: タイトル/リード/今日の3ポイント/市場概況/注目トピック/図版/まとめ
- [ ] 画像参照: `build/social/YYYYMMDD/` と `build/charts/YYYYMMDD/` の相対パス
- [ ] 出力: `build/note/YYYYMMDD.md`
- [ ] スナップショットテスト（見出し・箇条書き・改行）

### D) SNS画像レンダラ（MVP: Pillow 16:9）
- [ ] 実装: `src/renderers/image_renderer.py`
- [ ] レイアウト: 1920x1080、余白96、見出し64pt/本文36pt
- [ ] 要素: タイトル、日付（JST）、ロゴ、上位3トピック、フッター（URL/ハッシュタグ）
- [ ] 右側チャート差し込み枠（MVPは空）
- [ ] 出力: `build/social/YYYYMMDD/news_01_16x9.png`
- [ ] スモークテスト（生成/解像度/フォント存在）

### E) アセット整備
- [ ] フォント: `assets/brand/fonts/NotoSansJP-{Regular,Bold}.ttf` を配置
- [ ] ロゴ: `assets/brand/logo_mn_square.png`（仮）を配置（テキストロゴでも可）
- [ ] カラー/余白/フォントサイズを定数化（将来設定化）

### F) パイプライン統合
- [ ] `NewsProcessor` にfeature flag判定とレンダラ呼び出しを追加
- [ ] 実行順: トピック選定→画像生成→note生成→ログ保存
- [ ] ログ: 採択トピック/スコア/レンダリング結果パスを記録

### G) 出力/スケジュール
- [ ] 日次出力ディレクトリの自動作成（`build/social/YYYYMMDD/`）
- [ ] 既存のスケジュール（CI/ローカル）に統合（手動実行も可）

### H) QA/チェック
- [ ] 文字溢れ対策（省略記号・改行・最大行数）
- [ ] 日付/時刻（JST）の表記確認
- [ ] コントラスト/可読性（背景×文字色）
- [ ] ロゴが無い場合のフォールバック描画

### I) ドキュメント/運用
- [ ] 使い方（実行手順・出力確認）の追記（README/OPERATIONS）
- [ ] デザイン調整方法（テンプレ/カラー/フォント差し替え）
- [ ] 将来チャート/指標PNG差し込み手順（占位枠仕様）

### J) 将来拡張のフック
- [ ] 画像サイズバリエーション（1:1/9:16）切替の抽象I/F
- [ ] Playwright方式への移行ポイント（テンプレ/レンダラ分離）
- [ ] 自動投稿のための出力メタ（タイトル文・推奨ハッシュタグ）
