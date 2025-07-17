# -*- coding: utf-8 -*-

from pydantic import Field, validator
from pydantic_settings import BaseSettings
from typing import List, Optional
import json
import os


class ScrapingConfig(BaseSettings):
    """スクレイピング関連設定"""
    hours_limit: int = Field(24, ge=1, le=168, description="記事収集時間範囲（時間）")
    sentiment_analysis_enabled: bool = Field(True, description="感情分析有効化")
    
    class Config:
        env_prefix = "SCRAPING_"


class ReutersConfig(BaseSettings):
    """ロイター設定"""
    query: str = Field("米 OR 金融 OR 経済 OR 株価 OR FRB OR FOMC OR 決算 OR 利上げ OR インフレ", description="検索クエリ")
    max_pages: int = Field(5, ge=1, le=20, description="最大ページ数")
    items_per_page: int = Field(20, ge=10, le=100, description="ページあたりの記事数")
    target_categories: List[str] = Field(
        default=[
            "ビジネスcategory",
            "マーケットcategory", 
            "トップニュースcategory",
            "ワールドcategory",
            "テクノロジーcategory",
            "アジア市場category",
            "不明",
            "経済category"
        ],
        description="対象カテゴリ"
    )
    exclude_keywords: List[str] = Field(
        default=[
            "スポーツ", "エンタメ", "五輪", "サッカー", "映画", 
            "将棋", "囲碁", "芸能", "ライフ", "アングル："
        ],
        description="除外キーワード"
    )
    
    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError('検索クエリは空にできません')
        return v.strip()
    
    class Config:
        env_prefix = "REUTERS_"


class BloombergConfig(BaseSettings):
    """Bloomberg設定"""
    exclude_keywords: List[str] = Field(
        default=[
            "動画", "ポッドキャスト", "Bloomberg TV", 
            "意見広告", "ライブブログ", "コラム"
        ],
        description="除外キーワード"
    )
    
    class Config:
        env_prefix = "BLOOMBERG_"


class GoogleConfig(BaseSettings):
    """Google APIs設定"""
    drive_output_folder_id: str = Field(..., description="Google Drive出力フォルダID")
    overwrite_doc_id: Optional[str] = Field(None, description="上書き更新ドキュメントID")
    service_account_json: str = Field(..., description="サービスアカウントJSON")
    
    @validator('service_account_json')
    def validate_json(cls, v):
        try:
            json.loads(v)
            return v
        except json.JSONDecodeError:
            raise ValueError('無効なJSON形式です')
    
    @validator('drive_output_folder_id')
    def validate_folder_id(cls, v):
        if "YOUR_FOLDER_ID" in v:
            raise ValueError('Google Drive フォルダIDが設定されていません')
        return v
    
    class Config:
        env_prefix = "GOOGLE_"


class AIConfig(BaseSettings):
    """AI関連設定"""
    gemini_api_key: str = Field(..., description="Gemini APIキー")
    model_name: str = Field("gemini-2.0-flash-lite-001", description="使用モデル")
    max_output_tokens: int = Field(1024, ge=256, le=8192, description="最大出力トークン数")
    temperature: float = Field(0.2, ge=0.0, le=2.0, description="温度パラメータ")
    
    process_prompt_template: str = Field(
        default="""
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
""",
        description="AI処理プロンプトテンプレート"
    )
    
    @validator('gemini_api_key')
    def validate_api_key(cls, v):
        if not v or len(v) < 10:
            raise ValueError('Gemini APIキーが無効です')
        return v
    
    class Config:
        env_prefix = "AI_"


class DatabaseConfig(BaseSettings):
    """データベース設定"""
    url: str = Field("sqlite:///market_news.db", description="データベースURL")
    echo: bool = Field(False, description="SQLログ出力")
    
    class Config:
        env_prefix = "DATABASE_"


class LoggingConfig(BaseSettings):
    """ログ設定"""
    level: str = Field("INFO", description="ログレベル")
    format: str = Field("json", description="ログフォーマット (json/text)")
    file_enabled: bool = Field(True, description="ファイル出力有効")
    file_path: str = Field("logs/market_news.log", description="ログファイルパス")
    max_file_size: int = Field(10*1024*1024, description="最大ファイルサイズ（バイト）")
    backup_count: int = Field(5, description="バックアップファイル数")
    
    class Config:
        env_prefix = "LOGGING_"


class AppConfig(BaseSettings):
    """アプリケーション全体設定"""
    scraping: ScrapingConfig = ScrapingConfig()
    reuters: ReutersConfig = ReutersConfig()
    bloomberg: BloombergConfig = BloombergConfig()
    google: GoogleConfig
    ai: AIConfig
    database: DatabaseConfig = DatabaseConfig()
    logging: LoggingConfig = LoggingConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# シングルトンパターンでアプリ設定を管理
_app_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """アプリケーション設定を取得"""
    global _app_config
    if _app_config is None:
        _app_config = AppConfig()
    return _app_config


def reload_config() -> AppConfig:
    """設定を再読み込み"""
    global _app_config
    _app_config = AppConfig()
    return _app_config