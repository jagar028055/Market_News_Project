# -*- coding: utf-8 -*-

"""
配信エラーハンドリングシステム
リトライ機能、代替手段、ユーザー通知を提供する包括的なエラー管理
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import json
import hashlib

from .message_templates import MessageTemplates


class ErrorType(Enum):
    """エラータイプ定義"""

    TTS_GENERATION_FAILED = "tts_generation_failed"
    AUDIO_PROCESSING_FAILED = "audio_processing_failed"
    GITHUB_UPLOAD_FAILED = "github_upload_failed"
    RSS_GENERATION_FAILED = "rss_generation_failed"
    LINE_BROADCAST_FAILED = "line_broadcast_failed"
    GEMINI_API_ERROR = "gemini_api_error"
    NETWORK_ERROR = "network_error"
    FILE_SYSTEM_ERROR = "file_system_error"
    AUTHENTICATION_ERROR = "authentication_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(Enum):
    """エラー重要度定義"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """エラー情報データクラス"""

    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3
    backoff_seconds: int = 60
    context: Dict[str, Any] = field(default_factory=dict)
    stacktrace: Optional[str] = None
    resolved: bool = False

    @property
    def error_id(self) -> str:
        """エラー固有ID生成"""
        content = f"{self.error_type.value}_{self.message}_{self.timestamp.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    @property
    def can_retry(self) -> bool:
        """リトライ可能かチェック"""
        return self.retry_count < self.max_retries and not self.resolved

    @property
    def next_retry_time(self) -> datetime:
        """次回リトライ時刻計算"""
        # 指数バックオフ戦略
        delay = self.backoff_seconds * (2**self.retry_count)
        return self.timestamp + timedelta(seconds=delay)


class DistributionErrorHandler:
    """
    ポッドキャスト配信エラーハンドリングシステム

    Features:
    - 指数バックオフによるリトライ機能
    - エラータイプ別の適切な対応策
    - ユーザー通知システム
    - エラー履歴管理
    - 代替配信手段の実装
    - 自動復旧メカニズム
    """

    def __init__(
        self,
        base_url: str = "https://jagar028055.github.io/Market_News",
        error_log_path: str = "./logs/distribution_errors.json",
    ):
        self.logger = logging.getLogger(__name__)
        self.base_url = base_url
        self.error_log_path = Path(error_log_path)
        self.error_log_path.parent.mkdir(parents=True, exist_ok=True)

        # メッセージテンプレート
        self.message_templates = MessageTemplates(base_url)

        # エラー履歴
        self.error_history: Dict[str, ErrorInfo] = {}
        self.load_error_history()

        # エラータイプ別設定
        self.error_config = self._initialize_error_config()

        # 代替配信方法のハンドラー
        self.fallback_handlers: Dict[str, Callable] = {}

    def _initialize_error_config(self) -> Dict[ErrorType, Dict[str, Any]]:
        """エラータイプ別設定初期化"""
        return {
            ErrorType.TTS_GENERATION_FAILED: {
                "max_retries": 3,
                "backoff_seconds": 30,
                "severity": ErrorSeverity.HIGH,
                "user_notification": True,
                "fallback_enabled": True,
            },
            ErrorType.AUDIO_PROCESSING_FAILED: {
                "max_retries": 2,
                "backoff_seconds": 60,
                "severity": ErrorSeverity.HIGH,
                "user_notification": True,
                "fallback_enabled": True,
            },
            ErrorType.GITHUB_UPLOAD_FAILED: {
                "max_retries": 5,
                "backoff_seconds": 120,
                "severity": ErrorSeverity.MEDIUM,
                "user_notification": False,
                "fallback_enabled": True,
            },
            ErrorType.RSS_GENERATION_FAILED: {
                "max_retries": 3,
                "backoff_seconds": 30,
                "severity": ErrorSeverity.MEDIUM,
                "user_notification": False,
                "fallback_enabled": False,
            },
            ErrorType.LINE_BROADCAST_FAILED: {
                "max_retries": 4,
                "backoff_seconds": 300,  # 5分
                "severity": ErrorSeverity.LOW,
                "user_notification": False,
                "fallback_enabled": False,
            },
            ErrorType.GEMINI_API_ERROR: {
                "max_retries": 3,
                "backoff_seconds": 180,  # 3分
                "severity": ErrorSeverity.HIGH,
                "user_notification": True,
                "fallback_enabled": True,
            },
            ErrorType.NETWORK_ERROR: {
                "max_retries": 5,
                "backoff_seconds": 60,
                "severity": ErrorSeverity.MEDIUM,
                "user_notification": False,
                "fallback_enabled": True,
            },
            ErrorType.QUOTA_EXCEEDED: {
                "max_retries": 0,  # クォータ超過は即座に停止
                "backoff_seconds": 3600,  # 1時間後
                "severity": ErrorSeverity.CRITICAL,
                "user_notification": True,
                "fallback_enabled": False,
            },
            ErrorType.AUTHENTICATION_ERROR: {
                "max_retries": 1,
                "backoff_seconds": 600,  # 10分
                "severity": ErrorSeverity.CRITICAL,
                "user_notification": True,
                "fallback_enabled": False,
            },
        }

    def handle_error(
        self,
        error_type: Union[ErrorType, str],
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ) -> ErrorInfo:
        """
        エラーを処理し、適切な対応を実行

        Args:
            error_type: エラータイプ
            message: エラーメッセージ
            context: エラー発生時のコンテキスト
            exception: 発生した例外オブジェクト

        Returns:
            ErrorInfo: エラー情報オブジェクト
        """
        # ErrorType enum変換
        if isinstance(error_type, str):
            try:
                error_type = ErrorType(error_type)
            except ValueError:
                error_type = ErrorType.UNKNOWN_ERROR

        # エラー設定取得
        config = self.error_config.get(error_type, self.error_config[ErrorType.UNKNOWN_ERROR])

        # ErrorInfo作成
        error_info = ErrorInfo(
            error_type=error_type,
            severity=config["severity"],
            message=message,
            max_retries=config["max_retries"],
            backoff_seconds=config["backoff_seconds"],
            context=context or {},
            stacktrace=str(exception) if exception else None,
        )

        # エラー履歴に記録
        self.error_history[error_info.error_id] = error_info
        self.save_error_history()

        # ログ記録
        self.logger.error(
            f"Distribution error: {error_type.value} - {message}",
            extra={"error_id": error_info.error_id, "context": context},
        )

        # ユーザー通知
        if config["user_notification"]:
            self._notify_user_about_error(error_info)

        return error_info

    async def retry_operation(
        self, error_info: ErrorInfo, operation: Callable, *args, **kwargs
    ) -> bool:
        """
        操作をリトライ実行

        Args:
            error_info: エラー情報
            operation: リトライする操作
            args, kwargs: 操作に渡すパラメータ

        Returns:
            bool: リトライ成功したかどうか
        """
        if not error_info.can_retry:
            self.logger.warning(f"Cannot retry error {error_info.error_id}: max retries exceeded")
            return False

        # リトライ時刻まで待機
        now = datetime.now()
        if now < error_info.next_retry_time:
            wait_seconds = (error_info.next_retry_time - now).total_seconds()
            self.logger.info(
                f"Waiting {wait_seconds:.1f}s before retry for error {error_info.error_id}"
            )
            await asyncio.sleep(wait_seconds)

        # リトライカウント更新
        error_info.retry_count += 1
        self.save_error_history()

        try:
            # 操作実行
            result = (
                await operation(*args, **kwargs)
                if asyncio.iscoroutinefunction(operation)
                else operation(*args, **kwargs)
            )

            # 成功時の処理
            error_info.resolved = True
            self.save_error_history()

            self.logger.info(
                f"Retry successful for error {error_info.error_id} (attempt {error_info.retry_count})"
            )

            # 成功通知
            self._notify_user_about_recovery(error_info)

            return True

        except Exception as e:
            # 失敗時の処理
            self.logger.error(
                f"Retry failed for error {error_info.error_id} (attempt {error_info.retry_count}): {str(e)}"
            )
            self.save_error_history()

            # 最大リトライ回数に到達した場合の処理
            if not error_info.can_retry:
                await self._handle_max_retries_exceeded(error_info, e)

            return False

    async def _handle_max_retries_exceeded(self, error_info: ErrorInfo, last_exception: Exception):
        """最大リトライ回数到達時の処理"""
        self.logger.critical(f"Max retries exceeded for error {error_info.error_id}")

        # 代替手段の実行
        config = self.error_config.get(error_info.error_type, {})
        if config.get("fallback_enabled", False):
            await self._execute_fallback_strategy(error_info)

        # ユーザー通知（重要度がHIGH以上の場合）
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            error_data = {
                "type": f"{error_info.error_type.value} (最大リトライ到達)",
                "timestamp": error_info.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "details": f"リトライ{error_info.retry_count}回後も解決できませんでした。\\n最新エラー: {str(last_exception)}",
                "retry_count": error_info.retry_count,
                "next_retry": "",
            }

            notification_msg = self.message_templates.create_error_notification(error_data)
            await self._send_notification(notification_msg)

    async def _execute_fallback_strategy(self, error_info: ErrorInfo):
        """代替手段の実行"""
        fallback_handler = self.fallback_handlers.get(error_info.error_type.value)

        if fallback_handler:
            try:
                self.logger.info(f"Executing fallback strategy for {error_info.error_type.value}")
                await fallback_handler(error_info)
            except Exception as e:
                self.logger.error(
                    f"Fallback strategy failed for {error_info.error_type.value}: {str(e)}"
                )
        else:
            # デフォルト代替手段
            await self._default_fallback_strategy(error_info)

    async def _default_fallback_strategy(self, error_info: ErrorInfo):
        """デフォルト代替手段"""
        if error_info.error_type in [
            ErrorType.TTS_GENERATION_FAILED,
            ErrorType.AUDIO_PROCESSING_FAILED,
        ]:
            # 音声生成失敗時：簡易音声またはテキスト配信
            self.logger.info("Executing fallback: text-only notification")
            fallback_msg = f"""🎙️ ポッドキャスト生成エラー
            
