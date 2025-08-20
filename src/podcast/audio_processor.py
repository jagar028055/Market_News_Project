"""
音声処理とファイル最適化

pydubを使用した音声品質調整、BGM・ジングル合成、ファイル最適化機能を提供します。
"""

import logging
import os
import io
import tempfile
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

try:
    from pydub import AudioSegment
    from pydub.effects import normalize, compress_dynamic_range
    from pydub.utils import make_chunks

    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

try:
    import pyloudnorm as pyln
    import numpy as np
    import soundfile as sf

    PYLOUDNORM_AVAILABLE = True
except ImportError:
    PYLOUDNORM_AVAILABLE = False


@dataclass
class AudioAssets:
    """音声アセットを表すデータクラス"""

    intro_jingle: str  # ファイルパス
    outro_jingle: str
    background_music: str
    segment_transition: str
    credits: Dict[str, str]  # CC-BYクレジット情報


@dataclass
class AudioProcessingResult:
    """音声処理結果を表すデータクラス"""

    audio_data: bytes
    duration_seconds: int
    file_size_bytes: int
    format: str
    sample_rate: int
    channels: int
    bitrate: str
    lufs_level: Optional[float] = None
    peak_level: Optional[float] = None


class AudioProcessingError(Exception):
    """音声処理関連のエラー"""

    pass


