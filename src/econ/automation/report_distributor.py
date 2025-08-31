"""
Integrated report distribution system for economic indicators.

経済指標レポートの統合配信システム。
生成されたレポートを複数のチャネルに自動配信する。
"""

import logging
import os
import sys
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
import json
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
import base64
import mimetypes

# Add src to path if running from project root
if 'src' not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.econ.config.settings import get_econ_config
from src.econ.automation.notifications import NotificationManager

logger = logging.getLogger(__name__)


@dataclass
class ReportFile:
    """レポートファイル情報"""
    file_path: str
    file_type: str  # html, pdf, png, csv, ics
    title: str
    description: str = ""
    created_at: datetime = None
    file_size: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        
        # ファイルサイズを取得
        try:
            path = Path(self.file_path)
            if path.exists():
                self.file_size = path.stat().st_size
        except Exception:
            pass


@dataclass
class DistributionChannel:
    """配信チャネル設定"""
    channel_id: str
    name: str
    type: str  # email, slack, webhook, ftp, s3, note, social
    enabled: bool = True
    config: Dict[str, Any] = None
    file_types: List[str] = None  # 対応ファイルタイプ
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}
        if self.file_types is None:
            self.file_types = ['html', 'pdf', 'png']


@dataclass
class DistributionResult:
    """配信結果"""
    channel_id: str
    success: bool
    message: str = ""
    url: Optional[str] = None  # 配信先URL
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ReportDistributor:
    """統合レポート配信システム"""
    
    def __init__(self, config):
        """
        初期化
        
        Args:
            config: 経済指標設定
        """
        self.config = config
        self.notification_manager = NotificationManager(config)
        
        # 配信チャネル
        self.channels: Dict[str, DistributionChannel] = {}
        
        # 配信履歴
        self.distribution_history: List[Dict[str, Any]] = []
        
        # デフォルトチャネルを設定
        self._setup_default_channels()
    
    def _setup_default_channels(self):
        """デフォルト配信チャネルを設定"""
        try:
            # メール配信
            if os.getenv('SMTP_HOST') and os.getenv('REPORT_EMAIL_LIST'):
                self.add_channel(
                    channel_id='email_reports',
                    name='Email Distribution',
                    type='email',
                    config={
                        'smtp_host': os.getenv('SMTP_HOST'),
                        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
                        'smtp_user': os.getenv('SMTP_USER'),
                        'smtp_password': os.getenv('SMTP_PASSWORD'),
                        'from_email': os.getenv('SMTP_USER'),
                        'recipient_list': os.getenv('REPORT_EMAIL_LIST', '').split(','),
                        'subject_template': '[Economic Report] {title} - {date}'
                    },
                    file_types=['html', 'pdf']
                )
            
            # Slack配信
            if os.getenv('SLACK_WEBHOOK_URL'):
                self.add_channel(
                    channel_id='slack_reports',
                    name='Slack Distribution',
                    type='slack',
                    config={
                        'webhook_url': os.getenv('SLACK_WEBHOOK_URL'),
                        'channel': os.getenv('SLACK_CHANNEL', '#economic-reports'),
                        'username': 'Economic Bot'
                    },
                    file_types=['html', 'png']
                )
            
            # ファイル公開（Webサーバー）
            if os.getenv('WEB_PUBLISH_DIR'):
                self.add_channel(
                    channel_id='web_publish',
                    name='Web Publishing',
                    type='file_publish',
                    config={
                        'publish_dir': os.getenv('WEB_PUBLISH_DIR'),
                        'base_url': os.getenv('WEB_BASE_URL', 'https://example.com/reports'),
                        'index_file': 'index.html'
                    },
                    file_types=['html', 'pdf', 'png', 'ics']
                )
            
            # S3配信（AWS）
            if os.getenv('AWS_S3_BUCKET'):
                self.add_channel(
                    channel_id='s3_publish',
                    name='S3 Publishing',
                    type='s3',
                    config={
                        'bucket': os.getenv('AWS_S3_BUCKET'),
                        'region': os.getenv('AWS_REGION', 'us-east-1'),
                        'prefix': os.getenv('S3_PREFIX', 'economic-reports/'),
                        'public_read': os.getenv('S3_PUBLIC_READ', 'true').lower() == 'true'
                    },
                    file_types=['html', 'pdf', 'png', 'csv', 'ics']
                )
            
            # Note配信
            if os.getenv('NOTE_API_TOKEN'):
                self.add_channel(
                    channel_id='note_publish',
                    name='Note Publishing',
                    type='note',
                    config={
                        'api_token': os.getenv('NOTE_API_TOKEN'),
                        'user_id': os.getenv('NOTE_USER_ID'),
                        'publish_status': os.getenv('NOTE_PUBLISH_STATUS', 'draft')  # draft, published
                    },
                    file_types=['html']
                )
            
            logger.info(f"Setup {len(self.channels)} distribution channels")
            
        except Exception as e:
            logger.error(f"Failed to setup distribution channels: {e}")
    
    def add_channel(
        self,
        channel_id: str,
        name: str,
        type: str,
        config: Dict[str, Any] = None,
        file_types: List[str] = None,
        enabled: bool = True
    ):
        """配信チャネルを追加"""
        channel = DistributionChannel(
            channel_id=channel_id,
            name=name,
            type=type,
            enabled=enabled,
            config=config or {},
            file_types=file_types or ['html', 'pdf']
        )
        
        self.channels[channel_id] = channel
        logger.info(f"Added distribution channel: {channel_id} ({type})")
    
    async def distribute_report(
        self,
        report_files: List[ReportFile],
        title: str,
        description: str = "",
        channels: Optional[List[str]] = None
    ) -> Dict[str, DistributionResult]:
        """レポートを配信"""
        logger.info(f"Distributing report: {title}")
        
        results = {}
        target_channels = channels or list(self.channels.keys())
        
        for channel_id in target_channels:
            if channel_id not in self.channels:
                logger.warning(f"Channel {channel_id} not found")
                results[channel_id] = DistributionResult(
                    channel_id=channel_id,
                    success=False,
                    message=f"Channel {channel_id} not found"
                )
                continue
            
            channel = self.channels[channel_id]
            
            if not channel.enabled:
                logger.info(f"Channel {channel_id} is disabled, skipping")
                continue
            
            try:
                # チャネルに対応するファイルタイプをフィルタ
                compatible_files = [
                    f for f in report_files
                    if f.file_type in channel.file_types
                ]
                
                if not compatible_files:
                    results[channel_id] = DistributionResult(
                        channel_id=channel_id,
                        success=False,
                        message=f"No compatible file types for channel {channel_id}"
                    )
                    continue
                
                # チャネル別の配信処理
                result = await self._distribute_to_channel(
                    channel, compatible_files, title, description
                )
                results[channel_id] = result
                
                if result.success:
                    logger.info(f"Successfully distributed to {channel_id}")
                else:
                    logger.error(f"Failed to distribute to {channel_id}: {result.message}")
                    
            except Exception as e:
                logger.error(f"Error distributing to {channel_id}: {e}")
                results[channel_id] = DistributionResult(
                    channel_id=channel_id,
                    success=False,
                    message=str(e)
                )
        
        # 配信履歴に記録
        self.distribution_history.append({
            'title': title,
            'timestamp': datetime.utcnow().isoformat(),
            'files': [f.file_path for f in report_files],
            'results': {k: {'success': v.success, 'message': v.message} for k, v in results.items()},
            'successful_channels': [k for k, v in results.items() if v.success]
        })
        
        # 配信結果の通知
        await self._send_distribution_notification(title, results)
        
        return results
    
    async def _distribute_to_channel(
        self,
        channel: DistributionChannel,
        files: List[ReportFile],
        title: str,
        description: str
    ) -> DistributionResult:
        """指定チャネルにレポートを配信"""
        try:
            if channel.type == 'email':
                return await self._distribute_email(channel, files, title, description)
            elif channel.type == 'slack':
                return await self._distribute_slack(channel, files, title, description)
            elif channel.type == 'file_publish':
                return await self._distribute_file_publish(channel, files, title, description)
            elif channel.type == 's3':
                return await self._distribute_s3(channel, files, title, description)
            elif channel.type == 'note':
                return await self._distribute_note(channel, files, title, description)
            elif channel.type == 'webhook':
                return await self._distribute_webhook(channel, files, title, description)
            else:
                return DistributionResult(
                    channel_id=channel.channel_id,
                    success=False,
                    message=f"Unsupported channel type: {channel.type}"
                )
                
        except Exception as e:
            return DistributionResult(
                channel_id=channel.channel_id,
                success=False,
                message=str(e)
            )
    
    async def _distribute_email(
        self,
        channel: DistributionChannel,
        files: List[ReportFile],
        title: str,
        description: str
    ) -> DistributionResult:
        """メール配信"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        
        config = channel.config
        
        # メールメッセージを構築
        msg = MIMEMultipart()
        msg['From'] = config['from_email']
        msg['To'] = ', '.join(config['recipient_list'])
        
        # 件名をテンプレートから生成
        subject = config.get('subject_template', '{title}').format(
            title=title,
            date=date.today().strftime('%Y-%m-%d')
        )
        msg['Subject'] = subject
        
        # 本文を構築
        body = f"""
{description}

