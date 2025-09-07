"""
Enhanced Visualization for Economic Indicators
経済指標可視化強化モジュール

プロフェッショナル向けの高度な分析・可視化機能を提供
"""

from typing import List, Dict, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
from dataclasses import dataclass, field
from enum import Enum

# 可視化ライブラリ
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates

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


class VisualizationType(Enum):
    """可視化タイプ"""
    TREND_ANALYSIS = "trend_analysis"
    CORRELATION_MATRIX = "correlation_matrix"
    VOLATILITY_SURFACE = "volatility_surface"
    REGIME_DETECTION = "regime_detection"
    FORECAST_ACCURACY = "forecast_accuracy"
    RISK_METRICS = "risk_metrics"
    SECTOR_ANALYSIS = "sector_analysis"
    COUNTRY_COMPARISON = "country_comparison"
    TIME_SERIES_DECOMPOSITION = "time_series_decomposition"
    DISTRIBUTION_ANALYSIS = "distribution_analysis"


@dataclass
class VisualizationConfig:
    """可視化設定"""
    # 基本設定
    width: int = 1200
    height: int = 800
    dpi: int = 300
    
    # スタイル設定
    theme: str = "plotly_white"
    color_palette: List[str] = field(default_factory=lambda: [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
        '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
        '#bcbd22', '#17becf'
    ])
    
    # 統計設定
    confidence_level: float = 0.95
    outlier_threshold: float = 3.0  # z-score threshold
    
    # 出力設定
    output_format: List[str] = field(default_factory=lambda: ["html", "png"])
    save_path: Optional[Path] = None


