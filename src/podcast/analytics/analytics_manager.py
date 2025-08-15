"""
配信分析システム統合管理

Phase 3のすべての分析機能を統合管理するメインクラス
"""

import logging
import datetime
from typing import Dict, List, Optional, Any
from .analytics_engine import AnalyticsEngine
from .metrics_collector import MetricsCollector
from .engagement_analyzer import EngagementAnalyzer
from .ab_test_manager import ABTestManager
from .dashboard_generator import DashboardGenerator
from .report_generator import ReportGenerator, ReportType


class AnalyticsManager:
    """配信分析システム統合管理"""
    
    def __init__(self, db_path: str = "podcast_analytics.db", output_dir: str = "reports"):
        self.logger = logging.getLogger(__name__)
        
        # コンポーネント初期化
        self.analytics = AnalyticsEngine(db_path)
        self.metrics = MetricsCollector(self.analytics)
        self.engagement = EngagementAnalyzer(self.analytics)
        self.ab_tests = ABTestManager(self.analytics)
        self.dashboard = DashboardGenerator(self.analytics, self.engagement, self.ab_tests)
        self.reports = ReportGenerator(self.analytics, self.engagement, self.ab_tests, output_dir)
        
        self.logger.info("配信分析システム初期化完了")
    
    # === 配信トラッキング ===
    def start_delivery_tracking(self, episode_id: str, message_type: str, recipient_count: int) -> str:
        """配信トラッキング開始"""
        return self.metrics.start_notification_tracking(episode_id, message_type, recipient_count)
    
    def record_delivery_success(self, tracking_id: str, response_time_ms: float, actual_count: Optional[int] = None):
        """配信成功記録"""
        self.metrics.record_delivery_success(tracking_id, response_time_ms, actual_count)
        self.metrics.finish_notification_tracking(tracking_id)
    
    def record_delivery_failure(self, tracking_id: str, error_message: str, failed_count: Optional[int] = None):
        """配信失敗記録"""
        self.metrics.record_delivery_failure(tracking_id, error_message, failed_count)
        self.metrics.finish_notification_tracking(tracking_id)
    
    # === ユーザーエンゲージメント記録 ===
    def record_user_click(self, episode_id: str, user_id: str, click_target: str, additional_data: Optional[Dict[str, Any]] = None):
        """ユーザークリック記録"""
        self.metrics.record_user_click(episode_id, user_id, click_target, additional_data)
    
    def record_user_view(self, episode_id: str, user_id: str, view_duration_ms: Optional[int] = None):
        """ユーザービュー記録"""
        self.metrics.record_user_view(episode_id, user_id, view_duration_ms)
    
    def record_user_share(self, episode_id: str, user_id: str, share_platform: str):
        """ユーザーシェア記録"""
        self.metrics.record_user_share(episode_id, user_id, share_platform)
    
    def record_subscription(self, episode_id: str, user_id: str, subscription_type: str = 'rss'):
        """購読記録"""
        self.metrics.record_subscription(episode_id, user_id, subscription_type)
    
    # === パフォーマンス分析 ===
    def calculate_episode_performance(self, episode_id: str, delivery_time: datetime.datetime) -> Dict[str, Any]:
        """エピソードパフォーマンス計算"""
        metrics = self.analytics.calculate_performance_metrics(episode_id, delivery_time)
        engagement_summary = self.engagement.analyze_episode_engagement(episode_id)
        
        return {
            'performance_metrics': metrics,
            'engagement_summary': engagement_summary,
            'analysis_time': datetime.datetime.now().isoformat()
        }
    
    def get_performance_trends(self, days: int = 7) -> List[Dict[str, Any]]:
        """パフォーマンストレンド取得"""
        trends = self.analytics.get_performance_trends(days)
        
        return [
            {
                'episode_id': trend.episode_id,
                'delivery_time': trend.delivery_time.isoformat(),
                'total_recipients': trend.total_recipients,
                'successful_deliveries': trend.successful_deliveries,
                'click_through_rate': trend.click_through_rate,
                'engagement_rate': trend.engagement_rate,
                'conversion_rate': trend.conversion_rate,
                'avg_read_time': trend.avg_read_time
            } for trend in trends
        ]
    
    def get_top_performing_episodes(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """高パフォーマンスエピソード取得"""
        trends = self.analytics.get_performance_trends(days)
        
        # エンゲージメント率でソート
        top_episodes = sorted(trends, key=lambda x: x.engagement_rate, reverse=True)[:limit]
        
        results = []
        for episode in top_episodes:
            engagement_summary = self.engagement.analyze_episode_engagement(episode.episode_id)
            results.append({
                'episode_id': episode.episode_id,
                'delivery_time': episode.delivery_time.isoformat(),
                'engagement_rate': episode.engagement_rate,
                'click_through_rate': episode.click_through_rate,
                'total_views': engagement_summary.total_views if engagement_summary else 0,
                'total_shares': engagement_summary.total_shares if engagement_summary else 0,
                'engagement_score': engagement_summary.engagement_score if engagement_summary else 0
            })
        
        return results
    
    # === A/Bテスト管理 ===
    def create_ab_test(
        self,
        test_name: str,
        test_type: str,
        variants: List[Dict[str, Any]],
        description: str = "",
        duration_days: int = 7
    ) -> str:
        """A/Bテスト作成"""
        from .ab_test_manager import TestType
        
        test_type_enum = TestType(test_type.lower())
        return self.ab_tests.create_test(test_name, test_type_enum, variants, description, duration_days)
    
    def start_ab_test(self, test_id: str) -> bool:
        """A/Bテスト開始"""
        return self.ab_tests.start_test(test_id)
    
    def assign_user_to_test(self, test_id: str, user_id: str, episode_id: str) -> Optional[str]:
        """ユーザーをA/Bテストに割り当て"""
        return self.ab_tests.assign_user_to_variant(test_id, user_id, episode_id)
    
    def get_test_variant_config(self, test_id: str, variant_id: str) -> Optional[Dict[str, Any]]:
        """テストバリアント設定取得"""
        return self.ab_tests.get_variant_config(test_id, variant_id)
    
    def complete_ab_test(self, test_id: str) -> Dict[str, Any]:
        """A/Bテスト完了と結果取得"""
        success = self.ab_tests.complete_test(test_id)
        if success:
            return self.ab_tests.get_test_results(test_id)
        return {}
    
    def get_active_ab_tests(self) -> List[Dict[str, Any]]:
        """実行中A/Bテスト一覧"""
        return self.ab_tests.get_active_tests()
    
    # === エンゲージメント分析 ===
    def analyze_user_engagement(self, user_id: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """ユーザーエンゲージメント分析"""
        profile = self.engagement.analyze_user_engagement(user_id, days)
        
        if profile:
            return {
                'user_id': profile.user_id,
                'total_interactions': profile.total_interactions,
                'unique_episodes': profile.unique_episodes,
                'avg_read_time': profile.avg_read_time,
                'favorite_time_slots': profile.favorite_time_slots,
                'engagement_score': profile.engagement_score,
                'last_activity': profile.last_activity.isoformat(),
                'subscription_status': profile.subscription_status
            }
        return None
    
    def get_engagement_heatmap(self, days: int = 7) -> Dict[str, Any]:
        """エンゲージメントヒートマップ取得"""
        return self.engagement.get_engagement_heatmap(days)
    
    def get_top_engaged_users(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """トップエンゲージメントユーザー取得"""
        users = self.engagement.get_top_engaged_users(limit, days)
        
        return [
            {
                'user_id': user.user_id,
                'total_interactions': user.total_interactions,
                'unique_episodes': user.unique_episodes,
                'engagement_score': user.engagement_score,
                'avg_read_time': user.avg_read_time,
                'subscription_status': user.subscription_status
            } for user in users
        ]
    
    # === ダッシュボード ===
    def generate_dashboard(self, days: int = 7) -> Dict[str, Any]:
        """ダッシュボード生成"""
        return self.dashboard.generate_dashboard_data(days)
    
    def save_dashboard_html(self, days: int = 7, output_path: Optional[str] = None) -> str:
        """ダッシュボードHTML保存"""
        data = self.generate_dashboard(days)
        
        if output_path is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"reports/dashboard_{timestamp}.html"
        
        self.dashboard.save_dashboard_html(data, output_path)
        return output_path
    
    # === レポート生成 ===
    def generate_daily_report(self) -> str:
        """日次レポート生成"""
        result = self.reports.generate_daily_report()
        return result.file_path if result.success else ""
    
    def generate_weekly_report(self) -> str:
        """週次レポート生成"""
        result = self.reports.generate_weekly_report()
        return result.file_path if result.success else ""
    
    def generate_monthly_report(self) -> str:
        """月次レポート生成"""
        result = self.reports.generate_monthly_report()
        return result.file_path if result.success else ""
    
    def generate_ab_test_report(self, test_id: str) -> str:
        """A/Bテストレポート生成"""
        result = self.reports.generate_ab_test_report(test_id)
        return result.file_path if result.success else ""
    
    # === システム管理 ===
    def get_system_status(self) -> Dict[str, Any]:
        """システムステータス取得"""
        base_status = self.analytics.get_system_status()
        realtime_stats = self.metrics.calculate_realtime_stats()
        
        return {
            **base_status,
            'realtime': realtime_stats,
            'components': {
                'analytics_engine': 'active',
                'metrics_collector': 'active',
                'engagement_analyzer': 'active', 
                'ab_test_manager': 'active',
                'dashboard_generator': 'active',
                'report_generator': 'active'
            }
        }
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """古いデータクリーンアップ"""
        try:
            # メトリクスコレクターのクリーンアップ
            self.metrics.cleanup_old_metrics(hours_old=24)
            
            # データベースの古いエンゲージメントイベントを削除
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
            
            import sqlite3
            with sqlite3.connect(self.analytics.db_path) as conn:
                # 古いエンゲージメントイベント削除
                result = conn.execute("""
                    DELETE FROM engagement_events 
                    WHERE created_at < ?
                """, (cutoff_date.isoformat(),))
                
                deleted_engagement = result.rowcount
                
                # 古い配信イベント削除
                result = conn.execute("""
                    DELETE FROM delivery_events 
                    WHERE created_at < ?
                """, (cutoff_date.isoformat(),))
                
                deleted_delivery = result.rowcount
            
            self.logger.info(f"データクリーンアップ完了: エンゲージメント{deleted_engagement}件、配信{deleted_delivery}件削除")
            
            return {
                'deleted_engagement_events': deleted_engagement,
                'deleted_delivery_events': deleted_delivery,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"データクリーンアップエラー: {e}")
            return {'error': str(e)}
    
    def export_data(self, output_format: str = 'json', days: int = 30) -> str:
        """データエクスポート"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # データ収集
            export_data = {
                'exported_at': datetime.datetime.now().isoformat(),
                'period_days': days,
                'performance_trends': self.get_performance_trends(days),
                'engagement_analysis': {
                    'trends': [
                        {
                            'date': trend.date.isoformat(),
                            'total_interactions': trend.total_interactions,
                            'unique_users': trend.unique_users,
                            'avg_engagement_score': trend.avg_engagement_score
                        } for trend in self.engagement.get_engagement_trends(days)
                    ],
                    'heatmap': self.get_engagement_heatmap(days)
                },
                'system_status': self.get_system_status()
            }
            
            # ファイル保存
            if output_format.lower() == 'json':
                import json
                output_path = f"reports/export_{timestamp}.json"
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            elif output_format.lower() == 'csv':
                import csv
                output_path = f"reports/export_{timestamp}.csv"
                
                # パフォーマンストレンドをCSVで出力
                trends = export_data['performance_trends']
                if trends:
                    with open(output_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=trends[0].keys())
                        writer.writeheader()
                        writer.writerows(trends)
            
            self.logger.info(f"データエクスポート完了: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"データエクスポートエラー: {e}")
            return ""
    
    def close(self):
        """リソースクリーンアップ"""
        # 必要に応じてデータベース接続などをクローズ
        self.logger.info("配信分析システム終了")