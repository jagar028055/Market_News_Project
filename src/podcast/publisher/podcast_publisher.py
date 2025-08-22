"""マルチチャンネル配信統合機能の実装"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time
from pathlib import Path

from .rss_generator import RSSGenerator
from .line_broadcaster import LINEBroadcaster
from ...config.app_config import AppConfig
from ...error_handling.custom_exceptions import NewsAggregatorError
from ..error_handling.publish_error_handler import PublishErrorHandler


logger = logging.getLogger(__name__)


class PodcastPublishError(NewsAggregatorError):
    """ポッドキャスト配信関連のエラー"""

    pass


class PodcastPublisher:
    """ポッドキャスト マルチチャンネル配信統合クラス"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.podcast_config = config.podcast

        # 配信チャンネル初期化
        self.rss_generator = RSSGenerator(config)
        self.line_broadcaster = LINEBroadcaster(config)

        # エラーハンドリング初期化
        self.error_handler = PublishErrorHandler(config)

        # 配信結果追跡
        self.publish_results = {}

    def publish_episode(self, episode: Dict, audio_file_path: str) -> Dict[str, bool]:
        """エピソードを全チャンネルに配信

        Args:
            episode: エピソード情報
            audio_file_path: 音声ファイルのパス

        Returns:
            Dict[str, bool]: チャンネル別配信結果
        """
        logger.info(f"Starting multi-channel publish for episode: {episode['title']}")

        results = {"rss": False, "line": False, "overall_success": False}

        try:
            # エピソードデータの妥当性検証
            if not self.validate_episode_data(episode):
                raise PodcastPublishError("エピソードデータが不正です")

            # 音声ファイルを配信用ディレクトリにコピー
            self._prepare_audio_file(audio_file_path, episode["audio_filename"])

            # エラーハンドリング機能付きでRSS配信
            results["rss"] = self.error_handler.execute_with_retry(
                self._publish_to_rss, episode["guid"], "rss", episode
            )

            # エラーハンドリング機能付きでLINE配信
            results["line"] = self.error_handler.execute_with_retry(
                self._publish_to_line, episode["guid"], "line", episode
            )

            # 部分的成功の処理
            if not (results["rss"] and results["line"]):
                results = self.error_handler.handle_partial_success(episode, results)

            # 全体的な成功判定
            results["overall_success"] = results["rss"] or results["line"]

            # 結果をログ出力
            self._log_publish_results(episode, results)

            return results

        except Exception as e:
            logger.error(f"Multi-channel publish failed: {e}")
            raise PodcastPublishError(f"配信処理でエラーが発生しました: {e}")

    def _prepare_audio_file(self, source_path: str, target_filename: str) -> None:
        """音声ファイルを配信用ディレクトリに準備"""
        try:
            source = Path(source_path)
            target_dir = Path(self.podcast_config.audio_output_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / target_filename

            # ファイルコピー
            import shutil

            shutil.copy2(source, target)

            logger.info(f"Audio file prepared: {target}")

        except Exception as e:
            logger.error(f"Audio file preparation failed: {e}")
            raise

    def _publish_to_rss(self, episode: Dict) -> bool:
        """RSS配信実行"""
        try:
            logger.info("Publishing to RSS...")

            # 既存エピソードリストを取得（実際の実装では永続化ストレージから）
            episodes = self._get_existing_episodes()
            episodes.append(episode)

            # RSSフィード生成
            rss_path = self.rss_generator.generate_rss_feed(episodes)

            # GitHub Pagesへのデプロイ（実際の実装ではGit操作を含む）
            deployment_success = self._deploy_to_github_pages(rss_path)

            if deployment_success:
                logger.info("RSS publish successful")
                return True
            else:
                logger.error("RSS deployment failed")
                return False

        except Exception as e:
            logger.error(f"RSS publish failed: {e}")
            return False

    def _publish_to_line(self, episode: Dict) -> bool:
        """LINE配信実行"""
        try:
            logger.info("Publishing to LINE...")

            success = self.line_broadcaster.broadcast_episode(episode)

            if success:
                logger.info("LINE publish successful")
                return True
            else:
                logger.error("LINE publish failed")
                return False

        except Exception as e:
            logger.error(f"LINE publish failed: {e}")
            return False

    def _get_existing_episodes(self) -> List[Dict]:
        """既存エピソード一覧を取得（モック実装）"""
        # 実際の実装では、データベースまたはファイルシステムから取得
        return []

    def _deploy_to_github_pages(self, rss_path: str) -> bool:
        """GitHub Pagesへのデプロイ（モック実装）"""
        # 実際の実装では、Git操作を含む
        logger.info(f"Deploying RSS to GitHub Pages: {rss_path}")
        return True

    def _log_publish_results(self, episode: Dict, results: Dict[str, bool]) -> None:
        """配信結果をログ出力"""
        logger.info("=== Publish Results ===")
        logger.info(f"Episode: {episode['title']}")
        logger.info(f"RSS: {'✓' if results['rss'] else '✗'}")
        logger.info(f"LINE: {'✓' if results['line'] else '✗'}")
        logger.info(f"Overall: {'SUCCESS' if results['overall_success'] else 'FAILED'}")
        logger.info("=======================")

    def retry_failed_publish(
        self, episode: Dict, failed_channels: List[str], max_retries: int = 3
    ) -> Dict[str, bool]:
        """失敗した配信の再試行

        Args:
            episode: エピソード情報
            failed_channels: 失敗したチャンネルのリスト
            max_retries: 最大再試行回数

        Returns:
            Dict[str, bool]: 再試行結果
        """
        results = {}

        for channel in failed_channels:
            success = False

            for attempt in range(max_retries):
                logger.info(f"Retrying {channel} publish (attempt {attempt + 1}/{max_retries})")

                try:
                    if channel == "rss":
                        success = self._publish_to_rss(episode)
                    elif channel == "line":
                        success = self._publish_to_line(episode)

                    if success:
                        logger.info(f"{channel} retry successful")
                        break
                    else:
                        # 指数バックオフで待機
                        wait_time = 2**attempt
                        logger.info(f"Retry failed, waiting {wait_time} seconds...")
                        time.sleep(wait_time)

                except Exception as e:
                    logger.error(f"{channel} retry failed: {e}")
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt
                        time.sleep(wait_time)

            results[channel] = success

        return results

    def get_publish_status(self, episode_guid: str) -> Dict:
        """配信状況を取得"""
        # 実際の実装では永続化ストレージから状況を取得
        return {
            "episode_guid": episode_guid,
            "rss_published": True,
            "line_published": True,
            "last_updated": datetime.now(),
        }

    def cleanup_old_episodes(self, keep_count: int = 50) -> None:
        """古いエピソードのクリーンアップ"""
        try:
            # 音声ファイルディレクトリから古いファイルを削除
            audio_dir = Path(self.podcast_config.audio_output_dir)

            if audio_dir.exists():
                audio_files = sorted(
                    audio_dir.glob("*.mp3"), key=lambda f: f.stat().st_mtime, reverse=True
                )

                # 保持数を超えるファイルを削除
                if len(audio_files) > keep_count:
                    for old_file in audio_files[keep_count:]:
                        old_file.unlink()
                        logger.info(f"Removed old audio file: {old_file}")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def validate_episode_data(self, episode: Dict) -> bool:
        """エピソードデータの妥当性検証"""
        required_fields = [
            "title",
            "description",
            "audio_filename",
            "duration",
            "file_size",
            "pub_date",
            "guid",
        ]

        for field in required_fields:
            if field not in episode:
                logger.error(f"Missing required field: {field}")
                return False

        # ファイルサイズ制限チェック
        if episode["file_size"] > self.podcast_config.max_file_size_mb * 1024 * 1024:
            logger.error(f"File size exceeds limit: {episode['file_size']} bytes")
            return False

        return True

    def get_error_summary(self, hours: int = 24) -> Dict:
        """配信エラーサマリーを取得"""
        return self.error_handler.get_error_summary(hours)

    def check_error_alerts(self) -> bool:
        """エラーアラートをチェック"""
        return self.error_handler.should_alert()

    def cleanup_error_logs(self, days: int = 30) -> None:
        """古いエラーログをクリーンアップ"""
        self.error_handler.error_tracker.cleanup_old_errors(days)