class VisualizationEnhancer:
    """可視化強化エンジン"""
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()
        
    def create_advanced_visualizations(
        self,
        indicators: List[ProcessedIndicator],
        trend_results: Optional[List[TrendResult]] = None,
        visualization_types: Optional[List[VisualizationType]] = None
    ) -> Dict[str, Any]:
        """高度な可視化を作成"""
        
        if visualization_types is None:
            visualization_types = [
                VisualizationType.TREND_ANALYSIS,
                VisualizationType.CORRELATION_MATRIX,
                VisualizationType.VOLATILITY_SURFACE,
                VisualizationType.REGIME_DETECTION,
                VisualizationType.FORECAST_ACCURACY,
                VisualizationType.RISK_METRICS
            ]
        
        results = {}
        
        try:
            for viz_type in visualization_types:
                try:
                    if viz_type == VisualizationType.TREND_ANALYSIS:
                        results['trend_analysis'] = self._create_trend_analysis(indicators, trend_results)
                    elif viz_type == VisualizationType.CORRELATION_MATRIX:
                        results['correlation_matrix'] = self._create_correlation_matrix(indicators)
                    elif viz_type == VisualizationType.VOLATILITY_SURFACE:
                        results['volatility_surface'] = self._create_volatility_surface(indicators)
                    elif viz_type == VisualizationType.REGIME_DETECTION:
                        results['regime_detection'] = self._create_regime_detection(indicators)
                    elif viz_type == VisualizationType.FORECAST_ACCURACY:
                        results['forecast_accuracy'] = self._create_forecast_accuracy(indicators)
                    elif viz_type == VisualizationType.RISK_METRICS:
                        results['risk_metrics'] = self._create_risk_metrics(indicators, trend_results)
                    elif viz_type == VisualizationType.SECTOR_ANALYSIS:
                        results['sector_analysis'] = self._create_sector_analysis(indicators)
                    elif viz_type == VisualizationType.COUNTRY_COMPARISON:
                        results['country_comparison'] = self._create_country_comparison(indicators)
                    elif viz_type == VisualizationType.TIME_SERIES_DECOMPOSITION:
                        results['time_series_decomposition'] = self._create_time_series_decomposition(indicators)
                    elif viz_type == VisualizationType.DISTRIBUTION_ANALYSIS:
                        results['distribution_analysis'] = self._create_distribution_analysis(indicators)
                    
                except Exception as e:
                    logger.error(f"{viz_type.value}可視化エラー: {e}")
                    results[viz_type.value] = {'error': str(e)}
            
            return results
            
        except Exception as e:
            logger.error(f"高度な可視化作成エラー: {e}")
            return {'error': str(e)}
    
    def _create_trend_analysis(self, indicators: List[ProcessedIndicator], trend_results: Optional[List[TrendResult]]) -> Dict[str, Any]:
        """トレンド分析可視化"""
        try:
            # サブプロット作成
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=[
                    "トレンド強度分布", "トレンド方向別指標数",
                    "トレンド信頼度", "トレンド持続期間"
                ],
                specs=[[{"type": "histogram"}, {"type": "bar"}],
                       [{"type": "scatter"}, {"type": "bar"}]]
            )
            
            # トレンド強度分布
            trend_strengths = []
            for indicator in indicators:
                if hasattr(indicator, 'trend_strength') and indicator.trend_strength:
                    trend_strengths.append(indicator.trend_strength)
            
            if trend_strengths:
                fig.add_trace(
                    go.Histogram(
                        x=trend_strengths,
                        nbinsx=20,
                        name="トレンド強度",
                        marker_color=self.config.color_palette[0]
                    ),
                    row=1, col=1
                )
            
            # トレンド方向別指標数
            trend_directions = {}
            for indicator in indicators:
                if indicator.trend_direction:
                    direction = indicator.trend_direction.value
                    trend_directions[direction] = trend_directions.get(direction, 0) + 1
            
            if trend_directions:
                fig.add_trace(
                    go.Bar(
                        x=list(trend_directions.keys()),
                        y=list(trend_directions.values()),
                        name="トレンド方向",
                        marker_color=self.config.color_palette[1]
                    ),
                    row=1, col=2
                )
            
            # トレンド信頼度
            if trend_results:
                confidences = [tr.confidence_level for tr in trend_results if tr]
                countries = [indicators[i].original_event.country for i, tr in enumerate(trend_results) if tr and i < len(indicators)]
                
                if confidences:
                    fig.add_trace(
                        go.Scatter(
                            x=countries,
                            y=confidences,
                            mode='markers+text',
                            name="信頼度",
                            marker=dict(
                                size=confidences,
                                color=confidences,
                                colorscale='Viridis',
                                showscale=True,
                                colorbar=dict(title="信頼度(%)")
                            ),
                            text=[f"{c:.1f}%" for c in confidences],
                            textposition='top center'
                        ),
                        row=2, col=1
                    )
            
            # トレンド持続期間（簡易版）
            trend_durations = []
            for indicator in indicators:
                if indicator.historical_data is not None:
                    # 簡易的な持続期間計算
                    data = indicator.historical_data
                    if len(data) > 1:
                        duration = (data.index[-1] - data.index[0]).days
                        trend_durations.append(duration)
            
            if trend_durations:
                fig.add_trace(
                    go.Bar(
                        x=[f"期間{i+1}" for i in range(len(trend_durations))],
                        y=trend_durations,
                        name="持続期間",
                        marker_color=self.config.color_palette[2]
                    ),
                    row=2, col=2
                )
            
            # レイアウト設定
            fig.update_layout(
                title="高度なトレンド分析",
                width=self.config.width,
                height=self.config.height,
                showlegend=False
            )
            
            return {
                'figure': fig,
                'html': fig.to_html(include_plotlyjs='cdn'),
                'type': 'trend_analysis'
            }
            
        except Exception as e:
            logger.error(f"トレンド分析可視化エラー: {e}")
            return {'error': str(e)}
    
    def _create_correlation_matrix(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """相関マトリクス可視化"""
        try:
            # データ準備
            data_dict = {}
            for indicator in indicators:
                if indicator.historical_data is not None and len(indicator.historical_data) > 10:
                    event = indicator.original_event
                    key = f"{event.country}_{getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')}"
                    data_dict[key] = indicator.historical_data
            
            if len(data_dict) < 2:
                return {'error': '相関分析には2つ以上の指標が必要です'}
            
            # DataFrame作成
            df = pd.DataFrame(data_dict)
            df = df.dropna()
            
            if df.empty:
                return {'error': 'データの共通期間がありません'}
            
            # 相関計算
            correlation_matrix = df.corr()
            
            # ヒートマップ作成
            fig = go.Figure(data=go.Heatmap(
                z=correlation_matrix.values,
                x=correlation_matrix.columns,
                y=correlation_matrix.index,
                colorscale='RdBu',
                zmid=0,
                text=np.around(correlation_matrix.values, decimals=2),
                texttemplate='%{text}',
                textfont={"size": 10},
                hovertemplate='相関: %{z:.2f}<extra></extra>'
            ))
            
            # クラスタリング分析
            cluster_analysis = self._perform_correlation_clustering(correlation_matrix)
            
            fig.update_layout(
                title="経済指標相関マトリクス（クラスタリング分析付き）",
                width=self.config.width,
                height=self.config.height
            )
            
            return {
                'figure': fig,
                'html': fig.to_html(include_plotlyjs='cdn'),
                'correlation_matrix': correlation_matrix.to_dict(),
                'cluster_analysis': cluster_analysis,
                'type': 'correlation_matrix'
            }
            
        except Exception as e:
            logger.error(f"相関マトリクス可視化エラー: {e}")
            return {'error': str(e)}
    
    def _create_volatility_surface(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """ボラティリティサーフェス可視化"""
        try:
            # ボラティリティデータ準備
            volatility_data = []
            countries = []
            indicators_names = []
            dates = []
            
            for indicator in indicators:
                if indicator.historical_data is not None and len(indicator.historical_data) > 20:
                    data = indicator.historical_data
                    event = indicator.original_event
                    
                    # ローリングボラティリティ計算
                    returns = data.pct_change().dropna()
                    rolling_vol = returns.rolling(window=20).std() * np.sqrt(252) * 100
                    
                    for date, vol in rolling_vol.items():
                        if not pd.isna(vol):
                            volatility_data.append(vol)
                            countries.append(event.country)
                            indicators_names.append(getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A'))
                            dates.append(date)
            
            if not volatility_data:
                return {'error': 'ボラティリティデータが不足しています'}
            
            # 3Dサーフェスプロット
            df_vol = pd.DataFrame({
                'volatility': volatility_data,
                'country': countries,
                'indicator': indicators_names,
                'date': dates
            })
            
            # 国別・指標別の平均ボラティリティ
            vol_pivot = df_vol.groupby(['country', 'indicator'])['volatility'].mean().unstack(fill_value=0)
            
            fig = go.Figure(data=go.Surface(
                z=vol_pivot.values,
                x=vol_pivot.columns,
                y=vol_pivot.index,
                colorscale='Viridis',
                hovertemplate='国: %{y}<br>指標: %{x}<br>ボラティリティ: %{z:.2f}%<extra></extra>'
            ))
            
            fig.update_layout(
                title="経済指標ボラティリティサーフェス",
                scene=dict(
                    xaxis_title="指標",
                    yaxis_title="国",
                    zaxis_title="ボラティリティ(%)"
                ),
                width=self.config.width,
                height=self.config.height
            )
            
            return {
                'figure': fig,
                'html': fig.to_html(include_plotlyjs='cdn'),
                'volatility_data': vol_pivot.to_dict(),
                'type': 'volatility_surface'
            }
            
        except Exception as e:
            logger.error(f"ボラティリティサーフェス可視化エラー: {e}")
            return {'error': str(e)}
    
    def _create_regime_detection(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """レジーム検出可視化"""
        try:
            # 主要指標のレジーム検出
            regime_data = []
            
            for indicator in indicators[:5]:  # 上位5指標
                if indicator.historical_data is not None and len(indicator.historical_data) > 50:
                    data = indicator.historical_data
                    event = indicator.original_event
                    
                    # 簡易レジーム検出（移動平均ベース）
                    short_ma = data.rolling(10).mean()
                    long_ma = data.rolling(30).mean()
                    
                    # レジーム判定
                    regime = np.where(short_ma > long_ma, 1, 0)  # 1: 上昇レジーム, 0: 下降レジーム
                    
                    regime_data.append({
                        'indicator': f"{event.country}_{getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')}",
                        'dates': data.index,
                        'values': data.values,
                        'regime': regime,
                        'short_ma': short_ma.values,
                        'long_ma': long_ma.values
                    })
            
            if not regime_data:
                return {'error': 'レジーム検出に十分なデータがありません'}
            
            # レジーム可視化
            fig = make_subplots(
                rows=len(regime_data), cols=1,
                subplot_titles=[data['indicator'] for data in regime_data],
                vertical_spacing=0.05
            )
            
            for i, data in enumerate(regime_data):
                # メインデータ
                fig.add_trace(
                    go.Scatter(
                        x=data['dates'],
                        y=data['values'],
                        mode='lines',
                        name=f"{data['indicator']} 値",
                        line=dict(color='blue', width=1)
                    ),
                    row=i+1, col=1
                )
                
                # 移動平均
                fig.add_trace(
                    go.Scatter(
                        x=data['dates'],
                        y=data['short_ma'],
                        mode='lines',
                        name=f"{data['indicator']} 短期MA",
                        line=dict(color='red', width=1, dash='dash')
                    ),
                    row=i+1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=data['dates'],
                        y=data['long_ma'],
                        mode='lines',
                        name=f"{data['indicator']} 長期MA",
                        line=dict(color='green', width=1, dash='dash')
                    ),
                    row=i+1, col=1
                )
                
                # レジーム背景
                regime_changes = np.diff(data['regime'])
                change_points = np.where(regime_changes != 0)[0]
                
                for j, change_point in enumerate(change_points):
                    start_date = data['dates'][change_point]
                    end_date = data['dates'][change_point + 1] if change_point + 1 < len(data['dates']) else data['dates'][-1]
                    
                    fig.add_vrect(
                        x0=start_date, x1=end_date,
                        fillcolor="red" if data['regime'][change_point] == 1 else "blue",
                        opacity=0.1,
                        row=i+1, col=1
                    )
            
            fig.update_layout(
                title="経済指標レジーム検出分析",
                width=self.config.width,
                height=self.config.height * len(regime_data) // 2,
                showlegend=False
            )
            
            return {
                'figure': fig,
                'html': fig.to_html(include_plotlyjs='cdn'),
                'regime_data': regime_data,
                'type': 'regime_detection'
            }
            
        except Exception as e:
            logger.error(f"レジーム検出可視化エラー: {e}")
            return {'error': str(e)}
    
    def _create_forecast_accuracy(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """予測精度可視化"""
        try:
            # 予測精度データ準備
            accuracy_data = []
            
            for indicator in indicators:
                event = indicator.original_event
                if event.actual is not None and event.forecast is not None and event.forecast != 0:
                    # 予測精度計算
                    accuracy = 100 - abs((event.actual - event.forecast) / event.forecast * 100)
                    error = abs(event.actual - event.forecast)
                    error_pct = abs((event.actual - event.forecast) / event.forecast * 100)
                    
                    accuracy_data.append({
                        'country': event.country,
                        'indicator': getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A'),
                        'accuracy': accuracy,
                        'error': error,
                        'error_pct': error_pct,
                        'actual': event.actual,
                        'forecast': event.forecast
                    })
            
            if not accuracy_data:
                return {'error': '予測精度データがありません'}
            
            df_accuracy = pd.DataFrame(accuracy_data)
            
            # 可視化
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=[
                    "予測精度分布", "国別平均精度",
                    "精度vs誤差率", "予測vs実際値"
                ]
            )
            
            # 予測精度分布
            fig.add_trace(
                go.Histogram(
                    x=df_accuracy['accuracy'],
                    nbinsx=20,
                    name="予測精度分布",
                    marker_color=self.config.color_palette[0]
                ),
                row=1, col=1
            )
            
            # 国別平均精度
            country_accuracy = df_accuracy.groupby('country')['accuracy'].mean().sort_values(ascending=False)
            fig.add_trace(
                go.Bar(
                    x=country_accuracy.index,
                    y=country_accuracy.values,
                    name="国別平均精度",
                    marker_color=self.config.color_palette[1]
                ),
                row=1, col=2
            )
            
            # 精度vs誤差率
            fig.add_trace(
                go.Scatter(
                    x=df_accuracy['error_pct'],
                    y=df_accuracy['accuracy'],
                    mode='markers',
                    name="精度vs誤差率",
                    marker=dict(
                        color=df_accuracy['accuracy'],
                        colorscale='RdYlGn',
                        showscale=True,
                        colorbar=dict(title="精度(%)")
                    ),
                    text=df_accuracy['indicator'],
                    hovertemplate='%{text}<br>誤差率: %{x:.1f}%<br>精度: %{y:.1f}%<extra></extra>'
                ),
                row=2, col=1
            )
            
            # 予測vs実際値
            fig.add_trace(
                go.Scatter(
                    x=df_accuracy['forecast'],
                    y=df_accuracy['actual'],
                    mode='markers',
                    name="予測vs実際値",
                    marker=dict(
                        color=df_accuracy['accuracy'],
                        colorscale='RdYlGn',
                        showscale=True,
                        colorbar=dict(title="精度(%)")
                    ),
                    text=df_accuracy['indicator'],
                    hovertemplate='%{text}<br>予測: %{x}<br>実際: %{y}<extra></extra>'
                ),
                row=2, col=2
            )
            
            # 完璧な予測線
            min_val = min(df_accuracy['forecast'].min(), df_accuracy['actual'].min())
            max_val = max(df_accuracy['forecast'].max(), df_accuracy['actual'].max())
            fig.add_trace(
                go.Scatter(
                    x=[min_val, max_val],
                    y=[min_val, max_val],
                    mode='lines',
                    name="完璧な予測",
                    line=dict(dash='dash', color='red'),
                    showlegend=False
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                title="経済指標予測精度分析",
                width=self.config.width,
                height=self.config.height,
                showlegend=False
            )
            
            # 統計情報
            stats_info = {
                'mean_accuracy': df_accuracy['accuracy'].mean(),
                'median_accuracy': df_accuracy['accuracy'].median(),
                'std_accuracy': df_accuracy['accuracy'].std(),
                'best_forecast': df_accuracy.loc[df_accuracy['accuracy'].idxmax()].to_dict(),
                'worst_forecast': df_accuracy.loc[df_accuracy['accuracy'].idxmin()].to_dict()
            }
            
            return {
                'figure': fig,
                'html': fig.to_html(include_plotlyjs='cdn'),
                'accuracy_data': df_accuracy.to_dict('records'),
                'statistics': stats_info,
                'type': 'forecast_accuracy'
            }
            
        except Exception as e:
            logger.error(f"予測精度可視化エラー: {e}")
            return {'error': str(e)}
    
    def _create_risk_metrics(self, indicators: List[ProcessedIndicator], trend_results: Optional[List[TrendResult]]) -> Dict[str, Any]:
        """リスクメトリクス可視化"""
        try:
            # リスクデータ準備
            risk_data = []
            
            for i, indicator in enumerate(indicators):
                event = indicator.original_event
                trend_result = trend_results[i] if trend_results and i < len(trend_results) else None
                
                # 各種リスクメトリクス計算
                risk_metrics = {
                    'country': event.country,
                    'indicator': getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A'),
                    'data_quality_risk': 100 - indicator.data_quality_score,
                    'volatility_risk': getattr(indicator, 'volatility_index', 0) or 0,
                    'trend_risk': 0,
                    'surprise_risk': 0
                }
                
                # トレンドリスク
                if trend_result:
                    if trend_result.trend_type.value == "反転":
                        risk_metrics['trend_risk'] = 100 - trend_result.confidence_level
                    else:
                        risk_metrics['trend_risk'] = 50 - trend_result.confidence_level
                
                # サプライズリスク
                if event.actual is not None and event.forecast is not None:
                    surprise_info = event.calculate_surprise()
                    if surprise_info:
                        risk_metrics['surprise_risk'] = abs(surprise_info['surprise_pct'])
                
                # 総合リスクスコア
                risk_metrics['total_risk'] = (
                    risk_metrics['data_quality_risk'] * 0.3 +
                    risk_metrics['volatility_risk'] * 0.3 +
                    risk_metrics['trend_risk'] * 0.2 +
                    risk_metrics['surprise_risk'] * 0.2
                )
                
                risk_data.append(risk_metrics)
            
            if not risk_data:
                return {'error': 'リスクデータがありません'}
            
            df_risk = pd.DataFrame(risk_data)
            
            # 可視化
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=[
                    "総合リスク分布", "リスク要因別分析",
                    "国別リスク比較", "リスクvsリターン"
                ]
            )
            
            # 総合リスク分布
            fig.add_trace(
                go.Histogram(
                    x=df_risk['total_risk'],
                    nbinsx=20,
                    name="総合リスク分布",
                    marker_color=self.config.color_palette[0]
                ),
                row=1, col=1
            )
            
            # リスク要因別分析
            risk_factors = ['data_quality_risk', 'volatility_risk', 'trend_risk', 'surprise_risk']
            risk_means = [df_risk[factor].mean() for factor in risk_factors]
            
            fig.add_trace(
                go.Bar(
                    x=['データ品質', 'ボラティリティ', 'トレンド', 'サプライズ'],
                    y=risk_means,
                    name="リスク要因別平均",
                    marker_color=self.config.color_palette[1]
                ),
                row=1, col=2
            )
            
            # 国別リスク比較
            country_risk = df_risk.groupby('country')['total_risk'].mean().sort_values(ascending=False)
            fig.add_trace(
                go.Bar(
                    x=country_risk.index,
                    y=country_risk.values,
                    name="国別平均リスク",
                    marker_color=self.config.color_palette[2]
                ),
                row=2, col=1
            )
            
            # リスクvsリターン（簡易版）
            # リターンは変化率で代用
            returns = []
            for indicator in indicators:
                if indicator.yoy_change:
                    returns.append(indicator.yoy_change)
                else:
                    returns.append(0)
            
            fig.add_trace(
                go.Scatter(
                    x=df_risk['total_risk'],
                    y=returns[:len(df_risk)],
                    mode='markers',
                    name="リスクvsリターン",
                    marker=dict(
                        color=df_risk['total_risk'],
                        colorscale='RdYlGn_r',
                        showscale=True,
                        colorbar=dict(title="リスクスコア")
                    ),
                    text=df_risk['indicator'],
                    hovertemplate='%{text}<br>リスク: %{x:.1f}<br>リターン: %{y:.1f}%<extra></extra>'
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                title="経済指標リスクメトリクス分析",
                width=self.config.width,
                height=self.config.height,
                showlegend=False
            )
            
            # リスク統計
            risk_stats = {
                'high_risk_count': len(df_risk[df_risk['total_risk'] > 70]),
                'medium_risk_count': len(df_risk[(df_risk['total_risk'] > 40) & (df_risk['total_risk'] <= 70)]),
                'low_risk_count': len(df_risk[df_risk['total_risk'] <= 40]),
                'highest_risk': df_risk.loc[df_risk['total_risk'].idxmax()].to_dict(),
                'lowest_risk': df_risk.loc[df_risk['total_risk'].idxmin()].to_dict()
            }
            
            return {
                'figure': fig,
                'html': fig.to_html(include_plotlyjs='cdn'),
                'risk_data': df_risk.to_dict('records'),
                'risk_statistics': risk_stats,
                'type': 'risk_metrics'
            }
            
        except Exception as e:
            logger.error(f"リスクメトリクス可視化エラー: {e}")
            return {'error': str(e)}
    
    def _create_sector_analysis(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """セクター分析可視化"""
        # 実装は省略（セクター分類が必要）
        return {'error': 'セクター分析は実装予定です'}
    
    def _create_country_comparison(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """国別比較可視化"""
        try:
            # 国別データ準備
            country_data = {}
            
            for indicator in indicators:
                country = indicator.original_event.country
                if country not in country_data:
                    country_data[country] = {
                        'indicators': [],
                        'avg_quality': 0,
                        'surprise_count': 0,
                        'volatility_sum': 0
                    }
                
                country_data[country]['indicators'].append(indicator)
                country_data[country]['avg_quality'] += indicator.data_quality_score
                
                # サプライズカウント
                event = indicator.original_event
                if event.actual and event.forecast:
                    surprise_info = event.calculate_surprise()
                    if surprise_info and abs(surprise_info['surprise_pct']) > 5:
                        country_data[country]['surprise_count'] += 1
                
                # ボラティリティ
                if hasattr(indicator, 'volatility_index') and indicator.volatility_index:
                    country_data[country]['volatility_sum'] += indicator.volatility_index
            
            # 平均値計算
            for country in country_data:
                count = len(country_data[country]['indicators'])
                country_data[country]['avg_quality'] /= count
                country_data[country]['avg_volatility'] = country_data[country]['volatility_sum'] / count if count > 0 else 0
            
            # 可視化
            countries = list(country_data.keys())
            avg_qualities = [country_data[c]['avg_quality'] for c in countries]
            surprise_counts = [country_data[c]['surprise_count'] for c in countries]
            avg_volatilities = [country_data[c]['avg_volatility'] for c in countries]
            
            fig = make_subplots(
                rows=1, cols=3,
                subplot_titles=["平均データ品質", "サプライズ件数", "平均ボラティリティ"]
            )
            
            # 平均データ品質
            fig.add_trace(
                go.Bar(
                    x=countries,
                    y=avg_qualities,
                    name="平均データ品質",
                    marker_color=self.config.color_palette[0]
                ),
                row=1, col=1
            )
            
            # サプライズ件数
            fig.add_trace(
                go.Bar(
                    x=countries,
                    y=surprise_counts,
                    name="サプライズ件数",
                    marker_color=self.config.color_palette[1]
                ),
                row=1, col=2
            )
            
            # 平均ボラティリティ
            fig.add_trace(
                go.Bar(
                    x=countries,
                    y=avg_volatilities,
                    name="平均ボラティリティ",
                    marker_color=self.config.color_palette[2]
                ),
                row=1, col=3
            )
            
            fig.update_layout(
                title="国別経済指標比較分析",
                width=self.config.width,
                height=self.config.height // 2,
                showlegend=False
            )
            
            return {
                'figure': fig,
                'html': fig.to_html(include_plotlyjs='cdn'),
                'country_data': country_data,
                'type': 'country_comparison'
            }
            
        except Exception as e:
            logger.error(f"国別比較可視化エラー: {e}")
            return {'error': str(e)}
    
    def _create_time_series_decomposition(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """時系列分解可視化"""
        try:
            # 主要指標の時系列分解
            decomposition_data = []
            
            for indicator in indicators[:3]:  # 上位3指標
                if indicator.historical_data is not None and len(indicator.historical_data) > 50:
                    data = indicator.historical_data
                    event = indicator.original_event
                    
                    # 簡易時系列分解
                    # トレンド（移動平均）
                    trend = data.rolling(12, center=True).mean()
                    
                    # 季節性（簡易版）
                    seasonal = data.groupby(data.index.month).transform('mean') - data.mean()
                    
                    # 残差
                    residual = data - trend - seasonal
                    
                    decomposition_data.append({
                        'indicator': f"{event.country}_{getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')}",
                        'dates': data.index,
                        'original': data.values,
                        'trend': trend.values,
                        'seasonal': seasonal.values,
                        'residual': residual.values
                    })
            
            if not decomposition_data:
                return {'error': '時系列分解に十分なデータがありません'}
            
            # 可視化
            fig = make_subplots(
                rows=len(decomposition_data), cols=4,
                subplot_titles=[
                    f"{data['indicator']} - 元データ" for data in decomposition_data
                ] + [
                    f"{data['indicator']} - トレンド" for data in decomposition_data
                ] + [
                    f"{data['indicator']} - 季節性" for data in decomposition_data
                ] + [
                    f"{data['indicator']} - 残差" for data in decomposition_data
                ],
                vertical_spacing=0.05
            )
            
            for i, data in enumerate(decomposition_data):
                # 元データ
                fig.add_trace(
                    go.Scatter(
                        x=data['dates'],
                        y=data['original'],
                        mode='lines',
                        name=f"{data['indicator']} 元データ",
                        line=dict(color='blue', width=1)
                    ),
                    row=i+1, col=1
                )
                
                # トレンド
                fig.add_trace(
                    go.Scatter(
                        x=data['dates'],
                        y=data['trend'],
                        mode='lines',
                        name=f"{data['indicator']} トレンド",
                        line=dict(color='red', width=2)
                    ),
                    row=i+1, col=2
                )
                
                # 季節性
                fig.add_trace(
                    go.Scatter(
                        x=data['dates'],
                        y=data['seasonal'],
                        mode='lines',
                        name=f"{data['indicator']} 季節性",
                        line=dict(color='green', width=1)
                    ),
                    row=i+1, col=3
                )
                
                # 残差
                fig.add_trace(
                    go.Scatter(
                        x=data['dates'],
                        y=data['residual'],
                        mode='lines',
                        name=f"{data['indicator']} 残差",
                        line=dict(color='orange', width=1)
                    ),
                    row=i+1, col=4
                )
            
            fig.update_layout(
                title="経済指標時系列分解分析",
                width=self.config.width,
                height=self.config.height * len(decomposition_data) // 2,
                showlegend=False
            )
            
            return {
                'figure': fig,
                'html': fig.to_html(include_plotlyjs='cdn'),
                'decomposition_data': decomposition_data,
                'type': 'time_series_decomposition'
            }
            
        except Exception as e:
            logger.error(f"時系列分解可視化エラー: {e}")
            return {'error': str(e)}
    
    def _create_distribution_analysis(self, indicators: List[ProcessedIndicator]) -> Dict[str, Any]:
        """分布分析可視化"""
        try:
            # 分布データ準備
            distribution_data = []
            
            for indicator in indicators:
                if indicator.historical_data is not None and len(indicator.historical_data) > 20:
                    data = indicator.historical_data
                    event = indicator.original_event
                    
                    # 統計量計算
                    returns = data.pct_change().dropna()
                    
                    if len(returns) > 10:
                        # 正規性検定
                        try:
                            _, p_value = normaltest(returns)
                            is_normal = p_value > 0.05
                        except:
                            is_normal = False
                        
                        distribution_data.append({
                            'indicator': f"{event.country}_{getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')}",
                            'returns': returns.values,
                            'mean': returns.mean(),
                            'std': returns.std(),
                            'skewness': returns.skew(),
                            'kurtosis': returns.kurtosis(),
                            'is_normal': is_normal,
                            'jarque_bera_p': 0  # 簡易版
                        })
            
            if not distribution_data:
                return {'error': '分布分析に十分なデータがありません'}
            
            # 可視化
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=[
                    "リターン分布", "統計量比較",
                    "正規性検定結果", "歪度・尖度分析"
                ]
            )
            
            # リターン分布
            for i, data in enumerate(distribution_data[:5]):  # 上位5指標
                fig.add_trace(
                    go.Histogram(
                        x=data['returns'],
                        name=data['indicator'],
                        opacity=0.7,
                        nbinsx=30
                    ),
                    row=1, col=1
                )
            
            # 統計量比較
            indicators_names = [data['indicator'] for data in distribution_data]
            means = [data['mean'] for data in distribution_data]
            stds = [data['std'] for data in distribution_data]
            
            fig.add_trace(
                go.Scatter(
                    x=means,
                    y=stds,
                    mode='markers+text',
                    text=indicators_names,
                    textposition='top center',
                    name="平均vs標準偏差",
                    marker=dict(
                        size=stds,
                        color=means,
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title="平均リターン")
                    )
                ),
                row=1, col=2
            )
            
            # 正規性検定結果
            normal_count = sum(1 for data in distribution_data if data['is_normal'])
            non_normal_count = len(distribution_data) - normal_count
            
            fig.add_trace(
                go.Pie(
                    labels=['正規分布', '非正規分布'],
                    values=[normal_count, non_normal_count],
                    name="正規性検定結果"
                ),
                row=2, col=1
            )
            
            # 歪度・尖度分析
            skewness = [data['skewness'] for data in distribution_data]
            kurtosis = [data['kurtosis'] for data in distribution_data]
            
            fig.add_trace(
                go.Scatter(
                    x=skewness,
                    y=kurtosis,
                    mode='markers+text',
                    text=indicators_names,
                    textposition='top center',
                    name="歪度vs尖度",
                    marker=dict(
                        size=abs(np.array(kurtosis)) + 1,
                        color=skewness,
                        colorscale='RdBu',
                        showscale=True,
                        colorbar=dict(title="歪度")
                    )
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                title="経済指標分布分析",
                width=self.config.width,
                height=self.config.height,
                showlegend=False
            )
            
            return {
                'figure': fig,
                'html': fig.to_html(include_plotlyjs='cdn'),
                'distribution_data': distribution_data,
                'type': 'distribution_analysis'
            }
            
        except Exception as e:
            logger.error(f"分布分析可視化エラー: {e}")
            return {'error': str(e)}
    
    def _perform_correlation_clustering(self, correlation_matrix: pd.DataFrame) -> Dict[str, Any]:
        """相関クラスタリング分析"""
        try:
            # 距離行列計算（1 - |相関|）
            distance_matrix = 1 - np.abs(correlation_matrix.values)
            
            # K-meansクラスタリング
            n_clusters = min(3, len(correlation_matrix.columns))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(distance_matrix)
            
            # クラスタ結果
            clusters = {}
            for i, label in enumerate(cluster_labels):
                indicator_name = correlation_matrix.columns[i]
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(indicator_name)
            
            return {
                'clusters': clusters,
                'cluster_labels': cluster_labels.tolist(),
                'n_clusters': n_clusters
            }
            
        except Exception as e:
            logger.error(f"相関クラスタリングエラー: {e}")
            return {'error': str(e)}
