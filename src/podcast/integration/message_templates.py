# -*- coding: utf-8 -*-

"""
ポッドキャスト配信用メッセージテンプレート
音声リンクとRSS購読案内機能を含む高品質な通知システム
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging


class MessageTemplates:
    """
    ポッドキャスト配信用のメッセージテンプレート
    音声リンクとRSS購読案内機能を含む高品質な通知システム

    Features:
    - 音声ファイルへの直接リンク
    - RSS購読URL案内
    - 視覚的に魅力的なフォーマット
    - エピソード情報の詳細表示
    - ポッドキャストアプリ対応
    """

    def __init__(self, base_url: str = "https://jagar028055.github.io/Market_News"):
        self.logger = logging.getLogger(__name__)
        self.base_url = base_url.rstrip("/")
        self.rss_url = f"{self.base_url}/podcast/feed.xml"
        self.audio_base_url = f"{self.base_url}/podcast"

    def create_podcast_notification(self, episode_data: dict) -> str:
        """
        ポッドキャストエピソード通知メッセージを生成
        音声リンクとRSS購読情報を含む完全版

        Args:
            episode_data: エピソード情報辞書
                - title: エピソードタイトル
                - duration: 再生時間
                - date: 配信日
                - summary: 内容要約
                - filename: 音声ファイル名
                - file_size_mb: ファイルサイズ（MB）
                - episode_number: エピソード番号

        Returns:
            str: フォーマットされた通知メッセージ
        """
        title = episode_data.get("title", "今日のマーケットニュース")
        duration = episode_data.get("duration", "約10分")
        date = episode_data.get("date", datetime.now().strftime("%Y年%m月%d日"))
        summary = episode_data.get("summary", "本日の重要な市場動向をお届けします。")
        filename = episode_data.get("filename", "")
        file_size = episode_data.get("file_size_mb", 0)
        episode_number = episode_data.get("episode_number", 1)

        # 音声ファイルのURL生成
        audio_url = f"{self.audio_base_url}/{filename}" if filename else ""

        # ファイルサイズの表示フォーマット
        size_text = f"{file_size:.1f}MB" if file_size > 0 else "不明"

        message = f"""🎙️ マーケットニュース10分 配信開始！

━━━━━━━━━━━━━━━━━━━━━
📊 Episode #{episode_number:03d}
🏷️ {title}
📅 {date} 配信
⏱️ 再生時間: {duration}
💾 ファイルサイズ: {size_text}
━━━━━━━━━━━━━━━━━━━━━

📋 今回の内容:
{summary}

🎧 今すぐ聞く:
{audio_url}

📡 RSS購読でいつでも最新エピソードを:
{self.rss_url}

💡 ポッドキャストアプリで購読すると便利です！
   Apple Podcast、Spotify等でRSSを追加してください。

