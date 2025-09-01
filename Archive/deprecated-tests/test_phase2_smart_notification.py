#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Phase 2 スマート通知システム統合テスト
実際の機能動作を確認するためのデモスクリプト
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

from src.config.app_config import AppConfig
from src.podcast.integration.smart_notification_manager import SmartNotificationManager
from src.podcast.integration.notification_scheduler import NotificationPriority

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def create_sample_data():
    """サンプルデータ作成"""
    episode_info = {
        'published_at': datetime.now(),
        'file_size_mb': 5.2,
        'article_count': 8,
        'title': 'マーケットニュース 2025年8月14日版'
    }
    
    articles = [
        {
            'title': '日経平均株価が大幅上昇、年内最高値を更新',
            'sentiment_label': 'Positive',
            'summary': '東京株式市場で日経平均株価が前日比500円高の34,000円で終了し、年内最高値を更新した。'
        },
        {
            'title': '米FRBの利上げ決定が市場に与える影響を分析',
            'sentiment_label': 'Neutral',
            'summary': 'アメリカ連邦準備制度理事会（FRB）の利上げ決定について、専門家が市場への影響を詳しく解説。'
        },
        {
            'title': '暗号通貨市場で大幅な下落が継続、投資家が警戒',
            'sentiment_label': 'Negative',
            'summary': 'ビットコインをはじめとする主要暗号通貨が軒並み下落し、投資家の間で警戒感が広がっている。'
        },
        {
            'title': '新興市場銘柄に注目が集まる理由とは',
            'sentiment_label': 'Positive',
            'summary': '成長期待の高い新興市場銘柄に機関投資家からの注目が集まっている背景を探る。'
        },
        {
            'title': '円安進行で輸出企業の業績改善が期待される',
            'sentiment_label': 'Positive',
            'summary': '円安の進行により、自動車や電子機器メーカーなど輸出関連企業の業績改善への期待が高まっている。'
        }
    ]
    
    return episode_info, articles

def test_notification_preview(manager, episode_info, articles, logger):
    """通知プレビュー機能のテスト"""
    logger.info("=== 通知プレビューテスト開始 ===")
    
    try:
        preview_options = {
            'use_flex_message': True,
            'use_images': True,
            'audio_url': 'https://example.com/podcast/episode_20250814.mp3',
            'rss_url': 'https://example.com/podcast/feed.xml'
        }
        
        preview = manager.get_notification_preview(episode_info, articles, preview_options)
        
        logger.info(f"プレビュー生成成功")
        logger.info(f"記事数: {preview.get('article_count', 0)}")
        logger.info(f"推定文字数: {preview.get('estimated_characters', 0)}")
        logger.info(f"センチメント分布: {preview.get('sentiment_distribution', {})}")
        logger.info(f"画像URL数: {len(preview.get('image_urls', {}))}")
        
        # テキストメッセージの一部を表示
        text_message = preview.get('text_message', '')
        if text_message:
            preview_text = text_message[:200] + '...' if len(text_message) > 200 else text_message
            logger.info(f"テキストメッセージ（先頭200文字）:\n{preview_text}")
        
        return True
        
    except Exception as e:
        logger.error(f"プレビューテストエラー: {e}")
        return False

