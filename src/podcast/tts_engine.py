"""
TTS音声合成エンジン

Gemini TTSを使用してスピーカータグ付きの台本を音声データに変換します。
2人の異なる音声での音声合成をサポートします。
"""

import logging
import re
import io
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import google.generativeai as genai
from pydub import AudioSegment
from ..config.app_config import AppConfig, get_config


@dataclass
class SpeakerSegment:
    """音声セグメントを表すデータクラス"""

    speaker_id: int
    text: str
    audio_data: Optional[bytes] = None
    duration_ms: int = 0


@dataclass
class TTSConfig:
    """TTS設定を表すデータクラス"""

    model: str = "gemini-tts"
    voice_config: Dict[int, str] = None
    speaking_rate: float = 1.0
    pitch: float = 0.0
    volume_gain_db: float = 0.0

    def __post_init__(self):
        if self.voice_config is None:
            self.voice_config = {
                1: "ja-JP-Standard-C",  # 男性音声
                2: "ja-JP-Standard-A",  # 女性音声
            }


class GeminiTTSEngine:
    """Gemini TTS音声合成エンジン

    スピーカータグ付きの台本を2人の異なる音声で合成し、
    結合された音声データを生成します。
    """

    def __init__(self, api_key: str, config: Optional[TTSConfig] = None):
        """
        初期化

        Args:
            api_key: Gemini APIキー
            config: TTS設定（省略時はデフォルト）
        """
        self.api_key = api_key
        self.config = config or TTSConfig()
        self.logger = logging.getLogger(__name__)

        # Gemini API設定
        genai.configure(api_key=api_key)

        # アプリケーション設定を読み込み
        app_config = get_config()
        self.cost_limit_usd = app_config.podcast.monthly_cost_limit_usd
        self.current_month_cost = 0.0  # 実際の運用では永続化が必要

        self.logger.info("GeminiTTSEngine を初期化しました")

    def synthesize_dialogue(self, script: str) -> bytes:
        """
        スピーカータグ付き台本を音声データに変換

        Args:
            script: スピーカータグ付きの台本

        Returns:
            合成された音声データ（WAV形式）

        Raises:
            Exception: 音声合成に失敗した場合
        """
        try:
            self.logger.info("対話音声合成を開始")

            # コスト制限チェック
            if self._is_cost_limit_exceeded():
                raise Exception(f"月間コスト制限（${self.cost_limit_usd}）に到達しました")

            # スピーカー別セグメントに分割
            segments = self._extract_speaker_segments(script)
            self.logger.info(f"セグメント数: {len(segments)}")

            # 各セグメントを音声合成
            synthesized_segments = []
            for segment in segments:
                if segment.text.strip():
                    audio_data = self._synthesize_segment(segment)
                    segment.audio_data = audio_data
                    synthesized_segments.append(segment)

            # 音声データを結合
            combined_audio = self._combine_audio_segments(synthesized_segments)

            # コスト計算と記録
            self._update_cost_tracking(script)

            self.logger.info("対話音声合成が完了しました")
            return combined_audio

        except Exception as e:
            self.logger.error(f"音声合成に失敗: {str(e)}")
            raise

    def _extract_speaker_segments(self, script: str) -> List[SpeakerSegment]:
        """
        台本からスピーカー別セグメントを抽出

        Args:
            script: スピーカータグ付き台本

        Returns:
            スピーカーセグメントのリスト
        """
        segments = []

        # スピーカータグパターンに一致する部分を抽出
        pattern = r"<speaker(\d+)>([^<]*)</speaker\d+>:([^<]*?)(?=<speaker\d+>|$)"
        matches = re.findall(pattern, script, re.MULTILINE | re.DOTALL)

        for match in matches:
            speaker_id = int(match[0])
            speaker_name = match[1].strip()
            text = match[2].strip()

            if text:  # 空でないテキストのみ処理
                segments.append(SpeakerSegment(speaker_id=speaker_id, text=text))

        # パターンが一致しない場合の代替処理
        if not segments:
            segments = self._extract_segments_fallback(script)

        return segments

    def _extract_segments_fallback(self, script: str) -> List[SpeakerSegment]:
        """
        スピーカータグパターンが一致しない場合の代替抽出

        Args:
            script: 台本

        Returns:
            スピーカーセグメントのリスト
        """
        segments = []
        lines = script.split("\n")
        current_speaker = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 簡易的なスピーカー判定
            if "speaker1" in line.lower() or "田中" in line:
                current_speaker = 1
            elif "speaker2" in line.lower() or "山田" in line:
                current_speaker = 2

            # タグやスピーカー名を除去してテキストを抽出
            text = re.sub(r"<[^>]*>", "", line)  # HTMLタグ除去
            text = re.sub(r"^[^:]*:", "", text)  # スピーカー名とコロン除去
            text = text.strip()

            if text:
                segments.append(SpeakerSegment(speaker_id=current_speaker, text=text))

                # 話者を交互に切り替え
                current_speaker = 2 if current_speaker == 1 else 1

        return segments

    def _synthesize_segment(self, segment: SpeakerSegment) -> bytes:
        """
        単一セグメントを音声合成

        Args:
            segment: 音声セグメント

        Returns:
            音声データ（WAV形式）
        """
        try:
            # 現在は模擬実装（実際のGemini TTSが利用可能になるまで）
            # TODO: 実際のGemini TTS APIに置き換える際の参考実装：
            # response = genai.synthesize_text(
            #     text=segment.text,
            #     voice_name=voice_name,
            #     speaking_rate=self.config.speaking_rate,
            #     pitch=self.config.pitch,
            #     volume_gain_db=self.config.volume_gain_db
            # )
            # return response.audio_content

            voice_name = self.config.voice_config.get(segment.speaker_id, "ja-JP-Standard-A")

            # 模擬音声データを生成（スピーカーによって異なる特性を付与）
            duration_ms = len(segment.text) * 50  # 文字数 × 50ms の概算

            # スピーカーによって音声特性を変える
            if segment.speaker_id == 1:
                # 男性音声（少し低めの音調）
                silence_audio = AudioSegment.silent(duration=duration_ms)
                # 実際のTTSでは低めの音調設定
            else:
                # 女性音声（少し高めの音調）
                silence_audio = AudioSegment.silent(duration=duration_ms)
                # 実際のTTSでは高めの音調設定

            # WAV形式でエクスポート
            buffer = io.BytesIO()
            silence_audio.export(buffer, format="wav")
            audio_data = buffer.getvalue()

            # セグメント情報を更新
            segment.duration_ms = duration_ms

            self.logger.debug(
                f"セグメント合成完了: speaker{segment.speaker_id} ({voice_name}), {len(segment.text)}文字, {duration_ms}ms"
            )
            return audio_data

        except Exception as e:
            self.logger.error(f"セグメント音声合成に失敗: {str(e)}")
            raise SynthesisError(f"セグメント合成エラー: {str(e)}")

    def _combine_audio_segments(self, segments: List[SpeakerSegment]) -> bytes:
        """
        音声セグメントを結合

        Args:
            segments: 音声セグメントのリスト

        Returns:
            結合された音声データ（WAV形式）
        """
        try:
            combined = AudioSegment.empty()
            total_segments = len(segments)

            for i, segment in enumerate(segments):
                if segment.audio_data:
                    # バイナリデータからAudioSegmentを作成
                    audio_segment = AudioSegment.from_wav(io.BytesIO(segment.audio_data))

                    # セグメント間の無音調整
                    if len(combined) > 0:
                        # 話者が変わる場合は長めの無音、同じ話者なら短め
                        prev_segment = segments[i - 1] if i > 0 else None
                        if prev_segment and prev_segment.speaker_id != segment.speaker_id:
                            # 話者交代時は少し長めの無音
                            combined += AudioSegment.silent(duration=500)  # 500ms
                        else:
                            # 同一話者の継続は短めの無音
                            combined += AudioSegment.silent(duration=200)  # 200ms

                    combined += audio_segment

                    self.logger.debug(
                        f"セグメント結合: {i+1}/{total_segments}, speaker{segment.speaker_id}"
                    )

            # 結合された音声をWAV形式でエクスポート
            buffer = io.BytesIO()
            combined.export(buffer, format="wav")

            total_duration_sec = len(combined) / 1000
            self.logger.info(
                f"音声結合完了: 総再生時間 {total_duration_sec:.2f}秒, {total_segments}セグメント"
            )

            return buffer.getvalue()

        except Exception as e:
            self.logger.error(f"音声結合に失敗: {str(e)}")
            raise SynthesisError(f"音声結合エラー: {str(e)}")

    def _is_cost_limit_exceeded(self) -> bool:
        """
        コスト制限チェック

        Returns:
            制限を超えている場合True
        """
        return self.current_month_cost >= self.cost_limit_usd

    def _update_cost_tracking(self, script: str) -> None:
        """
        コスト追跡を更新

        Args:
            script: 処理された台本
        """
        # 簡易的なコスト計算（文字数ベース）
        char_count = len(script)
        estimated_cost = char_count * 0.000001  # 仮の単価: $0.000001/文字

        self.current_month_cost += estimated_cost

        self.logger.info(f"TTS使用量: {char_count}文字, 推定コスト: ${estimated_cost:.6f}")
        self.logger.info(f"月間累計コスト: ${self.current_month_cost:.6f}/${self.cost_limit_usd}")

    def get_cost_status(self) -> Dict:
        """
        コスト状況を取得

        Returns:
            コスト状況の辞書
        """
        return {
            "current_month_cost": self.current_month_cost,
            "cost_limit": self.cost_limit_usd,
            "usage_percentage": (self.current_month_cost / self.cost_limit_usd) * 100,
            "remaining_budget": self.cost_limit_usd - self.current_month_cost,
        }

    def reset_monthly_cost(self) -> None:
        """
        月間コストをリセット（月次処理用）
        """
        self.current_month_cost = 0.0
        self.logger.info("月間コストをリセットしました")


class TTSError(Exception):
    """TTS関連のエラー"""

    pass


class CostLimitExceededError(TTSError):
    """コスト制限超過エラー"""

    pass


class SynthesisError(TTSError):
    """音声合成エラー"""

    pass
