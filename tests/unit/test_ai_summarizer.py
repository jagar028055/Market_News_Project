# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch, MagicMock
import json

from ai_summarizer import process_article_with_ai


class TestAISummarizer:
    """AI Summarizer のテストクラス"""
    
    def test_process_article_with_ai_success(self, mock_gemini_api):
        """AI処理成功テスト"""
        api_key = "test_api_key"
        text = "テスト記事本文。株価が上昇しています。"
        
        result = process_article_with_ai(api_key, text)
        
        assert result is not None
        assert result['summary'] == "Test summary"
        assert result['sentiment_label'] == "Positive"
        assert result['sentiment_score'] == 0.8
        
        # APIが呼ばれたことを確認
        mock_gemini_api.assert_called_once()
    
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
        '{"summary": ""}',  # 必須フィールド不足
        '{"summary": "test", "sentiment_label": "Invalid"}',  # 無効な感情ラベル
        '{"sentiment_label": "Positive", "sentiment_score": 0.8}',  # summaryなし
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
    
    def test_process_article_with_ai_valid_sentiment_labels(self):
        """有効な感情ラベルテスト"""
        valid_labels = ["Positive", "Negative", "Neutral"]
        
        for label in valid_labels:
            with patch('google.generativeai.GenerativeModel') as mock_model:
                mock_response = MagicMock()
                mock_response.text = json.dumps({
                    "summary": "Test summary",
                    "sentiment_label": label,
                    "sentiment_score": 0.7
                })
                mock_model.return_value.generate_content.return_value = mock_response
                
                result = process_article_with_ai("test_key", "text")
                
                assert result is not None
                assert result['sentiment_label'] == label
    
    def test_process_article_with_ai_score_conversion(self):
        """スコア変換テスト"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "summary": "Test summary",
                "sentiment_label": "Positive",
                "sentiment_score": "0.85"  # 文字列として返される場合
            })
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = process_article_with_ai("test_key", "text")
            
            assert result is not None
            assert isinstance(result['sentiment_score'], float)
            assert result['sentiment_score'] == 0.85
    
    def test_process_article_with_ai_json_extraction(self):
        """JSON抽出テスト（前後にテキストがある場合）"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            # JSON の前後に余分なテキストがある場合
            mock_response.text = '''
            これは分析結果です。
            
            {
                "summary": "Test summary",
                "sentiment_label": "Positive",
                "sentiment_score": 0.8
            }
            
            以上です。
            '''
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = process_article_with_ai("test_key", "text")
            
            assert result is not None
            assert result['summary'] == "Test summary"
            assert result['sentiment_label'] == "Positive"
            assert result['sentiment_score'] == 0.8
    
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