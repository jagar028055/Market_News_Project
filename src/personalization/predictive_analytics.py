"""
予測分析システム
機械学習を活用したユーザー行動・エンゲージメント・コンテンツ需要の予測
"""

import json
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from collections import defaultdict, deque
import math
from enum import Enum


class PredictionType(Enum):
    """予測タイプ"""

    ENGAGEMENT = "engagement"
    CHURN_RISK = "churn_risk"
    CONTENT_DEMAND = "content_demand"
    OPTIMAL_TIMING = "optimal_timing"
    USER_GROWTH = "user_growth"


@dataclass
class PredictionResult:
    """予測結果"""

    prediction_id: str
    user_id: Optional[str]
    prediction_type: PredictionType
    predicted_value: float
    confidence_level: float
    prediction_date: datetime
    valid_until: datetime
    contributing_factors: Dict[str, float]
    model_version: str


@dataclass
class ModelMetrics:
    """モデル評価指標"""

    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    mae: float  # Mean Absolute Error
    rmse: float  # Root Mean Square Error
    last_updated: datetime


@dataclass
class TrendAnalysis:
    """トレンド分析"""

    metric_name: str
    time_series: List[Tuple[datetime, float]]
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float
    seasonality_detected: bool
    forecast_values: List[Tuple[datetime, float]]
    confidence_intervals: List[Tuple[datetime, float, float]]


