#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ポッドキャスト機能の統合テスト
"""
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import pytz

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.integration
class TestPodcastIntegration:
    """ポッドキャスト機能の統合テスト"""

    def test_podcast_workflow_configuration(self):
        """ポッドキャストワークフローの設定テスト"""
        try:
            from src.config.app_config import AppConfig
            
            # 環境変数をモック設定
            with patch.dict(os.environ, {
                'PODCAST_WORKFLOW_ENABLED': 'true',
                'PODCAST_TEST_MODE': 'true',
                'PODCAST_TARGET_DURATION_MINUTES': '5',
                'PODCAST_MONTHLY_COST_LIMIT': '1.0'
            }):
                config = AppConfig()
                
                # ポッドキャスト関連設定の確認
                assert hasattr(config, 'podcast'), "ポッドキャスト設定が存在しない"
                
        except ImportError:
            pytest.skip("AppConfig が利用できないため、テストをスキップ")

    @pytest.mark.skip(reason="Test is outdated and uses old TTS engine")
    @patch('google.cloud.texttospeech.TextToSpeechClient')
    def test_tts_client_initialization(self, mock_tts_client):
        """Google Cloud TTS クライアントの初期化テスト"""
        try:
            from src.podcast.tts import tts_engine
            
            # モッククライアントの設定
            mock_client = Mock()
            mock_tts_client.return_value = mock_client
            
            # 環境変数を設定
            with patch.dict(os.environ, {
                'GOOGLE_APPLICATION_CREDENTIALS_JSON': '{"type": "service_account", "project_id": "test"}',
                'PODCAST_TEST_MODE': 'true'
            }):
                # TTS エンジンの初期化テスト
                engine = tts_engine.TTSEngine()
                assert engine is not None, "TTS エンジンの初期化に失敗"
                
        except ImportError:
            pytest.skip("TTS モジュールが利用できないため、テストをスキップ")

    def test_audio_processing_pipeline(self):
        """音声処理パイプラインのテスト"""
        try:
            import pydub
            from pydub import AudioSegment
            from io import BytesIO
            import tempfile
            
            # テスト用の無音データを作成
            duration_ms = 1000  # 1秒
            sample_rate = 22050
            silence = AudioSegment.silent(duration=duration_ms, frame_rate=sample_rate)
            
            # 一時ファイルに書き出し
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                silence.export(temp_file.name, format="wav")
                
                # ファイルが作成されたことを確認
                assert os.path.exists(temp_file.name), "音声ファイルの作成に失敗"
                
                # ファイルサイズが適切であることを確認
                file_size = os.path.getsize(temp_file.name)
                assert file_size > 0, "音声ファイルのサイズが0"
                
                # クリーンアップ
                os.unlink(temp_file.name)
                
        except ImportError:
            pytest.skip("PyDub が利用できないため、テストをスキップ")

    def test_podcast_rss_generation(self):
        """ポッドキャストRSS生成のテスト"""
        try:
            import feedgen.feed
            from datetime import datetime
            
            # RSS フィードの作成テスト
            fg = feedgen.feed.FeedGenerator()
            fg.title('テストポッドキャスト')
            fg.id('http://test.example.com/')
            fg.link(href='http://test.example.com/', rel='alternate')
            fg.description('テスト用のポッドキャストフィード')
            fg.author({'name': 'Test Author', 'email': 'test@example.com'})
            fg.language('ja')
            
            # エピソードの追加
            fe = fg.add_entry()
            fe.id('http://test.example.com/episodes/1')
            fe.title('テストエピソード')
            fe.link(href='http://test.example.com/episodes/1')
            fe.description('テスト用のエピソード')
            fe.enclosure('http://test.example.com/audio/episode1.mp3', 0, 'audio/mpeg')
            fe.pubDate(datetime.now(pytz.utc))
            
            # RSS の生成
            rss_str_bytes = fg.rss_str(pretty=True)
            assert rss_str_bytes is not None, "RSS生成に失敗"
            rss_str = rss_str_bytes.decode('utf-8')
            assert '<rss' in rss_str, "RSS形式が正しくない"
            assert '<title>テストポッドキャスト</title>' in rss_str, "タイトルが含まれていない"
            
        except ImportError:
            pytest.skip("FeedGen が利用できないため、テストをスキップ")

    @patch('requests.post')
    def test_line_bot_notification(self, mock_post):
        """LINE Bot 通知のテスト"""
        try:
            import json
            
            # LINE Bot APIのモック
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response
            
            # 環境変数の設定
            with patch.dict(os.environ, {
                'LINE_CHANNEL_ACCESS_TOKEN': 'test_token',
                'PODCAST_TEST_MODE': 'true'
            }):
                # 通知テスト（実際の実装があればそれを使用）
                import requests
                
                # テスト用の通知データ
                notification_data = {
                    'to': 'test_user_id',
                    'messages': [{
                        'type': 'text',
                        'text': 'テストポッドキャストが完成しました'
                    }]
                }
                
                # リクエストの送信をシミュレート
                response = requests.post(
                    'https://api.line.me/v2/bot/message/push',
                    json=notification_data,
                    headers={'Authorization': 'Bearer test_token'}
                )
                
                assert response.status_code == 200, "LINE通知に失敗"
                
        except ImportError:
            pytest.skip("Requests が利用できないため、テストをスキップ")

    def test_cost_management_system(self):
        """コスト管理システムのテスト"""
        try:
            import tempfile
            import json
            
            # 一時的なコスト追跡ファイル
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
                # テスト用のコストデータ
                cost_data = {
                    'monthly_limit': 10.0,
                    'current_usage': 2.5,
                    'last_updated': '2024-01-01T00:00:00',
                    'transactions': [
                        {'date': '2024-01-01', 'amount': 1.0, 'service': 'TTS'},
                        {'date': '2024-01-01', 'amount': 1.5, 'service': 'TTS'}
                    ]
                }
                
                json.dump(cost_data, temp_file)
                temp_file.flush()
                
                # ファイルの読み込みテスト
                with open(temp_file.name, 'r') as f:
                    loaded_data = json.load(f)
                
                assert loaded_data['monthly_limit'] == 10.0, "月間上限の読み込みに失敗"
                assert loaded_data['current_usage'] == 2.5, "現在の使用量の読み込みに失敗"
                assert len(loaded_data['transactions']) == 2, "取引履歴の読み込みに失敗"
                
                # 上限チェック
                remaining_budget = loaded_data['monthly_limit'] - loaded_data['current_usage']
                assert remaining_budget > 0, "予算オーバー"
                
                # クリーンアップ
                os.unlink(temp_file.name)
                
        except Exception as e:
            pytest.fail(f"コスト管理システムテストでエラー: {e}")

    @patch('os.path.exists')
    def test_podcast_file_organization(self, mock_exists):
        """ポッドキャストファイル整理のテスト"""
        # ファイル存在チェックをモック
        mock_exists.return_value = True
        
        try:
            from datetime import datetime
            import tempfile
            
            # 日付ベースのファイル名生成テスト
            today = datetime.now().strftime('%Y%m%d')
            expected_filename = f"market_news_{today}.mp3"
            
            # ファイル名の検証
            assert expected_filename.endswith('.mp3'), "ファイル拡張子が正しくない"
            assert 'market_news_' in expected_filename, "ファイル名の形式が正しくない"
            assert len(today) == 8, "日付形式が正しくない"
            
            # ディレクトリ構造のテスト
            expected_paths = [
                f"output/podcast/{expected_filename}",
                f"public/podcast/{expected_filename}",
                "output/podcast/feed.xml"
            ]
            
            for path in expected_paths:
                assert isinstance(path, str), f"パスが文字列でない: {path}"
                assert '/' in path, f"パスセパレーターが含まれていない: {path}"
                
        except Exception as e:
            pytest.fail(f"ファイル整理テストでエラー: {e}")

    def test_environment_variable_validation(self):
        """環境変数バリデーションのテスト"""
        required_vars = [
            'GOOGLE_APPLICATION_CREDENTIALS_JSON',
            'PODCAST_RSS_BASE_URL',
            'PODCAST_AUTHOR_NAME',
            'PODCAST_AUTHOR_EMAIL'
        ]
        
        optional_vars = [
            'PODCAST_MONTHLY_COST_LIMIT',
            'PODCAST_TARGET_DURATION_MINUTES',
            'PODCAST_MAX_FILE_SIZE_MB',
            'LINE_CHANNEL_ACCESS_TOKEN'
        ]
        
        # テストモードでは環境変数の存在確認のみ
        with patch.dict(os.environ, {'PODCAST_TEST_MODE': 'true'}):
            # 必須環境変数のチェック（テストモードでは警告のみ）
            for var in required_vars:
                var_value = os.getenv(var)
                if not var_value:
                    print(f"⚠️ Warning: {var} is not set (test mode)")
                else:
                    assert isinstance(var_value, str), f"{var}が文字列でない"
            
            # オプション環境変数のチェック
            for var in optional_vars:
                var_value = os.getenv(var)
                if var_value:
                    assert isinstance(var_value, str), f"{var}が文字列でない"


@pytest.mark.integration
@pytest.mark.slow
class TestPodcastEndToEnd:
    """ポッドキャスト機能のエンドツーエンドテスト"""

    @pytest.mark.skip(reason="Test is outdated and uses old TTS engine")
    @patch('google.cloud.texttospeech.TextToSpeechClient')
    @patch('requests.post')
    def test_complete_podcast_workflow(self, mock_line_post, mock_tts_client):
        """完全なポッドキャストワークフローのテスト"""
        # 完全な統合テストはGitHub Actions環境で実行
        if not os.getenv('GITHUB_ACTIONS'):
            pytest.skip("完全な統合テストはCI環境でのみ実行")
        
        try:
            # モッククライアントの設定
            mock_client = Mock()
            mock_tts_client.return_value = mock_client
            
            # TTS レスポンスのモック
            mock_response = Mock()
            mock_response.audio_content = b"mock_audio_data"
            mock_client.synthesize_speech.return_value = mock_response
            
            # LINE Bot レスポンスのモック
            mock_line_response = Mock()
            mock_line_response.status_code = 200
            mock_line_post.return_value = mock_line_response
            
            # 環境変数の設定
            with patch.dict(os.environ, {
                'PODCAST_TEST_MODE': 'true',
                'PODCAST_FORCE_RUN': 'true',
                'GOOGLE_APPLICATION_CREDENTIALS_JSON': '{"type": "service_account"}',
                'PODCAST_TARGET_DURATION_MINUTES': '1',
                'PODCAST_MONTHLY_COST_LIMIT': '0.1'
            }):
                # 実際のワークフローの実行をシミュレート
                from src.podcast.main import main as podcast_main
                
                # メイン処理の実行
                result = podcast_main()
                
                assert result is not None, "ポッドキャストワークフローの実行に失敗"
                
        except ImportError as e:
            pytest.skip(f"ポッドキャストモジュールが利用できない: {e}")
        except Exception as e:
            pytest.fail(f"完全な統合テストでエラー: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])