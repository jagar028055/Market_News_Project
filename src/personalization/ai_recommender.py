"""
AI駆動コンテンツ推奨システム
機械学習とAIを活用したインテリジェントな記事推奨エンジン
"""

import json
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import hashlib
from collections import defaultdict, Counter
import math

@dataclass
class ContentVector:
    """コンテンツベクトル表現"""
    content_id: str
    title_vector: List[float]
    category_vector: List[float]  
    sentiment_score: float
    complexity_score: float
    freshness_score: float
    popularity_score: float

@dataclass
class UserVector:
    """ユーザーベクトル表現"""
    user_id: str
    preference_vector: List[float]
    reading_pattern: List[float]
    engagement_vector: List[float]
    temporal_pattern: List[float]

@dataclass
class RecommendationResult:
    """推奨結果"""
    content_id: str
    relevance_score: float
    confidence_score: float
    explanation: Dict[str, float]
    predicted_engagement: float

class AIContentRecommender:
    """AI駆動コンテンツ推奨システム"""
    
    def __init__(self, db_path: str = "ai_recommender.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # 次元設定
        self.title_vector_dim = 50
        self.category_vector_dim = 20
        self.preference_vector_dim = 100
        
        # 学習済みモデル（簡易版）
        self.category_embeddings = self._init_category_embeddings()
        self.sentiment_analyzer = self._init_sentiment_analyzer()
        
        self._init_database()
        
    def _init_database(self):
        """データベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS content_vectors (
                    content_id TEXT PRIMARY KEY,
                    title_vector TEXT,
                    category_vector TEXT,
                    sentiment_score REAL,
                    complexity_score REAL,
                    freshness_score REAL,
                    popularity_score REAL,
                    created_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_vectors (
                    user_id TEXT PRIMARY KEY,
                    preference_vector TEXT,
                    reading_pattern TEXT,
                    engagement_vector TEXT,
                    temporal_pattern TEXT,
                    updated_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS recommendation_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    content_id TEXT,
                    recommended_score REAL,
                    actual_engagement REAL,
                    feedback_type TEXT,
                    timestamp TEXT
                )
            ''')
            
    def _init_category_embeddings(self) -> Dict[str, List[float]]:
        """カテゴリ埋め込み初期化（簡易版）"""
        categories = [
            'technology', 'finance', 'politics', 'economy', 'international',
            'sports', 'entertainment', 'health', 'science', 'business',
            'market', 'investment', 'cryptocurrency', 'stocks', 'bonds',
            'real_estate', 'commodities', 'forex', 'banking', 'insurance'
        ]
        
        # ランダムシード固定でベクトル生成
        np.random.seed(42)
        embeddings = {}
        
        for category in categories:
            # カテゴリ名のハッシュをシードとして使用
            seed = int(hashlib.md5(category.encode()).hexdigest()[:8], 16)
            np.random.seed(seed)
            embeddings[category] = np.random.normal(0, 1, self.category_vector_dim).tolist()
            
        return embeddings
        
    def _init_sentiment_analyzer(self) -> Dict[str, float]:
        """感情分析器初期化（簡易版）"""
        # ポジティブ/ネガティブキーワード重み
        return {
            # ポジティブ
            '上昇': 0.8, '成長': 0.7, '利益': 0.6, '好調': 0.7, '改善': 0.6,
            '増加': 0.5, '回復': 0.6, '拡大': 0.5, '前進': 0.5, '成功': 0.8,
            # ネガティブ  
            '下落': -0.8, '減少': -0.6, '悪化': -0.7, '損失': -0.8, '不調': -0.7,
            '縮小': -0.5, '後退': -0.6, '失敗': -0.8, '危機': -0.9, 'リスク': -0.4,
            # 中性
            '維持': 0.0, '横ばい': 0.0, '安定': 0.1, '継続': 0.0, '予想': 0.0
        }
        
    def vectorize_content(self, content: Dict[str, Any]) -> ContentVector:
        """コンテンツのベクトル化"""
        
        # タイトルベクトル（単語の重み付き平均）
        title_vector = self._vectorize_text(content.get('title', ''), self.title_vector_dim)
        
        # カテゴリベクトル
        category_vector = self._vectorize_categories(content.get('categories', []))
        
        # 感情スコア
        sentiment_score = self._analyze_sentiment(content.get('title', '') + ' ' + 
                                                content.get('summary', ''))
        
        # 複雑度スコア（文字数と専門用語密度から）
        complexity_score = self._calculate_complexity(content)
        
        # 新鮮度スコア（公開時間から）
        freshness_score = self._calculate_freshness(content.get('published_at'))
        
        # 人気度スコア（エンゲージメント指標から）
        popularity_score = self._calculate_popularity(content)
        
        return ContentVector(
            content_id=content['id'],
            title_vector=title_vector,
            category_vector=category_vector,
            sentiment_score=sentiment_score,
            complexity_score=complexity_score,
            freshness_score=freshness_score,
            popularity_score=popularity_score
        )
        
    def _vectorize_text(self, text: str, dim: int) -> List[float]:
        """テキストのベクトル化（TF-IDF風の簡易実装）"""
        if not text:
            return [0.0] * dim
            
        # 文字のハッシュベースでベクトル生成
        words = text.split()
        if not words:
            return [0.0] * dim
            
        vectors = []
        for word in words:
            seed = int(hashlib.md5(word.encode()).hexdigest()[:8], 16)
            np.random.seed(seed)
            vectors.append(np.random.normal(0, 1, dim))
            
        # 平均ベクトル
        mean_vector = np.mean(vectors, axis=0)
        return mean_vector.tolist()
        
    def _vectorize_categories(self, categories: List[str]) -> List[float]:
        """カテゴリのベクトル化"""
        if not categories:
            return [0.0] * self.category_vector_dim
            
        vectors = []
        for category in categories:
            if category in self.category_embeddings:
                vectors.append(self.category_embeddings[category])
            else:
                # 未知カテゴリは0ベクトル
                vectors.append([0.0] * self.category_vector_dim)
                
        # 平均ベクトル
        mean_vector = np.mean(vectors, axis=0)
        return mean_vector.tolist()
        
    def _analyze_sentiment(self, text: str) -> float:
        """感情分析"""
        score = 0.0
        word_count = 0
        
        for word, weight in self.sentiment_analyzer.items():
            if word in text:
                score += weight
                word_count += 1
                
        return score / max(word_count, 1) if word_count > 0 else 0.0
        
    def _calculate_complexity(self, content: Dict[str, Any]) -> float:
        """複雑度計算"""
        text = content.get('title', '') + ' ' + content.get('summary', '')
        
        if not text:
            return 0.5  # デフォルト
            
        # 文字数による基本複雑度
        char_complexity = min(1.0, len(text) / 1000.0)
        
        # 専門用語の密度
        technical_terms = ['API', 'AI', 'GDP', 'REIT', 'IPO', 'M&A', 'ESG', 'DX']
        term_density = sum(1 for term in technical_terms if term in text) / len(text.split())
        
        return min(1.0, (char_complexity + term_density) / 2)
        
    def _calculate_freshness(self, published_at: Optional[str]) -> float:
        """新鮮度計算"""
        if not published_at:
            return 0.5
            
        try:
            pub_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            now = datetime.now()
            hours_diff = (now - pub_time).total_seconds() / 3600
            
            # 24時間以内は高スコア、徐々に減衰
            return max(0.0, 1.0 - hours_diff / 168)  # 1週間で0
        except:
            return 0.5
            
    def _calculate_popularity(self, content: Dict[str, Any]) -> float:
        """人気度計算"""
        # エンゲージメント指標の重み付き合計
        views = content.get('views', 0)
        shares = content.get('shares', 0)
        comments = content.get('comments', 0)
        
        # 正規化
        normalized_views = min(1.0, views / 10000.0)
        normalized_shares = min(1.0, shares / 100.0)  
        normalized_comments = min(1.0, comments / 50.0)
        
        return (normalized_views * 0.4 + normalized_shares * 0.4 + normalized_comments * 0.2)
        
    def build_user_vector(self, user_id: str, interaction_history: List[Dict[str, Any]]) -> UserVector:
        """ユーザーベクトル構築"""
        
        # 嗜好ベクトル（過去のコンテンツの加重平均）
        preference_vectors = []
        engagement_scores = []
        reading_times = []
        time_patterns = [0.0] * 24  # 時間別パターン
        
        for interaction in interaction_history:
            content_vector = self._get_content_vector(interaction['content_id'])
            if content_vector:
                # エンゲージメントによる重み付け
                engagement = self._calculate_engagement_score(interaction)
                engagement_scores.append(engagement)
                
                # 嗜好ベクトル更新
                weighted_vector = np.array(content_vector.title_vector + content_vector.category_vector) * engagement
                preference_vectors.append(weighted_vector)
                
                # 読書時間パターン
                if 'timestamp' in interaction:
                    try:
                        timestamp = datetime.fromisoformat(interaction['timestamp'])
                        time_patterns[timestamp.hour] += engagement
                    except:
                        pass
                        
        # ベクトル平均
        if preference_vectors:
            preference_vector = np.mean(preference_vectors, axis=0).tolist()
        else:
            preference_vector = [0.0] * (self.title_vector_dim + self.category_vector_dim)
            
        # 読書パターン（時間正規化）
        reading_pattern = time_patterns
        total_activity = sum(time_patterns)
        if total_activity > 0:
            reading_pattern = [t / total_activity for t in time_patterns]
            
        # エンゲージメントベクトル
        if engagement_scores:
            engagement_vector = [
                np.mean(engagement_scores),
                np.std(engagement_scores),
                max(engagement_scores),
                min(engagement_scores)
            ]
        else:
            engagement_vector = [0.0, 0.0, 0.0, 0.0]
            
        # 時間パターン（曜日、時間帯）
        temporal_pattern = reading_pattern
        
        return UserVector(
            user_id=user_id,
            preference_vector=preference_vector,
            reading_pattern=reading_pattern,
            engagement_vector=engagement_vector,
            temporal_pattern=temporal_pattern
        )
        
    def _get_content_vector(self, content_id: str) -> Optional[ContentVector]:
        """コンテンツベクトル取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT * FROM content_vectors WHERE content_id = ?',
                (content_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return ContentVector(
                    content_id=row[0],
                    title_vector=json.loads(row[1]),
                    category_vector=json.loads(row[2]),
                    sentiment_score=row[3],
                    complexity_score=row[4],
                    freshness_score=row[5],
                    popularity_score=row[6]
                )
        return None
        
    def _calculate_engagement_score(self, interaction: Dict[str, Any]) -> float:
        """インタラクションからエンゲージメントスコア計算"""
        action_type = interaction.get('action_type', 'view')
        session_duration = interaction.get('session_duration', 0)
        
        base_scores = {
            'view': 0.1,
            'click': 0.3,
            'share': 0.8,
            'comment': 0.9,
            'save': 0.7,
            'like': 0.5
        }
        
        base_score = base_scores.get(action_type, 0.1)
        
        # セッション時間ボーナス
        time_bonus = min(0.5, session_duration / 300.0) if session_duration > 30 else 0
        
        return min(1.0, base_score + time_bonus)
        
    def recommend_content(self, user_id: str, available_content: List[Dict[str, Any]], 
                         top_k: int = 10) -> List[RecommendationResult]:
        """コンテンツ推奨"""
        
        # ユーザーベクトル取得
        user_vector = self._get_user_vector(user_id)
        if not user_vector:
            # 新規ユーザーの場合、人気度ベースで推奨
            return self._recommend_for_new_user(available_content, top_k)
            
        recommendations = []
        
        for content in available_content:
            # コンテンツベクトル化
            content_vector = self.vectorize_content(content)
            
            # 関連度計算
            relevance_score = self._calculate_relevance(user_vector, content_vector)
            
            # 信頼度計算
            confidence_score = self._calculate_confidence(user_vector, content_vector)
            
            # エンゲージメント予測
            predicted_engagement = self._predict_engagement(user_vector, content_vector)
            
            # 説明生成
            explanation = self._generate_explanation(user_vector, content_vector, relevance_score)
            
            recommendations.append(RecommendationResult(
                content_id=content['id'],
                relevance_score=relevance_score,
                confidence_score=confidence_score,
                explanation=explanation,
                predicted_engagement=predicted_engagement
            ))
            
        # スコア順ソート
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return recommendations[:top_k]
        
    def _get_user_vector(self, user_id: str) -> Optional[UserVector]:
        """ユーザーベクトル取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT * FROM user_vectors WHERE user_id = ?',
                (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return UserVector(
                    user_id=row[0],
                    preference_vector=json.loads(row[1]),
                    reading_pattern=json.loads(row[2]),
                    engagement_vector=json.loads(row[3]),
                    temporal_pattern=json.loads(row[4])
                )
        return None
        
    def _recommend_for_new_user(self, available_content: List[Dict[str, Any]], 
                               top_k: int) -> List[RecommendationResult]:
        """新規ユーザー向け推奨"""
        recommendations = []
        
        for content in available_content:
            content_vector = self.vectorize_content(content)
            
            # 人気度と新鮮度ベースのスコア
            score = (content_vector.popularity_score * 0.6 + 
                    content_vector.freshness_score * 0.4)
            
            recommendations.append(RecommendationResult(
                content_id=content['id'],
                relevance_score=score,
                confidence_score=0.3,  # 低い信頼度
                explanation={'新規ユーザー向け': 1.0},
                predicted_engagement=0.5
            ))
            
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        return recommendations[:top_k]
        
    def _calculate_relevance(self, user_vector: UserVector, content_vector: ContentVector) -> float:
        """関連度計算"""
        
        # 嗜好ベクトルとの類似度
        user_pref = np.array(user_vector.preference_vector)
        content_combined = np.array(content_vector.title_vector + content_vector.category_vector)
        
        # コサイン類似度
        preference_similarity = self._cosine_similarity(user_pref, content_combined)
        
        # その他の要素
        freshness_bonus = content_vector.freshness_score * 0.2
        popularity_bonus = content_vector.popularity_score * 0.1
        
        # 時間パターンマッチング
        current_hour = datetime.now().hour
        time_match = user_vector.reading_pattern[current_hour] if current_hour < len(user_vector.reading_pattern) else 0
        
        total_score = (preference_similarity * 0.6 + 
                      freshness_bonus + 
                      popularity_bonus +
                      time_match * 0.1)
                      
        return min(1.0, max(0.0, total_score))
        
    def _calculate_confidence(self, user_vector: UserVector, content_vector: ContentVector) -> float:
        """信頼度計算"""
        
        # ユーザーの過去のエンゲージメント安定性
        engagement_std = user_vector.engagement_vector[1] if len(user_vector.engagement_vector) > 1 else 0.5
        stability = 1.0 - min(1.0, engagement_std)
        
        # コンテンツの人気度（他のユーザーの反応）
        content_confidence = content_vector.popularity_score
        
        return (stability * 0.7 + content_confidence * 0.3)
        
    def _predict_engagement(self, user_vector: UserVector, content_vector: ContentVector) -> float:
        """エンゲージメント予測"""
        
        # ユーザーの平均エンゲージメント
        avg_engagement = user_vector.engagement_vector[0] if user_vector.engagement_vector else 0.5
        
        # 類似度による調整
        preference_similarity = self._cosine_similarity(
            np.array(user_vector.preference_vector),
            np.array(content_vector.title_vector + content_vector.category_vector)
        )
        
        # 複雑度とユーザーレベルの適合性
        complexity_match = 1.0 - abs(content_vector.complexity_score - avg_engagement)
        
        predicted = avg_engagement * preference_similarity * complexity_match
        
        return min(1.0, max(0.0, predicted))
        
    def _generate_explanation(self, user_vector: UserVector, content_vector: ContentVector, 
                            relevance_score: float) -> Dict[str, float]:
        """推奨理由の説明生成"""
        explanation = {}
        
        # 嗜好適合度
        pref_sim = self._cosine_similarity(
            np.array(user_vector.preference_vector),
            np.array(content_vector.title_vector + content_vector.category_vector)
        )
        if pref_sim > 0.5:
            explanation['嗜好適合'] = pref_sim
            
        # 新鮮度
        if content_vector.freshness_score > 0.7:
            explanation['最新情報'] = content_vector.freshness_score
            
        # 人気度
        if content_vector.popularity_score > 0.6:
            explanation['人気コンテンツ'] = content_vector.popularity_score
            
        # 時間適合性
        current_hour = datetime.now().hour
        if (current_hour < len(user_vector.reading_pattern) and 
            user_vector.reading_pattern[current_hour] > 0.1):
            explanation['時間帯適合'] = user_vector.reading_pattern[current_hour]
            
        return explanation
        
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """コサイン類似度計算"""
        if len(vec1) != len(vec2):
            return 0.0
            
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
        
    def save_content_vector(self, content_vector: ContentVector):
        """コンテンツベクトル保存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO content_vectors 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_vector.content_id,
                json.dumps(content_vector.title_vector),
                json.dumps(content_vector.category_vector),
                content_vector.sentiment_score,
                content_vector.complexity_score,
                content_vector.freshness_score,
                content_vector.popularity_score,
                datetime.now().isoformat()
            ))
            
    def save_user_vector(self, user_vector: UserVector):
        """ユーザーベクトル保存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO user_vectors 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_vector.user_id,
                json.dumps(user_vector.preference_vector),
                json.dumps(user_vector.reading_pattern),
                json.dumps(user_vector.engagement_vector),
                json.dumps(user_vector.temporal_pattern),
                datetime.now().isoformat()
            ))
            
    def record_recommendation_feedback(self, user_id: str, content_id: str,
                                     recommended_score: float, actual_engagement: float,
                                     feedback_type: str = 'implicit'):
        """推奨フィードバック記録"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO recommendation_feedback 
                (user_id, content_id, recommended_score, actual_engagement, feedback_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, content_id, recommended_score, actual_engagement, 
                  feedback_type, datetime.now().isoformat()))

