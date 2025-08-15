"""
動的ユーザーセグメンテーション
リアルタイムの行動分析に基づくユーザーグループの自動分類・更新システム
"""

import json
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from collections import defaultdict, Counter
from enum import Enum
import math

class EngagementLevel(Enum):
    """エンゲージメントレベル"""
    HIGH = "high"
    MEDIUM = "medium"  
    LOW = "low"
    INACTIVE = "inactive"

class ContentPreference(Enum):
    """コンテンツ嗜好タイプ"""
    TECH_FOCUSED = "tech_focused"
    FINANCE_FOCUSED = "finance_focused"
    GENERAL_NEWS = "general_news"
    DEEP_ANALYSIS = "deep_analysis"
    QUICK_UPDATES = "quick_updates"

class ReadingBehavior(Enum):
    """読書行動パターン"""
    MORNING_READER = "morning_reader"
    LUNCH_READER = "lunch_reader" 
    EVENING_READER = "evening_reader"
    NIGHT_READER = "night_reader"
    WEEKEND_READER = "weekend_reader"

@dataclass
class UserSegment:
    """ユーザーセグメント定義"""
    segment_id: str
    segment_name: str
    description: str
    engagement_level: EngagementLevel
    content_preference: ContentPreference
    reading_behavior: ReadingBehavior
    characteristics: Dict[str, Any]
    user_count: int = 0
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class UserSegmentMembership:
    """ユーザーのセグメント所属情報"""
    user_id: str
    segment_id: str
    membership_score: float
    confidence_level: float
    assigned_at: datetime
    last_updated: datetime
    migration_history: List[str]

@dataclass
class SegmentationMetrics:
    """セグメンテーション指標"""
    total_users: int
    total_segments: int
    average_segment_size: float
    segment_stability_score: float
    coverage_ratio: float
    quality_score: float

