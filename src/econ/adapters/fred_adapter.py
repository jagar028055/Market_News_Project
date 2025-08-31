"""
FRED (Federal Reserve Economic Data) API adapter.

米国連邦準備制度の公式経済統計データを取得するアダプター。
高品質な米国経済指標の詳細データと履歴データを提供する。
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from fredapi import Fred
import logging
from dataclasses import dataclass

from ..config import get_econ_config
from .investpy_calendar import EconomicEvent

logger = logging.getLogger(__name__)


@dataclass
class FredSeries:
    """FRED系列情報"""
    series_id: str
    title: str
    units: str
    frequency: str
    seasonal_adjustment: str
    last_updated: Optional[datetime] = None


class FredAdapter:
    """FRED APIアダプター"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.config = get_econ_config()
        
        # API key priority: parameter > config > environment
        self.api_key = (
            api_key or 
            getattr(self.config.api_keys, 'fred_api_key', None) or
            None
        )
        
        if not self.api_key:
            logger.warning("FRED API key not found. Historical data features will be limited.")
            self.fred = None
        else:
            try:
                self.fred = Fred(api_key=self.api_key)
                logger.info("FRED API adapter initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize FRED API: {e}")
                self.fred = None
    
    def is_available(self) -> bool:
        """FRED APIが利用可能かチェック"""
        return self.fred is not None
    
    def get_series_info(self, series_id: str) -> Optional[FredSeries]:
        """系列情報を取得"""
        if not self.is_available():
            return None
        
        try:
            info = self.fred.get_series_info(series_id)
            return FredSeries(
                series_id=series_id,
                title=info['title'],
                units=info['units'],
                frequency=info['frequency'],
                seasonal_adjustment=info['seasonal_adjustment'],
                last_updated=pd.to_datetime(info['last_updated']) if 'last_updated' in info else None
            )
        except Exception as e:
            logger.error(f"Failed to get series info for {series_id}: {e}")
            return None
    
    def get_series_data(
        self, 
        series_id: str, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> Optional[pd.Series]:
        """系列データを取得"""
        if not self.is_available():
            return None
        
        try:
            # デフォルトは過去1年間
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365)
            if end_date is None:
                end_date = datetime.now()
            
            data = self.fred.get_series(
                series_id, 
                start_date, 
                end_date,
                limit=limit
            )
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to get series data for {series_id}: {e}")
            return None
    
    def get_latest_value(self, series_id: str) -> Optional[Dict[str, Any]]:
        """最新値を取得"""
        if not self.is_available():
            return None
        
        try:
            # 過去30日のデータを取得して最新値を特定
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            data = self.get_series_data(series_id, start_date, end_date)
            if data is None or data.empty:
                return None
            
            # 最新の非NaN値を取得
            latest_data = data.dropna()
            if latest_data.empty:
                return None
            
            latest_date = latest_data.index[-1]
            latest_value = latest_data.iloc[-1]
            
            return {
                'date': latest_date,
                'value': latest_value,
                'series_id': series_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get latest value for {series_id}: {e}")
            return None
    
    def calculate_change_rates(
        self, 
        series_id: str, 
        periods: List[str] = None
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """変化率を計算（MoM, YoY等）"""
        if periods is None:
            periods = ['1M', '3M', '6M', '12M']  # 1ヶ月、3ヶ月、6ヶ月、12ヶ月前比
        
        if not self.is_available():
            return None
        
        try:
            # 過去13ヶ月のデータを取得（12ヶ月前比のため）
            end_date = datetime.now()
            start_date = end_date - timedelta(days=400)  # 余裕を持って400日
            
            data = self.get_series_data(series_id, start_date, end_date)
            if data is None or data.empty:
                return None
            
            data = data.dropna()
            if len(data) < 2:
                return None
            
            results = {}
            latest_value = data.iloc[-1]
            latest_date = data.index[-1]
            
            # 各期間の変化率を計算
            for period in periods:
                try:
                    if period == '1M':
                        # 1ヶ月前
                        target_date = latest_date - pd.DateOffset(months=1)
                    elif period == '3M':
                        # 3ヶ月前
                        target_date = latest_date - pd.DateOffset(months=3)
                    elif period == '6M':
                        # 6ヶ月前
                        target_date = latest_date - pd.DateOffset(months=6)
                    elif period == '12M':
                        # 12ヶ月前
                        target_date = latest_date - pd.DateOffset(months=12)
                    else:
                        continue
                    
                    # 最も近い日付のデータを取得
                    past_data = data[data.index <= target_date]
                    if past_data.empty:
                        continue
                    
                    past_value = past_data.iloc[-1]
                    past_date = past_data.index[-1]
                    
                    # 変化率計算
                    if past_value != 0:
                        change_rate = ((latest_value - past_value) / past_value) * 100
                        absolute_change = latest_value - past_value
                        
                        results[period] = {
                            'change_rate_pct': round(change_rate, 2),
                            'absolute_change': round(absolute_change, 4),
                            'current_value': round(latest_value, 4),
                            'past_value': round(past_value, 4),
                            'past_date': past_date.strftime('%Y-%m-%d')
                        }
                
                except Exception as e:
                    logger.error(f"Failed to calculate {period} change for {series_id}: {e}")
                    continue
            
            return results if results else None
            
        except Exception as e:
            logger.error(f"Failed to calculate change rates for {series_id}: {e}")
            return None
    
    def get_indicator_trend(
        self, 
        series_id: str, 
        window_size: int = 12
    ) -> Optional[Dict[str, Any]]:
        """指標のトレンド分析"""
        if not self.is_available():
            return None
        
        try:
            # 過去2年のデータを取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)
            
            data = self.get_series_data(series_id, start_date, end_date)
            if data is None or data.empty:
                return None
            
            data = data.dropna()
            if len(data) < window_size:
                return None
            
            # 移動平均計算
            rolling_mean = data.rolling(window=window_size).mean()
            
            # トレンド判定（直近の傾き）
            recent_data = rolling_mean.tail(6)  # 直近6ポイント
            if len(recent_data) >= 2:
                # 線形回帰で傾きを計算
                x = np.arange(len(recent_data))
                y = recent_data.values
                slope = np.polyfit(x, y, 1)[0]
                
                # トレンド判定
                if slope > 0.01:
                    trend = "上昇"
                elif slope < -0.01:
                    trend = "下降"
                else:
                    trend = "横ばい"
            else:
                trend = "不明"
            
            # 統計情報
            latest_value = data.iloc[-1]
            mean_value = data.mean()
            std_value = data.std()
            
            # Z-score（現在値の相対位置）
            z_score = (latest_value - mean_value) / std_value if std_value > 0 else 0
            
            return {
                'trend': trend,
                'slope': round(slope, 6) if 'slope' in locals() else None,
                'latest_value': round(latest_value, 4),
                'period_mean': round(mean_value, 4),
                'period_std': round(std_value, 4),
                'z_score': round(z_score, 2),
                'relative_position': self._interpret_z_score(z_score),
                'data_points': len(data)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze trend for {series_id}: {e}")
            return None
    
    def _interpret_z_score(self, z_score: float) -> str:
        """Z-scoreの解釈"""
        if z_score > 2:
            return "非常に高い"
        elif z_score > 1:
            return "高い"
        elif z_score > -1:
            return "平均的"
        elif z_score > -2:
            return "低い"
        else:
            return "非常に低い"
    
    def enrich_economic_event(self, event: EconomicEvent) -> EconomicEvent:
        """経済指標イベントにFREDデータを付加"""
        if not self.is_available() or event.country != "US":
            return event
        
        # indicator_mapping.jsonから対応するFRED系列IDを取得
        mapping = self.config.get_indicator_mapping()
        if not mapping or "US" not in mapping:
            return event
        
        us_mapping = mapping["US"]
        
        # 指標名からFRED系列IDを特定（簡易マッチング）
        series_id = None
        indicator_lower = event.indicator.lower()
        
        for mapped_name, fred_id in us_mapping.items():
            if mapped_name.lower() in indicator_lower or indicator_lower in mapped_name.lower():
                series_id = fred_id
                break
        
        if not series_id:
            return event
        
        try:
            # FRED データで補強
            latest_data = self.get_latest_value(series_id)
            change_rates = self.calculate_change_rates(series_id)
            trend_info = self.get_indicator_trend(series_id)
            
            # イベントにFRED情報を付加
            if hasattr(event, 'fred_data'):
                event.fred_data = {
                    'series_id': series_id,
                    'latest_data': latest_data,
                    'change_rates': change_rates,
                    'trend_info': trend_info
                }
            
            return event
            
        except Exception as e:
            logger.error(f"Failed to enrich event with FRED data: {e}")
            return event
    
    def test_connection(self) -> Dict[str, Any]:
        """接続テスト"""
        if not self.is_available():
            return {
                'status': 'unavailable',
                'message': 'FRED API key not configured'
            }
        
        try:
            # 簡単なテスト：GDP系列を取得
            test_series = 'GDP'
            data = self.get_latest_value(test_series)
            
            if data is not None:
                return {
                    'status': 'success',
                    'message': f'FRED API connection successful',
                    'test_data': data
                }
            else:
                return {
                    'status': 'error',
                    'message': 'FRED API connection failed - no data received'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'FRED API connection test failed: {str(e)}'
            }