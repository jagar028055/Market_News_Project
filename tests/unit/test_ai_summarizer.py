# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch, MagicMock
import json

from src.legacy.ai_summarizer import process_article_with_ai


class TestAISummarizer:
    """AI Summarizer のテストクラス"""
    
    def test_process_article_with_ai_success(self):
        """AI処理成功テスト"""
        api_key = "test_api_key"
        text = "これはテスト用の記事本文です。十分な長さがあり、処理がスキップされないことを確認します。株価が上昇しています。"
        
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = """
## 地域
[usa]

## カテゴリ
[market]

## 要約
[Test summary about the market in the USA.]
"""
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = process_article_with_ai(api_key, text)
            
            assert result is not None
            assert result['summary'] == "Test summary about the market in the USA."
            assert result['region'] == "usa"
            assert result['category'] == "market"
            
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
            mock_response.text = """
## 地域
[japan]

## カテゴリ
[technology]

## 要約
[AIと株価と市場に関するテスト要約です。]
"""
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = process_article_with_ai("test_key", "This is a test text that is long enough to pass the validation check.")
            
            assert result is not None
            assert result['summary'] == "AIと株価と市場に関するテスト要約です。"
            assert result['region'] == "japan"
            assert result['category'] == "technology"
    
    def test_process_article_with_ai_summary_length_validation(self):
        """要約文字数検証テスト"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            # 短い要約のテスト
            mock_response = MagicMock()
            mock_response.text = """
## 地域
[other]

## カテゴリ
[other]

## 要約
[短い]
"""
            mock_model.return_value.generate_content.return_value = mock_response
            
            with patch('src.legacy.ai_summarizer.logging') as mock_logging:
                result = process_article_with_ai("test_key", "This is a test text that is long enough to pass the validation check.")
                
                assert result is not None
                assert result['summary'] == "短い"
                # 警告ログが出力されることを確認
                mock_logging.warning.assert_any_call('要約文字数が推奨範囲外です: 2字')
    
    
    @patch('src.legacy.ai_summarizer.logging')
    def test_process_article_with_ai_logging(self, mock_logging):
        """ログ出力テスト"""
        # APIキーなしでエラーログが出力されることを確認
        process_article_with_ai("", "text")
        mock_logging.error.assert_called()
        
        # API エラー時にログが出力されることを確認
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_model.return_value.generate_content.side_effect = Exception("API Error")
            process_article_with_ai("test_key", "This is a test text that is long enough to pass the validation check.")
            
        # エラーログが呼ばれたことを確認
        assert mock_logging.error.call_count >= 2