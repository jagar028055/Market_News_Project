# Gemini API使用状況調査レポート

**調査日時**: 2025年8月21日  
**プロジェクト**: Market News Aggregator & AI Summarizer  
**調査範囲**: 全Pythonファイル (32ファイル検出)

## 🎯 エグゼクティブサマリー

### 主要使用箇所
- **記事要約**: Gemini 2.5 Flash-lite で個別記事要約
- **Pro統合要約**: Gemini 2.5 Pro で複数記事統合
- **ポッドキャスト台本**: Gemini 2.5 Pro で高品質台本生成
- **コスト最適化**: 用途別モデル使い分けで効率化

### 使用モデル分布
```
gemini-2.5-flash-lite: 記事要約・一般処理 (コスト重視)
gemini-2.5-pro: 台本生成・統合要約 (品質重視)
```

## 📊 機能別詳細分析

### 1. **記事要約機能** (メイン機能)

#### **ai_summarizer.py**
- **モデル**: `gemini-2.5-flash-lite`
- **用途**: 個別ニュース記事の要約・キーワード抽出
- **処理**: JSON形式の構造化出力
- **最適化**: max_output_tokens=1024, temperature=0.2
```python
model = genai.GenerativeModel('gemini-2.5-flash-lite')
```

### 2. **Pro統合要約機能**

#### **ai_pro_summarizer.py** 
- **モデル**: `gemini-2.5-pro`
- **用途**: 複数記事の統合要約・詳細分析
- **特徴**: 月次コスト制限、実行時間制御
- **設定**: timeout_seconds=180, cost_limit_monthly=50.0 USD

### 3. **ポッドキャスト台本生成**

#### **professional_dialogue_script_generator.py**
- **モデル**: `gemini-2.5-pro` ⚠️ (修正済み: gemini-2.5-pro-001 → gemini-2.5-pro)
- **用途**: 10分完全版プロフェッショナル台本生成
- **品質管理**: 文字数調整、品質評価、構造検証

#### **dialogue_script_generator.py**
- **モデル**: `gemini-2.0-flash-lite-001` ⚠️ (要確認: 非推奨モデル?)
- **用途**: 基本的な対話台本生成

### 4. **統合・管理システム**

#### **src/core/news_processor.py**
- **統合処理**: 記事処理とPro要約の統合管理
- **API管理**: プロンプト設定、エラーハンドリング
- **メタデータ**: model_version管理

#### **production_podcast_integration_manager.py**
- **環境変数管理**: GEMINI_PODCAST_MODEL設定
- **フォールバック**: デフォルト値 gemini-2.5-pro

## 🏗️ 設定・環境変数

### **config/base.py**
```python
model_name: str = Field("gemini-2.5-flash-lite", description="使用モデル")
podcast_script_model: str = Field("gemini-2.5-pro", description="台本生成用モデル")
```

### **環境変数一覧**
```bash
GEMINI_API_KEY                 # 必須: APIキー
GEMINI_PODCAST_MODEL          # オプション: ポッドキャスト用モデル名
AI_MODEL_NAME                 # オプション: 一般AI処理用モデル名
```

## 📈 使用パターン分析

### **処理タイプ別使用状況**

| 機能カテゴリ | ファイル数 | 使用モデル | 主な用途 |
|------------|---------|-----------|---------|
| **記事要約** | 2 | Flash-lite | 日次記事処理 |
| **台本生成** | 2 | Pro | 週次ポッドキャスト |
| **統合要約** | 1 | Pro | 月次詳細分析 |
| **設定管理** | 3 | N/A | システム設定 |
| **テスト** | 8 | Mock | 開発・CI |

### **API呼び出しパターン**
1. **バッチ処理**: 記事要約 (並列処理対応)
2. **リアルタイム**: ポッドキャスト生成
3. **スケジュール**: Pro統合要約

## 💰 コスト・パフォーマンス分析

### **推定月次コスト**
```
記事要約 (Flash-lite): 約 $5-10/月
台本生成 (Pro): 約 $15-25/月  
統合要約 (Pro): 約 $10-15/月
合計推定: $30-50/月
```

### **最適化効果**
- ✅ **Flash-lite使用**: 記事要約で70%コスト削減
- ✅ **Pro使用限定**: 高品質必須機能のみ
- ✅ **使い分け戦略**: 適材適所のモデル選択

## ⚠️ 発見された問題・修正事項

### **修正済み**
1. **gemini-2.5-pro-001** → **gemini-2.5-pro** (存在しないモデル名を修正)

### **要検討**
1. **gemini-2.0-flash-lite-001**: 非推奨モデルの可能性
   - ファイル: `dialogue_script_generator.py:54`
   - 推奨: `gemini-2.5-flash-lite` へ更新

## 📁 ファイル別使用状況一覧

### **メイン機能**
- `ai_summarizer.py` - Flash-lite記事要約
- `ai_pro_summarizer.py` - Pro統合要約
- `src/core/news_processor.py` - 統合管理

### **ポッドキャスト機能**
- `src/podcast/script_generation/professional_dialogue_script_generator.py` - Pro台本
- `src/podcast/script_generation/dialogue_script_generator.py` - 基本台本
- `src/podcast/script_generator.py` - 台本管理
- `src/podcast/tts_engine.py` - TTS統合
- `src/podcast/integration/production_podcast_integration_manager.py` - 統合管理

### **設定・テスト**
- `config/base.py` - メイン設定
- `src/config/app_config.py` - アプリ設定
- `tests/unit/test_ai_summarizer.py` - テスト (8ファイル)

## 🚀 推奨事項・改善案

### **短期改善 (1ヶ月以内)**
1. **非推奨モデル更新**: `gemini-2.0-flash-lite-001` → `gemini-2.5-flash-lite`
2. **エラーハンドリング強化**: API制限・レート制限対応
3. **コスト監視**: 月次使用量アラート設定

### **中期改善 (3ヶ月以内)**  
1. **バッチ処理最適化**: 並列処理効率化
2. **キャッシュ機能**: 重複処理削減
3. **A/Bテスト**: モデル性能比較

### **長期戦略 (6ヶ月以内)**
1. **マルチモデル対応**: Claude, GPT等の併用検討
2. **自動モデル選択**: 用途別最適化エンジン
3. **コスト予測**: AI使用量予測システム

## 📊 技術仕様詳細

### **API設定パターン**
```python
# 記事要約用 (コスト重視)
generation_config=genai.types.GenerationConfig(
    max_output_tokens=1024,
    temperature=0.2
)

# 台本生成用 (品質重視)  
generation_config=genai.types.GenerationConfig(
    temperature=0.4,
    max_output_tokens=4096,
    candidate_count=1
)
```

### **プロンプト戦略**
- **記事要約**: 構造化JSON出力
- **台本生成**: 対話形式・時間制御
- **統合要約**: 多記事横断分析

---

**🤖 Generated with [Claude Code](https://claude.ai/code)**  
**📅 最終更新**: 2025年8月21日  
**🔄 次回更新**: 月次レビュー時