class DynamicUserSegmentation:
    """動的ユーザーセグメンテーション管理システム"""
    
    def __init__(self, db_path: str = "user_segmentation.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # セグメンテーション設定
        self.min_segment_size = 10
        self.max_segments = 20
        self.recalculation_interval_hours = 24
        self.migration_threshold = 0.3
        
        # 特徴量の重み
        self.feature_weights = {
            'engagement_frequency': 0.25,
            'session_duration': 0.20,
            'content_diversity': 0.15,
            'reading_time_pattern': 0.15,
            'sharing_behavior': 0.10,
            'feedback_quality': 0.10,
            'device_usage': 0.05
        }
        
        self._init_database()
        self._init_default_segments()
        
    def _init_database(self):
        """データベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_segments (
                    segment_id TEXT PRIMARY KEY,
                    segment_name TEXT,
                    description TEXT,
                    engagement_level TEXT,
                    content_preference TEXT,
                    reading_behavior TEXT,
                    characteristics TEXT,
                    user_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS segment_memberships (
                    user_id TEXT,
                    segment_id TEXT,
                    membership_score REAL,
                    confidence_level REAL,
                    assigned_at TEXT,
                    last_updated TEXT,
                    migration_history TEXT,
                    PRIMARY KEY (user_id, segment_id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS segment_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    segment_id TEXT,
                    analytics_date TEXT,
                    user_count INTEGER,
                    engagement_metrics TEXT,
                    performance_metrics TEXT,
                    FOREIGN KEY (segment_id) REFERENCES user_segments (segment_id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS segmentation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    old_segment_id TEXT,
                    new_segment_id TEXT,
                    migration_reason TEXT,
                    migration_score REAL,
                    timestamp TEXT
                )
            ''')
            
    def _init_default_segments(self):
        """デフォルトセグメント初期化"""
        default_segments = [
            UserSegment(
                segment_id="power_users",
                segment_name="パワーユーザー",
                description="高頻度・高エンゲージメントのアクティブユーザー",
                engagement_level=EngagementLevel.HIGH,
                content_preference=ContentPreference.DEEP_ANALYSIS,
                reading_behavior=ReadingBehavior.MORNING_READER,
                characteristics={
                    'daily_sessions': '>5',
                    'avg_session_duration': '>300',
                    'sharing_frequency': 'high',
                    'content_depth': 'detailed'
                }
            ),
            UserSegment(
                segment_id="casual_readers",
                segment_name="カジュアル読者",
                description="定期的だが軽量な利用パターンのユーザー",
                engagement_level=EngagementLevel.MEDIUM,
                content_preference=ContentPreference.QUICK_UPDATES,
                reading_behavior=ReadingBehavior.LUNCH_READER,
                characteristics={
                    'daily_sessions': '2-4',
                    'avg_session_duration': '120-300',
                    'sharing_frequency': 'medium',
                    'content_depth': 'summary'
                }
            ),
            UserSegment(
                segment_id="tech_enthusiasts",
                segment_name="テクノロジー愛好家",
                description="技術系コンテンツを重点的に消費するユーザー",
                engagement_level=EngagementLevel.HIGH,
                content_preference=ContentPreference.TECH_FOCUSED,
                reading_behavior=ReadingBehavior.EVENING_READER,
                characteristics={
                    'tech_content_ratio': '>60%',
                    'technical_depth': 'high',
                    'new_tech_interest': 'strong'
                }
            ),
            UserSegment(
                segment_id="finance_professionals",
                segment_name="金融プロフェッショナル",
                description="金融・経済情報に特化した専門ユーザー",
                engagement_level=EngagementLevel.HIGH,
                content_preference=ContentPreference.FINANCE_FOCUSED,
                reading_behavior=ReadingBehavior.MORNING_READER,
                characteristics={
                    'finance_content_ratio': '>70%',
                    'market_timing_sensitivity': 'high',
                    'professional_indicators': 'present'
                }
            ),
            UserSegment(
                segment_id="weekend_browsers",
                segment_name="週末ブラウザー",
                description="主に週末に集中的に利用するユーザー",
                engagement_level=EngagementLevel.MEDIUM,
                content_preference=ContentPreference.GENERAL_NEWS,
                reading_behavior=ReadingBehavior.WEEKEND_READER,
                characteristics={
                    'weekend_activity_ratio': '>60%',
                    'batch_consumption': 'high',
                    'leisure_reading': 'primary'
                }
            ),
            UserSegment(
                segment_id="inactive_users",
                segment_name="非アクティブユーザー",
                description="低エンゲージメント・休眠傾向のユーザー",
                engagement_level=EngagementLevel.INACTIVE,
                content_preference=ContentPreference.GENERAL_NEWS,
                reading_behavior=ReadingBehavior.MORNING_READER,
                characteristics={
                    'last_activity': '>7_days',
                    'engagement_trend': 'declining',
                    'reactivation_potential': 'variable'
                }
            )
        ]
        
        for segment in default_segments:
            self._save_segment(segment)
            
    def _save_segment(self, segment: UserSegment):
        """セグメント保存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO user_segments 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                segment.segment_id,
                segment.segment_name,
                segment.description,
                segment.engagement_level.value,
                segment.content_preference.value,
                segment.reading_behavior.value,
                json.dumps(segment.characteristics),
                segment.user_count,
                segment.created_at.isoformat() if segment.created_at else datetime.now().isoformat(),
                segment.updated_at.isoformat() if segment.updated_at else datetime.now().isoformat()
            ))
            
    def analyze_user_behavior(self, user_id: str, interaction_history: List[Dict[str, Any]], 
                            time_window_days: int = 30) -> Dict[str, float]:
        """ユーザー行動分析"""
        
        if not interaction_history:
            return self._default_behavior_features()
            
        # 時間窓内のデータフィルタリング
        cutoff_date = datetime.now() - timedelta(days=time_window_days)
        recent_interactions = [
            interaction for interaction in interaction_history
            if datetime.fromisoformat(interaction.get('timestamp', '2020-01-01')) >= cutoff_date
        ]
        
        if not recent_interactions:
            return self._default_behavior_features()
        
        features = {}
        
        # エンゲージメント頻度
        features['engagement_frequency'] = len(recent_interactions) / time_window_days
        
        # セッション継続時間
        session_durations = [
            interaction.get('session_duration', 0) 
            for interaction in recent_interactions
        ]
        features['session_duration'] = np.mean(session_durations) if session_durations else 0
        
        # コンテンツ多様性
        content_categories = []
        for interaction in recent_interactions:
            categories = interaction.get('categories', [])
            content_categories.extend(categories)
        
        unique_categories = len(set(content_categories))
        total_categories = len(content_categories) if content_categories else 1
        features['content_diversity'] = unique_categories / total_categories
        
        # 読書時間パターン
        reading_hours = []
        for interaction in recent_interactions:
            try:
                timestamp = datetime.fromisoformat(interaction['timestamp'])
                reading_hours.append(timestamp.hour)
            except:
                continue
                
        if reading_hours:
            hour_distribution = Counter(reading_hours)
            most_common_hour = hour_distribution.most_common(1)[0][0]
            features['reading_time_pattern'] = self._categorize_reading_time(most_common_hour)
        else:
            features['reading_time_pattern'] = 0.5
            
        # シェア行動
        sharing_actions = [
            interaction for interaction in recent_interactions
            if interaction.get('action_type') in ['share', 'comment']
        ]
        features['sharing_behavior'] = len(sharing_actions) / max(len(recent_interactions), 1)
        
        # フィードバック品質
        feedback_actions = [
            interaction for interaction in recent_interactions
            if interaction.get('action_type') in ['like', 'save', 'comment']
        ]
        features['feedback_quality'] = len(feedback_actions) / max(len(recent_interactions), 1)
        
        # デバイス利用パターン
        device_types = [interaction.get('device_type', 'unknown') for interaction in recent_interactions]
        mobile_ratio = device_types.count('mobile') / len(device_types) if device_types else 0.5
        features['device_usage'] = mobile_ratio
        
        return features
        
    def _default_behavior_features(self) -> Dict[str, float]:
        """デフォルト行動特徴量"""
        return {
            'engagement_frequency': 0.5,
            'session_duration': 0.5,
            'content_diversity': 0.5,
            'reading_time_pattern': 0.5,
            'sharing_behavior': 0.1,
            'feedback_quality': 0.1,
            'device_usage': 0.7  # モバイルがデフォルト
        }
        
    def _categorize_reading_time(self, hour: int) -> float:
        """読書時間の分類"""
        if 6 <= hour <= 11:
            return 1.0  # 朝
        elif 12 <= hour <= 17:
            return 0.75  # 昼
        elif 18 <= hour <= 21:
            return 0.5  # 夕方
        else:
            return 0.25  # 夜・深夜
            
    def calculate_segment_scores(self, user_features: Dict[str, float]) -> Dict[str, float]:
        """各セグメントへの適合スコア計算"""
        
        segments = self._get_all_segments()
        segment_scores = {}
        
        for segment in segments:
            score = self._calculate_segment_match_score(user_features, segment)
            segment_scores[segment.segment_id] = score
            
        return segment_scores
        
    def _get_all_segments(self) -> List[UserSegment]:
        """全セグメント取得"""
        segments = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM user_segments')
            rows = cursor.fetchall()
            
            for row in rows:
                segments.append(UserSegment(
                    segment_id=row[0],
                    segment_name=row[1],
                    description=row[2],
                    engagement_level=EngagementLevel(row[3]),
                    content_preference=ContentPreference(row[4]),
                    reading_behavior=ReadingBehavior(row[5]),
                    characteristics=json.loads(row[6]),
                    user_count=row[7],
                    created_at=datetime.fromisoformat(row[8]),
                    updated_at=datetime.fromisoformat(row[9])
                ))
                
        return segments
        
    def _calculate_segment_match_score(self, user_features: Dict[str, float], 
                                     segment: UserSegment) -> float:
        """セグメント適合度スコア計算"""
        
        score = 0.0
        
        # セグメント特性に基づくスコア計算
        if segment.engagement_level == EngagementLevel.HIGH:
            score += user_features.get('engagement_frequency', 0) * 0.3
            score += min(1.0, user_features.get('session_duration', 0) / 300.0) * 0.2
            
        elif segment.engagement_level == EngagementLevel.MEDIUM:
            # 中程度のエンゲージメント
            freq_score = 1.0 - abs(user_features.get('engagement_frequency', 0) - 0.5)
            score += freq_score * 0.3
            
        elif segment.engagement_level == EngagementLevel.LOW:
            score += (1.0 - user_features.get('engagement_frequency', 0)) * 0.3
            
        elif segment.engagement_level == EngagementLevel.INACTIVE:
            score += (1.0 - user_features.get('engagement_frequency', 0)) * 0.5
            
        # コンテンツ嗜好による調整
        if segment.content_preference == ContentPreference.TECH_FOCUSED:
            # 技術カテゴリの多様性が低い（特化している）場合にスコア高
            diversity = user_features.get('content_diversity', 0.5)
            if diversity < 0.3:  # 特化傾向
                score += 0.3
                
        elif segment.content_preference == ContentPreference.GENERAL_NEWS:
            # 多様性が高い場合にスコア高
            score += user_features.get('content_diversity', 0.5) * 0.2
            
        # 読書行動パターン
        time_pattern_score = user_features.get('reading_time_pattern', 0.5)
        
        if segment.reading_behavior == ReadingBehavior.MORNING_READER:
            score += time_pattern_score * 0.2
        elif segment.reading_behavior == ReadingBehavior.LUNCH_READER:
            score += (1.0 - abs(time_pattern_score - 0.75)) * 0.2
        elif segment.reading_behavior == ReadingBehavior.EVENING_READER:
            score += (1.0 - abs(time_pattern_score - 0.5)) * 0.2
        elif segment.reading_behavior == ReadingBehavior.NIGHT_READER:
            score += (1.0 - abs(time_pattern_score - 0.25)) * 0.2
            
        # デバイス利用パターン
        if segment.characteristics.get('mobile_preferred') == 'true':
            score += user_features.get('device_usage', 0.5) * 0.1
            
        return min(1.0, max(0.0, score))
        
    def assign_user_to_segments(self, user_id: str, segment_scores: Dict[str, float]) -> str:
        """ユーザーのセグメント割り当て"""
        
        if not segment_scores:
            return "casual_readers"  # デフォルトセグメント
            
        # 最高スコアのセグメント選択
        best_segment_id = max(segment_scores, key=segment_scores.get)
        best_score = segment_scores[best_segment_id]
        confidence = self._calculate_assignment_confidence(segment_scores)
        
        # 既存の割り当て確認
        current_membership = self._get_current_membership(user_id)
        
        # セグメント移行の判定
        should_migrate = (
            current_membership is None or
            current_membership.segment_id != best_segment_id and
            best_score - segment_scores.get(current_membership.segment_id, 0) > self.migration_threshold
        )
        
        if should_migrate:
            self._update_segment_membership(
                user_id, best_segment_id, best_score, confidence, current_membership
            )
            
            if current_membership:
                self._record_segment_migration(
                    user_id, current_membership.segment_id, best_segment_id, best_score
                )
                
            return best_segment_id
            
        return current_membership.segment_id if current_membership else best_segment_id
        
    def _get_current_membership(self, user_id: str) -> Optional[UserSegmentMembership]:
        """現在のセグメント所属取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT user_id, segment_id, membership_score, confidence_level, 
                       assigned_at, last_updated, migration_history
                FROM segment_memberships 
                WHERE user_id = ?
                ORDER BY last_updated DESC LIMIT 1
            ''', (user_id,))
            
            row = cursor.fetchone()
            if row:
                return UserSegmentMembership(
                    user_id=row[0],
                    segment_id=row[1],
                    membership_score=row[2],
                    confidence_level=row[3],
                    assigned_at=datetime.fromisoformat(row[4]),
                    last_updated=datetime.fromisoformat(row[5]),
                    migration_history=json.loads(row[6])
                )
        return None
        
    def _calculate_assignment_confidence(self, segment_scores: Dict[str, float]) -> float:
        """割り当て信頼度計算"""
        if len(segment_scores) < 2:
            return 0.5
            
        scores = sorted(segment_scores.values(), reverse=True)
        top_score = scores[0]
        second_score = scores[1]
        
        # トップとセカンドの差が大きいほど信頼度高
        confidence = min(1.0, (top_score - second_score) / 0.5)
        
        return confidence
        
    def _update_segment_membership(self, user_id: str, segment_id: str, score: float,
                                 confidence: float, previous_membership: Optional[UserSegmentMembership]):
        """セグメント所属情報更新"""
        
        migration_history = []
        if previous_membership:
            migration_history = previous_membership.migration_history.copy()
            migration_history.append(f"{previous_membership.segment_id}→{segment_id}")
            
        # 履歴は最大10件まで
        if len(migration_history) > 10:
            migration_history = migration_history[-10:]
            
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO segment_memberships 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, segment_id, score, confidence,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                json.dumps(migration_history)
            ))
            
    def _record_segment_migration(self, user_id: str, old_segment_id: str, 
                                new_segment_id: str, migration_score: float):
        """セグメント移行記録"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO segmentation_history 
                (user_id, old_segment_id, new_segment_id, migration_reason, migration_score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id, old_segment_id, new_segment_id,
                "behavior_change_detected", migration_score,
                datetime.now().isoformat()
            ))
            
        self.logger.info(f"User {user_id} migrated from {old_segment_id} to {new_segment_id}")
        
    def segment_user(self, user_id: str, interaction_history: List[Dict[str, Any]]) -> str:
        """ユーザーセグメンテーション実行"""
        
        # 行動分析
        user_features = self.analyze_user_behavior(user_id, interaction_history)
        
        # セグメントスコア計算
        segment_scores = self.calculate_segment_scores(user_features)
        
        # セグメント割り当て
        assigned_segment = self.assign_user_to_segments(user_id, segment_scores)
        
        self.logger.info(f"User {user_id} assigned to segment: {assigned_segment}")
        
        return assigned_segment
        
    def get_segment_users(self, segment_id: str) -> List[str]:
        """セグメント内ユーザー一覧取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT user_id FROM segment_memberships 
                WHERE segment_id = ?
                ORDER BY membership_score DESC
            ''', (segment_id,))
            
            return [row[0] for row in cursor.fetchall()]
            
    def get_user_segment_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザーセグメント情報取得"""
        membership = self._get_current_membership(user_id)
        if not membership:
            return None
            
        segment = self._get_segment_by_id(membership.segment_id)
        
        return {
            'segment': asdict(segment) if segment else None,
            'membership': asdict(membership),
            'assignment_date': membership.assigned_at.isoformat(),
            'confidence': membership.confidence_level
        }
        
    def _get_segment_by_id(self, segment_id: str) -> Optional[UserSegment]:
        """ID指定でセグメント取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT * FROM user_segments WHERE segment_id = ?',
                (segment_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return UserSegment(
                    segment_id=row[0],
                    segment_name=row[1],
                    description=row[2],
                    engagement_level=EngagementLevel(row[3]),
                    content_preference=ContentPreference(row[4]),
                    reading_behavior=ReadingBehavior(row[5]),
                    characteristics=json.loads(row[6]),
                    user_count=row[7],
                    created_at=datetime.fromisoformat(row[8]),
                    updated_at=datetime.fromisoformat(row[9])
                )
        return None
        
    def calculate_segmentation_metrics(self) -> SegmentationMetrics:
        """セグメンテーション品質指標計算"""
        
        with sqlite3.connect(self.db_path) as conn:
            # 総ユーザー数
            total_users = conn.execute('SELECT COUNT(DISTINCT user_id) FROM segment_memberships').fetchone()[0]
            
            # 総セグメント数（アクティブ）
            total_segments = conn.execute('SELECT COUNT(*) FROM user_segments WHERE user_count > 0').fetchone()[0]
            
            # セグメント別ユーザー数
            cursor = conn.execute('''
                SELECT segment_id, COUNT(*) as user_count
                FROM segment_memberships 
                GROUP BY segment_id
            ''')
            segment_sizes = [row[1] for row in cursor.fetchall()]
            
        # 平均セグメントサイズ
        avg_segment_size = np.mean(segment_sizes) if segment_sizes else 0
        
        # セグメント安定性スコア（移行頻度の逆数）
        with sqlite3.connect(self.db_path) as conn:
            migration_count = conn.execute(
                'SELECT COUNT(*) FROM segmentation_history WHERE timestamp >= ?',
                ((datetime.now() - timedelta(days=30)).isoformat(),)
            ).fetchone()[0]
            
        stability_score = max(0.0, 1.0 - (migration_count / max(total_users, 1)))
        
        # カバレッジ率
        coverage_ratio = total_users / max(total_users, 1) if total_users > 0 else 0
        
        # 品質スコア（バランス・安定性・カバレッジの総合）
        size_balance = 1.0 - np.std(segment_sizes) / max(avg_segment_size, 1) if segment_sizes else 0
        quality_score = (size_balance + stability_score + coverage_ratio) / 3
        
        return SegmentationMetrics(
            total_users=total_users,
            total_segments=total_segments,
            average_segment_size=avg_segment_size,
            segment_stability_score=stability_score,
            coverage_ratio=coverage_ratio,
            quality_score=quality_score
        )

if __name__ == "__main__":
    # テスト実行
    segmentation = DynamicUserSegmentation()
    
    # テストユーザーのインタラクション履歴
    test_interactions = [
        {
            'timestamp': datetime.now().isoformat(),
            'action_type': 'view',
            'session_duration': 240,
            'categories': ['technology', 'ai'],
            'device_type': 'mobile'
        },
        {
            'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
            'action_type': 'share',
            'session_duration': 180,
            'categories': ['technology'],
            'device_type': 'mobile'
        }
    ]
    
    # ユーザーセグメンテーション実行
    segment = segmentation.segment_user('test_user_001', test_interactions)
    print(f"Assigned segment: {segment}")
    
    # セグメント情報取得
    segment_info = segmentation.get_user_segment_info('test_user_001')
    print(json.dumps(segment_info, indent=2, ensure_ascii=False, default=str))
    
    # 全体指標
    metrics = segmentation.calculate_segmentation_metrics()
    print(json.dumps(asdict(metrics), indent=2, ensure_ascii=False))