本日のポッドキャストは技術的な問題により生成できませんでした。
代わりにテキスト形式で主要ニュースをお届けします。

エラー詳細: {error_info.message}

システム復旧後、通常配信を再開いたします。
ご迷惑をおかけして申し訳ございません。"""

            await self._send_notification(fallback_msg)

        elif error_info.error_type == ErrorType.GITHUB_UPLOAD_FAILED:
            # アップロード失敗時：ローカル保存と手動アップロード指示
            self.logger.info("Executing fallback: local file preservation")
            # ファイルを安全な場所に移動
            # 管理者に手動アップロード指示を送信

        elif error_info.error_type == ErrorType.GEMINI_API_ERROR:
            # API失敗時：キャッシュされたコンテンツまたは簡易生成
            self.logger.info("Executing fallback: cached content or simple generation")

    def register_fallback_handler(self, error_type: Union[ErrorType, str], handler: Callable):
        """代替手段ハンドラーを登録"""
        if isinstance(error_type, ErrorType):
            error_type = error_type.value

        self.fallback_handlers[error_type] = handler
        self.logger.info(f"Registered fallback handler for {error_type}")

    def _notify_user_about_error(self, error_info: ErrorInfo):
        """ユーザーにエラー通知"""
        error_data = {
            "type": error_info.error_type.value,
            "timestamp": error_info.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "details": error_info.message,
            "retry_count": error_info.retry_count,
            "next_retry": (
                error_info.next_retry_time.strftime("%Y-%m-%d %H:%M:%S")
                if error_info.can_retry
                else ""
            ),
        }

        notification_msg = self.message_templates.create_error_notification(error_data)
        asyncio.create_task(self._send_notification(notification_msg))

    def _notify_user_about_recovery(self, error_info: ErrorInfo):
        """ユーザーに復旧通知"""
        recovery_msg = f"""✅ システム復旧完了

