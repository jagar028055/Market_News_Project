# -*- coding: utf-8 -*-

"""
エラーハンドリング機能
"""

import logging
import traceback
from typing import Any, Callable, Dict, Optional, Type, Union
from functools import wraps
import time
from contextlib import contextmanager
from datetime import datetime

from .custom_exceptions import (
    NewsAggregatorError,
    RetryableError,
    NonRetryableError,
    ErrorContext
)


class ErrorHandler:
    """エラーハンドリングのメインクラス"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_metrics = {
            'total_errors': 0,
            'retryable_errors': 0,
            'non_retryable_errors': 0,
            'retry_attempts': 0,
            'successful_retries': 0
        }
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        reraise: bool = True
    ) -> None:
        """エラーの処理とログ記録"""
        self.error_metrics['total_errors'] += 1
        
        # エラーの分類
        if isinstance(error, RetryableError):
            self.error_metrics['retryable_errors'] += 1
            error_type = "RETRYABLE"
        elif isinstance(error, NonRetryableError):
            self.error_metrics['non_retryable_errors'] += 1
            error_type = "NON_RETRYABLE"
        else:
            error_type = "UNKNOWN"
        
        # ログ記録
        log_data = {
            'error_type': error_type,
            'error_class': error.__class__.__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }
        
        if context:
            log_data.update({
                'operation': context.operation,
                'component': context.component,
                'timestamp': context.timestamp,
                'details': context.details
            })
        
        self.logger.error(f"エラーが発生しました: {error}", extra=log_data)
        
        if reraise:
            raise error
    
    def create_context(
        self,
        operation: str,
        component: str,
        details: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """エラーコンテキストの作成"""
        return ErrorContext(
            operation=operation,
            component=component,
            timestamp=datetime.now().isoformat(),
            details=details or {}
        )
    
    def get_metrics(self) -> Dict[str, int]:
        """エラーメトリクスの取得"""
        return self.error_metrics.copy()
    
    def reset_metrics(self) -> None:
        """エラーメトリクスのリセット"""
        for key in self.error_metrics:
            self.error_metrics[key] = 0


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (RetryableError,),
    error_handler: Optional[ErrorHandler] = None
) -> Callable:
    """
    指数バックオフ付きリトライデコレータ
    
    Args:
        max_retries: 最大リトライ回数
        base_delay: 基本遅延時間（秒）
        max_delay: 最大遅延時間（秒）
        backoff_factor: バックオフ倍率
        jitter: ジッターの有無
        exceptions: リトライ対象の例外タプル
        error_handler: エラーハンドラー
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            handler = error_handler or ErrorHandler()
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    handler.error_metrics['retry_attempts'] += 1
                    
                    if attempt == max_retries:
                        context = handler.create_context(
                            operation=func.__name__,
                            component=func.__module__,
                            details={'max_retries_exceeded': True, 'attempt': attempt}
                        )
                        handler.handle_error(e, context, reraise=True)
                    
                    # 遅延時間の計算
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    
                    if jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)  # 50-100%の範囲でジッター
                    
                    handler.logger.warning(
                        f"リトライ実行 (試行 {attempt + 1}/{max_retries + 1}): {e}",
                        extra={
                            'function': func.__name__,
                            'attempt': attempt + 1,
                            'delay': delay,
                            'error': str(e)
                        }
                    )
                    
                    time.sleep(delay)
                except Exception as e:
                    # リトライ対象外の例外
                    context = handler.create_context(
                        operation=func.__name__,
                        component=func.__module__,
                        details={'non_retryable_error': True}
                    )
                    handler.handle_error(e, context, reraise=True)
            
            handler.error_metrics['successful_retries'] += 1
            return None  # 実際にはここに到達しない
        
        return wrapper
    return decorator


@contextmanager
def error_context(
    operation: str,
    component: str,
    logger: Optional[logging.Logger] = None,
    details: Optional[Dict[str, Any]] = None
):
    """
    エラーコンテキストマネージャー
    
    Usage:
        with error_context("data_processing", "scraper") as ctx:
            # 処理
            pass
    """
    handler = ErrorHandler(logger)
    context = handler.create_context(operation, component, details)
    
    try:
        yield context
    except Exception as e:
        handler.handle_error(e, context, reraise=True)


def safe_execute(
    func: Callable,
    *args,
    default_value: Any = None,
    error_handler: Optional[ErrorHandler] = None,
    **kwargs
) -> Any:
    """
    安全な関数実行
    
    Args:
        func: 実行する関数
        *args: 関数の位置引数
        default_value: エラー時のデフォルト値
        error_handler: エラーハンドラー
        **kwargs: 関数のキーワード引数
    
    Returns:
        関数の実行結果またはデフォルト値
    """
    handler = error_handler or ErrorHandler()
    
    try:
        return func(*args, **kwargs)
    except Exception as e:
        context = handler.create_context(
            operation=func.__name__,
            component=func.__module__,
            details={'safe_execution': True, 'default_value': default_value}
        )
        handler.handle_error(e, context, reraise=False)
        return default_value