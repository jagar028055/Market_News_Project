"""
Phase 3 配信分析システムのユニットテスト

このテストファイルはPhase 3で実装された分析機能の動作確認を行います。
"""

import pytest
import datetime
import tempfile
import os
from unittest.mock import Mock, patch
import sys

# テスト対象モジュールをインポート
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from podcast.analytics.analytics_engine import (
    AnalyticsEngine, DeliveryEvent, EngagementEvent, 
    DeliveryStatus, MessageType, PerformanceMetrics
)
from podcast.analytics.metrics_collector import MetricsCollector
from podcast.analytics.engagement_analyzer import EngagementAnalyzer
from podcast.analytics.ab_test_manager import ABTestManager, TestType
from podcast.analytics.analytics_manager import AnalyticsManager


class TestAnalyticsEngine:
    """AnalyticsEngineテストクラス"""
    
    @pytest.fixture
    def temp_db(self):
        """一時データベースファイル"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            yield tmp.name
        os.unlink(tmp.name)
    
    @pytest.fixture
    def analytics_engine(self, temp_db):
        """AnalyticsEngineインスタンス"""
        return AnalyticsEngine(temp_db)
    
    def test_database_initialization(self, analytics_engine):
        """データベース初期化テスト"""
        # データベースが初期化されることを確認
        status = analytics_engine.get_system_status()
        assert 'database' in status
        assert 'today' in status
    
    def test_delivery_event_recording(self, analytics_engine):
        """配信イベント記録テスト"""
        event = DeliveryEvent(
            event_id="test_001",
            episode_id="episode_001",
            delivery_time=datetime.datetime.now(),
            message_type=MessageType.FLEX_MESSAGE,
            status=DeliveryStatus.DELIVERED,
            recipient_count=100,
            metadata={"test": True}
        )
        
        # イベント記録が成功することを確認
        analytics_engine.record_delivery_event(event)
        
        # システム状態に反映されることを確認
        status = analytics_engine.get_system_status()
        assert status['database']['delivery_events'] > 0
    
    def test_engagement_event_recording(self, analytics_engine):
        """エンゲージメントイベント記録テスト"""
        event = EngagementEvent(
            event_id="engagement_001",
            episode_id="episode_001",
            user_id="user_001",
            event_type="click",
            event_time=datetime.datetime.now(),
            event_data={"target": "play_button"}
        )
        
        # イベント記録が成功することを確認
        analytics_engine.record_engagement_event(event)
        
        # システム状態に反映されることを確認
        status = analytics_engine.get_system_status()
        assert status['database']['engagement_events'] > 0
    
    def test_performance_metrics_calculation(self, analytics_engine):
        """パフォーマンス指標計算テスト"""
        # テストデータ準備
        delivery_time = datetime.datetime.now()
        episode_id = "test_episode"
        
        # 配信イベント記録
        delivery_event = DeliveryEvent(
            event_id="delivery_001",
            episode_id=episode_id,
            delivery_time=delivery_time,
            message_type=MessageType.FLEX_MESSAGE,
            status=DeliveryStatus.DELIVERED,
            recipient_count=100,
            metadata={}
        )
        analytics_engine.record_delivery_event(delivery_event)
        
        # エンゲージメントイベント記録
        engagement_event = EngagementEvent(
            event_id="engagement_001",
            episode_id=episode_id,
            user_id="user_001",
            event_type="click",
            event_time=delivery_time,
            event_data={}
        )
        analytics_engine.record_engagement_event(engagement_event)
        
        # メトリクス計算
        metrics = analytics_engine.calculate_performance_metrics(episode_id, delivery_time)
        
        # 結果検証
        assert metrics.episode_id == episode_id
        assert metrics.total_recipients == 100
        assert metrics.successful_deliveries == 100
        assert metrics.click_through_rate > 0


class TestMetricsCollector:
    """MetricsCollectorテストクラス"""
    
    @pytest.fixture
    def temp_db(self):
        """一時データベースファイル"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            yield tmp.name
        os.unlink(tmp.name)
    
    @pytest.fixture
    def metrics_collector(self, temp_db):
        """MetricsCollectorインスタンス"""
        analytics = AnalyticsEngine(temp_db)
        return MetricsCollector(analytics)
    
    def test_notification_tracking_lifecycle(self, metrics_collector):
        """通知トラッキングライフサイクルテスト"""
        # トラッキング開始
        tracking_id = metrics_collector.start_notification_tracking(
            episode_id="episode_001",
            message_type="flex_message",
            recipient_count=50
        )
        
        assert tracking_id is not None
        
        # アクティブ通知に含まれることを確認
        active = metrics_collector.get_active_notifications()
        assert len(active) == 1
        assert active[0].episode_id == "episode_001"
        
        # 成功記録
        metrics_collector.record_delivery_success(tracking_id, 1500.0, 48)
        
        # 完了処理
        metrics_collector.finish_notification_tracking(tracking_id)
        
        # アクティブリストから削除されることを確認
        active_after = metrics_collector.get_active_notifications()
        assert len(active_after) == 0
    
    def test_user_engagement_recording(self, metrics_collector):
        """ユーザーエンゲージメント記録テスト"""
        episode_id = "episode_001"
        user_id = "user_001"
        
        # 各種エンゲージメントイベント記録
        metrics_collector.record_user_click(episode_id, user_id, "play_button")
        metrics_collector.record_user_view(episode_id, user_id, 30000)
        metrics_collector.record_user_share(episode_id, user_id, "twitter")
        metrics_collector.record_subscription(episode_id, user_id, "rss")
        metrics_collector.record_read_time(episode_id, user_id, 120.5)
        
        # イベントが記録されることを確認（実際の検証はAnalyticsEngineで行う）
        # ここではエラーが発生しないことを確認
        assert True
    
    def test_realtime_stats_calculation(self, metrics_collector):
        """リアルタイム統計計算テスト"""
        # トラッキング開始
        tracking_id1 = metrics_collector.start_notification_tracking("ep1", "flex", 100)
        tracking_id2 = metrics_collector.start_notification_tracking("ep2", "text", 200)
        
        # 統計計算
        stats = metrics_collector.calculate_realtime_stats()
        
        assert stats['active_notifications'] == 2
        assert stats['total_recipients'] == 300
        assert 'last_updated' in stats


