# RAGシステム クイックスタートガイド

5分でRAGシステムを動かせるセットアップガイドです。

## 🚀 5分セットアップ

### ステップ1: Supabaseプロジェクト作成 (1分)

1. **Supabaseアカウント作成**
   - https://supabase.com/ にアクセス
   - 「Start your project」をクリック
   - GitHubでサインアップ

2. **新規プロジェクト作成**
   - 「New project」をクリック
   - プロジェクト名: `market-news-rag`
   - パスワード: 強力なパスワードを設定
   - 地域: `Asia Pacific (Tokyo)`

### ステップ2: データベースセットアップ (2分)

1. **SQLエディタを開く**
   - 左メニュー「SQL Editor」をクリック
   
2. **RAG用テーブル作成**
   ```sql
   -- このSQLをコピー&ペーストして実行
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
   
   -- ストレージバケット作成
   insert into storage.buckets (id, name, public)
   values ('market-news-archive', 'market-news-archive', false)
   on conflict (id) do nothing;
   
   -- 完了メッセージ
   select 'RAGシステム用データベースセットアップ完了' as message;
   ```

3. **実行結果確認**
   - 「RAGシステム用データベースセットアップ完了」が表示されればOK

### ステップ3: 環境変数設定 (1分)

1. **API情報を取得**
   - 左メニュー「Settings」→「API」
   - 以下の値をコピー：
     - Project URL
     - anon public key
     - service_role secret key

2. **`.env`ファイル設定**
   ```bash
   # Market_Newsディレクトリの.envファイルを編集
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_ANON_KEY=your_anon_key_here
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
   SUPABASE_ENABLED=true
   SUPABASE_BUCKET=market-news-archive
   ```

### ステップ4: 依存関係インストール (1分)

```bash
# プロジェクトディレクトリで実行
cd "/Users/satoissei/Desktop/VS Code/Cline/Market_News"

# 仮想環境をアクティブ化
source .venv/bin/activate

# RAG関連パッケージをインストール
pip install supabase sentence-transformers numpy faiss-cpu
```

### ステップ5: 動作確認テスト (30秒)

```bash
# テストスクリプト実行
python scripts/test_rag_system.py
```

**期待する出力:**
```
🚀 RAGシステム テスト開始
==================================================
🔧 設定確認
✅ 基本設定OK
   URL: https://your-project.supabase.co...
   バケット: market-news-archive
   埋め込みモデル: sentence-transformers/all-MiniLM-L6-v2

📋 Supabase接続テスト
✅ ドキュメント作成成功: uuid-here
結果: ✅ 成功

🎉 全テスト成功！RAGシステムは正常に動作しています。
```

## 🎯 基本的な使い方

### 記事をアーカイブする

```python
from src.rag.rag_manager import RAGManager
from src.config.app_config import AppConfig

# 初期化
config = AppConfig()
rag = RAGManager(config)

# サンプル記事をアーカイブ
articles = [{
    "id": "sample_001",
    "title": "AI技術の最新動向",
    "content": "本日、大手テクノロジー企業が新しいAI技術を発表...",
    "published_at": "2024-08-24T10:30:00Z",
    "category": "technology",
    "summary": "新AI技術により市場が活性化"
}]

result = rag.archive_articles(articles)
print(f"✅ {result['processed_articles']}件をアーカイブしました")
```

### コンテンツを検索する

```python
# 意味検索を実行
results = rag.search_content("AI技術", limit=5)

for result in results:
    print(f"タイトル: {result.title}")
    print(f"内容: {result.content[:100]}...")
    print(f"類似度: {result.similarity:.3f}")
    print("---")
```

### システム状態を確認する

```python
# システムの健全性をチェック
status = rag.get_system_status()

print(f"システム健全性: {status['system_healthy']}")
print(f"総ドキュメント数: {status['total_documents']}")
print(f"総チャンク数: {status['total_chunks']}")
print(f"Supabase接続: {status['supabase_available']}")
```

## 🛠️ よくある問題と解決方法

### エラー1: 「pgvector extension not found」
```bash
# 解決方法: SQLエディタで再実行
create extension if not exists vector;
```

### エラー2: 「Permission denied for table」
```bash
# 解決方法: RLSポリシー確認
# SQLエディタで実行:
alter table documents enable row level security;
alter table chunks enable row level security;
```

### エラー3: 「Module not found: supabase」
```bash
# 解決方法: 依存関係を再インストール
pip install -r requirements.txt
```

### エラー4: 「Connection timeout」
```bash
# 解決方法: 環境変数を再確認
cat .env | grep SUPABASE
# URL, KEYが正しく設定されているか確認
```

## 🚀 次のステップ

### レベル1: 基本操作をマスター
- [使用例集](./06_USE_CASES.md)で実用的な使い方を学ぶ
- デモスクリプト実行: `python scripts/demo_rag_usage.py`

### レベル2: 既存システムと連携
- Market Newsの日次処理にRAGアーカイブを組み込む
- Web APIエンドポイントを作成

### レベル3: カスタマイズ
- [技術仕様書](./03_TECHNICAL_SPECIFICATION.md)で内部構造を理解
- チャンクサイズやベクトル次元の調整

## 📋 設定確認チェックリスト

- [ ] Supabaseプロジェクトが作成済み
- [ ] データベーステーブルが作成済み
- [ ] 環境変数(.env)が正しく設定済み
- [ ] 依存関係がインストール済み
- [ ] テストスクリプトが正常実行
- [ ] サンプル記事のアーカイブ成功
- [ ] サンプル検索が正常動作

## 🆘 サポート

問題が発生した場合:
1. **エラーメッセージを確認** - 上記のよくある問題をチェック
2. **システム状態確認** - `get_system_status()`でシステム健全性をチェック
3. **設定再確認** - 環境変数とSupabase設定を再確認

---

> **🎉 お疲れさまでした！** RAGシステムのセットアップが完了しました。これで過去の記事を意味検索できるようになりました。