class PredictiveAnalytics:
    """予測分析エンジン"""

    def __init__(self, db_path: str = "predictive_analytics.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

        # モデル設定
        self.prediction_window_days = 7
        self.min_data_points = 30
        self.model_retrain_interval_days = 7

        # 特徴量重み
        self.engagement_features = {
            "recent_activity": 0.3,
            "session_frequency": 0.25,
            "content_interaction": 0.2,
            "time_patterns": 0.15,
            "social_signals": 0.1,
        }

        self._init_database()

    def _init_database(self):
        """データベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    prediction_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    prediction_type TEXT,
                    predicted_value REAL,
                    confidence_level REAL,
                    prediction_date TEXT,
                    valid_until TEXT,
                    contributing_factors TEXT,
                    model_version TEXT,
                    actual_value REAL,
                    is_validated BOOLEAN DEFAULT 0
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS model_metrics (
                    model_name TEXT PRIMARY KEY,
                    accuracy REAL,
                    precision_score REAL,
                    recall REAL,
                    f1_score REAL,
                    mae REAL,
                    rmse REAL,
                    last_updated TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS time_series_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT,
                    timestamp TEXT,
                    value REAL,
                    metadata TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feature_importance (
                    model_name TEXT,
                    feature_name TEXT,
                    importance_score REAL,
                    updated_at TEXT,
                    PRIMARY KEY (model_name, feature_name)
                )
            """
            )

    def extract_user_features(
        self, user_id: str, interaction_history: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """ユーザー特徴量抽出"""

        if not interaction_history:
            return self._default_feature_vector()

        # 時系列データを日付順にソート
        sorted_history = sorted(
            interaction_history,
            key=lambda x: datetime.fromisoformat(x.get("timestamp", "2020-01-01")),
        )

        features = {}

        # 最近の活動レベル（7日間）
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_interactions = [
            interaction
            for interaction in sorted_history
            if datetime.fromisoformat(interaction.get("timestamp", "2020-01-01")) >= recent_cutoff
        ]

        features["recent_activity"] = len(recent_interactions) / 7.0

        # セッション頻度（全期間の平均）
        if sorted_history:
            first_date = datetime.fromisoformat(sorted_history[0].get("timestamp", "2020-01-01"))
            days_active = max(1, (datetime.now() - first_date).days)
            features["session_frequency"] = len(sorted_history) / days_active
        else:
            features["session_frequency"] = 0.0

        # コンテンツインタラクション多様性
        action_types = [interaction.get("action_type", "view") for interaction in sorted_history]
        unique_actions = len(set(action_types))
        features["content_interaction"] = unique_actions / max(len(action_types), 1)

        # 時間パターンの一貫性
        reading_hours = []
        for interaction in sorted_history:
            try:
                timestamp = datetime.fromisoformat(interaction["timestamp"])
                reading_hours.append(timestamp.hour)
            except:
                continue

        if reading_hours:
            hour_std = np.std(reading_hours)
            features["time_patterns"] = 1.0 - min(1.0, hour_std / 12.0)  # 一貫性が高いほど高スコア
        else:
            features["time_patterns"] = 0.5

        # ソーシャルシグナル（シェア・コメント率）
        social_actions = [
            interaction
            for interaction in sorted_history
            if interaction.get("action_type") in ["share", "comment", "like"]
        ]
        features["social_signals"] = len(social_actions) / max(len(sorted_history), 1)

        # セッション継続時間の平均
        session_durations = [
            interaction.get("session_duration", 0) for interaction in sorted_history
        ]
        avg_duration = np.mean(session_durations) if session_durations else 0
        features["avg_session_duration"] = min(1.0, avg_duration / 600.0)  # 10分で正規化

        # 成長トレンド（最近30日 vs 前30日）
        if len(sorted_history) >= 10:
            mid_date = datetime.now() - timedelta(days=30)
            recent_30 = [
                interaction
                for interaction in sorted_history
                if datetime.fromisoformat(interaction.get("timestamp", "2020-01-01")) >= mid_date
            ]
            previous_30 = [
                interaction
                for interaction in sorted_history
                if datetime.fromisoformat(interaction.get("timestamp", "2020-01-01")) < mid_date
            ]

            if previous_30:
                growth_rate = len(recent_30) / len(previous_30)
                features["engagement_growth"] = min(2.0, growth_rate) / 2.0
            else:
                features["engagement_growth"] = 1.0
        else:
            features["engagement_growth"] = 0.5

        # 曜日パターン
        weekdays = []
        for interaction in sorted_history:
            try:
                timestamp = datetime.fromisoformat(interaction["timestamp"])
                weekdays.append(timestamp.weekday())
            except:
                continue

        if weekdays:
            weekday_activity = len([d for d in weekdays if d < 5])  # 平日
            weekend_activity = len([d for d in weekdays if d >= 5])  # 週末
            total_activity = len(weekdays)
            features["weekday_preference"] = weekday_activity / max(total_activity, 1)
        else:
            features["weekday_preference"] = 0.7  # デフォルトは平日寄り

        return features

    def _default_feature_vector(self) -> Dict[str, float]:
        """デフォルト特徴量ベクトル"""
        return {
            "recent_activity": 0.1,
            "session_frequency": 0.1,
            "content_interaction": 0.3,
            "time_patterns": 0.5,
            "social_signals": 0.1,
            "avg_session_duration": 0.3,
            "engagement_growth": 0.5,
            "weekday_preference": 0.7,
        }

    def predict_user_engagement(
        self, user_id: str, interaction_history: List[Dict[str, Any]]
    ) -> PredictionResult:
        """ユーザーエンゲージメント予測"""

        features = self.extract_user_features(user_id, interaction_history)

        # 簡易回帰モデル（線形結合）
        engagement_score = 0.0
        contributing_factors = {}

        for feature_name, feature_value in features.items():
            weight = self.engagement_features.get(feature_name, 0.1)
            contribution = feature_value * weight
            engagement_score += contribution
            contributing_factors[feature_name] = contribution

        # スコア正規化
        engagement_score = min(1.0, max(0.0, engagement_score))

        # 信頼度計算（データ量と一貫性に基づく）
        data_quality = min(1.0, len(interaction_history) / 50.0)
        pattern_consistency = features.get("time_patterns", 0.5)
        confidence = (data_quality + pattern_consistency) / 2.0

        return PredictionResult(
            prediction_id=f"eng_{user_id}_{int(datetime.now().timestamp())}",
            user_id=user_id,
            prediction_type=PredictionType.ENGAGEMENT,
            predicted_value=engagement_score,
            confidence_level=confidence,
            prediction_date=datetime.now(),
            valid_until=datetime.now() + timedelta(days=self.prediction_window_days),
            contributing_factors=contributing_factors,
            model_version="linear_v1.0",
        )

    def predict_churn_risk(
        self, user_id: str, interaction_history: List[Dict[str, Any]]
    ) -> PredictionResult:
        """チャーンリスク予測"""

        if not interaction_history:
            # データ不足の場合は中程度のリスク
            return self._create_default_churn_prediction(user_id, 0.5)

        # 最後のアクティビティからの経過日数
        latest_interaction = max(
            interaction_history,
            key=lambda x: datetime.fromisoformat(x.get("timestamp", "2020-01-01")),
        )

        days_since_last = (
            datetime.now()
            - datetime.fromisoformat(latest_interaction.get("timestamp", "2020-01-01"))
        ).days

        # 活動頻度の低下トレンド
        recent_30_days = datetime.now() - timedelta(days=30)
        previous_30_days = datetime.now() - timedelta(days=60)

        recent_activity = len(
            [
                interaction
                for interaction in interaction_history
                if recent_30_days
                <= datetime.fromisoformat(interaction.get("timestamp", "2020-01-01"))
                <= datetime.now()
            ]
        )

        previous_activity = len(
            [
                interaction
                for interaction in interaction_history
                if previous_30_days
                <= datetime.fromisoformat(interaction.get("timestamp", "2020-01-01"))
                < recent_30_days
            ]
        )

        # チャーンリスク計算
        risk_factors = {}

        # 非活動期間
        inactivity_risk = min(1.0, days_since_last / 14.0)  # 14日で最大
        risk_factors["inactivity_days"] = inactivity_risk

        # 活動頻度低下
        if previous_activity > 0:
            activity_decline = max(0.0, 1.0 - (recent_activity / previous_activity))
            risk_factors["activity_decline"] = activity_decline
        else:
            risk_factors["activity_decline"] = 0.5

        # セッション品質の低下
        recent_sessions = [
            interaction
            for interaction in interaction_history
            if datetime.fromisoformat(interaction.get("timestamp", "2020-01-01")) >= recent_30_days
        ]

        if recent_sessions:
            avg_recent_duration = np.mean(
                [interaction.get("session_duration", 0) for interaction in recent_sessions]
            )

            # 全期間の平均と比較
            all_sessions = [
                interaction.get("session_duration", 0) for interaction in interaction_history
            ]
            avg_all_duration = np.mean(all_sessions)

            if avg_all_duration > 0:
                duration_decline = max(0.0, 1.0 - (avg_recent_duration / avg_all_duration))
                risk_factors["session_quality_decline"] = duration_decline
            else:
                risk_factors["session_quality_decline"] = 0.0
        else:
            risk_factors["session_quality_decline"] = 0.8  # 最近のセッションなし

        # 総合リスクスコア
        churn_risk = (
            risk_factors["inactivity_days"] * 0.4
            + risk_factors["activity_decline"] * 0.35
            + risk_factors["session_quality_decline"] * 0.25
        )

        churn_risk = min(1.0, max(0.0, churn_risk))

        # 信頼度
        confidence = min(1.0, len(interaction_history) / 30.0)

        return PredictionResult(
            prediction_id=f"churn_{user_id}_{int(datetime.now().timestamp())}",
            user_id=user_id,
            prediction_type=PredictionType.CHURN_RISK,
            predicted_value=churn_risk,
            confidence_level=confidence,
            prediction_date=datetime.now(),
            valid_until=datetime.now() + timedelta(days=self.prediction_window_days),
            contributing_factors=risk_factors,
            model_version="composite_v1.0",
        )

    def _create_default_churn_prediction(self, user_id: str, risk_level: float) -> PredictionResult:
        """デフォルトチャーン予測"""
        return PredictionResult(
            prediction_id=f"churn_{user_id}_{int(datetime.now().timestamp())}",
            user_id=user_id,
            prediction_type=PredictionType.CHURN_RISK,
            predicted_value=risk_level,
            confidence_level=0.3,
            prediction_date=datetime.now(),
            valid_until=datetime.now() + timedelta(days=self.prediction_window_days),
            contributing_factors={"insufficient_data": 1.0},
            model_version="default_v1.0",
        )

    def predict_content_demand(
        self, category: str, historical_metrics: List[Dict[str, Any]]
    ) -> PredictionResult:
        """コンテンツ需要予測"""

        if not historical_metrics:
            return self._create_default_demand_prediction(category, 0.5)

        # 時系列データ準備
        time_series = []
        for metric in historical_metrics:
            try:
                timestamp = datetime.fromisoformat(metric["timestamp"])
                value = metric.get("engagement_score", 0)
                time_series.append((timestamp, value))
            except:
                continue

        if not time_series:
            return self._create_default_demand_prediction(category, 0.5)

        # 時系列分析
        trend_analysis = self.analyze_time_series_trend(time_series)

        # 需要予測（トレンドベース）
        latest_value = time_series[-1][1] if time_series else 0.5

        if trend_analysis.trend_direction == "increasing":
            predicted_demand = min(1.0, latest_value * (1 + trend_analysis.trend_strength * 0.2))
        elif trend_analysis.trend_direction == "decreasing":
            predicted_demand = max(0.0, latest_value * (1 - trend_analysis.trend_strength * 0.2))
        else:
            predicted_demand = latest_value

        # 季節性考慮
        if trend_analysis.seasonality_detected:
            current_hour = datetime.now().hour
            seasonal_multiplier = self._get_seasonal_multiplier(category, current_hour)
            predicted_demand *= seasonal_multiplier

        contributing_factors = {
            "trend_direction": 0.6 if trend_analysis.trend_direction == "increasing" else 0.3,
            "trend_strength": trend_analysis.trend_strength,
            "historical_average": latest_value,
            "seasonality_effect": (
                seasonal_multiplier if trend_analysis.seasonality_detected else 1.0
            ),
        }

        # 信頼度
        confidence = min(1.0, len(time_series) / 50.0) * (
            1.0 if trend_analysis.trend_strength > 0.3 else 0.7
        )

        return PredictionResult(
            prediction_id=f"demand_{category}_{int(datetime.now().timestamp())}",
            user_id=None,
            prediction_type=PredictionType.CONTENT_DEMAND,
            predicted_value=predicted_demand,
            confidence_level=confidence,
            prediction_date=datetime.now(),
            valid_until=datetime.now() + timedelta(days=1),  # 需要予測は短期間
            contributing_factors=contributing_factors,
            model_version="trend_seasonal_v1.0",
        )

    def _create_default_demand_prediction(
        self, category: str, demand_level: float
    ) -> PredictionResult:
        """デフォルト需要予測"""
        return PredictionResult(
            prediction_id=f"demand_{category}_{int(datetime.now().timestamp())}",
            user_id=None,
            prediction_type=PredictionType.CONTENT_DEMAND,
            predicted_value=demand_level,
            confidence_level=0.3,
            prediction_date=datetime.now(),
            valid_until=datetime.now() + timedelta(days=1),
            contributing_factors={"insufficient_data": 1.0},
            model_version="default_v1.0",
        )

    def _get_seasonal_multiplier(self, category: str, hour: int) -> float:
        """季節性調整倍率"""
        # カテゴリ別時間帯嗜好
        seasonal_patterns = {
            "finance": {
                "morning": 1.3,  # 6-11
                "trading": 1.5,  # 9-15
                "evening": 0.8,  # 18-21
                "night": 0.4,  # 22-5
            },
            "technology": {
                "morning": 1.1,
                "afternoon": 1.2,
                "evening": 1.4,  # テック系は夕方以降に人気
                "night": 1.0,
            },
            "general": {"morning": 1.2, "afternoon": 1.0, "evening": 1.3, "night": 0.7},
        }

        pattern = seasonal_patterns.get(category, seasonal_patterns["general"])

        if 6 <= hour <= 11:
            return pattern.get("morning", 1.0)
        elif 12 <= hour <= 17:
            return pattern.get("afternoon", 1.0)
        elif 18 <= hour <= 21:
            return pattern.get("evening", 1.0)
        else:
            return pattern.get("night", 1.0)

    def analyze_time_series_trend(self, time_series: List[Tuple[datetime, float]]) -> TrendAnalysis:
        """時系列トレンド分析"""

        if len(time_series) < 5:
            return TrendAnalysis(
                metric_name="insufficient_data",
                time_series=time_series,
                trend_direction="stable",
                trend_strength=0.0,
                seasonality_detected=False,
                forecast_values=[],
                confidence_intervals=[],
            )

        # データソート
        sorted_series = sorted(time_series, key=lambda x: x[0])
        values = [point[1] for point in sorted_series]

        # 線形トレンド計算
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        trend_slope = coeffs[0]

        # トレンド方向と強度
        if abs(trend_slope) < 0.01:
            trend_direction = "stable"
            trend_strength = 0.0
        elif trend_slope > 0:
            trend_direction = "increasing"
            trend_strength = min(1.0, abs(trend_slope) * 10)
        else:
            trend_direction = "decreasing"
            trend_strength = min(1.0, abs(trend_slope) * 10)

        # 季節性検出（簡易版）
        seasonality_detected = self._detect_seasonality(values)

        # 短期予測（線形外挿）
        forecast_values = []
        confidence_intervals = []

        for i in range(1, 8):  # 7日先まで予測
            future_date = sorted_series[-1][0] + timedelta(days=i)
            predicted_value = coeffs[1] + coeffs[0] * (len(values) + i - 1)

            # 信頼区間（簡易版）
            std_error = np.std(values) * 0.2 * i  # 時間経過で拡大
            lower_bound = max(0.0, predicted_value - std_error)
            upper_bound = min(1.0, predicted_value + std_error)

            forecast_values.append((future_date, predicted_value))
            confidence_intervals.append((future_date, lower_bound, upper_bound))

        return TrendAnalysis(
            metric_name="trend_analysis",
            time_series=sorted_series,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            seasonality_detected=seasonality_detected,
            forecast_values=forecast_values,
            confidence_intervals=confidence_intervals,
        )

    def _detect_seasonality(self, values: List[float]) -> bool:
        """季節性検出（簡易版）"""
        if len(values) < 14:  # 最低2週間のデータが必要
            return False

        # 週単位のパターン検出
        weekly_patterns = []
        for i in range(0, len(values) - 7, 7):
            weekly_patterns.append(values[i : i + 7])

        if len(weekly_patterns) < 2:
            return False

        # 週間パターンの一致度計算
        correlation_sum = 0
        comparison_count = 0

        for i in range(len(weekly_patterns) - 1):
            correlation = np.corrcoef(weekly_patterns[i], weekly_patterns[i + 1])[0, 1]
            if not np.isnan(correlation):
                correlation_sum += abs(correlation)
                comparison_count += 1

        if comparison_count == 0:
            return False

        avg_correlation = correlation_sum / comparison_count
        return avg_correlation > 0.5  # 50%以上の相関で季節性ありと判定

    def save_prediction(self, prediction: PredictionResult):
        """予測結果保存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO predictions 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    prediction.prediction_id,
                    prediction.user_id,
                    prediction.prediction_type.value,
                    prediction.predicted_value,
                    prediction.confidence_level,
                    prediction.prediction_date.isoformat(),
                    prediction.valid_until.isoformat(),
                    json.dumps(prediction.contributing_factors),
                    prediction.model_version,
                    None,  # actual_value
                    False,  # is_validated
                ),
            )

    def get_user_predictions(self, user_id: str) -> List[PredictionResult]:
        """ユーザーの予測結果取得"""
        predictions = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM predictions 
                WHERE user_id = ? AND valid_until > ?
                ORDER BY prediction_date DESC
            """,
                (user_id, datetime.now().isoformat()),
            )

            for row in cursor.fetchall():
                predictions.append(
                    PredictionResult(
                        prediction_id=row[0],
                        user_id=row[1],
                        prediction_type=PredictionType(row[2]),
                        predicted_value=row[3],
                        confidence_level=row[4],
                        prediction_date=datetime.fromisoformat(row[5]),
                        valid_until=datetime.fromisoformat(row[6]),
                        contributing_factors=json.loads(row[7]),
                        model_version=row[8],
                    )
                )

        return predictions

    def validate_prediction(self, prediction_id: str, actual_value: float):
        """予測結果の検証"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE predictions 
                SET actual_value = ?, is_validated = 1
                WHERE prediction_id = ?
            """,
                (actual_value, prediction_id),
            )

        self.logger.info(f"Validated prediction {prediction_id} with actual value {actual_value}")

    def calculate_model_performance(self, model_version: str) -> Optional[ModelMetrics]:
        """モデル性能計算"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT predicted_value, actual_value FROM predictions 
                WHERE model_version = ? AND is_validated = 1
            """,
                (model_version,),
            )

            validated_predictions = cursor.fetchall()

        if not validated_predictions:
            return None

        predicted_values = [row[0] for row in validated_predictions]
        actual_values = [row[1] for row in validated_predictions]

        # MAE計算
        mae = np.mean([abs(p - a) for p, a in zip(predicted_values, actual_values)])

        # RMSE計算
        rmse = np.sqrt(np.mean([(p - a) ** 2 for p, a in zip(predicted_values, actual_values)]))

        # バイナリ分類指標（0.5を閾値として）
        pred_binary = [1 if p > 0.5 else 0 for p in predicted_values]
        actual_binary = [1 if a > 0.5 else 0 for a in actual_values]

        # 混同行列
        tp = sum(1 for p, a in zip(pred_binary, actual_binary) if p == 1 and a == 1)
        tn = sum(1 for p, a in zip(pred_binary, actual_binary) if p == 0 and a == 0)
        fp = sum(1 for p, a in zip(pred_binary, actual_binary) if p == 1 and a == 0)
        fn = sum(1 for p, a in zip(pred_binary, actual_binary) if p == 0 and a == 1)

        # 指標計算
        accuracy = (tp + tn) / len(predicted_values) if len(predicted_values) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return ModelMetrics(
            model_name=model_version,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            mae=mae,
            rmse=rmse,
            last_updated=datetime.now(),
        )


if __name__ == "__main__":
    # テスト実行
    analytics = PredictiveAnalytics()

    # テストユーザーデータ
    test_interactions = [
        {
            "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
            "action_type": "view",
            "session_duration": 240,
            "categories": ["technology"],
        },
        {
            "timestamp": (datetime.now() - timedelta(days=2)).isoformat(),
            "action_type": "share",
            "session_duration": 180,
            "categories": ["finance"],
        },
    ]

    # エンゲージメント予測
    engagement_prediction = analytics.predict_user_engagement("test_user_001", test_interactions)
    print("Engagement Prediction:")
    print(json.dumps(asdict(engagement_prediction), indent=2, ensure_ascii=False, default=str))

    # チャーン予測
    churn_prediction = analytics.predict_churn_risk("test_user_001", test_interactions)
    print("\nChurn Risk Prediction:")
    print(json.dumps(asdict(churn_prediction), indent=2, ensure_ascii=False, default=str))

    # 予測保存
    analytics.save_prediction(engagement_prediction)
    analytics.save_prediction(churn_prediction)
