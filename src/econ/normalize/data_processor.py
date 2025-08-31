"""
Economic data processing and normalization module.

経済指標データの正規化、単位統一、トレンド計算を行う。
複数のデータソースから取得したデータを統一フォーマットで処理する。
"""

from typing import List, Dict, Optional, Union, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import logging
from enum import Enum

from ..adapters.investpy_calendar import EconomicEvent

logger = logging.getLogger(__name__)


class DataFrequency(Enum):
    """データ頻度"""
    DAILY = "daily"
    WEEKLY = "weekly" 
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class TrendDirection(Enum):
    """トレンド方向"""
    UP = "上昇"
    DOWN = "下降" 
    FLAT = "横ばい"
    VOLATILE = "不安定"
    UNKNOWN = "不明"


@dataclass
class ProcessedIndicator:
    """処理済み経済指標データ"""
    original_event: EconomicEvent
    
    # 正規化されたデータ
    normalized_value: Optional[float] = None
    unit_standardized: Optional[str] = None
    
    # 履歴データ
    historical_data: Optional[pd.Series] = None
    frequency: Optional[DataFrequency] = None
    
    # 計算済み指標
    mom_change: Optional[float] = None  # Month-over-Month
    yoy_change: Optional[float] = None  # Year-over-Year
    qoq_change: Optional[float] = None  # Quarter-over-Quarter
    
    # トレンド分析
    trend_direction: Optional[TrendDirection] = None
    trend_strength: Optional[float] = None  # 0-100
    volatility_index: Optional[float] = None
    
    # 統計情報
    historical_mean: Optional[float] = None
    historical_std: Optional[float] = None
    z_score: Optional[float] = None
    percentile_rank: Optional[float] = None
    
    # メタデータ
    data_quality_score: float = 0.0  # 0-100
    processing_timestamp: datetime = field(default_factory=datetime.now)
    data_sources: List[str] = field(default_factory=list)


