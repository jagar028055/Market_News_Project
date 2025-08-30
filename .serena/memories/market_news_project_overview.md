# Market News Project Overview

## Project Purpose
Market News Aggregator & AI Summarizer - 金融・経済ニュースサイトから最新ニュースを自動収集し、AI（Google Gemini）による要約、Webページ公開、ポッドキャスト生成まで行う統合システム

## Tech Stack
- **Language**: Python 3.9-3.11
- **AI/ML**: Google Gemini API, sentence-transformers, Google Cloud Text-to-Speech
- **Database**: Supabase (PostgreSQL + pgvector), SQLite (開発環境)
- **Web**: GitHub Pages
- **External APIs**: Google Drive API, Google Docs API, LINE Bot
- **CI/CD**: GitHub Actions

## Project Structure
```
Market_News/
├── main.py                    # エントリーポイント
├── src/
│   ├── core/                  # コア処理ロジック
│   ├── config/                # 統一設定管理
│   ├── rag/                   # RAGシステム (new)
│   ├── podcast/               # ポッドキャスト機能
│   ├── database/              # データベース操作
│   └── html/                  # HTML生成
├── tests/                     # テストファイル
├── scripts/                   # ユーティリティスクリプト
└── docs/                      # ドキュメント
```

## Key Features
1. **ニュース収集**: ロイター、ブルームバーグから自動収集
2. **AI要約**: Gemini APIによる記事要約
3. **Webページ自動生成**: GitHub Pages公開
4. **ポッドキャスト生成**: Text-to-Speech + RSS配信
5. **RAGシステム**: 過去記事のベクトル検索・アーカイブ
6. **LINE Bot連携**: 配信通知

## RAG System Architecture
- **Database**: Supabase (PostgreSQL + pgvector)
- **Embedding**: sentence-transformers (384-dimensional vectors)
- **Storage**: Document chunking + vector storage
- **Search**: Cosine similarity + metadata filtering