"""
LINEBroadcaster のユニットテスト
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# requestsのモック（テスト環境で利用できない場合）
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    # モッククラスを作成
    class MockResponse:
        def __init__(self, status_code=200, json_data=None, content=b''):
            self.status_code = status_code
            self._json_data = json_data or {}
            self.content = content
            self.headers = {}
        
        def json(self):
            return self._json_data
    
    class requests:
        @staticmethod
        def post(url, **kwargs):
            return MockResponse()
        
        @staticmethod
        def get(url, **kwargs):
            return MockResponse()
        
        class exceptions:
            class RequestException(Exception):
                pass
            
            class Timeout(RequestException):
                pass
            
            class ConnectionError(RequestException):
                pass

from src.podcast.publisher import (
    LINEBroadcaster,
    PodcastEpisode,
    PublishResult,
    LINEBroadcastingError,
    LINEAPIError
)


class TestLINEBroadcaster:
    """LINEBroadcaster のテストクラス"""
    
    @pytest.fixture
    def line_config(self):
        """LINE設定"""
        return {
            'channel_access_token': 'test_channel_access_token',
            'max_message_length': 5000,
            'enable_notification': True,
            'retry_count': 3,
            'retry_delay': 1.0,
            'test_mode': False,
            'test_user_ids': ['test_user_1', 'test_user_2']
        }
    
    @pytest.fixture
    def sample_episode(self):
        """テスト用エピソード"""
        return PodcastEpisode(
            title="第1回 テストエピソード",
            description="テスト用のエピソード説明です。今日の市場動向について詳しく解説します。",
            audio_file_path="/tmp/test_audio.mp3",
            duration_seconds=600,  # 10分
            file_size_bytes=1024000,
            publish_date=datetime(2024, 1, 15, 7, 0, 0, tzinfo=timezone.utc),
            episode_number=1,
            transcript="テスト用のトランスクリプト",
            source_articles=[]
        )
    
    def test_init_success(self, line_config):
        """正常な初期化のテスト"""
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            assert broadcaster.channel_access_token == 'test_channel_access_token'
            assert broadcaster.max_message_length == 5000
            assert broadcaster.enable_notification is True
            assert broadcaster.retry_count == 3
            assert broadcaster.test_mode is False
    
    def test_init_requests_not_available(self, line_config):
        """requests未インストール時の初期化テスト"""
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', False):
            with pytest.raises(LINEBroadcastingError) as exc_info:
                LINEBroadcaster(line_config)
            
            assert "requestsライブラリが必要です" in str(exc_info.value)
    
    def test_init_no_access_token(self, line_config):
        """アクセストークンなしの初期化テスト"""
        line_config['channel_access_token'] = ''
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            with pytest.raises(LINEBroadcastingError) as exc_info:
                LINEBroadcaster(line_config)
            
            assert "LINE Channel Access Tokenが設定されていません" in str(exc_info.value)
    
    def test_init_default_values(self):
        """デフォルト値での初期化テスト"""
        config = {'channel_access_token': 'test_token'}
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(config)
            
            assert broadcaster.max_message_length == 5000
            assert broadcaster.enable_notification is True
            assert broadcaster.retry_count == 3
            assert broadcaster.retry_delay == 1.0
            assert broadcaster.test_mode is False
            assert broadcaster.test_user_ids == []
    
    def test_create_broadcast_message(self, line_config, sample_episode):
        """ブロードキャストメッセージ作成のテスト"""
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            podcast_url = "https://test.github.io/podcast/feed.xml"
            credits = "音声素材: CC-BY ライセンス"
            
            message = broadcaster._create_broadcast_message(sample_episode, podcast_url, credits)
            
            assert message['type'] == 'text'
            assert '🎙️ 第1回 テストエピソード' in message['text']
            assert '📅 2024年01月15日' in message['text']
            assert '⏱️ 約10分' in message['text']
            assert 'テスト用のエピソード説明' in message['text']
            assert '🎧 聴く: https://test.github.io/podcast/feed.xml' in message['text']
            assert 'CC-BY ライセンス' in message['text']
    
    def test_create_broadcast_message_long_description(self, line_config, sample_episode):
        """長い説明文のメッセージ作成テスト"""
        # 非常に長い説明文を設定
        sample_episode.description = "非常に長い説明文です。" * 200  # 約5000文字
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            podcast_url = "https://test.github.io/podcast/feed.xml"
            credits = "音声素材: CC-BY ライセンス"
            
            message = broadcaster._create_broadcast_message(sample_episode, podcast_url, credits)
            
            # メッセージが制限内に収まることを確認
            assert len(message['text']) <= broadcaster.max_message_length
            assert '...' in message['text']  # 短縮されている
    
    def test_validate_message_length_success(self, line_config):
        """メッセージ長さ検証成功のテスト"""
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            message = {'type': 'text', 'text': '短いメッセージです'}
            
            # エラーが発生しないことを確認
            broadcaster._validate_message_length(message)
    
    def test_validate_message_length_too_long(self, line_config):
        """メッセージ長さ検証失敗のテスト"""
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            long_text = 'あ' * 6000  # 制限を超える長さ
            message = {'type': 'text', 'text': long_text}
            
            with pytest.raises(LINEBroadcastingError) as exc_info:
                broadcaster._validate_message_length(message)
            
            assert "メッセージが長すぎます" in str(exc_info.value)
    
    @patch('src.podcast.publisher.requests.post')
    def test_send_broadcast_message_success(self, mock_post, line_config):
        """ブロードキャストメッセージ送信成功のテスト"""
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success'}
        mock_response.content = b'{"status": "success"}'
        mock_post.return_value = mock_response
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            message = {'type': 'text', 'text': 'テストメッセージ'}
            
            result = broadcaster._send_broadcast_message(message)
            
            # API呼び出しが正しく行われることを確認
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            # URL確認
            assert call_args[0][0] == 'https://api.line.me/v2/bot/message/broadcast'
            
            # ヘッダー確認
            headers = call_args[1]['headers']
            assert 'Bearer test_channel_access_token' in headers['Authorization']
            assert headers['Content-Type'] == 'application/json'
            
            # ペイロード確認
            payload = call_args[1]['json']
            assert payload['messages'] == [message]
            assert payload['notificationDisabled'] is False
            
            # 結果確認
            assert result == {'status': 'success'}
    
    @patch('src.podcast.publisher.requests.post')
    def test_send_multicast_message_success(self, mock_post, line_config):
        """マルチキャストメッセージ送信成功のテスト"""
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success'}
        mock_response.content = b'{"status": "success"}'
        mock_post.return_value = mock_response
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            message = {'type': 'text', 'text': 'テストメッセージ'}
            user_ids = ['user1', 'user2', 'user3']
            
            result = broadcaster._send_multicast_message(message, user_ids)
            
            # API呼び出しが正しく行われることを確認
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            # URL確認
            assert call_args[0][0] == 'https://api.line.me/v2/bot/message/multicast'
            
            # ペイロード確認
            payload = call_args[1]['json']
            assert payload['to'] == user_ids
            assert payload['messages'] == [message]
            
            # 結果確認
            assert result == {'status': 'success'}
    
    @patch('src.podcast.publisher.requests.post')
    def test_send_multicast_message_too_many_users(self, mock_post, line_config):
        """マルチキャストメッセージ送信（ユーザー数制限）のテスト"""
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success'}
        mock_response.content = b'{"status": "success"}'
        mock_post.return_value = mock_response
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            message = {'type': 'text', 'text': 'テストメッセージ'}
            user_ids = [f'user{i}' for i in range(600)]  # 500を超える
            
            result = broadcaster._send_multicast_message(message, user_ids)
            
            # ペイロード確認（500に制限されている）
            payload = mock_post.call_args[1]['json']
            assert len(payload['to']) == 500
    
    @patch('src.podcast.publisher.requests.post')
    def test_make_api_request_rate_limit(self, mock_post, line_config):
        """レート制限時のAPIリクエストテスト"""
        # 最初はレート制限、2回目は成功
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {'Retry-After': '1'}
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {'status': 'success'}
        mock_response_200.content = b'{"status": "success"}'
        
        mock_post.side_effect = [mock_response_429, mock_response_200]
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            with patch('time.sleep') as mock_sleep:  # sleepをモック
                broadcaster = LINEBroadcaster(line_config)
                
                headers = {'Authorization': 'Bearer test_token'}
                payload = {'messages': [{'type': 'text', 'text': 'test'}]}
                
                result = broadcaster._make_api_request('https://test.api', headers, payload)
                
                # 2回呼ばれることを確認
                assert mock_post.call_count == 2
                
                # sleepが呼ばれることを確認
                mock_sleep.assert_called_once_with(1)
                
                # 最終的に成功することを確認
                assert result == {'status': 'success'}
    
    @patch('src.podcast.publisher.requests.post')
    def test_make_api_request_api_error(self, mock_post, line_config):
        """API エラー時のリクエストテスト"""
        # APIエラーレスポンス
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'message': 'Bad Request'}
        mock_response.content = b'{"message": "Bad Request"}'
        mock_post.return_value = mock_response
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            headers = {'Authorization': 'Bearer test_token'}
            payload = {'messages': [{'type': 'text', 'text': 'test'}]}
            
            with pytest.raises(LINEAPIError) as exc_info:
                broadcaster._make_api_request('https://test.api', headers, payload)
            
            assert "Bad Request" in str(exc_info.value)
    
    @patch('src.podcast.publisher.requests.post')
    def test_make_api_request_timeout(self, mock_post, line_config):
        """タイムアウト時のリクエストテスト"""
        # タイムアウト例外を発生
        mock_post.side_effect = requests.exceptions.Timeout()
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            broadcaster.retry_count = 1  # リトライ回数を1に設定
            
            headers = {'Authorization': 'Bearer test_token'}
            payload = {'messages': [{'type': 'text', 'text': 'test'}]}
            
            with pytest.raises(LINEAPIError) as exc_info:
                broadcaster._make_api_request('https://test.api', headers, payload)
            
            assert "タイムアウト" in str(exc_info.value)
    
    @patch('src.podcast.publisher.requests.get')
    def test_get_bot_info_success(self, mock_get, line_config):
        """ボット情報取得成功のテスト"""
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'displayName': 'テストボット',
            'userId': 'test_bot_id',
            'pictureUrl': 'https://example.com/bot.jpg'
        }
        mock_get.return_value = mock_response
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            bot_info = broadcaster.get_bot_info()
            
            # API呼び出しが正しく行われることを確認
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            
            # URL確認
            assert call_args[0][0] == 'https://api.line.me/v2/bot/info'
            
            # ヘッダー確認
            headers = call_args[1]['headers']
            assert 'Bearer test_channel_access_token' in headers['Authorization']
            
            # 結果確認
            assert bot_info['displayName'] == 'テストボット'
            assert bot_info['userId'] == 'test_bot_id'
    
    @patch('src.podcast.publisher.requests.get')
    def test_get_bot_info_error(self, mock_get, line_config):
        """ボット情報取得エラーのテスト"""
        # エラーレスポンス
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {'message': 'Unauthorized'}
        mock_response.content = b'{"message": "Unauthorized"}'
        mock_get.return_value = mock_response
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            with pytest.raises(LINEAPIError) as exc_info:
                broadcaster.get_bot_info()
            
            assert "Unauthorized" in str(exc_info.value)
    
    @patch.object(LINEBroadcaster, 'get_bot_info')
    def test_test_connection_success(self, mock_get_bot_info, line_config):
        """接続テスト成功のテスト"""
        mock_get_bot_info.return_value = {'displayName': 'テストボット'}
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            result = broadcaster.test_connection()
            
            assert result is True
            mock_get_bot_info.assert_called_once()
    
    @patch.object(LINEBroadcaster, 'get_bot_info')
    def test_test_connection_failure(self, mock_get_bot_info, line_config):
        """接続テスト失敗のテスト"""
        mock_get_bot_info.side_effect = LINEAPIError("接続エラー")
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            result = broadcaster.test_connection()
            
            assert result is False
    
    def test_create_rich_message(self, line_config, sample_episode):
        """リッチメッセージ作成のテスト"""
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            podcast_url = "https://test.github.io/podcast/feed.xml"
            credits = "音声素材: CC-BY ライセンス"
            
            rich_message = broadcaster.create_rich_message(sample_episode, podcast_url, credits)
            
            # Flex Messageの基本構造を確認
            assert rich_message['type'] == 'flex'
            assert rich_message['altText'] == '第1回 テストエピソード - 新しいエピソードが配信されました'
            assert rich_message['contents']['type'] == 'bubble'
            
            # ヘッダー確認
            header = rich_message['contents']['header']
            assert '🎙️ 新しいエピソード' in str(header)
            
            # ボディ確認
            body = rich_message['contents']['body']
            assert '第1回 テストエピソード' in str(body)
            assert '2024年01月15日' in str(body)
            assert '約10分' in str(body)
            
            # フッター確認
            footer = rich_message['contents']['footer']
            assert podcast_url in str(footer)
            assert credits in str(footer)
    
    @patch.object(LINEBroadcaster, '_send_broadcast_message')
    @patch.object(LINEBroadcaster, '_validate_message_length')
    @patch.object(LINEBroadcaster, '_create_broadcast_message')
    def test_publish_success_broadcast(self, mock_create, mock_validate, mock_send, 
                                     line_config, sample_episode):
        """配信成功（ブロードキャスト）のテスト"""
        # モックの戻り値を設定
        mock_message = {'type': 'text', 'text': 'テストメッセージ'}
        mock_create.return_value = mock_message
        mock_send.return_value = {'status': 'success'}
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            podcast_url = "https://test.github.io/podcast/feed.xml"
            credits = "テストクレジット"
            
            result = broadcaster.publish(sample_episode, podcast_url, credits)
            
            # 成功結果を確認
            assert result.success is True
            assert result.channel == "LINE"
            assert result.url == podcast_url
            assert "ブロードキャスト配信完了" in result.message
            
            # 各メソッドが呼ばれることを確認
            mock_create.assert_called_once_with(sample_episode, podcast_url, credits)
            mock_validate.assert_called_once_with(mock_message)
            mock_send.assert_called_once_with(mock_message)
    
    @patch.object(LINEBroadcaster, '_send_multicast_message')
    @patch.object(LINEBroadcaster, '_validate_message_length')
    @patch.object(LINEBroadcaster, '_create_broadcast_message')
    def test_publish_success_test_mode(self, mock_create, mock_validate, mock_send, 
                                      line_config, sample_episode):
        """配信成功（テストモード）のテスト"""
        # テストモードを有効にする
        line_config['test_mode'] = True
        
        # モックの戻り値を設定
        mock_message = {'type': 'text', 'text': 'テストメッセージ'}
        mock_create.return_value = mock_message
        mock_send.return_value = {'status': 'success'}
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            podcast_url = "https://test.github.io/podcast/feed.xml"
            credits = "テストクレジット"
            
            result = broadcaster.publish(sample_episode, podcast_url, credits)
            
            # 成功結果を確認
            assert result.success is True
            assert result.channel == "LINE"
            assert "テストユーザー 2人に配信完了" in result.message
            
            # マルチキャストが呼ばれることを確認
            mock_send.assert_called_once_with(mock_message, line_config['test_user_ids'])
    
    @patch.object(LINEBroadcaster, '_create_broadcast_message')
    def test_publish_error(self, mock_create, line_config, sample_episode):
        """配信エラーのテスト"""
        # メッセージ作成でエラーが発生
        mock_create.side_effect = Exception("メッセージ作成エラー")
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(line_config)
            
            podcast_url = "https://test.github.io/podcast/feed.xml"
            credits = "テストクレジット"
            
            result = broadcaster.publish(sample_episode, podcast_url, credits)
            
            # エラー結果を確認
            assert result.success is False
            assert result.channel == "LINE"
            assert result.url is None
            assert "LINE配信エラー" in result.message
            assert "メッセージ作成エラー" in result.message


class TestLINEBroadcastingError:
    """LINEBroadcastingError のテスト"""
    
    def test_line_broadcasting_error(self):
        """LINEBroadcastingError のテスト"""
        error = LINEBroadcastingError("テストエラー")
        assert str(error) == "テストエラー"
        assert isinstance(error, Exception)


class TestLINEAPIError:
    """LINEAPIError のテスト"""
    
    def test_line_api_error(self):
        """LINEAPIError のテスト"""
        error = LINEAPIError("API エラー")
        assert str(error) == "API エラー"
        assert isinstance(error, LINEBroadcastingError)


class TestIntegration:
    """統合テスト"""
    
    @pytest.fixture
    def integration_config(self):
        """統合テスト用設定"""
        return {
            'channel_access_token': 'integration_test_token',
            'test_mode': True,
            'test_user_ids': ['integration_user_1'],
            'retry_count': 1,
            'retry_delay': 0.1
        }
    
    @patch('src.podcast.publisher.requests.post')
    def test_full_line_broadcasting_pipeline(self, mock_post, integration_config):
        """完全なLINE配信パイプラインのテスト"""
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success'}
        mock_response.content = b'{"status": "success"}'
        mock_post.return_value = mock_response
        
        episode = PodcastEpisode(
            title="統合テストエピソード",
            description="統合テスト用のエピソード説明",
            audio_file_path="/tmp/test.mp3",
            duration_seconds=600,
            file_size_bytes=1024000,
            publish_date=datetime.now(timezone.utc),
            episode_number=1,
            transcript="統合テスト",
            source_articles=[]
        )
        
        with patch('src.podcast.publisher.REQUESTS_AVAILABLE', True):
            broadcaster = LINEBroadcaster(integration_config)
            
            podcast_url = "https://integration.test/podcast/feed.xml"
            credits = "統合テストクレジット"
            
            result = broadcaster.publish(episode, podcast_url, credits)
            
            # 成功することを確認
            assert result.success is True
            assert result.channel == "LINE"
            assert result.url == podcast_url
            
            # API呼び出しが行われることを確認
            mock_post.assert_called_once()
            
            # 正しいエンドポイントが呼ばれることを確認
            call_args = mock_post.call_args
            assert 'multicast' in call_args[0][0]  # テストモードなのでmulticast
            
            # ペイロードの確認
            payload = call_args[1]['json']
            assert payload['to'] == ['integration_user_1']
            assert len(payload['messages']) == 1
            assert payload['messages'][0]['type'] == 'text'
            assert '統合テストエピソード' in payload['messages'][0]['text']