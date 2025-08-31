"""
Economic Indicators Configuration
経済指標システムの設定管理
"""

import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pytz


@dataclass
class EconDataSourceConfig:
    """データソース設定"""
    
    # 優先順位の高い順
    source_priority: List[str] = field(default_factory=lambda: [
        "investpy", "fmp", "finnhub", "rss"
    ])
    
    # investpy設定
    investpy_enabled: bool = True
    investpy_timeout: int = 30
    
    # FMP設定 (Financial Modeling Prep)
    fmp_api_key: str = ""
    fmp_enabled: bool = True
    fmp_base_url: str = "https://financialmodelingprep.com/api/v3"
    
    # Finnhub設定
    finnhub_api_key: str = ""
    finnhub_enabled: bool = True
    finnhub_base_url: str = "https://finnhub.io/api/v1"
    
    # RSS fallback設定
    rss_sources: Dict[str, str] = field(default_factory=lambda: {
        "fed": "https://www.federalreserve.gov/feeds/press_all.xml",
        "bea": "https://www.bea.gov/rss/news_releases.xml",
        "bls": "https://www.bls.gov/bls.rss"
    })


@dataclass
class EconAPIConfig:
    """公式統計API設定"""
    
    # FRED (Federal Reserve Economic Data)
    fred_api_key: str = ""
    fred_enabled: bool = True
    fred_base_url: str = "https://api.stlouisfed.org/fred"
    
    # BLS (Bureau of Labor Statistics)
    bls_api_key: str = ""
    bls_enabled: bool = True
    bls_base_url: str = "https://api.bls.gov/publicAPI/v2"
    
    # BEA (Bureau of Economic Analysis)
    bea_api_key: str = ""
    bea_enabled: bool = True
    bea_base_url: str = "https://apps.bea.gov/api/data"
    
    # ECB (European Central Bank)
    ecb_enabled: bool = True
    ecb_base_url: str = "https://data.ecb.europa.eu/api/v1"
    
    # ONS (Office for National Statistics - UK)
    ons_enabled: bool = True
    ons_base_url: str = "https://api.ons.gov.uk/v1"
    
    # e-Stat (Japan)
    estat_app_id: str = ""
    estat_enabled: bool = True
    estat_base_url: str = "https://api.e-stat.go.jp/rest/3.0/app/json"


@dataclass
class EconTargetConfig:
    """対象指標・国設定"""
    
    # 対象国コード
    target_countries: List[str] = field(default_factory=lambda: [
        "US", "EU", "UK", "JP", "CA", "AU"
    ])
    
    # 重要度しきい値 ("Low", "Medium", "High")
    importance_threshold: str = "Medium"
    
    # 主要指標リスト
    key_indicators: List[str] = field(default_factory=lambda: [
        "CPI", "Core CPI", "Unemployment Rate", "Non-Farm Payrolls",
        "Retail Sales", "GDP", "PMI", "Industrial Production",
        "Consumer Confidence", "Interest Rate Decision"
    ])
    
    # 除外キーワード
    exclude_keywords: List[str] = field(default_factory=lambda: [
        "Revised", "Preliminary", "Flash", "Final"
    ])


@dataclass
class EconOutputConfig:
    """出力設定"""
    
    # ベースディレクトリ
    output_base_dir: str = "./build"
    
    # 日次レポート
    daily_reports_dir: str = "reports/daily_indicators"
    daily_report_format: str = "markdown"  # "markdown" or "html"
    
    # カレンダー
    calendars_dir: str = "calendars"
    calendar_filename: str = "economic.ics"
    
    # 指標詳細
    indicators_dir: str = "indicators"
    chart_format: str = "png"  # "png" or "svg"
    chart_dpi: int = 300
    
    # 保持期間（日）
    retention_days: int = 90
    
    # タイムゾーン設定
    display_timezone: str = "Asia/Tokyo"
    internal_timezone: str = "UTC"


