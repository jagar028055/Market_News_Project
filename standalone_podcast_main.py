#!/usr/bin/env python3
"""
Standalone Podcast Main Script
GitHub Actions用のポッドキャスト生成・配信スクリプト
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 依存関係の問題を回避するため、直接インポートを避ける
try:
    from src.podcast.integration.podcast_integration_manager import PodcastIntegrationManager
except ImportError as e:
    print(f"Import error: {e}")
    print("Required dependencies may be missing. Please check requirements.txt")
    sys.exit(1)

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('podcast_workflow.log')
        ]
    )
    return logging.getLogger(__name__)

def check_environment():
    """環境変数の確認"""
    required_vars = [
        'GEMINI_API_KEY',
        'LINE_CHANNEL_ACCESS_TOKEN',
        'GOOGLE_OAUTH2_CLIENT_ID',
        'GOOGLE_OAUTH2_CLIENT_SECRET',
        'GOOGLE_OAUTH2_REFRESH_TOKEN'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")

def should_run_workflow():
    """ワークフローを実行すべきかチェック"""
    # 強制実行フラグ
    force_run = os.getenv('PODCAST_FORCE_RUN', 'false').lower() == 'true'
    if force_run:
        return True, "Force run enabled"
    
    # 平日のみ実行フラグ
    weekdays_only = os.getenv('PODCAST_WEEKDAYS_ONLY', 'false').lower() == 'true'
    if weekdays_only:
        today = datetime.now().weekday()  # 0=月曜日, 6=日曜日
        if today >= 5:  # 土曜日(5)または日曜日(6)
            return False, "Weekdays only mode: Today is weekend"
    
    return True, "Normal execution conditions met"

def main():
    """メイン処理"""
    logger = setup_logging()
    logger.info("=== Standalone Podcast Workflow Started ===")
    
    try:
        # 環境変数チェック
        check_environment()
        logger.info("Environment variables validated")
        
        # 実行条件チェック
        should_run, reason = should_run_workflow()
        logger.info(f"Execution check: {reason}")
        
        if not should_run:
            logger.info("Workflow execution skipped")
            return 0
        
        # テストモードチェック
        test_mode = os.getenv('PODCAST_TEST_MODE', 'false').lower() == 'true'
        if test_mode:
            logger.info("Running in TEST MODE - no actual broadcast")
        
        # 設定とロガーを準備
        from src.config.app_config import get_config
        config = get_config()
        
        # ポッドキャスト統合マネージャーを初期化
        manager = PodcastIntegrationManager(config, logger)
        
        # ポッドキャスト生成・配信実行
        logger.info("Starting podcast generation and broadcast...")
        
        # 設定チェック
        if not manager.is_podcast_enabled():
            logger.error("Podcast generation is not enabled")
            return 1
            
        if not manager.check_configuration():
            logger.error("Podcast configuration is invalid")
            return 1
            
        if not manager.check_cost_limits():
            logger.error("Cost limits exceeded")
            return 1
        
        # 簡単なテスト記事でポッドキャスト生成
        test_articles = [
            {
                'title': 'テスト記事：今日の市場動向',
                'summary': '本日の株式市場は堅調な動きを見せています。主要指数は軒並み上昇し、投資家心理の改善が見られます。技術株を中心に買いが集まり、市場全体の活況が続いています。',
                'content': '本日の株式市場は堅調な動きを見せています。主要指数は軒並み上昇し、投資家心理の改善が見られます。',
                'url': 'https://example.com/test',
                'source': 'テストニュース',
                'published_jst': datetime.now(),
                'sentiment_label': 'Positive'
            }
        ]
        
        # ポッドキャスト生成
        podcast_path = manager.generate_podcast_from_articles(test_articles)
        
        if podcast_path:
            logger.info(f"Podcast generated successfully: {podcast_path}")
            
            # テストモードでなければLINE配信
            if not test_mode:
                broadcast_success = manager.broadcast_podcast_to_line(podcast_path, test_articles)
                if broadcast_success:
                    logger.info("Podcast broadcast to LINE successful")
                else:
                    logger.error("Podcast broadcast to LINE failed")
                    return 1
            else:
                logger.info("TEST MODE: Skipping LINE broadcast")
            
            success = True
        else:
            logger.error("Podcast generation failed")
            success = False
        
        if success:
            logger.info("=== Podcast workflow completed successfully ===")
            return 0
        else:
            logger.error("=== Podcast workflow failed ===")
            return 1
            
    except Exception as e:
        logger.error(f"Workflow failed with error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)