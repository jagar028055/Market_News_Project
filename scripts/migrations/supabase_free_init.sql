-- Supabase Free 前提の初期セットアップ
-- 拡張: pgvector / pgcrypto
create extension if not exists vector;
create extension if not exists pgcrypto;

-- documents: 日次メタ + Storageパス（原文/構造化はStorageに保持）
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  doc_date date not null,
  doc_type text not null check (doc_type in ('daily_summary','full_corpus')),
  url text,
  storage_path text,
  tokens int default 0,
  created_at timestamptz default now()
);

comment on table public.documents is '日次サマリーなど、RAGの論理ドキュメント単位';

-- chunks: チャンク本文 + メタ + ベクター(384)
create table if not exists public.chunks (
  id bigserial primary key,
  document_id uuid not null references public.documents(id) on delete cascade,
  chunk_no int not null,
  content text not null,
  region text,
  category text,
  source text,
  url text,
  embedding vector(384) not null,
  created_at timestamptz default now()
);

create index if not exists idx_chunks_document_id on public.chunks(document_id);
create index if not exists idx_chunks_region on public.chunks(region);
create index if not exists idx_chunks_category on public.chunks(category);

-- ベクター近傍探索（cosine）: listsはFree前提で小さめ
do $$ begin
  execute 'create index if not exists idx_chunks_embedding_ivfflat
           on public.chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100)';
exception when others then
  -- ivfflat未対応や権限問題時はスキップ
  raise notice 'ivfflat index creation skipped: %', sqlerrm;
end $$;

-- 類似検索用の簡易SQL関数
create or replace function public.search_chunks(
  query_embedding vector(384),
  match_count int,
  region_filter text default null,
  category_filter text default null,
  date_since date default null
) returns table(
  chunk_id bigint,
  document_id uuid,
  content text,
  similarity real,
  region text,
  category text,
  url text
) language sql stable as $$
  select
    c.id as chunk_id,
    c.document_id,
    c.content,
    cast(1 - (c.embedding <#> query_embedding) as real) as similarity,
    c.region,
    c.category,
    coalesce(c.url, d.url) as url
  from public.chunks c
  join public.documents d on d.id = c.document_id
  where (region_filter is null or c.region = region_filter)
    and (category_filter is null or c.category = category_filter)
    and (date_since is null or d.doc_date >= date_since)
  order by c.embedding <#> query_embedding
  limit match_count;
$$;

-- メモ: RLSはダッシュボードから要件に従い設定（FreeではPrivate維持を推奨）

