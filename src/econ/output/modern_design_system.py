"""
Modern Design System for Economic Indicators
経済指標モダンデザインシステム

スタイリッシュでスマートなデザインシステム
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
class ModernDesignConfig:
    """モダンデザイン設定"""
    
    # カラーパレット（モダンで洗練された色）
    color_palette: Dict[str, str] = field(default_factory=lambda: {
        'primary': '#2563eb',      # 鮮やかな青
        'secondary': '#7c3aed',    # 紫
        'accent': '#06b6d4',       # シアン
        'success': '#10b981',      # エメラルドグリーン
        'warning': '#f59e0b',      # アンバー
        'error': '#ef4444',        # レッド
        'neutral': '#6b7280',      # グレー
        'background': '#f8fafc',   # ライトグレー
        'surface': '#ffffff',      # 白
        'text_primary': '#1f2937', # ダークグレー
        'text_secondary': '#6b7280' # ミディアムグレー
    })
    
    # グラデーション
    gradients: Dict[str, str] = field(default_factory=lambda: {
        'primary': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'success': 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
        'warning': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        'info': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        'dark': 'linear-gradient(135deg, #2c3e50 0%, #34495e 100%)'
    })
    
    # タイポグラフィ
    typography: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        'font_family': "'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif",
        'font_sizes': {
            'xs': '0.75rem',    # 12px
            'sm': '0.875rem',   # 14px
            'base': '1rem',     # 16px
            'lg': '1.125rem',   # 18px
            'xl': '1.25rem',    # 20px
            '2xl': '1.5rem',    # 24px
            '3xl': '1.875rem',  # 30px
            '4xl': '2.25rem',   # 36px
            '5xl': '3rem'       # 48px
        },
        'font_weights': {
            'light': '300',
            'normal': '400',
            'medium': '500',
            'semibold': '600',
            'bold': '700',
            'extrabold': '800'
        }
    })
    
    # スペーシング
    spacing: Dict[str, str] = field(default_factory=lambda: {
        'xs': '0.25rem',   # 4px
        'sm': '0.5rem',    # 8px
        'md': '1rem',      # 16px
        'lg': '1.5rem',    # 24px
        'xl': '2rem',      # 32px
        '2xl': '3rem',     # 48px
        '3xl': '4rem'      # 64px
    })
    
    # ボーダーラディウス
    border_radius: Dict[str, str] = field(default_factory=lambda: {
        'sm': '0.375rem',  # 6px
        'md': '0.5rem',    # 8px
        'lg': '0.75rem',   # 12px
        'xl': '1rem',      # 16px
        '2xl': '1.5rem',   # 24px
        'full': '9999px'
    })
    
    # シャドウ
    shadows: Dict[str, str] = field(default_factory=lambda: {
        'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'xl': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
    })
    
    # アニメーション
    animations: Dict[str, str] = field(default_factory=lambda: {
        'fast': '0.15s ease-in-out',
        'normal': '0.3s ease-in-out',
        'slow': '0.5s ease-in-out'
    })


class ModernDesignSystem:
    """モダンデザインシステム"""
    
    def __init__(self, config: Optional[ModernDesignConfig] = None):
        self.config = config or ModernDesignConfig()
    
    def generate_modern_css(self, screen_size: str = "desktop") -> str:
        """モダンなCSSを生成"""
        
        # 画面サイズに応じた設定
        screen_configs = {
            'mobile': {'container_max_width': '100%', 'padding': '1rem', 'font_scale': 0.9},
            'tablet': {'container_max_width': '768px', 'padding': '1.5rem', 'font_scale': 1.0},
            'desktop': {'container_max_width': '1200px', 'padding': '2rem', 'font_scale': 1.0},
            'large_desktop': {'container_max_width': '1400px', 'padding': '2.5rem', 'font_scale': 1.1}
        }
        
        screen_config = screen_configs.get(screen_size, screen_configs['desktop'])
        font_scale = screen_config['font_scale']
        
        css = f"""
        /* モダンデザインシステム CSS */
        
        /* カスタムプロパティ */
        :root {{
            --color-primary: {self.config.color_palette['primary']};
            --color-secondary: {self.config.color_palette['secondary']};
            --color-accent: {self.config.color_palette['accent']};
            --color-success: {self.config.color_palette['success']};
            --color-warning: {self.config.color_palette['warning']};
            --color-error: {self.config.color_palette['error']};
            --color-neutral: {self.config.color_palette['neutral']};
            --color-background: {self.config.color_palette['background']};
            --color-surface: {self.config.color_palette['surface']};
            --color-text-primary: {self.config.color_palette['text_primary']};
            --color-text-secondary: {self.config.color_palette['text_secondary']};
            
            --font-family: {self.config.typography['font_family']};
            --font-size-xs: {self.config.typography['font_sizes']['xs']};
            --font-size-sm: {self.config.typography['font_sizes']['sm']};
            --font-size-base: {self.config.typography['font_sizes']['base']};
            --font-size-lg: {self.config.typography['font_sizes']['lg']};
            --font-size-xl: {self.config.typography['font_sizes']['xl']};
            --font-size-2xl: {self.config.typography['font_sizes']['2xl']};
            --font-size-3xl: {self.config.typography['font_sizes']['3xl']};
            --font-size-4xl: {self.config.typography['font_sizes']['4xl']};
            --font-size-5xl: {self.config.typography['font_sizes']['5xl']};
            
            --spacing-xs: {self.config.spacing['xs']};
            --spacing-sm: {self.config.spacing['sm']};
            --spacing-md: {self.config.spacing['md']};
            --spacing-lg: {self.config.spacing['lg']};
            --spacing-xl: {self.config.spacing['xl']};
            --spacing-2xl: {self.config.spacing['2xl']};
            --spacing-3xl: {self.config.spacing['3xl']};
            
            --border-radius-sm: {self.config.border_radius['sm']};
            --border-radius-md: {self.config.border_radius['md']};
            --border-radius-lg: {self.config.border_radius['lg']};
            --border-radius-xl: {self.config.border_radius['xl']};
            --border-radius-2xl: {self.config.border_radius['2xl']};
            --border-radius-full: {self.config.border_radius['full']};
            
            --shadow-sm: {self.config.shadows['sm']};
            --shadow-md: {self.config.shadows['md']};
            --shadow-lg: {self.config.shadows['lg']};
            --shadow-xl: {self.config.shadows['xl']};
            --shadow-2xl: {self.config.shadows['2xl']};
            
            --animation-fast: {self.config.animations['fast']};
            --animation-normal: {self.config.animations['normal']};
            --animation-slow: {self.config.animations['slow']};
            
            --font-scale: {font_scale};
        }}
        
        /* リセット */
        *, *::before, *::after {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        html {{
            font-size: calc(16px * var(--font-scale));
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        
        body {{
            font-family: var(--font-family);
            background: var(--color-background);
            color: var(--color-text-primary);
            overflow-x: hidden;
        }}
        
        /* コンテナ */
        .container {{
            max-width: {screen_config['container_max_width']};
            margin: 0 auto;
            padding: {screen_config['padding']};
        }}
        
        /* ヘッダー */
        .header {{
            background: {self.config.gradients['primary']};
            color: white;
            padding: var(--spacing-3xl) var(--spacing-2xl);
            border-radius: var(--border-radius-2xl);
            margin-bottom: var(--spacing-2xl);
            text-align: center;
            box-shadow: var(--shadow-xl);
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, rgba(255,255,255,0.1) 0%, transparent 100%);
            pointer-events: none;
        }}
        
        .header h1 {{
            font-size: var(--font-size-4xl);
            font-weight: {self.config.typography['font_weights']['bold']};
            margin-bottom: var(--spacing-md);
            position: relative;
            z-index: 1;
        }}
        
        .header .subtitle {{
            font-size: var(--font-size-lg);
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }}
        
        .header .meta {{
            font-size: var(--font-size-sm);
            opacity: 0.8;
            margin-top: var(--spacing-sm);
            position: relative;
            z-index: 1;
        }}
        
        /* メインコンテンツ */
        .main-content {{
            display: grid;
            gap: var(--spacing-2xl);
        }}
        
        /* セクション */
        .section {{
            background: var(--color-surface);
            border-radius: var(--border-radius-xl);
            padding: var(--spacing-2xl);
            box-shadow: var(--shadow-md);
            border: 1px solid rgba(0, 0, 0, 0.05);
            transition: all var(--animation-normal);
        }}
        
        .section:hover {{
            box-shadow: var(--shadow-lg);
            transform: translateY(-2px);
        }}
        
        .section h2 {{
            font-size: var(--font-size-2xl);
            font-weight: {self.config.typography['font_weights']['semibold']};
            color: var(--color-text-primary);
            margin-bottom: var(--spacing-xl);
            position: relative;
            padding-bottom: var(--spacing-md);
        }}
        
        .section h2::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 60px;
            height: 3px;
            background: {self.config.gradients['primary']};
            border-radius: var(--border-radius-full);
        }}
        
        /* サマリーカード */
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: var(--spacing-lg);
        }}
        
        .summary-card {{
            background: var(--color-surface);
            border-radius: var(--border-radius-xl);
            padding: var(--spacing-xl);
            box-shadow: var(--shadow-md);
            border: 1px solid rgba(0, 0, 0, 0.05);
            transition: all var(--animation-normal);
            position: relative;
            overflow: hidden;
        }}
        
        .summary-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: {self.config.gradients['primary']};
        }}
        
        .summary-card:hover {{
            box-shadow: var(--shadow-xl);
            transform: translateY(-4px);
        }}
        
        .summary-card h3 {{
            font-size: var(--font-size-lg);
            font-weight: {self.config.typography['font_weights']['medium']};
            color: var(--color-text-primary);
            margin-bottom: var(--spacing-md);
        }}
        
        .summary-card .value {{
            font-size: var(--font-size-3xl);
            font-weight: {self.config.typography['font_weights']['bold']};
            color: var(--color-primary);
            margin-bottom: var(--spacing-sm);
        }}
        
        .summary-card .forecast {{
            font-size: var(--font-size-sm);
            color: var(--color-text-secondary);
            margin-bottom: var(--spacing-xs);
        }}
        
        .summary-card .surprise {{
            font-size: var(--font-size-sm);
            font-weight: {self.config.typography['font_weights']['medium']};
            padding: var(--spacing-xs) var(--spacing-sm);
            border-radius: var(--border-radius-full);
            display: inline-block;
        }}
        
        .summary-card .surprise.positive {{
            background: rgba(16, 185, 129, 0.1);
            color: var(--color-success);
        }}
        
        .summary-card .surprise.negative {{
            background: rgba(239, 68, 68, 0.1);
            color: var(--color-error);
        }}
        
        /* チャートコンテナ */
        .charts-container {{
            display: grid;
            gap: var(--spacing-xl);
        }}
        
        .chart-item {{
            background: var(--color-surface);
            border-radius: var(--border-radius-xl);
            padding: var(--spacing-xl);
            box-shadow: var(--shadow-md);
            border: 1px solid rgba(0, 0, 0, 0.05);
            transition: all var(--animation-normal);
        }}
        
        .chart-item:hover {{
            box-shadow: var(--shadow-lg);
        }}
        
        .chart-item h3 {{
            font-size: var(--font-size-xl);
            font-weight: {self.config.typography['font_weights']['medium']};
            color: var(--color-text-primary);
            margin-bottom: var(--spacing-lg);
        }}
        
        .chart-container {{
            width: 100%;
            height: 400px;
            border-radius: var(--border-radius-lg);
            overflow: hidden;
            background: var(--color-background);
        }}
        
        /* テーブルコンテナ */
        .tables-container {{
            display: grid;
            gap: var(--spacing-xl);
        }}
        
        .table-item {{
            background: var(--color-surface);
            border-radius: var(--border-radius-xl);
            padding: var(--spacing-xl);
            box-shadow: var(--shadow-md);
            border: 1px solid rgba(0, 0, 0, 0.05);
            overflow: hidden;
        }}
        
        .table-item h3 {{
            font-size: var(--font-size-xl);
            font-weight: {self.config.typography['font_weights']['medium']};
            color: var(--color-text-primary);
            margin-bottom: var(--spacing-lg);
        }}
        
        /* テーブル */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: var(--font-size-sm);
            background: var(--color-surface);
            border-radius: var(--border-radius-lg);
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }}
        
        .data-table th {{
            background: {self.config.gradients['primary']};
            color: white;
            font-weight: {self.config.typography['font_weights']['medium']};
            padding: var(--spacing-md) var(--spacing-lg);
            text-align: left;
            font-size: var(--font-size-sm);
        }}
        
        .data-table td {{
            padding: var(--spacing-md) var(--spacing-lg);
            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            color: var(--color-text-primary);
        }}
        
        .data-table tr:hover {{
            background: rgba(37, 99, 235, 0.05);
        }}
        
        .data-table tr:last-child td {{
            border-bottom: none;
        }}
        
        /* フッター */
        .footer {{
            text-align: center;
            padding: var(--spacing-2xl);
            color: var(--color-text-secondary);
            font-size: var(--font-size-sm);
            margin-top: var(--spacing-3xl);
        }}
        
        /* レスポンシブ調整 */
        @media (max-width: 768px) {{
            .container {{
                padding: var(--spacing-md);
            }}
            
            .header {{
                padding: var(--spacing-2xl) var(--spacing-lg);
            }}
            
            .section {{
                padding: var(--spacing-lg);
            }}
            
            .summary-cards {{
                grid-template-columns: 1fr;
            }}
            
            .chart-container {{
                height: 300px;
            }}
        }}
        
        @media (max-width: 480px) {{
            .container {{
                padding: var(--spacing-sm);
            }}
            
            .header {{
                padding: var(--spacing-lg) var(--spacing-md);
            }}
            
            .section {{
                padding: var(--spacing-md);
            }}
            
            .data-table {{
                font-size: var(--font-size-xs);
            }}
            
            .data-table th,
            .data-table td {{
                padding: var(--spacing-sm);
            }}
        }}
        
        /* アニメーション */
        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .section {{
            animation: fadeInUp 0.6s ease-out;
        }}
        
        .summary-card {{
            animation: fadeInUp 0.6s ease-out;
        }}
        
        .summary-card:nth-child(2) {{
            animation-delay: 0.1s;
        }}
        
        .summary-card:nth-child(3) {{
            animation-delay: 0.2s;
        }}
        
        .summary-card:nth-child(4) {{
            animation-delay: 0.3s;
        }}
        """
        
        return css
    
    def generate_modern_html(
        self,
        data: Dict[str, Any],
        screen_size: str = "desktop"
    ) -> str:
        """モダンなHTMLを生成"""
        
        css = self.generate_modern_css(screen_size)
        
        # サマリーカードHTML
        summary_cards_html = self._generate_modern_summary_cards(data.get('summary_cards', []))
        
        # チャートHTML
        charts_html = self._generate_modern_charts(data.get('charts', []))
        
        # テーブルHTML
        tables_html = self._generate_modern_tables(data.get('tables', []))
        
        # 完全なHTMLページ
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data.get('title', '経済指標ダッシュボード')}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        {css}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>{data.get('title', '経済指標ダッシュボード')}</h1>
            <div class="subtitle">リアルタイム経済分析プラットフォーム</div>
            <div class="meta">
                分析日: {data.get('analysis_date', 'N/A')} | 
                画面サイズ: {screen_size} | 
                最終更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
            </div>
        </header>
        
        <main class="main-content">
            <section class="section">
                <h2>📊 主要指標サマリー</h2>
                <div class="summary-cards">
                    {summary_cards_html}
                </div>
            </section>
            
            <section class="section">
                <h2>📈 チャート分析</h2>
                <div class="charts-container">
                    {charts_html}
                </div>
            </section>
            
            <section class="section">
                <h2>📋 詳細データテーブル</h2>
                <div class="tables-container">
                    {tables_html}
                </div>
            </section>
        </main>
        
        <footer class="footer">
            <p>© 2024 Economic Indicators Analysis System | Powered by Modern Design System</p>
        </footer>
    </div>
</body>
</html>
"""
        
        return html_content
    
    def _generate_modern_summary_cards(self, summary_cards: List[Dict[str, Any]]) -> str:
        """モダンなサマリーカードHTMLを生成"""
        
        cards_html = ""
        
        for card in summary_cards:
            surprise_class = card.get('surprise_impact', 'neutral')
            surprise_pct = card.get('surprise_pct', 0)
            change_pct = card.get('change_pct', 0)
            
            # アイコンを決定
            icon = "📈" if surprise_pct > 0 else "📉" if surprise_pct < 0 else "➡️"
            
            card_html = f"""
            <div class="summary-card">
                <h3>{icon} {card.get('title', 'N/A')}</h3>
                <div class="value">{card.get('value', 'N/A')}</div>
                <div class="forecast">予想: {card.get('forecast', 'N/A')}</div>
                <div class="surprise {surprise_class}">
                    サプライズ: {surprise_pct:+.1f}% | 変化: {change_pct:+.1f}%
                </div>
            </div>
            """
            cards_html += card_html
        
        return cards_html
    
    def _generate_modern_charts(self, charts_data: List[Dict[str, Any]]) -> str:
        """モダンなチャートHTMLを生成"""
        
        charts_html = ""
        
        for chart in charts_data:
            chart_html = f"""
            <div class="chart-item">
                <h3>{chart.get('title', 'N/A')}</h3>
                <div class="chart-container">
                    {chart.get('html', '<p>チャートデータがありません</p>')}
                </div>
            </div>
            """
            charts_html += chart_html
        
        return charts_html
    
    def _generate_modern_tables(self, tables_data: List[Dict[str, Any]]) -> str:
        """モダンなテーブルHTMLを生成"""
        
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
