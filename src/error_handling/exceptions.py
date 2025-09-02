# -*- coding: utf-8 -*-

"""
例外クラスのエクスポート
custom_exceptions.pyからの再エクスポート
"""

from .custom_exceptions import (
    ErrorContext,
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
    PodcastPublishError,
    PodcastGenerationError,
    TTSError,
    AudioProcessingError,
)

__all__ = [
    'ErrorContext',
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
    'PodcastPublishError',
    'PodcastGenerationError',
    'TTSError',
    'AudioProcessingError',
]