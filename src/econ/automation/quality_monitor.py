"""
Data quality monitoring system for economic indicators.

経済指標データの品質監視システム。
データ品質チェック、異常検知、品質レポート生成を行う。
"""

import logging
import os
import sys
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any, Union, Tuple
from dataclasses import dataclass
import json
import pandas as pd
import numpy as np
from pathlib import Path
import sqlite3

# Add src to path if running from project root
if 'src' not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.econ.config.settings import get_econ_config
from src.econ.adapters.investpy_calendar import EconomicEvent
from src.econ.normalize.data_processor import ProcessedIndicator, EconomicDataProcessor

logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """品質問題の定義"""
    issue_id: str
    type: str  # missing_data, outlier, stale_data, api_error, format_error
    severity: str  # low, medium, high, critical
    description: str
    indicator: Optional[str] = None
    value: Optional[float] = None
    expected: Optional[float] = None
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class QualityMetrics:
    """品質指標"""
    total_indicators: int
    data_completeness: float  # 0-100%
    data_freshness: float     # 0-100%
    accuracy_score: float     # 0-100%
    consistency_score: float  # 0-100%
    outlier_count: int
    error_count: int
    warning_count: int
    overall_score: float      # 0-100%
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class QualityMonitor:
    """データ品質監視システム"""
    
    def __init__(self, config):
        """
        初期化
        
        Args:
            config: 経済指標設定
        """
        self.config = config
        self.data_processor = EconomicDataProcessor()
        
        # 品質チェック履歴
        self.quality_history: List[QualityMetrics] = []
        self.issues_history: List[QualityIssue] = []
        
        # 品質基準の設定
        self.quality_thresholds = {
            'completeness_min': 90.0,    # 90%以上のデータ完全性
            'freshness_max_hours': 48,   # 48時間以内のデータ
            'outlier_z_threshold': 3.0,  # Z-score 3.0以上を異常値
            'consistency_min': 85.0,     # 85%以上の一貫性
            'error_rate_max': 0.05,      # 5%以下のエラー率
        }
        
        # データベース初期化
        self._init_quality_database()
    
    def _init_quality_database(self):
        """品質監視用データベースを初期化"""
        try:
            db_path = Path("data/quality") 
            db_path.mkdir(parents=True, exist_ok=True)
            
            self.db_path = db_path / "quality_monitor.db"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 品質メトリクス履歴テーブル
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quality_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        total_indicators INTEGER,
                        data_completeness REAL,
                        data_freshness REAL,
                        accuracy_score REAL,
                        consistency_score REAL,
                        outlier_count INTEGER,
                        error_count INTEGER,
                        warning_count INTEGER,
                        overall_score REAL
                    )
                """)
                
                # 品質問題履歴テーブル
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quality_issues (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        issue_id TEXT NOT NULL,
                        type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        description TEXT NOT NULL,
                        indicator TEXT,
                        value REAL,
                        expected_value REAL,
                        timestamp TEXT NOT NULL,
                        metadata TEXT
                    )
                """)
                
                conn.commit()
                logger.info(f"Quality database initialized at {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize quality database: {e}")
    
    def run_quality_check(self) -> Dict[str, Any]:
        """包括的な品質チェックを実行"""
        logger.info("Running comprehensive quality check")
        
        try:
            # 現在の指標データを取得
            indicators = self._get_recent_indicators()
            
            # 各品質チェックを実行
            completeness = self._check_data_completeness(indicators)
            freshness = self._check_data_freshness(indicators)
            accuracy = self._check_data_accuracy(indicators)
            consistency = self._check_data_consistency(indicators)
            outliers = self._detect_outliers(indicators)
            
            # 品質問題をコンパイル
            issues = []
            issues.extend(completeness['issues'])
            issues.extend(freshness['issues'])
            issues.extend(accuracy['issues'])
            issues.extend(consistency['issues'])
            issues.extend(outliers['issues'])
            
            # 重要度別に分類
            severity_breakdown = {
                'critical': len([i for i in issues if i.severity == 'critical']),
                'high': len([i for i in issues if i.severity == 'high']),
                'medium': len([i for i in issues if i.severity == 'medium']),
                'low': len([i for i in issues if i.severity == 'low'])
            }
            
            # 総合品質スコアを計算
            overall_score = self._calculate_overall_score(
                completeness['score'],
                freshness['score'],
                accuracy['score'],
                consistency['score'],
                len(outliers['issues'])
            )
            
            # 品質メトリクスを作成
            metrics = QualityMetrics(
                total_indicators=len(indicators),
                data_completeness=completeness['score'],
                data_freshness=freshness['score'],
                accuracy_score=accuracy['score'],
                consistency_score=consistency['score'],
                outlier_count=len(outliers['issues']),
                error_count=severity_breakdown['critical'] + severity_breakdown['high'],
                warning_count=severity_breakdown['medium'] + severity_breakdown['low'],
                overall_score=overall_score
            )
            
            # 履歴に記録
            self.quality_history.append(metrics)
            self.issues_history.extend(issues)
            
            # データベースに保存
            self._save_quality_metrics(metrics)
            self._save_quality_issues(issues)
            
            # 品質レポートを生成
            report = {
                'timestamp': metrics.timestamp.isoformat(),
                'overall_score': overall_score,
                'metrics': {
                    'total_indicators': metrics.total_indicators,
                    'data_completeness': metrics.data_completeness,
                    'data_freshness': metrics.data_freshness,
                    'accuracy_score': metrics.accuracy_score,
                    'consistency_score': metrics.consistency_score,
                    'outlier_count': metrics.outlier_count,
                    'error_count': metrics.error_count,
                    'warning_count': metrics.warning_count
                },
                'issues': [
                    {
                        'type': issue.type,
                        'severity': issue.severity,
                        'description': issue.description,
                        'indicator': issue.indicator,
                        'timestamp': issue.timestamp.isoformat()
                    }
                    for issue in issues
                ],
                'severity_breakdown': severity_breakdown,
                'thresholds': self.quality_thresholds,
                'recommendations': self._generate_recommendations(metrics, issues)
            }
            
            logger.info(f"Quality check completed. Overall score: {overall_score:.1f}%, Issues: {len(issues)}")
            
            return report
            
        except Exception as e:
            logger.error(f"Quality check failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _get_recent_indicators(self) -> List[ProcessedIndicator]:
        """最近の指標データを取得"""
        # 実際の実装では、データベースや外部APIから取得
        # ここでは簡易版として空のリストを返す
        return []
    
    def _check_data_completeness(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """データ完全性をチェック"""
        if not indicators:
            return {
                'score': 0.0,
                'issues': [QualityIssue(
                    issue_id='completeness_no_data',
                    type='missing_data',
                    severity='critical',
                    description='No indicator data available for quality check'
                )]
            }
        
        issues = []
        total_indicators = len(indicators)
        complete_indicators = 0
        
        for indicator in indicators:
            is_complete = True
            
            # 必須フィールドの確認
            if indicator.normalized_value is None:
                issues.append(QualityIssue(
                    issue_id=f'missing_value_{indicator.original_event.title}',
                    type='missing_data',
                    severity='high',
                    description=f'Missing normalized value for {indicator.original_event.title}',
                    indicator=indicator.original_event.title
                ))
                is_complete = False
            
            # 履歴データの確認
            if indicator.historical_data is None or len(indicator.historical_data) == 0:
                issues.append(QualityIssue(
                    issue_id=f'missing_historical_{indicator.original_event.title}',
                    type='missing_data',
                    severity='medium',
                    description=f'Missing historical data for {indicator.original_event.title}',
                    indicator=indicator.original_event.title
                ))
                is_complete = False
            
            if is_complete:
                complete_indicators += 1
        
        completeness_score = (complete_indicators / total_indicators) * 100 if total_indicators > 0 else 0
        
        # 閾値チェック
        if completeness_score < self.quality_thresholds['completeness_min']:
            issues.append(QualityIssue(
                issue_id='low_completeness',
                type='missing_data',
                severity='high',
                description=f'Data completeness {completeness_score:.1f}% below threshold {self.quality_thresholds["completeness_min"]}%'
            ))
        
        return {
            'score': completeness_score,
            'issues': issues,
            'details': {
                'total_indicators': total_indicators,
                'complete_indicators': complete_indicators
            }
        }
    
    def _check_data_freshness(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """データ鮮度をチェック"""
        if not indicators:
            return {'score': 0.0, 'issues': []}
        
        issues = []
        now = datetime.utcnow()
        fresh_indicators = 0
        max_age = timedelta(hours=self.quality_thresholds['freshness_max_hours'])
        
        for indicator in indicators:
            # データの最終更新時刻をチェック
            data_timestamp = indicator.processing_timestamp or now
            age = now - data_timestamp
            
            if age > max_age:
                issues.append(QualityIssue(
                    issue_id=f'stale_data_{indicator.original_event.title}',
                    type='stale_data',
                    severity='medium',
                    description=f'Data for {indicator.original_event.title} is {age.total_seconds()/3600:.1f} hours old',
                    indicator=indicator.original_event.title,
                    metadata={'age_hours': age.total_seconds()/3600}
                ))
            else:
                fresh_indicators += 1
        
        freshness_score = (fresh_indicators / len(indicators)) * 100 if indicators else 0
        
        return {
            'score': freshness_score,
            'issues': issues
        }
    
    def _check_data_accuracy(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """データ精度をチェック"""
        issues = []
        accurate_indicators = 0
        
        for indicator in indicators:
            accuracy_issues_count = 0
            
            # データ品質スコアの確認
            if indicator.data_quality_score < 70:  # 70未満は低品質
                issues.append(QualityIssue(
                    issue_id=f'low_quality_{indicator.original_event.title}',
                    type='format_error',
                    severity='medium',
                    description=f'Low quality score {indicator.data_quality_score:.1f} for {indicator.original_event.title}',
                    indicator=indicator.original_event.title,
                    value=indicator.data_quality_score
                ))
                accuracy_issues_count += 1
            
            # 異常な値のチェック
            if indicator.normalized_value is not None:
                if np.isnan(indicator.normalized_value) or np.isinf(indicator.normalized_value):
                    issues.append(QualityIssue(
                        issue_id=f'invalid_value_{indicator.original_event.title}',
                        type='format_error',
                        severity='high',
                        description=f'Invalid numeric value for {indicator.original_event.title}',
                        indicator=indicator.original_event.title,
                        value=indicator.normalized_value
                    ))
                    accuracy_issues_count += 1
            
            if accuracy_issues_count == 0:
                accurate_indicators += 1
        
        accuracy_score = (accurate_indicators / len(indicators)) * 100 if indicators else 100
        
        return {
            'score': accuracy_score,
            'issues': issues
        }
    
    def _check_data_consistency(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """データ一貫性をチェック"""
        issues = []
        consistent_indicators = 0
        
        for indicator in indicators:
            consistency_issues = 0
            
            # 単位の一貫性チェック
            if hasattr(indicator.original_event, 'unit') and indicator.unit_standardized is None:
                issues.append(QualityIssue(
                    issue_id=f'unit_inconsistency_{indicator.original_event.title}',
                    type='format_error',
                    severity='low',
                    description=f'Unit standardization failed for {indicator.original_event.title}',
                    indicator=indicator.original_event.title
                ))
                consistency_issues += 1
            
            # 変化率の妥当性チェック
            if indicator.mom_change is not None and abs(indicator.mom_change) > 1000:  # 1000%を超える変化は異常
                issues.append(QualityIssue(
                    issue_id=f'extreme_change_{indicator.original_event.title}',
                    type='outlier',
                    severity='medium',
                    description=f'Extreme MoM change {indicator.mom_change:.1f}% for {indicator.original_event.title}',
                    indicator=indicator.original_event.title,
                    value=indicator.mom_change
                ))
                consistency_issues += 1
            
            if consistency_issues == 0:
                consistent_indicators += 1
        
        consistency_score = (consistent_indicators / len(indicators)) * 100 if indicators else 100
        
        return {
            'score': consistency_score,
            'issues': issues
        }
    
    def _detect_outliers(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """異常値を検出"""
        issues = []
        
        for indicator in indicators:
            # Z-scoreによる異常値検出
            if (indicator.z_score is not None and 
                abs(indicator.z_score) > self.quality_thresholds['outlier_z_threshold']):
                
                severity = 'high' if abs(indicator.z_score) > 4.0 else 'medium'
                
                issues.append(QualityIssue(
                    issue_id=f'outlier_{indicator.original_event.title}',
                    type='outlier',
                    severity=severity,
                    description=f'Statistical outlier detected for {indicator.original_event.title} (Z-score: {indicator.z_score:.2f})',
                    indicator=indicator.original_event.title,
                    value=indicator.normalized_value,
                    metadata={'z_score': indicator.z_score}
                ))
            
            # 極端なボラティリティのチェック
            if (indicator.volatility_index is not None and 
                indicator.volatility_index > 50):  # 50%を超えるボラティリティ
                
                issues.append(QualityIssue(
                    issue_id=f'high_volatility_{indicator.original_event.title}',
                    type='outlier',
                    severity='medium',
                    description=f'High volatility {indicator.volatility_index:.1f}% for {indicator.original_event.title}',
                    indicator=indicator.original_event.title,
                    value=indicator.volatility_index
                ))
        
        return {
            'score': max(0, 100 - len(issues) * 10),  # 異常値1つあたり10点減点
            'issues': issues
        }
    
    def _calculate_overall_score(
        self,
        completeness: float,
        freshness: float,
        accuracy: float,
        consistency: float,
        outlier_count: int
    ) -> float:
        """総合品質スコアを計算"""
        # 重み付き平均で総合スコアを計算
        weights = {
            'completeness': 0.3,
            'freshness': 0.2,
            'accuracy': 0.25,
            'consistency': 0.15,
            'outliers': 0.1
        }
        
        outlier_penalty = min(outlier_count * 5, 50)  # 異常値1つあたり5点減点、最大50点
        outlier_score = max(0, 100 - outlier_penalty)
        
        overall_score = (
            completeness * weights['completeness'] +
            freshness * weights['freshness'] +
            accuracy * weights['accuracy'] +
            consistency * weights['consistency'] +
            outlier_score * weights['outliers']
        )
        
        return round(overall_score, 1)
    
    def _generate_recommendations(
        self,
        metrics: QualityMetrics,
        issues: List[QualityIssue]
    ) -> List[str]:
        """品質改善の推奨事項を生成"""
        recommendations = []
        
        # データ完全性の改善
        if metrics.data_completeness < self.quality_thresholds['completeness_min']:
            recommendations.append(
                f"データ完全性を改善してください（現在: {metrics.data_completeness:.1f}%、目標: {self.quality_thresholds['completeness_min']}%以上）"
            )
        
        # データ鮮度の改善
        if metrics.data_freshness < 90:
            recommendations.append("データ更新頻度を上げて、より新しいデータを取得してください")
        
        # エラー対応
        if metrics.error_count > 0:
            recommendations.append(f"{metrics.error_count}個の重要なエラーを修正してください")
        
        # 異常値対応
        if metrics.outlier_count > 5:
            recommendations.append(f"{metrics.outlier_count}個の異常値を確認し、必要に応じてデータソースを見直してください")
        
        # API エラー対応
        api_errors = [i for i in issues if i.type == 'api_error']
        if api_errors:
            recommendations.append("API接続エラーを確認し、設定や権限を見直してください")
        
        # 品質スコア低下への対応
        if metrics.overall_score < 80:
            recommendations.append("総合品質スコアが低下しています。システム全体の見直しを検討してください")
        
        return recommendations
    
    def _save_quality_metrics(self, metrics: QualityMetrics):
        """品質メトリクスをデータベースに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO quality_metrics (
                        timestamp, total_indicators, data_completeness, data_freshness,
                        accuracy_score, consistency_score, outlier_count, error_count,
                        warning_count, overall_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.timestamp.isoformat(),
                    metrics.total_indicators,
                    metrics.data_completeness,
                    metrics.data_freshness,
                    metrics.accuracy_score,
                    metrics.consistency_score,
                    metrics.outlier_count,
                    metrics.error_count,
                    metrics.warning_count,
                    metrics.overall_score
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save quality metrics: {e}")
    
    def _save_quality_issues(self, issues: List[QualityIssue]):
        """品質問題をデータベースに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for issue in issues:
                    cursor.execute("""
                        INSERT INTO quality_issues (
                            issue_id, type, severity, description, indicator,
                            value, expected_value, timestamp, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        issue.issue_id,
                        issue.type,
                        issue.severity,
                        issue.description,
                        issue.indicator,
                        issue.value,
                        issue.expected,
                        issue.timestamp.isoformat(),
                        json.dumps(issue.metadata) if issue.metadata else None
                    ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save quality issues: {e}")
    
    # =============================================================================
    # 履歴・統計機能
    # =============================================================================
    
    def get_quality_trend(self, days: int = 7) -> Dict[str, Any]:
        """品質トレンドを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, overall_score, data_completeness, data_freshness,
                           accuracy_score, consistency_score, outlier_count, error_count
                    FROM quality_metrics
                    WHERE datetime(timestamp) >= datetime('now', '-{} days')
                    ORDER BY timestamp ASC
                """.format(days))
                
                rows = cursor.fetchall()
                
                if not rows:
                    return {'message': 'No quality data available for the specified period'}
                
                trend_data = {
                    'period_days': days,
                    'data_points': len(rows),
                    'timeline': [],
                    'overall_score': [],
                    'completeness': [],
                    'freshness': [],
                    'accuracy': [],
                    'consistency': [],
                    'outlier_counts': [],
                    'error_counts': []
                }
                
                for row in rows:
                    trend_data['timeline'].append(row[0])
                    trend_data['overall_score'].append(row[1])
                    trend_data['completeness'].append(row[2])
                    trend_data['freshness'].append(row[3])
                    trend_data['accuracy'].append(row[4])
                    trend_data['consistency'].append(row[5])
                    trend_data['outlier_counts'].append(row[6])
                    trend_data['error_counts'].append(row[7])
                
                # 統計サマリーを追加
                trend_data['summary'] = {
                    'avg_overall_score': np.mean(trend_data['overall_score']),
                    'trend_direction': 'improving' if trend_data['overall_score'][-1] > trend_data['overall_score'][0] else 'declining',
                    'total_errors': sum(trend_data['error_counts']),
                    'total_outliers': sum(trend_data['outlier_counts'])
                }
                
                return trend_data
                
        except Exception as e:
            logger.error(f"Failed to get quality trend: {e}")
            return {'error': str(e)}
    
    def get_issue_statistics(self, days: int = 30) -> Dict[str, Any]:
        """問題統計を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 期間内の問題統計
                cursor.execute("""
                    SELECT type, severity, COUNT(*) as count
                    FROM quality_issues
                    WHERE datetime(timestamp) >= datetime('now', '-{} days')
                    GROUP BY type, severity
                    ORDER BY count DESC
                """.format(days))
                
                type_severity_counts = cursor.fetchall()
                
                # 指標別問題統計
                cursor.execute("""
                    SELECT indicator, COUNT(*) as count
                    FROM quality_issues
                    WHERE datetime(timestamp) >= datetime('now', '-{} days')
                      AND indicator IS NOT NULL
                    GROUP BY indicator
                    ORDER BY count DESC
                    LIMIT 10
                """.format(days))
                
                indicator_counts = cursor.fetchall()
                
                statistics = {
                    'period_days': days,
                    'type_severity_breakdown': {},
                    'top_problematic_indicators': [],
                    'total_issues': 0
                }
                
                for type_name, severity, count in type_severity_counts:
                    if type_name not in statistics['type_severity_breakdown']:
                        statistics['type_severity_breakdown'][type_name] = {}
                    statistics['type_severity_breakdown'][type_name][severity] = count
                    statistics['total_issues'] += count
                
                for indicator, count in indicator_counts:
                    statistics['top_problematic_indicators'].append({
                        'indicator': indicator,
                        'issue_count': count
                    })
                
                return statistics
                
        except Exception as e:
            logger.error(f"Failed to get issue statistics: {e}")
            return {'error': str(e)}
    
    def cleanup_old_data(self, days: int = 90):
        """古いデータをクリーンアップ"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 古い品質メトリクスを削除
                cursor.execute("""
                    DELETE FROM quality_metrics
                    WHERE datetime(timestamp) < datetime('now', '-{} days')
                """.format(days))
                metrics_deleted = cursor.rowcount
                
                # 古い品質問題を削除
                cursor.execute("""
                    DELETE FROM quality_issues
                    WHERE datetime(timestamp) < datetime('now', '-{} days')
                """.format(days))
                issues_deleted = cursor.rowcount
                
                conn.commit()
                
                logger.info(f"Cleaned up {metrics_deleted} old quality metrics and {issues_deleted} old issues")
                
                return {
                    'metrics_deleted': metrics_deleted,
                    'issues_deleted': issues_deleted
                }
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return {'error': str(e)}


# サンプル使用例
def main():
    """サンプル実行"""
    # 設定を読み込み
    config = get_econ_config()
    
    # 品質監視システムを作成
    quality_monitor = QualityMonitor(config)
    
    # 品質チェックを実行
    report = quality_monitor.run_quality_check()
    print(f"Quality Report: {json.dumps(report, indent=2)}")
    
    # トレンドを確認
    trend = quality_monitor.get_quality_trend(days=7)
    print(f"Quality Trend: {json.dumps(trend, indent=2)}")


if __name__ == "__main__":
    main()