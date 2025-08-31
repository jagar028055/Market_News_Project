"""
ICS Calendar Builder
経済指標発表予定のICS（iCalendar）ファイル生成
"""

import logging
from typing import List, Optional, Union
from datetime import datetime, date, timedelta
import pytz
from pathlib import Path
import hashlib

from ..adapters.investpy_calendar import EconomicEvent
from ..config.settings import get_econ_config

logger = logging.getLogger(__name__)


class ICSBuilder:
    """経済指標カレンダー ICS ビルダー"""
    
    def __init__(self):
        self.config = get_econ_config()
        self.display_tz = self.config.get_timezone("display")
        self.internal_tz = self.config.get_timezone("internal")
    
    def build_calendar(
        self,
        events: List[EconomicEvent],
        calendar_name: str = "Economic Indicators",
        description: str = "Economic indicators release schedule"
    ) -> str:
        """
        経済イベントからICSカレンダーを生成
        
        Args:
            events: 経済イベントリスト
            calendar_name: カレンダー名
            description: カレンダー説明
            
        Returns:
            ICS形式の文字列
        """
        try:
            from icalendar import Calendar, Event, vText
            
            # カレンダーオブジェクト作成
            cal = Calendar()
            cal.add('prodid', '-//Economic Indicators//Market News System//EN')
            cal.add('version', '2.0')
            cal.add('calscale', 'GREGORIAN')
            cal.add('method', 'PUBLISH')
            cal.add('x-wr-calname', vText(calendar_name))
            cal.add('x-wr-caldesc', vText(description))
            cal.add('x-wr-timezone', self.display_tz.zone)
            
            # イベント追加
            for econ_event in events:
                ics_event = self._create_ics_event(econ_event)
                if ics_event:
                    cal.add_component(ics_event)
            
            # ICS文字列として返す
            ics_content = cal.to_ical().decode('utf-8')
            
            logger.info(f"Generated ICS calendar with {len(events)} events")
            return ics_content
            
        except ImportError:
            logger.error("icalendar library not found. Please install: pip install icalendar")
            raise ImportError("icalendar library is required but not installed")
        except Exception as e:
            logger.error(f"Error building ICS calendar: {e}")
            raise
    
    def save_calendar(
        self,
        events: List[EconomicEvent],
        calendar_name: str = "Economic Indicators",
        description: str = "Economic indicators release schedule"
    ) -> str:
        """
        ICSカレンダーをファイルに保存
        
        Args:
            events: 経済イベントリスト
            calendar_name: カレンダー名
            description: カレンダー説明
            
        Returns:
            保存されたファイルパス
        """
        # ICS生成
        ics_content = self.build_calendar(events, calendar_name, description)
        
        # 出力パス
        file_path = self.config.get_output_path("calendar")
        
        # ディレクトリ作成
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # ファイル保存
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(ics_content)
        
        logger.info(f"ICS calendar saved to: {file_path}")
        return file_path
    
    def _create_ics_event(self, econ_event: EconomicEvent) -> Optional['Event']:
        """EconomicEventからICS Eventを作成"""
        try:
            from icalendar import Event, vText
            
            ics_event = Event()
            
            # 基本情報
            ics_event.add('uid', self._generate_uid(econ_event))
            ics_event.add('summary', vText(f"{econ_event.country}: {econ_event.title}"))
            
            # 時刻設定
            event_start, event_end = self._calculate_event_times(econ_event)
            ics_event.add('dtstart', event_start)
            ics_event.add('dtend', event_end)
            
            # 説明文
            description = self._build_event_description(econ_event)
            ics_event.add('description', vText(description))
            
            # カテゴリ
            categories = [econ_event.importance, "Economics"]
            if econ_event.category:
                categories.append(econ_event.category)
            ics_event.add('categories', categories)
            
            # 場所（国）
            ics_event.add('location', vText(econ_event.country))
            
            # 優先度
            priority = self._get_priority(econ_event.importance)
            ics_event.add('priority', priority)
            
            # 作成・更新時刻
            now = datetime.now(pytz.UTC)
            ics_event.add('created', now)
            ics_event.add('last-modified', now)
            ics_event.add('dtstamp', now)
            
            # 高重要度イベントにはアラーム追加
            if econ_event.importance == 'High' and self.config.schedule.notification_enabled:
                self._add_alarm(ics_event, econ_event)
            
            return ics_event
            
        except Exception as e:
            logger.error(f"Error creating ICS event for {econ_event.title}: {e}")
            return None
    
    def _generate_uid(self, event: EconomicEvent) -> str:
        """一意のUID生成"""
        # イベントの情報を結合してハッシュ化
        uid_source = f"{event.title}_{event.country}_{event.scheduled_time_utc.isoformat()}"
        uid_hash = hashlib.md5(uid_source.encode('utf-8')).hexdigest()
        return f"econ-{uid_hash}@market-news.system"
    
    def _calculate_event_times(self, event: EconomicEvent) -> tuple:
        """イベントの開始・終了時刻を計算"""
        start_time = event.scheduled_time_utc
        
        # 経済指標の発表は瞬間的なので、15分間のイベントとして設定
        end_time = start_time + timedelta(minutes=15)
        
        return start_time, end_time
    
    def _build_event_description(self, event: EconomicEvent) -> str:
        """イベント説明文を構築"""
        description_lines = [
            f"Economic Indicator: {event.title}",
            f"Country: {event.country}",
            f"Importance: {event.importance}",
            f"Category: {event.category or 'N/A'}",
        ]
        
        # 予測値・前回値
        if event.forecast is not None:
            unit_str = f" {event.unit}" if event.unit else ""
            description_lines.append(f"Forecast: {event.forecast}{unit_str}")
        
        if event.previous is not None:
            unit_str = f" {event.unit}" if event.unit else ""
            description_lines.append(f"Previous: {event.previous}{unit_str}")
        
        # 実際値（発表済みの場合）
        if event.actual is not None:
            unit_str = f" {event.unit}" if event.unit else ""
            description_lines.append(f"Actual: {event.actual}{unit_str}")
            
            # サプライズ
            surprise_data = event.calculate_surprise()
            if surprise_data:
                description_lines.append(f"Surprise: {surprise_data['surprise']:.2f}{unit_str}")
        
        # データソース
        description_lines.append(f"Source: {event.source.upper()}")
        
        # 発表時刻（現地時間）
        local_time = event.scheduled_time_utc.astimezone(self.display_tz)
        description_lines.append(f"Local Time: {local_time.strftime('%Y-%m-%d %H:%M %Z')}")
        
        return "\\n".join(description_lines)
    
    def _get_priority(self, importance: str) -> int:
        """重要度をICS優先度に変換"""
        priority_map = {
            'High': 1,    # 高優先度
            'Medium': 5,  # 中優先度
            'Low': 9      # 低優先度
        }
        return priority_map.get(importance, 5)
    
    def _add_alarm(self, ics_event, econ_event: EconomicEvent):
        """アラームを追加（高重要度イベント用）"""
        try:
            from icalendar import Alarm, vText
            
            alarm = Alarm()
            alarm.add('action', 'DISPLAY')
            alarm.add('description', vText(f"Economic Release: {econ_event.title}"))
            
            # 発表60分前にアラーム
            advance_minutes = self.config.schedule.notification_advance_minutes
            alarm.add('trigger', timedelta(minutes=-advance_minutes))
            
            ics_event.add_component(alarm)
            
        except Exception as e:
            logger.warning(f"Failed to add alarm for event {econ_event.title}: {e}")
    
    def build_filtered_calendar(
        self,
        events: List[EconomicEvent],
        importance_filter: Optional[str] = None,
        country_filter: Optional[List[str]] = None,
        category_filter: Optional[List[str]] = None
    ) -> str:
        """
        フィルタリングされた経済カレンダーを生成
        
        Args:
            events: 経済イベントリスト
            importance_filter: 重要度フィルタ（"High", "Medium", "Low"）
            country_filter: 国フィルタ
            category_filter: カテゴリフィルタ
            
        Returns:
            フィルタリングされたICS文字列
        """
        # イベントフィルタリング
        filtered_events = []
        
        for event in events:
            # 重要度フィルタ
            if importance_filter and event.importance != importance_filter:
                continue
            
            # 国フィルタ
            if country_filter and not any(
                country.lower() in event.country.lower() for country in country_filter
            ):
                continue
            
            # カテゴリフィルタ
            if category_filter and event.category not in category_filter:
                continue
            
            filtered_events.append(event)
        
        # カレンダー名を動的に生成
        filters = []
        if importance_filter:
            filters.append(f"{importance_filter} Importance")
        if country_filter:
            filters.append(f"{', '.join(country_filter)}")
        if category_filter:
            filters.append(f"{', '.join(category_filter)}")
        
        if filters:
            calendar_name = f"Economic Indicators - {' | '.join(filters)}"
        else:
            calendar_name = "Economic Indicators"
        
        return self.build_calendar(
            filtered_events,
            calendar_name,
            f"Filtered economic indicators: {len(filtered_events)} events"
        )
    
    def generate_subscription_url(self, base_url: str) -> str:
        """
        カレンダー購読用URLを生成
        
        Args:
            base_url: ベースURL（例: https://example.com）
            
        Returns:
            購読用URL
        """
        calendar_path = self.config.get_output_path("calendar")
        filename = Path(calendar_path).name
        
        # webcal:// プロトコルで購読URL生成
        if base_url.startswith('http://'):
            subscription_url = base_url.replace('http://', 'webcal://') + f"/{filename}"
        elif base_url.startswith('https://'):
            subscription_url = base_url.replace('https://', 'webcals://') + f"/{filename}"
        else:
            subscription_url = f"webcal://{base_url}/{filename}"
        
        return subscription_url


