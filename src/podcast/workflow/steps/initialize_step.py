# -*- coding: utf-8 -*-

"""
ステップ1: 初期化
- 必要なディレクトリを作成
- Google Driveへの接続を確認
"""

import logging
from typing import Optional

from .step import IWorkflowStep, StepContext
from ...standalone.gdrive_document_reader import GoogleDriveDocumentReader

class InitializeStep(IWorkflowStep):
    """
    初期化ステップ。
    """

    def __init__(self, gdrive_reader: GoogleDriveDocumentReader):
        self._gdrive_reader = gdrive_reader
        self.logger = logging.getLogger(__name__)

    @property
    def step_name(self) -> str:
        return "初期化"

    async def execute(self, context: StepContext) -> Optional[str]:
        """
        初期化処理を実行します。

        Args:
            context: ワークフローのコンテキスト。

        Returns:
            エラーメッセージ。成功した場合はNone。
        """
        try:
            self.logger.info("必要なディレクトリを作成しています...")
            output_path = context.config.output_dir
            output_path.mkdir(parents=True, exist_ok=True)
            context.data['output_dir'] = output_path
            self.logger.info(f"出力ディレクトリ: {output_path}")

            self.logger.info("Google Driveへの接続を確認しています...")
            is_accessible = self._gdrive_reader.validate_document_access(
                context.config.google_document_id
            )
            if not is_accessible:
                return "Google Driveドキュメントにアクセスできません。権限またはドキュメントIDを確認してください。"

            self.logger.info("Google Drive接続OK。")
            return None

        except Exception as e:
            self.logger.error(f"初期化中に予期せぬエラーが発生しました: {e}", exc_info=True)
            return f"初期化エラー: {e}"