class EconomicDataProcessor:
    """経済データ処理エンジン"""
    
    def __init__(self):
        self.unit_conversions = self._initialize_unit_conversions()
        self.indicator_categories = self._initialize_categories()
    
    def process_event(
        self, 
        event: EconomicEvent,
        historical_data: Optional[pd.Series] = None,
        enhance_with_calculations: bool = True
    ) -> ProcessedIndicator:
        """経済指標イベントを処理・正規化"""
        processed = ProcessedIndicator(original_event=event)
        
        try:
            # 基本正規化
            processed.normalized_value = self._normalize_value(event.actual, getattr(event, 'unit', None))
            processed.unit_standardized = self._standardize_unit(getattr(event, 'unit', None))
            
            # 履歴データの処理
            if historical_data is not None:
                processed.historical_data = historical_data
                processed.frequency = self._detect_frequency(historical_data)
                
                if enhance_with_calculations:
                    self._calculate_change_rates(processed)
                    self._analyze_trend(processed)
                    self._calculate_statistics(processed)
            
            # データ品質評価
            processed.data_quality_score = self._assess_data_quality(processed)
            
            # データソース記録
            processed.data_sources = [event.source]
            
            indicator_name = getattr(event, 'indicator', None) or getattr(event, 'title', 'Unknown')
            logger.debug(f"Processed indicator: {indicator_name}")
            
        except Exception as e:
            indicator_name = getattr(event, 'indicator', None) or getattr(event, 'title', 'Unknown')
            logger.error(f"Failed to process event {indicator_name}: {e}")
            processed.data_quality_score = 0.0
        
        return processed
    
    def _normalize_value(self, value: Optional[float], unit: Optional[str]) -> Optional[float]:
        """値を正規化"""
        if value is None:
            return None
        
        try:
            # 単位変換
            if unit and unit in self.unit_conversions:
                conversion_factor = self.unit_conversions[unit]
                return value * conversion_factor
            
            return value
            
        except Exception as e:
            logger.error(f"Failed to normalize value {value} with unit {unit}: {e}")
            return value
    
    def _standardize_unit(self, unit: Optional[str]) -> Optional[str]:
        """単位を標準化"""
        if not unit:
            return None
        
        # 単位の標準化マッピング
        unit_mapping = {
            '%': 'percent',
            'pct': 'percent', 
            'percentage': 'percent',
            'k': 'thousands',
            'thousand': 'thousands',
            'm': 'millions',
            'million': 'millions',
            'b': 'billions',
            'billion': 'billions',
            'index': 'index_value',
            'ratio': 'ratio',
            'rate': 'rate'
        }
        
        unit_lower = unit.lower().strip()
        return unit_mapping.get(unit_lower, unit_lower)
    
    def _detect_frequency(self, data: pd.Series) -> DataFrequency:
        """データ頻度を自動検出"""
        if len(data) < 2:
            return DataFrequency.UNKNOWN
        
        # インデックス間隔を計算
        time_diffs = data.index.to_series().diff().dropna()
        median_diff = time_diffs.median()
        
        if median_diff <= timedelta(days=2):
            return DataFrequency.DAILY
        elif median_diff <= timedelta(days=8):
            return DataFrequency.WEEKLY
        elif median_diff <= timedelta(days=35):
            return DataFrequency.MONTHLY
        elif median_diff <= timedelta(days=100):
            return DataFrequency.QUARTERLY
        else:
            return DataFrequency.YEARLY
    
    def _calculate_change_rates(self, processed: ProcessedIndicator):
        """変化率を計算"""
        data = processed.historical_data
        if data is None or len(data) < 2:
            return
        
        try:
            latest_value = data.iloc[-1]
            
            # Month-over-Month
            if len(data) >= 2:
                mom_value = data.iloc[-2] if len(data) > 1 else None
                if mom_value is not None and mom_value != 0:
                    processed.mom_change = ((latest_value - mom_value) / mom_value) * 100
            
            # Year-over-Year（12ヶ月前比）
            if len(data) >= 12:
                yoy_value = data.iloc[-12]
                if yoy_value != 0:
                    processed.yoy_change = ((latest_value - yoy_value) / yoy_value) * 100
            
            # Quarter-over-Quarter（3ヶ月前比）
            if len(data) >= 3:
                qoq_value = data.iloc[-3]
                if qoq_value != 0:
                    processed.qoq_change = ((latest_value - qoq_value) / qoq_value) * 100
        
        except Exception as e:
            logger.error(f"Failed to calculate change rates: {e}")
    
    def _analyze_trend(self, processed: ProcessedIndicator):
        """トレンド分析"""
        data = processed.historical_data
        if data is None or len(data) < 6:
            processed.trend_direction = TrendDirection.UNKNOWN
            return
        
        try:
            # 直近6ポイントでトレンド計算
            recent_data = data.tail(6)
            x = np.arange(len(recent_data))
            y = recent_data.values
            
            # 線形回帰で傾きを計算
            slope, intercept = np.polyfit(x, y, 1)
            
            # R²値でトレンドの強度を評価
            y_pred = slope * x + intercept
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            # トレンド方向の判定
            slope_threshold = np.std(y) * 0.1  # 標準偏差の10%を閾値とする
            
            if abs(slope) < slope_threshold or r_squared < 0.3:
                processed.trend_direction = TrendDirection.FLAT
            elif slope > slope_threshold:
                processed.trend_direction = TrendDirection.UP
            elif slope < -slope_threshold:
                processed.trend_direction = TrendDirection.DOWN
            else:
                processed.trend_direction = TrendDirection.VOLATILE
            
            # トレンド強度（0-100）
            processed.trend_strength = min(r_squared * 100, 100)
            
            # ボラティリティ指数
            returns = data.pct_change().dropna()
            if len(returns) > 0:
                processed.volatility_index = returns.std() * 100
        
        except Exception as e:
            logger.error(f"Failed to analyze trend: {e}")
            processed.trend_direction = TrendDirection.UNKNOWN
    
    def _calculate_statistics(self, processed: ProcessedIndicator):
        """統計指標を計算"""
        data = processed.historical_data
        if data is None or len(data) < 2:
            return
        
        try:
            # 基本統計
            processed.historical_mean = data.mean()
            processed.historical_std = data.std()
            
            # 最新値のZ-score
            latest_value = data.iloc[-1]
            if processed.historical_std > 0:
                processed.z_score = (latest_value - processed.historical_mean) / processed.historical_std
            
            # パーセンタイル順位
            processed.percentile_rank = (data <= latest_value).mean() * 100
        
        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")
    
    def _assess_data_quality(self, processed: ProcessedIndicator) -> float:
        """データ品質を評価（0-100）"""
        score = 0.0
        
        try:
            # 基本データの存在チェック
            if processed.original_event.actual is not None:
                score += 20
            
            if processed.original_event.forecast is not None:
                score += 15
                
            if processed.original_event.previous is not None:
                score += 10
            
            # 履歴データの評価
            if processed.historical_data is not None:
                data = processed.historical_data
                score += 20
                
                # データ完全性
                completeness = 1 - (data.isna().sum() / len(data))
                score += completeness * 20
                
                # データ期間の長さ
                if len(data) >= 12:  # 1年以上
                    score += 15
                elif len(data) >= 6:  # 6ヶ月以上
                    score += 10
                elif len(data) >= 3:  # 3ヶ月以上
                    score += 5
        
        except Exception as e:
            logger.error(f"Failed to assess data quality: {e}")
            
        return min(score, 100.0)
    
    def _initialize_unit_conversions(self) -> Dict[str, float]:
        """単位変換係数を初期化"""
        return {
            # パーセント系
            'bps': 0.01,  # basis points to percent
            'bp': 0.01,
            
            # 数値系（千、百万、十億）
            'k': 1000,
            'thousand': 1000,
            'm': 1000000,
            'million': 1000000,
            'b': 1000000000,
            'billion': 1000000000,
        }
    
    def _initialize_categories(self) -> Dict[str, List[str]]:
        """指標カテゴリを初期化"""
        return {
            'inflation': ['cpi', 'ppi', 'pce', 'hicp', 'inflation'],
            'employment': ['unemployment', 'nonfarm', 'payroll', 'jobless', 'claims'],
            'growth': ['gdp', 'industrial production', 'retail sales'],
            'monetary': ['interest rate', 'fed funds', 'ecb rate', 'bank rate'],
            'confidence': ['consumer confidence', 'business confidence', 'sentiment']
        }
    
    def get_indicator_category(self, indicator_name: str) -> Optional[str]:
        """指標のカテゴリを取得"""
        indicator_lower = indicator_name.lower()
        
        for category, keywords in self.indicator_categories.items():
            for keyword in keywords:
                if keyword in indicator_lower:
                    return category
        
        return None
    
    def process_multiple_events(
        self, 
        events: List[EconomicEvent],
        historical_data_map: Optional[Dict[str, pd.Series]] = None
    ) -> List[ProcessedIndicator]:
        """複数のイベントを一括処理"""
        processed_indicators = []
        
        for event in events:
            # 履歴データの取得
            historical_data = None
            indicator_name = getattr(event, 'indicator', None) or getattr(event, 'title', None)
            if historical_data_map and indicator_name and indicator_name in historical_data_map:
                historical_data = historical_data_map[indicator_name]
            
            processed = self.process_event(event, historical_data)
            processed_indicators.append(processed)
        
        return processed_indicators
    
    def generate_summary_stats(self, processed_indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """処理済み指標の統計サマリーを生成"""
        if not processed_indicators:
            return {}
        
        try:
            # 基本統計
            total_indicators = len(processed_indicators)
            with_historical = sum(1 for p in processed_indicators if p.historical_data is not None)
            avg_quality_score = sum(p.data_quality_score for p in processed_indicators) / total_indicators
            
            # トレンド分布
            trend_counts = {}
            for p in processed_indicators:
                if p.trend_direction:
                    trend = p.trend_direction.value
                    trend_counts[trend] = trend_counts.get(trend, 0) + 1
            
            # 変化率統計
            mom_changes = [p.mom_change for p in processed_indicators if p.mom_change is not None]
            yoy_changes = [p.yoy_change for p in processed_indicators if p.yoy_change is not None]
            
            return {
                'total_indicators': total_indicators,
                'indicators_with_historical': with_historical,
                'average_quality_score': round(avg_quality_score, 1),
                'trend_distribution': trend_counts,
                'change_rates': {
                    'mom_count': len(mom_changes),
                    'mom_avg': round(np.mean(mom_changes), 2) if mom_changes else None,
                    'yoy_count': len(yoy_changes), 
                    'yoy_avg': round(np.mean(yoy_changes), 2) if yoy_changes else None
                },
                'processing_timestamp': datetime.now()
            }
        
        except Exception as e:
            logger.error(f"Failed to generate summary stats: {e}")
            return {'error': str(e)}