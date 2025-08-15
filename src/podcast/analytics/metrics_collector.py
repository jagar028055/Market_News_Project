"""
メトリクス収集システム

このモジュールは配信とエンゲージメントのリアルタイム指標収集を行います。
"""

import uuid
import logging
import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from .analytics_engine import (
    AnalyticsEngine, DeliveryEvent, EngagementEvent, 
    DeliveryStatus, MessageType
)


@dataclass
class NotificationMetrics:
    """通知関連メトリクス"""
    notification_id: str
    episode_id: str
    message_type: str
    recipient_count: int
    delivery_time: datetime.datetime
    success_count: int = 0
    failure_count: int = 0
    response_time_ms: float = 0.0


class MetricsCollector:
    """メトリクス収集管理システム"""
    
    def __init__(self, analytics_engine: Optional[AnalyticsEngine] = None):
        self.analytics = analytics_engine or AnalyticsEngine()
        self.logger = logging.getLogger(__name__)
        self._active_notifications: Dict[str, NotificationMetrics] = {}
    
    def start_notification_tracking(
        self, 
        episode_id: str, 
        message_type: str,
        recipient_count: int
    ) -> str:
        """通知トラッキング開始"""
        notification_id = str(uuid.uuid4())
        
        metrics = NotificationMetrics(
            notification_id=notification_id,
            episode_id=episode_id,
            message_type=message_type,
            recipient_count=recipient_count,
            delivery_time=datetime.datetime.now()
        )
        
        self._active_notifications[notification_id] = metrics
        
        self.logger.info(f"通知トラッキング開始: {notification_id} (エピソード: {episode_id})")
        return notification_id
    
    def record_delivery_success(
        self, 
        notification_id: str,
        response_time_ms: float,
        actual_recipient_count: Optional[int] = None
    ):
        """配信成功記録"""
        if notification_id not in self._active_notifications:
            self.logger.warning(f"不明な通知ID: {notification_id}")
            return
        
        metrics = self._active_notifications[notification_id]
        metrics.success_count = actual_recipient_count or metrics.recipient_count
        metrics.response_time_ms = response_time_ms
        
        # 配信イベント記録
        delivery_event = DeliveryEvent(
            event_id=notification_id,
            episode_id=metrics.episode_id,
            delivery_time=metrics.delivery_time,
            message_type=MessageType(metrics.message_type.lower()),
            status=DeliveryStatus.DELIVERED,
            recipient_count=metrics.success_count,
            metadata={
                'response_time_ms': response_time_ms,
                'original_recipient_count': metrics.recipient_count
            }
        )
        
        self.analytics.record_delivery_event(delivery_event)
        self.logger.info(f"配信成功記録: {notification_id}")
    
    def record_delivery_failure(
        self, 
        notification_id: str,
        error_message: str,
        failed_count: Optional[int] = None
    ):
        """配信失敗記録"""
        if notification_id not in self._active_notifications:
            self.logger.warning(f"不明な通知ID: {notification_id}")
            return
        
        metrics = self._active_notifications[notification_id]
        metrics.failure_count = failed_count or metrics.recipient_count
        
        # 配信イベント記録
        delivery_event = DeliveryEvent(
            event_id=notification_id,
            episode_id=metrics.episode_id,
            delivery_time=metrics.delivery_time,
            message_type=MessageType(metrics.message_type.lower()),
            status=DeliveryStatus.FAILED,
            recipient_count=metrics.failure_count,
            metadata={
                'error_message': error_message,
                'original_recipient_count': metrics.recipient_count
            }
        )
        
        self.analytics.record_delivery_event(delivery_event)
        self.logger.error(f"配信失敗記録: {notification_id} - {error_message}")
    
    def record_user_click(
        self, 
        episode_id: str,
        user_id: str,
        click_target: str,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """ユーザークリック記録"""
        event = EngagementEvent(
            event_id=str(uuid.uuid4()),
            episode_id=episode_id,
            user_id=user_id,
            event_type='click',
            event_time=datetime.datetime.now(),
            event_data={
                'click_target': click_target,
                **(additional_data or {})
            }
        )
        
        self.analytics.record_engagement_event(event)
        self.logger.info(f"ユーザークリック記録: {user_id} -> {click_target}")
    
    def record_user_view(
        self, 
        episode_id: str,
        user_id: str,
        view_duration_ms: Optional[int] = None
    ):
        """ユーザービュー記録"""
        event = EngagementEvent(
            event_id=str(uuid.uuid4()),
            episode_id=episode_id,
            user_id=user_id,
            event_type='view',
            event_time=datetime.datetime.now(),
            event_data={
                'duration_ms': view_duration_ms
            } if view_duration_ms else {}
        )
        
        self.analytics.record_engagement_event(event)
        self.logger.info(f"ユーザービュー記録: {user_id} ({view_duration_ms}ms)")
    
    def record_user_share(
        self, 
        episode_id: str,
        user_id: str,
        share_platform: str
    ):
        """ユーザーシェア記録"""
        event = EngagementEvent(
            event_id=str(uuid.uuid4()),
            episode_id=episode_id,
            user_id=user_id,
            event_type='share',
            event_time=datetime.datetime.now(),
            event_data={
                'platform': share_platform
            }
        )
        
        self.analytics.record_engagement_event(event)
        self.logger.info(f"ユーザーシェア記録: {user_id} -> {share_platform}")
    
    def record_subscription(
        self, 
        episode_id: str,
        user_id: str,
        subscription_type: str = 'rss'
    ):
        """購読記録"""
        event = EngagementEvent(
            event_id=str(uuid.uuid4()),
            episode_id=episode_id,
            user_id=user_id,
            event_type='subscribe',
            event_time=datetime.datetime.now(),
            event_data={
                'subscription_type': subscription_type
            }
        )
        
        self.analytics.record_engagement_event(event)
        self.logger.info(f"購読記録: {user_id} ({subscription_type})")
    
    def record_read_time(
        self, 
        episode_id: str,
        user_id: str,
        read_duration_seconds: float
    ):
        """読取時間記録"""
        event = EngagementEvent(
            event_id=str(uuid.uuid4()),
            episode_id=episode_id,
            user_id=user_id,
            event_type='read_time',
            event_time=datetime.datetime.now(),
            event_data={
                'duration': read_duration_seconds
            }
        )
        
        self.analytics.record_engagement_event(event)
        self.logger.info(f"読取時間記録: {user_id} ({read_duration_seconds}秒)")
    
    def finish_notification_tracking(self, notification_id: str):
        """通知トラッキング終了"""
        if notification_id in self._active_notifications:
            metrics = self._active_notifications[notification_id]
            
            # 最終メトリクス計算
            total_processed = metrics.success_count + metrics.failure_count
            success_rate = (metrics.success_count / total_processed) if total_processed > 0 else 0.0
            
            self.logger.info(
                f"通知トラッキング完了: {notification_id} "
                f"(成功率: {success_rate:.1%}, 応答時間: {metrics.response_time_ms}ms)"
            )
            
            # アクティブリストから削除
            del self._active_notifications[notification_id]
    
    def get_notification_metrics(self, notification_id: str) -> Optional[NotificationMetrics]:
        """通知メトリクス取得"""
        return self._active_notifications.get(notification_id)
    
    def get_active_notifications(self) -> List[NotificationMetrics]:
        """アクティブ通知一覧取得"""
        return list(self._active_notifications.values())
    
    def calculate_realtime_stats(self) -> Dict[str, Any]:
        """リアルタイム統計計算"""
        active_count = len(self._active_notifications)
        
        if active_count == 0:
            return {
                'active_notifications': 0,
                'total_recipients': 0,
                'avg_response_time': 0.0
            }
        
        total_recipients = sum(m.recipient_count for m in self._active_notifications.values())
        completed_notifications = [m for m in self._active_notifications.values() 
                                 if m.success_count > 0 or m.failure_count > 0]
        
        avg_response_time = 0.0
        if completed_notifications:
            avg_response_time = sum(m.response_time_ms for m in completed_notifications) / len(completed_notifications)
        
        return {
            'active_notifications': active_count,
            'total_recipients': total_recipients,
            'completed_notifications': len(completed_notifications),
            'avg_response_time': avg_response_time,
            'last_updated': datetime.datetime.now().isoformat()
        }
    
    def cleanup_old_metrics(self, hours_old: int = 24):
        """古いメトリクス削除"""
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=hours_old)
        
        to_remove = []
        for notification_id, metrics in self._active_notifications.items():
            if metrics.delivery_time < cutoff_time:
                to_remove.append(notification_id)
        
        for notification_id in to_remove:
            del self._active_notifications[notification_id]
            self.logger.info(f"期限切れメトリクス削除: {notification_id}")
        
        if to_remove:
            self.logger.info(f"{len(to_remove)}件の古いメトリクスを削除しました")