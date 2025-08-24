# Supabase 利用ガイド（Freeプラン前提 / RAG・アーカイブ）

本ガイドは、Market Newsの過去要約アーカイブとRAG検索を、Supabase Freeプランを前提に最小コストで実装・運用するための技術指針です。

## 📚 関連ドキュメント

- **[RAGシステム完全ガイド](./rag/01_RAG_SYSTEM_GUIDE.md)** - 全体像と仕組みの理解
- **[クイックスタートガイド](./rag/04_QUICK_START_GUIDE.md)** - 5分で始められるセットアップ
- **[データフロー詳細](./rag/02_DATA_FLOW_DETAILS.md)** - システム内部の詳細処理
- **[RAGドキュメント集](./rag/README.md)** - 全ドキュメントの索引

---

## 1. 目的と適用範囲
- 目的: 長期保存と横断検索（RAG）を成立させ、note/SNS/レポート生成に再利用可能な知識ベースを維持する。
- 想定規模: 1日40–80件の要約、年間テキスト総量は数百MB（画像は当面外部CDN/Pages/Driveを利用）。
- プラン: Supabase Free（必要に応じてProへ移行可能）。

---

## 2. 全体アーキテクチャ（Free最適化）
- データレイヤ
  - Database（Postgres + pgvector）: 最小メタと要約チャンク＋埋め込みのみを保持（軽量化）。
  - Storage: 原文JSON/Markdown（構造化）を保存。画像は当面置かない。
- 主要コンポーネント
  - テーブル: `public.documents`（日次単位）/ `public.chunks`（チャンク＋embedding）
  - ベクター: `vector(384)`（DBフットプリント削減）
  - 近傍探索: `ivfflat (vector_cosine_ops, lists=100)`
  - 検索関数: `public.search_chunks(...)`
- 命名・配置
  - Storageバケット: `market-news-archive`
  - パス: `market-news-archive/YYYY/MM/DD/{daily_summary.md, corpus.json}`

---

## 3. 初期セットアップ手順
1) プロジェクト作成
- Supabaseダッシュボードで新規プロジェクト作成（地域/パスワード設定）。

2) DB拡張とスキーマ作成
- ダッシュボードのSQLエディタで以下を実行:
  - `scripts/migrations/supabase_free_init.sql`
  - 内容: `vector`/`pgcrypto`拡張、`documents`/`chunks`作成、`ivfflat`索引、`search_chunks`関数

3) Storageバケット作成
- Storage > New bucket: `market-news-archive`
- Publicは無効（Privateで開始を推奨）。

4) 環境変数設定（ローカル/.env）
- `SUPABASE_URL`、`SUPABASE_ANON_KEY`（クライアント用）
- サーバ処理には `SUPABASE_SERVICE_ROLE_KEY`（厳重管理; サーバのみ）
- 推奨: `SUPABASE_BUCKET=market-news-archive`

5) RLS（Row Level Security）
- 初期はPrivate運用。将来フロント公開する場合はRLSポリシーを個別に設計。

---

## 4. データモデル概要（詳細はDDL参照）
- `public.documents`
  - `doc_date: date`, `doc_type: text(daily_summary|full_corpus)`, `storage_path: text`, `url: text` ほか
- `public.chunks`
  - `document_id: uuid`, `chunk_no: int`, `content: text`, `region/category/source/url`, `embedding: vector(384)`
- 索引
  - `idx_chunks_embedding_ivfflat`（cosine）/ `idx_chunks_document_id` など
- 検索関数
  - `search_chunks(query_embedding, match_count, region_filter, category_filter, date_since)`

---

## 5. ETL/RAGパイプライン（MVP）
1) Export（生成直後）
- DBの個別要約/統合要約を整形し、`corpus.json` と `daily_summary.md` としてStorageへ保存。

2) Chunk/Embed
- チャンク長: 400–800字（オーバーラップ10–20%）
- 埋め込み: OSS（例: `sentence-transformers/all-MiniLM-L6-v2` の384次元）で生成（APIコストゼロ）。

3) Upsert
- `documents` に日次単位でUpsert → `chunks` にチャンク＋埋め込みを一括投入。
- 必要に応じて `ivfflat` 再構築。

4) Query
- メタフィルタ（期間/地域/カテゴリ）＋Top-k類似検索でRAG候補を取得。

5) Monitor/冷温化
- DB/StorageサイズをSheetsに記録。しきい値接近で「古いチャンクを削除→StorageのJSONで保持」。

---

## 6. 検索の使い方（例）
- 類似検索（SQL）
```sql
select *
from public.search_chunks(
  query_embedding => $1::vector(384), -- アプリ側で生成
  match_count     => 8,
  region_filter   => null,
  category_filter => null,
  date_since      => current_date - interval '180 days'
);
```
- 返却: `chunk_id, document_id, content, similarity, region, category, url`
- アプリ側でリランキング/重複除去/要約統合などを実施。

---

## 7. 運用とコスト最適化（Free）
- 画像は当面Storageへ置かず、GitHub Pages/Driveで配信（帯域節約）。
- ベクターは `384` 次元で開始。必要になれば切替（後移行スクリプト用意）。
- 定期メンテ
  - 重複/低品質チャンクの再圧縮
  - 不要メタの削除
  - インデックス再構築
- 将来増強
  - Proへ移行（Storage/帯域/バックアップ余裕）
  - 画像配信をStorageへ寄せる（帯域監視）

---

## 8. セキュリティと鍵管理
- `SERVICE_ROLE_KEY` はサーバーサイドのみで使用し、クライアントへ公開しない。
- RLSを適用してPrivate開始。公開が必要なAPI/ビューのみポリシーを作成。
- バケットはPrivateを前提に署名付きURLなどで提供。

---

## 9. リテンション/アーカイブ方針
- `retention_policy=keep`（削除ではなく保持）。
- DBは「最新nヶ月」を目安に保持、古いチャンクはStorageのJSONに冷温化。
- RAGはまず最新中心に、必要時にアーカイブも対象（範囲フィルタ）

---

## 10. よくある質問/トラブルシューティング
- Q: `ivfflat`が作れない
  - A: 権限/拡張エラーの可能性。`vector`拡張導入を確認。権限がない場合はB-treeのみで暫定運用。
- Q: 埋め込み次元が不一致でエラー
  - A: `vector(384)`に合わせてアプリ側埋め込みを生成。モデル切替時はDDL/再投入が必要。
- Q: Free枠を超えそう
  - A: 画像は外部配信に維持、古いチャンクを冷温化。必要時にProへ移行。

---

## 11. 次アクション
- Supabaseで `scripts/migrations/supabase_free_init.sql` を実行
- `.env` に `SUPABASE_URL`/`SUPABASE_ANON_KEY`/`SUPABASE_SERVICE_ROLE_KEY` を設定
- ETL/Embed/UpsertのMVPを実装し、30日削除ポリシーを停止（保持へ）

*** 参考 ***
- DDL: `scripts/migrations/supabase_free_init.sql`
- 設計ドラフト: `docs/CONTENT_EXPANSION_ROADMAP.md`（章 11/12）
