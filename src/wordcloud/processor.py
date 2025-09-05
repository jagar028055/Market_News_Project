# -*- coding: utf-8 -*-
"""
テキスト処理エンジン

記事データから意味のある単語を抽出し、ワードクラウド生成用のデータを準備します。
"""

import re
from janome.tokenizer import Tokenizer
from typing import Dict, List, Optional, Tuple
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

from .config import WordCloudConfig


class TextProcessor:
    """テキスト処理エンジン

    日本語テキストの形態素解析、前処理、重み付けを行います。
    """

    def __init__(self, config: WordCloudConfig):
        """初期化

        Args:
            config: ワードクラウド設定
        """
        self.config = config
        self.tokenizer = None
        self.stopwords = set(config.custom_stopwords)
        self.financial_weights = config.financial_weights

        self._initialize_janome()

    def _initialize_janome(self):
        """Janomeを初期化"""
        try:
            # Janome トークナイザーを初期化
            self.tokenizer = Tokenizer()

            # テスト解析を実行して動作確認
            test_tokens = list(self.tokenizer.tokenize("テスト", wakati=False))
            if not test_tokens:
                raise Exception("Janome動作テスト失敗")

            print("Janome初期化成功: 純Python実装で安定動作")

        except Exception as e:
            print(f"Janome初期化エラー: {e}")
            print("フォールバック: シンプルな単語分割を使用します")
            self.tokenizer = None

    def process_articles_text(self, articles: List[Dict]) -> str:
        """記事リストから統合テキストを生成

        Args:
            articles: 記事データのリスト

        Returns:
            統合されたテキスト文字列
        """
        combined_text = []

        for article in articles:
            title = article.get("title", "")
            body = article.get("body", "")

            # タイトルは重要度を上げるため2回追加
            if title:
                combined_text.extend([title, title])

            if body:
                combined_text.append(body)

        return " ".join(combined_text)

    def extract_meaningful_words(self, text: str) -> List[str]:
        """テキストから意味のある単語を抽出

        Args:
            text: 処理対象テキスト

        Returns:
            抽出された単語のリスト
        """
        if not self.tokenizer:
            print("Janomeが利用できません。簡易処理を使用します。")
            return self._simple_word_extraction(text)

        try:
            # Janomeによる形態素解析
            tokens = self.tokenizer.tokenize(text, wakati=False)
            words = []

            for token in tokens:
                # 品詞情報を取得
                features = token.part_of_speech.split(",")
                pos = f"{features[0]},{features[1]}" if len(features) > 1 else features[0]
                word = token.surface

                # フィルタリング条件
                if (
                    word
                    and len(word) >= self.config.min_word_length
                    and len(word) <= self.config.max_word_length
                    and pos in self.config.pos_filter
                    and word not in self.stopwords
                    and not self._is_numeric(word)
                ):

                    words.append(word)

            return words

        except Exception as e:
            print(f"形態素解析エラー: {e}")
            return self._simple_word_extraction(text)

    def _simple_word_extraction(self, text: str) -> List[str]:
        """簡易単語抽出（MeCab非対応時の代替手段）

        Args:
            text: 処理対象テキスト

        Returns:
            抽出された単語のリスト
        """
        # 簡易的な日本語単語抽出
        words = []

        # スペースや句読点で分割
        text = re.sub(r"[、。！？\s]+", " ", text)
        word_candidates = text.split()

        for word in word_candidates:
            # 記号を除去
            cleaned_word = re.sub(r"[^\w]", "", word)

            if (
                cleaned_word
                and len(cleaned_word) >= self.config.min_word_length
                and len(cleaned_word) <= self.config.max_word_length
                and cleaned_word not in self.stopwords
                and not self._is_numeric(cleaned_word)
            ):
                words.append(cleaned_word)

        return words

    def _is_numeric(self, word: str) -> bool:
        """数値のみの文字列かチェック

        Args:
            word: チェック対象の単語

        Returns:
            数値のみの場合True
        """
        return bool(re.match(r"^[\d０-９]+$", word))

    def calculate_word_frequencies(self, words: List[str]) -> Dict[str, int]:
        """単語頻度を計算

        Args:
            words: 単語のリスト

        Returns:
            単語頻度辞書
        """
        frequency_counter = Counter(words)

        # 最小頻度でフィルタリング
        filtered_frequencies = {
            word: freq
            for word, freq in frequency_counter.items()
            if freq >= self.config.min_frequency
        }

        return filtered_frequencies

    def apply_financial_weights(self, frequencies: Dict[str, int]) -> Dict[str, int]:
        """金融重要語句の重み付けを適用

        Args:
            frequencies: 元の単語頻度辞書

        Returns:
            重み付け後の単語頻度辞書
        """
        weighted_frequencies = frequencies.copy()

        for word, freq in frequencies.items():
            if word in self.financial_weights:
                weight = self.financial_weights[word]
                weighted_frequencies[word] = int(freq * weight)

        return weighted_frequencies

    def calculate_tfidf_scores(self, texts: List[str], words: List[str]) -> Dict[str, float]:
        """TF-IDFスコアを計算

        Args:
            texts: 文書のリスト
            words: 対象単語のリスト

        Returns:
            単語のTF-IDFスコア辞書
        """
        if not self.config.use_tfidf or len(texts) < 2:
            return {}

        try:
            # TF-IDFベクトライザーを初期化
            vectorizer = TfidfVectorizer(
                max_features=self.config.tfidf_max_features,
                ngram_range=self.config.tfidf_ngram_range,
                vocabulary=words,
            )

            # TF-IDF行列を計算
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()

            # 平均TF-IDFスコアを計算
            mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)

            return dict(zip(feature_names, mean_scores))

        except Exception as e:
            print(f"TF-IDF計算エラー: {e}")
            return {}

    def process(self, articles: List[Dict]) -> Dict[str, int]:
        """メイン処理：記事から重み付け済み単語頻度を生成

        Args:
            articles: 記事データのリスト

        Returns:
            重み付け済み単語頻度辞書
        """
        # 1. 統合テキスト生成
        combined_text = self.process_articles_text(articles)

        # 2. 意味のある単語を抽出
        words = self.extract_meaningful_words(combined_text)

        # 3. 基本頻度計算
        frequencies = self.calculate_word_frequencies(words)

        # 4. 金融重要語句の重み付け適用
        weighted_frequencies = self.apply_financial_weights(frequencies)

        # 5. TF-IDF適用（オプション）
        if self.config.use_tfidf:
            article_texts = [
                f"{article.get('title', '')} {article.get('body', '')}" for article in articles
            ]
            tfidf_scores = self.calculate_tfidf_scores(
                article_texts, list(weighted_frequencies.keys())
            )

            # TF-IDFスコアを頻度に反映
            for word in weighted_frequencies:
                if word in tfidf_scores:
                    tfidf_weight = max(tfidf_scores[word] * 10, 1.0)  # 最低1倍保証
                    weighted_frequencies[word] = int(weighted_frequencies[word] * tfidf_weight)

        return weighted_frequencies
