"""
AudioProcessor のユニットテスト
"""

import pytest
import io
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# pydubのモック（テスト環境で利用できない場合）
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    # モッククラスを作成
    class AudioSegment:
        def __init__(self, data=None):
            self.data = data or b"mock_audio_data"
            self._duration = 10000  # 10秒
            self._frame_rate = 44100
            self._channels = 2
            self._max_dbfs = -10.0
        
        @classmethod
        def from_wav(cls, file):
            return cls()
        
        @classmethod
        def from_file(cls, file):
            return cls()
        
        def set_frame_rate(self, rate):
            self._frame_rate = rate
            return self
        
        def set_channels(self, channels):
            self._channels = channels
            return self
        
        def __len__(self):
            return self._duration
        
        def __add__(self, db):
            return self
        
        def __getitem__(self, key):
            return self
        
        def fade_in(self, duration):
            return self
        
        def fade_out(self, duration):
            return self
        
        def overlay(self, other):
            return self
        
        def high_pass_filter(self, freq):
            return self
        
        def export(self, file, format="wav", **kwargs):
            if hasattr(file, 'write'):
                file.write(self.data)
            else:
                with open(file, 'wb') as f:
                    f.write(self.data)
        
        @property
        def max_dBFS(self):
            return self._max_dbfs
        
        @staticmethod
        def empty():
            return AudioSegment()
        
        @staticmethod
        def silent(duration=1000):
            return AudioSegment()

from src.podcast.audio_processor import (
    AudioProcessor, 
    AudioAssets, 
    AudioProcessingResult, 
    AudioProcessingError
)


class TestAudioAssets:
    """AudioAssets のテストクラス"""
    
    def test_audio_assets_creation(self):
        """AudioAssets の作成テスト"""
        credits = {"intro": "CC-BY License"}
        assets = AudioAssets(
            intro_jingle="intro.mp3",
            outro_jingle="outro.mp3",
            background_music="bgm.mp3",
            segment_transition="transition.mp3",
            credits=credits
        )
        
        assert assets.intro_jingle == "intro.mp3"
        assert assets.outro_jingle == "outro.mp3"
        assert assets.background_music == "bgm.mp3"
        assert assets.segment_transition == "transition.mp3"
        assert assets.credits == credits


class TestAudioProcessingResult:
    """AudioProcessingResult のテストクラス"""
    
    def test_audio_processing_result_creation(self):
        """AudioProcessingResult の作成テスト"""
        result = AudioProcessingResult(
            audio_data=b"test_audio",
            duration_seconds=600,
            file_size_bytes=1024000,
            format="mp3",
            sample_rate=44100,
            channels=2,
            bitrate="128k",
            lufs_level=-16.0,
            peak_level=-1.0
        )
        
        assert result.audio_data == b"test_audio"
        assert result.duration_seconds == 600
        assert result.file_size_bytes == 1024000
        assert result.format == "mp3"
        assert result.sample_rate == 44100
        assert result.channels == 2
        assert result.bitrate == "128k"
        assert result.lufs_level == -16.0
        assert result.peak_level == -1.0


