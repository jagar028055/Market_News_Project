"""
経済指標システム パフォーマンステストスイート
負荷テスト、ストレステスト、ベンチマーク機能を提供
"""

import os
import time
import json
import sqlite3
import asyncio
import threading
import statistics
import concurrent.futures
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import psutil
import logging

from ..config.settings import get_econ_config


@dataclass
class PerformanceTestResult:
    """パフォーマンステスト結果"""
    test_name: str
    test_type: str  # load, stress, spike, volume, endurance
    duration_seconds: float
    requests_total: int
    requests_successful: int  
    requests_failed: int
    requests_per_second: float
    response_times: List[float]
    response_time_avg: float
    response_time_median: float
    response_time_p95: float
    response_time_p99: float
    cpu_usage_avg: float
    memory_usage_avg: float
    errors: List[str]
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class LoadTestConfig:
    """負荷テスト設定"""
    concurrent_users: int
    duration_seconds: int
    ramp_up_seconds: int
    target_function: Callable
    function_args: List[Any]
    function_kwargs: Dict[str, Any]
    success_criteria: Dict[str, float]


class PerformanceTester:
    """パフォーマンステストスイート"""
    
    def __init__(self, config=None):
        self.config = config or get_econ_config()
        
        # テスト設定
        self.test_config = {
            'results_dir': self.config.get('performance_test_results_dir', 'build/performance_tests'),
            'default_timeout': self.config.get('performance_test_timeout', 300),
            'memory_limit_mb': self.config.get('performance_memory_limit_mb', 2048),
            'cpu_limit_percent': self.config.get('performance_cpu_limit_percent', 90),
            'benchmark_thresholds': {
                'data_fetch_ms': 3000,
                'report_generation_ms': 2000,
                'quality_check_ms': 5000,
                'scheduler_startup_ms': 1000
            }
        }
        
        # データベース初期化
        self.db_path = Path(self.test_config['results_dir']) / 'performance_results.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # システム監視
        self.system_monitor = SystemMonitor()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _init_database(self) -> None:
        """パフォーマンステスト結果データベース初期化"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    requests_total INTEGER NOT NULL,
                    requests_successful INTEGER NOT NULL,
                    requests_failed INTEGER NOT NULL,
                    requests_per_second REAL NOT NULL,
                    response_time_avg REAL NOT NULL,
                    response_time_median REAL NOT NULL,
                    response_time_p95 REAL NOT NULL,
                    response_time_p99 REAL NOT NULL,
                    cpu_usage_avg REAL NOT NULL,
                    memory_usage_avg REAL NOT NULL,
                    errors TEXT,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    INDEX(test_name, timestamp)
                )
            """)
    
    def run_load_test(self, test_config: LoadTestConfig) -> PerformanceTestResult:
        """負荷テスト実行"""
        self.logger.info(f"負荷テスト開始: {test_config.concurrent_users}ユーザー, {test_config.duration_seconds}秒")
        
        start_time = time.time()
        results = []
        errors = []
        
        # システム監視開始
        self.system_monitor.start_monitoring()
        
        try:
            # 並行実行設定
            with concurrent.futures.ThreadPoolExecutor(max_workers=test_config.concurrent_users) as executor:
                # ランプアップ期間を考慮したユーザー開始時間
                user_start_times = []
                if test_config.ramp_up_seconds > 0:
                    ramp_interval = test_config.ramp_up_seconds / test_config.concurrent_users
                    for i in range(test_config.concurrent_users):
                        user_start_times.append(i * ramp_interval)
                else:
                    user_start_times = [0] * test_config.concurrent_users
                
                # ユーザーごとのタスク実行
                futures = []
                for i, start_delay in enumerate(user_start_times):
                    future = executor.submit(
                        self._simulate_user_load,
                        user_id=i,
                        start_delay=start_delay,
                        duration=test_config.duration_seconds,
                        target_function=test_config.target_function,
                        function_args=test_config.function_args,
                        function_kwargs=test_config.function_kwargs
                    )
                    futures.append(future)
                
                # 結果収集
                for future in concurrent.futures.as_completed(futures):
                    try:
                        user_results = future.result()
                        results.extend(user_results['response_times'])
                        errors.extend(user_results['errors'])
                    except Exception as e:
                        errors.append(f"ユーザー実行エラー: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"負荷テスト実行エラー: {e}")
            errors.append(f"テスト実行エラー: {str(e)}")
        
        finally:
            # システム監視終了
            system_stats = self.system_monitor.stop_monitoring()
        
        # 結果集計
        total_duration = time.time() - start_time
        
        if results:
            response_times = [r['duration'] for r in results if r['success']]
            successful_requests = len([r for r in results if r['success']])
            failed_requests = len([r for r in results if not r['success']])
        else:
            response_times = []
            successful_requests = 0
            failed_requests = len(errors)
        
        # パフォーマンス統計計算
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            p95_response_time = self._percentile(response_times, 95)
            p99_response_time = self._percentile(response_times, 99)
        else:
            avg_response_time = median_response_time = p95_response_time = p99_response_time = 0.0
        
        requests_per_second = len(results) / total_duration if total_duration > 0 else 0.0
        
        # テスト結果作成
        test_result = PerformanceTestResult(
            test_name=f"load_test_{test_config.concurrent_users}users",
            test_type="load",
            duration_seconds=total_duration,
            requests_total=len(results),
            requests_successful=successful_requests,
            requests_failed=failed_requests,
            requests_per_second=requests_per_second,
            response_times=response_times,
            response_time_avg=avg_response_time,
            response_time_median=median_response_time,
            response_time_p95=p95_response_time,
            response_time_p99=p99_response_time,
            cpu_usage_avg=system_stats['cpu_avg'],
            memory_usage_avg=system_stats['memory_avg'],
            errors=errors,
            timestamp=datetime.now(),
            metadata={
                'concurrent_users': test_config.concurrent_users,
                'ramp_up_seconds': test_config.ramp_up_seconds,
                'target_duration': test_config.duration_seconds
            }
        )
        
        # データベース保存
        self._save_test_result(test_result)
        
        # 成功基準チェック
        self._check_success_criteria(test_result, test_config.success_criteria)
        
        self.logger.info(f"負荷テスト完了: RPS={requests_per_second:.2f}, 成功率={successful_requests/(len(results) or 1)*100:.1f}%")
        
        return test_result
    
    def _simulate_user_load(self, user_id: int, start_delay: float, duration: int,
                           target_function: Callable, function_args: List[Any],
                           function_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """ユーザー負荷シミュレーション"""
        # 開始遅延
        time.sleep(start_delay)
        
        results = []
        errors = []
        end_time = time.time() + duration
        
        while time.time() < end_time:
            try:
                start = time.time()
                result = target_function(*function_args, **function_kwargs)
                elapsed = time.time() - start
                
                results.append({
                    'user_id': user_id,
                    'duration': elapsed * 1000,  # ms
                    'success': True,
                    'timestamp': datetime.now(),
                    'result_size': len(str(result)) if result else 0
                })
                
                # 少し待機（現実的な使用パターン）
                time.sleep(0.1)
                
            except Exception as e:
                errors.append(f"User {user_id}: {str(e)}")
                results.append({
                    'user_id': user_id,
                    'duration': 0,
                    'success': False,
                    'timestamp': datetime.now(),
                    'error': str(e)
                })
        
        return {
            'user_id': user_id,
            'response_times': results,
            'errors': errors
        }
    
    def run_stress_test(self) -> PerformanceTestResult:
        """ストレステスト（システム限界確認）"""
        self.logger.info("ストレステスト開始")
        
        from ..adapters.investpy_calendar import InvestpyCalendarAdapter
        from ..reports.daily_list_renderer import DailyListRenderer
        
        # 段階的負荷増加
        stress_levels = [10, 25, 50, 100, 200]
        breaking_point = None
        
        for concurrent_users in stress_levels:
            self.logger.info(f"ストレステストレベル: {concurrent_users}同時ユーザー")
            
            # 短時間の負荷テスト
            config = LoadTestConfig(
                concurrent_users=concurrent_users,
                duration_seconds=30,
                ramp_up_seconds=5,
                target_function=self._stress_test_function,
                function_args=[],
                function_kwargs={},
                success_criteria={'error_rate': 5.0}
            )
            
            result = self.run_load_test(config)
            
            # システム限界判定
            error_rate = (result.requests_failed / result.requests_total * 100) if result.requests_total > 0 else 100
            if (error_rate > 10 or 
                result.cpu_usage_avg > self.test_config['cpu_limit_percent'] or
                result.memory_usage_avg > self.test_config['memory_limit_mb']):
                
                breaking_point = concurrent_users
                self.logger.warning(f"システム限界到達: {concurrent_users}ユーザー")
                break
        
        # ストレステスト結果作成
        return PerformanceTestResult(
            test_name="stress_test",
            test_type="stress",
            duration_seconds=sum([30] * len(stress_levels[:stress_levels.index(breaking_point or max(stress_levels))+1])),
            requests_total=0,  # 詳細は個別テスト結果参照
            requests_successful=0,
            requests_failed=0,
            requests_per_second=0,
            response_times=[],
            response_time_avg=0,
            response_time_median=0,
            response_time_p95=0,
            response_time_p99=0,
            cpu_usage_avg=0,
            memory_usage_avg=0,
            errors=[],
            timestamp=datetime.now(),
            metadata={
                'breaking_point': breaking_point,
                'tested_levels': stress_levels[:stress_levels.index(breaking_point or max(stress_levels))+1],
                'max_stable_users': breaking_point - 1 if breaking_point else max(stress_levels)
            }
        )
    
    def _stress_test_function(self) -> Any:
        """ストレステスト用負荷関数"""
        from ..adapters.investpy_calendar import InvestpyCalendarAdapter
        from ..reports.daily_list_renderer import DailyListRenderer
        
        # データ取得
        adapter = InvestpyCalendarAdapter()
        yesterday = datetime.now() - timedelta(days=1)
        events = adapter.get_economic_calendar(
            from_date=yesterday.strftime('%Y-%m-%d'),
            to_date=yesterday.strftime('%Y-%m-%d')
        )
        
        # レポート生成
        renderer = DailyListRenderer(self.config)
        report = renderer.render_daily_list(events[:5], 'markdown')  # 最初の5件のみ
        
        return len(report)
    
    def run_benchmark_suite(self) -> Dict[str, PerformanceTestResult]:
        """ベンチマークスイート実行"""
        self.logger.info("ベンチマークスイート開始")
        
        benchmarks = {
            'data_fetching': self._benchmark_data_fetching,
            'report_generation': self._benchmark_report_generation,
            'quality_monitoring': self._benchmark_quality_monitoring,
            'scheduler_operations': self._benchmark_scheduler_operations
        }
        
        results = {}
        for benchmark_name, benchmark_func in benchmarks.items():
            self.logger.info(f"ベンチマーク実行: {benchmark_name}")
            result = benchmark_func()
            results[benchmark_name] = result
            self._save_test_result(result)
        
        return results
    
    def _benchmark_data_fetching(self) -> PerformanceTestResult:
        """データ取得ベンチマーク"""
        from ..adapters.investpy_calendar import InvestpyCalendarAdapter
        from ..adapters.fmp_calendar import FMPCalendarAdapter
        
        iterations = 10
        response_times = []
        errors = []
        
        self.system_monitor.start_monitoring()
        
        try:
            for i in range(iterations):
                start_time = time.time()
                
                try:
                    # InvestPy
                    investpy_adapter = InvestpyCalendarAdapter()
                    yesterday = datetime.now() - timedelta(days=1)
                    investpy_events = investpy_adapter.get_economic_calendar(
                        from_date=yesterday.strftime('%Y-%m-%d'),
                        to_date=yesterday.strftime('%Y-%m-%d')
                    )
                    
                    # FMP フォールバック
                    fmp_adapter = FMPCalendarAdapter(self.config)
                    fmp_events = fmp_adapter.get_economic_calendar(
                        from_date=yesterday.strftime('%Y-%m-%d'),
                        to_date=yesterday.strftime('%Y-%m-%d')
                    )
                    
                    duration = (time.time() - start_time) * 1000
                    response_times.append(duration)
                    
                except Exception as e:
                    errors.append(f"Iteration {i}: {str(e)}")
        
        finally:
            system_stats = self.system_monitor.stop_monitoring()
        
        # 結果集計
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            p95_time = self._percentile(response_times, 95)
            p99_time = self._percentile(response_times, 99)
        else:
            avg_time = median_time = p95_time = p99_time = 0.0
        
        return PerformanceTestResult(
            test_name="benchmark_data_fetching",
            test_type="benchmark",
            duration_seconds=sum(response_times) / 1000,
            requests_total=iterations,
            requests_successful=len(response_times),
            requests_failed=len(errors),
            requests_per_second=len(response_times) / (sum(response_times) / 1000) if response_times else 0,
            response_times=response_times,
            response_time_avg=avg_time,
            response_time_median=median_time,
            response_time_p95=p95_time,
            response_time_p99=p99_time,
            cpu_usage_avg=system_stats['cpu_avg'],
            memory_usage_avg=system_stats['memory_avg'],
            errors=errors,
            timestamp=datetime.now(),
            metadata={
                'iterations': iterations,
                'threshold_ms': self.test_config['benchmark_thresholds']['data_fetch_ms']
            }
        )
    
    def _benchmark_report_generation(self) -> PerformanceTestResult:
        """レポート生成ベンチマーク"""
        from ..reports.daily_list_renderer import DailyListRenderer
        
        iterations = 20
        response_times = []
        errors = []
        
        # サンプルデータ
        sample_events = [
            {
                'time': f'0{8+i}:30' if i < 2 else f'{8+i}:30',
                'country': ['US', 'EU', 'JP', 'UK', 'CA'][i % 5],
                'event': f'Economic Indicator {i+1}',
                'importance': ['High', 'Medium', 'Low'][i % 3],
                'actual': f'{2.0 + i * 0.1:.1f}%',
                'forecast': f'{2.1 + i * 0.1:.1f}%',
                'previous': f'{1.9 + i * 0.1:.1f}%'
            }
            for i in range(20)  # 20件のサンプルデータ
        ]
        
        self.system_monitor.start_monitoring()
        
        try:
            renderer = DailyListRenderer(self.config)
            
            for i in range(iterations):
                start_time = time.time()
                
                try:
                    # Markdown生成
                    markdown_report = renderer.render_daily_list(sample_events, 'markdown')
                    
                    # HTML生成
                    html_report = renderer.render_daily_list(sample_events, 'html')
                    
                    # CSV生成
                    csv_report = renderer.render_daily_list(sample_events, 'csv')
                    
                    duration = (time.time() - start_time) * 1000
                    response_times.append(duration)
                    
                except Exception as e:
                    errors.append(f"Iteration {i}: {str(e)}")
        
        finally:
            system_stats = self.system_monitor.stop_monitoring()
        
        # 結果集計
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            p95_time = self._percentile(response_times, 95)
            p99_time = self._percentile(response_times, 99)
        else:
            avg_time = median_time = p95_time = p99_time = 0.0
        
        return PerformanceTestResult(
            test_name="benchmark_report_generation",
            test_type="benchmark",
            duration_seconds=sum(response_times) / 1000,
            requests_total=iterations,
            requests_successful=len(response_times),
            requests_failed=len(errors),
            requests_per_second=len(response_times) / (sum(response_times) / 1000) if response_times else 0,
            response_times=response_times,
            response_time_avg=avg_time,
            response_time_median=median_time,
            response_time_p95=p95_time,
            response_time_p99=p99_time,
            cpu_usage_avg=system_stats['cpu_avg'],
            memory_usage_avg=system_stats['memory_avg'],
            errors=errors,
            timestamp=datetime.now(),
            metadata={
                'iterations': iterations,
                'sample_events_count': len(sample_events),
                'threshold_ms': self.test_config['benchmark_thresholds']['report_generation_ms']
            }
        )
    
    def _benchmark_quality_monitoring(self) -> PerformanceTestResult:
        """品質監視ベンチマーク"""
        from ..automation.quality_monitor import QualityMonitor
        
        iterations = 5  # 品質チェックは重い処理なので少なめ
        response_times = []
        errors = []
        
        self.system_monitor.start_monitoring()
        
        try:
            monitor = QualityMonitor(self.config)
            
            for i in range(iterations):
                start_time = time.time()
                
                try:
                    quality_report = monitor.run_quality_check()
                    duration = (time.time() - start_time) * 1000
                    response_times.append(duration)
                    
                except Exception as e:
                    errors.append(f"Iteration {i}: {str(e)}")
        
        finally:
            system_stats = self.system_monitor.stop_monitoring()
        
        # 結果集計
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            p95_time = self._percentile(response_times, 95)
            p99_time = self._percentile(response_times, 99)
        else:
            avg_time = median_time = p95_time = p99_time = 0.0
        
        return PerformanceTestResult(
            test_name="benchmark_quality_monitoring",
            test_type="benchmark",
            duration_seconds=sum(response_times) / 1000,
            requests_total=iterations,
            requests_successful=len(response_times),
            requests_failed=len(errors),
            requests_per_second=len(response_times) / (sum(response_times) / 1000) if response_times else 0,
            response_times=response_times,
            response_time_avg=avg_time,
            response_time_median=median_time,
            response_time_p95=p95_time,
            response_time_p99=p99_time,
            cpu_usage_avg=system_stats['cpu_avg'],
            memory_usage_avg=system_stats['memory_avg'],
            errors=errors,
            timestamp=datetime.now(),
            metadata={
                'iterations': iterations,
                'threshold_ms': self.test_config['benchmark_thresholds']['quality_check_ms']
            }
        )
    
    def _benchmark_scheduler_operations(self) -> PerformanceTestResult:
        """スケジューラー操作ベンチマーク"""
        from ..automation.scheduler import EconomicScheduler
        
        iterations = 10
        response_times = []
        errors = []
        
        self.system_monitor.start_monitoring()
        
        try:
            for i in range(iterations):
                start_time = time.time()
                
                try:
                    # スケジューラー初期化
                    scheduler = EconomicScheduler(self.config)
                    
                    # テストジョブ登録
                    def dummy_job():
                        time.sleep(0.01)  # 軽い処理
                    
                    scheduler.register_job(
                        job_id=f'benchmark_job_{i}',
                        name=f'Benchmark Job {i}',
                        schedule='*/1 * * * *',
                        function=dummy_job,
                        description='Benchmark test job'
                    )
                    
                    duration = (time.time() - start_time) * 1000
                    response_times.append(duration)
                    
                except Exception as e:
                    errors.append(f"Iteration {i}: {str(e)}")
        
        finally:
            system_stats = self.system_monitor.stop_monitoring()
        
        # 結果集計
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            p95_time = self._percentile(response_times, 95)
            p99_time = self._percentile(response_times, 99)
        else:
            avg_time = median_time = p95_time = p99_time = 0.0
        
        return PerformanceTestResult(
            test_name="benchmark_scheduler_operations",
            test_type="benchmark",
            duration_seconds=sum(response_times) / 1000,
            requests_total=iterations,
            requests_successful=len(response_times),
            requests_failed=len(errors),
            requests_per_second=len(response_times) / (sum(response_times) / 1000) if response_times else 0,
            response_times=response_times,
            response_time_avg=avg_time,
            response_time_median=median_time,
            response_time_p95=p95_time,
            response_time_p99=p99_time,
            cpu_usage_avg=system_stats['cpu_avg'],
            memory_usage_avg=system_stats['memory_avg'],
            errors=errors,
            timestamp=datetime.now(),
            metadata={
                'iterations': iterations,
                'threshold_ms': self.test_config['benchmark_thresholds']['scheduler_startup_ms']
            }
        )
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """パーセンタイル計算"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _check_success_criteria(self, result: PerformanceTestResult, 
                               criteria: Dict[str, float]) -> None:
        """成功基準チェック"""
        failures = []
        
        if 'max_response_time' in criteria:
            if result.response_time_p95 > criteria['max_response_time']:
                failures.append(f"P95レスポンス時間が基準を超過: {result.response_time_p95:.1f}ms > {criteria['max_response_time']}ms")
        
        if 'min_throughput' in criteria:
            if result.requests_per_second < criteria['min_throughput']:
                failures.append(f"スループットが基準を下回り: {result.requests_per_second:.1f}rps < {criteria['min_throughput']}rps")
        
        if 'error_rate' in criteria:
            error_rate = (result.requests_failed / result.requests_total * 100) if result.requests_total > 0 else 0
            if error_rate > criteria['error_rate']:
                failures.append(f"エラー率が基準を超過: {error_rate:.1f}% > {criteria['error_rate']}%")
        
        if failures:
            self.logger.warning(f"性能基準未達成: {'; '.join(failures)}")
        else:
            self.logger.info("すべての性能基準を満たしました")
    
    def _save_test_result(self, result: PerformanceTestResult) -> None:
        """テスト結果データベース保存"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO performance_test_results 
                (test_name, test_type, duration_seconds, requests_total, requests_successful,
                 requests_failed, requests_per_second, response_time_avg, response_time_median,
                 response_time_p95, response_time_p99, cpu_usage_avg, memory_usage_avg,
                 errors, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.test_name,
                result.test_type,
                result.duration_seconds,
                result.requests_total,
                result.requests_successful,
                result.requests_failed,
                result.requests_per_second,
                result.response_time_avg,
                result.response_time_median,
                result.response_time_p95,
                result.response_time_p99,
                result.cpu_usage_avg,
                result.memory_usage_avg,
                json.dumps(result.errors, ensure_ascii=False),
                result.timestamp.isoformat(),
                json.dumps(result.metadata, ensure_ascii=False)
            ))
            conn.commit()
    
    def get_performance_history(self, test_type: str = None, days: int = 30) -> List[PerformanceTestResult]:
        """パフォーマンス履歴取得"""
        since = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(str(self.db_path)) as conn:
            if test_type:
                cursor = conn.execute("""
                    SELECT * FROM performance_test_results 
                    WHERE test_type = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                """, (test_type, since.isoformat()))
            else:
                cursor = conn.execute("""
                    SELECT * FROM performance_test_results 
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                """, (since.isoformat(),))
            
            results = []
            for row in cursor:
                result = PerformanceTestResult(
                    test_name=row[1],
                    test_type=row[2],
                    duration_seconds=row[3],
                    requests_total=row[4],
                    requests_successful=row[5],
                    requests_failed=row[6],
                    requests_per_second=row[7],
                    response_times=[],  # 省略
                    response_time_avg=row[8],
                    response_time_median=row[9],
                    response_time_p95=row[10],
                    response_time_p99=row[11],
                    cpu_usage_avg=row[12],
                    memory_usage_avg=row[13],
                    errors=json.loads(row[14]) if row[14] else [],
                    timestamp=datetime.fromisoformat(row[15]),
                    metadata=json.loads(row[16]) if row[16] else {}
                )
                results.append(result)
            
            return results
    
    def generate_performance_report(self, days: int = 7) -> Dict[str, Any]:
        """パフォーマンスレポート生成"""
        history = self.get_performance_history(days=days)
        
        if not history:
            return {
                'status': 'no_data',
                'message': f'過去{days}日間のパフォーマンステストデータがありません'
            }
        
        # テストタイプ別統計
        by_type = {}
        for result in history:
            if result.test_type not in by_type:
                by_type[result.test_type] = []
            by_type[result.test_type].append(result)
        
        type_stats = {}
        for test_type, results in by_type.items():
            avg_response_time = statistics.mean([r.response_time_avg for r in results])
            avg_throughput = statistics.mean([r.requests_per_second for r in results])
            avg_success_rate = statistics.mean([
                (r.requests_successful / r.requests_total * 100) if r.requests_total > 0 else 0
                for r in results
            ])
            
            type_stats[test_type] = {
                'test_count': len(results),
                'avg_response_time_ms': avg_response_time,
                'avg_throughput_rps': avg_throughput,
                'avg_success_rate_percent': avg_success_rate,
                'latest_result': results[0].test_name
            }
        
        # 全体統計
        overall_stats = {
            'total_tests': len(history),
            'avg_response_time': statistics.mean([r.response_time_avg for r in history]),
            'avg_throughput': statistics.mean([r.requests_per_second for r in history]),
            'avg_cpu_usage': statistics.mean([r.cpu_usage_avg for r in history]),
            'avg_memory_usage': statistics.mean([r.memory_usage_avg for r in history])
        }
        
        return {
            'status': 'success',
            'period_days': days,
            'overall_statistics': overall_stats,
            'by_test_type': type_stats,
            'latest_tests': [
                {
                    'name': r.test_name,
                    'type': r.test_type,
                    'timestamp': r.timestamp.isoformat(),
                    'response_time': r.response_time_avg,
                    'success_rate': (r.requests_successful / r.requests_total * 100) if r.requests_total > 0 else 0
                }
                for r in history[:10]
            ]
        }


class SystemMonitor:
    """システムリソース監視"""
    
    def __init__(self):
        self.monitoring = False
        self.cpu_samples = []
        self.memory_samples = []
        self.monitor_thread = None
    
    def start_monitoring(self) -> None:
        """監視開始"""
        self.monitoring = True
        self.cpu_samples = []
        self.memory_samples = []
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> Dict[str, float]:
        """監視終了・統計返却"""
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join()
        
        return {
            'cpu_avg': statistics.mean(self.cpu_samples) if self.cpu_samples else 0.0,
            'cpu_max': max(self.cpu_samples) if self.cpu_samples else 0.0,
            'memory_avg': statistics.mean(self.memory_samples) if self.memory_samples else 0.0,
            'memory_max': max(self.memory_samples) if self.memory_samples else 0.0
        }
    
    def _monitor_loop(self) -> None:
        """監視ループ"""
        while self.monitoring:
            try:
                self.cpu_samples.append(psutil.cpu_percent())
                self.memory_samples.append(psutil.virtual_memory().used / 1024 / 1024)  # MB
                time.sleep(1)  # 1秒間隔
            except Exception:
                pass  # 監視エラーは無視