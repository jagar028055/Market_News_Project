"""
ユーザー別配信最適化システム
個別ユーザーの行動履歴に基づいて配信内容と頻度を最適化
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3

@dataclass
class UserProfile:
    """ユーザープロファイル"""
    user_id: str
    interests: List[str]  # 関心分野
    reading_time_preference: str  # morning, afternoon, evening, night
    frequency_preference: int  # 1日あたりの配信希望数
    engagement_score: float  # エンゲージメントスコア
    device_type: str  # mobile, desktop, tablet
    language: str  # ja, en
    created_at: datetime
    updated_at: datetime

@dataclass
class ContentRecommendation:
    """コンテンツ推奨"""
    content_id: str
    score: float
    reason: str
    categories: List[str]
    estimated_read_time: int

class UserOptimizer:
    """ユーザー別配信最適化エンジン"""
    
    def __init__(self, db_path: str = "user_profiles.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
        
    def _init_database(self):
        """データベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    interests TEXT,
                    reading_time_preference TEXT,
                    frequency_preference INTEGER,
                    engagement_score REAL,
                    device_type TEXT,
                    language TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    content_id TEXT,
                    action_type TEXT,
                    timestamp TEXT,
                    session_duration INTEGER,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            ''')
            
    def create_user_profile(self, user_id: str, initial_preferences: Dict[str, Any]) -> UserProfile:
        """新規ユーザープロファイル作成"""
        profile = UserProfile(
            user_id=user_id,
            interests=initial_preferences.get('interests', []),
            reading_time_preference=initial_preferences.get('reading_time', 'morning'),
            frequency_preference=initial_preferences.get('frequency', 3),
            engagement_score=0.5,  # 初期値
            device_type=initial_preferences.get('device_type', 'mobile'),
            language=initial_preferences.get('language', 'ja'),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self._save_user_profile(profile)
        self.logger.info(f"Created user profile for {user_id}")
        return profile
        
    def _save_user_profile(self, profile: UserProfile):
        """ユーザープロファイル保存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO user_profiles 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                profile.user_id,
                json.dumps(profile.interests),
                profile.reading_time_preference,
                profile.frequency_preference,
                profile.engagement_score,
                profile.device_type,
                profile.language,
                profile.created_at.isoformat(),
                profile.updated_at.isoformat()
            ))
            
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """ユーザープロファイル取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT * FROM user_profiles WHERE user_id = ?',
                (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return UserProfile(
                    user_id=row[0],
                    interests=json.loads(row[1]),
                    reading_time_preference=row[2],
                    frequency_preference=row[3],
                    engagement_score=row[4],
                    device_type=row[5],
                    language=row[6],
                    created_at=datetime.fromisoformat(row[7]),
                    updated_at=datetime.fromisoformat(row[8])
                )
        return None
        
    def record_user_interaction(self, user_id: str, content_id: str, 
                              action_type: str, session_duration: int = 0):
        """ユーザー行動記録"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO user_interactions 
                (user_id, content_id, action_type, timestamp, session_duration)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, content_id, action_type, datetime.now().isoformat(), session_duration))
            
        # エンゲージメントスコア更新
        self._update_engagement_score(user_id, action_type, session_duration)
        
    def _update_engagement_score(self, user_id: str, action_type: str, session_duration: int):
        """エンゲージメントスコア更新"""
        profile = self.get_user_profile(user_id)
        if not profile:
            return
            
        # アクション種別による重み
        action_weights = {
            'view': 0.1,
            'click': 0.3,
            'share': 0.5,
            'save': 0.4,
            'comment': 0.6
        }
        
        # セッション時間による追加スコア (30秒以上で効果的)
        time_bonus = min(session_duration / 300.0, 0.3) if session_duration > 30 else 0
        
        score_delta = action_weights.get(action_type, 0.1) + time_bonus
        
        # スコアを0-1の範囲で調整
        new_score = min(1.0, max(0.0, profile.engagement_score + score_delta * 0.1))
        
        profile.engagement_score = new_score
        profile.updated_at = datetime.now()
        self._save_user_profile(profile)
        
    def get_optimal_delivery_time(self, user_id: str) -> str:
        """最適配信時間取得"""
        profile = self.get_user_profile(user_id)
        if not profile:
            return "09:00"  # デフォルト
            
        time_mapping = {
            'morning': "08:00",
            'afternoon': "12:00", 
            'evening': "18:00",
            'night': "20:00"
        }
        
        return time_mapping.get(profile.reading_time_preference, "09:00")
        
    def get_personalized_content_count(self, user_id: str) -> int:
        """パーソナライズされたコンテンツ数取得"""
        profile = self.get_user_profile(user_id)
        if not profile:
            return 5  # デフォルト
            
        # エンゲージメントスコアに基づく調整
        base_count = profile.frequency_preference
        engagement_multiplier = 0.5 + profile.engagement_score
        
        return max(1, min(10, int(base_count * engagement_multiplier)))
        
    def optimize_content_for_user(self, user_id: str, 
                                available_content: List[Dict[str, Any]]) -> List[ContentRecommendation]:
        """ユーザー向けコンテンツ最適化"""
        profile = self.get_user_profile(user_id)
        if not profile:
            # デフォルトレコメンデーション
            return [
                ContentRecommendation(
                    content_id=content['id'],
                    score=0.5,
                    reason="デフォルト推奨",
                    categories=content.get('categories', []),
                    estimated_read_time=content.get('read_time', 300)
                )
                for content in available_content[:5]
            ]
            
        recommendations = []
        
        for content in available_content:
            score = self._calculate_content_score(profile, content)
            
            if score > 0.3:  # 閾値以上のコンテンツのみ
                recommendations.append(ContentRecommendation(
                    content_id=content['id'],
                    score=score,
                    reason=self._generate_recommendation_reason(profile, content),
                    categories=content.get('categories', []),
                    estimated_read_time=content.get('read_time', 300)
                ))
                
        # スコア順でソート
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        # ユーザーの希望数まで
        target_count = self.get_personalized_content_count(user_id)
        return recommendations[:target_count]
        
    def _calculate_content_score(self, profile: UserProfile, content: Dict[str, Any]) -> float:
        """コンテンツスコア計算"""
        score = 0.0
        
        # 興味分野との一致度
        content_categories = content.get('categories', [])
        interest_match = len(set(profile.interests) & set(content_categories))
        score += interest_match * 0.3
        
        # エンゲージメントスコアによる重み付け
        score *= (0.5 + profile.engagement_score)
        
        # デバイスタイプによる調整
        if profile.device_type == 'mobile':
            # モバイルユーザーは短い記事を好む傾向
            read_time = content.get('read_time', 300)
            if read_time < 180:
                score *= 1.2
            elif read_time > 600:
                score *= 0.8
                
        # 時間帯による調整
        current_hour = datetime.now().hour
        if profile.reading_time_preference == 'morning' and 6 <= current_hour <= 11:
            score *= 1.1
        elif profile.reading_time_preference == 'afternoon' and 12 <= current_hour <= 17:
            score *= 1.1
        elif profile.reading_time_preference == 'evening' and 18 <= current_hour <= 21:
            score *= 1.1
        elif profile.reading_time_preference == 'night' and (current_hour >= 22 or current_hour <= 5):
            score *= 1.1
            
        return min(1.0, score)
        
    def _generate_recommendation_reason(self, profile: UserProfile, content: Dict[str, Any]) -> str:
        """推奨理由生成"""
        reasons = []
        
        content_categories = content.get('categories', [])
        matching_interests = set(profile.interests) & set(content_categories)
        
        if matching_interests:
            reasons.append(f"関心分野「{', '.join(matching_interests)}」に関連")
            
        if profile.engagement_score > 0.7:
            reasons.append("高エンゲージメントユーザー向け")
        elif profile.engagement_score < 0.3:
            reasons.append("入門者向けコンテンツ")
            
        if profile.device_type == 'mobile':
            read_time = content.get('read_time', 300)
            if read_time < 180:
                reasons.append("モバイル最適化")
                
        return " | ".join(reasons) if reasons else "一般推奨"
        
    def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """ユーザー分析データ取得"""
        profile = self.get_user_profile(user_id)
        if not profile:
            return {}
            
        since_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            # 行動サマリー
            cursor = conn.execute('''
                SELECT action_type, COUNT(*), AVG(session_duration)
                FROM user_interactions 
                WHERE user_id = ? AND timestamp >= ?
                GROUP BY action_type
            ''', (user_id, since_date.isoformat()))
            
            actions = {}
            for row in cursor.fetchall():
                actions[row[0]] = {
                    'count': row[1],
                    'avg_duration': row[2]
                }
                
        return {
            'profile': asdict(profile),
            'period_days': days,
            'actions': actions,
            'total_interactions': sum(a['count'] for a in actions.values())
        }

if __name__ == "__main__":
    # テスト実行
    optimizer = UserOptimizer()
    
    # テストユーザー作成
    test_user = optimizer.create_user_profile("test_user_001", {
        'interests': ['technology', 'finance'],
        'reading_time': 'morning',
        'frequency': 4,
        'device_type': 'mobile',
        'language': 'ja'
    })
    
    # テスト行動記録
    optimizer.record_user_interaction("test_user_001", "article_123", "view", 180)
    optimizer.record_user_interaction("test_user_001", "article_123", "share", 0)
    
    # 分析データ取得
    analytics = optimizer.get_user_analytics("test_user_001")
    print(json.dumps(analytics, indent=2, ensure_ascii=False, default=str))