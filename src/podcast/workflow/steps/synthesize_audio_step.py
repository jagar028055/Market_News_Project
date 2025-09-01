# -*- coding: utf-8 -*-

"""
ステップ5: 音声合成
"""

import logging
from typing import Optional

from .step import IWorkflowStep, StepContext
from ...tts.gemini_tts_engine import GeminiTTSEngine

class SynthesizeAudioStep(IWorkflowStep):
    """
    台本から音声を合成するステップ。
    """

    def __init__(self, tts_engine: GeminiTTSEngine):
        self._tts_engine = tts_engine
        self.logger = logging.getLogger(__name__)

    @property
    def step_name(self) -> str:
        return "音声合成"

    async def execute(self, context: StepContext) -> Optional[str]:
        """
        音声合成を実行し、コンテキストに保存します。

        Args:
            context: ワークフローのコンテキスト。

        Returns:
            エラーメッセージ。成功した場合はNone。
        """
        try:
            script = context.data.get('script')
            if not script:
                return "音声合成するための台本がありません。"

            self.logger.info("台本から音声を合成しています...")

            audio_data = self._tts_engine.synthesize_dialogue(script)

            if not audio_data:
                return "音声データが生成されませんでした。"

            self.logger.info(f"音声合成完了 - {len(audio_data)}バイト")
            context.data['audio_data'] = audio_data

            if context.config.save_intermediates:
                output_dir = context.data.get('output_dir')
                if output_dir:
                    raw_audio_path = output_dir / f"{context.result.episode_id}_raw.mp3"
                    with open(raw_audio_path, "wb") as f:
                        f.write(audio_data)
                    self.logger.info(f"中間ファイルとしてRAW音声を保存しました: {raw_audio_path}")

                    if 'intermediate_files' not in context.result.metadata:
                        context.result.metadata['intermediate_files'] = []
                    context.result.metadata['intermediate_files'].append(str(raw_audio_path))
                else:
                    self.logger.warning("出力ディレクトリがコンテキストに見つからないため、中間ファイルを保存できません。")

            return None

        except Exception as e:
            self.logger.error(f"音声合成中にエラーが発生しました: {e}", exc_info=True)
            return f"音声合成エラー: {e}"
