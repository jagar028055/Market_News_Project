# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path

from main import main
from config.base import get_config


class TestMainIntegration:
    """メイン処理の統合テスト"""
    
    @patch('main.client.authenticate_google_services')
    @patch('main.client.test_drive_connection')
    @patch('main.reuters.scrape_reuters_articles')
    @patch('main.bloomberg.scrape_bloomberg_top_page_articles')
    @patch('main.process_article_with_ai')
    @patch('main.create_html_file')
    @patch('main.client.update_google_doc_with_full_text')
    @patch('main.client.create_daily_summary_doc')
    def test_main_success_flow(
        self,
        mock_create_daily,
        mock_update_doc,
        mock_create_html,
        mock_process_ai,
        mock_bloomberg,
        mock_reuters,
        mock_test_drive,
        mock_auth,
        test_config
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
        
        # 設定をモック
        with patch('main.get_config', return_value=test_config):
            with patch('main.setup_logging'):
                with patch('main.get_logger') as mock_get_logger:
                    mock_logger = MagicMock()
                    mock_get_logger.return_value = mock_logger
                    
                    # メイン関数実行
                    main()
        
        # 各フェーズが呼ばれたことを確認
        mock_auth.assert_called_once()
        mock_test_drive.assert_called_once()
        mock_reuters.assert_called_once()
        mock_bloomberg.assert_called_once()
        mock_create_html.assert_called_once()
    
    @patch('main.get_config')
    def test_main_config_error(self, mock_get_config, capsys):
        """設定エラーテスト"""
        mock_get_config.side_effect = Exception("Config error")
        
        main()
        
        captured = capsys.readouterr()
        assert "設定読み込みエラー" in captured.out
    
    @patch('main.client.authenticate_google_services')
    def test_main_auth_failure(self, mock_auth, test_config):
        """Google認証失敗テスト"""
        mock_auth.return_value = (None, None)
        
        with patch('main.get_config', return_value=test_config):
            with patch('main.setup_logging'):
                with patch('main.get_logger') as mock_get_logger:
                    mock_logger = MagicMock()
                    mock_get_logger.return_value = mock_logger
                    
                    main()
                    
                    # エラーログが出力されたことを確認
                    mock_logger.error.assert_called()
    
    @patch('main.client.authenticate_google_services')
    @patch('main.client.test_drive_connection')
    def test_main_drive_connection_failure(self, mock_test_drive, mock_auth, test_config):
        """Drive接続失敗テスト"""
        mock_drive = MagicMock()
        mock_docs = MagicMock()
        mock_auth.return_value = (mock_drive, mock_docs)
        mock_test_drive.return_value = False
        
        with patch('main.get_config', return_value=test_config):
            with patch('main.setup_logging'):
                with patch('main.get_logger') as mock_get_logger:
                    mock_logger = MagicMock()
                    mock_get_logger.return_value = mock_logger
                    
                    main()
                    
                    # エラーログが出力されたことを確認
                    mock_logger.error.assert_called()
    
    @patch('main.client.authenticate_google_services')
    @patch('main.client.test_drive_connection')
    @patch('main.reuters.scrape_reuters_articles')
    @patch('main.bloomberg.scrape_bloomberg_top_page_articles')
    def test_main_no_articles_found(
        self,
        mock_bloomberg,
        mock_reuters,
        mock_test_drive,
        mock_auth,
        test_config
    ):
        """記事が見つからない場合のテスト"""
        mock_drive = MagicMock()
        mock_docs = MagicMock()
        mock_auth.return_value = (mock_drive, mock_docs)
        mock_test_drive.return_value = True
        
        # 空の記事リストを返す
        mock_reuters.return_value = []
        mock_bloomberg.return_value = []
        
        with patch('main.get_config', return_value=test_config):
            with patch('main.setup_logging'):
                with patch('main.get_logger') as mock_get_logger:
                    mock_logger = MagicMock()
                    mock_get_logger.return_value = mock_logger
                    
                    with patch('main.create_html_file') as mock_create_html:
                        main()
                        
                        # HTMLファイルは空の記事リストで生成される
                        mock_create_html.assert_called_once()
                        args, kwargs = mock_create_html.call_args
                        assert len(args[0]) == 0  # 空の記事リスト
    
    @patch('main.client.authenticate_google_services')
    @patch('main.client.test_drive_connection')
    @patch('main.reuters.scrape_reuters_articles')
    @patch('main.bloomberg.scrape_bloomberg_top_page_articles')
    @patch('main.process_article_with_ai')
    def test_main_ai_processing_failure(
        self,
        mock_process_ai,
        mock_bloomberg,
        mock_reuters,
        mock_test_drive,
        mock_auth,
        test_config
    ):
        """AI処理失敗時のテスト"""
        mock_drive = MagicMock()
        mock_docs = MagicMock()
        mock_auth.return_value = (mock_drive, mock_docs)
        mock_test_drive.return_value = True
        
        # 記事は取得できるがAI処理が失敗
        mock_reuters.return_value = [
            {
                'title': 'テスト記事',
                'url': 'https://test.com/article',
                'body': 'テスト本文',
                'source': 'Reuters'
            }
        ]
        mock_bloomberg.return_value = []
        mock_process_ai.return_value = None  # AI処理失敗
        
        with patch('main.get_config', return_value=test_config):
            with patch('main.setup_logging'):
                with patch('main.get_logger') as mock_get_logger:
                    mock_logger = MagicMock()
                    mock_get_logger.return_value = mock_logger
                    
                    with patch('main.create_html_file') as mock_create_html:
                        main()
                        
                        # HTMLファイルは生成されるが、AI処理失敗の記事が含まれる
                        mock_create_html.assert_called_once()
                        args, kwargs = mock_create_html.call_args
                        processed_articles = args[0]
                        
                        assert len(processed_articles) == 1
                        assert processed_articles[0]['summary'] == "AI処理に失敗しました。"
                        assert processed_articles[0]['sentiment_label'] == "N/A"