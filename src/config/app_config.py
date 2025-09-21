# -*- coding: utf-8 -*-

"""
アプリケーション設定の統一管理
"""

import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ScrapingConfig:
    """スクレイピング設定"""

    hours_limit: int = 24
    sentiment_analysis_enabled: bool = os.getenv("SCRAPING_SENTIMENT_ANALYSIS_ENABLED", "false").lower() == "true"  # 感情分析を環境変数で制御
    selenium_timeout: int = 20  # Seleniumの基本タイムアウト（秒）- 45→20秒に短縮
    selenium_max_retries: int = 3  # ページ読み込みのリトライ回数
    page_load_timeout: int = 30  # ページ読み込み専用タイムアウト（秒）- 60→30秒に短縮
    implicit_wait: int = 5  # 暗黙的待機時間（秒）- 10→5秒に短縮

    # 動的記事取得機能
    minimum_article_count: int = 100  # 最低記事数閾値
    max_hours_limit: int = 72  # 最大時間範囲（時間）
    weekend_hours_extension: int = 48  # 週末拡張時間（時間）


@dataclass
class ReutersConfig:
    """ロイター設定"""

    query: str = "米 OR 金融 OR 経済 OR 株価 OR FRB OR FOMC OR 決算 OR 利上げ OR インフレ"
    max_pages: int = 5
    items_per_page: int = 20
    num_parallel_requests: int = 8  # 記事本文を並列取得する際のスレッド数
    target_categories: List[str] = field(
        default_factory=lambda: [
            "ビジネスcategory",
            "マーケットcategory",
            "トップニュースcategory",
            "ワールドcategory",
            "テクノロジーcategory",
            "アジア市場category",
            "不明",
            "経済category",
        ]
    )
    exclude_keywords: List[str] = field(
        default_factory=lambda: [
            "スポーツ",
            "エンタメ",
            "五輪",
            "サッカー",
            "映画",
            "将棋",
            "囲碁",
            "芸能",
            "ライフ",
            "アングル：",
        ]
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "max_pages": self.max_pages,
            "items_per_page": self.items_per_page,
            "target_categories": self.target_categories,
            "exclude_keywords": self.exclude_keywords,
        }


@dataclass
class BloombergConfig:
    """ブルームバーグ設定"""

    num_parallel_requests: int = 6  # 記事本文を並列取得する際のスレッド数
    exclude_keywords: List[str] = field(
        default_factory=lambda: [
            "動画",
            "ポッドキャスト",
            "Bloomberg TV",
            "意見広告",
            "ライブブログ",
            "コラム",
        ]
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hours_limit": get_config().scraping.hours_limit,
            "exclude_keywords": self.exclude_keywords,
        }


@dataclass
class AIConfig:
    """AI処理設定"""

    gemini_api_key: str = ""
    model_name: str = "gemini-2.5-flash-lite"
    max_output_tokens: int = 1024
    temperature: float = 0.2

    process_prompt_template: str = """
あなたは10年以上の経験を持つ金融市場専門のニュース編集者兼アナリストです。
日本の金融・経済市場に精通し、複雑な市場情報を一般読者にもわかりやすく伝える専門家です。

## 分析タスク
以下の記事を分析し、高品質な要約を作成してください。

### 分析手順
1. **キーワード抽出**: 記事から重要な金融・経済用語、企業名、数値データを特定
2. **影響度評価**: 市場や経済への短期・中期的影響を分析
3. **要約作成**: 180-220字で簡潔かつ包括的にまとめる

### 要約の構成
1. 主要事実（何が起きたか）
2. 影響の範囲と程度
3. 市場への示唆や今後の見通し

### 分析例

**例1: 金融政策関連**
記事: 「日銀は政策金利を0.25%に引き上げると発表した。インフレ率の持続的な上昇を受けた措置で、3年ぶりの利上げとなる。」
要約: 日銀が政策金利を0.25%に引き上げ、3年ぶりの利上げを実施。持続的なインフレ上昇への対応として、金融正常化への転換点となる。市場では円高進行と銀行株上昇が期待され、借入コスト上昇により企業収益への影響も注視される。
キーワード: ["日銀", "政策金利", "0.25%", "利上げ", "インフレ", "金融正常化"]

**例2: 企業業績関連**
記事: 「トヨタ自動車の第3四半期決算は売上高が前年同期比8%減、営業利益は15%減となった。半導体不足と原材料高が主因。」
要約: トヨタ自動車の第3四半期は売上高8%減、営業利益15%減と減収減益。半導体不足と原材料高が主因だが、通期見通しは据え置き下期回復を見込む。自動車業界全体の課題を反映しており、サプライチェーン正常化が業績回復の鍵となる。
キーワード: ["トヨタ自動車", "第3四半期", "売上高8%減", "営業利益15%減", "半導体不足", "原材料高"]

## 出力形式
以下のJSON形式で出力してください。他のテキストは一切含めないでください。

{{
  "summary": "180-220字の要約",
  "keywords": ["重要キーワード1", "重要キーワード2", "重要キーワード3"]
}}

---記事本文---
{text}
---分析結果---
"""


