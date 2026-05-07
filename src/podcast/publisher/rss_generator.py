"""RSS配信機能の実装

このモジュールはテストとの後方互換性を保つため、
dict形式のconfigにも対応したRSSGenerator実装を提供します。
"""

import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from pathlib import Path
from urllib.parse import urljoin

if TYPE_CHECKING:
    pass

try:
    from feedgen.feed import FeedGenerator
    from feedgen.entry import FeedEntry
    FEEDGEN_AVAILABLE = True
except ImportError:
    FeedGenerator = None  # type: ignore
    FeedEntry = None  # type: ignore
    FEEDGEN_AVAILABLE = False


logger = logging.getLogger(__name__)


class RSSPublishingError(Exception):
    """RSS配信関連のエラー"""
    pass


class GitHubPagesError(RSSPublishingError):
    """GitHub Pages関連のエラー"""
    pass


class RSSGenerator:
    """RSS配信クラス

    feedgenを使用してポッドキャストRSSフィードを生成し、
    GitHub Pagesで公開します。dict形式のconfigとAppConfig形式の
    両方に対応しています。
    """

    def __init__(self, config: Any):
        """初期化

        Args:
            config: RSS配信設定（dict または AppConfig インスタンス）

        Raises:
            RSSPublishingError: feedgenライブラリが未インストールの場合
        """
        # テストが src.podcast.publisher.FEEDGEN_AVAILABLE をパッチする場合に対応するため
        # 親パッケージの変数も確認する
        import sys as _sys
        _parent_mod = _sys.modules.get("src.podcast.publisher")
        _feedgen_ok = FEEDGEN_AVAILABLE
        if _parent_mod is not None:
            _feedgen_ok = getattr(_parent_mod, "FEEDGEN_AVAILABLE", FEEDGEN_AVAILABLE)
        if not _feedgen_ok:
            raise RSSPublishingError("feedgenライブラリが必要です: pip install feedgen>=0.9.0")

        self.logger = logging.getLogger(__name__)

        # dict と AppConfig の両方に対応
        if isinstance(config, dict):
            self.config = config
            self.rss_title = config.get("rss_title", "マーケットニュース10分")
            self.rss_description = config.get("rss_description", "AIが生成する毎日のマーケットニュース")
            self.rss_link = config.get("rss_link", "https://example.github.io/podcast/")
            self.rss_language = config.get("rss_language", "ja-JP")
            self.rss_author = config.get("rss_author", "AI Market News")
            self.rss_email = config.get("rss_email", "noreply@example.com")
            self.rss_category = config.get("rss_category", "Business")
            self.rss_image_url = config.get("rss_image_url", "")
            self.github_pages_url = config.get("github_pages_url", "")
            self.github_repo_path = config.get("github_repo_path", "")
            self.audio_base_url = config.get(
                "audio_base_url",
                urljoin(self.github_pages_url, "podcast/audio/") if self.github_pages_url else ""
            )
            self.rss_output_path = config.get("rss_output_path", "podcast/feed.xml")
            self.episodes_data_path = config.get("episodes_data_path", "podcast/episodes.json")
            self.max_episodes = config.get("max_episodes", 50)
        else:
            # AppConfig インスタンス
            self.config = config
            podcast = config.podcast
            self.rss_title = getattr(podcast, "rss_title", "マーケットニュース10分")
            self.rss_description = getattr(podcast, "rss_description", "AIが生成する毎日のマーケットニュース")
            self.rss_link = getattr(podcast, "rss_base_url", "https://example.github.io/podcast/")
            self.rss_language = getattr(podcast, "language", "ja-JP")
            self.rss_author = getattr(podcast, "author_name", "AI Market News")
            self.rss_email = getattr(podcast, "author_email", "noreply@example.com")
            self.rss_category = "Business"
            self.rss_image_url = ""
            self.github_pages_url = getattr(podcast, "rss_base_url", "")
            self.github_repo_path = ""
            self.audio_base_url = ""
            self.rss_output_path = getattr(podcast, "rss_output_dir", "podcast") + "/feed.xml"
            self.episodes_data_path = getattr(podcast, "rss_output_dir", "podcast") + "/episodes.json"
            self.max_episodes = 50

        self.logger.info("RSSGenerator初期化完了")

    def publish(self, episode: Any, credits: str) -> Any:
        """RSSフィードを生成・公開

        Args:
            episode: ポッドキャストエピソード (PodcastEpisode)
            credits: CC-BYクレジット情報

        Returns:
            PublishResult: 配信結果
        """
        # PublishResult をインポート（循環インポート回避のため遅延）
        try:
            from src.podcast.publisher import PublishResult
        except Exception:
            # フォールバック: 単純なオブジェクトを作成
            class PublishResult:  # type: ignore
                def __init__(self, channel, success, message, url=None):
                    self.channel = channel
                    self.success = success
                    self.message = message
                    self.url = url

        try:
            self.logger.info(f"RSS配信を開始: {episode.title}")

            # 1. 音声ファイルをGitHub Pagesにアップロード
            audio_url = self._upload_audio_file(episode)

            # 2. エピソードデータを更新
            self._update_episodes_data(episode, audio_url, credits)

            # 3. RSSフィードを生成
            rss_content = self._generate_rss_feed(credits)

            # 4. RSSファイルをGitHub Pagesに配信
            rss_url = self._deploy_rss_feed(rss_content)

            self.logger.info(f"RSS配信完了: {rss_url}")
            return PublishResult(
                channel="RSS",
                success=True,
                message="RSS配信が正常に完了しました",
                url=rss_url
            )

        except Exception as e:
            self.logger.error(f"RSS配信に失敗: {str(e)}")
            return PublishResult(
                channel="RSS",
                success=False,
                message=f"RSS配信エラー: {str(e)}",
                url=None
            )

    def _upload_audio_file(self, episode: Any) -> str:
        """音声ファイルをGitHub Pagesにアップロード

        Args:
            episode: ポッドキャストエピソード

        Returns:
            アップロードされた音声ファイルのURL

        Raises:
            GitHubPagesError: アップロードに失敗した場合
        """
        try:
            audio_file_path = Path(episode.audio_file_path)
            if not audio_file_path.exists():
                raise GitHubPagesError(f"音声ファイルが見つかりません: {audio_file_path}")

            file_extension = audio_file_path.suffix
            audio_filename = (
                f"episode_{episode.episode_number:03d}_"
                f"{episode.publish_date.strftime('%Y%m%d')}{file_extension}"
            )

            if self.github_repo_path:
                audio_dest_path = (
                    Path(self.github_repo_path) / "podcast" / "audio" / audio_filename
                )
                audio_dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(audio_file_path, audio_dest_path)
                self.logger.info(f"音声ファイルをコピー: {audio_dest_path}")
                audio_url = urljoin(self.github_pages_url, f"podcast/audio/{audio_filename}")
            else:
                audio_url = urljoin(self.audio_base_url, audio_filename)
                self.logger.warning("GitHub APIアップロードは未実装、URLのみ生成")

            return audio_url

        except GitHubPagesError:
            raise
        except Exception as e:
            raise GitHubPagesError(f"音声ファイルアップロードエラー: {str(e)}")

    def _update_episodes_data(self, episode: Any, audio_url: str, credits: str) -> None:
        """エピソードデータを更新

        Args:
            episode: ポッドキャストエピソード
            audio_url: 音声ファイルURL
            credits: クレジット情報
        """
        episodes_data_file = (
            Path(self.github_repo_path) / self.episodes_data_path
            if self.github_repo_path
            else Path(self.episodes_data_path)
        )
        episodes_data_file.parent.mkdir(parents=True, exist_ok=True)

        episodes: List[Dict] = []
        if episodes_data_file.exists():
            try:
                with open(episodes_data_file, "r", encoding="utf-8") as f:
                    episodes = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                episodes = []

        episode_data = {
            "episode_number": episode.episode_number,
            "title": episode.title,
            "description": episode.description,
            "audio_url": audio_url,
            "duration_seconds": episode.duration_seconds,
            "file_size_bytes": episode.file_size_bytes,
            "publish_date": episode.publish_date.isoformat(),
            "guid": episode.get_episode_guid(),
            "transcript": episode.transcript,
            "credits": credits,
            "source_articles": episode.source_articles,
        }

        updated = False
        for i, existing in enumerate(episodes):
            if existing["episode_number"] == episode.episode_number:
                episodes[i] = episode_data
                updated = True
                break

        if not updated:
            episodes.append(episode_data)

        episodes.sort(key=lambda x: x["episode_number"], reverse=True)

        if len(episodes) > self.max_episodes:
            episodes = episodes[: self.max_episodes]

        with open(episodes_data_file, "w", encoding="utf-8") as f:
            json.dump(episodes, f, ensure_ascii=False, indent=2)

        self.logger.info(f"エピソードデータを更新: {len(episodes)}エピソード")

    def _generate_rss_feed(self, credits: str) -> str:
        """RSSフィードを生成

        Args:
            credits: クレジット情報

        Returns:
            RSS XML文字列
        """
        episodes_data_file = (
            Path(self.github_repo_path) / self.episodes_data_path
            if self.github_repo_path
            else Path(self.episodes_data_path)
        )
        episodes: List[Dict] = []
        if episodes_data_file.exists():
            with open(episodes_data_file, "r", encoding="utf-8") as f:
                episodes = json.load(f)

        # テストが src.podcast.publisher.FeedGenerator をパッチする場合に対応
        import sys as _sys
        _parent_mod = _sys.modules.get("src.podcast.publisher")
        _FG = FeedGenerator
        if _parent_mod is not None:
            _FG = getattr(_parent_mod, "FeedGenerator", FeedGenerator)
        if _FG is None:
            raise RSSPublishingError("feedgenライブラリが必要です")

        fg = _FG()

        fg.id(self.rss_link)
        fg.title(self.rss_title)
        fg.link(href=self.rss_link, rel="alternate")
        fg.description(self.rss_description)
        fg.author(name=self.rss_author, email=self.rss_email)
        fg.language(self.rss_language)
        fg.copyright(f"© {datetime.now().year} {self.rss_author}")
        fg.generator("AI Market News Podcast Generator")

        fg.podcast.itunes_category("Business", "Investing")
        fg.podcast.itunes_author(self.rss_author)
        fg.podcast.itunes_summary(self.rss_description)
        fg.podcast.itunes_owner(name=self.rss_author, email=self.rss_email)
        fg.podcast.itunes_explicit("no")

        if self.rss_image_url:
            fg.podcast.itunes_image(self.rss_image_url)
            fg.image(url=self.rss_image_url, title=self.rss_title, link=self.rss_link)

        for episode_data in episodes:
            fe = fg.add_entry()
            episode_url = urljoin(self.rss_link, f"episode/{episode_data['episode_number']}")
            fe.id(episode_url)
            fe.title(episode_data["title"])
            fe.link(href=episode_url)

            description_with_credits = (
                f"{episode_data['description']}\n\n{episode_data.get('credits', credits)}"
            )
            fe.description(description_with_credits)

            publish_date = datetime.fromisoformat(episode_data["publish_date"])
            if publish_date.tzinfo is None:
                publish_date = publish_date.replace(tzinfo=timezone.utc)
            fe.pubDate(publish_date)

            fe.enclosure(
                url=episode_data["audio_url"],
                length=str(episode_data["file_size_bytes"]),
                type="audio/mpeg",
            )

            fe.podcast.itunes_duration(self._format_duration(episode_data["duration_seconds"]))
            fe.podcast.itunes_explicit("no")
            fe.podcast.itunes_summary(description_with_credits)
            fe.guid(episode_data["guid"], permalink=False)

        rss_str = fg.rss_str(pretty=True).decode("utf-8")
        self.logger.info(f"RSSフィード生成完了: {len(episodes)}エピソード")
        return rss_str

    def _deploy_rss_feed(self, rss_content: str) -> str:
        """RSSフィードをGitHub Pagesに配信

        Args:
            rss_content: RSS XML文字列

        Returns:
            配信されたRSSフィードのURL

        Raises:
            GitHubPagesError: 配信に失敗した場合
        """
        try:
            if self.github_repo_path:
                rss_file_path = Path(self.github_repo_path) / self.rss_output_path
                rss_file_path.parent.mkdir(parents=True, exist_ok=True)

                with open(rss_file_path, "w", encoding="utf-8") as f:
                    f.write(rss_content)

                self.logger.info(f"RSSファイルを保存: {rss_file_path}")
                self._git_commit_and_push()
                rss_url = urljoin(self.github_pages_url, self.rss_output_path)
            else:
                rss_url = urljoin(self.github_pages_url, self.rss_output_path)
                self.logger.warning("GitHub API配信は未実装、URLのみ生成")

            return rss_url

        except GitHubPagesError:
            raise
        except Exception as e:
            raise GitHubPagesError(f"RSS配信エラー: {str(e)}")

    def _git_commit_and_push(self) -> None:
        """Gitリポジトリにコミット・プッシュ

        Raises:
            GitHubPagesError: Git操作に失敗した場合
        """
        if not self.github_repo_path:
            return

        repo_path = Path(self.github_repo_path)
        commands = [
            ["git", "add", "podcast/"],
            [
                "git",
                "commit",
                "-m",
                f'Update podcast feed - {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            ],
            ["git", "push", "origin", "main"],
        ]

        for cmd in commands:
            result = subprocess.run(
                cmd, cwd=repo_path, capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                if "nothing to commit" in result.stdout:
                    self.logger.info("変更がないためコミットをスキップ")
                    return
                else:
                    raise GitHubPagesError(
                        f"Git操作失敗: {' '.join(cmd)}\n{result.stderr}"
                    )

        self.logger.info("Git操作完了: コミット・プッシュ成功")

    def _format_duration(self, duration_seconds: int) -> str:
        """再生時間をiTunes形式でフォーマット

        Args:
            duration_seconds: 再生時間（秒）

        Returns:
            フォーマットされた再生時間
        """
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def get_rss_url(self) -> str:
        """RSSフィードのURLを取得

        Returns:
            RSSフィードURL
        """
        return urljoin(self.github_pages_url, self.rss_output_path)
