# -*- coding: utf-8 -*-

"""
ステップ4: 台本生成
"""

import logging
from typing import Optional

from .step import IWorkflowStep, StepContext
from ...script_generation.professional_dialogue_script_generator import ProfessionalDialogueScriptGenerator

class GenerateScriptStep(IWorkflowStep):
    """
    選択された記事に基づいて単一ホスト形式の台本を生成するステップ。
    """

    def __init__(self, script_generator: ProfessionalDialogueScriptGenerator):
        self._script_generator = script_generator
        self.logger = logging.getLogger(__name__)

    @property
    def step_name(self) -> str:
        return "台本生成"

    async def execute(self, context: StepContext) -> Optional[str]:
        """
        台本生成を実行し、コンテキストに保存します。

        Args:
            context: ワークフローのコンテキスト。

        Returns:
            エラーメッセージ。成功した場合はNone。
        """
        try:
            selected_articles = context.data.get('selected_articles')
            if not selected_articles:
                return "台本を生成するための記事がありません。"

            self.logger.info(f"{len(selected_articles)}件の記事から台本を生成しています...")

            # ProfessionalDialogueScriptGeneratorの結果を取得
            result = self._script_generator.generate_professional_script(
                selected_articles, 
                target_duration=context.config.target_script_length / 300
            )
            
            script = result.get('script', '')
            
            # 簡易的な品質チェック
            if not script or len(script) < 500: # 閾値を少し下げる
                return f"生成された台本が短すぎるか、空です。文字数: {len(script)}"

            self.logger.info(f"台本生成完了 - {len(script)}文字")
            context.data['script'] = script
            context.data['script_metadata'] = result

            if context.config.save_intermediates:
                output_dir = context.data.get('output_dir')
                if output_dir:
                    script_path = output_dir / f"{context.result.episode_id}_script.txt"
                    with open(script_path, "w", encoding="utf-8") as f:
                        f.write(script)
                    self.logger.info(f"中間ファイルとして台本を保存しました: {script_path}")

                    # 生成したファイルパスを結果に記録
                    if 'intermediate_files' not in context.result.metadata:
                        context.result.metadata['intermediate_files'] = []
                    context.result.metadata['intermediate_files'].append(str(script_path))
                else:
                    self.logger.warning("出力ディレクトリがコンテキストに見つからないため、中間ファイルを保存できません。")


            return None

        except Exception as e:
            self.logger.error(f"台本生成中にエラーが発生しました: {e}", exc_info=True)
            return f"台本生成エラー: {e}"
