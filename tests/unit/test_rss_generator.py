"""
RSSGenerator のユニットテスト
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from datetime import datetime, timezone

# feedgenのモック（テスト環境で利用できない場合）
try:
    from feedgen.feed import FeedGenerator
    FEEDGEN_AVAILABLE = True
except ImportError:
    FEEDGEN_AVAILABLE = False
    # モッククラスを作成
    class FeedGenerator:
        def __init__(self):
            self.entries = []
        
        def id(self, value): pass
        def title(self, value): pass
        def link(self, **kwargs): pass
        def description(self, value): pass
        def author(self, **kwargs): pass
        def language(self, value): pass
        def copyright(self, value): pass
        def generator(self, value): pass
        def image(self, **kwargs): pass
        
        @property
        def podcast(self):
            return Mock()
        
        def add_entry(self):
            entry = Mock()
            entry.podcast = Mock()
            self.entries.append(entry)
            return entry
        
        def rss_str(self, pretty=True):
            return b'<?xml version="1.0" encoding="UTF-8"?><rss>mock rss content</rss>'

from src.podcast.publisher import (
    RSSGenerator,
    PodcastEpisode,
    PublishResult,
    RSSPublishingError,
    GitHubPagesError
)


class TestPodcastEpisode:
    """PodcastEpisode のテストクラス"""
    
    @pytest.fixture
    def sample_episode(self):
        """テスト用エピソード"""
        return PodcastEpisode(
            title="第1回 マーケットニュース",
            description="今日の市場動向をお伝えします",
            audio_file_path="/path/to/episode_001.mp3",
            duration_seconds=600,  # 10分
            file_size_bytes=1024000,  # 1MB
            publish_date=datetime(2024, 1, 15, 7, 0, 0, tzinfo=timezone.utc),
            episode_number=1,
            transcript="今日のマーケットニュースをお伝えします...",
            source_articles=[
                {"title": "株価上昇", "url": "https://example.com/1"},
                {"title": "金利動向", "url": "https://example.com/2"}
            ]
        )
    
    def test_get_formatted_duration_minutes_only(self, sample_episode):
        """分のみの再生時間フォーマットテスト"""
        sample_episode.duration_seconds = 600  # 10分
        assert sample_episode.get_formatted_duration() == "10:00"
    
    def test_get_formatted_duration_with_hours(self, sample_episode):
        """時間を含む再生時間フォーマットテスト"""
        sample_episode.duration_seconds = 3661  # 1時間1分1秒
        assert sample_episode.get_formatted_duration() == "01:01:01"
    
    def test_get_formatted_duration_seconds_only(self, sample_episode):
        """秒のみの再生時間フォーマットテスト"""
        sample_episode.duration_seconds = 45  # 45秒
        assert sample_episode.get_formatted_duration() == "00:45"
    
    def test_get_episode_guid(self, sample_episode):
        """エピソードGUID生成テスト"""
        guid = sample_episode.get_episode_guid()
        assert guid == "episode-1-20240115"
        assert "episode-" in guid
        assert "1" in guid
        assert "20240115" in guid


class TestRSSGenerator:
    """RSSGenerator のテストクラス"""
    
    @pytest.fixture
    def rss_config(self):
        """RSS設定"""
        return {
            'rss_title': 'テストポッドキャスト',
            'rss_description': 'テスト用の説明',
            'rss_link': 'https://test.github.io/podcast/',
            'rss_language': 'ja-JP',
            'rss_author': 'テスト作者',
            'rss_email': 'test@example.com',
            'rss_category': 'Business',
            'rss_image_url': 'https://test.github.io/podcast/image.jpg',
            'github_pages_url': 'https://test.github.io/',
            'github_repo_path': '/tmp/test_repo',
            'audio_base_url': 'https://test.github.io/podcast/audio/',
            'rss_output_path': 'podcast/feed.xml',
            'episodes_data_path': 'podcast/episodes.json',
            'max_episodes': 50
        }
    
    @pytest.fixture
    def sample_episode(self):
        """テスト用エピソード"""
        return PodcastEpisode(
            title="第1回 テストエピソード",
            description="テスト用のエピソード説明",
            audio_file_path="/tmp/test_audio.mp3",
            duration_seconds=600,
            file_size_bytes=1024000,
            publish_date=datetime(2024, 1, 15, 7, 0, 0, tzinfo=timezone.utc),
            episode_number=1,
            transcript="テスト用のトランスクリプト",
            source_articles=[]
        )
    
    @pytest.fixture
    def temp_repo_dir(self):
        """テスト用の一時リポジトリディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_dir = Path(temp_dir) / "test_repo"
            repo_dir.mkdir()
            yield str(repo_dir)
    
    def test_init_success(self, rss_config):
        """正常な初期化のテスト"""
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            assert generator.rss_title == 'テストポッドキャスト'
            assert generator.rss_description == 'テスト用の説明'
            assert generator.rss_link == 'https://test.github.io/podcast/'
            assert generator.github_pages_url == 'https://test.github.io/'
            assert generator.max_episodes == 50
    
    def test_init_feedgen_not_available(self, rss_config):
        """feedgen未インストール時の初期化テスト"""
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', False):
            with pytest.raises(RSSPublishingError) as exc_info:
                RSSGenerator(rss_config)
            
            assert "feedgenライブラリが必要です" in str(exc_info.value)
    
    def test_init_default_values(self):
        """デフォルト値での初期化テスト"""
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator({})
            
            assert generator.rss_title == 'マーケットニュース10分'
            assert generator.rss_description == 'AIが生成する毎日のマーケットニュース'
            assert generator.rss_language == 'ja-JP'
            assert generator.rss_author == 'AI Market News'
            assert generator.max_episodes == 50
    
    @patch('pathlib.Path.exists')
    @patch('shutil.copy2')
    def test_upload_audio_file_success(self, mock_copy, mock_exists, rss_config, sample_episode, temp_repo_dir):
        """音声ファイルアップロード成功のテスト"""
        rss_config['github_repo_path'] = temp_repo_dir
        mock_exists.return_value = True
        
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            audio_url = generator._upload_audio_file(sample_episode)
            
            expected_filename = "episode_001_20240115.mp3"
            expected_url = f"https://test.github.io/podcast/audio/{expected_filename}"
            
            assert audio_url == expected_url
            mock_copy.assert_called_once()
    
    @patch('pathlib.Path.exists')
    def test_upload_audio_file_not_found(self, mock_exists, rss_config, sample_episode):
        """音声ファイルが存在しない場合のテスト"""
        mock_exists.return_value = False
        
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            with pytest.raises(GitHubPagesError) as exc_info:
                generator._upload_audio_file(sample_episode)
            
            assert "音声ファイルが見つかりません" in str(exc_info.value)
    
    def test_update_episodes_data_new_episode(self, rss_config, sample_episode, temp_repo_dir):
        """新しいエピソードデータ更新のテスト"""
        rss_config['github_repo_path'] = temp_repo_dir
        
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            audio_url = "https://test.github.io/podcast/audio/episode_001.mp3"
            credits = "テスト用クレジット"
            
            generator._update_episodes_data(sample_episode, audio_url, credits)
            
            # エピソードデータファイルが作成されることを確認
            episodes_file = Path(temp_repo_dir) / "podcast" / "episodes.json"
            assert episodes_file.exists()
            
            # データ内容を確認
            with open(episodes_file, 'r', encoding='utf-8') as f:
                episodes = json.load(f)
            
            assert len(episodes) == 1
            episode_data = episodes[0]
            assert episode_data['episode_number'] == 1
            assert episode_data['title'] == "第1回 テストエピソード"
            assert episode_data['audio_url'] == audio_url
            assert episode_data['credits'] == credits
    
    def test_update_episodes_data_existing_episode(self, rss_config, sample_episode, temp_repo_dir):
        """既存エピソードデータ更新のテスト"""
        rss_config['github_repo_path'] = temp_repo_dir
        
        # 既存のエピソードデータを作成
        episodes_file = Path(temp_repo_dir) / "podcast" / "episodes.json"
        episodes_file.parent.mkdir(parents=True, exist_ok=True)
        
        existing_data = [{
            'episode_number': 1,
            'title': '古いタイトル',
            'audio_url': 'old_url',
            'duration_seconds': 300,
            'file_size_bytes': 500000,
            'publish_date': '2024-01-14T07:00:00+00:00',
            'guid': 'old-guid',
            'transcript': '古いトランスクリプト',
            'credits': '古いクレジット',
            'source_articles': []
        }]
        
        with open(episodes_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f)
        
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            audio_url = "https://test.github.io/podcast/audio/episode_001_new.mp3"
            credits = "新しいクレジット"
            
            generator._update_episodes_data(sample_episode, audio_url, credits)
            
            # データが更新されることを確認
            with open(episodes_file, 'r', encoding='utf-8') as f:
                episodes = json.load(f)
            
            assert len(episodes) == 1
            episode_data = episodes[0]
            assert episode_data['title'] == "第1回 テストエピソード"  # 更新されている
            assert episode_data['audio_url'] == audio_url  # 更新されている
            assert episode_data['credits'] == credits  # 更新されている
    
    def test_format_duration(self, rss_config):
        """再生時間フォーマットのテスト"""
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            # 分のみ
            assert generator._format_duration(600) == "10:00"
            
            # 時間を含む
            assert generator._format_duration(3661) == "1:01:01"
            
            # 秒のみ
            assert generator._format_duration(45) == "0:45"
    
    @patch('src.podcast.publisher.FeedGenerator')
    def test_generate_rss_feed(self, mock_fg_class, rss_config, temp_repo_dir):
        """RSSフィード生成のテスト"""
        rss_config['github_repo_path'] = temp_repo_dir
        
        # テスト用エピソードデータを作成
        episodes_file = Path(temp_repo_dir) / "podcast" / "episodes.json"
        episodes_file.parent.mkdir(parents=True, exist_ok=True)
        
        episodes_data = [{
            'episode_number': 1,
            'title': 'テストエピソード',
            'description': 'テスト説明',
            'audio_url': 'https://test.github.io/audio/episode_001.mp3',
            'duration_seconds': 600,
            'file_size_bytes': 1024000,
            'publish_date': '2024-01-15T07:00:00+00:00',
            'guid': 'episode-1-20240115',
            'transcript': 'テストトランスクリプト',
            'credits': 'テストクレジット',
            'source_articles': []
        }]
        
        with open(episodes_file, 'w', encoding='utf-8') as f:
            json.dump(episodes_data, f)
        
        # FeedGeneratorのモックを設定
        mock_fg = Mock()
        mock_fg.rss_str.return_value = b'<?xml version="1.0"?><rss>test content</rss>'
        mock_fg_class.return_value = mock_fg
        
        mock_entry = Mock()
        mock_entry.podcast = Mock()
        mock_fg.add_entry.return_value = mock_entry
        
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            rss_content = generator._generate_rss_feed("テストクレジット")
            
            # FeedGeneratorが適切に設定されることを確認
            mock_fg.title.assert_called_with('テストポッドキャスト')
            mock_fg.description.assert_called_with('テスト用の説明')
            mock_fg.language.assert_called_with('ja-JP')
            
            # エントリが追加されることを確認
            mock_fg.add_entry.assert_called_once()
            mock_entry.title.assert_called_with('テストエピソード')
            
            # RSS文字列が返されることを確認
            assert '<?xml version="1.0"?>' in rss_content
            assert '<rss>' in rss_content
    
    @patch('subprocess.run')
    def test_git_commit_and_push_success(self, mock_run, rss_config, temp_repo_dir):
        """Git操作成功のテスト"""
        rss_config['github_repo_path'] = temp_repo_dir
        
        # subprocess.runの戻り値をモック
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            generator._git_commit_and_push()
            
            # 3つのGitコマンドが実行されることを確認
            assert mock_run.call_count == 3
            
            # 各コマンドの確認
            calls = mock_run.call_args_list
            assert calls[0][0][0] == ['git', 'add', 'podcast/']
            assert calls[1][0][0][0:2] == ['git', 'commit']
            assert calls[2][0][0] == ['git', 'push', 'origin', 'main']
    
    @patch('subprocess.run')
    def test_git_commit_and_push_nothing_to_commit(self, mock_run, rss_config, temp_repo_dir):
        """コミットするものがない場合のテスト"""
        rss_config['github_repo_path'] = temp_repo_dir
        
        # 最初のaddは成功、commitは「nothing to commit」、pushはスキップ
        mock_run.side_effect = [
            Mock(returncode=0, stdout='', stderr=''),  # git add
            Mock(returncode=1, stdout='nothing to commit', stderr=''),  # git commit
            Mock(returncode=0, stdout='', stderr='')   # git push (呼ばれない)
        ]
        
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            # エラーにならないことを確認
            generator._git_commit_and_push()
            
            # addとcommitが呼ばれることを確認
            assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_git_commit_and_push_error(self, mock_run, rss_config, temp_repo_dir):
        """Git操作エラーのテスト"""
        rss_config['github_repo_path'] = temp_repo_dir
        
        # Git操作でエラーが発生
        mock_run.return_value = Mock(returncode=1, stdout='', stderr='Git error occurred')
        
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            with pytest.raises(GitHubPagesError) as exc_info:
                generator._git_commit_and_push()
            
            assert "Git操作失敗" in str(exc_info.value)
    
    def test_get_rss_url(self, rss_config):
        """RSSフィードURL取得のテスト"""
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            rss_url = generator.get_rss_url()
            
            expected_url = "https://test.github.io/podcast/feed.xml"
            assert rss_url == expected_url
    
    @patch.object(RSSGenerator, '_upload_audio_file')
    @patch.object(RSSGenerator, '_update_episodes_data')
    @patch.object(RSSGenerator, '_generate_rss_feed')
    @patch.object(RSSGenerator, '_deploy_rss_feed')
    def test_publish_success(self, mock_deploy, mock_generate, mock_update, mock_upload, 
                           rss_config, sample_episode):
        """RSS配信成功のテスト"""
        # モックの戻り値を設定
        mock_upload.return_value = "https://test.github.io/audio/episode_001.mp3"
        mock_generate.return_value = "<?xml>RSS content</xml>"
        mock_deploy.return_value = "https://test.github.io/podcast/feed.xml"
        
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            result = generator.publish(sample_episode, "テストクレジット")
            
            # 成功結果を確認
            assert result.success is True
            assert result.channel == "RSS"
            assert result.url == "https://test.github.io/podcast/feed.xml"
            assert "RSS配信が正常に完了" in result.message
            
            # 各メソッドが呼ばれることを確認
            mock_upload.assert_called_once_with(sample_episode)
            mock_update.assert_called_once()
            mock_generate.assert_called_once_with("テストクレジット")
            mock_deploy.assert_called_once_with("<?xml>RSS content</xml>")
    
    @patch.object(RSSGenerator, '_upload_audio_file')
    def test_publish_error(self, mock_upload, rss_config, sample_episode):
        """RSS配信エラーのテスト"""
        # アップロードでエラーが発生
        mock_upload.side_effect = GitHubPagesError("アップロードエラー")
        
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            generator = RSSGenerator(rss_config)
            
            result = generator.publish(sample_episode, "テストクレジット")
            
            # エラー結果を確認
            assert result.success is False
            assert result.channel == "RSS"
            assert result.url is None
            assert "RSS配信エラー" in result.message
            assert "アップロードエラー" in result.message


