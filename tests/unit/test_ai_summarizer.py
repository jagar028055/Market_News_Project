# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch, MagicMock
import json

from ai_summarizer import process_article_with_ai


class TestAISummarizer:
    """AI Summarizer のテストクラス"""
    
    def test_process_article_with_ai_success(self):
        """AI処理成功テスト"""
        api_key = "test_api_key"
        text = "テスト記事本文。株価が上昇しています。"
        
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "summary": "Test summary",
                "keywords": ["test", "keyword"]
            })
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = process_article_with_ai(api_key, text)
            
            assert result is not None
            assert result['summary'] == "Test summary"
            assert result['keywords'] == ["test", "keyword"]
            
            # APIが呼ばれたことを確認
            mock_model.assert_called_once()
    
    def test_process_article_with_ai_no_api_key(self):
        """APIキーなしテスト"""
        result = process_article_with_ai("", "test text")
        assert result is None
        
        result = process_article_with_ai(None, "test text")
        assert result is None
    
    def test_process_article_with_ai_api_error(self):
        """API エラーテスト"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_model.return_value.generate_content.side_effect = Exception("API Error")
            
            result = process_article_with_ai("test_key", "text")
            assert result is None
    
    @pytest.mark.parametrize("invalid_response", [
        "",  # 空のレスポンス
        "Invalid JSON",  # 無効なJSON
        '{"summary": ""}',  # 空のsummary
        '{"keywords": ["test"]}',  # summaryなし
    ])
    def test_process_article_with_ai_invalid_response(self, invalid_response):
        """無効レスポンステスト"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = invalid_response
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = process_article_with_ai("test_key", "text")
            assert result is None
    
    def test_process_article_with_ai_json_decode_error(self):
        """JSONデコードエラーテスト"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = '{"invalid": json}'  # 無効なJSON
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = process_article_with_ai("test_key", "text")
            assert result is None
    
    def test_process_article_with_ai_with_keywords(self):
        """キーワード付きテスト"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "summary": "Test summary with keywords",
                "keywords": ["AI", "株価", "市場"]
            })
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = process_article_with_ai("test_key", "text")
            
            assert result is not None
            assert result['summary'] == "Test summary with keywords"
            assert result['keywords'] == ["AI", "株価", "市場"]
    
    def test_process_article_with_ai_summary_length_validation(self):
        """要約文字数検証テスト"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            # 短い要約のテスト
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "summary": "短い",  # 2文字
                "keywords": ["test"]
            })
            mock_model.return_value.generate_content.return_value = mock_response
            
            with patch('ai_summarizer.logging') as mock_logging:
                result = process_article_with_ai("test_key", "text")
                
                assert result is not None
                assert result['summary'] == "短い"
                # 警告ログが出力されることを確認
                mock_logging.warning.assert_called()
    
    def test_process_article_with_ai_json_extraction(self):
        """JSON抽出テスト（前後にテキストがある場合）"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            # JSON の前後に余分なテキストがある場合
            mock_response.text = '''
            これは分析結果です。
            
            {
                "summary": "Test summary",
                "keywords": ["test", "extraction"]
            }
            
            以上です。
            '''
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = process_article_with_ai("test_key", "text")
            
            assert result is not None
            assert result['summary'] == "Test summary"
            assert result['keywords'] == ["test", "extraction"]
    
    @patch('ai_summarizer.logging')
    def test_process_article_with_ai_logging(self, mock_logging):
        """ログ出力テスト"""
        # APIキーなしでエラーログが出力されることを確認
        process_article_with_ai("", "text")
        mock_logging.error.assert_called()
        
        # API エラー時にログが出力されることを確認
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_model.return_value.generate_content.side_effect = Exception("API Error")
            process_article_with_ai("test_key", "text")
            
        # エラーログが呼ばれたことを確認
        assert mock_logging.error.call_count >= 2