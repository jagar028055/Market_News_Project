# -*- coding: utf-8 -*-

"""
Gemini TTS エンジン
高品質な音声合成とプロフェッショナルなポッドキャスト音声生成
"""

try:
    from google.cloud import texttospeech
    GOOGLE_CLOUD_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_TTS_AVAILABLE = False
import logging
import io
import time
import json
from typing import Dict, Any, Optional, Union
from pathlib import Path
import tempfile
import os


class GeminiTTSEngine:
    """Google Cloud Text-to-Speech エンジンクラス（旧Gemini TTS）"""

    # 音声品質設定
    DEFAULT_VOICE_CONFIG = {
        "voice_name": "ja-JP-Neural2-D",  # 日本語女性音声（自然で聞きやすい）
        "speaking_rate": 1.0,  # 通常の速度
        "pitch": 0.0,  # 標準ピッチ
        "volume_gain_db": 0.0,  # 音量調整なし（後処理で調整）
        "audio_encoding": "MP3",  # MP3出力
        "sample_rate_hertz": 44100,  # 高品質サンプリングレート
    }

    # 発音修正辞書
    PRONUNCIATION_FIXES = {
        # 金融用語
        "FRB": "エフアールビー",
        "FOMC": "エフオーエムシー",
        "GDP": "ジーディーピー",
        "CPI": "シーピーアイ",
        "S&P500": "エスアンドピー ごひゃく",
        "NASDAQ": "ナスダック",
        "NYSE": "ニューヨーク証券取引所",
        "AI": "エーアイ",
        "API": "エーピーアイ",
        "CEO": "シーイーオー",
        "IPO": "アイピーオー",
        # 数値・記号
        "%": "パーセント",
        "$": "ドル",
        "¥": "円",
        "&": "アンド",
        ".": "てん",
        # マークダウン記号の除去（シャープ問題対策）
        "###": "",
        "##": "",
        "#": "",
        "**": "",
        "*": "",
        "---": "",
        "___": "",
        # 月名の読み上げ改善
        "1月": "いちがつ",
        "2月": "にがつ",
        "3月": "さんがつ",
        "4月": "しがつ",
        "5月": "ごがつ",
        "6月": "ろくがつ",
        "7月": "しちがつ",
        "8月": "はちがつ",
        "9月": "くがつ",
        "10月": "じゅうがつ",
        "11月": "じゅういちがつ",
        "12月": "じゅうにがつ",
    }

    def __init__(
        self, credentials_json: Optional[str] = None, voice_config: Optional[Dict[str, Any]] = None
    ):
        """
        初期化

        Args:
            credentials_json: Google Cloud認証情報JSON（文字列またはファイルパス）
            voice_config: 音声設定（オプション）
            
        Raises:
            ValueError: Google Cloud TTSライブラリが利用できない場合
        """
        if not GOOGLE_CLOUD_TTS_AVAILABLE:
            raise ValueError("Google Cloud TTSライブラリが利用できません: pip install google-cloud-texttospeech")
            
        self.voice_config = voice_config or self.DEFAULT_VOICE_CONFIG.copy()
        self.logger = logging.getLogger(__name__)

        # Google Cloud TTS クライアントを初期化
        try:
            if credentials_json:
                # JSON文字列の場合
                if credentials_json.startswith("{"):
                    import tempfile

                    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                        f.write(credentials_json)
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name
                else:
                    # ファイルパスの場合
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_json

            self.client = texttospeech.TextToSpeechClient()
            self.logger.info("Google Cloud TTS client initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize Google Cloud TTS client: {e}")
            raise ValueError(f"Google Cloud TTS client initialization failed: {e}")

    def synthesize_dialogue(
        self, script: str, output_path: Optional[Union[str, Path]] = None
    ) -> bytes:
        """
        台本から音声を合成

        Args:
            script: 台本テキスト
            output_path: 出力ファイルパス（オプション）

        Returns:
            bytes: 合成された音声データ

        Raises:
            Exception: 音声合成に失敗した場合
        """
        if not script or not script.strip():
            raise ValueError("台本が空です")

        self.logger.info(f"音声合成開始 - {len(script)}文字")

        try:
            # 発音の前処理
            processed_script = self._preprocess_pronunciation(script)

            # セグメント分割（長い台本を適切な長さに分割）
            segments = self._split_into_segments(processed_script)

            # 各セグメントを合成
            audio_segments = []
            for i, segment in enumerate(segments, 1):
                self.logger.info(f"セグメント {i}/{len(segments)} を合成中...")
                audio_data = self._synthesize_segment(segment)
                audio_segments.append(audio_data)

                # API制限を考慮した適切な間隔
                if i < len(segments):
                    time.sleep(0.5)

            # 音声セグメントを結合
            combined_audio = self._combine_audio_segments(audio_segments)

            # ファイルに保存（指定された場合）
            if output_path:
                self._save_audio_file(combined_audio, output_path)

            self.logger.info(f"音声合成完了 - {len(combined_audio)}バイト")
            return combined_audio

        except Exception as e:
            self.logger.error(f"音声合成エラー: {e}")
            # フォールバック処理を無効化 - 本当のエラーを表面化
            raise e

    def _preprocess_pronunciation(self, script: str) -> str:
        """
        発音を改善するための前処理

        Args:
            script: 元の台本

        Returns:
            str: 発音改善済みの台本
        """
        processed = script

        # 発音修正辞書を適用
        for original, corrected in self.PRONUNCIATION_FIXES.items():
            processed = processed.replace(original, corrected)

        # 数値の読み上げ改善
        processed = self._improve_number_pronunciation(processed)

        # 英語単語の読み上げ改善
        processed = self._improve_english_pronunciation(processed)

        # マークダウン・HTML記法の除去（強化版）
        processed = self._clean_markup_syntax(processed)

        return processed

    def _improve_number_pronunciation(self, text: str) -> str:
        """
        数値の読み上げを改善

        Args:
            text: 元のテキスト

        Returns:
            str: 数値読み上げ改善済みテキスト
        """
        import re

        # パーセンテージの処理
        text = re.sub(r"(\d+(?:\.\d+)?)%", r"\1パーセント", text)

        # 金額の処理
        text = re.sub(r"(\d+(?:,\d{3})*)\円", r"\1えん", text)
        text = re.sub(r"\$(\d+(?:,\d{3})*(?:\.\d+)?)", r"\1ドル", text)

        # 大きな数値の読み上げ改善（兆、億、万）
        text = re.sub(r"(\d+)\兆", r"\1ちょう", text)
        text = re.sub(r"(\d+)\億", r"\1おく", text)
        text = re.sub(r"(\d+)\万", r"\1まん", text)

        return text

    def _improve_english_pronunciation(self, text: str) -> str:
        """
        英語単語の読み上げを改善

        Args:
            text: 元のテキスト

        Returns:
            str: 英語読み上げ改善済みテキスト
        """
        # よく使用される英語単語のカタカナ読みマッピング
        english_words = {
            "Apple": "アップル",
            "Microsoft": "マイクロソフト",
            "Google": "グーグル",
            "Amazon": "アマゾン",
            "Meta": "メタ",
            "Tesla": "テスラ",
            "NVIDIA": "エヌビディア",
            "Intel": "インテル",
            "IBM": "アイビーエム",
            "Oracle": "オラクル",
        }

        for english, katakana in english_words.items():
            text = text.replace(english, katakana)

        return text

    def _clean_markup_syntax(self, text: str) -> str:
        """
        マークダウン・HTML記法の除去（シャープ問題対策強化版）
        
        Args:
            text: 元のテキスト
            
        Returns:
            str: マークダウン記法除去済みテキスト
        """
        import re
        
        # マークダウンヘッダーの除去（#を含む行頭パターン）
        text = re.sub(r'^#{1,6}\s*.*$', '', text, flags=re.MULTILINE)
        
        # マークダウン強調記号の除去
        text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)  # *text* or **text**
        text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)    # _text_ or __text__
        
        # マークダウン水平線の除去
        text = re.sub(r'^[-_*]{3,}$', '', text, flags=re.MULTILINE)
        
        # HTMLタグの除去
        text = re.sub(r'<[^>]+>', '', text)
        
        # 連続する空白・改行の整理
        text = re.sub(r'\n{3,}', '\n\n', text)  # 3つ以上の改行を2つに
        text = re.sub(r' {2,}', ' ', text)      # 2つ以上のスペースを1つに
        
        # 残存する記号の除去
        text = re.sub(r'[#*_`\[\]{}\\|]', '', text)
        
        return text.strip()

    def _split_into_segments(self, script: str, max_chars: int = 4500) -> list:
        """
        台本を適切な長さのセグメントに分割

        Args:
            script: 台本テキスト
            max_chars: セグメントの最大文字数

        Returns:
            list: セグメントのリスト
        """
        if len(script) <= max_chars:
            return [script]

        segments = []
        current_segment = ""

        # 文単位で分割を試行
        sentences = script.split("。")

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence += "。"  # 句点を復元

            if len(current_segment) + len(sentence) <= max_chars:
                current_segment += sentence
            else:
                if current_segment:
                    segments.append(current_segment)
                current_segment = sentence

        if current_segment:
            segments.append(current_segment)

        return segments

    def _synthesize_segment(self, segment: str) -> bytes:
        """
        単一セグメントの音声合成

        Args:
            segment: 台本セグメント

        Returns:
            bytes: 音声データ
        """
        try:
            # Google Cloud TTS APIで音声合成
            synthesis_input = texttospeech.SynthesisInput(text=segment)

            # 音声設定
            voice = texttospeech.VoiceSelectionParams(
                language_code="ja-JP",
                name=self.voice_config.get("voice_name", "ja-JP-Neural2-D"),
                # ssml_gender指定を削除（voice nameが指定されている場合は不要・競合する）
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=self.voice_config.get("speaking_rate", 1.0),
                pitch=self.voice_config.get("pitch", 0.0),
                volume_gain_db=self.voice_config.get("volume_gain_db", 0.0),
                sample_rate_hertz=self.voice_config.get("sample_rate_hertz", 44100),
            )

            # 音声合成リクエスト
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            self.logger.info(f"音声合成成功: {len(response.audio_content)}バイト")
            return response.audio_content

        except Exception as e:
            self.logger.error(f"セグメント合成エラー: {e}")
            # フォールバック処理を無効化 - 本当のエラーを表面化
            raise e

    def _generate_high_quality_dummy_audio(self, text: str) -> bytes:
        """
        高品質なダミー音声データを生成（開発・テスト用）

        Args:
            text: テキスト

        Returns:
            bytes: ダミー音声データ
        """
        # 文字数に基づいた適切なサイズのダミーデータ
        # 実際のMP3形式に近い構造を模擬

        # 基本的なMP3ヘッダー（ID3v2）
        mp3_header = b"\xff\xfb\x90\x00"  # MP3 sync word + layer info

        # 文字数に応じた適切な音声データサイズ（約0.8秒/100文字）
        estimated_duration_seconds = len(text) / 125  # 平均的な読み上げ速度
        estimated_size = int(estimated_duration_seconds * 16000)  # 128kbps相当

        # ダミー音声データ（実際には正弦波やホワイトノイズでより現実的に）
        import random

        audio_data = bytes([random.randint(128, 255) for _ in range(estimated_size)])

        # 処理時間のシミュレーション
        processing_time = len(text) / 2000  # より現実的な処理時間
        time.sleep(min(processing_time, 3.0))

        return mp3_header + audio_data

    def _combine_audio_segments(self, segments: list) -> bytes:
        """
        複数の音声セグメントを結合（MP3構造を考慮した改善版）

        Args:
            segments: 音声セグメントのリスト

        Returns:
            bytes: 結合された音声データ
        """
        if not segments:
            return b""

        if len(segments) == 1:
            return segments[0]

        # MP3セグメントの適切な結合
        combined = b""
        for i, segment in enumerate(segments):
            if i == 0:
                # 最初のセグメントはそのまま追加
                combined += segment
            else:
                # 2番目以降のセグメントはMP3ヘッダーを除去して結合
                # 簡易的にID3タグとMP3ヘッダー部分をスキップ
                if len(segment) > 128:  # 最小限のサイズチェック
                    # MP3フレームの開始位置を探す（FF FB パターン）
                    frame_start = 0
                    for j in range(len(segment) - 1):
                        if segment[j] == 0xFF and (segment[j + 1] & 0xF0) == 0xF0:
                            frame_start = j
                            break
                    combined += segment[frame_start:]
                else:
                    combined += segment

        self.logger.info(f"音声セグメント結合完了: {len(segments)}個 -> {len(combined)}バイト")
        return combined

    def _save_audio_file(self, audio_data: bytes, output_path: Union[str, Path]) -> None:
        """
        音声データをファイルに保存

        Args:
            audio_data: 音声データ
            output_path: 出力パス
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(audio_data)

        self.logger.info(f"音声ファイル保存完了: {output_path}")

    def _generate_fallback_audio(self, script: str) -> bytes:
        """
        フォールバック用の音声データ生成

        Args:
            script: 台本テキスト

        Returns:
            bytes: フォールバック音声データ
        """
        self.logger.warning("フォールバック音声生成を実行")

        # 最小限のMP3ヘッダー
        mp3_header = b"\xff\xfb\x90\x00"

        # 基本的な音声データ（無音に近い状態）
        duration_seconds = max(len(script) / 150, 10)  # 最低10秒
        audio_size = int(duration_seconds * 8000)  # 64kbps相当

        # 無音データ（実際には低レベルのホワイトノイズ）
        silence_data = bytes([128 for _ in range(audio_size)])

        return mp3_header + silence_data

    def update_voice_config(self, config: Dict[str, Any]) -> None:
        """
        音声設定を更新

        Args:
            config: 新しい音声設定
        """
        self.voice_config.update(config)
        self.logger.info(f"音声設定を更新: {config}")

    def get_voice_config(self) -> Dict[str, Any]:
        """
        現在の音声設定を取得

        Returns:
            Dict[str, Any]: 現在の音声設定
        """
        return self.voice_config.copy()