This email contains the following economic indicator reports:
{chr(10).join(f'• {f.title} ({f.file_type.upper()}, {f.file_size:,} bytes)' for f in files)}

Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Economic Indicators System
        """.strip()
        
        msg.attach(MIMEText(body, 'plain'))
        
        # ファイルを添付
        for file_info in files:
            try:
                with open(file_info.file_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    
                    filename = Path(file_info.file_path).name
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}'
                    )
                    msg.attach(part)
            except Exception as e:
                logger.warning(f"Failed to attach file {file_info.file_path}: {e}")
        
        # SMTP送信
        with smtplib.SMTP(config['smtp_host'], config['smtp_port']) as server:
            server.starttls()
            if config.get('smtp_user') and config.get('smtp_password'):
                server.login(config['smtp_user'], config['smtp_password'])
            server.send_message(msg)
        
        return DistributionResult(
            channel_id=channel.channel_id,
            success=True,
            message=f"Sent to {len(config['recipient_list'])} recipients"
        )
    
    async def _distribute_slack(
        self,
        channel: DistributionChannel,
        files: List[ReportFile],
        title: str,
        description: str
    ) -> DistributionResult:
        """Slack配信"""
        config = channel.config
        webhook_url = config['webhook_url']
        
        # Slackメッセージを構築
        blocks = []
        
        # ヘッダーブロック
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": title
            }
        })
        
        # 説明ブロック
        if description:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": description
                }
            })
        
        # ファイルリストブロック
        if files:
            file_list = []
            for file_info in files:
                file_list.append(f"• *{file_info.title}* ({file_info.file_type.upper()}, {file_info.file_size:,} bytes)")
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Generated files:\n" + "\n".join(file_list)
                }
            })
        
        # フッター
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Economic Indicators System"
                }
            ]
        })
        
        payload = {
            'username': config.get('username', 'Economic Bot'),
            'channel': config.get('channel'),
            'blocks': blocks
        }
        
        # HTTPリクエスト送信
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status == 200:
                    return DistributionResult(
                        channel_id=channel.channel_id,
                        success=True,
                        message="Posted to Slack"
                    )
                else:
                    error_text = await response.text()
                    return DistributionResult(
                        channel_id=channel.channel_id,
                        success=False,
                        message=f"Slack API error {response.status}: {error_text}"
                    )
    
    async def _distribute_file_publish(
        self,
        channel: DistributionChannel,
        files: List[ReportFile],
        title: str,
        description: str
    ) -> DistributionResult:
        """ファイル公開配信"""
        config = channel.config
        publish_dir = Path(config['publish_dir'])
        base_url = config['base_url']
        
        # 公開ディレクトリを作成
        publish_dir.mkdir(parents=True, exist_ok=True)
        
        # 今日の日付でサブディレクトリを作成
        date_dir = publish_dir / date.today().strftime('%Y%m%d')
        date_dir.mkdir(parents=True, exist_ok=True)
        
        published_files = []
        
        # ファイルをコピー
        for file_info in files:
            src_path = Path(file_info.file_path)
            if not src_path.exists():
                logger.warning(f"Source file not found: {file_info.file_path}")
                continue
            
            # ファイル名を生成
            timestamp = datetime.utcnow().strftime('%H%M')
            filename = f"{timestamp}_{src_path.name}"
            dst_path = date_dir / filename
            
            # ファイルをコピー
            async with aiofiles.open(src_path, 'rb') as src:
                content = await src.read()
                async with aiofiles.open(dst_path, 'wb') as dst:
                    await dst.write(content)
            
            # 公開URLを生成
            relative_path = dst_path.relative_to(publish_dir)
            file_url = f"{base_url}/{relative_path.as_posix()}"
            
            published_files.append({
                'title': file_info.title,
                'url': file_url,
                'type': file_info.file_type
            })
        
        # インデックスファイルを更新
        await self._update_index_file(publish_dir, config, title, description, published_files)
        
        return DistributionResult(
            channel_id=channel.channel_id,
            success=True,
            message=f"Published {len(published_files)} files",
            url=f"{base_url}/index.html"
        )
    
    async def _distribute_s3(
        self,
        channel: DistributionChannel,
        files: List[ReportFile],
        title: str,
        description: str
    ) -> DistributionResult:
        """S3配信"""
        try:
            import boto3
        except ImportError:
            return DistributionResult(
                channel_id=channel.channel_id,
                success=False,
                message="boto3 library not available for S3 distribution"
            )
        
        config = channel.config
        
        # S3クライアントを作成
        s3_client = boto3.client('s3', region_name=config['region'])
        bucket = config['bucket']
        prefix = config.get('prefix', '')
        
        # 今日の日付でプレフィックスを作成
        date_prefix = f"{prefix}{date.today().strftime('%Y/%m/%d')}/"
        
        uploaded_files = []
        
        for file_info in files:
            src_path = Path(file_info.file_path)
            if not src_path.exists():
                continue
            
            # S3キーを生成
            timestamp = datetime.utcnow().strftime('%H%M%S')
            key = f"{date_prefix}{timestamp}_{src_path.name}"
            
            # ファイルをアップロード
            with open(src_path, 'rb') as file_data:
                extra_args = {}
                
                # MIMEタイプを設定
                mime_type, _ = mimetypes.guess_type(src_path.name)
                if mime_type:
                    extra_args['ContentType'] = mime_type
                
                # パブリック読み込み権限
                if config.get('public_read', False):
                    extra_args['ACL'] = 'public-read'
                
                s3_client.upload_fileobj(file_data, bucket, key, ExtraArgs=extra_args)
            
            # S3 URLを生成
            if config.get('public_read', False):
                file_url = f"https://{bucket}.s3.{config['region']}.amazonaws.com/{key}"
            else:
                file_url = f"s3://{bucket}/{key}"
            
            uploaded_files.append({
                'title': file_info.title,
                'url': file_url,
                'key': key
            })
        
        return DistributionResult(
            channel_id=channel.channel_id,
            success=True,
            message=f"Uploaded {len(uploaded_files)} files to S3"
        )
    
    async def _distribute_note(
        self,
        channel: DistributionChannel,
        files: List[ReportFile],
        title: str,
        description: str
    ) -> DistributionResult:
        """Note配信"""
        config = channel.config
        
        # HTMLファイルを探す
        html_file = next((f for f in files if f.file_type == 'html'), None)
        if not html_file:
            return DistributionResult(
                channel_id=channel.channel_id,
                success=False,
                message="No HTML file found for Note publishing"
            )
        
        # HTMLコンテンツを読み込み
        try:
            with open(html_file.file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            return DistributionResult(
                channel_id=channel.channel_id,
                success=False,
                message=f"Failed to read HTML file: {e}"
            )
        
        # Note API用のペイロードを構築
        payload = {
            'title': title,
            'body': html_content,
            'status': config.get('publish_status', 'draft')
        }
        
        headers = {
            'Authorization': f'Bearer {config["api_token"]}',
            'Content-Type': 'application/json'
        }
        
        # Note APIにPOST
        note_api_url = f"https://note.com/api/v1/users/{config['user_id']}/notes"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(note_api_url, json=payload, headers=headers) as response:
                if response.status == 201:
                    result_data = await response.json()
                    note_url = result_data.get('data', {}).get('note_url')
                    
                    return DistributionResult(
                        channel_id=channel.channel_id,
                        success=True,
                        message="Published to Note",
                        url=note_url
                    )
                else:
                    error_text = await response.text()
                    return DistributionResult(
                        channel_id=channel.channel_id,
                        success=False,
                        message=f"Note API error {response.status}: {error_text}"
                    )
    
    async def _distribute_webhook(
        self,
        channel: DistributionChannel,
        files: List[ReportFile],
        title: str,
        description: str
    ) -> DistributionResult:
        """Webhook配信"""
        config = channel.config
        url = config['url']
        method = config.get('method', 'POST').upper()
        headers = config.get('headers', {})
        
        # ペイロードを構築
        payload = {
            'title': title,
            'description': description,
            'files': [
                {
                    'path': f.file_path,
                    'title': f.title,
                    'type': f.file_type,
                    'size': f.file_size,
                    'created_at': f.created_at.isoformat()
                }
                for f in files
            ],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=payload, headers=headers) as response:
                if response.status < 400:
                    return DistributionResult(
                        channel_id=channel.channel_id,
                        success=True,
                        message=f"Webhook called successfully ({response.status})"
                    )
                else:
                    error_text = await response.text()
                    return DistributionResult(
                        channel_id=channel.channel_id,
                        success=False,
                        message=f"Webhook error {response.status}: {error_text}"
                    )
    
    async def _update_index_file(
        self,
        publish_dir: Path,
        config: Dict[str, Any],
        title: str,
        description: str,
        files: List[Dict[str, Any]]
    ):
        """インデックスファイルを更新"""
        index_path = publish_dir / config.get('index_file', 'index.html')
        
        # 既存のインデックスファイルを読み込み
        existing_reports = []
        if index_path.exists():
            try:
                async with aiofiles.open(index_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    # 簡単なパース（実際はより複雑なHTMLパースが必要）
                    # ここでは新しいレポートを先頭に追加
            except Exception as e:
                logger.warning(f"Failed to read existing index: {e}")
        
        # HTMLインデックスファイルを生成
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Economic Reports</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .report {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .files {{ margin: 10px 0; }}
        .file-link {{ display: inline-block; margin: 5px 10px 5px 0; padding: 5px 10px; 
                     background: #007cba; color: white; text-decoration: none; border-radius: 3px; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>Economic Indicator Reports</h1>
    
    <div class="report">
        <h2>{title}</h2>
        <p>{description}</p>
        <div class="files">
            {chr(10).join(f'<a href="{f["url"]}" class="file-link">{f["title"]} ({f["type"].upper()})</a>' for f in files)}
        </div>
        <div class="timestamp">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>
    </div>
    
    <hr>
    <p><em>Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</em></p>
</body>
</html>
        """.strip()
        
        # インデックスファイルに書き込み
        async with aiofiles.open(index_path, 'w', encoding='utf-8') as f:
            await f.write(html_content)
    
    async def _send_distribution_notification(
        self,
        title: str,
        results: Dict[str, DistributionResult]
    ):
        """配信結果の通知"""
        successful = sum(1 for r in results.values() if r.success)
        total = len(results)
        
        if successful == total:
            priority = 'info'
            message = f"Report '{title}' successfully distributed to all {total} channels"
        elif successful > 0:
            priority = 'warning'
            failed_channels = [k for k, r in results.items() if not r.success]
            message = f"Report '{title}' distributed to {successful}/{total} channels. Failed: {', '.join(failed_channels)}"
        else:
            priority = 'error'
            message = f"Report '{title}' failed to distribute to all {total} channels"
        
        await self.notification_manager.send_notification(
            title="Report Distribution Complete",
            content=message,
            priority=priority,
            metadata={
                'report_title': title,
                'successful_channels': successful,
                'total_channels': total,
                'results': {k: {'success': v.success, 'message': v.message} for k, v in results.items()}
            }
        )
    
    # =============================================================================
    # 管理・統計機能
    # =============================================================================
    
    def get_distribution_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """配信履歴を取得"""
        return sorted(
            self.distribution_history,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]
    
    def get_channel_statistics(self, days: int = 30) -> Dict[str, Any]:
        """チャネル統計を取得"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # 期間内の配信をフィルタ
        recent_distributions = [
            d for d in self.distribution_history
            if datetime.fromisoformat(d['timestamp']) > cutoff
        ]
        
        channel_stats = {}
        for channel_id in self.channels.keys():
            success_count = 0
            total_count = 0
            
            for dist in recent_distributions:
                if channel_id in dist['results']:
                    total_count += 1
                    if dist['results'][channel_id]['success']:
                        success_count += 1
            
            channel_stats[channel_id] = {
                'total_distributions': total_count,
                'successful_distributions': success_count,
                'success_rate': (success_count / total_count * 100) if total_count > 0 else 0
            }
        
        return {
            'period_days': days,
            'total_distributions': len(recent_distributions),
            'channel_statistics': channel_stats
        }


# サンプル使用例
async def main():
    """サンプル実行"""
    # 設定を読み込み
    config = get_econ_config()
    
    # 配信システムを作成
    distributor = ReportDistributor(config)
    
    # サンプルレポートファイル
    sample_files = [
        ReportFile(
            file_path="build/reports/daily/20240831.html",
            file_type="html",
            title="Daily Economic Report",
            description="Daily economic indicators summary"
        )
    ]
    
    # サンプル配信を実行
    results = await distributor.distribute_report(
        report_files=sample_files,
        title="Daily Economic Report - 2024-08-31",
        description="Today's economic indicators and analysis"
    )
    
    print(f"Distribution results: {json.dumps({k: {'success': v.success, 'message': v.message} for k, v in results.items()}, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())