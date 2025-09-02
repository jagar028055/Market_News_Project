# 独立ポッドキャスト配信システム

Task 12で実装された、既存の6つのコンポーネントを統合した包括的なポッドキャスト配信ワークフローです。

## 🎯 概要

IndependentPodcastWorkflowクラスは、以下の6つのコンポーネントを統合したオーケストレータークラスです：

1. **GoogleDriveDocumentReader** - Google Drive文書からの記事データ読み取り
2. **DialogueScriptGenerator** - 対話形式ポッドキャスト台本生成
3. **GeminiTTSEngine** - 高品質音声合成
4. **AudioProcessor** - プロフェッショナル音声処理
5. **IndependentGitHubPagesPublisher** - GitHub Pages配信
6. **MessageTemplates + DistributionErrorHandler** - 通知・エラー処理

## 🚀 主な機能

### ワークフロー管理
- **9段階のステップ管理**: 初期化から配信完了まで
- **リアルタイム進行状況追跡**: 進行率、経過時間、残り時間の計算
- **包括的エラーハンドリング**: 各ステップでの適切なエラー処理
- **メトリクス記録**: 詳細な実行統計とパフォーマンス情報

### 設定管理
- **統合設定システム**: 336項目の環境変数を型安全に管理
- **バリデーション機能**: 設定の妥当性チェック
- **環境別設定**: デバッグ、テスト、プロダクション対応

### 品質管理
- **記事重要度計算**: センチメント、要約長、信頼度による自動厳選
- **音声品質管理**: LUFS正規化、ファイルサイズ制限
- **品質チェック**: 各ステップでの品質検証

## 📋 使用方法

### 基本的な実行

```bash
# コマンドライン実行
python -m src.podcast.main run

# ドライラン（設定確認のみ）
python -m src.podcast.main run --dry-run

# デバッグモード
python -m src.podcast.main run --debug

# ステータス確認
python -m src.podcast.main status

# 設定検証
python -m src.podcast.main validate
```

### プログラムから使用

```python
import asyncio
from src.podcast.workflow.independent_podcast_workflow import (
    IndependentPodcastWorkflow, 
    WorkflowConfig
)

# 設定作成
config = WorkflowConfig(
    google_document_id="your_document_id",
    gemini_api_key="your_api_key",
    github_repo_url="https://github.com/username/repo.git",
    github_pages_base_url="https://username.github.io/repo"
)

# ワークフロー実行
async def main():
    workflow = IndependentPodcastWorkflow(config)
    result = await workflow.execute_workflow()
    
    if result.success:
        print(f"配信成功: {result.audio_url}")
    else:
        print(f"配信失敗: {result.errors}")

asyncio.run(main())
```

## ⚙️ 設定

### 必須環境変数

```bash
# Google認証
GOOGLE_AUTH_METHOD=oauth2
GOOGLE_OAUTH2_CLIENT_ID=your_client_id
GOOGLE_OAUTH2_CLIENT_SECRET=your_client_secret
GOOGLE_OAUTH2_REFRESH_TOKEN=your_refresh_token
GOOGLE_DRIVE_DOCUMENT_ID=your_document_id

# Gemini API
GEMINI_API_KEY=your_gemini_key

# GitHub Pages配信
PODCAST_RSS_BASE_URL=https://username.github.io/repo
GITHUB_REPOSITORY_URL=https://github.com/username/repo.git
```

### 主要設定項目

```bash
# ポッドキャスト設定
PODCAST_RSS_TITLE="マーケットニュース10分"
PODCAST_AUTHOR_NAME="Market News AI"
PODCAST_TARGET_DURATION_MINUTES=10.0
PODCAST_MAX_FILE_SIZE_MB=15

# 音声品質
PODCAST_BITRATE=128k
PODCAST_LUFS_TARGET=-16.0
PODCAST_SAMPLE_RATE=44100

# スクリプト生成
PODCAST_TARGET_CHARACTER_COUNT_MIN=2400
PODCAST_TARGET_CHARACTER_COUNT_MAX=2800
PODCAST_MAX_ARTICLES_PROCESSED=5

# エラーハンドリング
PODCAST_MAX_RETRIES=3
PODCAST_RETRY_BACKOFF_SECONDS=60
```

