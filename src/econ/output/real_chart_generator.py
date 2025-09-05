"""
Real Chart Generator for Economic Indicators
経済指標実チャート生成器

実際のPlotlyチャートを生成するシステム
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json

# 可視化ライブラリ
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff

logger = logging.getLogger(__name__)


class RealChartGenerator:
    """実チャート生成器"""
    
    def __init__(self):
        # モダンなカラーパレット
        self.colors = {
            'primary': '#2563eb',
            'secondary': '#7c3aed',
            'accent': '#06b6d4',
            'success': '#10b981',
            'warning': '#f59e0b',
            'error': '#ef4444',
            'neutral': '#6b7280'
        }
        
        # グラデーション
        self.gradients = {
            'primary': ['#667eea', '#764ba2'],
            'success': ['#11998e', '#38ef7d'],
            'warning': ['#f093fb', '#f5576c'],
            'info': ['#4facfe', '#00f2fe']
        }
    
    def generate_employment_trend_chart(self, data: Dict[str, Any]) -> str:
        """雇用者数推移チャートを生成"""
        
        try:
            # サンプルデータ（実際の実装ではAPIから取得）
            dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='MS')
            employment_data = np.random.normal(150000, 5000, len(dates)).cumsum() + 150000
            
            # 移動平均
            ma_3 = pd.Series(employment_data).rolling(window=3).mean()
            ma_12 = pd.Series(employment_data).rolling(window=12).mean()
            
            # チャート作成
            fig = go.Figure()
            
            # メインデータ
            fig.add_trace(go.Scatter(
                x=dates,
                y=employment_data,
                mode='lines+markers',
                name='Non-Farm Payrolls',
                line=dict(color=self.colors['primary'], width=3),
                marker=dict(size=6, color=self.colors['primary']),
                hovertemplate='<b>%{x|%Y年%m月}</b><br>雇用者数: %{y:,.0f}千人<extra></extra>'
            ))
            
            # 3ヶ月移動平均
            fig.add_trace(go.Scatter(
                x=dates,
                y=ma_3,
                mode='lines',
                name='3ヶ月移動平均',
                line=dict(color=self.colors['accent'], width=2, dash='dash'),
                hovertemplate='<b>%{x|%Y年%m月}</b><br>3ヶ月移動平均: %{y:,.0f}千人<extra></extra>'
            ))
            
            # 12ヶ月移動平均
            fig.add_trace(go.Scatter(
                x=dates,
                y=ma_12,
                mode='lines',
                name='12ヶ月移動平均',
                line=dict(color=self.colors['secondary'], width=2, dash='dot'),
                hovertemplate='<b>%{x|%Y年%m月}</b><br>12ヶ月移動平均: %{y:,.0f}千人<extra></extra>'
            ))
            
            # レイアウト設定
            fig.update_layout(
                title=dict(
                    text='<b>Non-Farm Payrolls 推移</b>',
                    x=0.5,
                    font=dict(size=20, color='#1f2937')
                ),
                xaxis=dict(
                    title='日付',
                    gridcolor='rgba(0,0,0,0.1)',
                    showgrid=True,
                    tickformat='%Y年%m月'
                ),
                yaxis=dict(
                    title='雇用者数 (千人)',
                    gridcolor='rgba(0,0,0,0.1)',
                    showgrid=True,
                    tickformat=',.0f'
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, sans-serif', size=12),
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=1.02,
                    xanchor='right',
                    x=1
                ),
                margin=dict(l=50, r=50, t=80, b=50),
                height=400
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id='employment_trend_chart')
            
        except Exception as e:
            logger.error(f"雇用者数推移チャート生成エラー: {e}")
            return f"<p>チャート生成エラー: {e}</p>"
    
    def generate_unemployment_rate_chart(self, data: Dict[str, Any]) -> str:
        """失業率推移チャートを生成"""
        
        try:
            # サンプルデータ
            dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='MS')
            unemployment_data = np.random.normal(3.8, 0.2, len(dates))
            
            # チャート作成
            fig = go.Figure()
            
            # 失業率
            fig.add_trace(go.Scatter(
                x=dates,
                y=unemployment_data,
                mode='lines+markers',
                name='失業率',
                line=dict(color=self.colors['error'], width=3),
                marker=dict(size=6, color=self.colors['error']),
                fill='tonexty',
                fillcolor='rgba(239, 68, 68, 0.1)',
                hovertemplate='<b>%{x|%Y年%m月}</b><br>失業率: %{y:.2f}%<extra></extra>'
            ))
            
            # レイアウト設定
            fig.update_layout(
                title=dict(
                    text='<b>失業率推移</b>',
                    x=0.5,
                    font=dict(size=20, color='#1f2937')
                ),
                xaxis=dict(
                    title='日付',
                    gridcolor='rgba(0,0,0,0.1)',
                    showgrid=True,
                    tickformat='%Y年%m月'
                ),
                yaxis=dict(
                    title='失業率 (%)',
                    gridcolor='rgba(0,0,0,0.1)',
                    showgrid=True,
                    tickformat='.2f'
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, sans-serif', size=12),
                margin=dict(l=50, r=50, t=80, b=50),
                height=400
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id='unemployment_rate_chart')
            
        except Exception as e:
            logger.error(f"失業率推移チャート生成エラー: {e}")
            return f"<p>チャート生成エラー: {e}</p>"
    
    def generate_wage_growth_chart(self, data: Dict[str, Any]) -> str:
        """賃金成長チャートを生成"""
        
        try:
            # サンプルデータ
            dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='MS')
            wage_data = np.random.normal(28.0, 0.5, len(dates)).cumsum() * 0.1 + 28.0
            
            # チャート作成
            fig = go.Figure()
            
            # 賃金
            fig.add_trace(go.Scatter(
                x=dates,
                y=wage_data,
                mode='lines+markers',
                name='平均時給',
                line=dict(color=self.colors['success'], width=3),
                marker=dict(size=6, color=self.colors['success']),
                hovertemplate='<b>%{x|%Y年%m月}</b><br>平均時給: $%{y:.2f}<extra></extra>'
            ))
            
            # レイアウト設定
            fig.update_layout(
                title=dict(
                    text='<b>平均時給推移</b>',
                    x=0.5,
                    font=dict(size=20, color='#1f2937')
                ),
                xaxis=dict(
                    title='日付',
                    gridcolor='rgba(0,0,0,0.1)',
                    showgrid=True,
                    tickformat='%Y年%m月'
                ),
                yaxis=dict(
                    title='平均時給 ($)',
                    gridcolor='rgba(0,0,0,0.1)',
                    showgrid=True,
                    tickformat='$.2f'
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, sans-serif', size=12),
                margin=dict(l=50, r=50, t=80, b=50),
                height=400
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id='wage_growth_chart')
            
        except Exception as e:
            logger.error(f"賃金成長チャート生成エラー: {e}")
            return f"<p>チャート生成エラー: {e}</p>"
    
    def generate_surprise_analysis_chart(self, data: Dict[str, Any]) -> str:
        """サプライズ分析チャートを生成"""
        
        try:
            # サンプルデータ
            indicators = ['NFP', '失業率', '平均賃金', '労働参加率', '製造業雇用', '建設業雇用']
            surprises = np.random.normal(0, 5, len(indicators))
            
            # 色を決定
            colors = [self.colors['success'] if x > 0 else self.colors['error'] for x in surprises]
            
            # チャート作成
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=indicators,
                y=surprises,
                marker_color=colors,
                hovertemplate='<b>%{x}</b><br>サプライズ: %{y:+.1f}%<extra></extra>',
                text=[f'{x:+.1f}%' for x in surprises],
                textposition='auto'
            ))
            
            # レイアウト設定
            fig.update_layout(
                title=dict(
                    text='<b>サプライズ分析</b>',
                    x=0.5,
                    font=dict(size=20, color='#1f2937')
                ),
                xaxis=dict(
                    title='指標',
                    gridcolor='rgba(0,0,0,0.1)',
                    showgrid=True
                ),
                yaxis=dict(
                    title='サプライズ (%)',
                    gridcolor='rgba(0,0,0,0.1)',
                    showgrid=True,
                    tickformat='+.1f'
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, sans-serif', size=12),
                margin=dict(l=50, r=50, t=80, b=50),
                height=400
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id='surprise_analysis_chart')
            
        except Exception as e:
            logger.error(f"サプライズ分析チャート生成エラー: {e}")
            return f"<p>チャート生成エラー: {e}</p>"
    
    def generate_sector_analysis_chart(self, data: Dict[str, Any]) -> str:
        """セクター分析チャートを生成"""
        
        try:
            # サンプルデータ
            sectors = ['民間部門', '製造業', '建設業', '小売業', 'レジャー・ホスピタリティ', '政府部門']
            employment = [130000, 13000, 8000, 15000, 12000, 20000]
            changes = np.random.normal(0, 2, len(sectors))
            
            # チャート作成
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=sectors,
                y=employment,
                marker_color=self.colors['primary'],
                hovertemplate='<b>%{x}</b><br>雇用者数: %{y:,.0f}千人<extra></extra>',
                text=[f'{x:,.0f}千人' for x in employment],
                textposition='auto'
            ))
            
            # レイアウト設定
            fig.update_layout(
                title=dict(
                    text='<b>セクター別雇用者数</b>',
                    x=0.5,
                    font=dict(size=20, color='#1f2937')
                ),
                xaxis=dict(
                    title='セクター',
                    gridcolor='rgba(0,0,0,0.1)',
                    showgrid=True
                ),
                yaxis=dict(
                    title='雇用者数 (千人)',
                    gridcolor='rgba(0,0,0,0.1)',
                    showgrid=True,
                    tickformat=',.0f'
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, sans-serif', size=12),
                margin=dict(l=50, r=50, t=80, b=50),
                height=400
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id='sector_analysis_chart')
            
        except Exception as e:
            logger.error(f"セクター分析チャート生成エラー: {e}")
            return f"<p>チャート生成エラー: {e}</p>"
    
    def generate_correlation_heatmap(self, data: Dict[str, Any]) -> str:
        """相関ヒートマップを生成"""
        
        try:
            # サンプルデータ
            indicators = ['NFP', '失業率', '平均賃金', '労働参加率', '製造業雇用', '建設業雇用']
            correlation_matrix = np.random.uniform(-1, 1, (len(indicators), len(indicators)))
            correlation_matrix = (correlation_matrix + correlation_matrix.T) / 2
            np.fill_diagonal(correlation_matrix, 1)
            
            # チャート作成
            fig = go.Figure(data=go.Heatmap(
                z=correlation_matrix,
                x=indicators,
                y=indicators,
                colorscale='RdBu',
                zmid=0,
                hovertemplate='<b>%{y} vs %{x}</b><br>相関係数: %{z:.3f}<extra></extra>',
                text=np.round(correlation_matrix, 3),
                texttemplate='%{text}',
                textfont={'size': 10}
            ))
            
            # レイアウト設定
            fig.update_layout(
                title=dict(
                    text='<b>指標間相関ヒートマップ</b>',
                    x=0.5,
                    font=dict(size=20, color='#1f2937')
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, sans-serif', size=12),
                margin=dict(l=50, r=50, t=80, b=50),
                height=400
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id='correlation_heatmap')
            
        except Exception as e:
            logger.error(f"相関ヒートマップ生成エラー: {e}")
            return f"<p>チャート生成エラー: {e}</p>"
    
    def generate_all_charts(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """全チャートを生成"""
        
        charts = []
        
        try:
            # 雇用者数推移チャート
            charts.append({
                'title': 'Non-Farm Payrolls 推移',
                'html': self.generate_employment_trend_chart(data)
            })
            
            # 失業率推移チャート
            charts.append({
                'title': '失業率推移',
                'html': self.generate_unemployment_rate_chart(data)
            })
            
            # 賃金成長チャート
            charts.append({
                'title': '平均時給推移',
                'html': self.generate_wage_growth_chart(data)
            })
            
            # サプライズ分析チャート
            charts.append({
                'title': 'サプライズ分析',
                'html': self.generate_surprise_analysis_chart(data)
            })
            
            # セクター分析チャート
            charts.append({
                'title': 'セクター別雇用者数',
                'html': self.generate_sector_analysis_chart(data)
            })
            
            # 相関ヒートマップ
            charts.append({
                'title': '指標間相関ヒートマップ',
                'html': self.generate_correlation_heatmap(data)
            })
            
            logger.info(f"全チャート生成完了: {len(charts)}個")
            
        except Exception as e:
            logger.error(f"全チャート生成エラー: {e}")
        
        return charts
