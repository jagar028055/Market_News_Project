# -*- coding: utf-8 -*-

"""
LINE配信機能
ポッドキャスト通知をLINE Messaging APIで配信
"""

import json
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging
import pytz

from typing import Optional
from src.config.app_config import AppConfig
from src.podcast.integration.exceptions import BroadcastError


class LineBroadcaster:
    """
    LINE配信クラス

    ポッドキャスト通知をLINE Messaging APIのブロードキャスト機能で配信
    """

    def __init__(self, config: AppConfig, logger: logging.Logger):
        """
        初期化

        Args:
            config: アプリケーション設定
            logger: ロガー
        """
        self.config = config
        self.logger = logger
        self.api_base_url = "https://api.line.me/v2/bot"

        # リトライ設定
        self.max_retries = 3
        self.retry_delay = 2  # 秒

    def broadcast_podcast_notification(
        self,
        episode_info: Dict[str, Any],
        articles: List[Dict[str, Any]],
        audio_url: Optional[str] = None,
    ) -> bool:
        """
        ポッドキャスト通知をブロードキャスト配信

        Args:
            episode_info: エピソード情報
            articles: 記事データ（メッセージ作成用）
            audio_url: 音声ファイルの公開URL（オプション）

        Returns:
            bool: 配信成功時True
        """
        try:
            self.logger.info("LINE配信開始")

            # メッセージを作成
            message = self._create_podcast_message(episode_info, articles, audio_url)

            # ブロードキャスト配信実行
            success = self._send_broadcast_message(message)

            if success:
                self.logger.info("LINE配信成功")
                return True
            else:
                self.logger.error("LINE配信失敗")
                return False

        except Exception as e:
            self.logger.error(f"LINE配信エラー: {e}", exc_info=True)
            return False

    def _create_podcast_message(
        self,
        episode_info: Dict[str, Any],
        articles: List[Dict[str, Any]],
        audio_url: Optional[str] = None,
    ) -> str:
        """
        ポッドキャスト通知メッセージを作成

        Args:
            episode_info: エピソード情報
            articles: 記事データ
            audio_url: 音声ファイルの公開URL（オプション）

        Returns:
            str: 配信メッセージ
        """
        # 基本情報
        published_at = episode_info.get("published_at", datetime.now())
        file_size_mb = episode_info.get("file_size_mb", 0)
        article_count = episode_info.get("article_count", 0)

        # 日時フォーマット（日本時間に変換）
        jst = pytz.timezone('Asia/Tokyo')
        if isinstance(published_at, datetime):
            # UTCタイムゾーンが設定されていない場合は設定
            if published_at.tzinfo is None:
                published_at = pytz.utc.localize(published_at)
            # 日本時間に変換
            jst_time = published_at.astimezone(jst)
            date_str = jst_time.strftime("%Y年%m月%d日 %H:%M")
        else:
            # 現在時刻を日本時間で取得
            jst_time = datetime.now(jst)
            date_str = jst_time.strftime("%Y年%m月%d日 %H:%M")

        # 主要記事のハイライト作成
        highlights = self._create_article_highlights(articles)

        # メッセージ組み立て（本番用）
        message_parts = [
            "🎙️ マーケットニュースポッドキャスト",
            "",
            f"📅 {date_str} 配信",
            "",
            "📊 本日のハイライト：",
        ]

        # ハイライト追加
        for highlight in highlights:
            message_parts.append(f"• {highlight}")

        message_parts.extend(
            [
                "",
                f"⏱️ 再生時間: 約{self._estimate_duration(file_size_mb)}分",
                f"💾 ファイルサイズ: {file_size_mb:.1f}MB",
                f"📰 記事数: {article_count}件",
                "",
            ]
        )

        # 音声ファイルのリンクを追加
        if audio_url:
            message_parts.extend(
                [
                    "🎧 ポッドキャストを聞く:",
                    f"🔗 {audio_url}",
                    "",
                    "📱 ポッドキャストアプリでも購読可能:",
                    f"📡 RSS: {self.config.podcast.rss_base_url}/podcast/feed.xml",
                    "",
                ]
            )
        else:
            message_parts.extend(["🎧 AIが生成した高品質ポッドキャストをお楽しみください！", ""])

        # ハッシュタグ（本番用）
        message_parts.append("#マーケットニュース #ポッドキャスト #AI #投資")

        return "\n".join(message_parts)

    def _create_article_highlights(
        self, articles: List[Dict[str, Any]], max_highlights: int = 3
    ) -> List[str]:
        """
        記事のハイライトを作成

        Args:
            articles: 記事データ
            max_highlights: 最大ハイライト数

        Returns:
            List[str]: ハイライトリスト
        """
        highlights = []

        # 記事が存在する場合
        if articles:
            # センチメント別に記事を分類
            positive_articles = [a for a in articles if a.get("sentiment_label") == "Positive"]
            negative_articles = [a for a in articles if a.get("sentiment_label") == "Negative"]
            neutral_articles = [a for a in articles if a.get("sentiment_label") == "Neutral"]

            # 優先順位: Positive > Negative > Neutral
            priority_articles = positive_articles + negative_articles + neutral_articles
            
            # 記事がない場合は全記事から選択
            if not priority_articles:
                priority_articles = articles

            for article in priority_articles[:max_highlights]:
                title = article.get("title", "")
                if title:
                    # タイトルを短縮（45文字以内でより読みやすく）
                    if len(title) > 45:
                        title = title[:42] + "..."
                    highlights.append(title)

        # ハイライトが少ない場合のフォールバック（具体的な内容に変更）
        if not highlights:
            highlights = [
                "日経平均・為替レートの最新動向",
                "FRB・日銀の金融政策分析", 
                "主要企業の業績・投資判断"
            ]

        return highlights

    def _estimate_duration(self, file_size_mb: float) -> int:
        """
        ファイルサイズから再生時間を推定

        Args:
            file_size_mb: ファイルサイズ（MB）

        Returns:
            int: 推定再生時間（分）
        """
        # 概算: 1MBあたり約1.5分（128kbps MP3の場合）
        estimated_minutes = int(file_size_mb * 1.5)
        return max(1, estimated_minutes)  # 最低1分

    def _send_broadcast_message(self, message: str) -> bool:
        """
        ブロードキャストメッセージを送信

        Args:
            message: 送信メッセージ

        Returns:
            bool: 送信成功時True
        """
        url = f"{self.api_base_url}/message/broadcast"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.line.channel_access_token}",
        }

        data = {"messages": [{"type": "text", "text": message}]}

        # リトライ付きで送信
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"LINE API呼び出し (試行 {attempt + 1}/{self.max_retries})")

                response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)

                if response.status_code == 200:
                    self.logger.info(f"LINE配信成功 (ステータス: {response.status_code})")

                    # レスポンス情報をログ出力
                    if "X-Line-Request-Id" in response.headers:
                        self.logger.info(f"リクエストID: {response.headers['X-Line-Request-Id']}")

                    return True

                else:
                    self.logger.warning(
                        f"LINE API エラー (試行 {attempt + 1}): ステータス {response.status_code}, レスポンス: {response.text}"
                    )

                    # 特定のエラーコードの場合はリトライしない
                    if response.status_code in [400, 401, 403]:
                        self._log_api_error(response.status_code, response.text)
                        return False

            except requests.exceptions.Timeout:
                self.logger.warning(f"LINE API タイムアウト (試行 {attempt + 1})")
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"LINE API リクエストエラー (試行 {attempt + 1}): {e}")
            except Exception as e:
                self.logger.error(f"LINE API 予期しないエラー (試行 {attempt + 1}): {e}")

            # 最後の試行でない場合は待機
            if attempt < self.max_retries - 1:
                self.logger.info(f"{self.retry_delay}秒後にリトライします...")
                time.sleep(self.retry_delay)

        self.logger.error(f"LINE配信失敗: {self.max_retries}回の試行すべてが失敗")
        return False

    def _log_api_error(self, status_code: int, response_text: str) -> None:
        """
        API エラーの詳細をログ出力

        Args:
            status_code: HTTPステータスコード
            response_text: レスポンステキスト
        """
        error_messages = {
            400: "リクエストエラー: メッセージ形式を確認してください",
            401: "認証エラー: アクセストークンを確認してください",
            403: "権限エラー: Bot設定を確認してください",
            429: "レート制限エラー: しばらく待ってからリトライしてください",
            500: "LINE API サーバーエラー: しばらく待ってからリトライしてください",
        }

        error_hint = error_messages.get(status_code, "不明なエラー")
        self.logger.error(f"LINE API エラー詳細: {error_hint}")
        self.logger.error(f"ステータスコード: {status_code}")
        self.logger.error(f"レスポンス: {response_text}")

    def test_connection(self) -> bool:
        """
        LINE API接続テスト

        Returns:
            bool: 接続成功時True
        """
        try:
            url = f"{self.api_base_url}/info"
            headers = {"Authorization": f"Bearer {self.config.line.channel_access_token}"}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                bot_info = response.json()
                self.logger.info(
                    f"LINE Bot接続テスト成功: {bot_info.get('displayName', 'Unknown')}"
                )
                return True
            else:
                self.logger.error(f"LINE Bot接続テスト失敗: ステータス {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"LINE Bot接続テストエラー: {e}")
            return False
