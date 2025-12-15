# Supabaseのカテゴリー・地域情報保存の修正

## 問題の概要

記事のカテゴリー（category）と地域（region）情報がSupabaseに正しく保存されていませんでした。

### 発見された問題

1. **ローカルデータベース**: AI分析で抽出された`category`と`region`は`ai_analysis`テーブルに保存されている
2. **Supabaseデータベース**: `documents`テーブルと`chunks`テーブルに`category`と`region`フィールドがあるが、アーカイブ処理でmetadataに保存されており、トップレベルフィールドとして保存されていなかった

## 実施した修正

### 1. `archive_manager.py`の修正

**変更内容:**
- `archive_article`メソッド: `category`と`region`をトップレベルフィールドとして保存
- `_archive_single_article_document`メソッド: 同様に修正

**修正前:**
```python
'metadata': {
    'url': article_data.get('url', ''),
    'source': article_data.get('source', ''),
    'category': article_data.get('category', ''),
    'region': article_data.get('region', ''),
}
```

**修正後:**
```python
# トップレベルフィールドとして保存
'url': article_data.get('url', ''),
'source': article_data.get('source', ''),
'category': article_data.get('category', ''),
'region': article_data.get('region', ''),
'metadata': {
    'article_id': article_data.get('id'),
    'published_at': published_at,
    'ai_summary': article_data.get('ai_summary', ''),
    'tags': article_data.get('tags', []),
}
```

### 2. `news_processor.py`の修正

**変更内容:**
- `archive_to_supabase`メソッド: AI分析結果から`category`と`region`を取得して記事データに追加

**追加処理:**
```python
# AI分析結果からcategoryとregionを取得（存在する場合）
url = article.get('url')
if url:
    normalized_url = self.db_manager.url_normalizer.normalize_url(url)
    article_with_analysis = self.db_manager.get_article_by_url_with_analysis(normalized_url)
    
    if article_with_analysis and article_with_analysis.ai_analysis:
        analysis = article_with_analysis.ai_analysis[0]
        # AI分析結果をarticleデータに追加
        if analysis.category and not article.get('category'):
            article['category'] = analysis.category
        if analysis.region and not article.get('region'):
            article['region'] = analysis.region
```

## Supabaseスキーマの更新

### 必須: スキーマ更新スクリプトの実行

修正を有効にするには、Supabaseのスキーマを更新する必要があります。

**手順:**

1. Supabaseダッシュボードにログイン
2. 「SQL Editor」を開く
3. 以下のスクリプトを実行:

```sql
-- documentsテーブルにカラム追加
ALTER TABLE documents ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS region TEXT;

-- chunksテーブルにカラム追加（既に存在する場合もあり）
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS chunk_no INTEGER DEFAULT 1;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS region TEXT;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS url TEXT;

-- インデックスの追加（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_region ON documents(region);
CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source);
CREATE INDEX IF NOT EXISTS idx_chunks_category ON chunks(category);
CREATE INDEX IF NOT EXISTS idx_chunks_region ON chunks(region);

-- スキーマ確認クエリ
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name IN ('documents', 'chunks')
AND table_schema = 'public'
ORDER BY table_name, ordinal_position;
```

4. 実行結果を確認し、`category`と`region`フィールドが追加されていることを確認

### スクリプトファイルの場所

上記のスクリプトは以下のファイルにも保存されています：
- `scripts/update_supabase_schema.sql`

## データの流れ

### 修正後のデータフロー

1. **スクレイピング**: 記事を収集
   - BloombergやReutersから記事を取得
   - ローカルDBの`articles`テーブルに保存（`category`のみ）

2. **AI分析**: 記事を分析
   - Gemini APIで記事を分析
   - `category`と`region`を抽出
   - ローカルDBの`ai_analysis`テーブルに保存

3. **Supabaseアーカイブ**:
   - AI分析結果から`category`と`region`を取得
   - 記事データに追加
   - Supabaseの`documents`テーブルと`chunks`テーブルに保存
   - **トップレベルフィールドとして保存**（検索・フィルタリング可能）

## 期待される効果

### 改善点

1. ✅ **検索性の向上**: `category`と`region`で記事を直接検索・フィルタリング可能
2. ✅ **パフォーマンス向上**: インデックスが効いて高速検索が可能
3. ✅ **データの一貫性**: ローカルDBとSupabaseで同じ情報が保存される
4. ✅ **分析の容易性**: 地域別・カテゴリ別の統計分析が容易

### 利用例

```python
# 地域別検索
japan_articles = supabase.table('documents')\
    .select('*')\
    .eq('region', 'japan')\
    .execute()

# カテゴリ別検索
market_articles = supabase.table('documents')\
    .select('*')\
    .eq('category', 'market')\
    .execute()

# 地域とカテゴリの組み合わせ
japan_market_articles = supabase.table('documents')\
    .select('*')\
    .eq('region', 'japan')\
    .eq('category', 'market')\
    .execute()
```

## 既存データの移行

既にSupabaseに保存されている記事については、metadataから`category`と`region`を抽出してトップレベルフィールドに移行する必要があります。

### 移行スクリプト（必要に応じて実行）

```sql
-- metadataからcategoryとregionを抽出してトップレベルフィールドに移行
UPDATE documents
SET 
    category = metadata->>'category',
    region = metadata->>'region',
    source = metadata->>'source',
    url = metadata->>'url'
WHERE 
    doc_type = 'article'
    AND category IS NULL
    AND metadata->>'category' IS NOT NULL;

-- 確認クエリ
SELECT 
    id, 
    title, 
    category, 
    region, 
    source,
    doc_type,
    doc_date
FROM documents
WHERE doc_type = 'article'
ORDER BY doc_date DESC
LIMIT 10;
```

## 注意事項

1. **スキーマ更新は必須**: コード修正だけでは機能しません。Supabaseのスキーマ更新を忘れずに実行してください
2. **既存データの移行**: 既にアーカイブされている記事については、移行スクリプトを実行する必要があります
3. **インデックス**: 大量のデータがある場合、インデックス作成に時間がかかる場合があります

## 検証方法

### 1. ローカルテスト

```bash
# スクレイピングとAI分析を実行
python -m src.main

# ログを確認
tail -f logs/market_news.log
```

### 2. Supabaseデータ確認

```sql
-- 最新の記事を確認
SELECT 
    id,
    title,
    category,
    region,
    source,
    doc_date,
    created_at
FROM documents
WHERE doc_type = 'article'
ORDER BY created_at DESC
LIMIT 10;

-- カテゴリ別統計
SELECT 
    category,
    COUNT(*) as count
FROM documents
WHERE doc_type = 'article'
  AND category IS NOT NULL
GROUP BY category
ORDER BY count DESC;

-- 地域別統計
SELECT 
    region,
    COUNT(*) as count
FROM documents
WHERE doc_type = 'article'
  AND region IS NOT NULL
GROUP BY region
ORDER BY count DESC;
```

## まとめ

この修正により、記事のカテゴリーと地域情報がSupabaseに正しく保存され、効率的な検索と分析が可能になります。

