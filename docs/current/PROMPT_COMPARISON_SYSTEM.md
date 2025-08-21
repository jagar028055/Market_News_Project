# 🔍 7プロンプトパターン一括比較システム

## 📋 概要

市場ニュースポッドキャストシステム向けの7つのプロンプトパターンを一括実行し、品質・効率・コストを比較分析する統合システムです。

### ✨ 主要機能

- **7つのプロンプトパターン同時実行**: 並列処理による高速比較
- **詳細メトリクス分析**: 品質・パフォーマンス・コスト分析
- **Googleドキュメント出力**: 構造化された比較レポート自動生成
- **GitHub Actions統合**: 自動化された継続的比較テスト
- **音声生成スキップ**: 台本品質に特化した高速テスト

## 🏗️ システム構成

### Core Components

1. **PromptPatternComparisonRunner** (`prompt_pattern_comparison_runner.py`)
   - メインエントリーポイント
   - 7つのプロンプトパターン一括実行制御
   - 記事データ取得とGoogleドキュメント出力統合

2. **Enhanced ABTestManager** (`src/podcast/prompts/ab_test_manager.py`)
   - 比較テスト実行エンジン
   - 拡張メトリクス分析（品質・パフォーマンス・コスト）
   - 統計分析と推奨事項生成

3. **ComparisonDocGenerator** (`src/podcast/gdocs/comparison_doc_generator.py`)
   - Googleドキュメント比較レポート生成
   - 構造化されたビジュアルレポート
   - パターン別台本の並列表示

4. **GitHub Actions Workflow** (`.github/workflows/prompt-comparison-test.yml`)
   - 自動化された比較テスト環境
   - 実行結果の自動アーカイブ
   - 失敗時の詳細レポート生成

## 📊 プロンプトパターン（7種類）

| パターン | 名称 | 特徴 | 目的 |
|---------|------|------|------|
| `current_professional` | 現在のプロフェッショナル版 | 現在使用中のベースライン | 比較基準 |
| `cot_enhanced` | 構造化思考誘導型 | 3ステップ思考プロセス | 品質安定化 |
| `enhanced_persona` | 役割演技強化型 | 具体的キャラクター設定 | 一貫性向上 |
| `few_shot_learning` | 例示学習型 | 理想的サンプル提示 | 品質基準明確化 |
| `constraint_optimization` | 制約条件最適化型 | 厳密な制約条件 | 品質均一化 |
| `context_aware` | コンテキスト重視型 | 記事間関連性重視 | 包括的解説 |
| `minimalist` | 簡潔指示型 | 不要装飾排除 | 効率性重視 |

## 🚀 使用方法

### ローカル実行

```bash
# 必要な環境変数を設定
export GEMINI_API_KEY="your-api-key"
export PODCAST_DATA_SOURCE="database"  # または "google_document"
export COMPARISON_TARGET_ARTICLES="15"

# システム実行
python prompt_pattern_comparison_runner.py
```

### GitHub Actions実行

1. GitHub Actions タブを開く
2. "7-Prompt Pattern Comparison Test" を選択
3. "Run workflow" をクリック
4. パラメータを設定して実行

#### 実行パラメータ

- **data_source**: `database` または `google_document`
- **target_articles**: 対象記事数（デフォルト: 15）
- **skip_audio**: 音声生成スキップ（推奨: true）
- **generate_gdoc**: Googleドキュメントレポート生成（推奨: true）

## 📈 比較分析メトリクス

### 品質メトリクス

- **品質スコア**: 構造・可読性・専門性の総合評価
- **文字数適合性**: 目標文字数（2700文字）への近似度
- **一貫性**: エラー発生率・安定性評価

### パフォーマンスメトリクス

- **生成時間**: 台本生成にかかる時間
- **効率性**: 品質スコア/生成時間の比率
- **処理速度分類**: 高速・中速・低速パターンの分類

### コストメトリクス（推定）

- **API利用コスト**: Gemini API使用料金の推定
- **コスト効率**: 品質/コストの比率
- **コスト per 品質ポイント**: 単位品質あたりのコスト

## 📄 出力レポート構成

### Googleドキュメントレポート

1. **実行サマリー**: 実行時間・対象記事数・システム設定
2. **パターン別詳細結果**: 各パターンの個別結果と台本プレビュー
3. **品質比較表**: パターン別メトリクスの一覧表
4. **推奨パターン**: 総合評価に基づく最優秀パターン
5. **詳細メトリクス**: 統計分析結果と分布情報
6. **推奨事項**: システム改善提案と運用提案

