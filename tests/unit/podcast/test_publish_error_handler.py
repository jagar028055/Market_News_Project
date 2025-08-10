"""配信エラーハンドリング機能のテスト"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from src.podcast.error_handling.publish_error_handler import (
    PublishErrorHandler,
    PublishErrorTracker, 
    PublishRetryStrategy,
    PublishErrorType
)
from src.config.app_config import AppConfig, PodcastConfig


class TestPublishRetryStrategy:
    """PublishRetryStrategy クラスのテスト"""
    
    def test_init_default_values(self):
        """デフォルト値での初期化テスト"""
        strategy = PublishRetryStrategy()
        assert strategy.max_retries == 3
        assert strategy.base_delay == 1.0
        assert strategy.max_delay == 60.0
        
    def test_init_custom_values(self):
        """カスタム値での初期化テスト"""
        strategy = PublishRetryStrategy(max_retries=5, base_delay=2.0, max_delay=30.0)
        assert strategy.max_retries == 5
        assert strategy.base_delay == 2.0
        assert strategy.max_delay == 30.0
        
    def test_get_delay_exponential_backoff(self):
        """指数バックオフ遅延計算テスト"""
        strategy = PublishRetryStrategy(base_delay=1.0, max_delay=10.0)
        
        assert strategy.get_delay(0) == 1.0  # 1.0 * 2^0
        assert strategy.get_delay(1) == 2.0  # 1.0 * 2^1
        assert strategy.get_delay(2) == 4.0  # 1.0 * 2^2
        assert strategy.get_delay(3) == 8.0  # 1.0 * 2^3
        assert strategy.get_delay(4) == 10.0  # max_delay制限
        
    def test_should_retry_under_max_retries(self):
        """最大再試行回数未満での再試行判定テスト"""
        strategy = PublishRetryStrategy(max_retries=3)
        
        assert strategy.should_retry(PublishErrorType.NETWORK_ERROR, 0) is True
        assert strategy.should_retry(PublishErrorType.NETWORK_ERROR, 2) is True
        
    def test_should_retry_over_max_retries(self):
        """最大再試行回数超過での再試行判定テスト"""
        strategy = PublishRetryStrategy(max_retries=3)
        
        assert strategy.should_retry(PublishErrorType.NETWORK_ERROR, 3) is False
        assert strategy.should_retry(PublishErrorType.NETWORK_ERROR, 5) is False
        
    def test_should_retry_configuration_error(self):
        """設定エラーでの再試行判定テスト（再試行しない）"""
        strategy = PublishRetryStrategy(max_retries=3)
        
        assert strategy.should_retry(PublishErrorType.CONFIGURATION_ERROR, 0) is False
        assert strategy.should_retry(PublishErrorType.CONFIGURATION_ERROR, 1) is False
        
    def test_should_retry_rate_limit_error(self):
        """レート制限エラーでの再試行判定テスト（制限回数）"""
        strategy = PublishRetryStrategy(max_retries=3)
        
        assert strategy.should_retry(PublishErrorType.LINE_RATE_LIMIT, 0) is True
        assert strategy.should_retry(PublishErrorType.LINE_RATE_LIMIT, 1) is True
        assert strategy.should_retry(PublishErrorType.LINE_RATE_LIMIT, 2) is False  # 最大2回まで


class TestPublishErrorTracker:
    """PublishErrorTracker クラスのテスト"""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリ"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
            
    @pytest.fixture
    def mock_config(self, temp_dir):
        """モックConfig"""
        config = Mock(spec=AppConfig)
        config.podcast = Mock(spec=PodcastConfig)
        config.podcast.error_log_dir = temp_dir
        return config
        
    @pytest.fixture  
    def error_tracker(self, mock_config):
        """ErrorTracker インスタンス"""
        return PublishErrorTracker(mock_config)
        
    def test_init_creates_directory(self, mock_config):
        """初期化時のディレクトリ作成テスト"""
        error_log_path = Path(mock_config.podcast.error_log_dir) / "publish_errors.json"
        
        tracker = PublishErrorTracker(mock_config)
        
        assert error_log_path.parent.exists()
        assert tracker.error_log_path == error_log_path
        
    def test_record_error(self, error_tracker):
        """エラー記録テスト"""
        error_tracker.record_error(
            "ep-001", 
            "rss", 
            PublishErrorType.RSS_GENERATION_ERROR,
            "Generation failed",
            1
        )
        
        errors = error_tracker.get_episode_errors("ep-001")
        assert len(errors) == 1
        assert errors[0]['episode_guid'] == "ep-001"
        assert errors[0]['channel'] == "rss"
        assert errors[0]['error_type'] == PublishErrorType.RSS_GENERATION_ERROR.value
        assert errors[0]['error_message'] == "Generation failed"
        assert errors[0]['attempt'] == 1
        
    def test_record_multiple_errors_same_episode(self, error_tracker):
        """同一エピソードの複数エラー記録テスト"""
        error_tracker.record_error("ep-001", "rss", PublishErrorType.RSS_GENERATION_ERROR, "Error 1", 1)
        error_tracker.record_error("ep-001", "line", PublishErrorType.LINE_API_ERROR, "Error 2", 1)
        
        errors = error_tracker.get_episode_errors("ep-001")
        assert len(errors) == 2
        
    def test_get_recent_errors(self, error_tracker):
        """最近のエラー取得テスト"""
        # 最近のエラー
        error_tracker.record_error("ep-001", "rss", PublishErrorType.RSS_GENERATION_ERROR, "Recent error", 1)
        
        # 古いエラー（手動でタイムスタンプを変更）
        old_timestamp = (datetime.now() - timedelta(days=2)).isoformat()
        error_tracker.errors["ep-002"] = [{
            'timestamp': old_timestamp,
            'episode_guid': 'ep-002',
            'channel': 'line',
            'error_type': 'line_api_error',
            'error_message': 'Old error',
            'attempt': 1
        }]
        
        recent_errors = error_tracker.get_recent_errors(24)
        
        # 最近のエラーのみ取得されることを確認
        assert len(recent_errors) == 1
        assert recent_errors[0]['episode_guid'] == "ep-001"
        
    def test_cleanup_old_errors(self, error_tracker):
        """古いエラーログクリーンアップテスト"""
        # 最近のエラー
        error_tracker.record_error("ep-001", "rss", PublishErrorType.RSS_GENERATION_ERROR, "Recent error", 1)
        
        # 古いエラー
        old_timestamp = (datetime.now() - timedelta(days=40)).isoformat()
        error_tracker.errors["ep-002"] = [{
            'timestamp': old_timestamp,
            'episode_guid': 'ep-002',
            'channel': 'line',
            'error_type': 'line_api_error',
            'error_message': 'Old error',
            'attempt': 1
        }]
        
        # クリーンアップ実行（30日より古いエラーを削除）
        error_tracker.cleanup_old_errors(30)
        
        # 最近のエラーは残り、古いエラーは削除される
        assert "ep-001" in error_tracker.errors
        assert "ep-002" not in error_tracker.errors
        
    def test_save_and_load_error_log(self, error_tracker):
        """エラーログ保存・読み込みテスト"""
        # エラーを記録
        error_tracker.record_error("ep-001", "rss", PublishErrorType.RSS_GENERATION_ERROR, "Test error", 1)
        
        # 新しいインスタンスで読み込み
        new_tracker = PublishErrorTracker(error_tracker.config)
        
        # データが正しく読み込まれることを確認
        errors = new_tracker.get_episode_errors("ep-001")
        assert len(errors) == 1
        assert errors[0]['error_message'] == "Test error"


class TestPublishErrorHandler:
    """PublishErrorHandler クラスのテスト"""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリ"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
            
    @pytest.fixture
    def mock_config(self, temp_dir):
        """モックConfig"""
        config = Mock(spec=AppConfig)
        config.podcast = Mock(spec=PodcastConfig)
        config.podcast.error_log_dir = temp_dir
        config.podcast.max_publish_retries = 3
        config.podcast.publish_retry_delay = 0.1  # テスト用に短く
        config.podcast.max_publish_retry_delay = 1.0
        return config
        
    @pytest.fixture
    def error_handler(self, mock_config):
        """ErrorHandler インスタンス"""
        return PublishErrorHandler(mock_config)
        
    def test_init(self, mock_config):
        """初期化テスト"""
        handler = PublishErrorHandler(mock_config)
        
        assert handler.config == mock_config
        assert isinstance(handler.retry_strategy, PublishRetryStrategy)
        assert isinstance(handler.error_tracker, PublishErrorTracker)
        
    def test_execute_with_retry_success_first_attempt(self, error_handler):
        """1回目で成功する関数の実行テスト"""
        mock_func = Mock(return_value=True)
        
        result = error_handler.execute_with_retry(mock_func, "ep-001", "rss", "arg1", kwarg1="value1")
        
        assert result is True
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
        
    def test_execute_with_retry_success_after_retries(self, error_handler):
        """再試行後に成功する関数の実行テスト"""
        mock_func = Mock(side_effect=[False, False, True])  # 3回目で成功
        
        start_time = time.time()
        result = error_handler.execute_with_retry(mock_func, "ep-001", "rss")
        end_time = time.time()
        
        assert result is True
        assert mock_func.call_count == 3
        # 遅延が発生していることを確認（少なくとも0.1 + 0.2 = 0.3秒）
        assert (end_time - start_time) >= 0.3
        
    def test_execute_with_retry_failure_all_attempts(self, error_handler):
        """全ての再試行が失敗する関数の実行テスト"""
        mock_func = Mock(return_value=False)
        
        result = error_handler.execute_with_retry(mock_func, "ep-001", "rss")
        
        assert result is False
        assert mock_func.call_count == 4  # 初回 + 3回の再試行
        
    def test_execute_with_retry_exception_handling(self, error_handler):
        """例外発生時の再試行テスト"""
        mock_func = Mock(side_effect=[Exception("Network error"), Exception("Network error"), True])
        
        result = error_handler.execute_with_retry(mock_func, "ep-001", "rss")
        
        assert result is True
        assert mock_func.call_count == 3
        
        # エラーが記録されることを確認
        errors = error_handler.error_tracker.get_episode_errors("ep-001")
        assert len(errors) == 2  # 最初の2回の失敗が記録される
        
    def test_classify_error_type_network_error(self, error_handler):
        """ネットワークエラー分類テスト"""
        error = Exception("Connection timeout")
        error_type = error_handler._classify_error_type(error, "rss")
        assert error_type == PublishErrorType.NETWORK_ERROR
        
    def test_classify_error_type_line_rate_limit(self, error_handler):
        """LINEレート制限エラー分類テスト"""
        error = Exception("Rate limit exceeded")
        error_type = error_handler._classify_error_type(error, "line")
        assert error_type == PublishErrorType.LINE_RATE_LIMIT
        
    def test_classify_error_type_rss_deployment(self, error_handler):
        """RSSデプロイエラー分類テスト"""
        error = Exception("Git deployment failed")
        error_type = error_handler._classify_error_type(error, "rss")
        assert error_type == PublishErrorType.RSS_DEPLOYMENT_ERROR
        
    def test_handle_partial_success(self, error_handler):
        """部分的成功処理テスト"""
        episode = {"guid": "ep-001", "title": "Test Episode"}
        results = {"rss": True, "line": False, "overall_success": False}
        
        # モック設定
        error_handler._retry_rss_publish = Mock(return_value=True)
        error_handler._retry_line_publish = Mock(return_value=True)
        
        final_results = error_handler.handle_partial_success(episode, results)
        
        # LINE配信の再試行のみが実行される
        error_handler._retry_rss_publish.assert_not_called()
        error_handler._retry_line_publish.assert_called_once_with(episode)
        
        # 最終結果が更新される
        assert final_results['rss'] is True
        assert final_results['line'] is True
        assert final_results['overall_success'] is True
        
    def test_get_error_summary(self, error_handler):
        """エラーサマリー取得テスト"""
        # テスト用エラーを追加
        error_handler.error_tracker.record_error("ep-001", "rss", PublishErrorType.RSS_GENERATION_ERROR, "Error 1", 1)
        error_handler.error_tracker.record_error("ep-001", "line", PublishErrorType.LINE_API_ERROR, "Error 2", 1)
        error_handler.error_tracker.record_error("ep-002", "rss", PublishErrorType.RSS_GENERATION_ERROR, "Error 3", 1)
        
        summary = error_handler.get_error_summary(24)
        
        assert summary['total_errors'] == 3
        assert summary['error_types']['rss_generation_error'] == 2
        assert summary['error_types']['line_api_error'] == 1
        assert summary['channels']['rss'] == 2
        assert summary['channels']['line'] == 1
        assert summary['episodes_affected'] == 2
        
    def test_should_alert_threshold_exceeded(self, error_handler):
        """アラート閾値超過テスト"""
        # 6個のエラーを追加（閾値5を超過）
        for i in range(6):
            error_handler.error_tracker.record_error(f"ep-{i}", "rss", PublishErrorType.RSS_GENERATION_ERROR, f"Error {i}", 1)
            
        assert error_handler.should_alert(error_threshold=5, time_window_hours=1) is True
        
    def test_should_alert_threshold_not_exceeded(self, error_handler):
        """アラート閾値未満テスト"""
        # 3個のエラーを追加（閾値5未満）
        for i in range(3):
            error_handler.error_tracker.record_error(f"ep-{i}", "rss", PublishErrorType.RSS_GENERATION_ERROR, f"Error {i}", 1)
            
        assert error_handler.should_alert(error_threshold=5, time_window_hours=1) is False


class TestPublishErrorHandlerIntegration:
    """PublishErrorHandler 統合テスト"""
    
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
        config.podcast.error_log_dir = temp_dir
        config.podcast.max_publish_retries = 2
        config.podcast.publish_retry_delay = 0.1
        config.podcast.max_publish_retry_delay = 1.0
        return config
        
    def test_full_error_handling_flow(self, integration_config):
        """完全なエラーハンドリングフローテスト"""
        handler = PublishErrorHandler(integration_config)
        
        # 失敗→成功のパターンでテスト
        call_count = 0
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary failure")
            return True
            
        # 実行
        result = handler.execute_with_retry(flaky_function, "ep-001", "test_channel")
        
        # 検証
        assert result is True
        assert call_count == 3  # 1回目、2回目失敗、3回目成功
        
        # エラーが正しく記録されることを確認
        errors = handler.error_tracker.get_episode_errors("ep-001")
        assert len(errors) == 2  # 最初の2回の失敗
        
        # エラーサマリーの確認
        summary = handler.get_error_summary(1)
        assert summary['total_errors'] == 2
        assert summary['episodes_affected'] == 1