@dataclass
class GoogleConfig:
    """Google APIs設定"""

    # 認証方式選択
    auth_method: str = "oauth2"  # "service_account" or "oauth2"

    # 共通設定
    drive_output_folder_id: str = ""
    overwrite_doc_id: Optional[str] = None
    docs_retention_days: int = 30  # ドキュメント保持日数

    # サービスアカウント認証用
    service_account_json: str = ""

    # OAuth2認証用
    oauth2_client_id: str = ""
    oauth2_client_secret: str = ""
    oauth2_refresh_token: str = ""

    def is_document_creation_day_and_time(self) -> bool:
        """
        Googleドキュメント生成の実行条件を判定

        変更: 時刻制限を撤廃し、常にドキュメント生成を許可
        理由: 1日1ドキュメントルールは create_daily_summary_doc() で実装済み

        Returns:
            bool: 常にTrue（いつでもドキュメント生成可能）
        """
        return True


@dataclass
class DatabaseConfig:
    """データベース設定"""

    url: str = "sqlite:///market_news.db"
    echo: bool = False


@dataclass
class SupabaseConfig:
    """Supabase設定"""

    url: str = os.getenv("SUPABASE_URL", "")
    anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket_name: str = os.getenv("SUPABASE_BUCKET", "market-news-archive")
    enabled: bool = os.getenv("SUPABASE_ENABLED", "false").lower() == "true"
    
    # RAG設定
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    chunk_size: int = 600
    chunk_overlap: int = 100
    max_chunks_per_document: int = 50
    similarity_threshold: float = 0.7


@dataclass
class LoggingConfig:
    """ログ設定"""

    level: str = "INFO"
    format: str = "json"
    file_enabled: bool = True
    file_path: str = "logs/market_news.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class LINEConfig:
    """LINE Bot設定"""

    channel_access_token: str = ""
    channel_secret: str = ""
    webhook_url: str = ""

    def __post_init__(self):
        """環境変数から設定を読み込み"""
        self.channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        self.channel_secret = os.getenv("LINE_CHANNEL_SECRET", "")
        self.webhook_url = os.getenv("LINE_WEBHOOK_URL", "")

    def is_configured(self) -> bool:
        """LINE設定が完了しているかチェック"""
        return bool(
            self.channel_access_token
            and self.channel_access_token != "your_line_channel_access_token_here"
            and self.channel_secret
            and self.channel_secret != "your_line_channel_secret_here"
        )


