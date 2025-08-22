# -*- coding: utf-8 -*-

"""
NewsProcessorのユニットテスト
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import os

from src.core.news_processor import NewsProcessor
from src.config import AppConfig


class TestNewsProcessor(unittest.TestCase):
    """NewsProcessorのテストクラス"""
    
    def setUp(self):
        """テストの準備"""
        self.processor = NewsProcessor()
        self.sample_articles = [
            {
                'title': 'Test Article 1',
                'url': 'https://example.com/article1',
                'body': 'This is a test article body.',
                'published_jst': datetime(2025, 1, 1, 12, 0, 0),
                'source': 'Reuters',
                'sentiment_label': 'Positive',
                'sentiment_score': 0.8
            },
            {
                'title': 'Test Article 2',
                'url': 'https://example.com/article2',
                'body': 'This is another test article body.',
                'published_jst': datetime(2025, 1, 1, 13, 0, 0),
                'source': 'Bloomberg',
                'sentiment_label': 'Negative',
                'sentiment_score': 0.7
            }
        ]
    
    def test_init(self):
        """初期化テスト"""
        self.assertIsNotNone(self.processor.logger)
        self.assertIsNotNone(self.processor.config)
        self.assertIsInstance(self.processor.config, AppConfig)
    
    @patch.dict(os.environ, {'GOOGLE_DRIVE_OUTPUT_FOLDER_ID': 'test_folder', 'AI_GEMINI_API_KEY': 'test_key'})
    def test_validate_environment_success(self):
        """環境変数検証成功テスト"""
        processor = NewsProcessor()
        result = processor.validate_environment()
        self.assertTrue(result)
    
    @patch.dict(os.environ, {'GOOGLE_DRIVE_OUTPUT_FOLDER_ID': '', 'AI_GEMINI_API_KEY': ''})
    def test_validate_environment_failure(self):
        """環境変数検証失敗テスト"""
        processor = NewsProcessor()
        result = processor.validate_environment()
        self.assertFalse(result)
    
    @patch('src.core.news_processor.reuters')
    @patch('src.core.news_processor.bloomberg')
    def test_collect_articles_success(self, mock_bloomberg, mock_reuters):
        """記事収集成功テスト"""
        # モックの設定
        mock_reuters.scrape_reuters_articles.return_value = [self.sample_articles[0]]
        mock_bloomberg.scrape_bloomberg_top_page_articles.return_value = [self.sample_articles[1]]
        
        # テスト実行
        articles = self.processor.collect_articles()
        
        # 検証
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]['title'], 'Test Article 2')  # 新しい記事が先頭
        self.assertEqual(articles[1]['title'], 'Test Article 1')
    
    @patch('src.core.news_processor.reuters')
    @patch('src.core.news_processor.bloomberg')
    def test_collect_articles_with_error(self, mock_bloomberg, mock_reuters):
        """記事収集エラーテスト"""
        # モックの設定（エラーを発生させる）
        mock_reuters.scrape_reuters_articles.side_effect = Exception("Reuters Error")
        mock_bloomberg.scrape_bloomberg_top_page_articles.return_value = [self.sample_articles[1]]
        
        # テスト実行
        articles = self.processor.collect_articles()
        
        # 検証（エラーが発生してもBloombergの記事は取得される）
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]['title'], 'Test Article 2')
    
    @patch('src.core.news_processor.process_article_with_ai')
    def test_process_articles_with_ai_success(self, mock_process_ai):
        """AI処理成功テスト"""
        # モックの設定
        mock_process_ai.return_value = {
            'summary': 'AI generated summary',
            'sentiment_label': 'Positive',
            'sentiment_score': 0.9
        }
        
        # テスト実行
        processed_articles = self.processor.process_articles_with_ai(self.sample_articles)
        
        # 検証
        self.assertEqual(len(processed_articles), 2)
        self.assertEqual(processed_articles[0]['summary'], 'AI generated summary')
        self.assertEqual(processed_articles[0]['sentiment_label'], 'Positive')
        self.assertEqual(processed_articles[0]['sentiment_score'], 0.9)
    
    @patch('src.core.news_processor.process_article_with_ai')
    def test_process_articles_with_ai_failure(self, mock_process_ai):
        """AI処理失敗テスト"""
        # モックの設定（エラーを発生させる）
        mock_process_ai.side_effect = Exception("AI Processing Error")
        
        # テスト実行
        processed_articles = self.processor.process_articles_with_ai(self.sample_articles)
        
        # 検証
        self.assertEqual(len(processed_articles), 2)
        self.assertEqual(processed_articles[0]['summary'], 'AI処理中にエラーが発生しました。')
        self.assertEqual(processed_articles[0]['sentiment_label'], 'Error')
        self.assertEqual(processed_articles[0]['sentiment_score'], 0.0)
    
    @patch('src.core.news_processor.process_article_with_ai')
    def test_process_articles_with_ai_none_result(self, mock_process_ai):
        """AI処理結果None テスト"""
        # モックの設定
        mock_process_ai.return_value = None
        
        # テスト実行
        processed_articles = self.processor.process_articles_with_ai(self.sample_articles)
        
        # 検証
        self.assertEqual(len(processed_articles), 2)
        self.assertEqual(processed_articles[0]['summary'], 'AI処理に失敗しました。')
        self.assertEqual(processed_articles[0]['sentiment_label'], 'N/A')
        self.assertEqual(processed_articles[0]['sentiment_score'], 0.0)
    
    @patch('src.core.news_processor.HTMLGenerator')
    def test_generate_html_output_success(self, mock_html_generator):
        """HTML生成成功テスト"""
        # モックの設定
        mock_generator_instance = Mock()
        mock_html_generator.return_value = mock_generator_instance
        
        # テスト実行
        self.processor.generate_html_output(self.sample_articles)
        
        # 検証
        mock_html_generator.assert_called_once_with(self.processor.logger)
        mock_generator_instance.generate_html_file.assert_called_once_with(self.sample_articles, "index.html")
    
    @patch('src.core.news_processor.HTMLGenerator')
    def test_generate_html_output_failure(self, mock_html_generator):
        """HTML生成失敗テスト"""
        # モックの設定
        mock_generator_instance = Mock()
        mock_generator_instance.generate_html_file.side_effect = Exception("HTML Generation Error")
        mock_html_generator.return_value = mock_generator_instance
        
        # テスト実行・検証
        with self.assertRaises(Exception):
            self.processor.generate_html_output(self.sample_articles)
    
    def test_set_fallback_ai_result(self):
        """フォールバック設定テスト"""
        article = {'title': 'Test Article'}
        self.processor._set_fallback_ai_result(article)
        
        self.assertEqual(article['summary'], 'AI処理に失敗しました。')
        self.assertEqual(article['sentiment_label'], 'N/A')
        self.assertEqual(article['sentiment_score'], 0.0)
    
    def test_set_error_ai_result(self):
        """エラー設定テスト"""
        article = {'title': 'Test Article'}
        self.processor._set_error_ai_result(article)
        
        self.assertEqual(article['summary'], 'AI処理中にエラーが発生しました。')
        self.assertEqual(article['sentiment_label'], 'Error')
        self.assertEqual(article['sentiment_score'], 0.0)
    
    @patch.object(NewsProcessor, 'validate_environment')
    @patch.object(NewsProcessor, 'collect_articles')
    @patch.object(NewsProcessor, 'process_articles_with_ai')
    @patch.object(NewsProcessor, 'generate_html_output')
    @patch.object(NewsProcessor, 'process_google_docs_output')
    def test_run_success(self, mock_google_docs, mock_html, mock_ai, mock_collect, mock_validate):
        """メイン実行成功テスト"""
        # モックの設定
        mock_validate.return_value = True
        mock_collect.return_value = self.sample_articles
        mock_ai.return_value = self.sample_articles
        
        # テスト実行
        self.processor.run()
        
        # 検証
        mock_validate.assert_called_once()
        mock_collect.assert_called_once()
        mock_ai.assert_called_once_with(self.sample_articles)
        mock_html.assert_called_once_with(self.sample_articles)
        mock_google_docs.assert_called_once_with(self.sample_articles)
    
    @patch.object(NewsProcessor, 'validate_environment')
    def test_run_validation_failure(self, mock_validate):
        """メイン実行（環境変数検証失敗）テスト"""
        # モックの設定
        mock_validate.return_value = False
        
        # テスト実行
        self.processor.run()
        
        # 検証
        mock_validate.assert_called_once()
    
    @patch.object(NewsProcessor, 'validate_environment')
    @patch.object(NewsProcessor, 'collect_articles')
    def test_run_no_articles(self, mock_collect, mock_validate):
        """メイン実行（記事なし）テスト"""
        # モックの設定
        mock_validate.return_value = True
        mock_collect.return_value = []
        
        # テスト実行
        self.processor.run()
        
        # 検証
        mock_validate.assert_called_once()
        mock_collect.assert_called_once()


if __name__ == '__main__':
    unittest.main()