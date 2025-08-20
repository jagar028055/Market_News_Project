# -*- coding: utf-8 -*-

"""
スマート通知管理システム
Phase 2の全機能を統合する管理クラス
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from src.podcast.integration.line_broadcaster import LineBroadcaster
from src.podcast.integration.flex_message_templates import FlexMessageTemplates
from src.podcast.integration.image_asset_manager import ImageAssetManager
from src.podcast.integration.notification_scheduler import (
    NotificationScheduler,
    NotificationPriority,
    NotificationStatus,
)


class SmartNotificationManager:
    """
    スマート通知管理システム

    Phase 2で実装された全機能を統合し、
    ポッドキャスト通知の包括的な管理を提供
    """

    def __init__(self, config, logger: logging.Logger):
        """
        初期化

        Args:
            config: アプリケーション設定
            logger: ロガー
        """
        self.config = config
        self.logger = logger

        # 各コンポーネントを初期化
        self.line_broadcaster = LineBroadcaster(config, logger)
        self.flex_templates = FlexMessageTemplates(logger)
        self.image_manager = ImageAssetManager(config, logger)
        self.scheduler = NotificationScheduler(config, logger)

        # 統合設定
        self.default_settings = {
            "use_flex_message": True,
            "use_images": True,
            "auto_schedule": True,
            "priority": NotificationPriority.NORMAL,
            "enable_fallback": True,
        }

        self.logger.info("スマート通知管理システム初期化完了")

    def send_podcast_notification(
        self,
        episode_info: Dict[str, Any],
        articles: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        ポッドキャスト通知を送信（即座に配信）

        Args:
            episode_info: エピソード情報
            articles: 記事データ
            options: 配信オプション

        Returns:
            Dict[str, Any]: 送信結果
        """
        try:
            # オプション設定をマージ
            send_options = {**self.default_settings, **(options or {})}

            self.logger.info(f"ポッドキャスト通知送信開始 (記事数: {len(articles)})")

            # 画像アセット準備
            image_urls = {}
            if send_options.get("use_images", True):
                image_urls = self._prepare_image_assets(episode_info)

            # 音声・RSSファイルURL取得
            audio_url = send_options.get("audio_url")
            rss_url = send_options.get(
                "rss_url", f"{self.config.podcast.rss_base_url}/podcast/feed.xml"
            )

            # 送信実行
            success = self.line_broadcaster.broadcast_podcast_notification(
                episode_info=episode_info,
                articles=articles,
                audio_url=audio_url,
                rss_url=rss_url,
                use_flex=send_options.get("use_flex_message", True),
            )

            result = {
                "success": success,
                "sent_at": datetime.now().isoformat(),
                "episode_info": episode_info,
                "article_count": len(articles),
                "options_used": send_options,
                "image_urls": image_urls,
            }

            if success:
                self.logger.info("ポッドキャスト通知送信成功")
            else:
                self.logger.error("ポッドキャスト通知送信失敗")

            return result

        except Exception as e:
            self.logger.error(f"ポッドキャスト通知送信エラー: {e}")
            return {"success": False, "error": str(e), "sent_at": datetime.now().isoformat()}

    def schedule_podcast_notification(
        self,
        episode_info: Dict[str, Any],
        articles: List[Dict[str, Any]],
        schedule_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        ポッドキャスト通知をスケジュール（後で配信）

        Args:
            episode_info: エピソード情報
            articles: 記事データ
            schedule_options: スケジュールオプション

        Returns:
            Dict[str, Any]: スケジュール結果
        """
        try:
            # スケジュールオプション設定
            options = {**self.default_settings, **(schedule_options or {})}

            # 配信予定時刻決定
            scheduled_time = options.get("scheduled_time")
            if scheduled_time is None and options.get("auto_schedule", True):
                # 自動スケジューリング
                priority = options.get("priority", NotificationPriority.NORMAL)
                if isinstance(priority, str):
                    priority = NotificationPriority(priority)
                scheduled_time = self.scheduler._calculate_optimal_time(priority)

            # 画像アセット事前準備
            image_urls = {}
            if options.get("use_images", True):
                image_urls = self._prepare_image_assets(episode_info)

            # 配信オプション準備
            delivery_options = {
                "use_flex_message": options.get("use_flex_message", True),
                "audio_url": options.get("audio_url"),
                "rss_url": options.get(
                    "rss_url", f"{self.config.podcast.rss_base_url}/podcast/feed.xml"
                ),
                "image_urls": image_urls,
            }

            # スケジューラーに登録
            notification_id = self.scheduler.schedule_podcast_notification(
                episode_info=episode_info,
                articles=articles,
                scheduled_time=scheduled_time,
                priority=priority if "priority" in locals() else NotificationPriority.NORMAL,
                delivery_options=delivery_options,
            )

            result = {
                "success": True,
                "notification_id": notification_id,
                "scheduled_time": scheduled_time.isoformat() if scheduled_time else None,
                "episode_info": episode_info,
                "article_count": len(articles),
                "options_used": options,
                "image_urls": image_urls,
            }

            self.logger.info(f"ポッドキャスト通知スケジュール登録: {notification_id}")
            return result

        except Exception as e:
            self.logger.error(f"ポッドキャスト通知スケジュールエラー: {e}")
            return {"success": False, "error": str(e), "scheduled_at": datetime.now().isoformat()}

    def send_multiple_episodes(
        self, episodes: List[Dict[str, Any]], batch_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        複数エピソードの一括通知送信

        Args:
            episodes: エピソードリスト
            batch_options: バッチ処理オプション

        Returns:
            Dict[str, Any]: 一括送信結果
        """
        try:
            options = {**self.default_settings, **(batch_options or {})}

            self.logger.info(f"複数エピソード一括送信開始: {len(episodes)}件")

            # カルーセル形式で送信するか判定
            use_carousel = (
                options.get("use_carousel", True)
                and len(episodes) > 1
                and len(episodes) <= 10
                and options.get("use_flex_message", True)
            )

            if use_carousel:
                # カルーセル形式で送信
                success = self.line_broadcaster.broadcast_multiple_episodes(
                    episodes, use_carousel=True
                )

                result = {
                    "success": success,
                    "method": "carousel",
                    "episode_count": len(episodes),
                    "sent_at": datetime.now().isoformat(),
                }

            else:
                # 個別送信
                results = []
                for i, episode_data in enumerate(episodes):
                    episode_info = episode_data.get("episode_info", {})
                    articles = episode_data.get("articles", [])
                    episode_options = episode_data.get("options", {})

                    # 個別送信実行
                    send_result = self.send_podcast_notification(
                        episode_info, articles, episode_options
                    )
                    results.append(send_result)

                    # 送信間隔制御
                    if i < len(episodes) - 1:
                        import time

                        time.sleep(options.get("send_interval", 2))

                success_count = sum(1 for r in results if r.get("success", False))

                result = {
                    "success": success_count == len(episodes),
                    "method": "individual",
                    "episode_count": len(episodes),
                    "success_count": success_count,
                    "failed_count": len(episodes) - success_count,
                    "results": results,
                    "sent_at": datetime.now().isoformat(),
                }

            self.logger.info(
                f"複数エピソード送信完了: 成功率 {success_count if 'success_count' in locals() else int(success)}/{len(episodes)}"
            )
            return result

        except Exception as e:
            self.logger.error(f"複数エピソード送信エラー: {e}")
            return {
                "success": False,
                "error": str(e),
                "episode_count": len(episodes),
                "sent_at": datetime.now().isoformat(),
            }

    def get_notification_preview(
        self,
        episode_info: Dict[str, Any],
        articles: List[Dict[str, Any]],
        preview_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        通知のプレビューを生成

        Args:
            episode_info: エピソード情報
            articles: 記事データ
            preview_options: プレビューオプション

        Returns:
            Dict[str, Any]: プレビューデータ
        """
        try:
            options = {**self.default_settings, **(preview_options or {})}

            # 基本プレビュー取得
            preview = self.line_broadcaster.get_message_preview(
                episode_info=episode_info,
                articles=articles,
                audio_url=options.get("audio_url"),
                rss_url=options.get("rss_url"),
            )

            # 画像アセット情報追加
            image_urls = {}
            if options.get("use_images", True):
                image_urls = self._prepare_image_assets(episode_info)

            # 統計情報追加
            sentiment_distribution = self.scheduler._analyze_sentiment_distribution(articles)

            enhanced_preview = {
                **preview,
                "episode_info": episode_info,
                "article_count": len(articles),
                "image_urls": image_urls,
                "sentiment_distribution": sentiment_distribution,
                "estimated_send_time": self._estimate_send_time(options),
                "options": options,
                "generated_at": datetime.now().isoformat(),
            }

            return enhanced_preview

        except Exception as e:
            self.logger.error(f"プレビュー生成エラー: {e}")
            return {"error": str(e), "generated_at": datetime.now().isoformat()}

    def get_system_status(self) -> Dict[str, Any]:
        """
        システム全体のステータスを取得

        Returns:
            Dict[str, Any]: システムステータス
        """
        try:
            # 各コンポーネントのステータス取得
            line_status = self._get_line_broadcaster_status()
            scheduler_status = self.scheduler.get_schedule_stats()
            image_status = self.image_manager.get_cache_stats()

            system_status = {
                "overall_status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "line_broadcaster": line_status,
                    "scheduler": scheduler_status,
                    "image_manager": image_status,
                },
                "settings": self.default_settings,
            }

            # 健康状態判定
            if not scheduler_status.get("scheduler_running", False):
                system_status["overall_status"] = "warning"

            return system_status

        except Exception as e:
            self.logger.error(f"システムステータス取得エラー: {e}")
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _prepare_image_assets(self, episode_info: Dict[str, Any]) -> Dict[str, str]:
        """
        画像アセットを準備

        Args:
            episode_info: エピソード情報

        Returns:
            Dict[str, str]: 画像URL辞書
        """
        try:
            image_urls = {}

            # 各タイプの画像を生成
            for image_type in ["thumbnail", "header", "icon"]:
                url = self.image_manager.get_or_create_podcast_image(episode_info, image_type)
                if url:
                    image_urls[image_type] = url

            return image_urls

        except Exception as e:
            self.logger.warning(f"画像アセット準備エラー: {e}")
            return {}

    def _get_line_broadcaster_status(self) -> Dict[str, Any]:
        """LINE Broadcasterのステータス取得"""
        try:
            # 接続テスト実行
            connection_ok = self.line_broadcaster.test_connection()

            return {
                "connection_status": "connected" if connection_ok else "disconnected",
                "flex_message_enabled": self.line_broadcaster.use_flex_message,
                "api_base_url": self.line_broadcaster.api_base_url,
                "last_check": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "connection_status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat(),
            }

    def _estimate_send_time(self, options: Dict[str, Any]) -> str:
        """
        送信予定時刻を推定

        Args:
            options: 配信オプション

        Returns:
            str: 推定送信時刻
        """
        if options.get("auto_schedule", True):
            priority = options.get("priority", NotificationPriority.NORMAL)
            if isinstance(priority, str):
                priority = NotificationPriority(priority)
            estimated_time = self.scheduler._calculate_optimal_time(priority)
            return estimated_time.isoformat()
        else:
            return "immediate"

    def start_system(self) -> bool:
        """
        システム全体を開始

        Returns:
            bool: 開始成功時True
        """
        try:
            # スケジューラー開始
            self.scheduler.start_scheduler()

            # 画像キャッシュクリーンアップ
            self.image_manager.cleanup_expired_cache()

            self.logger.info("スマート通知管理システム開始完了")
            return True

        except Exception as e:
            self.logger.error(f"システム開始エラー: {e}")
            return False

    def stop_system(self) -> bool:
        """
        システム全体を停止

        Returns:
            bool: 停止成功時True
        """
        try:
            # スケジューラー停止
            self.scheduler.stop_scheduler()

            self.logger.info("スマート通知管理システム停止完了")
            return True

        except Exception as e:
            self.logger.error(f"システム停止エラー: {e}")
            return False

    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """
        システム設定を更新

        Args:
            new_settings: 新しい設定

        Returns:
            bool: 更新成功時True
        """
        try:
            # 設定検証
            valid_keys = set(self.default_settings.keys())
            invalid_keys = set(new_settings.keys()) - valid_keys

            if invalid_keys:
                self.logger.warning(f"無効な設定キー: {invalid_keys}")

            # 有効な設定のみを更新
            for key, value in new_settings.items():
                if key in valid_keys:
                    self.default_settings[key] = value

            # 各コンポーネントに設定を適用
            if "use_flex_message" in new_settings:
                self.line_broadcaster.set_flex_message_enabled(new_settings["use_flex_message"])

            self.logger.info(f"システム設定更新完了: {new_settings}")
            return True

        except Exception as e:
            self.logger.error(f"設定更新エラー: {e}")
            return False
