"""
Economic indicators automatic scheduler.

経済指標の自動実行スケジューラー。
日次レポート、ディープ分析、カレンダー生成などを自動実行する。
"""

import logging
import os
import sys
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
import asyncio
import threading
import time
import json
from pathlib import Path

# Add src to path if running from project root
if 'src' not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.econ.config.settings import get_econ_config
from src.econ.automation.notifications import NotificationManager
from src.econ.automation.quality_monitor import QualityMonitor

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    """スケジュール対象ジョブ"""
    job_id: str
    name: str
    function: Callable
    schedule: str  # cron format or interval
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    max_retries: int = 3
    retry_delay: int = 300  # seconds
    timeout: int = 1800  # seconds (30 minutes)
    description: str = ""


@dataclass 
class JobExecution:
    """ジョブ実行結果"""
    job_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "running"  # running, success, failed, timeout
    result: Optional[Any] = None
    error: Optional[str] = None
    duration: Optional[float] = None
    retry_count: int = 0


class EconomicScheduler:
    """経済指標自動実行スケジューラー"""
    
    def __init__(self, config = None):
        """
        初期化
        
        Args:
            config: 経済指標設定
        """
        self.config = config or get_econ_config()
        self.notification_manager = NotificationManager(self.config)
        self.quality_monitor = QualityMonitor(self.config)
        
        self.jobs: Dict[str, ScheduledJob] = {}
        self.executions: List[JobExecution] = []
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        
        # ジョブ実行状態の管理
        self.active_executions: Dict[str, JobExecution] = {}
        
        # デフォルトジョブを登録
        self._register_default_jobs()
    
    def _register_default_jobs(self):
        """デフォルトジョブを登録"""
        try:
            # 日次レポート生成（毎日06:00 UTC）
            self.register_job(
                job_id="daily_report",
                name="Daily Economic Report",
                function=self._daily_report_job,
                schedule="0 6 * * *",  # 06:00 UTC
                description="Generate daily economic indicators report"
            )
            
            # ディープ分析（重要指標発表時）
            self.register_job(
                job_id="deep_analysis",
                name="Deep Economic Analysis", 
                function=self._deep_analysis_job,
                schedule="0 8,14,20 * * *",  # 08:00, 14:00, 20:00 UTC
                description="Run deep analysis for important indicators"
            )
            
            # カレンダー更新（毎日05:00 UTC）
            self.register_job(
                job_id="calendar_update",
                name="Economic Calendar Update",
                function=self._calendar_update_job,
                schedule="0 5 * * *",  # 05:00 UTC
                description="Update economic calendar ICS file"
            )
            
            # データ品質監視（毎時）
            self.register_job(
                job_id="quality_check",
                name="Data Quality Monitoring",
                function=self._quality_check_job,
                schedule="0 * * * *",  # Every hour
                description="Monitor data quality and system health"
            )
            
            logger.info(f"Registered {len(self.jobs)} default jobs")
            
        except Exception as e:
            logger.error(f"Failed to register default jobs: {e}")
    
    def register_job(
        self,
        job_id: str,
        name: str,
        function: Callable,
        schedule: str,
        enabled: bool = True,
        max_retries: int = 3,
        retry_delay: int = 300,
        timeout: int = 1800,
        description: str = ""
    ):
        """ジョブを登録"""
        job = ScheduledJob(
            job_id=job_id,
            name=name,
            function=function,
            schedule=schedule,
            enabled=enabled,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            description=description
        )
        
        # 次回実行時間を計算
        job.next_run = self._calculate_next_run(schedule)
        
        self.jobs[job_id] = job
        logger.info(f"Registered job: {job_id} - {name}")
    
    def _calculate_next_run(self, schedule: str) -> Optional[datetime]:
        """次回実行時間を計算（簡易版）"""
        try:
            # シンプルなcron形式の解析（分 時 日 月 曜日）
            parts = schedule.split()
            if len(parts) != 5:
                return None
            
            now = datetime.utcnow()
            minute, hour = int(parts[0]), int(parts[1])
            
            # 今日の実行時間を計算
            today_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # 今日の実行時間が過ぎていれば明日
            if today_run <= now:
                return today_run + timedelta(days=1)
            else:
                return today_run
                
        except Exception as e:
            logger.error(f"Failed to calculate next run for schedule {schedule}: {e}")
            return None
    
    def start(self):
        """スケジューラーを開始"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting economic scheduler")
        self.running = True
        
        # ワーカースレッドを開始
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        logger.info("Economic scheduler started")
    
    def stop(self):
        """スケジューラーを停止"""
        if not self.running:
            return
        
        logger.info("Stopping economic scheduler")
        self.running = False
        
        # ワーカースレッドの終了を待機
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=10)
        
        logger.info("Economic scheduler stopped")
    
    def _worker_loop(self):
        """メインワーカーループ"""
        logger.info("Scheduler worker loop started")
        
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                # 実行すべきジョブをチェック
                for job_id, job in self.jobs.items():
                    if not job.enabled or job_id in self.active_executions:
                        continue
                    
                    if job.next_run and current_time >= job.next_run:
                        # ジョブを実行
                        self._execute_job_async(job)
                
                # 完了した実行をクリーンアップ
                self._cleanup_completed_executions()
                
                # 1分待機
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in scheduler worker loop: {e}")
                time.sleep(60)
        
        logger.info("Scheduler worker loop stopped")
    
    def _execute_job_async(self, job: ScheduledJob):
        """ジョブを非同期実行"""
        execution = JobExecution(
            job_id=job.job_id,
            start_time=datetime.utcnow()
        )
        
        self.active_executions[job.job_id] = execution
        self.executions.append(execution)
        
        # 別スレッドで実行
        thread = threading.Thread(
            target=self._execute_job_with_retry,
            args=(job, execution),
            daemon=True
        )
        thread.start()
        
        logger.info(f"Started job execution: {job.job_id}")
    
    def _execute_job_with_retry(self, job: ScheduledJob, execution: JobExecution):
        """リトライ付きでジョブを実行"""
        try:
            for attempt in range(job.max_retries + 1):
                try:
                    execution.retry_count = attempt
                    
                    # タイムアウト付きで実行
                    result = self._execute_with_timeout(job.function, job.timeout)
                    
                    # 成功
                    execution.status = "success"
                    execution.result = result
                    execution.end_time = datetime.utcnow()
                    execution.duration = (execution.end_time - execution.start_time).total_seconds()
                    
                    # 次回実行時間を更新
                    job.last_run = execution.start_time
                    job.next_run = self._calculate_next_run(job.schedule)
                    
                    logger.info(f"Job {job.job_id} completed successfully in {execution.duration:.1f}s")
                    
                    # 成功通知
                    try:
                        import asyncio
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self.notification_manager.send_job_notification(
                                job_id=job.job_id,
                                status="success",
                                message=f"Job completed in {execution.duration:.1f}s",
                                execution=execution
                            ))
                        else:
                            loop.run_until_complete(self.notification_manager.send_job_notification(
                                job_id=job.job_id,
                                status="success",
                                message=f"Job completed in {execution.duration:.1f}s",
                                execution=execution
                            ))
                    except Exception as e:
                        logger.warning(f"Failed to send success notification: {e}")
                    
                    break
                    
                except TimeoutError:
                    execution.status = "timeout"
                    execution.error = f"Job timed out after {job.timeout} seconds"
                    logger.error(f"Job {job.job_id} timed out (attempt {attempt + 1})")
                    
                except Exception as e:
                    execution.error = str(e)
                    logger.error(f"Job {job.job_id} failed (attempt {attempt + 1}): {e}")
                    
                    # 最後の試行でなければリトライ
                    if attempt < job.max_retries:
                        logger.info(f"Retrying job {job.job_id} in {job.retry_delay} seconds")
                        time.sleep(job.retry_delay)
                    else:
                        execution.status = "failed"
                        
                        # 失敗通知
                        try:
                            import asyncio
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(self.notification_manager.send_job_notification(
                                    job_id=job.job_id,
                                    status="failed",
                                    message=f"Job failed after {job.max_retries + 1} attempts: {execution.error}",
                                    execution=execution
                                ))
                            else:
                                loop.run_until_complete(self.notification_manager.send_job_notification(
                                    job_id=job.job_id,
                                    status="failed",
                                    message=f"Job failed after {job.max_retries + 1} attempts: {execution.error}",
                                    execution=execution
                                ))
                        except Exception as e:
                            logger.warning(f"Failed to send failure notification: {e}")
        
        finally:
            if execution.end_time is None:
                execution.end_time = datetime.utcnow()
                execution.duration = (execution.end_time - execution.start_time).total_seconds()
            
            # アクティブ実行リストから削除
            self.active_executions.pop(job.job_id, None)
    
    def _execute_with_timeout(self, function: Callable, timeout: int) -> Any:
        """タイムアウト付きで関数を実行"""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Function timed out after {timeout} seconds")
        
        # タイムアウトハンドラーを設定
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            result = function()
            return result
        finally:
            signal.alarm(0)  # タイマーをクリア
    
    def _cleanup_completed_executions(self):
        """完了した実行履歴をクリーンアップ"""
        # 過去24時間以降の履歴は削除
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.executions = [
            ex for ex in self.executions
            if ex.end_time is None or ex.end_time > cutoff
        ]
    
    # =============================================================================
    # デフォルトジョブの実装
    # =============================================================================
    
    def _daily_report_job(self) -> Dict[str, Any]:
        """日次レポート生成ジョブ"""
        logger.info("Running daily report job")
        
        try:
            # 昨日の日付を取得
            yesterday = date.today() - timedelta(days=1)
            
            # CLI経由で日次レポートを生成
            from src.econ.__main__ import EconomicCLI
            cli = EconomicCLI()
            
            # 引数を構築
            class Args:
                def __init__(self):
                    self.date = yesterday.strftime('%Y-%m-%d')
                    self.countries = ['US', 'EU', 'UK', 'JP', 'CA', 'AU']
                    self.importance = ['High', 'Medium']
                    self.format = 'html'
                    self.output_dir = 'build/reports/daily'
            
            args = Args()
            success = cli.daily_list_command(args)
            
            if success:
                return {
                    'status': 'success',
                    'date': yesterday.isoformat(),
                    'output': f'build/reports/daily/{yesterday.strftime("%Y%m%d")}.html'
                }
            else:
                raise Exception("Daily report generation failed")
                
        except Exception as e:
            logger.error(f"Daily report job failed: {e}")
            raise
    
    def _deep_analysis_job(self) -> Dict[str, Any]:
        """ディープ分析ジョブ"""
        logger.info("Running deep analysis job")
        
        try:
            # 昨日のディープ分析を実行
            from src.econ.__main__ import EconomicCLI
            cli = EconomicCLI()
            
            class Args:
                def __init__(self):
                    self.date = None  # 昨日
                    self.countries = ['US', 'EU']
                    self.importance = ['High']
                    self.format = 'html'
                    self.output_dir = 'build/reports/deep'
            
            args = Args()
            success = cli.deep_analysis_command(args)
            
            if success:
                return {
                    'status': 'success',
                    'analysis_type': 'deep',
                    'output_dir': 'build/reports/deep'
                }
            else:
                raise Exception("Deep analysis failed")
                
        except Exception as e:
            logger.error(f"Deep analysis job failed: {e}")
            raise
    
    def _calendar_update_job(self) -> Dict[str, Any]:
        """カレンダー更新ジョブ"""
        logger.info("Running calendar update job")
        
        try:
            # ICSカレンダーを生成
            from src.econ.__main__ import EconomicCLI
            cli = EconomicCLI()
            
            class Args:
                def __init__(self):
                    self.days = 7
                    self.countries = ['US', 'EU', 'UK', 'JP', 'CA', 'AU']
                    self.output = 'build/calendars/economic.ics'
            
            args = Args()
            success = cli.build_ics_command(args)
            
            if success:
                return {
                    'status': 'success',
                    'calendar_file': 'build/calendars/economic.ics',
                    'days': 7
                }
            else:
                raise Exception("Calendar update failed")
                
        except Exception as e:
            logger.error(f"Calendar update job failed: {e}")
            raise
    
    def _quality_check_job(self) -> Dict[str, Any]:
        """データ品質監視ジョブ"""
        logger.info("Running quality check job")
        
        try:
            # 品質監視を実行
            quality_report = self.quality_monitor.run_quality_check()
            
            # 問題があれば通知
            if quality_report.get('issues', []):
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.notification_manager.send_quality_alert(quality_report))
                    else:
                        loop.run_until_complete(self.notification_manager.send_quality_alert(quality_report))
                except Exception as e:
                    logger.warning(f"Failed to send quality alert: {e}")
            
            return quality_report
            
        except Exception as e:
            logger.error(f"Quality check job failed: {e}")
            raise
    
    # =============================================================================
    # 管理・状態確認機能
    # =============================================================================
    
    def get_job_status(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """ジョブ状態を取得"""
        if job_id:
            job = self.jobs.get(job_id)
            if not job:
                return {'error': f'Job {job_id} not found'}
            
            return {
                'job_id': job.job_id,
                'name': job.name,
                'enabled': job.enabled,
                'last_run': job.last_run.isoformat() if job.last_run else None,
                'next_run': job.next_run.isoformat() if job.next_run else None,
                'schedule': job.schedule,
                'description': job.description,
                'active': job_id in self.active_executions
            }
        else:
            # 全ジョブの状態を返す
            return {
                'scheduler_running': self.running,
                'active_jobs': len(self.active_executions),
                'total_jobs': len(self.jobs),
                'jobs': [
                    self.get_job_status(jid)['job_id'] if isinstance(self.get_job_status(jid), dict) and 'job_id' in self.get_job_status(jid) else {}
                    for jid in self.jobs.keys()
                ]
            }
    
    def get_execution_history(self, job_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """実行履歴を取得"""
        executions = self.executions
        
        if job_id:
            executions = [ex for ex in executions if ex.job_id == job_id]
        
        # 最新順でソート
        executions.sort(key=lambda x: x.start_time, reverse=True)
        
        return [
            {
                'job_id': ex.job_id,
                'start_time': ex.start_time.isoformat(),
                'end_time': ex.end_time.isoformat() if ex.end_time else None,
                'status': ex.status,
                'duration': ex.duration,
                'retry_count': ex.retry_count,
                'error': ex.error
            }
            for ex in executions[:limit]
        ]
    
    def trigger_job(self, job_id: str) -> bool:
        """ジョブを手動実行"""
        job = self.jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        if job_id in self.active_executions:
            logger.warning(f"Job {job_id} is already running")
            return False
        
        logger.info(f"Manually triggering job: {job_id}")
        self._execute_job_async(job)
        return True
    
    def enable_job(self, job_id: str, enabled: bool = True):
        """ジョブを有効/無効化"""
        job = self.jobs.get(job_id)
        if job:
            job.enabled = enabled
            logger.info(f"Job {job_id} {'enabled' if enabled else 'disabled'}")
        else:
            logger.error(f"Job {job_id} not found")


# サンプル使用例とテスト用関数
async def main():
    """サンプル実行"""
    # 設定を読み込み
    config = get_econ_config()
    
    # スケジューラーを作成
    scheduler = EconomicScheduler(config)
    
    try:
        # スケジューラーを開始
        scheduler.start()
        
        # 状態を確認
        status = scheduler.get_job_status()
        print(f"Scheduler status: {json.dumps(status, indent=2)}")
        
        # 10秒間実行
        await asyncio.sleep(10)
        
        # 実行履歴を確認
        history = scheduler.get_execution_history(limit=5)
        print(f"Execution history: {json.dumps(history, indent=2)}")
        
    finally:
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())