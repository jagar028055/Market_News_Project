#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
10分本番ポッドキャスト配信システム
プロダクション実行用メインエントリーポイント
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config.app_config import get_config
from src.podcast.integration.production_podcast_integration_manager import ProductionPodcastIntegrationManager
from src.logging_config import setup_logging


def setup_podcast_logging(mode: str) -> logging.Logger:
    """ポッドキャスト専用ログ設定"""
    log_dir = Path(project_root) / "logs" / "podcast"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"podcast_{mode}_{timestamp}.log"
    
    # ログ設定
    setup_logging(
        level=logging.INFO,
        log_file=str(log_file),
        format_type="detailed"
    )
    
    logger = logging.getLogger("podcast_production")
    logger.info(f"=== 10分ポッドキャスト配信開始 ===")
    logger.info(f"モード: {mode}")
    logger.info(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S JST')}")
    logger.info(f"ログファイル: {log_file}")
    
    return logger


async def run_podcast_production(
    mode: str,
    duration: int,
    config_overrides: Optional[dict] = None
) -> bool:
    """
    ポッドキャスト制作・配信実行
    
    Args:
        mode: 実行モード ('test' または 'production')
        duration: ポッドキャスト目標時間（秒）
        config_overrides: 設定上書き
        
    Returns:
        成功時True、失敗時False
    """
    logger = logging.getLogger("podcast_production")
    
    try:
        # 設定読み込み
        config = get_config()
        
        # 設定上書き適用
        if config_overrides:
            for key, value in config_overrides.items():
                if hasattr(config.ai, key):
                    setattr(config.ai, key, value)
                logger.info(f"設定上書き: {key} = {value}")
        
        # モード別設定調整
        if mode == "test":
            logger.info("テストモード設定適用")
            # テスト用にトークン数を制限
            config.ai.podcast_script_max_tokens = min(2048, config.ai.podcast_script_max_tokens)
            config.ai.max_output_tokens = min(512, config.ai.max_output_tokens)
            
        elif mode == "production":
            logger.info("本番モード設定適用")
            # 本番用に最適化
            config.ai.podcast_script_max_tokens = 4096
            config.ai.max_output_tokens = 1024
        
        # 統合マネージャー初期化
        logger.info("統合マネージャー初期化開始")
        integration_manager = ProductionPodcastIntegrationManager(config)
        
        # ポッドキャスト制作・配信実行
        logger.info(f"ポッドキャスト制作開始（目標時間: {duration}秒）")
        result = await integration_manager.execute_full_pipeline(
            target_duration=duration,
            test_mode=(mode == "test")
        )
        
        if result.get("success", False):
            logger.info("=== ポッドキャスト配信成功 ===")
            logger.info(f"制作時間: {result.get('production_time', 'N/A')}秒")
            logger.info(f"音声時間: {result.get('audio_duration', 'N/A')}秒")
            logger.info(f"配信URL: {result.get('distribution_url', 'N/A')}")
            
            # GitHub Actions用出力
            _output_github_actions_results(result)
            
            return True
        else:
            logger.error("=== ポッドキャスト配信失敗 ===")
            logger.error(f"エラー: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"ポッドキャスト制作中にエラー発生: {e}")
        logger.exception("詳細エラー情報")
        return False


def _output_github_actions_results(result: dict) -> None:
    """GitHub Actions用の出力を生成"""
    github_output = os.getenv("GITHUB_OUTPUT")
    if not github_output:
        return
    
    try:
        with open(github_output, 'a', encoding='utf-8') as f:
            f.write(f"success={str(result.get('success', False)).lower()}\n")
            f.write(f"production_time={result.get('production_time', 0)}\n")
            f.write(f"audio_duration={result.get('audio_duration', 0)}\n")
            
            if result.get('distribution_url'):
                f.write(f"distribution_url={result['distribution_url']}\n")
            
            if result.get('rss_url'):
                f.write(f"rss_url={result['rss_url']}\n")
            
            if result.get('error'):
                error_message = str(result['error']).replace('\n', ' ')
                f.write(f"error_message={error_message}\n")
                
    except Exception as e:
        logging.getLogger("podcast_production").warning(f"GitHub Actions出力生成エラー: {e}")


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="10分本番ポッドキャスト配信システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # テストモード実行
  python -m src.podcast.production_main --mode=test --duration=600
  
  # 本番モード実行  
  python -m src.podcast.production_main --mode=production --duration=600
  
  # 設定上書きあり
  python -m src.podcast.production_main --mode=test --duration=300 --script-model=gemini-2.5-flash-lite
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["test", "production"],
        default="test",
        help="実行モード (default: test)"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=600,
        help="ポッドキャスト目標時間（秒） (default: 600)"
    )
    
    parser.add_argument(
        "--script-model",
        type=str,
        help="台本生成モデル上書き"
    )
    
    parser.add_argument(
        "--script-temperature",
        type=float,
        help="台本生成温度上書き"
    )
    
    parser.add_argument(
        "--no-line-notify",
        action="store_true",
        help="LINE通知を無効化"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="ログレベル (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # ログ設定
    logger = setup_podcast_logging(args.mode)
    logger.info(f"引数: {vars(args)}")
    
    # 環境変数チェック
    required_env_vars = [
        "GEMINI_API_KEY",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "GOOGLE_DRIVE_OUTPUT_FOLDER_ID"
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"必須環境変数が設定されていません: {missing_vars}")
        sys.exit(1)
    
    # 設定上書き準備
    config_overrides = {}
    if args.script_model:
        config_overrides["podcast_script_model"] = args.script_model
    if args.script_temperature is not None:
        config_overrides["podcast_script_temperature"] = args.script_temperature
    if args.no_line_notify:
        config_overrides["line_notify_enabled"] = False
    
    # ポッドキャスト実行
    try:
        success = asyncio.run(run_podcast_production(
            mode=args.mode,
            duration=args.duration,
            config_overrides=config_overrides
        ))
        
        exit_code = 0 if success else 1
        logger.info(f"プロセス終了 (exit_code: {exit_code})")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("ユーザーによる実行中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        logger.exception("詳細エラー情報")
        sys.exit(1)


if __name__ == "__main__":
    main()