# -*- coding: utf-8 -*-

"""
Gemini TTS エンジン
高品質な音声合成とプロフェッショナルなポッドキャスト音声生成
"""

try:
    from google.cloud import texttospeech
    GOOGLE_CLOUD_TTS_AVAILABLE = True
except ImportError as e:
    raise ImportError(
        f"Google Cloud Text-to-Speechライブラリが必要です。以下のコマンドでインストールしてください:\n"
        f"pip install google-cloud-texttospeech>=2.16.0\n"
        f"詳細エラー: {e}"
    ) from e

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError as e:
    raise ImportError(
        f"PyDubライブラリが必要です。以下のコマンドでインストールしてください:\n"
        f"pip install pydub>=0.25.0\n"
        f"詳細エラー: {e}"
    ) from e
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
            self.logger.error("🚨 CRITICAL: Google Cloud TTS認証に失敗しました")
            self.logger.error("📋 確認事項:")
            self.logger.error("  1. GOOGLE_APPLICATION_CREDENTIALS_JSON が正しく設定されているか")
            self.logger.error("  2. サービスアカウントキーが有効か")  
            self.logger.error("  3. Google Cloud Text-to-Speech API が有効化されているか")
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

            # 品質検証（前処理後の文字数で推定時間を算出し精度向上）
            expected_duration = len(processed_script) / 200.0 * 60  # 200文字/分で推定
            quality_result = self.validate_audio_quality(combined_audio, expected_duration)
            
            if not quality_result["valid"]:
                self.logger.warning(f"音声品質に問題があります: {quality_result['issues']}")
            else:
                self.logger.info("音声品質検証: 良好")
            
            # ファイルに保存（指定された場合）
            if output_path:
                self._save_audio_file(combined_audio, output_path)
                # 品質レポートも保存
                self._save_quality_report(quality_result, output_path)

            self.logger.info(
                f"音声合成完了 - {len(combined_audio)}バイト, "
                f"再生時間: {quality_result['duration_seconds']:.2f}秒"
            )
            return combined_audio

        except Exception as e:
            self.logger.error(f"音声合成全体エラー: {e}")
            # 詳細を記録して表面化（フォールバックは行わない）
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "script_length": len(script),
                "segments_count": len(segments) if 'segments' in locals() else 0,
                "failed_segments": failed_segments if 'failed_segments' in locals() else [],
            }
            self.logger.error(f"エラー詳細: {error_details}")
            self.logger.error("🚨 音声合成が完全に失敗しました")
            self.logger.error("📊 影響: 音声ファイルは生成されません")
            raise RuntimeError(f"音声合成エラー: {e}")

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

    def _split_into_segments(self, script: str, max_bytes: int = 4500) -> list:
        """
        台本を適切な長さのセグメントに分割（Google Cloud TTS API制限に準拠）

        Args:
            script: 台本テキスト
            max_bytes: セグメントの最大バイト数（Google Cloud TTSの制限は5000バイト、安全マージンで4500バイト）

        Returns:
            list: セグメントのリスト
        """
        script_bytes = len(script.encode('utf-8'))
        if script_bytes <= max_bytes:
            return [script]

        segments = []
        current_segment = ""

        # 段落単位で分割を優先
        paragraphs = script.split("\n\n")
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # 段落が短い場合は現在のセグメントに追加を試行
            test_segment = current_segment + "\n\n" + paragraph if current_segment else paragraph
            if len(test_segment.encode('utf-8')) <= max_bytes:
                if current_segment:
                    current_segment += "\n\n" + paragraph
                else:
                    current_segment = paragraph
            else:
                # 現在のセグメントを確定
                if current_segment:
                    segments.append(current_segment)
                
                # 段落が単体で制限を超える場合は文単位で分割
                paragraph_bytes = len(paragraph.encode('utf-8'))
                if paragraph_bytes > max_bytes:
                    self.logger.info(f"長い段落を文単位で分割: {len(paragraph)} 文字 ({paragraph_bytes} バイト)")
                    sentence_segments = self._split_paragraph_by_sentences(paragraph, max_bytes)
                    segments.extend(sentence_segments[:-1])
                    current_segment = sentence_segments[-1] if sentence_segments else ""
                else:
                    current_segment = paragraph

        if current_segment:
            segments.append(current_segment)

        self.logger.info(f"台本分割完了: {len(script)} 文字 ({script_bytes} バイト) -> {len(segments)} セグメント")
        for i, segment in enumerate(segments, 1):
            segment_bytes = len(segment.encode('utf-8'))
            self.logger.debug(f"セグメント {i}: {len(segment)} 文字 ({segment_bytes} バイト)")

        return segments

    def _split_paragraph_by_sentences(self, paragraph: str, max_bytes: int) -> list:
        """
        段落を文単位で分割

        Args:
            paragraph: 分割対象段落
            max_bytes: 最大バイト数

        Returns:
            list: 分割されたテキストセグメント
        """
        if len(paragraph.encode('utf-8')) <= max_bytes:
            return [paragraph]
            
        segments = []
        current_segment = ""
        
        # 文単位で分割
        sentences = paragraph.split("。")
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence += "。"  # 句点を復元
            
            # 現在のセグメントに追加可能かチェック
            test_segment = current_segment + sentence
            if len(test_segment.encode('utf-8')) <= max_bytes:
                current_segment += sentence
            else:
                # 現在のセグメントを確定
                if current_segment:
                    segments.append(current_segment)
                
                # 文が単体で制限を超える場合は強制分割
                sentence_bytes = len(sentence.encode('utf-8'))
                if sentence_bytes > max_bytes:
                    self.logger.warning(f"長すぎる文を強制分割: {len(sentence)} 文字 ({sentence_bytes} バイト)")
                    force_segments = self._force_split_by_chars(sentence, max_bytes)
                    segments.extend(force_segments[:-1])
                    current_segment = force_segments[-1] if force_segments else ""
                else:
                    current_segment = sentence
        
        if current_segment:
            segments.append(current_segment)
            
        return segments
    
    def _force_split_by_chars(self, text: str, max_bytes: int) -> list:
        """
        長すぎるテキストをバイト数ベースで強制分割

        Args:
            text: 分割対象テキスト
            max_bytes: 最大バイト数

        Returns:
            list: 分割されたテキストセグメント
        """
        segments = []
        current = ""
        
        for char in text:
            test_text = current + char
            if len(test_text.encode('utf-8')) <= max_bytes:
                current += char
            else:
                if current:
                    segments.append(current)
                current = char
        
        if current:
            segments.append(current)
            
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
            self.logger.error(f"Google Cloud TTSセグメント合成エラー: {e}")
            self.logger.error("音声合成に失敗しました。APIキー、クォータ制限、ネットワーク接続を確認してください")
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
        PyDubを使用したプロフェッショナルな音声セグメント結合

        Args:
            segments: 音声セグメントのリスト（bytes）

        Returns:
            bytes: 結合された音声データ
        """
        if not segments:
            self.logger.error("結合する音声セグメントがありません")
            return b""

        if len(segments) == 1:
            self.logger.info("単一セグメントのため結合処理をスキップ")
            return segments[0]

        try:
            # PyDubを使用した高品質結合
            self.logger.info(f"PyDubを使用して {len(segments)} セグメントを結合開始")
            
            combined_audio = None
            total_duration = 0
            
            for i, segment_bytes in enumerate(segments):
                if not segment_bytes:
                    self.logger.warning(f"セグメント {i+1} が空のため、スキップします")
                    continue
                    
                try:
                    # BytesIOを使用してメモリ上でMP3を読み込み
                    segment_audio = AudioSegment.from_file(
                        io.BytesIO(segment_bytes), format="mp3"
                    )
                    
                    # セグメント情報をログ出力
                    duration_seconds = len(segment_audio) / 1000.0
                    total_duration += duration_seconds
                    self.logger.info(
                        f"セグメント {i+1}: {duration_seconds:.2f}秒, "
                        f"{len(segment_bytes)}バイト, "
                        f"サンプルレート: {segment_audio.frame_rate}Hz"
                    )
                    
                    # 結合処理
                    if combined_audio is None:
                        combined_audio = segment_audio
                    else:
                        combined_audio += segment_audio
                        
                except Exception as e:
                    self.logger.error(f"セグメント {i+1} の処理エラー: {e}")
                    # エラーのあるセグメントをスキップして続行
                    continue
            
            if combined_audio is None:
                self.logger.error("すべてのセグメントが無効でした")
                self.logger.error("🚨 CRITICAL: 音声セグメントの結合に完全に失敗")
                self.logger.error("📊 結果: 空の音声データが返されます（音声ファイル生成失敗）")
                raise RuntimeError("音声セグメント結合失敗: すべてのセグメントが無効")
            
            # 結合結果をMP3バイトデータとして出力
            output_buffer = io.BytesIO()
            combined_audio.export(
                output_buffer, 
                format="mp3",
                bitrate="128k",  # 高品質設定
                parameters=["-q:a", "2"]  # 高品質エンコーディング
            )
            
            combined_bytes = output_buffer.getvalue()
            final_duration = len(combined_audio) / 1000.0
            
            self.logger.info(
                f"音声結合完了: {len(segments)}セグメント -> {len(combined_bytes)}バイト, "
                f"総再生時間: {final_duration:.2f}秒 (予想: {total_duration:.2f}秒)"
            )
            
            # 品質チェック
            duration_diff = abs(final_duration - total_duration)
            if duration_diff > 1.0:  # 1秒以上の差がある場合は警告
                self.logger.warning(
                    f"結合後の時間長に差異があります: {duration_diff:.2f}秒の差"
                )
            
            return combined_bytes
            
        except Exception as e:
            self.logger.error(f"PyDub音声結合エラー: {e}")
            # エラーの根本原因を明確化し、例外を再発生
            self.logger.error("音声セグメントの結合に失敗しました。PyDubのインストール状態や音声データの整合性を確認してください")
            raise e
    

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

        # ファイルサイズ確認
        file_size = output_path.stat().st_size
        self.logger.info(f"音声ファイル保存完了: {output_path} ({file_size}バイト)")
        
        # 基本的なファイル整合性チェック
        if file_size != len(audio_data):
            self.logger.error(
                f"ファイル保存で整合性エラー: "
                f"期待サイズ {len(audio_data)}バイト != 実際サイズ {file_size}バイト"
            )

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
    
    def validate_audio_quality(self, audio_data: bytes, expected_duration: float = None) -> Dict[str, Any]:
        """
        音声データの品質検証
        
        Args:
            audio_data: 音声データ
            expected_duration: 期待される再生時間（秒）
            
        Returns:
            Dict[str, Any]: 品質検証結果
        """
        try:
            if not audio_data:
                return {
                    "valid": False,
                    "issues": ["音声データが空です"],
                    "size_bytes": 0,
                    "duration_seconds": 0.0
                }
            
            issues = []
            
            # サイズチェック
            size_bytes = len(audio_data)
            if size_bytes < 1000:  # 1KB未満は異常
                issues.append(f"音声データサイズが小さすぎます: {size_bytes}バイト")
            
            # MP3ヘッダーチェック
            if not audio_data.startswith(b'\xff\xfb') and not audio_data.startswith(b'ID3'):
                issues.append("MP3ヘッダーが不正です")
            
            duration_seconds = 0.0
            
            # PyDubでの詳細分析
            try:
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
                duration_seconds = len(audio_segment) / 1000.0
                
                # 再生時間チェック
                if duration_seconds < 1.0:
                    issues.append(f"再生時間が短すぎます: {duration_seconds:.2f}秒")
                
                # 期待時間との比較
                if expected_duration:
                    duration_diff = abs(duration_seconds - expected_duration)
                    if duration_diff > expected_duration * 0.2:  # 20%以上の差
                        issues.append(
                            f"期待再生時間との差が大きいです: "
                            f"実際 {duration_seconds:.2f}秒 vs 期待 {expected_duration:.2f}秒"
                        )
                
                # サンプルレートチェック
                if hasattr(audio_segment, 'frame_rate'):
                    if audio_segment.frame_rate < 22050:
                        issues.append(f"サンプルレートが低いです: {audio_segment.frame_rate}Hz")
                
            except Exception as analysis_error:
                issues.append(f"音声分析エラー: {analysis_error}")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "size_bytes": size_bytes,
                "duration_seconds": duration_seconds,
                "expected_duration": expected_duration,
                "analyzed_with_pydub": 'analysis_error' not in locals()
            }
            
        except Exception as e:
            self.logger.error(f"音声品質検証エラー: {e}")
            return {
                "valid": False,
                "issues": [f"品質検証エラー: {e}"],
                "size_bytes": len(audio_data) if audio_data else 0,
                "duration_seconds": 0.0
            }
    
    def _save_quality_report(self, quality_result: Dict[str, Any], audio_path: Union[str, Path]) -> None:
        """
        品質レポートをファイルに保存
        
        Args:
            quality_result: 品質検証結果
            audio_path: 音声ファイルパス（レポート名の基準）
        """
        try:
            audio_path = Path(audio_path)
            report_path = audio_path.with_suffix('.quality_report.json')
            
            import json
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(quality_result, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"品質レポート保存: {report_path}")
            
        except Exception as e:
            self.logger.warning(f"品質レポート保存エラー: {e}")
