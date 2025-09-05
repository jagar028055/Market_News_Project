"""
Responsive Visualization System for Economic Indicators
経済指標レスポンシブ可視化システム

画面サイズに応じて調整される可視化システム
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
from dataclasses import dataclass, field

# 可視化ライブラリ
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff

logger = logging.getLogger(__name__)


@dataclass
class ResponsiveConfig:
    """レスポンシブ設定"""
    # 基本設定
    base_width: int = 1200
    base_height: int = 800
    
    # レスポンシブ設定
    mobile_width: int = 375
    tablet_width: int = 768
    desktop_width: int = 1200
    large_desktop_width: int = 1920
    
    # フォントサイズ（画面サイズに応じて調整）
    font_sizes: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        'mobile': {'title': 16, 'label': 12, 'tick': 10, 'annotation': 12},
        'tablet': {'title': 20, 'label': 14, 'tick': 12, 'annotation': 14},
        'desktop': {'title': 24, 'label': 16, 'tick': 14, 'annotation': 16},
        'large_desktop': {'title': 28, 'label': 18, 'tick': 16, 'annotation': 18}
    })
    
    # チャートサイズ（画面サイズに応じて調整）
    chart_sizes: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        'mobile': {'width': 350, 'height': 250},
        'tablet': {'width': 700, 'height': 400},
        'desktop': {'width': 1000, 'height': 600},
        'large_desktop': {'width': 1400, 'height': 800}
    })
    
    # 色設定
    color_palette: List[str] = field(default_factory=lambda: [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
    ])
    
    # 出力設定
    output_format: List[str] = field(default_factory=lambda: ["html", "png"])
    save_path: Optional[Path] = None


class ResponsiveVisualizationEngine:
    """レスポンシブ可視化エンジン"""
    
    def __init__(self, config: Optional[ResponsiveConfig] = None):
        self.config = config or ResponsiveConfig()
    
    def create_responsive_dashboard(
        self,
        data: Dict[str, Any],
        screen_size: str = "desktop"
    ) -> Dict[str, Any]:
        """レスポンシブダッシュボードを作成"""
        
        try:
            # 画面サイズに応じた設定を取得
            font_config = self.config.font_sizes.get(screen_size, self.config.font_sizes['desktop'])
            chart_config = self.config.chart_sizes.get(screen_size, self.config.chart_sizes['desktop'])
            
            # レスポンシブHTMLを生成
            html_content = self._generate_responsive_html(data, font_config, chart_config, screen_size)
            
            # ファイル保存
            saved_files = []
            if self.config.save_path:
                saved_files = self._save_responsive_dashboard(html_content, screen_size)
            
            return {
                'html': html_content,
                'screen_size': screen_size,
                'font_config': font_config,
                'chart_config': chart_config,
                'saved_files': saved_files,
                'type': 'responsive_dashboard'
            }
            
        except Exception as e:
            logger.error(f"レスポンシブダッシュボード作成エラー: {e}")
            return {'error': str(e)}
    
    def _generate_responsive_html(
        self,
        data: Dict[str, Any],
        font_config: Dict[str, int],
        chart_config: Dict[str, int],
        screen_size: str
    ) -> str:
        """レスポンシブHTMLを生成"""
        
        try:
            # 画面サイズに応じたCSS
            css = self._generate_responsive_css(font_config, chart_config, screen_size)
            
            # チャートHTML
            charts_html = self._generate_responsive_charts(data, chart_config, font_config)
            
            # テーブルHTML
            tables_html = self._generate_responsive_tables(data, font_config)
            
            # 完全なHTMLページ
            html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>経済指標レスポンシブダッシュボード</title>
    <style>
        {css}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>経済指標レスポンシブダッシュボード</h1>
            <p>画面サイズ: {screen_size} ({chart_config['width']}x{chart_config['height']})</p>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </header>
        
        <main class="main-content">
            <section class="summary-section">
                <h2>📊 サマリー</h2>
                <div class="summary-cards">
                    {self._generate_summary_cards(data)}
                </div>
            </section>
            
            <section class="charts-section">
                <h2>📈 チャート分析</h2>
                <div class="charts-container">
                    {charts_html}
                </div>
            </section>
            
            <section class="tables-section">
                <h2>📋 データテーブル</h2>
                <div class="tables-container">
                    {tables_html}
                </div>
            </section>
        </main>
        
        <footer class="footer">
            <p>© 2024 Economic Indicators Analysis System</p>
        </footer>
    </div>
</body>
</html>
"""
            
            return html_content
            
        except Exception as e:
            logger.error(f"レスポンシブHTML生成エラー: {e}")
            return "<html><body><h1>HTML生成エラー</h1></body></html>"
    
    def _generate_responsive_css(
        self,
        font_config: Dict[str, int],
        chart_config: Dict[str, int],
        screen_size: str
    ) -> str:
        """レスポンシブCSSを生成"""
        
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
        
        .summary-card .change {{
            font-size: {font_config['tick']}px;
            margin-top: 5px;
        }}
        
        .summary-card .change.positive {{
            color: #28a745;
        }}
        
        .summary-card .change.negative {{
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
    
    def _generate_responsive_charts(
        self,
        data: Dict[str, Any],
        chart_config: Dict[str, int],
        font_config: Dict[str, int]
    ) -> str:
        """レスポンシブチャートを生成"""
        
        try:
            charts_html = ""
            
            # サンプルチャート（実際の実装では data から生成）
            charts_data = [
                {
                    'title': '雇用者数推移',
                    'type': 'line',
                    'data': [150000, 152000, 154000, 156000, 158000, 160000]
                },
                {
                    'title': '失業率推移',
                    'type': 'line',
                    'data': [3.8, 3.7, 3.6, 3.5, 3.4, 3.3]
                },
                {
                    'title': '平均賃金推移',
                    'type': 'bar',
                    'data': [25.5, 26.0, 26.5, 27.0, 27.5, 28.0]
                }
            ]
            
            for chart_data in charts_data:
                # 簡易的なチャートHTML（実際の実装ではPlotlyを使用）
                chart_html = f"""
                <div class="chart-item">
                    <h3>{chart_data['title']}</h3>
                    <div class="chart-placeholder" style="width: {chart_config['width']}px; height: {chart_config['height']}px; background: #e9ecef; border: 2px dashed #6c757d; display: flex; align-items: center; justify-content: center; border-radius: 10px;">
                        <p style="color: #6c757d; font-size: {font_config['label']}px;">{chart_data['title']} チャート<br/>({chart_config['width']}x{chart_config['height']})</p>
                    </div>
                </div>
                """
                charts_html += chart_html
            
            return charts_html
            
        except Exception as e:
            logger.error(f"レスポンシブチャート生成エラー: {e}")
            return "<p>チャート生成エラー</p>"
    
    def _generate_responsive_tables(
        self,
        data: Dict[str, Any],
        font_config: Dict[str, int]
    ) -> str:
        """レスポンシブテーブルを生成"""
        
        try:
            tables_html = ""
            
            # サンプルテーブルデータ
            tables_data = [
                {
                    'title': '雇用統計サマリー',
                    'headers': ['指標', '実際値', '予想値', '前回値', '変化率'],
                    'rows': [
                        ['Non-Farm Payrolls', '168,954千人', '146,617千人', '143,563千人', '+15.2%'],
                        ['失業率', '3.7%', '3.8%', '3.8%', '-0.1%'],
                        ['平均賃金', '$28.50', '$28.00', '$27.80', '+2.5%'],
                        ['労働参加率', '62.8%', '62.7%', '62.6%', '+0.2%']
                    ]
                },
                {
                    'title': '詳細データ',
                    'headers': ['日付', '雇用者数', '失業率', '平均賃金', '労働参加率'],
                    'rows': [
                        ['2024-01', '168,954', '3.7%', '$28.50', '62.8%'],
                        ['2023-12', '143,563', '3.8%', '$27.80', '62.6%'],
                        ['2023-11', '140,200', '3.9%', '$27.60', '62.5%'],
                        ['2023-10', '138,500', '4.0%', '$27.40', '62.4%'],
                        ['2023-09', '136,800', '4.1%', '$27.20', '62.3%']
                    ]
                }
            ]
            
            for table_data in tables_data:
                table_html = f"""
                <div class="table-item">
                    <h3>{table_data['title']}</h3>
                    <table class="data-table">
                        <thead>
                            <tr>
                """
                
                for header in table_data['headers']:
                    table_html += f"<th>{header}</th>"
                
                table_html += """
                            </tr>
                        </thead>
                        <tbody>
                """
                
                for row in table_data['rows']:
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
            logger.error(f"レスポンシブテーブル生成エラー: {e}")
            return "<p>テーブル生成エラー</p>"
    
    def _generate_summary_cards(self, data: Dict[str, Any]) -> str:
        """サマリーカードを生成"""
        
        try:
            # サンプルサマリーデータ
            summary_data = [
                {
                    'title': 'Non-Farm Payrolls',
                    'value': '168,954千人',
                    'change': '+15.2%',
                    'change_type': 'positive'
                },
                {
                    'title': '失業率',
                    'value': '3.7%',
                    'change': '-0.1%',
                    'change_type': 'positive'
                },
                {
                    'title': '平均賃金',
                    'value': '$28.50',
                    'change': '+2.5%',
                    'change_type': 'positive'
                },
                {
                    'title': '労働参加率',
                    'value': '62.8%',
                    'change': '+0.2%',
                    'change_type': 'positive'
                }
            ]
            
            cards_html = ""
            for card_data in summary_data:
                card_html = f"""
                <div class="summary-card">
                    <h3>{card_data['title']}</h3>
                    <div class="value">{card_data['value']}</div>
                    <div class="change {card_data['change_type']}">{card_data['change']}</div>
                </div>
                """
                cards_html += card_html
            
            return cards_html
            
        except Exception as e:
            logger.error(f"サマリーカード生成エラー: {e}")
            return "<p>サマリーカード生成エラー</p>"
    
    def _save_responsive_dashboard(self, html_content: str, screen_size: str) -> List[str]:
        """レスポンシブダッシュボードを保存"""
        
        saved_files = []
        
        try:
            if not self.config.save_path:
                return saved_files
            
            self.config.save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # HTML保存
            if 'html' in self.config.output_format:
                html_path = self.config.save_path.with_name(f"responsive_dashboard_{screen_size}.html")
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                saved_files.append(str(html_path))
            
            logger.info(f"レスポンシブダッシュボードが保存されました: {saved_files}")
            
        except Exception as e:
            logger.error(f"レスポンシブダッシュボード保存エラー: {e}")
        
        return saved_files
