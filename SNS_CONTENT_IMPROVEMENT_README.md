# SNSコンテンツ機能改善システム

## 📋 概要

このプロジェクトは、Market News Projectに対してSNSコンテンツ機能の大幅な改善を実装したものです。マーケットデータとAI分析を統合し、より多様で高品質なニュース記事生成システムを提供します。

## 🚀 主要な改善点

### 1. マーケットデータ統合システム 📈
- **リアルタイム市場データ取得**: Yahoo Finance、Stooqからの主要指標取得
- **統合データモデル**: 株価指数、通貨ペア、商品価格の統一管理
- **市場センチメント分析**: ボラティリティ、トレンド、リスクオン/オフの自動判定

### 2. AI記事生成プロンプト最適化 🤖
- **動的プロンプト生成**: 市場状況に応じたコンテキスト自動調整
- **市場連動型分析**: 現在の市場データを記事分析に反映
- **多様性向上**: 市場状況別の分析観点自動切り替え

### 3. 動的テンプレートシステム 📄
- **状況適応型テンプレート**: 市場急落、FED政策、決算シーズン等に対応
- **自動テンプレート選択**: 記事内容と市場状況から最適なテンプレート判定
- **動的セクション生成**: 市況に応じたコンテンツセクション自動生成

### 4. 品質管理・バリデーションシステム ✅
- **コンテンツ品質評価**: 要約品質、情報完全性、言語品質の多角的評価
- **類似度・重複チェック**: 記事間の類似性評価とコンテンツ多様性確保
- **ファクトチェック機能**: マーケットデータとの整合性自動検証

## 🏗️ アーキテクチャ

```
SNSコンテンツ機能改善システム/
├── src/market_data/              # マーケットデータ取得
│   ├── models.py                 # データモデル定義
│   ├── fetcher.py               # 統合データ取得
│   ├── yahoo_finance_client.py   # Yahoo Finance API
│   └── stooq_client.py          # Stooq API
├── src/content/                  # 動的コンテンツ生成
│   ├── template_selector.py     # テンプレート選択
│   └── dynamic_sections.py      # 動的セクション生成
├── src/quality/                  # 品質管理
│   ├── content_validator.py     # コンテンツ品質評価
│   ├── similarity_checker.py    # 類似度チェック
│   └── fact_checker.py          # ファクトチェック
└── test_market_data_integration.py  # 統合テスト
```

## 🔧 セットアップと使用方法

### 前提条件
```bash
pip install yfinance>=0.2.18
```

### 基本使用例

#### 1. マーケットデータ取得
```python
from src.market_data.fetcher import MarketDataFetcher

# マーケットデータフェッチャーの初期化
fetcher = MarketDataFetcher()

# 現在の市場スナップショット取得
snapshot = fetcher.get_current_market_snapshot()
print(f"市場センチメント: {snapshot.overall_sentiment.value}")
print(f"ボラティリティ: {snapshot.volatility_score:.1f}")

# LLM用コンテキスト生成
context = fetcher.get_market_context_for_llm()
```

#### 2. 拡張AI記事生成
```python
from ai_summarizer import process_article_with_ai

# マーケットコンテキスト付きで記事処理
result = process_article_with_ai(
    api_key="your_gemini_api_key",
    text="記事本文...",
    market_context=None  # Noneの場合は自動生成
)
```

#### 3. 動的テンプレート選択
```python
from src.content.template_selector import TemplateSelector
from src.content.dynamic_sections import DynamicSectionGenerator

# テンプレート選択
selector = TemplateSelector()
template_type = selector.select_template(market_snapshot, articles)

# 動的セクション生成
generator = DynamicSectionGenerator()
sections = generator.generate_sections(template_type, market_snapshot, articles)
```

#### 4. 品質チェック
```python
from src.quality.content_validator import ContentValidator
from src.quality.similarity_checker import SimilarityChecker

# コンテンツ品質評価
validator = ContentValidator()
validation_results = validator.validate_article_batch(articles)

# 類似度チェック
similarity_checker = SimilarityChecker()
similarity_results = similarity_checker.check_similarity_batch(articles)
```

## 🧪 テスト実行

統合テストスクリプトで全機能をテスト可能：

```bash
python test_market_data_integration.py
```

テスト内容：
- ✅ マーケットデータ取得機能
- ✅ 拡張AIサマライザー
- ✅ 動的テンプレートシステム  
- ✅ 品質管理システム
- ✅ システム統合確認

## 📊 期待される効果

### コンテンツ品質向上
- **多様性向上**: 市場状況に応じた異なる視点の記事生成
- **精度向上**: マーケットデータと連動した事実確認機能
- **一貫性向上**: 品質基準の自動チェックとバリデーション

### 運用効率化
- **自動品質管理**: 記事品質の自動評価とフィードバック
- **重複排除**: 類似記事の自動検出と多様性確保
- **状況適応**: 市場状況に応じた自動テンプレート切り替え

### データ活用拡大
- **リアルタイム統合**: 最新市場データとニュース記事の融合
- **コンテキスト豊富化**: 市場背景を踏まえた深い分析記事生成
- **トレンド追従**: 市場動向に応じた適応的コンテンツ生成

## 🔗 既存システムとの統合

このシステムは既存のMarket News Projectのアーキテクチャを活用し、以下の箇所と統合されます：

- **`src/core/news_processor.py`**: メイン処理ロジックとの統合
- **`ai_summarizer.py`**: 既存AI処理システムの拡張
- **`market_news_config.py`**: 設定システムの機能拡張
- **`src/html/html_generator.py`**: HTML生成への動的コンテンツ反映

## 📝 設定項目

### 環境変数
```bash
GEMINI_API_KEY=your_gemini_api_key  # 必須: Gemini API
# その他既存の環境変数
```

### カスタマイズ可能項目
- **市場データ取得間隔**: キャッシュ保持時間の調整
- **品質評価基準**: バリデーション閾値のカスタマイズ
- **テンプレート選択条件**: 市場状況判定基準の調整
- **類似度検出感度**: 重複記事判定の精度調整

## 🚨 注意事項

1. **API制限**: Yahoo FinanceやStooqのAPI制限に注意
2. **データ品質**: 無料APIのデータ品質と更新頻度を考慮
3. **処理時間**: マーケットデータ取得による若干の処理時間増加
4. **依存関係**: yfinanceライブラリの追加が必要

## 🔄 今後の拡張案

- **より多くのデータソース**: Alpha Vantage、IEX Cloud等の統合
- **機械学習モデル**: より高度な市場予測モデルの統合
- **リアルタイム更新**: WebSocket等によるリアルタイムデータ更新
- **A/Bテスト機能**: コンテンツ効果の測定・最適化機能

---

📅 **実装日**: 2025年9月3日  
🏷️ **バージョン**: 1.0.0  
👨‍💻 **実装**: SNSコンテンツ機能改善プロジェクト