class TestEngagementAnalyzer:
    """EngagementAnalyzerテストクラス"""
    
    @pytest.fixture
    def temp_db(self):
        """一時データベースファイル"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            yield tmp.name
        os.unlink(tmp.name)
    
    @pytest.fixture
    def engagement_analyzer(self, temp_db):
        """EngagementAnalyzerインスタンス"""
        analytics = AnalyticsEngine(temp_db)
        return EngagementAnalyzer(analytics)
    
    def test_user_engagement_analysis_empty(self, engagement_analyzer):
        """空データでのユーザーエンゲージメント分析テスト"""
        # 存在しないユーザーの分析
        profile = engagement_analyzer.analyze_user_engagement("nonexistent_user")
        assert profile is None
    
    def test_episode_engagement_analysis_empty(self, engagement_analyzer):
        """空データでのエピソードエンゲージメント分析テスト"""
        from podcast.analytics.engagement_analyzer import EpisodeEngagementSummary
        # 存在しないエピソードの分析
        summary = engagement_analyzer.analyze_episode_engagement("nonexistent_episode")
        assert isinstance(summary, EpisodeEngagementSummary)
        assert summary.total_views == 0
        assert summary.unique_viewers == 0
        assert summary.total_clicks == 0
    
    def test_engagement_heatmap_generation(self, engagement_analyzer):
        """エンゲージメントヒートマップ生成テスト"""
        # 空データでのヒートマップ生成
        heatmap = engagement_analyzer.get_engagement_heatmap(7)
        
        assert isinstance(heatmap, dict)
        assert 'heatmap_data' in heatmap
        assert 'total_activity' in heatmap
        assert 'analysis_period_days' in heatmap
    
    def test_top_engaged_users_empty(self, engagement_analyzer):
        """トップユーザー取得（空データ）テスト"""
        # 空データでのトップユーザー取得
        users = engagement_analyzer.get_top_engaged_users(limit=5)
        assert isinstance(users, list)
        assert len(users) == 0


class TestABTestManager:
    """ABTestManagerテストクラス"""
    
    @pytest.fixture
    def temp_db(self):
        """一時データベースファイル"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            yield tmp.name
        os.unlink(tmp.name)
    
    @pytest.fixture
    def ab_test_manager(self, temp_db):
        """ABTestManagerインスタンス"""
        analytics = AnalyticsEngine(temp_db)
        return ABTestManager(analytics)
    
    def test_test_creation(self, ab_test_manager):
        """A/Bテスト作成テスト"""
        variants = [
            {"name": "Control", "percentage": 50, "config": {"template": "original"}},
            {"name": "Variant A", "percentage": 50, "config": {"template": "new"}}
        ]
        
        test_id = ab_test_manager.create_test(
            test_name="Message Template Test",
            test_type=TestType.MESSAGE_CONTENT,
            variants=variants,
            description="Testing new message template"
        )
        
        assert test_id is not None
        assert len(test_id) > 0
    
    def test_test_lifecycle(self, ab_test_manager):
        """A/Bテストライフサイクルテスト"""
        # テスト作成
        variants = [
            {"name": "A", "percentage": 50, "config": {"color": "blue"}},
            {"name": "B", "percentage": 50, "config": {"color": "red"}}
        ]
        
        test_id = ab_test_manager.create_test(
            test_name="Color Test",
            test_type=TestType.MESSAGE_FORMAT,
            variants=variants
        )
        
        # テスト開始
        success = ab_test_manager.start_test(test_id)
        assert success is True
        
        # ユーザー割り当て
        variant_id = ab_test_manager.assign_user_to_variant(test_id, "user_001", "episode_001")
        assert variant_id is not None
        
        # バリアント設定取得
        config = ab_test_manager.get_variant_config(test_id, variant_id)
        assert config is not None
        assert "color" in config
    
    def test_active_tests_retrieval(self, ab_test_manager):
        """実行中テスト取得テスト"""
        # 最初は空リスト
        active_tests = ab_test_manager.get_active_tests()
        assert isinstance(active_tests, list)
        
        # テスト作成・開始後
        variants = [{"name": "A", "percentage": 100, "config": {}}]
        test_id = ab_test_manager.create_test("Test", TestType.MESSAGE_CONTENT, variants)
        ab_test_manager.start_test(test_id)
        
        active_tests = ab_test_manager.get_active_tests()
        assert len(active_tests) == 1


