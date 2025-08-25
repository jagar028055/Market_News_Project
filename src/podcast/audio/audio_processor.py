# -*- coding: utf-8 -*-

"""
音声処理クラス
プロフェッショナルポッドキャスト品質の音声処理とファイル生成
"""

import logging
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
import json

from ..assets.asset_manager import AssetManager


class AudioProcessor:
    """
    音声処理クラス

    機能:
    - 音量正規化（-16 LUFS）
    - MP3 128kbps出力
    - メタデータ埋め込み
    - 品質管理
    """

    # デフォルト処理設定（プロダクション最適化）
    DEFAULT_SETTINGS = {
        "lufs_target": -16.0,  # LUFS ラウドネス目標値（ポッドキャスト業界標準）
        "peak_target": -1.0,  # ピーク制限（dBFS）
        "bitrate": "128k",  # MP3ビットレート（高品質）
        "sample_rate": 44100,  # サンプリングレート（CD品質）
        "channels": 1,  # モノラル（ポッドキャスト標準、ファイルサイズ最適化）
        "max_file_size_mb": 25,  # 最大ファイルサイズ（MB）- BGM込みで増加
        "target_duration_minutes": 15.0,  # 目標再生時間（分）- より長いコンテンツに対応
        "enable_music": True,  # BGM・ミュージック合成を有効化
        "bgm_volume": 0.15,  # BGM音量レベル（メイン音声を邪魔しない）
        "fade_duration": 0.5,  # フェードイン/アウト時間（秒）
    }

    def __init__(self, assets_dir: str, ffmpeg_path: Optional[str] = None):
        """
        初期化

        Args:
            assets_dir: 音声アセットディレクトリ
            ffmpeg_path: FFmpegバイナリパス（オプション）
        """
        self.assets_dir = Path(assets_dir)
        self.logger = logging.getLogger(__name__)

        # アセットマネージャーの初期化
        self.asset_manager = AssetManager(str(self.assets_dir))

        # FFmpegパスの検出
        self.ffmpeg_path = ffmpeg_path or shutil.which("ffmpeg")
        if not self.ffmpeg_path:
            self.logger.warning("FFmpegが見つかりません - 基本機能のみ利用可能")

        # 一時ディレクトリの準備
        self.temp_dir = Path(tempfile.gettempdir()) / "podcast_audio"
        self.temp_dir.mkdir(exist_ok=True)

        self.logger.info(f"AudioProcessor初期化完了 - アセット: {assets_dir}")

    def process_audio(
        self,
        audio_data: bytes,
        episode_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        音声データを処理してファイルに保存

        Args:
            audio_data: 音声データ
            episode_id: エピソードID
            metadata: メタデータ辞書（オプション）
            settings: 処理設定（オプション）

        Returns:
            str: 保存されたファイルのパス

        Raises:
            Exception: 音声処理に失敗した場合
        """
        if not audio_data:
            raise ValueError("音声データが空です")

        self.logger.info(f"音声処理開始 - エピソード: {episode_id}")

        # 設定を統合
        process_settings = self.DEFAULT_SETTINGS.copy()
        if settings:
            process_settings.update(settings)

        try:
            # 一時入力ファイルの作成
            temp_input = self.temp_dir / f"{episode_id}_raw.mp3"
            with open(temp_input, "wb") as f:
                f.write(audio_data)

            # 出力ディレクトリを作成
            output_dir = Path("output/podcast")
            output_dir.mkdir(parents=True, exist_ok=True)

            # 最終出力パス
            output_path = output_dir / f"{episode_id}.mp3"

            # BGM付き高品質音声処理パイプライン
            if self.ffmpeg_path:
                processed_path = self._process_with_ffmpeg_and_music(
                    temp_input, output_path, process_settings, metadata
                )
            else:
                # FFmpeg無しの場合は基本処理
                processed_path = self._process_basic(temp_input, output_path, metadata)

            # 品質チェック
            self._validate_output_quality(processed_path, process_settings)

            # 一時ファイルの清掃
            self._cleanup_temp_files(temp_input)

            self.logger.info(f"音声処理完了 - 出力: {processed_path}")
            return str(processed_path)

        except Exception as e:
            self.logger.error(f"音声処理エラー: {e}")
            # エラー時は基本処理にフォールバック
            return self._create_fallback_file(audio_data, episode_id, metadata)

    def _process_with_ffmpeg_and_music(
        self,
        input_path: Path,
        output_path: Path,
        settings: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        FFmpegを使用したBGM付き高品質音声処理

        Args:
            input_path: 入力ファイルパス
            output_path: 出力ファイルパス
            settings: 処理設定
            metadata: メタデータ

        Returns:
            Path: 処理済みファイルパス
        """
        # 段階的処理のための一時ファイル
        temp_normalized = self.temp_dir / f"{input_path.stem}_normalized.mp3"
        temp_with_music = self.temp_dir / f"{input_path.stem}_with_music.mp3"

        try:
            # ステップ1: ラウドネス正規化
            self._normalize_loudness(input_path, temp_normalized, settings)

            # ステップ2: BGMとミュージック合成（設定で有効な場合のみ）
            if settings.get("enable_music", True) and self._add_music_layers(temp_normalized, temp_with_music, settings):
                # BGM合成成功時は音楽付きファイルを使用
                final_input = temp_with_music
                self.logger.info("BGM付き音声処理完了")
            else:
                # BGM合成無効または失敗時は正規化済みファイルを使用
                final_input = temp_normalized
                if settings.get("enable_music", True):
                    self.logger.warning("BGM合成に失敗しました。音楽なしで処理を続行します。")
                else:
                    self.logger.info("BGM合成は無効設定のため、音楽なしで処理します。")

            # ステップ3: 最終エンコーディング + メタデータ埋め込み
            self._encode_final_output(final_input, output_path, settings, metadata)

            return output_path

        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg処理エラー: {e}")
            raise
        finally:
            # 一時ファイル清掃
            for temp_file in [temp_normalized, temp_with_music]:
                if temp_file.exists():
                    temp_file.unlink()

    def _normalize_loudness(
        self, input_path: Path, output_path: Path, settings: Dict[str, Any]
    ) -> None:
        """
        ラウドネス正規化（-16 LUFS）

        Args:
            input_path: 入力ファイル
            output_path: 出力ファイル
            settings: 処理設定
        """
        lufs_target = settings["lufs_target"]
        peak_target = settings["peak_target"]

        # 2パス処理: 測定 -> 適用
        # パス1: ラウドネス測定
        cmd_measure = [
            self.ffmpeg_path,
            "-i",
            str(input_path),
            "-af",
            "loudnorm=print_format=json",
            "-f",
            "null",
            "-",
        ]

        self.logger.info("ラウドネス測定中...")
        result = subprocess.run(cmd_measure, capture_output=True, text=True, check=False)

        # JSON出力から測定値を抽出
        loudness_info = self._extract_loudness_info(result.stderr)

        # パス2: 正規化適用
        if loudness_info:
            measured_i = loudness_info.get("input_i", str(lufs_target))
            measured_lra = loudness_info.get("input_lra", "7.0")
            measured_tp = loudness_info.get("input_tp", str(peak_target))
            measured_thresh = loudness_info.get("input_thresh", "-26.0")

            cmd_normalize = [
                self.ffmpeg_path,
                "-i",
                str(input_path),
                "-af",
                f"loudnorm=I={lufs_target}:TP={peak_target}:LRA=7.0:measured_I={measured_i}:measured_LRA={measured_lra}:measured_TP={measured_tp}:measured_thresh={measured_thresh}:linear=true:print_format=summary",
                "-ar",
                str(settings["sample_rate"]),
                "-ac",
                str(settings["channels"]),
                "-y",
                str(output_path),
            ]
        else:
            # 測定失敗時は1パス正規化
            cmd_normalize = [
                self.ffmpeg_path,
                "-i",
                str(input_path),
                "-af",
                f"loudnorm=I={lufs_target}:TP={peak_target}",
                "-ar",
                str(settings["sample_rate"]),
                "-ac",
                str(settings["channels"]),
                "-y",
                str(output_path),
            ]

        self.logger.info("ラウドネス正規化実行中...")
        subprocess.run(cmd_normalize, check=True, capture_output=True)

    def _encode_final_output(
        self,
        input_path: Path,
        output_path: Path,
        settings: Dict[str, Any],
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        """
        最終MP3エンコーディングとメタデータ埋め込み

        Args:
            input_path: 入力ファイル
            output_path: 出力ファイル
            settings: 処理設定
            metadata: メタデータ
        """
        cmd = [
            self.ffmpeg_path,
            "-i",
            str(input_path),
            "-c:a",
            "libmp3lame",
            "-b:a",
            settings["bitrate"],
            "-ar",
            str(settings["sample_rate"]),
            "-ac",
            str(settings["channels"]),
            "-q:a",
            "2",  # 高品質設定
        ]

        # メタデータを追加
        if metadata:
            if "title" in metadata:
                cmd.extend(["-metadata", f"title={metadata['title']}"])
            if "artist" in metadata:
                cmd.extend(["-metadata", f"artist={metadata['artist']}"])
            if "album" in metadata:
                cmd.extend(["-metadata", f"album={metadata['album']}"])
            if "date" in metadata:
                cmd.extend(["-metadata", f"date={metadata['date']}"])
            if "genre" in metadata:
                cmd.extend(["-metadata", f"genre={metadata['genre']}"])
            if "comment" in metadata:
                cmd.extend(["-metadata", f"comment={metadata['comment']}"])

        cmd.extend(["-y", str(output_path)])

        self.logger.info("最終エンコーディング実行中...")
        subprocess.run(cmd, check=True, capture_output=True)

    def _add_music_layers(
        self, input_path: Path, output_path: Path, settings: Dict[str, Any]
    ) -> bool:
        """
        BGMとイントロ・アウトロミュージックを合成

        Args:
            input_path: 入力音声ファイル
            output_path: 出力ファイル
            settings: 処理設定

        Returns:
            bool: 合成成功時True
        """
        try:
            # アセットファイルパスを取得
            assets = self.asset_manager.get_all_assets()
            intro_path = assets.get("intro_jingle")
            outro_path = assets.get("outro_jingle")
            bgm_path = assets.get("background_music")

            self.logger.info("BGMとミュージック合成を開始")

            # 基本的な音声ミキシングコマンドを構築
            if bgm_path and Path(bgm_path).exists():
                # バックグラウンドミュージックありの場合
                success = self._mix_with_background_music(
                    input_path, output_path, bgm_path, intro_path, outro_path, settings
                )
            elif intro_path or outro_path:
                # イントロ・アウトロのみの場合
                success = self._add_intro_outro_only(
                    input_path, output_path, intro_path, outro_path, settings
                )
            else:
                # ミュージックファイルがない場合
                self.logger.warning("ミュージックアセットが見つかりません")
                return False

            if success:
                self.logger.info("BGMとミュージック合成完了")
            else:
                self.logger.warning("BGMとミュージック合成に失敗")

            return success

        except Exception as e:
            self.logger.error(f"ミュージック合成エラー: {e}")
            return False

    def _mix_with_background_music(
        self,
        voice_path: Path,
        output_path: Path,
        bgm_path: str,
        intro_path: Optional[str],
        outro_path: Optional[str],
        settings: Dict[str, Any],
    ) -> bool:
        """
        バックグラウンドミュージック付きの音声ミキシング

        Args:
            voice_path: 音声ファイル
            output_path: 出力ファイル
            bgm_path: BGMファイル
            intro_path: イントロファイル（オプション）
            outro_path: アウトロファイル（オプション）
            settings: 処理設定

        Returns:
            bool: 成功時True
        """
        try:
            # 入力の並びを構築（可変長インデックスに対応）
            input_files = []
            intro_exists = bool(intro_path and Path(intro_path).exists())
            outro_exists = bool(outro_path and Path(outro_path).exists())

            if intro_exists:
                input_files.append(intro_path)  # idx 0
            input_files.append(str(voice_path))  # idx 0 or 1
            input_files.append(bgm_path)         # idx 1 or 2
            if outro_exists:
                input_files.append(outro_path)   # last idx

            # 各インデックスを特定
            voice_idx = 1 if intro_exists else 0
            bgm_idx = 2 if intro_exists else 1
            intro_idx = 0 if intro_exists else None
            outro_idx = (3 if intro_exists else 2) if outro_exists else None

            # フィルタグラフを構築
            bgm_volume = settings.get("bgm_volume", 0.15)
            filter_complex_parts = []

            # 1) BGMを音量調整しループ
            filter_complex_parts.append(
                f"[{bgm_idx}:a]volume={bgm_volume},aloop=loop=-1:size=2e+09[bgm_loop]"
            )

            # 2) ナレーション音声とBGMをamix（音声長に合わせる）
            filter_complex_parts.append(
                f"[{voice_idx}:a][bgm_loop]amix=inputs=2:duration=first[voice_bgm]"
            )

            # 3) イントロ/アウトロがあればconcatで前後に結合
            final_output = "[voice_bgm]"
            if intro_exists and outro_exists:
                filter_complex_parts.append(
                    f"[{intro_idx}:a][voice_bgm][{outro_idx}:a]concat=n=3:v=0:a=1[final_mixed]"
                )
                final_output = "[final_mixed]"
            elif intro_exists and not outro_exists:
                filter_complex_parts.append(
                    f"[{intro_idx}:a][voice_bgm]concat=n=2:v=0:a=1[final_mixed]"
                )
                final_output = "[final_mixed]"
            elif (not intro_exists) and outro_exists:
                filter_complex_parts.append(
                    f"[voice_bgm][{outro_idx}:a]concat=n=2:v=0:a=1[final_mixed]"
                )
                final_output = "[final_mixed]"

            # FFmpegコマンド実行
            cmd = [self.ffmpeg_path]
            for input_file in input_files:
                cmd.extend(["-i", input_file])

            cmd.extend([
                "-filter_complex", ";".join(filter_complex_parts),
                "-map", final_output,
                "-c:a", "libmp3lame",
                "-b:a", settings.get("bitrate", "128k"),
                "-ar", str(settings.get("sample_rate", 44100)),
                "-ac", str(settings.get("channels", 1)),
                "-y", str(output_path)
            ])

            self.logger.info("BGM付きミキシング実行中...")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                self.logger.info("BGM付きミキシング成功")
                return True
            else:
                self.logger.error(f"BGM付きミキシング失敗: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"BGM付きミキシングエラー: {e}")
            return False

    def _add_intro_outro_only(
        self,
        voice_path: Path,
        output_path: Path,
        intro_path: Optional[str],
        outro_path: Optional[str],
        settings: Dict[str, Any],
    ) -> bool:
        """
        イントロ・アウトロのみ追加

        Args:
            voice_path: 音声ファイル
            output_path: 出力ファイル
            intro_path: イントロファイル（オプション）
            outro_path: アウトロファイル（オプション）
            settings: 処理設定

        Returns:
            bool: 成功時True
        """
        try:
            parts = []
            if intro_path and Path(intro_path).exists():
                parts.append(intro_path)

            parts.append(str(voice_path))

            if outro_path and Path(outro_path).exists():
                parts.append(outro_path)

            if len(parts) == 1:
                # イントロもアウトロもない場合は単純コピー
                shutil.copy2(voice_path, output_path)
                return True

            # 複数ファイルの結合
            cmd = [self.ffmpeg_path]
            for part in parts:
                cmd.extend(["-i", part])

            # filter_complexで結合
            filter_inputs = ":".join([f"[{i}:a]" for i in range(len(parts))])
            cmd.extend([
                "-filter_complex", f"{filter_inputs}concat=n={len(parts)}:v=0:a=1[out]",
                "-map", "[out]",
                "-c:a", "libmp3lame",
                "-b:a", settings.get("bitrate", "128k"),
                "-ar", str(settings.get("sample_rate", 44100)),
                "-ac", str(settings.get("channels", 1)),
                "-y", str(output_path)
            ])

            self.logger.info("イントロ・アウトロ結合実行中...")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                self.logger.info("イントロ・アウトロ結合成功")
                return True
            else:
                self.logger.error(f"イントロ・アウトロ結合失敗: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"イントロ・アウトロ結合エラー: {e}")
            return False

    def _extract_loudness_info(self, stderr_output: str) -> Optional[Dict[str, str]]:
        """
        FFmpeg出力からラウドネス情報を抽出

        Args:
            stderr_output: FFmpegのstderr出力

        Returns:
            Dict[str, str]: ラウドネス測定値（JSON形式）
        """
        try:
            # JSONブロックを探す
            lines = stderr_output.split("\n")
            json_started = False
            json_lines = []

            for line in lines:
                if "{" in line and not json_started:
                    json_started = True
                if json_started:
                    json_lines.append(line)
                if "}" in line and json_started:
                    break

            if json_lines:
                json_str = "\n".join(json_lines)
                return json.loads(json_str)

        except (json.JSONDecodeError, Exception) as e:
            self.logger.warning(f"ラウドネス情報解析エラー: {e}")

        return None

    def _process_basic(
        self, input_path: Path, output_path: Path, metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        FFmpeg無しの基本処理

        Args:
            input_path: 入力ファイル
            output_path: 出力ファイル
            metadata: メタデータ

        Returns:
            Path: 出力ファイルパス
        """
        self.logger.warning("基本処理モード - 高度な音声処理は利用できません")

        # 単純なファイルコピー + 基本メタデータ
        with open(input_path, "rb") as src, open(output_path, "wb") as dst:
            # 基本的なMP3ヘッダーを追加
            if metadata:
                # 簡易ID3v1タグを追加（30バイトのタイトル等）
                title = (metadata.get("title", "")[:30]).ljust(30, "\0")
                artist = (metadata.get("artist", "")[:30]).ljust(30, "\0")

                # ID3v1タグ構造（128バイト）
                id3v1_tag = (
                    b"TAG"
                    + title.encode("latin-1", errors="replace")[:30]
                    + artist.encode("latin-1", errors="replace")[:30]
                )
                id3v1_tag = id3v1_tag.ljust(128, b"\0")

                # 音声データをコピー
                audio_data = src.read()
                dst.write(audio_data)
                # 最後にタグを追加
                dst.write(id3v1_tag)
            else:
                # メタデータなしの場合は単純コピー
                shutil.copyfile(input_path, output_path)

        return output_path

    def _validate_output_quality(self, output_path: Path, settings: Dict[str, Any]) -> None:
        """
        出力ファイルの品質チェック

        Args:
            output_path: 出力ファイルパス
            settings: 処理設定
        """
        if not output_path.exists():
            raise Exception(f"出力ファイルが生成されていません: {output_path}")

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        max_size_mb = settings["max_file_size_mb"]

        if file_size_mb > max_size_mb:
            self.logger.warning(
                f"ファイルサイズが制限を超えています: {file_size_mb:.1f}MB > {max_size_mb}MB"
            )

        if file_size_mb < 0.1:  # 100KB未満は異常
            raise Exception(f"出力ファイルが小さすぎます: {file_size_mb:.1f}MB")

        self.logger.info(f"品質チェック完了 - サイズ: {file_size_mb:.1f}MB")

    def _cleanup_temp_files(self, *temp_files: Path) -> None:
        """
        一時ファイルの清掃

        Args:
            *temp_files: 削除する一時ファイルのパス
        """
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                self.logger.warning(f"一時ファイル削除エラー: {temp_file} - {e}")

    def _create_fallback_file(
        self, audio_data: bytes, episode_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        エラー時のフォールバック処理

        Args:
            audio_data: 元の音声データ
            episode_id: エピソードID
            metadata: メタデータ

        Returns:
            str: フォールバックファイルパス
        """
        self.logger.warning("フォールバック処理でファイル生成")

        output_dir = Path("output/podcast")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{episode_id}_fallback.mp3"

        with open(output_path, "wb") as f:
            # 基本MP3ヘッダー
            mp3_header = b"\xff\xfb\x90\x00"
            f.write(mp3_header)
            f.write(audio_data)

        return str(output_path)

    def get_processing_info(self) -> Dict[str, Any]:
        """
        処理環境の情報を取得

        Returns:
            Dict[str, Any]: 処理環境情報
        """
        return {
            "ffmpeg_available": bool(self.ffmpeg_path),
            "ffmpeg_path": self.ffmpeg_path,
            "assets_dir": str(self.assets_dir),
            "temp_dir": str(self.temp_dir),
            "default_settings": self.DEFAULT_SETTINGS.copy(),
        }

    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        """
        デフォルト設定を更新

        Args:
            new_settings: 新しい設定
        """
        self.DEFAULT_SETTINGS.update(new_settings)
        self.logger.info(f"処理設定を更新: {new_settings}")

    def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """
        音声ファイルの情報を取得

        Args:
            audio_path: 音声ファイルパス

        Returns:
            Dict[str, Any]: 音声ファイル情報
        """
        try:
            file_path = Path(audio_path)
            if not file_path.exists():
                return {"error": "ファイルが存在しません"}

            file_size = file_path.stat().st_size
            
            # FFmpegがある場合は詳細情報を取得
            if self.ffmpeg_path:
                try:
                    cmd = [
                        self.ffmpeg_path, "-i", str(file_path),
                        "-f", "null", "-"
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    
                    # 再生時間を抽出
                    duration = "00:00:00"
                    for line in result.stderr.split('\n'):
                        if "Duration:" in line:
                            duration = line.split("Duration:")[1].split(",")[0].strip()
                            break
                    
                    return {
                        "duration": duration,
                        "file_size": file_size,
                        "file_path": str(file_path)
                    }
                except Exception as info_error:
                    self.logger.warning(f"FFmpegでの音声情報取得エラー: {info_error}")
            
            # FFmpegが失敗した場合は基本情報のみ返す
            return {
                "duration": "00:00:00",
                "file_size": file_size,
                "file_path": str(file_path)
            }
            
        except Exception as e:
            self.logger.error(f"音声ファイル情報取得エラー: {e}")
            return {"error": str(e)}

    def get_credits_info(self) -> Dict[str, Any]:
        """
        使用中の音声アセットのクレジット情報を取得

        Returns:
            Dict[str, Any]: クレジット情報
        """
        try:
            credits_text = self.asset_manager.get_credits_text()
            assets_validation = self.asset_manager.validate_assets()
            
            return {
                "credits_text": credits_text,
                "assets_available": assets_validation,
                "assets_directory": str(self.assets_dir)
            }
            
        except Exception as e:
            self.logger.error(f"クレジット情報取得エラー: {e}")
            return {"error": str(e)}

    def cleanup_old_files(self, days: int = 7) -> None:
        """
        古い一時ファイルのクリーンアップ

        Args:
            days: 保持日数
        """
        try:
            import time
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        self.logger.debug(f"古いファイルを削除: {file_path}")
                    except Exception as e:
                        self.logger.warning(f"ファイル削除エラー: {file_path} - {e}")
                        
            self.logger.info(f"古いファイルのクリーンアップ完了: {days}日以上経過したファイルを削除")
            
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")

    def compress_audio(self, audio_path: str, target_size_mb: float) -> str:
        """
        音声ファイルを指定サイズ以下に圧縮

        Args:
            audio_path: 元の音声ファイルパス
            target_size_mb: 目標ファイルサイズ（MB）

        Returns:
            str: 圧縮後のファイルパス
        """
        try:
            input_path = Path(audio_path)
            current_size_mb = input_path.stat().st_size / (1024 * 1024)
            
            if current_size_mb <= target_size_mb:
                self.logger.info(f"ファイルサイズは既に目標以下です: {current_size_mb:.1f}MB <= {target_size_mb}MB")
                return str(input_path)
            
            if not self.ffmpeg_path:
                self.logger.warning("FFmpegが利用できないため圧縮をスキップします")
                return str(input_path)
            
            # 圧縮後ファイルパス
            compressed_path = input_path.parent / f"{input_path.stem}_compressed.mp3"
            
            # ビットレートを計算（圧縮率に基づく）
            compression_ratio = target_size_mb / current_size_mb
            original_bitrate = 128  # 元のビットレート推定
            target_bitrate = max(64, int(original_bitrate * compression_ratio))
            
            # 圧縮コマンド
            cmd = [
                self.ffmpeg_path,
                "-i", str(input_path),
                "-c:a", "libmp3lame",
                "-b:a", f"{target_bitrate}k",
                "-ar", "44100",
                "-ac", "1",
                "-y", str(compressed_path)
            ]
            
            self.logger.info(f"音声圧縮実行中: {current_size_mb:.1f}MB -> 目標{target_size_mb}MB (ビットレート: {target_bitrate}kbps)")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0 and compressed_path.exists():
                final_size_mb = compressed_path.stat().st_size / (1024 * 1024)
                self.logger.info(f"音声圧縮完了: {final_size_mb:.1f}MB")
                return str(compressed_path)
            else:
                self.logger.error(f"音声圧縮失敗: {result.stderr}")
                return str(input_path)
                
        except Exception as e:
            self.logger.error(f"音声圧縮エラー: {e}")
            return str(input_path)
