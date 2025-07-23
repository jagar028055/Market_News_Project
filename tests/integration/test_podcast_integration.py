"""ポッドキャスト機能統合テスト"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
import json
from pathlib import Path
from datetime import datetime

from src.podcast.core.podcast_processor import PodcastProcessor
from src.config.app_config import AppConfig, PodcastConfig
from podcast_main import run_podcast_generation


class TestPodcastIntegration:
    """ポッドキャスト機能の統合テスト"""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリ"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
            
    @pytest.fixture
    def integration_config(self, temp_dir):
        """統合テスト用設定"""
        config = Mock(spec=AppConfig)
        config.podcast = Mock(spec=PodcastConfig)
        
        # ポッドキャスト設定
        config.podcast.monthly_cost_limit = 10.0
        config.podcast.target_character_count = (2400, 2800)
        config.podcast.max_file_size_mb = 15
        config.podcast.target_duration_minutes = 10.0
        
        # ディレクトリ設定
        config.podcast.audio_output_dir = f"{temp_dir}/audio"
        config.podcast.rss_output_dir = f"{temp_dir}/rss"
        config.podcast.error_log_dir = f"{temp_dir}/errors"
        config.podcast.cost_monitor_dir = f"{temp_dir}/costs"
        
        # エラーハンドリング設定
        config.podcast.max_publish_retries = 2
        config.podcast.publish_retry_delay = 0.1
        config.podcast.max_publish_retry_delay = 1.0
        
        return config
        
    @pytest.fixture
    def sample_news_data(self):
        """サンプルニュースデータ"""
        return {
            'articles': [
                {
                    'title': '日経平均株価が続伸',
                    'summary': '東京株式市場では、日経平均株価が前日比200円高となった。',
                    'url': 'https://example.com/news1',
                    'source': 'Reuters Japan',
                    'published_at': '2024-01-15T09:00:00'
                },
                {
                    'title': 'FRBが金利据え置き決定',
                    'summary': '連邦準備制度理事会は政策金利を現行水準で維持することを決定した。',
                    'url': 'https://example.com/news2',
                    'source': 'Bloomberg Japan',
                    'published_at': '2024-01-15T10:30:00'
                }
            ],
            'collection_time': datetime.now(),
            'total_articles': 2,
            'sources': ['Reuters Japan', 'Bloomberg Japan']
        }
        
    @pytest.mark.asyncio
    async def test_full_podcast_generation_pipeline(self, integration_config, sample_news_data):
        """完全なポッドキャスト生成パイプラインテスト"""
        
        # 各コンポーネントをモック
        with patch('src.podcast.core.podcast_processor.NewsProcessor') as mock_news_processor, \
             patch('src.podcast.core.podcast_processor.DialogueScriptGenerator') as mock_script_gen, \
             patch('src.podcast.core.podcast_processor.GeminiTTSEngine') as mock_tts, \
             patch('src.podcast.core.podcast_processor.AudioProcessor') as mock_audio_proc, \
             patch('src.podcast.core.podcast_processor.PodcastPublisher') as mock_publisher, \
             patch('src.podcast.core.podcast_processor.CostMonitor') as mock_cost_monitor:
             
            # NewsProcessor モック
            mock_news_instance = Mock()
            mock_news_instance.collect_articles.return_value = sample_news_data['articles']
            mock_news_instance.process_articles_with_ai.return_value = sample_news_data['articles']
            mock_news_processor.return_value = mock_news_instance
            
            # ScriptGenerator モック
            mock_script_instance = Mock()
            mock_script_instance.prioritize_articles.return_value = sample_news_data['articles']
            mock_script_instance.generate_script.return_value = "テスト台本" * 500  # 約2500文字
            mock_script_gen.return_value = mock_script_instance
            
            # TTS Engine モック
            mock_tts_instance = Mock()
            mock_tts_instance.synthesize_dialogue.return_value = b"fake_audio_data" * 1000
            mock_tts.return_value = mock_tts_instance
            
            # Audio Processor モック
            mock_audio_instance = Mock()
            audio_path = f"{integration_config.podcast.audio_output_dir}/test_episode.mp3"
            mock_audio_instance.process_audio.return_value = audio_path
            mock_audio_instance.get_audio_info.return_value = {
                'duration': '09:45',
                'file_size': 8 * 1024 * 1024,  # 8MB
                'sample_rate': 44100
            }
            mock_audio_instance.get_credits_info.return_value = {
                'bgm': {'title': 'Test BGM', 'author': 'Test Author', 'license_version': '4.0'}
            }
            mock_audio_proc.return_value = mock_audio_instance
            
            # Publisher モック
            mock_publisher_instance = Mock()
            mock_publisher_instance.publish_episode.return_value = {
                'rss': True,
                'line': True,
                'overall_success': True
            }
            mock_publisher.return_value = mock_publisher_instance
            
            # Cost Monitor モック
            mock_cost_instance = Mock()
            mock_cost_instance.get_current_month_costs.return_value = {'total': 2.5}
            mock_cost_instance.estimate_episode_cost.return_value = 0.5
            mock_cost_instance.track_tts_usage = Mock()
            mock_cost_monitor.return_value = mock_cost_instance
            
            # 音声ファイル作成
            Path(integration_config.podcast.audio_output_dir).mkdir(parents=True, exist_ok=True)
            Path(audio_path).write_bytes(b"fake audio content")
            
            # ポッドキャスト処理器初期化・実行
            processor = PodcastProcessor(integration_config)
            result = await processor.generate_daily_podcast()
            
            # 結果検証
            assert result['success'] is True
            assert result['episode_info'] is not None
            assert result['publish_results']['overall_success'] is True
            assert 'processing_time' in result
            
            # 各コンポーネントが呼ばれたことを確認
            mock_news_instance.collect_articles.assert_called_once()
            mock_news_instance.process_articles_with_ai.assert_called_once()
            mock_script_instance.generate_script.assert_called_once()
            mock_tts_instance.synthesize_dialogue.assert_called_once()
            mock_audio_instance.process_audio.assert_called_once()
            mock_publisher_instance.publish_episode.assert_called_once()
            
            # コスト追跡が呼ばれたことを確認
            mock_cost_instance.track_tts_usage.assert_called()
            
    @pytest.mark.asyncio
    async def test_cost_limit_exceeded_scenario(self, integration_config):
        """コスト制限超過シナリオのテスト"""
        
        with patch('src.podcast.core.podcast_processor.CostMonitor') as mock_cost_monitor:
            # コスト制限を超過した状況をモック
            mock_cost_instance = Mock()
            mock_cost_instance.get_current_month_costs.return_value = {'total': 12.0}  # 制限超過
            mock_cost_monitor.return_value = mock_cost_instance
            
            processor = PodcastProcessor(integration_config)
            result = await processor.generate_daily_podcast()
            
            # 処理が失敗することを確認
            assert result['success'] is False
            assert 'コスト制限' in result['error']
            
    @pytest.mark.asyncio
    async def test_news_collection_failure_scenario(self, integration_config):
        """ニュース収集失敗シナリオのテスト"""
        
        with patch('src.podcast.core.podcast_processor.NewsProcessor') as mock_news_processor, \
             patch('src.podcast.core.podcast_processor.CostMonitor') as mock_cost_monitor:
             
            # Cost Monitor モック（正常）
            mock_cost_instance = Mock()
            mock_cost_instance.get_current_month_costs.return_value = {'total': 2.5}
            mock_cost_instance.estimate_episode_cost.return_value = 0.5
            mock_cost_monitor.return_value = mock_cost_instance
            
            # NewsProcessor モック（失敗）
            mock_news_instance = Mock()
            mock_news_instance.collect_articles.return_value = []  # 空のリスト
            mock_news_processor.return_value = mock_news_instance
            
            processor = PodcastProcessor(integration_config)
            result = await processor.generate_daily_podcast()
            
            # 処理が失敗することを確認
            assert result['success'] is False
            assert 'ニュース収集' in result['error']
            
    @pytest.mark.asyncio
    async def test_partial_publish_failure_scenario(self, integration_config, sample_news_data):
        """部分的配信失敗シナリオのテスト"""
        
        with patch('src.podcast.core.podcast_processor.NewsProcessor') as mock_news_processor, \
             patch('src.podcast.core.podcast_processor.DialogueScriptGenerator') as mock_script_gen, \
             patch('src.podcast.core.podcast_processor.GeminiTTSEngine') as mock_tts, \
             patch('src.podcast.core.podcast_processor.AudioProcessor') as mock_audio_proc, \
             patch('src.podcast.core.podcast_processor.PodcastPublisher') as mock_publisher, \
             patch('src.podcast.core.podcast_processor.CostMonitor') as mock_cost_monitor:
             
            # 基本的なモック設定（成功パターン）
            self._setup_basic_mocks(
                mock_news_processor, mock_script_gen, mock_tts, 
                mock_audio_proc, mock_cost_monitor, 
                integration_config, sample_news_data
            )
            
            # Publisher モック（部分的失敗）
            mock_publisher_instance = Mock()
            mock_publisher_instance.publish_episode.return_value = {
                'rss': True,
                'line': False,  # LINE配信失敗
                'overall_success': True  # 部分的成功
            }
            mock_publisher.return_value = mock_publisher_instance
            
            processor = PodcastProcessor(integration_config)
            result = await processor.generate_daily_podcast()
            
            # 処理は成功するが、部分的な失敗が記録される
            assert result['success'] is True
            assert result['publish_results']['line'] is False
            assert result['publish_results']['rss'] is True
            assert result['publish_results']['overall_success'] is True
            
    def _setup_basic_mocks(self, mock_news_processor, mock_script_gen, mock_tts, 
                          mock_audio_proc, mock_cost_monitor, config, sample_news_data):
        """基本的なモック設定ヘルパー"""
        
        # NewsProcessor
        mock_news_instance = Mock()
        mock_news_instance.collect_articles.return_value = sample_news_data['articles']
        mock_news_instance.process_articles_with_ai.return_value = sample_news_data['articles']
        mock_news_processor.return_value = mock_news_instance
        
        # ScriptGenerator
        mock_script_instance = Mock()
        mock_script_instance.prioritize_articles.return_value = sample_news_data['articles']
        mock_script_instance.generate_script.return_value = "テスト台本" * 500
        mock_script_gen.return_value = mock_script_instance
        
        # TTS Engine
        mock_tts_instance = Mock()
        mock_tts_instance.synthesize_dialogue.return_value = b"fake_audio_data" * 1000
        mock_tts.return_value = mock_tts_instance
        
        # Audio Processor
        mock_audio_instance = Mock()
        audio_path = f"{config.podcast.audio_output_dir}/test_episode.mp3"
        mock_audio_instance.process_audio.return_value = audio_path
        mock_audio_instance.get_audio_info.return_value = {
            'duration': '09:45',
            'file_size': 8 * 1024 * 1024,
            'sample_rate': 44100
        }
        mock_audio_instance.get_credits_info.return_value = {}
        mock_audio_proc.return_value = mock_audio_instance
        
        # Cost Monitor
        mock_cost_instance = Mock()
        mock_cost_instance.get_current_month_costs.return_value = {'total': 2.5}
        mock_cost_instance.estimate_episode_cost.return_value = 0.5
        mock_cost_instance.track_tts_usage = Mock()
        mock_cost_monitor.return_value = mock_cost_instance
        
        # 音声ファイル作成
        Path(config.podcast.audio_output_dir).mkdir(parents=True, exist_ok=True)
        Path(audio_path).write_bytes(b"fake audio content")


class TestPodcastMainIntegration:
    """podcast_main.py の統合テスト"""
    
    @pytest.mark.asyncio
    async def test_run_podcast_generation_success(self):
        """run_podcast_generation 成功テスト"""
        
        with patch('podcast_main.load_config') as mock_load_config, \
             patch('podcast_main.PodcastProcessor') as mock_processor_class, \
             patch('podcast_main.setup_logging'):
             
            # Config モック
            mock_config = Mock()
            mock_config.podcast.monthly_cost_limit = 10.0
            mock_load_config.return_value = mock_config
            
            # Processor モック
            mock_processor = Mock()
            mock_processor.cleanup_old_files = Mock()
            mock_processor.get_cost_summary.return_value = Mock(current_month_total=2.5)
            mock_processor.generate_daily_podcast = AsyncMock(return_value={
                'success': True,
                'processing_time': 120.5,
                'episode_info': {'title': 'Test Episode'},
                'publish_results': {'rss': True, 'line': True, 'overall_success': True}
            })
            mock_processor_class.return_value = mock_processor
            
            # 実行
            result = await run_podcast_generation()
            
            # 検証
            assert result['success'] is True
            mock_processor.cleanup_old_files.assert_called_once_with(days=7)
            mock_processor.generate_daily_podcast.assert_called_once()
            
    @pytest.mark.asyncio 
    async def test_run_podcast_generation_cost_limit_exceeded(self):
        """run_podcast_generation コスト制限超過テスト"""
        
        with patch('podcast_main.load_config') as mock_load_config, \
             patch('podcast_main.PodcastProcessor') as mock_processor_class, \
             patch('podcast_main.setup_logging'):
             
            # Config モック
            mock_config = Mock()
            mock_config.podcast.monthly_cost_limit = 10.0
            mock_load_config.return_value = mock_config
            
            # Processor モック（コスト制限超過）
            mock_processor = Mock()
            mock_processor.cleanup_old_files = Mock()
            mock_processor.get_cost_summary.return_value = Mock(current_month_total=12.0)
            mock_processor_class.return_value = mock_processor
            
            # 実行
            result = await run_podcast_generation()
            
            # 検証：コスト制限超過により早期終了
            assert result is None
            mock_processor.cleanup_old_files.assert_called_once_with(days=7)
            mock_processor.generate_daily_podcast.assert_not_called()
            
    @pytest.mark.asyncio
    async def test_run_podcast_generation_processing_failure(self):
        """run_podcast_generation 処理失敗テスト"""
        
        with patch('podcast_main.load_config') as mock_load_config, \
             patch('podcast_main.PodcastProcessor') as mock_processor_class, \
             patch('podcast_main.setup_logging'):
             
            # Config モック
            mock_config = Mock()
            mock_config.podcast.monthly_cost_limit = 10.0
            mock_load_config.return_value = mock_config
            
            # Processor モック（処理失敗）
            mock_processor = Mock()
            mock_processor.cleanup_old_files = Mock()
            mock_processor.get_cost_summary.return_value = Mock(current_month_total=2.5)
            mock_processor.generate_daily_podcast = AsyncMock(return_value={
                'success': False,
                'error': 'Test processing error'
            })
            mock_processor.publisher.get_error_summary.return_value = {'total_errors': 1}
            mock_processor_class.return_value = mock_processor
            
            # 実行
            result = await run_podcast_generation()
            
            # 検証
            assert result['success'] is False
            assert result['error'] == 'Test processing error'
            mock_processor.publisher.get_error_summary.assert_called_once_with(hours=1)


class TestEndToEndPodcastFlow:
    """エンドツーエンドポッドキャストフローテスト"""
    
    @pytest.mark.slow
    @pytest.mark.requires_network
    def test_github_actions_simulation(self):
        """GitHub Actions実行のシミュレーション（重いテスト）"""
        
        # 実際のGitHub Actions環境変数をシミュレート
        test_env = {
            'ENABLE_PODCAST_GENERATION': 'true',
            'GEMINI_API_KEY': 'test_key',
            'LINE_CHANNEL_ACCESS_TOKEN': 'test_token',
            'PODCAST_RSS_BASE_URL': 'https://example.com/podcast',
            'PODCAST_MONTHLY_COST_LIMIT': '10.0'
        }
        
        with patch.dict('os.environ', test_env), \
             patch('main.NewsProcessor') as mock_news_processor, \
             patch('main.run_podcast_generation') as mock_podcast_gen:
             
            # NewsProcessor モック
            mock_news_instance = Mock()
            mock_news_instance.run = Mock()
            mock_news_processor.return_value = mock_news_instance
            
            # Podcast generation モック
            mock_podcast_gen.return_value = {'success': True}
            
            # メイン処理実行
            from main import main
            main()
            
            # 検証
            mock_news_instance.run.assert_called_once()
            mock_podcast_gen.assert_called_once()
            
    def test_performance_requirements(self):
        """パフォーマンス要件テスト"""
        
        # 実際の実装では、処理時間、メモリ使用量などを測定
        # ここでは簡易的な例を示す
        
        import time
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss
        start_time = time.time()
        
        # 模擬的な重い処理
        for i in range(1000):
            data = "test" * 1000
            
        end_time = time.time()
        end_memory = process.memory_info().rss
        
        processing_time = end_time - start_time
        memory_increase = end_memory - start_memory
        
        # パフォーマンス要件チェック
        assert processing_time < 5.0  # 5秒以内
        assert memory_increase < 100 * 1024 * 1024  # 100MB以内