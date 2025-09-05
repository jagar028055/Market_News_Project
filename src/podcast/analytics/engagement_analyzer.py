"""
ユーザーエンゲージメント分析システム

このモジュールはユーザーの行動パターン、エンゲージメント率、トレンド分析を提供します。
"""

import sqlite3
import logging
import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
import statistics
from .analytics_engine import AnalyticsEngine


@dataclass
class UserEngagementProfile:
    """ユーザーエンゲージメントプロファイル"""

    user_id: str
    total_interactions: int
    unique_episodes: int
    avg_read_time: float
    favorite_time_slots: List[int]  # 時間帯（0-23）
    engagement_score: float
    last_activity: datetime.datetime
    subscription_status: bool


@dataclass
class EpisodeEngagementSummary:
    """エピソードエンゲージメントサマリー"""

    episode_id: str
    total_views: int
    unique_viewers: int
    total_clicks: int
    total_shares: int
    avg_read_time: float
    peak_activity_hour: int
    engagement_score: float
    retention_rate: float


@dataclass
class EngagementTrend:
    """エンゲージメントトレンド"""

    date: datetime.date
    total_interactions: int
    unique_users: int
    avg_engagement_score: float
    top_content_types: List[str]


class EngagementAnalyzer:
    """ユーザーエンゲージメント分析エンジン"""

    def __init__(self, analytics_engine: Optional[AnalyticsEngine] = None):
        self.analytics = analytics_engine or AnalyticsEngine()
        self.logger = logging.getLogger(__name__)

    def analyze_user_engagement(
        self, user_id: str, days: int = 30
    ) -> Optional[UserEngagementProfile]:
        """ユーザーエンゲージメント分析"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                # 基本統計取得
                basic_stats = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_interactions,
                        COUNT(DISTINCT episode_id) as unique_episodes,
                        MAX(event_time) as last_activity
                    FROM engagement_events 
                    WHERE user_id = ? AND event_time >= datetime('now', '-{} days')
                """.format(
                        days
                    ),
                    (user_id,),
                ).fetchone()

                if not basic_stats or basic_stats[0] == 0:
                    return None

                # 読取時間統計
                read_time_stats = conn.execute(
                    """
                    SELECT AVG(CAST(json_extract(event_data, '$.duration') AS REAL))
                    FROM engagement_events 
                    WHERE user_id = ? AND event_type = 'read_time' 
                    AND event_time >= datetime('now', '-{} days')
                """.format(
                        days
                    ),
                    (user_id,),
                ).fetchone()

                # 時間帯別活動
                time_slots = conn.execute(
                    """
                    SELECT 
                        strftime('%H', event_time) as hour,
                        COUNT(*) as activity_count
                    FROM engagement_events 
                    WHERE user_id = ? AND event_time >= datetime('now', '-{} days')
                    GROUP BY hour
                    ORDER BY activity_count DESC
                    LIMIT 3
                """.format(
                        days
                    ),
                    (user_id,),
                ).fetchall()

                # 購読状況確認
                subscription_status = conn.execute(
                    """
                    SELECT COUNT(*) > 0
                    FROM engagement_events 
                    WHERE user_id = ? AND event_type = 'subscribe'
                    AND event_time >= datetime('now', '-{} days')
                """.format(
                        days
                    ),
                    (user_id,),
                ).fetchone()[0]

                # エンゲージメントスコア計算
                engagement_score = self._calculate_user_engagement_score(
                    user_id, basic_stats[0], basic_stats[1], days
                )

                return UserEngagementProfile(
                    user_id=user_id,
                    total_interactions=basic_stats[0],
                    unique_episodes=basic_stats[1],
                    avg_read_time=read_time_stats[0] or 0.0,
                    favorite_time_slots=[int(slot[0]) for slot in time_slots],
                    engagement_score=engagement_score,
                    last_activity=datetime.datetime.fromisoformat(basic_stats[2]),
                    subscription_status=bool(subscription_status),
                )

        except Exception as e:
            self.logger.error(f"ユーザーエンゲージメント分析エラー: {e}")
            return None

    def analyze_episode_engagement(self, episode_id: str) -> Optional[EpisodeEngagementSummary]:
        """エピソードエンゲージメント分析"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                # 基本統計
                basic_stats = conn.execute(
                    """
                    SELECT 
                        COUNT(CASE WHEN event_type = 'view' THEN 1 END) as total_views,
                        COUNT(DISTINCT user_id) as unique_viewers,
                        COUNT(CASE WHEN event_type = 'click' THEN 1 END) as total_clicks,
                        COUNT(CASE WHEN event_type = 'share' THEN 1 END) as total_shares
                    FROM engagement_events 
                    WHERE episode_id = ?
                """,
                    (episode_id,),
                ).fetchone()

                # 読取時間統計
                read_time = (
                    conn.execute(
                        """
                    SELECT AVG(CAST(json_extract(event_data, '$.duration') AS REAL))
                    FROM engagement_events 
                    WHERE episode_id = ? AND event_type = 'read_time'
                """,
                        (episode_id,),
                    ).fetchone()[0]
                    or 0.0
                )

                # ピーク活動時間
                peak_hour = conn.execute(
                    """
                    SELECT 
                        strftime('%H', event_time) as hour,
                        COUNT(*) as activity_count
                    FROM engagement_events 
                    WHERE episode_id = ?
                    GROUP BY hour
                    ORDER BY activity_count DESC
                    LIMIT 1
                """,
                    (episode_id,),
                ).fetchone()

                peak_activity_hour = int(peak_hour[0]) if peak_hour else 12

                # エンゲージメントスコアと保持率計算
                engagement_score = self._calculate_episode_engagement_score(episode_id)
                retention_rate = self._calculate_retention_rate(episode_id)

                return EpisodeEngagementSummary(
                    episode_id=episode_id,
                    total_views=basic_stats[0],
                    unique_viewers=basic_stats[1],
                    total_clicks=basic_stats[2],
                    total_shares=basic_stats[3],
                    avg_read_time=read_time,
                    peak_activity_hour=peak_activity_hour,
                    engagement_score=engagement_score,
                    retention_rate=retention_rate,
                )

        except Exception as e:
            self.logger.error(f"エピソードエンゲージメント分析エラー: {e}")
            return None

    def get_engagement_trends(self, days: int = 7) -> List[EngagementTrend]:
        """エンゲージメントトレンド分析"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                # 日別エンゲージメント統計
                daily_stats = conn.execute(
                    """
                    SELECT 
                        DATE(event_time) as date,
                        COUNT(*) as total_interactions,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM engagement_events 
                    WHERE event_time >= datetime('now', '-{} days')
                    GROUP BY DATE(event_time)
                    ORDER BY date DESC
                """.format(
                        days
                    )
                ).fetchall()

                trends = []
                for date_str, interactions, users in daily_stats:
                    # その日のエンゲージメントスコア平均
                    avg_score = self._calculate_daily_avg_engagement_score(date_str)

                    # その日のトップコンテンツタイプ
                    top_types = self._get_top_content_types_for_date(date_str)

                    trends.append(
                        EngagementTrend(
                            date=datetime.date.fromisoformat(date_str),
                            total_interactions=interactions,
                            unique_users=users,
                            avg_engagement_score=avg_score,
                            top_content_types=top_types,
                        )
                    )

                return trends

        except Exception as e:
            self.logger.error(f"エンゲージメントトレンド分析エラー: {e}")
            return []

    def get_top_engaged_users(self, limit: int = 10, days: int = 30) -> List[UserEngagementProfile]:
        """エンゲージメント上位ユーザー取得"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                top_users = conn.execute(
                    """
                    SELECT 
                        user_id,
                        COUNT(*) as total_interactions
                    FROM engagement_events 
                    WHERE event_time >= datetime('now', '-{} days')
                    GROUP BY user_id
                    ORDER BY total_interactions DESC
                    LIMIT ?
                """.format(
                        days
                    ),
                    (limit,),
                ).fetchall()

                profiles = []
                for user_id, _ in top_users:
                    profile = self.analyze_user_engagement(user_id, days)
                    if profile:
                        profiles.append(profile)

                return profiles

        except Exception as e:
            self.logger.error(f"トップユーザー取得エラー: {e}")
            return []

    def get_engagement_heatmap(self, days: int = 7) -> Dict[str, Any]:
        """エンゲージメントヒートマップ生成"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                # 時間帯別×曜日別アクティビティ
                heatmap_data = conn.execute(
                    """
                    SELECT 
                        strftime('%w', event_time) as day_of_week,
                        strftime('%H', event_time) as hour,
                        COUNT(*) as activity_count
                    FROM engagement_events 
                    WHERE event_time >= datetime('now', '-{} days')
                    GROUP BY day_of_week, hour
                    ORDER BY day_of_week, hour
                """.format(
                        days
                    )
                ).fetchall()

                # ヒートマップ形式に変換
                heatmap = defaultdict(lambda: defaultdict(int))
                for day, hour, count in heatmap_data:
                    heatmap[int(day)][int(hour)] = count

                # 統計情報
                total_activity = sum(count for _, _, count in heatmap_data)
                peak_hour = max(heatmap_data, key=lambda x: x[2]) if heatmap_data else None

                return {
                    "heatmap_data": dict(heatmap),
                    "total_activity": total_activity,
                    "peak_time": (
                        {
                            "day_of_week": int(peak_hour[0]),
                            "hour": int(peak_hour[1]),
                            "activity_count": peak_hour[2],
                        }
                        if peak_hour
                        else None
                    ),
                    "analysis_period_days": days,
                    "last_updated": datetime.datetime.now().isoformat(),
                }

        except Exception as e:
            self.logger.error(f"ヒートマップ生成エラー: {e}")
            return {}

    def _calculate_user_engagement_score(
        self, user_id: str, interactions: int, episodes: int, days: int
    ) -> float:
        """ユーザーエンゲージメントスコア計算"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                # 様々な行動の重み付け
                action_weights = {
                    "view": 1.0,
                    "click": 2.0,
                    "share": 3.0,
                    "subscribe": 5.0,
                    "read_time": 1.5,
                }

                weighted_score = 0
                for action, weight in action_weights.items():
                    count = conn.execute(
                        """
                        SELECT COUNT(*) 
                        FROM engagement_events 
                        WHERE user_id = ? AND event_type = ? 
                        AND event_time >= datetime('now', '-{} days')
                    """.format(
                            days
                        ),
                        (user_id, action),
                    ).fetchone()[0]

                    weighted_score += count * weight

                # 正規化（0-100スケール）
                max_possible_score = days * 10  # 1日10ポイントが最大と仮定
                normalized_score = min(100, (weighted_score / max_possible_score) * 100)

                return round(normalized_score, 2)

        except Exception as e:
            self.logger.error(f"エンゲージメントスコア計算エラー: {e}")
            return 0.0

    def _calculate_episode_engagement_score(self, episode_id: str) -> float:
        """エピソードエンゲージメントスコア計算"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                # 配信数取得
                delivery_count = (
                    conn.execute(
                        """
                    SELECT SUM(recipient_count) 
                    FROM delivery_events 
                    WHERE episode_id = ? AND status = 'delivered'
                """,
                        (episode_id,),
                    ).fetchone()[0]
                    or 1
                )

                # エンゲージメント数取得
                engagement_count = (
                    conn.execute(
                        """
                    SELECT COUNT(DISTINCT user_id) 
                    FROM engagement_events 
                    WHERE episode_id = ?
                """,
                        (episode_id,),
                    ).fetchone()[0]
                    or 0
                )

                # エンゲージメント率計算（0-100）
                engagement_rate = (engagement_count / delivery_count) * 100
                return round(min(100, engagement_rate), 2)

        except Exception as e:
            self.logger.error(f"エピソードスコア計算エラー: {e}")
            return 0.0

    def _calculate_retention_rate(self, episode_id: str) -> float:
        """保持率計算"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                # ビューワー数
                total_viewers = (
                    conn.execute(
                        """
                    SELECT COUNT(DISTINCT user_id) 
                    FROM engagement_events 
                    WHERE episode_id = ? AND event_type = 'view'
                """,
                        (episode_id,),
                    ).fetchone()[0]
                    or 0
                )

                # 読み終えたユーザー数（read_timeが平均以上）
                completed_users = (
                    conn.execute(
                        """
                    SELECT COUNT(DISTINCT user_id)
                    FROM engagement_events e1
                    WHERE e1.episode_id = ? AND e1.event_type = 'read_time'
                    AND CAST(json_extract(e1.event_data, '$.duration') AS REAL) >= (
                        SELECT AVG(CAST(json_extract(event_data, '$.duration') AS REAL))
                        FROM engagement_events
                        WHERE episode_id = ? AND event_type = 'read_time'
                    )
                """,
                        (episode_id, episode_id),
                    ).fetchone()[0]
                    or 0
                )

                if total_viewers == 0:
                    return 0.0

                retention_rate = (completed_users / total_viewers) * 100
                return round(retention_rate, 2)

        except Exception as e:
            self.logger.error(f"保持率計算エラー: {e}")
            return 0.0

    def _calculate_daily_avg_engagement_score(self, date_str: str) -> float:
        """日別平均エンゲージメントスコア"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                users = conn.execute(
                    """
                    SELECT DISTINCT user_id 
                    FROM engagement_events 
                    WHERE DATE(event_time) = ?
                """,
                    (date_str,),
                ).fetchall()

                if not users:
                    return 0.0

                scores = []
                for (user_id,) in users:
                    score = self._calculate_user_engagement_score(user_id, 0, 0, 1)
                    scores.append(score)

                return round(statistics.mean(scores) if scores else 0.0, 2)

        except Exception as e:
            self.logger.error(f"日別平均スコア計算エラー: {e}")
            return 0.0

    def _get_top_content_types_for_date(self, date_str: str) -> List[str]:
        """日別トップコンテンツタイプ"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                content_types = conn.execute(
                    """
                    SELECT 
                        event_type,
                        COUNT(*) as type_count
                    FROM engagement_events 
                    WHERE DATE(event_time) = ?
                    GROUP BY event_type
                    ORDER BY type_count DESC
                    LIMIT 3
                """,
                    (date_str,),
                ).fetchall()

                return [content_type for content_type, _ in content_types]

        except Exception as e:
            self.logger.error(f"コンテンツタイプ取得エラー: {e}")
            return []
