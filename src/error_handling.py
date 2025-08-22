# -*- coding: utf-8 -*-

import time
import random
import logging
from functools import wraps
from typing import Type, Tuple, Callable, Any, Optional, Union
import requests
import selenium.common.exceptions
from googleapiclient.errors import HttpError


class RetryableError(Exception):
    """リトライ可能なエラーの基底クラス"""

    pass


class NonRetryableError(Exception):
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


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    指数バックオフ付きリトライデコレータ

    Args:
        max_retries: 最大リトライ回数
        base_delay: 基本遅延時間（秒）
        max_delay: 最大遅延時間（秒）
        backoff_factor: バックオフ係数
        jitter: ジッター（ランダム要素）追加
        exceptions: リトライ対象の例外クラス
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(f"market_news.retry.{func.__name__}")

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except NonRetryableError:
                    # リトライ不可能なエラーはそのまま再発生
                    raise

                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries",
                            extra={
                                "extra_data": {
                                    "function": func.__name__,
                                    "final_error": str(e),
                                    "total_attempts": attempt + 1,
                                }
                            },
                        )
                        raise

                    # 遅延時間計算
                    delay = min(base_delay * (backoff_factor**attempt), max_delay)

                    if jitter:
                        delay += random.uniform(0, delay * 0.1)

                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__} after {delay:.2f}s",
                        extra={
                            "extra_data": {
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "delay_seconds": delay,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            }
                        },
                    )

                    time.sleep(delay)

        return wrapper

    return decorator


def handle_requests_errors(func: Callable) -> Callable:
    """requests関連エラーの統一ハンドリング"""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        logger = logging.getLogger(f"market_news.requests.{func.__name__}")

        try:
            return func(*args, **kwargs)

        except requests.exceptions.Timeout as e:
            logger.error(
                f"Request timeout in {func.__name__}",
                extra={"extra_data": {"error_type": "timeout", "error": str(e)}},
            )
            raise ScrapingError(f"Request timeout: {e}")

        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"Connection error in {func.__name__}",
                extra={"extra_data": {"error_type": "connection", "error": str(e)}},
            )
            raise ScrapingError(f"Connection error: {e}")

        except requests.exceptions.HTTPError as e:
            status_code = getattr(e.response, "status_code", None)

            if status_code and 400 <= status_code < 500:
                # 4xxエラーはリトライしない
                logger.error(
                    f"Client error in {func.__name__}",
                    extra={
                        "extra_data": {
                            "error_type": "client_error",
                            "status_code": status_code,
                            "error": str(e),
                        }
                    },
                )
                raise NonRetryableError(f"Client error {status_code}: {e}")
            else:
                # 5xxエラーはリトライ可能
                logger.error(
                    f"Server error in {func.__name__}",
                    extra={
                        "extra_data": {
                            "error_type": "server_error",
                            "status_code": status_code,
                            "error": str(e),
                        }
                    },
                )
                raise ScrapingError(f"Server error {status_code}: {e}")

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Request error in {func.__name__}",
                extra={"extra_data": {"error_type": "request", "error": str(e)}},
            )
            raise ScrapingError(f"Request error: {e}")

    return wrapper


def handle_selenium_errors(func: Callable) -> Callable:
    """Selenium関連エラーの統一ハンドリング"""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        logger = logging.getLogger(f"market_news.selenium.{func.__name__}")

        try:
            return func(*args, **kwargs)

        except selenium.common.exceptions.TimeoutException as e:
            logger.error(
                f"Selenium timeout in {func.__name__}",
                extra={"extra_data": {"error_type": "selenium_timeout", "error": str(e)}},
            )
            raise ScrapingError(f"Selenium timeout: {e}")

        except selenium.common.exceptions.NoSuchElementException as e:
            logger.warning(
                f"Element not found in {func.__name__}",
                extra={"extra_data": {"error_type": "element_not_found", "error": str(e)}},
            )
            raise ScrapingError(f"Element not found: {e}")

        except selenium.common.exceptions.WebDriverException as e:
            logger.error(
                f"WebDriver error in {func.__name__}",
                extra={"extra_data": {"error_type": "webdriver", "error": str(e)}},
            )
            raise ScrapingError(f"WebDriver error: {e}")

    return wrapper


def handle_google_api_errors(func: Callable) -> Callable:
    """Google API関連エラーの統一ハンドリング"""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        logger = logging.getLogger(f"market_news.google_api.{func.__name__}")

        try:
            return func(*args, **kwargs)

        except HttpError as e:
            status_code = e.resp.status

            if status_code == 403:
                logger.error(
                    f"Google API permission denied in {func.__name__}",
                    extra={
                        "extra_data": {
                            "error_type": "permission_denied",
                            "status_code": status_code,
                            "error": str(e),
                        }
                    },
                )
                raise NonRetryableError(f"Permission denied: {e}")

            elif status_code == 404:
                logger.error(
                    f"Google API resource not found in {func.__name__}",
                    extra={
                        "extra_data": {
                            "error_type": "not_found",
                            "status_code": status_code,
                            "error": str(e),
                        }
                    },
                )
                raise NonRetryableError(f"Resource not found: {e}")

            elif 400 <= status_code < 500:
                logger.error(
                    f"Google API client error in {func.__name__}",
                    extra={
                        "extra_data": {
                            "error_type": "client_error",
                            "status_code": status_code,
                            "error": str(e),
                        }
                    },
                )
                raise NonRetryableError(f"Client error {status_code}: {e}")

            else:
                # 5xxエラーはリトライ可能
                logger.error(
                    f"Google API server error in {func.__name__}",
                    extra={
                        "extra_data": {
                            "error_type": "server_error",
                            "status_code": status_code,
                            "error": str(e),
                        }
                    },
                )
                raise RetryableError(f"Server error {status_code}: {e}")

        except Exception as e:
            logger.error(
                f"Unexpected Google API error in {func.__name__}",
                extra={"extra_data": {"error_type": "unexpected", "error": str(e)}},
            )
            raise

    return wrapper


def safe_execute(
    func: Callable, *args, default_return: Any = None, log_errors: bool = True, **kwargs
) -> Any:
    """
    安全な関数実行ヘルパー

    Args:
        func: 実行する関数
        *args: 関数の引数
        default_return: エラー時のデフォルト戻り値
        log_errors: エラーログ出力フラグ
        **kwargs: 関数のキーワード引数
    """
    logger = logging.getLogger(f"market_news.safe_execute")

    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(
                f"Error in safe_execute for {func.__name__}",
                extra={
                    "extra_data": {
                        "function": func.__name__,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                },
            )
        return default_return


class ErrorContext:
    """エラーコンテキスト管理"""

    def __init__(self, operation: str, logger: Optional[logging.Logger] = None):
        self.operation = operation
        self.logger = logger or logging.getLogger("market_news.error_context")
        self.start_time = time.time()

    def __enter__(self):
        self.logger.info(f"Starting operation: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        if exc_type is None:
            self.logger.info(
                f"Operation completed: {self.operation}",
                extra={
                    "extra_data": {
                        "operation": self.operation,
                        "duration_ms": int(duration * 1000),
                        "status": "success",
                    }
                },
            )
        else:
            self.logger.error(
                f"Operation failed: {self.operation}",
                extra={
                    "extra_data": {
                        "operation": self.operation,
                        "duration_ms": int(duration * 1000),
                        "status": "failed",
                        "error": str(exc_val),
                        "error_type": exc_type.__name__,
                    }
                },
            )

        # 例外を再発生させない（Falseを返す）
        return False
