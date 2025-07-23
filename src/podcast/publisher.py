"""
マルチチャンネル配信機能

RSS配信とLINE配信を統合した配信システムを提供します。
"""

import logging
import os
import shutil
import subprocess
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import tempfile

try:
    from feedgen.feed import FeedGenerator
    from feedgen.entry import FeedEntry
    FEEDGEN_AVAILABLE = True
except ImportError:
    FEEDGEN_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class PublishResult:
    """配信結果を表すデータクラス"""
    channel: str
    success: bool
    message: str
    url: Optional[str] = None


@dataclass
class PodcastEpisode:
    """ポッドキャストエピソードを表すデータクラス"""
    title: str
    description: str
    audio_file_path: str
    duration_seconds: int
    file_size_bytes: int
    publish_date: datetime
    episode_number: int
    transcript: str
    source_articles: List[Dict]
    
    def get_formatted_duration(self) -> str:
        """
        再生時間をHH:MM:SS形式で取得
        
        Returns:
            フォーマットされた再生時間
        """
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def get_episode_guid(self) -> str:
        """
        エピソードのGUIDを生成
        
        Returns:
            一意のGUID
        """
        return f"episode-{self.episode_number}-{self.publish_date.strftime('%Y%m%d')}"


class RSSPublishingError(Exception):
    """RSS配信関連のエラー"""
    pass


class GitHubPagesError(RSSPublishingError):
    """GitHub Pages関連のエラー"""
    pass


