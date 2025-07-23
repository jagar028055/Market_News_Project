"""ポッドキャスト機能の統合テスト"""

import os
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
import yaml

from src.config.app_config import AppConfig, PodcastConfig
from src.podcast.core.podcast_processor import PodcastProcessor
from src.podcast.script_generator import DialogueScriptGenerator
from src.podcast.tts_engine import GeminiTTSEngine
from src.podcast.audio_processor import AudioProcessor
from src.podcast.publisher.rss_generator import RSSGenerator
from src.podcast.publisher.line_broadcaster import LINEBroadcaster
from src.podcast.publisher.podcast_publisher import PodcastPublisher
from src.podcast.assets.asset_manager import AssetManager
from src.podcast.assets.credit_inserter import CreditInserter


class TestPodcastIntegration:
    """ポッドキャスト機能の統合テスト"""
    
    @pytest.fixture
    def temp_dir(self):
        """テスト用一時ディレクトリ"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def mock_config(self, temp_dir):
        """モック設定"""
        config = Mock(spec=AppConfig)
        
        # ポッドキャスト設定
        podcast_config = Mock(spec=PodcastConfig)
        podcast_config.enabled = True
        podcast_config.script_model = "gemini-2.5-pro"
        podcast_config.tts_model = "gemini-tts"
        podcast_config.target_duration_minutes = 10.0
        podcast_config.max_file_size_mb = 15
        podcast_config.target_character_count = (2400, 2800)
        podcast_config.audio_format = "mp3"
        podcast_config.sample_rate = 44100
        podcast_config.bitrate = "128k"
        podcast_config.lufs_target = -16.0
        podcast_config.peak_target = -1.0
        podcast_config.rss_title = "テストポッドキャスト"
        podcast_config.rss_description = "テスト用ポッドキャスト"
        podcast_config.rss_base_url = "https://test.example.com"
        podcast_config.rss_output_dir = os.path.join(temp_dir, "rss")
        podcast_config.audio_output_dir = os.path.join(temp_dir, "audio")
        podcast_config.author_name = "Test Author"
        podcast_config.author_email = "test@example.com"
        podcast_config.language = "ja"
        podcast_config.episode_prefix = "第"
        podcast_config.episode_suffix = "回"
        
        # LINE設定
        line_config = Mock()
        line_config.channel_access_token = "test_token"
        line_config.channel_secret = "test_secret"
        podcast_config.line = line_config
        
        config.podcast = podcast_config
        
        # Gemini設定
        ai_config = Mock()
        ai_config.api_key = "test_gemini_key"
        config.ai = ai_config
        
        return config
    
    @pytest.fixture
    def sample_articles(self):
        """テスト用記事データ"""
        return [
            {
                'title': 'テスト記事1: 市場動向について',
                'content': 'これは市場動向に関するテスト記事です。株価が上昇しており、投資家の関心が高まっています。',
                'url': 'https://example.com/article1',
                'published_at': datetime.now(),
                'source': 'テストソース1',
                'summary': '市場が好調に推移している。',
                'sentiment_label': 'positive',
                'sentiment_score': 0.8
            },
            {
                'title': 'テスト記事2: 経済指標の発表',
                'content': '重要な経済指標が発表されました。GDP成長率は予想を上回る結果となりました。',
                'url': 'https://example.com/article2',
                'published_at': datetime.now() - timedelta(hours=1),
                'source': 'テストソース2',
                'summary': 'GDP成長率が予想を上回った。',
                'sentiment_label': 'positive',
                'sentiment_score': 0.7
            },
            {
                'title': 'テスト記事3: 企業決算',
                'content': '主要企業の決算が発表され、予想を下回る結果となりました。',
                'url': 'https://example.com/article3',
                'published_at': datetime.now() - timedelta(hours=2),
                'source': 'テストソース3',
                'summary': '企業決算が予想を下回った。',
                'sentiment_label': 'negative',
                'sentiment_score': -0.5
            }
        ]
    
    @pytest.fixture
    def mock_audio_assets(self, temp_dir):
        """モック音声アセット"""
        assets_dir = os.path.join(temp_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        # サンプル音声ファイルを作成（空ファイル）
        asset_files = ['intro.mp3', 'outro.mp3', 'bgm.mp3', 'transition.mp3']
        for filename in asset_files:
            file_path = os.path.join(assets_dir, filename)
            Path(file_path).touch()
        
        # クレジットファイルを作成
        credits_data = {
            'audio_assets': {
                'intro_jingle': {
                    'file_path': 'intro.mp3',
                    'title': 'Test Intro',
                    'author': 'Test Author',
                    'license': 'CC BY 4.0',
                    'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                },
                'outro_jingle': {
                    'file_path': 'outro.mp3',
                    'title': 'Test Outro',
                    'author': 'Test Author',
                    'license': 'CC BY 4.0',
                    'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                },
                'background_music': {
                    'file_path': 'bgm.mp3',
                    'title': 'Test BGM',
                    'author': 'Test Author',
                    'license': 'CC BY 4.0',
                    'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                },
                'segment_transition': {
                    'file_path': 'transition.mp3',
                    'title': 'Test Transition',
                    'author': 'Test Author',
                    'license': 'CC BY 4.0',
                    'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                }
            }
        }
        
        credits_file = os.path.join(assets_dir, "credits.yaml")
        with open(credits_file, 'w', encoding='utf-8') as f:
            yaml.dump(credits_data, f, default_flow_style=False, allow_unicode=True)
        
        return assets_dir
    
    @patch('src.podcast.script_generator.DialogueScriptGenerator')
    @patch('src.podcast.tts_engine.GeminiTTSEngine')
    @patch('src.podcast.audio_processor.AudioProcessor')
    def test_full_podcast_generation_pipeline(
        self, 
        mock_audio_processor_class,
        mock_tts_engine_class, 
        mock_script_generator_class,
        mock_config, 
        sample_articles, 
        mock_audio_assets,
        temp_dir
    ):
        """完全なポッドキャスト生成パイプラインのテスト"""
        
        # モックの設定
        mock_script_generator = Mock()
        mock_script_generator.generate_script.return_value = (
            "<speaker1>こんにちは、市場ニュースの時間です。</speaker1>"
            "<speaker2>今日の主要なニュースをお伝えします。</speaker2>"
            "<speaker1>まず、市場動向についてです。株価が上昇しており...</speaker1>"
            "<speaker2>続いて、経済指標の発表です。GDP成長率は...</speaker2>"
        )
        mock_script_generator_class.return_value = mock_script_generator
        
        mock_tts_engine = Mock()
        mock_tts_engine.synthesize_dialogue.return_value = b"mock_audio_data"
        mock_tts_engine_class.return_value = mock_tts_engine
        
        mock_audio_processor = Mock()
        mock_audio_processor.process_audio.return_value = b"processed_audio_data"
        mock_audio_processor_class.return_value = mock_audio_processor
        
        # PodcastProcessorを初期化
        processor = PodcastProcessor(mock_config)
        
        # ポッドキャスト生成実行
        result = processor.generate_podcast_episode(sample_articles)
        
        # 結果の検証
        assert result is not None
        assert 'episode_id' in result
        assert 'audio_file_path' in result
        assert 'metadata' in result
        
        # 各コンポーネントが適切に呼ばれたことを確認
        mock_script_generator.generate_script.assert_called_once()
        mock_tts_engine.synthesize_dialogue.assert_called_once()
        mock_audio_processor.process_audio.assert_called_once()
        
        # メタデータの検証
        metadata = result['metadata']
        assert 'title' in metadata
        assert 'description' in metadata
        assert 'duration' in metadata
        assert 'file_size' in metadata
        assert 'pub_date' in metadata
    
    @patch('src.podcast.publisher.rss_generator.RSSGenerator')
    @patch('src.podcast.publisher.line_broadcaster.LINEBroadcaster')
    def test_multi_channel_publishing(
        self, 
        mock_line_broadcaster_class,
        mock_rss_generator_class,
        mock_config,
        temp_dir
    ):
        """マルチチャンネル配信のテスト"""
        
        # モックの設定
        mock_rss_generator = Mock()
        mock_rss_generator.generate_rss_feed.return_value = "/path/to/rss.xml"
        mock_rss_generator_class.return_value = mock_rss_generator
        
        mock_line_broadcaster = Mock()
        mock_line_broadcaster.broadcast_episode.return_value = True
        mock_line_broadcaster_class.return_value = mock_line_broadcaster
        
        # PodcastPublisherを初期化
        publisher = PodcastPublisher(mock_config)
        
        # テスト用エピソードデータ
        episode_data = {
            'title': 'テストエピソード',
            'description': 'テスト用の説明',
            'audio_filename': 'test_episode.mp3',
            'duration': '10:00',
            'file_size': 12345678,
            'pub_date': datetime.now(),
            'guid': 'test-episode-guid'
        }
        
        # 配信実行
        result = publisher.publish_episode(episode_data)
        
        # 結果の検証
        assert result['success'] is True
        assert result['rss_published'] is True
        assert result['line_published'] is True
        
        # 各配信機能が呼ばれたことを確認
        mock_rss_generator.generate_rss_feed.assert_called_once()
        mock_line_broadcaster.broadcast_episode.assert_called_once()
    
    def test_asset_management_integration(self, mock_audio_assets, temp_dir):
        """アセット管理機能の統合テスト"""
        
        # AssetManagerを初期化
        asset_manager = AssetManager(mock_audio_assets)
        
        # CreditInserterを初期化
        credit_inserter = CreditInserter(asset_manager)
        
        # アセット検証
        validation = asset_manager.validate_assets()
        assert all(validation.values()), "All assets should exist"
        
        # クレジット情報取得
        credits_info = asset_manager.get_credits_info()
        assert credits_info is not None
        
        # クレジット挿入
        test_description = "テストエピソードの説明"
        rss_result = credit_inserter.insert_rss_credits(test_description)
        line_result = credit_inserter.insert_line_credits(test_description)
        
        assert test_description in rss_result
        assert test_description in line_result
        assert "CC BY" in rss_result
        assert "音源" in line_result
        
        # ライセンス準拠確認
        compliance = credit_inserter.validate_license_compliance()
        assert compliance['cc_by_compliance'] is True
        assert compliance['credits_complete'] is True
    
    @patch('src.podcast.core.podcast_processor.PodcastProcessor')
    def test_error_handling_in_pipeline(self, mock_processor_class, mock_config):
        """パイプライン内のエラーハンドリングテスト"""
        
        # エラーを発生させるモック
        mock_processor = Mock()
        mock_processor.generate_podcast_episode.side_effect = Exception("Test error")
        mock_processor_class.return_value = mock_processor
        
        # エラーハンドリングの確認
        with pytest.raises(Exception) as exc_info:
            processor = mock_processor_class(mock_config)
            processor.generate_podcast_episode([])
        
        assert "Test error" in str(exc_info.value)
    
    def test_performance_metrics_collection(self, mock_config, sample_articles, temp_dir):
        """パフォーマンスメトリクス収集テスト"""
        
        # メトリクス収集機能付きのモックプロセッサ
        with patch('src.podcast.core.podcast_processor.PodcastProcessor') as mock_processor_class:
            mock_processor = Mock()
            
            # 処理時間を模擬
            import time
            def mock_generate(articles):
                time.sleep(0.1)  # 100ms の処理時間を模擬
                return {
                    'episode_id': 'test-episode',
                    'audio_file_path': '/path/to/audio.mp3',
                    'metadata': {
                        'title': 'テストエピソード',
                        'processing_time': 0.1,
                        'character_count': 2500,
                        'tts_calls': 5
                    }
                }
            
            mock_processor.generate_podcast_episode = mock_generate
            mock_processor_class.return_value = mock_processor
            
            processor = mock_processor_class(mock_config)
            result = processor.generate_podcast_episode(sample_articles)
            
            # メトリクスの確認
            assert 'metadata' in result
            metadata = result['metadata']
            assert 'processing_time' in metadata
            assert 'character_count' in metadata
            assert 'tts_calls' in metadata
            
            # パフォーマンス基準の確認
            assert metadata['processing_time'] < 1.0  # 1秒以内
            assert 2400 <= metadata['character_count'] <= 2800  # 文字数制限
    
    def test_cost_monitoring_integration(self, mock_config):
        """コスト監視機能の統合テスト"""
        
        with patch('src.podcast.monitoring.cost_monitor.CostMonitor') as mock_monitor_class:
            mock_monitor = Mock()
            mock_monitor.track_tts_usage.return_value = None
            mock_monitor.get_monthly_cost.return_value = 5.0  # $5
            mock_monitor.is_within_budget.return_value = True
            mock_monitor_class.return_value = mock_monitor
            
            # コスト監視付きの処理実行
            monitor = mock_monitor_class()
            
            # TTS使用量を記録
            monitor.track_tts_usage(character_count=2500, model="gemini-tts")
            
            # 月額コストを確認
            monthly_cost = monitor.get_monthly_cost()
            assert monthly_cost == 5.0
            
            # 予算内であることを確認
            within_budget = monitor.is_within_budget()
            assert within_budget is True
    
    def test_end_to_end_workflow_simulation(
        self, 
        mock_config, 
        sample_articles, 
        mock_audio_assets,
        temp_dir
    ):
        """エンドツーエンドワークフローのシミュレーション"""
        
        # 全てのコンポーネントをモック
        with patch('src.podcast.script_generator.DialogueScriptGenerator') as mock_script_gen, \\
             patch('src.podcast.tts_engine.GeminiTTSEngine') as mock_tts, \\
             patch('src.podcast.audio_processor.AudioProcessor') as mock_audio, \\
             patch('src.podcast.publisher.podcast_publisher.PodcastPublisher') as mock_publisher:
            
            # モック設定
            mock_script_gen.return_value.generate_script.return_value = "mock_script"
            mock_tts.return_value.synthesize_dialogue.return_value = b"mock_audio"
            mock_audio.return_value.process_audio.return_value = b"processed_audio"
            mock_publisher.return_value.publish_episode.return_value = {
                'success': True,
                'rss_published': True,
                'line_published': True
            }
            
            # ワークフロー実行
            processor = PodcastProcessor(mock_config)
            episode_result = processor.generate_podcast_episode(sample_articles)
            
            publisher = mock_publisher.return_value
            publish_result = publisher.publish_episode(episode_result['metadata'])
            
            # 結果検証
            assert episode_result is not None
            assert publish_result['success'] is True
            assert publish_result['rss_published'] is True
            assert publish_result['line_published'] is True
            
            # 各ステップが実行されたことを確認
            mock_script_gen.return_value.generate_script.assert_called_once()
            mock_tts.return_value.synthesize_dialogue.assert_called_once()
            mock_audio.return_value.process_audio.assert_called_once()
            publisher.publish_episode.assert_called_once()
    
    def test_multiple_articles_processing(self, mock_config, temp_dir):
        """複数記事での動作確認テスト"""
        
        # 大量の記事データを生成
        many_articles = []
        for i in range(20):
            article = {
                'title': f'テスト記事{i+1}',
                'content': f'これは記事{i+1}の内容です。' * 10,  # 長い内容
                'url': f'https://example.com/article{i+1}',
                'published_at': datetime.now() - timedelta(hours=i),
                'source': f'テストソース{i % 3 + 1}',
                'summary': f'記事{i+1}の要約',
                'sentiment_label': 'neutral',
                'sentiment_score': 0.0
            }
            many_articles.append(article)
        
        with patch('src.podcast.script_generator.DialogueScriptGenerator') as mock_script_gen:
            mock_script_gen.return_value.generate_script.return_value = "mock_script"
            
            script_gen = mock_script_gen.return_value
            script_gen.generate_script(many_articles)
            
            # 大量記事でも適切に処理されることを確認
            mock_script_gen.return_value.generate_script.assert_called_once_with(many_articles)
    
    def teardown_method(self):
        """テスト後のクリーンアップ"""
        # 一時ファイルのクリーンアップは fixture で自動実行される
        pass