#!/usr/bin/env python3
"""
RAGシステム環境セットアップスクリプト

このスクリプトは以下を実行します:
1. 必要な依存関係のインストール
2. 環境変数テンプレートの生成
3. Supabaseデータベースの設定確認
4. 初期データのセットアップ

使用方法:
python scripts/setup_rag_environment.py
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, Any

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class RAGEnvironmentSetup:
    """RAGシステム環境セットアップクラス"""
    
    def __init__(self):
        """セットアップクラス初期化"""
        self.project_root = project_root
        self.env_file = self.project_root / ".env"
        
    def run_setup(self):
        """環境セットアップを実行"""
        print("🚀 RAGシステム環境セットアップ開始")
        print("=" * 50)
        
        steps = [
            ("依存関係確認", self._check_dependencies),
            ("環境変数テンプレート生成", self._create_env_template),
            ("Supabase SQL確認", self._check_supabase_sql),
            ("ディレクトリ構造確認", self._check_directories),
            ("設定ファイル確認", self._verify_config_files)
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}")
            print("-" * 30)
            try:
                step_func()
                print("✅ 完了")
            except Exception as e:
                print(f"❌ エラー: {str(e)}")
                return False
        
        self._print_next_steps()
        return True
    
    def _check_dependencies(self):
        """依存関係確認"""
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            print("❌ requirements.txtが見つかりません")
            return False
        
        # 必要な依存関係を確認
        required_packages = [
            "supabase",
            "sentence-transformers",
            "numpy",
            "faiss-cpu"
        ]
        
        with open(requirements_file, 'r', encoding='utf-8') as f:
            requirements_content = f.read()
        
        missing_packages = []
        for package in required_packages:
            if package not in requirements_content:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"⚠️  以下のパッケージが不足しています: {', '.join(missing_packages)}")
        else:
            print("✅ 必要なパッケージが全て含まれています")
        
        # インストール状況確認
        try:
            import supabase
            print("✅ supabase パッケージ利用可能")
        except ImportError:
            print("⚠️  supabase パッケージがインストールされていません")
            print("   実行: pip install -r requirements.txt")
    
    def _create_env_template(self):
        """環境変数テンプレート生成"""
        env_template = """# RAGシステム設定
# Supabase設定 (必須)
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
SUPABASE_ENABLED=true
SUPABASE_BUCKET=market-news-archive

# RAG設定 (オプション - デフォルト値が使用されます)
# RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
# RAG_EMBEDDING_DIMENSION=384
# RAG_CHUNK_SIZE=600
# RAG_CHUNK_OVERLAP=100
# RAG_MAX_CHUNKS_PER_DOCUMENT=50
# RAG_SIMILARITY_THRESHOLD=0.7

# その他の既存設定はそのまま保持してください
"""
        
        env_example_file = self.project_root / ".env.example"
        
        # .env.exampleファイルを作成/更新
        with open(env_example_file, 'w', encoding='utf-8') as f:
            f.write(env_template)
        
        print(f"✅ 環境変数テンプレート作成: {env_example_file}")
        
        # 既存の.envファイルを確認
        if self.env_file.exists():
            print("ℹ️  既存の.envファイルが見つかりました")
            print("   Supabase設定を手動で追加してください")
        else:
            print("ℹ️  .envファイルを作成して設定を追加してください")
            print("   cp .env.example .env")
    
    def _check_supabase_sql(self):
        """Supabase SQL確認"""
        sql_content = '''-- RAGシステム用データベーススキーマ
-- Supabaseダッシュボード > SQL Editorで実行してください

-- pgvector拡張機能を有効化
create extension if not exists vector;

-- ドキュメントテーブル
create table if not exists documents (
    id uuid default gen_random_uuid() primary key,
    title text not null,
    content text not null,
    doc_type text not null,
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
create index if not exists documents_created_at_idx on documents(created_at);

-- RLS (Row Level Security) 設定
alter table documents enable row level security;
alter table chunks enable row level security;

-- サービスロール用ポリシー（フルアクセス）
create policy if not exists "Service role can do everything on documents" 
    on documents for all 
    using (auth.jwt() ->> 'role' = 'service_role');

create policy if not exists "Service role can do everything on chunks" 
    on chunks for all 
    using (auth.jwt() ->> 'role' = 'service_role');

-- ストレージバケット作成
insert into storage.buckets (id, name, public)
values ('market-news-archive', 'market-news-archive', false)
on conflict (id) do nothing;

-- ストレージポリシー
create policy if not exists "Service role can manage archive files"
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

create trigger if not exists update_documents_updated_at
    before update on documents
    for each row execute procedure update_updated_at_column();

-- 完了メッセージ
select 'RAGシステム用データベースセットアップ完了' as message;'''
        
        sql_file = self.project_root / "scripts" / "supabase_rag_setup.sql"
        sql_file.parent.mkdir(exist_ok=True)
        
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write(sql_content)
        
        print(f"✅ Supabase SQLファイル作成: {sql_file}")
        print("   このSQLをSupabaseダッシュボードで実行してください")
    
    def _check_directories(self):
        """ディレクトリ構造確認"""
        required_dirs = [
            "src/rag",
            "src/database",
            "scripts"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                print(f"✅ {dir_path} 存在")
            else:
                print(f"❌ {dir_path} が見つかりません")
    
    def _verify_config_files(self):
        """設定ファイル確認"""
        config_files = [
            "src/config/app_config.py",
            "src/rag/rag_manager.py",
            "src/database/supabase_client.py"
        ]
        
        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                print(f"✅ {config_file} 存在")
            else:
                print(f"❌ {config_file} が見つかりません")
    
    def _print_next_steps(self):
        """次のステップを表示"""
        print("\n" + "=" * 50)
        print("🎯 次のステップ")
        print("=" * 50)
        
        steps = [
            "1. Supabaseプロジェクトを作成",
            "2. scripts/supabase_rag_setup.sqlをSupabaseダッシュボードで実行",
            "3. .envファイルにSupabase接続情報を設定",
            "4. 依存関係をインストール: pip install -r requirements.txt",
            "5. テストスクリプトを実行: python scripts/test_rag_system.py"
        ]
        
        for step in steps:
            print(f"   {step}")
        
        print("\n📚 参考資料:")
        print("   - Supabase: https://supabase.com/")
        print("   - プロジェクト作成: https://app.supabase.com/")
        print("   - ドキュメント: docs/SUPABASE_USAGE_GUIDE.md")


def main():
    """メイン実行関数"""
    setup = RAGEnvironmentSetup()
    success = setup.run_setup()
    
    if success:
        print("\n✨ 環境セットアップ完了！")
        print("上記の次のステップに従って設定を完了してください。")
    else:
        print("\n❗ セットアップ中にエラーが発生しました。")
        print("エラーを確認して再度実行してください。")
    
    return success


if __name__ == "__main__":
    exit(0 if main() else 1)