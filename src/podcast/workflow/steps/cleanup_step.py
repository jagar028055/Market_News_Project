# -*- coding: utf-8 -*-

"""
ステップ9: クリーンアップ
"""

import logging
from typing import Optional
from pathlib import Path

from .step import IWorkflowStep, StepContext

class CleanupStep(IWorkflowStep):
    """
    ワークフロー実行中に生成された一時ファイルをクリーンアップするステップ。
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @property
    def step_name(self) -> str:
        return "クリーンアップ"

    async def execute(self, context: StepContext) -> Optional[str]:
        """
        中間ファイルのクリーンアップ処理を実行します。

        Args:
            context: ワークフローのコンテキスト。

        Returns:
            エラーメッセージ。成功した場合はNone。
        """
        try:
            intermediate_files = context.result.metadata.get('intermediate_files', [])
            if not intermediate_files:
                self.logger.info("クリーンアップ対象の中間ファイルはありません。")
                return None

            self.logger.info(f"{len(intermediate_files)}個の中間ファイルをクリーンアップします...")

            deleted_count = 0
            for file_str in intermediate_files:
                try:
                    temp_file = Path(file_str)
                    if temp_file.exists():
                        temp_file.unlink()
                        deleted_count += 1
                        self.logger.debug(f"削除しました: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"一時ファイルの削除に失敗しました: {file_str} - {e}")

            self.logger.info(f"クリーンアップ完了 - {deleted_count}個のファイルを削除しました。")

            # 将来的に、ここで他のサービスのクリーンアップ処理を呼び出すことも可能
            #例: context.services.gdrive_reader.cleanup_cache()

            return None

        except Exception as e:
            # クリーンアップエラーはワークフローを停止させない
            self.logger.warning(f"クリーンアップステップでエラーが発生しました: {e}", exc_info=True)
            context.result.warnings.append(f"クリーンアップエラー: {e}")
            return None
