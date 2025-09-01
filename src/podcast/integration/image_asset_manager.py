# -*- coding: utf-8 -*-

"""
画像アセット管理クラス
LINE Flex Message用の画像アセットの管理と生成を行う
"""

import os
import json
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import logging


class ImageAssetManager:
    """
    画像アセット管理クラス

    LINE Flex Message用の画像生成・アップロード・URL管理を行う
    """

    def __init__(self, config, logger: logging.Logger):
        """
        初期化

        Args:
            config: アプリケーション設定
            logger: ロガー
        """
        self.config = config
        self.logger = logger

        # 画像保存パス設定
        self.assets_dir = Path(config.project_root) / "assets" / "images" / "line"
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        # 画像URL設定（GitHub Pagesベース）
        self.base_url = f"{config.podcast.base_url}/assets/images/line"

        # 画像サイズ設定
        self.image_sizes = {
            "icon": (120, 120),  # アイコン用
            "header": (1040, 520),  # ヘッダー画像
            "thumbnail": (360, 200),  # サムネイル
            "background": (1040, 1040),  # 背景画像
        }

        # 色設定
        self.colors = {
            "primary": "#1DB446",  # LINE Green
            "secondary": "#404040",  # Dark Gray
            "accent": "#FF6B00",  # Orange
            "text_primary": "#333333",
            "text_secondary": "#666666",
            "background": "#F8F8F8",
        }

        # 画像キャッシュ
        self.image_cache = {}
        self._load_cache()

    def get_or_create_podcast_image(
        self, episode_info: Dict[str, Any], image_type: str = "thumbnail"
    ) -> Optional[str]:
        """
        ポッドキャスト用画像を取得または生成

        Args:
            episode_info: エピソード情報
            image_type: 画像タイプ（thumbnail, header, icon, background）

        Returns:
            Optional[str]: 画像URL（生成失敗時はNone）
        """
        try:
            # キャッシュキーを生成
            cache_key = self._generate_cache_key(episode_info, image_type)

            # キャッシュから確認
            if cache_key in self.image_cache:
                cached_entry = self.image_cache[cache_key]
                if self._is_cache_valid(cached_entry):
                    self.logger.info(f"キャッシュから画像URL取得: {image_type}")
                    return cached_entry["url"]

            # 画像生成
            image_url = self._create_podcast_image(episode_info, image_type)

            if image_url:
                # キャッシュに保存
                self.image_cache[cache_key] = {
                    "url": image_url,
                    "created_at": time.time(),
                    "expires_at": time.time() + (24 * 60 * 60),  # 24時間有効
                    "episode_info": episode_info,
                    "image_type": image_type,
                }
                self._save_cache()

            return image_url

        except Exception as e:
            self.logger.error(f"画像取得・生成エラー: {e}")
            return None

    def _create_podcast_image(self, episode_info: Dict[str, Any], image_type: str) -> Optional[str]:
        """
        ポッドキャスト画像を実際に生成

        Args:
            episode_info: エピソード情報
            image_type: 画像タイプ

        Returns:
            Optional[str]: 生成された画像URL
        """
        try:
            # PIL (Pillow) を使用した画像生成
            return self._generate_image_with_pillow(episode_info, image_type)

        except ImportError:
            # Pillowが利用できない場合は代替手段
            self.logger.warning("Pillowが利用できません。代替画像を使用します")
            return self._get_fallback_image(image_type)
        except Exception as e:
            self.logger.error(f"画像生成エラー: {e}")
            return self._get_fallback_image(image_type)

    def _generate_image_with_pillow(
        self, episode_info: Dict[str, Any], image_type: str
    ) -> Optional[str]:
        """
        Pillowを使用して画像を生成

        Args:
            episode_info: エピソード情報
            image_type: 画像タイプ

        Returns:
            Optional[str]: 生成された画像URL
        """
        try:
            from PIL import Image, ImageDraw, ImageFont

            # 画像サイズ取得
            width, height = self.image_sizes.get(image_type, (360, 200))

            # 基本画像作成
            img = Image.new("RGB", (width, height), self.colors["background"])
            draw = ImageDraw.Draw(img)

            # エピソード情報取得
            published_at = episode_info.get("published_at", datetime.now())
            article_count = episode_info.get("article_count", 0)

            if isinstance(published_at, datetime):
                date_str = published_at.strftime("%Y/%m/%d")
            else:
                date_str = datetime.now().strftime("%Y/%m/%d")

            # 画像タイプ別の描画
            if image_type == "thumbnail":
                self._draw_thumbnail(draw, width, height, date_str, article_count)
            elif image_type == "header":
                self._draw_header(draw, width, height, date_str, article_count)
            elif image_type == "icon":
                self._draw_icon(draw, width, height)
            elif image_type == "background":
                self._draw_background(draw, width, height, date_str)

            # ファイル名生成
            filename = f"podcast_{image_type}_{self._generate_filename_hash(episode_info)}.png"
            filepath = self.assets_dir / filename

            # 画像保存
            img.save(filepath, "PNG", quality=95, optimize=True)

            # URL生成
            image_url = f"{self.base_url}/{filename}"

            self.logger.info(f"{image_type}画像生成完了: {filename}")
            return image_url

        except Exception as e:
            self.logger.error(f"Pillow画像生成エラー: {e}")
            return None

    def _draw_thumbnail(
        self, draw, width: int, height: int, date_str: str, article_count: int
    ) -> None:
        """サムネイル画像の描画"""
        # 背景グラデーション（簡易版）
        for i in range(height):
            color_ratio = i / height
            r = int(29 + (64 - 29) * color_ratio)  # 1DB446 → 404040
            g = int(180 + (64 - 180) * color_ratio)
            b = int(70 + (64 - 70) * color_ratio)
            draw.rectangle([(0, i), (width, i + 1)], fill=(r, g, b))

        # テキスト描画（フォント無しでも動作するよう簡素化）
        try:
            # システムフォント使用を試行
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        except:
            # フォントが利用できない場合はデフォルト
            font_large = font_medium = font_small = ImageFont.load_default()

        # タイトル
        title_text = "📻 マーケットニュース"
        title_bbox = draw.textbbox((0, 0), title_text, font=font_large)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) // 2, 30), title_text, fill="white", font=font_large)

        # 日付
        date_bbox = draw.textbbox((0, 0), date_str, font=font_medium)
        date_width = date_bbox[2] - date_bbox[0]
        draw.text(((width - date_width) // 2, 80), date_str, fill="white", font=font_medium)

        # 記事数
        articles_text = f"📰 {article_count}件のニュース"
        articles_bbox = draw.textbbox((0, 0), articles_text, font=font_small)
        articles_width = articles_bbox[2] - articles_bbox[0]
        draw.text(
            ((width - articles_width) // 2, height - 40),
            articles_text,
            fill="white",
            font=font_small,
        )

    def _draw_header(
        self, draw, width: int, height: int, date_str: str, article_count: int
    ) -> None:
        """ヘッダー画像の描画"""
        # より大きなヘッダー用の描画
        # グラデーション背景
        for i in range(height):
            color_ratio = i / height
            r = int(29 + (255 - 29) * color_ratio * 0.1)
            g = int(180 + (255 - 180) * color_ratio * 0.1)
            b = int(70 + (255 - 70) * color_ratio * 0.1)
            draw.rectangle([(0, i), (width, i + 1)], fill=(r, g, b))

        # 中央にメインテキスト
        try:
            font_title = ImageFont.load_default()
            font_subtitle = ImageFont.load_default()
        except:
            font_title = font_subtitle = ImageFont.load_default()

        # メインタイトル
        main_title = "🎙️ MARKET NEWS PODCAST"
        title_bbox = draw.textbbox((0, 0), main_title, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(
            ((width - title_width) // 2, height // 2 - 60),
            main_title,
            fill="white",
            font=font_title,
        )

        # サブタイトル
        subtitle = f"AIが読み上げる最新マーケット情報 | {date_str}"
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        draw.text(
            ((width - subtitle_width) // 2, height // 2 + 20),
            subtitle,
            fill="white",
            font=font_subtitle,
        )

    def _draw_icon(self, draw, width: int, height: int) -> None:
        """アイコン画像の描画"""
        # 円形の背景
        draw.ellipse([10, 10, width - 10, height - 10], fill=self.colors["primary"])

        # 中央にマイクアイコン（簡易版）
        center_x, center_y = width // 2, height // 2

        # マイク本体（楕円）
        draw.ellipse([center_x - 20, center_y - 30, center_x + 20, center_y + 10], fill="white")

        # マイクスタンド（線）
        draw.rectangle([center_x - 2, center_y + 10, center_x + 2, center_y + 35], fill="white")
        draw.rectangle([center_x - 15, center_y + 33, center_x + 15, center_y + 37], fill="white")

    def _draw_background(self, draw, width: int, height: int, date_str: str) -> None:
        """背景画像の描画"""
        # パターン背景を生成
        for x in range(0, width, 40):
            for y in range(0, height, 40):
                # チェッカーボードパターン
                if (x // 40 + y // 40) % 2 == 0:
                    draw.rectangle([x, y, x + 40, y + 40], fill=self.colors["background"])
                else:
                    draw.rectangle([x, y, x + 40, y + 40], fill="white")

        # 中央にロゴとテキスト
        overlay = Image.new("RGBA", (width, height), (29, 180, 70, 128))
        draw_overlay = ImageDraw.Draw(overlay)

        try:
            font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        text = "MARKET NEWS"
        text_bbox = draw_overlay.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        draw_overlay.text(((width - text_width) // 2, height // 2), text, fill="white", font=font)

    def _get_fallback_image(self, image_type: str) -> str:
        """
        フォールバック用のデフォルト画像URL

        Args:
            image_type: 画像タイプ

        Returns:
            str: デフォルト画像URL
        """
        # デフォルト画像のマッピング
        fallback_images = {
            "thumbnail": f"{self.base_url}/default_thumbnail.png",
            "header": f"{self.base_url}/default_header.png",
            "icon": f"{self.base_url}/default_icon.png",
            "background": f"{self.base_url}/default_background.png",
        }

        return fallback_images.get(image_type, f"{self.base_url}/default_thumbnail.png")

    def _generate_cache_key(self, episode_info: Dict[str, Any], image_type: str) -> str:
        """
        キャッシュキー生成

        Args:
            episode_info: エピソード情報
            image_type: 画像タイプ

        Returns:
            str: キャッシュキー
        """
        key_data = {
            "date": (
                episode_info.get("published_at", "").strftime("%Y-%m-%d")
                if isinstance(episode_info.get("published_at"), datetime)
                else str(episode_info.get("published_at", ""))
            ),
            "article_count": episode_info.get("article_count", 0),
            "type": image_type,
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _generate_filename_hash(self, episode_info: Dict[str, Any]) -> str:
        """
        ファイル名用ハッシュ生成

        Args:
            episode_info: エピソード情報

        Returns:
            str: ファイル名用ハッシュ
        """
        hash_data = f"{episode_info.get('published_at', '')}{episode_info.get('article_count', 0)}{int(time.time())}"
        return hashlib.md5(hash_data.encode()).hexdigest()[:12]

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """
        キャッシュの有効性を確認

        Args:
            cache_entry: キャッシュエントリ

        Returns:
            bool: 有効な場合True
        """
        return cache_entry.get("expires_at", 0) > time.time()

    def _load_cache(self) -> None:
        """キャッシュをファイルから読み込み"""
        cache_file = self.assets_dir / "image_cache.json"
        try:
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.image_cache = json.load(f)
                self.logger.info(f"画像キャッシュ読み込み完了: {len(self.image_cache)}件")
        except Exception as e:
            self.logger.warning(f"画像キャッシュ読み込みエラー: {e}")
            self.image_cache = {}

    def _save_cache(self) -> None:
        """キャッシュをファイルに保存"""
        cache_file = self.assets_dir / "image_cache.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self.image_cache, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"画像キャッシュ保存エラー: {e}")

    def cleanup_expired_cache(self) -> int:
        """
        期限切れキャッシュをクリーンアップ

        Returns:
            int: 削除されたエントリ数
        """
        current_time = time.time()
        expired_keys = []

        for key, entry in self.image_cache.items():
            if not self._is_cache_valid(entry):
                expired_keys.append(key)

        for key in expired_keys:
            del self.image_cache[key]

        if expired_keys:
            self._save_cache()
            self.logger.info(f"期限切れ画像キャッシュを{len(expired_keys)}件削除")

        return len(expired_keys)

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        キャッシュ統計情報を取得

        Returns:
            Dict[str, Any]: 統計情報
        """
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0

        for entry in self.image_cache.values():
            if self._is_cache_valid(entry):
                valid_entries += 1
            else:
                expired_entries += 1

        return {
            "total_entries": len(self.image_cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_size_mb": sum(os.path.getsize(f) for f in self.assets_dir.glob("*.png"))
            / 1024
            / 1024,
        }
