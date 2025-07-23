# 設計書

## 概要

自動ポッドキャスト生成システムは、既存のマーケットニュース収集システムに統合される形で実装されます。既存のニュース収集・AI要約機能を活用し、新たに対話台本生成、TTS音声合成、音声処理、配信機能を追加します。

## アーキテクチャ

### システム全体構成

```
既存システム                     新規ポッドキャスト機能
┌─────────────────┐           ┌─────────────────┐
│ News Collection │           │ Script Generator│
│ (Reuters/Bloomberg)│ ────────→ │ (Dialogue)      │
└─────────────────┘           └─────────────────┘
         │                             │
         ▼                             ▼
┌─────────────────┐           ┌─────────────────┐
│ AI Summarizer   │           │ TTS Engine      │
│ (Gemini Flash)  │           │ (Gemini TTS)    │
└─────────────────┘           └─────────────────┘
         │                             │
         ▼                             ▼
┌─────────────────┐           ┌─────────────────┐
│ HTML Generator  │           │ Audio Processor │
│ (GitHub Pages)  │           │ (pydub)         │
└─────────────────┘           └─────────────────┘
                                       │
                                       ▼
                               ┌─────────────────┐
                               │ Multi-Channel   │
                               │ Publisher       │
                               │ (RSS + LINE)    │
                               └─────────────────┘
```

### データフロー

1. **既存フロー活用**: ニュース収集 → AI要約 → HTML生成
2. **新規フロー追加**: ニュース記事全文 → 対話台本生成 → TTS音声合成 → 音声処理 → 配信

## コンポーネントと インターフェース

### 1. Script Generator (台本生成器)

**責務**: 収集されたニュース記事の全文を2人の対話形式の台本に変換

```python
class DialogueScriptGenerator:
    def __init__(self, gemini_api_key: str):
        self.api_key = gemini_api_key
        self.model = "gemini-2.5-pro"  # 高性能モデル使用
    
    def generate_script(self, articles: List[Dict]) -> str:
        """記事全文リストから対話台本を生成"""
        pass
    
    def _format_dialogue(self, content: str) -> str:
        """<speaker1>と<speaker2>タグ付きの対話形式に整形"""
        pass
    
    def _prioritize_articles(self, articles: List[Dict]) -> List[Dict]:
        """記事を重要度順に並び替え"""
        pass
```

**入力**: 収集されたニュース記事の全文リスト
**出力**: スピーカータグ付き対話台本（2,400-2,800文字）

### 2. TTS Engine (音声合成エンジン)

**責務**: 対話台本を2人の音声で合成

```python
class GeminiTTSEngine:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def synthesize_dialogue(self, script: str) -> bytes:
        """スピーカータグ付き台本を音声データに変換"""
        pass
    
    def _extract_speaker_segments(self, script: str) -> List[Tuple[str, str]]:
        """台本からスピーカー別セグメントを抽出"""
        pass
```

**入力**: スピーカータグ付き台本
**出力**: 音声データ（WAV/MP3形式）

### 3. Audio Processor (音声処理器)

**責務**: 音声の品質調整、BGM・ジングル合成、ファイル最適化

```python
class AudioProcessor:
    def __init__(self, assets_path: str):
        self.assets_path = assets_path
        self.jingles = self._load_jingles()
        self.bgm = self._load_bgm()
    
    def process_audio(self, tts_audio: bytes) -> bytes:
        """TTS音声を最終的なポッドキャスト音声に処理"""
        pass
    
    def _normalize_audio(self, audio: AudioSegment) -> AudioSegment:
        """音量正規化（-16 LUFS, -1 dBFS peak）"""
        pass
    
    def _add_intro_outro(self, audio: AudioSegment) -> AudioSegment:
        """オープニング・エンディング追加"""
        pass
```

**入力**: TTS生成音声
**出力**: 最終ポッドキャスト音声（MP3, ≤15MB, 9.5-10分）

### 4. Multi-Channel Publisher (配信器)

**責務**: 複数チャンネルへの同時配信

```python
class PodcastPublisher:
    def __init__(self, config: PublisherConfig):
        self.rss_generator = RSSGenerator(config.rss)
        self.line_broadcaster = LINEBroadcaster(config.line)
    
    def publish(self, audio_file: str, metadata: Dict) -> bool:
        """ポッドキャストを全チャンネルに配信"""
        pass
    
    def _publish_rss(self, audio_file: str, metadata: Dict) -> bool:
        """RSS配信（GitHub Pages）"""
        pass
    
    def _publish_line(self, audio_url: str, metadata: Dict) -> bool:
        """LINE配信"""
        pass
```

**入力**: 音声ファイル、メタデータ
**出力**: RSS配信、LINE配信の成功/失敗

## データモデル

### PodcastEpisode

```python
@dataclass
class PodcastEpisode:
    title: str
    description: str
    audio_file_path: str
    duration_seconds: int
    file_size_bytes: int
    publish_date: datetime
    episode_number: int
    transcript: str
    source_articles: List[Dict]
```

### AudioAssets

```python
@dataclass
class AudioAssets:
    intro_jingle: str  # ファイルパス
    outro_jingle: str
    background_music: str
    segment_transition: str
    credits: Dict[str, str]  # CC-BYクレジット情報
```

