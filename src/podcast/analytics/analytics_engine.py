"""
配信効果測定システムのメインエンジン

このモジュールは配信効果の測定、メトリクス収集、レポート生成を管理します。
"""

import sqlite3
import logging
import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json


class DeliveryStatus(Enum):
    """配信ステータス"""

    SCHEDULED = "scheduled"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(Enum):
    """メッセージタイプ"""

    FLEX_MESSAGE = "flex_message"
    TEXT_MESSAGE = "text_message"
    CAROUSEL = "carousel"


@dataclass
class DeliveryEvent:
    """配信イベント"""

    event_id: str
    episode_id: str
    delivery_time: datetime.datetime
    message_type: MessageType
    status: DeliveryStatus
    recipient_count: int
    metadata: Dict[str, Any]


@dataclass
class EngagementEvent:
    """エンゲージメントイベント"""

    event_id: str
    episode_id: str
    user_id: str
    event_type: str  # click, view, share, subscribe, etc.
    event_time: datetime.datetime
    event_data: Dict[str, Any]


@dataclass
class PerformanceMetrics:
    """パフォーマンス指標"""

    episode_id: str
    delivery_time: datetime.datetime
    total_recipients: int
    successful_deliveries: int
    failed_deliveries: int
    click_through_rate: float
    engagement_rate: float
    avg_read_time: float
    conversion_rate: float


