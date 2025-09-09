"""
経済指標カレンダー取得モジュール
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import pytz
import requests


class EconomicCalendarFetcher:
    """経済指標カレンダー取得クラス"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
    def get_economic_calendar(
        self, 
        target_date: datetime,
        days_ahead: int = 1
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        経済指標カレンダーを取得
        
        Args:
            target_date: 対象日
            days_ahead: 何日先まで取得するか
            
        Returns:
            経済指標カレンダーデータ
        """
        try:
            # 1. investpyから取得を試行
            calendar_data = self._get_from_investpy(target_date, days_ahead)
            if calendar_data:
                self.logger.info(f"investpyから経済カレンダー取得: {len(calendar_data.get('today', []))}件")
                return calendar_data
            
            # 2. フォールバック: サンプルデータ
            self.logger.warning("経済カレンダーAPIが利用できないため、サンプルデータを使用")
            return self._get_sample_calendar_data(target_date)
            
        except Exception as e:
            self.logger.error(f"経済カレンダー取得エラー: {e}")
            return self._get_sample_calendar_data(target_date)
    
    def _get_from_investpy(self, target_date: datetime, days_ahead: int) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """investpyから経済カレンダーを取得"""
        try:
            import investpy
            
            # 日付の範囲を調整（過去1日から未来3日まで）
            start_date = target_date - timedelta(days=1)
            end_date = target_date + timedelta(days=3)
            
            # 日付フォーマットを確認
            start_str = start_date.strftime('%d/%m/%Y')
            end_str = end_date.strftime('%d/%m/%Y')
            
            self.logger.info(f"経済カレンダー取得範囲: {start_str} ～ {end_str}")
            
            # 経済カレンダーを取得
            events = investpy.economic_calendar(
                from_date=start_str,
                to_date=end_str
            )
            
            if events is None or events.empty:
                self.logger.warning("経済カレンダーデータが空です")
                return None
            
            # 前日と本日以降に分離
            previous_day = target_date - timedelta(days=1)
            previous_events = events[events['date'] == previous_day.strftime('%d/%m/%Y')]
            today_events = events[events['date'] >= target_date.strftime('%d/%m/%Y')]
            
            # データを整形
            previous_formatted = self._format_investpy_events(previous_events, 'previous')
            today_formatted = self._format_investpy_events(today_events, 'today')
            
            return {
                'previous_day': previous_formatted,
                'today': today_formatted
            }
            
        except ImportError:
            self.logger.warning("investpyがインストールされていません")
            return None
        except Exception as e:
            self.logger.error(f"investpyからの取得エラー: {e}")
            return None
    
    def _format_investpy_events(self, events, event_type: str) -> List[Dict[str, Any]]:
        """investpyのイベントデータを整形"""
        formatted_events = []
        
        for _, event in events.iterrows():
            # 時刻をJSTに変換
            event_time = event.get('time', '')
            if event_time:
                try:
                    # investpyの時刻形式に応じて調整
                    time_str = str(event_time).split()[0] if ' ' in str(event_time) else str(event_time)
                    formatted_time = time_str[:5]  # HH:MM形式
                except:
                    formatted_time = "未定"
            else:
                formatted_time = "未定"
            
            # 重要度を判定
            importance = event.get('importance', '')
            is_important = importance in ['High', 'high', '重要']
            
            formatted_event = {
                'time': formatted_time,
                'name': event.get('event', ''),
                'country': event.get('country', ''),
                'importance': importance,
                'important': is_important
            }
            
            if event_type == 'previous':
                # 前日実績の場合
                formatted_event.update({
                    'result': str(event.get('actual', '—')),
                    'forecast': str(event.get('forecast', '—')),
                    'previous': str(event.get('previous', '—'))
                })
            else:
                # 本日予定の場合
                formatted_event.update({
                    'forecast': str(event.get('forecast', '—')),
                    'range': self._generate_forecast_range(event.get('forecast', ''))
                })
            
            formatted_events.append(formatted_event)
        
        return formatted_events[:10]  # 最大10件
    
    def _generate_forecast_range(self, forecast: str) -> str:
        """予想値からレンジを生成"""
        try:
            if not forecast or forecast == '—':
                return "—"
            
            # 数値を抽出
            import re
            numbers = re.findall(r'-?\d+\.?\d*', str(forecast))
            if numbers:
                value = float(numbers[0])
                # ±10%のレンジを生成
                lower = value * 0.9
                upper = value * 1.1
                return f"{lower:.1f}〜{upper:.1f}"
        except:
            pass
        
        return "—"
    
    def _get_sample_calendar_data(self, target_date: datetime) -> Dict[str, List[Dict[str, Any]]]:
        """サンプル経済カレンダーデータを生成"""
        previous_day = target_date - timedelta(days=1)
        
        return {
            'previous_day': [
                {
                    'time': '21:30',
                    'name': '米 卸売物価（PPI）総合 前月比',
                    'result': '+0.2%',
                    'forecast': '+0.1%',
                    'previous': '+0.1%',
                    'country': 'US',
                    'importance': 'Medium'
                },
                {
                    'time': '23:00',
                    'name': '米 ミシガン消費者信頼感（確報）',
                    'result': '68.9',
                    'forecast': '69.1',
                    'previous': '69.5',
                    'country': 'US',
                    'importance': 'Medium'
                }
            ],
            'today': [
                {
                    'time': '21:30',
                    'name': '米 消費者物価（CPI）総合 前月比',
                    'forecast': '+0.2%',
                    'range': '+0.1〜0.3%',
                    'important': True,
                    'country': 'US',
                    'importance': 'High'
                },
                {
                    'time': '21:30',
                    'name': '米 CPI コア 前月比',
                    'forecast': '+0.2%',
                    'range': '+0.1〜0.2%',
                    'important': False,
                    'country': 'US',
                    'importance': 'High'
                },
                {
                    'time': '23:00',
                    'name': '加 中銀 金利',
                    'forecast': '5.00%',
                    'range': '据置見通し',
                    'important': False,
                    'country': 'CA',
                    'importance': 'High'
                }
            ]
        }
    
    def save_calendar_cache(self, target_date: datetime, calendar_data: Dict[str, List[Dict[str, Any]]], cache_dir: str = "build/calendars"):
        """経済カレンダーをキャッシュに保存"""
        try:
            cache_path = Path(cache_dir)
            cache_path.mkdir(parents=True, exist_ok=True)
            
            date_str = target_date.strftime('%Y%m%d')
            cache_file = cache_path / f"economic_calendar_{date_str}.json"
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(calendar_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"経済カレンダーをキャッシュ保存: {cache_file}")
            
        except Exception as e:
            self.logger.error(f"経済カレンダーキャッシュ保存エラー: {e}")
    
    def load_calendar_cache(self, target_date: datetime, cache_dir: str = "build/calendars") -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """キャッシュから経済カレンダーを読み込み"""
        try:
            date_str = target_date.strftime('%Y%m%d')
            cache_file = Path(cache_dir) / f"economic_calendar_{date_str}.json"
            
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
                    
        except Exception as e:
            self.logger.error(f"経済カレンダーキャッシュ読み込みエラー: {e}")
        
        return None
