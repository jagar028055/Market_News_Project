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


class AudioProcessor:
    """
    音声処理クラス

    機能:
    - 音量正規化（-16 LUFS）
    - MP3 128kbps出力
    - メタデータ埋め込み
    - 品質管理
    """

    # デフォルト処理設定
    DEFAULT_SETTINGS = {
        "lufs_target": -16.0,  # LUFS ラウドネス目標値
        "peak_target": -1.0,  # ピーク制限（dBFS）
        "bitrate": "128k",  # MP3ビットレート
        "sample_rate": 44100,  # サンプリングレート
        "channels": 1,  # モノラル（ポッドキャスト標準）
        "max_file_size_mb": 15,  # 最大ファイルサイズ（MB）
        "target_duration_minutes": 10.0,  # 目標再生時間（分）
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

            # 高品質音声処理パイプライン
            if self.ffmpeg_path:
                processed_path = self._process_with_ffmpeg(
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

    def _process_with_ffmpeg(
        self,
        input_path: Path,
        output_path: Path,
        settings: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        FFmpegを使用した高品質音声処理

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

        try:
            # ステップ1: ラウドネス正規化
            self._normalize_loudness(input_path, temp_normalized, settings)

            # ステップ2: 最終エンコーディング + メタデータ埋め込み
            self._encode_final_output(temp_normalized, output_path, settings, metadata)

            return output_path

        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg処理エラー: {e}")
            raise
        finally:
            # 一時ファイル清掃
            if temp_normalized.exists():
                temp_normalized.unlink()

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