class TestRSSPublishingError:
    """RSSPublishingError のテスト"""
    
    def test_rss_publishing_error(self):
        """RSSPublishingError のテスト"""
        error = RSSPublishingError("テストエラー")
        assert str(error) == "テストエラー"
        assert isinstance(error, Exception)


class TestGitHubPagesError:
    """GitHubPagesError のテスト"""
    
    def test_github_pages_error(self):
        """GitHubPagesError のテスト"""
        error = GitHubPagesError("GitHub Pagesエラー")
        assert str(error) == "GitHub Pagesエラー"
        assert isinstance(error, RSSPublishingError)


class TestIntegration:
    """統合テスト"""
    
    @pytest.fixture
    def integration_config(self):
        """統合テスト用設定"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield {
                'rss_title': '統合テストポッドキャスト',
                'rss_description': '統合テスト用',
                'rss_link': 'https://integration.test/',
                'github_pages_url': 'https://integration.test/',
                'github_repo_path': temp_dir,
                'rss_output_path': 'feed.xml',
                'episodes_data_path': 'episodes.json'
            }
    
    @patch('subprocess.run')
    @patch('shutil.copy2')
    @patch('pathlib.Path.exists')
    def test_full_rss_publishing_pipeline(self, mock_exists, mock_copy, mock_run, integration_config):
        """完全なRSS配信パイプラインのテスト"""
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        
        episode = PodcastEpisode(
            title="統合テストエピソード",
            description="統合テスト用のエピソード",
            audio_file_path="/tmp/test.mp3",
            duration_seconds=600,
            file_size_bytes=1024000,
            publish_date=datetime.now(timezone.utc),
            episode_number=1,
            transcript="統合テスト",
            source_articles=[]
        )
        
        with patch('src.podcast.publisher.FEEDGEN_AVAILABLE', True):
            with patch('src.podcast.publisher.FeedGenerator') as mock_fg_class:
                mock_fg = Mock()
                mock_fg.rss_str.return_value = b'<?xml version="1.0"?><rss>integration test</rss>'
                mock_fg_class.return_value = mock_fg
                
                mock_entry = Mock()
                mock_entry.podcast = Mock()
                mock_fg.add_entry.return_value = mock_entry
                
                generator = RSSGenerator(integration_config)
                result = generator.publish(episode, "統合テストクレジット")
                
                # 成功することを確認
                assert result.success is True
                assert result.channel == "RSS"
                
                # ファイル操作が行われることを確認
                mock_copy.assert_called_once()  # 音声ファイルコピー
                
                # Git操作が行われることを確認
                assert mock_run.call_count >= 2  # git add, commit, push
                
                # RSSフィードが生成されることを確認
                mock_fg.title.assert_called()
                mock_fg.add_entry.assert_called()