### JSON結果ファイル

```json
{
  "comparison_id": "comparison_20241221_143022",
  "execution_timestamp": "2024-12-21T14:30:22.123456",
  "total_execution_time_seconds": 180.5,
  "system_config": {...},
  "articles_metadata": {...},
  "comparison_results": {
    "pattern_results": {...},
    "comparison_analysis": {
      "quality_analysis": {...},
      "performance_analysis": {...},
      "cost_analysis": {...},
      "best_pattern": {...},
      "recommendations": [...]
    }
  },
  "google_document": {
    "document_url": "https://docs.google.com/...",
    "success": true
  }
}
```

## 🛠️ 設定ファイル

### プロンプト設定 (`src/podcast/prompts/configs/prompt_configs.yaml`)

```yaml
patterns:
  current_professional:
    name: "現在のプロフェッショナル版"
    description: "現在使用中のプロンプト"
    template_file: "current_professional.txt"
    target_chars: 2700
    temperature: 0.4
    enabled: true
```

## 🔧 技術仕様

### 必要環境変数

#### 必須

- `GEMINI_API_KEY`: Gemini API認証キー
- `PODCAST_DATA_SOURCE`: データソース（`database` or `google_document`）

#### Googleドキュメント出力用（オプション）

- `GOOGLE_OAUTH2_CLIENT_ID`: Google OAuth2 クライアントID
- `GOOGLE_OAUTH2_CLIENT_SECRET`: Google OAuth2 クライアントシークレット
- `GOOGLE_OAUTH2_REFRESH_TOKEN`: Google OAuth2 リフレッシュトークン

#### データベース接続用（オプション）

- `DATABASE_URL`: データベース接続URL

### システム要件

- Python 3.11+
- 必要なPythonパッケージ（`requirements.txt`参照）
- FFmpeg（音声処理用、GitHub Actionsで自動インストール）

## 📊 実行例

### 成功例

```
🚀 7プロンプトパターン一括比較システム開始
──────────────────────────────────────────────────────────
📊 比較ID: comparison_20241221_143022
⏱️  実行時間: 180.5秒
📰 対象記事数: 15

📋 パターン別実行結果:
──────────────────────────────────
✅ current_professional:
   文字数: 2,689, 品質: 0.834, 時間: 32.1秒
✅ cot_enhanced:
   文字数: 2,721, 品質: 0.851, 時間: 28.7秒
✅ enhanced_persona:
   文字数: 2,695, 品質: 0.829, 時間: 35.2秒
...

📈 実行サマリー:
  成功: 6パターン
  失敗: 1パターン

🏆 最優秀パターン: cot_enhanced
  総合スコア: 0.892

📄 Googleドキュメント: https://docs.google.com/document/d/...

🎉 比較システム実行完了
```

## 🎯 運用推奨

### 定期実行

- **週次**: 新プロンプトパターンのテスト
- **月次**: 全パターンの包括的比較
- **変更時**: プロンプト修正後の検証

### 品質指標

- **品質スコア**: 0.8以上を推奨
- **生成時間**: 60秒以内を推奨
- **文字数**: 2650-2750文字を推奨

### 改善提案

1. **高品質パターンの標準化**: スコア0.8以上のパターンを基準化
2. **効率性重視**: 時間効率の良いパターンの優先採用
3. **継続的改善**: 定期比較による段階的品質向上

## 🔍 トラブルシューティング

### よくある問題

1. **API制限エラー**: Gemini APIの利用制限を確認
2. **Google認証エラー**: OAuth2トークンの有効期限を確認
3. **メモリ不足**: 大量記事処理時のシステムリソース確認
4. **プロンプトファイル不足**: テンプレートファイルの存在確認

### ログファイル

- `logs/prompt_comparison.log`: システム実行ログ
- `prompt_comparison_results/*.json`: 比較結果詳細データ

## 📝 更新履歴

- **v1.0** (2024-12-21): 初期実装
  - 7プロンプトパターン比較機能
  - Googleドキュメント出力機能
  - GitHub Actions統合
  - 拡張分析エンジン

## 👥 貢献

プロンプトパターンの改善提案や新機能要望は、GitHub Issuesまでお願いします。

## 📄 ライセンス

このプロジェクトのライセンスについては、プロジェクトルートのLICENSEファイルを参照してください。