### PublisherConfig

```python
@dataclass
class PublisherConfig:
    rss: RSSConfig
    line: LINEConfig
    github_pages_url: str
    s3_fallback_config: Optional[S3Config] = None
```

## エラーハンドリング

### エラー分類と対応

1. **TTS API エラー**
   - レート制限: 指数バックオフで再試行
   - 文字数制限: 台本を分割して処理
   - API障害: 既存のFlashモデルでフォールバック

2. **音声処理エラー**
   - ファイル破損: 元データから再生成
   - サイズ超過: 圧縮率調整で再処理
   - 時間超過: 台本短縮で再生成

3. **配信エラー**
   - GitHub Pages障害: S3フォールバック
   - LINE API障害: 次回実行時に再送
   - ネットワーク障害: 指数バックオフで再試行

### エラー監視

```python
class PodcastErrorHandler:
    def __init__(self):
        self.error_tracker = ErrorTracker()
        self.cost_monitor = CostMonitor()
    
    def handle_tts_error(self, error: Exception, context: Dict) -> bool:
        """TTS関連エラーの処理"""
        pass
    
    def monitor_costs(self, usage: Dict) -> None:
        """コスト監視（月$10制限）"""
        pass
```

## テスト戦略

### 単体テスト

1. **台本生成テスト**
   - 文字数制限（2,400-2,800文字）
   - スピーカータグ形式
   - 対話の自然さ

2. **音声処理テスト**
   - 音量正規化
   - ファイルサイズ制限
   - 再生時間制限

3. **配信テスト**
   - RSS生成
   - LINE API連携
   - エラーハンドリング

### 統合テスト

1. **エンドツーエンドテスト**
   - ニュース収集 → ポッドキャスト生成 → 配信
   - GitHub Actions実行
   - 複数チャンネル同時配信

2. **パフォーマンステスト**
   - 処理時間測定
   - メモリ使用量
   - API呼び出し回数

### テスト環境

```python
class PodcastTestSuite:
    def setUp(self):
        self.mock_news_data = self._load_test_data()
        self.test_assets = self._setup_test_assets()
        self.mock_apis = self._setup_api_mocks()
    
    def test_full_pipeline(self):
        """完全なポッドキャスト生成パイプラインのテスト"""
        pass
    
    def test_cost_limits(self):
        """コスト制限のテスト"""
        pass
```

## 設定管理

### 新規設定項目

```python
@dataclass
class PodcastConfig:
    """ポッドキャスト機能設定"""
    script_model: str = "gemini-2.5-pro"
    tts_model: str = "gemini-tts"
    target_duration_minutes: float = 10.0
    max_file_size_mb: int = 15
    target_character_count: Tuple[int, int] = (2400, 2800)
    
    # 音声設定
    audio_format: str = "mp3"
    sample_rate: int = 44100
    bitrate: str = "128k"
    lufs_target: float = -16.0
    peak_target: float = -1.0
    
    # 配信設定
    rss_title: str = "マーケットニュース10分"
    rss_description: str = "AIが生成する毎日のマーケットニュース"
    episode_prefix: str = "第"
    episode_suffix: str = "回"
```

### 発音辞書

```yaml
# config/pronunciation_dict.yaml
pronunciation_corrections:
  "FRB": "エフアールビー"
  "FOMC": "エフオーエムシー"
  "GDP": "ジーディーピー"
  "CPI": "シーピーアイ"
  "S&P500": "エスアンドピー ごひゃく"
  "NASDAQ": "ナスダック"
  "NYSE": "ニューヨーク証券取引所"
```

## セキュリティ考慮事項

### API キー管理

- 既存のGemini APIキーを再利用
- LINE APIキーは新規にGitHub Secretsで管理
- TTS使用量監視でコスト制御

### 著作権対応

- 元記事は要約のみ使用（既存システムと同様）
- BGM・ジングルはCC-BYライセンス使用
- クレジット情報の自動挿入

### データ保護

- 音声ファイルの一時保存期間制限
- 個人情報を含まないニュースデータのみ処理
- ログの機密情報マスキング（既存機能活用）

## パフォーマンス最適化

### 処理時間短縮

1. **並列処理**: TTS生成と音声処理の並列実行
2. **キャッシュ**: 同一記事の重複処理回避
3. **ストリーミング**: 大容量音声ファイルのストリーミング処理

### リソース使用量

1. **メモリ管理**: 音声データの段階的処理
2. **ディスク使用量**: 一時ファイルの自動削除
3. **API呼び出し最適化**: バッチ処理とレート制限対応

## 運用監視

### メトリクス収集

```python
class PodcastMetrics:
    def __init__(self):
        self.cost_tracker = CostTracker()
        self.performance_monitor = PerformanceMonitor()
    
    def track_episode_generation(self, episode: PodcastEpisode) -> None:
        """エピソード生成メトリクス記録"""
        pass
    
    def track_distribution(self, channels: List[str], success: bool) -> None:
        """配信メトリクス記録"""
        pass
```

### ログ出力

- 既存のログシステムを拡張
- ポッドキャスト固有のログレベル追加
- 構造化ログでメトリクス分析対応