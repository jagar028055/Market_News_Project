# -*- coding: utf-8 -*-

"""
ステップ7: GitHub Pagesへの配信
"""

import logging
from typing import Optional
from datetime import datetime
from pathlib import Path

from .step import IWorkflowStep, StepContext
from ...publisher.independent_github_pages_publisher import IndependentGitHubPagesPublisher
from ...audio.audio_processor import get_audio_duration # 音声再生時間を取得するヘルパーをインポート

class PublishToGitHubStep(IWorkflowStep):
    """
    生成されたポッドキャストエピソードをGitHub Pagesに配信するステップ。
    """

    def __init__(self, publisher: IndependentGitHubPagesPublisher):
        self._publisher = publisher
        self.logger = logging.getLogger(__name__)

    @property
    def step_name(self) -> str:
        return "GitHub Pages配信"

    async def execute(self, context: StepContext) -> Optional[str]:
        """
        GitHub Pagesへの配信を実行し、結果をコンテキストに保存します。

        Args:
            context: ワークフローのコンテキスト。

        Returns:
            エラーメッセージ。成功した場合はNone。
        """
        try:
            processed_audio_path = context.data.get('processed_audio_path')
            if not processed_audio_path:
                return "配信する音声ファイルがありません。"

            audio_file = Path(processed_audio_path)
            if not audio_file.exists():
                return f"音声ファイルが見つかりません: {processed_audio_path}"

            selected_articles = context.data.get('selected_articles', [])

            self.logger.info(f"エピソードをGitHub Pagesに配信しています: {audio_file.name}")

            episode_number = self._get_next_episode_number()
            duration_str = self._get_formatted_duration(processed_audio_path)

            episode_metadata = {
                "title": f"{context.config.podcast_title} - {datetime.now().strftime('%Y年%m月%d日')} (Ep. {episode_number})",
                "description": f"本日の市場動向を{len(selected_articles)}件の記事からAIが解説します。",
                "published_date": datetime.now(),
                "duration": duration_str,
                "keywords": ["market", "news", "finance", "japan", "ai", "investing"],
                "episode_number": episode_number,
            }

            audio_url = self._publisher.publish_episode(
                audio_file=audio_file,
                episode_metadata=episode_metadata
            )

            if not audio_url:
                return "配信URLが取得できませんでした。"

            self.logger.info(f"配信完了 - URL: {audio_url}")

            context.result.audio_url = audio_url
            context.result.rss_url = self._publisher.get_rss_url()
            context.result.file_size_mb = audio_file.stat().st_size / (1024 * 1024)
            context.data['episode_number'] = episode_number

            return None

        except Exception as e:
            self.logger.error(f"配信中にエラーが発生しました: {e}", exc_info=True)
            return f"配信エラー: {e}"

    def _get_next_episode_number(self) -> int:
        """次のエピソード番号を取得します。"""
        try:
            episodes = self._publisher.get_episode_list()
            if episodes:
                valid_episodes = [ep.get("episode_number", 0) for ep in episodes if isinstance(ep.get("episode_number"), int)]
                if valid_episodes:
                    return max(valid_episodes) + 1
            return 1
        except Exception as e:
            self.logger.warning(f"エピソード番号の取得に失敗しました。1から開始します。エラー: {e}", exc_info=True)
            return 1

    def _get_formatted_duration(self, file_path: str) -> str:
        """音声ファイルの再生時間をHH:MM:SS形式で取得します。"""
        try:
            duration_seconds = get_audio_duration(file_path)
            if duration_seconds is None:
                return "00:10:00" # デフォルト値

            hours, remainder = divmod(duration_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
        except Exception as e:
            self.logger.warning(f"音声再生時間の取得に失敗しました。デフォルト値を使用します。エラー: {e}")
            return "00:10:00"
