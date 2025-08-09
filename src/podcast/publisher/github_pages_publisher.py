# -*- coding: utf-8 -*-

"""
GitHub Pages ポッドキャスト配信機能
"""

import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from src.config.app_config import AppConfig


class GitHubPagesPublisher:
    """GitHub Pages でのポッドキャスト配信クラス"""
    
    def __init__(self, config: AppConfig, logger: logging.Logger):
        """
        初期化
        
        Args:
            config: アプリケーション設定
            logger: ロガー
        """
        self.config = config
        self.logger = logger
        self.public_dir = Path("podcast")  # GitHub Pages の公開ディレクトリ
        
    def publish_podcast_episode(self, podcast_path: str, episode_info: Dict[str, Any]) -> Optional[str]:
        """
        ポッドキャストエピソードをGitHub Pagesに配信
        
        Args:
            podcast_path: ローカルのポッドキャストファイルパス
            episode_info: エピソード情報
            
        Returns:
            Optional[str]: 公開されたポッドキャストのURL（失敗時はNone）
        """
        try:
            # 公開ディレクトリを作成
            self.public_dir.mkdir(exist_ok=True)
            
            # ファイル名を生成（日付ベース）
            source_path = Path(podcast_path)
            if not source_path.exists():
                self.logger.error(f"ポッドキャストファイルが存在しません: {podcast_path}")
                return None
            
            # 公開用ファイル名（日付ベース）
            published_at = episode_info.get('published_at', datetime.now())
            if isinstance(published_at, datetime):
                date_str = published_at.strftime('%Y%m%d')
            else:
                date_str = datetime.now().strftime('%Y%m%d')
            
            public_filename = f"market_news_{date_str}.mp3"
            public_path = self.public_dir / public_filename
            
            # ファイルをコピー
            shutil.copy2(source_path, public_path)
            self.logger.info(f"ポッドキャストファイルを公開ディレクトリにコピー: {public_path}")
            
            # 公開URLを生成
            base_url = self.config.podcast.rss_base_url.rstrip('/')
            public_url = f"{base_url}/podcast/{public_filename}"
            
            self.logger.info(f"ポッドキャスト公開URL: {public_url}")
            return public_url
            
        except Exception as e:
            self.logger.error(f"ポッドキャスト配信エラー: {e}", exc_info=True)
            return None
    
    def generate_rss_feed(self, episodes: list) -> bool:
        """
        RSS配信フィードを生成
        
        Args:
            episodes: エピソードリスト
            
        Returns:
            bool: 生成成功時True
        """
        try:
            from feedgen.feed import FeedGenerator
            
            # RSS フィードジェネレーターを初期化
            fg = FeedGenerator()
            fg.title(self.config.podcast.rss_title)
            fg.description(self.config.podcast.rss_description)
            fg.link(href=self.config.podcast.rss_base_url, rel='alternate')
            fg.language('ja')
            fg.author(name=self.config.podcast.author_name, email=self.config.podcast.author_email)
            
            # ポッドキャスト固有の設定
            fg.podcast.itunes_category('Business', 'Investing')
            fg.podcast.itunes_author(self.config.podcast.author_name)
            fg.podcast.itunes_summary(self.config.podcast.rss_description)
            fg.podcast.itunes_owner(name=self.config.podcast.author_name, email=self.config.podcast.author_email)
            fg.podcast.itunes_explicit('no')
            
            # エピソードを追加
            for episode in episodes:
                fe = fg.add_entry()
                fe.title(episode.get('title', 'マーケットニュース'))
                fe.description(episode.get('description', ''))
                fe.link(href=episode.get('url', ''))
                fe.guid(episode.get('url', ''))
                fe.pubDate(episode.get('published_at', datetime.now()))
                
                # 音声ファイルの情報
                if episode.get('audio_url'):
                    fe.enclosure(episode['audio_url'], str(episode.get('file_size', 0)), 'audio/mpeg')
            
            # RSSファイルを生成
            rss_path = self.public_dir / 'feed.xml'
            fg.rss_file(str(rss_path))
            
            self.logger.info(f"RSSフィード生成完了: {rss_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"RSSフィード生成エラー: {e}", exc_info=True)
            return False
    
    def cleanup_old_episodes(self, days_to_keep: int = 30) -> None:
        """
        古いエピソードファイルをクリーンアップ
        
        Args:
            days_to_keep: 保持する日数
        """
        try:
            if not self.public_dir.exists():
                return
            
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            deleted_count = 0
            
            for file_path in self.public_dir.glob("market_news_*.mp3"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
                    self.logger.debug(f"古いポッドキャストファイルを削除: {file_path}")
            
            if deleted_count > 0:
                self.logger.info(f"古い公開ポッドキャストファイルクリーンアップ完了 ({deleted_count}件削除)")
                
        except Exception as e:
            self.logger.warning(f"公開ポッドキャストファイルクリーンアップエラー: {e}")