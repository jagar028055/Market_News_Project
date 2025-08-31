-- 既存のテーブルに追加で必要な設定
-- Supabaseダッシュボード > SQL Editorで実行

-- 1. pgvector拡張機能を有効化（重要）
create extension if not exists vector;

-- 2. ベクトル検索用インデックス作成
create index if not exists chunks_embedding_idx 
on chunks using ivfflat (embedding vector_cosine_ops) 
with (lists = 100);

-- 3. RAG検索関数の作成（最も重要）
create or replace function search_chunks(
    query_embedding vector(384),
    match_count int default 5,
    region_filter text default null,
    category_filter text default null,
    date_since date default null
)
returns table (
    chunk_id uuid,
    document_id uuid,
    content text,
    similarity float,
    doc_type text,
    doc_date date,
    title text,
    metadata jsonb
)
language sql stable
as $$
    select 
        c.id,
        c.document_id,
        c.content,
        1 - (c.embedding <=> query_embedding) as similarity,
        d.doc_type,
        coalesce(
            case when (to_jsonb(d)->>'doc_date') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then (to_jsonb(d)->>'doc_date')::date end,
            case when (d.metadata->>'doc_date') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then (d.metadata->>'doc_date')::date end,
            d.created_at::date
        ) as doc_date,
        d.title,
        d.metadata
    from chunks c
    join documents d on c.document_id = d.id
    where 
        ($3::text is null or d.metadata->>'region' = $3) and
        ($4::text is null or d.metadata->>'category' = $4) and
        (
            $5::date is null or
            coalesce(
                case when (to_jsonb(d)->>'doc_date') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then (to_jsonb(d)->>'doc_date')::date end,
                case when (d.metadata->>'doc_date') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then (d.metadata->>'doc_date')::date end,
                d.created_at::date
            ) >= $5
        )
    order by c.embedding <=> query_embedding
    limit match_count;
$$;

-- 完了メッセージ
select 'RAG検索機能のセットアップ完了' as message;
