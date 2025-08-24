# Supabase & RAG システム 完全ガイド

Market NewsプロジェクトにおけるSupabaseベースのRAG（Retrieval-Augmented Generation）システムの完全ドキュメント集です。

## 📂 ドキュメント構成

### 🚀 クイックスタート
- **[NEXT_STEPS.md](./NEXT_STEPS.md)** - **まずここから！** セットアップと初回実行ガイド

### 📋 基本ガイド  
- **[SUPABASE_USAGE_GUIDE.md](./SUPABASE_USAGE_GUIDE.md)** - Supabase利用の全体的な方針とベストプラクティス

### 🔧 RAG システム詳細
- **[rag/README.md](./rag/README.md)** - RAG関連ドキュメントの索引
- **[rag/01_RAG_SYSTEM_GUIDE.md](./rag/01_RAG_SYSTEM_GUIDE.md)** - システム全体像とアーキテクチャ（Mermaid図解付き）
- **[rag/02_DATA_FLOW_DETAILS.md](./rag/02_DATA_FLOW_DETAILS.md)** - データ処理の内部仕組み詳細
- **[rag/04_QUICK_START_GUIDE.md](./rag/04_QUICK_START_GUIDE.md)** - 5分で始められるRAGシステム利用法

---

## 🎯 読み方ガイド

### 初回セットアップの方へ
1. **[NEXT_STEPS.md](./NEXT_STEPS.md)** でSupabaseセットアップを完了
2. **[rag/04_QUICK_START_GUIDE.md](./rag/04_QUICK_START_GUIDE.md)** で基本操作を習得

### システム理解を深めたい方へ
1. **[rag/01_RAG_SYSTEM_GUIDE.md](./rag/01_RAG_SYSTEM_GUIDE.md)** で全体像を把握
2. **[rag/02_DATA_FLOW_DETAILS.md](./rag/02_DATA_FLOW_DETAILS.md)** で技術詳細を理解

### 運用・設定を調整したい方へ
- **[SUPABASE_USAGE_GUIDE.md](./SUPABASE_USAGE_GUIDE.md)** でベストプラクティスを確認

---

## ⚡ システム概要

**Market News RAGシステム**は以下を提供します：

- 📚 **記事アーカイブ**: 過去の記事を構造化して長期保存
- 🔍 **類似記事検索**: ベクター検索による高精度な関連記事発見  
- 📈 **トレンド分析**: 期間指定でのトピック傾向分析
- 🎯 **知識ベース**: note・SNS・レポート生成への活用

## 🛠 技術スタック

- **データベース**: Supabase (PostgreSQL + pgvector)
- **ベクター生成**: sentence-transformers (384次元)
- **検索**: コサイン類似度 + メタデータフィルタ
- **アーカイブ**: JSON + Markdown形式での構造化保存

---

## 📞 サポート

システムに関する質問や問題があれば、各ドキュメントのトラブルシューティング章を参照してください。

**Happy Coding! 🎉**