if __name__ == "__main__":
    # テスト実行
    recommender = AIContentRecommender()
    
    # テストコンテンツ
    test_content = {
        'id': 'test_article_001',
        'title': '最新のAI技術動向と市場への影響',
        'summary': '人工知能の急速な発展が金融市場に与える影響を分析',
        'categories': ['technology', 'finance', 'ai'],
        'published_at': datetime.now().isoformat(),
        'views': 1500,
        'shares': 25,
        'comments': 8
    }
    
    # コンテンツベクトル化
    content_vector = recommender.vectorize_content(test_content)
    recommender.save_content_vector(content_vector)
    
    # テストユーザー履歴
    interaction_history = [
        {
            'content_id': 'test_article_001',
            'action_type': 'view',
            'session_duration': 180,
            'timestamp': datetime.now().isoformat()
        }
    ]
    
    # ユーザーベクトル構築
    user_vector = recommender.build_user_vector('test_user_001', interaction_history)
    recommender.save_user_vector(user_vector)
    
    # 推奨実行
    recommendations = recommender.recommend_content('test_user_001', [test_content])
    
    for rec in recommendations:
        print(f"Content: {rec.content_id}")
        print(f"Relevance: {rec.relevance_score:.3f}")
        print(f"Confidence: {rec.confidence_score:.3f}")
        print(f"Explanation: {rec.explanation}")
        print("---")