class AnalyticsEngine:
    """配信効果測定エンジン"""

    def __init__(self, db_path: str = "podcast_analytics.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()

    def _init_database(self):
        """データベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS delivery_events (
                    event_id TEXT PRIMARY KEY,
                    episode_id TEXT NOT NULL,
                    delivery_time TIMESTAMP NOT NULL,
                    message_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    recipient_count INTEGER NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS engagement_events (
                    event_id TEXT PRIMARY KEY,
                    episode_id TEXT NOT NULL,
                    user_id TEXT,
                    event_type TEXT NOT NULL,
                    event_time TIMESTAMP NOT NULL,
                    event_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id TEXT NOT NULL,
                    delivery_time TIMESTAMP NOT NULL,
                    total_recipients INTEGER NOT NULL,
                    successful_deliveries INTEGER NOT NULL,
                    failed_deliveries INTEGER NOT NULL,
                    click_through_rate REAL NOT NULL,
                    engagement_rate REAL NOT NULL,
                    avg_read_time REAL NOT NULL,
                    conversion_rate REAL NOT NULL,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(episode_id, delivery_time)
                )
            """
            )

            # インデックス作成
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_delivery_episode ON delivery_events(episode_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_delivery_time ON delivery_events(delivery_time)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_engagement_episode ON engagement_events(episode_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_engagement_user ON engagement_events(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_performance_episode ON performance_metrics(episode_id)"
            )

    def record_delivery_event(self, event: DeliveryEvent):
        """配信イベント記録"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO delivery_events 
                    (event_id, episode_id, delivery_time, message_type, status, 
                     recipient_count, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        event.event_id,
                        event.episode_id,
                        event.delivery_time.isoformat(),
                        event.message_type.value,
                        event.status.value,
                        event.recipient_count,
                        json.dumps(event.metadata),
                    ),
                )

            self.logger.info(f"配信イベント記録: {event.event_id}")
        except Exception as e:
            self.logger.error(f"配信イベント記録エラー: {e}")
            raise

    def record_engagement_event(self, event: EngagementEvent):
        """エンゲージメントイベント記録"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO engagement_events 
                    (event_id, episode_id, user_id, event_type, event_time, event_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        event.event_id,
                        event.episode_id,
                        event.user_id,
                        event.event_type,
                        event.event_time.isoformat(),
                        json.dumps(event.event_data),
                    ),
                )

            self.logger.info(f"エンゲージメントイベント記録: {event.event_id}")
        except Exception as e:
            self.logger.error(f"エンゲージメントイベント記録エラー: {e}")
            raise

    def calculate_performance_metrics(
        self, episode_id: str, delivery_time: datetime.datetime
    ) -> PerformanceMetrics:
        """パフォーマンス指標計算"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 配信統計取得
                delivery_stats = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_events,
                        SUM(CASE WHEN status = 'delivered' THEN recipient_count ELSE 0 END) as successful_deliveries,
                        SUM(CASE WHEN status = 'failed' THEN recipient_count ELSE 0 END) as failed_deliveries,
                        SUM(recipient_count) as total_recipients
                    FROM delivery_events 
                    WHERE episode_id = ? AND DATE(delivery_time) = DATE(?)
                """,
                    (episode_id, delivery_time.isoformat()),
                ).fetchone()

                # エンゲージメント統計取得
                engagement_stats = conn.execute(
                    """
                    SELECT 
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(CASE WHEN event_type = 'click' THEN 1 END) as clicks,
                        COUNT(CASE WHEN event_type = 'view' THEN 1 END) as views,
                        COUNT(CASE WHEN event_type = 'subscribe' THEN 1 END) as conversions,
                        AVG(CASE WHEN event_type = 'read_time' 
                            THEN CAST(json_extract(event_data, '$.duration') AS REAL) END) as avg_read_time
                    FROM engagement_events 
                    WHERE episode_id = ? AND DATE(event_time) = DATE(?)
                """,
                    (episode_id, delivery_time.isoformat()),
                ).fetchone()

                total_recipients = delivery_stats[3] or 0
                successful_deliveries = delivery_stats[1] or 0
                failed_deliveries = delivery_stats[2] or 0
                clicks = engagement_stats[1] or 0
                unique_users = engagement_stats[0] or 0
                conversions = engagement_stats[3] or 0
                avg_read_time = engagement_stats[4] or 0.0

                # 指標計算
                click_through_rate = (
                    (clicks / successful_deliveries) if successful_deliveries > 0 else 0.0
                )
                engagement_rate = (
                    (unique_users / successful_deliveries) if successful_deliveries > 0 else 0.0
                )
                conversion_rate = (
                    (conversions / successful_deliveries) if successful_deliveries > 0 else 0.0
                )

                metrics = PerformanceMetrics(
                    episode_id=episode_id,
                    delivery_time=delivery_time,
                    total_recipients=total_recipients,
                    successful_deliveries=successful_deliveries,
                    failed_deliveries=failed_deliveries,
                    click_through_rate=click_through_rate,
                    engagement_rate=engagement_rate,
                    avg_read_time=avg_read_time,
                    conversion_rate=conversion_rate,
                )

                # 結果をデータベースに保存
                self._save_performance_metrics(metrics)

                return metrics

        except Exception as e:
            self.logger.error(f"パフォーマンス指標計算エラー: {e}")
            raise

    def _save_performance_metrics(self, metrics: PerformanceMetrics):
        """パフォーマンス指標保存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO performance_metrics 
                (episode_id, delivery_time, total_recipients, successful_deliveries, 
                 failed_deliveries, click_through_rate, engagement_rate, 
                 avg_read_time, conversion_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    metrics.episode_id,
                    metrics.delivery_time.isoformat(),
                    metrics.total_recipients,
                    metrics.successful_deliveries,
                    metrics.failed_deliveries,
                    metrics.click_through_rate,
                    metrics.engagement_rate,
                    metrics.avg_read_time,
                    metrics.conversion_rate,
                ),
            )

    def get_episode_performance(self, episode_id: str) -> Optional[PerformanceMetrics]:
        """エピソード別パフォーマンス取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT episode_id, delivery_time, total_recipients, successful_deliveries,
                           failed_deliveries, click_through_rate, engagement_rate,
                           avg_read_time, conversion_rate
                    FROM performance_metrics 
                    WHERE episode_id = ? 
                    ORDER BY calculated_at DESC 
                    LIMIT 1
                """,
                    (episode_id,),
                ).fetchone()

                if row:
                    return PerformanceMetrics(
                        episode_id=row[0],
                        delivery_time=datetime.datetime.fromisoformat(row[1]),
                        total_recipients=row[2],
                        successful_deliveries=row[3],
                        failed_deliveries=row[4],
                        click_through_rate=row[5],
                        engagement_rate=row[6],
                        avg_read_time=row[7],
                        conversion_rate=row[8],
                    )
                return None

        except Exception as e:
            self.logger.error(f"エピソードパフォーマンス取得エラー: {e}")
            return None

    def get_performance_trends(self, days: int = 7) -> List[PerformanceMetrics]:
        """パフォーマンストレンド取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT episode_id, delivery_time, total_recipients, successful_deliveries,
                           failed_deliveries, click_through_rate, engagement_rate,
                           avg_read_time, conversion_rate
                    FROM performance_metrics 
                    WHERE delivery_time >= datetime('now', '-{} days')
                    ORDER BY delivery_time DESC
                """.format(
                        days
                    )
                ).fetchall()

                return [
                    PerformanceMetrics(
                        episode_id=row[0],
                        delivery_time=datetime.datetime.fromisoformat(row[1]),
                        total_recipients=row[2],
                        successful_deliveries=row[3],
                        failed_deliveries=row[4],
                        click_through_rate=row[5],
                        engagement_rate=row[6],
                        avg_read_time=row[7],
                        conversion_rate=row[8],
                    )
                    for row in rows
                ]

        except Exception as e:
            self.logger.error(f"パフォーマンストレンド取得エラー: {e}")
            return []

    def get_system_status(self) -> Dict[str, Any]:
        """システムステータス取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 今日の配信統計
                today_stats = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_deliveries,
                        SUM(recipient_count) as total_recipients,
                        COUNT(CASE WHEN status = 'delivered' THEN 1 END) as successful,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
                    FROM delivery_events 
                    WHERE DATE(delivery_time) = DATE('now')
                """
                ).fetchone()

                # 今日のエンゲージメント統計
                today_engagement = conn.execute(
                    """
                    SELECT 
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(*) as total_events
                    FROM engagement_events 
                    WHERE DATE(event_time) = DATE('now')
                """
                ).fetchone()

                # データベース統計
                db_stats = conn.execute(
                    """
                    SELECT 
                        (SELECT COUNT(*) FROM delivery_events) as delivery_events,
                        (SELECT COUNT(*) FROM engagement_events) as engagement_events,
                        (SELECT COUNT(*) FROM performance_metrics) as performance_records
                """
                ).fetchone()

                return {
                    "today": {
                        "total_deliveries": today_stats[0],
                        "total_recipients": today_stats[1],
                        "successful_deliveries": today_stats[2],
                        "failed_deliveries": today_stats[3],
                        "unique_users": today_engagement[0],
                        "engagement_events": today_engagement[1],
                    },
                    "database": {
                        "delivery_events": db_stats[0],
                        "engagement_events": db_stats[1],
                        "performance_records": db_stats[2],
                    },
                    "status": "active",
                    "last_updated": datetime.datetime.now().isoformat(),
                }

        except Exception as e:
            self.logger.error(f"システムステータス取得エラー: {e}")
            return {"status": "error", "error": str(e)}