@dataclass
class PodcastConfig:
    """ポッドキャスト設定（拡張版）"""

    rss_base_url: str = ""
    author_name: str = "Market News Bot"
    author_email: str = "market-news@example.com"
    rss_title: str = "マーケットニュース15分"
    rss_description: str = "AIが生成する15分間の毎日マーケットニュース（拡張情報版）"
    monthly_cost_limit_usd: float = 15.0
    target_duration_minutes: float = 15.0
    max_file_size_mb: int = 25  # 15分版に対応して容量増大
    
    # 拡張版設定
    max_articles: int = 15  # 記事数制限（拡張版）
    target_character_count: Tuple[int, int] = (4000, 8000)  # 台本文字数範囲（最低4000文字保証、最大8000文字で途中終了防止）

    # 音声設定
    audio_format: str = "mp3"
    sample_rate: int = 44100
    bitrate: str = "128k"
    lufs_target: float = -16.0
    peak_target: float = -1.0

    # 配信設定
    episode_prefix: str = "第"
    episode_suffix: str = "回"

    # ファイルパス設定
    assets_path: str = "assets/audio"
    pronunciation_dict_path: str = "config/pronunciation_dict.yaml"

    # API設定
    gemini_api_key: str = ""
    line_channel_access_token: str = ""

    # GitHub Pages設定
    github_pages_url: str = ""
    rss_feed_path: str = "podcast/feed.xml"

    def __post_init__(self):
        """環境変数から設定を読み込み"""
        self.rss_base_url = os.getenv("PODCAST_RSS_BASE_URL", "")
        self.author_name = os.getenv("PODCAST_AUTHOR_NAME", self.author_name)
        self.author_email = os.getenv("PODCAST_AUTHOR_EMAIL", self.author_email)
        self.rss_title = os.getenv("PODCAST_RSS_TITLE", self.rss_title)
        self.rss_description = os.getenv("PODCAST_RSS_DESCRIPTION", self.rss_description)
        self.monthly_cost_limit_usd = float(
            os.getenv("PODCAST_MONTHLY_COST_LIMIT", str(self.monthly_cost_limit_usd))
        )
        self.target_duration_minutes = float(
            os.getenv("PODCAST_TARGET_DURATION_MINUTES", str(self.target_duration_minutes))
        )
        self.max_file_size_mb = int(
            os.getenv("PODCAST_MAX_FILE_SIZE_MB", str(self.max_file_size_mb))
        )

    def load_pronunciation_dict(self) -> Dict[str, str]:
        """発音辞書を読み込み"""
        import yaml

        try:
            with open(self.pronunciation_dict_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                # YAMLファイルが辞書形式の場合はそのまま返す
                if isinstance(data, dict):
                    return data
                return {}
        except FileNotFoundError:
            return {}
        except yaml.YAMLError:
            return {}


@dataclass
class SocialConfig:
    """ソーシャルコンテンツ生成設定"""
    
    # 機能有効/無効フラグ
    enable_social_images: bool = True
    enable_note_md: bool = True
    # 保持方針
    retention_policy: str = "keep"  # keep | archive | delete
    retention_days: int = 30
    
    # コンテンツ生成方式
    generation_mode: str = "hybrid"  # auto | manual | hybrid
    enable_llm_optimization: bool = True
    
    # 画像設定 - HTMLテンプレート準拠の縦型フォーマット
    image_width: int = 800   # 縦型フォーマットに変更
    image_height: int = 1200 # 縦型フォーマットに変更
    image_margin: int = 48   # マージンを調整
    background_color: str = "#FFFFFF"  # 白背景に変更（HTMLテンプレート準拠）
    text_color: str = "#1F2937"        # ダークグレー文字
    accent_color: str = "#111827"      # よりダークなメインカラー
    sub_accent_color: str = "#6B7280"   # セカンダリカラー
    
    # ブランド設定
    brand_name: str = "Market News"
    website_url: str = "https://market-news.example.com"
    hashtags: str = "#MarketNews"
    
    # 出力設定（既定を build に統一）
    output_base_dir: str = "./build"
    
    # SNS最適化プロンプト
    sns_optimization_prompt: str = """あなたは金融ニュースのSNSマーケティング専門家です。

【タスク】
以下の記事要約をSNS投稿用の魅力的な文章に変換してください。

【制約】
- 文字数: 140字以内
- トーン: 専門的だが親しみやすい
- 対象: 個人投資家・ビジネスパーソン
- 必須要素: 重要ポイント1つ、影響度、適切なハッシュタグ

【出力形式】
以下のJSON形式で出力してください。他のテキストは一切含めないでください。

{{
  "sns_text": "SNS投稿用テキスト（140字以内、ハッシュタグ含む）",
  "keywords": ["重要キーワード1", "重要キーワード2", "重要キーワード3"]
}}

---記事情報---
タイトル: {title}
要約: {summary}
カテゴリ: {category}
地域: {region}"""
    
    # note記事生成プロンプト
    note_article_prompt: str = """あなたは15年以上の経験を持つ金融市場アナリスト兼投資ストラテジストです。機関投資家向けの高品質な市場分析レポートを作成する専門家として、以下の要件で詳細な分析記事を作成してください。

## 📋 記事構成要件

### 1. エグゼクティブサマリー（400-500字）
- 本日の市場動向の全体像
- 最重要3つのポイント
- 投資戦略への短期的示唆

### 2. 市場概況・トレンド分析（600-800字）
- 全体的な市場環境の分析
- セクター別動向の詳細解説
- 技術的指標とファンダメンタルズの関係

### 3. 重要トピック詳細分析（各トピック800-1000字）
各トピックについて以下を詳細に分析：
- **事実関係**: 客観的な事実の整理
- **市場への影響分析**: 
  - 短期影響（1-3日）: センチメント・価格への直接的影響
  - 中長期影響（1-4週間）: 業界トレンド・投資戦略への波及効果
- **投資家への示唆**: 
  - リスク要因の特定
  - 機会要因の分析
  - 監視すべき指標・発表

### 4. 投資戦略への示唆（500-600字）
- ポートフォリオ調整の具体的ポイント
- リスク管理の観点
- 新たな投資機会の特定

### 5. 明日への展望（300-400字）
- 継続監視項目
- 新規要因の可能性
- 技術的分析の観点

## 🎯 品質要件

### 文章品質
- **文字数**: 4000-6000字（高品質な分析記事として）
- **専門性**: 金融専門用語を適切に使用し、分かりやすく説明
- **客観性**: 感情的表現を避け、データに基づいた分析
- **実用性**: 投資判断に実際に役立つ具体的な示唆

### 分析の深さ
- **多角的視点**: 技術分析・ファンダメンタルズ・センチメント分析
- **定量的評価**: 可能な限り数値データを活用
- **リスク評価**: 上振れ・下振れリスクの両面を分析
- **時系列分析**: 過去の類似事例との比較

### 投資家向け配慮
- **アクションアイテム**: 具体的な投資行動の示唆
- **リスク開示**: 適切なリスク要因の明記
- **監視項目**: 今後注目すべき指標・発表の明示

## 📊 出力形式

Markdown形式で以下の構造で出力してください：

```markdown
# [日付] の市場分析レポート

## 📈 エグゼクティブサマリー
[400-500字の要約]

## 🔍 市場概況・トレンド分析
[600-800字の分析]

## 📊 重要トピック詳細分析

### 1. [トピック1の見出し]
[800-1000字の詳細分析]

### 2. [トピック2の見出し]
[800-1000字の詳細分析]

### 3. [トピック3の見出し]
[800-1000字の詳細分析]

## 🎯 投資戦略への示唆
[500-600字の戦略的示唆]

## 🔮 明日への展望
[300-400字の展望]

## ⚠️ 免責事項・リスク開示
[適切なリスク開示]
```

## 📈 入力データ

**日付**: {date}
**選出トピック**: {topics}
**市場概況**: {market_summary}
**統合要約**: {integrated_summary}

---

上記の要件に従って、プロフェッショナルな市場分析レポートを作成してください。投資家が実際の投資判断に活用できる高品質な内容にしてください。"""


@dataclass
class AppConfig:
    """アプリケーション全体設定"""

    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    reuters: ReutersConfig = field(default_factory=ReutersConfig)
    bloomberg: BloombergConfig = field(default_factory=BloombergConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    google: GoogleConfig = field(default_factory=GoogleConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    supabase: SupabaseConfig = field(default_factory=SupabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    line: LINEConfig = field(default_factory=LINEConfig)
    podcast: PodcastConfig = field(default_factory=PodcastConfig)
    social: SocialConfig = field(default_factory=SocialConfig)

    def __post_init__(self):
        """環境変数から設定を読み込み"""
        self.ai.gemini_api_key = os.getenv("GEMINI_API_KEY", "")

        # Google設定
        self.google.auth_method = os.getenv("GOOGLE_AUTH_METHOD", "oauth2")
        self.google.drive_output_folder_id = os.getenv("GOOGLE_DRIVE_OUTPUT_FOLDER_ID", "")
        self.google.overwrite_doc_id = os.getenv("GOOGLE_OVERWRITE_DOC_ID")

        # サービスアカウント認証設定
        self.google.service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")

        # OAuth2認証設定
        self.google.oauth2_client_id = os.getenv("GOOGLE_OAUTH2_CLIENT_ID", "")
        self.google.oauth2_client_secret = os.getenv("GOOGLE_OAUTH2_CLIENT_SECRET", "")
        self.google.oauth2_refresh_token = os.getenv("GOOGLE_OAUTH2_REFRESH_TOKEN", "")

        # 環境変数でのオーバーライド（任意）
        if os.getenv("SCRAPING_HOURS_LIMIT"):
            self.scraping.hours_limit = int(os.getenv("SCRAPING_HOURS_LIMIT"))

        if os.getenv("SCRAPING_MINIMUM_ARTICLE_COUNT"):
            self.scraping.minimum_article_count = int(os.getenv("SCRAPING_MINIMUM_ARTICLE_COUNT"))

        if os.getenv("SCRAPING_MAX_HOURS_LIMIT"):
            self.scraping.max_hours_limit = int(os.getenv("SCRAPING_MAX_HOURS_LIMIT"))

        if os.getenv("SCRAPING_WEEKEND_HOURS_EXTENSION"):
            self.scraping.weekend_hours_extension = int(
                os.getenv("SCRAPING_WEEKEND_HOURS_EXTENSION")
            )

        if os.getenv("LOGGING_LEVEL"):
            self.logging.level = os.getenv("LOGGING_LEVEL")

    @property
    def is_document_creation_day_and_time(self) -> bool:
        """
        Googleドキュメント生成の実行条件を判定

        変更: 時刻制限を撤廃し、常にドキュメント生成を許可
        理由: 1日1ドキュメントルールは create_daily_summary_doc() で実装済み

        Returns:
            bool: 常にTrue（いつでもドキュメント生成可能）
        """
        return True

    def to_legacy_format(self) -> Dict:
        """既存コードとの互換性のため、古い形式で設定を返す"""
        return {
            "HOURS_LIMIT": self.scraping.hours_limit,
            "SENTIMENT_ANALYSIS_ENABLED": self.scraping.sentiment_analysis_enabled,
            "AI_PROCESS_PROMPT_TEMPLATE": self.ai.process_prompt_template,
            "GOOGLE_OVERWRITE_DOC_ID": self.google.overwrite_doc_id,
            "REUTERS_CONFIG": {
                "query": self.reuters.query,
                "max_pages": self.reuters.max_pages,
                "items_per_page": self.reuters.items_per_page,
                "target_categories": self.reuters.target_categories,
                "exclude_keywords": self.reuters.exclude_keywords,
            },
            "BLOOMBERG_CONFIG": {"exclude_keywords": self.bloomberg.exclude_keywords},
        }


# シングルトンインスタンス
_config_instance: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """アプリケーション設定を取得（シングルトン）"""
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance


def reload_config() -> AppConfig:
    """設定を再読み込み"""
    global _config_instance
    _config_instance = AppConfig()
    return _config_instance


def load_config() -> AppConfig:
    """設定を読み込み（get_configのエイリアス）"""
    return get_config()
