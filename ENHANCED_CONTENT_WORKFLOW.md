# 拡張SNSコンテンツ処理システム - 独立ワークフロー

## 概要

拡張SNSコンテンツ処理システムは、従来のニュース処理システムとは完全に独立して動作するワークフローです。リアルタイムマーケットデータ統合、AI記事分析の高度化、動的テンプレート選択、包括的な品質管理を提供します。

## 🌟 主要機能

### 1. マーケットデータ統合
- **リアルタイム市場データ取得**
  - Yahoo Finance & Stooq API統合
  - 株価指数、通貨ペア、商品価格の監視
  - 市場センチメント分析とボラティリティスコア計算

### 2. 拡張AI記事処理
- **高度な記事分析**
  - 市場コンテキストを統合したプロンプト最適化
  - カテゴリ・地域・センチメント・市場影響度の自動判定
  - 重要ポイント抽出と品質スコア算出

### 3. 動的テンプレートシステム
- **市場状況別テンプレート自動選択**
  - 市場暴落対応（MARKET_CRASH）
  - FRB政策フォーカス（FED_POLICY）
  - 決算シーズン（EARNINGS_SEASON）
  - 地政学リスク（GEOPOLITICAL）
  - 暗号資産フォーカス（CRYPTO_FOCUS）

### 4. 包括的品質管理
- **多層品質チェック**
  - 記事品質バリデーション（要約品質・情報完全性・言語品質）
  - 類似度チェック・重複記事検出
  - マーケットデータとのファクトチェック

## 🚀 使用方法

### ローカル実行

```bash
# 基本実行（テストモード）
python enhanced_content_main.py --test-mode

# ファイル入力による実行
python enhanced_content_main.py --input-file articles.json --output-file results.json

# 設定カスタマイズ実行
python enhanced_content_main.py \\
  --quality-threshold 80.0 \\
  --similarity-threshold 0.8 \\
  --disable-fact-check \\
  --log-level DEBUG
```

### GitHub Actions実行

#### 手動実行
1. GitHubリポジトリの「Actions」タブに移動
2. 「Enhanced Content Processing Workflow」を選択
3. 「Run workflow」をクリック
4. パラメータを設定して実行

#### 自動実行
- **スケジュール実行**: 平日の日本時間 9:00、12:00、18:00
- **プッシュトリガー**: `feature/enhanced-content` ブランチ

## 📁 ファイル構成

```
Market_News_Project/
├── enhanced_content_main.py           # メインワークフロー
├── enhanced_content_config.py         # 設定ファイル
├── src/ai/enhanced_summarizer.py      # 拡張AI要約処理
├── src/market_data/                   # マーケットデータ統合
├── src/content/                       # 動的コンテンツ生成
├── src/quality/                       # 品質管理システム
├── test_market_data_integration.py    # 統合テスト
├── test_basic_functionality.py       # 基本機能テスト
└── .github/workflows/enhanced-content-processing.yml
```

## ⚙️ 設定

### 環境変数

```bash
# 必須設定
export GEMINI_API_KEY="your-gemini-api-key"

# オプション設定
export MIN_QUALITY_SCORE="70.0"
export SIMILARITY_THRESHOLD="0.7"
export ENABLE_FACT_CHECK="true"
export ENABLE_MARKET_CONTEXT="true"
export LOG_LEVEL="INFO"
```

### 設定ファイル (`enhanced_content_config.py`)

```python
CONFIG = EnhancedContentConfig(
    MIN_QUALITY_SCORE=70.0,
    SIMILARITY_THRESHOLD=0.7,
    ENABLE_FACT_CHECK=True,
    ENABLE_MARKET_CONTEXT=True
)
```

## 🔧 カスタマイズ

### テンプレート追加

```python
TEMPLATE_DEFINITIONS["CUSTOM_TEMPLATE"] = {
    "name": "カスタムテンプレート",
    "priority": 85,
    "triggers": {
        "custom_keywords": ["特定のキーワード"],
        "condition": True
    },
    "sections": ["custom_section1", "custom_section2"]
}
```

### 品質基準調整

```python
QUALITY_CRITERIA["custom_check"] = {
    "description": "カスタム品質チェック",
    "weight": 0.1,
    "criteria": {"min_score": 50}
}
```

## 📊 出力例

### 処理結果JSON

```json
{
  "input_article_count": 2,
  "market_context": {
    "snapshot": {
      "sentiment": "neutral",
      "volatility_score": 45.3,
      "stock_indices_count": 6,
      "currency_pairs_count": 5
    }
  },
  "selected_template": {
    "template_type": "FED_POLICY"
  },
  "quality_check_results": {
    "summary": {
      "pass_rate": 85.0,
      "average_score": 78.2
    }
  },
  "enhanced_articles": [
    {
      "original_article": {...},
      "market_insights": {
        "market_sentiment": "neutral",
        "volatility_level": "Normal"
      },
      "quality_passed": true
    }
  ]
}
```

### 処理レポート

```
=== 拡張SNSコンテンツ処理レポート ===
処理日時: 2025-09-03T20:30:00+09:00
入力記事数: 2
拡張記事生成数: 2

市場センチメント: neutral
ボラティリティ: 45.3
選択テンプレート: FED_POLICY

品質チェック合格率: 85.0%
平均品質スコア: 78.2
類似記事ペア: 0組
コンテンツ多様性スコア: 0.847
```

## 🧪 テスト

### 基本機能テスト

```bash
python test_basic_functionality.py
```

### 統合テスト（依存パッケージ要）

```bash
pip install yfinance
python test_market_data_integration.py
```

## 🔄 システム独立性

本システムは既存のニュース処理システムと完全に独立しています：

- **独立した設定**: `enhanced_content_config.py`
- **独立したAI処理**: `src/ai/enhanced_summarizer.py`
- **独立したワークフロー**: `enhanced_content_main.py`
- **独立したGitHubActions**: `.github/workflows/enhanced-content-processing.yml`

従来の `main.py` や `ai_summarizer.py` には一切影響を与えません。

## 📋 依存関係

```txt
# 新規追加
yfinance>=0.2.18
requests>=2.28.0

# 既存依存関係
google-generativeai
pandas
python-dotenv
pydantic>=2.0.0
```

## 🚨 トラブルシューティング

### よくある問題

1. **APIキー未設定**
   ```
   ValueError: GEMINI_API_KEY が設定されていません
   ```
   → 環境変数 `GEMINI_API_KEY` を設定してください

2. **マーケットデータ取得失敗**
   ```
   WARNING: マーケットデータ取得失敗、デフォルトコンテキストを使用
   ```
   → ネットワーク接続またはAPI制限を確認してください

3. **モジュール読み込みエラー**
   ```
   ModuleNotFoundError: No module named 'yfinance'
   ```
   → `pip install yfinance` でパッケージをインストールしてください

## 📈 パフォーマンス

- **処理時間**: 記事1件あたり平均 3-5秒
- **API呼び出し**: 記事1件あたり Gemini API 1回 + マーケットデータ API 数回
- **メモリ使用量**: 約 50-100MB（マーケットデータキャッシュ含む）

## 🛠 開発・拡張

### 新機能追加の手順

1. `src/` 配下に新しいモジュール追加
2. `enhanced_content_config.py` に設定追加  
3. `enhanced_content_main.py` に処理統合
4. テストケース追加
5. ドキュメント更新

### コントリビューション

1. `feature/enhanced-content` ブランチで開発
2. テストの追加・実行
3. プルリクエスト作成

## 📄 ライセンス

このプロジェクトのライセンスに従います。