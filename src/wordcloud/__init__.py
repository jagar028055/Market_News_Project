# -*- coding: utf-8 -*-
"""
ワードクラウド生成機能モジュール

このモジュールは市場ニュース記事から日次ワードクラウドを生成する機能を提供します。
主要コンポーネント:
- テキスト処理エンジン (processor.py)
- ワードクラウド生成器 (generator.py)
- 視覚化コンポーネント (visualizer.py)
- 設定管理 (config.py)
"""

from .config import WordCloudConfig, load_wordcloud_config
from .processor import TextProcessor
from .generator import WordCloudGenerator
from .visualizer import WordCloudVisualizer

__version__ = "1.0.0"

__all__ = [
    "WordCloudConfig",
    "load_wordcloud_config",
    "TextProcessor",
    "WordCloudGenerator",
    "WordCloudVisualizer",
]
