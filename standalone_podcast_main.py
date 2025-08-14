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
import pytz

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
        
        # JST時刻を取得
        jst = pytz.timezone('Asia/Tokyo')
        now_jst = datetime.now(jst)
        
        # 複数のテスト記事でポッドキャスト生成（実際の配信に近い内容量）
        test_articles = [
            {
                'title': '日経平均、3日続伸で年初来高値更新',
                'summary': '東京株式市場で日経平均株価が3営業日続伸し、年初来高値を更新しました。米国市場の堅調な推移や円安基調を背景に、自動車株や電機株に買いが集まり、幅広い銘柄が上昇しました。市場関係者は「企業業績の改善期待と海外投資家の資金流入が相場を押し上げている」と分析しています。',
                'content': '東京株式市場で日経平均株価が3営業日続伸し、年初来高値を更新しました。',
                'url': 'https://example.com/nikkei-high',
                'source': '経済ニュース',
                'published_jst': now_jst,
                'sentiment_label': 'Positive'
            },
            {
                'title': '米FRB、政策金利を据え置き決定',
                'summary': '米連邦準備制度理事会（FRB）は今回の連邦公開市場委員会（FOMC）で政策金利を現行水準に据え置くことを決定しました。パウエル議長は記者会見で「インフレ率の推移を慎重に見極める」と述べ、今後の金融政策について慎重姿勢を示しました。市場では次回会合での利下げ観測が高まっています。',
                'content': '米連邦準備制度理事会（FRB）は政策金利を据え置くことを決定しました。',
                'url': 'https://example.com/fed-rate',
                'source': '金融ニュース',
                'published_jst': now_jst,
                'sentiment_label': 'Neutral'
            },
            {
                'title': '原油価格急落、需要懸念で約3%下落',
                'summary': '国際原油市場でWTI原油先物価格が急落し、前日比約3%下落しました。中国経済の減速懸念や米国の原油在庫増加を受け、需給バランスへの懸念が高まったことが要因です。エネルギー関連株も軒並み下落し、株式市場全体の重荷となっています。アナリストは「短期的な調整局面」との見方を示しています。',
                'content': '国際原油市場でWTI原油先物価格が前日比約3%下落しました。',
                'url': 'https://example.com/oil-drop',
                'source': 'エネルギーニュース',
                'published_jst': now_jst,
                'sentiment_label': 'Negative'
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