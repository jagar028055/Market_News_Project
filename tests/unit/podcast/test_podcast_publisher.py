"""ポッドキャスト配信統合機能のテスト"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
import json
from pathlib import Path

from src.podcast.publisher.podcast_publisher import PodcastPublisher
from src.podcast.error_handling.publish_error_handler import PublishErrorType
from src.config.app_config import AppConfig, PodcastConfig
from src.error_handling.exceptions import PodcastPublishError


class TestPodcastPublisher:
    """PodcastPublisher クラスのテスト"""
    
    @pytest.fixture
    def mock_config(self):
        """モックConfig作成"""
        config = Mock(spec=AppConfig)
        config.podcast = Mock(spec=PodcastConfig)
        config.podcast.max_file_size_mb = 15
        config.podcast.audio_output_dir = "/tmp/podcast/audio"
        config.podcast.rss_output_dir = "/tmp/podcast/rss"
        config.podcast.error_log_dir = "/tmp/podcast/errors"
        config.podcast.max_publish_retries = 3
        config.podcast.publish_retry_delay = 1.0
        config.podcast.max_publish_retry_delay = 10.0
        return config
        
    @pytest.fixture
    def sample_episode(self):
        """サンプルエピソードデータ"""
        return {
            'guid': 'ep-001',
            'title': 'マーケットニュース第1回',
            'description': '今日のマーケット概要',
            'audio_filename': 'episode-001.mp3',
            'duration': '10:00',
            'file_size': 8 * 1024 * 1024,  # 8MB
            'pub_date': datetime.now(),
            'credits': {
                'bgm': {
                    'title': 'Background Music',
                    'author': 'Test Author',
                    'license_version': '4.0',
                    'source_url': 'https://example.com/bgm'
                }
            }
        }
        
    @pytest.fixture
    def publisher(self, mock_config):
        """PodcastPublisher インスタンス"""
        with patch('src.podcast.publisher.podcast_publisher.RSSGenerator'), \
             patch('src.podcast.publisher.podcast_publisher.LINEBroadcaster'), \
             patch('src.podcast.publisher.podcast_publisher.PublishErrorHandler'):
            return PodcastPublisher(mock_config)
            
    def test_init(self, mock_config):
        """初期化テスト"""
        with patch('src.podcast.publisher.podcast_publisher.RSSGenerator') as mock_rss, \
             patch('src.podcast.publisher.podcast_publisher.LINEBroadcaster') as mock_line, \
             patch('src.podcast.publisher.podcast_publisher.PublishErrorHandler') as mock_error:
             
            publisher = PodcastPublisher(mock_config)
            
            # 各コンポーネントが初期化されることを確認
            mock_rss.assert_called_once_with(mock_config)
            mock_line.assert_called_once_with(mock_config)
            mock_error.assert_called_once_with(mock_config)
            
    def test_validate_episode_data_valid(self, publisher, sample_episode):
        """有効なエピソードデータの検証テスト"""
        assert publisher.validate_episode_data(sample_episode) is True
        
    def test_validate_episode_data_missing_field(self, publisher, sample_episode):
        """必須フィールド不足の検証テスト"""
        del sample_episode['title']
        assert publisher.validate_episode_data(sample_episode) is False
        
    def test_validate_episode_data_file_size_exceeded(self, publisher, sample_episode):
        """ファイルサイズ制限超過の検証テスト"""
        sample_episode['file_size'] = 20 * 1024 * 1024  # 20MB
        assert publisher.validate_episode_data(sample_episode) is False
        
    @patch('shutil.copy2')
    @patch('pathlib.Path.mkdir')
    def test_prepare_audio_file(self, mock_mkdir, mock_copy, publisher):
        """音声ファイル準備テスト"""
        publisher._prepare_audio_file('/tmp/source.mp3', 'target.mp3')
        
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_copy.assert_called_once()
        
    def test_publish_episode_success(self, publisher, sample_episode):
        """配信成功テスト"""
        # モック設定
        publisher._prepare_audio_file = Mock()
        publisher.error_handler.execute_with_retry = Mock(return_value=True)
        publisher.error_handler.handle_partial_success = Mock()
        
        # 実行
        result = publisher.publish_episode(sample_episode, '/tmp/audio.mp3')
        
        # 検証
        assert result['rss'] is True
        assert result['line'] is True
        assert result['overall_success'] is True
        publisher._prepare_audio_file.assert_called_once()
        
    def test_publish_episode_partial_success(self, publisher, sample_episode):
        """部分的成功テスト（RSS成功、LINE失敗）"""
        # モック設定
        publisher._prepare_audio_file = Mock()
        publisher.error_handler.execute_with_retry = Mock(side_effect=[True, False])
        publisher.error_handler.handle_partial_success = Mock(return_value={
            'rss': True,
            'line': False,  
            'overall_success': True
        })
        
        # 実行
        result = publisher.publish_episode(sample_episode, '/tmp/audio.mp3')
        
        # 検証
        assert result['rss'] is True
        assert result['line'] is False
        assert result['overall_success'] is True
        publisher.error_handler.handle_partial_success.assert_called_once()
        
    def test_publish_episode_validation_failure(self, publisher, sample_episode):
        """エピソードデータ検証失敗テスト"""
        del sample_episode['title']  # 必須フィールドを削除
        
        with pytest.raises(PodcastPublishError, match="エピソードデータが不正です"):
            publisher.publish_episode(sample_episode, '/tmp/audio.mp3')
            
    def test_publish_to_rss_success(self, publisher, sample_episode):
        """RSS配信成功テスト"""
        # モック設定
        publisher._get_existing_episodes = Mock(return_value=[])
        publisher.rss_generator.generate_rss_feed = Mock(return_value='/tmp/rss.xml')
        publisher._deploy_to_github_pages = Mock(return_value=True)
        
        # 実行
        result = publisher._publish_to_rss(sample_episode)
        
        # 検証
        assert result is True
        publisher.rss_generator.generate_rss_feed.assert_called_once()
        publisher._deploy_to_github_pages.assert_called_once_with('/tmp/rss.xml')
        
    def test_publish_to_rss_deployment_failure(self, publisher, sample_episode):
        """RSS配信時のデプロイ失敗テスト"""
        # モック設定
        publisher._get_existing_episodes = Mock(return_value=[])
        publisher.rss_generator.generate_rss_feed = Mock(return_value='/tmp/rss.xml')
        publisher._deploy_to_github_pages = Mock(return_value=False)
        
        # 実行
        result = publisher._publish_to_rss(sample_episode)
        
        # 検証
        assert result is False
        
    def test_publish_to_line_success(self, publisher, sample_episode):
        """LINE配信成功テスト"""
        # モック設定
        publisher.line_broadcaster.broadcast_episode = Mock(return_value=True)
        
        # 実行
        result = publisher._publish_to_line(sample_episode)
        
        # 検証
        assert result is True
        publisher.line_broadcaster.broadcast_episode.assert_called_once_with(sample_episode)
        
    def test_publish_to_line_failure(self, publisher, sample_episode):
        """LINE配信失敗テスト"""
        # モック設定
        publisher.line_broadcaster.broadcast_episode = Mock(return_value=False)
        
        # 実行
        result = publisher._publish_to_line(sample_episode)
        
        # 検証
        assert result is False
        
    def test_get_error_summary(self, publisher):
        """エラーサマリー取得テスト"""
        expected_summary = {
            'total_errors': 5,
            'error_types': {'rss_error': 3, 'line_error': 2},
            'channels': {'rss': 3, 'line': 2},
            'episodes_affected': 2
        }
        publisher.error_handler.get_error_summary = Mock(return_value=expected_summary)
        
        result = publisher.get_error_summary(24)
        
        assert result == expected_summary
        publisher.error_handler.get_error_summary.assert_called_once_with(24)
        
    def test_check_error_alerts(self, publisher):
        """エラーアラートチェックテスト"""
        publisher.error_handler.should_alert = Mock(return_value=True)
        
        result = publisher.check_error_alerts()
        
        assert result is True
        publisher.error_handler.should_alert.assert_called_once()
        
    def test_cleanup_error_logs(self, publisher):
        """エラーログクリーンアップテスト"""
        publisher.error_handler.error_tracker.cleanup_old_errors = Mock()
        
        publisher.cleanup_error_logs(30)
        
        publisher.error_handler.error_tracker.cleanup_old_errors.assert_called_once_with(30)
        
    @patch('pathlib.Path.glob')
    @patch('pathlib.Path.exists')
    def test_cleanup_old_episodes(self, mock_exists, mock_glob, publisher):
        """古いエピソードクリーンアップテスト"""
        # モック設定
        mock_exists.return_value = True
        mock_files = []
        for i in range(60):  # 60個のファイル
            mock_file = Mock()
            mock_file.stat.return_value.st_mtime = 1000000 + i
            mock_file.unlink = Mock()
            mock_files.append(mock_file)
        mock_glob.return_value = mock_files
        
        # 実行（50個を保持）
        publisher.cleanup_old_episodes(50)
        
        # 検証：古い10個のファイルが削除される
        for i in range(10):
            mock_files[59-i].unlink.assert_called_once()
            
    def test_get_publish_status(self, publisher):
        """配信状況取得テスト"""
        result = publisher.get_publish_status('ep-001')
        
        assert result['episode_guid'] == 'ep-001'
        assert 'rss_published' in result
        assert 'line_published' in result
        assert 'last_updated' in result


class TestPodcastPublisherIntegration:
    """PodcastPublisher 統合テスト"""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリ"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
            
    @pytest.fixture
    def integration_config(self, temp_dir):
        """統合テスト用Config"""
        config = Mock(spec=AppConfig)
        config.podcast = Mock(spec=PodcastConfig)
        config.podcast.max_file_size_mb = 15
        config.podcast.audio_output_dir = f"{temp_dir}/audio"
        config.podcast.rss_output_dir = f"{temp_dir}/rss"  
        config.podcast.error_log_dir = f"{temp_dir}/errors"
        config.podcast.max_publish_retries = 2
        config.podcast.publish_retry_delay = 0.1
        config.podcast.max_publish_retry_delay = 1.0
        return config
        
    def test_full_publish_flow_with_retries(self, integration_config, sample_episode):
        """再試行を含む完全な配信フローテスト"""
        with patch('src.podcast.publisher.podcast_publisher.RSSGenerator') as mock_rss_cls, \
             patch('src.podcast.publisher.podcast_publisher.LINEBroadcaster') as mock_line_cls:
             
            # RSS: 1回目失敗、2回目成功
            mock_rss = Mock()
            mock_rss.generate_rss_feed.side_effect = [Exception("Network error"), "/tmp/rss.xml"]
            mock_rss_cls.return_value = mock_rss
            
            # LINE: 成功
            mock_line = Mock()
            mock_line.broadcast_episode.return_value = True
            mock_line_cls.return_value = mock_line
            
            publisher = PodcastPublisher(integration_config)
            publisher._deploy_to_github_pages = Mock(return_value=True)
            
            # 音声ファイル作成
            audio_path = f"{integration_config.podcast.audio_output_dir}/../test_audio.mp3"
            Path(audio_path).parent.mkdir(parents=True, exist_ok=True)
            Path(audio_path).write_bytes(b"fake audio data")
            
            # 実行
            result = publisher.publish_episode(sample_episode, audio_path)
            
            # 検証
            assert result['rss'] is True  # 再試行で成功
            assert result['line'] is True
            assert result['overall_success'] is True
            
            # RSS生成が2回呼ばれることを確認（1回目失敗、2回目成功）
            assert mock_rss.generate_rss_feed.call_count == 2
            
    def test_error_tracking_and_summary(self, integration_config, sample_episode):
        """エラー追跡とサマリー機能テスト"""
        with patch('src.podcast.publisher.podcast_publisher.RSSGenerator') as mock_rss_cls, \
             patch('src.podcast.publisher.podcast_publisher.LINEBroadcaster') as mock_line_cls:
             
            # 両方のチャンネルで失敗
            mock_rss = Mock()
            mock_rss.generate_rss_feed.side_effect = Exception("RSS error")
            mock_rss_cls.return_value = mock_rss
            
            mock_line = Mock()
            mock_line.broadcast_episode.side_effect = Exception("LINE error")
            mock_line_cls.return_value = mock_line
            
            publisher = PodcastPublisher(integration_config)
            
            # 音声ファイル作成
            audio_path = f"{integration_config.podcast.audio_output_dir}/../test_audio.mp3"
            Path(audio_path).parent.mkdir(parents=True, exist_ok=True)
            Path(audio_path).write_bytes(b"fake audio data")
            
            # 実行（失敗予想）
            result = publisher.publish_episode(sample_episode, audio_path)
            
            # 検証
            assert result['rss'] is False
            assert result['line'] is False
            assert result['overall_success'] is False
            
            # エラーサマリー確認
            summary = publisher.get_error_summary(1)
            assert summary['total_errors'] > 0