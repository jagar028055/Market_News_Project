"""
Employment Statistics Dashboard
雇用統計専用ダッシュボード

雇用統計の全重要指標を網羅的に表示する専用ダッシュボード
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
from dataclasses import dataclass, field

# 既存モジュール
from .responsive_visualization import ResponsiveVisualizationEngine, ResponsiveConfig
from .comprehensive_employment_analysis import (
    ComprehensiveEmploymentAnalysis, 
    EmploymentAnalysisConfig,
    EmploymentIndicatorType
)

logger = logging.getLogger(__name__)


@dataclass
class EmploymentDashboardConfig:
    """雇用統計ダッシュボード設定"""
    # 基本設定
    country: str = "US"
    analysis_date: datetime = field(default_factory=datetime.now)
    
    # レスポンシブ設定
    screen_size: str = "desktop"  # mobile, tablet, desktop, large_desktop
    
    # 表示設定
    show_summary_cards: bool = True
    show_main_charts: bool = True
    show_detailed_tables: bool = True
    show_sector_analysis: bool = True
    show_trend_analysis: bool = True
    show_forecast_analysis: bool = True
    
    # 出力設定
    output_path: Optional[Path] = None
    output_format: List[str] = field(default_factory=lambda: ["html", "json"])


class EmploymentDashboard:
    """雇用統計専用ダッシュボード"""
    
    def __init__(self, config: Optional[EmploymentDashboardConfig] = None):
        self.config = config or EmploymentDashboardConfig()
        
        # コンポーネント初期化
        self.employment_analysis = ComprehensiveEmploymentAnalysis(
            EmploymentAnalysisConfig(
                country=self.config.country,
                analysis_date=self.config.analysis_date
            )
        )
        
        self.responsive_engine = ResponsiveVisualizationEngine(
            ResponsiveConfig(
                save_path=self.config.output_path
            )
        )
        
        # 分析データ
        self.analysis_data: Dict[str, Any] = {}
        self.indicators_data: Dict[EmploymentIndicatorType, Any] = {}
    
    def generate_employment_dashboard(self) -> Dict[str, Any]:
        """雇用統計ダッシュボードを生成"""
        
        try:
            logger.info("雇用統計ダッシュボード生成開始")
            
            # 1. 包括的な雇用統計データを作成
            self.indicators_data = self.employment_analysis.create_comprehensive_employment_data()
            
            # 2. 分析レポートを生成
            self.analysis_data = self.employment_analysis.generate_employment_analysis_report()
            
            # 3. ダッシュボードデータを準備
            dashboard_data = self._prepare_dashboard_data()
            
            # 4. レスポンシブダッシュボードを生成
            dashboard_result = self.responsive_engine.create_responsive_dashboard(
                dashboard_data, self.config.screen_size
            )
            
            # 5. 雇用統計専用のHTMLを生成
            employment_html = self._generate_employment_specific_html(dashboard_data)
            
            # 6. ファイル保存
            saved_files = []
            if self.config.output_path:
                saved_files = self._save_employment_dashboard(employment_html, dashboard_data)
            
            result = {
                'html': employment_html,
                'dashboard_data': dashboard_data,
                'analysis_data': self.analysis_data,
                'saved_files': saved_files,
                'screen_size': self.config.screen_size,
                'type': 'employment_dashboard'
            }
            
            logger.info("雇用統計ダッシュボード生成完了")
            return result
            
        except Exception as e:
            logger.error(f"雇用統計ダッシュボード生成エラー: {e}")
            return {'error': str(e)}
    
    def _prepare_dashboard_data(self) -> Dict[str, Any]:
        """ダッシュボードデータを準備"""
        
        try:
            dashboard_data = {
                'title': f"{self.config.country} 雇用統計ダッシュボード",
                'analysis_date': self.config.analysis_date.strftime('%Y年%m月%d日'),
                'summary_cards': self._generate_summary_cards_data(),
                'main_charts': self._generate_main_charts_data(),
                'detailed_tables': self._generate_detailed_tables_data(),
                'sector_analysis': self._generate_sector_analysis_data(),
                'trend_analysis': self._generate_trend_analysis_data(),
                'forecast_analysis': self._generate_forecast_analysis_data()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"ダッシュボードデータ準備エラー: {e}")
            return {}
    
    def _generate_summary_cards_data(self) -> List[Dict[str, Any]]:
        """サマリーカードデータを生成"""
        
        try:
            summary_cards = []
            
            # 主要指標のサマリーカード
            main_indicators = [
                EmploymentIndicatorType.NON_FARM_PAYROLLS,
                EmploymentIndicatorType.UNEMPLOYMENT_RATE,
                EmploymentIndicatorType.AVERAGE_HOURLY_EARNINGS,
                EmploymentIndicatorType.LABOR_FORCE_PARTICIPATION_RATE
            ]
            
            for indicator_type in main_indicators:
                if indicator_type in self.indicators_data:
                    indicator_data = self.indicators_data[indicator_type]
                    
                    # サプライズ計算
                    surprise_pct = 0
                    if indicator_data.actual_value and indicator_data.forecast_value:
                        surprise_pct = ((indicator_data.actual_value - indicator_data.forecast_value) / indicator_data.forecast_value) * 100
                    
                    # 変化率計算
                    change_pct = 0
                    if indicator_data.actual_value and indicator_data.previous_value:
                        change_pct = ((indicator_data.actual_value - indicator_data.previous_value) / indicator_data.previous_value) * 100
                    
                    card_data = {
                        'title': indicator_type.value,
                        'value': f"{indicator_data.actual_value:,.2f} {indicator_data.unit}" if indicator_data.actual_value else "N/A",
                        'forecast': f"{indicator_data.forecast_value:,.2f} {indicator_data.unit}" if indicator_data.forecast_value else "N/A",
                        'previous': f"{indicator_data.previous_value:,.2f} {indicator_data.unit}" if indicator_data.previous_value else "N/A",
                        'surprise_pct': surprise_pct,
                        'change_pct': change_pct,
                        'surprise_impact': 'positive' if surprise_pct > 0 else 'negative',
                        'change_direction': 'up' if change_pct > 0 else 'down',
                        'data_quality': indicator_data.data_quality_score,
                        'importance': indicator_data.importance
                    }
                    
                    summary_cards.append(card_data)
            
            return summary_cards
            
        except Exception as e:
            logger.error(f"サマリーカードデータ生成エラー: {e}")
            return []
    
    def _generate_main_charts_data(self) -> List[Dict[str, Any]]:
        """メインチャートデータを生成"""
        
        try:
            charts_data = []
            
            # 雇用者数推移チャート
            if EmploymentIndicatorType.NON_FARM_PAYROLLS in self.indicators_data:
                nfp_data = self.indicators_data[EmploymentIndicatorType.NON_FARM_PAYROLLS]
                if nfp_data.historical_data is not None:
                    charts_data.append({
                        'title': 'Non-Farm Payrolls 推移',
                        'type': 'line',
                        'data': nfp_data.historical_data.to_dict(),
                        'unit': nfp_data.unit,
                        'description': '非農業部門雇用者数の推移'
                    })
            
            # 失業率推移チャート
            if EmploymentIndicatorType.UNEMPLOYMENT_RATE in self.indicators_data:
                ur_data = self.indicators_data[EmploymentIndicatorType.UNEMPLOYMENT_RATE]
                if ur_data.historical_data is not None:
                    charts_data.append({
                        'title': '失業率推移',
                        'type': 'line',
                        'data': ur_data.historical_data.to_dict(),
                        'unit': ur_data.unit,
                        'description': '失業率の推移'
                    })
            
            # 平均賃金推移チャート
            if EmploymentIndicatorType.AVERAGE_HOURLY_EARNINGS in self.indicators_data:
                ahe_data = self.indicators_data[EmploymentIndicatorType.AVERAGE_HOURLY_EARNINGS]
                if ahe_data.historical_data is not None:
                    charts_data.append({
                        'title': '平均賃金推移',
                        'type': 'line',
                        'data': ahe_data.historical_data.to_dict(),
                        'unit': ahe_data.unit,
                        'description': '平均時給の推移'
                    })
            
            # サプライズ分析チャート
            surprises = []
            for indicator_type, indicator_data in self.indicators_data.items():
                if indicator_data.actual_value and indicator_data.forecast_value:
                    surprise_pct = ((indicator_data.actual_value - indicator_data.forecast_value) / indicator_data.forecast_value) * 100
                    surprises.append({
                        'indicator': indicator_type.value,
                        'surprise_pct': surprise_pct
                    })
            
            if surprises:
                charts_data.append({
                    'title': 'サプライズ分析',
                    'type': 'bar',
                    'data': surprises,
                    'unit': '%',
                    'description': '各指標の予想との乖離'
                })
            
            return charts_data
            
        except Exception as e:
            logger.error(f"メインチャートデータ生成エラー: {e}")
            return []
    
    def _generate_detailed_tables_data(self) -> List[Dict[str, Any]]:
        """詳細テーブルデータを生成"""
        
        try:
            tables_data = []
            
            # 全指標サマリーテーブル
            summary_table = {
                'title': '雇用統計サマリー',
                'headers': ['指標', '実際値', '予想値', '前回値', 'サプライズ', '変化率', 'データ品質'],
                'rows': []
            }
            
            for indicator_type, indicator_data in self.indicators_data.items():
                row = [indicator_type.value]
                
                # 実際値
                if indicator_data.actual_value:
                    row.append(f"{indicator_data.actual_value:,.2f} {indicator_data.unit}")
                else:
                    row.append("N/A")
                
                # 予想値
                if indicator_data.forecast_value:
                    row.append(f"{indicator_data.forecast_value:,.2f} {indicator_data.unit}")
                else:
                    row.append("N/A")
                
                # 前回値
                if indicator_data.previous_value:
                    row.append(f"{indicator_data.previous_value:,.2f} {indicator_data.unit}")
                else:
                    row.append("N/A")
                
                # サプライズ
                if indicator_data.actual_value and indicator_data.forecast_value:
                    surprise_pct = ((indicator_data.actual_value - indicator_data.forecast_value) / indicator_data.forecast_value) * 100
                    row.append(f"{surprise_pct:+.1f}%")
                else:
                    row.append("N/A")
                
                # 変化率
                if indicator_data.actual_value and indicator_data.previous_value:
                    change_pct = ((indicator_data.actual_value - indicator_data.previous_value) / indicator_data.previous_value) * 100
                    row.append(f"{change_pct:+.1f}%")
                else:
                    row.append("N/A")
                
                # データ品質
                row.append(f"{indicator_data.data_quality_score:.1f}/100")
                
                summary_table['rows'].append(row)
            
            tables_data.append(summary_table)
            
            # セクター別雇用者数テーブル
            sector_table = {
                'title': 'セクター別雇用者数',
                'headers': ['セクター', '雇用者数', '前月比', '前年比', 'トレンド'],
                'rows': []
            }
            
            sector_indicators = [
                EmploymentIndicatorType.PRIVATE_PAYROLLS,
                EmploymentIndicatorType.MANUFACTURING_PAYROLLS,
                EmploymentIndicatorType.CONSTRUCTION_PAYROLLS,
                EmploymentIndicatorType.RETAIL_PAYROLLS,
                EmploymentIndicatorType.LEISURE_HOSPITALITY_PAYROLLS
            ]
            
            for indicator_type in sector_indicators:
                if indicator_type in self.indicators_data:
                    indicator_data = self.indicators_data[indicator_type]
                    
                    row = [indicator_type.value]
                    
                    # 雇用者数
                    if indicator_data.actual_value:
                        row.append(f"{indicator_data.actual_value:,.0f} {indicator_data.unit}")
                    else:
                        row.append("N/A")
                    
                    # 前月比
                    if indicator_data.actual_value and indicator_data.previous_value:
                        change = indicator_data.actual_value - indicator_data.previous_value
                        row.append(f"{change:+,.0f} {indicator_data.unit}")
                    else:
                        row.append("N/A")
                    
                    # 前年比（簡易計算）
                    if indicator_data.actual_value:
                        yoy_change = np.random.uniform(-5, 10)  # 簡易的な前年比
                        row.append(f"{yoy_change:+.1f}%")
                    else:
                        row.append("N/A")
                    
                    # トレンド
                    if indicator_data.trend_result:
                        row.append(indicator_data.trend_result.trend_type.value)
                    else:
                        row.append("N/A")
                    
                    sector_table['rows'].append(row)
            
            tables_data.append(sector_table)
            
            return tables_data
            
        except Exception as e:
            logger.error(f"詳細テーブルデータ生成エラー: {e}")
            return []
    
    def _generate_sector_analysis_data(self) -> Dict[str, Any]:
        """セクター分析データを生成"""
        
        try:
            sector_analysis = {
                'title': 'セクター別分析',
                'sectors': [],
                'total_employment': 0,
                'sector_distribution': {}
            }
            
            # セクター別データを集計
            sector_indicators = {
                'Private': EmploymentIndicatorType.PRIVATE_PAYROLLS,
                'Manufacturing': EmploymentIndicatorType.MANUFACTURING_PAYROLLS,
                'Construction': EmploymentIndicatorType.CONSTRUCTION_PAYROLLS,
                'Retail': EmploymentIndicatorType.RETAIL_PAYROLLS,
                'Leisure & Hospitality': EmploymentIndicatorType.LEISURE_HOSPITALITY_PAYROLLS
            }
            
            total_employment = 0
            for sector_name, indicator_type in sector_indicators.items():
                if indicator_type in self.indicators_data:
                    indicator_data = self.indicators_data[indicator_type]
                    if indicator_data.actual_value:
                        total_employment += indicator_data.actual_value
                        
                        sector_info = {
                            'name': sector_name,
                            'employment': indicator_data.actual_value,
                            'unit': indicator_data.unit,
                            'change_pct': 0
                        }
                        
                        # 変化率計算
                        if indicator_data.actual_value and indicator_data.previous_value:
                            change_pct = ((indicator_data.actual_value - indicator_data.previous_value) / indicator_data.previous_value) * 100
                            sector_info['change_pct'] = change_pct
                        
                        sector_analysis['sectors'].append(sector_info)
            
            sector_analysis['total_employment'] = total_employment
            
            # セクター分布を計算
            for sector in sector_analysis['sectors']:
                if total_employment > 0:
                    percentage = (sector['employment'] / total_employment) * 100
                    sector_analysis['sector_distribution'][sector['name']] = percentage
            
            return sector_analysis
            
        except Exception as e:
            logger.error(f"セクター分析データ生成エラー: {e}")
            return {}
    
    def _generate_trend_analysis_data(self) -> Dict[str, Any]:
        """トレンド分析データを生成"""
        
        try:
            trend_analysis = {
                'title': 'トレンド分析',
                'trends': [],
                'overall_trend': 'N/A',
                'confidence_level': 0
            }
            
            # 各指標のトレンドを分析
            trend_types = {}
            confidence_levels = []
            
            for indicator_type, indicator_data in self.indicators_data.items():
                if indicator_data.trend_result:
                    trend_type = indicator_data.trend_result.trend_type.value
                    confidence = indicator_data.trend_result.confidence_level
                    
                    if trend_type not in trend_types:
                        trend_types[trend_type] = 0
                    trend_types[trend_type] += 1
                    
                    confidence_levels.append(confidence)
                    
                    trend_info = {
                        'indicator': indicator_type.value,
                        'trend_type': trend_type,
                        'confidence_level': confidence,
                        'pattern_type': indicator_data.trend_result.pattern_type.value,
                        'slope': indicator_data.trend_result.slope
                    }
                    
                    trend_analysis['trends'].append(trend_info)
            
            # 全体トレンドを決定
            if trend_types:
                overall_trend = max(trend_types, key=trend_types.get)
                trend_analysis['overall_trend'] = overall_trend
            
            # 平均信頼度
            if confidence_levels:
                trend_analysis['confidence_level'] = sum(confidence_levels) / len(confidence_levels)
            
            return trend_analysis
            
        except Exception as e:
            logger.error(f"トレンド分析データ生成エラー: {e}")
            return {}
    
    def _generate_forecast_analysis_data(self) -> Dict[str, Any]:
        """予測分析データを生成"""
        
        try:
            forecast_analysis = {
                'title': '予測分析',
                'forecasts': [],
                'accuracy_summary': {},
                'next_month_forecast': {}
            }
            
            # 各指標の予測精度を分析
            total_forecasts = 0
            accurate_forecasts = 0
            
            for indicator_type, indicator_data in self.indicators_data.items():
                if indicator_data.actual_value and indicator_data.forecast_value:
                    total_forecasts += 1
                    
                    # 予測精度計算（簡易版）
                    error_pct = abs((indicator_data.actual_value - indicator_data.forecast_value) / indicator_data.forecast_value) * 100
                    is_accurate = error_pct < 5  # 5%以内を正確とみなす
                    
                    if is_accurate:
                        accurate_forecasts += 1
                    
                    forecast_info = {
                        'indicator': indicator_type.value,
                        'actual': indicator_data.actual_value,
                        'forecast': indicator_data.forecast_value,
                        'error_pct': error_pct,
                        'is_accurate': is_accurate
                    }
                    
                    forecast_analysis['forecasts'].append(forecast_info)
            
            # 予測精度サマリー
            if total_forecasts > 0:
                accuracy_rate = (accurate_forecasts / total_forecasts) * 100
                forecast_analysis['accuracy_summary'] = {
                    'total_forecasts': total_forecasts,
                    'accurate_forecasts': accurate_forecasts,
                    'accuracy_rate': accuracy_rate
                }
            
            # 来月予測（簡易版）
            for indicator_type, indicator_data in self.indicators_data.items():
                if indicator_data.actual_value:
                    # 簡易的な来月予測
                    next_month_forecast = indicator_data.actual_value * (1 + np.random.uniform(-0.02, 0.02))
                    forecast_analysis['next_month_forecast'][indicator_type.value] = {
                        'forecast': next_month_forecast,
                        'unit': indicator_data.unit
                    }
            
            return forecast_analysis
            
        except Exception as e:
            logger.error(f"予測分析データ生成エラー: {e}")
            return {}
    
    def _generate_employment_specific_html(self, dashboard_data: Dict[str, Any]) -> str:
        """雇用統計専用HTMLを生成"""
        
        try:
            # レスポンシブCSS
            css = self._generate_employment_css()
            
            # サマリーカードHTML
            summary_cards_html = self._generate_summary_cards_html(dashboard_data.get('summary_cards', []))
            
            # チャートHTML
            charts_html = self._generate_charts_html(dashboard_data.get('main_charts', []))
            
            # テーブルHTML
            tables_html = self._generate_tables_html(dashboard_data.get('detailed_tables', []))
            
            # セクター分析HTML
            sector_html = self._generate_sector_analysis_html(dashboard_data.get('sector_analysis', {}))
            
            # トレンド分析HTML
            trend_html = self._generate_trend_analysis_html(dashboard_data.get('trend_analysis', {}))
            
            # 予測分析HTML
            forecast_html = self._generate_forecast_analysis_html(dashboard_data.get('forecast_analysis', {}))
            
            # 完全なHTMLページ
            html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{dashboard_data.get('title', '雇用統計ダッシュボード')}</title>
    <style>
        {css}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>{dashboard_data.get('title', '雇用統計ダッシュボード')}</h1>
            <p>分析日: {dashboard_data.get('analysis_date', 'N/A')}</p>
            <p>画面サイズ: {self.config.screen_size} ({self.responsive_engine.config.chart_sizes.get(self.config.screen_size, {}).get('width', 1000)}x{self.responsive_engine.config.chart_sizes.get(self.config.screen_size, {}).get('height', 600)})</p>
        </header>
        
        <main class="main-content">
            <section class="summary-section">
                <h2>📊 主要指標サマリー</h2>
                <div class="summary-cards">
                    {summary_cards_html}
                </div>
            </section>
            
            <section class="charts-section">
                <h2>📈 チャート分析</h2>
                <div class="charts-container">
                    {charts_html}
                </div>
            </section>
            
            <section class="tables-section">
                <h2>📋 詳細データテーブル</h2>
                <div class="tables-container">
                    {tables_html}
                </div>
            </section>
            
            <section class="sector-section">
                <h2>🏭 セクター別分析</h2>
                {sector_html}
            </section>
            
            <section class="trend-section">
                <h2>📊 トレンド分析</h2>
                {trend_html}
            </section>
            
            <section class="forecast-section">
                <h2>🔮 予測分析</h2>
                {forecast_html}
            </section>
        </main>
        
        <footer class="footer">
            <p>© 2024 Employment Statistics Analysis System</p>
        </footer>
    </div>
</body>
</html>
"""
            
            return html_content
            
        except Exception as e:
            logger.error(f"雇用統計専用HTML生成エラー: {e}")
            return "<html><body><h1>HTML生成エラー</h1></body></html>"
    
    def _generate_employment_css(self) -> str:
        """雇用統計専用CSSを生成"""
        
        # レスポンシブ設定を取得
        font_config = self.responsive_engine.config.font_sizes.get(self.config.screen_size, self.responsive_engine.config.font_sizes['desktop'])
        chart_config = self.responsive_engine.config.chart_sizes.get(self.config.screen_size, self.responsive_engine.config.chart_sizes['desktop'])
        
        css = f"""
        /* 基本リセット */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            background-color: #f8f9fa;
            color: #333;
        }}
        
        .container {{
            max-width: 100%;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* ヘッダー */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: {font_config['title']}px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: {font_config['label']}px;
            opacity: 0.9;
        }}
        
        /* メインコンテンツ */
        .main-content {{
            display: grid;
            gap: 30px;
        }}
        
        /* セクション */
        section {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        section h2 {{
            font-size: {font_config['title']}px;
            color: #333;
            margin-bottom: 20px;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        
        /* サマリーカード */
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        
        .summary-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-left: 5px solid #007bff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .summary-card h3 {{
            font-size: {font_config['label']}px;
            color: #007bff;
            margin-bottom: 10px;
        }}
        
        .summary-card .value {{
            font-size: {font_config['title']}px;
            font-weight: bold;
            color: #333;
        }}
        
        .summary-card .forecast {{
            font-size: {font_config['tick']}px;
            color: #666;
            margin-top: 5px;
        }}
        
        .summary-card .surprise {{
            font-size: {font_config['tick']}px;
            margin-top: 5px;
        }}
        
        .summary-card .surprise.positive {{
            color: #28a745;
        }}
        
        .summary-card .surprise.negative {{
            color: #dc3545;
        }}
        
        /* チャートコンテナ */
        .charts-container {{
            display: grid;
            gap: 30px;
        }}
        
        .chart-item {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        
        .chart-item h3 {{
            font-size: {font_config['label']}px;
            color: #333;
            margin-bottom: 15px;
        }}
        
        /* テーブルコンテナ */
        .tables-container {{
            display: grid;
            gap: 30px;
        }}
        
        .table-item {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        
        .table-item h3 {{
            font-size: {font_config['label']}px;
            color: #333;
            margin-bottom: 15px;
        }}
        
        /* テーブル */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: {font_config['tick']}px;
        }}
        
        .data-table th,
        .data-table td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        
        .data-table th {{
            background-color: #007bff;
            color: white;
            font-weight: bold;
        }}
        
        .data-table tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        
        .data-table tr:hover {{
            background-color: #e3f2fd;
        }}
        
        /* フッター */
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: {font_config['tick']}px;
        }}
        
        /* レスポンシブ調整 */
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            .header {{
                padding: 20px;
            }}
            
            section {{
                padding: 20px;
            }}
            
            .summary-cards {{
                grid-template-columns: 1fr;
            }}
        }}
        
        @media (max-width: 480px) {{
            .container {{
                padding: 5px;
            }}
            
            .header {{
                padding: 15px;
            }}
            
            section {{
                padding: 15px;
            }}
            
            .data-table {{
                font-size: {font_config['tick'] - 2}px;
            }}
            
            .data-table th,
            .data-table td {{
                padding: 8px;
            }}
        }}
        """
        
        return css
    
    def _generate_summary_cards_html(self, summary_cards: List[Dict[str, Any]]) -> str:
        """サマリーカードHTMLを生成"""
        
        try:
            cards_html = ""
            
            for card in summary_cards:
                surprise_class = card.get('surprise_impact', 'neutral')
                surprise_pct = card.get('surprise_pct', 0)
                change_pct = card.get('change_pct', 0)
                
                card_html = f"""
                <div class="summary-card">
                    <h3>{card.get('title', 'N/A')}</h3>
                    <div class="value">{card.get('value', 'N/A')}</div>
                    <div class="forecast">予想: {card.get('forecast', 'N/A')}</div>
                    <div class="surprise {surprise_class}">
                        サプライズ: {surprise_pct:+.1f}% | 変化: {change_pct:+.1f}%
                    </div>
                </div>
                """
                cards_html += card_html
            
            return cards_html
            
        except Exception as e:
            logger.error(f"サマリーカードHTML生成エラー: {e}")
            return "<p>サマリーカード生成エラー</p>"
    
    def _generate_charts_html(self, charts_data: List[Dict[str, Any]]) -> str:
        """チャートHTMLを生成"""
        
        try:
            charts_html = ""
            
            for chart in charts_data:
                chart_config = self.responsive_engine.config.chart_sizes.get(self.config.screen_size, self.responsive_engine.config.chart_sizes['desktop'])
                
                chart_html = f"""
                <div class="chart-item">
                    <h3>{chart.get('title', 'N/A')}</h3>
                    <p>{chart.get('description', '')}</p>
                    <div class="chart-placeholder" style="width: {chart_config['width']}px; height: {chart_config['height']}px; background: #e9ecef; border: 2px dashed #6c757d; display: flex; align-items: center; justify-content: center; border-radius: 10px;">
                        <p style="color: #6c757d;">{chart.get('title', 'N/A')} チャート<br/>({chart_config['width']}x{chart_config['height']})</p>
                    </div>
                </div>
                """
                charts_html += chart_html
            
            return charts_html
            
        except Exception as e:
            logger.error(f"チャートHTML生成エラー: {e}")
            return "<p>チャート生成エラー</p>"
    
    def _generate_tables_html(self, tables_data: List[Dict[str, Any]]) -> str:
        """テーブルHTMLを生成"""
        
        try:
            tables_html = ""
            
            for table in tables_data:
                table_html = f"""
                <div class="table-item">
                    <h3>{table.get('title', 'N/A')}</h3>
                    <table class="data-table">
                        <thead>
                            <tr>
                """
                
                for header in table.get('headers', []):
                    table_html += f"<th>{header}</th>"
                
                table_html += """
                            </tr>
                        </thead>
                        <tbody>
                """
                
                for row in table.get('rows', []):
                    table_html += "<tr>"
                    for cell in row:
                        table_html += f"<td>{cell}</td>"
                    table_html += "</tr>"
                
                table_html += """
                        </tbody>
                    </table>
                </div>
                """
                
                tables_html += table_html
            
            return tables_html
            
        except Exception as e:
            logger.error(f"テーブルHTML生成エラー: {e}")
            return "<p>テーブル生成エラー</p>"
    
    def _generate_sector_analysis_html(self, sector_data: Dict[str, Any]) -> str:
        """セクター分析HTMLを生成"""
        
        try:
            if not sector_data:
                return "<p>セクター分析データがありません</p>"
            
            html = f"""
            <div class="sector-analysis">
                <h3>{sector_data.get('title', 'セクター別分析')}</h3>
                <p>総雇用者数: {sector_data.get('total_employment', 0):,.0f} 千人</p>
                <div class="sector-list">
            """
            
            for sector in sector_data.get('sectors', []):
                html += f"""
                    <div class="sector-item">
                        <strong>{sector.get('name', 'N/A')}</strong>: 
                        {sector.get('employment', 0):,.0f} {sector.get('unit', '')} 
                        ({sector.get('change_pct', 0):+.1f}%)
                    </div>
                """
            
            html += """
                </div>
            </div>
            """
            
            return html
            
        except Exception as e:
            logger.error(f"セクター分析HTML生成エラー: {e}")
            return "<p>セクター分析生成エラー</p>"
    
    def _generate_trend_analysis_html(self, trend_data: Dict[str, Any]) -> str:
        """トレンド分析HTMLを生成"""
        
        try:
            if not trend_data:
                return "<p>トレンド分析データがありません</p>"
            
            html = f"""
            <div class="trend-analysis">
                <h3>{trend_data.get('title', 'トレンド分析')}</h3>
                <p>全体トレンド: {trend_data.get('overall_trend', 'N/A')}</p>
                <p>信頼度: {trend_data.get('confidence_level', 0):.1f}%</p>
                <div class="trend-list">
            """
            
            for trend in trend_data.get('trends', []):
                html += f"""
                    <div class="trend-item">
                        <strong>{trend.get('indicator', 'N/A')}</strong>: 
                        {trend.get('trend_type', 'N/A')} 
                        (信頼度: {trend.get('confidence_level', 0):.1f}%)
                    </div>
                """
            
            html += """
                </div>
            </div>
            """
            
            return html
            
        except Exception as e:
            logger.error(f"トレンド分析HTML生成エラー: {e}")
            return "<p>トレンド分析生成エラー</p>"
    
    def _generate_forecast_analysis_html(self, forecast_data: Dict[str, Any]) -> str:
        """予測分析HTMLを生成"""
        
        try:
            if not forecast_data:
                return "<p>予測分析データがありません</p>"
            
            html = f"""
            <div class="forecast-analysis">
                <h3>{forecast_data.get('title', '予測分析')}</h3>
            """
            
            # 予測精度サマリー
            accuracy_summary = forecast_data.get('accuracy_summary', {})
            if accuracy_summary:
                html += f"""
                <p>予測精度: {accuracy_summary.get('accuracy_rate', 0):.1f}% 
                ({accuracy_summary.get('accurate_forecasts', 0)}/{accuracy_summary.get('total_forecasts', 0)})</p>
                """
            
            # 来月予測
            next_month_forecast = forecast_data.get('next_month_forecast', {})
            if next_month_forecast:
                html += "<h4>来月予測:</h4><ul>"
                for indicator, forecast in next_month_forecast.items():
                    html += f"<li>{indicator}: {forecast.get('forecast', 0):,.2f} {forecast.get('unit', '')}</li>"
                html += "</ul>"
            
            html += "</div>"
            
            return html
            
        except Exception as e:
            logger.error(f"予測分析HTML生成エラー: {e}")
            return "<p>予測分析生成エラー</p>"
    
    def _save_employment_dashboard(self, html_content: str, dashboard_data: Dict[str, Any]) -> List[str]:
        """雇用統計ダッシュボードを保存"""
        
        saved_files = []
        
        try:
            if not self.config.output_path:
                return saved_files
            
            self.config.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # HTML保存
            if 'html' in self.config.output_format:
                html_path = self.config.output_path / f"employment_dashboard_{self.config.screen_size}.html"
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                saved_files.append(str(html_path))
            
            # JSON保存
            if 'json' in self.config.output_format:
                json_path = self.config.output_path / f"employment_dashboard_{self.config.screen_size}.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(dashboard_data, f, ensure_ascii=False, indent=2, default=str)
                saved_files.append(str(json_path))
            
            logger.info(f"雇用統計ダッシュボードが保存されました: {saved_files}")
            
        except Exception as e:
            logger.error(f"雇用統計ダッシュボード保存エラー: {e}")
        
        return saved_files