━━━━━━━━━━━━━━━━━━━━━
🎙️ ポッドキャスト配信システム復旧
━━━━━━━━━━━━━━━━━━━━━

先程発生していた問題が解決されました：
• エラータイプ: {error_info.error_type.value}
• 解決日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• リトライ回数: {error_info.retry_count}回

🎧 通常の配信を再開いたします。
ご迷惑をおかけして申し訳ありませんでした。

システムは正常に動作しています。"""

        asyncio.create_task(self._send_notification(recovery_msg))

    async def _send_notification(self, message: str):
        """通知送信（実装は外部システムに依存）"""
        # 実際の実装では LINE API、メール、Slack等に送信
        self.logger.info(f"Notification: {message}")
        # ここに実際の通知送信ロジックを実装

    def get_error_statistics(self) -> Dict[str, Any]:
        """エラー統計情報を取得"""
        stats = {
            "total_errors": len(self.error_history),
            "resolved_errors": len([e for e in self.error_history.values() if e.resolved]),
            "pending_errors": len([e for e in self.error_history.values() if not e.resolved]),
            "error_types": {},
            "severity_distribution": {},
            "average_resolution_time": 0,
        }

        # エラータイプ別統計
        for error in self.error_history.values():
            error_type = error.error_type.value
            stats["error_types"][error_type] = stats["error_types"].get(error_type, 0) + 1

            severity = error.severity.value
            stats["severity_distribution"][severity] = (
                stats["severity_distribution"].get(severity, 0) + 1
            )

        # 解決時間計算
        resolved_errors = [e for e in self.error_history.values() if e.resolved]
        if resolved_errors:
            total_resolution_time = sum(
                [e.retry_count * e.backoff_seconds for e in resolved_errors]
            )
            stats["average_resolution_time"] = total_resolution_time / len(resolved_errors)

        return stats

    def cleanup_old_errors(self, days_old: int = 30):
        """古いエラー記録をクリーンアップ"""
        cutoff_date = datetime.now() - timedelta(days=days_old)

        old_errors = [
            error_id
            for error_id, error in self.error_history.items()
            if error.timestamp < cutoff_date and error.resolved
        ]

        for error_id in old_errors:
            del self.error_history[error_id]

        self.save_error_history()
        self.logger.info(f"Cleaned up {len(old_errors)} old error records")

    def load_error_history(self):
        """エラー履歴をファイルから読み込み"""
        if not self.error_log_path.exists():
            return

        try:
            with open(self.error_log_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for error_id, error_data in data.items():
                # JSON からErrorInfoオブジェクトを復元
                error_info = ErrorInfo(
                    error_type=ErrorType(error_data["error_type"]),
                    severity=ErrorSeverity(error_data["severity"]),
                    message=error_data["message"],
                    timestamp=datetime.fromisoformat(error_data["timestamp"]),
                    retry_count=error_data["retry_count"],
                    max_retries=error_data["max_retries"],
                    backoff_seconds=error_data["backoff_seconds"],
                    context=error_data.get("context", {}),
                    stacktrace=error_data.get("stacktrace"),
                    resolved=error_data.get("resolved", False),
                )
                self.error_history[error_id] = error_info

            self.logger.info(
                f"Loaded {len(self.error_history)} error records from {self.error_log_path}"
            )

        except Exception as e:
            self.logger.error(f"Failed to load error history: {str(e)}")

    def save_error_history(self):
        """エラー履歴をファイルに保存"""
        try:
            data = {}
            for error_id, error_info in self.error_history.items():
                data[error_id] = {
                    "error_type": error_info.error_type.value,
                    "severity": error_info.severity.value,
                    "message": error_info.message,
                    "timestamp": error_info.timestamp.isoformat(),
                    "retry_count": error_info.retry_count,
                    "max_retries": error_info.max_retries,
                    "backoff_seconds": error_info.backoff_seconds,
                    "context": error_info.context,
                    "stacktrace": error_info.stacktrace,
                    "resolved": error_info.resolved,
                }

            with open(self.error_log_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save error history: {str(e)}")


# 使用例とテストヘルパー
class ErrorHandlerTestHelper:
    """エラーハンドラーのテスト用ヘルパークラス"""

    @staticmethod
    def simulate_tts_error():
        """TTS生成エラーをシミュレート"""
        return Exception("Gemini TTS API rate limit exceeded")

    @staticmethod
    def simulate_upload_error():
        """アップロードエラーをシミュレート"""
        return Exception("GitHub API authentication failed")

    @staticmethod
    async def mock_successful_operation():
        """成功する操作のモック"""
        await asyncio.sleep(0.1)  # 実際の処理をシミュレート
        return {"status": "success", "result": "operation completed"}

    @staticmethod
    async def mock_failing_operation():
        """失敗する操作のモック"""
        await asyncio.sleep(0.1)
        raise Exception("Mock operation failed")


if __name__ == "__main__":
    # 使用例
    async def main():
        error_handler = DistributionErrorHandler()

        # エラー処理の例
        error = error_handler.handle_error(
            ErrorType.TTS_GENERATION_FAILED,
            "Gemini API quota exceeded",
            context={"episode_number": 42, "retry_attempt": 1},
        )

        print(f"Error registered: {error.error_id}")
        print(f"Can retry: {error.can_retry}")
        print(f"Next retry: {error.next_retry_time}")

        # リトライの例
        success = await error_handler.retry_operation(
            error, ErrorHandlerTestHelper.mock_successful_operation
        )

        print(f"Retry successful: {success}")

        # 統計情報表示
        stats = error_handler.get_error_statistics()
        print(f"Error statistics: {stats}")

    # asyncio.run(main())
