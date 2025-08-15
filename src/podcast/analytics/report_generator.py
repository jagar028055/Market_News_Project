"""
レポート自動生成システム

このモジュールは配信分析の定期レポートとカスタムレポートを自動生成します。
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
from .analytics_engine import AnalyticsEngine, PerformanceMetrics
from .engagement_analyzer import EngagementAnalyzer
from .ab_test_manager import ABTestManager
from .dashboard_generator import DashboardGenerator


class ReportType(Enum):
    """レポートタイプ"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    AB_TEST = "ab_test"
    CUSTOM = "custom"


class ReportFormat(Enum):
    """レポート形式"""
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    CSV = "csv"


@dataclass
class ReportConfig:
    """レポート設定"""
    report_id: str
    report_name: str
    report_type: ReportType
    report_format: ReportFormat
    schedule_expression: str  # cron形式
    recipients: List[str]
    include_charts: bool
    custom_metrics: List[str]
    metadata: Dict[str, Any]


@dataclass
class GeneratedReport:
    """生成されたレポート"""
    report_id: str
    config: ReportConfig
    generated_at: datetime.datetime
    file_path: str
    file_size: int
    execution_time_ms: float
    success: bool
    error_message: Optional[str]


class ReportGenerator:
    """レポート自動生成システム"""
    
    def __init__(
        self,
        analytics_engine: Optional[AnalyticsEngine] = None,
        engagement_analyzer: Optional[EngagementAnalyzer] = None,
        ab_test_manager: Optional[ABTestManager] = None,
        output_directory: str = "reports"
    ):
        self.analytics = analytics_engine or AnalyticsEngine()
        self.engagement = engagement_analyzer or EngagementAnalyzer(self.analytics)
        self.ab_tests = ab_test_manager or ABTestManager(self.analytics)
        self.dashboard = DashboardGenerator(self.analytics, self.engagement, self.ab_tests)
        self.output_dir = output_directory
        self.logger = logging.getLogger(__name__)
        
        # 出力ディレクトリ作成
        os.makedirs(output_directory, exist_ok=True)
    
    def generate_daily_report(self) -> GeneratedReport:
        """日次レポート生成"""
        config = ReportConfig(
            report_id="daily_" + datetime.datetime.now().strftime("%Y%m%d"),
            report_name="日次配信レポート",
            report_type=ReportType.DAILY,
            report_format=ReportFormat.HTML,
            schedule_expression="0 8 * * *",  # 毎日8時
            recipients=[],
            include_charts=True,
            custom_metrics=[],
            metadata={"generated_by": "auto_scheduler"}
        )
        
        return self._generate_report(config, days=1)
    
    def generate_weekly_report(self) -> GeneratedReport:
        """週次レポート生成"""
        config = ReportConfig(
            report_id="weekly_" + datetime.datetime.now().strftime("%Y_W%U"),
            report_name="週次配信分析レポート", 
            report_type=ReportType.WEEKLY,
            report_format=ReportFormat.HTML,
            schedule_expression="0 9 * * 1",  # 毎週月曜9時
            recipients=[],
            include_charts=True,
            custom_metrics=["engagement_trends", "top_users", "ab_test_summary"],
            metadata={"generated_by": "auto_scheduler"}
        )
        
        return self._generate_report(config, days=7)
    
    def generate_monthly_report(self) -> GeneratedReport:
        """月次レポート生成"""
        config = ReportConfig(
            report_id="monthly_" + datetime.datetime.now().strftime("%Y_%m"),
            report_name="月次総合分析レポート",
            report_type=ReportType.MONTHLY,
            report_format=ReportFormat.HTML,
            schedule_expression="0 10 1 * *",  # 毎月1日10時
            recipients=[],
            include_charts=True,
            custom_metrics=["performance_summary", "engagement_analysis", "growth_metrics", "recommendations"],
            metadata={"generated_by": "auto_scheduler"}
        )
        
        return self._generate_report(config, days=30)
    
    def generate_ab_test_report(self, test_id: str) -> GeneratedReport:
        """A/Bテストレポート生成"""
        config = ReportConfig(
            report_id=f"abtest_{test_id}",
            report_name=f"A/Bテスト結果レポート ({test_id})",
            report_type=ReportType.AB_TEST,
            report_format=ReportFormat.HTML,
            schedule_expression="",
            recipients=[],
            include_charts=False,
            custom_metrics=["test_results", "statistical_analysis"],
            metadata={"test_id": test_id}
        )
        
        return self._generate_ab_test_report(config, test_id)
    
    def generate_custom_report(self, config: ReportConfig, days: int = 7) -> GeneratedReport:
        """カスタムレポート生成"""
        return self._generate_report(config, days)
    
    def _generate_report(self, config: ReportConfig, days: int) -> GeneratedReport:
        """レポート生成（メイン処理）"""
        start_time = datetime.datetime.now()
        
        try:
            # データ収集
            report_data = self._collect_report_data(config, days)
            
            # レポート生成
            file_path = self._generate_report_file(config, report_data)
            
            # 実行時間計算
            execution_time = (datetime.datetime.now() - start_time).total_seconds() * 1000
            
            # ファイルサイズ取得
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            result = GeneratedReport(
                report_id=config.report_id,
                config=config,
                generated_at=start_time,
                file_path=file_path,
                file_size=file_size,
                execution_time_ms=execution_time,
                success=True,
                error_message=None
            )
            
            self.logger.info(f"レポート生成完了: {config.report_id} ({execution_time:.1f}ms)")
            return result
            
        except Exception as e:
            execution_time = (datetime.datetime.now() - start_time).total_seconds() * 1000
            error_msg = str(e)
            
            result = GeneratedReport(
                report_id=config.report_id,
                config=config,
                generated_at=start_time,
                file_path="",
                file_size=0,
                execution_time_ms=execution_time,
                success=False,
                error_message=error_msg
            )
            
            self.logger.error(f"レポート生成エラー: {config.report_id} - {error_msg}")
            return result
    
    def _generate_ab_test_report(self, config: ReportConfig, test_id: str) -> GeneratedReport:
        """A/Bテストレポート生成"""
        start_time = datetime.datetime.now()
        
        try:
            # テスト結果取得
            test_results = self.ab_tests.get_test_results(test_id)
            
            if not test_results:
                raise ValueError(f"テスト結果が見つかりません: {test_id}")
            
            # レポートデータ構築
            report_data = {
                'generated_at': start_time.isoformat(),
                'report_type': 'ab_test',
                'test_results': test_results,
                'analysis': self._analyze_ab_test_results(test_results),
                'recommendations': self._generate_ab_test_recommendations(test_results)
            }
            
            # ファイル生成
            file_path = self._generate_report_file(config, report_data)
            
            execution_time = (datetime.datetime.now() - start_time).total_seconds() * 1000
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            result = GeneratedReport(
                report_id=config.report_id,
                config=config,
                generated_at=start_time,
                file_path=file_path,
                file_size=file_size,
                execution_time_ms=execution_time,
                success=True,
                error_message=None
            )
            
            self.logger.info(f"A/Bテストレポート生成完了: {test_id}")
            return result
            
        except Exception as e:
            execution_time = (datetime.datetime.now() - start_time).total_seconds() * 1000
            
            result = GeneratedReport(
                report_id=config.report_id,
                config=config,
                generated_at=start_time,
                file_path="",
                file_size=0,
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e)
            )
            
            self.logger.error(f"A/Bテストレポート生成エラー: {e}")
            return result
    
    def _collect_report_data(self, config: ReportConfig, days: int) -> Dict[str, Any]:
        """レポートデータ収集"""
        data = {
            'generated_at': datetime.datetime.now().isoformat(),
            'report_config': asdict(config),
            'analysis_period': days
        }
        
        # 基本データ
        data['overview'] = self._generate_overview_data(days)
        data['performance_trends'] = self._get_performance_trends_data(days)
        data['system_status'] = self.analytics.get_system_status()
        
        # カスタムメトリクス
        for metric in config.custom_metrics:
            if metric == "engagement_trends":
                data['engagement_trends'] = self._get_engagement_trends_data(days)
            elif metric == "top_users":
                data['top_users'] = self._get_top_users_data(days)
            elif metric == "ab_test_summary":
                data['ab_test_summary'] = self._get_ab_test_summary()
            elif metric == "performance_summary":
                data['performance_summary'] = self._get_performance_summary(days)
            elif metric == "engagement_analysis":
                data['engagement_analysis'] = self._get_engagement_analysis(days)
            elif metric == "growth_metrics":
                data['growth_metrics'] = self._get_growth_metrics(days)
            elif metric == "recommendations":
                data['recommendations'] = self._generate_recommendations(days)
        
        return data
    
    def _generate_report_file(self, config: ReportConfig, data: Dict[str, Any]) -> str:
        """レポートファイル生成"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{config.report_id}_{timestamp}.{config.report_format.value}"
        file_path = os.path.join(self.output_dir, filename)
        
        if config.report_format == ReportFormat.JSON:
            self._save_json_report(file_path, data)
        elif config.report_format == ReportFormat.HTML:
            self._save_html_report(file_path, data, config)
        elif config.report_format == ReportFormat.MARKDOWN:
            self._save_markdown_report(file_path, data, config)
        elif config.report_format == ReportFormat.CSV:
            self._save_csv_report(file_path, data)
        
        return file_path
    
    def _save_json_report(self, file_path: str, data: Dict[str, Any]):
        """JSON形式でレポート保存"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_html_report(self, file_path: str, data: Dict[str, Any], config: ReportConfig):
        """HTML形式でレポート保存"""
        html_content = self._generate_html_report(data, config)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _save_markdown_report(self, file_path: str, data: Dict[str, Any], config: ReportConfig):
        """Markdown形式でレポート保存"""
        markdown_content = self._generate_markdown_report(data, config)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
    
    def _save_csv_report(self, file_path: str, data: Dict[str, Any]):
        """CSV形式でレポート保存"""
        import csv
        
        # パフォーマンストレンドをCSVで出力
        trends = data.get('performance_trends', [])
        if trends:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=trends[0].keys())
                writer.writeheader()
                writer.writerows(trends)
    
    def _generate_html_report(self, data: Dict[str, Any], config: ReportConfig) -> str:
        """HTMLレポート生成"""
        overview = data.get('overview', {})
        performance_trends = data.get('performance_trends', [])
        
        return f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.report_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
        .container {{ max-width: 1000px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #e9ecef; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric-box {{ background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; border-left: 4px solid #007bff; }}
        .metric-value {{ font-size: 1.8em; font-weight: bold; color: #495057; }}
        .metric-label {{ color: #6c757d; margin-top: 5px; font-size: 0.9em; }}
        .section {{ margin-bottom: 30px; }}
        .section-title {{ font-size: 1.4em; color: #343a40; margin-bottom: 15px; padding-bottom: 5px; border-bottom: 1px solid #dee2e6; }}
        .table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        .table th {{ background-color: #e9ecef; padding: 12px; text-align: left; font-weight: 600; }}
        .table td {{ padding: 10px 12px; border-bottom: 1px solid #dee2e6; }}
        .table tr:hover {{ background-color: #f8f9fa; }}
        .summary-text {{ line-height: 1.6; color: #495057; }}
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 0.9em; }}
        .highlight {{ background-color: #fff3cd; padding: 15px; border-radius: 4px; border-left: 4px solid #ffc107; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{config.report_name}</h1>
            <p>分析期間: {data.get('analysis_period', 7)}日間 | 生成日時: {data.get('generated_at', '')}</p>
        </div>
        
        <div class="section">
            <h2 class="section-title">📊 概要指標</h2>
            <div class="metric-grid">
                <div class="metric-box">
                    <div class="metric-value">{overview.get('total_episodes', 0)}</div>
                    <div class="metric-label">配信エピソード数</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">{overview.get('total_recipients', 0):,}</div>
                    <div class="metric-label">総配信数</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">{overview.get('delivery_rate', 0):.1f}%</div>
                    <div class="metric-label">配信成功率</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">{overview.get('avg_engagement_rate', 0):.1f}%</div>
                    <div class="metric-label">平均エンゲージメント率</div>
                </div>
            </div>
        </div>
        
        {self._render_performance_trends_section(performance_trends)}
        {self._render_engagement_section(data.get('engagement_analysis', {}))}
        {self._render_recommendations_section(data.get('recommendations', []))}
        {self._render_system_status_section(data.get('system_status', {}))}
        
        <div class="footer">
            <p>このレポートは自動生成されました - ポッドキャスト配信分析システム</p>
        </div>
    </div>
</body>
</html>
        """
    
    def _generate_markdown_report(self, data: Dict[str, Any], config: ReportConfig) -> str:
        """Markdownレポート生成"""
        overview = data.get('overview', {})
        
        md_content = f"""# {config.report_name}

**分析期間**: {data.get('analysis_period', 7)}日間  
**生成日時**: {data.get('generated_at', '')}

## 📊 概要指標

| 指標 | 値 |
|------|-----|
| 配信エピソード数 | {overview.get('total_episodes', 0)} |
| 総配信数 | {overview.get('total_recipients', 0):,} |
| 配信成功率 | {overview.get('delivery_rate', 0):.1f}% |
| 平均エンゲージメント率 | {overview.get('avg_engagement_rate', 0):.1f}% |
| 平均クリック率 | {overview.get('avg_click_through_rate', 0):.1f}% |

"""
        
        # パフォーマンストレンド
        performance_trends = data.get('performance_trends', [])
        if performance_trends:
            md_content += """## 📈 パフォーマンストレンド

| 日付 | エピソードID | 配信数 | エンゲージメント率 | クリック率 |
|------|-------------|--------|------------------|----------|
"""
            for trend in performance_trends[:10]:
                md_content += f"| {trend.get('date', '')} | {trend.get('episode_id', '')[:12]}... | {trend.get('recipients', 0):,} | {trend.get('engagement_rate', 0):.1f}% | {trend.get('click_through_rate', 0):.1f}% |\n"
        
        # 推奨事項
        recommendations = data.get('recommendations', [])
        if recommendations:
            md_content += "\n## 💡 推奨事項\n\n"
            for i, rec in enumerate(recommendations, 1):
                md_content += f"{i}. **{rec.get('title', '')}**: {rec.get('description', '')}\n"
        
        md_content += f"\n---\n\n*このレポートは自動生成されました - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*"
        
        return md_content
    
    def _render_performance_trends_section(self, trends: List[Dict[str, Any]]) -> str:
        """パフォーマンストレンドセクション生成"""
        if not trends:
            return ""
        
        table_rows = ""
        for trend in trends[:10]:  # 最新10件
            table_rows += f"""
            <tr>
                <td>{trend.get('date', '')}</td>
                <td>{trend.get('episode_id', '')[:16]}...</td>
                <td>{trend.get('recipients', 0):,}</td>
                <td>{trend.get('engagement_rate', 0):.1f}%</td>
                <td>{trend.get('click_through_rate', 0):.1f}%</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2 class="section-title">📈 パフォーマンストレンド</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>日付</th>
                        <th>エピソードID</th>
                        <th>配信数</th>
                        <th>エンゲージメント率</th>
                        <th>クリック率</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        """
    
    def _render_engagement_section(self, engagement_data: Dict[str, Any]) -> str:
        """エンゲージメントセクション生成"""
        if not engagement_data:
            return ""
        
        summary = engagement_data.get('summary', {})
        
        return f"""
        <div class="section">
            <h2 class="section-title">👥 エンゲージメント分析</h2>
            <div class="summary-text">
                <p>期間中の総インタラクション数: <strong>{summary.get('total_interactions', 0):,}件</strong></p>
                <p>ユニークユーザー数: <strong>{summary.get('unique_users', 0):,}人</strong></p>
                <p>平均エンゲージメントスコア: <strong>{summary.get('avg_engagement_score', 0):.1f}点</strong></p>
            </div>
        </div>
        """
    
    def _render_recommendations_section(self, recommendations: List[Dict[str, Any]]) -> str:
        """推奨事項セクション生成"""
        if not recommendations:
            return ""
        
        rec_items = ""
        for rec in recommendations:
            rec_items += f"""
            <div class="highlight">
                <strong>{rec.get('title', '')}</strong><br>
                {rec.get('description', '')}
            </div>
            """
        
        return f"""
        <div class="section">
            <h2 class="section-title">💡 推奨事項</h2>
            {rec_items}
        </div>
        """
    
    def _render_system_status_section(self, status: Dict[str, Any]) -> str:
        """システム状態セクション生成"""
        if not status:
            return ""
        
        health_color = {"healthy": "#28a745", "warning": "#ffc107", "critical": "#dc3545"}
        status_text = status.get('status', 'unknown')
        color = health_color.get(status_text, "#6c757d")
        
        return f"""
        <div class="section">
            <h2 class="section-title">🔧 システム状態</h2>
            <p>
                <span style="color: {color}; font-weight: bold;">● {status_text.title()}</span>
                (スコア: {status.get('overall_score', 0)}/100)
            </p>
        </div>
        """
    
    # データ収集ヘルパーメソッド
    def _generate_overview_data(self, days: int) -> Dict[str, Any]:
        """概要データ生成"""
        trends = self.analytics.get_performance_trends(days)
        
        if not trends:
            return {}
        
        total_recipients = sum(t.total_recipients for t in trends)
        total_delivered = sum(t.successful_deliveries for t in trends)
        avg_engagement = statistics.mean(t.engagement_rate for t in trends)
        avg_ctr = statistics.mean(t.click_through_rate for t in trends)
        
        return {
            'total_episodes': len(trends),
            'total_recipients': total_recipients,
            'total_delivered': total_delivered,
            'delivery_rate': (total_delivered / total_recipients * 100) if total_recipients > 0 else 0,
            'avg_engagement_rate': avg_engagement,
            'avg_click_through_rate': avg_ctr
        }
    
    def _get_performance_trends_data(self, days: int) -> List[Dict[str, Any]]:
        """パフォーマンストレンドデータ取得"""
        trends = self.analytics.get_performance_trends(days)
        
        return [
            {
                'date': trend.delivery_time.date().isoformat(),
                'episode_id': trend.episode_id,
                'recipients': trend.total_recipients,
                'delivered': trend.successful_deliveries,
                'engagement_rate': trend.engagement_rate,
                'click_through_rate': trend.click_through_rate
            } for trend in trends
        ]
    
    def _get_engagement_trends_data(self, days: int) -> Dict[str, Any]:
        """エンゲージメントトレンドデータ取得"""
        trends = self.engagement.get_engagement_trends(days)
        
        return {
            'trends': [asdict(trend) for trend in trends],
            'summary': {
                'total_interactions': sum(t.total_interactions for t in trends),
                'unique_users': sum(t.unique_users for t in trends),
                'avg_engagement_score': statistics.mean(t.avg_engagement_score for t in trends) if trends else 0
            }
        }
    
    def _get_top_users_data(self, days: int) -> List[Dict[str, Any]]:
        """トップユーザーデータ取得"""
        users = self.engagement.get_top_engaged_users(limit=10, days=days)
        return [asdict(user) for user in users]
    
    def _get_ab_test_summary(self) -> Dict[str, Any]:
        """A/Bテストサマリー取得"""
        active_tests = self.ab_tests.get_active_tests()
        
        return {
            'active_count': len(active_tests),
            'tests': active_tests
        }
    
    def _get_performance_summary(self, days: int) -> Dict[str, Any]:
        """パフォーマンスサマリー取得"""
        trends = self.analytics.get_performance_trends(days)
        
        if not trends:
            return {}
        
        return {
            'best_performance': max(trends, key=lambda x: x.engagement_rate),
            'worst_performance': min(trends, key=lambda x: x.engagement_rate),
            'avg_metrics': {
                'engagement_rate': statistics.mean(t.engagement_rate for t in trends),
                'click_through_rate': statistics.mean(t.click_through_rate for t in trends),
                'conversion_rate': statistics.mean(t.conversion_rate for t in trends)
            }
        }
    
    def _get_engagement_analysis(self, days: int) -> Dict[str, Any]:
        """エンゲージメント分析取得"""
        return self._get_engagement_trends_data(days)
    
    def _get_growth_metrics(self, days: int) -> Dict[str, Any]:
        """成長指標取得"""
        current_trends = self.analytics.get_performance_trends(days)
        previous_trends = self.analytics.get_performance_trends(days * 2)
        
        if len(previous_trends) < days:
            return {}
        
        previous_period = previous_trends[days:]
        
        current_avg_engagement = statistics.mean(t.engagement_rate for t in current_trends) if current_trends else 0
        previous_avg_engagement = statistics.mean(t.engagement_rate for t in previous_period) if previous_period else 0
        
        growth_rate = ((current_avg_engagement - previous_avg_engagement) / previous_avg_engagement * 100) if previous_avg_engagement > 0 else 0
        
        return {
            'engagement_growth_rate': growth_rate,
            'current_period_avg': current_avg_engagement,
            'previous_period_avg': previous_avg_engagement
        }
    
    def _generate_recommendations(self, days: int) -> List[Dict[str, Any]]:
        """推奨事項生成"""
        recommendations = []
        
        # パフォーマンス分析に基づく推奨事項
        trends = self.analytics.get_performance_trends(days)
        
        if trends:
            avg_engagement = statistics.mean(t.engagement_rate for t in trends)
            
            if avg_engagement < 5:
                recommendations.append({
                    'title': 'エンゲージメント率の改善',
                    'description': f'現在のエンゲージメント率({avg_engagement:.1f}%)は業界平均を下回っています。メッセージ内容やタイミングの見直しを検討してください。',
                    'priority': 'high'
                })
            
            # 配信失敗率チェック
            avg_delivery_rate = statistics.mean((t.successful_deliveries / t.total_recipients * 100) for t in trends if t.total_recipients > 0)
            
            if avg_delivery_rate < 95:
                recommendations.append({
                    'title': '配信信頼性の向上',
                    'description': f'配信成功率({avg_delivery_rate:.1f}%)が目標値を下回っています。配信システムの見直しが必要です。',
                    'priority': 'high'
                })
        
        # A/Bテスト推奨
        active_tests = self.ab_tests.get_active_tests()
        if len(active_tests) == 0:
            recommendations.append({
                'title': 'A/Bテストの実施',
                'description': '現在実行中のA/Bテストがありません。メッセージ形式や配信タイミングのテストを検討してください。',
                'priority': 'medium'
            })
        
        return recommendations
    
    def _analyze_ab_test_results(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """A/Bテスト結果分析"""
        variants = test_results.get('variant_results', [])
        
        if len(variants) < 2:
            return {}
        
        winner = max(variants, key=lambda x: x.get('success_rate', 0))
        loser = min(variants, key=lambda x: x.get('success_rate', 0))
        
        improvement = winner.get('success_rate', 0) - loser.get('success_rate', 0)
        
        return {
            'winner': winner,
            'improvement_percentage': improvement,
            'statistical_significance': winner.get('statistical_significance'),
            'confidence_level': 'high' if winner.get('statistical_significance', 0.5) <= 0.05 else 'low'
        }
    
    def _generate_ab_test_recommendations(self, test_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """A/Bテスト推奨事項生成"""
        analysis = self._analyze_ab_test_results(test_results)
        recommendations = []
        
        if analysis:
            confidence = analysis.get('confidence_level', 'low')
            improvement = analysis.get('improvement_percentage', 0)
            
            if confidence == 'high' and improvement > 5:
                recommendations.append({
                    'title': '勝者バリアントの採用',
                    'description': f'統計的に有意な差({improvement:.1f}%の改善)が確認されました。勝者バリアントを本採用することを推奨します。'
                })
            elif confidence == 'low':
                recommendations.append({
                    'title': 'テスト期間の延長',
                    'description': '統計的有意性が不十分です。より多くのサンプルを収集するため、テスト期間を延長してください。'
                })
        
        return recommendations