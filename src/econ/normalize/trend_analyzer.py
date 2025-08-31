"""
Trend analysis module for economic indicators.

経済指標のトレンド分析、パターン認識、異常検知を行う。
統計的手法と機械学習アプローチを組み合わせて分析する。
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import find_peaks, savgol_filter
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class TrendType(Enum):
    """トレンドタイプ"""
    BULL = "強気"  # 強い上昇トレンド
    BEAR = "弱気"  # 強い下降トレンド
    SIDEWAYS = "横ばい"  # 横ばいトレンド
    VOLATILE = "変動激しい"  # 高ボラティリティ
    CYCLE = "循環的"  # 循環パターン
    BREAKOUT = "ブレイクアウト"  # レンジブレイク
    REVERSAL = "反転"  # トレンド反転


class PatternType(Enum):
    """パターンタイプ"""
    HEAD_SHOULDERS = "三尊"
    DOUBLE_TOP = "ダブルトップ"
    DOUBLE_BOTTOM = "ダブルボトム"
    TRIANGLE = "三角持ち合い"
    CHANNEL = "チャネル"
    SUPPORT_RESISTANCE = "サポート・レジスタンス"
    NONE = "パターンなし"


@dataclass
class TrendResult:
    """トレンド分析結果"""
    # 基本トレンド情報
    trend_type: TrendType
    trend_strength: float  # 0-100
    trend_duration_days: int
    confidence_level: float  # 0-100
    
    # 統計的指標
    slope: float
    r_squared: float
    volatility: float
    momentum: float
    
    # パターン認識
    pattern_type: PatternType
    pattern_confidence: float
    
    # サポート・レジスタンスレベル
    support_levels: List[float]
    resistance_levels: List[float]
    
    # 予測・示唆
    next_direction_probability: Dict[str, float]  # {"up": 0.6, "down": 0.2, "sideways": 0.2}
    key_levels_to_watch: List[float]
    
    # 異常値・特異点
    anomalies: List[Dict[str, Any]]
    
    # 分析メタデータ
    analysis_date: datetime
    data_period: Tuple[datetime, datetime]
    data_points: int


class TrendAnalyzer:
    """トレンド分析エンジン"""
    
    def __init__(self):
        self.min_data_points = 10
        self.volatility_window = 20
        self.trend_window = 30
    
    def analyze_trend(
        self, 
        data: pd.Series, 
        include_patterns: bool = True,
        include_forecasting: bool = True
    ) -> Optional[TrendResult]:
        """包括的なトレンド分析を実行"""
        if len(data) < self.min_data_points:
            logger.warning(f"Insufficient data points: {len(data)} < {self.min_data_points}")
            return None
        
        try:
            # データの前処理
            clean_data = self._preprocess_data(data)
            
            # 基本トレンド分析
            trend_info = self._analyze_basic_trend(clean_data)
            
            # ボラティリティ分析
            volatility = self._calculate_volatility(clean_data)
            
            # モメンタム分析
            momentum = self._calculate_momentum(clean_data)
            
            # パターン認識
            pattern_info = (
                self._recognize_patterns(clean_data) 
                if include_patterns 
                else (PatternType.NONE, 0.0)
            )
            
            # サポート・レジスタンス検出
            support_resistance = self._find_support_resistance(clean_data)
            
            # 異常値検出
            anomalies = self._detect_anomalies(clean_data)
            
            # 予測分析
            prediction = (
                self._predict_direction(clean_data) 
                if include_forecasting 
                else {"up": 0.33, "down": 0.33, "sideways": 0.34}
            )
            
            # 結果を統合
            result = TrendResult(
                trend_type=trend_info['type'],
                trend_strength=trend_info['strength'],
                trend_duration_days=trend_info['duration'],
                confidence_level=trend_info['confidence'],
                slope=trend_info['slope'],
                r_squared=trend_info['r_squared'],
                volatility=volatility,
                momentum=momentum,
                pattern_type=pattern_info[0],
                pattern_confidence=pattern_info[1],
                support_levels=support_resistance['support'],
                resistance_levels=support_resistance['resistance'],
                next_direction_probability=prediction,
                key_levels_to_watch=self._identify_key_levels(clean_data, support_resistance),
                anomalies=anomalies,
                analysis_date=datetime.now(),
                data_period=(data.index[0], data.index[-1]),
                data_points=len(clean_data)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze trend: {e}")
            return None
    
    def _preprocess_data(self, data: pd.Series) -> pd.Series:
        """データの前処理"""
        # NaN値の処理
        clean_data = data.dropna()
        
        # 異常値のスムージング（3σルール）
        mean_val = clean_data.mean()
        std_val = clean_data.std()
        threshold = 3 * std_val
        
        # 異常値をクリップ
        clean_data = clean_data.clip(
            lower=mean_val - threshold,
            upper=mean_val + threshold
        )
        
        return clean_data
    
    def _analyze_basic_trend(self, data: pd.Series) -> Dict[str, Any]:
        """基本トレンド分析"""
        x = np.arange(len(data))
        y = data.values
        
        # 線形回帰
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2
        
        # トレンドタイプの判定
        data_std = np.std(y)
        slope_threshold = data_std * 0.1 / len(data)  # 正規化された閾値
        
        if r_squared < 0.3:
            trend_type = TrendType.VOLATILE
        elif abs(slope) < slope_threshold:
            trend_type = TrendType.SIDEWAYS
        elif slope > slope_threshold:
            if slope > slope_threshold * 2:
                trend_type = TrendType.BULL
            else:
                trend_type = TrendType.BULL
        else:
            if slope < -slope_threshold * 2:
                trend_type = TrendType.BEAR
            else:
                trend_type = TrendType.BEAR
        
        # トレンド強度（0-100）
        strength = min(r_squared * 100, 100)
        
        # 信頼度（統計的有意性）
        confidence = (1 - p_value) * 100 if p_value < 1 else 0
        
        # トレンド継続期間（概算）
        duration = len(data)  # データポイント数を日数として近似
        
        return {
            'type': trend_type,
            'strength': strength,
            'confidence': confidence,
            'duration': duration,
            'slope': slope,
            'r_squared': r_squared
        }
    
    def _calculate_volatility(self, data: pd.Series) -> float:
        """ボラティリティを計算"""
        if len(data) < 2:
            return 0.0
        
        # リターン計算
        returns = data.pct_change().dropna()
        
        if len(returns) == 0:
            return 0.0
        
        # 年率ボラティリティ（仮に月次データとして計算）
        volatility = returns.std() * np.sqrt(12) * 100
        
        return min(volatility, 100.0)  # 上限100%
    
    def _calculate_momentum(self, data: pd.Series) -> float:
        """モメンタムを計算"""
        if len(data) < 6:
            return 0.0
        
        # 短期・長期移動平均
        short_ma = data.rolling(window=3).mean()
        long_ma = data.rolling(window=6).mean()
        
        # モメンタム = (短期MA - 長期MA) / 長期MA * 100
        momentum_series = ((short_ma - long_ma) / long_ma * 100).dropna()
        
        return momentum_series.iloc[-1] if len(momentum_series) > 0 else 0.0
    
    def _recognize_patterns(self, data: pd.Series) -> Tuple[PatternType, float]:
        """チャートパターンを認識"""
        if len(data) < 10:
            return PatternType.NONE, 0.0
        
        try:
            # スムージング
            smoothed = savgol_filter(data.values, window_length=min(5, len(data)//2*2-1), polyorder=2)
            
            # ピークと谷を検出
            peaks, _ = find_peaks(smoothed, distance=len(data)//5)
            valleys, _ = find_peaks(-smoothed, distance=len(data)//5)
            
            # パターン分類
            if len(peaks) >= 2 and len(valleys) >= 1:
                # ダブルトップパターンの検出
                if self._is_double_top(smoothed, peaks, valleys):
                    return PatternType.DOUBLE_TOP, 0.7
                
                # ダブルボトムパターンの検出  
                if self._is_double_bottom(smoothed, peaks, valleys):
                    return PatternType.DOUBLE_BOTTOM, 0.7
            
            if len(peaks) >= 1 and len(valleys) >= 2:
                # 三尊パターンの検出
                if self._is_head_shoulders(smoothed, peaks, valleys):
                    return PatternType.HEAD_SHOULDERS, 0.8
            
            # チャネル・三角持ち合いパターン
            if self._is_channel_pattern(data):
                return PatternType.CHANNEL, 0.6
            
            return PatternType.NONE, 0.0
            
        except Exception as e:
            logger.error(f"Pattern recognition failed: {e}")
            return PatternType.NONE, 0.0
    
    def _is_double_top(self, data: np.ndarray, peaks: np.ndarray, valleys: np.ndarray) -> bool:
        """ダブルトップパターンの判定"""
        if len(peaks) < 2:
            return False
        
        # 最後の2つのピークを評価
        peak1, peak2 = peaks[-2:]
        peak1_val, peak2_val = data[peak1], data[peak2]
        
        # ピークの高さが類似しているか
        height_diff = abs(peak1_val - peak2_val) / max(peak1_val, peak2_val)
        
        return height_diff < 0.05  # 5%以内の差
    
    def _is_double_bottom(self, data: np.ndarray, peaks: np.ndarray, valleys: np.ndarray) -> bool:
        """ダブルボトムパターンの判定"""
        if len(valleys) < 2:
            return False
        
        # 最後の2つの谷を評価
        valley1, valley2 = valleys[-2:]
        valley1_val, valley2_val = data[valley1], data[valley2]
        
        # 谷の深さが類似しているか
        depth_diff = abs(valley1_val - valley2_val) / min(valley1_val, valley2_val)
        
        return depth_diff < 0.05  # 5%以内の差
    
    def _is_head_shoulders(self, data: np.ndarray, peaks: np.ndarray, valleys: np.ndarray) -> bool:
        """三尊パターンの判定"""
        if len(peaks) < 3 or len(valleys) < 2:
            return False
        
        # 最後の3つのピークを評価（左肩、頭、右肩）
        left_shoulder, head, right_shoulder = peaks[-3:]
        
        left_val = data[left_shoulder]
        head_val = data[head]
        right_val = data[right_shoulder]
        
        # 頭が両肩より高く、両肩の高さが類似
        head_higher = head_val > left_val and head_val > right_val
        shoulders_similar = abs(left_val - right_val) / max(left_val, right_val) < 0.1
        
        return head_higher and shoulders_similar
    
    def _is_channel_pattern(self, data: pd.Series) -> bool:
        """チャネルパターンの判定"""
        if len(data) < 20:
            return False
        
        # 上下のトレンドライン傾きが類似しているか
        upper_envelope = data.rolling(window=5).max()
        lower_envelope = data.rolling(window=5).min()
        
        # 各エンベロープの傾きを計算
        x = np.arange(len(data))
        upper_slope = np.polyfit(x, upper_envelope.fillna(method='ffill'), 1)[0]
        lower_slope = np.polyfit(x, lower_envelope.fillna(method='ffill'), 1)[0]
        
        # 傾きが類似している場合はチャネル
        slope_diff = abs(upper_slope - lower_slope)
        avg_slope = abs((upper_slope + lower_slope) / 2)
        
        return slope_diff / (avg_slope + 1e-6) < 0.3  # 30%以内の差
    
    def _find_support_resistance(self, data: pd.Series) -> Dict[str, List[float]]:
        """サポート・レジスタンスレベルを検出"""
        try:
            # 価格レベルのヒストグラム作成
            bins = 20
            hist, bin_edges = np.histogram(data.values, bins=bins)
            
            # 出現頻度が高いレベルを特定
            threshold = np.percentile(hist, 70)  # 上位30%
            significant_levels = []
            
            for i, count in enumerate(hist):
                if count >= threshold:
                    level = (bin_edges[i] + bin_edges[i+1]) / 2
                    significant_levels.append(level)
            
            # 現在価格を基準にサポート/レジスタンスを分類
            current_price = data.iloc[-1]
            
            support = [level for level in significant_levels if level < current_price]
            resistance = [level for level in significant_levels if level > current_price]
            
            # 上位3つまでに制限
            support = sorted(support, reverse=True)[:3]
            resistance = sorted(resistance)[:3]
            
            return {'support': support, 'resistance': resistance}
            
        except Exception as e:
            logger.error(f"Support/resistance detection failed: {e}")
            return {'support': [], 'resistance': []}
    
    def _detect_anomalies(self, data: pd.Series) -> List[Dict[str, Any]]:
        """異常値を検出"""
        anomalies = []
        
        try:
            # Z-scoreベースの異常値検出
            z_scores = np.abs(stats.zscore(data.values))
            threshold = 2.5
            
            anomaly_indices = np.where(z_scores > threshold)[0]
            
            for idx in anomaly_indices:
                date = data.index[idx]
                value = data.iloc[idx]
                z_score = z_scores[idx]
                
                anomalies.append({
                    'date': date,
                    'value': value,
                    'z_score': z_score,
                    'type': 'statistical_outlier'
                })
            
            # 急激な変化の検出
            pct_changes = data.pct_change().abs()
            change_threshold = pct_changes.quantile(0.95)  # 上位5%
            
            sudden_changes = pct_changes[pct_changes > change_threshold]
            
            for date, change in sudden_changes.items():
                anomalies.append({
                    'date': date,
                    'value': data[date],
                    'change_rate': change,
                    'type': 'sudden_change'
                })
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
        
        return anomalies[:10]  # 上位10個まで
    
    def _predict_direction(self, data: pd.Series) -> Dict[str, float]:
        """方向性を予測"""
        try:
            # 複数の指標を組み合わせて予測
            predictions = []
            
            # 1. トレンド継続予測
            recent_slope = self._calculate_recent_slope(data, window=5)
            if abs(recent_slope) > data.std() * 0.05:
                trend_prediction = {
                    "up": 0.7 if recent_slope > 0 else 0.2,
                    "down": 0.2 if recent_slope > 0 else 0.7,
                    "sideways": 0.1
                }
                predictions.append(trend_prediction)
            
            # 2. 移動平均クロス予測
            if len(data) >= 10:
                short_ma = data.rolling(3).mean().iloc[-1]
                long_ma = data.rolling(6).mean().iloc[-1]
                current = data.iloc[-1]
                
                ma_prediction = {
                    "up": 0.6 if short_ma > long_ma and current > short_ma else 0.3,
                    "down": 0.6 if short_ma < long_ma and current < short_ma else 0.3,
                    "sideways": 0.1 if abs(short_ma - long_ma) / long_ma < 0.01 else 0.4
                }
                predictions.append(ma_prediction)
            
            # 3. リバーション予測（平均回帰）
            current = data.iloc[-1]
            mean_val = data.mean()
            std_val = data.std()
            
            if abs(current - mean_val) > std_val:
                reversion_prediction = {
                    "up": 0.3 if current < mean_val else 0.6,
                    "down": 0.6 if current < mean_val else 0.3,
                    "sideways": 0.1
                }
                predictions.append(reversion_prediction)
            
            # 予測の平均を取る
            if predictions:
                avg_prediction = {}
                for direction in ["up", "down", "sideways"]:
                    avg_prediction[direction] = sum(p[direction] for p in predictions) / len(predictions)
                
                # 正規化（合計を1に）
                total = sum(avg_prediction.values())
                return {k: v/total for k, v in avg_prediction.items()}
            
            # デフォルト予測（均等分布）
            return {"up": 0.33, "down": 0.33, "sideways": 0.34}
            
        except Exception as e:
            logger.error(f"Direction prediction failed: {e}")
            return {"up": 0.33, "down": 0.33, "sideways": 0.34}
    
    def _calculate_recent_slope(self, data: pd.Series, window: int = 5) -> float:
        """直近期間の傾きを計算"""
        if len(data) < window:
            return 0.0
        
        recent_data = data.tail(window)
        x = np.arange(len(recent_data))
        y = recent_data.values
        
        slope, _ = np.polyfit(x, y, 1)
        return slope
    
    def _identify_key_levels(self, data: pd.Series, support_resistance: Dict[str, List[float]]) -> List[float]:
        """重要価格レベルを特定"""
        levels = []
        
        # サポート・レジスタンスレベル
        levels.extend(support_resistance['support'])
        levels.extend(support_resistance['resistance'])
        
        # 過去の重要高値・安値
        if len(data) >= 20:
            recent_high = data.tail(20).max()
            recent_low = data.tail(20).min()
            levels.extend([recent_high, recent_low])
        
        # 移動平均レベル
        if len(data) >= 20:
            ma20 = data.rolling(20).mean().iloc[-1]
            levels.append(ma20)
        
        # 重複除去と現在価格に近い順でソート
        current_price = data.iloc[-1]
        unique_levels = list(set([round(level, 4) for level in levels if not np.isnan(level)]))
        unique_levels.sort(key=lambda x: abs(x - current_price))
        
        return unique_levels[:5]  # 上位5つ