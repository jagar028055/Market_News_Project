"""
Financial Modeling Prep (FMP) Calendar Adapter
FMP APIを使用した経済カレンダーデータの取得（投資用フォールバック）
"""

import logging
import requests
from typing import List, Dict, Optional, Union
from datetime import datetime, date, timedelta
import pytz
from .investpy_calendar import EconomicEvent

logger = logging.getLogger(__name__)


class FMPCalendarAdapter:
    """FMP経済カレンダーアダプター（フォールバック用）"""
    
    def __init__(self, api_key: str, base_url: str = "https://financialmodelingprep.com/api/v3", timeout: int = 30):
        """
        Args:
            api_key: FMP API key
            base_url: FMP API base URL
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
    
    def get_calendar_data(
        self,
        from_date: Union[str, date, datetime],
        to_date: Union[str, date, datetime]
    ) -> List[EconomicEvent]:
        """
        経済カレンダーデータを取得
        
        Args:
            from_date: 開始日
            to_date: 終了日
            
        Returns:
            EconomicEventのリスト
        """
        try:
            from_date_str = self._format_date(from_date)
            to_date_str = self._format_date(to_date)
            
            logger.info(f"Fetching FMP calendar data from {from_date_str} to {to_date_str}")
            
            url = f"{self.base_url}/economic_calendar"
            params = {
                "from": from_date_str,
                "to": to_date_str,
                "apikey": self.api_key
            }
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning("No data returned from FMP API")
                return []
            
            logger.info(f"Retrieved {len(data)} calendar events from FMP")
            
            # EconomicEventオブジェクトに変換
            events = []
            for idx, item in enumerate(data):
                event = self._item_to_event(item, idx)
                if event:
                    events.append(event)
            
            return events
            
        except requests.RequestException as e:
            logger.error(f"FMP API request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing FMP calendar data: {e}")
            raise
    
    def get_yesterday_events(self) -> List[EconomicEvent]:
        """昨日の経済イベントを取得"""
        yesterday = datetime.now() - timedelta(days=1)
        return self.get_calendar_data(
            from_date=yesterday.date(),
            to_date=yesterday.date()
        )
    
    def get_upcoming_events(self, days_ahead: int = 7) -> List[EconomicEvent]:
        """今後の経済イベントを取得"""
        today = datetime.now().date()
        end_date = today + timedelta(days=days_ahead)
        
        return self.get_calendar_data(
            from_date=today,
            to_date=end_date
        )
    
    def _format_date(self, date_input: Union[str, date, datetime]) -> str:
        """日付をFMP用の文字列形式に変換（YYYY-MM-DD）"""
        if isinstance(date_input, str):
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.strftime("%Y-%m-%d")
        elif isinstance(date_input, date):
            return date_input.strftime("%Y-%m-%d")
        else:
            raise ValueError(f"Invalid date format: {date_input}")
    
    def _item_to_event(self, item: Dict, idx: int) -> Optional[EconomicEvent]:
        """FMP APIレスポンスアイテムをEconomicEventに変換"""
        try:
            # FMP APIの基本フィールド
            event_name = item.get('event', '')
            country = item.get('country', '')
            date_str = item.get('date', '')
            time_str = item.get('time', '')
            
            # 重要度はFMPにはないので、イベント名から推定
            importance = self._estimate_importance(event_name)
            
            # 日時処理
            try:
                scheduled_time = self._parse_datetime(date_str, time_str)
            except Exception as e:
                logger.warning(f"Failed to parse datetime for FMP event {event_name}: {e}")
                scheduled_time = datetime.now(pytz.UTC)
            
            # 数値データ
            actual = self._parse_numeric(item.get('actual'))
            estimate = self._parse_numeric(item.get('estimate'))  # FMPでは'estimate'
            previous = self._parse_numeric(item.get('previous'))
            
            # 通貨・単位
            currency = self._detect_currency(country)
            unit = self._detect_unit(event_name, str(item.get('actual', '')))
            
            event = EconomicEvent(
                id=f"fmp_{idx}_{scheduled_time.strftime('%Y%m%d_%H%M')}",
                title=event_name,
                country=country,
                importance=importance,
                scheduled_time_utc=scheduled_time,
                actual=actual,
                forecast=estimate,  # FMPのestimateをforecastとして使用
                previous=previous,
                source="fmp",
                category=self._categorize_event(event_name),
                currency=currency,
                unit=unit
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error converting FMP item to event: {e}")
            return None
    
    def _parse_datetime(self, date_str: str, time_str: str) -> datetime:
        """FMPの日付・時刻文字列をUTC datetimeに変換"""
        try:
            # FMPの日付形式は通常 YYYY-MM-DD
            if date_str:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                date_obj = datetime.now().date()
            
            # 時刻処理
            if time_str and time_str.strip() != '' and ':' in time_str:
                # FMPの時刻は "HH:MM" or "HH:MM AM/PM" 形式
                time_str_clean = time_str.strip()
                if 'AM' in time_str_clean.upper() or 'PM' in time_str_clean.upper():
                    time_obj = datetime.strptime(time_str_clean, "%I:%M %p").time()
                else:
                    time_obj = datetime.strptime(time_str_clean, "%H:%M").time()
            else:
                time_obj = datetime.strptime("00:00", "%H:%M").time()
            
            # UTCに変換
            dt = datetime.combine(date_obj, time_obj)
            dt_utc = pytz.utc.localize(dt)
            
            return dt_utc
            
        except Exception as e:
            logger.warning(f"FMP date parsing error: {e}, using current time")
            return datetime.now(pytz.UTC)
    
    def _parse_numeric(self, value: any) -> Optional[float]:
        """数値をfloatに変換"""
        if value is None or value == '' or str(value).lower() in ['nan', 'none', 'null']:
            return None
        
        try:
            if isinstance(value, str):
                # FMP特有の単位処理
                cleaned = value.replace('%', '').replace('K', '000').replace('M', '000000')
                cleaned = cleaned.replace('B', '000000000').replace(',', '').strip()
                
                if cleaned == '' or cleaned == '-' or cleaned == 'N/A':
                    return None
                
                return float(cleaned)
            
            return float(value)
            
        except (ValueError, TypeError):
            return None
    
    def _estimate_importance(self, event_name: str) -> str:
        """イベント名から重要度を推定"""
        event_lower = event_name.lower()
        
        # 高重要度イベント
        high_importance_keywords = [
            'gdp', 'unemployment', 'cpi', 'inflation', 'federal funds',
            'interest rate', 'nonfarm payrolls', 'retail sales',
            'fomc', 'fed', 'ecb decision', 'boe decision'
        ]
        
        # 中重要度イベント
        medium_importance_keywords = [
            'pmi', 'confidence', 'housing', 'industrial production',
            'trade balance', 'current account'
        ]
        
        if any(keyword in event_lower for keyword in high_importance_keywords):
            return 'High'
        elif any(keyword in event_lower for keyword in medium_importance_keywords):
            return 'Medium'
        else:
            return 'Low'
    
    def _detect_currency(self, country: str) -> Optional[str]:
        """国名から通貨コードを推定"""
        currency_map = {
            'United States': 'USD',
            'US': 'USD',
            'USA': 'USD',
            'Euro Zone': 'EUR',
            'Eurozone': 'EUR',
            'Germany': 'EUR',
            'France': 'EUR',
            'Italy': 'EUR',
            'Spain': 'EUR',
            'United Kingdom': 'GBP',
            'UK': 'GBP',
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
        
        if '%' in actual_value or 'rate' in title_lower or 'percent' in title_lower:
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
        elif any(word in title_lower for word in ['rate', 'interest', 'monetary', 'fed', 'fomc']):
            return 'Monetary Policy'
        elif any(word in title_lower for word in ['retail', 'sales', 'consumption']):
            return 'Consumption'
        elif any(word in title_lower for word in ['pmi', 'manufacturing', 'industrial']):
            return 'Manufacturing'
        elif any(word in title_lower for word in ['confidence', 'sentiment']):
            return 'Sentiment'
        else:
            return 'Other'


# テスト用関数
def test_fmp_adapter():
    """FMPアダプターのテスト（要APIキー）"""
    import os
    
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print("FMP_API_KEY environment variable not set")
        return False
    
    try:
        adapter = FMPCalendarAdapter(api_key)
        
        # 昨日のイベントを取得
        events = adapter.get_yesterday_events()
        
        print(f"Found {len(events)} events from FMP API")
        
        for event in events[:5]:
            print(f"- {event.title} ({event.country})")
            print(f"  Time: {event.scheduled_time_utc}")
            print(f"  Actual: {event.actual}, Forecast: {event.forecast}")
            surprise = event.calculate_surprise()
            if surprise:
                print(f"  Surprise: {surprise['surprise']:.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"FMP test failed: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_fmp_adapter()