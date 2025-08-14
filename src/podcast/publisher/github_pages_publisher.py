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
        self.public_dir = Path("output/podcast")  # GitHub Pages の公開ディレクトリ
        
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
            self.logger.info("feedgenライブラリのインポート開始")
            from feedgen.feed import FeedGenerator
            self.logger.info("feedgenライブラリのインポート成功")
            
            # 公開ディレクトリが存在することを確認
            self.public_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"公開ディレクトリ確認: {self.public_dir}")
            
            # RSS フィードジェネレーターを初期化
            self.logger.info("FeedGenerator初期化開始")
            fg = FeedGenerator()
            
            # 基本設定
            fg.title(self.config.podcast.rss_title or 'マーケットニュースポッドキャスト')
            fg.description(self.config.podcast.rss_description or 'AIが生成する毎日のマーケットニュース')
            fg.link(href=self.config.podcast.rss_base_url, rel='alternate')
            fg.language('ja-JP')
            fg.author(name=self.config.podcast.author_name, email=self.config.podcast.author_email)
            
            self.logger.info("基本設定完了")
            
            # ポッドキャスト固有の設定
            fg.podcast.itunes_category('Business', 'Investing')
            fg.podcast.itunes_author(self.config.podcast.author_name)
            fg.podcast.itunes_summary(self.config.podcast.rss_description or 'AIが生成する毎日のマーケットニュース')
            fg.podcast.itunes_owner(name=self.config.podcast.author_name, email=self.config.podcast.author_email)
            fg.podcast.itunes_explicit('no')
            
            self.logger.info("ポッドキャスト固有設定完了")
            
            # エピソードを追加
            for i, episode in enumerate(episodes):
                self.logger.info(f"エピソード {i+1}/{len(episodes)} 追加開始: {episode.get('title', 'タイトルなし')}")
                fe = fg.add_entry()
                fe.title(episode.get('title', 'マーケットニュース'))
                fe.description(episode.get('description', ''))
                fe.link(href=episode.get('url', ''))
                fe.guid(episode.get('url', ''), permalink=True)
                
                # published_at の処理
                published_at = episode.get('published_at', datetime.now())
                if hasattr(published_at, 'replace') and published_at.tzinfo is not None:
                    # タイムゾーン情報がある場合はそのまま使用
                    fe.pubDate(published_at)
                else:
                    # タイムゾーン情報がない場合はUTCとして扱う
                    fe.pubDate(published_at)
                
                # 音声ファイルの情報
                audio_url = episode.get('audio_url')
                file_size = episode.get('file_size', 0)
                if audio_url:
                    self.logger.info(f"エンクロージャ追加: {audio_url} ({file_size}バイト)")
                    fe.enclosure(audio_url, str(file_size), 'audio/mpeg')
                    
                self.logger.info(f"エピソード {i+1} 追加完了")
            
            # RSSファイルを生成
            rss_path = self.public_dir / 'feed.xml'
            self.logger.info(f"RSSファイル生成開始: {rss_path}")
            fg.rss_file(str(rss_path))
            
            # 生成されたファイルの確認
            if rss_path.exists():
                file_size = rss_path.stat().st_size
                self.logger.info(f"✅ RSSフィード生成完了: {rss_path} ({file_size}バイト)")
                
                # ファイルの先頭部分をログ出力（デバッグ用）
                with open(rss_path, 'r', encoding='utf-8') as f:
                    first_lines = f.read(200)
                    self.logger.info(f"RSSファイル先頭部分: {first_lines}...")
                    
                return True
            else:
                self.logger.error(f"❌ RSSファイルが生成されませんでした: {rss_path}")
                return False
            
        except ImportError as e:
            self.logger.error(f"feedgenライブラリのインポートエラー: {e}")
            return False
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