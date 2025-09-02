# -*- coding: utf-8 -*-

"""
動的記事取得機能のユニットテスト
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pytz
from src.core.news_processor import NewsProcessor
from src.config.app_config import AppConfig, ScrapingConfig


class TestDynamicArticleCollection(unittest.TestCase):
    """動的記事取得機能のテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.processor = NewsProcessor()
        self.processor.logger = Mock()
        
        # テスト用設定
        self.processor.config.scraping = ScrapingConfig(
            hours_limit=24,
            minimum_article_count=100,
            max_hours_limit=72,
            weekend_hours_extension=48
        )
    
    def test_get_dynamic_hours_limit_monday(self):
        """月曜日のテスト: 自動的に最大時間範囲を返す"""
        with patch('src.core.news_processor.datetime') as mock_datetime, \
             patch('src.core.news_processor.pytz') as mock_pytz:
            
            # 月曜日のモック設定
            mock_jst_now = Mock()
            mock_jst_now.weekday.return_value = 0  # Monday
            mock_pytz.timezone.return_value.localize.return_value = mock_jst_now
            mock_datetime.now.return_value = mock_jst_now
            
            result = self.processor.get_dynamic_hours_limit()
            
            self.assertEqual(result, 72)  # max_hours_limit
            self.processor.logger.info.assert_called_with(
                "月曜日検出: 自動的に72時間範囲を適用"
            )
    
    def test_get_dynamic_hours_limit_weekday(self):
        """平日（火-金）のテスト: 基本時間範囲を返す"""
        with patch('src.core.news_processor.datetime') as mock_datetime, \
             patch('src.core.news_processor.pytz') as mock_pytz:
            
            # 火曜日のモック設定
            mock_jst_now = Mock()
            mock_jst_now.weekday.return_value = 1  # Tuesday
            mock_pytz.timezone.return_value.localize.return_value = mock_jst_now
            mock_datetime.now.return_value = mock_jst_now
            
            result = self.processor.get_dynamic_hours_limit()
            
            self.assertEqual(result, 24)  # hours_limit
    
    @patch('src.core.news_processor.NewsProcessor._collect_articles_with_hours')
    def test_collect_articles_with_dynamic_range_sufficient_articles(self, mock_collect):
        """十分な記事数の場合のテスト"""
        # 十分な記事数をモック
        mock_articles = [{'title': f'Article {i}'} for i in range(120)]
        mock_collect.return_value = mock_articles
        
        with patch.object(self.processor, 'get_dynamic_hours_limit', return_value=24):
            result = self.processor.collect_articles_with_dynamic_range()
            
            self.assertEqual(len(result), 120)
            mock_collect.assert_called_once_with(24)
            self.processor.logger.info.assert_any_call("✅ 成功: 最低記事数(100件)を満たしました")
    
    @patch('src.core.news_processor.NewsProcessor._collect_articles_with_hours')
    def test_collect_articles_with_dynamic_range_insufficient_articles(self, mock_collect):
        """記事数不足の場合の時間範囲拡張テスト"""
        # 最初は少ない記事数、次に十分な記事数
        mock_collect.side_effect = [
            [{'title': f'Article {i}'} for i in range(50)],  # 50件（不足）
            [{'title': f'Article {i}'} for i in range(120)]  # 120件（十分）
        ]
        
        with patch.object(self.processor, 'get_dynamic_hours_limit', return_value=24):
            result = self.processor.collect_articles_with_dynamic_range()
            
            self.assertEqual(len(result), 120)
            self.assertEqual(mock_collect.call_count, 2)
            mock_collect.assert_any_call(24)  # 最初の呼び出し
            mock_collect.assert_any_call(48)  # 拡張後の呼び出し
            
            self.processor.logger.info.assert_any_call(
                "📈 記事数不足 → 時間範囲拡張: 24時間 → 48時間"
            )
    
    @patch('src.core.news_processor.NewsProcessor._collect_articles_with_hours')
    def test_collect_articles_with_dynamic_range_max_limit_reached(self, mock_collect):
        """最大時間範囲に到達する場合のテスト"""
        # 常に記事数不足
        mock_articles = [{'title': f'Article {i}'} for i in range(30)]
        mock_collect.return_value = mock_articles
        
        with patch.object(self.processor, 'get_dynamic_hours_limit', return_value=24):
            result = self.processor.collect_articles_with_dynamic_range()
            
            self.assertEqual(len(result), 30)
            # 24h → 48h → 72h の3回呼び出し
            self.assertEqual(mock_collect.call_count, 3)
            mock_collect.assert_any_call(72)  # 最終的に最大値
            
            self.processor.logger.warning.assert_any_call(
                "⚠️  最大時間範囲(72時間)に到達"
            )
            self.processor.logger.warning.assert_any_call(
                "   最終記事数: 30件 (目標: 100件)"
            )
    
    @patch('scrapers.reuters.scrape_reuters_articles')
    @patch('scrapers.bloomberg.scrape_bloomberg_top_page_articles')
    def test_collect_articles_with_hours(self, mock_bloomberg, mock_reuters):
        """指定時間範囲での記事収集テスト"""
        # モック記事を設定
        mock_reuters_articles = [
            {'title': 'Reuters 1', 'published_jst': datetime.now()},
            {'title': 'Reuters 2', 'published_jst': datetime.now() - timedelta(hours=1)}
        ]
        mock_bloomberg_articles = [
            {'title': 'Bloomberg 1', 'published_jst': datetime.now() - timedelta(hours=2)}
        ]
        
        mock_reuters.return_value = mock_reuters_articles
        mock_bloomberg.return_value = mock_bloomberg_articles
        
        result = self.processor._collect_articles_with_hours(48)
        
        self.assertEqual(len(result), 3)
        
        # スクレイパーが正しい引数で呼ばれたかチェック
        mock_reuters.assert_called_once_with(
            query=self.processor.config.reuters.query,
            hours_limit=48,
            max_pages=self.processor.config.reuters.max_pages,
            items_per_page=self.processor.config.reuters.items_per_page,
            target_categories=self.processor.config.reuters.target_categories,
            exclude_keywords=self.processor.config.reuters.exclude_keywords
        )
        
        mock_bloomberg.assert_called_once_with(
            hours_limit=48,
            exclude_keywords=self.processor.config.bloomberg.exclude_keywords
        )
        
        # ログ出力の確認は、log_with_contextのモックが複雑なため、このテストでは省略する
    
    @patch('src.core.news_processor.log_with_context')
    @patch('scrapers.reuters.scrape_reuters_articles')
    @patch('scrapers.bloomberg.scrape_bloomberg_top_page_articles')
    def test_collect_articles_with_hours_error_handling(self, mock_bloomberg, mock_reuters, mock_log):
        """記事収集エラーハンドリングのテスト"""
        import logging
        # ロイターでエラー発生
        mock_reuters.side_effect = Exception("Reuters Error")
        mock_bloomberg.return_value = [{'title': 'Bloomberg 1'}]
        
        result = self.processor._collect_articles_with_hours(24)
        
        self.assertEqual(len(result), 1)  # Bloombergの記事のみ

        # log_with_contextがエラー情報とともに呼ばれたことを確認
        mock_log.assert_any_call(
            self.processor.logger,
            logging.ERROR,
            "Reuters 記事取得エラー",
            operation="collect_articles",
            scraper="Reuters",
            error="Reuters Error",
            exc_info=True
        )
    
    def test_integration_collect_articles(self):
        """collect_articlesメソッドの統合テスト"""
        with patch.object(self.processor, 'collect_articles_with_dynamic_range') as mock_dynamic:
            mock_dynamic.return_value = [{'title': 'Test Article'}]
            
            result = self.processor.collect_articles()
            
            self.assertEqual(len(result), 1)
            mock_dynamic.assert_called_once()


