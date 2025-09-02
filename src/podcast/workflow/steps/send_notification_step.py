# -*- coding: utf-8 -*-

"""
ステップ8: 通知送信
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from .step import IWorkflowStep, StepContext
from ...integration.message_templates import MessageTemplates
from ...audio.audio_processor import get_audio_duration

class SendNotificationStep(IWorkflowStep):
    """
    新しいエピソードに関する通知を生成するステップ。
    """

    def __init__(self, message_templates: MessageTemplates):
        self._message_templates = message_templates
        self.logger = logging.getLogger(__name__)

    @property
    def step_name(self) -> str:
        return "通知送信"

    async def execute(self, context: StepContext) -> Optional[str]:
        """
        通知メッセージを生成し、ログに出力します。

        Args:
            context: ワークフローのコンテキスト。

        Returns:
            エラーメッセージ。成功した場合はNone。
        """
        try:
            if not context.config.enable_line_notification:
                self.logger.info("LINE通知は無効化されているため、スキップします。")
                return None

            self.logger.info("通知メッセージを生成しています...")

            episode_data = {
                "title": f"{context.config.podcast_title} - {datetime.now().strftime('%Y年%m月%d日')}",
                "duration": self._get_formatted_duration(context),
                "date": datetime.now().strftime("%Y年%m月%d日"),
                "summary": self._create_articles_summary(context.data.get('selected_articles', [])),
                "filename": Path(context.result.audio_url).name if context.result.audio_url else "",
                "file_size_mb": context.result.file_size_mb,
                "episode_number": context.data.get('episode_number', 'N/A'),
                "rss_url": context.result.rss_url,
            }

            notification_message = self._message_templates.create_podcast_notification(episode_data)

            self.logger.info("📢 通知メッセージ生成完了。")
            self.logger.info("実際のLINEブロードキャストAPI呼び出しは、このステップの責務外です。")
            if context.config.debug_mode:
                self.logger.debug(f"--- 通知内容プレビュー ---\n{notification_message}\n--------------------")

            return None

        except Exception as e:
            # 通知エラーはワークフローを停止させない
            self.logger.warning(f"通知送信ステップでエラーが発生しました: {e}", exc_info=True)
            context.result.warnings.append(f"通知送信エラー: {e}")
            return None

    def _create_articles_summary(self, articles: List[Dict[str, Any]]) -> str:
        """通知用の記事要約を作成します。"""
        if not articles:
            return "本日の重要な市場動向をお届けします。"

        summaries = [f"・{a.get('title', '').strip()}" for a in articles[:3]]
        return "\n".join(summaries)

    def _get_formatted_duration(self, context: StepContext) -> str:
        """フォーマットされた再生時間を取得します。"""
        processed_audio_path = context.data.get('processed_audio_path')
        if processed_audio_path:
            duration_sec = get_audio_duration(processed_audio_path)
            if duration_sec is not None:
                minutes = round(duration_sec / 60)
                return f"約{minutes}分"

        # フォールバック
        return f"約{int(context.config.target_script_length / 400)}分"
