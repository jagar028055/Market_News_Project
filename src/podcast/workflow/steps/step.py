# -*- coding: utf-8 -*-

"""
ワークフローのステップの基本インターフェースを定義します。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

from ..independent_podcast_workflow import WorkflowConfig, WorkflowResult

class StepContext:
    """
    ワークフローのステップ間で共有されるコンテキスト。
    """
    def __init__(self, config: WorkflowConfig, result: WorkflowResult):
        self.config = config
        self.result = result
        self.data: Dict[str, Any] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

class IWorkflowStep(ABC):
    """
    ワークフローの単一ステップを表すインターフェース。
    """

    @property
    @abstractmethod
    def step_name(self) -> str:
        """ステップの名称"""
        pass

    @abstractmethod
    async def execute(self, context: StepContext) -> Optional[str]:
        """
        ステップを実行します。

        Args:
            context: ワークフローのコンテキスト。

        Returns:
            エラーメッセージ。成功した場合はNone。
        """
        pass
