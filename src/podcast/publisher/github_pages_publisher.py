# -*- coding: utf-8 -*-

"""
GitHub Pages ポッドキャスト配信機能
"""

import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from feedgen.feed import FeedGenerator

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

    def publish_podcast_episode(
        self, podcast_path: str, episode_info: Dict[str, Any]
    ) -> Optional[str]:
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
            published_at = episode_info.get("published_at", datetime.now())
            if isinstance(published_at, datetime):
                date_str = published_at.strftime("%Y%m%d")
            else:
                date_str = datetime.now().strftime("%Y%m%d")

            public_filename = f"market_news_{date_str}.mp3"
            public_path = self.public_dir / public_filename

            # ファイルをコピー（ファイル名を統一）
            shutil.copy2(source_path, public_path)
            self.logger.info(
                f"ポッドキャストファイルコピー: {source_path.name} → {public_filename}"
            )
            self.logger.info(f"公開ディレクトリ: {public_path}")

            # 公開URLを生成
            base_url = self.config.podcast.rss_base_url.rstrip("/")
            public_url = f"{base_url}/podcast/{public_filename}"

            self.logger.info(f"ポッドキャスト公開URL: {public_url}")

            # ファイル名統一の確認ログ
            if source_path.name != public_filename:
                self.logger.info(
                    f"ファイル名変更: {source_path.name} → {public_filename} (日付ベースに統一)"
                )

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
            # RSS フィードジェネレーターを初期化
            self.logger.info("FeedGenerator初期化開始")
            fg = FeedGenerator()
            fg.title(self.config.podcast.rss_title)
            fg.description(self.config.podcast.rss_description)
            fg.link(href=self.config.podcast.rss_base_url, rel="alternate")
            fg.language("ja")
            fg.author(name=self.config.podcast.author_name, email=self.config.podcast.author_email)

            # ポッドキャスト拡張を明示的に読み込み
            self.logger.info("ポッドキャスト拡張を初期化中")
            try:
                fg.load_extension('podcast')
                self.logger.info("ポッドキャスト拡張読み込み成功")
            except Exception as e:
                self.logger.warning(f"ポッドキャスト拡張読み込み失敗: {e}")
                # フォールバックは使わず、基本的なpodcast属性アクセスを試行
                try:
                    # podcast属性が使用可能か確認
                    _ = fg.podcast
                    self.logger.info("podcast属性は既に利用可能です")
                except AttributeError:
                    self.logger.error("podcast拡張が利用できません。feedgen[podcast]がインストールされていない可能性があります")
                    raise
            
            # ポッドキャスト固有の設定
            fg.podcast.itunes_category("Business", "Investing")
            fg.podcast.itunes_author(self.config.podcast.author_name)
            fg.podcast.itunes_summary(self.config.podcast.rss_description)
            fg.podcast.itunes_owner(
                name=self.config.podcast.author_name, email=self.config.podcast.author_email
            )
            fg.podcast.itunes_explicit("no")

            # エピソードを追加
            for i, episode in enumerate(episodes):
                self.logger.info(f"エピソード {i+1}/{len(episodes)} 追加開始: {episode.get('title', 'タイトルなし')}")
                fe = fg.add_entry()
                fe.title(episode.get("title", "マーケットニュース"))
                fe.description(episode.get("description", ""))
                fe.link(href=episode.get("url", ""))
                fe.guid(episode.get("url", ""))
                fe.pubDate(episode.get("published_at", datetime.now()))

                # 音声ファイルの情報
                if episode.get("audio_url"):
                    fe.enclosure(
                        episode["audio_url"], str(episode.get("file_size", 0)), "audio/mpeg"
                    )

            # RSSファイルを生成
            rss_path = self.public_dir / "feed.xml"
            fg.rss_file(str(rss_path))

            self.logger.info(f"RSSフィード生成完了: {rss_path}")
            
            # ポッドキャストディレクトリのindex.htmlを生成
            self._generate_podcast_index(episodes)
            
            return True

        except Exception as e:
            self.logger.error(f"RSSフィード生成エラー: {e}", exc_info=True)
            return False

    def _generate_podcast_index(self, episodes: list) -> None:
        """
        ポッドキャストディレクトリのindex.htmlを生成
        
        Args:
            episodes: エピソードリスト
        """
        try:
            index_path = self.public_dir / "index.html"
            
            html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.podcast.rss_title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 800px; margin: 0 auto; padding: 20px; }}
        .episode {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 8px; }}
        .audio {{ margin: 10px 0; }}
        .rss-link {{ background: #007bff; color: white; padding: 10px 20px; 
                     text-decoration: none; border-radius: 5px; display: inline-block; }}
    </style>
