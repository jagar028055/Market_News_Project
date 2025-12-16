# -*- coding: utf-8 -*-

"""
通知タイミング制御システム
ポッドキャスト配信通知のスケジューリングと配信タイミング最適化
"""

import json
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import logging
from enum import Enum

# scheduleライブラリがない環境でも読み込みできるようにする
try:
    import schedule  # type: ignore
except ImportError:  # pragma: no cover - テスト環境用のフォールバック
    class _ScheduleStub:
        def __getattr__(self, name):
            return self

        def __call__(self, *args, **kwargs):
            return self

    schedule = _ScheduleStub()


class NotificationPriority(Enum):
    """通知優先度"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(Enum):
    """通知ステータス"""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationScheduler:
    """
    通知タイミング制御クラス

    ポッドキャスト配信通知のスケジューリング、配信タイミング最適化、
    バッチ処理、エラーハンドリングを行う
    """

    def __init__(self, config, logger: logging.Logger):
        """
        初期化

        Args:
            config: アプリケーション設定
            logger: ロガー
        """
        self.config = config
        self.logger = logger

        # スケジュールファイル
        self.schedule_file = Path(config.project_root) / "data" / "notification_schedule.json"
        self.schedule_file.parent.mkdir(parents=True, exist_ok=True)

        # 通知キュー
        self.notification_queue = []
        self.scheduled_notifications = {}

        # スケジューラー設定
        self.is_running = False
        self.scheduler_thread = None

        # 配信時間設定
        self.optimal_times = [
            "07:00",  # 朝の通勤時間
            "12:00",  # 昼休み
            "17:00",  # 夕方の通勤時間
            "19:00",  # 夕食時間
            "21:00",  # 夜のリラックスタイム
        ]

        # バッチ処理設定
        self.batch_size = 5
        self.batch_interval = 60  # 秒

        # リトライ設定
        self.max_retries = 3
        self.retry_intervals = [60, 300, 900]  # 1分、5分、15分後

        # レート制限
        self.rate_limit_per_hour = 1000
        self.rate_limit_counter = {}

        self._load_schedule()

    def schedule_podcast_notification(
        self,
        episode_info: Dict[str, Any],
        articles: List[Dict[str, Any]],
        scheduled_time: Optional[datetime] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        delivery_options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        ポッドキャスト通知をスケジュール

        Args:
            episode_info: エピソード情報
            articles: 記事データ
            scheduled_time: 配信予定時刻（Noneの場合は最適時刻を自動選択）
            priority: 通知優先度
            delivery_options: 配信オプション

        Returns:
            str: 通知ID
        """
        try:
            # 通知IDを生成
            notification_id = self._generate_notification_id()

            # 配信時刻を決定
            if scheduled_time is None:
                scheduled_time = self._calculate_optimal_time(priority)

            # 通知データ作成
            notification_data = {
                "id": notification_id,
                "episode_info": episode_info,
                "articles": articles,
                "scheduled_time": scheduled_time.isoformat(),
                "priority": priority.value,
                "status": NotificationStatus.PENDING.value,
                "created_at": datetime.now().isoformat(),
                "retry_count": 0,
                "delivery_options": delivery_options or {},
                "metadata": {
                    "article_count": len(articles),
                    "estimated_duration": episode_info.get("file_size_mb", 0) * 1.5,
                    "sentiment_distribution": self._analyze_sentiment_distribution(articles),
                },
            }

            # キューに追加
            self.notification_queue.append(notification_data)

            # スケジュール保存
            self._save_schedule()

            self.logger.info(
                f"通知スケジュール追加: {notification_id} (配信予定: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')})"
            )

            # スケジューラー開始（まだ開始していない場合）
            if not self.is_running:
                self.start_scheduler()

            return notification_id

        except Exception as e:
            self.logger.error(f"通知スケジュール追加エラー: {e}")
            raise

    def start_scheduler(self) -> None:
        """スケジューラーを開始"""
        if self.is_running:
            self.logger.warning("スケジューラーは既に実行中です")
            return

        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_worker, daemon=True)
        self.scheduler_thread.start()

        self.logger.info("通知スケジューラーを開始しました")

    def stop_scheduler(self) -> None:
        """スケジューラーを停止"""
        self.is_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        self.logger.info("通知スケジューラーを停止しました")

    def _scheduler_worker(self) -> None:
        """スケジューラーワーカー"""
        self.logger.info("通知スケジューラーワーカー開始")

        while self.is_running:
            try:
                # 配信予定の通知をチェック
                self._process_pending_notifications()

                # レート制限カウンターをリセット（1時間ごと）
                self._reset_rate_limit_counter()

                # 期限切れ通知のクリーンアップ
                self._cleanup_expired_notifications()

                # 次のチェックまで待機
                time.sleep(10)  # 10秒間隔でチェック

            except Exception as e:
                self.logger.error(f"スケジューラーワーカーエラー: {e}")
                time.sleep(60)  # エラー時は1分待機

        self.logger.info("通知スケジューラーワーカー終了")

    def _process_pending_notifications(self) -> None:
        """配信予定通知の処理"""
        current_time = datetime.now()
        processed_notifications = []

        for notification in self.notification_queue:
            try:
                scheduled_time = datetime.fromisoformat(notification["scheduled_time"])
                status = NotificationStatus(notification["status"])

                # 配信時刻になった通知を処理
                if status == NotificationStatus.PENDING and scheduled_time <= current_time:
                    # レート制限チェック
                    if self._check_rate_limit():
                        notification["status"] = NotificationStatus.SENDING.value
                        self._send_notification(notification)
                        processed_notifications.append(notification)
                    else:
                        # レート制限に達している場合は5分後に再スケジュール
                        new_time = current_time + timedelta(minutes=5)
                        notification["scheduled_time"] = new_time.isoformat()
                        self.logger.warning(
                            f"レート制限により配信延期: {notification['id']} -> {new_time}"
                        )

            except Exception as e:
                self.logger.error(f"通知処理エラー: {notification.get('id', 'unknown')}: {e}")
                notification["status"] = NotificationStatus.FAILED.value
                processed_notifications.append(notification)

        # 処理済み通知をキューから削除
        for notification in processed_notifications:
            if notification in self.notification_queue:
                self.notification_queue.remove(notification)

        if processed_notifications:
            self._save_schedule()

    def _send_notification(self, notification: Dict[str, Any]) -> None:
        """
        実際の通知送信処理

        Args:
            notification: 通知データ
        """
        try:
            # LINE Broadcasterを使用して送信
            from src.podcast.integration.line_broadcaster import LineBroadcaster

            # 設定からLine Broadcasterを初期化（実際の実装では依存性注入を使用）
            line_broadcaster = LineBroadcaster(self.config, self.logger)

            # 配信オプション取得
            delivery_options = notification.get("delivery_options", {})
            use_flex = delivery_options.get("use_flex_message", True)

            # 通知送信
            success = line_broadcaster.broadcast_podcast_notification(
                notification["episode_info"],
                notification["articles"],
                audio_url=delivery_options.get("audio_url"),
                rss_url=delivery_options.get("rss_url"),
                use_flex=use_flex,
            )

            if success:
                notification["status"] = NotificationStatus.SENT.value
                notification["sent_at"] = datetime.now().isoformat()
                self.logger.info(f"通知送信成功: {notification['id']}")

                # レート制限カウンター更新
                self._update_rate_limit_counter()

            else:
                self._handle_notification_failure(notification)

        except Exception as e:
            self.logger.error(f"通知送信エラー: {notification['id']}: {e}")
            self._handle_notification_failure(notification)

    def _handle_notification_failure(self, notification: Dict[str, Any]) -> None:
        """
        通知送信失敗時の処理

        Args:
            notification: 通知データ
        """
        retry_count = notification.get("retry_count", 0)

        if retry_count < self.max_retries:
            # リトライスケジュール
            retry_delay = (
                self.retry_intervals[retry_count]
                if retry_count < len(self.retry_intervals)
                else self.retry_intervals[-1]
            )
            new_time = datetime.now() + timedelta(seconds=retry_delay)

            notification["retry_count"] = retry_count + 1
            notification["scheduled_time"] = new_time.isoformat()
            notification["status"] = NotificationStatus.PENDING.value

            # キューに戻す
            self.notification_queue.append(notification)

            self.logger.info(
                f"通知リトライスケジュール: {notification['id']} (試行 {retry_count + 1}/{self.max_retries}, {retry_delay}秒後)"
            )

        else:
            # リトライ上限に達した場合は失敗とする
            notification["status"] = NotificationStatus.FAILED.value
            notification["failed_at"] = datetime.now().isoformat()
            self.logger.error(f"通知送信失敗（リトライ上限到達）: {notification['id']}")

    def _calculate_optimal_time(self, priority: NotificationPriority) -> datetime:
        """
        最適配信時刻を計算

        Args:
            priority: 通知優先度

        Returns:
            datetime: 最適配信時刻
        """
        current_time = datetime.now()

        if priority == NotificationPriority.URGENT:
            # 緊急の場合は即座に配信
            return current_time + timedelta(seconds=30)

        elif priority == NotificationPriority.HIGH:
            # 高優先度の場合は次の最適時刻
            next_optimal = self._get_next_optimal_time(current_time)
            return next_optimal

        else:
            # 通常・低優先度の場合は次の次の最適時刻
            next_optimal = self._get_next_optimal_time(current_time)
            next_next_optimal = self._get_next_optimal_time(next_optimal + timedelta(minutes=1))
            return (
                next_next_optimal
                if priority == NotificationPriority.NORMAL
                else next_next_optimal + timedelta(hours=1)
            )

    def _get_next_optimal_time(self, from_time: datetime) -> datetime:
        """
        指定時刻以降の次の最適時刻を取得

        Args:
            from_time: 基準時刻

        Returns:
            datetime: 次の最適時刻
        """
        for time_str in self.optimal_times:
            hour, minute = map(int, time_str.split(":"))
            optimal_today = from_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if optimal_today > from_time:
                return optimal_today

        # 今日の最適時刻がすべて過ぎている場合は翌日の最初の時刻
        hour, minute = map(int, self.optimal_times[0].split(":"))
        next_day = from_time + timedelta(days=1)
        return next_day.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _check_rate_limit(self) -> bool:
        """
        レート制限チェック

        Returns:
            bool: 送信可能な場合True
        """
        current_hour = datetime.now().hour
        current_count = self.rate_limit_counter.get(current_hour, 0)
        return current_count < self.rate_limit_per_hour

    def _update_rate_limit_counter(self) -> None:
        """レート制限カウンター更新"""
        current_hour = datetime.now().hour
        self.rate_limit_counter[current_hour] = self.rate_limit_counter.get(current_hour, 0) + 1

    def _reset_rate_limit_counter(self) -> None:
        """レート制限カウンターリセット"""
        current_hour = datetime.now().hour
        # 2時間以上前のカウンターをクリア
        old_hours = [h for h in self.rate_limit_counter.keys() if abs(h - current_hour) > 2]
        for hour in old_hours:
            del self.rate_limit_counter[hour]

    def _analyze_sentiment_distribution(self, articles: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        記事のセンチメント分布を分析

        Args:
            articles: 記事データ

        Returns:
            Dict[str, int]: センチメント分布
        """
        distribution = {"Positive": 0, "Neutral": 0, "Negative": 0}

        for article in articles:
            sentiment = article.get("sentiment_label", "Neutral")
            if sentiment in distribution:
                distribution[sentiment] += 1

        return distribution

    def _cleanup_expired_notifications(self) -> None:
        """期限切れ通知のクリーンアップ"""
        cutoff_time = datetime.now() - timedelta(days=7)  # 7日前

        expired_notifications = [
            n
            for n in self.notification_queue
            if datetime.fromisoformat(n["created_at"]) < cutoff_time
        ]

        for notification in expired_notifications:
            self.notification_queue.remove(notification)

        if expired_notifications:
            self.logger.info(f"期限切れ通知を{len(expired_notifications)}件削除")
            self._save_schedule()

    def _generate_notification_id(self) -> str:
        """通知ID生成"""
        import uuid

        return f"notification_{int(time.time())}_{str(uuid.uuid4())[:8]}"

    def _load_schedule(self) -> None:
        """スケジュールファイル読み込み"""
        try:
            if self.schedule_file.exists():
                with open(self.schedule_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.notification_queue = data.get("notifications", [])
                    self.scheduled_notifications = data.get("scheduled", {})
                self.logger.info(f"通知スケジュール読み込み完了: {len(self.notification_queue)}件")
        except Exception as e:
            self.logger.warning(f"スケジュールファイル読み込みエラー: {e}")
            self.notification_queue = []
            self.scheduled_notifications = {}

    def _save_schedule(self) -> None:
        """スケジュールファイル保存"""
        try:
            data = {
                "notifications": self.notification_queue,
                "scheduled": self.scheduled_notifications,
                "last_updated": datetime.now().isoformat(),
            }

            with open(self.schedule_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        except Exception as e:
            self.logger.warning(f"スケジュールファイル保存エラー: {e}")

    def get_notification_status(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """
        通知ステータス取得

        Args:
            notification_id: 通知ID

        Returns:
            Optional[Dict[str, Any]]: 通知情報
        """
        for notification in self.notification_queue:
            if notification["id"] == notification_id:
                return notification
        return None

    def cancel_notification(self, notification_id: str) -> bool:
        """
        通知キャンセル

        Args:
            notification_id: 通知ID

        Returns:
            bool: キャンセル成功時True
        """
        for notification in self.notification_queue:
            if notification["id"] == notification_id:
                if notification["status"] in [
                    NotificationStatus.PENDING.value,
                    NotificationStatus.SCHEDULED.value,
                ]:
                    notification["status"] = NotificationStatus.CANCELLED.value
                    notification["cancelled_at"] = datetime.now().isoformat()
                    self._save_schedule()
                    self.logger.info(f"通知キャンセル: {notification_id}")
                    return True
                else:
                    self.logger.warning(
                        f"通知キャンセル不可（ステータス: {notification['status']}）: {notification_id}"
                    )
                    return False

        self.logger.warning(f"通知が見つかりません: {notification_id}")
        return False

    def get_schedule_stats(self) -> Dict[str, Any]:
        """
        スケジュール統計取得

        Returns:
            Dict[str, Any]: 統計情報
        """
        status_counts = {}
        priority_counts = {}

        for notification in self.notification_queue:
            status = notification["status"]
            priority = notification["priority"]

            status_counts[status] = status_counts.get(status, 0) + 1
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        return {
            "total_notifications": len(self.notification_queue),
            "status_distribution": status_counts,
            "priority_distribution": priority_counts,
            "rate_limit_usage": self.rate_limit_counter,
            "scheduler_running": self.is_running,
        }
