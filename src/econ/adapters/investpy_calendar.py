"""
Investpy Calendar Adapter
investpyライブラリを使用した経済カレンダーデータの取得
"""

import logging
from typing import List, Dict, Optional, Union
from datetime import datetime, date, timedelta
import pandas as pd
import pytz
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EconomicEvent:
    """経済イベントデータクラス"""
    
    id: str
    title: str
    country: str
    importance: str  # "Low", "Medium", "High"
    scheduled_time_utc: datetime
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    source: str = "investpy"
    category: Optional[str] = None
    currency: Optional[str] = None
    unit: Optional[str] = None
    
    def calculate_surprise(self) -> Optional[Dict[str, float]]:
        """サプライズ指標を計算"""
        if self.actual is None or self.forecast is None:
            return None
        
        surprise = self.actual - self.forecast
        surprise_ratio = surprise / abs(self.forecast) if self.forecast != 0 else 0
        
        return {
            "surprise": surprise,
            "surprise_ratio": surprise_ratio,
            "surprise_pct": surprise_ratio * 100
        }
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        data = {
            "id": self.id,
            "title": self.title,
            "country": self.country,
            "importance": self.importance,
            "scheduled_time_utc": self.scheduled_time_utc.isoformat(),
            "actual": self.actual,
            "forecast": self.forecast,
            "previous": self.previous,
            "source": self.source,
            "category": self.category,
            "currency": self.currency,
            "unit": self.unit
        }
        
        # サプライズ指標を追加
        surprise_data = self.calculate_surprise()
        if surprise_data:
            data.update(surprise_data)
        
        return data


