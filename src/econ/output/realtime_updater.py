"""
Real-time Update System for Economic Indicators
経済指標リアルタイム更新システム

自動データ更新、ダッシュボード同期、通知機能を提供
"""

from typing import List, Dict, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
import asyncio
import logging
from pathlib import Path
import json
import threading
import time
from dataclasses import dataclass, field
from enum import Enum

# 既存モジュール
from ..config.settings import EconConfig
from ..normalize.data_processor import ProcessedIndicator
from ..normalize.trend_analyzer import TrendResult
from .sheets_dashboard import SheetsDashboardManager
from .advanced_dashboard import AdvancedDashboard, DashboardConfig

logger = logging.getLogger(__name__)


class UpdateFrequency(Enum):
    """更新頻度"""
    REALTIME = "realtime"  # リアルタイム
    HOURLY = "hourly"      # 1時間毎
    DAILY = "daily"        # 日次
    WEEKLY = "weekly"      # 週次


class UpdateTrigger(Enum):
    """更新トリガー"""
    SCHEDULED = "scheduled"    # スケジュール
    DATA_CHANGE = "data_change"  # データ変更
    MANUAL = "manual"          # 手動
    API_WEBHOOK = "api_webhook"  # API Webhook


@dataclass
class UpdateConfig:
    """更新設定"""
    # 基本設定
    enabled: bool = True
    frequency: UpdateFrequency = UpdateFrequency.HOURLY
    max_retries: int = 3
    retry_delay: int = 30  # 秒
    
    # 更新対象
    update_sheets: bool = True
    update_dashboard: bool = True
    update_reports: bool = True
    
    # 通知設定
    notify_on_success: bool = False
    notify_on_error: bool = True
    notification_channels: List[str] = field(default_factory=lambda: ["slack"])
    
    # データ保持
    keep_history: bool = True
    history_days: int = 30
    
    # パフォーマンス
    concurrent_updates: bool = True
    max_concurrent: int = 5


@dataclass
class UpdateStatus:
    """更新ステータス"""
    last_update: Optional[datetime] = None
    next_update: Optional[datetime] = None
    status: str = "idle"  # idle, running, error, success
    error_message: Optional[str] = None
    update_count: int = 0
    success_count: int = 0
    error_count: int = 0


