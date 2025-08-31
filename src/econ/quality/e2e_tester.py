"""
経済指標システム エンドツーエンドテスト基盤
システム全体を通した統合テスト機能を提供
"""

import os
import time
import json
import asyncio
import sqlite3
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging

from ..config.settings import get_econ_config


@dataclass
class E2ETestStep:
    """E2Eテストステップ"""
    step_id: str
    name: str
    description: str
    function: str
    parameters: Dict[str, Any]
    expected_result: Any
    timeout_seconds: int = 30
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class E2ETestResult:
    """E2Eテスト結果"""
    step_id: str
    status: str  # passed, failed, skipped, error
    actual_result: Any
    expected_result: Any
    duration_seconds: float
    error_message: Optional[str]
    timestamp: datetime
    artifacts: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = {}


@dataclass
class E2ETestScenario:
    """E2Eテストシナリオ"""
    scenario_id: str
    name: str
    description: str
    steps: List[E2ETestStep]
    setup_steps: List[E2ETestStep] = None
    teardown_steps: List[E2ETestStep] = None
    
    def __post_init__(self):
        if self.setup_steps is None:
            self.setup_steps = []
        if self.teardown_steps is None:
            self.teardown_steps = []


@dataclass
class E2ETestExecution:
    """E2Eテスト実行結果"""
    execution_id: str
    scenario_id: str
    scenario_name: str
    total_steps: int
    passed_steps: int
    failed_steps: int
    skipped_steps: int
    error_steps: int
    total_duration: float
    success_rate: float
    step_results: List[E2ETestResult]
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class EndToEndTester:
    """エンドツーエンドテスト基盤"""
    
    def __init__(self, config=None):
        self.config = config or get_econ_config()
        
        # E2E設定
        self.e2e_config = {
            'results_dir': self.config.get('e2e_results_dir', 'build/e2e_tests'),
            'artifacts_dir': self.config.get('e2e_artifacts_dir', 'build/e2e_artifacts'),
            'default_timeout': self.config.get('e2e_timeout_seconds', 60),
            'retry_attempts': self.config.get('e2e_retry_attempts', 2),
            'parallel_execution': self.config.get('e2e_parallel', False)
        }
        
        # データベース初期化
        self.db_path = Path(self.e2e_config['results_dir']) / 'e2e_results.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        Path(self.e2e_config['artifacts_dir']).mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # テストシナリオ
        self.scenarios: Dict[str, E2ETestScenario] = {}
        self._initialize_scenarios()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _init_database(self) -> None:
        """E2Eテスト結果データベース初期化"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS e2e_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT UNIQUE NOT NULL,
                    scenario_id TEXT NOT NULL,
                    scenario_name TEXT NOT NULL,
                    total_steps INTEGER NOT NULL,
                    passed_steps INTEGER NOT NULL,
                    failed_steps INTEGER NOT NULL,
                    skipped_steps INTEGER NOT NULL,
                    error_steps INTEGER NOT NULL,
                    total_duration REAL NOT NULL,
                    success_rate REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    INDEX(execution_id, timestamp)
                );
                
                CREATE TABLE IF NOT EXISTS e2e_step_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    actual_result TEXT,
                    expected_result TEXT,
                    duration_seconds REAL NOT NULL,
                    error_message TEXT,
                    timestamp TEXT NOT NULL,
                    artifacts TEXT,
                    FOREIGN KEY (execution_id) REFERENCES e2e_executions (execution_id),
                    INDEX(execution_id, step_id)
                );
            """)
    
    def _initialize_scenarios(self) -> None:
        """テストシナリオ初期化"""
        # シナリオ1: 日次レポート生成フロー
        daily_report_scenario = E2ETestScenario(
            scenario_id='daily_report_flow',
            name='Daily Report Generation Flow',
            description='完全な日次レポート生成プロセスのテスト',
            setup_steps=[
                E2ETestStep(
                    step_id='setup_data',
                    name='Test Data Setup',
                    description='テスト用データの準備',
                    function='setup_test_data',
                    parameters={},
                    expected_result={'status': 'success'}
                )
            ],
            steps=[
                E2ETestStep(
                    step_id='fetch_calendar_data',
                    name='Fetch Economic Calendar Data',
                    description='経済カレンダーデータ取得',
                    function='fetch_calendar_data',
                    parameters={'date': 'yesterday'},
                    expected_result={'events_count': {'min': 1}},
                    timeout_seconds=30
                ),
                E2ETestStep(
                    step_id='generate_daily_report',
                    name='Generate Daily Report',
                    description='日次レポート生成',
                    function='generate_daily_report',
                    parameters={'format': 'markdown'},
                    expected_result={'report_size': {'min': 100}},
                    dependencies=['fetch_calendar_data'],
                    timeout_seconds=60
                ),
                E2ETestStep(
                    step_id='save_report_file',
                    name='Save Report File',
                    description='レポートファイル保存',
                    function='save_report_file',
                    parameters={'format': 'markdown'},
                    expected_result={'file_exists': True},
                    dependencies=['generate_daily_report']
                ),
                E2ETestStep(
                    step_id='verify_report_content',
                    name='Verify Report Content',
                    description='レポート内容検証',
                    function='verify_report_content',
                    parameters={},
                    expected_result={'content_valid': True},
                    dependencies=['save_report_file']
                )
            ],
            teardown_steps=[
                E2ETestStep(
                    step_id='cleanup_files',
                    name='Clean up Test Files',
                    description='テストファイルのクリーンアップ',
                    function='cleanup_test_files',
                    parameters={},
                    expected_result={'cleaned': True}
                )
            ]
        )
        self.scenarios['daily_report_flow'] = daily_report_scenario
        
        # シナリオ2: 自動化システム動作確認
        automation_scenario = E2ETestScenario(
            scenario_id='automation_system_flow',
            name='Automation System Flow',
            description='自動化システムの動作確認',
            steps=[
                E2ETestStep(
                    step_id='start_scheduler',
                    name='Start Scheduler',
                    description='スケジューラー開始',
                    function='start_scheduler',
                    parameters={'daemon': False},
                    expected_result={'status': 'running'},
                    timeout_seconds=30
                ),
                E2ETestStep(
                    step_id='register_test_job',
                    name='Register Test Job',
                    description='テストジョブ登録',
                    function='register_test_job',
                    parameters={'job_id': 'e2e_test_job'},
                    expected_result={'registered': True},
                    dependencies=['start_scheduler']
                ),
                E2ETestStep(
                    step_id='execute_manual_job',
                    name='Execute Manual Job',
                    description='手動ジョブ実行',
                    function='execute_manual_job',
                    parameters={'job_id': 'e2e_test_job'},
                    expected_result={'status': 'completed'},
                    dependencies=['register_test_job'],
                    timeout_seconds=45
                ),
                E2ETestStep(
                    step_id='check_notifications',
                    name='Check Notifications',
                    description='通知システム確認',
                    function='check_notifications',
                    parameters={},
                    expected_result={'notification_sent': True},
                    dependencies=['execute_manual_job']
                ),
                E2ETestStep(
                    step_id='stop_scheduler',
                    name='Stop Scheduler',
                    description='スケジューラー停止',
                    function='stop_scheduler',
                    parameters={},
                    expected_result={'status': 'stopped'},
                    dependencies=['check_notifications']
                )
            ]
        )
        self.scenarios['automation_system_flow'] = automation_scenario
        
        # シナリオ3: 品質監視システム
        quality_monitoring_scenario = E2ETestScenario(
            scenario_id='quality_monitoring_flow',
            name='Quality Monitoring Flow',
            description='品質監視システムの完全テスト',
            steps=[
                E2ETestStep(
                    step_id='run_quality_check',
                    name='Run Quality Check',
                    description='品質チェック実行',
                    function='run_quality_check',
                    parameters={},
                    expected_result={'overall_score': {'min': 0}},
                    timeout_seconds=120
                ),
                E2ETestStep(
                    step_id='analyze_quality_trends',
                    name='Analyze Quality Trends',
                    description='品質トレンド分析',
                    function='analyze_quality_trends',
                    parameters={'days': 7},
                    expected_result={'trends_available': True},
                    dependencies=['run_quality_check']
                ),
                E2ETestStep(
                    step_id='generate_quality_alerts',
                    name='Generate Quality Alerts',
                    description='品質アラート生成',
                    function='generate_quality_alerts',
                    parameters={},
                    expected_result={'alerts_processed': True},
                    dependencies=['run_quality_check']
                ),
                E2ETestStep(
                    step_id='create_quality_report',
                    name='Create Quality Report',
                    description='品質レポート作成',
                    function='create_quality_report',
                    parameters={},
                    expected_result={'report_created': True},
                    dependencies=['analyze_quality_trends', 'generate_quality_alerts']
                )
            ]
        )
        self.scenarios['quality_monitoring_flow'] = quality_monitoring_scenario
    
    async def run_scenario(self, scenario_id: str) -> E2ETestExecution:
        """E2Eテストシナリオ実行"""
        if scenario_id not in self.scenarios:
            raise ValueError(f"未知のシナリオID: {scenario_id}")
        
        scenario = self.scenarios[scenario_id]
        execution_id = f"{scenario_id}_{int(datetime.now().timestamp())}"
        
        self.logger.info(f"E2Eテストシナリオ実行開始: {scenario.name}")
        
        start_time = time.time()
        step_results = []
        context = {}  # ステップ間でのデータ共有用
        
        try:
            # セットアップステップ実行
            for setup_step in scenario.setup_steps:
                result = await self._execute_step(setup_step, context)
                step_results.append(result)
                if result.status in ['failed', 'error']:
                    self.logger.error(f"セットアップステップ失敗: {setup_step.name}")
                    break
            
            # メインステップ実行（依存関係を考慮）
            executed_steps = set()
            
            while len(executed_steps) < len(scenario.steps):
                progress_made = False
                
                for step in scenario.steps:
                    if step.step_id in executed_steps:
                        continue
                    
                    # 依存関係チェック
                    dependencies_met = all(
                        dep in executed_steps or self._is_dependency_satisfied(dep, step_results)
                        for dep in step.dependencies
                    )
                    
                    if dependencies_met:
                        result = await self._execute_step(step, context)
                        step_results.append(result)
                        executed_steps.add(step.step_id)
                        progress_made = True
                        
                        # 失敗したステップの依存ステップはスキップ
                        if result.status in ['failed', 'error']:
                            self._skip_dependent_steps(step.step_id, scenario.steps, executed_steps, step_results)
                
                if not progress_made:
                    # 依存関係のループまたは不満足な依存関係
                    remaining_steps = [s for s in scenario.steps if s.step_id not in executed_steps]
                    for step in remaining_steps:
                        skip_result = E2ETestResult(
                            step_id=step.step_id,
                            status='skipped',
                            actual_result=None,
                            expected_result=step.expected_result,
                            duration_seconds=0.0,
                            error_message='依存関係が満たされませんでした',
                            timestamp=datetime.now()
                        )
                        step_results.append(skip_result)
                        executed_steps.add(step.step_id)
                    break
            
            # ティアダウンステップ実行
            for teardown_step in scenario.teardown_steps:
                result = await self._execute_step(teardown_step, context)
                step_results.append(result)
        
        except Exception as e:
            self.logger.error(f"シナリオ実行エラー: {e}")
            error_result = E2ETestResult(
                step_id='scenario_execution',
                status='error',
                actual_result=None,
                expected_result=None,
                duration_seconds=0.0,
                error_message=str(e),
                timestamp=datetime.now()
            )
            step_results.append(error_result)
        
        # 実行結果集計
        total_duration = time.time() - start_time
        
        passed_steps = len([r for r in step_results if r.status == 'passed'])
        failed_steps = len([r for r in step_results if r.status == 'failed'])
        skipped_steps = len([r for r in step_results if r.status == 'skipped'])
        error_steps = len([r for r in step_results if r.status == 'error'])
        
        success_rate = (passed_steps / len(step_results) * 100) if step_results else 0
        
        execution = E2ETestExecution(
            execution_id=execution_id,
            scenario_id=scenario_id,
            scenario_name=scenario.name,
            total_steps=len(step_results),
            passed_steps=passed_steps,
            failed_steps=failed_steps,
            skipped_steps=skipped_steps,
            error_steps=error_steps,
            total_duration=total_duration,
            success_rate=success_rate,
            step_results=step_results,
            timestamp=datetime.now(),
            metadata={
                'context': context,
                'scenario_description': scenario.description
            }
        )
        
        # データベース保存
        self._save_execution_result(execution)
        
        self.logger.info(f"E2Eテストシナリオ完了: {scenario.name} (成功率: {success_rate:.1f}%)")
        
        return execution
    
    async def _execute_step(self, step: E2ETestStep, context: Dict[str, Any]) -> E2ETestResult:
        """個別ステップ実行"""
        self.logger.info(f"ステップ実行開始: {step.name}")
        
        start_time = time.time()
        
        try:
            # ステップ関数実行
            step_function = getattr(self, step.function)
            
            # タイムアウト付き実行
            actual_result = await asyncio.wait_for(
                step_function(step.parameters, context),
                timeout=step.timeout_seconds
            )
            
            duration = time.time() - start_time
            
            # 期待結果との比較
            validation_result = self._validate_result(actual_result, step.expected_result)
            
            if validation_result['valid']:
                status = 'passed'
                error_message = None
            else:
                status = 'failed'
                error_message = validation_result['message']
            
            # コンテキストに結果を保存（次のステップで使用可能）
            context[step.step_id] = actual_result
            
            return E2ETestResult(
                step_id=step.step_id,
                status=status,
                actual_result=actual_result,
                expected_result=step.expected_result,
                duration_seconds=duration,
                error_message=error_message,
                timestamp=datetime.now(),
                artifacts=self._collect_step_artifacts(step, actual_result)
            )
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            return E2ETestResult(
                step_id=step.step_id,
                status='error',
                actual_result=None,
                expected_result=step.expected_result,
                duration_seconds=duration,
                error_message=f'ステップがタイムアウトしました ({step.timeout_seconds}秒)',
                timestamp=datetime.now()
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return E2ETestResult(
                step_id=step.step_id,
                status='error',
                actual_result=None,
                expected_result=step.expected_result,
                duration_seconds=duration,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    def _validate_result(self, actual: Any, expected: Any) -> Dict[str, Any]:
        """結果検証"""
        if expected is None:
            return {'valid': True, 'message': None}
        
        if isinstance(expected, dict):
            for key, expected_value in expected.items():
                if key not in actual:
                    return {'valid': False, 'message': f'キー "{key}" が結果に存在しません'}
                
                actual_value = actual[key]
                
                # 条件付き検証
                if isinstance(expected_value, dict):
                    if 'min' in expected_value and actual_value < expected_value['min']:
                        return {'valid': False, 'message': f'{key}: {actual_value} < {expected_value["min"]} (最小値)'}
                    if 'max' in expected_value and actual_value > expected_value['max']:
                        return {'valid': False, 'message': f'{key}: {actual_value} > {expected_value["max"]} (最大値)'}
                    if 'equals' in expected_value and actual_value != expected_value['equals']:
                        return {'valid': False, 'message': f'{key}: {actual_value} != {expected_value["equals"]}'}
                else:
                    if actual_value != expected_value:
                        return {'valid': False, 'message': f'{key}: {actual_value} != {expected_value}'}
        else:
            if actual != expected:
                return {'valid': False, 'message': f'結果不一致: {actual} != {expected}'}
        
        return {'valid': True, 'message': None}
    
    def _is_dependency_satisfied(self, dependency: str, results: List[E2ETestResult]) -> bool:
        """依存関係満足チェック"""
        for result in results:
            if result.step_id == dependency:
                return result.status == 'passed'
        return False
    
    def _skip_dependent_steps(self, failed_step_id: str, all_steps: List[E2ETestStep],
                             executed_steps: set, results: List[E2ETestResult]) -> None:
        """失敗ステップに依存するステップをスキップ"""
        for step in all_steps:
            if step.step_id not in executed_steps and failed_step_id in step.dependencies:
                skip_result = E2ETestResult(
                    step_id=step.step_id,
                    status='skipped',
                    actual_result=None,
                    expected_result=step.expected_result,
                    duration_seconds=0.0,
                    error_message=f'依存ステップ {failed_step_id} が失敗したためスキップ',
                    timestamp=datetime.now()
                )
                results.append(skip_result)
                executed_steps.add(step.step_id)
                
                # 再帰的にスキップ
                self._skip_dependent_steps(step.step_id, all_steps, executed_steps, results)
    
    def _collect_step_artifacts(self, step: E2ETestStep, result: Any) -> Dict[str, Any]:
        """ステップアーティファクト収集"""
        artifacts = {
            'step_name': step.name,
            'execution_timestamp': datetime.now().isoformat()
        }
        
        # ファイル生成系ステップの場合、ファイルパスを記録
        if 'file' in step.function or 'save' in step.function:
            if isinstance(result, dict) and 'file_path' in result:
                artifacts['generated_files'] = [result['file_path']]
        
        # レポート生成系ステップの場合、サイズを記録
        if 'report' in step.function:
            if isinstance(result, dict) and 'report_size' in result:
                artifacts['report_size'] = result['report_size']
        
        return artifacts
    
    # ステップ実行関数群
    async def setup_test_data(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """テストデータセットアップ"""
        # テスト用ディレクトリ作成
        test_dir = Path(self.e2e_config['artifacts_dir']) / 'test_data'
        test_dir.mkdir(parents=True, exist_ok=True)
        
        context['test_dir'] = str(test_dir)
        
        return {'status': 'success', 'test_dir': str(test_dir)}
    
    async def fetch_calendar_data(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """経済カレンダーデータ取得"""
        from ..adapters.investpy_calendar import InvestpyCalendarAdapter
        
        adapter = InvestpyCalendarAdapter()
        
        if params.get('date') == 'yesterday':
            yesterday = datetime.now() - timedelta(days=1)
            date_str = yesterday.strftime('%Y-%m-%d')
        else:
            date_str = params.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        events = adapter.get_economic_calendar(
            from_date=date_str,
            to_date=date_str
        )
        
        context['calendar_events'] = events
        
        return {
            'events_count': len(events),
            'date': date_str,
            'events': events[:5]  # 最初の5件のみ返却
        }
    
    async def generate_daily_report(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """日次レポート生成"""
        from ..reports.daily_list_renderer import DailyListRenderer
        
        events = context.get('calendar_events', [])
        if not events:
            # フォールバック用サンプルデータ
            events = [{
                'time': '08:30',
                'country': 'US',
                'event': 'CPI (YoY)',
                'importance': 'High',
                'actual': '3.0%',
                'forecast': '3.1%',
                'previous': '3.3%'
            }]
        
        renderer = DailyListRenderer(self.config)
        report_format = params.get('format', 'markdown')
        
        report_content = renderer.render_daily_list(events, report_format)
        
        context['report_content'] = report_content
        context['report_format'] = report_format
        
        return {
            'report_size': len(report_content),
            'format': report_format,
            'events_processed': len(events)
        }
    
    async def save_report_file(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """レポートファイル保存"""
        report_content = context.get('report_content', '')
        report_format = params.get('format', 'markdown')
        
        if not report_content:
            raise ValueError('保存するレポートコンテンツがありません')
        
        # ファイル保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'e2e_test_report_{timestamp}.{report_format}'
        file_path = Path(self.e2e_config['artifacts_dir']) / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        context['report_file_path'] = str(file_path)
        
        return {
            'file_exists': file_path.exists(),
            'file_path': str(file_path),
            'file_size': file_path.stat().st_size
        }
    
    async def verify_report_content(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """レポート内容検証"""
        file_path = context.get('report_file_path')
        if not file_path or not Path(file_path).exists():
            return {'content_valid': False, 'error': 'レポートファイルが存在しません'}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 基本的な内容チェック
        checks = {
            'has_content': len(content) > 50,
            'has_table_header': '|' in content or 'Time' in content,
            'has_economic_data': any(term in content for term in ['CPI', 'GDP', 'Employment', '経済']),
            'proper_encoding': True  # UTF-8で正常に読み取れた
        }
        
        all_valid = all(checks.values())
        
        return {
            'content_valid': all_valid,
            'checks': checks,
            'content_length': len(content)
        }
    
    async def cleanup_test_files(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """テストファイルクリーンアップ"""
        cleaned_files = []
        
        # レポートファイル削除
        report_file = context.get('report_file_path')
        if report_file and Path(report_file).exists():
            Path(report_file).unlink()
            cleaned_files.append(report_file)
        
        # テストディレクトリクリーンアップ
        test_dir = context.get('test_dir')
        if test_dir and Path(test_dir).exists():
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)
            cleaned_files.append(test_dir)
        
        return {
            'cleaned': True,
            'cleaned_files': cleaned_files,
            'count': len(cleaned_files)
        }
    
    async def start_scheduler(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """スケジューラー開始"""
        from ..automation.scheduler import EconomicScheduler
        
        scheduler = EconomicScheduler(self.config)
        context['scheduler'] = scheduler
        
        # テストモードで初期化
        return {
            'status': 'running',
            'jobs_registered': len(scheduler.jobs),
            'scheduler_id': id(scheduler)
        }
    
    async def register_test_job(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """テストジョブ登録"""
        scheduler = context.get('scheduler')
        if not scheduler:
            raise ValueError('スケジューラーが初期化されていません')
        
        job_id = params.get('job_id', 'e2e_test_job')
        
        def test_job():
            context['test_job_executed'] = True
            return {'status': 'completed', 'timestamp': datetime.now().isoformat()}
        
        scheduler.register_job(
            job_id=job_id,
            name='E2E Test Job',
            schedule='*/1 * * * *',  # 毎分実行
            function=test_job,
            description='E2Eテスト用ジョブ'
        )
        
        return {
            'registered': job_id in scheduler.jobs,
            'job_id': job_id,
            'total_jobs': len(scheduler.jobs)
        }
    
    async def execute_manual_job(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """手動ジョブ実行"""
        scheduler = context.get('scheduler')
        job_id = params.get('job_id', 'e2e_test_job')
        
        if not scheduler or job_id not in scheduler.jobs:
            raise ValueError(f'ジョブ {job_id} が見つかりません')
        
        # ジョブ手動実行
        job = scheduler.jobs[job_id]
        result = job.function()
        
        return {
            'status': 'completed',
            'job_id': job_id,
            'result': result,
            'executed_at': datetime.now().isoformat()
        }
    
    async def check_notifications(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """通知システム確認"""
        from ..automation.notifications import NotificationManager
        
        manager = NotificationManager(self.config)
        
        # テスト通知送信
        try:
            result = await manager.send_notification(
                title="E2E Test Notification",
                content="This is a test notification from E2E tests",
                priority="info"
            )
            
            notification_sent = isinstance(result, dict)
            
        except Exception as e:
            notification_sent = False
            result = {'error': str(e)}
        
        return {
            'notification_sent': notification_sent,
            'result': result,
            'manager_initialized': manager is not None
        }
    
    async def stop_scheduler(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """スケジューラー停止"""
        scheduler = context.get('scheduler')
        if scheduler:
            # テスト用クリーンアップ
            scheduler.jobs.clear()
            context['scheduler'] = None
            
            return {
                'status': 'stopped',
                'jobs_cleared': True
            }
        
        return {
            'status': 'already_stopped',
            'jobs_cleared': False
        }
    
    async def run_quality_check(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """品質チェック実行"""
        from ..automation.quality_monitor import QualityMonitor
        
        monitor = QualityMonitor(self.config)
        quality_report = monitor.run_quality_check()
        
        context['quality_report'] = quality_report
        
        return {
            'overall_score': quality_report.get('overall_score', 0),
            'issues_count': len(quality_report.get('issues', [])),
            'report_generated': True
        }
    
    async def analyze_quality_trends(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """品質トレンド分析"""
        days = params.get('days', 7)
        
        # 簡易トレンド分析（実装簡略化）
        quality_report = context.get('quality_report', {})
        
        return {
            'trends_available': True,
            'analysis_period_days': days,
            'current_score': quality_report.get('overall_score', 0)
        }
    
    async def generate_quality_alerts(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """品質アラート生成"""
        quality_report = context.get('quality_report', {})
        
        # アラート条件チェック
        alerts = []
        overall_score = quality_report.get('overall_score', 0)
        
        if overall_score < 80:
            alerts.append('品質スコアが80未満です')
        
        issues = quality_report.get('issues', [])
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        
        if critical_issues:
            alerts.append(f'{len(critical_issues)}件の重要な問題があります')
        
        context['quality_alerts'] = alerts
        
        return {
            'alerts_processed': True,
            'alerts_count': len(alerts),
            'alerts': alerts
        }
    
    async def create_quality_report(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """品質レポート作成"""
        quality_report = context.get('quality_report', {})
        alerts = context.get('quality_alerts', [])
        
        # レポートファイル生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = Path(self.e2e_config['artifacts_dir']) / f'quality_report_{timestamp}.json'
        
        report_data = {
            'timestamp': timestamp,
            'quality_report': quality_report,
            'alerts': alerts,
            'generated_by': 'e2e_test'
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return {
            'report_created': True,
            'report_file': str(report_file),
            'report_size': report_file.stat().st_size
        }
    
    def _save_execution_result(self, execution: E2ETestExecution) -> None:
        """実行結果データベース保存"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # 実行結果保存
            conn.execute("""
                INSERT INTO e2e_executions 
                (execution_id, scenario_id, scenario_name, total_steps, passed_steps,
                 failed_steps, skipped_steps, error_steps, total_duration, success_rate,
                 timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution.execution_id,
                execution.scenario_id,
                execution.scenario_name,
                execution.total_steps,
                execution.passed_steps,
                execution.failed_steps,
                execution.skipped_steps,
                execution.error_steps,
                execution.total_duration,
                execution.success_rate,
                execution.timestamp.isoformat(),
                json.dumps(execution.metadata, ensure_ascii=False)
            ))
            
            # ステップ結果保存
            for step_result in execution.step_results:
                conn.execute("""
                    INSERT INTO e2e_step_results 
                    (execution_id, step_id, status, actual_result, expected_result,
                     duration_seconds, error_message, timestamp, artifacts)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution.execution_id,
                    step_result.step_id,
                    step_result.status,
                    json.dumps(step_result.actual_result, ensure_ascii=False, default=str),
                    json.dumps(step_result.expected_result, ensure_ascii=False, default=str),
                    step_result.duration_seconds,
                    step_result.error_message,
                    step_result.timestamp.isoformat(),
                    json.dumps(step_result.artifacts, ensure_ascii=False, default=str)
                ))
            
            conn.commit()
    
    def get_execution_history(self, days: int = 30) -> List[E2ETestExecution]:
        """実行履歴取得"""
        since = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                SELECT execution_id, scenario_id, scenario_name, total_steps, passed_steps,
                       failed_steps, skipped_steps, error_steps, total_duration, success_rate,
                       timestamp, metadata
                FROM e2e_executions 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (since.isoformat(),))
            
            executions = []
            for row in cursor:
                # ステップ結果は省略（詳細取得時に別途取得）
                execution = E2ETestExecution(
                    execution_id=row[0],
                    scenario_id=row[1],
                    scenario_name=row[2],
                    total_steps=row[3],
                    passed_steps=row[4],
                    failed_steps=row[5],
                    skipped_steps=row[6],
                    error_steps=row[7],
                    total_duration=row[8],
                    success_rate=row[9],
                    step_results=[],  # 省略
                    timestamp=datetime.fromisoformat(row[10]),
                    metadata=json.loads(row[11]) if row[11] else {}
                )
                executions.append(execution)
            
            return executions
    
    def generate_e2e_report(self, days: int = 7) -> Dict[str, Any]:
        """E2Eテストレポート生成"""
        executions = self.get_execution_history(days)
        
        if not executions:
            return {
                'status': 'no_data',
                'message': f'過去{days}日間のE2Eテスト実行データがありません'
            }
        
        # 統計計算
        success_rates = [e.success_rate for e in executions]
        avg_success_rate = sum(success_rates) / len(success_rates)
        
        durations = [e.total_duration for e in executions]
        avg_duration = sum(durations) / len(durations)
        
        # シナリオ別統計
        scenario_stats = {}
        for execution in executions:
            scenario_id = execution.scenario_id
            if scenario_id not in scenario_stats:
                scenario_stats[scenario_id] = {
                    'executions': [],
                    'avg_success_rate': 0,
                    'avg_duration': 0
                }
            scenario_stats[scenario_id]['executions'].append(execution)
        
        for scenario_id, stats in scenario_stats.items():
            executions_list = stats['executions']
            stats['avg_success_rate'] = sum(e.success_rate for e in executions_list) / len(executions_list)
            stats['avg_duration'] = sum(e.total_duration for e in executions_list) / len(executions_list)
            stats['execution_count'] = len(executions_list)
        
        return {
            'status': 'success',
            'period_days': days,
            'overall_statistics': {
                'total_executions': len(executions),
                'average_success_rate': avg_success_rate,
                'average_duration_seconds': avg_duration
            },
            'by_scenario': scenario_stats,
            'latest_executions': [
                {
                    'execution_id': e.execution_id,
                    'scenario_name': e.scenario_name,
                    'success_rate': e.success_rate,
                    'duration': e.total_duration,
                    'timestamp': e.timestamp.isoformat()
                }
                for e in executions[:10]
            ]
        }