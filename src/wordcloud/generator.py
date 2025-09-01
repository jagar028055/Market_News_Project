# -*- coding: utf-8 -*-
"""
ワードクラウド生成エンジン

テキスト処理から画像生成まで統合的に管理します。
"""

import time
from typing import Dict, List, Optional, NamedTuple
from dataclasses import dataclass
from datetime import datetime

from .config import WordCloudConfig
from .processor import TextProcessor
from .visualizer import WordCloudVisualizer


@dataclass
class WordCloudResult:
    """ワードクラウド生成結果"""

    success: bool
    image_base64: Optional[str] = None
    word_frequencies: Optional[Dict[str, int]] = None
    total_articles: int = 0
    total_words: int = 0
    unique_words: int = 0
    generation_time_ms: int = 0
    quality_score: float = 0.0
    error_message: Optional[str] = None


class WordCloudGenerator:
    """ワードクラウド生成エンジン

    記事データからワードクラウド画像を生成する統合エンジンです。
    """

    def __init__(self, config: WordCloudConfig):
        """初期化

        Args:
            config: ワードクラウド設定
        """
        self.config = config
        self.processor = TextProcessor(config)
        self.visualizer = WordCloudVisualizer(config)

    def generate_daily_wordcloud(self, articles: List[Dict]) -> WordCloudResult:
        """日次ワードクラウドを生成

        Args:
            articles: 記事データのリスト

        Returns:
            ワードクラウド生成結果
        """
        start_time = time.time()

        try:
            # バリデーション
            if not articles:
                return WordCloudResult(success=False, error_message="記事データが空です")

            # 1. テキスト処理
            word_frequencies = self.processor.process(articles)

            if not word_frequencies:
                return WordCloudResult(
                    success=False, error_message="有効な単語が抽出されませんでした"
                )

            # 2. ワードクラウド画像生成
            image_result = self.visualizer.create_wordcloud_image(word_frequencies)

            if not image_result.success:
                return WordCloudResult(
                    success=False, error_message=f"画像生成失敗: {image_result.error_message}"
                )

            # 3. 統計情報計算
            total_words = sum(word_frequencies.values())
            unique_words = len(word_frequencies)

            # 4. 品質スコア計算
            quality_score = self._calculate_quality_score(
                word_frequencies, len(articles), image_result.image_size_bytes or 0
            )

            # 5. 処理時間計算
            generation_time_ms = int((time.time() - start_time) * 1000)

            return WordCloudResult(
                success=True,
                image_base64=image_result.image_base64,
                word_frequencies=word_frequencies,
                total_articles=len(articles),
                total_words=total_words,
                unique_words=unique_words,
                generation_time_ms=generation_time_ms,
                quality_score=quality_score,
            )

        except Exception as e:
            generation_time_ms = int((time.time() - start_time) * 1000)
            return WordCloudResult(
                success=False,
                generation_time_ms=generation_time_ms,
                error_message=f"生成エラー: {str(e)}",
            )

    def _calculate_quality_score(
        self, word_frequencies: Dict[str, int], article_count: int, image_size_bytes: int
    ) -> float:
        """ワードクラウドの品質スコアを計算

        Args:
            word_frequencies: 単語頻度辞書
            article_count: 記事数
            image_size_bytes: 画像サイズ（バイト）

        Returns:
            品質スコア（0-100）
        """
        try:
            score = 0.0

            # 1. 単語数の多様性（0-30点）
            unique_words = len(word_frequencies)
            diversity_score = min(unique_words / self.config.max_words * 30, 30)
            score += diversity_score

            # 2. 頻度分布の均等性（0-25点）
            if word_frequencies:
                frequencies = list(word_frequencies.values())
                max_freq = max(frequencies)
                min_freq = min(frequencies)

                if max_freq > 0:
                    ratio = min_freq / max_freq
                    balance_score = ratio * 25
                    score += balance_score

            # 3. 記事カバレッジ（0-20点）
            if article_count > 0:
                coverage_ratio = min(unique_words / article_count, 1.0)
                coverage_score = coverage_ratio * 20
                score += coverage_score

            # 4. ファイルサイズ効率性（0-15点）
            max_size_bytes = self.config.max_file_size_kb * 1024
            if image_size_bytes > 0:
                if image_size_bytes <= max_size_bytes:
                    size_efficiency = 15 - (image_size_bytes / max_size_bytes) * 5
                    score += max(size_efficiency, 10)
                else:
                    score += 5  # オーバーサイズペナルティ

            # 5. 金融用語の含有率（0-10点）
            financial_word_count = sum(
                1 for word in word_frequencies.keys() if word in self.config.financial_weights
            )
            if unique_words > 0:
                financial_ratio = financial_word_count / unique_words
                financial_score = min(financial_ratio * 10, 10)
                score += financial_score

            return min(score, 100.0)

        except Exception as e:
            print(f"品質スコア計算エラー: {e}")
            return 50.0  # デフォルトスコア

    def generate_wordcloud_for_session(
        self, session_id: int, articles: List[Dict]
    ) -> WordCloudResult:
        """セッション用ワードクラウドを生成

        Args:
            session_id: スクレイピングセッションID
            articles: 記事データのリスト

        Returns:
            ワードクラウド生成結果
        """
        # 基本的には daily_wordcloud と同じ処理
        return self.generate_daily_wordcloud(articles)
