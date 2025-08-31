"""
Chart generation module for economic indicators.

matplotlib と plotly を使用して高品質な経済指標チャートを生成する。
インタラクティブチャート、静的画像、HTML埋め込み形式をサポート。
"""

from typing import List, Dict, Optional, Union, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
import logging
from pathlib import Path

# Plotting libraries
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as patches
from matplotlib.figure import Figure
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio

# Styling
import seaborn as sns
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..normalize.data_processor import ProcessedIndicator
    from ..normalize.trend_analyzer import TrendResult

logger = logging.getLogger(__name__)


class ChartType(Enum):
    """チャートタイプ"""
    LINE = "line"
    AREA = "area" 
    CANDLESTICK = "candlestick"
    BAR = "bar"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    CORRELATION = "correlation"
    TREND_ANALYSIS = "trend_analysis"
    MULTI_SERIES = "multi_series"


class ChartEngine(Enum):
    """チャートエンジン"""
    MATPLOTLIB = "matplotlib"
    PLOTLY = "plotly"


@dataclass
class ChartConfig:
    """チャート設定"""
    # 基本設定
    chart_type: ChartType = ChartType.LINE
    engine: ChartEngine = ChartEngine.PLOTLY
    
    # サイズ・レイアウト
    width: int = 1200
    height: int = 600
    dpi: int = 300  # matplotlib用
    
    # スタイル
    theme: str = "plotly_white"  # plotly用
    style: str = "whitegrid"  # matplotlib用
    color_palette: List[str] = field(default_factory=lambda: [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', 
        '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'
    ])
    
    # 日本語フォント設定
    font_family: str = "DejaVu Sans"
    font_size: int = 12
    
    # タイトル・ラベル
    title: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    show_legend: bool = True
    
    # インタラクティブ機能（plotly）
    interactive: bool = True
    show_range_selector: bool = True
    show_hover: bool = True
    
    # アノテーション
    show_annotations: bool = True
    show_trend_lines: bool = False
    show_support_resistance: bool = False
    
    # 出力設定
    output_format: List[str] = field(default_factory=lambda: ["html", "png"])
    save_path: Optional[Path] = None


