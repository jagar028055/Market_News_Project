# Supabase設定手順書

## 🎯 現在の状況

✅ **完了済み**:
- Supabase連携コードの修正
- GitHubアクションの環境変数追加
- ローカル環境でのテスト成功
- 依存関係の更新

⚠️ **手動設定が必要**:
- GitHub Secretsの設定
- Supabaseデータベーススキーマの更新

## 🔧 手動設定手順

### 1. GitHub Secretsの設定

以下のURLにアクセスしてSecretsを設定してください:
**https://github.com/jagar028055/Market_News_Project/settings/secrets/actions**

以下のSecretsを追加:

```
SUPABASE_URL: https://uiabfnfpvbthysvoveun.supabase.co
SUPABASE_ANON_KEY: [あなたのAnon Key]
SUPABASE_SERVICE_ROLE_KEY: [あなたのService Role Key]
```

### 2. Supabaseデータベーススキーマの更新

**Supabaseダッシュボード** (https://app.supabase.com) にログインして:

1. プロジェクトを選択
2. 左メニューから「SQL Editor」を開く
3. 以下のSQLを実行:

```sql
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

-- チャンクテーブル (384次元ベクトル) - 修正版
create table if not exists chunks (
    id uuid default gen_random_uuid() primary key,
    document_id uuid references documents(id) on delete cascade,
    content text not null,
    embedding vector(384),
    chunk_index integer not null,
    chunk_no integer not null default 1,
    category text,
    region text,
    source text,
    url text,
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
    using (auth.jwt() ->> 'role' = 'service_role')
    with check (auth.jwt() ->> 'role' = 'service_role');

create policy "Service role can do everything on chunks" 
    on chunks for all 
    using (auth.jwt() ->> 'role' = 'service_role')
    with check (auth.jwt() ->> 'role' = 'service_role');

-- アノニマスアクセス用ポリシー（読み取り専用）
create policy "Anonymous can read documents" 
    on documents for select 
    using (true);

create policy "Anonymous can read chunks" 
    on chunks for select 
    using (true);

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
```

### 3. GitHubアクションのテスト実行

設定完了後、以下の手順でテスト:

1. **手動実行**: GitHubリポジトリの「Actions」タブから「Market News Scraper」ワークフローを手動実行
2. **ログ確認**: 「Test Supabase Integration」ステップの結果を確認
3. **成功確認**: 全てのステップが成功することを確認

## 📊 期待される結果

### 成功時のログ
```
🔧 Supabase連携テスト開始
✅ Supabase設定確認成功
✅ Supabase接続テスト成功
✅ Supabase操作テスト成功
🎉 Supabase連携テスト: 全て成功!
```

### 失敗時の対処

1. **設定エラー**: GitHub Secretsの確認
2. **接続エラー**: Supabase URLとAPIキーの確認
3. **権限エラー**: RLSポリシーの確認
4. **スキーマエラー**: データベーススキーマの再実行

## 🚀 次のステップ

1. **本番運用開始**: スケジュール実行での動作確認
2. **RAG機能の活用**: 記事のアーカイブと検索機能のテスト
3. **監視設定**: Supabase使用量とエラーログの監視
4. **パフォーマンス最適化**: インデックスとクエリの最適化

---

**作成日**: 2025年1月12日  
**状況**: 手動設定待ち  
**リポジトリ**: https://github.com/jagar028055/Market_News_Project
