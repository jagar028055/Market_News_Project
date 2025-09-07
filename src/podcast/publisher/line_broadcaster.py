"""LINE配信機能の実装"""

import logging
from typing import Dict, List, Optional
import requests
from datetime import datetime

from ...config.app_config import AppConfig
from ..assets.asset_manager import AssetManager
from ..assets.credit_inserter import CreditInserter


logger = logging.getLogger(__name__)


class LINEBroadcaster:
    """LINE Messaging APIを使用したブロードキャスト配信クラス"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.podcast_config = config.podcast
        self.line_config = config.podcast.line
        self.api_endpoint = "https://api.line.me/v2/bot/message/broadcast"

        # APIヘッダー設定
        self.headers = {
            "Authorization": f"Bearer {self.line_config.channel_access_token}",
            "Content-Type": "application/json",
        }

        # アセット管理とクレジット挿入機能を初期化
        import os

        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        self.asset_manager = AssetManager(assets_dir)
        self.credit_inserter = CreditInserter(self.asset_manager)

    def broadcast_episode(self, episode: Dict) -> bool:
        """新しいエピソードをLINEブロードキャスト配信する

        Args:
            episode: エピソード情報

        Returns:
            bool: 配信成功/失敗
        """
        try:
            message = self._create_broadcast_message(episode)

            payload = {"messages": [message]}

            response = requests.post(
                self.api_endpoint, headers=self.headers, json=payload, timeout=30
            )

            if response.status_code == 200:
                logger.info(f"LINE broadcast successful for episode: {episode['title']}")
                return True
            else:
                logger.error(f"LINE broadcast failed: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"LINE broadcast request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"LINE broadcast unexpected error: {e}")
            return False

    def _create_broadcast_message(self, episode: Dict) -> Dict:
        """ブロードキャストメッセージを作成"""
        # 音声ファイルURL（GitHub Pagesの実際の構造に合わせる）
        audio_url = f"{self.podcast_config.rss_base_url}/podcast/{episode['audio_filename']}"

        # メッセージテキスト作成
        message_text = self._create_message_text(episode, audio_url)

        # リッチメニューカード形式のメッセージ
        message = {
            "type": "flex",
            "altText": f"新しいポッドキャストエピソード: {episode['title']}",
            "contents": {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🎙️ 新しいエピソード配信",
                            "weight": "bold",
                            "color": "#1DB446",
                            "size": "sm",
                        }
                    ],
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": episode["title"],
                            "weight": "bold",
                            "size": "lg",
                            "wrap": True,
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "lg",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "spacing": "sm",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "再生時間",
                                            "color": "#aaaaaa",
                                            "size": "sm",
                                            "flex": 1,
                                        },
                                        {
                                            "type": "text",
                                            "text": episode["duration"],
                                            "wrap": True,
                                            "color": "#666666",
                                            "size": "sm",
                                            "flex": 5,
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "spacing": "sm",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "配信日",
                                            "color": "#aaaaaa",
                                            "size": "sm",
                                            "flex": 1,
                                        },
                                        {
                                            "type": "text",
                                            "text": episode["pub_date"].strftime("%Y年%m月%d日"),
                                            "wrap": True,
                                            "color": "#666666",
                                            "size": "sm",
                                            "flex": 5,
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            "type": "text",
                            "text": (
                                episode["description"][:100] + "..."
                                if len(episode["description"]) > 100
                                else episode["description"]
                            ),
                            "wrap": True,
                            "color": "#666666",
                            "size": "sm",
                            "margin": "lg",
                        },
                    ],
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "height": "sm",
                            "action": {"type": "uri", "label": "🎧 聴く", "uri": audio_url},
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "height": "sm",
                            "action": {
                                "type": "uri",
                                "label": "📱 RSS購読",
                                "uri": f"{self.podcast_config.rss_base_url}/podcast/feed.xml",
                            },
                        },
                        {
                            "type": "text",
                            "text": self.credit_inserter.get_episode_credits()["line_credits"],
                            "wrap": True,
                            "color": "#aaaaaa",
                            "size": "xs",
                            "margin": "md",
                        },
                    ],
                },
            },
        }

        return message

    def _create_message_text(self, episode: Dict, audio_url: str) -> str:
        """シンプルなテキストメッセージ作成（フォールバック用）"""
        text = f"🎙️ 新しいポッドキャストエピソード\n\n"
        text += f"【{episode['title']}】\n"
        text += f"再生時間: {episode['duration']}\n"
        text += f"配信日: {episode['pub_date'].strftime('%Y年%m月%d日')}\n\n"
        text += f"🎧 聴く: {audio_url}\n"
        text += f"📱 RSS: {self.podcast_config.rss_base_url}/podcast/feed.xml\n\n"

        # 新しいクレジット機能を使用
        credits_text = self.credit_inserter.get_episode_credits()["line_credits"]
        if credits_text:
            text += credits_text

        return text

    def send_test_message(self, user_id: str, message: str) -> bool:
        """テスト用メッセージ送信"""
        try:
            endpoint = "https://api.line.me/v2/bot/message/push"
            payload = {"to": user_id, "messages": [{"type": "text", "text": message}]}

            response = requests.post(endpoint, headers=self.headers, json=payload, timeout=30)

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Test message send failed: {e}")
            return False