@dataclass
class EconScheduleConfig:
    """スケジュール設定"""
    
    # 日次一覧生成時刻 (UTC)
    daily_generation_hour: int = 6  # 06:00 UTC = 15:00 JST
    daily_generation_minute: int = 0
    
    # 通知設定
    notification_enabled: bool = True
    notification_advance_minutes: int = 60  # 発表60分前に通知
    notification_channels: List[str] = field(default_factory=lambda: ["slack"])
    
    # ICS更新間隔（時間）
    ics_update_interval_hours: int = 6
    
    # データ取得範囲
    lookback_days: int = 2  # T-2から取得
    forecast_days: int = 7   # T+7まで予測


@dataclass
class EconRenderConfig:
    """描画設定"""
    
    # 日本語フォント
    japanese_font: str = "NotoSansCJK-Regular"
    font_size_title: int = 16
    font_size_label: int = 12
    font_size_tick: int = 10
    
    # カラーパレット
    colors: Dict[str, str] = field(default_factory=lambda: {
        "primary": "#1f77b4",      # 青
        "secondary": "#ff7f0e",     # オレンジ
        "positive": "#2ca02c",      # 緑
        "negative": "#d62728",      # 赤
        "neutral": "#7f7f7f",      # グレー
        "background": "#ffffff",    # 白
        "grid": "#eeeeee"          # ライトグレー
    })
    
    # グラフサイズ
    figure_width: int = 12
    figure_height: int = 8
    figure_dpi: int = 300
    
    # 景気後退期網掛け (NBER recession periods)
    recession_shading: bool = True
    
    # データソース表記
    show_data_source: bool = True
    source_position: str = "bottom_right"  # "bottom_right", "bottom_left"


@dataclass
class EconCacheConfig:
    """キャッシュ設定"""
    
    # キャッシュ有効化
    enabled: bool = True
    
    # キャッシュ形式
    cache_format: str = "parquet"  # "parquet" or "sqlite"
    cache_dir: str = "./data/cache"
    
    # キャッシュ保持期間
    calendar_cache_hours: int = 6
    series_cache_hours: int = 24
    
    # SQLiteキャッシュ（代替）
    sqlite_cache_file: str = "./data/cache/econ_cache.db"


@dataclass
class EconNotificationConfig:
    """通知設定"""
    
    # Slack設定
    slack_webhook_url: str = ""
    slack_channel: str = "#market-news"
    slack_username: str = "Economic Indicators Bot"
    slack_icon_emoji: str = ":chart_with_upwards_trend:"
    
    # メール設定（オプション）
    email_enabled: bool = False
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: List[str] = field(default_factory=list)


