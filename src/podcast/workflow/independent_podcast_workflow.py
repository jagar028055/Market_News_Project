# -*- coding: utf-8 -*-

"""
独立ポッドキャスト配信ワークフロー
6つのコンポーネントを統合した包括的なオーケストレータークラス
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
import json

# 6つのコンポーネントをインポート
from ..standalone.gdrive_document_reader import GoogleDriveDocumentReader, DocumentReaderWithRetry
from ..script_generation.dialogue_script_generator import DialogueScriptGenerator
from ..tts.gemini_tts_engine import GeminiTTSEngine
from ..audio.audio_processor import AudioProcessor
from ..publisher.independent_github_pages_publisher import IndependentGitHubPagesPublisher
from ..integration.message_templates import MessageTemplates
from ..integration.distribution_error_handler import (
    DistributionErrorHandler,
    ErrorType,
    ErrorSeverity,
)


@dataclass
class WorkflowConfig:
    """ワークフローの設定"""

    # Google Drive設定
    google_document_id: str

    # Gemini API設定
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash-lite-001"

    # GitHub Pages設定
    github_repo_url: str
    github_pages_base_url: str

    # ポッドキャスト設定
    podcast_title: str = "マーケットニュース10分"
    podcast_description: str = "AIが生成する毎日のマーケットニュース"
    podcast_author: str = "Market News Team"
    podcast_email: str = "podcast@example.com"

    # 処理設定
    max_articles: int = 5
    target_script_length: int = 2700
    audio_bitrate: str = "128k"
    enable_line_notification: bool = True

    # リトライ設定
    max_retries: int = 3
    retry_delay: float = 60.0

    # 出力設定
    output_dir: str = "output/podcast"
    assets_dir: str = "src/podcast/assets"

    # デバッグ設定
    debug_mode: bool = False
    save_intermediates: bool = True


@dataclass
class WorkflowResult:
    """ワークフロー実行結果"""

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


@dataclass
class WorkflowProgress:
    """ワークフロー進行状況"""

    current_step: str
    total_steps: int
    completed_steps: int
    step_start_time: datetime
    overall_start_time: datetime
    estimated_remaining_time: Optional[float] = None

    @property
    def progress_percentage(self) -> float:
        """進行率（%）"""
        return (self.completed_steps / self.total_steps) * 100 if self.total_steps > 0 else 0.0

    @property
    def elapsed_time(self) -> float:
        """経過時間（秒）"""
        return (datetime.now() - self.overall_start_time).total_seconds()


class IndependentPodcastWorkflow:
    """
    独立ポッドキャスト配信ワークフロー

    6つのコンポーネントを統合したオーケストレータークラス:
    1. GoogleDriveDocumentReader - 記事データ読み取り
    2. DialogueScriptGenerator - 台本生成
    3. GeminiTTSEngine - 音声合成
    4. AudioProcessor - 音声処理
    5. IndependentGitHubPagesPublisher - 配信
    6. MessageTemplates + DistributionErrorHandler - 通知・エラー処理

    Features:
    - 包括的なエラーハンドリング
    - 進行状況管理
    - 並列処理最適化
    - 自動リトライ機能
    - 品質管理
    - 詳細なログとメトリクス
    """

    WORKFLOW_STEPS = [
        "初期化",
        "Google Drive文書読み取り",
        "記事データ解析",
        "台本生成",
        "音声合成",
        "音声処理",
        "GitHub Pages配信",
        "通知送信",
        "クリーンアップ",
    ]

    def __init__(self, config: WorkflowConfig):
        """
        初期化

        Args:
            config: ワークフロー設定
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 進行状況管理
        self.progress = WorkflowProgress(
            current_step="",
            total_steps=len(self.WORKFLOW_STEPS),
            completed_steps=0,
            step_start_time=datetime.now(),
            overall_start_time=datetime.now(),
        )

        # 出力ディレクトリ作成
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # コンポーネント初期化（遅延初期化）
        self._gdrive_reader: Optional[GoogleDriveDocumentReader] = None
        self._script_generator: Optional[DialogueScriptGenerator] = None
        self._tts_engine: Optional[GeminiTTSEngine] = None
        self._audio_processor: Optional[AudioProcessor] = None
        self._publisher: Optional[IndependentGitHubPagesPublisher] = None
        self._message_templates: Optional[MessageTemplates] = None
        self._error_handler: Optional[DistributionErrorHandler] = None

        # 一時ファイル管理
        self._temp_files: List[Path] = []

        # メトリクス
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "processing_times": {},
            "component_stats": {},
            "errors": [],
            "warnings": [],
        }

        self.logger.info(f"IndependentPodcastWorkflow初期化完了 - 出力: {self.output_dir}")

    @property
    def gdrive_reader(self) -> GoogleDriveDocumentReader:
        """Google Drive文書リーダー（遅延初期化）"""
        if self._gdrive_reader is None:
            if self.config.max_retries > 1:
                self._gdrive_reader = DocumentReaderWithRetry(
                    max_retries=self.config.max_retries, retry_delay=self.config.retry_delay
                )
            else:
                self._gdrive_reader = GoogleDriveDocumentReader()
            self.logger.debug("Google Drive Reader初期化完了")
        return self._gdrive_reader

    @property
    def script_generator(self) -> DialogueScriptGenerator:
        """台本生成器（遅延初期化）"""
        if self._script_generator is None:
            self._script_generator = DialogueScriptGenerator(
                api_key=self.config.gemini_api_key, model_name=self.config.gemini_model
            )
            self.logger.debug("Script Generator初期化完了")
        return self._script_generator

    @property
    def tts_engine(self) -> GeminiTTSEngine:
        """音声合成エンジン（遅延初期化）"""
        if self._tts_engine is None:
            self._tts_engine = GeminiTTSEngine(api_key=self.config.gemini_api_key)
            self.logger.debug("TTS Engine初期化完了")
        return self._tts_engine

    @property
    def audio_processor(self) -> AudioProcessor:
        """音声処理器（遅延初期化）"""
        if self._audio_processor is None:
            self._audio_processor = AudioProcessor(assets_dir=self.config.assets_dir)
            # ビットレート設定更新
            self._audio_processor.update_settings({"bitrate": self.config.audio_bitrate})
            self.logger.debug("Audio Processor初期化完了")
        return self._audio_processor

    @property
    def publisher(self) -> IndependentGitHubPagesPublisher:
        """配信システム（遅延初期化）"""
        if self._publisher is None:
            podcast_info = {
                "title": self.config.podcast_title,
                "description": self.config.podcast_description,
                "author": self.config.podcast_author,
                "email": self.config.podcast_email,
            }

            self._publisher = IndependentGitHubPagesPublisher(
                github_repo_url=self.config.github_repo_url,
                base_url=self.config.github_pages_base_url,
                podcast_info=podcast_info,
            )
            self.logger.debug("Publisher初期化完了")
        return self._publisher

    @property
    def message_templates(self) -> MessageTemplates:
        """メッセージテンプレート（遅延初期化）"""
        if self._message_templates is None:
            self._message_templates = MessageTemplates(base_url=self.config.github_pages_base_url)
            self.logger.debug("Message Templates初期化完了")
        return self._message_templates

    @property
    def error_handler(self) -> DistributionErrorHandler:
        """エラーハンドラー（遅延初期化）"""
        if self._error_handler is None:
            self._error_handler = DistributionErrorHandler(
                base_url=self.config.github_pages_base_url
            )
            self.logger.debug("Error Handler初期化完了")
        return self._error_handler

    async def execute_workflow(self) -> WorkflowResult:
        """
        ワークフロー全体を実行

        Returns:
            WorkflowResult: 実行結果
        """
        self.logger.info("🚀 独立ポッドキャストワークフロー実行開始")
        self.metrics["start_time"] = datetime.now()

        result = WorkflowResult(
            success=False, episode_id=self._generate_episode_id(), processing_time=0.0
        )

        try:
            # ステップ1: 初期化
            await self._execute_step("初期化", self._step_initialization, result)

            # ステップ2: Google Drive文書読み取り
            articles_data = await self._execute_step(
                "Google Drive文書読み取り", self._step_read_articles, result
            )

            # ステップ3: 記事データ解析・厳選
            selected_articles = await self._execute_step(
                "記事データ解析", lambda: self._step_analyze_articles(articles_data), result
            )
            result.articles_processed = len(selected_articles)

            # ステップ4: 台本生成
            script = await self._execute_step(
                "台本生成", lambda: self._step_generate_script(selected_articles), result
            )

            # ステップ5: 音声合成
            audio_data = await self._execute_step(
                "音声合成", lambda: self._step_synthesize_audio(script, result.episode_id), result
            )

            # ステップ6: 音声処理
            processed_audio_path = await self._execute_step(
                "音声処理",
                lambda: self._step_process_audio(audio_data, result.episode_id, selected_articles),
                result,
            )

            # ステップ7: GitHub Pages配信
            audio_url = await self._execute_step(
                "GitHub Pages配信",
                lambda: self._step_publish_to_github(
                    processed_audio_path, result.episode_id, selected_articles
                ),
                result,
            )
            result.audio_url = audio_url
            result.rss_url = self.publisher.get_rss_url()

            # ファイルサイズ記録
            if Path(processed_audio_path).exists():
                result.file_size_mb = Path(processed_audio_path).stat().st_size / (1024 * 1024)

            # ステップ8: 通知送信
            if self.config.enable_line_notification:
                await self._execute_step(
                    "通知送信",
                    lambda: self._step_send_notifications(result, selected_articles),
                    result,
                )

            # ステップ9: クリーンアップ
            await self._execute_step("クリーンアップ", self._step_cleanup, result)

            # 成功完了
            result.success = True
            self.logger.info("✅ ワークフロー実行完了")

        except Exception as e:
            self.logger.error(f"❌ ワークフロー実行エラー: {e}")

            # エラー処理
            error_info = self.error_handler.handle_error(
                ErrorType.UNKNOWN_ERROR,
                str(e),
                context={"episode_id": result.episode_id, "step": self.progress.current_step},
            )

            result.errors.append(str(e))
            result.success = False

            # クリーンアップは常に実行
            try:
                await self._step_cleanup()
            except Exception as cleanup_error:
                self.logger.warning(f"クリーンアップエラー: {cleanup_error}")

        finally:
            # 最終処理
            self.metrics["end_time"] = datetime.now()
            result.processing_time = self.progress.elapsed_time

            # メトリクス記録
            await self._record_metrics(result)

        return result

    async def _execute_step(self, step_name: str, step_func, result: WorkflowResult):
        """
        単一ステップの実行

        Args:
            step_name: ステップ名
            step_func: ステップ実行関数
            result: 結果オブジェクト

        Returns:
            Any: ステップの実行結果
        """
        self.progress.current_step = step_name
        self.progress.step_start_time = datetime.now()

        self.logger.info(
            f"📍 ステップ開始: {step_name} ({self.progress.completed_steps + 1}/{self.progress.total_steps})"
        )

        step_start = datetime.now()

        try:
            # ステップ実行
            if asyncio.iscoroutinefunction(step_func):
                step_result = await step_func()
            else:
                step_result = step_func()

            # 成功処理
            self.progress.completed_steps += 1
            processing_time = (datetime.now() - step_start).total_seconds()
            self.metrics["processing_times"][step_name] = processing_time

            self.logger.info(f"✅ ステップ完了: {step_name} ({processing_time:.2f}秒)")

            return step_result

        except Exception as e:
            # エラー処理
            processing_time = (datetime.now() - step_start).total_seconds()
            self.metrics["processing_times"][step_name] = processing_time

            self.logger.error(f"❌ ステップ失敗: {step_name} - {e}")

            # エラー記録
            result.errors.append(f"{step_name}: {str(e)}")

            raise

    def _generate_episode_id(self) -> str:
        """エピソードIDを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        return f"market_news_{timestamp}"

    async def _step_initialization(self) -> None:
        """ステップ1: 初期化"""
        # 必要なディレクトリの作成
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # コンポーネントの事前チェック
        try:
            # Google Drive アクセステスト
            is_accessible = self.gdrive_reader.validate_document_access(
                self.config.google_document_id
            )
            if not is_accessible:
                raise Exception("Google Driveドキュメントにアクセスできません")

            self.logger.info("✅ 初期化チェック完了")

        except Exception as e:
            raise Exception(f"初期化エラー: {e}")

    async def _step_read_articles(self) -> List[Dict[str, Any]]:
        """ステップ2: Google Drive文書読み取り"""
        try:
            metadata, articles = self.gdrive_reader.read_and_parse_document(
                self.config.google_document_id, use_cache=True
            )

            if not articles:
                raise Exception("記事データが取得できませんでした")

            self.logger.info(f"✅ {len(articles)}件の記事を読み取り")

            # 記事データをDict形式に変換
            articles_dict = []
            for article in articles:
                articles_dict.append(
                    {
                        "title": article.title,
                        "url": article.url,
                        "summary": article.summary,
                        "sentiment_label": article.sentiment_label,
                        "sentiment_score": article.sentiment_score,
                        "source": article.source,
                        "published_date": article.published_jst.isoformat(),
                    }
                )

            return articles_dict

        except Exception as e:
            raise Exception(f"記事読み取りエラー: {e}")

    async def _step_analyze_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """ステップ3: 記事データ解析・厳選"""
        if not articles:
            raise Exception("解析する記事がありません")

        # 記事の重要度スコア計算
        scored_articles = []
        for article in articles:
            score = self._calculate_article_importance(article)
            article_with_score = article.copy()
            article_with_score["importance_score"] = score
            scored_articles.append(article_with_score)

        # 重要度順でソート
        scored_articles.sort(key=lambda x: x["importance_score"], reverse=True)

        # 最大記事数まで厳選
        selected_articles = scored_articles[: self.config.max_articles]

        self.logger.info(f"✅ {len(articles)}件から{len(selected_articles)}件を厳選")

        return selected_articles

    def _calculate_article_importance(self, article: Dict[str, Any]) -> float:
        """記事の重要度スコアを計算"""
        score = 0.0

        # センチメントスコアの絶対値（話題性）
        sentiment_score = abs(article.get("sentiment_score", 0.0))
        score += sentiment_score * 0.4

        # 要約の長さ（詳細度）
        summary_length = len(article.get("summary", ""))
        score += min(summary_length / 500.0, 1.0) * 0.3

        # タイトルの長さ（詳細度）
        title_length = len(article.get("title", ""))
        score += min(title_length / 100.0, 1.0) * 0.2

        # ソースの信頼度
        source = article.get("source", "").lower()
        if "reuters" in source:
            score += 0.1
        elif "bloomberg" in source:
            score += 0.1

        return score

    async def _step_generate_script(self, articles: List[Dict[str, Any]]) -> str:
        """ステップ4: 台本生成"""
        try:
            script = self.script_generator.generate_script(articles)

            if not script or len(script) < 1000:
                raise Exception("台本が短すぎます")

            # 中間ファイル保存（デバッグ用）
            if self.config.save_intermediates:
                script_path = self.output_dir / f"{self._generate_episode_id()}_script.txt"
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(script)
                self._temp_files.append(script_path)

            self.logger.info(f"✅ 台本生成完了 - {len(script)}文字")

            return script

        except Exception as e:
            raise Exception(f"台本生成エラー: {e}")

    async def _step_synthesize_audio(self, script: str, episode_id: str) -> bytes:
        """ステップ5: 音声合成"""
        try:
            audio_data = self.tts_engine.synthesize_dialogue(script)

            if not audio_data:
                raise Exception("音声データが生成されませんでした")

            # 中間ファイル保存（デバッグ用）
            if self.config.save_intermediates:
                raw_audio_path = self.output_dir / f"{episode_id}_raw.mp3"
                with open(raw_audio_path, "wb") as f:
                    f.write(audio_data)
                self._temp_files.append(raw_audio_path)

            self.logger.info(f"✅ 音声合成完了 - {len(audio_data)}バイト")

            return audio_data

        except Exception as e:
            raise Exception(f"音声合成エラー: {e}")

    async def _step_process_audio(
        self, audio_data: bytes, episode_id: str, articles: List[Dict[str, Any]]
    ) -> str:
        """ステップ6: 音声処理"""
        try:
            # メタデータ作成
            metadata = {
                "title": f"{self.config.podcast_title} - {datetime.now().strftime('%Y年%m月%d日')}",
                "artist": self.config.podcast_author,
                "album": self.config.podcast_title,
                "date": datetime.now().strftime("%Y"),
                "genre": "News",
                "comment": f"記事数: {len(articles)}件",
            }

            processed_path = self.audio_processor.process_audio(
                audio_data=audio_data, episode_id=episode_id, metadata=metadata
            )

            self.logger.info(f"✅ 音声処理完了 - 出力: {processed_path}")

            return processed_path

        except Exception as e:
            raise Exception(f"音声処理エラー: {e}")

    async def _step_publish_to_github(
        self, audio_file_path: str, episode_id: str, articles: List[Dict[str, Any]]
    ) -> Optional[str]:
        """ステップ7: GitHub Pages配信"""
        try:
            # エピソードメタデータ作成
            episode_metadata = {
                "title": f"{self.config.podcast_title} - {datetime.now().strftime('%Y年%m月%d日')}",
                "description": f"本日の市場動向を{len(articles)}件の記事から解説",
                "published_date": datetime.now(),
                "duration": "00:10:00",  # 固定値（実際の再生時間は音声処理後に取得可能）
                "keywords": ["market", "news", "finance", "japan", "ai"],
                "episode_number": self._get_next_episode_number(),
            }

            audio_url = self.publisher.publish_episode(
                audio_file=Path(audio_file_path), episode_metadata=episode_metadata
            )

            if not audio_url:
                raise Exception("配信URLが取得できませんでした")

            self.logger.info(f"✅ 配信完了 - URL: {audio_url}")

            return audio_url

        except Exception as e:
            raise Exception(f"配信エラー: {e}")

    def _get_next_episode_number(self) -> int:
        """次のエピソード番号を取得"""
        try:
            episodes = self.publisher.get_episode_list()
            if episodes:
                max_episode = max([ep.get("episode_number", 0) for ep in episodes])
                return max_episode + 1
            return 1
        except:
            return 1

    async def _step_send_notifications(
        self, result: WorkflowResult, articles: List[Dict[str, Any]]
    ) -> None:
        """ステップ8: 通知送信"""
        try:
            # 通知メッセージ作成
            episode_data = {
                "title": f"{self.config.podcast_title} - {datetime.now().strftime('%Y年%m月%d日')}",
                "duration": "約10分",
                "date": datetime.now().strftime("%Y年%m月%d日"),
                "summary": self._create_articles_summary(articles),
                "filename": Path(result.audio_url).name if result.audio_url else "",
                "file_size_mb": result.file_size_mb,
                "episode_number": self._get_next_episode_number() - 1,  # 既に配信済みなので-1
            }

            notification_message = self.message_templates.create_podcast_notification(episode_data)

            # 実際の通知送信は外部システムに依存するため、ここではログ出力
            self.logger.info("📢 通知メッセージ生成完了")
            if self.config.debug_mode:
                self.logger.debug(f"通知内容:\n{notification_message}")

        except Exception as e:
            # 通知エラーは致命的ではないため、警告レベル
            self.logger.warning(f"通知送信エラー: {e}")

    def _create_articles_summary(self, articles: List[Dict[str, Any]]) -> str:
        """記事から要約を作成"""
        if not articles:
            return "本日の重要な市場動向をお届けします。"

        summaries = []
        for i, article in enumerate(articles[:3], 1):
            title = article.get("title", "").strip()
            if title and len(title) > 10:
                if len(title) > 40:
                    title = title[:37] + "..."
                summaries.append(f"{i}. {title}")

        return "\n".join(summaries) if summaries else "本日の重要な市場動向をお届けします。"

    async def _step_cleanup(self) -> None:
        """ステップ9: クリーンアップ"""
        try:
            # 一時ファイルの削除
            deleted_count = 0
            for temp_file in self._temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                        deleted_count += 1
                except Exception as e:
                    self.logger.warning(f"一時ファイル削除エラー: {temp_file} - {e}")

            # キャッシュクリーンアップ
            if self._gdrive_reader:
                cache_cleaned = self.gdrive_reader.cleanup_cache()

            # 古いエラーレコードのクリーンアップ
            if self._error_handler:
                self.error_handler.cleanup_old_errors()

            self.logger.info(f"✅ クリーンアップ完了 - 一時ファイル{deleted_count}件削除")

        except Exception as e:
            self.logger.warning(f"クリーンアップエラー: {e}")

    async def _record_metrics(self, result: WorkflowResult) -> None:
        """メトリクス記録"""
        try:
            metrics_data = {
                "execution_id": result.episode_id,
                "timestamp": datetime.now().isoformat(),
                "success": result.success,
                "processing_time": result.processing_time,
                "articles_processed": result.articles_processed,
                "file_size_mb": result.file_size_mb,
                "step_times": self.metrics["processing_times"],
                "errors": result.errors,
                "warnings": result.warnings,
                "config": {
                    "max_articles": self.config.max_articles,
                    "target_script_length": self.config.target_script_length,
                    "audio_bitrate": self.config.audio_bitrate,
                },
            }

            # メトリクスファイルに記録
            metrics_file = self.output_dir / "workflow_metrics.jsonl"
            with open(metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(metrics_data, ensure_ascii=False) + "\n")

            self.logger.info("📊 メトリクス記録完了")

        except Exception as e:
            self.logger.warning(f"メトリクス記録エラー: {e}")

    def get_progress_info(self) -> Dict[str, Any]:
        """現在の進行状況を取得"""
        return {
            "current_step": self.progress.current_step,
            "progress_percentage": self.progress.progress_percentage,
            "completed_steps": self.progress.completed_steps,
            "total_steps": self.progress.total_steps,
            "elapsed_time": self.progress.elapsed_time,
            "estimated_remaining_time": self.progress.estimated_remaining_time,
            "processing_times": self.metrics["processing_times"],
        }

    def get_component_status(self) -> Dict[str, Any]:
        """コンポーネントの状態を取得"""
        return {
            "gdrive_reader": {
                "initialized": self._gdrive_reader is not None,
                "info": self._gdrive_reader.get_processing_info() if self._gdrive_reader else None,
            },
            "script_generator": {
                "initialized": self._script_generator is not None,
                "model": self.config.gemini_model,
            },
            "tts_engine": {
                "initialized": self._tts_engine is not None,
                "config": self._tts_engine.get_voice_config() if self._tts_engine else None,
            },
            "audio_processor": {
                "initialized": self._audio_processor is not None,
                "info": (
                    self._audio_processor.get_processing_info() if self._audio_processor else None
                ),
            },
            "publisher": {
                "initialized": self._publisher is not None,
                "stats": self._publisher.get_stats() if self._publisher else None,
            },
            "error_handler": {
                "initialized": self._error_handler is not None,
                "stats": (
                    self._error_handler.get_error_statistics() if self._error_handler else None
                ),
            },
        }


# テストとデモ用のヘルパー関数
async def demo_workflow_execution():
    """デモワークフロー実行"""
    # 設定例
    config = WorkflowConfig(
        google_document_id="your_document_id_here",
        gemini_api_key="your_gemini_api_key",
        github_repo_url="https://github.com/username/repo.git",
        github_pages_base_url="https://username.github.io/repo",
        debug_mode=True,
    )

    # ワークフロー実行
    workflow = IndependentPodcastWorkflow(config)

    try:
        result = await workflow.execute_workflow()

        print(f"ワークフロー実行結果:")
        print(f"  成功: {result.success}")
        print(f"  エピソードID: {result.episode_id}")
        print(f"  処理時間: {result.processing_time:.2f}秒")
        print(f"  音声URL: {result.audio_url}")
        print(f"  記事処理数: {result.articles_processed}")
        print(f"  ファイルサイズ: {result.file_size_mb:.1f}MB")

        if result.errors:
            print(f"  エラー: {result.errors}")

        return result

    except Exception as e:
        print(f"ワークフロー実行エラー: {e}")
        return None


if __name__ == "__main__":
    import asyncio

    # デモ実行
    asyncio.run(demo_workflow_execution())
