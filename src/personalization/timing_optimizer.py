"""
インテリジェント配信タイミング最適化システム
機械学習とユーザー行動分析を活用した最適配信時間の決定
"""

import json
import logging
import numpy as np
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from collections import defaultdict, Counter
from enum import Enum
import math

class DeliveryChannel(Enum):
    """配信チャネル"""
    EMAIL = "email"
    PUSH = "push"
    LINE = "line"
    RSS = "rss"
    WEB = "web"

class TimingStrategy(Enum):
    """タイミング戦略"""
    OPTIMAL_ENGAGEMENT = "optimal_engagement"
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    ADAPTIVE = "adaptive"
    BATCH = "batch"

@dataclass
class DeliveryWindow:
    """配信時間窓"""
    channel: DeliveryChannel
    user_id: str
    start_time: time
    end_time: time
    probability_score: float
    engagement_prediction: float
    timezone: str = "Asia/Tokyo"

@dataclass
class OptimalTiming:
    """最適配信タイミング"""
    user_id: str
    content_type: str
    recommended_time: datetime
    confidence_score: float
    strategy: TimingStrategy
    delivery_windows: List[DeliveryWindow]
    fallback_times: List[datetime]
    reasoning: Dict[str, Any]

@dataclass
class TimingMetrics:
    """タイミング指標"""
    user_id: str
    time_slot: str  # "HH:MM"
    day_of_week: int
    engagement_rate: float
    response_rate: float
    avg_response_time_minutes: int
    sample_size: int
    last_updated: datetime

@dataclass
class DeliveryPerformance:
    """配信パフォーマンス"""
    delivery_id: str
    user_id: str
    scheduled_time: datetime
    actual_delivery_time: datetime
    opened_time: Optional[datetime]
    engagement_time: Optional[datetime]
    engagement_score: float
    channel: DeliveryChannel

