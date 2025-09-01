# -*- coding: utf-8 -*-

"""
スマート通知システムのユニットテスト
Phase 2: LINE Flex Message機能のテスト
"""

import unittest
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.podcast.integration.flex_message_templates import FlexMessageTemplates
from src.podcast.integration.line_broadcaster import LineBroadcaster
from src.podcast.integration.image_asset_manager import ImageAssetManager
from src.podcast.integration.notification_scheduler import NotificationScheduler, NotificationPriority


class TestFlexMessageTemplates(unittest.TestCase):
    """FlexMessageTemplatesのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.logger = Mock()
        self.templates = FlexMessageTemplates(self.logger)
        
        self.sample_episode_info = {
            'published_at': datetime(2025, 8, 14, 9, 0, 0),
            'file_size_mb': 5.2,
            'article_count': 8
        }
        
        self.sample_articles = [
            {
                'title': '日経平均株価が大幅上昇、年内最高値を更新',
                'sentiment_label': 'Positive'
            },
            {
                'title': '米FRBの利上げ決定が市場に与える影響',
                'sentiment_label': 'Neutral'
            },
            {
                'title': '暗号通貨市場で大幅な下落が続く',
                'sentiment_label': 'Negative'
            }
        ]
    
    def test_create_podcast_notification_flex(self):
        """Flex Message作成テスト"""
        flex_message = self.templates.create_podcast_notification_flex(
            self.sample_episode_info,
            self.sample_articles,
            audio_url="https://example.com/audio.mp3",
            rss_url="https://example.com/rss.xml"
        )
        
        # 基本構造確認
        self.assertEqual(flex_message['type'], 'flex')
        self.assertIn('contents', flex_message)
        self.assertEqual(flex_message['contents']['type'], 'bubble')
        
        # ヘッダー確認
        self.assertIn('header', flex_message['contents'])
        header = flex_message['contents']['header']
        self.assertEqual(header['type'], 'box')
        
        # ボディ確認
        self.assertIn('body', flex_message['contents'])
        body = flex_message['contents']['body']
        self.assertEqual(body['type'], 'box')
        
        # フッター確認
        self.assertIn('footer', flex_message['contents'])
        footer = flex_message['contents']['footer']
        self.assertEqual(footer['type'], 'box')
    
    def test_create_carousel_message(self):
        """カルーセルメッセージ作成テスト"""
        episodes = [
            {
                'episode_info': self.sample_episode_info,
                'articles': self.sample_articles[:2],
                'audio_url': 'https://example.com/audio1.mp3'
            },
            {
                'episode_info': {
                    'published_at': datetime(2025, 8, 13, 9, 0, 0),
                    'file_size_mb': 4.8,
                    'article_count': 6
                },
                'articles': self.sample_articles[1:],
                'audio_url': 'https://example.com/audio2.mp3'
            }
        ]
        
        carousel_message = self.templates.create_carousel_message(episodes)
        
        self.assertEqual(carousel_message['type'], 'flex')
        self.assertEqual(carousel_message['contents']['type'], 'carousel')
        self.assertIsInstance(carousel_message['contents']['contents'], list)
    
    def test_create_article_highlights(self):
        """記事ハイライト作成テスト"""
        highlights = self.templates._create_article_highlights(self.sample_articles, max_highlights=2)
        
        self.assertIsInstance(highlights, list)
        self.assertLessEqual(len(highlights), 2)
        self.assertTrue(all(isinstance(h, str) for h in highlights))
    
    def test_fallback_message(self):
        """フォールバックメッセージテスト"""
        fallback = self.templates._create_simple_fallback_message(
            self.sample_episode_info,
            self.sample_articles
        )
        
        self.assertEqual(fallback['type'], 'text')
        self.assertIn('text', fallback)
        self.assertIn('マーケットニュースポッドキャスト', fallback['text'])


class TestLineBroadcaster(unittest.TestCase):
    """LineBroadcasterのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.logger = Mock()
        self.config = Mock()
        self.config.line.channel_access_token = "test_token"
        self.config.podcast.rss_base_url = "https://example.com"
        
        self.broadcaster = LineBroadcaster(self.config, self.logger)
        
        self.sample_episode_info = {
            'published_at': datetime(2025, 8, 14, 9, 0, 0),
            'file_size_mb': 5.2,
            'article_count': 8
        }
        
        self.sample_articles = [
            {
                'title': '日経平均株価が大幅上昇',
                'sentiment_label': 'Positive'
            }
        ]
    
    @patch('requests.post')
    def test_broadcast_podcast_notification_success(self, mock_post):
        """通知配信成功テスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'X-Line-Request-Id': 'test_request_id'}
        mock_post.return_value = mock_response
        
        result = self.broadcaster.broadcast_podcast_notification(
            self.sample_episode_info,
            self.sample_articles,
            audio_url="https://example.com/audio.mp3"
        )
        
        self.assertTrue(result)
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_broadcast_with_flex_fallback(self, mock_post):
        """Flex Message失敗時のテキストメッセージフォールバック"""
        # 最初のFlex Message呼び出しで失敗
        mock_response_fail = Mock()
        mock_response_fail.status_code = 400
        mock_response_fail.text = "Invalid flex message"
        
        # テキストメッセージで成功
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.headers = {'X-Line-Request-Id': 'test_request_id'}
        
        mock_post.side_effect = [mock_response_fail, mock_response_success]
        
        result = self.broadcaster.broadcast_podcast_notification(
            self.sample_episode_info,
            self.sample_articles,
            use_flex=True
        )
        
        self.assertTrue(result)
        self.assertEqual(mock_post.call_count, 2)
    
    def test_flex_message_creation(self):
        """Flex Message作成テスト"""
        flex_message = self.broadcaster._create_flex_message(
            self.sample_episode_info,
            self.sample_articles,
            audio_url="https://example.com/audio.mp3",
            rss_url="https://example.com/rss.xml"
        )
        
        self.assertIn('type', flex_message)
        # Flex Messageまたはフォールバック（テキスト）
        self.assertIn(flex_message['type'], ['flex', 'text'])
    
    def test_text_message_creation(self):
        """テキストメッセージ作成テスト"""
        text_message = self.broadcaster._create_text_message(
            self.sample_episode_info,
            self.sample_articles,
            audio_url="https://example.com/audio.mp3"
        )
        
        self.assertEqual(text_message['type'], 'text')
        self.assertIn('text', text_message)
        self.assertIn('マーケットニュースポッドキャスト', text_message['text'])
    
    def test_message_preview(self):
        """メッセージプレビュー取得テスト"""
        preview = self.broadcaster.get_message_preview(
            self.sample_episode_info,
            self.sample_articles,
            audio_url="https://example.com/audio.mp3"
        )
        
        self.assertIn('text_message', preview)
        self.assertIn('flex_message', preview)
        self.assertIn('estimated_characters', preview)
        self.assertIsInstance(preview['estimated_characters'], int)
    
    def test_set_flex_message_enabled(self):
        """Flex Message使用フラグ設定テスト"""
        self.broadcaster.set_flex_message_enabled(False)
        self.assertFalse(self.broadcaster.use_flex_message)
        
        self.broadcaster.set_flex_message_enabled(True)
        self.assertTrue(self.broadcaster.use_flex_message)


class TestImageAssetManager(unittest.TestCase):
    """ImageAssetManagerのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.logger = Mock()
        self.config = Mock()
        self.config.project_root = tempfile.gettempdir()
        self.config.podcast.base_url = "https://example.com"
        
        self.asset_manager = ImageAssetManager(self.config, self.logger)
        
        self.sample_episode_info = {
            'published_at': datetime(2025, 8, 14, 9, 0, 0),
            'file_size_mb': 5.2,
            'article_count': 8
        }
    
    def test_cache_key_generation(self):
        """キャッシュキー生成テスト"""
        cache_key = self.asset_manager._generate_cache_key(
            self.sample_episode_info,
            'thumbnail'
        )
        
        self.assertIsInstance(cache_key, str)
        self.assertEqual(len(cache_key), 32)  # MD5ハッシュ
    
    def test_filename_hash_generation(self):
        """ファイル名ハッシュ生成テスト"""
        filename_hash = self.asset_manager._generate_filename_hash(self.sample_episode_info)
        
        self.assertIsInstance(filename_hash, str)
        self.assertEqual(len(filename_hash), 12)
    
    def test_fallback_image_url(self):
        """フォールバック画像URL取得テスト"""
        thumbnail_url = self.asset_manager._get_fallback_image('thumbnail')
        header_url = self.asset_manager._get_fallback_image('header')
        
        self.assertIn('default_thumbnail.png', thumbnail_url)
        self.assertIn('default_header.png', header_url)
    
    def test_cache_validation(self):
        """キャッシュ有効性確認テスト"""
        # 有効なキャッシュ
        valid_cache = {
            'expires_at': datetime.now().timestamp() + 3600  # 1時間後
        }
        self.assertTrue(self.asset_manager._is_cache_valid(valid_cache))
        
        # 期限切れキャッシュ
        expired_cache = {
            'expires_at': datetime.now().timestamp() - 3600  # 1時間前
        }
        self.assertFalse(self.asset_manager._is_cache_valid(expired_cache))
    
    def test_cache_stats(self):
        """キャッシュ統計取得テスト"""
        stats = self.asset_manager.get_cache_stats()
        
        self.assertIn('total_entries', stats)
        self.assertIn('valid_entries', stats)
        self.assertIn('expired_entries', stats)
        self.assertIn('cache_size_mb', stats)


