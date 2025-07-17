# -*- coding: utf-8 -*-

"""
HTMLGeneratorのユニットテスト
"""

import unittest
from unittest.mock import Mock, patch, mock_open
import tempfile
import os
from datetime import datetime

from src.html.html_generator import HTMLGenerator
from src.html.template_engine import TemplateData
from src.error_handling import HTMLGenerationError


class TestHTMLGenerator(unittest.TestCase):
    """HTMLGeneratorのテストクラス"""
    
    def setUp(self):
        """テストの準備"""
        self.generator = HTMLGenerator()
        self.sample_articles = [
            {
                'title': 'Test Article 1',
                'url': 'https://example.com/article1',
                'summary': 'This is a test summary.',
                'source': 'Reuters',
                'published_jst': datetime(2025, 1, 1, 12, 0, 0),
                'sentiment_label': 'Positive',
                'sentiment_score': 0.8
            },
            {
                'title': 'Test Article 2',
                'url': 'https://example.com/article2',
                'summary': 'This is another test summary.',
                'source': 'Bloomberg',
                'published_jst': datetime(2025, 1, 1, 13, 0, 0),
                'sentiment_label': 'Negative',
                'sentiment_score': 0.7
            }
        ]
    
    def test_init(self):
        """初期化テスト"""
        self.assertIsNotNone(self.generator.logger)
        self.assertIsNotNone(self.generator.template_engine)
    
    def test_calculate_statistics(self):
        """統計計算テスト"""
        stats = self.generator._calculate_statistics(self.sample_articles)
        
        # ソース統計
        self.assertEqual(stats['source']['Reuters'], 1)
        self.assertEqual(stats['source']['Bloomberg'], 1)
        
        # 感情統計
        self.assertEqual(stats['sentiment']['Positive'], 1)
        self.assertEqual(stats['sentiment']['Negative'], 1)
        self.assertEqual(stats['sentiment']['Neutral'], 0)
        self.assertEqual(stats['sentiment']['Error'], 0)
    
    def test_calculate_statistics_empty(self):
        """統計計算（空のリスト）テスト"""
        stats = self.generator._calculate_statistics([])
        
        self.assertEqual(stats['source'], {})
        self.assertEqual(stats['sentiment']['Positive'], 0)
        self.assertEqual(stats['sentiment']['Negative'], 0)
        self.assertEqual(stats['sentiment']['Neutral'], 0)
        self.assertEqual(stats['sentiment']['Error'], 0)
    
    def test_calculate_last_updated(self):
        """最終更新時刻計算テスト"""
        last_updated = self.generator._calculate_last_updated(self.sample_articles)
        self.assertEqual(last_updated, '2025-01-01 13:00')
    
    def test_calculate_last_updated_empty(self):
        """最終更新時刻計算（空のリスト）テスト"""
        last_updated = self.generator._calculate_last_updated([])
        self.assertEqual(last_updated, 'N/A')
    
    def test_calculate_last_updated_no_date(self):
        """最終更新時刻計算（日付なし）テスト"""
        articles = [{'title': 'Test', 'published_jst': None}]
        last_updated = self.generator._calculate_last_updated(articles)
        self.assertEqual(last_updated, 'N/A')
    
    @patch('builtins.open', new_callable=mock_open)
    def test_write_html_file_success(self, mock_file):
        """HTMLファイル書き込み成功テスト"""
        content = '<html><body>Test</body></html>'
        self.generator._write_html_file(content, 'test.html')
        
        mock_file.assert_called_once_with('test.html', 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with(content)
    
    @patch('builtins.open', side_effect=IOError("File write error"))
    def test_write_html_file_failure(self, mock_file):
        """HTMLファイル書き込み失敗テスト"""
        content = '<html><body>Test</body></html>'
        
        with self.assertRaises(HTMLGenerationError):
            self.generator._write_html_file(content, 'test.html')
    
    def test_validate_articles_success(self):
        """記事検証成功テスト"""
        errors = self.generator.validate_articles(self.sample_articles)
        self.assertEqual(len(errors), 0)
    
    def test_validate_articles_missing_fields(self):
        """記事検証（必須フィールド不足）テスト"""
        invalid_articles = [
            {'title': 'Test Article'},  # url, summary不足
            {'url': 'https://example.com', 'summary': 'Test'},  # title不足
        ]
        
        errors = self.generator.validate_articles(invalid_articles)
        self.assertGreater(len(errors), 0)
        self.assertIn('url が不足しています', errors[0])
        self.assertIn('summary が不足しています', errors[0])
        self.assertIn('title が不足しています', errors[1])
    
    def test_validate_articles_invalid_url(self):
        """記事検証（不正URL）テスト"""
        invalid_articles = [
            {
                'title': 'Test Article',
                'url': 'invalid-url',
                'summary': 'Test summary'
            }
        ]
        
        errors = self.generator.validate_articles(invalid_articles)
        self.assertGreater(len(errors), 0)
        self.assertIn('不正なURL形式', errors[0])
    
    def test_validate_articles_not_dict(self):
        """記事検証（辞書形式でない）テスト"""
        invalid_articles = ['not a dict', 123, None]
        
        errors = self.generator.validate_articles(invalid_articles)
        self.assertEqual(len(errors), 3)
        for error in errors:
            self.assertIn('辞書形式ではありません', error)
    
    @patch.object(HTMLGenerator, '_write_html_file')
    @patch.object(HTMLGenerator, '_calculate_statistics')
    @patch.object(HTMLGenerator, '_calculate_last_updated')
    def test_generate_html_file_success(self, mock_last_updated, mock_statistics, mock_write):
        """HTMLファイル生成成功テスト"""
        # モックの設定
        mock_statistics.return_value = {
            'source': {'Reuters': 1, 'Bloomberg': 1},
            'sentiment': {'Positive': 1, 'Negative': 1, 'Neutral': 0, 'Error': 0}
        }
        mock_last_updated.return_value = '2025-01-01 13:00'
        
        # テスト実行
        self.generator.generate_html_file(self.sample_articles, 'test.html', 'Test Title')
        
        # 検証
        mock_statistics.assert_called_once_with(self.sample_articles)
        mock_last_updated.assert_called_once_with(self.sample_articles)
        mock_write.assert_called_once()
    
    @patch.object(HTMLGenerator, '_write_html_file', side_effect=HTMLGenerationError("Write error"))
    def test_generate_html_file_failure(self, mock_write):
        """HTMLファイル生成失敗テスト"""
        with self.assertRaises(HTMLGenerationError):
            self.generator.generate_html_file(self.sample_articles, 'test.html')
    
    def test_integration_with_real_file(self):
        """実ファイルとの統合テスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # HTML生成
            self.generator.generate_html_file(self.sample_articles, temp_path)
            
            # ファイルが生成されたか確認
            self.assertTrue(os.path.exists(temp_path))
            
            # ファイル内容の確認
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('<!DOCTYPE html>', content)
                self.assertIn('Test Article 1', content)
                self.assertIn('Test Article 2', content)
                self.assertIn('Reuters', content)
                self.assertIn('Bloomberg', content)
        
        finally:
            # テンポラリファイルの削除
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()