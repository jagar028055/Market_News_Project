# -*- coding: utf-8 -*-

"""
拡張SNSコンテンツ処理システム - 設定ファイル

独立ワークフロー専用の設定を管理
"""

import os
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class EnhancedContentConfig:
    """拡張コンテンツ処理システムの設定"""
    
    # マーケットデータ設定
    MARKET_DATA_CACHE_DURATION: int = 300  # 秒（5分）
    MARKET_DATA_TIMEOUT: int = 30  # 秒
    YAHOO_FINANCE_RETRY_COUNT: int = 3
    STOOQ_RETRY_COUNT: int = 2
    
    # AI処理設定
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash-lite"
    GEMINI_API_TIMEOUT: int = 30
    GEMINI_MAX_RETRIES: int = 3
    ENABLE_MARKET_CONTEXT: bool = True
    
    # 品質管理設定
    MIN_QUALITY_SCORE: float = 70.0
    SIMILARITY_THRESHOLD: float = 0.7
    MIN_DIVERSITY_SCORE: float = 0.6
    ENABLE_FACT_CHECK: bool = True
    FACT_CHECK_TOLERANCE_PERCENTAGE: float = 2.0
    
    # テンプレート設定
    DEFAULT_TEMPLATE: str = "STANDARD"
    TEMPLATE_SELECTION_FACTORS: Dict[str, float] = None
    
    # ログ設定
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PREFIX: str = "enhanced_content"
    ENABLE_FILE_LOGGING: bool = True
    
    # API設定
    REQUEST_RATE_LIMIT: int = 10  # requests per second
    API_RETRY_DELAY: float = 1.0  # seconds
    
    def __post_init__(self):
        """初期化後の設定"""
        if self.TEMPLATE_SELECTION_FACTORS is None:
            self.TEMPLATE_SELECTION_FACTORS = {
                "volatility_weight": 0.3,
                "sentiment_weight": 0.25, 
                "time_weight": 0.2,
                "content_weight": 0.25
            }

# グローバル設定インスタンス
CONFIG = EnhancedContentConfig()

# マーケットデータ取得対象資産
MARKET_SYMBOLS = {
    "stock_indices": [
        "^N225",    # 日経平均
        "^DJI",     # ダウ
        "^GSPC",    # S&P 500
        "^IXIC",    # NASDAQ
        "^FTSE",    # FTSE 100
        "^GDAXI",   # DAX
    ],
    "currency_pairs": [
        "USDJPY",   # USD/JPY
        "EURUSD",   # EUR/USD
        "GBPUSD",   # GBP/USD
        "AUDUSD",   # AUD/USD
        "EURJPY",   # EUR/JPY
    ],
    "commodities": [
        "GC=F",     # Gold
        "CL=F",     # Crude Oil
        "BTC-USD",  # Bitcoin
        "ETH-USD",  # Ethereum
    ]
}

# テンプレート定義
TEMPLATE_DEFINITIONS = {
    "MARKET_CRASH": {
        "name": "市場暴落対応",
        "priority": 90,
        "triggers": {
            "volatility_threshold": 80,
            "negative_sentiment_threshold": 0.7,
            "major_index_drop_threshold": -3.0
        },
        "sections": ["market_alert", "impact_analysis", "recovery_outlook"]
    },
    "FED_POLICY": {
        "name": "FRB政策フォーカス", 
        "priority": 85,
        "triggers": {
            "fed_keywords": ["FRB", "FOMC", "政策金利", "量的緩和"],
            "us_focus": True
        },
        "sections": ["policy_summary", "market_reaction", "future_implications"]
    },
    "EARNINGS_SEASON": {
        "name": "決算シーズン",
        "priority": 75,
        "triggers": {
            "earnings_keywords": ["決算", "業績", "四半期"],
            "seasonal_factor": True
        },
        "sections": ["earnings_highlights", "sector_performance", "outlook"]
    },
    "GEOPOLITICAL": {
        "name": "地政学リスク",
        "priority": 80,
        "triggers": {
            "geopolitical_keywords": ["地政学", "紛争", "制裁", "選挙"],
            "safe_haven_movement": True
        },
        "sections": ["risk_assessment", "market_impact", "safe_haven_trends"]
    },
    "CRYPTO_FOCUS": {
        "name": "暗号資産フォーカス",
        "priority": 70,
        "triggers": {
            "crypto_keywords": ["ビットコイン", "仮想通貨", "暗号資産", "ブロックチェーン"],
            "crypto_volatility_threshold": 60
        },
        "sections": ["crypto_market", "regulation_impact", "institutional_trends"]
    },
    "STANDARD": {
        "name": "標準テンプレート",
        "priority": 50,
        "triggers": {},
        "sections": ["market_summary", "key_news", "outlook"]
    }
}

