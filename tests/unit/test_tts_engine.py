"""
GeminiTTSEngine のユニットテスト
"""

import pytest
import io
from unittest.mock import Mock, patch, MagicMock
from pydub import AudioSegment
from src.podcast.tts_engine import (
    GeminiTTSEngine, 
    SpeakerSegment, 
    TTSConfig, 
    TTSError, 
    CostLimitExceededError, 
    SynthesisError
)


class TestSpeakerSegment:
    """SpeakerSegment のテストクラス"""
    
    def test_speaker_segment_creation(self):
        """SpeakerSegment の作成テスト"""
        segment = SpeakerSegment(
            speaker_id=1,
            text="テストメッセージです。"
        )
        
        assert segment.speaker_id == 1
        assert segment.text == "テストメッセージです。"
        assert segment.audio_data is None
        assert segment.duration_ms == 0


class TestTTSConfig:
    """TTSConfig のテストクラス"""
    
    def test_default_config(self):
        """デフォルト設定のテスト"""
        config = TTSConfig()
        
        assert config.model == "gemini-tts"
        assert config.speaking_rate == 1.0
        assert config.pitch == 0.0
        assert config.volume_gain_db == 0.0
        assert 1 in config.voice_config
        assert 2 in config.voice_config
        assert config.voice_config[1] == "ja-JP-Standard-C"
        assert config.voice_config[2] == "ja-JP-Standard-A"
    
    def test_custom_config(self):
        """カスタム設定のテスト"""
        custom_voices = {1: "voice1", 2: "voice2"}
        config = TTSConfig(
            model="custom-tts",
            voice_config=custom_voices,
            speaking_rate=1.2,
            pitch=0.5,
            volume_gain_db=2.0
        )
        
        assert config.model == "custom-tts"
        assert config.voice_config == custom_voices
        assert config.speaking_rate == 1.2
        assert config.pitch == 0.5
        assert config.volume_gain_db == 2.0