class AudioProcessor:
    """音声処理クラス

    TTS生成音声を最終的なポッドキャスト音声に処理します。
    音量正規化、BGM・ジングル合成、ファイル最適化を行います。
    """

    def __init__(self, assets_path: str):
        """
        初期化

        Args:
            assets_path: 音声アセットディレクトリのパス

        Raises:
            AudioProcessingError: 必要なライブラリが不足している場合
        """
        if not PYDUB_AVAILABLE:
            raise AudioProcessingError("pydubライブラリが必要です: pip install pydub")

        self.assets_path = Path(assets_path)
        self.logger = logging.getLogger(__name__)

        # 音声アセットを読み込み
        self.assets = self._load_assets()

        # 音声処理設定
        self.target_lufs = -16.0  # 音量正規化目標
        self.peak_target = -1.0  # ピーク制限目標
        self.target_duration_minutes = 10.0  # 目標再生時間
        self.max_duration_minutes = 10.5  # 最大再生時間
        self.max_file_size_mb = 15  # 最大ファイルサイズ

        # 音声品質設定
        self.output_sample_rate = 44100  # サンプルレート
        self.output_channels = 2  # ステレオ
        self.default_bitrate = "128k"  # デフォルトビットレート
        self.min_bitrate = "64k"  # 最小ビットレート（ファイルサイズ制限時）

        # BGM音量設定
        self.bgm_volume_db = -20  # BGMの音量（メイン音声より20dB低く）
        self.jingle_volume_db = -3  # ジングルの音量

        if not PYLOUDNORM_AVAILABLE:
            self.logger.warning("pyloudnormが利用できません。LUFS正規化は簡易版を使用します")

        self.logger.info("AudioProcessor初期化完了")

    def process_audio(self, tts_audio: bytes) -> AudioProcessingResult:
        """
        TTS音声を最終的なポッドキャスト音声に処理

        Args:
            tts_audio: TTS生成音声データ（WAV形式）

        Returns:
            最終ポッドキャスト音声処理結果

        Raises:
            AudioProcessingError: 音声処理に失敗した場合
        """
        try:
            self.logger.info("音声処理を開始")

            # 1. TTS音声をAudioSegmentに変換
            main_audio = self._load_audio_from_bytes(tts_audio)
            self.logger.info(f"メイン音声読み込み完了: {len(main_audio)/1000:.2f}秒")

            # 2. 基本的な音声品質調整
            processed_audio = self._prepare_main_audio(main_audio)

            # 3. オープニング・エンディング追加
            with_intro_outro = self._add_intro_outro(processed_audio)

            # 4. BGM統合
            with_bgm = self._add_background_music(with_intro_outro)

            # 5. 音量正規化
            normalized_audio = self._normalize_audio(with_bgm)

            # 6. 再生時間チェックと調整
            duration_adjusted = self._adjust_duration(normalized_audio)

            # 7. 最終調整とMP3出力
            final_result = self._finalize_audio(duration_adjusted)

            self.logger.info(
                f"音声処理完了: {final_result.duration_seconds}秒, {final_result.file_size_bytes/1024/1024:.2f}MB"
            )
            return final_result

        except Exception as e:
            self.logger.error(f"音声処理に失敗: {str(e)}")
            raise AudioProcessingError(f"音声処理エラー: {str(e)}")

    def _load_assets(self) -> AudioAssets:
        """
        音声アセットを読み込み

        Returns:
            音声アセット情報
        """
        assets_dir = self.assets_path

        # デフォルトのアセットファイル名
        intro_path = assets_dir / "intro_jingle.mp3"
        outro_path = assets_dir / "outro_jingle.mp3"
        bgm_path = assets_dir / "background_music.mp3"
        transition_path = assets_dir / "segment_transition.mp3"

        # ファイル存在チェック
        for path in [intro_path, outro_path, bgm_path, transition_path]:
            if not path.exists():
                self.logger.warning(f"音声アセットが見つかりません: {path}")

        # CC-BYクレジット情報（プレースホルダー）
        credits = {
            "intro_jingle": "CC-BY ライセンス音源",
            "outro_jingle": "CC-BY ライセンス音源",
            "background_music": "CC-BY ライセンス音源",
            "segment_transition": "CC-BY ライセンス音源",
        }

        return AudioAssets(
            intro_jingle=str(intro_path),
            outro_jingle=str(outro_path),
            background_music=str(bgm_path),
            segment_transition=str(transition_path),
            credits=credits,
        )

    def _load_audio_from_bytes(self, audio_bytes: bytes) -> AudioSegment:
        """
        バイト列から音声データを読み込み

        Args:
            audio_bytes: 音声データのバイト列

        Returns:
            AudioSegmentオブジェクト
        """
        try:
            return AudioSegment.from_wav(io.BytesIO(audio_bytes))
        except Exception as e:
            self.logger.error(f"音声データの読み込みに失敗: {str(e)}")
            raise AudioProcessingError(f"音声データ読み込みエラー: {str(e)}")

    def _prepare_main_audio(self, audio: AudioSegment) -> AudioSegment:
        """
        メイン音声の基本的な品質調整

        Args:
            audio: 元の音声データ

        Returns:
            調整された音声データ
        """
        # サンプルレートとチャンネル数を統一
        processed = audio.set_frame_rate(self.output_sample_rate)
        processed = processed.set_channels(self.output_channels)

        # 基本的なノイズ除去（簡易版）
        processed = self._apply_basic_noise_reduction(processed)

        # 動的レンジ圧縮
        processed = compress_dynamic_range(processed)

        self.logger.debug("メイン音声の基本調整完了")
        return processed

    def _apply_basic_noise_reduction(self, audio: AudioSegment) -> AudioSegment:
        """
        基本的なノイズ除去処理

        Args:
            audio: 音声データ

        Returns:
            ノイズ除去済み音声データ
        """
        # 簡易的なハイパスフィルタ（低周波ノイズ除去）
        # 実際の実装では、より高度なノイズ除去が必要
        return audio.high_pass_filter(80)  # 80Hz以下をカット

    def _normalize_audio(self, audio_data: AudioSegment) -> AudioSegment:
        """
        音量正規化（-16 LUFS, -1 dBFS peak）

        Args:
            audio_data: AudioSegmentオブジェクト

        Returns:
            正規化された音声データ
        """
        try:
            if PYLOUDNORM_AVAILABLE:
                return self._normalize_with_pyloudnorm(audio_data)
            else:
                return self._normalize_simple(audio_data)
        except Exception as e:
            self.logger.warning(f"音量正規化に失敗、簡易版を使用: {str(e)}")
            return self._normalize_simple(audio_data)

    def _normalize_with_pyloudnorm(self, audio: AudioSegment) -> AudioSegment:
        """
        pyloudnormを使用したLUFS正規化

        Args:
            audio: 音声データ

        Returns:
            LUFS正規化された音声データ
        """
        # AudioSegmentを一時ファイルに保存してnumpy配列に変換
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            audio.export(temp_file.name, format="wav")

            # soundfileで読み込み
            data, rate = sf.read(temp_file.name)

            # LUFS測定とノーマライゼーション
            meter = pyln.Meter(rate)
            loudness = meter.integrated_loudness(data)

            # -16 LUFSに正規化
            normalized_data = pyln.normalize.loudness(data, loudness, self.target_lufs)

            # ピーク制限
            peak = np.max(np.abs(normalized_data))
            if peak > 10 ** (self.peak_target / 20):
                normalized_data = normalized_data * (10 ** (self.peak_target / 20) / peak)

            # 一時ファイルに保存してAudioSegmentに変換
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as normalized_file:
                sf.write(normalized_file.name, normalized_data, rate)
                result = AudioSegment.from_wav(normalized_file.name)

                # 一時ファイルを削除
                os.unlink(temp_file.name)
                os.unlink(normalized_file.name)

                self.logger.debug(f"LUFS正規化完了: {loudness:.2f} -> {self.target_lufs} LUFS")
                return result

    def _normalize_simple(self, audio: AudioSegment) -> AudioSegment:
        """
        簡易音量正規化（pydubのみ使用）

        Args:
            audio: 音声データ

        Returns:
            正規化された音声データ
        """
        # pydubの正規化（ピーク正規化）
        normalized = normalize(audio, headroom=abs(self.peak_target))

        # 簡易的な音量調整（-16 LUFSに近似）
        # 実際のLUFS測定はできないため、RMS値で近似
        target_rms_db = -20  # -16 LUFSの近似値
        current_rms_db = normalized.dBFS

        if current_rms_db != float("-inf"):
            adjustment_db = target_rms_db - current_rms_db
            normalized = normalized + adjustment_db

        self.logger.debug(f"簡易正規化完了: {current_rms_db:.2f} -> {target_rms_db} dB RMS")
        return normalized

    def _add_intro_outro(self, audio_data: AudioSegment) -> AudioSegment:
        """
        オープニング・エンディング追加

        Args:
            audio_data: メイン音声データ

        Returns:
            イントロ・アウトロ付き音声データ
        """
        result = audio_data

        # オープニングジングル追加
        intro_path = Path(self.assets.intro_jingle)
        if intro_path.exists():
            try:
                intro = AudioSegment.from_file(str(intro_path))
                intro = intro.set_frame_rate(self.output_sample_rate)
                intro = intro.set_channels(self.output_channels)
                intro = intro + self.jingle_volume_db  # 音量調整

                # フェードイン・アウト効果
                intro = intro.fade_in(500).fade_out(1000)

                # メイン音声の前に追加（少しオーバーラップ）
                overlap_ms = 500
                if len(intro) > overlap_ms:
                    intro_main = intro[:-overlap_ms]
                    intro_overlap = intro[-overlap_ms:]

                    # メイン音声の最初の部分と重ねる
                    if len(result) > overlap_ms:
                        main_start = result[:overlap_ms]
                        main_rest = result[overlap_ms:]

                        # オーバーラップ部分をミックス
                        overlapped = intro_overlap.overlay(main_start)
                        result = intro_main + overlapped + main_rest
                    else:
                        result = intro + result
                else:
                    result = intro + result

                self.logger.debug("オープニングジングル追加完了")
            except Exception as e:
                self.logger.warning(f"オープニングジングルの追加に失敗: {str(e)}")
        else:
            self.logger.warning(f"オープニングジングルが見つかりません: {intro_path}")

        # エンディングジングル追加
        outro_path = Path(self.assets.outro_jingle)
        if outro_path.exists():
            try:
                outro = AudioSegment.from_file(str(outro_path))
                outro = outro.set_frame_rate(self.output_sample_rate)
                outro = outro.set_channels(self.output_channels)
                outro = outro + self.jingle_volume_db  # 音量調整

                # フェードイン・アウト効果
                outro = outro.fade_in(1000).fade_out(500)

                # メイン音声の後に追加（少しオーバーラップ）
                overlap_ms = 1000
                if len(outro) > overlap_ms and len(result) > overlap_ms:
                    outro_overlap = outro[:overlap_ms]
                    outro_main = outro[overlap_ms:]

                    # メイン音声の最後の部分と重ねる
                    main_end = result[-overlap_ms:]
                    main_body = result[:-overlap_ms]

                    # オーバーラップ部分をミックス
                    overlapped = main_end.overlay(outro_overlap)
                    result = main_body + overlapped + outro_main
                else:
                    result = result + outro

                self.logger.debug("エンディングジングル追加完了")
            except Exception as e:
                self.logger.warning(f"エンディングジングルの追加に失敗: {str(e)}")
        else:
            self.logger.warning(f"エンディングジングルが見つかりません: {outro_path}")

        return result

    def _add_background_music(self, audio_data: AudioSegment) -> AudioSegment:
        """
        BGM統合

        Args:
            audio_data: メイン音声データ

        Returns:
            BGM統合済み音声データ
        """
        bgm_path = Path(self.assets.background_music)
        if not bgm_path.exists():
            self.logger.warning(f"BGMファイルが見つかりません: {bgm_path}")
            return audio_data

        try:
            # BGMを読み込み
            bgm = AudioSegment.from_file(str(bgm_path))
            bgm = bgm.set_frame_rate(self.output_sample_rate)
            bgm = bgm.set_channels(self.output_channels)

            # BGMの音量を調整（メイン音声より低く）
            bgm = bgm + self.bgm_volume_db

            # メイン音声の長さに合わせてBGMをループまたはカット
            main_duration = len(audio_data)

            if len(bgm) < main_duration:
                # BGMが短い場合はループ
                loops_needed = (main_duration // len(bgm)) + 1
                bgm = bgm * loops_needed

            # メイン音声の長さに合わせてカット
            bgm = bgm[:main_duration]

            # フェードイン・アウト効果を追加
            fade_duration = min(3000, len(bgm) // 10)  # 3秒または全体の10%
            bgm = bgm.fade_in(fade_duration).fade_out(fade_duration)

            # メイン音声とBGMをミックス
            result = audio_data.overlay(bgm)

            self.logger.debug(f"BGM統合完了: {len(bgm)/1000:.2f}秒")
            return result

        except Exception as e:
            self.logger.warning(f"BGM統合に失敗: {str(e)}")
            return audio_data

    def _adjust_duration(self, audio: AudioSegment) -> AudioSegment:
        """
        再生時間を目標範囲内に調整

        Args:
            audio: 音声データ

        Returns:
            時間調整された音声データ
        """
        current_duration_minutes = len(audio) / 1000 / 60

        if current_duration_minutes > self.max_duration_minutes:
            # 長すぎる場合は末尾をカット
            target_ms = int(self.max_duration_minutes * 60 * 1000)

            # フェードアウトを追加してから切る
            fade_duration = 2000  # 2秒のフェードアウト
            if len(audio) > target_ms + fade_duration:
                audio = audio[: target_ms + fade_duration]
                audio = audio.fade_out(fade_duration)
            else:
                audio = audio[:target_ms]

            self.logger.warning(
                f"音声を短縮: {current_duration_minutes:.2f} -> {len(audio)/1000/60:.2f}分"
            )

        return audio

    def _finalize_audio(self, audio: AudioSegment) -> AudioProcessingResult:
        """
        最終調整とMP3出力

        Args:
            audio: 処理済み音声データ

        Returns:
            最終的な音声処理結果
        """
        # 最適なビットレートを決定
        bitrate = self._determine_optimal_bitrate(audio)

        # MP3形式でエクスポート
        buffer = io.BytesIO()
        audio.export(buffer, format="mp3", bitrate=bitrate, parameters=["-q:a", "2"])  # 高品質設定

        audio_data = buffer.getvalue()
        file_size_mb = len(audio_data) / 1024 / 1024

        # ファイルサイズチェック
        if file_size_mb > self.max_file_size_mb:
            self.logger.warning(
                f"ファイルサイズが制限を超過: {file_size_mb:.2f}MB > {self.max_file_size_mb}MB"
            )
            # より低いビットレートで再エクスポート
            audio_data = self._optimize_file_size(audio)
            file_size_mb = len(audio_data) / 1024 / 1024

        # 音声レベル測定
        lufs_level, peak_level = self._measure_audio_levels(audio)

        result = AudioProcessingResult(
            audio_data=audio_data,
            duration_seconds=int(len(audio) / 1000),
            file_size_bytes=len(audio_data),
            format="mp3",
            sample_rate=self.output_sample_rate,
            channels=self.output_channels,
            bitrate=bitrate,
            lufs_level=lufs_level,
            peak_level=peak_level,
        )

        self.logger.info(f"最終音声: {result.duration_seconds}秒, {file_size_mb:.2f}MB, {bitrate}")
        return result

    def _determine_optimal_bitrate(self, audio: AudioSegment) -> str:
        """
        最適なビットレートを決定

        Args:
            audio: 音声データ

        Returns:
            ビットレート文字列
        """
        duration_minutes = len(audio) / 1000 / 60

        # 概算ファイルサイズを計算（MB = bitrate(kbps) * duration(min) / 8 / 1024）
        for bitrate in ["128k", "96k", "80k", "64k"]:
            bitrate_num = int(bitrate.replace("k", ""))
            estimated_size_mb = bitrate_num * duration_minutes / 8 / 1024

            if estimated_size_mb <= self.max_file_size_mb:
                return bitrate

        return self.min_bitrate

    def _optimize_file_size(self, audio: AudioSegment) -> bytes:
        """
        ファイルサイズ最適化

        Args:
            audio: 音声データ

        Returns:
            最適化された音声データ（バイト列）
        """
        # より低いビットレートで再エクスポート
        buffer = io.BytesIO()
        audio.export(
            buffer,
            format="mp3",
            bitrate=self.min_bitrate,
            parameters=["-q:a", "4"],  # 品質を少し下げる
        )

        optimized_data = buffer.getvalue()
        optimized_size_mb = len(optimized_data) / 1024 / 1024

        self.logger.info(f"ファイルサイズ最適化: {optimized_size_mb:.2f}MB ({self.min_bitrate})")
        return optimized_data

    def _measure_audio_levels(self, audio: AudioSegment) -> Tuple[Optional[float], Optional[float]]:
        """
        音声レベルを測定

        Args:
            audio: 音声データ

        Returns:
            (LUFS値, ピーク値) のタプル
        """
        try:
            if PYLOUDNORM_AVAILABLE:
                # 一時ファイルに保存してLUFS測定
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    audio.export(temp_file.name, format="wav")
                    data, rate = sf.read(temp_file.name)

                    meter = pyln.Meter(rate)
                    lufs = meter.integrated_loudness(data)
                    peak = 20 * np.log10(np.max(np.abs(data)))

                    os.unlink(temp_file.name)
                    return lufs, peak
            else:
                # 簡易測定
                peak_db = audio.max_dBFS
                return None, peak_db

        except Exception as e:
            self.logger.warning(f"音声レベル測定に失敗: {str(e)}")
            return None, None

    def get_credits_text(self) -> str:
        """
        CC-BYクレジット情報を取得

        Returns:
            クレジット文字列
        """
        credits_list = []
        for asset_name, credit in self.assets.credits.items():
            credits_list.append(f"{asset_name}: {credit}")

        return "音声素材: " + ", ".join(credits_list)
