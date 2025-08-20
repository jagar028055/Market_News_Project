# 次セッション作業ガイド - 10分本番ポッドキャスト実装

## 🎯 次セッションの目標

**10分本番ポッドキャスト (Gemini 2.5 Pro対応) の完全実装・配信開始**

---

## 📋 今セッションの完了状況

### ✅ 完了したタスク
1. **要件定義書作成** - `PODCAST_PRODUCTION_REQUIREMENTS.md`
2. **masterブランチ同期** - 最新データベース構造確認完了
3. **拡張データベース記事フェッチャー実装** - category/region対応
4. **Gemini 2.5 Pro台本生成器実装** - 高品質10分台本対応
5. **プロダクション統合管理システム実装** - 完全自動化ワークフロー
6. **詳細実装タスク分解** - `PODCAST_PRODUCTION_IMPLEMENTATION_TASKS.md`

### 📁 作成されたファイル
```
src/podcast/data_fetcher/enhanced_database_article_fetcher.py     ✅ 新規作成
src/podcast/script_generation/professional_dialogue_script_generator.py  ✅ 新規作成  
src/podcast/integration/production_podcast_integration_manager.py  ✅ 新規作成
PODCAST_PRODUCTION_REQUIREMENTS.md     ✅ 新規作成
PODCAST_PRODUCTION_IMPLEMENTATION_TASKS.md  ✅ 新規作成
NEXT_SESSION_GUIDE.md  ✅ 新規作成（このファイル）
```

---

## 🔧 次セッション最優先タスク

### Phase 2.1: 設定ファイル更新（必須・最優先）

#### 1. 環境変数設定
```bash
# Termux環境での設定コマンド
export GEMINI_PODCAST_MODEL="gemini-2.5-pro-001"
export PODCAST_PRODUCTION_MODE="true"
export PODCAST_TEST_MODE="false"
export PODCAST_TARGET_DURATION_MINUTES="10"
```

#### 2. config/base.py 拡張
以下の設定クラスを追加：
```python
@dataclass
class PodcastProductionConfig:
    gemini_model: str = "gemini-2.5-pro-001"
    production_mode: bool = True
    target_duration_minutes: int = 10
    target_character_count_min: int = 2600
    target_character_count_max: int = 2800
    quality_threshold: float = 80.0
```

### Phase 2.2: GitHub Actions ワークフロー更新（必須）

#### `.github/workflows/podcast-broadcast.yml` 更新箇所：

```yaml
# 環境変数追加
env:
  GEMINI_PODCAST_MODEL: "gemini-2.5-pro-001"
  PODCAST_PRODUCTION_MODE: "true"
  PODCAST_TARGET_DURATION_MINUTES: "10"

# Pythonスクリプト部分を以下に置換：
- name: Generate Production Podcast
  run: |
    python -c "
    from src.podcast.integration.production_podcast_integration_manager import ProductionPodcastIntegrationManager
    from config.base import get_config
    
    config = get_config()
    manager = ProductionPodcastIntegrationManager(config)
    result = manager.generate_complete_podcast(test_mode=False)
    
    if result['success']:
        print('✅ Production podcast generated successfully')
        print(f'📊 Script length: {result[\"execution_summary\"][\"script_length\"]} chars')
        print(f'🎧 Audio duration: {result[\"execution_summary\"][\"audio_duration_seconds\"]} seconds')
        print(f'📻 LINE broadcast: {result[\"execution_summary\"][\"line_broadcast_success\"]}')
    else:
        print('❌ Production podcast generation failed')
        print(f'Error: {result.get(\"error\", \"Unknown error\")}')
        exit(1)
    "
```

---

## 🧪 Phase 3: テスト・検証（高優先）

### 3.1 テストモード実行
次セッション開始後、以下のテストを順次実行：

#### 基本動作テスト
```python
# 1. データベース接続・記事取得テスト
from src.podcast.data_fetcher.enhanced_database_article_fetcher import EnhancedDatabaseArticleFetcher
from src.database.database_manager import DatabaseManager
from config.base import get_config

config = get_config()
db_manager = DatabaseManager(config.database)
fetcher = EnhancedDatabaseArticleFetcher(db_manager)

# 記事統計確認
stats = fetcher.get_database_statistics(hours=24)
print(f"📊 Database stats: {stats}")

# 記事選択テスト
articles = fetcher.get_balanced_article_selection(hours=24, max_articles=6)
print(f"📰 Selected articles: {len(articles)}")
```

