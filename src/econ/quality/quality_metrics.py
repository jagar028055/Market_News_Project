"""
経済指標システム強化品質メトリクス収集・分析システム
Phase 4の品質監視システムを拡張し、より詳細な品質追跡機能を提供
"""

import os
import json
import time
import sqlite3
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import psutil
import logging

from ..config.settings import get_econ_config
from ..automation.quality_monitor import QualityMonitor


@dataclass
class PerformanceMetric:
    """パフォーマンスメトリクス"""
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    context: Dict[str, Any]
    threshold: Optional[float] = None
    status: str = "unknown"  # good, warning, critical


@dataclass 
class QualityTrend:
    """品質トレンドデータ"""
    metric_name: str
    values: List[float]
    timestamps: List[datetime]
    trend_direction: str  # improving, stable, degrading
    trend_strength: float  # 0.0-1.0
    prediction: Optional[float] = None


@dataclass
class SystemHealth:
    """システム健全性レポート"""
    overall_score: float
    component_scores: Dict[str, float]
    performance_metrics: Dict[str, PerformanceMetric]
    quality_trends: Dict[str, QualityTrend]
    alerts: List[Dict[str, Any]]
    recommendations: List[str]
    timestamp: datetime


class QualityMetricsCollector:
    """強化品質メトリクス収集・分析システム"""
    
    def __init__(self, config=None):
        self.config = config or get_econ_config()
        
        # 設定
        self.metrics_config = {
            'collection_interval': getattr(self.config, 'metrics_collection_interval', 300),  # 5分
            'retention_days': getattr(self.config, 'metrics_retention_days', 30),
            'performance_thresholds': {
                'response_time_ms': 5000,
                'memory_usage_mb': 1000,
                'cpu_usage_percent': 80,
                'disk_usage_percent': 85,
                'error_rate_percent': 5
            },
            'quality_thresholds': {
                'data_completeness': 95.0,
                'data_freshness': 90.0,
                'data_accuracy': 90.0,
                'test_coverage': 80.0,
                'test_success_rate': 95.0
            }
        }
        
        # データベース初期化
        self.db_path = Path(getattr(self.config, 'quality_db_path', 'data/quality_metrics.db'))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # 既存の品質監視システム統合
        self.quality_monitor = QualityMonitor(self.config)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _init_database(self) -> None:
        """メトリクスデータベース初期化"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    context TEXT,
                    threshold REAL,
                    status TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_perf_metrics_name_time ON performance_metrics(metric_name, timestamp);
                
                CREATE TABLE IF NOT EXISTS quality_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_quality_metrics_name_time ON quality_metrics(metric_name, timestamp);
                
                CREATE TABLE IF NOT EXISTS system_health_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    overall_score REAL NOT NULL,
                    component_scores TEXT NOT NULL,
                    performance_metrics TEXT NOT NULL,
                    quality_trends TEXT NOT NULL,
                    alerts TEXT NOT NULL,
                    recommendations TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_health_snapshots_time ON system_health_snapshots(timestamp);
                
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    metric_name TEXT,
                    metric_value REAL,
                    threshold REAL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE
                );
                CREATE INDEX IF NOT EXISTS idx_alerts_time_resolved ON alerts(timestamp, resolved);
            """)
    
    def initialize_database(self) -> None:
        """品質システムデータベース初期化（公開メソッド）"""
        self._init_database()
        self.logger.info(f"Quality database initialized at: {self.db_path}")
    
    def collect_system_performance(self) -> Dict[str, PerformanceMetric]:
        """システムパフォーマンス収集"""
        metrics = {}
        timestamp = datetime.now()
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics['cpu_usage'] = PerformanceMetric(
                metric_name='cpu_usage',
                value=cpu_percent,
                unit='percent',
                timestamp=timestamp,
                context={'cores': psutil.cpu_count()},
                threshold=self.metrics_config['performance_thresholds']['cpu_usage_percent'],
                status='good' if cpu_percent < 60 else 'warning' if cpu_percent < 80 else 'critical'
            )
            
            # メモリ使用量
            memory = psutil.virtual_memory()
            memory_mb = memory.used / 1024 / 1024
            metrics['memory_usage'] = PerformanceMetric(
                metric_name='memory_usage',
                value=memory_mb,
                unit='MB',
                timestamp=timestamp,
                context={
                    'total_mb': memory.total / 1024 / 1024,
                    'percent': memory.percent
                },
                threshold=self.metrics_config['performance_thresholds']['memory_usage_mb'],
                status='good' if memory.percent < 70 else 'warning' if memory.percent < 85 else 'critical'
            )
            
            # ディスク使用量
            disk = psutil.disk_usage('/')
            metrics['disk_usage'] = PerformanceMetric(
                metric_name='disk_usage',
                value=disk.percent,
                unit='percent',
                timestamp=timestamp,
                context={
                    'free_gb': disk.free / 1024 / 1024 / 1024,
                    'total_gb': disk.total / 1024 / 1024 / 1024
                },
                threshold=self.metrics_config['performance_thresholds']['disk_usage_percent'],
                status='good' if disk.percent < 75 else 'warning' if disk.percent < 85 else 'critical'
            )
            
            # プロセス固有メトリクス
            current_process = psutil.Process()
            process_memory = current_process.memory_info().rss / 1024 / 1024
            metrics['process_memory'] = PerformanceMetric(
                metric_name='process_memory',
                value=process_memory,
                unit='MB',
                timestamp=timestamp,
                context={'pid': current_process.pid},
                threshold=500.0,
                status='good' if process_memory < 300 else 'warning' if process_memory < 500 else 'critical'
            )
            
        except Exception as e:
            self.logger.error(f"システムパフォーマンス収集エラー: {e}")
        
        return metrics
    
    def collect_application_performance(self) -> Dict[str, PerformanceMetric]:
        """アプリケーションパフォーマンス収集"""
        metrics = {}
        timestamp = datetime.now()
        
        try:
            # データ取得パフォーマンステスト
            start_time = time.time()
            from ..adapters.investpy_calendar import InvestpyCalendarAdapter
            
            adapter = InvestpyCalendarAdapter()
            yesterday = datetime.now() - timedelta(days=1)
            
            try:
                events = adapter.get_economic_calendar(
                    from_date=yesterday.strftime('%Y-%m-%d'),
                    to_date=yesterday.strftime('%Y-%m-%d')
                )
                response_time = (time.time() - start_time) * 1000
                
                metrics['data_fetch_response_time'] = PerformanceMetric(
                    metric_name='data_fetch_response_time',
                    value=response_time,
                    unit='ms',
                    timestamp=timestamp,
                    context={'events_count': len(events)},
                    threshold=self.metrics_config['performance_thresholds']['response_time_ms'],
                    status='good' if response_time < 3000 else 'warning' if response_time < 5000 else 'critical'
                )
                
                # データ品質メトリクス
                complete_events = len([e for e in events if all(
                    key in e and e[key] is not None 
                    for key in ['time', 'country', 'event', 'importance']
                )])
                completeness = (complete_events / len(events) * 100) if events else 0
                
                metrics['data_completeness'] = PerformanceMetric(
                    metric_name='data_completeness',
                    value=completeness,
                    unit='percent',
                    timestamp=timestamp,
                    context={'total_events': len(events), 'complete_events': complete_events},
                    threshold=self.metrics_config['quality_thresholds']['data_completeness'],
                    status='good' if completeness >= 95 else 'warning' if completeness >= 90 else 'critical'
                )
                
            except Exception as e:
                # データ取得失敗
                metrics['data_fetch_error'] = PerformanceMetric(
                    metric_name='data_fetch_error',
                    value=1.0,
                    unit='count',
                    timestamp=timestamp,
                    context={'error': str(e)},
                    threshold=0.0,
                    status='critical'
                )
            
            # レポート生成パフォーマンス
            start_time = time.time()
            try:
                from ..reports.daily_list_renderer import DailyListRenderer
                renderer = DailyListRenderer(self.config)
                
                sample_data = [{
                    'time': '08:30',
                    'country': 'US',
                    'event': 'CPI (YoY)',
                    'importance': 'High',
                    'actual': '3.0%',
                    'forecast': '3.1%',
                    'previous': '3.3%'
                }]
                
                markdown_report = renderer.render_daily_list(sample_data, 'markdown')
                report_gen_time = (time.time() - start_time) * 1000
                
                metrics['report_generation_time'] = PerformanceMetric(
                    metric_name='report_generation_time',
                    value=report_gen_time,
                    unit='ms',
                    timestamp=timestamp,
                    context={'report_length': len(markdown_report)},
                    threshold=2000.0,
                    status='good' if report_gen_time < 1000 else 'warning' if report_gen_time < 2000 else 'critical'
                )
                
            except Exception as e:
                metrics['report_generation_error'] = PerformanceMetric(
                    metric_name='report_generation_error',
                    value=1.0,
                    unit='count',
                    timestamp=timestamp,
                    context={'error': str(e)},
                    threshold=0.0,
                    status='critical'
                )
            
        except Exception as e:
            self.logger.error(f"アプリケーションパフォーマンス収集エラー: {e}")
        
        return metrics
    
    def collect_quality_metrics(self) -> Dict[str, float]:
        """品質メトリクス収集（既存システム拡張）"""
        try:
            # 既存の品質チェックシステムを活用
            quality_report = self.quality_monitor.run_quality_check()
            
            metrics = {
                'overall_quality_score': quality_report.get('overall_score', 0),
                'data_completeness_score': quality_report.get('data_completeness', {}).get('score', 0),
                'data_freshness_score': quality_report.get('data_freshness', {}).get('score', 0),
                'data_accuracy_score': quality_report.get('data_accuracy', {}).get('score', 0),
                'data_consistency_score': quality_report.get('data_consistency', {}).get('score', 0),
                'issues_count': len(quality_report.get('issues', [])),
                'critical_issues_count': len([
                    issue for issue in quality_report.get('issues', [])
                    if issue.get('severity') == 'critical'
                ])
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"品質メトリクス収集エラー: {e}")
            return {}
    
    def analyze_trends(self, metric_name: str, days: int = 7) -> QualityTrend:
        """メトリクストレンド分析"""
        since = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(str(self.db_path)) as conn:
            # パフォーマンスメトリクスから取得
            cursor = conn.execute("""
                SELECT value, timestamp FROM performance_metrics
                WHERE metric_name = ? AND timestamp >= ?
                ORDER BY timestamp
            """, (metric_name, since.isoformat()))
            
            perf_data = cursor.fetchall()
            
            # 品質メトリクスからも取得
            cursor = conn.execute("""
                SELECT value, timestamp FROM quality_metrics
                WHERE metric_name = ? AND timestamp >= ?
                ORDER BY timestamp
            """, (metric_name, since.isoformat()))
            
            quality_data = cursor.fetchall()
            
            # データ統合
            all_data = perf_data + quality_data
            
            if len(all_data) < 2:
                return QualityTrend(
                    metric_name=metric_name,
                    values=[],
                    timestamps=[],
                    trend_direction="unknown",
                    trend_strength=0.0
                )
            
            values = [float(row[0]) for row in all_data]
            timestamps = [datetime.fromisoformat(row[1]) for row in all_data]
            
            # トレンド計算
            if len(values) >= 3:
                # 線形回帰によるトレンド算出
                x_values = list(range(len(values)))
                slope = self._calculate_slope(x_values, values)
                
                if abs(slope) < 0.1:
                    trend_direction = "stable"
                    trend_strength = 0.1
                elif slope > 0:
                    trend_direction = "improving"
                    trend_strength = min(abs(slope), 1.0)
                else:
                    trend_direction = "degrading" 
                    trend_strength = min(abs(slope), 1.0)
            else:
                trend_direction = "stable"
                trend_strength = 0.0
            
            # 予測値（単純な線形外挿）
            prediction = None
            if len(values) >= 3:
                last_values = values[-3:]
                prediction = statistics.mean(last_values)
            
            return QualityTrend(
                metric_name=metric_name,
                values=values,
                timestamps=timestamps,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                prediction=prediction
            )
    
    def _calculate_slope(self, x_values: List[float], y_values: List[float]) -> float:
        """線形回帰の傾き計算"""
        n = len(x_values)
        if n < 2:
            return 0.0
        
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def generate_alerts(self, metrics: Dict[str, PerformanceMetric]) -> List[Dict[str, Any]]:
        """アラート生成"""
        alerts = []
        
        for metric_name, metric in metrics.items():
            if metric.status == 'critical':
                alert = {
                    'type': 'performance',
                    'severity': 'critical',
                    'title': f'{metric_name}が臨界値を超えました',
                    'description': f'{metric_name}: {metric.value}{metric.unit} (閾値: {metric.threshold})',
                    'metric_name': metric_name,
                    'metric_value': metric.value,
                    'threshold': metric.threshold,
                    'timestamp': metric.timestamp,
                    'context': metric.context
                }
                alerts.append(alert)
            elif metric.status == 'warning':
                alert = {
                    'type': 'performance',
                    'severity': 'warning',
                    'title': f'{metric_name}が警告レベルです',
                    'description': f'{metric_name}: {metric.value}{metric.unit} (閾値: {metric.threshold})',
                    'metric_name': metric_name,
                    'metric_value': metric.value,
                    'threshold': metric.threshold,
                    'timestamp': metric.timestamp,
                    'context': metric.context
                }
                alerts.append(alert)
        
        # アラートをデータベースに保存
        self._save_alerts(alerts)
        
        return alerts
    
    def _save_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """アラートデータベース保存"""
        if not alerts:
            return
            
        with sqlite3.connect(str(self.db_path)) as conn:
            for alert in alerts:
                conn.execute("""
                    INSERT INTO alerts 
                    (alert_type, severity, title, description, metric_name, 
                     metric_value, threshold, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert['type'],
                    alert['severity'],
                    alert['title'],
                    alert['description'],
                    alert.get('metric_name'),
                    alert.get('metric_value'),
                    alert.get('threshold'),
                    alert['timestamp'].isoformat()
                ))
            conn.commit()
    
    def save_metrics(self, performance_metrics: Dict[str, PerformanceMetric], 
                    quality_metrics: Dict[str, float]) -> None:
        """メトリクスデータベース保存"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # パフォーマンスメトリクス保存
            for metric in performance_metrics.values():
                conn.execute("""
                    INSERT INTO performance_metrics 
                    (metric_name, value, unit, timestamp, context, threshold, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    metric.metric_name,
                    metric.value,
                    metric.unit,
                    metric.timestamp.isoformat(),
                    json.dumps(metric.context, ensure_ascii=False),
                    metric.threshold,
                    metric.status
                ))
            
            # 品質メトリクス保存
            timestamp = datetime.now()
            for metric_name, value in quality_metrics.items():
                conn.execute("""
                    INSERT INTO quality_metrics 
                    (metric_name, value, timestamp, details)
                    VALUES (?, ?, ?, ?)
                """, (
                    metric_name,
                    value,
                    timestamp.isoformat(),
                    json.dumps({}, ensure_ascii=False)
                ))
            
            conn.commit()
    
    def generate_system_health_report(self) -> SystemHealth:
        """システム健全性レポート生成"""
        timestamp = datetime.now()
        
        # メトリクス収集
        performance_metrics = self.collect_system_performance()
        performance_metrics.update(self.collect_application_performance())
        quality_metrics = self.collect_quality_metrics()
        
        # アラート生成
        alerts = self.generate_alerts(performance_metrics)
        
        # コンポーネントスコア算出
        component_scores = {
            'system_performance': self._calculate_system_performance_score(performance_metrics),
            'data_quality': quality_metrics.get('overall_quality_score', 0),
            'availability': self._calculate_availability_score(performance_metrics),
            'security': 85.0  # セキュリティスキャナ実装後に更新
        }
        
        # 総合スコア
        overall_score = statistics.mean(component_scores.values())
        
        # トレンド分析
        quality_trends = {}
        key_metrics = ['cpu_usage', 'memory_usage', 'data_completeness', 'overall_quality_score']
        for metric_name in key_metrics:
            try:
                trend = self.analyze_trends(metric_name, days=7)
                quality_trends[metric_name] = trend
            except Exception as e:
                self.logger.error(f"トレンド分析エラー ({metric_name}): {e}")
        
        # 推奨事項生成
        recommendations = self._generate_recommendations(
            overall_score, component_scores, alerts, quality_trends
        )
        
        # システム健全性レポート作成
        health_report = SystemHealth(
            overall_score=overall_score,
            component_scores=component_scores,
            performance_metrics=performance_metrics,
            quality_trends=quality_trends,
            alerts=alerts,
            recommendations=recommendations,
            timestamp=timestamp
        )
        
        # データベース保存
        self._save_system_health_snapshot(health_report)
        
        # メトリクス保存
        self.save_metrics(performance_metrics, quality_metrics)
        
        return health_report
    
    def _calculate_system_performance_score(self, metrics: Dict[str, PerformanceMetric]) -> float:
        """システムパフォーマンススコア算出"""
        scores = []
        
        for metric in metrics.values():
            if metric.status == 'good':
                scores.append(100.0)
            elif metric.status == 'warning':
                scores.append(75.0)
            elif metric.status == 'critical':
                scores.append(30.0)
            else:
                scores.append(50.0)
        
        return statistics.mean(scores) if scores else 0.0
    
    def _calculate_availability_score(self, metrics: Dict[str, PerformanceMetric]) -> float:
        """可用性スコア算出"""
        error_count = len([m for m in metrics.values() if 'error' in m.metric_name])
        total_checks = len(metrics)
        
        if total_checks == 0:
            return 100.0
        
        availability = ((total_checks - error_count) / total_checks) * 100
        return max(0.0, availability)
    
    def _generate_recommendations(self, overall_score: float, 
                                 component_scores: Dict[str, float],
                                 alerts: List[Dict[str, Any]],
                                 trends: Dict[str, QualityTrend]) -> List[str]:
        """改善推奨事項生成"""
        recommendations = []
        
        # 総合スコアベース
        if overall_score < 70:
            recommendations.append("システム全体の健全性が低下しています。包括的な改善が必要です。")
        
        # コンポーネント別推奨
        if component_scores.get('system_performance', 0) < 80:
            recommendations.append("システムパフォーマンスの最適化が必要です。CPUやメモリ使用量を確認してください。")
        
        if component_scores.get('data_quality', 0) < 80:
            recommendations.append("データ品質の改善が必要です。データ完全性と正確性をチェックしてください。")
        
        # アラートベース
        critical_alerts = [a for a in alerts if a.get('severity') == 'critical']
        if critical_alerts:
            recommendations.append(f"{len(critical_alerts)}件の重要なアラートがあります。緊急対応が必要です。")
        
        # トレンドベース
        degrading_trends = [
            name for name, trend in trends.items() 
            if trend.trend_direction == 'degrading'
        ]
        if degrading_trends:
            recommendations.append(
                f"以下のメトリクスが悪化傾向です: {', '.join(degrading_trends)}。"
                "原因調査と対策が必要です。"
            )
        
        if not recommendations:
            recommendations.append("システム状態は良好です。現在の品質レベルを維持してください。")
        
        return recommendations
    
    def _save_system_health_snapshot(self, health_report: SystemHealth) -> None:
        """システム健全性スナップショット保存"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO system_health_snapshots 
                (overall_score, component_scores, performance_metrics, quality_trends,
                 alerts, recommendations, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                health_report.overall_score,
                json.dumps(health_report.component_scores, ensure_ascii=False),
                json.dumps({k: asdict(v) for k, v in health_report.performance_metrics.items()}, 
                          ensure_ascii=False, default=str),
                json.dumps({k: asdict(v) for k, v in health_report.quality_trends.items()}, 
                          ensure_ascii=False, default=str),
                json.dumps(health_report.alerts, ensure_ascii=False, default=str),
                json.dumps(health_report.recommendations, ensure_ascii=False),
                health_report.timestamp.isoformat()
            ))
            conn.commit()
    
    def get_health_history(self, days: int = 7) -> List[SystemHealth]:
        """健全性履歴取得"""
        since = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                SELECT overall_score, component_scores, performance_metrics, quality_trends,
                       alerts, recommendations, timestamp
                FROM system_health_snapshots 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (since.isoformat(),))
            
            snapshots = []
            for row in cursor:
                snapshot = SystemHealth(
                    overall_score=row[0],
                    component_scores=json.loads(row[1]),
                    performance_metrics={},  # 詳細は省略
                    quality_trends={},       # 詳細は省略  
                    alerts=json.loads(row[4]),
                    recommendations=json.loads(row[5]),
                    timestamp=datetime.fromisoformat(row[6])
                )
                snapshots.append(snapshot)
            
            return snapshots