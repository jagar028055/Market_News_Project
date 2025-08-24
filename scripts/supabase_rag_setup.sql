-- RAGシステム用データベーススキーマ
-- Supabaseダッシュボード > SQL Editorで実行してください

-- pgvector拡張機能を有効化
create extension if not exists vector;

-- ドキュメントテーブル
create table if not exists documents (
    id uuid default gen_random_uuid() primary key,
    title text not null,
    content text not null,
    doc_type text not null,
    doc_date date not null default current_date,
    metadata jsonb default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- チャンクテーブル (384次元ベクトル)
create table if not exists chunks (
    id uuid default gen_random_uuid() primary key,
    document_id uuid references documents(id) on delete cascade,
    content text not null,
    embedding vector(384),
    chunk_index integer not null,
    metadata jsonb default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- インデックス作成
create index if not exists chunks_document_id_idx on chunks(document_id);
create index if not exists chunks_embedding_idx on chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index if not exists documents_doc_type_idx on documents(doc_type);
create index if not exists documents_doc_date_idx on documents(doc_date);
create index if not exists documents_created_at_idx on documents(created_at);

-- RLS (Row Level Security) 設定
alter table documents enable row level security;
alter table chunks enable row level security;

-- 既存ポリシーを削除（エラー回避のため）
drop policy if exists "Service role can do everything on documents" on documents;
drop policy if exists "Service role can do everything on chunks" on chunks;

-- サービスロール用ポリシー（フルアクセス）
create policy "Service role can do everything on documents" 
    on documents for all 
    using (auth.jwt() ->> 'role' = 'service_role');

create policy "Service role can do everything on chunks" 
    on chunks for all 
    using (auth.jwt() ->> 'role' = 'service_role');

-- ストレージバケット作成
insert into storage.buckets (id, name, public)
values ('market-news-archive', 'market-news-archive', false)
on conflict (id) do nothing;

-- ストレージポリシー
drop policy if exists "Service role can manage archive files" on storage.objects;
create policy "Service role can manage archive files"
on storage.objects for all
using (bucket_id = 'market-news-archive' and auth.jwt() ->> 'role' = 'service_role');

-- 更新日時自動更新のためのトリガー
create or replace function update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = timezone('utc'::text, now());
    return new;
end;
$$ language 'plpgsql';

drop trigger if exists update_documents_updated_at on documents;
create trigger update_documents_updated_at
    before update on documents
    for each row execute procedure update_updated_at_column();

-- RAG検索関数
create or replace function search_chunks(
    query_embedding vector(384),
    match_count int default 5,
    date_filter date default null
)
returns table (
    chunk_id uuid,
    document_id uuid,
    content text,
    similarity float,
    doc_type text,
    doc_date date,
    title text
)
language sql stable
as $$
    select 
        c.id,
        c.document_id,
        c.content,
        1 - (c.embedding <=> query_embedding) as similarity,
        d.doc_type,
        d.doc_date,
        d.title
    from chunks c
    join documents d on c.document_id = d.id
    where ($3::date is null or d.doc_date >= $3)
    order by c.embedding <=> query_embedding
    limit match_count;
$$;

-- 完了メッセージ
select 'RAGシステム用データベースセットアップ完了' as message;