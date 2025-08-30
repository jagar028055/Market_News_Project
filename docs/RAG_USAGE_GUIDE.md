# Market News RAGシステム 実用ガイド

## 📋 概要

Market NewsのRAG（Retrieval-Augmented Generation）システムが完全に実装され、使用可能な状態になりました。このガイドでは、実際の使用方法とベストプラクティスを説明します。

## 🎯 RAGシステムでできること

### 1. **記事の長期アーカイブ**
- 過去のニュース記事を構造化して保存
- ベクトル検索による高速な意味検索
- カテゴリ・地域・日時でのフィルタリング

### 2. **類似記事の発見**  
- 新しい記事に関連する過去記事の自動検出
- トピック別のトレンド分析
- コンテンツ重複の防止

### 3. **知識ベース構築**
- noteやブログ記事作成時の参考資料検索
- 投資判断のための過去事例参照
- レポート作成時の情報収集

## 🚀 基本的な使用方法

### 環境確認

まず、RAGシステムが利用可能か確認します：

```python
from src.rag.rag_manager import RAGManager

# システム初期化
rag = RAGManager()

# システム状態確認
status = rag.get_system_status()
print(f"システム健全性: {status['system_healthy']}")
print(f"Supabase接続: {status['supabase_available']}")
print(f"総ドキュメント数: {status['total_documents']}")
```

### 1. 記事のアーカイブ

日次収集した記事をアーカイブに保存：

```python
# 記事データの例
articles = [
    {
        "id": "reuters_20241230_001",
        "title": "日経平均、年末に向けて調整局面入り",
        "content": "東京株式市場では30日、日経平均株価が前日比...",
        "published_at": "2024-12-30T09:30:00Z",
        "category": "market",
        "region": "日本",
        "source": "reuters",
        "summary": "年末要因で調整売りが優勢"
    },
    {
        "id": "bloomberg_20241230_002", 
        "title": "FRB、来年の利下げペース慎重姿勢",
        "content": "米連邦準備理事会（FRB）は30日...",
        "published_at": "2024-12-30T14:15:00Z",
        "category": "central_bank",
        "region": "米国",
        "source": "bloomberg",
        "summary": "インフレ動向を注視し慎重な金融政策"
    }
]

# アーカイブ実行
result = rag.archive_articles(articles)
print(f"✅ {result['processed_articles']}件の記事をアーカイブしました")
print(f"📦 {result['created_chunks']}個のチャンクを作成しました")
```

### 2. 関連記事の検索

キーワードやトピックから関連記事を検索：

```python
# 意味検索の実行
results = rag.search_content(
    query="FRBの金利政策",
    limit=5,
    similarity_threshold=0.7,
    date_range={
        "start": "2024-11-01",
        "end": "2024-12-31"
    }
)

# 検索結果の表示
print(f"🔍 「FRBの金利政策」に関連する記事: {len(results)}件\n")

for i, result in enumerate(results, 1):
    print(f"{i}. {result.title}")
    print(f"   📅 {result.published_at}")
    print(f"   📈 類似度: {result.similarity:.3f}")
    print(f"   💬 {result.content[:100]}...")
    print(f"   🏷️ カテゴリ: {result.category}")
    print()
```

### 3. 特定記事の関連コンテンツ取得

新しい記事に関連する過去記事を自動発見：

```python
# 新しい記事
new_article = {
    "title": "日銀、物価目標達成へ政策修正検討",
    "content": "日本銀行は物価安定目標2%の持続的達成に向けて..."
}

# 関連記事の検索
related = rag.get_related_content(
    content=new_article["content"],
    limit=3,
    exclude_similar_titles=True
)

print(f"📊 関連記事: {len(related)}件")
for article in related:
    print(f"- {article.title} (類似度: {article.similarity:.3f})")
```

### 4. トレンド分析

期間指定でのトピック傾向分析：

```python
# 過去30日間のトレンド分析
trends = rag.get_trending_topics(
    days=30,
    min_articles=5,
    categories=["market", "central_bank", "economy"]
)

print("📈 トレンドトピック (過去30日):")
for trend in trends[:5]:
    print(f"- {trend['topic']}: {trend['article_count']}件")
    print(f"  平均類似度: {trend['avg_similarity']:.3f}")
```

## 💡 実践的な活用例

### A. 投資判断サポート

```python
# 特定銘柄の関連ニュース検索
company_news = rag.search_content(
    query="トヨタ自動車 業績 電動車",
    limit=10,
    date_range={"start": "2024-10-01"}
)

# 業績関連記事の分析
for news in company_news:
    if "決算" in news.title or "業績" in news.title:
        print(f"📊 {news.title}")
        print(f"   {news.summary}")
```

### B. ブログ記事作成サポート

