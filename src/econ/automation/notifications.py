"""
Notification and alert system for economic indicators.

経済指標システム用の通知・アラートシステム。
Slack、メール、Webhook等への通知機能を提供する。
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
import json
import asyncio
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# Add src to path if running from project root
if 'src' not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.econ.config.settings import get_econ_config

logger = logging.getLogger(__name__)


@dataclass
class NotificationChannel:
    """通知チャネル設定"""
    channel_id: str
    name: str
    type: str  # slack, email, webhook, discord
    enabled: bool = True
    config: Dict[str, Any] = None
    priority_filter: List[str] = None  # info, warning, error, critical


@dataclass
class NotificationMessage:
    """通知メッセージ"""
    title: str
    content: str
    priority: str = "info"  # info, warning, error, critical
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class NotificationManager:
    """通知管理システム"""
    
    def __init__(self, config):
        """
        初期化
        
        Args:
            config: 経済指標設定
        """
        self.config = config
        self.channels: Dict[str, NotificationChannel] = {}
        self.message_history: List[NotificationMessage] = []
        
        # デフォルトチャネルを設定
        self._setup_default_channels()
    
    def _setup_default_channels(self):
        """デフォルト通知チャネルを設定"""
        try:
            # Slackチャネル
            if os.getenv('SLACK_WEBHOOK_URL'):
                self.add_channel(
                    channel_id='slack_main',
                    name='Slack Main Channel',
                    type='slack',
                    config={
                        'webhook_url': os.getenv('SLACK_WEBHOOK_URL'),
                        'username': 'Economic Bot',
                        'icon_emoji': ':chart_with_upwards_trend:'
                    },
                    priority_filter=['warning', 'error', 'critical']
                )
            
            # メール通知
            if os.getenv('SMTP_HOST') and os.getenv('NOTIFICATION_EMAIL'):
                self.add_channel(
                    channel_id='email_alerts',
                    name='Email Alerts',
                    type='email',
                    config={
                        'smtp_host': os.getenv('SMTP_HOST'),
                        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
                        'smtp_user': os.getenv('SMTP_USER'),
                        'smtp_password': os.getenv('SMTP_PASSWORD'),
                        'from_email': os.getenv('SMTP_USER'),
                        'to_email': os.getenv('NOTIFICATION_EMAIL')
                    },
                    priority_filter=['error', 'critical']
                )
            
            # Webhook通知（汎用）
            if os.getenv('WEBHOOK_URL'):
                self.add_channel(
                    channel_id='webhook_general',
                    name='General Webhook',
                    type='webhook',
                    config={
                        'url': os.getenv('WEBHOOK_URL'),
                        'method': 'POST',
                        'headers': {
                            'Content-Type': 'application/json'
                        }
                    }
                )
            
            logger.info(f"Setup {len(self.channels)} notification channels")
            
        except Exception as e:
            logger.error(f"Failed to setup notification channels: {e}")
    
    def add_channel(
        self,
        channel_id: str,
        name: str,
        type: str,
        config: Dict[str, Any] = None,
        priority_filter: List[str] = None,
        enabled: bool = True
    ):
        """通知チャネルを追加"""
        channel = NotificationChannel(
            channel_id=channel_id,
            name=name,
            type=type,
            enabled=enabled,
            config=config or {},
            priority_filter=priority_filter or ['info', 'warning', 'error', 'critical']
        )
        
        self.channels[channel_id] = channel
        logger.info(f"Added notification channel: {channel_id} ({type})")
    
    def remove_channel(self, channel_id: str):
        """通知チャネルを削除"""
        if channel_id in self.channels:
            del self.channels[channel_id]
            logger.info(f"Removed notification channel: {channel_id}")
    
    def enable_channel(self, channel_id: str, enabled: bool = True):
        """チャネルを有効/無効化"""
        if channel_id in self.channels:
            self.channels[channel_id].enabled = enabled
            logger.info(f"Channel {channel_id} {'enabled' if enabled else 'disabled'}")
    
    async def send_notification(
        self,
        title: str,
        content: str,
        priority: str = "info",
        channels: Optional[List[str]] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, bool]:
        """通知を送信"""
        message = NotificationMessage(
            title=title,
            content=content,
            priority=priority,
            metadata=metadata or {}
        )
        
        # メッセージ履歴に追加
        self.message_history.append(message)
        
        # 送信結果を記録
        results = {}
        
        # 対象チャネルを決定
        target_channels = channels or list(self.channels.keys())
        
        for channel_id in target_channels:
            if channel_id not in self.channels:
                logger.warning(f"Channel {channel_id} not found")
                results[channel_id] = False
                continue
            
            channel = self.channels[channel_id]
            
            # チャネルが無効または優先度フィルターに合わない場合はスキップ
            if not channel.enabled or priority not in channel.priority_filter:
                continue
            
            try:
                success = await self._send_to_channel(message, channel)
                results[channel_id] = success
                
                if success:
                    logger.info(f"Notification sent to {channel_id}: {title}")
                else:
                    logger.error(f"Failed to send notification to {channel_id}")
                    
            except Exception as e:
                logger.error(f"Error sending notification to {channel_id}: {e}")
                results[channel_id] = False
        
        return results
    
    async def _send_to_channel(self, message: NotificationMessage, channel: NotificationChannel) -> bool:
        """指定チャネルに通知を送信"""
        try:
            if channel.type == 'slack':
                return await self._send_slack(message, channel)
            elif channel.type == 'email':
                return await self._send_email(message, channel)
            elif channel.type == 'webhook':
                return await self._send_webhook(message, channel)
            elif channel.type == 'discord':
                return await self._send_discord(message, channel)
            else:
                logger.error(f"Unsupported channel type: {channel.type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send to {channel.channel_id}: {e}")
            return False
    
    async def _send_slack(self, message: NotificationMessage, channel: NotificationChannel) -> bool:
        """Slackに通知を送信"""
        webhook_url = channel.config.get('webhook_url')
        if not webhook_url:
            logger.error("Slack webhook URL not configured")
            return False
        
        # 優先度に応じた色を設定
        color_map = {
            'info': 'good',
            'warning': 'warning', 
            'error': 'danger',
            'critical': 'danger'
        }
        
        # Slack用のペイロードを構築
        payload = {
            'username': channel.config.get('username', 'Economic Bot'),
            'icon_emoji': channel.config.get('icon_emoji', ':chart_with_upwards_trend:'),
            'attachments': [{
                'color': color_map.get(message.priority, 'good'),
                'title': message.title,
                'text': message.content,
                'footer': 'Economic Indicators System',
                'ts': int(message.timestamp.timestamp())
            }]
        }
        
        # メタデータがあればフィールドとして追加
        if message.metadata:
            fields = []
            for key, value in message.metadata.items():
                fields.append({
                    'title': key.replace('_', ' ').title(),
                    'value': str(value),
                    'short': True
                })
            payload['attachments'][0]['fields'] = fields
        
        # HTTPリクエストを送信
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                return response.status == 200
    
    async def _send_email(self, message: NotificationMessage, channel: NotificationChannel) -> bool:
        """メール通知を送信"""
        config = channel.config
        
        try:
            # メールメッセージを構築
            msg = MIMEMultipart()
            msg['From'] = config['from_email']
            msg['To'] = config['to_email']
            msg['Subject'] = f"[{message.priority.upper()}] {message.title}"
            
            # 本文を構築
            body = f"""
{message.content}

