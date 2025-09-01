# -*- coding: utf-8 -*-

"""
ステップ2: Google Drive文書の読み取り
"""

import logging
from typing import Optional, List, Dict, Any

from .step import IWorkflowStep, StepContext
from ...standalone.gdrive_document_reader import GoogleDriveDocumentReader

class ReadArticlesStep(IWorkflowStep):
    """
    Google Driveから記事データを読み込むステップ。
    """

    def __init__(self, gdrive_reader: GoogleDriveDocumentReader):
        self._gdrive_reader = gdrive_reader
        self.logger = logging.getLogger(__name__)

    @property
    def step_name(self) -> str:
        return "Google Drive文書読み取り"

    async def execute(self, context: StepContext) -> Optional[str]:
        """
        Google Driveから記事を読み込み、コンテキストに保存します。

        Args:
            context: ワークフローのコンテキスト。

        Returns:
            エラーメッセージ。成功した場合はNone。
        """
        try:
            doc_id = context.config.google_document_id
            self.logger.info(f"Google Driveからドキュメントを読み込んでいます: {doc_id}")

            metadata, articles = self._gdrive_reader.read_and_parse_document(
                doc_id, use_cache=True
            )

            if not articles:
                return "記事データが取得できませんでした。ドキュメントが空か、形式が正しくない可能性があります。"

            self.logger.info(f"{len(articles)}件の記事を読み取りました。")

            articles_dict: List[Dict[str, Any]] = [
                {
                    "title": article.title,
                    "url": article.url,
                    "summary": article.summary,
                    "sentiment_label": article.sentiment_label,
                    "sentiment_score": article.sentiment_score,
                    "source": article.source,
                    "published_date": article.published_jst.isoformat() if article.published_jst else None,
                }
                for article in articles
            ]

            context.data['articles'] = articles_dict
            context.data['document_metadata'] = metadata

            return None

        except Exception as e:
            self.logger.error(f"記事読み取り中にエラーが発生しました: {e}", exc_info=True)
            return f"記事読み取りエラー: {e}"