def test_ics_builder():
    """ICSビルダーのテスト"""
    
    # テストデータ作成
    test_events = [
        EconomicEvent(
            id="test_1",
            title="CPI (YoY)",
            country="United States",
            importance="High",
            scheduled_time_utc=datetime.now(pytz.UTC) + timedelta(hours=1),
            actual=None,
            forecast=3.1,
            previous=3.3,
            source="test",
            category="Inflation",
            unit="percent"
        ),
        EconomicEvent(
            id="test_2",
            title="GDP (QoQ)",
            country="Japan",
            importance="Medium",
            scheduled_time_utc=datetime.now(pytz.UTC) + timedelta(days=1),
            actual=None,
            forecast=0.3,
            previous=0.1,
            source="test",
            category="Growth",
            unit="percent"
        )
    ]
    
    try:
        builder = ICSBuilder()
        
        # ICS生成テスト
        ics_content = builder.build_calendar(test_events, "Test Economic Calendar")
        print("ICS calendar generated successfully")
        print("="*50)
        print(ics_content[:800] + "..." if len(ics_content) > 800 else ics_content)
        
        # フィルタリングテスト
        filtered_ics = builder.build_filtered_calendar(
            test_events,
            importance_filter="High"
        )
        print(f"\nFiltered calendar generated (High importance only)")
        print(f"Events count: {filtered_ics.count('BEGIN:VEVENT')}")
        
        # 購読URLテスト
        subscription_url = builder.generate_subscription_url("https://example.com")
        print(f"\nSubscription URL: {subscription_url}")
        
        return True
        
    except Exception as e:
        logger.error(f"ICS builder test failed: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_ics_builder()