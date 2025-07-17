# -*- coding: utf-8 -*-

"""
エラーハンドリングモジュール
"""

from .custom_exceptions import (
    NewsAggregatorError,
    RetryableError,
    NonRetryableError,
    ScrapingError,
    AIProcessingError,
    DatabaseError,
    ConfigurationError,
    AuthenticationError,
    ValidationError,
    HTMLGenerationError,
    RateLimitError,
    TimeoutError,
    ErrorContext
)

from .error_handler import (
    ErrorHandler,
    retry_with_backoff,
    error_context,
    safe_execute
)

# 既存コードとの互換性のため
from .error_handler import error_context as ErrorContext

__all__ = [
    # 例外クラス
    'NewsAggregatorError',
    'RetryableError',
    'NonRetryableError',
    'ScrapingError',
    'AIProcessingError',
    'DatabaseError',
    'ConfigurationError',
    'AuthenticationError',
    'ValidationError',
    'HTMLGenerationError',
    'RateLimitError',
    'TimeoutError',
    'ErrorContext',
    
    # ハンドラー
    'ErrorHandler',
    'retry_with_backoff',
    'error_context',
    'safe_execute'
]