# 品質チェック基準
QUALITY_CRITERIA = {
    "summary_quality": {
        "min_length": 50,
        "max_length": 500,
        "required_elements": ["主要ポイント", "影響分析"],
        "weight": 0.4
    },
    "information_completeness": {
        "required_fields": ["title", "summary", "category", "region"],
        "optional_fields": ["source", "sentiment_label"],
        "weight": 0.3
    },
    "language_quality": {
        "check_grammar": True,
        "check_readability": True,
        "min_readability_score": 60,
        "weight": 0.3
    }
}

# 類似度チェック設定
SIMILARITY_CONFIG = {
    "stop_words": [
        'は', 'が', 'を', 'に', 'へ', 'と', 'で', 'の', 'から', 'まで',
        'した', 'する', 'される', 'している', 'です', 'である', 'だった',
        'こと', 'もの', 'ため', 'など', 'として', 'について', 'により',
        '年', '月', '日', '時', '分', 'および', 'または', 'しかし', 'また'
    ],
    "similarity_weights": {
        "title_weight": 0.4,
        "summary_weight": 0.5,
        "jaccard_weight": 0.1
    },
    "diversity_weights": {
        "content_diversity": 0.4,
        "category_diversity": 0.25,
        "region_diversity": 0.2,
        "source_diversity": 0.15
    }
}

# ファクトチェック設定
FACT_CHECK_CONFIG = {
    "numerical_patterns": {
        'percentage': r'([-+]?\\d+\\.?\\d*)[%％]',
        'price': r'(\\d+(?:,\\d{3})*(?:\\.\\d+)?)円',
        'points': r'([-+]?\\d+(?:,\\d{3})*(?:\\.\\d+)?)ポイント',
        'yen_rate': r'1ドル[=＝](\\d+(?:\\.\\d+)?)円',
        'index_value': r'(\\d+(?:,\\d{3})*(?:\\.\\d+)?)で'
    },
    "market_indicators": {
        '日経平均': '^N225',
        'ダウ': '^DJI', 
        'ナスダック': '^IXIC',
        'S&P500': '^GSPC',
        'ドル円': 'USDJPY',
        'ユーロドル': 'EURUSD'
    },
    "sentiment_keywords": {
        "positive": ['上昇', '高', '増加', '好調', '改善', '強い', '買い'],
        "negative": ['下落', '低', '減少', '悪化', '弱い', '売り', '下がる']
    }
}

# 環境変数から設定を上書き
def load_environment_overrides():
    """環境変数から設定を上書き"""
    
    # API設定
    if os.getenv("GEMINI_API_KEY"):
        CONFIG.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # 品質設定  
    if os.getenv("MIN_QUALITY_SCORE"):
        CONFIG.MIN_QUALITY_SCORE = float(os.getenv("MIN_QUALITY_SCORE"))
        
    if os.getenv("SIMILARITY_THRESHOLD"):
        CONFIG.SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD"))
    
    # 機能フラグ
    if os.getenv("ENABLE_FACT_CHECK"):
        CONFIG.ENABLE_FACT_CHECK = os.getenv("ENABLE_FACT_CHECK").lower() == "true"
        
    if os.getenv("ENABLE_MARKET_CONTEXT"):
        CONFIG.ENABLE_MARKET_CONTEXT = os.getenv("ENABLE_MARKET_CONTEXT").lower() == "true"
    
    # ログ設定
    if os.getenv("LOG_LEVEL"):
        CONFIG.LOG_LEVEL = os.getenv("LOG_LEVEL").upper()

# 設定検証
def validate_config():
    """設定値の妥当性を検証"""
    errors = []
    
    # 数値範囲チェック
    if not 0 <= CONFIG.MIN_QUALITY_SCORE <= 100:
        errors.append("MIN_QUALITY_SCORE must be between 0 and 100")
    
    if not 0 <= CONFIG.SIMILARITY_THRESHOLD <= 1:
        errors.append("SIMILARITY_THRESHOLD must be between 0 and 1")
    
    if not 0 <= CONFIG.MIN_DIVERSITY_SCORE <= 1:
        errors.append("MIN_DIVERSITY_SCORE must be between 0 and 1")
    
    # 必須設定チェック
    required_env_vars = ["GEMINI_API_KEY"]
    for var in required_env_vars:
        if not os.getenv(var):
            errors.append(f"Environment variable {var} is required")
    
    return errors

# 初期化時に環境変数を読み込み
load_environment_overrides()

# エクスポート
__all__ = [
    'CONFIG',
    'MARKET_SYMBOLS', 
    'TEMPLATE_DEFINITIONS',
    'QUALITY_CRITERIA',
    'SIMILARITY_CONFIG',
    'FACT_CHECK_CONFIG',
    'validate_config',
    'load_environment_overrides'
]