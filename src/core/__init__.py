# -*- coding: utf-8 -*-

"""
コアモジュール
"""

try:
    from .news_processor import NewsProcessor
    _CORE_AVAILABLE = True
except ImportError:
    NewsProcessor = None  # type: ignore
    _CORE_AVAILABLE = False

__all__ = ["NewsProcessor"]