## 🏗️ アーキテクチャ

### ワークフロー構成

```
1. 初期化
   ├── ディレクトリ作成
   ├── コンポーネント検証
   └── Google Drive接続確認

2. Google Drive文書読み取り
   ├── 文書メタデータ取得
   ├── 記事データ解析
   └── 構造化データ変換

3. 記事データ解析
   ├── 重要度スコア計算
   ├── センチメント分析
   └── 上位記事厳選

4. 台本生成
   ├── Gemini APIによる生成
   ├── 品質チェック
   └── 読みやすさ最適化

5. 音声合成
   ├── TTS実行
   ├── セグメント分割
   └── 音声データ結合

6. 音声処理
   ├── ラウドネス正規化
   ├── MP3エンコーディング
   └── メタデータ埋め込み

7. GitHub Pages配信
   ├── ファイルアップロード
   ├── RSS生成・更新
   └── 配信URL生成

8. 通知送信
   ├── メッセージ作成
   ├── LINE配信（オプション）
   └── 配信完了通知

9. クリーンアップ
   ├── 一時ファイル削除
   ├── キャッシュクリア
   └── エラーログ整理
```

### 設定システム階層

```
PodcastConfig (統合設定)
├── GoogleAuthConfig (Google認証)
├── GeminiConfig (Gemini AI)  
├── PodcastMetadataConfig (メタデータ)
├── AudioConfig (音声設定)
├── ScriptConfig (台本設定)
├── TTSConfig (TTS設定)
├── DirectoryConfig (ディレクトリ)
├── CostConfig (コスト管理)
├── ScheduleConfig (スケジュール)
├── ErrorHandlingConfig (エラー処理)
├── FileManagementConfig (ファイル管理)
├── QualityConfig (品質管理)
├── PerformanceConfig (パフォーマンス)
└── LineConfig (LINE配信)
```

## 📊 監視とメトリクス

### 進行状況監視

```python
# 進行状況取得
workflow = IndependentPodcastWorkflow(config)
progress = workflow.get_progress_info()

print(f"現在のステップ: {progress['current_step']}")
print(f"進行率: {progress['progress_percentage']:.1f}%")
print(f"経過時間: {progress['elapsed_time']:.1f}秒")
```

### コンポーネント状態確認

```python
# コンポーネント状態取得
status = workflow.get_component_status()

for component, info in status.items():
    print(f"{component}: {'✅ 初期化済み' if info['initialized'] else '⏳ 未初期化'}")
```

### 実行メトリクス

```json
{
  "execution_id": "market_news_20250808_1430",
  "success": true,
  "processing_time": 45.67,
  "articles_processed": 5,
  "file_size_mb": 12.3,
  "step_times": {
    "初期化": 0.12,
    "Google Drive文書読み取り": 2.34,
    "記事データ解析": 0.45,
    "台本生成": 8.90,
    "音声合成": 25.67,
    "音声処理": 5.43,
    "GitHub Pages配信": 2.10,
    "通知送信": 0.32,
    "クリーンアップ": 0.34
  }
}
```

## 🧪 テスト

### 単体テスト実行

```bash
# 全テスト実行
python -m pytest tests/podcast/ -v

# 特定テストクラス
python -m pytest tests/podcast/test_independent_podcast_workflow.py::TestIndependentPodcastWorkflow -v

# カバレッジ付き
python -m pytest tests/podcast/ --cov=src.podcast --cov-report=html
```

### 統合テスト

```bash
# 統合テスト（環境変数が必要）
INTEGRATION_TEST_ENABLED=true python -m pytest tests/podcast/ -m integration -v

# 実際のAPIを使用したテスト（慎重に実行）
GEMINI_API_KEY=your_key GOOGLE_DRIVE_DOCUMENT_ID=your_doc python -m pytest tests/podcast/ -m slow
```

