"""
Enhanced Visualization System for Economic Indicators
経済指標強化可視化システム

視認性を大幅に改善し、各指標の深度のある分析を提供
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
import matplotlib.pyplot as plt
import seaborn as sns

# 統計・分析ライブラリ
from scipy import stats
from scipy.stats import normaltest, jarque_bera
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

# 既存モジュール
from ..config.settings import EconConfig
from ..normalize.data_processor import ProcessedIndicator
from ..normalize.trend_analyzer import TrendResult

logger = logging.getLogger(__name__)


@dataclass
class EnhancedVisualizationConfig:
    """強化可視化設定"""
    # 基本設定
    width: int = 1600
    height: int = 1200
    dpi: int = 300
    
    # 視認性改善設定
    font_size_title: int = 24
    font_size_label: int = 18
    font_size_tick: int = 14
    font_size_annotation: int = 16
    
    # 色設定（視認性重視）
    color_palette: List[str] = field(default_factory=lambda: [
        '#1f77b4',  # 鮮やかな青
        '#ff7f0e',  # 鮮やかなオレンジ
        '#2ca02c',  # 鮮やかな緑
        '#d62728',  # 鮮やかな赤
        '#9467bd',  # 鮮やかな紫
        '#8c564b',  # 茶色
        '#e377c2',  # ピンク
        '#7f7f7f',  # グレー
        '#bcbd22',  # オリーブ
        '#17becf'   # シアン
    ])
    
    # 背景・テーマ設定
    background_color: str = '#ffffff'
    grid_color: str = '#e0e0e0'
    text_color: str = '#333333'
    
    # チャート設定
    line_width: int = 3
    marker_size: int = 8
    bar_width: float = 0.8
    
    # 出力設定
    output_format: List[str] = field(default_factory=lambda: ["html", "png"])
    save_path: Optional[Path] = None


class EnhancedVisualizationEngine:
    """強化可視化エンジン"""
    
    def __init__(self, config: Optional[EnhancedVisualizationConfig] = None):
        self.config = config or EnhancedVisualizationConfig()
        
    def create_single_indicator_deep_analysis(
        self,
        indicator: ProcessedIndicator,
        trend_result: Optional[TrendResult] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """単一指標の深度分析可視化"""
        
        try:
            # 大きなサブプロット構成（2x3）
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=[
                    f"{indicator.original_event.country} - {getattr(indicator.original_event, 'indicator', 'N/A')} 詳細分析",
                    "時系列分解分析",
                    "統計分析・分布",
                    "トレンド・パターン分析", 
                    "リスク・ボラティリティ分析",
                    "予測・サプライズ分析"
                ],
                specs=[
                    [{"secondary_y": True}, {"secondary_y": True}],
                    [{"secondary_y": True}, {"secondary_y": True}],
                    [{"secondary_y": True}, {"secondary_y": True}]
                ],
                vertical_spacing=0.08,
                horizontal_spacing=0.1
            )
            
            # 1. メイン時系列チャート
            self._add_main_time_series(fig, indicator, trend_result, row=1, col=1)
            
            # 2. 時系列分解
            self._add_time_series_decomposition(fig, indicator, row=1, col=2)
            
            # 3. 統計分析・分布
            self._add_statistical_analysis(fig, indicator, row=2, col=1)
            
            # 4. トレンド・パターン分析
            self._add_trend_pattern_analysis(fig, indicator, trend_result, row=2, col=2)
            
            # 5. リスク・ボラティリティ分析
            self._add_risk_volatility_analysis(fig, indicator, row=3, col=1)
            
            # 6. 予測・サプライズ分析
            self._add_forecast_surprise_analysis(fig, indicator, row=3, col=2)
            
            # レイアウト設定
            self._configure_enhanced_layout(fig, indicator)
            
            # 詳細分析情報を生成
            analysis_info = self._generate_deep_analysis_info(indicator, trend_result, additional_data)
            
            # HTML生成
            html_content = self._generate_enhanced_html(fig, analysis_info, indicator)
            
            # ファイル保存
            saved_files = []
            if self.config.save_path:
                saved_files = self._save_enhanced_visualization(fig, html_content, analysis_info, indicator)
            
            return {
                'figure': fig,
                'html': html_content,
                'analysis_info': analysis_info,
                'saved_files': saved_files,
                'type': 'enhanced_single_indicator_analysis'
            }
            
        except Exception as e:
            logger.error(f"深度分析可視化エラー: {e}")
            return {'error': str(e)}
    
    def _add_main_time_series(self, fig, indicator: ProcessedIndicator, trend_result: Optional[TrendResult], row: int, col: int):
        """メイン時系列チャートを追加"""
        try:
            if indicator.historical_data is None:
                return
            
            data = indicator.historical_data
            event = indicator.original_event
            
            # メインデータライン
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data.values,
                    mode='lines+markers',
                    name='実際値',
                    line=dict(
                        color=self.config.color_palette[0],
                        width=self.config.line_width
                    ),
                    marker=dict(
                        size=self.config.marker_size,
                        color=self.config.color_palette[0]
                    ),
                    hovertemplate='<b>%{x}</b><br>値: %{y:.2f}<extra></extra>'
                ),
                row=row, col=col
            )
            
            # 移動平均線（複数期間）
            if len(data) >= 20:
                # 短期移動平均（5期間）
                ma5 = data.rolling(5).mean()
                fig.add_trace(
                    go.Scatter(
                        x=ma5.index,
                        y=ma5.values,
                        mode='lines',
                        name='5期間移動平均',
                        line=dict(
                            color=self.config.color_palette[1],
                            width=2,
                            dash='dash'
                        ),
                        opacity=0.8
                    ),
                    row=row, col=col
                )
                
                # 長期移動平均（20期間）
                ma20 = data.rolling(20).mean()
                fig.add_trace(
                    go.Scatter(
                        x=ma20.index,
                        y=ma20.values,
                        mode='lines',
                        name='20期間移動平均',
                        line=dict(
                            color=self.config.color_palette[2],
                            width=2,
                            dash='dot'
                        ),
                        opacity=0.8
                    ),
                    row=row, col=col
                )
            
            # トレンドライン
            if trend_result and hasattr(trend_result, 'slope'):
                x_trend = np.arange(len(data))
                y_trend = trend_result.slope * x_trend + data.iloc[0]
                
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=y_trend,
                        mode='lines',
                        name=f'トレンド ({trend_result.trend_type.value})',
                        line=dict(
                            color=self.config.color_palette[3],
                            width=3,
                            dash='dashdot'
                        ),
                        opacity=0.9
                    ),
                    row=row, col=col
                )
            
            # 最新値をハイライト
            latest_date = data.index[-1]
            latest_value = data.iloc[-1]
            
            fig.add_trace(
                go.Scatter(
                    x=[latest_date],
                    y=[latest_value],
                    mode='markers',
                    name='最新値',
                    marker=dict(
                        size=15,
                        color='red',
                        symbol='circle',
                        line=dict(color='darkred', width=3)
                    ),
                    hovertemplate=f'<b>最新値</b><br>日付: {latest_date.strftime("%Y-%m-%d")}<br>値: {latest_value:.2f}<extra></extra>'
                ),
                row=row, col=col
            )
            
            # サプライズ情報の表示
            if event.actual is not None and event.forecast is not None:
                surprise_info = event.calculate_surprise()
                if surprise_info:
                    surprise_color = 'green' if surprise_info['surprise'] > 0 else 'red'
                    fig.add_annotation(
                        x=latest_date,
                        y=latest_value,
                        text=f"サプライズ: {surprise_info['surprise']:+.2f}<br>({surprise_info['surprise_pct']:+.1f}%)",
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor=surprise_color,
                        bgcolor=surprise_color,
                        bordercolor=surprise_color,
                        font=dict(color='white', size=self.config.font_size_annotation),
                        row=row, col=col
                    )
            
        except Exception as e:
            logger.error(f"メイン時系列チャート追加エラー: {e}")
    
    def _add_time_series_decomposition(self, fig, indicator: ProcessedIndicator, row: int, col: int):
        """時系列分解を追加"""
        try:
            if indicator.historical_data is None or len(indicator.historical_data) < 20:
                return
            
            data = indicator.historical_data
            
            # 時系列分解
            # トレンド（移動平均）
            trend = data.rolling(12, center=True).mean()
            
            # 季節性（簡易版）
            seasonal = data.groupby(data.index.month).transform('mean') - data.mean()
            
            # 残差
            residual = data - trend - seasonal
            
            # トレンド
            fig.add_trace(
                go.Scatter(
                    x=trend.index,
                    y=trend.values,
                    mode='lines',
                    name='トレンド',
                    line=dict(
                        color=self.config.color_palette[0],
                        width=self.config.line_width
                    ),
                    hovertemplate='<b>トレンド</b><br>%{x}<br>値: %{y:.2f}<extra></extra>'
                ),
                row=row, col=col
            )
            
            # 季節性
            fig.add_trace(
                go.Scatter(
                    x=seasonal.index,
                    y=seasonal.values,
                    mode='lines',
                    name='季節性',
                    line=dict(
                        color=self.config.color_palette[1],
                        width=self.config.line_width
                    ),
                    hovertemplate='<b>季節性</b><br>%{x}<br>値: %{y:.2f}<extra></extra>'
                ),
                row=row, col=col
            )
            
            # 残差
            fig.add_trace(
                go.Scatter(
                    x=residual.index,
                    y=residual.values,
                    mode='lines',
                    name='残差',
                    line=dict(
                        color=self.config.color_palette[2],
                        width=self.config.line_width
                    ),
                    hovertemplate='<b>残差</b><br>%{x}<br>値: %{y:.2f}<extra></extra>'
                ),
                row=row, col=col
            )
            
        except Exception as e:
            logger.error(f"時系列分解追加エラー: {e}")
    
    def _add_statistical_analysis(self, fig, indicator: ProcessedIndicator, row: int, col: int):
        """統計分析・分布を追加"""
        try:
            if indicator.historical_data is None:
                return
            
            data = indicator.historical_data
            
            # ヒストグラム
            fig.add_trace(
                go.Histogram(
                    x=data.values,
                    nbinsx=30,
                    name='値の分布',
                    marker_color=self.config.color_palette[0],
                    opacity=0.7,
                    hovertemplate='<b>分布</b><br>値: %{x}<br>頻度: %{y}<extra></extra>'
                ),
                row=row, col=col
            )
            
            # 正規分布のオーバーレイ
            mean_val = data.mean()
            std_val = data.std()
            x_norm = np.linspace(data.min(), data.max(), 100)
            y_norm = stats.norm.pdf(x_norm, mean_val, std_val) * len(data) * (data.max() - data.min()) / 30
            
            fig.add_trace(
                go.Scatter(
                    x=x_norm,
                    y=y_norm,
                    mode='lines',
                    name='正規分布',
                    line=dict(
                        color=self.config.color_palette[1],
                        width=3,
                        dash='dash'
                    ),
                    hovertemplate='<b>正規分布</b><br>値: %{x}<br>密度: %{y:.2f}<extra></extra>'
                ),
                row=row, col=col
            )
            
            # 統計情報の注釈
            stats_text = f"""
            平均: {mean_val:.2f}
            標準偏差: {std_val:.2f}
            歪度: {data.skew():.2f}
            尖度: {data.kurtosis():.2f}
            """
            
            fig.add_annotation(
                x=0.02, y=0.98,
                xref='paper', yref='paper',
                text=stats_text,
                showarrow=False,
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='black',
                borderwidth=1,
                font=dict(size=self.config.font_size_annotation),
                row=row, col=col
            )
            
        except Exception as e:
            logger.error(f"統計分析追加エラー: {e}")
    
    def _add_trend_pattern_analysis(self, fig, indicator: ProcessedIndicator, trend_result: Optional[TrendResult], row: int, col: int):
        """トレンド・パターン分析を追加"""
        try:
            if indicator.historical_data is None:
                return
            
            data = indicator.historical_data
            
            # 変化率の分析
            returns = data.pct_change().dropna()
            
            # 変化率の時系列
            fig.add_trace(
                go.Scatter(
                    x=returns.index,
                    y=returns.values * 100,  # パーセント表示
                    mode='lines+markers',
                    name='変化率',
                    line=dict(
                        color=self.config.color_palette[0],
                        width=self.config.line_width
                    ),
                    marker=dict(size=self.config.marker_size),
                    hovertemplate='<b>変化率</b><br>%{x}<br>変化率: %{y:.2f}%<extra></extra>'
                ),
                row=row, col=col
            )
            
            # ゼロライン
            fig.add_hline(
                y=0,
                line=dict(color='black', width=2, dash='dash'),
                row=row, col=col
            )
            
            # トレンド情報の表示
            if trend_result:
                trend_text = f"""
                トレンドタイプ: {trend_result.trend_type.value}
                信頼度: {trend_result.confidence_level:.1f}%
                パターン: {trend_result.pattern_type.value}
                """
                
                fig.add_annotation(
                    x=0.02, y=0.98,
                    xref='paper', yref='paper',
                    text=trend_text,
                    showarrow=False,
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='black',
                    borderwidth=1,
                    font=dict(size=self.config.font_size_annotation),
                    row=row, col=col
                )
            
        except Exception as e:
            logger.error(f"トレンドパターン分析追加エラー: {e}")
    
    def _add_risk_volatility_analysis(self, fig, indicator: ProcessedIndicator, row: int, col: int):
        """リスク・ボラティリティ分析を追加"""
        try:
            if indicator.historical_data is None or len(indicator.historical_data) < 20:
                return
            
            data = indicator.historical_data
            
            # ボラティリティ計算
            returns = data.pct_change().dropna()
            rolling_vol = returns.rolling(window=20).std() * np.sqrt(252) * 100  # 年率
            
            # ボラティリティ
            fig.add_trace(
                go.Scatter(
                    x=rolling_vol.index,
                    y=rolling_vol.values,
                    mode='lines',
                    name='ボラティリティ',
                    line=dict(
                        color=self.config.color_palette[0],
                        width=self.config.line_width
                    ),
                    fill='tozeroy',
                    fillcolor=f'rgba({int(self.config.color_palette[0][1:3], 16)}, {int(self.config.color_palette[0][3:5], 16)}, {int(self.config.color_palette[0][5:7], 16)}, 0.3)',
                    hovertemplate='<b>ボラティリティ</b><br>%{x}<br>年率: %{y:.2f}%<extra></extra>'
                ),
                row=row, col=col
            )
            
            # 平均ボラティリティライン
            avg_vol = rolling_vol.mean()
            fig.add_hline(
                y=avg_vol,
                line=dict(color=self.config.color_palette[1], width=2, dash='dash'),
                annotation_text=f"平均: {avg_vol:.1f}%",
                row=row, col=col
            )
            
            # リスク情報の表示
            risk_info = f"""
            平均ボラティリティ: {avg_vol:.1f}%
            最大ボラティリティ: {rolling_vol.max():.1f}%
            最小ボラティリティ: {rolling_vol.min():.1f}%
            データ品質: {indicator.data_quality_score:.0f}/100
            """
            
            fig.add_annotation(
                x=0.02, y=0.98,
                xref='paper', yref='paper',
                text=risk_info,
                showarrow=False,
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='black',
                borderwidth=1,
                font=dict(size=self.config.font_size_annotation),
                row=row, col=col
            )
            
        except Exception as e:
            logger.error(f"リスクボラティリティ分析追加エラー: {e}")
    
    def _add_forecast_surprise_analysis(self, fig, indicator: ProcessedIndicator, row: int, col: int):
        """予測・サプライズ分析を追加"""
        try:
            event = indicator.original_event
            
            # 予測vs実際値の比較
            if event.actual is not None and event.forecast is not None:
                categories = ['予想値', '実際値']
                values = [event.forecast, event.actual]
                
                # 色分け（予想より高いか低いか）
                colors = [self.config.color_palette[1], 
                         self.config.color_palette[2] if event.actual > event.forecast else self.config.color_palette[3]]
                
                fig.add_trace(
                    go.Bar(
                        x=categories,
                        y=values,
                        name='予測vs実際',
                        marker_color=colors,
                        text=[f'{v:.2f}' for v in values],
                        textposition='auto',
                        textfont=dict(size=self.config.font_size_annotation),
                        hovertemplate='<b>%{x}</b><br>値: %{y:.2f}<extra></extra>'
                    ),
                    row=row, col=col
                )
                
                # サプライズ情報
                surprise_info = event.calculate_surprise()
                if surprise_info:
                    surprise_text = f"""
                    サプライズ: {surprise_info['surprise']:+.2f}
                    サプライズ率: {surprise_info['surprise_pct']:+.1f}%
                    前回値: {event.previous or 'N/A'}
                    """
                    
                    fig.add_annotation(
                        x=0.02, y=0.98,
                        xref='paper', yref='paper',
                        text=surprise_text,
                        showarrow=False,
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor='black',
                        borderwidth=1,
                        font=dict(size=self.config.font_size_annotation),
                        row=row, col=col
                    )
            else:
                # データがない場合
                fig.add_annotation(
                    x=0.5, y=0.5,
                    xref='paper', yref='paper',
                    text="予測データがありません",
                    showarrow=False,
                    font=dict(size=self.config.font_size_annotation),
                    row=row, col=col
                )
            
        except Exception as e:
            logger.error(f"予測サプライズ分析追加エラー: {e}")
    
    def _configure_enhanced_layout(self, fig, indicator: ProcessedIndicator):
        """強化レイアウトを設定"""
        event = indicator.original_event
        
        fig.update_layout(
            title=dict(
                text=f"<b>{event.country} - {getattr(event, 'indicator', 'N/A')} 深度分析</b>",
                font=dict(size=self.config.font_size_title, family="Arial, sans-serif"),
                x=0.5
            ),
            width=self.config.width,
            height=self.config.height,
            showlegend=True,
            hovermode='closest',
            template='plotly_white',
            font=dict(
                family="Arial, sans-serif", 
                size=self.config.font_size_label,
                color=self.config.text_color
            ),
            plot_bgcolor=self.config.background_color,
            paper_bgcolor=self.config.background_color,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=self.config.font_size_label)
            )
        )
        
        # 各サブプロットの軸ラベル
        fig.update_xaxes(
            title_font=dict(size=self.config.font_size_label),
            tickfont=dict(size=self.config.font_size_tick),
            gridcolor=self.config.grid_color,
            row=1, col=1
        )
        fig.update_yaxes(
            title_font=dict(size=self.config.font_size_label),
            tickfont=dict(size=self.config.font_size_tick),
            gridcolor=self.config.grid_color,
            row=1, col=1
        )
        
        # 他のサブプロットも同様に設定
        for row in range(1, 4):
            for col in range(1, 3):
                fig.update_xaxes(
                    title_font=dict(size=self.config.font_size_label),
                    tickfont=dict(size=self.config.font_size_tick),
                    gridcolor=self.config.grid_color,
                    row=row, col=col
                )
                fig.update_yaxes(
                    title_font=dict(size=self.config.font_size_label),
                    tickfont=dict(size=self.config.font_size_tick),
                    gridcolor=self.config.grid_color,
                    row=row, col=col
                )
    
    def _generate_deep_analysis_info(self, indicator: ProcessedIndicator, trend_result: Optional[TrendResult], additional_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """深度分析情報を生成"""
        try:
            event = indicator.original_event
            
            # 基本情報
            basic_info = {
                'country': event.country,
                'indicator': getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A'),
                'importance': event.importance,
                'datetime': event.datetime.isoformat() if event.datetime else None,
                'actual': event.actual,
                'forecast': event.forecast,
                'previous': event.previous
            }
            
            # 統計情報
            statistical_info = {}
            if indicator.historical_data is not None:
                data = indicator.historical_data
                statistical_info = {
                    'mean': float(data.mean()),
                    'median': float(data.median()),
                    'std': float(data.std()),
                    'min': float(data.min()),
                    'max': float(data.max()),
                    'skewness': float(data.skew()),
                    'kurtosis': float(data.kurtosis()),
                    'data_points': len(data),
                    'date_range': {
                        'start': data.index[0].isoformat(),
                        'end': data.index[-1].isoformat()
                    }
                }
            
            # トレンド情報
            trend_info = {}
            if trend_result:
                trend_info = {
                    'trend_type': trend_result.trend_type.value,
                    'confidence_level': trend_result.confidence_level,
                    'pattern_type': trend_result.pattern_type.value,
                    'pattern_confidence': trend_result.pattern_confidence,
                    'support_levels': trend_result.support_levels[:5] if trend_result.support_levels else [],
                    'resistance_levels': trend_result.resistance_levels[:5] if trend_result.resistance_levels else []
                }
            
            # サプライズ情報
            surprise_info = {}
            if event.actual is not None and event.forecast is not None:
                surprise = event.calculate_surprise()
                if surprise:
                    surprise_info = {
                        'surprise': surprise['surprise'],
                        'surprise_pct': surprise['surprise_pct'],
                        'impact': 'positive' if surprise['surprise'] > 0 else 'negative'
                    }
            
            # リスク情報
            risk_info = {
                'data_quality_score': indicator.data_quality_score,
                'volatility_index': getattr(indicator, 'volatility_index', None),
                'z_score': indicator.z_score,
                'mom_change': indicator.mom_change,
                'yoy_change': indicator.yoy_change
            }
            
            # 分析サマリー
            analysis_summary = self._generate_analysis_summary(indicator, trend_result, statistical_info, surprise_info)
            
            return {
                'basic_info': basic_info,
                'statistical_info': statistical_info,
                'trend_info': trend_info,
                'surprise_info': surprise_info,
                'risk_info': risk_info,
                'analysis_summary': analysis_summary,
                'generation_time': datetime.now().isoformat(),
                'additional_data': additional_data or {}
            }
            
        except Exception as e:
            logger.error(f"深度分析情報生成エラー: {e}")
            return {}
    
    def _generate_analysis_summary(self, indicator: ProcessedIndicator, trend_result: Optional[TrendResult], statistical_info: Dict, surprise_info: Dict) -> List[str]:
        """分析サマリーを生成"""
        summary = []
        
        try:
            # 基本サマリー
            event = indicator.original_event
            summary.append(f"📊 {event.country} {getattr(event, 'indicator', 'N/A')} の詳細分析")
            
            # サプライズサマリー
            if surprise_info:
                impact = "ポジティブ" if surprise_info['impact'] == 'positive' else "ネガティブ"
                summary.append(f"🎯 {impact}サプライズ: {surprise_info['surprise_pct']:+.1f}%")
            
            # トレンドサマリー
            if trend_result:
                summary.append(f"📈 トレンド: {trend_result.trend_type.value} (信頼度: {trend_result.confidence_level:.1f}%)")
            
            # 統計サマリー
            if statistical_info:
                summary.append(f"📊 統計: 平均 {statistical_info['mean']:.2f}, 標準偏差 {statistical_info['std']:.2f}")
            
            # リスクサマリー
            if indicator.data_quality_score < 70:
                summary.append(f"⚠️ データ品質注意: {indicator.data_quality_score:.0f}/100")
            
            if hasattr(indicator, 'volatility_index') and indicator.volatility_index and indicator.volatility_index > 20:
                summary.append(f"📊 高ボラティリティ: {indicator.volatility_index:.1f}%")
            
        except Exception as e:
            logger.error(f"分析サマリー生成エラー: {e}")
        
        return summary
    
    def _generate_enhanced_html(self, fig, analysis_info: Dict[str, Any], indicator: ProcessedIndicator) -> str:
        """強化HTMLを生成"""
        try:
            # PlotlyチャートのHTML
            chart_html = fig.to_html(include_plotlyjs='cdn', div_id="enhanced-chart")
            
            # 分析情報のHTML
            info_html = self._generate_analysis_info_html(analysis_info, indicator)
            
            # 完全なHTMLページ
            full_html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{indicator.original_event.country} - {getattr(indicator.original_event, 'indicator', 'N/A')} 深度分析</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            line-height: 1.6;
        }}
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
            margin: 0;
            font-size: 28px;
            font-weight: bold;
        }}
        .header p {{
            margin: 10px 0 0 0;
            font-size: 16px;
            opacity: 0.9;
        }}
        .dashboard-container {{
            display: flex;
            gap: 30px;
            margin-bottom: 30px;
        }}
        .chart-section {{
            flex: 2;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .info-section {{
            flex: 1;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            max-height: 800px;
            overflow-y: auto;
        }}
        .info-card {{
            background: #f8f9fa;
            border-left: 5px solid #007bff;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        .info-card h3 {{
            margin: 0 0 15px 0;
            color: #007bff;
            font-size: 18px;
        }}
        .metric {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 5px;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }}
        .summary-item {{
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
            font-size: 16px;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .data-table th, .data-table td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        .data-table th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        .highlight {{
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            border-left: 4px solid #ffc107;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{indicator.original_event.country} - {getattr(indicator.original_event, 'indicator', 'N/A')} 深度分析</h1>
        <p>生成日時: {analysis_info.get('generation_time', 'N/A')}</p>
    </div>
    
    <div class="dashboard-container">
        <div class="chart-section">
            {chart_html}
        </div>
        
        <div class="info-section">
            {info_html}
        </div>
    </div>
</body>
</html>
"""
            
            return full_html
            
        except Exception as e:
            logger.error(f"強化HTML生成エラー: {e}")
            return fig.to_html(include_plotlyjs='cdn')
    
    def _generate_analysis_info_html(self, analysis_info: Dict[str, Any], indicator: ProcessedIndicator) -> str:
        """分析情報HTMLを生成"""
        try:
            basic_info = analysis_info.get('basic_info', {})
            statistical_info = analysis_info.get('statistical_info', {})
            trend_info = analysis_info.get('trend_info', {})
            surprise_info = analysis_info.get('surprise_info', {})
            risk_info = analysis_info.get('risk_info', {})
            summary = analysis_info.get('analysis_summary', [])
            
            html = f"""
            <div class="info-card">
                <h3>📊 基本情報</h3>
                <div class="metric">{basic_info.get('country', 'N/A')}</div>
                <div class="metric-label">{basic_info.get('indicator', 'N/A')}</div>
                <p><strong>重要度:</strong> {basic_info.get('importance', 'N/A')}</p>
                <p><strong>発表日時:</strong> {basic_info.get('datetime', 'N/A')}</p>
            </div>
            
            <div class="info-card">
                <h3>📈 最新データ</h3>
                <table class="data-table">
                    <tr><th>項目</th><th>値</th></tr>
                    <tr><td>実際値</td><td>{basic_info.get('actual', 'N/A')}</td></tr>
                    <tr><td>予想値</td><td>{basic_info.get('forecast', 'N/A')}</td></tr>
                    <tr><td>前回値</td><td>{basic_info.get('previous', 'N/A')}</td></tr>
                </table>
            </div>
            """
            
            if surprise_info:
                html += f"""
                <div class="info-card">
                    <h3>🎯 サプライズ分析</h3>
                    <div class="metric">{surprise_info.get('surprise_pct', 0):+.1f}%</div>
                    <div class="metric-label">サプライズ率</div>
                    <p><strong>サプライズ:</strong> {surprise_info.get('surprise', 0):+.2f}</p>
                    <p><strong>影響:</strong> {surprise_info.get('impact', 'N/A')}</p>
                </div>
                """
            
            if trend_info:
                html += f"""
                <div class="info-card">
                    <h3>📊 トレンド分析</h3>
                    <p><strong>トレンドタイプ:</strong> {trend_info.get('trend_type', 'N/A')}</p>
                    <p><strong>信頼度:</strong> {trend_info.get('confidence_level', 0):.1f}%</p>
                    <p><strong>パターン:</strong> {trend_info.get('pattern_type', 'N/A')}</p>
                </div>
                """
            
            if statistical_info:
                html += f"""
                <div class="info-card">
                    <h3>📊 統計情報</h3>
                    <p><strong>平均:</strong> {statistical_info.get('mean', 0):.2f}</p>
                    <p><strong>標準偏差:</strong> {statistical_info.get('std', 0):.2f}</p>
                    <p><strong>最小値:</strong> {statistical_info.get('min', 0):.2f}</p>
                    <p><strong>最大値:</strong> {statistical_info.get('max', 0):.2f}</p>
                    <p><strong>データ数:</strong> {statistical_info.get('data_points', 0)}</p>
                </div>
                """
            
            html += f"""
            <div class="info-card">
                <h3>⚠️ リスク情報</h3>
                <p><strong>データ品質:</strong> {risk_info.get('data_quality_score', 0):.0f}/100</p>
                <p><strong>ボラティリティ:</strong> {risk_info.get('volatility_index', 'N/A')}</p>
                <p><strong>Z-Score:</strong> {risk_info.get('z_score', 'N/A')}</p>
                <p><strong>月次変化:</strong> {risk_info.get('mom_change', 'N/A')}</p>
                <p><strong>年次変化:</strong> {risk_info.get('yoy_change', 'N/A')}</p>
            </div>
            """
            
            if summary:
                html += """
                <div class="info-card">
                    <h3>💡 分析サマリー</h3>
                """
                for item in summary:
                    html += f'<div class="summary-item">{item}</div>'
                html += "</div>"
            
            return html
            
        except Exception as e:
            logger.error(f"分析情報HTML生成エラー: {e}")
            return "<p>分析情報の生成中にエラーが発生しました。</p>"
    
    def _save_enhanced_visualization(self, fig, html_content: str, analysis_info: Dict[str, Any], indicator: ProcessedIndicator) -> List[str]:
        """強化可視化を保存"""
        saved_files = []
        
        try:
            if not self.config.save_path:
                return saved_files
            
            self.config.save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # HTML保存
            if 'html' in self.config.output_format:
                html_path = self.config.save_path.with_suffix('.html')
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                saved_files.append(str(html_path))
            
            # PNG保存
            if 'png' in self.config.output_format:
                png_path = self.config.save_path.with_suffix('.png')
                fig.write_image(str(png_path), width=self.config.width, height=self.config.height, scale=2)
                saved_files.append(str(png_path))
            
            # JSON保存（分析情報）
            if 'json' in self.config.output_format:
                json_path = self.config.save_path.with_suffix('.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(analysis_info, f, ensure_ascii=False, indent=2)
                saved_files.append(str(json_path))
            
            logger.info(f"強化可視化が保存されました: {saved_files}")
            
        except Exception as e:
            logger.error(f"強化可視化保存エラー: {e}")
        
        return saved_files
