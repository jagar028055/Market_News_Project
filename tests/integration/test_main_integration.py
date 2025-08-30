# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path

from scripts.core.main import main
from src.core.news_processor import NewsProcessor


class TestMainIntegration:
    """メイン処理の統合テスト"""
    
    @patch('src.core.news_processor.create_daily_summary_doc_with_cleanup_retry')
    @patch('src.core.news_processor.update_google_doc_with_full_text')
    @patch('src.core.news_processor.test_drive_connection')
    @patch('src.core.news_processor.cleanup_old_drive_documents')
    @patch('src.core.news_processor.debug_drive_storage_info')
    def test_main_success_flow(self, mock_debug_drive, mock_cleanup, mock_test_drive, mock_update_doc, mock_create_daily):
        """メイン処理成功フローテスト（Google Docs生成部分）"""
        
        # モック設定
        mock_test_drive.return_value = True
        mock_cleanup.return_value = 0
        
        with patch('src.config.app_config.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.google.overwrite_doc_id = "test_doc_id"
            mock_config.google.drive_output_folder_id = "test_folder_id"
            mock_config.scraping.hours_limit = 24
            mock_config.google.docs_retention_days = 30
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
                mock_drive = MagicMock()
                mock_docs = MagicMock()
                processor._generate_google_docs_internal(mock_drive, mock_docs)
        
        # 各フェーズが呼ばれたことを確認
        mock_update_doc.assert_called_once()
    
    @patch('src.core.news_processor.authenticate_google_services')
    def test_google_auth_failure(self, mock_auth):
        """Google認証失敗テスト"""
        mock_auth.return_value = (None, None, None)
        
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
        mock_sheets = MagicMock()
        mock_auth.return_value = (mock_drive, mock_docs, mock_sheets)
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
    
    @patch('src.core.news_processor.create_daily_summary_doc_with_cleanup_retry')
    def test_time_condition_not_met(self, mock_create_doc):
        """時刻条件未満時のテスト（現在はロジック変更により、このテストは認証が呼ばれることを確認する）"""
        with patch('src.config.app_config.get_config') as mock_get_config:
            mock_config = MagicMock()
            # is_document_creation_day_and_time は現在使用されていない
            mock_config.google.is_document_creation_day_and_time.return_value = False
            mock_get_config.return_value = mock_config
            
            processor = NewsProcessor()
            
            with patch('src.core.news_processor.authenticate_google_services') as mock_auth, \
                 patch.object(processor.db_manager, 'get_recent_articles_all') as mock_get_articles:

                mock_auth.return_value = (MagicMock(), MagicMock(), MagicMock())
                mock_get_articles.return_value = [] # 記事がない場合

                processor.generate_google_docs()
                
                # 認証は呼ばれる
                mock_auth.assert_called_once()
                # ドキュメント作成は記事がないため呼ばれない
                mock_create_doc.assert_not_called()