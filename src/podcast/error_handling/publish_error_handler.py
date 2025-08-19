"""ポッドキャスト配信エラーハンドリング機能"""

import logging
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path

from ...config.app_config import AppConfig
from ...error_handling.custom_exceptions import PodcastPublishError


logger = logging.getLogger(__name__)


class PublishErrorType(Enum):
    """配信エラータイプ"""
    RSS_GENERATION_ERROR = "rss_generation_error"
    RSS_DEPLOYMENT_ERROR = "rss_deployment_error"
    LINE_API_ERROR = "line_api_error"
    LINE_RATE_LIMIT = "line_rate_limit"
    NETWORK_ERROR = "network_error"
    FILE_ERROR = "file_error"
    CONFIGURATION_ERROR = "configuration_error"


class PublishRetryStrategy:
    """配信再試行戦略"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        
    def get_delay(self, attempt: int) -> float:
        """指数バックオフによる遅延時間計算"""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        return delay
        
    def should_retry(self, error_type: PublishErrorType, attempt: int) -> bool:
        """再試行すべきかどうかを判定"""
        if attempt >= self.max_retries:
            return False
            
        # 設定エラーは再試行しない
        if error_type == PublishErrorType.CONFIGURATION_ERROR:
            return False
            
        # レート制限エラーは長めの間隔で再試行
        if error_type == PublishErrorType.LINE_RATE_LIMIT:
            return attempt < 2  # 最大2回まで
            
        return True


class PublishErrorTracker:
    """配信エラー追跡クラス"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.error_log_path = Path(config.podcast.error_log_dir) / "publish_errors.json"
        self.error_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.errors = self._load_error_log()
        
    def record_error(self, episode_guid: str, channel: str, error_type: PublishErrorType, 
                    error_message: str, attempt: int = 1) -> None:
        """エラーを記録"""
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'episode_guid': episode_guid,
            'channel': channel,
            'error_type': error_type.value,
            'error_message': error_message,
            'attempt': attempt
        }
        
        if episode_guid not in self.errors:
            self.errors[episode_guid] = []
            
        self.errors[episode_guid].append(error_record)
        self._save_error_log()
        
        logger.error(f"Publish error recorded: {channel} - {error_type.value} - {error_message}")
        
    def get_episode_errors(self, episode_guid: str) -> List[Dict]:
        """エピソードのエラー履歴を取得"""
        return self.errors.get(episode_guid, [])
        
    def get_recent_errors(self, hours: int = 24) -> List[Dict]:
        """最近のエラーを取得"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = []
        
        for episode_errors in self.errors.values():
            for error in episode_errors:
                error_time = datetime.fromisoformat(error['timestamp'])
                if error_time > cutoff_time:
                    recent_errors.append(error)
                    
        return sorted(recent_errors, key=lambda x: x['timestamp'], reverse=True)
        
    def cleanup_old_errors(self, days: int = 30) -> None:
        """古いエラーログをクリーンアップ"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for episode_guid in list(self.errors.keys()):
            filtered_errors = []
            for error in self.errors[episode_guid]:
                error_time = datetime.fromisoformat(error['timestamp'])
                if error_time > cutoff_time:
                    filtered_errors.append(error)
                    
            if filtered_errors:
                self.errors[episode_guid] = filtered_errors
            else:
                del self.errors[episode_guid]
                
        self._save_error_log()
        
    def _load_error_log(self) -> Dict:
        """エラーログファイルを読み込み"""
        try:
            if self.error_log_path.exists():
                with open(self.error_log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"Error log load failed: {e}")
            return {}
            
    def _save_error_log(self) -> None:
        """エラーログファイルを保存"""
        try:
            with open(self.error_log_path, 'w', encoding='utf-8') as f:
                json.dump(self.errors, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error log save failed: {e}")


class PublishErrorHandler:
    """配信エラーハンドリング統合クラス"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.retry_strategy = PublishRetryStrategy(
            max_retries=config.podcast.max_publish_retries,
            base_delay=config.podcast.publish_retry_delay,
            max_delay=config.podcast.max_publish_retry_delay
        )
        self.error_tracker = PublishErrorTracker(config)
        
    def execute_with_retry(self, 
                          func: Callable,
                          episode_guid: str,
                          channel: str,
                          *args, **kwargs) -> bool:
        """再試行機能付きで関数を実行
        
        Args:
            func: 実行する関数
            episode_guid: エピソードGUID
            channel: 配信チャンネル
            *args, **kwargs: 函数への引数
            
        Returns:
            bool: 実行成功/失敗
        """
        last_error = None
        
        for attempt in range(self.retry_strategy.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if result:  # 成功
                    if attempt > 0:
                        logger.info(f"{channel} publish succeeded after {attempt} retries")
                    return True
                else:
                    # 失敗だが例外は発生していない
                    error_type = self._classify_error_type(None, channel)
                    last_error = f"Function returned False (attempt {attempt + 1})"
                    
            except Exception as e:
                error_type = self._classify_error_type(e, channel)
                last_error = str(e)
                
                # エラーを記録
                self.error_tracker.record_error(
                    episode_guid, channel, error_type, last_error, attempt + 1
                )
                
                # 再試行すべきかチェック
                if not self.retry_strategy.should_retry(error_type, attempt):
                    logger.error(f"{channel} publish failed after {attempt + 1} attempts: {last_error}")
                    return False
                    
                # 再試行前の待機
                if attempt < self.retry_strategy.max_retries:
                    delay = self.retry_strategy.get_delay(attempt)
                    logger.info(f"{channel} publish failed (attempt {attempt + 1}), retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    
        # 全ての再試行が失敗
        logger.error(f"{channel} publish failed after all retries: {last_error}")
        return False
        
    def _classify_error_type(self, error: Optional[Exception], channel: str) -> PublishErrorType:
        """エラータイプを分類"""
        if error is None:
            return PublishErrorType.RSS_GENERATION_ERROR if channel == 'rss' else PublishErrorType.LINE_API_ERROR
            
        error_str = str(error).lower()
        
        # ネットワーク関連エラー
        if any(keyword in error_str for keyword in ['timeout', 'connection', 'network']):
            return PublishErrorType.NETWORK_ERROR
            
        # ファイル関連エラー
        if any(keyword in error_str for keyword in ['file', 'permission', 'disk']):
            return PublishErrorType.FILE_ERROR
            
        # LINE API固有エラー
        if channel == 'line':
            if 'rate limit' in error_str or '429' in error_str:
                return PublishErrorType.LINE_RATE_LIMIT
            return PublishErrorType.LINE_API_ERROR
            
        # RSS関連エラー
        if channel == 'rss':
            if 'deploy' in error_str or 'git' in error_str:
                return PublishErrorType.RSS_DEPLOYMENT_ERROR
            return PublishErrorType.RSS_GENERATION_ERROR
            
        return PublishErrorType.CONFIGURATION_ERROR
        
    def handle_partial_success(self, episode: Dict, results: Dict[str, bool]) -> Dict[str, bool]:
        """部分的成功の処理（一部チャンネルの配信が失敗した場合）"""
        failed_channels = [channel for channel, success in results.items() 
                          if not success and channel in ['rss', 'line']]
        
        if not failed_channels:
            return results
            
        logger.info(f"Handling partial success, retrying failed channels: {failed_channels}")
        
        # 失敗したチャンネルのみ再試行
        retry_results = {}
        for channel in failed_channels:
            if channel == 'rss':
                # RSS再配信のダミー実装
                retry_results[channel] = self._retry_rss_publish(episode)
            elif channel == 'line':
                # LINE再配信のダミー実装
                retry_results[channel] = self._retry_line_publish(episode)
                
        # 結果をマージ
        final_results = results.copy()
        final_results.update(retry_results)
        final_results['overall_success'] = any(final_results[ch] for ch in ['rss', 'line'])
        
        return final_results
        
    def _retry_rss_publish(self, episode: Dict) -> bool:
        """RSS配信の再試行（実装は具体的な配信ロジックに依存）"""
        # 実際の実装では、RSSGeneratorの再実行
        logger.info("Retrying RSS publish...")
        return True  # ダミー実装
        
    def _retry_line_publish(self, episode: Dict) -> bool:
        """LINE配信の再試行（実装は具体的な配信ロジックに依存）"""
        # 実際の実装では、LINEBroadcasterの再実行
        logger.info("Retrying LINE publish...")
        return True  # ダミー実装
        
    def get_error_summary(self, hours: int = 24) -> Dict:
        """エラーサマリーを取得"""
        recent_errors = self.error_tracker.get_recent_errors(hours)
        
        summary = {
            'total_errors': len(recent_errors),
            'error_types': {},
            'channels': {},
            'episodes_affected': set()
        }
        
        for error in recent_errors:
            # エラータイプ別集計
            error_type = error['error_type']
            summary['error_types'][error_type] = summary['error_types'].get(error_type, 0) + 1
            
            # チャンネル別集計
            channel = error['channel']
            summary['channels'][channel] = summary['channels'].get(channel, 0) + 1
            
            # 影響を受けたエピソード
            summary['episodes_affected'].add(error['episode_guid'])
            
        summary['episodes_affected'] = len(summary['episodes_affected'])
        
        return summary
        
    def should_alert(self, error_threshold: int = 5, time_window_hours: int = 1) -> bool:
        """アラートを発信すべきかどうか判定"""
        recent_errors = self.error_tracker.get_recent_errors(time_window_hours)
        return len(recent_errors) >= error_threshold