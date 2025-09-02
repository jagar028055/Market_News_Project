# -*- coding: utf-8 -*-

"""
ステップ6: 音声処理
"""

import logging
from typing import Optional
from datetime import datetime

from .step import IWorkflowStep, StepContext
from ...audio.audio_processor import AudioProcessor

class ProcessAudioStep(IWorkflowStep):
    """
    RAW音声を処理し、BGMやジングルを追加して最終的なポッドキャストファイルを生成するステップ。
    """

    def __init__(self, audio_processor: AudioProcessor):
        self._audio_processor = audio_processor
        self.logger = logging.getLogger(__name__)

    @property
    def step_name(self) -> str:
        return "音声処理"

    async def execute(self, context: StepContext) -> Optional[str]:
        """
        音声処理を実行し、最終的な音声ファイルのパスをコンテキストに保存します。

        Args:
            context: ワークフローのコンテキスト。

        Returns:
            エラーメッセージ。成功した場合はNone。
        """
        try:
            audio_data = context.data.get('audio_data')
            if not audio_data:
                return "処理する音声データがありません。"

            selected_articles = context.data.get('selected_articles', [])
            episode_id = context.result.episode_id

            self.logger.info("RAW音声を処理しています（BGM、正規化など）...")

            metadata = {
                "title": f"{context.config.podcast_title} - {datetime.now().strftime('%Y年%m月%d日')}",
                "artist": context.config.podcast_author,
                "album": context.config.podcast_title,
                "date": datetime.now().strftime("%Y"),
                "genre": "News",
                "comment": f"本日のニュースダイジェスト。記事数: {len(selected_articles)}件。",
            }

            processed_path = self._audio_processor.process_audio(
                audio_data=audio_data,
                episode_id=episode_id,
                metadata=metadata
            )

            if not processed_path:
                return "音声処理に失敗しました。FFmpegがインストールされているか確認してください。"

            self.logger.info(f"音声処理完了 - 出力: {processed_path}")
            context.data['processed_audio_path'] = processed_path

            return None

        except Exception as e:
            self.logger.error(f"音声処理中にエラーが発生しました: {e}", exc_info=True)
            return f"音声処理エラー: {e}"
