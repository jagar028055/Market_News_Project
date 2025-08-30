# -*- coding: utf-8 -*-
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
from io import BytesIO

# プロジェクトルートをパスに追加
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.podcast.tts_engine import GeminiTTSEngine, TTSConfig, SynthesisError
from pydub import AudioSegment

@pytest.mark.unit
class TestGeminiTTSEngine:
    """Gemini TTS Engineのユニットテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.api_key = "test_api_key"
        self.config = TTSConfig()

    @patch('google.generativeai.configure')
    def test_initialization(self, mock_configure):
        """エンジンの初期化テスト"""
        engine = GeminiTTSEngine(api_key=self.api_key, config=self.config)
        assert engine.api_key == self.api_key
        assert engine.config == self.config
        mock_configure.assert_called_once_with(api_key=self.api_key)

    def test_extract_speaker_segments(self):
        """台本からのセグメント抽出テスト"""
        engine = GeminiTTSEngine(api_key=self.api_key)
        script = """
        <speaker1>田中</speaker1>:こんにちは。
        <speaker2>山田</speaker2>:こんにちは、山田です。
        <speaker1>田中</speaker1>:今日のニュースです。
        """
        segments = engine._extract_speaker_segments(script)
        assert len(segments) == 3
        assert segments[0].speaker_id == 1
        assert segments[0].text == "こんにちは。"
        assert segments[1].speaker_id == 2
        assert segments[1].text == "こんにちは、山田です。"
        assert segments[2].speaker_id == 1
        assert segments[2].text == "今日のニュースです。"

    @patch.object(GeminiTTSEngine, '_synthesize_segment')
    def test_synthesize_dialogue_success(self, mock_synthesize):
        """対話全体の音声合成成功テスト"""
        # モックの音声データを準備
        mock_audio_data = AudioSegment.silent(duration=1000).export(format="wav").read()
        mock_synthesize.return_value = mock_audio_data

        engine = GeminiTTSEngine(api_key=self.api_key)
        script = "<speaker1>田中</speaker1>:テスト"

        result = engine.synthesize_dialogue(script)

        assert isinstance(result, bytes)
        assert len(result) > 0
        mock_synthesize.assert_called()

    def test_synthesize_dialogue_cost_limit_exceeded(self):
        """コスト上限超過テスト"""
        engine = GeminiTTSEngine(api_key=self.api_key)
        engine.current_month_cost = engine.cost_limit_usd + 1.0 # 上限超え

        with pytest.raises(Exception, match="月間コスト制限"):
            engine.synthesize_dialogue("<speaker1>田中</speaker1>:テスト")

    @patch('pydub.AudioSegment.silent')
    def test_synthesize_segment_mocked(self, mock_silent):
        """単一セグメントの音声合成テスト（pydubモック）"""

        def mock_export(buffer, format):
            buffer.write(b"mock_wav_data")
            return buffer

        mock_audio = MagicMock()
        mock_audio.export.side_effect = mock_export
        mock_silent.return_value = mock_audio

        engine = GeminiTTSEngine(api_key=self.api_key)
        segment = engine._extract_speaker_segments("<speaker1>田中</speaker1>:テスト")[0]
        
        audio_data = engine._synthesize_segment(segment)
        
        assert audio_data == b"mock_wav_data"
        mock_silent.assert_called()

    def test_combine_audio_segments(self):
        """音声セグメント結合テスト"""
        engine = GeminiTTSEngine(api_key=self.api_key)
        
        # 2つの無音セグメントを作成
        silent_1s = AudioSegment.silent(duration=1000)
        data1 = BytesIO()
        silent_1s.export(data1, format="wav")

        silent_2s = AudioSegment.silent(duration=2000)
        data2 = BytesIO()
        silent_2s.export(data2, format="wav")

        segments = [
            MagicMock(audio_data=data1.getvalue(), speaker_id=1),
            MagicMock(audio_data=data2.getvalue(), speaker_id=2)
        ]

        combined_data = engine._combine_audio_segments(segments)
        combined_audio = AudioSegment.from_wav(BytesIO(combined_data))

        # 1000ms (seg1) + 500ms (pause) + 2000ms (seg2) = 3500ms
        assert abs(len(combined_audio) - 3500) < 50 # 50ms程度の誤差は許容