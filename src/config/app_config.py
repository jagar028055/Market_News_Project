# -*- coding: utf-8 -*-

"""
アプリケーション設定の統一管理
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ScrapingConfig:
    """スクレイピング設定"""
    hours_limit: int = 24
    sentiment_analysis_enabled: bool = True
    selenium_timeout: int = 120  # Seleniumの基本タイムアウト（秒）
    selenium_max_retries: int = 3  # ページ読み込みのリトライ回数


@dataclass
class ReutersConfig:
    """ロイター設定"""
    query: str = "米 OR 金融 OR 経済 OR 株価 OR FRB OR FOMC OR 決算 OR 利上げ OR インフレ"
    max_pages: int = 5
    items_per_page: int = 20
    num_parallel_requests: int = 5  # 記事本文を並列取得する際のスレッド数
    target_categories: List[str] = field(default_factory=lambda: [
        "ビジネスcategory",
        "マーケットcategory", 
        "トップニュースcategory",
        "ワールドcategory",
        "テクノロジーcategory",
        "アジア市場category",
        "不明",
        "経済category"
    ])
    exclude_keywords: List[str] = field(default_factory=lambda: [
        "スポーツ", "エンタメ", "五輪", "サッカー", "映画", 
        "将棋", "囲碁", "芸能", "ライフ", "アングル："
    ])


@dataclass
class BloombergConfig:
    """ブルームバーグ設定"""
    exclude_keywords: List[str] = field(default_factory=lambda: [
        "動画", "ポッドキャスト", "Bloomberg TV", 
        "意見広告", "ライブブログ", "コラム"
    ])


@dataclass
class AIConfig:
    """AI処理設定"""
    gemini_api_key: str = ""
    model_name: str = "gemini-2.0-flash-lite-001"
    max_output_tokens: int = 1024
    temperature: float = 0.2
    
    process_prompt_template: str = """
あなたは優秀なニュース編集者兼アナリストです。
以下の記事を分析し、次の2つのタスクを実行してください。

1.  **要約**: 記事の最も重要なポイントを抽出し、日本語で200字以内にまとめてください。要約は自然で完結した一つの段落にしてください。
2.  **感情分析**: 記事全体の論調が市場に与える影響を考慮し、センチメントを「Positive」、「Negative」、「Neutral」のいずれかで判定してください。

回答は必ず以下のJSON形式で、他のテキストは一切含めずに返してください。

{{
  "summary": "ここに記事の要約",
  "sentiment_label": "ここに判定結果（Positive, Negative, Neutral）",
  "sentiment_score": ここに判定の確信度（0.0〜1.0の数値）
}}

---記事本文---
{text}
---分析結果---
"""


@dataclass
class GoogleConfig:
    """Google APIs設定"""
    drive_output_folder_id: str = ""
    overwrite_doc_id: Optional[str] = None
    service_account_json: str = ""


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
    max_file_size: int = 10*1024*1024  # 10MB
    backup_count: int = 5


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
    
    def __post_init__(self):
        """環境変数から設定を読み込み"""
        self.ai.gemini_api_key = os.getenv('GEMINI_API_KEY', '')
        self.google.drive_output_folder_id = os.getenv('GOOGLE_DRIVE_OUTPUT_FOLDER_ID', '')
        self.google.service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '{}')
        
        # 環境変数でのオーバーライド（任意）
        if os.getenv('SCRAPING_HOURS_LIMIT'):
            self.scraping.hours_limit = int(os.getenv('SCRAPING_HOURS_LIMIT'))
        
        if os.getenv('LOGGING_LEVEL'):
            self.logging.level = os.getenv('LOGGING_LEVEL')
    
    def to_legacy_format(self) -> Dict:
        """既存コードとの互換性のため、古い形式で設定を返す"""
        return {
            'HOURS_LIMIT': self.scraping.hours_limit,
            'SENTIMENT_ANALYSIS_ENABLED': self.scraping.sentiment_analysis_enabled,
            'AI_PROCESS_PROMPT_TEMPLATE': self.ai.process_prompt_template,
            'GOOGLE_OVERWRITE_DOC_ID': self.google.overwrite_doc_id,
            'REUTERS_CONFIG': {
                'query': self.reuters.query,
                'max_pages': self.reuters.max_pages,
                'items_per_page': self.reuters.items_per_page,
                'target_categories': self.reuters.target_categories,
                'exclude_keywords': self.reuters.exclude_keywords
            },
            'BLOOMBERG_CONFIG': {
                'exclude_keywords': self.bloomberg.exclude_keywords
            }
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
