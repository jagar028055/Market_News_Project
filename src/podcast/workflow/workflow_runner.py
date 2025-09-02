# -*- coding: utf-8 -*-

"""
ワークフロー実行エンジン
"""

import logging
import asyncio
from datetime import datetime
from typing import List

from .steps import IWorkflowStep, StepContext
from .independent_podcast_workflow import WorkflowConfig, WorkflowResult, WorkflowProgress

class WorkflowRunner:
    """
    ワークフローのステップリストを受け取り、順次実行するクラス。
    """
    def __init__(self, steps: List[IWorkflowStep]):
        if not all(isinstance(s, IWorkflowStep) for s in steps):
            raise TypeError("All items in 'steps' must be instances of IWorkflowStep.")
        self.steps = steps
        self.logger = logging.getLogger(__name__)

    async def run(self, context: StepContext) -> WorkflowResult:
        """
        ワークフロー全体を実行します。

        Args:
            context: ワークフローのコンテキスト。

        Returns:
            実行結果。
        """
        progress = self._initialize_progress()
        result = context.result

        self.logger.info(f"🚀 ワークフロー実行開始 - {len(self.steps)}ステップ")

        start_time = datetime.now()
        result.metadata['start_time'] = start_time.isoformat()

        for step in self.steps:
            progress.current_step = step.step_name
            step_start_time = datetime.now()

            self.logger.info(f"📍 ステップ開始: {step.step_name} ({progress.completed_steps + 1}/{progress.total_steps})")

            try:
                # ステップ実行
                error_message = await step.execute(context)

                if error_message:
                    self.logger.error(f"❌ ステップ失敗: {step.step_name} -> {error_message}")
                    result.errors.append(f"{step.step_name}: {error_message}")
                    result.success = False
                    await self._run_cleanup_on_failure()
                    break

                # 成功時の処理
                processing_time = (datetime.now() - step_start_time).total_seconds()
                result.metadata.setdefault('step_times', {})[step.step_name] = processing_time
                self.logger.info(f"✅ ステップ完了: {step.step_name} ({processing_time:.2f}秒)")
                progress.completed_steps += 1

            except Exception as e:
                self.logger.error(f"❌ ステップ '{step.step_name}' で予期せぬ例外が発生: {e}", exc_info=True)
                result.errors.append(f"予期せぬエラー ({step.step_name}): {e}")
                result.success = False
                await self._run_cleanup_on_failure()
                break
        else:
            # ループが正常に完了した場合
            result.success = True
            self.logger.info("✅ ワークフロー全ステップ正常完了")

        end_time = datetime.now()
        result.metadata['end_time'] = end_time.isoformat()
        result.processing_time = (end_time - start_time).total_seconds()

        return result

    def _initialize_progress(self) -> WorkflowProgress:
        """進捗管理オブジェクトを初期化します。"""
        return WorkflowProgress(
            current_step="初期化前",
            total_steps=len(self.steps),
            completed_steps=0,
            step_start_time=datetime.now(),
            overall_start_time=datetime.now(),
        )

    async def _run_cleanup_on_failure(self):
        """
        ワークフロー失敗時にクリーンアップステップを実行します。
        """
        cleanup_step = next((s for s in self.steps if s.step_name == "クリーンアップ"), None)
        if cleanup_step:
            self.logger.info("ワークフロー失敗のため、クリーンアップステップを実行します...")
            dummy_result = WorkflowResult(success=False, episode_id="cleanup_on_failure")
            dummy_config = WorkflowConfig(google_document_id="", gemini_api_key="", github_repo_url="", github_pages_base_url="")
            dummy_context = StepContext(config=dummy_config, result=dummy_result)
            try:
                await cleanup_step.execute(dummy_context)
                self.logger.info("クリーンアップステップ完了。")
            except Exception as e:
                self.logger.error(f"失敗時のクリーンアップ中にエラーが発生しました: {e}", exc_info=True)