class TestGeminiTTSEngine:
    """GeminiTTSEngine のテストクラス"""
    
    @pytest.fixture
    def mock_config(self):
        """設定のモック"""
        config = Mock()
        config.podcast.monthly_cost_limit_usd = 10.0
        return config
    
    @pytest.fixture
    def tts_engine(self, mock_config):
        """GeminiTTSEngine インスタンス"""
        with patch('src.podcast.tts_engine.get_config', return_value=mock_config):
            with patch('google.generativeai.configure'):
                return GeminiTTSEngine("test_api_key")
    
    @pytest.fixture
    def sample_script(self):
        """テスト用台本"""
        return """<speaker1>田中</speaker1>:おはようございます。今日のマーケットニュースをお伝えします。
<speaker2>山田</speaker2>:おはようございます。まず最初にFRBの利上げについてお話しします。
<speaker1>田中</speaker1>:そうですね。金利政策について詳しく見ていきましょう。
<speaker2>山田</speaker2>:ありがとうございました。以上、マーケットニュースでした。"""
    
    def test_init(self, tts_engine):
        """初期化のテスト"""
        assert tts_engine.api_key == "test_api_key"
        assert isinstance(tts_engine.config, TTSConfig)
        assert tts_engine.cost_limit_usd == 10.0
        assert tts_engine.current_month_cost == 0.0
    
    def test_extract_speaker_segments(self, tts_engine, sample_script):
        """スピーカーセグメント抽出のテスト"""
        segments = tts_engine._extract_speaker_segments(sample_script)
        
        # 4つのセグメントが抽出される
        assert len(segments) == 4
        
        # 各セグメントの確認
        assert segments[0].speaker_id == 1
        assert segments[0].text == "おはようございます。今日のマーケットニュースをお伝えします。"
        
        assert segments[1].speaker_id == 2
        assert segments[1].text == "おはようございます。まず最初にFRBの利上げについてお話しします。"
        
        assert segments[2].speaker_id == 1
        assert segments[2].text == "そうですね。金利政策について詳しく見ていきましょう。"
        
        assert segments[3].speaker_id == 2
        assert segments[3].text == "ありがとうございました。以上、マーケットニュースでした。"
    
    def test_extract_segments_fallback(self, tts_engine):
        """代替セグメント抽出のテスト"""
        # タグがない台本
        script_without_tags = """田中: こんにちは
山田: こんばんは
テスト内容です
追加メッセージ"""
        
        segments = tts_engine._extract_segments_fallback(script_without_tags)
        
        assert len(segments) > 0
        # 何らかのセグメントが抽出されることを確認
        assert all(isinstance(seg, SpeakerSegment) for seg in segments)
        assert all(seg.speaker_id in [1, 2] for seg in segments)
    
    def test_synthesize_segment(self, tts_engine):
        """セグメント音声合成のテスト"""
        segment = SpeakerSegment(
            speaker_id=1,
            text="テスト音声です。"
        )
        
        audio_data = tts_engine._synthesize_segment(segment)
        
        # 音声データが生成されている
        assert isinstance(audio_data, bytes)
        assert len(audio_data) > 0
        
        # セグメントの継続時間が設定されている
        assert segment.duration_ms > 0
        
        # WAV形式として読み込み可能
        audio_segment = AudioSegment.from_wav(io.BytesIO(audio_data))
        assert len(audio_segment) > 0
    
    def test_combine_audio_segments(self, tts_engine):
        """音声セグメント結合のテスト"""
        # テスト用セグメントを作成
        segments = [
            SpeakerSegment(speaker_id=1, text="最初のメッセージ"),
            SpeakerSegment(speaker_id=2, text="次のメッセージ"),
            SpeakerSegment(speaker_id=1, text="最後のメッセージ")
        ]
        
        # 各セグメントに音声データを追加
        for segment in segments:
            segment.audio_data = tts_engine._synthesize_segment(segment)
        
        combined_audio = tts_engine._combine_audio_segments(segments)
        
        # 結合された音声データが生成される
        assert isinstance(combined_audio, bytes)
        assert len(combined_audio) > 0
        
        # WAV形式として読み込み可能
        combined_segment = AudioSegment.from_wav(io.BytesIO(combined_audio))
        assert len(combined_segment) > 0
        
        # 結合された音声の長さが個別セグメントの合計より長い（無音が挿入されるため）
        individual_lengths = sum(len(AudioSegment.from_wav(io.BytesIO(seg.audio_data))) for seg in segments)
        assert len(combined_segment) > individual_lengths
    
    def test_cost_tracking(self, tts_engine):
        """コスト追跡のテスト"""
        script = "テスト台本です。" * 100  # 長めの台本
        
        initial_cost = tts_engine.current_month_cost
        tts_engine._update_cost_tracking(script)
        
        # コストが増加している
        assert tts_engine.current_month_cost > initial_cost
        
        # コスト状況を取得
        status = tts_engine.get_cost_status()
        assert 'current_month_cost' in status
        assert 'cost_limit' in status
        assert 'usage_percentage' in status
        assert 'remaining_budget' in status
        
        assert status['current_month_cost'] == tts_engine.current_month_cost
        assert status['cost_limit'] == tts_engine.cost_limit_usd
    
    def test_cost_limit_check(self, tts_engine):
        """コスト制限チェックのテスト"""
        # 制限以下の場合
        tts_engine.current_month_cost = 5.0
        assert not tts_engine._is_cost_limit_exceeded()
        
        # 制限に達した場合
        tts_engine.current_month_cost = 10.0
        assert tts_engine._is_cost_limit_exceeded()
        
        # 制限を超えた場合
        tts_engine.current_month_cost = 15.0
        assert tts_engine._is_cost_limit_exceeded()
    
    def test_synthesize_dialogue_success(self, tts_engine, sample_script):
        """対話音声合成成功のテスト"""
        result = tts_engine.synthesize_dialogue(sample_script)
        
        # 音声データが生成される
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # WAV形式として読み込み可能
        audio_segment = AudioSegment.from_wav(io.BytesIO(result))
        assert len(audio_segment) > 0
        
        # コストが更新される
        assert tts_engine.current_month_cost > 0
    
    def test_synthesize_dialogue_cost_limit_exceeded(self, tts_engine, sample_script):
        """コスト制限超過時の対話音声合成テスト"""
        # コスト制限を超過させる
        tts_engine.current_month_cost = 15.0
        
        with pytest.raises(Exception) as exc_info:
            tts_engine.synthesize_dialogue(sample_script)
        
        assert "月間コスト制限" in str(exc_info.value)
    
    def test_synthesize_dialogue_empty_script(self, tts_engine):
        """空の台本での対話音声合成テスト"""
        empty_script = ""
        
        result = tts_engine.synthesize_dialogue(empty_script)
        
        # 空の音声データが生成される
        assert isinstance(result, bytes)
        # 最低限のWAVヘッダは含まれる
        assert len(result) > 0
    
    def test_reset_monthly_cost(self, tts_engine):
        """月間コストリセットのテスト"""
        # コストを設定
        tts_engine.current_month_cost = 5.0
        
        # リセット
        tts_engine.reset_monthly_cost()
        
        # コストが0になる
        assert tts_engine.current_month_cost == 0.0
    
    def test_voice_config_per_speaker(self, tts_engine):
        """スピーカー別音声設定のテスト"""
        segment1 = SpeakerSegment(speaker_id=1, text="男性音声テスト")
        segment2 = SpeakerSegment(speaker_id=2, text="女性音声テスト")
        
        # 異なるスピーカーで音声合成
        audio1 = tts_engine._synthesize_segment(segment1)
        audio2 = tts_engine._synthesize_segment(segment2)
        
        # 両方とも音声データが生成される
        assert isinstance(audio1, bytes)
        assert isinstance(audio2, bytes)
        assert len(audio1) > 0
        assert len(audio2) > 0
        
        # 設定された継続時間が異なる可能性がある（文字数による）
        assert segment1.duration_ms > 0
        assert segment2.duration_ms > 0
    
    def test_segment_pause_duration(self, tts_engine):
        """セグメント間の無音調整テスト"""
        # 話者が異なるセグメント
        segments_different_speakers = [
            SpeakerSegment(speaker_id=1, text="最初"),
            SpeakerSegment(speaker_id=2, text="次")
        ]
        
        # 同じ話者のセグメント
        segments_same_speaker = [
            SpeakerSegment(speaker_id=1, text="最初"),
            SpeakerSegment(speaker_id=1, text="次")
        ]
        
        # 音声データを生成
        for segments in [segments_different_speakers, segments_same_speaker]:
            for segment in segments:
                segment.audio_data = tts_engine._synthesize_segment(segment)
        
        # 結合してテスト
        combined_different = tts_engine._combine_audio_segments(segments_different_speakers)
        combined_same = tts_engine._combine_audio_segments(segments_same_speaker)
        
        # 両方とも音声データが生成される
        assert len(combined_different) > 0
        assert len(combined_same) > 0
    
    def test_malformed_script_handling(self, tts_engine):
        """不正な形式の台本の処理テスト"""
        malformed_scripts = [
            "<speaker1>田中: 不完全なタグ",
            "speaker2>山田</speaker2>: 開始タグなし",
            "<speaker1>田中</speaker1>",  # テキストなし
            "<speaker3>未知</speaker3>: 不明なスピーカー",
            "普通のテキスト タグなし"
        ]
        
        for script in malformed_scripts:
            # エラーにならずに何らかの結果が返される
            try:
                result = tts_engine.synthesize_dialogue(script)
                assert isinstance(result, bytes)
            except Exception as e:
                # 特定のエラーが発生する可能性もある
                assert isinstance(e, (TTSError, SynthesisError))


class TestTTSErrors:
    """TTS関連エラーのテスト"""
    
    def test_tts_error(self):
        """TTSError のテスト"""
        error = TTSError("テストエラー")
        assert str(error) == "テストエラー"
        assert isinstance(error, Exception)
    
    def test_cost_limit_exceeded_error(self):
        """CostLimitExceededError のテスト"""
        error = CostLimitExceededError("コスト制限超過")
        assert str(error) == "コスト制限超過"
        assert isinstance(error, TTSError)
    
    def test_synthesis_error(self):
        """SynthesisError のテスト"""
        error = SynthesisError("音声合成エラー")
        assert str(error) == "音声合成エラー"
        assert isinstance(error, TTSError)