"""ポッドキャスト処理統合クラス"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import uuid
from pathlib import Path
import asyncio

from ...core.news_processor import NewsProcessor
from ..script_generation.dialogue_script_generator import DialogueScriptGenerator
from ..tts.gemini_tts_engine import GeminiTTSEngine
from ..audio.audio_processor import AudioProcessor
from ..publisher.podcast_publisher import PodcastPublisher
from ..monitoring.cost_monitor import CostMonitor
from ...config.app_config import AppConfig
from ...error_handling.custom_exceptions import PodcastProcessingError


logger = logging.getLogger(__name__)


class PodcastProcessor:
    """ポッドキャスト生成パイプライン統合クラス"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.podcast_config = config.podcast

        # 既存NewsProcessorとの統合
        self.news_processor = NewsProcessor(config)

        # ポッドキャスト処理コンポーネント
        self.script_generator = DialogueScriptGenerator(config.ai.gemini_api_key)
        self.tts_engine = GeminiTTSEngine(config.ai.gemini_api_key)
        self.audio_processor = AudioProcessor(
            str(Path(config.base_dir) / "src" / "podcast" / "assets")
        )
        self.publisher = PodcastPublisher(config)

        # 監視・管理
        self.cost_monitor = CostMonitor(config)

        # 処理状態追跡
        self.processing_state = {"current_episode": None, "start_time": None, "stage": "idle"}

    async def generate_daily_podcast(self) -> Dict:
        """毎日のポッドキャスト生成メイン処理

        Returns:
            Dict: 処理結果情報
        """
        processing_id = str(uuid.uuid4())
        self.processing_state.update(
            {"current_episode": processing_id, "start_time": datetime.now(), "stage": "starting"}
        )

        logger.info(f"Starting daily podcast generation: {processing_id}")

        try:
            # Step 1: コスト制限チェック
            await self._check_cost_limits()

            # Step 2: ニュース収集・要約（既存機能活用）
            news_data = await self._collect_and_summarize_news()

            # Step 3: 対話台本生成
            script = await self._generate_dialogue_script(news_data)

            # Step 4: TTS音声合成
            audio_data = await self._synthesize_audio(script)

            # Step 5: 音声処理・最適化
            final_audio_path = await self._process_audio(audio_data, processing_id)

            # Step 6: エピソード情報作成
            episode_info = await self._create_episode_info(
                processing_id, news_data, script, final_audio_path
            )

            # Step 7: マルチチャンネル配信
            publish_results = await self._publish_episode(episode_info, final_audio_path)

            # Step 8: 処理結果まとめ
            result = self._create_processing_result(
                processing_id, episode_info, publish_results, success=True
            )

            logger.info(f"Daily podcast generation completed successfully: {processing_id}")
            return result

        except Exception as e:
            logger.error(f"Daily podcast generation failed: {e}")
            result = self._create_processing_result(
                processing_id, None, None, success=False, error=str(e)
            )
            return result

        finally:
            self.processing_state.update(
                {"current_episode": None, "start_time": None, "stage": "idle"}
            )

    async def _check_cost_limits(self) -> None:
        """コスト制限チェック"""
        self.processing_state["stage"] = "cost_check"

        current_costs = self.cost_monitor.get_current_month_costs()
        if current_costs.get("total", 0) >= self.podcast_config.monthly_cost_limit:
            raise PodcastProcessingError(
                f"月間コスト制限に到達しています: ${current_costs.get('total', 0):.2f}"
            )

        # 今日の予想コストを計算
        estimated_cost = self.cost_monitor.estimate_episode_cost()
        if current_costs.get("total", 0) + estimated_cost > self.podcast_config.monthly_cost_limit:
            raise PodcastProcessingError(f"予想コストが制限を超過します: ${estimated_cost:.2f}")

        logger.info(
            f"Cost check passed. Current: ${current_costs.get('total', 0):.2f}, Estimated: ${estimated_cost:.2f}"
        )

    async def _collect_and_summarize_news(self) -> Dict:
        """ニュース収集・要約（既存機能活用）"""
        self.processing_state["stage"] = "news_collection"

        try:
            # 既存のNewsProcessorを使用してニュース処理
            logger.info("Starting news collection and summarization")

            # ニュース収集
            collected_articles = await asyncio.to_thread(self.news_processor.collect_articles)

            if not collected_articles:
                raise PodcastProcessingError("ニュース収集に失敗しました")

            logger.info(f"Collected {len(collected_articles)} articles")

            # AI要約処理
            summarized_articles = await asyncio.to_thread(
                self.news_processor.process_articles_with_ai, collected_articles
            )

            if not summarized_articles:
                raise PodcastProcessingError("ニュース要約処理に失敗しました")

            logger.info(f"Summarized {len(summarized_articles)} articles")

            # ポッドキャスト用に記事データを整理
            podcast_news_data = {
                "articles": summarized_articles,
                "collection_time": datetime.now(),
                "total_articles": len(summarized_articles),
                "sources": list(
                    set(article.get("source", "unknown") for article in summarized_articles)
                ),
            }

            return podcast_news_data

        except Exception as e:
            logger.error(f"News collection and summarization failed: {e}")
            raise PodcastProcessingError(f"ニュース処理でエラーが発生しました: {e}")

    async def _generate_dialogue_script(self, news_data: Dict) -> str:
        """対話台本生成"""
        self.processing_state["stage"] = "script_generation"

        try:
            logger.info("Generating dialogue script")

            # 記事を重要度順に並び替え
            prioritized_articles = self.script_generator._prioritize_articles(news_data["articles"])

            # 対話台本生成
            script = await asyncio.to_thread(
                self.script_generator.generate_script, prioritized_articles
            )

            # 文字数チェック
            script_length = len(script)
            target_min, target_max = self.podcast_config.target_character_count

            if script_length < target_min:
                logger.warning(f"Script too short: {script_length} < {target_min}")
                # 追加コンテンツ生成または既存台本の拡張
                script = await self._extend_script(script, prioritized_articles, target_min)

            elif script_length > target_max:
                logger.warning(f"Script too long: {script_length} > {target_max}")
                # 台本の縮約
                script = await self._shorten_script(script, target_max)

            logger.info(f"Generated script: {len(script)} characters")

            # TTS使用量を追跡
            self.cost_monitor.track_tts_usage(len(script))

            return script

        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            raise PodcastProcessingError(f"台本生成でエラーが発生しました: {e}")

    async def _synthesize_audio(self, script: str) -> bytes:
        """TTS音声合成"""
        self.processing_state["stage"] = "tts_synthesis"

        try:
            logger.info("Synthesizing audio with TTS")

            # 音声合成実行
            audio_data = await asyncio.to_thread(self.tts_engine.synthesize_dialogue, script)

            if not audio_data:
                raise PodcastProcessingError("TTS音声合成に失敗しました")

            logger.info(f"TTS synthesis completed: {len(audio_data)} bytes")
            return audio_data

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise PodcastProcessingError(f"音声合成でエラーが発生しました: {e}")

    async def _process_audio(self, audio_data: bytes, episode_id: str) -> str:
        """音声処理・最適化"""
        self.processing_state["stage"] = "audio_processing"

        try:
            logger.info("Processing and optimizing audio")

            # 音声処理実行
            processed_audio_path = await asyncio.to_thread(
                self.audio_processor.process_audio, audio_data, episode_id
            )

            if not processed_audio_path or not Path(processed_audio_path).exists():
                raise PodcastProcessingError("音声処理に失敗しました")

            # ファイルサイズ・再生時間チェック
            audio_info = self.audio_processor.get_audio_info(processed_audio_path)

            if audio_info["file_size"] > self.podcast_config.max_file_size_mb * 1024 * 1024:
                logger.warning(f"Audio file too large: {audio_info['file_size']} bytes")
                # ファイルサイズ縮小処理
                processed_audio_path = await self._compress_audio(processed_audio_path)

            logger.info(f"Audio processing completed: {processed_audio_path}")
            logger.info(f"File info: {audio_info}")

            return processed_audio_path

        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            raise PodcastProcessingError(f"音声処理でエラーが発生しました: {e}")

    async def _create_episode_info(
        self, episode_id: str, news_data: Dict, script: str, audio_path: str
    ) -> Dict:
        """エピソード情報作成"""
        self.processing_state["stage"] = "episode_creation"

        try:
            # 音声ファイル情報取得
            audio_info = self.audio_processor.get_audio_info(audio_path)

            # エピソード番号生成（日付ベース）
            episode_number = self._generate_episode_number()

            # エピソード情報構築
            episode_info = {
                "guid": episode_id,
                "episode_number": episode_number,
                "title": f"マーケットニュース第{episode_number}回",
                "description": self._create_episode_description(news_data, script),
                "audio_filename": f"episode-{episode_number:03d}.mp3",
                "duration": audio_info["duration"],
                "file_size": audio_info["file_size"],
                "pub_date": datetime.now(),
                "source_articles": news_data["articles"],
                "transcript": script,
                "credits": self.audio_processor.get_credits_info(),
            }

            logger.info(f"Episode info created: {episode_info['title']}")
            return episode_info

        except Exception as e:
            logger.error(f"Episode info creation failed: {e}")
            raise PodcastProcessingError(f"エピソード情報作成でエラーが発生しました: {e}")

    async def _publish_episode(self, episode_info: Dict, audio_path: str) -> Dict:
        """マルチチャンネル配信"""
        self.processing_state["stage"] = "publishing"

        try:
            logger.info("Publishing episode to multiple channels")

            # 配信実行
            publish_results = await asyncio.to_thread(
                self.publisher.publish_episode, episode_info, audio_path
            )

            logger.info(f"Publishing completed: {publish_results}")
            return publish_results

        except Exception as e:
            logger.error(f"Publishing failed: {e}")
            raise PodcastProcessingError(f"配信処理でエラーが発生しました: {e}")

    def _create_processing_result(
        self,
        processing_id: str,
        episode_info: Optional[Dict],
        publish_results: Optional[Dict],
        success: bool,
        error: Optional[str] = None,
    ) -> Dict:
        """処理結果作成"""
        result = {
            "processing_id": processing_id,
            "success": success,
            "timestamp": datetime.now(),
            "processing_time": None,
            "episode_info": episode_info,
            "publish_results": publish_results,
            "error": error,
        }

        if self.processing_state["start_time"]:
            processing_time = datetime.now() - self.processing_state["start_time"]
            result["processing_time"] = processing_time.total_seconds()

        return result

    def _generate_episode_number(self) -> int:
        """エピソード番号生成（日付ベース）"""
        # 開始日からの日数でエピソード番号を計算
        start_date = datetime(2024, 1, 1)  # 開始日
        current_date = datetime.now()
        days_since_start = (current_date - start_date).days
        return days_since_start + 1

    def _create_episode_description(self, news_data: Dict, script: str) -> str:
        """エピソード説明文作成"""
        description = f"今日のマーケットニュースをお届けします。\n\n"
        description += f"収集記事数: {news_data['total_articles']}件\n"
        description += f"情報源: {', '.join(news_data['sources'])}\n"
        description += (
            f"収集時刻: {news_data['collection_time'].strftime('%Y年%m月%d日 %H:%M')}\n\n"
        )

        # 主要トピックを抽出（簡易実装）
        topics = self._extract_main_topics(news_data["articles"])
        if topics:
            description += "主要トピック:\n"
            for i, topic in enumerate(topics[:5], 1):
                description += f"{i}. {topic}\n"

        return description

    def _extract_main_topics(self, articles: List[Dict]) -> List[str]:
        """主要トピック抽出（簡易実装）"""
        # 実際の実装では自然言語処理を使用
        topics = []
        for article in articles[:5]:  # 上位5記事から
            if "title" in article:
                topics.append(article["title"])
        return topics

    async def _extend_script(self, script: str, articles: List[Dict], target_length: int) -> str:
        """台本拡張"""
        # 簡易実装：追加記事から補完コンテンツを生成
        remaining_articles = articles[5:]  # 最初の5記事以外を使用
        if remaining_articles:
            additional_script = await asyncio.to_thread(
                self.script_generator.generate_script, remaining_articles[:3]  # 追加で3記事を使用
            )
            return script + "\n" + additional_script[: target_length - len(script)]
        return script

    async def _shorten_script(self, script: str, target_length: int) -> str:
        """台本縮約"""
        # 簡易実装：文字数で切り詰め
        if len(script) <= target_length:
            return script
        return script[: target_length - 3] + "..."

    async def _compress_audio(self, audio_path: str) -> str:
        """音声ファイル圧縮"""
        compressed_path = await asyncio.to_thread(
            self.audio_processor.compress_audio, audio_path, self.podcast_config.max_file_size_mb
        )
        return compressed_path

    def get_processing_status(self) -> Dict:
        """現在の処理状況を取得"""
        return self.processing_state.copy()

    def get_cost_summary(self) -> Dict:
        """コスト使用状況サマリー取得"""
        return self.cost_monitor.get_cost_summary()

    def cleanup_old_files(self, days: int = 7) -> None:
        """古いファイルのクリーンアップ"""
        try:
            # 音声ファイルクリーンアップ
            self.audio_processor.cleanup_old_files(days)

            # 配信エラーログクリーンアップ
            self.publisher.cleanup_error_logs(days * 3)  # エラーログは長めに保持

            logger.info(f"Cleanup completed: older than {days} days")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
