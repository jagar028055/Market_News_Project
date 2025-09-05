# -*- coding: utf-8 -*-

"""
アプリケーション設定の統一管理
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ScrapingConfig:
    """スクレイピング設定"""

    hours_limit: int = 24
    sentiment_analysis_enabled: bool = True
    selenium_timeout: int = 45  # Seleniumの基本タイムアウト（秒）
    selenium_max_retries: int = 3  # ページ読み込みのリトライ回数
    page_load_timeout: int = 60  # ページ読み込み専用タイムアウト（秒）
    implicit_wait: int = 10  # 暗黙的待機時間（秒）

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
    """ポッドキャスト設定"""

    rss_base_url: str = ""
    author_name: str = "Market News Bot"
    author_email: str = "market-news@example.com"
    rss_title: str = "マーケットニュース10分"
    rss_description: str = "AIが生成する毎日のマーケットニュース"
    monthly_cost_limit_usd: float = 10.0
    target_duration_minutes: float = 10.0
    max_file_size_mb: int = 15

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
class AppConfig:
    """アプリケーション全体設定"""

    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    reuters: ReutersConfig = field(default_factory=ReutersConfig)
    bloomberg: BloombergConfig = field(default_factory=BloombergConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    google: GoogleConfig = field(default_factory=GoogleConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    line: LINEConfig = field(default_factory=LINEConfig)
    podcast: PodcastConfig = field(default_factory=PodcastConfig)

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