class TestScrapingConfigExtension(unittest.TestCase):
    """ScrapingConfig拡張のテスト"""
    
    def test_scraping_config_defaults(self):
        """デフォルト値のテスト"""
        config = ScrapingConfig()
        
        self.assertEqual(config.hours_limit, 24)
        self.assertEqual(config.minimum_article_count, 100)
        self.assertEqual(config.max_hours_limit, 72)
        self.assertEqual(config.weekend_hours_extension, 48)
    
    def test_scraping_config_custom_values(self):
        """カスタム値のテスト"""
        config = ScrapingConfig(
            hours_limit=12,
            minimum_article_count=50,
            max_hours_limit=96,
            weekend_hours_extension=60
        )
        
        self.assertEqual(config.hours_limit, 12)
        self.assertEqual(config.minimum_article_count, 50)
        self.assertEqual(config.max_hours_limit, 96)
        self.assertEqual(config.weekend_hours_extension, 60)
    
    @patch.dict('os.environ', {
        'SCRAPING_MINIMUM_ARTICLE_COUNT': '150',
        'SCRAPING_MAX_HOURS_LIMIT': '96',
        'SCRAPING_WEEKEND_HOURS_EXTENSION': '60'
    })
    def test_app_config_environment_override(self):
        """環境変数でのオーバーライドテスト"""
        config = AppConfig()
        
        self.assertEqual(config.scraping.minimum_article_count, 150)
        self.assertEqual(config.scraping.max_hours_limit, 96)
        self.assertEqual(config.scraping.weekend_hours_extension, 60)


if __name__ == '__main__':
    unittest.main()