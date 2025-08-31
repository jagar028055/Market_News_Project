"""
ECB (European Central Bank) API adapter.

欧州中央銀行の公式統計データを取得するアダプター。
SDMX (Statistical Data and Metadata eXchange) 標準を使用してユーロ圏の経済指標を提供する。
"""

from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass
import requests
import xml.etree.ElementTree as ET

from ..config import get_econ_config
from .investpy_calendar import EconomicEvent

logger = logging.getLogger(__name__)


@dataclass 
class EcbSeries:
    """ECB系列情報"""
    series_key: str
    title: str
    unit: str
    frequency: str
    last_updated: Optional[datetime] = None


class EcbAdapter:
    """ECB SDMX APIアダプター"""
    
    BASE_URL = "https://sdw-wsrest.ecb.europa.eu/service"
    
    def __init__(self):
        self.config = get_econ_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'EconIndicatorsSystem/0.1.0',
            'Accept': 'application/json'
        })
        
    def is_available(self) -> bool:
        """ECB APIが利用可能かチェック"""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/datastructure",
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"ECB API availability check failed: {e}")
            return False
    
    def get_series_info(self, series_key: str) -> Optional[EcbSeries]:
        """系列情報を取得"""
        try:
            # データフロー情報から系列メタデータを取得
            url = f"{self.BASE_URL}/datastructure/ECB/ICP"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                # 簡略化された情報を返す
                return EcbSeries(
                    series_key=series_key,
                    title=f"ECB Series {series_key}",
                    unit="Various",
                    frequency="Monthly"
                )
                
        except Exception as e:
            logger.error(f"Failed to get ECB series info for {series_key}: {e}")
            
        return None
    
    def get_series_data(
        self,
        series_key: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[pd.Series]:
        """系列データを取得"""
        try:
            # 日付範囲のフォーマット
            date_filter = ""
            if start_date and end_date:
                start_str = start_date.strftime("%Y-%m")
                end_str = end_date.strftime("%Y-%m")
                date_filter = f"?startPeriod={start_str}&endPeriod={end_str}"
            
            # データ取得
            url = f"{self.BASE_URL}/data/ICP/{series_key}{date_filter}"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data_json = response.json()
                return self._parse_ecb_data(data_json, series_key)
                
        except Exception as e:
            logger.error(f"Failed to get ECB series data for {series_key}: {e}")
            
        return None
    
    def _parse_ecb_data(self, data_json: Dict, series_key: str) -> Optional[pd.Series]:
        """ECB JSONデータをpandas Seriesに変換"""
        try:
            if 'dataSets' not in data_json or not data_json['dataSets']:
                return None
                
            dataset = data_json['dataSets'][0]
            if 'series' not in dataset:
                return None
            
            # 時系列データを抽出
            series_data = dataset['series']
            if not series_data:
                return None
            
            # 構造情報から時間軸を取得
            structure = data_json.get('structure', {})
            dimensions = structure.get('dimensions', {})
            
            # 時間ディメンションを特定
            time_dimension = None
            for dim_group in dimensions.get('series', []):
                if dim_group.get('id') == 'TIME_PERIOD':
                    time_dimension = dim_group
                    break
            
            if not time_dimension:
                return None
            
            # データポイントを収集
            time_values = time_dimension.get('values', [])
            data_points = {}
            
            for series_id, series_info in series_data.items():
                observations = series_info.get('observations', {})
                
                for obs_key, obs_values in observations.items():
                    if isinstance(obs_values, list) and obs_values:
                        time_index = int(obs_key)
                        if time_index < len(time_values):
                            time_str = time_values[time_index]['id']
                            value = float(obs_values[0]) if obs_values[0] is not None else np.nan
                            
                            # 日付変換
                            try:
                                date = pd.to_datetime(time_str, format='%Y-%m')
                                data_points[date] = value
                            except:
                                continue
            
            if data_points:
                series = pd.Series(data_points)
                series.index = pd.to_datetime(series.index)
                return series.sort_index()
            
        except Exception as e:
            logger.error(f"Failed to parse ECB data: {e}")
            
        return None
    
    def get_latest_value(self, series_key: str) -> Optional[Dict[str, Any]]:
        """最新値を取得"""
        try:
            # 過去6ヶ月のデータを取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=180)
            
            data = self.get_series_data(series_key, start_date, end_date)
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
                'series_key': series_key
            }
            
        except Exception as e:
            logger.error(f"Failed to get latest ECB value for {series_key}: {e}")
            return None
    
    def calculate_change_rates(
        self,
        series_key: str,
        periods: List[str] = None
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """変化率を計算"""
        if periods is None:
            periods = ['1M', '3M', '12M']
        
        try:
            # 過去15ヶ月のデータを取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=450)
            
            data = self.get_series_data(series_key, start_date, end_date)
            if data is None or data.empty:
                return None
            
            data = data.dropna()
            if len(data) < 2:
                return None
            
            results = {}
            latest_value = data.iloc[-1]
            latest_date = data.index[-1]
            
            for period in periods:
                try:
                    if period == '1M':
                        target_date = latest_date - pd.DateOffset(months=1)
                    elif period == '3M':
                        target_date = latest_date - pd.DateOffset(months=3)
                    elif period == '12M':
                        target_date = latest_date - pd.DateOffset(months=12)
                    else:
                        continue
                    
                    # 最も近い日付のデータを取得
                    past_data = data[data.index <= target_date]
                    if past_data.empty:
                        continue
                    
                    past_value = past_data.iloc[-1]
                    past_date = past_data.index[-1]
                    
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
                    logger.error(f"Failed to calculate {period} change for ECB {series_key}: {e}")
                    continue
            
            return results if results else None
            
        except Exception as e:
            logger.error(f"Failed to calculate ECB change rates for {series_key}: {e}")
            return None
    
    def enrich_economic_event(self, event: EconomicEvent) -> EconomicEvent:
        """経済指標イベントにECBデータを付加"""
        if event.country not in ["EU", "DE", "FR", "IT", "ES"]:
            return event
        
        # indicator_mapping.jsonから対応するECB系列キーを取得
        mapping = self.config.get_indicator_mapping()
        if not mapping or "EU" not in mapping:
            return event
        
        eu_mapping = mapping["EU"]
        
        # 指標名からECB系列キーを特定
        series_key = None
        indicator_lower = event.indicator.lower()
        
        for mapped_name, series_info in eu_mapping.items():
            if isinstance(series_info, dict) and 'series_id' in series_info:
                if mapped_name.lower() in indicator_lower or indicator_lower in mapped_name.lower():
                    series_key = series_info['series_id']
                    break
        
        if not series_key:
            return event
        
        try:
            # ECBデータで補強
            latest_data = self.get_latest_value(series_key)
            change_rates = self.calculate_change_rates(series_key)
            
            # イベントにECB情報を付加
            if hasattr(event, 'ecb_data'):
                event.ecb_data = {
                    'series_key': series_key,
                    'latest_data': latest_data,
                    'change_rates': change_rates
                }
            
            return event
            
        except Exception as e:
            logger.error(f"Failed to enrich event with ECB data: {e}")
            return event
    
    def test_connection(self) -> Dict[str, Any]:
        """接続テスト"""
        try:
            # ECB API の健全性をチェック
            response = self.session.get(
                f"{self.BASE_URL}/datastructure",
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'message': 'ECB SDMX API connection successful',
                    'response_code': response.status_code
                }
            else:
                return {
                    'status': 'error',
                    'message': f'ECB API returned status code: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'ECB API connection test failed: {str(e)}'
            }