#マーケットニュース #ポッドキャスト #経済"""

        return message

    def create_error_notification(self, error_info: dict) -> str:
        """
        エラー通知メッセージを生成
        詳細なエラー情報と復旧手順を含む

        Args:
            error_info: エラー情報辞書
                - type: エラーの種類
                - timestamp: 発生時刻
                - details: エラー詳細
                - retry_count: リトライ回数
                - next_retry: 次回リトライ時刻

        Returns:
            str: エラー通知メッセージ
        """
        error_type = error_info.get("type", "不明なエラー")
        timestamp = error_info.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        details = error_info.get("details", "エラーの詳細情報はありません")
        retry_count = error_info.get("retry_count", 0)
        next_retry = error_info.get("next_retry", "")

        retry_info = ""
        if retry_count > 0:
            retry_info = f"\n🔄 リトライ回数: {retry_count}/3"
            if next_retry:
                retry_info += f"\n⏰ 次回リトライ: {next_retry}"

        message = f"""⚠️ マーケットニュース配信エラー

━━━━━━━━━━━━━━━━━━━━━
🔴 エラー種別: {error_type}
📅 発生時刻: {timestamp}{retry_info}
━━━━━━━━━━━━━━━━━━━━━

📝 エラー詳細:
{details}

🛠️ 対応状況:
- 自動復旧システムが動作中
- 次回の定期配信で再試行予定
- 問題が続く場合は手動で確認します

💬 ご不便をおかけして申し訳ございません。"""

        return message

    def create_success_notification(self, episode_data: dict, stats: dict) -> str:
        """
        配信成功通知メッセージを生成（管理者向け）

        Args:
            episode_data: エピソード情報
            stats: 配信統計情報
                - processing_time: 処理時間
                - articles_processed: 処理記事数
                - file_uploaded: アップロード成功

        Returns:
            str: 配信成功通知
        """
        episode_number = episode_data.get("episode_number", 1)
        title = episode_data.get("title", "今日のマーケットニュース")
        processing_time = stats.get("processing_time", 0)
        articles_processed = stats.get("articles_processed", 0)
        file_uploaded = stats.get("file_uploaded", False)

        upload_status = "✅ 成功" if file_uploaded else "❌ 失敗"

        message = f"""✅ ポッドキャスト配信完了

━━━━━━━━━━━━━━━━━━━━━
📊 Episode #{episode_number:03d} 配信成功
🏷️ {title}
━━━━━━━━━━━━━━━━━━━━━

📊 処理統計:
• 処理時間: {processing_time:.1f}秒
• 処理記事数: {articles_processed}件
• ファイルアップロード: {upload_status}

🔗 配信URL:
{self.audio_base_url}/{episode_data.get('filename', '')}

📡 RSS更新: ✅ 完了
📱 ポッドキャストアプリで聴取可能

システムは正常に動作しています。"""

        return message

    def create_rss_subscription_guide(self) -> str:
        """
        RSS購読案内メッセージを生成

        Returns:
            str: RSS購読案内メッセージ
        """
        message = f"""📡 ポッドキャスト RSS購読案内

━━━━━━━━━━━━━━━━━━━━━
🎙️ マーケットニュース10分
毎日の市場動向をAIが音声で解説
━━━━━━━━━━━━━━━━━━━━━

📱 購読方法:
1️⃣ お好みのポッドキャストアプリを開く
2️⃣ "RSS/URLで追加" を選択
3️⃣ 以下のURLを入力:

{self.rss_url}

🎧 対応アプリ:
• Apple Podcasts
• Spotify
• Google Podcasts
• Amazon Music
• その他RSS対応アプリ

💡 購読すると:
✅ 新エピソードの自動通知
✅ オフライン再生対応
✅ 再生履歴管理
✅ プレイリスト機能

毎日の投資判断にお役立てください！"""

        return message

    def create_daily_summary_notification(self, summary_data: dict) -> str:
        """
        日次サマリー通知を生成

        Args:
            summary_data: サマリー情報
                - total_episodes: 総エピソード数
                - total_articles: 総記事数
                - avg_sentiment: 平均センチメント
                - top_topics: 主要トピック

        Returns:
            str: 日次サマリー通知
        """
        total_episodes = summary_data.get("total_episodes", 0)
        total_articles = summary_data.get("total_articles", 0)
        avg_sentiment = summary_data.get("avg_sentiment", "中立")
        top_topics = summary_data.get("top_topics", [])

        topics_text = ""
        if top_topics:
            topics_text = "\n".join([f"• {topic}" for topic in top_topics[:3]])
        else:
            topics_text = "• データなし"

        message = f"""📊 本日のマーケットニュース配信レポート

━━━━━━━━━━━━━━━━━━━━━
📅 {datetime.now().strftime('%Y年%m月%d日')}
━━━━━━━━━━━━━━━━━━━━━

📈 配信統計:
• 配信エピソード数: {total_episodes}件
• 処理記事数: {total_articles}件
• 市場センチメント: {avg_sentiment}

🔥 主要トピック:
{topics_text}

🎙️ 本日も質の高い市場分析を
   お届けできました。

明日も継続して配信予定です。
ご視聴ありがとうございます！

📡 RSS購読: {self.rss_url}"""

        return message

    @staticmethod
    def create_podcast_notification(
        episode_info: Dict[str, Any],
        articles: List[Dict[str, Any]],
        template_type: str = "enhanced",
        base_url: str = "https://jagar028055.github.io/Market_News",
    ) -> str:
        """
        ポッドキャスト通知メッセージを作成（静的メソッド - 下位互換性）

        Args:
            episode_info: エピソード情報
            articles: 記事データ
            template_type: テンプレートタイプ
            base_url: ベースURL

        Returns:
            str: 配信メッセージ
        """
        # インスタンス作成して新しいメソッドを使用
        templates = MessageTemplates(base_url)

        # episode_infoを新しい形式に変換
        episode_data = {
            "title": episode_info.get("title", "今日のマーケットニュース"),
            "duration": f"約{templates._estimate_duration(episode_info.get('file_size_mb', 0))}分",
            "date": episode_info.get("published_at", datetime.now()).strftime("%Y年%m月%d日"),
            "summary": templates._create_summary_from_articles(articles),
            "filename": episode_info.get("filename", ""),
            "file_size_mb": episode_info.get("file_size_mb", 0),
            "episode_number": episode_info.get("episode_number", 1),
        }

        return templates.create_podcast_notification(episode_data)

    def _estimate_duration(self, file_size_mb: float) -> int:
        """再生時間推定"""
        # 概算: 1MBあたり約1.5分（128kbps MP3）
        estimated_minutes = int(file_size_mb * 1.5)
        return max(1, estimated_minutes)

    def _create_summary_from_articles(self, articles: List[Dict[str, Any]]) -> str:
        """記事から要約を生成"""
        if not articles:
            return "本日の重要な市場動向をお届けします。"

        # 上位3つの記事のタイトルから要約作成
        top_articles = articles[:3]
        highlights = []

        for article in top_articles:
            title = article.get("title", "").strip()
            if title and len(title) > 10:
                if len(title) > 40:
                    title = title[:37] + "..."
                highlights.append(title)

        if highlights:
            return "• " + "\n• ".join(highlights)
        else:
            return "本日の重要な市場動向を詳しく解説します。"