class ChartGenerator:
    """チャート生成エンジン"""
    
    def __init__(self, default_config: Optional[ChartConfig] = None):
        self.default_config = default_config or ChartConfig()
        self._setup_styles()
        
        # 日本語フォント設定
        self._configure_japanese_fonts()
    
    def _setup_styles(self):
        """スタイル設定"""
        # matplotlib設定
        plt.style.use('default')
        sns.set_style(self.default_config.style)
        sns.set_palette(self.default_config.color_palette)
        
        # plotly設定  
        pio.templates.default = self.default_config.theme
    
    def _configure_japanese_fonts(self):
        """日本語フォント設定"""
        try:
            # matplotlib日本語フォント設定
            import matplotlib.font_manager as fm
            
            # システムの日本語フォントを探す
            japanese_fonts = []
            for font in fm.fontManager.ttflist:
                if 'Japanese' in font.name or 'Hiragino' in font.name or 'Noto' in font.name:
                    japanese_fonts.append(font.name)
            
            if japanese_fonts:
                plt.rcParams['font.family'] = japanese_fonts[0]
                logger.info(f"Japanese font configured: {japanese_fonts[0]}")
            else:
                # フォールバック
                plt.rcParams['font.family'] = ['DejaVu Sans', 'sans-serif']
                logger.warning("No Japanese fonts found, using default font")
            
        except Exception as e:
            logger.error(f"Failed to configure Japanese fonts: {e}")
    
    def generate_indicator_chart(
        self,
        processed_indicator: 'ProcessedIndicator',
        trend_result: Optional['TrendResult'] = None,
        config: Optional[ChartConfig] = None
    ) -> Dict[str, Any]:
        """経済指標の包括的チャートを生成"""
        config = config or self.default_config
        
        if processed_indicator.historical_data is None:
            logger.error("No historical data available for chart generation")
            return {'error': 'No historical data'}
        
        data = processed_indicator.historical_data
        event = processed_indicator.original_event
        
        try:
            if config.engine == ChartEngine.PLOTLY:
                return self._generate_plotly_indicator_chart(
                    processed_indicator, trend_result, config
                )
            else:
                return self._generate_matplotlib_indicator_chart(
                    processed_indicator, trend_result, config
                )
                
        except Exception as e:
            logger.error(f"Failed to generate indicator chart: {e}")
            return {'error': str(e)}
    
    def _generate_plotly_indicator_chart(
        self,
        processed_indicator: 'ProcessedIndicator',
        trend_result: Optional['TrendResult'],
        config: ChartConfig
    ) -> Dict[str, Any]:
        """Plotlyで経済指標チャートを生成"""
        data = processed_indicator.historical_data
        event = processed_indicator.original_event
        
        # サブプロットを作成
        fig = make_subplots(
            rows=3, cols=1,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=[
                f"{event.indicator} - {event.country}",
                "変化率（MoM/YoY）",
                "ボラティリティ"
            ],
            vertical_spacing=0.08
        )
        
        # メインチャート
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data.values,
                mode='lines+markers',
                name='値',
                line=dict(color=config.color_palette[0], width=2),
                marker=dict(size=4),
                hovertemplate='%{x}<br>値: %{y}<extra></extra>'
            ),
            row=1, col=1
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
                    size=10,
                    color='red',
                    symbol='circle',
                    line=dict(color='darkred', width=2)
                ),
                hovertemplate=f'最新値<br>日付: {latest_date.strftime("%Y-%m-%d")}<br>値: {latest_value:.2f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 移動平均線
        if len(data) >= 12:
            ma12 = data.rolling(12).mean()
            fig.add_trace(
                go.Scatter(
                    x=ma12.index,
                    y=ma12.values,
                    mode='lines',
                    name='12期間移動平均',
                    line=dict(color=config.color_palette[1], width=1, dash='dash'),
                    opacity=0.7
                ),
                row=1, col=1
            )
        
        # サプライズ情報の表示
        if event.actual is not None and event.forecast is not None:
            surprise_info = event.calculate_surprise()
            if surprise_info:
                surprise_color = 'green' if surprise_info['surprise'] > 0 else 'red'
                fig.add_annotation(
                    x=latest_date,
                    y=latest_value,
                    text=f"サプライズ: {surprise_info['surprise']:+.2f}",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor=surprise_color,
                    bgcolor=surprise_color,
                    bordercolor=surprise_color,
                    font=dict(color='white'),
                    row=1, col=1
                )
        
        # トレンド情報の表示
        if trend_result and config.show_trend_lines:
            # トレンドライン
            x_trend = np.arange(len(data))
            y_trend = trend_result.slope * x_trend + data.iloc[0]
            
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=y_trend,
                    mode='lines',
                    name=f'トレンド ({trend_result.trend_type.value})',
                    line=dict(color='orange', width=2, dash='dot'),
                    opacity=0.8
                ),
                row=1, col=1
            )
        
        # サポート・レジスタンスライン
        if trend_result and config.show_support_resistance:
            for level in trend_result.support_levels[:2]:  # 上位2つ
                fig.add_hline(
                    y=level,
                    line=dict(color='green', width=1, dash='dash'),
                    annotation_text=f"サポート: {level:.2f}",
                    row=1, col=1
                )
            
            for level in trend_result.resistance_levels[:2]:  # 上位2つ
                fig.add_hline(
                    y=level,
                    line=dict(color='red', width=1, dash='dash'),
                    annotation_text=f"レジスタンス: {level:.2f}",
                    row=1, col=1
                )
        
        # 変化率チャート
        if processed_indicator.mom_change is not None or processed_indicator.yoy_change is not None:
            change_types = []
            change_values = []
            
            if processed_indicator.mom_change is not None:
                change_types.append('MoM')
                change_values.append(processed_indicator.mom_change)
            
            if processed_indicator.yoy_change is not None:
                change_types.append('YoY')
                change_values.append(processed_indicator.yoy_change)
            
            colors = ['blue' if v >= 0 else 'red' for v in change_values]
            
            fig.add_trace(
                go.Bar(
                    x=change_types,
                    y=change_values,
                    marker_color=colors,
                    name='変化率',
                    text=[f'{v:+.1f}%' for v in change_values],
                    textposition='auto'
                ),
                row=2, col=1
            )
        
        # ボラティリティ
        if len(data) >= 20:
            returns = data.pct_change().dropna()
            volatility = returns.rolling(window=20).std() * np.sqrt(252) * 100  # 年率
            
            fig.add_trace(
                go.Scatter(
                    x=volatility.index,
                    y=volatility.values,
                    mode='lines',
                    name='ボラティリティ',
                    line=dict(color='purple', width=1),
                    fill='tozeroy',
                    fillcolor='rgba(128,0,128,0.1)'
                ),
                row=3, col=1
            )
        
        # レイアウト設定
        fig.update_layout(
            title=dict(
                text=config.title or f"{event.indicator} 詳細分析",
                font=dict(size=16, family=config.font_family)
            ),
            width=config.width,
            height=config.height,
            showlegend=config.show_legend,
            hovermode='x unified',
            template=config.theme
        )
        
        # X軸の設定
        fig.update_xaxes(
            title_text="日付",
            tickformat='%Y-%m-%d',
            row=3, col=1
        )
        
        # Y軸の設定
        fig.update_yaxes(title_text="値", row=1, col=1)
        fig.update_yaxes(title_text="変化率(%)", row=2, col=1)
        fig.update_yaxes(title_text="ボラティリティ(%)", row=3, col=1)
        
        # レンジセレクター
        if config.show_range_selector:
            fig.update_layout(
                xaxis=dict(
                    rangeselector=dict(
                        buttons=list([
                            dict(count=1, label="1M", step="month", stepmode="backward"),
                            dict(count=3, label="3M", step="month", stepmode="backward"),
                            dict(count=6, label="6M", step="month", stepmode="backward"),
                            dict(count=1, label="1Y", step="year", stepmode="backward"),
                            dict(step="all")
                        ])
                    ),
                    rangeslider=dict(visible=True),
                    type="date"
                )
            )
        
        # HTML文字列とファイル保存
        html_content = fig.to_html(include_plotlyjs='cdn')
        
        result = {
            'figure': fig,
            'html': html_content,
            'type': 'plotly'
        }
        
        # ファイル保存
        if config.save_path:
            self._save_plotly_chart(fig, config.save_path, config.output_format)
            result['saved_files'] = config.output_format
        
        return result
    
    def _generate_matplotlib_indicator_chart(
        self,
        processed_indicator: 'ProcessedIndicator',
        trend_result: Optional['TrendResult'],
        config: ChartConfig
    ) -> Dict[str, Any]:
        """matplotlibで経済指標チャートを生成"""
        data = processed_indicator.historical_data
        event = processed_indicator.original_event
        
        # Figure作成
        fig, axes = plt.subplots(3, 1, figsize=(config.width/100, config.height/100), 
                                gridspec_kw={'height_ratios': [3, 1, 1]})
        fig.suptitle(config.title or f"{event.indicator} 詳細分析", 
                     fontsize=config.font_size + 2, fontweight='bold')
        
        # メインチャート
        ax_main = axes[0]
        ax_main.plot(data.index, data.values, 
                    color=config.color_palette[0], linewidth=2, 
                    marker='o', markersize=3, label='値')
        
        # 移動平均線
        if len(data) >= 12:
            ma12 = data.rolling(12).mean()
            ax_main.plot(ma12.index, ma12.values,
                        color=config.color_palette[1], linewidth=1,
                        linestyle='--', alpha=0.7, label='12期間移動平均')
        
        # 最新値をハイライト
        latest_date = data.index[-1]
        latest_value = data.iloc[-1]
        ax_main.scatter([latest_date], [latest_value], 
                       color='red', s=100, zorder=5, label='最新値')
        
        # トレンドライン
        if trend_result and config.show_trend_lines:
            x_trend = np.arange(len(data))
            y_trend = trend_result.slope * x_trend + data.iloc[0]
            ax_main.plot(data.index, y_trend,
                        color='orange', linewidth=2, linestyle=':', 
                        alpha=0.8, label=f'トレンド ({trend_result.trend_type.value})')
        
        ax_main.set_ylabel('値')
        ax_main.legend(loc='upper left')
        ax_main.grid(True, alpha=0.3)
        ax_main.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        
        # 変化率チャート
        ax_change = axes[1]
        if processed_indicator.mom_change is not None or processed_indicator.yoy_change is not None:
            change_types = []
            change_values = []
            
            if processed_indicator.mom_change is not None:
                change_types.append('MoM')
                change_values.append(processed_indicator.mom_change)
            
            if processed_indicator.yoy_change is not None:
                change_types.append('YoY')
                change_values.append(processed_indicator.yoy_change)
            
            colors = ['blue' if v >= 0 else 'red' for v in change_values]
            bars = ax_change.bar(change_types, change_values, color=colors, alpha=0.7)
            
            # 値をバーの上に表示
            for bar, value in zip(bars, change_values):
                height = bar.get_height()
                ax_change.text(bar.get_x() + bar.get_width()/2., height,
                             f'{value:+.1f}%', ha='center', 
                             va='bottom' if height >= 0 else 'top')
        
        ax_change.set_ylabel('変化率(%)')
        ax_change.grid(True, alpha=0.3)
        ax_change.axhline(y=0, color='black', linewidth=0.5)
        
        # ボラティリティチャート
        ax_vol = axes[2]
        if len(data) >= 20:
            returns = data.pct_change().dropna()
            volatility = returns.rolling(window=20).std() * np.sqrt(252) * 100
            
            ax_vol.plot(volatility.index, volatility.values,
                       color='purple', linewidth=1)
            ax_vol.fill_between(volatility.index, volatility.values,
                               alpha=0.3, color='purple')
        
        ax_vol.set_xlabel('日付')
        ax_vol.set_ylabel('ボラティリティ(%)')
        ax_vol.grid(True, alpha=0.3)
        ax_vol.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        
        plt.tight_layout()
        
        result = {
            'figure': fig,
            'type': 'matplotlib'
        }
        
        # ファイル保存
        if config.save_path:
            self._save_matplotlib_chart(fig, config.save_path, config.output_format)
            result['saved_files'] = config.output_format
        
        return result
    
    def generate_correlation_matrix(
        self,
        indicators: List['ProcessedIndicator'],
        config: Optional[ChartConfig] = None
    ) -> Dict[str, Any]:
        """複数指標の相関マトリクスを生成"""
        config = config or self.default_config
        
        # データの準備
        data_dict = {}
        for indicator in indicators:
            if indicator.historical_data is not None:
                event = indicator.original_event
                key = f"{event.country}_{event.indicator}"
                data_dict[key] = indicator.historical_data
        
        if len(data_dict) < 2:
            return {'error': '相関分析には2つ以上の指標が必要です'}
        
        # DataFrameに統合
        df = pd.DataFrame(data_dict)
        df = df.dropna()  # 共通期間のみ
        
        if df.empty:
            return {'error': 'データの共通期間がありません'}
        
        # 相関計算
        correlation_matrix = df.corr()
        
        if config.engine == ChartEngine.PLOTLY:
            return self._generate_plotly_correlation(correlation_matrix, config)
        else:
            return self._generate_matplotlib_correlation(correlation_matrix, config)
    
    def _generate_plotly_correlation(self, corr_matrix: pd.DataFrame, config: ChartConfig) -> Dict[str, Any]:
        """Plotlyで相関マトリクスを生成"""
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale='RdBu',
            zmid=0,
            text=np.around(corr_matrix.values, decimals=2),
            texttemplate='%{text}',
            textfont={"size": 10},
            hovertemplate='相関: %{z:.2f}<extra></extra>'
        ))
        
        fig.update_layout(
            title='経済指標相関マトリクス',
            width=config.width,
            height=config.height
        )
        
        html_content = fig.to_html(include_plotlyjs='cdn')
        
        return {
            'figure': fig,
            'html': html_content,
            'type': 'plotly_correlation'
        }
    
    def _generate_matplotlib_correlation(self, corr_matrix: pd.DataFrame, config: ChartConfig) -> Dict[str, Any]:
        """matplotlibで相関マトリクスを生成"""
        fig, ax = plt.subplots(figsize=(config.width/100, config.height/100))
        
        im = ax.imshow(corr_matrix, cmap='RdBu', aspect='auto', vmin=-1, vmax=1)
        
        # ラベル設定
        ax.set_xticks(np.arange(len(corr_matrix.columns)))
        ax.set_yticks(np.arange(len(corr_matrix.index)))
        ax.set_xticklabels(corr_matrix.columns, rotation=45, ha='right')
        ax.set_yticklabels(corr_matrix.index)
        
        # 値を表示
        for i in range(len(corr_matrix.index)):
            for j in range(len(corr_matrix.columns)):
                text = ax.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                             ha="center", va="center", color="black", fontsize=8)
        
        ax.set_title("経済指標相関マトリクス")
        plt.colorbar(im)
        plt.tight_layout()
        
        return {
            'figure': fig,
            'type': 'matplotlib_correlation'
        }
    
    def _save_plotly_chart(self, fig: go.Figure, save_path: Path, formats: List[str]):
        """Plotlyチャートを保存"""
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        for fmt in formats:
            if fmt == 'html':
                fig.write_html(save_path.with_suffix('.html'))
            elif fmt == 'png':
                fig.write_image(save_path.with_suffix('.png'), 
                               width=1200, height=800, scale=2)
            elif fmt == 'pdf':
                fig.write_image(save_path.with_suffix('.pdf'))
            elif fmt == 'svg':
                fig.write_image(save_path.with_suffix('.svg'))
    
    def _save_matplotlib_chart(self, fig: Figure, save_path: Path, formats: List[str]):
        """matplotlibチャートを保存"""
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        for fmt in formats:
            if fmt == 'png':
                fig.savefig(save_path.with_suffix('.png'), 
                           dpi=300, bbox_inches='tight', facecolor='white')
            elif fmt == 'pdf':
                fig.savefig(save_path.with_suffix('.pdf'), 
                           bbox_inches='tight', facecolor='white')
            elif fmt == 'svg':
                fig.savefig(save_path.with_suffix('.svg'), 
                           bbox_inches='tight', facecolor='white')
        
        plt.close(fig)  # メモリリークを防ぐ