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
    model_name: str = Field("gemini-2.5-flash-lite", description="使用モデル")
    max_output_tokens: int = Field(1024, ge=256, le=8192, description="最大出力トークン数")
    temperature: float = Field(0.2, ge=0.0, le=2.0, description="温度パラメータ")
    
    # ポッドキャスト関連設定
    podcast_enabled: bool = Field(True, description="ポッドキャスト機能有効化")
    podcast_script_model: str = Field("gemini-2.5-pro", description="台本生成用モデル")
    podcast_script_temperature: float = Field(0.4, ge=0.0, le=2.0, description="台本生成温度")
    podcast_script_max_tokens: int = Field(4096, ge=1024, le=8192, description="台本生成最大トークン数")
    
    # プロダクションモード設定
    podcast_production_mode: bool = Field(False, description="プロダクションモード有効化")
    podcast_target_duration_minutes: float = Field(10.0, ge=5.0, le=20.0, description="目標配信時間（分）")
    podcast_target_script_chars: int = Field(2700, ge=2600, le=2800, description="目標台本文字数")
    
    # TTS関連設定
    tts_enabled: bool = Field(True, description="TTS機能有効化")
    tts_voice_speed: float = Field(1.0, ge=0.5, le=2.0, description="音声速度")
    tts_voice_pitch: float = Field(0.0, ge=-20.0, le=20.0, description="音声ピッチ")
    
    # LINE配信設定
    line_notify_enabled: bool = Field(True, description="LINE通知有効化")
    line_notify_token: Optional[str] = Field(None, description="LINE Notify トークン")
    
    process_prompt_template: str = Field(
        default="""
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
    google: Optional[GoogleConfig] = None
    ai: Optional[AIConfig] = None
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