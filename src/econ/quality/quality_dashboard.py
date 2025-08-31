"""
経済指標システム 品質レポート・ダッシュボード
品質メトリクス可視化とレポート生成機能を提供
"""

import os
import json
import sqlite3
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import statistics
import logging

from .test_framework import EconomicTestFramework
from .quality_metrics import QualityMetricsCollector
from .performance_tester import PerformanceTester
from .security_scanner import SecurityScanner
from .e2e_tester import EndToEndTester
from ..config.settings import get_econ_config


@dataclass
class DashboardMetrics:
    """ダッシュボードメトリクス"""
    timestamp: datetime
    overall_score: float
    test_success_rate: float
    test_coverage: float
    performance_score: float
    security_score: float
    e2e_success_rate: float
    quality_trends: Dict[str, Any]
    recent_alerts: List[Dict[str, Any]]
    recommendations: List[str]


class QualityDashboard:
    """品質レポート・ダッシュボード"""
    
    def __init__(self, config=None):
        self.config = config or get_econ_config()
        
        # ダッシュボード設定
        self.dashboard_config = {
            'output_dir': self.config.get('dashboard_output_dir', 'build/dashboard'),
            'reports_dir': self.config.get('dashboard_reports_dir', 'build/dashboard/reports'),
            'static_dir': self.config.get('dashboard_static_dir', 'build/dashboard/static'),
            'data_retention_days': self.config.get('dashboard_retention_days', 90),
            'update_interval_hours': self.config.get('dashboard_update_interval', 6)
        }
        
        # 出力ディレクトリ作成
        for dir_path in [self.dashboard_config['output_dir'], 
                        self.dashboard_config['reports_dir'],
                        self.dashboard_config['static_dir']]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # 品質システム初期化
        self.test_framework = EconomicTestFramework(self.config)
        self.quality_metrics = QualityMetricsCollector(self.config)
        self.performance_tester = PerformanceTester(self.config)
        self.security_scanner = SecurityScanner(self.config)
        self.e2e_tester = EndToEndTester(self.config)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def generate_comprehensive_report(self, days: int = 30) -> Dict[str, Any]:
        """包括的品質レポート生成"""
        self.logger.info(f"包括的品質レポート生成開始 (過去{days}日間)")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 各種データ収集
        test_history = self.test_framework.get_test_history(days)
        health_history = self.quality_metrics.get_health_history(days)
        performance_history = self.performance_tester.get_performance_history(days=days)
        security_history = self.security_scanner.get_scan_history(days)
        e2e_history = self.e2e_tester.get_execution_history(days)
        
        # メトリクス集計
        report = {
            'metadata': {
                'generated_at': end_date.isoformat(),
                'period_days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'executive_summary': self._generate_executive_summary(
                test_history, health_history, performance_history, 
                security_history, e2e_history
            ),
            'test_analytics': self._analyze_test_metrics(test_history),
            'quality_analytics': self._analyze_quality_metrics(health_history),
            'performance_analytics': self._analyze_performance_metrics(performance_history),
            'security_analytics': self._analyze_security_metrics(security_history),
            'e2e_analytics': self._analyze_e2e_metrics(e2e_history),
            'trends_and_insights': self._generate_trends_and_insights(
                test_history, health_history, performance_history, 
                security_history, e2e_history
            ),
            'recommendations': self._generate_comprehensive_recommendations(
                test_history, health_history, performance_history,
                security_history, e2e_history
            )
        }
        
        # レポート保存
        report_file = self._save_report(report, 'comprehensive_quality_report')
        
        self.logger.info(f"包括的品質レポート生成完了: {report_file}")
        
        return report
    
    def _generate_executive_summary(self, test_history, health_history, 
                                   performance_history, security_history, e2e_history) -> Dict[str, Any]:
        """エグゼクティブサマリー生成"""
        # 最新データ取得
        latest_test = test_history[0] if test_history else None
        latest_health = health_history[0] if health_history else None
        latest_performance = performance_history[0] if performance_history else None
        latest_security = security_history[0] if security_history else None
        latest_e2e = e2e_history[0] if e2e_history else None
        
        # 全体評価スコア算出
        scores = []
        
        if latest_test:
            scores.append(latest_test.success_rate)
        if latest_health:
            scores.append(latest_health.overall_score)
        if latest_performance:
            # パフォーマンススコア算出（レスポンス時間ベース）
            perf_score = max(0, 100 - (latest_performance.response_time_avg / 50))  # 50ms基準
            scores.append(perf_score)
        if latest_security:
            scores.append(latest_security.security_score)
        if latest_e2e:
            scores.append(latest_e2e.success_rate)
        
        overall_score = statistics.mean(scores) if scores else 0
        
        # リスクレベル判定
        if overall_score >= 90:
            risk_level = 'low'
            status = 'excellent'
        elif overall_score >= 80:
            risk_level = 'medium'
            status = 'good'
        elif overall_score >= 70:
            risk_level = 'high'
            status = 'acceptable'
        else:
            risk_level = 'critical'
            status = 'poor'
        
        return {
            'overall_score': overall_score,
            'risk_level': risk_level,
            'quality_status': status,
            'key_metrics': {
                'test_success_rate': latest_test.success_rate if latest_test else 0,
                'system_health_score': latest_health.overall_score if latest_health else 0,
                'performance_score': perf_score if latest_performance else 0,
                'security_score': latest_security.security_score if latest_security else 0,
                'e2e_success_rate': latest_e2e.success_rate if latest_e2e else 0
            },
            'data_availability': {
                'test_data': len(test_history),
                'health_data': len(health_history),
                'performance_data': len(performance_history),
                'security_data': len(security_history),
                'e2e_data': len(e2e_history)
            }
        }
    
    def _analyze_test_metrics(self, test_history) -> Dict[str, Any]:
        """テストメトリクス分析"""
        if not test_history:
            return {'status': 'no_data', 'message': 'テストデータがありません'}
        
        # 成功率トレンド
        success_rates = [suite.success_rate for suite in test_history]
        coverage_rates = [suite.coverage_report.get('total_coverage', 0) for suite in test_history]
        
        # 統計計算
        avg_success_rate = statistics.mean(success_rates)
        avg_coverage = statistics.mean(coverage_rates)
        
        # トレンド計算
        if len(success_rates) >= 2:
            success_trend = 'improving' if success_rates[0] > success_rates[-1] else 'declining'
            coverage_trend = 'improving' if coverage_rates[0] > coverage_rates[-1] else 'declining'
        else:
            success_trend = coverage_trend = 'stable'
        
        # 最近の失敗テスト分析
        recent_failures = []
        for suite in test_history[:5]:  # 最近5件
            failed_tests = [t for t in suite.tests if t.status == 'failed']
            if failed_tests:
                recent_failures.extend(failed_tests[:3])  # 最大3件まで
        
        return {
            'summary': {
                'total_test_suites': len(test_history),
                'average_success_rate': avg_success_rate,
                'average_coverage': avg_coverage,
                'success_rate_trend': success_trend,
                'coverage_trend': coverage_trend
            },
            'time_series': [
                {
                    'timestamp': suite.timestamp.isoformat() if hasattr(suite, 'timestamp') else None,
                    'success_rate': suite.success_rate,
                    'coverage': suite.coverage_report.get('total_coverage', 0),
                    'total_tests': len(suite.tests)
                }
                for suite in reversed(test_history[-30:])  # 最近30件
            ],
            'recent_failures': [
                {
                    'test_name': failure.test_name,
                    'error_message': failure.error_message,
                    'timestamp': failure.timestamp.isoformat() if hasattr(failure, 'timestamp') else None
                }
                for failure in recent_failures
            ]
        }
    
    def _analyze_quality_metrics(self, health_history) -> Dict[str, Any]:
        """品質メトリクス分析"""
        if not health_history:
            return {'status': 'no_data', 'message': '品質データがありません'}
        
        # スコアトレンド
        overall_scores = [h.overall_score for h in health_history]
        
        # コンポーネント別分析
        component_analysis = {}
        if health_history:
            latest_health = health_history[0]
            for component, score in latest_health.component_scores.items():
                component_scores = [
                    h.component_scores.get(component, 0) 
                    for h in health_history[:10]  # 最近10件
                ]
                component_analysis[component] = {
                    'current_score': score,
                    'average_score': statistics.mean(component_scores),
                    'trend': 'improving' if len(component_scores) >= 2 and component_scores[0] > component_scores[-1] else 'declining'
                }
        
        # アラート分析
        total_alerts = sum(len(h.alerts) for h in health_history)
        critical_alerts = sum(
            len([a for a in h.alerts if a.get('severity') == 'critical'])
            for h in health_history
        )
        
        return {
            'summary': {
                'current_score': overall_scores[0] if overall_scores else 0,
                'average_score': statistics.mean(overall_scores),
                'score_trend': 'improving' if len(overall_scores) >= 2 and overall_scores[0] > overall_scores[-1] else 'declining',
                'total_alerts': total_alerts,
                'critical_alerts': critical_alerts
            },
            'component_analysis': component_analysis,
            'time_series': [
                {
                    'timestamp': h.timestamp.isoformat(),
                    'overall_score': h.overall_score,
                    'alert_count': len(h.alerts)
                }
                for h in reversed(health_history[-30:])
            ]
        }
    
    def _analyze_performance_metrics(self, performance_history) -> Dict[str, Any]:
        """パフォーマンスメトリクス分析"""
        if not performance_history:
            return {'status': 'no_data', 'message': 'パフォーマンスデータがありません'}
        
        # レスポンス時間統計
        response_times = [p.response_time_avg for p in performance_history]
        throughputs = [p.requests_per_second for p in performance_history]
        
        # パフォーマンステスト別分析
        test_type_analysis = {}
        for perf in performance_history:
            test_type = perf.test_type
            if test_type not in test_type_analysis:
                test_type_analysis[test_type] = {
                    'count': 0,
                    'avg_response_time': 0,
                    'avg_throughput': 0,
                    'success_rates': []
                }
            
            analysis = test_type_analysis[test_type]
            analysis['count'] += 1
            analysis['avg_response_time'] += perf.response_time_avg
            analysis['avg_throughput'] += perf.requests_per_second
            
            if perf.requests_total > 0:
                success_rate = (perf.requests_successful / perf.requests_total) * 100
                analysis['success_rates'].append(success_rate)
        
        # 平均値計算
        for test_type, analysis in test_type_analysis.items():
            if analysis['count'] > 0:
                analysis['avg_response_time'] /= analysis['count']
                analysis['avg_throughput'] /= analysis['count']
                analysis['avg_success_rate'] = statistics.mean(analysis['success_rates']) if analysis['success_rates'] else 0
        
        return {
            'summary': {
                'total_tests': len(performance_history),
                'average_response_time': statistics.mean(response_times),
                'average_throughput': statistics.mean(throughputs),
                'response_time_trend': 'improving' if len(response_times) >= 2 and response_times[0] < response_times[-1] else 'declining'
            },
            'by_test_type': test_type_analysis,
            'time_series': [
                {
                    'timestamp': p.timestamp.isoformat(),
                    'response_time_avg': p.response_time_avg,
                    'throughput': p.requests_per_second,
                    'test_type': p.test_type
                }
                for p in reversed(performance_history[-30:])
            ]
        }
    
    def _analyze_security_metrics(self, security_history) -> Dict[str, Any]:
        """セキュリティメトリクス分析"""
        if not security_history:
            return {'status': 'no_data', 'message': 'セキュリティデータがありません'}
        
        # セキュリティスコア統計
        security_scores = [s.security_score for s in security_history]
        
        # 脆弱性統計
        vulnerability_stats = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'info': 0
        }
        
        category_stats = {}
        
        for scan in security_history:
            for vuln in scan.vulnerabilities:
                vulnerability_stats[vuln.severity] += 1
                
                if vuln.category not in category_stats:
                    category_stats[vuln.category] = 0
                category_stats[vuln.category] += 1
        
        # 最新の重要な脆弱性
        recent_critical = []
        if security_history:
            latest_scan = security_history[0]
            recent_critical = [
                {
                    'title': vuln.title,
                    'category': vuln.category,
                    'file_path': vuln.file_path,
                    'recommendation': vuln.recommendation
                }
                for vuln in latest_scan.vulnerabilities
                if vuln.severity in ['critical', 'high']
            ][:5]  # 最大5件
        
        return {
            'summary': {
                'current_security_score': security_scores[0] if security_scores else 0,
                'average_security_score': statistics.mean(security_scores),
                'total_vulnerabilities': sum(vulnerability_stats.values()),
                'critical_vulnerabilities': vulnerability_stats['critical'],
                'high_vulnerabilities': vulnerability_stats['high']
            },
            'vulnerability_distribution': vulnerability_stats,
            'category_distribution': category_stats,
            'recent_critical_vulnerabilities': recent_critical,
            'time_series': [
                {
                    'timestamp': s.timestamp.isoformat(),
                    'security_score': s.security_score,
                    'vulnerability_count': len(s.vulnerabilities)
                }
                for s in reversed(security_history[-30:])
            ]
        }
    
    def _analyze_e2e_metrics(self, e2e_history) -> Dict[str, Any]:
        """E2Eメトリクス分析"""
        if not e2e_history:
            return {'status': 'no_data', 'message': 'E2Eテストデータがありません'}
        
        # 成功率統計
        success_rates = [e.success_rate for e in e2e_history]
        durations = [e.total_duration for e in e2e_history]
        
        # シナリオ別分析
        scenario_analysis = {}
        for execution in e2e_history:
            scenario_id = execution.scenario_id
            if scenario_id not in scenario_analysis:
                scenario_analysis[scenario_id] = {
                    'executions': 0,
                    'total_success_rate': 0,
                    'total_duration': 0,
                    'failures': []
                }
            
            analysis = scenario_analysis[scenario_id]
            analysis['executions'] += 1
            analysis['total_success_rate'] += execution.success_rate
            analysis['total_duration'] += execution.total_duration
            
            if execution.success_rate < 100:
                analysis['failures'].append({
                    'timestamp': execution.timestamp.isoformat(),
                    'success_rate': execution.success_rate,
                    'failed_steps': execution.failed_steps
                })
        
        # 平均値計算
        for scenario_id, analysis in scenario_analysis.items():
            if analysis['executions'] > 0:
                analysis['avg_success_rate'] = analysis['total_success_rate'] / analysis['executions']
                analysis['avg_duration'] = analysis['total_duration'] / analysis['executions']
        
        return {
            'summary': {
                'total_executions': len(e2e_history),
                'average_success_rate': statistics.mean(success_rates),
                'average_duration': statistics.mean(durations),
                'success_rate_trend': 'improving' if len(success_rates) >= 2 and success_rates[0] > success_rates[-1] else 'declining'
            },
            'by_scenario': scenario_analysis,
            'time_series': [
                {
                    'timestamp': e.timestamp.isoformat(),
                    'success_rate': e.success_rate,
                    'duration': e.total_duration,
                    'scenario': e.scenario_name
                }
                for e in reversed(e2e_history[-30:])
            ]
        }
    
    def _generate_trends_and_insights(self, test_history, health_history, 
                                    performance_history, security_history, e2e_history) -> Dict[str, Any]:
        """トレンドと洞察生成"""
        insights = []
        trends = {}
        
        # テストトレンド
        if test_history and len(test_history) >= 3:
            recent_success = statistics.mean([t.success_rate for t in test_history[:3]])
            older_success = statistics.mean([t.success_rate for t in test_history[-3:]])
            
            if recent_success > older_success + 5:
                insights.append("テスト成功率が改善傾向にあります")
                trends['test_trend'] = 'improving'
            elif recent_success < older_success - 5:
                insights.append("テスト成功率が悪化傾向にあります。要因の調査が必要です")
                trends['test_trend'] = 'declining'
            else:
                trends['test_trend'] = 'stable'
        
        # パフォーマンストレンド
        if performance_history and len(performance_history) >= 3:
            recent_perf = statistics.mean([p.response_time_avg for p in performance_history[:3]])
            older_perf = statistics.mean([p.response_time_avg for p in performance_history[-3:]])
            
            if recent_perf < older_perf - 100:  # 100ms改善
                insights.append("レスポンス時間が大幅に改善されています")
                trends['performance_trend'] = 'improving'
            elif recent_perf > older_perf + 100:  # 100ms悪化
                insights.append("レスポンス時間が悪化しています。パフォーマンス最適化が必要です")
                trends['performance_trend'] = 'declining'
            else:
                trends['performance_trend'] = 'stable'
        
        # セキュリティトレンド
        if security_history and len(security_history) >= 2:
            recent_score = security_history[0].security_score
            older_score = security_history[-1].security_score
            
            if recent_score > older_score + 10:
                insights.append("セキュリティスコアが向上しています")
                trends['security_trend'] = 'improving'
            elif recent_score < older_score - 10:
                insights.append("セキュリティスコアが低下しています。脆弱性対応が必要です")
                trends['security_trend'] = 'declining'
            else:
                trends['security_trend'] = 'stable'
        
        # 全体的な洞察
        if len(insights) == 0:
            insights.append("システムの品質指標は安定しています")
        
        # データ品質洞察
        data_sources = {
            'tests': len(test_history),
            'health': len(health_history),
            'performance': len(performance_history),
            'security': len(security_history),
            'e2e': len(e2e_history)
        }
        
        insufficient_data = [name for name, count in data_sources.items() if count < 5]
        if insufficient_data:
            insights.append(f"以下の分野でデータが不足しています: {', '.join(insufficient_data)}")
        
        return {
            'key_insights': insights,
            'trends': trends,
            'data_coverage': data_sources,
            'recommendations_summary': f"{len(insights)}件の主要な洞察を特定しました"
        }
    
    def _generate_comprehensive_recommendations(self, test_history, health_history, 
                                              performance_history, security_history, e2e_history) -> List[str]:
        """包括的推奨事項生成"""
        recommendations = []
        
        # テスト関連推奨事項
        if test_history:
            latest_test = test_history[0]
            if latest_test.success_rate < 95:
                recommendations.append(f"テスト成功率が{latest_test.success_rate:.1f}%です。失敗したテストの調査と修正が必要です")
            
            coverage = latest_test.coverage_report.get('total_coverage', 0)
            if coverage < 80:
                recommendations.append(f"テストカバレッジが{coverage:.1f}%です。テストケースの追加が必要です")
        
        # パフォーマンス関連推奨事項
        if performance_history:
            slow_tests = [p for p in performance_history[:5] if p.response_time_avg > 2000]  # 2秒以上
            if slow_tests:
                recommendations.append(f"{len(slow_tests)}件のパフォーマンステストで遅延が検出されました。最適化が必要です")
        
        # セキュリティ関連推奨事項
        if security_history:
            latest_security = security_history[0]
            critical_vulns = [v for v in latest_security.vulnerabilities if v.severity == 'critical']
            if critical_vulns:
                recommendations.append(f"{len(critical_vulns)}件の重要な脆弱性が検出されました。直ちに修正が必要です")
        
        # E2E関連推奨事項
        if e2e_history:
            failed_executions = [e for e in e2e_history[:5] if e.success_rate < 90]
            if failed_executions:
                recommendations.append(f"{len(failed_executions)}件のE2Eテストで失敗が発生しました。システム統合の確認が必要です")
        
        # 全般的な推奨事項
        if not recommendations:
            recommendations.append("現在の品質レベルは良好です。定期的な監視を継続してください")
        else:
            recommendations.insert(0, f"{len(recommendations)}件の改善項目が特定されました。優先度順に対応してください")
        
        return recommendations
    
    def _save_report(self, report: Dict[str, Any], report_type: str) -> str:
        """レポート保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSONレポート保存
        json_filename = f"{report_type}_{timestamp}.json"
        json_path = Path(self.dashboard_config['reports_dir']) / json_filename
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        # HTMLレポート生成
        html_filename = f"{report_type}_{timestamp}.html"
        html_path = Path(self.dashboard_config['reports_dir']) / html_filename
        
        html_content = self._generate_html_report(report)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(json_path)
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """HTMLレポート生成"""
        metadata = report.get('metadata', {})
        summary = report.get('executive_summary', {})
        
        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>経済指標システム品質レポート</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .score {{ font-size: 2em; font-weight: bold; }}
        .score.excellent {{ color: #27ae60; }}
        .score.good {{ color: #f39c12; }}
        .score.poor {{ color: #e74c3c; }}
        .section {{ margin: 30px 0; }}
        .recommendation {{ background: #ecf0f1; padding: 15px; border-left: 4px solid #3498db; margin: 10px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>経済指標システム品質レポート</h1>
        <p>生成日時: {metadata.get('generated_at', 'N/A')}</p>
        <p>分析期間: {metadata.get('period_days', 'N/A')}日間</p>
    </div>
    
    <div class="section">
        <h2>エグゼクティブサマリー</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <h3>総合品質スコア</h3>
                <div class="score {summary.get('quality_status', 'poor')}">{summary.get('overall_score', 0):.1f}</div>
                <p>リスクレベル: {summary.get('risk_level', 'N/A')}</p>
            </div>
        """
        
        # キーメトリクスカード追加
        key_metrics = summary.get('key_metrics', {})
        for metric_name, value in key_metrics.items():
            html += f"""
            <div class="metric-card">
                <h3>{metric_name.replace('_', ' ').title()}</h3>
                <div class="score">{value:.1f}</div>
            </div>
            """
        
        html += """
        </div>
    </div>
    
    <div class="section">
        <h2>推奨事項</h2>
        """
        
        recommendations = report.get('recommendations', [])
        for recommendation in recommendations:
            html += f'<div class="recommendation">{recommendation}</div>'
        
        html += """
    </div>
    
    <div class="section">
        <h2>詳細分析</h2>
        <p>詳細な分析結果は同時生成されるJSONレポートをご参照ください。</p>
    </div>
</body>
</html>"""
        
        return html
    
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """ダッシュボード用データ生成"""
        self.logger.info("ダッシュボードデータ生成開始")
        
        # 最新データ収集
        current_metrics = DashboardMetrics(
            timestamp=datetime.now(),
            overall_score=0,
            test_success_rate=0,
            test_coverage=0,
            performance_score=0,
            security_score=0,
            e2e_success_rate=0,
            quality_trends={},
            recent_alerts=[],
            recommendations=[]
        )
        
        try:
            # 最新テスト結果
            test_history = self.test_framework.get_test_history(7)
            if test_history:
                latest_test = test_history[0]
                current_metrics.test_success_rate = latest_test.success_rate
                current_metrics.test_coverage = latest_test.coverage_report.get('total_coverage', 0)
        
            # システム健全性
            health_report = self.quality_metrics.generate_system_health_report()
            current_metrics.overall_score = health_report.overall_score
            current_metrics.recent_alerts = health_report.alerts[:5]  # 最新5件
            current_metrics.recommendations = health_report.recommendations[:3]  # 上位3件
            
            # セキュリティスコア
            security_history = self.security_scanner.get_scan_history(7)
            if security_history:
                current_metrics.security_score = security_history[0].security_score
            
            # E2E成功率
            e2e_history = self.e2e_tester.get_execution_history(7)
            if e2e_history:
                current_metrics.e2e_success_rate = statistics.mean([e.success_rate for e in e2e_history])
            
        except Exception as e:
            self.logger.error(f"ダッシュボードデータ生成エラー: {e}")
        
        # ダッシュボードデータ
        dashboard_data = {
            'current_metrics': asdict(current_metrics),
            'last_updated': datetime.now().isoformat(),
            'data_sources': {
                'test_framework': 'active',
                'quality_metrics': 'active', 
                'performance_tester': 'active',
                'security_scanner': 'active',
                'e2e_tester': 'active'
            },
            'status': 'healthy' if current_metrics.overall_score > 80 else 'degraded'
        }
        
        # ダッシュボードデータ保存
        dashboard_file = Path(self.dashboard_config['output_dir']) / 'dashboard_data.json'
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2, default=str)
        
        self.logger.info(f"ダッシュボードデータ生成完了: {dashboard_file}")
        
        return dashboard_data
    
    def get_dashboard_status(self) -> Dict[str, Any]:
        """ダッシュボード状態取得"""
        dashboard_file = Path(self.dashboard_config['output_dir']) / 'dashboard_data.json'
        
        if not dashboard_file.exists():
            return {
                'status': 'no_data',
                'message': 'ダッシュボードデータがありません',
                'last_updated': None
            }
        
        try:
            with open(dashboard_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            last_updated = datetime.fromisoformat(data['last_updated'])
            age_hours = (datetime.now() - last_updated).total_seconds() / 3600
            
            if age_hours > self.dashboard_config['update_interval_hours']:
                status = 'stale'
            else:
                status = 'current'
            
            return {
                'status': status,
                'last_updated': data['last_updated'],
                'age_hours': age_hours,
                'overall_score': data['current_metrics']['overall_score'],
                'data_sources': data['data_sources']
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'ダッシュボードデータ読み取りエラー: {e}',
                'last_updated': None
            }