class RealTimeUpdater:
    """リアルタイム更新システム"""
    
    def __init__(self, config: Optional[UpdateConfig] = None, econ_config: Optional[EconConfig] = None):
        self.config = config or UpdateConfig()
        self.econ_config = econ_config or EconConfig()
        
        # 更新システム
        self.status = UpdateStatus()
        self.is_running = False
        self.update_thread = None
        self.stop_event = threading.Event()
        
        # ダッシュボード管理
        self.sheets_manager = None
        self.advanced_dashboard = None
        
        # コールバック関数
        self.data_update_callbacks: List[Callable] = []
        self.status_change_callbacks: List[Callable] = []
        
        # データキャッシュ
        self.last_indicators: List[ProcessedIndicator] = []
        self.last_trend_results: List[TrendResult] = []
        
        # 初期化
        self._initialize_components()
    
    def _initialize_components(self):
        """コンポーネントを初期化"""
        try:
            # Google Sheets管理
            if self.config.update_sheets:
                self.sheets_manager = SheetsDashboardManager(self.econ_config)
            
            # 高度なダッシュボード
            if self.config.update_dashboard:
                dashboard_config = DashboardConfig(
                    title="リアルタイム経済指標ダッシュボード",
                    save_path=Path(self.econ_config.output.output_base_dir) / "realtime_dashboard"
                )
                self.advanced_dashboard = AdvancedDashboard(dashboard_config)
            
            logger.info("リアルタイム更新システムが初期化されました")
            
        except Exception as e:
            logger.error(f"初期化エラー: {e}")
    
    def start(self):
        """更新システムを開始"""
        if self.is_running:
            logger.warning("更新システムは既に実行中です")
            return
        
        if not self.config.enabled:
            logger.info("更新システムが無効化されています")
            return
        
        try:
            self.is_running = True
            self.stop_event.clear()
            
            # 更新スレッドを開始
            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
            
            # 次の更新時刻を設定
            self._schedule_next_update()
            
            self._update_status("running", "更新システムが開始されました")
            logger.info("リアルタイム更新システムが開始されました")
            
        except Exception as e:
            self.is_running = False
            self._update_status("error", f"開始エラー: {e}")
            logger.error(f"更新システム開始エラー: {e}")
    
    def stop(self):
        """更新システムを停止"""
        if not self.is_running:
            logger.warning("更新システムは実行されていません")
            return
        
        try:
            self.is_running = False
            self.stop_event.set()
            
            # スレッドの終了を待機
            if self.update_thread and self.update_thread.is_alive():
                self.update_thread.join(timeout=10)
            
            self._update_status("idle", "更新システムが停止されました")
            logger.info("リアルタイム更新システムが停止されました")
            
        except Exception as e:
            logger.error(f"更新システム停止エラー: {e}")
    
    def _update_loop(self):
        """更新ループ"""
        while self.is_running and not self.stop_event.is_set():
            try:
                # 更新が必要かチェック
                if self._should_update():
                    self._perform_update()
                
                # 待機
                self._wait_for_next_check()
                
            except Exception as e:
                logger.error(f"更新ループエラー: {e}")
                self._update_status("error", f"更新ループエラー: {e}")
                time.sleep(60)  # エラー時は1分待機
    
    def _should_update(self) -> bool:
        """更新が必要かチェック"""
        if not self.status.next_update:
            return True
        
        return datetime.now() >= self.status.next_update
    
    def _perform_update(self):
        """更新を実行"""
        try:
            self._update_status("running", "更新を実行中...")
            
            # データ取得
            indicators, trend_results = self._fetch_latest_data()
            
            if not indicators:
                logger.warning("新しいデータが取得できませんでした")
                return
            
            # データが変更されたかチェック
            if self._has_data_changed(indicators):
                logger.info("データの変更を検出しました")
                
                # 並行更新
                if self.config.concurrent_updates:
                    self._concurrent_update(indicators, trend_results)
                else:
                    self._sequential_update(indicators, trend_results)
                
                # データをキャッシュ
                self.last_indicators = indicators
                self.last_trend_results = trend_results
                
                # コールバック実行
                self._execute_callbacks(indicators, trend_results)
                
                # 成功統計更新
                self.status.success_count += 1
                self._update_status("success", "更新が完了しました")
                
                # 成功通知
                if self.config.notify_on_success:
                    self._send_notification("success", "データ更新が完了しました")
                
            else:
                logger.info("データに変更はありませんでした")
                self._update_status("idle", "データに変更なし")
            
            # 次の更新をスケジュール
            self._schedule_next_update()
            
        except Exception as e:
            logger.error(f"更新実行エラー: {e}")
            self.status.error_count += 1
            self._update_status("error", f"更新エラー: {e}")
            
            # エラー通知
            if self.config.notify_on_error:
                self._send_notification("error", f"更新エラー: {e}")
            
            # リトライ
            self._schedule_retry()
    
    def _concurrent_update(self, indicators: List[ProcessedIndicator], trend_results: List[TrendResult]):
        """並行更新"""
        try:
            import concurrent.futures
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_concurrent) as executor:
                futures = []
                
                # Google Sheets更新
                if self.config.update_sheets and self.sheets_manager:
                    future = executor.submit(self._update_sheets, indicators, trend_results)
                    futures.append(("sheets", future))
                
                # ダッシュボード更新
                if self.config.update_dashboard and self.advanced_dashboard:
                    future = executor.submit(self._update_dashboard, indicators, trend_results)
                    futures.append(("dashboard", future))
                
                # レポート更新
                if self.config.update_reports:
                    future = executor.submit(self._update_reports, indicators, trend_results)
                    futures.append(("reports", future))
                
                # 結果を待機
                for name, future in futures:
                    try:
                        result = future.result(timeout=300)  # 5分タイムアウト
                        logger.info(f"{name}更新が完了しました")
                    except Exception as e:
                        logger.error(f"{name}更新エラー: {e}")
            
        except Exception as e:
            logger.error(f"並行更新エラー: {e}")
            raise
    
    def _sequential_update(self, indicators: List[ProcessedIndicator], trend_results: List[TrendResult]):
        """順次更新"""
        try:
            # Google Sheets更新
            if self.config.update_sheets and self.sheets_manager:
                self._update_sheets(indicators, trend_results)
            
            # ダッシュボード更新
            if self.config.update_dashboard and self.advanced_dashboard:
                self._update_dashboard(indicators, trend_results)
            
            # レポート更新
            if self.config.update_reports:
                self._update_reports(indicators, trend_results)
            
        except Exception as e:
            logger.error(f"順次更新エラー: {e}")
            raise
    
    def _update_sheets(self, indicators: List[ProcessedIndicator], trend_results: List[TrendResult]):
        """Google Sheets更新"""
        try:
            if not self.sheets_manager:
                return
            
            # 既存ダッシュボードを更新
            if self.sheets_manager.dashboard_spreadsheet_id:
                success = self.sheets_manager.update_dashboard(indicators, trend_results)
                if success:
                    logger.info("Google Sheetsダッシュボードが更新されました")
                else:
                    logger.error("Google Sheetsダッシュボード更新に失敗しました")
            else:
                # 新規ダッシュボード作成
                spreadsheet_id = self.sheets_manager.create_economic_dashboard(
                    indicators, trend_results, "リアルタイム経済指標ダッシュボード"
                )
                if spreadsheet_id:
                    logger.info(f"新しいGoogle Sheetsダッシュボードが作成されました: {spreadsheet_id}")
                else:
                    logger.error("Google Sheetsダッシュボード作成に失敗しました")
            
        except Exception as e:
            logger.error(f"Google Sheets更新エラー: {e}")
            raise
    
    def _update_dashboard(self, indicators: List[ProcessedIndicator], trend_results: List[TrendResult]):
        """高度なダッシュボード更新"""
        try:
            if not self.advanced_dashboard:
                return
            
            # ダッシュボード生成
            result = self.advanced_dashboard.create_comprehensive_dashboard(indicators, trend_results)
            
            if 'error' not in result:
                logger.info("高度なダッシュボードが更新されました")
                
                # 保存されたファイルをログ出力
                if 'saved_files' in result:
                    for file_path in result['saved_files']:
                        logger.info(f"ダッシュボードファイル保存: {file_path}")
            else:
                logger.error(f"高度なダッシュボード更新エラー: {result['error']}")
                raise Exception(result['error'])
            
        except Exception as e:
            logger.error(f"高度なダッシュボード更新エラー: {e}")
            raise
    
    def _update_reports(self, indicators: List[ProcessedIndicator], trend_results: List[TrendResult]):
        """レポート更新"""
        try:
            # 既存のレポート生成機能を使用
            from ..render.report_builder import ReportBuilder, ReportConfig, ReportFormat
            
            # レポート設定
            report_config = ReportConfig(
                format=ReportFormat.HTML,
                output_path=Path(self.econ_config.output.output_base_dir) / "realtime_reports" / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            )
            
            # レポート生成
            report_builder = ReportBuilder(report_config)
            result = report_builder.generate_comprehensive_report(indicators, trend_results)
            
            if 'error' not in result:
                logger.info("リアルタイムレポートが生成されました")
            else:
                logger.error(f"リアルタイムレポート生成エラー: {result['error']}")
                raise Exception(result['error'])
            
        except Exception as e:
            logger.error(f"レポート更新エラー: {e}")
            raise
    
    def _fetch_latest_data(self) -> Tuple[List[ProcessedIndicator], List[TrendResult]]:
        """最新データを取得"""
        try:
            # 既存のデータ取得機能を使用
            from ..adapters.investpy_calendar import InvestPyCalendar
            from ..normalize.data_processor import DataProcessor
            from ..normalize.trend_analyzer import TrendAnalyzer
            
            # カレンダー取得
            calendar = InvestPyCalendar()
            events = calendar.get_economic_calendar(
                countries=self.econ_config.targets.target_countries,
                importance=self.econ_config.targets.importance_threshold
            )
            
            # データ処理
            processor = DataProcessor()
            indicators = []
            
            for event in events:
                try:
                    processed = processor.process_indicator(event)
                    if processed:
                        indicators.append(processed)
                except Exception as e:
                    logger.warning(f"指標処理エラー: {e}")
                    continue
            
            # トレンド分析
            trend_analyzer = TrendAnalyzer()
            trend_results = []
            
            for indicator in indicators:
                try:
                    if indicator.historical_data is not None:
                        trend_result = trend_analyzer.analyze_trend(indicator.historical_data)
                        trend_results.append(trend_result)
                    else:
                        trend_results.append(None)
                except Exception as e:
                    logger.warning(f"トレンド分析エラー: {e}")
                    trend_results.append(None)
            
            logger.info(f"最新データを取得しました: {len(indicators)}指標")
            return indicators, trend_results
            
        except Exception as e:
            logger.error(f"データ取得エラー: {e}")
            return [], []
    
    def _has_data_changed(self, new_indicators: List[ProcessedIndicator]) -> bool:
        """データが変更されたかチェック"""
        try:
            if not self.last_indicators:
                return True
            
            if len(new_indicators) != len(self.last_indicators):
                return True
            
            # 各指標の最新値を比較
            for i, (new_ind, old_ind) in enumerate(zip(new_indicators, self.last_indicators)):
                new_event = new_ind.original_event
                old_event = old_ind.original_event
                
                if (new_event.actual != old_event.actual or 
                    new_event.forecast != old_event.forecast or
                    new_event.previous != old_event.previous):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"データ変更チェックエラー: {e}")
            return True  # エラー時は更新を実行
    
    def _execute_callbacks(self, indicators: List[ProcessedIndicator], trend_results: List[TrendResult]):
        """コールバック関数を実行"""
        try:
            for callback in self.data_update_callbacks:
                try:
                    callback(indicators, trend_results)
                except Exception as e:
                    logger.error(f"コールバック実行エラー: {e}")
            
        except Exception as e:
            logger.error(f"コールバック実行エラー: {e}")
    
    def _schedule_next_update(self):
        """次の更新をスケジュール"""
        try:
            now = datetime.now()
            
            if self.config.frequency == UpdateFrequency.REALTIME:
                # リアルタイムの場合は5分後
                next_update = now + timedelta(minutes=5)
            elif self.config.frequency == UpdateFrequency.HOURLY:
                # 1時間後
                next_update = now + timedelta(hours=1)
            elif self.config.frequency == UpdateFrequency.DAILY:
                # 翌日の指定時刻
                next_update = now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
            elif self.config.frequency == UpdateFrequency.WEEKLY:
                # 来週の指定時刻
                next_update = now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(weeks=1)
            else:
                # デフォルトは1時間後
                next_update = now + timedelta(hours=1)
            
            self.status.next_update = next_update
            logger.info(f"次の更新予定: {next_update}")
            
        except Exception as e:
            logger.error(f"スケジュール設定エラー: {e}")
    
    def _schedule_retry(self):
        """リトライをスケジュール"""
        try:
            if self.status.update_count < self.config.max_retries:
                retry_time = datetime.now() + timedelta(seconds=self.config.retry_delay)
                self.status.next_update = retry_time
                self.status.update_count += 1
                logger.info(f"リトライ {self.status.update_count}/{self.config.max_retries} を {retry_time} にスケジュール")
            else:
                logger.error("最大リトライ回数に達しました")
                self._schedule_next_update()  # 通常のスケジュールに戻す
                self.status.update_count = 0
            
        except Exception as e:
            logger.error(f"リトライスケジュールエラー: {e}")
    
    def _wait_for_next_check(self):
        """次のチェックまで待機"""
        try:
            if self.config.frequency == UpdateFrequency.REALTIME:
                # リアルタイムの場合は30秒間隔でチェック
                time.sleep(30)
            else:
                # 次の更新時刻まで待機
                if self.status.next_update:
                    wait_seconds = (self.status.next_update - datetime.now()).total_seconds()
                    if wait_seconds > 0:
                        time.sleep(min(wait_seconds, 3600))  # 最大1時間
                    else:
                        time.sleep(60)  # 1分待機
                else:
                    time.sleep(300)  # 5分待機
            
        except Exception as e:
            logger.error(f"待機エラー: {e}")
            time.sleep(60)
    
    def _update_status(self, status: str, message: str):
        """ステータスを更新"""
        try:
            self.status.status = status
            self.status.last_update = datetime.now()
            
            if status == "success":
                self.status.error_message = None
            elif status == "error":
                self.status.error_message = message
            
            # ステータス変更コールバック実行
            for callback in self.status_change_callbacks:
                try:
                    callback(self.status)
                except Exception as e:
                    logger.error(f"ステータスコールバック実行エラー: {e}")
            
            logger.info(f"ステータス更新: {status} - {message}")
            
        except Exception as e:
            logger.error(f"ステータス更新エラー: {e}")
    
    def _send_notification(self, notification_type: str, message: str):
        """通知を送信"""
        try:
            # Slack通知
            if "slack" in self.config.notification_channels:
                self._send_slack_notification(notification_type, message)
            
            # その他の通知チャネル
            # TODO: メール、Discord等の実装
            
        except Exception as e:
            logger.error(f"通知送信エラー: {e}")
    
    def _send_slack_notification(self, notification_type: str, message: str):
        """Slack通知を送信"""
        try:
            # 既存の通知機能を使用
            from ..automation.notifications import NotificationManager
            
            notification_manager = NotificationManager(self.econ_config)
            
            # 通知メッセージ作成
            if notification_type == "success":
                title = "✅ 経済指標データ更新完了"
                color = "good"
            else:
                title = "❌ 経済指標データ更新エラー"
                color = "danger"
            
            notification_manager.send_slack_message(
                title=title,
                message=message,
                color=color
            )
            
        except Exception as e:
            logger.error(f"Slack通知エラー: {e}")
    
    def add_data_update_callback(self, callback: Callable[[List[ProcessedIndicator], List[TrendResult]], None]):
        """データ更新コールバックを追加"""
        self.data_update_callbacks.append(callback)
    
    def add_status_change_callback(self, callback: Callable[[UpdateStatus], None]):
        """ステータス変更コールバックを追加"""
        self.status_change_callbacks.append(callback)
    
    def get_status(self) -> UpdateStatus:
        """現在のステータスを取得"""
        return self.status
    
    def force_update(self):
        """強制更新"""
        try:
            logger.info("強制更新を実行します")
            self._perform_update()
        except Exception as e:
            logger.error(f"強制更新エラー: {e}")
    
    def get_dashboard_urls(self) -> Dict[str, Optional[str]]:
        """ダッシュボードURLを取得"""
        urls = {}
        
        if self.sheets_manager:
            urls['sheets'] = self.sheets_manager.get_dashboard_url()
        
        if self.advanced_dashboard and self.advanced_dashboard.config.save_path:
            html_path = self.advanced_dashboard.config.save_path.with_suffix('.html')
            if html_path.exists():
                urls['advanced'] = str(html_path)
        
        return urls