class RSSGenerator:
    """RSS配信クラス
    
    feedgenを使用してポッドキャストRSSフィードを生成し、
    GitHub Pagesで公開します。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: RSS配信設定
            
        Raises:
            RSSPublishingError: 必要なライブラリが不足している場合
        """
        if not FEEDGEN_AVAILABLE:
            raise RSSPublishingError("feedgenライブラリが必要です: pip install feedgen")
        
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # RSS設定
        self.rss_title = config.get('rss_title', 'マーケットニュース10分')
        self.rss_description = config.get('rss_description', 'AIが生成する毎日のマーケットニュース')
        self.rss_link = config.get('rss_link', 'https://example.github.io/podcast/')
        self.rss_language = config.get('rss_language', 'ja-JP')
        self.rss_author = config.get('rss_author', 'AI Market News')
        self.rss_email = config.get('rss_email', 'noreply@example.com')
        self.rss_category = config.get('rss_category', 'Business')
        self.rss_image_url = config.get('rss_image_url', '')
        
        # GitHub Pages設定
        self.github_pages_url = config.get('github_pages_url', '')
        self.github_repo_path = config.get('github_repo_path', '')
        self.audio_base_url = config.get('audio_base_url', '')
        
        # ファイルパス設定
        self.rss_output_path = config.get('rss_output_path', 'podcast/feed.xml')
        self.episodes_data_path = config.get('episodes_data_path', 'podcast/episodes.json')
        
        # エピソード管理
        self.max_episodes = config.get('max_episodes', 50)  # RSSに含める最大エピソード数
        
        self.logger.info("RSSGenerator初期化完了")
    
    def publish(self, episode: PodcastEpisode, credits: str) -> PublishResult:
        """
        RSSフィードを生成・公開
        
        Args:
            episode: ポッドキャストエピソード
            credits: CC-BYクレジット情報
            
        Returns:
            配信結果
        """
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
                message=f"RSS配信エラー: {str(e)}"
            )
    
    def _upload_audio_file(self, episode: PodcastEpisode) -> str:
        """
        音声ファイルをGitHub Pagesにアップロード
        
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
            
            # ファイル名を生成（エピソード番号と日付を含む）
            file_extension = audio_file_path.suffix
            audio_filename = f"episode_{episode.episode_number:03d}_{episode.publish_date.strftime('%Y%m%d')}{file_extension}"
            
            if self.github_repo_path:
                # ローカルのGitリポジトリにコピー
                audio_dest_path = Path(self.github_repo_path) / "podcast" / "audio" / audio_filename
                audio_dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(audio_file_path, audio_dest_path)
                self.logger.info(f"音声ファイルをコピー: {audio_dest_path}")
                
                # GitHub Pagesの音声ファイルURL
                audio_url = urljoin(self.github_pages_url, f"podcast/audio/{audio_filename}")
            else:
                # GitHub APIを使用したアップロード（実装は省略、実際の運用では必要）
                audio_url = urljoin(self.audio_base_url, audio_filename)
                self.logger.warning("GitHub APIアップロードは未実装、URLのみ生成")
            
            return audio_url
            
        except Exception as e:
            raise GitHubPagesError(f"音声ファイルアップロードエラー: {str(e)}")
    
    def _update_episodes_data(self, episode: PodcastEpisode, audio_url: str, credits: str) -> None:
        """
        エピソードデータを更新
        
        Args:
            episode: ポッドキャストエピソード
            audio_url: 音声ファイルURL
            credits: クレジット情報
        """
        import json
        
        episodes_data_file = Path(self.github_repo_path) / self.episodes_data_path if self.github_repo_path else Path(self.episodes_data_path)
        episodes_data_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 既存のエピソードデータを読み込み
        episodes = []
        if episodes_data_file.exists():
            try:
                with open(episodes_data_file, 'r', encoding='utf-8') as f:
                    episodes = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                episodes = []
        
        # 新しいエピソードデータを作成
        episode_data = {
            'episode_number': episode.episode_number,
            'title': episode.title,
            'description': episode.description,
            'audio_url': audio_url,
            'duration_seconds': episode.duration_seconds,
            'file_size_bytes': episode.file_size_bytes,
            'publish_date': episode.publish_date.isoformat(),
            'guid': episode.get_episode_guid(),
            'transcript': episode.transcript,
            'credits': credits,
            'source_articles': episode.source_articles
        }
        
        # 既存のエピソードを更新または新規追加
        updated = False
        for i, existing_episode in enumerate(episodes):
            if existing_episode['episode_number'] == episode.episode_number:
                episodes[i] = episode_data
                updated = True
                break
        
        if not updated:
            episodes.append(episode_data)
        
        # エピソード番号でソート（新しい順）
        episodes.sort(key=lambda x: x['episode_number'], reverse=True)
        
        # 最大エピソード数を超える場合は古いものを削除
        if len(episodes) > self.max_episodes:
            episodes = episodes[:self.max_episodes]
        
        # ファイルに保存
        with open(episodes_data_file, 'w', encoding='utf-8') as f:
            json.dump(episodes, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"エピソードデータを更新: {len(episodes)}エピソード")
    
    def _generate_rss_feed(self, credits: str) -> str:
        """
        RSSフィードを生成
        
        Args:
            credits: クレジット情報
            
        Returns:
            RSS XML文字列
        """
        import json
        
        # エピソードデータを読み込み
        episodes_data_file = Path(self.github_repo_path) / self.episodes_data_path if self.github_repo_path else Path(self.episodes_data_path)
        episodes = []
        if episodes_data_file.exists():
            with open(episodes_data_file, 'r', encoding='utf-8') as f:
                episodes = json.load(f)
        
        # FeedGeneratorを初期化
        fg = FeedGenerator()
        
        # ポッドキャスト基本情報
        fg.id(self.rss_link)
        fg.title(self.rss_title)
        fg.link(href=self.rss_link, rel='alternate')
        fg.description(self.rss_description)
        fg.author(name=self.rss_author, email=self.rss_email)
        fg.language(self.rss_language)
        fg.copyright(f'© {datetime.now().year} {self.rss_author}')
        fg.generator('AI Market News Podcast Generator')
        
        # ポッドキャスト固有の設定
        fg.podcast.itunes_category('Business', 'Investing')
        fg.podcast.itunes_author(self.rss_author)
        fg.podcast.itunes_summary(self.rss_description)
        fg.podcast.itunes_owner(name=self.rss_author, email=self.rss_email)
        fg.podcast.itunes_explicit('no')
        
        if self.rss_image_url:
            fg.podcast.itunes_image(self.rss_image_url)
            fg.image(url=self.rss_image_url, title=self.rss_title, link=self.rss_link)
        
        # エピソードを追加
        for episode_data in episodes:
            fe = fg.add_entry()
            
            # 基本情報
            episode_url = urljoin(self.rss_link, f"episode/{episode_data['episode_number']}")
            fe.id(episode_url)
            fe.title(episode_data['title'])
            fe.link(href=episode_url)
            
            # 説明文にクレジット情報を追加
            description_with_credits = f"{episode_data['description']}\n\n{episode_data.get('credits', credits)}"
            fe.description(description_with_credits)
            
            # 公開日時
            publish_date = datetime.fromisoformat(episode_data['publish_date'])
            if publish_date.tzinfo is None:
                publish_date = publish_date.replace(tzinfo=timezone.utc)
            fe.pubDate(publish_date)
            
            # 音声ファイル情報
            fe.enclosure(
                url=episode_data['audio_url'],
                length=str(episode_data['file_size_bytes']),
                type='audio/mpeg'
            )
            
            # ポッドキャスト固有の情報
            fe.podcast.itunes_duration(self._format_duration(episode_data['duration_seconds']))
            fe.podcast.itunes_explicit('no')
            fe.podcast.itunes_summary(description_with_credits)
            
            # GUID設定
            fe.guid(episode_data['guid'], permalink=False)
        
        # RSS XMLを生成
        rss_str = fg.rss_str(pretty=True).decode('utf-8')
        
        self.logger.info(f"RSSフィード生成完了: {len(episodes)}エピソード")
        return rss_str
    
    def _format_duration(self, duration_seconds: int) -> str:
        """
        再生時間をiTunes形式でフォーマット
        
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
    
    def _deploy_rss_feed(self, rss_content: str) -> str:
        """
        RSSフィードをGitHub Pagesに配信
        
        Args:
            rss_content: RSS XML文字列
            
        Returns:
            配信されたRSSフィードのURL
            
        Raises:
            GitHubPagesError: 配信に失敗した場合
        """
        try:
            if self.github_repo_path:
                # ローカルのGitリポジトリにRSSファイルを保存
                rss_file_path = Path(self.github_repo_path) / self.rss_output_path
                rss_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(rss_file_path, 'w', encoding='utf-8') as f:
                    f.write(rss_content)
                
                self.logger.info(f"RSSファイルを保存: {rss_file_path}")
                
                # Git操作（自動コミット・プッシュ）
                self._git_commit_and_push()
                
                # GitHub PagesのRSSフィードURL
                rss_url = urljoin(self.github_pages_url, self.rss_output_path)
            else:
                # GitHub APIを使用した直接アップロード（実装は省略）
                rss_url = urljoin(self.github_pages_url, self.rss_output_path)
                self.logger.warning("GitHub API配信は未実装、URLのみ生成")
            
            return rss_url
            
        except Exception as e:
            raise GitHubPagesError(f"RSS配信エラー: {str(e)}")
    
    def _git_commit_and_push(self) -> None:
        """
        Gitリポジトリにコミット・プッシュ
        
        Raises:
            GitHubPagesError: Git操作に失敗した場合
        """
        try:
            if not self.github_repo_path:
                return
            
            repo_path = Path(self.github_repo_path)
            
            # Git操作
            commands = [
                ['git', 'add', 'podcast/'],
                ['git', 'commit', '-m', f'Update podcast feed - {datetime.now().strftime("%Y-%m-%d %H:%M")}'],
                ['git', 'push', 'origin', 'main']
            ]
            
            for cmd in commands:
                result = subprocess.run(
                    cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    # コミットが空の場合は無視
                    if 'nothing to commit' in result.stdout:
                        self.logger.info("変更がないためコミットをスキップ")
                        continue
                    else:
                        raise GitHubPagesError(f"Git操作失敗: {' '.join(cmd)}\n{result.stderr}")
            
            self.logger.info("Git操作完了: コミット・プッシュ成功")
            
        except subprocess.TimeoutExpired:
            raise GitHubPagesError("Git操作がタイムアウトしました")
        except Exception as e:
            raise GitHubPagesError(f"Git操作エラー: {str(e)}")
    
    def get_rss_url(self) -> str:
        """
        RSSフィードのURLを取得
        
        Returns:
            RSSフィードURL
        """
        return urljoin(self.github_pages_url, self.rss_output_path)


class LINEBroadcastingError(Exception):
    """LINE配信関連のエラー"""
    pass


class LINEAPIError(LINEBroadcastingError):
    """LINE API関連のエラー"""
    pass


class LINEBroadcaster:
    """LINE配信クラス
    
    LINE Messaging APIを使用してブロードキャストメッセージを送信します。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: LINE配信設定
            
        Raises:
            LINEBroadcastingError: 必要な設定が不足している場合
        """
        if not REQUESTS_AVAILABLE:
            raise LINEBroadcastingError("requestsライブラリが必要です: pip install requests")
        
        self.config = config
        self.channel_access_token = config.get('channel_access_token', '')
        
        if not self.channel_access_token:
            raise LINEBroadcastingError("LINE Channel Access Tokenが設定されていません")
        
        self.logger = logging.getLogger(__name__)
        
        # LINE API設定
        self.api_base_url = "https://api.line.me/v2/bot"
        self.broadcast_endpoint = f"{self.api_base_url}/message/broadcast"
        self.profile_endpoint = f"{self.api_base_url}/profile"
        
        # メッセージ設定
        self.max_message_length = config.get('max_message_length', 5000)  # LINE制限
        self.enable_notification = config.get('enable_notification', True)
        self.retry_count = config.get('retry_count', 3)
        self.retry_delay = config.get('retry_delay', 1.0)
        
        # テスト設定
        self.test_mode = config.get('test_mode', False)
        self.test_user_ids = config.get('test_user_ids', [])
        
        self.logger.info("LINEBroadcaster初期化完了")
    
    def publish(self, episode: PodcastEpisode, podcast_url: str, credits: str) -> PublishResult:
        """
        LINEブロードキャストメッセージを送信
        
        Args:
            episode: ポッドキャストエピソード
            podcast_url: ポッドキャストURL
            credits: CC-BYクレジット情報
            
        Returns:
            配信結果
        """
        try:
            self.logger.info(f"LINE配信を開始: {episode.title}")
            
            # 1. ブロードキャストメッセージ作成
            message = self._create_broadcast_message(episode, podcast_url, credits)
            
            # 2. メッセージ長さチェック
            self._validate_message_length(message)
            
            # 3. API送信
            if self.test_mode and self.test_user_ids:
                # テストモード: 特定ユーザーにのみ送信
                response_data = self._send_multicast_message(message, self.test_user_ids)
                message_text = f"テストユーザー {len(self.test_user_ids)}人に配信完了"
            else:
                # 本番モード: ブロードキャスト送信
                response_data = self._send_broadcast_message(message)
                message_text = "ブロードキャスト配信完了"
            
            self.logger.info(f"LINE配信成功: {message_text}")
            return PublishResult(
                channel="LINE",
                success=True,
                message=message_text,
                url=podcast_url
            )
            
        except Exception as e:
            self.logger.error(f"LINE配信に失敗: {str(e)}")
            return PublishResult(
                channel="LINE",
                success=False,
                message=f"LINE配信エラー: {str(e)}"
            )
    
    def _create_broadcast_message(self, episode: PodcastEpisode, podcast_url: str, credits: str) -> Dict[str, Any]:
        """
        ブロードキャストメッセージを作成
        
        Args:
            episode: ポッドキャストエピソード
            podcast_url: ポッドキャストURL
            credits: CC-BYクレジット情報
            
        Returns:
            LINE APIメッセージ形式
        """
        # 基本メッセージテキスト
        message_text = f"""🎙️ {episode.title}

📅 {episode.publish_date.strftime('%Y年%m月%d日')}
⏱️ 約{episode.duration_seconds // 60}分

{episode.description}

🎧 聴く: {podcast_url}

{credits}"""
        
        # 長すぎる場合は説明文を短縮
        if len(message_text) > self.max_message_length:
            # 説明文を短縮
            max_description_length = self.max_message_length - len(message_text) + len(episode.description) - 100
            if max_description_length > 50:
                short_description = episode.description[:max_description_length] + "..."
                message_text = f"""🎙️ {episode.title}

📅 {episode.publish_date.strftime('%Y年%m月%d日')}
⏱️ 約{episode.duration_seconds // 60}分

{short_description}

🎧 聴く: {podcast_url}

{credits}"""
        
        return {
            "type": "text",
            "text": message_text.strip()
        }
    
    def _validate_message_length(self, message: Dict[str, Any]) -> None:
        """
        メッセージ長さを検証
        
        Args:
            message: LINEメッセージ
            
        Raises:
            LINEBroadcastingError: メッセージが長すぎる場合
        """
        text = message.get('text', '')
        if len(text) > self.max_message_length:
            raise LINEBroadcastingError(f"メッセージが長すぎます: {len(text)} > {self.max_message_length}")
    
    def _send_broadcast_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        ブロードキャストメッセージを送信
        
        Args:
            message: LINEメッセージ
            
        Returns:
            API応答データ
            
        Raises:
            LINEAPIError: API呼び出しに失敗した場合
        """
        headers = {
            'Authorization': f'Bearer {self.channel_access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messages': [message],
            'notificationDisabled': not self.enable_notification
        }
        
        return self._make_api_request(self.broadcast_endpoint, headers, payload)
    
    def _send_multicast_message(self, message: Dict[str, Any], user_ids: List[str]) -> Dict[str, Any]:
        """
        マルチキャストメッセージを送信（テスト用）
        
        Args:
            message: LINEメッセージ
            user_ids: 送信先ユーザーIDリスト
            
        Returns:
            API応答データ
            
        Raises:
            LINEAPIError: API呼び出しに失敗した場合
        """
        headers = {
            'Authorization': f'Bearer {self.channel_access_token}',
            'Content-Type': 'application/json'
        }
        
        # LINEのマルチキャストは最大500ユーザーまで
        if len(user_ids) > 500:
            user_ids = user_ids[:500]
            self.logger.warning(f"ユーザー数を500に制限しました: {len(user_ids)}")
        
        payload = {
            'to': user_ids,
            'messages': [message],
            'notificationDisabled': not self.enable_notification
        }
        
        multicast_endpoint = f"{self.api_base_url}/message/multicast"
        return self._make_api_request(multicast_endpoint, headers, payload)
    
    def _make_api_request(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        LINE APIリクエストを実行
        
        Args:
            url: APIエンドポイントURL
            headers: HTTPヘッダー
            payload: リクエストペイロード
            
        Returns:
            API応答データ
            
        Raises:
            LINEAPIError: API呼び出しに失敗した場合
        """
        import time
        
        last_error = None
        
        for attempt in range(self.retry_count):
            try:
                self.logger.debug(f"LINE API呼び出し (試行 {attempt + 1}/{self.retry_count}): {url}")
                
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                # レスポンス処理
                if response.status_code == 200:
                    self.logger.debug("LINE API呼び出し成功")
                    return response.json() if response.content else {}
                
                elif response.status_code == 429:
                    # レート制限
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                    self.logger.warning(f"レート制限に達しました。{retry_after}秒後にリトライします")
                    time.sleep(retry_after)
                    continue
                
                else:
                    # その他のエラー
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get('message', f'HTTP {response.status_code}')
                    raise LINEAPIError(f"LINE API エラー: {error_message}")
                
            except requests.exceptions.Timeout:
                last_error = LINEAPIError("LINE API タイムアウト")
                self.logger.warning(f"API呼び出しタイムアウト (試行 {attempt + 1})")
                
            except requests.exceptions.ConnectionError:
                last_error = LINEAPIError("LINE API 接続エラー")
                self.logger.warning(f"API接続エラー (試行 {attempt + 1})")
                
            except LINEAPIError:
                # 既にLINEAPIErrorの場合は再発生
                raise
                
            except Exception as e:
                last_error = LINEAPIError(f"予期しないエラー: {str(e)}")
                self.logger.warning(f"予期しないエラー (試行 {attempt + 1}): {str(e)}")
            
            # リトライ前の待機
            if attempt < self.retry_count - 1:
                time.sleep(self.retry_delay)
        
        # 全てのリトライが失敗した場合
        raise last_error or LINEAPIError("LINE API呼び出しに失敗しました")
    
    def get_bot_info(self) -> Dict[str, Any]:
        """
        ボット情報を取得（接続テスト用）
        
        Returns:
            ボット情報
            
        Raises:
            LINEAPIError: API呼び出しに失敗した場合
        """
        headers = {
            'Authorization': f'Bearer {self.channel_access_token}'
        }
        
        info_endpoint = f"{self.api_base_url}/info"
        
        try:
            response = requests.get(info_endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json() if response.content else {}
                error_message = error_data.get('message', f'HTTP {response.status_code}')
                raise LINEAPIError(f"ボット情報取得エラー: {error_message}")
                
        except requests.exceptions.RequestException as e:
            raise LINEAPIError(f"ボット情報取得に失敗: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        LINE API接続テスト
        
        Returns:
            接続成功の場合True
        """
        try:
            bot_info = self.get_bot_info()
            self.logger.info(f"LINE API接続テスト成功: {bot_info.get('displayName', 'Unknown Bot')}")
            return True
        except Exception as e:
            self.logger.error(f"LINE API接続テスト失敗: {str(e)}")
            return False
    
    def create_rich_message(self, episode: PodcastEpisode, podcast_url: str, credits: str) -> Dict[str, Any]:
        """
        リッチメッセージを作成（将来の拡張用）
        
        Args:
            episode: ポッドキャストエピソード
            podcast_url: ポッドキャストURL
            credits: クレジット情報
            
        Returns:
            LINE Flex Messageフォーマット
        """
        # 基本的なFlex Messageテンプレート
        flex_message = {
            "type": "flex",
            "altText": f"{episode.title} - 新しいエピソードが配信されました",
            "contents": {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🎙️ 新しいエピソード",
                            "weight": "bold",
                            "color": "#1DB446"
                        }
                    ]
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": episode.title,
                            "weight": "bold",
                            "size": "lg",
                            "wrap": True
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "md",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": f"📅 {episode.publish_date.strftime('%Y年%m月%d日')}",
                                    "size": "sm",
                                    "color": "#666666"
                                },
                                {
                                    "type": "text",
                                    "text": f"⏱️ 約{episode.duration_seconds // 60}分",
                                    "size": "sm",
                                    "color": "#666666"
                                }
                            ]
                        },
                        {
                            "type": "text",
                            "text": episode.description,
                            "wrap": True,
                            "margin": "md"
                        }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "action": {
                                "type": "uri",
                                "label": "🎧 聴く",
                                "uri": podcast_url
                            }
                        },
                        {
                            "type": "text",
                            "text": credits,
                            "size": "xs",
                            "color": "#999999",
                            "margin": "sm",
                            "wrap": True
                        }
                    ]
                }
            }
        }
        
        return flex_message


class PodcastPublisher:
    """統合配信クラス
    
    RSS配信とLINE配信を統合して管理します。
    """
    
    def __init__(self, rss_config: Dict[str, Any], line_config: Dict[str, Any]):
        """
        初期化
        
        Args:
            rss_config: RSS配信設定
            line_config: LINE配信設定
        """
        self.rss_generator = RSSGenerator(rss_config)
        self.line_broadcaster = LINEBroadcaster(line_config)
        self.logger = logging.getLogger(__name__)
        self.logger.info("PodcastPublisher初期化完了")
    
    def publish(self, episode: PodcastEpisode, credits: str) -> List[PublishResult]:
        """
        ポッドキャストを全チャンネルに配信
        
        Args:
            episode: ポッドキャストエピソード
            credits: CC-BYクレジット情報
            
        Returns:
            各チャンネルの配信結果リスト
        """
        self.logger.info(f"マルチチャンネル配信を開始: {episode.title}")
        
        results = []
        
        # RSS配信
        try:
            rss_result = self.rss_generator.publish(episode, credits)
            results.append(rss_result)
            
            # RSS配信が成功した場合、URLを取得してLINE配信
            if rss_result.success and rss_result.url:
                line_result = self.line_broadcaster.publish(episode, rss_result.url, credits)
                results.append(line_result)
            else:
                results.append(PublishResult(
                    channel="LINE",
                    success=False,
                    message="RSS配信失敗のためLINE配信をスキップ"
                ))
                
        except Exception as e:
            self.logger.error(f"配信エラー: {str(e)}")
            results.append(PublishResult(
                channel="RSS",
                success=False,
                message=f"RSS配信エラー: {str(e)}"
            ))
            results.append(PublishResult(
                channel="LINE", 
                success=False,
                message="RSS配信失敗のためLINE配信をスキップ"
            ))
        
        # 配信結果をログ出力
        for result in results:
            if result.success:
                self.logger.info(f"{result.channel}配信成功: {result.message}")
            else:
                self.logger.error(f"{result.channel}配信失敗: {result.message}")
        
        return results
    
    def get_success_count(self, results: List[PublishResult]) -> int:
        """
        成功した配信数を取得
        
        Args:
            results: 配信結果リスト
            
        Returns:
            成功した配信数
        """
        return sum(1 for result in results if result.success)
    
    def is_all_success(self, results: List[PublishResult]) -> bool:
        """
        全ての配信が成功したかチェック
        
        Args:
            results: 配信結果リスト
            
        Returns:
            全て成功した場合True
        """
        return all(result.success for result in results)