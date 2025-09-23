-- Supabaseスキーマ更新スクリプト
-- このSQLをSupabaseダッシュボードのSQL Editorで実行してください

-- documentsテーブルにカラム追加
ALTER TABLE documents ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS region TEXT;

-- chunksテーブルにカラム追加
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS chunk_no INTEGER DEFAULT 1;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS region TEXT;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS url TEXT;

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