</head>
<body>
    <h1>{self.config.podcast.rss_title}</h1>
    <p>{self.config.podcast.rss_description}</p>
    
    <p><a href="feed.xml" class="rss-link">RSS フィード</a></p>
    
    <h2>エピソード一覧</h2>
"""
            
            for episode in episodes:
                episode_date = episode.get('published_at', datetime.now())
                if isinstance(episode_date, datetime):
                    date_str = episode_date.strftime('%Y年%m月%d日')
                else:
                    date_str = str(episode_date)
                    
                html_content += f"""
    <div class="episode">
        <h3>{episode.get('title', 'マーケットニュース')}</h3>
        <p><strong>配信日:</strong> {date_str}</p>
        <p>{episode.get('description', '')}</p>
        <div class="audio">
            <audio controls>
                <source src="{episode.get('audio_url', '')}" type="audio/mpeg">
                お使いのブラウザは音声再生に対応していません。
            </audio>
        </div>
    </div>
"""
            
            html_content += """
</body>
</html>"""
            
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            self.logger.info(f"ポッドキャストindex.html生成完了: {index_path}")
            
        except Exception as e:
            self.logger.error(f"index.html生成エラー: {e}", exc_info=True)

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
                self.logger.info(
                    f"古い公開ポッドキャストファイルクリーンアップ完了 ({deleted_count}件削除)"
                )

        except Exception as e:
            self.logger.warning(f"公開ポッドキャストファイルクリーンアップエラー: {e}")

    def run_diagnostics(self) -> Dict[str, Any]:
        """
        ログ診断機能
        
        Returns:
            Dict[str, Any]: 診断結果
        """
        try:
            diagnostic_results = {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "checks": {}
            }
            
            # ディレクトリの存在確認
            diagnostic_results["checks"]["public_directory"] = {
                "exists": self.public_dir.exists(),
                "path": str(self.public_dir),
                "is_directory": self.public_dir.is_dir() if self.public_dir.exists() else False
            }
            
            # 設定チェック
            diagnostic_results["checks"]["configuration"] = {
                "rss_base_url": getattr(self.config.podcast, 'rss_base_url', 'not_configured'),
                "rss_title": getattr(self.config.podcast, 'rss_title', 'not_configured'),
                "author_name": getattr(self.config.podcast, 'author_name', 'not_configured')
            }
            
            # ファイル一覧
            if self.public_dir.exists():
                mp3_files = list(self.public_dir.glob("market_news_*.mp3"))
                diagnostic_results["checks"]["podcast_files"] = {
                    "count": len(mp3_files),
                    "files": [f.name for f in mp3_files[:5]]  # 最新5件のみ表示
                }
                
                # RSSフィードの存在確認
                rss_path = self.public_dir / "feed.xml"
                diagnostic_results["checks"]["rss_feed"] = {
                    "exists": rss_path.exists(),
                    "path": str(rss_path),
                    "size": rss_path.stat().st_size if rss_path.exists() else 0
                }
            else:
                diagnostic_results["checks"]["podcast_files"] = {"count": 0, "files": []}
                diagnostic_results["checks"]["rss_feed"] = {"exists": False}
            
            self.logger.info(f"診断実行完了: {diagnostic_results}")
            return diagnostic_results
            
        except Exception as e:
            error_result = {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "error_type": type(e).__name__
            }
            self.logger.error(f"診断実行エラー: {error_result}", exc_info=True)
            return error_result