```python
# 記事テーマに関連する過去情報の収集
theme = "2024年の金融市場回顧"

background_info = rag.search_content(
    query=theme,
    limit=15,
    date_range={"start": "2024-01-01", "end": "2024-12-31"}
)

# 情報の整理と活用
topics = {}
for info in background_info:
    category = info.category
    if category not in topics:
        topics[category] = []
    topics[category].append(info)

print("📝 ブログ記事用参考資料:")
for category, articles in topics.items():
    print(f"\n## {category.upper()} ({len(articles)}件)")
    for article in articles[:3]:
        print(f"- {article.title}")
```

### C. 日次レポート作成

```python
# 今日のニュースと関連する過去記事の組み合わせ
from datetime import datetime, timedelta

today = datetime.now().strftime("%Y-%m-%d")
week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

# 今日の主要ニュースから関連記事を検索
daily_summary = rag.search_content(
    query="株価 市場 動向",
    date_range={"start": today},
    limit=5
)

print(f"📊 {today} 市場レポート")
print("=" * 40)

for news in daily_summary:
    print(f"\n【{news.title}】")
    print(f"📅 {news.published_at}")
    print(f"💡 {news.summary}")
    
    # 関連する過去記事
    related = rag.get_related_content(news.content, limit=2)
    if related:
        print("🔗 関連記事:")
        for r in related:
            print(f"  - {r.title} ({r.published_at})")
```

## ⚙️ 設定とメンテナンス

### システム統計の確認

```python
# アーカイブ統計
stats = rag.get_archive_statistics()
print("📊 アーカイブ統計:")
print(f"  総記事数: {stats['total_articles']}件")
print(f"  総チャンク数: {stats['total_chunks']}件")
print(f"  平均チャンク/記事: {stats['avg_chunks_per_article']:.1f}個")
print(f"  最古の記事: {stats['oldest_article']}")
print(f"  最新の記事: {stats['newest_article']}")
```

### 古いデータのクリーンアップ

```python
# 90日より古いデータの削除（オプション）
cleanup_result = rag.cleanup_old_data(days=90)
print(f"🗑️  {cleanup_result['deleted_documents']}件の古い記事を削除")
print(f"💾 {cleanup_result['freed_storage_mb']:.1f}MBの容量を解放")
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

1. **「Supabase接続エラー」**
   ```bash
   # 環境変数の確認
   echo $SUPABASE_URL
   echo $SUPABASE_ENABLED
   ```

2. **「検索結果が空」**
   ```python
   # 類似度閾値を下げる
   results = rag.search_content("キーワード", similarity_threshold=0.5)
   ```

3. **「パフォーマンスが遅い」**
   ```python
   # インデックス状態確認
   integrity = rag.validate_system_integrity()
   print(f"インデックス効率: {integrity['index_efficiency']}")
   ```

## 📈 パフォーマンス最適化

### 効率的な検索のコツ

1. **具体的なキーワードを使用**
   - ❌ `"経済"`
   - ✅ `"日銀 金利政策 インフレ目標"`

2. **日付範囲で絞り込み**
   ```python
   # 最近1ヶ月に絞って高速化
   results = rag.search_content(
       query="キーワード",
       date_range={"start": "2024-12-01"}
   )
   ```

3. **カテゴリフィルタ活用**
   ```python
   # 特定カテゴリのみ検索
   results = rag.search_content(
       query="キーワード", 
       filters={"category": ["market", "economy"]}
   )
   ```

## 🔄 Market Newsワークフローとの統合

### 日次処理での自動アーカイブ

既存の`main.py`にRAGアーカイブ機能を統合：

```python
# main.pyでの実装例
from src.rag.rag_manager import RAGManager

def main():
    # 既存のニュース収集処理
    articles = collect_news_articles()
    
    # AI要約処理
    summarized_articles = generate_ai_summaries(articles)
    
    # RAGアーカイブに保存 (新機能)
    rag = RAGManager()
    if rag.is_available():
        archive_result = rag.archive_articles(summarized_articles)
        print(f"📚 {archive_result['processed_articles']}件をアーカイブ")
    
    # 既存のWeb公開処理
    generate_html_report(summarized_articles)
    
if __name__ == "__main__":
    main()
```

## 🎯 まとめ

Market NewsのRAGシステムにより、以下が実現できます：

✅ **過去記事の効率的な検索と活用**
✅ **関連情報の自動発見**  
✅ **トレンド分析とパターン認識**
✅ **コンテンツ作成の支援**
✅ **投資判断の情報基盤**

システムは完全に動作可能な状態で、既存のワークフローに簡単に統合できます。

---

> **🚀 始め方**: `rag = RAGManager()`でシステム初期化 → `rag.archive_articles()`で記事保存 → `rag.search_content()`で検索開始！