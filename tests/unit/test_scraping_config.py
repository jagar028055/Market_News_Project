# -*- coding: utf-8 -*-

"""
ScrapingConfig拡張のユニットテスト
"""

import unittest
from src.config.app_config import ScrapingConfig


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


if __name__ == '__main__':
    unittest.main()