"""
音声アセット管理モジュール

CC-BYライセンス音声ファイルの管理とクレジット情報の提供
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
import yaml


logger = logging.getLogger(__name__)


@dataclass
class AudioAsset:
    """音声アセット情報"""

    file_path: str
    title: str
    author: str
    license: str
    license_url: str
    source_url: Optional[str] = None
    description: Optional[str] = None


@dataclass
class AssetCredits:
    """アセットクレジット情報"""

    intro_jingle: AudioAsset
    outro_jingle: AudioAsset
    background_music: AudioAsset
    segment_transition: AudioAsset


class AssetManager:
    """音声アセット管理クラス"""

    def __init__(self, assets_dir: str):
        """
        Args:
            assets_dir: 音声アセットディレクトリのパス
        """
        self.assets_dir = Path(assets_dir)
        self.credits_file = self.assets_dir / "credits.yaml"
        self._credits_cache: Optional[AssetCredits] = None

        # アセットディレクトリが存在しない場合は作成
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        # クレジットファイルが存在しない場合はサンプルを作成
        if not self.credits_file.exists():
            self._create_sample_credits_file()

    def get_asset_path(self, asset_type: str) -> Optional[str]:
        """
        指定されたタイプの音声アセットファイルパスを取得

        Args:
            asset_type: アセットタイプ (intro_jingle, outro_jingle, background_music, segment_transition)

        Returns:
            音声ファイルのフルパス、見つからない場合はNone
        """
        try:
            credits = self._load_credits()
            asset = getattr(credits, asset_type, None)
            if asset and os.path.exists(asset.file_path):
                return asset.file_path

            logger.warning(f"Asset file not found for type: {asset_type}")
            return None

        except Exception as e:
            logger.error(f"Error getting asset path for {asset_type}: {e}")
            return None

    def get_all_assets(self) -> Dict[str, Optional[str]]:
        """
        すべての音声アセットファイルパスを取得

        Returns:
            アセットタイプ → ファイルパスの辞書
        """
        asset_types = ["intro_jingle", "outro_jingle", "background_music", "segment_transition"]
        return {asset_type: self.get_asset_path(asset_type) for asset_type in asset_types}

    def get_credits_info(self) -> Optional[AssetCredits]:
        """
        音声アセットのクレジット情報を取得

        Returns:
            AssetCreditsオブジェクト、エラーの場合はNone
        """
        try:
            return self._load_credits()
        except Exception as e:
            logger.error(f"Error loading credits info: {e}")
            return None

    def get_credits_text(self) -> str:
        """
        クレジット情報をテキスト形式で取得

        Returns:
            フォーマットされたクレジットテキスト
        """
        try:
            credits = self._load_credits()
            if not credits:
                return "クレジット情報が読み込めませんでした。"

            credit_lines = []
            assets = [
                ("オープニングジングル", credits.intro_jingle),
                ("エンディングジングル", credits.outro_jingle),
                ("バックグラウンドミュージック", credits.background_music),
                ("セグメント移行音", credits.segment_transition),
            ]

            for asset_name, asset in assets:
                if asset:
                    line = f'{asset_name}: "{asset.title}" by {asset.author} ({asset.license}) - {asset.license_url}'
                    credit_lines.append(line)

            return "\\n".join(credit_lines)

        except Exception as e:
            logger.error(f"Error generating credits text: {e}")
            return "クレジット情報の生成に失敗しました。"

    def validate_assets(self) -> Dict[str, bool]:
        """
        すべての音声アセットファイルの存在確認

        Returns:
            アセットタイプ → 存在確認結果の辞書
        """
        validation_results = {}
        assets = self.get_all_assets()

        for asset_type, file_path in assets.items():
            if file_path and os.path.exists(file_path):
                validation_results[asset_type] = True
                logger.debug(f"Asset validation passed: {asset_type} -> {file_path}")
            else:
                validation_results[asset_type] = False
                logger.warning(f"Asset validation failed: {asset_type} -> {file_path}")

        return validation_results

    def _load_credits(self) -> AssetCredits:
        """クレジット情報をYAMLファイルから読み込み"""
        if self._credits_cache:
            return self._credits_cache

        try:
            with open(self.credits_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            assets_data = data["audio_assets"]

            self._credits_cache = AssetCredits(
                intro_jingle=self._create_audio_asset(assets_data["intro_jingle"]),
                outro_jingle=self._create_audio_asset(assets_data["outro_jingle"]),
                background_music=self._create_audio_asset(assets_data["background_music"]),
                segment_transition=self._create_audio_asset(assets_data["segment_transition"]),
            )

            return self._credits_cache

        except Exception as e:
            logger.error(f"Error loading credits from {self.credits_file}: {e}")
            raise

    def _create_audio_asset(self, asset_data: Dict) -> AudioAsset:
        """辞書データからAudioAssetオブジェクトを作成"""
        # 相対パスを絶対パスに変換
        file_path = asset_data["file_path"]
        if not os.path.isabs(file_path):
            file_path = str(self.assets_dir / file_path)

        return AudioAsset(
            file_path=file_path,
            title=asset_data["title"],
            author=asset_data["author"],
            license=asset_data["license"],
            license_url=asset_data["license_url"],
            source_url=asset_data.get("source_url"),
            description=asset_data.get("description"),
        )

    def _create_sample_credits_file(self):
        """サンプルクレジットファイルを作成"""
        sample_data = {
            "audio_assets": {
                "intro_jingle": {
                    "file_path": "intro_jingle.mp3",
                    "title": "Market News Intro",
                    "author": "Sample Creator",
                    "license": "CC BY 4.0",
                    "license_url": "https://creativecommons.org/licenses/by/4.0/",
                    "source_url": "https://example.com/intro",
                    "description": "Opening jingle for market news podcast",
                },
                "outro_jingle": {
                    "file_path": "outro_jingle.mp3",
                    "title": "Market News Outro",
                    "author": "Sample Creator",
                    "license": "CC BY 4.0",
                    "license_url": "https://creativecommons.org/licenses/by/4.0/",
                    "source_url": "https://example.com/outro",
                    "description": "Closing jingle for market news podcast",
                },
                "background_music": {
                    "file_path": "background_music.mp3",
                    "title": "Gentle Business Background",
                    "author": "Sample Musician",
                    "license": "CC BY 4.0",
                    "license_url": "https://creativecommons.org/licenses/by/4.0/",
                    "source_url": "https://example.com/bgm",
                    "description": "Background music for news segments",
                },
                "segment_transition": {
                    "file_path": "transition.mp3",
                    "title": "News Transition Sound",
                    "author": "Sample Audio Designer",
                    "license": "CC BY 4.0",
                    "license_url": "https://creativecommons.org/licenses/by/4.0/",
                    "source_url": "https://example.com/transition",
                    "description": "Transition sound between news segments",
                },
            }
        }

        try:
            with open(self.credits_file, "w", encoding="utf-8") as f:
                yaml.dump(sample_data, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"Created sample credits file: {self.credits_file}")

        except Exception as e:
            logger.error(f"Error creating sample credits file: {e}")
            raise
