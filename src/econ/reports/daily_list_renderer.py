"""
Daily Economic Indicators List Renderer
日次経済指標一覧のMarkdown/HTML生成
"""

import logging
from typing import List, Dict, Optional, Union
from datetime import datetime, date
import pytz
from pathlib import Path
import json

from ..adapters.investpy_calendar import EconomicEvent
from ..config.settings import get_econ_config

logger = logging.getLogger(__name__)


class DailyListRenderer:
    """日次経済指標一覧レンダラー"""
    
    def __init__(self):
        self.config = get_econ_config()
        self.display_tz = self.config.get_timezone("display")
        self.internal_tz = self.config.get_timezone("internal")
    
    def render_markdown(
        self,
        events: List[EconomicEvent],
        target_date: Optional[Union[str, date, datetime]] = None,
        include_no_surprise: bool = False
    ) -> str:
        """
        経済イベントリストをMarkdown形式でレンダリング
        
        Args:
            events: 経済イベントリスト
            target_date: 対象日（Noneの場合は昨日）
            include_no_surprise: 予想値がないイベントも含めるか
            
        Returns:
            Markdown形式の文字列
        """
        if not target_date:
            target_date = datetime.now() - datetime.timedelta(days=1)
        
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        
        # イベントをフィルタリング・ソート
        filtered_events = self._filter_and_sort_events(events, include_no_surprise)
        
        # Markdownコンテンツ生成
        markdown_content = self._generate_markdown_content(filtered_events, target_date)
        
        return markdown_content
    
    def render_html(
        self,
        events: List[EconomicEvent],
        target_date: Optional[Union[str, date, datetime]] = None,
        include_no_surprise: bool = False
    ) -> str:
        """
        経済イベントリストをHTML形式でレンダリング
        
        Args:
            events: 経済イベントリスト
            target_date: 対象日
            include_no_surprise: 予想値がないイベントも含めるか
            
        Returns:
            HTML形式の文字列
        """
        # まずMarkdownを生成し、HTMLに変換
        markdown = self.render_markdown(events, target_date, include_no_surprise)
        
        try:
            import markdown
            html = markdown.markdown(markdown, extensions=['tables'])
            
            # CSSスタイルを追加
            styled_html = self._add_html_styles(html)
            return styled_html
            
        except ImportError:
            logger.warning("markdown library not available, returning raw markdown")
            return f"<pre>{markdown}</pre>"
    
    def save_daily_report(
        self,
        events: List[EconomicEvent],
        target_date: Optional[Union[str, date, datetime]] = None,
        format_type: str = "markdown"
    ) -> str:
        """
        日次レポートをファイルに保存
        
        Args:
            events: 経済イベントリスト
            target_date: 対象日
            format_type: 出力形式（"markdown" or "html"）
            
        Returns:
            保存されたファイルパス
        """
        if not target_date:
            target_date = datetime.now() - datetime.timedelta(days=1)
        
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        
        # 出力パスを生成
        date_str = target_date.strftime("%Y%m%d")
        if format_type.lower() == "html":
            file_path = self.config.get_output_path("daily_report", date_str).replace(".md", ".html")
        else:
            file_path = self.config.get_output_path("daily_report", date_str)
        
        # ディレクトリ作成
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # コンテンツ生成
        if format_type.lower() == "html":
            content = self.render_html(events, target_date)
        else:
            content = self.render_markdown(events, target_date)
        
        # ファイル保存
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Daily report saved to: {file_path}")
        return file_path
    
    def generate_csv_export(self, events: List[EconomicEvent]) -> str:
        """
        CSV形式でエクスポート用データを生成
        
        Args:
            events: 経済イベントリスト
            
        Returns:
            CSV形式の文字列
        """
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        writer.writerow([
            'Date', 'Time (JST)', 'Country', 'Indicator', 'Importance',
            'Actual', 'Forecast', 'Previous', 'Surprise', 'Surprise %',
            'Category', 'Source'
        ])
        
        # データ行
        for event in events:
            # 表示用時刻変換
            local_time = event.scheduled_time_utc.astimezone(self.display_tz)
            
            # サプライズ計算
            surprise_data = event.calculate_surprise()
            surprise = surprise_data['surprise'] if surprise_data else ''
            surprise_pct = surprise_data['surprise_pct'] if surprise_data else ''
            
            writer.writerow([
                local_time.strftime('%Y-%m-%d'),
                local_time.strftime('%H:%M'),
                event.country,
                event.title,
                event.importance,
                event.actual if event.actual is not None else '',
                event.forecast if event.forecast is not None else '',
                event.previous if event.previous is not None else '',
                f"{surprise:.2f}" if surprise != '' else '',
                f"{surprise_pct:.1f}%" if surprise_pct != '' else '',
                event.category or '',
                event.source
            ])
        
        return output.getvalue()
    
    def _filter_and_sort_events(
        self,
        events: List[EconomicEvent],
        include_no_surprise: bool = False
    ) -> List[EconomicEvent]:
        """イベントをフィルタリング・ソート"""
        
        # 重要度・国フィルタリング
        target_countries = self.config.targets.target_countries
        importance_threshold = self.config.targets.importance_threshold
        
        filtered = []
        for event in events:
            # 国フィルタ
            if target_countries and not any(
                country.lower() in event.country.lower() for country in target_countries
            ):
                continue
            
            # 重要度フィルタ
            if not self._meets_importance_threshold(event.importance, importance_threshold):
                continue
            
            # サプライズ表示フィルタ
            if not include_no_surprise and event.forecast is None:
                # 予想値がない場合、設定によってスキップ
                if self.config.missing_forecast_handling == "skip_surprise":
                    # サプライズは計算しないが、イベントは含める
                    pass
                else:
                    continue
            
            filtered.append(event)
        
        # ソート: 重要度（High > Medium > Low）→時刻順
        importance_order = {'High': 3, 'Medium': 2, 'Low': 1}
        
        filtered.sort(key=lambda x: (
            -importance_order.get(x.importance, 0),  # 重要度降順
            x.scheduled_time_utc  # 時刻昇順
        ))
        
        return filtered
    
    def _meets_importance_threshold(self, importance: str, threshold: str) -> bool:
        """重要度しきい値チェック"""
        importance_levels = {'Low': 1, 'Medium': 2, 'High': 3}
        
        event_level = importance_levels.get(importance, 0)
        threshold_level = importance_levels.get(threshold, 2)
        
        return event_level >= threshold_level
    
    def _generate_markdown_content(
        self,
        events: List[EconomicEvent],
        target_date: date
    ) -> str:
        """Markdownコンテンツ生成"""
        
        date_str_jp = target_date.strftime("%Y年%m月%d日")
        date_str_iso = target_date.strftime("%Y-%m-%d")
        
        # ヘッダー生成
        content = f"""# 経済指標一覧 - {date_str_jp}

> 対象日: {date_str_iso}  
> 表示時刻: {self.display_tz.zone}  
> データソース: investpy, FMP  
> 重要度しきい値: {self.config.targets.importance_threshold}

## 発表済み経済指標

"""
        
        if not events:
            content += "**該当する経済指標の発表はありませんでした。**\n\n"
            return content
        
        # 統計情報
        total_events = len(events)
        high_importance = len([e for e in events if e.importance == 'High'])
        with_surprise = len([e for e in events if e.calculate_surprise() is not None])
        
        content += f"""### 概要
- 発表件数: **{total_events}件**
- 高重要度: **{high_importance}件**
- サプライズあり: **{with_surprise}件**

"""
        
        # テーブル生成
        content += """| 時刻 | 国 | 指標名 | 重要度 | 実際値 | 予想値 | 前回値 | サプライズ | 出典 |
|------|----|----|:----:|----|----|----|----|:----:|
"""
        
        for event in events:
            content += self._generate_table_row(event)
        
        # フッター
        content += f"""

## 注記

- **重要度**: High (高), Medium (中), Low (低)
- **サプライズ**: 実際値 - 予想値（予想値がある場合のみ表示）
- **時刻**: {self.display_tz.zone} 表示
- **データ更新**: {datetime.now(self.display_tz).strftime('%Y-%m-%d %H:%M:%S')}

## データソース

- **investpy**: Python investpy library
- **FMP**: Financial Modeling Prep API
- 数値は各統計機関の公式発表値

---

*本データは投資判断の参考情報として提供されており、投資を推奨するものではありません。*
"""
        
        return content
    
    def _generate_table_row(self, event: EconomicEvent) -> str:
        """テーブル行生成"""
        # 時刻変換
        local_time = event.scheduled_time_utc.astimezone(self.display_tz)
        time_str = local_time.strftime('%H:%M')
        
        # 重要度アイコン
        importance_icon = {
            'High': '🔴',
            'Medium': '🟡',
            'Low': '🟢'
        }.get(event.importance, '⚪')
        
        # 数値フォーマット
        actual_str = self._format_numeric_value(event.actual, event.unit)
        forecast_str = self._format_numeric_value(event.forecast, event.unit)
        previous_str = self._format_numeric_value(event.previous, event.unit)
        
        # サプライズ計算
        surprise_data = event.calculate_surprise()
        if surprise_data:
            surprise = surprise_data['surprise']
            if abs(surprise) < 0.01:  # 小さなサプライズ
                surprise_str = f"{surprise:.3f}"
            else:
                surprise_str = f"**{surprise:+.2f}**"
            
            # サプライズの色付け（Markdownでは限定的）
            if surprise > 0:
                surprise_str += " 📈"
            elif surprise < 0:
                surprise_str += " 📉"
        else:
            surprise_str = "-"
        
        # 国名の短縮
        country_short = self._shorten_country_name(event.country)
        
        # 指標名の短縮（長すぎる場合）
        indicator_name = event.title
        if len(indicator_name) > 30:
            indicator_name = indicator_name[:27] + "..."
        
        return f"| {time_str} | {country_short} | {indicator_name} | {importance_icon} | {actual_str} | {forecast_str} | {previous_str} | {surprise_str} | {event.source.upper()} |\n"
    
    def _format_numeric_value(self, value: Optional[float], unit: Optional[str]) -> str:
        """数値フォーマット"""
        if value is None:
            return "-"
        
        if unit == 'percent':
            return f"{value:.1f}%"
        elif unit == 'index':
            return f"{value:.1f}"
        elif unit in ['millions', 'billions', 'thousands']:
            if abs(value) >= 1000:
                return f"{value:,.0f}"
            else:
                return f"{value:.1f}"
        else:
            # デフォルトフォーマット
            if abs(value) >= 100:
                return f"{value:,.0f}"
            else:
                return f"{value:.2f}"
    
    def _shorten_country_name(self, country: str) -> str:
        """国名短縮"""
        name_map = {
            'United States': 'US',
            'Euro Zone': 'EU',
            'United Kingdom': 'UK',
            'Japan': 'JP',
            'Canada': 'CA',
            'Australia': 'AU',
            'Germany': 'DE',
            'France': 'FR',
            'Italy': 'IT',
            'Spain': 'ES',
            'Switzerland': 'CH',
            'China': 'CN',
            'South Korea': 'KR'
        }
        return name_map.get(country, country[:10])  # 最大10文字
    
    def _add_html_styles(self, html_content: str) -> str:
        """HTMLスタイル追加"""
        
        css_styles = """
<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    line-height: 1.6;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 14px;
}

th, td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}

th {
    background-color: #f5f5f5;
    font-weight: bold;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

.importance-high { color: #d32f2f; }
.importance-medium { color: #f57c00; }
.importance-low { color: #388e3c; }

.surprise-positive { color: #2e7d32; font-weight: bold; }
.surprise-negative { color: #c62828; font-weight: bold; }

@media (max-width: 768px) {
    table { font-size: 12px; }
    th, td { padding: 4px; }
}
</style>
"""
        
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>経済指標一覧</title>
    {css_styles}