---
Priority: {message.priority.upper()}
Timestamp: {message.timestamp.isoformat()}

Economic Indicators System
            """.strip()
            
            # メタデータがあれば追加
            if message.metadata:
                body += "\n\nMetadata:\n"
                for key, value in message.metadata.items():
                    body += f"- {key}: {value}\n"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # SMTP接続でメールを送信
            with smtplib.SMTP(config['smtp_host'], config['smtp_port']) as server:
                server.starttls()
                if config.get('smtp_user') and config.get('smtp_password'):
                    server.login(config['smtp_user'], config['smtp_password'])
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def _send_webhook(self, message: NotificationMessage, channel: NotificationChannel) -> bool:
        """Webhook通知を送信"""
        config = channel.config
        url = config.get('url')
        method = config.get('method', 'POST').upper()
        headers = config.get('headers', {})
        
        if not url:
            logger.error("Webhook URL not configured")
            return False
        
        # ペイロードを構築
        payload = {
            'title': message.title,
            'content': message.content,
            'priority': message.priority,
            'timestamp': message.timestamp.isoformat(),
            'metadata': message.metadata
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == 'POST':
                    async with session.post(url, json=payload, headers=headers) as response:
                        return response.status < 400
                elif method == 'PUT':
                    async with session.put(url, json=payload, headers=headers) as response:
                        return response.status < 400
                else:
                    logger.error(f"Unsupported HTTP method: {method}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            return False
    
    async def _send_discord(self, message: NotificationMessage, channel: NotificationChannel) -> bool:
        """Discord通知を送信"""
        webhook_url = channel.config.get('webhook_url')
        if not webhook_url:
            logger.error("Discord webhook URL not configured")
            return False
        
        # Discord用のペイロードを構築
        payload = {
            'username': channel.config.get('username', 'Economic Bot'),
            'avatar_url': channel.config.get('avatar_url'),
            'embeds': [{
                'title': message.title,
                'description': message.content,
                'color': {
                    'info': 0x00ff00,      # green
                    'warning': 0xffff00,   # yellow  
                    'error': 0xff0000,     # red
                    'critical': 0x800000   # dark red
                }.get(message.priority, 0x00ff00),
                'timestamp': message.timestamp.isoformat(),
                'footer': {
                    'text': 'Economic Indicators System'
                }
            }]
        }
        
        # メタデータがあればフィールドとして追加
        if message.metadata:
            fields = []
            for key, value in message.metadata.items():
                fields.append({
                    'name': key.replace('_', ' ').title(),
                    'value': str(value),
                    'inline': True
                })
            payload['embeds'][0]['fields'] = fields
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                return response.status == 204
    
    # =============================================================================
    # 特定用途の通知メソッド
    # =============================================================================
    
    async def send_job_notification(
        self,
        job_id: str,
        status: str,
        message: str = "",
        execution: Any = None
    ):
        """ジョブ実行結果の通知"""
        priority_map = {
            'success': 'info',
            'failed': 'error',
            'timeout': 'warning'
        }
        
        priority = priority_map.get(status, 'info')
        
        title = f"Job {status.title()}: {job_id}"
        content = message
        
        metadata = {
            'job_id': job_id,
            'status': status
        }
        
        if execution:
            metadata.update({
                'duration': f"{execution.duration:.1f}s" if execution.duration else "N/A",
                'retry_count': execution.retry_count,
                'start_time': execution.start_time.isoformat() if execution.start_time else None
            })
        
        await self.send_notification(
            title=title,
            content=content,
            priority=priority,
            metadata=metadata
        )
    
    async def send_quality_alert(self, quality_report: Dict[str, Any]):
        """データ品質アラートの通知"""
        issues = quality_report.get('issues', [])
        if not issues:
            return
        
        title = f"Data Quality Alert: {len(issues)} Issue(s) Detected"
        
        content_lines = ["Data quality issues detected:"]
        for issue in issues[:5]:  # 最大5件まで表示
            content_lines.append(f"• {issue.get('type', 'Unknown')}: {issue.get('description', 'No description')}")
        
        if len(issues) > 5:
            content_lines.append(f"... and {len(issues) - 5} more issues")
        
        content = "\n".join(content_lines)
        
        metadata = {
            'total_issues': len(issues),
            'severity_breakdown': quality_report.get('severity_breakdown', {}),
            'check_timestamp': quality_report.get('timestamp', datetime.utcnow().isoformat())
        }
        
        await self.send_notification(
            title=title,
            content=content,
            priority='warning',
            metadata=metadata
        )
    
    async def send_indicator_alert(
        self,
        indicator_name: str,
        actual_value: float,
        forecast_value: Optional[float] = None,
        surprise: Optional[float] = None,
        significance: str = "medium"
    ):
        """重要経済指標の発表アラート"""
        title = f"Economic Indicator Alert: {indicator_name}"
        
        content_lines = [f"New data available for {indicator_name}"]
        content_lines.append(f"Actual: {actual_value}")
        
        if forecast_value is not None:
            content_lines.append(f"Forecast: {forecast_value}")
            
        if surprise is not None:
            surprise_text = f"+{surprise:.2f}" if surprise >= 0 else f"{surprise:.2f}"
            content_lines.append(f"Surprise: {surprise_text}")
        
        content = "\n".join(content_lines)
        
        priority_map = {
            'low': 'info',
            'medium': 'info',
            'high': 'warning',
            'critical': 'error'
        }
        
        priority = priority_map.get(significance, 'info')
        
        metadata = {
            'indicator': indicator_name,
            'actual': actual_value,
            'forecast': forecast_value,
            'surprise': surprise,
            'significance': significance
        }
        
        await self.send_notification(
            title=title,
            content=content,
            priority=priority,
            metadata=metadata
        )
    
    async def send_system_status(self, status: Dict[str, Any]):
        """システム状態の定期通知"""
        title = "Economic System Status Report"
        
        content_lines = []
        content_lines.append(f"Scheduler Running: {'✅' if status.get('scheduler_running') else '❌'}")
        content_lines.append(f"Active Jobs: {status.get('active_jobs', 0)}")
        content_lines.append(f"Total Jobs: {status.get('total_jobs', 0)}")
        
        if status.get('last_executions'):
            content_lines.append("\nRecent Executions:")
            for exec in status['last_executions'][:3]:
                status_icon = {'success': '✅', 'failed': '❌', 'running': '🔄'}.get(exec.get('status'), '❓')
                content_lines.append(f"• {exec.get('job_id')}: {status_icon}")
        
        content = "\n".join(content_lines)
        
        await self.send_notification(
            title=title,
            content=content,
            priority='info',
            metadata=status
        )
    
    # =============================================================================
    # 管理機能
    # =============================================================================
    
    def get_message_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """通知履歴を取得"""
        # 最新順でソート
        messages = sorted(self.message_history, key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                'title': msg.title,
                'content': msg.content,
                'priority': msg.priority,
                'timestamp': msg.timestamp.isoformat(),
                'metadata': msg.metadata
            }
            for msg in messages[:limit]
        ]
    
    def cleanup_history(self, hours: int = 72):
        """古い通知履歴をクリーンアップ"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        initial_count = len(self.message_history)
        
        self.message_history = [
            msg for msg in self.message_history
            if msg.timestamp > cutoff
        ]
        
        cleaned = initial_count - len(self.message_history)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old notification messages")
    
    def get_channel_status(self) -> Dict[str, Any]:
        """チャネル状態を取得"""
        return {
            'total_channels': len(self.channels),
            'enabled_channels': sum(1 for c in self.channels.values() if c.enabled),
            'channels': {
                channel_id: {
                    'name': channel.name,
                    'type': channel.type,
                    'enabled': channel.enabled,
                    'priority_filter': channel.priority_filter
                }
                for channel_id, channel in self.channels.items()
            }
        }


# サンプル使用例
async def main():
    """サンプル実行"""
    # 設定を読み込み
    config = get_econ_config()
    
    # 通知マネージャーを作成
    notification_manager = NotificationManager(config)
    
    # サンプル通知を送信
    results = await notification_manager.send_notification(
        title="Test Notification",
        content="This is a test notification from the economic system.",
        priority="info",
        metadata={
            'test_key': 'test_value',
            'timestamp': datetime.utcnow().isoformat()
        }
    )
    
    print(f"Notification results: {results}")
    
    # チャネル状態を確認
    status = notification_manager.get_channel_status()
    print(f"Channel status: {json.dumps(status, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())