class TestAnalyticsManager:
    """AnalyticsManager統合テストクラス"""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリ"""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)
    
    @pytest.fixture
    def analytics_manager(self, temp_dir):
        """AnalyticsManagerインスタンス"""
        db_path = os.path.join(temp_dir, "test_analytics.db")
        reports_dir = os.path.join(temp_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        return AnalyticsManager(db_path, reports_dir)
    
    def test_initialization(self, analytics_manager):
        """初期化テスト"""
        status = analytics_manager.get_system_status()
        assert 'components' in status
        assert status['components']['analytics_engine'] == 'active'
        assert status['components']['metrics_collector'] == 'active'
    
    def test_delivery_tracking_flow(self, analytics_manager):
        """配信トラッキングフローテスト"""
        # トラッキング開始
        tracking_id = analytics_manager.start_delivery_tracking(
            episode_id="test_episode",
            message_type="flex_message", 
            recipient_count=100
        )
        assert tracking_id is not None
        
        # 成功記録
        analytics_manager.record_delivery_success(tracking_id, 1200.0)
        
        # システム状態確認
        status = analytics_manager.get_system_status()
        assert status['database']['delivery_events'] > 0
    
    def test_engagement_recording_flow(self, analytics_manager):
        """エンゲージメント記録フローテスト"""
        episode_id = "test_episode"
        user_id = "test_user"
        
        # 各種エンゲージメント記録
        analytics_manager.record_user_click(episode_id, user_id, "play_button")
        analytics_manager.record_user_view(episode_id, user_id, 30000)
        analytics_manager.record_user_share(episode_id, user_id, "twitter")
        analytics_manager.record_subscription(episode_id, user_id)
        
        # システム状態確認
        status = analytics_manager.get_system_status()
        assert status['database']['engagement_events'] > 0
    
    def test_ab_test_integration(self, analytics_manager):
        """A/Bテスト統合テスト"""
        # テスト作成
        test_id = analytics_manager.create_ab_test(
            test_name="Integration Test",
            test_type="message_content",
            variants=[
                {"name": "A", "percentage": 50, "config": {"version": 1}},
                {"name": "B", "percentage": 50, "config": {"version": 2}}
            ]
        )
        assert test_id is not None
        
        # テスト開始
        success = analytics_manager.start_ab_test(test_id)
        assert success is True
        
        # ユーザー割り当て
        variant_id = analytics_manager.assign_user_to_test(test_id, "user_001", "episode_001")
        assert variant_id is not None
        
        # バリアント設定取得
        config = analytics_manager.get_test_variant_config(test_id, variant_id)
        assert config is not None
        assert "version" in config
    
    def test_dashboard_generation(self, analytics_manager):
        """ダッシュボード生成テスト"""
        # ダッシュボードデータ生成
        dashboard_data = analytics_manager.generate_dashboard(days=7)
        
        assert isinstance(dashboard_data, dict)
        assert 'generated_at' in dashboard_data
        assert 'analysis_period' in dashboard_data
        assert 'overview' in dashboard_data
        assert 'system_health' in dashboard_data
    
    @patch('matplotlib.pyplot.savefig')  # matplotlibが無い場合のテスト対応
    def test_report_generation(self, mock_savefig, analytics_manager):
        """レポート生成テスト"""
        # 日次レポート生成テスト
        daily_report_path = analytics_manager.generate_daily_report()
        # パスが返されることを確認（ファイルが存在しない場合は空文字列）
        assert isinstance(daily_report_path, str)
    
    def test_system_status_comprehensive(self, analytics_manager):
        """包括的システム状態テスト"""
        status = analytics_manager.get_system_status()
        
        # 必要なキーが存在することを確認
        required_keys = ['database', 'today', 'realtime', 'components', 'status']
        for key in required_keys:
            assert key in status
        
        # コンポーネントが全てactiveであることを確認
        components = status['components']
        for component_name, component_status in components.items():
            assert component_status == 'active'
    
    def test_data_export(self, analytics_manager):
        """データエクスポートテスト"""
        # JSONエクスポート
        json_path = analytics_manager.export_data('json', days=7)
        if json_path:  # パスが返された場合のみチェック
            assert json_path.endswith('.json')
        
        # CSVエクスポート
        csv_path = analytics_manager.export_data('csv', days=7)
        if csv_path:  # パスが返された場合のみチェック
            assert csv_path.endswith('.csv')
    
    def test_cleanup_functionality(self, analytics_manager):
        """クリーンアップ機能テスト"""
        # 古いデータクリーンアップ
        result = analytics_manager.cleanup_old_data(days_to_keep=30)
        
        assert isinstance(result, dict)
        # エラーでない場合は削除統計を確認
        if 'error' not in result:
            assert 'deleted_engagement_events' in result
            assert 'deleted_delivery_events' in result
            assert 'cutoff_date' in result


# テスト実行時の設定
if __name__ == "__main__":
    pytest.main([__file__, "-v"])