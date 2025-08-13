# Flash+Pro Market News System - API仕様書

## コアAPI

### ProSummarizer API

#### 地域別要約生成
```python
from ai_pro_summarizer import ProSummarizer

summarizer = ProSummarizer(api_key="your_api_key")
regional_summaries = summarizer.generate_regional_summaries(grouped_articles)
```

**入力:**
- grouped_articles: Dict[str, List[Dict]] - 地域別グループ化された記事

**出力:**
- Dict[str, Dict] - 地域別要約結果

#### 全体要約生成
```python
global_summary = summarizer.generate_global_summary(all_articles, regional_summaries)
```

### ArticleGrouper API

#### 地域別グループ化
```python
from article_grouper import ArticleGrouper

grouper = ArticleGrouper()
grouped = grouper.group_articles_by_region(articles)
```

### CostManager API

#### コスト見積もり
```python
from cost_manager import CostManager

cost_manager = CostManager()
estimated_cost = cost_manager.estimate_cost(model_name, input_text, output_tokens)
```

## データ形式

### 記事データ形式
- title: 記事タイトル
- body: 記事本文  
- source: 情報源
- url: 記事URL
- published_at: 公開日時
- region: 地域分類
- category: カテゴリ分類

### 要約結果形式
- global_summary: 全体市況要約
- regional_summaries: 地域別要約辞書
- metadata: メタデータ（記事数など）

---
更新日: 2025-08-13