class TestAudioProcessor:
    """AudioProcessor のテストクラス"""
    
    @pytest.fixture
    def temp_assets_dir(self):
        """テスト用の一時アセットディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir) / "assets"
            assets_dir.mkdir()
            
            # ダミーの音声ファイルを作成
            for filename in ["intro_jingle.mp3", "outro_jingle.mp3", "background_music.mp3", "segment_transition.mp3"]:
                (assets_dir / filename).write_bytes(b"dummy_audio_data")
            
            yield str(assets_dir)
    
    @pytest.fixture
    def audio_processor(self, temp_assets_dir):
        """AudioProcessor インスタンス"""
        with patch('src.podcast.audio_processor.PYDUB_AVAILABLE', True):
            return AudioProcessor(temp_assets_dir)
    
    @pytest.fixture
    def sample_tts_audio(self):
        """テスト用TTS音声データ"""
        # WAVヘッダーを含むダミーデータ
        wav_header = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00\x44\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x08\x00\x00'
        audio_data = b'\x00' * 2048  # ダミー音声データ
        return wav_header + audio_data
    
    def test_init_success(self, temp_assets_dir):
        """正常な初期化のテスト"""
        with patch('src.podcast.audio_processor.PYDUB_AVAILABLE', True):
            processor = AudioProcessor(temp_assets_dir)
            
            assert processor.assets_path == Path(temp_assets_dir)
            assert processor.target_lufs == -16.0
            assert processor.peak_target == -1.0
            assert processor.target_duration_minutes == 10.0
            assert processor.max_file_size_mb == 15
            assert isinstance(processor.assets, AudioAssets)
    
    def test_init_pydub_not_available(self, temp_assets_dir):
        """pydub未インストール時の初期化テスト"""
        with patch('src.podcast.audio_processor.PYDUB_AVAILABLE', False):
            with pytest.raises(AudioProcessingError) as exc_info:
                AudioProcessor(temp_assets_dir)
            
            assert "pydubライブラリが必要です" in str(exc_info.value)
    
    def test_load_assets(self, audio_processor):
        """音声アセット読み込みのテスト"""
        assets = audio_processor.assets
        
        assert assets.intro_jingle.endswith("intro_jingle.mp3")
        assert assets.outro_jingle.endswith("outro_jingle.mp3")
        assert assets.background_music.endswith("background_music.mp3")
        assert assets.segment_transition.endswith("segment_transition.mp3")
        assert "CC-BY" in assets.credits["intro_jingle"]
    
    def test_load_assets_missing_files(self):
        """音声アセットファイルが存在しない場合のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_dir = Path(temp_dir) / "empty"
            empty_dir.mkdir()
            
            with patch('src.podcast.audio_processor.PYDUB_AVAILABLE', True):
                processor = AudioProcessor(str(empty_dir))
                
                # ファイルが存在しなくてもエラーにならない
                assert isinstance(processor.assets, AudioAssets)
    
    @patch('src.podcast.audio_processor.AudioSegment')
    def test_load_audio_from_bytes(self, mock_audio_segment, audio_processor, sample_tts_audio):
        """バイト列からの音声読み込みテスト"""
        mock_audio = Mock()
        mock_audio_segment.from_wav.return_value = mock_audio
        
        result = audio_processor._load_audio_from_bytes(sample_tts_audio)
        
        assert result == mock_audio
        mock_audio_segment.from_wav.assert_called_once()
    
    @patch('src.podcast.audio_processor.AudioSegment')
    def test_load_audio_from_bytes_error(self, mock_audio_segment, audio_processor):
        """音声読み込みエラーのテスト"""
        mock_audio_segment.from_wav.side_effect = Exception("Invalid audio data")
        
        with pytest.raises(AudioProcessingError) as exc_info:
            audio_processor._load_audio_from_bytes(b"invalid_data")
        
        assert "音声データ読み込みエラー" in str(exc_info.value)
    
    @patch('src.podcast.audio_processor.AudioSegment')
    def test_prepare_main_audio(self, mock_audio_segment, audio_processor):
        """メイン音声の基本調整テスト"""
        mock_audio = Mock()
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.high_pass_filter.return_value = mock_audio
        
        with patch('src.podcast.audio_processor.compress_dynamic_range', return_value=mock_audio):
            result = audio_processor._prepare_main_audio(mock_audio)
            
            mock_audio.set_frame_rate.assert_called_with(44100)
            mock_audio.set_channels.assert_called_with(2)
            mock_audio.high_pass_filter.assert_called_with(80)
            assert result == mock_audio
    
    @patch('src.podcast.audio_processor.PYLOUDNORM_AVAILABLE', False)
    @patch('src.podcast.audio_processor.normalize')
    def test_normalize_simple(self, mock_normalize, audio_processor):
        """簡易音量正規化のテスト"""
        mock_audio = Mock()
        mock_audio.dBFS = -20.0
        mock_normalized = Mock()
        mock_normalize.return_value = mock_normalized
        
        result = audio_processor._normalize_simple(mock_audio)
        
        mock_normalize.assert_called_once_with(mock_audio, headroom=1.0)
        assert result == mock_normalized
    
    @patch('src.podcast.audio_processor.AudioSegment')
    def test_add_intro_outro_success(self, mock_audio_segment, audio_processor):
        """イントロ・アウトロ追加成功のテスト"""
        mock_main_audio = Mock()
        mock_main_audio.__len__ = Mock(return_value=10000)  # 10秒
        
        mock_intro = Mock()
        mock_intro.__len__ = Mock(return_value=3000)  # 3秒
        mock_intro.set_frame_rate.return_value = mock_intro
        mock_intro.set_channels.return_value = mock_intro
        mock_intro.__add__ = Mock(return_value=mock_intro)
        mock_intro.fade_in.return_value = mock_intro
        mock_intro.fade_out.return_value = mock_intro
        mock_intro.__getitem__ = Mock(return_value=mock_intro)
        
        mock_outro = Mock()
        mock_outro.__len__ = Mock(return_value=2000)  # 2秒
        mock_outro.set_frame_rate.return_value = mock_outro
        mock_outro.set_channels.return_value = mock_outro
        mock_outro.__add__ = Mock(return_value=mock_outro)
        mock_outro.fade_in.return_value = mock_outro
        mock_outro.fade_out.return_value = mock_outro
        mock_outro.__getitem__ = Mock(return_value=mock_outro)
        
        mock_audio_segment.from_file.side_effect = [mock_intro, mock_outro]
        
        # ファイル存在をモック
        with patch('pathlib.Path.exists', return_value=True):
            result = audio_processor._add_intro_outro(mock_main_audio)
            
            # from_fileが2回呼ばれる（intro, outro）
            assert mock_audio_segment.from_file.call_count == 2
    
    @patch('src.podcast.audio_processor.AudioSegment')
    def test_add_intro_outro_missing_files(self, mock_audio_segment, audio_processor):
        """イントロ・アウトロファイルが存在しない場合のテスト"""
        mock_main_audio = Mock()
        
        # ファイルが存在しない場合
        with patch('pathlib.Path.exists', return_value=False):
            result = audio_processor._add_intro_outro(mock_main_audio)
            
            # 元の音声がそのまま返される
            assert result == mock_main_audio
            mock_audio_segment.from_file.assert_not_called()
    
    @patch('src.podcast.audio_processor.AudioSegment')
    def test_add_background_music_success(self, mock_audio_segment, audio_processor):
        """BGM統合成功のテスト"""
        mock_main_audio = Mock()
        mock_main_audio.__len__ = Mock(return_value=10000)  # 10秒
        mock_main_audio.overlay.return_value = mock_main_audio
        
        mock_bgm = Mock()
        mock_bgm.__len__ = Mock(return_value=15000)  # 15秒（長い）
        mock_bgm.set_frame_rate.return_value = mock_bgm
        mock_bgm.set_channels.return_value = mock_bgm
        mock_bgm.__add__ = Mock(return_value=mock_bgm)
        mock_bgm.__getitem__ = Mock(return_value=mock_bgm)
        mock_bgm.fade_in.return_value = mock_bgm
        mock_bgm.fade_out.return_value = mock_bgm
        
        mock_audio_segment.from_file.return_value = mock_bgm
        
        # ファイル存在をモック
        with patch('pathlib.Path.exists', return_value=True):
            result = audio_processor._add_background_music(mock_main_audio)
            
            mock_audio_segment.from_file.assert_called_once()
            mock_main_audio.overlay.assert_called_once()
    
    @patch('src.podcast.audio_processor.AudioSegment')
    def test_add_background_music_missing_file(self, mock_audio_segment, audio_processor):
        """BGMファイルが存在しない場合のテスト"""
        mock_main_audio = Mock()
        
        # ファイルが存在しない場合
        with patch('pathlib.Path.exists', return_value=False):
            result = audio_processor._add_background_music(mock_main_audio)
            
            # 元の音声がそのまま返される
            assert result == mock_main_audio
            mock_audio_segment.from_file.assert_not_called()
    
    def test_adjust_duration_normal(self, audio_processor):
        """正常な再生時間の調整テスト"""
        mock_audio = Mock()
        mock_audio.__len__ = Mock(return_value=9 * 60 * 1000)  # 9分
        
        result = audio_processor._adjust_duration(mock_audio)
        
        # 9分は制限内なのでそのまま返される
        assert result == mock_audio
    
    def test_adjust_duration_too_long(self, audio_processor):
        """長すぎる音声の調整テスト"""
        mock_audio = Mock()
        mock_audio.__len__ = Mock(return_value=12 * 60 * 1000)  # 12分
        mock_audio.__getitem__ = Mock(return_value=mock_audio)
        mock_audio.fade_out.return_value = mock_audio
        
        result = audio_processor._adjust_duration(mock_audio)
        
        # 音声がカットされる
        mock_audio.__getitem__.assert_called()
        mock_audio.fade_out.assert_called_with(2000)
    
    def test_determine_optimal_bitrate(self, audio_processor):
        """最適ビットレート決定のテスト"""
        mock_audio = Mock()
        mock_audio.__len__ = Mock(return_value=10 * 60 * 1000)  # 10分
        
        bitrate = audio_processor._determine_optimal_bitrate(mock_audio)
        
        # 10分の音声なら128kで約9.4MBなので128kが選ばれる
        assert bitrate in ["128k", "96k", "80k", "64k"]
    
    @patch('src.podcast.audio_processor.AudioSegment')
    def test_optimize_file_size(self, mock_audio_segment, audio_processor):
        """ファイルサイズ最適化のテスト"""
        mock_audio = Mock()
        mock_buffer = Mock()
        mock_buffer.getvalue.return_value = b"optimized_audio_data"
        
        with patch('io.BytesIO', return_value=mock_buffer):
            result = audio_processor._optimize_file_size(mock_audio)
            
            assert result == b"optimized_audio_data"
            mock_audio.export.assert_called_once()
    
    def test_measure_audio_levels_without_pyloudnorm(self, audio_processor):
        """pyloudnorm無しでの音声レベル測定テスト"""
        mock_audio = Mock()
        mock_audio.max_dBFS = -12.5
        
        with patch('src.podcast.audio_processor.PYLOUDNORM_AVAILABLE', False):
            lufs, peak = audio_processor._measure_audio_levels(mock_audio)
            
            assert lufs is None
            assert peak == -12.5
    
    @patch('src.podcast.audio_processor.AudioSegment')
    def test_process_audio_success(self, mock_audio_segment, audio_processor, sample_tts_audio):
        """音声処理成功のテスト"""
        mock_audio = Mock()
        mock_audio.__len__ = Mock(return_value=10 * 60 * 1000)  # 10分
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.high_pass_filter.return_value = mock_audio
        mock_audio.fade_in.return_value = mock_audio
        mock_audio.fade_out.return_value = mock_audio
        mock_audio.overlay.return_value = mock_audio
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.__getitem__ = Mock(return_value=mock_audio)
        mock_audio.max_dBFS = -10.0
        
        mock_buffer = Mock()
        mock_buffer.getvalue.return_value = b"final_audio_data" * 1000  # 適切なサイズ
        
        mock_audio_segment.from_wav.return_value = mock_audio
        mock_audio_segment.from_file.return_value = mock_audio
        
        with patch('io.BytesIO', return_value=mock_buffer):
            with patch('src.podcast.audio_processor.compress_dynamic_range', return_value=mock_audio):
                with patch('src.podcast.audio_processor.normalize', return_value=mock_audio):
                    with patch('pathlib.Path.exists', return_value=False):  # アセットファイルなし
                        result = audio_processor.process_audio(sample_tts_audio)
        
        assert isinstance(result, AudioProcessingResult)
        assert result.format == "mp3"
        assert result.sample_rate == 44100
        assert result.channels == 2
        assert len(result.audio_data) > 0
    
    @patch('src.podcast.audio_processor.AudioSegment')
    def test_process_audio_error(self, mock_audio_segment, audio_processor, sample_tts_audio):
        """音声処理エラーのテスト"""
        mock_audio_segment.from_wav.side_effect = Exception("Processing error")
        
        with pytest.raises(AudioProcessingError) as exc_info:
            audio_processor.process_audio(sample_tts_audio)
        
        assert "音声処理エラー" in str(exc_info.value)
    
    def test_get_credits_text(self, audio_processor):
        """クレジット文字列取得のテスト"""
        credits_text = audio_processor.get_credits_text()
        
        assert "音声素材:" in credits_text
        assert "CC-BY" in credits_text
        assert "intro_jingle" in credits_text
        assert "outro_jingle" in credits_text
        assert "background_music" in credits_text
        assert "segment_transition" in credits_text


