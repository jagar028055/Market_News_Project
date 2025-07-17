# -*- coding: utf-8 -*-

import logging
import logging.handlers
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from config.base import LoggingConfig


class StructuredFormatter(logging.Formatter):
    """構造化ログフォーマッター"""
    
    def format(self, record: logging.LogRecord) -> str:
        # 基本ログエントリ
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process_id': os.getpid(),
            'thread_id': record.thread
        }
        
        # 例外情報
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # 追加のコンテキスト情報
        if hasattr(record, 'extra_data'):
            log_entry['context'] = record.extra_data
        
        # 機密情報のマスキング
        log_entry = self._mask_sensitive_data(log_entry)
        
        return json.dumps(log_entry, ensure_ascii=False)
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """機密情報のマスキング"""
        sensitive_keys = {
            'api_key', 'token', 'password', 'secret', 'credentials',
            'gemini_api_key', 'service_account_json', 'auth', 'key'
        }
        
        def mask_recursive(obj):
            if isinstance(obj, dict):
                return {
                    key: '***MASKED***' if any(sensitive in key.lower() for sensitive in sensitive_keys)
                    else mask_recursive(value)
                    for key, value in obj.items()
                }
            elif isinstance(obj, list):
                return [mask_recursive(item) for item in obj]
            elif isinstance(obj, str) and len(obj) > 20:
                # 長い文字列で機密情報の可能性があるものをマスク
                for sensitive in sensitive_keys:
                    if sensitive in obj.lower():
                        return '***MASKED***'
            return obj
        
        return mask_recursive(data)


class TextFormatter(logging.Formatter):
    """通常のテキストフォーマッター"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


class LoggerManager:
    """ログ管理クラス"""
    
    def __init__(self, config: LoggingConfig):
        self.config = config
        self.setup_logging()
    
    def setup_logging(self):
        """ログ設定初期化"""
        # ルートロガー設定
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.level.upper()))
        
        # 既存ハンドラー削除
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # フォーマッター選択
        if self.config.format.lower() == 'json':
            formatter = StructuredFormatter()
        else:
            formatter = TextFormatter()
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # ファイルハンドラー（有効な場合）
        if self.config.file_enabled:
            self._setup_file_handlers(formatter)
    
    def _setup_file_handlers(self, formatter: logging.Formatter):
        """ファイルハンドラー設定"""
        # ログディレクトリ作成
        log_path = Path(self.config.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 通常ログファイル（ローテーション付き）
        file_handler = logging.handlers.RotatingFileHandler(
            self.config.file_path,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
        
        # エラーログ専用ファイル
        error_log_path = log_path.parent / f"{log_path.stem}_errors{log_path.suffix}"
        error_handler = logging.handlers.RotatingFileHandler(
            str(error_log_path),
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count * 2,  # エラーログは多めに保持
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logging.getLogger().addHandler(error_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """ロガー取得"""
        return logging.getLogger(f"market_news.{name}")


# グローバルロガーマネージャー
_logger_manager: Optional[LoggerManager] = None


def setup_logging(config: LoggingConfig) -> LoggerManager:
    """ログシステム初期化"""
    global _logger_manager
    _logger_manager = LoggerManager(config)
    return _logger_manager


def get_logger(name: str) -> logging.Logger:
    """ロガー取得（簡易インターフェース）"""
    if _logger_manager is None:
        # デフォルト設定でロガーマネージャーを初期化
        from config.base import LoggingConfig
        setup_logging(LoggingConfig())
    return _logger_manager.get_logger(name)


def log_with_context(
    logger: logging.Logger, 
    level: int, 
    message: str, 
    **context
) -> None:
    """コンテキスト情報付きログ出力"""
    extra_data = {
        'operation': context.get('operation'),
        'url': context.get('url'),
        'duration_ms': context.get('duration_ms'),
        'status': context.get('status'),
        'count': context.get('count'),
        **{k: v for k, v in context.items() 
           if k not in ['operation', 'url', 'duration_ms', 'status', 'count']}
    }
    
    # None値を除去
    extra_data = {k: v for k, v in extra_data.items() if v is not None}
    
    logger.log(level, message, extra={'extra_data': extra_data})