class TestNotificationScheduler(unittest.TestCase):
    """NotificationSchedulerのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.logger = Mock()
        self.config = Mock()
        self.config.project_root = tempfile.gettempdir()
        
        self.scheduler = NotificationScheduler(self.config, self.logger)
        
        self.sample_episode_info = {
            'published_at': datetime(2025, 8, 14, 9, 0, 0),
            'file_size_mb': 5.2,
            'article_count': 8
        }
        
        self.sample_articles = [
            {
                'title': '日経平均株価が大幅上昇',
                'sentiment_label': 'Positive'
            }
        ]
    
    def test_schedule_podcast_notification(self):
        """ポッドキャスト通知スケジュール追加テスト"""
        notification_id = self.scheduler.schedule_podcast_notification(
            self.sample_episode_info,
            self.sample_articles,
            scheduled_time=datetime.now() + timedelta(hours=1),
            priority=NotificationPriority.NORMAL
        )
        
        self.assertIsInstance(notification_id, str)
        self.assertTrue(notification_id.startswith('notification_'))
        self.assertEqual(len(self.scheduler.notification_queue), 1)
    
    def test_optimal_time_calculation(self):
        """最適配信時刻計算テスト"""
        current_time = datetime(2025, 8, 14, 6, 0, 0)  # 朝6時
        
        # 緊急通知は即座に
        urgent_time = self.scheduler._calculate_optimal_time(NotificationPriority.URGENT)
        self.assertLess(urgent_time, current_time + timedelta(minutes=1))
        
        # 高優先度は次の最適時刻
        high_priority_time = self.scheduler._calculate_optimal_time(NotificationPriority.HIGH)
        self.assertGreater(high_priority_time, current_time)
        
        # 通常優先度は後回し
        normal_priority_time = self.scheduler._calculate_optimal_time(NotificationPriority.NORMAL)
        self.assertGreater(normal_priority_time, high_priority_time)
    
    def test_next_optimal_time(self):
        """次の最適時刻取得テスト"""
        # 早朝の場合
        early_morning = datetime(2025, 8, 14, 5, 0, 0)
        next_time = self.scheduler._get_next_optimal_time(early_morning)
        self.assertEqual(next_time.hour, 7)  # 最初の最適時刻は7時
        
        # 夜の場合は翌日
        late_night = datetime(2025, 8, 14, 23, 0, 0)
        next_time = self.scheduler._get_next_optimal_time(late_night)
        self.assertEqual(next_time.day, 15)  # 翌日
    
    def test_sentiment_analysis(self):
        """センチメント分析テスト"""
        articles = [
            {'sentiment_label': 'Positive'},
            {'sentiment_label': 'Positive'},
            {'sentiment_label': 'Negative'},
            {'sentiment_label': 'Neutral'}
        ]
        
        distribution = self.scheduler._analyze_sentiment_distribution(articles)
        
        self.assertEqual(distribution['Positive'], 2)
        self.assertEqual(distribution['Negative'], 1)
        self.assertEqual(distribution['Neutral'], 1)
    
    def test_rate_limit_check(self):
        """レート制限チェックテスト"""
        # 初期状態では送信可能
        self.assertTrue(self.scheduler._check_rate_limit())
        
        # 制限値まで更新
        current_hour = datetime.now().hour
        self.scheduler.rate_limit_counter[current_hour] = self.scheduler.rate_limit_per_hour
        
        # 制限値に達したら送信不可
        self.assertFalse(self.scheduler._check_rate_limit())
    
    def test_notification_id_generation(self):
        """通知ID生成テスト"""
        notification_id = self.scheduler._generate_notification_id()
        
        self.assertIsInstance(notification_id, str)
        self.assertTrue(notification_id.startswith('notification_'))
        self.assertGreater(len(notification_id), 20)
    
    def test_notification_cancellation(self):
        """通知キャンセルテスト"""
        # 通知追加
        notification_id = self.scheduler.schedule_podcast_notification(
            self.sample_episode_info,
            self.sample_articles,
            scheduled_time=datetime.now() + timedelta(hours=1)
        )
        
        # キャンセル実行
        result = self.scheduler.cancel_notification(notification_id)
        self.assertTrue(result)
        
        # ステータス確認
        notification = self.scheduler.get_notification_status(notification_id)
        self.assertEqual(notification['status'], 'cancelled')
    
    def test_schedule_stats(self):
        """スケジュール統計取得テスト"""
        # 通知を追加
        self.scheduler.schedule_podcast_notification(
            self.sample_episode_info,
            self.sample_articles,
            priority=NotificationPriority.HIGH
        )
        
        stats = self.scheduler.get_schedule_stats()
        
        self.assertIn('total_notifications', stats)
        self.assertIn('status_distribution', stats)
        self.assertIn('priority_distribution', stats)
        self.assertIn('rate_limit_usage', stats)
        self.assertIn('scheduler_running', stats)
        
        self.assertEqual(stats['total_notifications'], 1)
        self.assertIn('high', stats['priority_distribution'])


if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)