class TestAudioProcessingError:
    """AudioProcessingError のテスト"""
    
    def test_audio_processing_error(self):
        """AudioProcessingError のテスト"""
        error = AudioProcessingError("テストエラー")
        assert str(error) == "テストエラー"
        assert isinstance(error, Exception)


class TestIntegration:
    """統合テスト"""
    
    @pytest.fixture
    def integration_assets_dir(self):
        """統合テスト用アセットディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir) / "assets"
            assets_dir.mkdir()
            
            # より現実的なダミーファイルを作成
            for filename in ["intro_jingle.mp3", "outro_jingle.mp3", "background_music.mp3"]:
                (assets_dir / filename).write_bytes(b"dummy" * 1000)
            
            yield str(assets_dir)
    
    @patch('src.podcast.audio_processor.PYDUB_AVAILABLE', True)
    def test_full_audio_processing_pipeline(self, integration_assets_dir):
        """完全な音声処理パイプラインのテスト"""
        processor = AudioProcessor(integration_assets_dir)
        
        # より現実的なWAVデータを作成
        sample_audio = b'RIFF' + b'\x00' * 100 + b'WAVE' + b'\x00' * 1000
        
        # モックを使用して完全なパイプラインをテスト
        with patch.object(processor, '_load_audio_from_bytes') as mock_load:
            with patch.object(processor, '_prepare_main_audio') as mock_prepare:
                with patch.object(processor, '_add_intro_outro') as mock_intro:
                    with patch.object(processor, '_add_background_music') as mock_bgm:
                        with patch.object(processor, '_normalize_audio') as mock_normalize:
                            with patch.object(processor, '_adjust_duration') as mock_duration:
                                with patch.object(processor, '_finalize_audio') as mock_finalize:
                                    
                                    # モックの戻り値を設定
                                    mock_audio = Mock()
                                    mock_load.return_value = mock_audio
                                    mock_prepare.return_value = mock_audio
                                    mock_intro.return_value = mock_audio
                                    mock_bgm.return_value = mock_audio
                                    mock_normalize.return_value = mock_audio
                                    mock_duration.return_value = mock_audio
                                    
                                    expected_result = AudioProcessingResult(
                                        audio_data=b"test_result",
                                        duration_seconds=600,
                                        file_size_bytes=1024000,
                                        format="mp3",
                                        sample_rate=44100,
                                        channels=2,
                                        bitrate="128k"
                                    )
                                    mock_finalize.return_value = expected_result
                                    
                                    # テスト実行
                                    result = processor.process_audio(sample_audio)
                                    
                                    # 各ステップが呼ばれることを確認
                                    mock_load.assert_called_once_with(sample_audio)
                                    mock_prepare.assert_called_once_with(mock_audio)
                                    mock_intro.assert_called_once_with(mock_audio)
                                    mock_bgm.assert_called_once_with(mock_audio)
                                    mock_normalize.assert_called_once_with(mock_audio)
                                    mock_duration.assert_called_once_with(mock_audio)
                                    mock_finalize.assert_called_once_with(mock_audio)
                                    
                                    assert result == expected_result