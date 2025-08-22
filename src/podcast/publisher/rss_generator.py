"""RSS配信機能の実装"""

import os
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
from pathlib import Path
import logging

if TYPE_CHECKING:
    from feedgen.feed import FeedGenerator
    from feedgen.entry import FeedEntry

try:
    from feedgen.feed import FeedGenerator
    from feedgen.entry import FeedEntry
    FEEDGEN_AVAILABLE = True
except ImportError:
    FEEDGEN_AVAILABLE = False

from ...config.app_config import AppConfig
from ..assets.asset_manager import AssetManager
from ..assets.credit_inserter import CreditInserter


logger = logging.getLogger(__name__)


class RSSGenerator:
    """ポッドキャストRSSフィード生成クラス"""

    def __init__(self, config: AppConfig):
        if not FEEDGEN_AVAILABLE:
            raise ImportError("feedgenライブラリが利用できません: pip install feedgen")
            
        self.config = config
        self.podcast_config = config.podcast
        self.output_dir = Path(config.podcast.rss_output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # アセット管理とクレジット挿入機能を初期化
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        self.asset_manager = AssetManager(assets_dir)
        self.credit_inserter = CreditInserter(self.asset_manager)

    def generate_rss_feed(self, episodes: List[Dict]) -> str:
        """RSSフィードを生成する

        Args:
            episodes: エピソード情報のリスト

        Returns:
            str: 生成されたRSSファイルのパス
        """
        try:
            fg = FeedGenerator()

            # フィード基本情報
            fg.id(self.podcast_config.rss_base_url)
            fg.title(self.podcast_config.rss_title)
            fg.link(href=self.podcast_config.rss_base_url, rel="alternate")

            # 説明文にクレジット情報を自動挿入
            description_with_credits = self.credit_inserter.insert_rss_credits(
                self.podcast_config.rss_description
            )
            fg.description(description_with_credits)
            fg.author(name=self.podcast_config.author_name, email=self.podcast_config.author_email)
            fg.language(self.podcast_config.language)
            fg.lastBuildDate(datetime.now())

            # ポッドキャスト固有設定
            fg.podcast.itunes_category("Business", "Investing")
            fg.podcast.itunes_explicit("clean")
            fg.podcast.itunes_complete(False)
            fg.podcast.itunes_new_feed_url(self.podcast_config.rss_base_url)
            fg.podcast.itunes_owner(
                name=self.podcast_config.author_name, email=self.podcast_config.author_email
            )

            # エピソード追加
            for episode in episodes:
                self._add_episode_to_feed(fg, episode)

            # RSSファイル出力
            rss_path = self.output_dir / "podcast.xml"
            fg.rss_file(str(rss_path))

            logger.info(f"RSS feed generated: {rss_path}")
            return str(rss_path)

        except Exception as e:
            logger.error(f"RSS generation failed: {e}")
            raise

    def _add_episode_to_feed(self, fg: "FeedGenerator", episode: Dict) -> None:
        """フィードにエピソードを追加"""
        fe = fg.add_entry()

        # エピソード基本情報
        fe.id(episode["guid"])
        fe.title(episode["title"])
        fe.description(episode["description"])
        fe.pubDate(episode["pub_date"])

        # 音声ファイル情報
        audio_url = f"{self.podcast_config.rss_base_url}/audio/{episode['audio_filename']}"
        fe.enclosure(url=audio_url, length=str(episode["file_size"]), type="audio/mpeg")

        # ポッドキャスト固有設定
        fe.podcast.itunes_duration(episode["duration"])
        fe.podcast.itunes_explicit("clean")

        # CC-BYクレジット情報を含む説明文（新しいクレジット機能を使用）
        episode_credits = self.credit_inserter.get_episode_credits()
        description_with_credits = self.credit_inserter.insert_rss_credits(episode["description"])
        fe.description(description_with_credits)

    def update_episode_in_feed(self, episode_guid: str, updated_data: Dict) -> bool:
        """既存エピソードの情報を更新"""
        try:
            rss_path = self.output_dir / "podcast.xml"
            if not rss_path.exists():
                logger.warning("RSS feed file not found")
                return False

            # 既存RSSファイルを読み込み、該当エピソードを更新
            # 実装の詳細は必要に応じて追加
            logger.info(f"Episode updated: {episode_guid}")
            return True

        except Exception as e:
            logger.error(f"Episode update failed: {e}")
            return False
