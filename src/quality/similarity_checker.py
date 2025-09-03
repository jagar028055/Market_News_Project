# -*- coding: utf-8 -*-

"""
記事類似度チェッカー
重複・類似記事を検出し、多様性を評価する
"""

from typing import List, Dict, Any, Tuple, Optional
import logging
import re
import math
from collections import Counter
from datetime import datetime, timedelta


class SimilarityChecker:
    """記事類似度チェッカー"""
    
    def __init__(self, 
                 similarity_threshold: float = 0.7,
                 min_diversity_score: float = 0.6,
                 logger: Optional[logging.Logger] = None):
        """
        初期化
        
        Args:
            similarity_threshold: 類似度判定閾値 (0-1)
            min_diversity_score: 最小多様性スコア (0-1)
            logger: ロガー
        """
        self.similarity_threshold = similarity_threshold
        self.min_diversity_score = min_diversity_score
        self.logger = logger or logging.getLogger(__name__)
        
        # ストップワード (よくある単語で類似度計算から除外)
        self.stop_words = {
            'は', 'が', 'を', 'に', 'へ', 'と', 'で', 'の', 'から', 'まで',
            'した', 'する', 'される', 'している', 'です', 'である', 'だった',
            'こと', 'もの', 'ため', 'など', 'として', 'について', 'により',
            '年', '月', '日', '時', '分', 'および', 'または', 'しかし', 'また'
        }
    
    def check_similarity_batch(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        記事バッチの類似度をチェック
        
        Args:
            articles: 記事リスト
        
        Returns:
            Dict[str, Any]: 類似度チェック結果
        """
        self.logger.info(f"類似度チェック開始: {len(articles)}件")
        
        if len(articles) < 2:
            return {
                'total_articles': len(articles),
                'similar_pairs': [],
                'duplicate_groups': [],
                'diversity_score': 1.0,
                'recommendations': []
            }
        
        # ペアワイズ類似度計算
        similar_pairs = []
        similarity_matrix = {}
        
        for i in range(len(articles)):
            for j in range(i + 1, len(articles)):
                similarity = self._calculate_similarity(articles[i], articles[j])
                similarity_matrix[(i, j)] = similarity
                
                if similarity >= self.similarity_threshold:
                    similar_pairs.append({
                        'article_1': {
                            'index': i,
                            'title': articles[i].get('title', '')[:100],
                            'source': articles[i].get('source', '')
                        },
                        'article_2': {
                            'index': j,
                            'title': articles[j].get('title', '')[:100],
                            'source': articles[j].get('source', '')
                        },
                        'similarity': round(similarity, 3)
                    })
        
        # 重複グループの特定
        duplicate_groups = self._find_duplicate_groups(similarity_matrix, len(articles))
        
        # 多様性スコア計算
        diversity_score = self._calculate_diversity_score(articles, similarity_matrix)
        
        # 推奨事項生成
        recommendations = self._generate_recommendations(similar_pairs, duplicate_groups, diversity_score)
        
        result = {
            'total_articles': len(articles),
            'similar_pairs': similar_pairs,
            'duplicate_groups': duplicate_groups,
            'diversity_score': round(diversity_score, 3),
            'recommendations': recommendations,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"類似度チェック完了: 類似ペア={len(similar_pairs)}組, 多様性={diversity_score:.3f}")
        return result
    
    def _calculate_similarity(self, article1: Dict[str, Any], article2: Dict[str, Any]) -> float:
        """2つの記事間の類似度を計算"""
        
        # テキスト抽出
        text1 = self._extract_comparable_text(article1)
        text2 = self._extract_comparable_text(article2)
        
        if not text1 or not text2:
            return 0.0
        
        # 複数の類似度指標を組み合わせ
        title_sim = self._cosine_similarity(
            article1.get('title', ''),
            article2.get('title', '')
        )
        
        summary_sim = self._cosine_similarity(
            article1.get('summary', ''),
            article2.get('summary', '')
        )
        
        # Jaccard類似度も計算
        jaccard_sim = self._jaccard_similarity(text1, text2)
        
        # 加重平均で最終類似度を計算
        final_similarity = (
            title_sim * 0.4 +      # タイトルの重み
            summary_sim * 0.5 +    # 要約の重み
            jaccard_sim * 0.1      # Jaccard類似度の重み
        )
        
        return final_similarity
    
    def _extract_comparable_text(self, article: Dict[str, Any]) -> str:
        """比較可能なテキストを抽出・正規化"""
        title = article.get('title', '')
        summary = article.get('summary', '')
        text = f"{title} {summary}"
        
        # テキスト正規化
        text = re.sub(r'[^\w\s]', '', text)  # 句読点除去
        text = text.lower()
        
        return text
    
    def _cosine_similarity(self, text1: str, text2: str) -> float:
        """コサイン類似度を計算"""
        if not text1 or not text2:
            return 0.0
        
        # 単語分割（簡易版、実際にはMeCab等を使用すべき）
        words1 = self._tokenize_japanese(text1)
        words2 = self._tokenize_japanese(text2)
        
        # ストップワード除去
        words1 = [w for w in words1 if w not in self.stop_words and len(w) > 1]
        words2 = [w for w in words2 if w not in self.stop_words and len(w) > 1]
        
        if not words1 or not words2:
            return 0.0
        
        # 語彙の統合
        vocab = set(words1 + words2)
        
        # ベクトル化
        vec1 = [words1.count(word) for word in vocab]
        vec2 = [words2.count(word) for word in vocab]
        
        # コサイン類似度計算
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Jaccard類似度を計算"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(self._tokenize_japanese(text1))
        words2 = set(self._tokenize_japanese(text2))
        
        # ストップワード除去
        words1 = {w for w in words1 if w not in self.stop_words and len(w) > 1}
        words2 = {w for w in words2 if w not in self.stop_words and len(w) > 1}
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _tokenize_japanese(self, text: str) -> List[str]:
        """日本語テキストの簡易トークン化"""
        # 実際の実装ではMeCabやJanomeを使用すべき
        
        # ひらがな・カタカナ・漢字・英数字のパターンで分割
        tokens = re.findall(r'[一-龯]+|[ア-ン]+|[あ-ん]+|[a-zA-Z0-9]+', text)
        
        # 2文字以上の語句のみ採用
        tokens = [token for token in tokens if len(token) >= 2]
        
        return tokens
    
    def _find_duplicate_groups(self, similarity_matrix: Dict[Tuple[int, int], float], num_articles: int) -> List[List[int]]:
        """重複グループを特定"""
        # Union-Find的なアプローチで類似記事をグループ化
        groups = []
        visited = set()
        
        for i in range(num_articles):
            if i in visited:
                continue
            
            group = [i]
            visited.add(i)
            
            # iと類似している記事を再帰的に探索
            def find_similar(article_idx):
                for j in range(num_articles):
                    if j in visited:
                        continue
                    
                    # 類似度チェック
                    pair = (min(article_idx, j), max(article_idx, j))
                    if pair in similarity_matrix and similarity_matrix[pair] >= self.similarity_threshold:
                        group.append(j)
                        visited.add(j)
                        find_similar(j)  # 再帰的に探索
            
            find_similar(i)
            
            # 複数の記事を含むグループのみを重複として扱う
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    def _calculate_diversity_score(self, articles: List[Dict[str, Any]], similarity_matrix: Dict[Tuple[int, int], float]) -> float:
        """コンテンツ多様性スコアを計算"""
        if len(articles) < 2:
            return 1.0
        
        # 平均類似度を計算（低いほど多様）
        similarities = list(similarity_matrix.values())
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        
        # カテゴリ多様性
        categories = [article.get('category', 'その他') for article in articles]
        category_diversity = len(set(categories)) / len(categories)
        
        # 地域多様性
        regions = [article.get('region', 'その他') for article in articles]
        region_diversity = len(set(regions)) / len(regions)
        
        # ソース多様性
        sources = [article.get('source', '') for article in articles]
        source_diversity = len(set(sources)) / len(sources) if sources else 0.0
        
        # 総合多様性スコア計算
        content_diversity = 1.0 - avg_similarity  # 類似度が低いほど多様
        
        diversity_score = (
            content_diversity * 0.4 +
            category_diversity * 0.25 +
            region_diversity * 0.2 +
            source_diversity * 0.15
        )
        
        return max(0.0, min(1.0, diversity_score))
    
    def _generate_recommendations(self, similar_pairs: List[Dict[str, Any]], 
                                duplicate_groups: List[List[int]], 
                                diversity_score: float) -> List[str]:
        """推奨事項を生成"""
        recommendations = []
        
        if similar_pairs:
            recommendations.append(
                f"{len(similar_pairs)}組の類似記事ペアが検出されました。"
                "重複記事の除去または統合を検討してください。"
            )
        
        if duplicate_groups:
            recommendations.append(
                f"{len(duplicate_groups)}つの重複グループが検出されました。"
                "各グループから最良の記事を選択することを推奨します。"
            )
        
        if diversity_score < self.min_diversity_score:
            recommendations.append(
                f"コンテンツ多様性が低いです（スコア: {diversity_score:.3f}）。"
                "異なるソース、地域、カテゴリからの記事収集を増やしてください。"
            )
        
        if diversity_score < 0.4:
            recommendations.append(
                "極めて多様性が低い状況です。記事取得フィルターの見直しが必要です。"
            )
        
        if not recommendations:
            recommendations.append("コンテンツの多様性と独自性は良好です。")
        
        return recommendations
    
    def check_temporal_similarity(self, articles: List[Dict[str, Any]], 
                                days_back: int = 7) -> Dict[str, Any]:
        """
        過去記事との時系列類似度をチェック
        
        Args:
            articles: 現在の記事リスト
            days_back: 比較対象とする過去の日数
        
        Returns:
            Dict[str, Any]: 時系列類似度分析結果
        """
        # この機能は実際にはデータベースとの連携が必要
        # ここでは基本的な枠組みのみ実装
        
        self.logger.info(f"時系列類似度チェック開始: {days_back}日前まで")
        
        # 実際の実装では、データベースから過去の記事を取得
        # past_articles = self.db_manager.get_articles_from_days_back(days_back)
        
        return {
            'checked_days': days_back,
            'current_articles': len(articles),
            'temporal_analysis': "データベース連携が必要な機能です",
            'recommendations': [
                "過去記事との重複チェックを実装するには、",
                "データベースとの連携機能が必要です"
            ]
        }
    
    def get_similarity_report(self, similarity_results: Dict[str, Any]) -> str:
        """類似度チェック結果のレポートを生成"""
        report_lines = [
            "=== 記事類似度・多様性分析レポート ===",
            f"分析日時: {similarity_results.get('analysis_timestamp', 'N/A')}",
            f"対象記事数: {similarity_results.get('total_articles', 0)}件",
            "",
            f"類似記事ペア: {len(similarity_results.get('similar_pairs', []))}組",
            f"重複グループ: {len(similarity_results.get('duplicate_groups', []))}グループ",
            f"多様性スコア: {similarity_results.get('diversity_score', 0):.3f}",
            ""
        ]
        
        # 推奨事項
        recommendations = similarity_results.get('recommendations', [])
        if recommendations:
            report_lines.append("推奨事項:")
            for i, rec in enumerate(recommendations, 1):
                report_lines.append(f"{i}. {rec}")
        
        return "\n".join(report_lines)