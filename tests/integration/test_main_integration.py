# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path

from main import main
from src.core.news_processor import NewsProcessor


class TestMainIntegration:
    """メイン処理の統合テスト"""
    
    @patch('src.core.news_processor.authenticate_google_services')
    @patch('src.core.news_processor.test_drive_connection')
    @patch('scrapers.reuters.scrape_reuters_articles')
    @patch('scrapers.bloomberg.scrape_bloomberg_top_page_articles')
    @patch('ai_summarizer.process_article_with_ai')
    @patch('src.html.html_generator.HTMLGenerator.generate_html_file')
    @patch('src.core.news_processor.update_google_doc_with_full_text')
    @patch('src.core.news_processor.create_daily_summary_doc')
    def test_main_success_flow(
        self,
        mock_create_daily,
        mock_update_doc,
        mock_create_html,
        mock_process_ai,
        mock_bloomberg,
        mock_reuters,
        mock_test_drive,
        mock_auth
    ):
        """メイン処理成功フローテスト"""
        
        # モック設定
        mock_drive = MagicMock()
        mock_docs = MagicMock()
        mock_auth.return_value = (mock_drive, mock_docs)
        mock_test_drive.return_value = True
        
        # スクレイピング結果のモック
        mock_reuters_articles = [
            {
                'title': 'ロイター記事1',
                'url': 'https://reuters.com/article1',
                'body': 'ロイター記事の本文',
                'source': 'Reuters',
                'published_jst': None
            }
        ]
        mock_bloomberg_articles = [
            {
                'title': 'Bloomberg記事1',
                'url': 'https://bloomberg.com/article1',
                'body': 'Bloomberg記事の本文',
                'source': 'Bloomberg',
                'published_jst': None
            }
        ]
        
        mock_reuters.return_value = mock_reuters_articles
        mock_bloomberg.return_value = mock_bloomberg_articles
        
        # AI処理結果のモック
        mock_process_ai.return_value = {
            'summary': 'テスト要約',
            'sentiment_label': 'Positive',
            'sentiment_score': 0.8
        }
        
        mock_update_doc.return_value = True
        mock_create_daily.return_value = True
        
        # NewsProcessorを直接テスト
        with patch('src.config.app_config.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.google.is_document_creation_day_and_time.return_value = True
            mock_config.google.overwrite_doc_id = "test_doc_id"
            mock_config.google.drive_output_folder_id = "test_folder_id"
            mock_config.scraping.hours_limit = 24
            mock_get_config.return_value = mock_config
            
            processor = NewsProcessor()
            with patch.object(processor.db_manager, 'get_recent_articles_all') as mock_get_articles:
                # モック記事データ作成
                mock_article = MagicMock()
                mock_article.title = "テスト記事"
                mock_article.url = "https://test.com"
                mock_article.source = "Reuters"
                mock_article.published_at = None
                mock_article.body = "テスト本文"
                mock_article.ai_analysis = [MagicMock()]
                mock_article.ai_analysis[0].summary = "テスト要約"
                mock_article.ai_analysis[0].sentiment_label = "Positive"
                mock_article.ai_analysis[0].sentiment_score = 0.8
                
                mock_get_articles.return_value = [mock_article]
                
                # Googleドキュメント処理実行
                processor.generate_google_docs()
        
        # 各フェーズが呼ばれたことを確認
        mock_auth.assert_called_once()
        mock_test_drive.assert_called_once()
        mock_update_doc.assert_called_once()
        mock_create_daily.assert_called_once()
    
    @patch('src.core.news_processor.authenticate_google_services')
    def test_google_auth_failure(self, mock_auth):
        """Google認証失敗テスト"""
        mock_auth.return_value = (None, None)
        
        with patch('src.config.app_config.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.google.is_document_creation_day_and_time.return_value = True
            mock_get_config.return_value = mock_config
            
            processor = NewsProcessor()
            processor.generate_google_docs()
            
            # 認証が呼ばれたことを確認
            mock_auth.assert_called_once()
    
    @patch('src.core.news_processor.authenticate_google_services')
    @patch('src.core.news_processor.test_drive_connection')
    def test_drive_connection_failure(self, mock_test_drive, mock_auth):
        """Drive接続失敗テスト"""
        mock_drive = MagicMock()
        mock_docs = MagicMock()
        mock_auth.return_value = (mock_drive, mock_docs)
        mock_test_drive.return_value = False
        
        with patch('src.config.app_config.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.google.is_document_creation_day_and_time.return_value = True
            mock_config.google.drive_output_folder_id = "test_folder_id"
            mock_get_config.return_value = mock_config
            
            processor = NewsProcessor()
            processor.generate_google_docs()
            
            # 接続テストが呼ばれたことを確認
            mock_test_drive.assert_called_once()
    
    def test_time_condition_not_met(self):
        """時刻条件未満時のテスト"""
        with patch('src.config.app_config.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.google.is_document_creation_day_and_time.return_value = False
            mock_get_config.return_value = mock_config
            
            processor = NewsProcessor()
            
            with patch('src.core.news_processor.authenticate_google_services') as mock_auth:
                processor.generate_google_docs()
                
                # 時刻条件未満の場合、認証は呼ばれない
                mock_auth.assert_not_called()