class IntelligentTimingOptimizer:
    """インテリジェント配信タイミング最適化システム"""
    
    def __init__(self, db_path: str = "timing_optimizer.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # 最適化設定
        self.min_confidence_threshold = 0.6
        self.learning_window_days = 60
        self.min_samples_for_personalization = 10
        
        # チャネル別重み
        self.channel_weights = {
            DeliveryChannel.PUSH: 0.3,
            DeliveryChannel.EMAIL: 0.25,
            DeliveryChannel.LINE: 0.25,
            DeliveryChannel.RSS: 0.1,
            DeliveryChannel.WEB: 0.1
        }
        
        # 時間帯カテゴリ
        self.time_categories = {
            'early_morning': (5, 8),    # 早朝
            'morning': (8, 11),         # 朝
            'late_morning': (11, 13),   # 午前遅め
            'afternoon': (13, 17),      # 午後
            'evening': (17, 20),        # 夕方
            'night': (20, 23),          # 夜
            'late_night': (23, 5)       # 深夜
        }
        
        self._init_database()
        
    def _init_database(self):
        """データベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS timing_metrics (
                    user_id TEXT,
                    time_slot TEXT,
                    day_of_week INTEGER,
                    engagement_rate REAL,
                    response_rate REAL,
                    avg_response_time_minutes INTEGER,
                    sample_size INTEGER,
                    last_updated TEXT,
                    PRIMARY KEY (user_id, time_slot, day_of_week)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS delivery_performance (
                    delivery_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    scheduled_time TEXT,
                    actual_delivery_time TEXT,
                    opened_time TEXT,
                    engagement_time TEXT,
                    engagement_score REAL,
                    channel TEXT,
                    content_type TEXT,
                    created_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS optimal_timings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    content_type TEXT,
                    recommended_time TEXT,
                    confidence_score REAL,
                    strategy TEXT,
                    reasoning TEXT,
                    valid_until TEXT,
                    created_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_timezone_preferences (
                    user_id TEXT PRIMARY KEY,
                    timezone TEXT,
                    auto_detected BOOLEAN,
                    last_updated TEXT
                )
            ''')
            
    def analyze_user_timing_patterns(self, user_id: str, 
                                   interaction_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """ユーザータイミングパターン分析"""
        
        if not interaction_history:
            return self._default_timing_patterns()
            
        patterns = {
            'hourly_distribution': defaultdict(int),
            'daily_distribution': defaultdict(int),
            'response_times': [],
            'engagement_by_hour': defaultdict(list),
            'peak_activity_windows': [],
            'consistency_score': 0.0
        }
        
        # 時間別活動分析
        activity_times = []
        engagement_scores = []
        
        for interaction in interaction_history:
            try:
                timestamp = datetime.fromisoformat(interaction.get('timestamp', ''))
                hour = timestamp.hour
                day_of_week = timestamp.weekday()
                
                patterns['hourly_distribution'][hour] += 1
                patterns['daily_distribution'][day_of_week] += 1
                activity_times.append(hour)
                
                # エンゲージメントスコア
                engagement = self._calculate_interaction_engagement(interaction)
                patterns['engagement_by_hour'][hour].append(engagement)
                engagement_scores.append(engagement)
                
                # レスポンス時間（セッション継続時間から推定）
                response_time = interaction.get('session_duration', 0) / 60  # 分に変換
                if response_time > 0:
                    patterns['response_times'].append(response_time)
                    
            except ValueError:
                continue
                
        # 活動パターンの一貫性
        if activity_times:
            hour_std = np.std(activity_times)
            patterns['consistency_score'] = max(0.0, 1.0 - (hour_std / 12.0))
            
        # ピーク活動時間帯検出
        patterns['peak_activity_windows'] = self._identify_peak_windows(
            patterns['hourly_distribution']
        )
        
        # 時間帯別エンゲージメント平均
        hourly_engagement = {}
        for hour, engagements in patterns['engagement_by_hour'].items():
            if engagements:
                hourly_engagement[hour] = np.mean(engagements)
                
        patterns['hourly_engagement_avg'] = hourly_engagement
        
        return patterns
        
    def _default_timing_patterns(self) -> Dict[str, Any]:
        """デフォルトタイミングパターン"""
        return {
            'hourly_distribution': {9: 3, 12: 2, 18: 2},  # 朝・昼・夕方
            'daily_distribution': {i: 1 for i in range(7)},
            'response_times': [5.0],  # 5分
            'engagement_by_hour': {9: [0.7], 12: [0.6], 18: [0.8]},
            'peak_activity_windows': [(9, 10), (18, 19)],
            'consistency_score': 0.5,
            'hourly_engagement_avg': {9: 0.7, 12: 0.6, 18: 0.8}
        }
        
    def _calculate_interaction_engagement(self, interaction: Dict[str, Any]) -> float:
        """インタラクションエンゲージメント計算"""
        base_scores = {
            'view': 0.2,
            'click': 0.4,
            'share': 0.8,
            'comment': 0.9,
            'save': 0.7,
            'like': 0.5
        }
        
        action_type = interaction.get('action_type', 'view')
        base_score = base_scores.get(action_type, 0.2)
        
        # セッション時間ボーナス
        session_duration = interaction.get('session_duration', 0)
        time_bonus = min(0.3, session_duration / 300.0) if session_duration > 30 else 0
        
        return min(1.0, base_score + time_bonus)
        
    def _identify_peak_windows(self, hourly_distribution: Dict[int, int]) -> List[Tuple[int, int]]:
        """ピーク活動時間帯特定"""
        if not hourly_distribution:
            return [(9, 10), (18, 19)]  # デフォルト
            
        # 活動量でソート
        sorted_hours = sorted(hourly_distribution.items(), key=lambda x: x[1], reverse=True)
        
        # 上位時間帯を連続区間にグループ化
        peak_windows = []
        top_hours = [hour for hour, count in sorted_hours[:6]]  # 上位6時間
        top_hours.sort()
        
        if not top_hours:
            return [(9, 10), (18, 19)]
            
        # 連続時間を窓にまとめる
        current_window_start = top_hours[0]
        current_window_end = top_hours[0]
        
        for hour in top_hours[1:]:
            if hour == current_window_end + 1:
                current_window_end = hour
            else:
                if current_window_end > current_window_start:
                    peak_windows.append((current_window_start, current_window_end + 1))
                else:
                    peak_windows.append((current_window_start, current_window_start + 1))
                current_window_start = hour
                current_window_end = hour
                
        # 最後の窓を追加
        if current_window_end > current_window_start:
            peak_windows.append((current_window_start, current_window_end + 1))
        else:
            peak_windows.append((current_window_start, current_window_start + 1))
            
        return peak_windows[:3]  # 最大3つの窓
        
    def calculate_delivery_windows(self, user_id: str, 
                                 timing_patterns: Dict[str, Any],
                                 channels: List[DeliveryChannel] = None) -> List[DeliveryWindow]:
        """配信時間窓計算"""
        
        if channels is None:
            channels = list(DeliveryChannel)
            
        delivery_windows = []
        peak_windows = timing_patterns.get('peak_activity_windows', [(9, 10), (18, 19)])
        hourly_engagement = timing_patterns.get('hourly_engagement_avg', {})
        
        for channel in channels:
            for start_hour, end_hour in peak_windows:
                # 時間帯のエンゲージメント予測
                window_hours = list(range(start_hour, end_hour))
                engagement_scores = [hourly_engagement.get(h, 0.5) for h in window_hours]
                avg_engagement = np.mean(engagement_scores) if engagement_scores else 0.5
                
                # チャネル別調整
                channel_multiplier = self.channel_weights.get(channel, 0.2)
                adjusted_engagement = avg_engagement * (0.5 + channel_multiplier)
                
                # 確率スコア（活動頻度ベース）
                hourly_dist = timing_patterns.get('hourly_distribution', {})
                window_activity = sum(hourly_dist.get(h, 0) for h in window_hours)
                total_activity = sum(hourly_dist.values()) or 1
                probability = window_activity / total_activity
                
                delivery_windows.append(DeliveryWindow(
                    channel=channel,
                    user_id=user_id,
                    start_time=time(start_hour, 0),
                    end_time=time(end_hour, 0),
                    probability_score=probability,
                    engagement_prediction=adjusted_engagement
                ))
                
        # エンゲージメント予測でソート
        delivery_windows.sort(key=lambda x: x.engagement_prediction, reverse=True)
        
        return delivery_windows[:10]  # 上位10個
        
    def optimize_delivery_timing(self, user_id: str, content_type: str,
                               interaction_history: List[Dict[str, Any]],
                               preferred_channels: List[DeliveryChannel] = None,
                               urgency_level: str = "normal") -> OptimalTiming:
        """配信タイミング最適化"""
        
        # ユーザータイミングパターン分析
        timing_patterns = self.analyze_user_timing_patterns(user_id, interaction_history)
        
        # 配信時間窓計算
        delivery_windows = self.calculate_delivery_windows(
            user_id, timing_patterns, preferred_channels
        )
        
        if not delivery_windows:
            return self._create_default_timing(user_id, content_type)
            
        # 戦略決定
        strategy = self._determine_timing_strategy(
            timing_patterns, urgency_level, len(interaction_history)
        )
        
        # 最適時間決定
        if strategy == TimingStrategy.IMMEDIATE:
            recommended_time = datetime.now()
            confidence = 0.8
        elif strategy == TimingStrategy.SCHEDULED:
            # 固定スケジュール（例：毎日9時）
            tomorrow_9am = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            if tomorrow_9am <= datetime.now():
                tomorrow_9am += timedelta(days=1)
            recommended_time = tomorrow_9am
            confidence = 0.7
        else:
            # 最適化による決定
            best_window = delivery_windows[0]
            recommended_time = self._calculate_optimal_time_in_window(
                best_window, timing_patterns
            )
            confidence = self._calculate_timing_confidence(
                timing_patterns, len(interaction_history)
            )
            
        # フォールバック時間
        fallback_times = self._generate_fallback_times(
            recommended_time, delivery_windows[1:4]
        )
        
        # 推論理由
        reasoning = self._generate_timing_reasoning(
            timing_patterns, strategy, delivery_windows[0] if delivery_windows else None
        )
        
        return OptimalTiming(
            user_id=user_id,
            content_type=content_type,
            recommended_time=recommended_time,
            confidence_score=confidence,
            strategy=strategy,
            delivery_windows=delivery_windows,
            fallback_times=fallback_times,
            reasoning=reasoning
        )
        
    def _create_default_timing(self, user_id: str, content_type: str) -> OptimalTiming:
        """デフォルトタイミング作成"""
        # 一般的に効果的とされる朝9時
        tomorrow_9am = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        if tomorrow_9am <= datetime.now():
            tomorrow_9am += timedelta(days=1)
            
        return OptimalTiming(
            user_id=user_id,
            content_type=content_type,
            recommended_time=tomorrow_9am,
            confidence_score=0.3,
            strategy=TimingStrategy.SCHEDULED,
            delivery_windows=[],
            fallback_times=[tomorrow_9am + timedelta(hours=3)],
            reasoning={'default_strategy': '十分なデータがないためデフォルト時間を使用'}
        )
        
    def _determine_timing_strategy(self, timing_patterns: Dict[str, Any], 
                                 urgency_level: str, data_points: int) -> TimingStrategy:
        """タイミング戦略決定"""
        
        if urgency_level == "urgent":
            return TimingStrategy.IMMEDIATE
            
        if data_points < self.min_samples_for_personalization:
            return TimingStrategy.SCHEDULED
            
        consistency = timing_patterns.get('consistency_score', 0.5)
        
        if consistency > 0.7:
            return TimingStrategy.OPTIMAL_ENGAGEMENT
        elif consistency > 0.4:
            return TimingStrategy.ADAPTIVE
        else:
            return TimingStrategy.BATCH
            
    def _calculate_optimal_time_in_window(self, window: DeliveryWindow, 
                                        timing_patterns: Dict[str, Any]) -> datetime:
        """時間窓内の最適時間計算"""
        
        start_hour = window.start_time.hour
        end_hour = window.end_time.hour
        
        # 時間帯別エンゲージメント取得
        hourly_engagement = timing_patterns.get('hourly_engagement_avg', {})
        
        # 窓内で最もエンゲージメントの高い時間
        best_hour = start_hour
        best_engagement = hourly_engagement.get(start_hour, 0.5)
        
        for hour in range(start_hour, end_hour):
            engagement = hourly_engagement.get(hour, 0.5)
            if engagement > best_engagement:
                best_hour = hour
                best_engagement = engagement
                
        # 明日の該当時間
        target_time = datetime.now().replace(
            hour=best_hour, minute=0, second=0, microsecond=0
        )
        
        if target_time <= datetime.now():
            target_time += timedelta(days=1)
            
        return target_time
        
    def _calculate_timing_confidence(self, timing_patterns: Dict[str, Any], 
                                   data_points: int) -> float:
        """タイミング信頼度計算"""
        
        # データ量による信頼度
        data_confidence = min(1.0, data_points / 50.0)
        
        # パターン一貫性による信頼度
        consistency = timing_patterns.get('consistency_score', 0.5)
        
        # 全体信頼度
        overall_confidence = (data_confidence * 0.6 + consistency * 0.4)
        
        return overall_confidence
        
    def _generate_fallback_times(self, primary_time: datetime, 
                               alternative_windows: List[DeliveryWindow]) -> List[datetime]:
        """フォールバック時間生成"""
        
        fallback_times = []
        
        # プライマリ時間の1時間後
        fallback_times.append(primary_time + timedelta(hours=1))
        
        # 代替窓の活用
        for window in alternative_windows:
            fallback_time = datetime.now().replace(
                hour=window.start_time.hour,
                minute=0, second=0, microsecond=0
            )
            if fallback_time <= datetime.now():
                fallback_time += timedelta(days=1)
            fallback_times.append(fallback_time)
            
        return fallback_times[:3]  # 最大3つ
        
    def _generate_timing_reasoning(self, timing_patterns: Dict[str, Any],
                                 strategy: TimingStrategy,
                                 best_window: Optional[DeliveryWindow]) -> Dict[str, Any]:
        """タイミング推論理由生成"""
        
        reasoning = {
            'strategy': strategy.value,
            'factors': {}
        }
        
        if best_window:
            reasoning['factors']['primary_channel'] = best_window.channel.value
            reasoning['factors']['engagement_prediction'] = best_window.engagement_prediction
            reasoning['factors']['activity_probability'] = best_window.probability_score
            
        consistency = timing_patterns.get('consistency_score', 0.5)
        reasoning['factors']['pattern_consistency'] = consistency
        
        peak_windows = timing_patterns.get('peak_activity_windows', [])
        if peak_windows:
            reasoning['factors']['peak_windows'] = [
                f"{start}:00-{end}:00" for start, end in peak_windows
            ]
            
        return reasoning
        
    def record_delivery_performance(self, performance: DeliveryPerformance):
        """配信パフォーマンス記録"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO delivery_performance 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                performance.delivery_id,
                performance.user_id,
                performance.scheduled_time.isoformat(),
                performance.actual_delivery_time.isoformat(),
                performance.opened_time.isoformat() if performance.opened_time else None,
                performance.engagement_time.isoformat() if performance.engagement_time else None,
                performance.engagement_score,
                performance.channel.value,
                "news",  # content_type
                datetime.now().isoformat()
            ))
            
        # タイミング指標更新
        self._update_timing_metrics(performance)
        
    def _update_timing_metrics(self, performance: DeliveryPerformance):
        """タイミング指標更新"""
        
        hour = performance.actual_delivery_time.hour
        day_of_week = performance.actual_delivery_time.weekday()
        time_slot = f"{hour:02d}:00"
        
        # 既存メトリクス取得
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT engagement_rate, response_rate, avg_response_time_minutes, sample_size
                FROM timing_metrics 
                WHERE user_id = ? AND time_slot = ? AND day_of_week = ?
            ''', (performance.user_id, time_slot, day_of_week))
            
            existing = cursor.fetchone()
            
        if existing:
            # 既存データと新データを統合
            old_engagement = existing[0]
            old_sample_size = existing[3]
            
            new_sample_size = old_sample_size + 1
            new_engagement_rate = (
                (old_engagement * old_sample_size + performance.engagement_score) / 
                new_sample_size
            )
            
            # レスポンス時間計算
            response_time_minutes = 0
            if performance.engagement_time and performance.actual_delivery_time:
                response_time_minutes = int(
                    (performance.engagement_time - performance.actual_delivery_time).total_seconds() / 60
                )
                
            new_response_time = (
                (existing[2] * old_sample_size + response_time_minutes) /
                new_sample_size
            )
            
            response_rate = 1.0 if performance.engagement_time else 0.0
            new_response_rate = (
                (existing[1] * old_sample_size + response_rate) /
                new_sample_size
            )
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE timing_metrics 
                    SET engagement_rate = ?, response_rate = ?, 
                        avg_response_time_minutes = ?, sample_size = ?, last_updated = ?
                    WHERE user_id = ? AND time_slot = ? AND day_of_week = ?
                ''', (
                    new_engagement_rate, new_response_rate, int(new_response_time),
                    new_sample_size, datetime.now().isoformat(),
                    performance.user_id, time_slot, day_of_week
                ))
        else:
            # 新規メトリクス作成
            response_time_minutes = 0
            if performance.engagement_time and performance.actual_delivery_time:
                response_time_minutes = int(
                    (performance.engagement_time - performance.actual_delivery_time).total_seconds() / 60
                )
                
            response_rate = 1.0 if performance.engagement_time else 0.0
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO timing_metrics 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    performance.user_id, time_slot, day_of_week,
                    performance.engagement_score, response_rate,
                    response_time_minutes, 1,
                    datetime.now().isoformat()
                ))
                
    def save_optimal_timing(self, optimal_timing: OptimalTiming):
        """最適タイミング保存"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO optimal_timings 
                (user_id, content_type, recommended_time, confidence_score, 
                 strategy, reasoning, valid_until, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                optimal_timing.user_id,
                optimal_timing.content_type,
                optimal_timing.recommended_time.isoformat(),
                optimal_timing.confidence_score,
                optimal_timing.strategy.value,
                json.dumps(optimal_timing.reasoning),
                (datetime.now() + timedelta(days=1)).isoformat(),
                datetime.now().isoformat()
            ))
            
    def get_user_timing_analytics(self, user_id: str) -> Dict[str, Any]:
        """ユーザータイミング分析取得"""
        
        with sqlite3.connect(self.db_path) as conn:
            # タイミング指標
            cursor = conn.execute('''
                SELECT time_slot, day_of_week, engagement_rate, response_rate, 
                       avg_response_time_minutes, sample_size
                FROM timing_metrics 
                WHERE user_id = ?
                ORDER BY engagement_rate DESC
            ''', (user_id,))
            
            timing_metrics = []
            for row in cursor.fetchall():
                timing_metrics.append({
                    'time_slot': row[0],
                    'day_of_week': row[1],
                    'engagement_rate': row[2],
                    'response_rate': row[3],
                    'avg_response_time_minutes': row[4],
                    'sample_size': row[5]
                })
                
            # 最近の最適タイミング
            cursor = conn.execute('''
                SELECT recommended_time, confidence_score, strategy, reasoning
                FROM optimal_timings 
                WHERE user_id = ? AND valid_until > ?
                ORDER BY created_at DESC LIMIT 1
            ''', (user_id, datetime.now().isoformat()))
            
            latest_timing = cursor.fetchone()
            
        return {
            'user_id': user_id,
            'timing_metrics': timing_metrics,
            'latest_optimal_timing': {
                'recommended_time': latest_timing[0] if latest_timing else None,
                'confidence_score': latest_timing[1] if latest_timing else None,
                'strategy': latest_timing[2] if latest_timing else None,
                'reasoning': json.loads(latest_timing[3]) if latest_timing else None
            } if latest_timing else None,
            'analytics_generated_at': datetime.now().isoformat()
        }

if __name__ == "__main__":
    # テスト実行
    optimizer = IntelligentTimingOptimizer()
    
    # テストインタラクション履歴
    test_interactions = [
        {
            'timestamp': datetime(2024, 1, 15, 9, 30).isoformat(),
            'action_type': 'view',
            'session_duration': 180
        },
        {
            'timestamp': datetime(2024, 1, 15, 18, 15).isoformat(),
            'action_type': 'share',
            'session_duration': 120
        },
        {
            'timestamp': datetime(2024, 1, 16, 9, 0).isoformat(),
            'action_type': 'view',
            'session_duration': 240
        }
    ]
    
    # 最適タイミング決定
    optimal_timing = optimizer.optimize_delivery_timing(
        user_id='test_user_001',
        content_type='news',
        interaction_history=test_interactions,
        preferred_channels=[DeliveryChannel.PUSH, DeliveryChannel.EMAIL]
    )
    
    print("Optimal Timing:")
    print(json.dumps(asdict(optimal_timing), indent=2, ensure_ascii=False, default=str))
    
    # 保存
    optimizer.save_optimal_timing(optimal_timing)
    
    # 分析データ取得
    analytics = optimizer.get_user_timing_analytics('test_user_001')
    print("\nTiming Analytics:")
    print(json.dumps(analytics, indent=2, ensure_ascii=False, default=str))