## 🔧 トラブルシューティング

### 一般的な問題

1. **Google Drive認証エラー**
   ```bash
   # OAuth2セットアップ
   python setup_oauth2.py
   ```

2. **設定エラー**
   ```bash
   # 設定検証
   python -m src.podcast.main validate
   ```

3. **音声処理エラー**
   ```bash
   # FFmpegインストール確認
   ffmpeg -version
   
   # Homebrewでインストール（Mac）
   brew install ffmpeg
   ```

4. **依存関係エラー**
   ```bash
   # 依存関係再インストール
   pip install -r requirements.txt
   ```

### ログ確認

```bash
# ログディレクトリ
ls -la logs/podcast/

# 最新ログ確認
tail -f logs/podcast/podcast_$(date +%Y%m%d).log

# エラーログのみ確認
grep ERROR logs/podcast/podcast_*.log
```

### デバッグモード

```bash
# デバッグ情報付き実行
PODCAST_DEBUG_MODE=true python -m src.podcast.main run --debug

# 中間ファイル保持
PODCAST_DEBUG_SAVE_INTERMEDIATE_FILES=true python -m src.podcast.main run
```

## 📈 パフォーマンス

### 通常の実行時間

- **初期化**: ~0.1秒
- **記事読み取り**: ~2-3秒（キャッシュ有効時は~0.3秒）
- **台本生成**: ~8-12秒（記事数・文字数による）
- **音声合成**: ~20-30秒（台本長による）
- **音声処理**: ~3-8秒（FFmpeg処理）
- **配信**: ~1-3秒（ファイルサイズによる）

### 最適化のヒント

1. **キャッシュ活用**: Google Driveキャッシュで読み取り高速化
2. **並列処理**: 可能な部分での並列実行
3. **ファイルサイズ**: 音声品質と処理時間のバランス調整
4. **リトライ設定**: ネットワーク環境に応じた調整

## 🔄 GitHub Actions連携

### ワークフロー設定例

```yaml
name: Podcast Generation
on:
  schedule:
    - cron: '30 22 * * *'  # 毎日7:30 JST
  workflow_dispatch:

jobs:
  generate-podcast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          sudo apt-get update
          sudo apt-get install -y ffmpeg
      
      - name: Run Podcast Workflow
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          GOOGLE_OAUTH2_CLIENT_ID: ${{ secrets.GOOGLE_OAUTH2_CLIENT_ID }}
          GOOGLE_OAUTH2_CLIENT_SECRET: ${{ secrets.GOOGLE_OAUTH2_CLIENT_SECRET }}
          GOOGLE_OAUTH2_REFRESH_TOKEN: ${{ secrets.GOOGLE_OAUTH2_REFRESH_TOKEN }}
          GOOGLE_DRIVE_DOCUMENT_ID: ${{ secrets.GOOGLE_DRIVE_DOCUMENT_ID }}
          PODCAST_RSS_BASE_URL: https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}
        run: |
          python -m src.podcast.main run
      
      - name: Deploy to GitHub Pages
        if: success()
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./output/podcast-pages
          publish_branch: gh-pages
```

## 🔮 今後の拡張予定

- **多言語対応**: 英語ポッドキャスト生成
- **音声効果**: ジングル・BGM自動追加
- **分析機能**: 配信統計・視聴者フィードバック
- **配信チャンネル拡大**: Spotify、Apple Podcasts等
- **AI音声改善**: より自然な対話生成

## 📞 サポート

問題が発生した場合は：

1. [Issues](https://github.com/jagar028055/Market_News/issues)で報告
2. ログファイルの内容を含めて詳細を記載
3. 環境情報（OS、Python版、依存関係版）を明記

---

**独立ポッドキャスト配信システム v1.0**  
*高品質なAI生成ポッドキャストを自動配信*