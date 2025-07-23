"""ポッドキャスト生成メイン実行スクリプト"""

import asyncio
import logging
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.app_config import load_config
from src.podcast.core.podcast_processor import PodcastProcessor
from src.logging_config import setup_logging


async def main():
    """メイン処理"""
    try:
        # ログ設定
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("Starting podcast generation process")
        
        # 設定読み込み
        config = load_config()
        
        # ポッドキャスト処理器初期化
        processor = PodcastProcessor(config)
        
        # 処理前のクリーンアップ
        logger.info("Performing cleanup of old files")
        processor.cleanup_old_files(days=7)
        
        # コスト状況確認
        cost_summary = processor.get_cost_summary()
        logger.info(f"Current cost status: ${cost_summary.current_month_total:.2f} / ${config.podcast.monthly_cost_limit:.2f}")
        
        if cost_summary.current_month_total >= config.podcast.monthly_cost_limit:
            logger.error("Monthly cost limit reached. Skipping podcast generation.")
            return
            
        # ポッドキャスト生成実行
        logger.info("Starting daily podcast generation")
        result = await processor.generate_daily_podcast()
        
        # 結果出力
        if result['success']:
            logger.info("Podcast generation completed successfully")
            logger.info(f"Processing time: {result['processing_time']:.1f} seconds")
            logger.info(f"Episode: {result['episode_info']['title']}")
            logger.info(f"Publish results: {result['publish_results']}")
            
            # コスト情報更新
            final_cost_summary = processor.get_cost_summary()
            logger.info(f"Final cost status: ${final_cost_summary.current_month_total:.2f}")
            
        else:
            logger.error(f"Podcast generation failed: {result['error']}")
            
            # エラー情報取得
            error_summary = processor.publisher.get_error_summary(hours=1)
            if error_summary['total_errors'] > 0:
                logger.error(f"Recent errors: {error_summary}")
                
        return result
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Podcast generation process failed: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def run_podcast_generation():
    """同期的な実行ラッパー"""
    return asyncio.run(main())


if __name__ == "__main__":
    # 直接実行時
    result = run_podcast_generation()
    
    # 終了コード設定
    if result and result.get('success'):
        sys.exit(0)
    else:
        sys.exit(1)