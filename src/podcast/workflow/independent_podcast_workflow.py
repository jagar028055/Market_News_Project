# -*- coding: utf-8 -*-

"""
独立ポッドキャスト配信ワークフロー
リファクタリング版：各ステップを独立したクラスに分割し、
このクラスはワークフローの「組み立て役」に徹する。
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
import json

# 依存コンポーネント
from ..standalone.gdrive_document_reader import GoogleDriveDocumentReader, DocumentReaderWithRetry
from ..script_generation.professional_dialogue_script_generator import ProfessionalDialogueScriptGenerator
from ..tts.gemini_tts_engine import GeminiTTSEngine
from ..audio.audio_processor import AudioProcessor
from ..publisher.independent_github_pages_publisher import IndependentGitHubPagesPublisher
from ..integration.message_templates import MessageTemplates
from ..integration.distribution_error_handler import DistributionErrorHandler

# 新しいリファクタリングされたコンポーネント
from .workflow_runner import WorkflowRunner
from .steps import (
    IWorkflowStep,
    StepContext,
    InitializeStep,
    ReadArticlesStep,
    AnalyzeArticlesStep,
    GenerateScriptStep,
    SynthesizeAudioStep,
    ProcessAudioStep,
    PublishToGitHubStep,
    SendNotificationStep,
    CleanupStep,
)
from ..analysis import ScriptAnalyzer

# --- データクラス定義 ---

@dataclass
class WorkflowConfig:
    """ワークフローの設定（変更なし）"""
    google_document_id: str
    gemini_api_key: str
    github_repo_url: str
    github_pages_base_url: str
    gemini_model: str = "gemini-2.0-flash-lite-001"
    podcast_title: str = "マーケットニュース15分"
    podcast_description: str = "AIが生成する15分間の毎日マーケットニュース（拡張情報版）"
    podcast_author: str = "Market News Team"
    podcast_email: str = "podcast@example.com"
    max_articles: int = 12
    target_script_length: int = 4200
    audio_bitrate: str = "128k"
    enable_line_notification: bool = True
    max_retries: int = 3
    retry_delay: float = 60.0
    output_dir: str = "output/podcast"
    assets_dir: str = "src/podcast/assets"
    debug_mode: bool = False
    save_intermediates: bool = True

@dataclass
class WorkflowResult:
    """ワークフロー実行結果（変更なし）"""
    success: bool
    episode_id: str
    audio_url: Optional[str] = None
    rss_url: Optional[str] = None
    processing_time: float = 0.0
    articles_processed: int = 0
    file_size_mb: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    script_info: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

@dataclass
class WorkflowProgress:
    """ワークフロー進行状況（変更なし）"""
    current_step: str
    total_steps: int
    completed_steps: int
    step_start_time: datetime
    overall_start_time: datetime
    estimated_remaining_time: Optional[float] = None

    @property
    def progress_percentage(self) -> float:
        return (self.completed_steps / self.total_steps) * 100 if self.total_steps > 0 else 0.0

    @property
    def elapsed_time(self) -> float:
        return (datetime.now() - self.overall_start_time).total_seconds()

@dataclass
class PodcastServiceComponents:
    """ワークフローが必要とするサービスコンポーネントのコンテナ"""
    gdrive_reader: GoogleDriveDocumentReader
    script_generator: ProfessionalDialogueScriptGenerator
    tts_engine: GeminiTTSEngine
    audio_processor: AudioProcessor
    publisher: IndependentGitHubPagesPublisher
    message_templates: MessageTemplates
    error_handler: DistributionErrorHandler

# --- メインワークフロークラス（リファクタリング版） ---

class IndependentPodcastWorkflow:
    """
    独立ポッドキャスト配信ワークフローの組み立て役。
    責務：
    1. 必要なサービスコンポーネントを初期化する。
    2. ワークフローのステップリストを構築する。
    3. WorkflowRunnerにステップリストを渡して実行する。
    """

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.logger.info("IndependentPodcastWorkflow (Refactored) a初期化完了")

    def _initialize_services(self) -> PodcastServiceComponents:
        """必要な全サービスを初期化し、コンテナとして返す。"""
        self.logger.debug("サービスコンポーネントを初期化しています...")

        gdrive_reader = DocumentReaderWithRetry(
            max_retries=self.config.max_retries, retry_delay=self.config.retry_delay
        ) if self.config.max_retries > 1 else GoogleDriveDocumentReader()

        script_generator = ProfessionalDialogueScriptGenerator(
            api_key=self.config.gemini_api_key, model_name=self.config.gemini_model
        )

        tts_engine = GeminiTTSEngine(api_key=self.config.gemini_api_key)

        audio_processor = AudioProcessor(assets_dir=self.config.assets_dir)
        audio_processor.update_settings({"bitrate": self.config.audio_bitrate})

        podcast_info = {
            "title": self.config.podcast_title,
            "description": self.config.podcast_description,
            "author": self.config.podcast_author,
            "email": self.config.podcast_email,
        }
        publisher = IndependentGitHubPagesPublisher(
            github_repo_url=self.config.github_repo_url,
            base_url=self.config.github_pages_base_url,
            podcast_info=podcast_info,
        )

        message_templates = MessageTemplates(base_url=self.config.github_pages_base_url)

        error_handler = DistributionErrorHandler(base_url=self.config.github_pages_base_url)

        self.logger.debug("全サービスコンポーネントの初期化完了。")
        return PodcastServiceComponents(
            gdrive_reader=gdrive_reader,
            script_generator=script_generator,
            tts_engine=tts_engine,
            audio_processor=audio_processor,
            publisher=publisher,
            message_templates=message_templates,
            error_handler=error_handler,
        )

    def _build_steps(self, services: PodcastServiceComponents) -> List[IWorkflowStep]:
        """ワークフローのステップリストを構築して返す。"""
        self.logger.debug("ワークフローステップを構築しています...")
        return [
            InitializeStep(services.gdrive_reader),
            ReadArticlesStep(services.gdrive_reader),
            AnalyzeArticlesStep(),
            GenerateScriptStep(services.script_generator),
            SynthesizeAudioStep(services.tts_engine),
            ProcessAudioStep(services.audio_processor),
            PublishToGitHubStep(services.publisher),
            SendNotificationStep(services.message_templates),
            CleanupStep(),
        ]

    async def execute_workflow(self) -> WorkflowResult:
        """
        ワークフロー全体を組み立てて実行する。
        """
        self.logger.info("🚀 独立ポッドキャストワークフロー実行開始 (リファクタリング版)")

        # 1. サービスの初期化
        services = self._initialize_services()

        # 2. ステップの構築
        steps = self._build_steps(services)

        # 3. 実行エンジンの準備
        runner = WorkflowRunner(steps)

        # 4. コンテキストの準備
        episode_id = f"market_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = WorkflowResult(success=False, episode_id=episode_id)
        context = StepContext(config=self.config, result=result)

        # 5. 実行
        final_result = await runner.run(context)

        # メトリクス記録などの最終処理
        await self._record_metrics(final_result)

        return final_result

    async def execute_script_test_mode(self) -> WorkflowResult:
        """
        部分的なワークフローを実行して台本を生成し、分析します。
        """
        self.logger.info("📄 台本分析ワークフロー実行開始")
        services = self._initialize_services()
        
        # 台本生成に必要なステップのみを構築
        script_steps = [
            InitializeStep(services.gdrive_reader),
            ReadArticlesStep(services.gdrive_reader),
            AnalyzeArticlesStep(),
            GenerateScriptStep(services.script_generator),
        ]
        
        runner = WorkflowRunner(script_steps)
        
        episode_id = f"script_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = WorkflowResult(success=False, episode_id=episode_id)
        context = StepContext(config=self.config, result=result)
        
        # 部分的なワークフローを実行
        partial_result = await runner.run(context)
        
        if not partial_result.success:
            return partial_result

        script = context.data.get('script')
        if not script:
            partial_result.success = False
            partial_result.errors.append("台本が生成されませんでした。")
            return partial_result

        # 生成された台本を分析
        self.logger.info("台本の詳細分析を実行します...")
        analyzer = ScriptAnalyzer()
        analysis_data = analyzer.analyze(script)
        analyzer.display_analysis(analysis_data, script)
        
        partial_result.script_info = analysis_data
        partial_result.message = "台本生成と分析が完了しました。"
        return partial_result

    async def _record_metrics(self, result: WorkflowResult) -> None:
        """メトリクスを記録する。"""
        try:
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            metrics_data = {
                "execution_id": result.episode_id,
                "timestamp": datetime.now().isoformat(),
                "success": result.success,
                "processing_time": result.processing_time,
                "articles_processed": result.articles_processed,
                "file_size_mb": result.file_size_mb,
                "step_times": result.metadata.get("step_times", {}),
                "errors": result.errors,
                "warnings": result.warnings,
                "config": {
                    "max_articles": self.config.max_articles,
                    "target_script_length": self.config.target_script_length,
                    "audio_bitrate": self.config.audio_bitrate,
                },
            }
            metrics_file = output_dir / "workflow_metrics.jsonl"
            with open(metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(metrics_data, ensure_ascii=False) + "\n")
            self.logger.info("📊 メトリクス記録完了")

        except Exception as e:
            self.logger.warning(f"メトリクス記録エラー: {e}")