</head>
<body>
    {html_content}
</body>
</html>"""


# テスト用関数
def test_daily_list_renderer():
    """日次一覧レンダラーのテスト"""
    
    # テストデータ作成
    test_events = [
        EconomicEvent(
            id="test_1",
            title="CPI (YoY)",
            country="United States",
            importance="High",
            scheduled_time_utc=datetime.now(pytz.UTC),
            actual=3.2,
            forecast=3.1,
            previous=3.3,
            source="test",
            category="Inflation",
            unit="percent"
        ),
        EconomicEvent(
            id="test_2",
            title="Unemployment Rate",
            country="Japan",
            importance="Medium",
            scheduled_time_utc=datetime.now(pytz.UTC),
            actual=2.8,
            forecast=None,
            previous=2.9,
            source="test",
            category="Employment",
            unit="percent"
        )
    ]
    
    try:
        renderer = DailyListRenderer()
        
        # Markdown生成テスト
        markdown = renderer.render_markdown(test_events)
        print("Markdown generated successfully")
        print("="*50)
        print(markdown[:500] + "..." if len(markdown) > 500 else markdown)
        
        # CSV生成テスト
        csv_content = renderer.generate_csv_export(test_events)
        print("\nCSV generated successfully")
        print("="*50)
        print(csv_content)
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_daily_list_renderer()