def test_scheduled_notification(manager, episode_info, articles, logger):
    """スケジュール通知機能のテスト"""
    logger.info("=== スケジュール通知テスト開始 ===")
    
    try:
        # 5分後にスケジュール
        scheduled_time = datetime.now() + timedelta(minutes=5)
        
        schedule_options = {
            'scheduled_time': scheduled_time,
            'priority': NotificationPriority.HIGH,
            'use_flex_message': True,
            'use_images': True,
            'audio_url': 'https://example.com/podcast/episode_20250814.mp3'
        }
        
        result = manager.schedule_podcast_notification(episode_info, articles, schedule_options)
        
        if result.get('success', False):
            notification_id = result.get('notification_id')
            logger.info(f"スケジュール登録成功: {notification_id}")
            logger.info(f"配信予定時刻: {result.get('scheduled_time')}")
            
            # スケジュール状態確認
            status = manager.scheduler.get_notification_status(notification_id)
            if status:
                logger.info(f"通知ステータス: {status.get('status')}")
                logger.info(f"優先度: {status.get('priority')}")
            
            return notification_id
        else:
            logger.error(f"スケジュール登録失敗: {result.get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        logger.error(f"スケジュール通知テストエラー: {e}")
        return None

def test_multiple_episodes(manager, logger):
    """複数エピソード配信テスト"""
    logger.info("=== 複数エピソード配信テスト開始 ===")
    
    try:
        # 複数のサンプルエピソードを作成
        episodes = []
        
        for i in range(3):
            episode_info = {
                'published_at': datetime.now() - timedelta(days=i),
                'file_size_mb': 4.5 + i * 0.3,
                'article_count': 6 + i,
                'title': f'マーケットニュース {datetime.now().strftime("%Y年%m月%d日")} 第{i+1}回'
            }
            
            articles = [
                {
                    'title': f'市場動向分析 第{i+1}回',
                    'sentiment_label': ['Positive', 'Neutral', 'Negative'][i % 3]
                },
                {
                    'title': f'注目銘柄レポート 第{i+1}回', 
                    'sentiment_label': 'Neutral'
                }
            ]
            
            episodes.append({
                'episode_info': episode_info,
                'articles': articles,
                'options': {
                    'audio_url': f'https://example.com/podcast/episode_{i+1}.mp3'
                }
            })
        
        batch_options = {
            'use_carousel': True,
            'use_flex_message': True,
            'send_interval': 1  # 1秒間隔
        }
        
        # ※実際のLINE配信はしないため、プレビューのみテスト
        logger.info(f"複数エピソード配信シミュレーション: {len(episodes)}件")
        logger.info("実際の配信はテストのため実行しません")
        
        # 各エピソードのプレビューを生成
        for i, episode in enumerate(episodes):
            preview = manager.get_notification_preview(
                episode['episode_info'], 
                episode['articles']
            )
            logger.info(f"エピソード {i+1}: 記事数={preview.get('article_count', 0)}, 文字数={preview.get('estimated_characters', 0)}")
        
        return True
        
    except Exception as e:
        logger.error(f"複数エピソード配信テストエラー: {e}")
        return False

def test_system_status(manager, logger):
    """システムステータス確認テスト"""
    logger.info("=== システムステータス確認テスト ===")
    
    try:
        status = manager.get_system_status()
        
        logger.info(f"システム全体ステータス: {status.get('overall_status', 'unknown')}")
        logger.info(f"チェック時刻: {status.get('timestamp')}")
        
        # 各コンポーネントのステータス
        components = status.get('components', {})
        
        line_status = components.get('line_broadcaster', {})
        logger.info(f"LINE Broadcaster: {line_status.get('connection_status', 'unknown')}")
        logger.info(f"Flex Message有効: {line_status.get('flex_message_enabled', False)}")
        
        scheduler_status = components.get('scheduler', {})
        logger.info(f"スケジューラー: {'実行中' if scheduler_status.get('scheduler_running', False) else '停止中'}")
        logger.info(f"待機中通知数: {scheduler_status.get('total_notifications', 0)}")
        
        image_status = components.get('image_manager', {})
        logger.info(f"画像キャッシュ: {image_status.get('valid_entries', 0)}件 ({image_status.get('cache_size_mb', 0):.2f}MB)")
        
        return True
        
    except Exception as e:
        logger.error(f"システムステータス確認エラー: {e}")
        return False

def main():
    """メイン実行関数"""
    logger = setup_logging()
    logger.info("Phase 2 スマート通知システム統合テスト開始")
    
    try:
        # 設定読み込み（実際の設定ファイルがない場合はダミー設定）
        try:
            config = AppConfig()
        except Exception:
            logger.warning("設定ファイル読み込み失敗、ダミー設定を使用")
            from unittest.mock import Mock
            config = Mock()
            config.project_root = Path(__file__).parent
            config.podcast = Mock()
            config.podcast.base_url = "https://example.com"
            config.podcast.rss_base_url = "https://example.com"
            config.line = Mock()
            config.line.channel_access_token = "dummy_token"
        
        # スマート通知管理システム初期化
        manager = SmartNotificationManager(config, logger)
        
        # システム開始
        if not manager.start_system():
            logger.error("システム開始に失敗しました")
            return
        
        # サンプルデータ作成
        episode_info, articles = create_sample_data()
        
        # テスト実行
        test_results = []
        
        # 1. プレビュー機能テスト
        test_results.append(("プレビュー機能", test_notification_preview(manager, episode_info, articles, logger)))
        
        # 2. スケジュール通知テスト
        notification_id = test_scheduled_notification(manager, episode_info, articles, logger)
        test_results.append(("スケジュール通知", notification_id is not None))
        
        # 3. 複数エピソード配信テスト
        test_results.append(("複数エピソード配信", test_multiple_episodes(manager, logger)))
        
        # 4. システムステータス確認
        test_results.append(("システムステータス", test_system_status(manager, logger)))
        
        # テスト結果まとめ
        logger.info("=== テスト結果まとめ ===")
        success_count = 0
        for test_name, success in test_results:
            status = "✅ 成功" if success else "❌ 失敗"
            logger.info(f"{test_name}: {status}")
            if success:
                success_count += 1
        
        logger.info(f"総合結果: {success_count}/{len(test_results)} テスト成功")
        
        # スケジュール通知のクリーンアップ
        if notification_id:
            logger.info("スケジュール通知をキャンセルします")
            manager.scheduler.cancel_notification(notification_id)
        
        # システム停止
        manager.stop_system()
        
        logger.info("Phase 2 スマート通知システム統合テスト完了")
        
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {e}")
        raise

if __name__ == "__main__":
    main()