class InvestpyCalendarAdapter:
    """Investpy経済カレンダーアダプター"""
    
    def __init__(self, timeout: int = 30):
        """
        Args:
            timeout: APIタイムアウト（秒）
        """
        self.timeout = timeout
        self._validate_investpy()
    
    def _validate_investpy(self):
        """investpyライブラリの利用可能性を確認"""
        try:
            import investpy
            self.investpy = investpy
            logger.info("investpy library loaded successfully")
        except ImportError:
            logger.error("investpy library not found. Please install: pip install investpy")
            raise ImportError("investpy library is required but not installed")
    
    def get_calendar_data(
        self,
        from_date: Union[str, date, datetime],
        to_date: Union[str, date, datetime],
        countries: Optional[List[str]] = None,
        importance: Optional[str] = None
    ) -> List[EconomicEvent]:
        """
        経済カレンダーデータを取得
        
        Args:
            from_date: 開始日
            to_date: 終了日
            countries: 対象国リスト（例: ['United States', 'Japan']）
            importance: 重要度フィルタ（'low', 'medium', 'high'）
            
        Returns:
            EconomicEventのリスト
        """
        try:
            # 日付を文字列形式に変換
            from_date_str = self._format_date(from_date)
            to_date_str = self._format_date(to_date)
            
            logger.info(f"Fetching calendar data from {from_date_str} to {to_date_str}")
            
            # investpyでデータ取得
            calendar_df = self.investpy.economic_calendar(
                from_date=from_date_str,
                to_date=to_date_str,
                countries=countries,
                importances=importance
            )
            
            logger.info(f"Retrieved {len(calendar_df)} calendar events")
            
            # EconomicEventオブジェクトに変換
            events = []
            for idx, row in calendar_df.iterrows():
                event = self._row_to_event(row, idx)
                if event:
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error fetching calendar data: {e}")
            raise
    
    def get_yesterday_events(
        self,
        countries: Optional[List[str]] = None,
        importance: Optional[str] = None
    ) -> List[EconomicEvent]:
        """
        昨日の経済イベントを取得（ライト機能用）
        
        Args:
            countries: 対象国リスト
            importance: 重要度フィルタ
            
        Returns:
            昨日のEconomicEventリスト
        """
        yesterday = datetime.now() - timedelta(days=1)
        return self.get_calendar_data(
            from_date=yesterday.date(),
            to_date=yesterday.date(),
            countries=countries,
            importance=importance
        )
    
    def get_upcoming_events(
        self,
        days_ahead: int = 7,
        countries: Optional[List[str]] = None,
        importance: Optional[str] = None
    ) -> List[EconomicEvent]:
        """
        今後の経済イベントを取得（カレンダー機能用）
        
        Args:
            days_ahead: 何日先まで取得するか
            countries: 対象国リスト
            importance: 重要度フィルタ
            
        Returns:
            今後のEconomicEventリスト
        """
        today = datetime.now().date()
        end_date = today + timedelta(days=days_ahead)
        
        return self.get_calendar_data(
            from_date=today,
            to_date=end_date,
            countries=countries,
            importance=importance
        )
    
    def _format_date(self, date_input: Union[str, date, datetime]) -> str:
        """日付をinvestpy用の文字列形式に変換"""
        if isinstance(date_input, str):
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.strftime("%d/%m/%Y")
        elif isinstance(date_input, date):
            return date_input.strftime("%d/%m/%Y")
        else:
            raise ValueError(f"Invalid date format: {date_input}")
    
    def _row_to_event(self, row: pd.Series, idx: int) -> Optional[EconomicEvent]:
        """DataFrameの行をEconomicEventに変換"""
        try:
            # 基本情報の取得
            title = str(row.get('event', ''))
            country = str(row.get('zone', ''))
            importance = str(row.get('importance', 'Medium')).title()
            
            # 日時の処理
            date_str = str(row.get('date', ''))
            time_str = str(row.get('time', '00:00'))
            
            try:
                # 日時をUTCに変換
                scheduled_time = self._parse_datetime(date_str, time_str)
            except Exception as e:
                logger.warning(f"Failed to parse datetime for event {title}: {e}")
                scheduled_time = datetime.now(pytz.UTC)
            
            # 数値データの処理
            actual = self._parse_numeric(row.get('actual', ''))
            forecast = self._parse_numeric(row.get('forecast', ''))
            previous = self._parse_numeric(row.get('previous', ''))
            
            # 通貨・単位の推定
            currency = self._detect_currency(country)
            unit = self._detect_unit(title, str(row.get('actual', '')))
            
            # イベントオブジェクト作成
            event = EconomicEvent(
                id=f"investpy_{idx}_{scheduled_time.strftime('%Y%m%d_%H%M')}",
                title=title,
                country=country,
                importances=importance,
                scheduled_time_utc=scheduled_time,
                actual=actual,
                forecast=forecast,
                previous=previous,
                source="investpy",
                category=self._categorize_event(title),
                currency=currency,
                unit=unit
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error converting row to event: {e}")
            return None
    
    def _parse_datetime(self, date_str: str, time_str: str) -> datetime:
        """日付・時刻文字列をUTC datetimeに変換"""
        try:
            # investpyの日付形式を処理 (通常は DD/MM/YYYY)
            if '/' in date_str:
                date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
            else:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # 時刻の処理
            if time_str and time_str != 'nan' and ':' in time_str:
                time_obj = datetime.strptime(time_str, "%H:%M").time()
            else:
                time_obj = datetime.strptime("00:00", "%H:%M").time()
            
            # UTCに変換（投資データは通常UTC前提）
            dt = datetime.combine(date_obj, time_obj)
            dt_utc = pytz.utc.localize(dt)
            
            return dt_utc
            
        except Exception as e:
            logger.warning(f"Date parsing error: {e}, using current time")
            return datetime.now(pytz.UTC)
    
    def _parse_numeric(self, value: any) -> Optional[float]:
        """数値文字列をfloatに変換"""
        if pd.isna(value) or value == '' or str(value).lower() in ['nan', 'none']:
            return None
        
        try:
            # 文字列の場合の処理
            if isinstance(value, str):
                # 単位記号を除去
                cleaned = value.replace('%', '').replace('K', '000').replace('M', '000000')
                cleaned = cleaned.replace('B', '000000000').replace(',', '').strip()
                
                if cleaned == '' or cleaned == '-':
                    return None
                
                return float(cleaned)
            
            return float(value)
            
        except (ValueError, TypeError):
            return None
    
    def _detect_currency(self, country: str) -> Optional[str]:
        """国名から通貨コードを推定"""
        currency_map = {
            'United States': 'USD',
            'Euro Zone': 'EUR',
            'Germany': 'EUR',
            'France': 'EUR',
            'Italy': 'EUR',
            'Spain': 'EUR',
            'United Kingdom': 'GBP',
            'Japan': 'JPY',
            'Canada': 'CAD',
            'Australia': 'AUD',
            'Switzerland': 'CHF',
            'China': 'CNY',
            'South Korea': 'KRW'
        }
        return currency_map.get(country)
    
    def _detect_unit(self, title: str, actual_value: str) -> Optional[str]:
        """イベント名と実際値から単位を推定"""
        title_lower = title.lower()
        
        if '%' in actual_value or 'rate' in title_lower:
            return 'percent'
        elif 'index' in title_lower:
            return 'index'
        elif 'gdp' in title_lower:
            return 'billions'
        elif 'employment' in title_lower or 'payroll' in title_lower:
            return 'thousands'
        elif 'sales' in title_lower:
            return 'millions'
        else:
            return None
    
    def _categorize_event(self, title: str) -> Optional[str]:
        """イベント名からカテゴリを推定"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['cpi', 'inflation', 'price']):
            return 'Inflation'
        elif any(word in title_lower for word in ['employment', 'unemployment', 'payroll', 'jobs']):
            return 'Employment'
        elif any(word in title_lower for word in ['gdp', 'growth', 'output']):
            return 'Growth'
        elif any(word in title_lower for word in ['rate', 'interest', 'monetary']):
            return 'Monetary Policy'
        elif any(word in title_lower for word in ['retail', 'sales', 'consumption']):
            return 'Consumption'
        elif any(word in title_lower for word in ['pmi', 'manufacturing', 'industrial']):
            return 'Manufacturing'
        elif any(word in title_lower for word in ['confidence', 'sentiment']):
            return 'Sentiment'
        else:
            return 'Other'


# 使用例とテスト用関数
def test_investpy_adapter():
    """投資カレンダーアダプターのテスト"""
    try:
        adapter = InvestpyCalendarAdapter()
        
        # 昨日のイベントを取得
        events = adapter.get_yesterday_events(
            countries=['United States', 'Japan'],
            importance='high'
        )
        
        print(f"Found {len(events)} high-importance events from yesterday")
        
        for event in events[:5]:  # 最初の5件を表示
            print(f"- {event.title} ({event.country})")
            print(f"  Time: {event.scheduled_time_utc}")
            print(f"  Actual: {event.actual}, Forecast: {event.forecast}")
            surprise = event.calculate_surprise()
            if surprise:
                print(f"  Surprise: {surprise['surprise']:.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    # 簡単なテスト実行
    logging.basicConfig(level=logging.INFO)
    test_investpy_adapter()