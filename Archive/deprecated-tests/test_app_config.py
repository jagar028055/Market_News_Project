# -*- coding: utf-8 -*-

"""
AppConfigのユニットテスト
"""

import unittest
from unittest.mock import patch
import os

from src.config.app_config import (
    AppConfig,
    ScrapingConfig,
    ReutersConfig,
    BloombergConfig,
    AIConfig,
    GoogleConfig,
    DatabaseConfig,
    LoggingConfig,
    get_config,
    reload_config
)


class TestAppConfig(unittest.TestCase):
    """AppConfigのテストクラス"""
    
    def setUp(self):
        """テストの準備"""
        # シングルトンインスタンスをリセット
        import src.config.app_config
        src.config.app_config._config_instance = None
    
    def test_scraping_config_defaults(self):
        """ScrapingConfigのデフォルト値テスト"""
        config = ScrapingConfig()
        self.assertEqual(config.hours_limit, 24)
        self.assertTrue(config.sentiment_analysis_enabled)
    
    def test_reuters_config_defaults(self):
        """ReutersConfigのデフォルト値テスト"""
        config = ReutersConfig()
        self.assertIn("米 OR 金融", config.query)
        self.assertEqual(config.max_pages, 5)
        self.assertEqual(config.items_per_page, 20)
        self.assertIn("ビジネスcategory", config.target_categories)
        self.assertIn("スポーツ", config.exclude_keywords)
    
    def test_bloomberg_config_defaults(self):
        """BloombergConfigのデフォルト値テスト"""
        config = BloombergConfig()
        self.assertIn("動画", config.exclude_keywords)
        self.assertIn("ポッドキャスト", config.exclude_keywords)
    
    def test_ai_config_defaults(self):
        """AIConfigのデフォルト値テスト"""
        config = AIConfig()
        self.assertEqual(config.gemini_api_key, "")
        self.assertEqual(config.model_name, "gemini-2.0-flash-lite-001")
        self.assertEqual(config.max_output_tokens, 1024)
        self.assertEqual(config.temperature, 0.2)
        self.assertIn("あなたは優秀なニュース編集者", config.process_prompt_template)
    
    def test_google_config_defaults(self):
        """GoogleConfigのデフォルト値テスト"""
        config = GoogleConfig()
        self.assertEqual(config.drive_output_folder_id, "")
        self.assertIsNone(config.overwrite_doc_id)
        self.assertEqual(config.service_account_json, "")
    
    def test_database_config_defaults(self):
        """DatabaseConfigのデフォルト値テスト"""
        config = DatabaseConfig()
        self.assertEqual(config.url, "sqlite:///market_news.db")
        self.assertFalse(config.echo)
    
    def test_logging_config_defaults(self):
        """LoggingConfigのデフォルト値テスト"""
        config = LoggingConfig()
        self.assertEqual(config.level, "INFO")
        self.assertEqual(config.format, "json")
        self.assertTrue(config.file_enabled)
        self.assertEqual(config.file_path, "logs/market_news.log")
        self.assertEqual(config.max_file_size, 10*1024*1024)
        self.assertEqual(config.backup_count, 5)
    
    @patch.dict(os.environ, {
        'AI_GEMINI_API_KEY': 'test_gemini_key',
        'GOOGLE_DRIVE_OUTPUT_FOLDER_ID': 'test_folder_id',
        'GOOGLE_SERVICE_ACCOUNT_JSON': '{"test": "json"}',
        'SCRAPING_HOURS_LIMIT': '48',
        'LOGGING_LEVEL': 'DEBUG'
    })
    def test_app_config_environment_variables(self):
        """AppConfigの環境変数読み込みテスト"""
        config = AppConfig()
        
        # 環境変数が正しく読み込まれているか確認
        self.assertEqual(config.ai.gemini_api_key, 'test_gemini_key')
        self.assertEqual(config.google.drive_output_folder_id, 'test_folder_id')
        self.assertEqual(config.google.service_account_json, '{"test": "json"}')
        self.assertEqual(config.scraping.hours_limit, 48)
        self.assertEqual(config.logging.level, 'DEBUG')
    
    def test_app_config_defaults(self):
        """AppConfigのデフォルト値テスト"""
        config = AppConfig()
        
        # サブ設定のインスタンスが作成されているか確認
        self.assertIsInstance(config.scraping, ScrapingConfig)
        self.assertIsInstance(config.reuters, ReutersConfig)
        self.assertIsInstance(config.bloomberg, BloombergConfig)
        self.assertIsInstance(config.ai, AIConfig)
        self.assertIsInstance(config.google, GoogleConfig)
        self.assertIsInstance(config.database, DatabaseConfig)
        self.assertIsInstance(config.logging, LoggingConfig)
    
    def test_to_legacy_format(self):
        """レガシーフォーマット変換テスト"""
        config = AppConfig()
        legacy_format = config.to_legacy_format()
        
        # 必要なキーが存在するか確認
        self.assertIn('HOURS_LIMIT', legacy_format)
        self.assertIn('SENTIMENT_ANALYSIS_ENABLED', legacy_format)
        self.assertIn('AI_PROCESS_PROMPT_TEMPLATE', legacy_format)
        self.assertIn('GOOGLE_OVERWRITE_DOC_ID', legacy_format)
        self.assertIn('REUTERS_CONFIG', legacy_format)
        self.assertIn('BLOOMBERG_CONFIG', legacy_format)
        
        # 値が正しく変換されているか確認
        self.assertEqual(legacy_format['HOURS_LIMIT'], config.scraping.hours_limit)
        self.assertEqual(legacy_format['SENTIMENT_ANALYSIS_ENABLED'], config.scraping.sentiment_analysis_enabled)
        self.assertEqual(legacy_format['AI_PROCESS_PROMPT_TEMPLATE'], config.ai.process_prompt_template)
        self.assertEqual(legacy_format['GOOGLE_OVERWRITE_DOC_ID'], config.google.overwrite_doc_id)
        
        # ネストされた設定が正しく変換されているか確認
        self.assertEqual(legacy_format['REUTERS_CONFIG']['query'], config.reuters.query)
        self.assertEqual(legacy_format['BLOOMBERG_CONFIG']['exclude_keywords'], config.bloomberg.exclude_keywords)
    
    def test_get_config_singleton(self):
        """get_configのシングルトンテスト"""
        config1 = get_config()
        config2 = get_config()
        
        # 同じインスタンスが返されるか確認
        self.assertIs(config1, config2)
        self.assertIsInstance(config1, AppConfig)
    
    def test_reload_config(self):
        """reload_configテスト"""
        # 最初のインスタンスを取得
        config1 = get_config()
        
        # 設定を変更
        config1.scraping.hours_limit = 99
        
        # 設定を再読み込み
        config2 = reload_config()
        
        # 新しいインスタンスが作成されているか確認
        self.assertIsNot(config1, config2)
        self.assertEqual(config2.scraping.hours_limit, 24)  # デフォルト値に戻っている
    
    @patch.dict(os.environ, {}, clear=True)
    def test_app_config_missing_environment_variables(self):
        """AppConfigの環境変数なしテスト"""
        config = AppConfig()
        
        # 環境変数がない場合のデフォルト値
        self.assertEqual(config.ai.gemini_api_key, '')
        self.assertEqual(config.google.drive_output_folder_id, '')
        self.assertEqual(config.google.service_account_json, '')
        self.assertEqual(config.scraping.hours_limit, 24)
        self.assertEqual(config.logging.level, 'INFO')
    
    def test_app_config_invalid_environment_variables(self):
        """AppConfigの無効な環境変数テスト"""
        with patch.dict(os.environ, {'SCRAPING_HOURS_LIMIT': 'invalid_number'}):
            # 無効な値の場合、例外が発生するかデフォルト値が使用される
            with self.assertRaises(ValueError):
                AppConfig()
    
    def test_nested_config_modification(self):
        """ネストされた設定の変更テスト"""
        config = AppConfig()
        
        # ネストされた設定を変更
        config.scraping.hours_limit = 48
        config.reuters.max_pages = 10
        config.ai.temperature = 0.5
        
        # 値が正しく変更されているか確認
        self.assertEqual(config.scraping.hours_limit, 48)
        self.assertEqual(config.reuters.max_pages, 10)
        self.assertEqual(config.ai.temperature, 0.5)
        
        # レガシーフォーマットにも反映されているか確認
        legacy_format = config.to_legacy_format()
        self.assertEqual(legacy_format['HOURS_LIMIT'], 48)
        self.assertEqual(legacy_format['REUTERS_CONFIG']['max_pages'], 10)


if __name__ == '__main__':
    unittest.main()