#### 台本生成テスト
```python
# 2. Gemini 2.5 Pro台本生成テスト
from src.podcast.script_generation.professional_dialogue_script_generator import ProfessionalDialogueScriptGenerator

# Gemini 2.5 Proでテスト
generator = ProfessionalDialogueScriptGenerator(
    api_key=config.gemini.api_key,
    model_name="gemini-2.5-pro-001"
)

script = generator.generate_professional_script(articles)
print(f"📝 Script length: {len(script)} chars")
print(f"✅ Target achieved: {2600 <= len(script) <= 2800}")
```

#### 完全統合テスト
```python
# 3. 完全ワークフローテスト（テストモード）
from src.podcast.integration.production_podcast_integration_manager import ProductionPodcastIntegrationManager

manager = ProductionPodcastIntegrationManager(config)
result = manager.generate_complete_podcast(test_mode=True)

print(f"🎯 Test result: {result['success']}")
print(f"📊 Quality metrics: {result['quality_metrics']}")
```

### 3.2 品質検証チェックリスト
- [ ] 台本文字数: 2600-2800文字範囲内
- [ ] 音声時間: 9-11分範囲内  
- [ ] 記事選択: 3カテゴリ以上、2地域以上
- [ ] GitHub Pages配信: URL正常アクセス可能
- [ ] LINE配信: メッセージ正常送信

---

## 🚀 Phase 4: プロダクション配信開始

### 4.1 最終確認事項
1. **Gemini 2.5 Pro APIアクセス** - 料金・制限確認
2. **データベース記事数** - 過去24時間で6記事以上あること
3. **音声ファイル容量** - GitHub Pages制限内（25MB以下）
4. **LINE通知設定** - 受信確認済み

### 4.2 プロダクション開始手順
```bash
# 1. 環境変数最終確認
echo $GEMINI_PODCAST_MODEL  # "gemini-2.5-pro-001"
echo $PODCAST_PRODUCTION_MODE  # "true"

# 2. 手動プロダクション実行
python -c "
from src.podcast.integration.production_podcast_integration_manager import ProductionPodcastIntegrationManager
from config.base import get_config

config = get_config()
manager = ProductionPodcastIntegrationManager(config)
result = manager.generate_complete_podcast(test_mode=False)
print('Production result:', result['success'])
"

# 3. GitHub Actions自動配信有効化（JST 7:30）
# ワークフロー更新をプッシュ
```

---

## 📊 成功判定基準

### 必須達成項目
- [ ] テストモード完全実行成功
- [ ] 台本品質スコア > 80点
- [ ] 音声時間 9-11分達成
- [ ] LINE配信成功
- [ ] GitHub Actions自動実行成功

### 品質目標
- [ ] 記事カテゴリ多様性 ≥ 3カテゴリ
- [ ] 記事地域多様性 ≥ 2地域  
- [ ] 台本文字数: 2600-2800文字
- [ ] エラー率 < 5%

---

## 🚨 トラブルシューティング

### よくある問題と対処法

#### 1. Gemini 2.5 Pro APIエラー
```python
# 対処: 従来モデルでフォールバック
export GEMINI_PODCAST_MODEL="gemini-2.0-flash-lite-001"
# または quota制限確認
```

#### 2. データベース記事不足
```python
# 対処: 時間範囲拡張
articles = fetcher.get_balanced_article_selection(hours=48, max_articles=6)
```

#### 3. 音声生成失敗
```bash
# 対処: Google Cloud TTS設定確認
# サービスアカウントキー有効性確認
```

#### 4. LINE配信失敗
```bash
# 対処: LINE設定確認
echo $LINE_CHANNEL_ACCESS_TOKEN
# トークン有効性確認
```

---

## 📝 セッション終了時の確認事項

### 完了チェックリスト（次セッション終了時）
- [ ] config/base.py更新完了
- [ ] GitHub Actions ワークフロー更新完了
- [ ] テストモード実行・検証完了
- [ ] プロダクションモード初回実行完了
- [ ] 自動配信（JST 7:30）開始確認
- [ ] 継続監視体制構築開始

### 継続監視項目
- [ ] 毎日の配信成功率
- [ ] 台本品質メトリクス
- [ ] API使用料金
- [ ] ユーザーフィードバック

---

## 💡 最適化・改善アイデア（将来実装）

### 短期改善（1週間以内）
- A/Bテスト: 異なるプロンプトパターン
- 音声設定最適化: 話速・音質調整
- エラー回復強化: 自動リトライ機能

### 中期改善（1ヶ月以内）
- 多言語対応: 英語版ポッドキャスト
- ユーザーカスタマイズ: 投資スタイル別内容
- 詳細分析: 市場予測・専門解説拡充

### 長期展望（3ヶ月以内）
- Spotify/Apple Podcasts配信
- YouTube動画版（チャート・グラフ付き）
- 企業向けSlack/Discord配信

---

**次セッション開始準備完了** ✅

Phase 2から順次実装を開始し、10分本番ポッドキャストの配信開始を目指してください。