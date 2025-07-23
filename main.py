# -*- coding: utf-8 -*-

import os
import logging
from dotenv import load_dotenv
from src.core import NewsProcessor
from src.logging_config import setup_logging
from config.base import LoggingConfig

# ポッドキャスト機能の条件付きインポート
try:
    from podcast_main import run_podcast_generation
    PODCAST_ENABLED = True
except ImportError:
    PODCAST_ENABLED = False

# .envファイルから環境変数を読み込む
load_dotenv()

def main() -> None:
    """
    スクリプト全体のメイン処理を実行する
    """
    # ログ設定
    config = LoggingConfig()
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    # 既存のニュース処理実行
    logger.info("Starting news processing")
    processor = NewsProcessor()
    processor.run()
    
    # ポッドキャスト生成の実行判定
    enable_podcast = os.getenv('ENABLE_PODCAST_GENERATION', 'false').lower() == 'true'
    
    if enable_podcast and PODCAST_ENABLED:
        logger.info("Starting podcast generation")
        try:
            podcast_result = run_podcast_generation()
            if podcast_result and podcast_result.get('success'):
                logger.info("Podcast generation completed successfully")
            else:
                logger.error(f"Podcast generation failed: {podcast_result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Podcast generation error: {e}", exc_info=True)
    else:
        if enable_podcast and not PODCAST_ENABLED:
            logger.warning("Podcast generation requested but not available (missing dependencies)")
        else:
            logger.info("Podcast generation disabled (ENABLE_PODCAST_GENERATION=false)")

if __name__ == "__main__":
    main()
