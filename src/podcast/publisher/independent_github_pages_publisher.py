# -*- coding: utf-8 -*-

"""
独立GitHub Pagesポッドキャスト配信機能
既存システムから完全に分離された独立配信システム
"""

import os
import shutil
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import hashlib


class IndependentGitHubPagesPublisher:
    """
    独立GitHub Pages ポッドキャスト配信クラス

    機能:
    - 独立したファイル管理
    - GitHub Pages自動デプロイ
    - RSS フィード自動生成
    - メタデータ管理
    """

    DEFAULT_CONFIG = {
        "output_dir": "output/podcast-pages",
        "audio_dir": "audio",
        "rss_filename": "feed.xml",  # GitHub Pagesと統一
        "max_episodes": 50,
        "days_to_keep": 30,
        "commit_message_template": "🎙️ Update podcast episode: {title}",
        "branch": "gh-pages",
    }

    def __init__(
        self,
        github_repo_url: str,
        base_url: str,
        podcast_info: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初期化

        Args:
            github_repo_url: GitHubリポジトリURL
            base_url: 配信ベースURL (https://username.github.io/repo)
            podcast_info: ポッドキャスト情報
            config: 設定（オプション）
        """
        self.github_repo_url = github_repo_url
        self.base_url = base_url.rstrip("/")
        self.podcast_info = podcast_info

        # 設定統合
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)

        self.logger = logging.getLogger(__name__)

        # ディレクトリ設定
        self.output_dir = Path(self.config["output_dir"])
        self.audio_dir = self.output_dir / self.config["audio_dir"]

        # エピソード管理ファイル
        self.episodes_db = self.output_dir / "episodes.json"

        # 初期化
        self._initialize_directories()

    def _initialize_directories(self) -> None:
        """ディレクトリとファイルの初期化"""
        try:
            # 必要なディレクトリを作成
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.audio_dir.mkdir(parents=True, exist_ok=True)

            # エピソードDBの初期化
            if not self.episodes_db.exists():
                self._save_episodes_db([])

            self.logger.info(f"独立配信システム初期化完了 - 出力: {self.output_dir}")

        except Exception as e:
            self.logger.error(f"ディレクトリ初期化エラー: {e}")
            raise

    def publish_episode(self, audio_file: Path, episode_metadata: Dict[str, Any]) -> Optional[str]:
        """
        エピソードを配信

        Args:
            audio_file: 音声ファイルパス
            episode_metadata: エピソードメタデータ

        Returns:
            Optional[str]: 配信URL（失敗時はNone）
        """
        if not audio_file.exists():
            self.logger.error(f"音声ファイルが見つかりません: {audio_file}")
            return None

        self.logger.info(f"エピソード配信開始: {episode_metadata.get('title', '未設定')}")

        try:
            # エピソードIDを生成
            episode_id = self._generate_episode_id(episode_metadata)

            # 音声ファイルをコピー
            audio_filename = f"{episode_id}.mp3"
            target_audio_path = self.audio_dir / audio_filename
            shutil.copy2(audio_file, target_audio_path)

            # 配信URL生成
            audio_url = f"{self.base_url}/{self.config['audio_dir']}/{audio_filename}"

            # エピソード情報を作成
            episode_info = self._create_episode_info(
                episode_id,
                audio_filename,
                audio_url,
                target_audio_path.stat().st_size,
                episode_metadata,
            )

            # エピソードDB更新
            self._add_episode_to_db(episode_info)

            # RSS フィード更新
            self._generate_rss_feed()

            # GitHub Pages にデプロイ
            if self._deploy_to_github_pages(episode_info):
                self.logger.info(f"エピソード配信完了: {audio_url}")
                return audio_url
            else:
                self.logger.error("GitHub Pages配信に失敗しました")
                return None

        except Exception as e:
            self.logger.error(f"エピソード配信エラー: {e}")
            return None

    def _generate_episode_id(self, metadata: Dict[str, Any]) -> str:
        """
        エピソードIDを生成

        Args:
            metadata: エピソードメタデータ

        Returns:
            str: 一意のエピソードID
        """
        # 日付ベースのID生成
        published_date = metadata.get("published_date", datetime.now())
        if isinstance(published_date, str):
            # 文字列の場合は現在日時を使用
            published_date = datetime.now()
        elif not isinstance(published_date, datetime):
            published_date = datetime.now()

        date_str = published_date.strftime("%Y%m%d_%H%M")

        # タイトルのハッシュを追加（一意性確保）
        title = metadata.get("title", "episode")
        title_hash = hashlib.md5(title.encode("utf-8")).hexdigest()[:8]

        return f"episode_{date_str}_{title_hash}"

    def _create_episode_info(
        self,
        episode_id: str,
        audio_filename: str,
        audio_url: str,
        file_size: int,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        エピソード情報を作成

        Args:
            episode_id: エピソードID
            audio_filename: 音声ファイル名
            audio_url: 配信URL
            file_size: ファイルサイズ
            metadata: メタデータ

        Returns:
            Dict[str, Any]: エピソード情報
        """
        return {
            "id": episode_id,
            "title": metadata.get("title", f'Market News {datetime.now().strftime("%Y-%m-%d")}'),
            "description": metadata.get("description", "Daily market news podcast"),
            "published_date": metadata.get("published_date", datetime.now()).isoformat(),
            "audio_filename": audio_filename,
            "audio_url": audio_url,
            "file_size": file_size,
            "duration": metadata.get("duration", "00:10:00"),  # デフォルト10分
            "episode_number": metadata.get("episode_number"),
            "season": metadata.get("season", 1),
            "keywords": metadata.get("keywords", ["market", "news", "finance", "japan"]),
            "created_at": datetime.now().isoformat(),
        }

    def _load_episodes_db(self) -> List[Dict[str, Any]]:
        """エピソードDBをロード"""
        try:
            if self.episodes_db.exists():
                with open(self.episodes_db, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.warning(f"エピソードDB読み込みエラー: {e}")
            return []

    def _save_episodes_db(self, episodes: List[Dict[str, Any]]) -> None:
        """エピソードDBを保存"""
        try:
            with open(self.episodes_db, "w", encoding="utf-8") as f:
                json.dump(episodes, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"エピソードDB保存エラー: {e}")
            raise

    def _add_episode_to_db(self, episode_info: Dict[str, Any]) -> None:
        """エピソードDBに追加"""
        episodes = self._load_episodes_db()

        # 既存エピソードの重複チェック
        episode_ids = [ep["id"] for ep in episodes]
        if episode_info["id"] in episode_ids:
            # 既存エピソードを更新
            for i, ep in enumerate(episodes):
                if ep["id"] == episode_info["id"]:
                    episodes[i] = episode_info
                    break
        else:
            # 新しいエピソードを追加
            episodes.append(episode_info)

        # 日付順でソート（新しいものが最初）
        episodes.sort(key=lambda x: x["published_date"], reverse=True)

        # 最大エピソード数で制限
        max_episodes = self.config["max_episodes"]
        if len(episodes) > max_episodes:
            episodes = episodes[:max_episodes]

        self._save_episodes_db(episodes)
        self.logger.info(f"エピソードDB更新完了 - 総数: {len(episodes)}")

    def _generate_rss_feed(self) -> None:
        """RSS フィード生成"""
        try:
            episodes = self._load_episodes_db()

            rss_content = self._build_rss_xml(episodes)

            rss_path = self.output_dir / self.config["rss_filename"]
            with open(rss_path, "w", encoding="utf-8") as f:
                f.write(rss_content)

            self.logger.info(f"RSS フィード生成完了: {rss_path}")

        except Exception as e:
            self.logger.error(f"RSS フィード生成エラー: {e}")
            raise

    def _build_rss_xml(self, episodes: List[Dict[str, Any]]) -> str:
        """RSS XML を構築"""
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom

        # RSS ルート要素
        rss = Element("rss", version="2.0")
        rss.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
        rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")

        channel = SubElement(rss, "channel")

        # チャンネル情報
        SubElement(channel, "title").text = self.podcast_info.get("title", "Market News Podcast")
        SubElement(channel, "description").text = self.podcast_info.get(
            "description", "Daily market news"
        )
        SubElement(channel, "link").text = self.base_url
        SubElement(channel, "language").text = "ja"
        SubElement(channel, "lastBuildDate").text = datetime.now().strftime(
            "%a, %d %b %Y %H:%M:%S %z"
        )
        SubElement(channel, "generator").text = "Independent Podcast Publisher"

        # iTunes 固有タグ
        SubElement(channel, "itunes:author").text = self.podcast_info.get(
            "author", "Market News Team"
        )
        SubElement(channel, "itunes:summary").text = self.podcast_info.get(
            "description", "Daily market news"
        )
        SubElement(channel, "itunes:explicit").text = "no"

        # カテゴリ
        category = SubElement(channel, "itunes:category", text="Business")
        SubElement(category, "itunes:category", text="Investing")

        # オーナー情報
        owner = SubElement(channel, "itunes:owner")
        SubElement(owner, "itunes:name").text = self.podcast_info.get("author", "Market News Team")
        SubElement(owner, "itunes:email").text = self.podcast_info.get(
            "email", "podcast@example.com"
        )

        # エピソード
        for episode in episodes[:20]:  # 最新20エピソード
            item = SubElement(channel, "item")

            SubElement(item, "title").text = episode["title"]
            SubElement(item, "description").text = episode["description"]
            SubElement(item, "link").text = episode["audio_url"]
            SubElement(item, "guid", isPermaLink="true").text = episode["audio_url"]

            # 日付フォーマット
            try:
                pub_date = datetime.fromisoformat(episode["published_date"].replace("Z", "+00:00"))
                SubElement(item, "pubDate").text = pub_date.strftime("%a, %d %b %Y %H:%M:%S %z")
            except:
                SubElement(item, "pubDate").text = datetime.now().strftime(
                    "%a, %d %b %Y %H:%M:%S %z"
                )

            # エンクロージャー（音声ファイル）
            enclosure = SubElement(item, "enclosure")
            enclosure.set("url", episode["audio_url"])
            enclosure.set("type", "audio/mpeg")
            enclosure.set("length", str(episode["file_size"]))

            # iTunes 固有
            SubElement(item, "itunes:duration").text = episode.get("duration", "00:10:00")
            if episode.get("episode_number"):
                SubElement(item, "itunes:episode").text = str(episode["episode_number"])
            if episode.get("season"):
                SubElement(item, "itunes:season").text = str(episode["season"])

        # XML 文字列に変換（整形）
        rough_string = tostring(rss, encoding="unicode")
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def _deploy_to_github_pages(self, episode_info: Dict[str, Any]) -> bool:
        """
        GitHub Pages にデプロイ

        Args:
            episode_info: エピソード情報

        Returns:
            bool: 成功時True
        """
        try:
            # Git が利用可能かチェック
            if not shutil.which("git"):
                self.logger.warning(
                    "Git コマンドが見つかりません - GitHub Pages自動デプロイはスキップ"
                )
                return True  # ローカル配信は成功とする

            # Git リポジトリの初期化・更新
            self._setup_git_repository()

            # ファイルをステージング
            self._stage_files_for_commit()

            # コミット
            commit_message = self.config["commit_message_template"].format(
                title=episode_info["title"], date=datetime.now().strftime("%Y-%m-%d %H:%M")
            )

            result = self._git_commit_and_push(commit_message)

            if result:
                self.logger.info("GitHub Pages デプロイ成功")
                return True
            else:
                self.logger.warning("GitHub Pages デプロイに失敗 - ローカル配信は成功")
                return True  # ローカル配信は成功

        except Exception as e:
            self.logger.error(f"GitHub Pages デプロイエラー: {e}")
            return True  # エラーでもローカル配信は成功とする

    def _setup_git_repository(self) -> None:
        """Git リポジトリのセットアップ"""
        os.chdir(self.output_dir)

        if not Path(".git").exists():
            # 新規リポジトリ初期化
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(
                ["git", "remote", "add", "origin", self.github_repo_url],
                check=True,
                capture_output=True,
            )

        # gh-pages ブランチに切り替え
        branch = self.config["branch"]
        try:
            subprocess.run(["git", "checkout", branch], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            # ブランチが存在しない場合は作成
            subprocess.run(["git", "checkout", "-b", branch], check=True, capture_output=True)

    def _stage_files_for_commit(self) -> None:
        """コミット用ファイルをステージング"""
        # 必要なファイルのみ追加
        files_to_add = [
            self.config["rss_filename"],
            f"{self.config['audio_dir']}/*.mp3",
            "episodes.json",
        ]

        for file_pattern in files_to_add:
            try:
                subprocess.run(["git", "add", file_pattern], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                # ファイルが存在しない場合はスキップ
                pass

    def _git_commit_and_push(self, commit_message: str) -> bool:
        """Git コミットとプッシュ"""
        try:
            # コミット
            subprocess.run(["git", "commit", "-m", commit_message], check=True, capture_output=True)

            # プッシュ
            branch = self.config["branch"]
            subprocess.run(["git", "push", "-u", "origin", branch], check=True, capture_output=True)

            return True

        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Git 操作エラー: {e}")
            return False

    def cleanup_old_files(self) -> None:
        """古いファイルのクリーンアップ"""
        try:
            days_to_keep = self.config["days_to_keep"]
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            episodes = self._load_episodes_db()
            episodes_to_keep = []
            files_to_delete = []

            for episode in episodes:
                try:
                    episode_date = datetime.fromisoformat(
                        episode["published_date"].replace("Z", "+00:00")
                    )
                    if episode_date >= cutoff_date:
                        episodes_to_keep.append(episode)
                    else:
                        # 古いエピソードのファイルを削除対象に
                        audio_file = self.audio_dir / episode["audio_filename"]
                        if audio_file.exists():
                            files_to_delete.append(audio_file)
                except:
                    # 日付解析エラーの場合は保持
                    episodes_to_keep.append(episode)

            # ファイル削除
            for file_path in files_to_delete:
                file_path.unlink()
                self.logger.debug(f"古いファイルを削除: {file_path}")

            # エピソードDB更新
            if len(episodes_to_keep) < len(episodes):
                self._save_episodes_db(episodes_to_keep)
                self.logger.info(f"クリーンアップ完了: {len(files_to_delete)}ファイル削除")

        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")

    def get_episode_list(self) -> List[Dict[str, Any]]:
        """エピソードリストを取得"""
        return self._load_episodes_db()

    def get_rss_url(self) -> str:
        """RSS URL を取得"""
        return f"{self.base_url}/{self.config['rss_filename']}"

    def get_stats(self) -> Dict[str, Any]:
        """配信統計を取得"""
        episodes = self._load_episodes_db()
        total_size = sum(ep.get("file_size", 0) for ep in episodes)

        return {
            "total_episodes": len(episodes),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "latest_episode": episodes[0] if episodes else None,
            "rss_url": self.get_rss_url(),
            "base_url": self.base_url,
        }