@dataclass
class EconConfig:
    """経済指標システム統合設定"""
    
    # 機能有効化フラグ
    daily_list_enabled: bool = True
    calendar_enabled: bool = True
    deep_dive_enabled: bool = True
    notifications_enabled: bool = True
    
    # サブ設定
    data_sources: EconDataSourceConfig = field(default_factory=EconDataSourceConfig)
    apis: EconAPIConfig = field(default_factory=EconAPIConfig)
    targets: EconTargetConfig = field(default_factory=EconTargetConfig)
    output: EconOutputConfig = field(default_factory=EconOutputConfig)
    schedule: EconScheduleConfig = field(default_factory=EconScheduleConfig)
    render: EconRenderConfig = field(default_factory=EconRenderConfig)
    cache: EconCacheConfig = field(default_factory=EconCacheConfig)
    notifications: EconNotificationConfig = field(default_factory=EconNotificationConfig)
    
    # パフォーマンス設定
    max_concurrent_requests: int = 5
    request_delay_seconds: float = 1.0
    retry_attempts: int = 3
    retry_delay_seconds: float = 2.0
    
    # 品質管理
    data_quality_checks: bool = True
    missing_forecast_handling: str = "skip_surprise"  # "skip_surprise" or "show_na"
    outlier_detection: bool = True
    outlier_threshold: float = 3.0  # z-score threshold
    
    def __post_init__(self):
        """環境変数から設定を読み込み"""
        # API keys
        self.apis.fred_api_key = os.getenv("FRED_API_KEY", "")
        self.apis.bls_api_key = os.getenv("BLS_API_KEY", "")
        self.apis.bea_api_key = os.getenv("BEA_API_KEY", "")
        self.apis.estat_app_id = os.getenv("ESTAT_APP_ID", "")
        
        self.data_sources.fmp_api_key = os.getenv("FMP_API_KEY", "")
        self.data_sources.finnhub_api_key = os.getenv("FINNHUB_API_KEY", "")
        
        # Notification settings
        self.notifications.slack_webhook_url = os.getenv("ECON_SLACK_WEBHOOK_URL", "")
        self.notifications.slack_channel = os.getenv("ECON_SLACK_CHANNEL", "#market-news")
        
        # Output directories
        if os.getenv("ECON_OUTPUT_DIR"):
            self.output.output_base_dir = os.getenv("ECON_OUTPUT_DIR")
        
        # Feature flags
        self.daily_list_enabled = os.getenv("ECON_DAILY_LIST_ENABLED", "true").lower() == "true"
        self.calendar_enabled = os.getenv("ECON_CALENDAR_ENABLED", "true").lower() == "true"
        self.deep_dive_enabled = os.getenv("ECON_DEEP_DIVE_ENABLED", "true").lower() == "true"
        self.notifications_enabled = os.getenv("ECON_NOTIFICATIONS_ENABLED", "true").lower() == "true"
    
    def get_output_path(self, path_type: str, *args) -> str:
        """出力パスを生成"""
        base = self.output.output_base_dir
        
        if path_type == "daily_report":
            date_str = args[0] if args else datetime.now().strftime("%Y%m%d")
            return f"{base}/{self.output.daily_reports_dir}/{date_str}.md"
        elif path_type == "calendar":
            return f"{base}/{self.output.calendars_dir}/{self.output.calendar_filename}"
        elif path_type == "indicator":
            date_str, series_id = args[0], args[1]
            return f"{base}/{self.output.indicators_dir}/{date_str}/{series_id}.{self.output.chart_format}"
        elif path_type == "insights":
            date_str = args[0]
            return f"{base}/{self.output.indicators_dir}/{date_str}/insights.json"
        else:
            raise ValueError(f"Unknown path type: {path_type}")
    
    def get_timezone(self, tz_type: str = "display") -> pytz.BaseTzInfo:
        """タイムゾーンオブジェクトを取得"""
        if tz_type == "display":
            return pytz.timezone(self.output.display_timezone)
        elif tz_type == "internal":
            return pytz.timezone(self.output.internal_timezone)
        else:
            raise ValueError(f"Unknown timezone type: {tz_type}")
    
    def to_dict(self) -> Dict:
        """設定を辞書形式で返す（デバッグ用）"""
        return {
            "daily_list_enabled": self.daily_list_enabled,
            "calendar_enabled": self.calendar_enabled,
            "deep_dive_enabled": self.deep_dive_enabled,
            "notifications_enabled": self.notifications_enabled,
            "target_countries": self.targets.target_countries,
            "importance_threshold": self.targets.importance_threshold,
            "key_indicators": self.targets.key_indicators,
            "output_base_dir": self.output.output_base_dir,
            "display_timezone": self.output.display_timezone,
        }


# シングルトンインスタンス
_econ_config_instance: Optional[EconConfig] = None


def get_econ_config() -> EconConfig:
    """経済指標設定を取得（シングルトン）"""
    global _econ_config_instance
    if _econ_config_instance is None:
        _econ_config_instance = EconConfig()
    return _econ_config_instance


def reload_econ_config() -> EconConfig:
    """経済指標設定を再読み込み"""
    global _econ_config_instance
    _econ_config_instance = EconConfig()
    return _econ_config_instance