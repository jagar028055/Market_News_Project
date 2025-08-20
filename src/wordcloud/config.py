# -*- coding: utf-8 -*-
"""
ワードクラウド設定管理モジュール

ワードクラウド生成に関する全ての設定を管理します。
"""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class WordCloudConfig:
    """ワードクラウド生成設定"""

    # 基本設定
    width: int = 800
    height: int = 400
    background_color: str = "white"
    max_words: int = 100

    # フォント設定
    font_path: Optional[str] = None
    font_size_min: int = 10
    font_size_max: int = 100

    # 色設定
    colormap: str = "viridis"
    prefer_horizontal: float = 0.7

    # テキスト処理設定
    min_word_length: int = 2
    max_word_length: int = 15
    min_frequency: int = 2

    # MeCab設定
    mecab_dicdir: Optional[str] = None
    pos_filter: List[str] = field(
        default_factory=lambda: [
            "名詞,一般",
            "名詞,固有名詞",
            "名詞,サ変接続",
            "形容詞,自立",
            "動詞,自立",
            "副詞,一般",
        ]
    )

    # ストップワード設定
    stopwords_file: str = "assets/config/stopwords_japanese.txt"
    custom_stopwords: List[str] = field(default_factory=list)

    # 金融重要語句設定
    financial_weights_file: str = "assets/config/financial_weights.json"
    financial_weights: Dict[str, float] = field(default_factory=dict)

    # TF-IDF設定
    use_tfidf: bool = True
    tfidf_max_features: int = 1000
    tfidf_ngram_range: tuple = (1, 2)

    # 品質設定
    quality_threshold: float = 80.0
    max_file_size_kb: int = 500

    # パフォーマンス設定
    max_processing_time_seconds: int = 30
    memory_limit_mb: int = 512


def load_stopwords(stopwords_file: str) -> List[str]:
    """ストップワードファイルを読み込み"""
    try:
        stopwords = []
        if os.path.exists(stopwords_file):
            with open(stopwords_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        stopwords.append(line)
        return stopwords
    except Exception as e:
        print(f"ストップワード読み込みエラー: {e}")
        return []


def load_financial_weights(weights_file: str) -> Dict[str, float]:
    """金融重要語句の重み設定を読み込み"""
    try:
        if os.path.exists(weights_file):
            with open(weights_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("financial_weights", {})
        return {}
    except Exception as e:
        print(f"金融重み設定読み込みエラー: {e}")
        return {}


def get_default_font_path() -> Optional[str]:
    """デフォルト日本語フォントパスを取得"""

    # よく使われる日本語フォントパス
    font_candidates = [
        # macOS
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Hiragino Sans GB W3.otf",
        "/Library/Fonts/Osaka.ttf",
        # Linux
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        "/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf",
        # Windows (WSLやWindows環境)
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
        # Homebrew経由でインストールした場合
        "/opt/homebrew/share/fonts/NotoSansCJK-Regular.ttc",
    ]

    for font_path in font_candidates:
        if os.path.exists(font_path):
            return font_path

    return None


def load_wordcloud_config() -> WordCloudConfig:
    """環境変数を考慮してWordCloud設定を読み込み"""

    config = WordCloudConfig()

    # 環境変数からの設定上書き
    if os.getenv("WORDCLOUD_WIDTH"):
        config.width = int(os.getenv("WORDCLOUD_WIDTH"))

    if os.getenv("WORDCLOUD_HEIGHT"):
        config.height = int(os.getenv("WORDCLOUD_HEIGHT"))

    if os.getenv("WORDCLOUD_MAX_WORDS"):
        config.max_words = int(os.getenv("WORDCLOUD_MAX_WORDS"))

    if os.getenv("WORDCLOUD_COLORMAP"):
        config.colormap = os.getenv("WORDCLOUD_COLORMAP")

    if os.getenv("WORDCLOUD_BACKGROUND_COLOR"):
        config.background_color = os.getenv("WORDCLOUD_BACKGROUND_COLOR")

    # フォントパス設定
    font_path = os.getenv("WORDCLOUD_FONT_PATH") or get_default_font_path()
    if font_path and os.path.exists(font_path):
        config.font_path = font_path

    # ストップワードを読み込み
    stopwords = load_stopwords(config.stopwords_file)
    if stopwords:
        config.custom_stopwords.extend(stopwords)

    # 金融重要語句の重みを読み込み
    financial_weights = load_financial_weights(config.financial_weights_file)
    if financial_weights:
        config.financial_weights.update(financial_weights)

    return config


def get_wordcloud_config() -> WordCloudConfig:
    """WordCloud設定のシングルトンアクセス"""
    if not hasattr(get_wordcloud_config, "_config"):
        get_wordcloud_config._config = load_wordcloud_config()
    return get_wordcloud_config._config


# 設定バリデーション関数
def validate_config(config: WordCloudConfig) -> List[str]:
    """設定の妥当性をチェック"""
    errors = []

    if config.width <= 0 or config.height <= 0:
        errors.append("画像サイズは正の値である必要があります")

    if config.max_words <= 0:
        errors.append("最大単語数は正の値である必要があります")

    if config.font_size_min >= config.font_size_max:
        errors.append("最小フォントサイズは最大フォントサイズより小さい必要があります")

    if config.font_path and not os.path.exists(config.font_path):
        errors.append(f"フォントファイルが見つかりません: {config.font_path}")

    if not os.path.exists(config.stopwords_file):
        errors.append(f"ストップワードファイルが見つかりません: {config.stopwords_file}")

    if not os.path.exists(config.financial_weights_file):
        errors.append(f"金融重み設定ファイルが見つかりません: {config.financial_weights_file}")

    return errors
