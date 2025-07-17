# -*- coding: utf-8 -*-

"""
カスタム例外クラス
"""

from typing import Optional, Any, Dict
from dataclasses import dataclass


@dataclass
class ErrorContext:
    """エラー発生時のコンテキスト情報"""
    operation: str
    component: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class NewsAggregatorError(Exception):
    """ニュース集約アプリケーションのベース例外"""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(message)
        self.context = context


class RetryableError(NewsAggregatorError):
    """リトライ可能なエラーの基底クラス"""
    pass


class NonRetryableError(NewsAggregatorError):
    """リトライ不可能なエラーの基底クラス"""
    pass


class ScrapingError(RetryableError):
    """スクレイピング関連エラー"""
    pass


class AIProcessingError(RetryableError):
    """AI処理関連エラー"""
    pass


class DatabaseError(RetryableError):
    """データベース関連エラー"""
    pass


class ConfigurationError(NonRetryableError):
    """設定関連エラー"""
    pass


class AuthenticationError(NonRetryableError):
    """認証関連エラー"""
    pass


class ValidationError(NonRetryableError):
    """バリデーション関連エラー"""
    pass


class HTMLGenerationError(NewsAggregatorError):
    """HTML生成関連エラー"""
    pass


class RateLimitError(RetryableError):
    """レート制限エラー"""
    pass


class TimeoutError(RetryableError):
    """タイムアウトエラー"""
    pass