"""
Advanced Dashboard for Economic Indicators
高度な経済指標ダッシュボード

インタラクティブな可視化、リアルタイム更新、高度な分析機能を提供
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
import base64
from dataclasses import dataclass, field

# 可視化ライブラリ
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
import matplotlib.pyplot as plt
import seaborn as sns

# 既存モジュール
from ..config.settings import EconConfig
from ..normalize.data_processor import ProcessedIndicator
from ..normalize.trend_analyzer import TrendResult
from ..render.chart_generator import ChartGenerator, ChartConfig, ChartType, ChartEngine

logger = logging.getLogger(__name__)


@dataclass
class DashboardConfig:
    """ダッシュボード設定"""
    # 基本設定
    title: str = "経済指標ダッシュボード"
    theme: str = "plotly_white"
    width: int = 1400
    height: int = 800
    
    # レイアウト設定
    rows: int = 3
    cols: int = 2
    subplot_titles: List[str] = field(default_factory=lambda: [
        "主要指標トレンド", "相関マトリクス", 
        "リスク評価", "サプライズ分析",
        "ボラティリティ分析", "予測精度"
    ])
    
    # 色設定
    color_palette: List[str] = field(default_factory=lambda: [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
        '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'
    ])
    
    # インタラクティブ機能
    show_range_selector: bool = True
    show_hover: bool = True
    show_annotations: bool = True
    
    # 出力設定
    output_format: List[str] = field(default_factory=lambda: ["html", "png"])
    save_path: Optional[Path] = None


class AdvancedDashboard:
    """高度な経済指標ダッシュボード"""
    
    def __init__(self, config: Optional[DashboardConfig] = None):
        self.config = config or DashboardConfig()
        self.chart_generator = ChartGenerator()
        
    def create_comprehensive_dashboard(
        self,
        indicators: List[ProcessedIndicator],
        trend_results: Optional[List[TrendResult]] = None
    ) -> Dict[str, Any]:
        """包括的なダッシュボードを作成"""
        
        try:
            # サブプロット作成
            fig = make_subplots(
                rows=self.config.rows,
                cols=self.config.cols,
                subplot_titles=self.config.subplot_titles,
                specs=[
                    [{"secondary_y": True}, {"type": "heatmap"}],
                    [{"type": "bar"}, {"type": "scatter"}],
                    [{"type": "scatter"}, {"type": "scatter"}]
                ],
                vertical_spacing=0.08,
                horizontal_spacing=0.1
            )
            
            # 各チャートを追加
            self._add_trend_chart(fig, indicators, trend_results)
            self._add_correlation_heatmap(fig, indicators)
            self._add_risk_assessment(fig, indicators, trend_results)
            self._add_surprise_analysis(fig, indicators)
            self._add_volatility_analysis(fig, indicators)
            self._add_forecast_accuracy(fig, indicators)
            
            # レイアウト設定
            self._configure_layout(fig)
            
            # ダッシュボード情報を生成
            dashboard_info = self._generate_dashboard_info(indicators, trend_results)
            
            # HTML生成
            html_content = self._generate_html_dashboard(fig, dashboard_info)
            
            # ファイル保存
            saved_files = []
            if self.config.save_path:
                saved_files = self._save_dashboard(fig, html_content, dashboard_info)
            
            return {
                'figure': fig,
                'html': html_content,
                'dashboard_info': dashboard_info,
                'saved_files': saved_files,
                'type': 'advanced_dashboard'
            }
            
        except Exception as e:
            logger.error(f"ダッシュボード作成エラー: {e}")
            return {'error': str(e)}
    
    def _add_trend_chart(self, fig, indicators: List[ProcessedIndicator], trend_results: Optional[List[TrendResult]]):
        """トレンドチャートを追加"""
        try:
            # 主要指標のトレンドを表示
            key_indicators = self._get_key_indicators(indicators)
            
            for i, indicator in enumerate(key_indicators[:5]):  # 上位5指標
                if indicator.historical_data is not None:
                    data = indicator.historical_data
                    event = indicator.original_event
                    
                    # メインライン
                    fig.add_trace(
                        go.Scatter(
                            x=data.index,
                            y=data.values,
                            mode='lines+markers',
                            name=f"{event.country} {getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')}",
                            line=dict(color=self.config.color_palette[i % len(self.config.color_palette)], width=2),
                            marker=dict(size=4),
                            hovertemplate='%{x}<br>%{y:.2f}<extra></extra>'
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
                                name=f"{event.country} MA12",
                                line=dict(dash='dash', width=1),
                                opacity=0.7,
                                showlegend=False
                            ),
                            row=1, col=1
                        )
            
            # トレンドライン（trend_resultsから）
            if trend_results:
                for i, trend_result in enumerate(trend_results[:3]):  # 上位3つ
                    if trend_result and hasattr(trend_result, 'slope'):
                        # トレンドラインの描画
                        indicator = indicators[i] if i < len(indicators) else None
                        if indicator and indicator.historical_data is not None:
                            data = indicator.historical_data
                            x_trend = np.arange(len(data))
                            y_trend = trend_result.slope * x_trend + data.iloc[0]
                            
                            fig.add_trace(
                                go.Scatter(
                                    x=data.index,
                                    y=y_trend,
                                    mode='lines',
                                    name=f"トレンド {trend_result.trend_type.value}",
                                    line=dict(dash='dot', width=2, color='orange'),
                                    opacity=0.8,
                                    showlegend=False
                                ),
                                row=1, col=1
                            )
            
        except Exception as e:
            logger.error(f"トレンドチャート追加エラー: {e}")
    
    def _add_correlation_heatmap(self, fig, indicators: List[ProcessedIndicator]):
        """相関ヒートマップを追加"""
        try:
            correlation_matrix = self._generate_correlation_matrix(indicators)
            
            if correlation_matrix is not None and not correlation_matrix.empty:
                fig.add_trace(
                    go.Heatmap(
                        z=correlation_matrix.values,
                        x=correlation_matrix.columns,
                        y=correlation_matrix.index,
                        colorscale='RdBu',
                        zmid=0,
                        text=np.around(correlation_matrix.values, decimals=2),
                        texttemplate='%{text}',
                        textfont={"size": 10},
                        hovertemplate='相関: %{z:.2f}<extra></extra>'
                    ),
                    row=1, col=2
                )
            else:
                # データがない場合のプレースホルダー
                fig.add_annotation(
                    x=0.5, y=0.5,
                    text="相関データが不足しています",
                    showarrow=False,
                    row=1, col=2
                )
                
        except Exception as e:
            logger.error(f"相関ヒートマップ追加エラー: {e}")
    
    def _add_risk_assessment(self, fig, indicators: List[ProcessedIndicator], trend_results: Optional[List[TrendResult]]):
        """リスク評価チャートを追加"""
        try:
            risks = self._assess_risks(indicators, trend_results)
            
            if risks:
                risk_types = [risk['type'] for risk in risks]
                risk_counts = [risk['indicator_count'] for risk in risks]
                risk_severities = [risk['severity'] for risk in risks]
                
                # 重要度に応じて色を設定
                colors = []
                for severity in risk_severities:
                    if severity == 'high':
                        colors.append('#d62728')  # 赤
                    elif severity == 'medium':
                        colors.append('#ff7f0e')  # オレンジ
                    else:
                        colors.append('#2ca02c')  # 緑
                
                fig.add_trace(
                    go.Bar(
                        x=risk_types,
                        y=risk_counts,
                        marker_color=colors,
                        text=risk_counts,
                        textposition='auto',
                        hovertemplate='%{x}<br>影響指標数: %{y}<extra></extra>'
                    ),
                    row=2, col=1
                )
            else:
                fig.add_annotation(
                    x=0.5, y=0.5,
                    text="リスクは検出されませんでした",
                    showarrow=False,
                    row=2, col=1
                )
                
        except Exception as e:
            logger.error(f"リスク評価チャート追加エラー: {e}")
    
    def _add_surprise_analysis(self, fig, indicators: List[ProcessedIndicator]):
        """サプライズ分析チャートを追加"""
        try:
            surprises = []
            countries = []
            indicators_names = []
            
            for indicator in indicators:
                event = indicator.original_event
                if event.actual is not None and event.forecast is not None:
                    surprise_info = event.calculate_surprise()
                    if surprise_info:
                        surprises.append(surprise_info['surprise_pct'])
                        countries.append(event.country)
                        indicators_names.append(getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A'))
            
            if surprises:
                # 色分け（ポジティブ/ネガティブ）
                colors = ['green' if s > 0 else 'red' for s in surprises]
                
                fig.add_trace(
                    go.Scatter(
                        x=countries,
                        y=surprises,
                        mode='markers+text',
                        marker=dict(
                            size=abs(np.array(surprises)) * 2 + 10,  # サプライズの大きさに応じてサイズ調整
                            color=colors,
                            opacity=0.7
                        ),
                        text=indicators_names,
                        textposition='top center',
                        hovertemplate='%{text}<br>サプライズ: %{y:+.2f}%<extra></extra>'
                    ),
                    row=2, col=2
                )
            else:
                fig.add_annotation(
                    x=0.5, y=0.5,
                    text="サプライズデータがありません",
                    showarrow=False,
                    row=2, col=2
                )
                
        except Exception as e:
            logger.error(f"サプライズ分析チャート追加エラー: {e}")
    
    def _add_volatility_analysis(self, fig, indicators: List[ProcessedIndicator]):
        """ボラティリティ分析チャートを追加"""
        try:
            volatilities = []
            countries = []
            indicators_names = []
            
            for indicator in indicators:
                if hasattr(indicator, 'volatility_index') and indicator.volatility_index:
                    volatilities.append(indicator.volatility_index)
                    event = indicator.original_event
                    countries.append(event.country)
                    indicators_names.append(getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A'))
            
            if volatilities:
                fig.add_trace(
                    go.Scatter(
                        x=countries,
                        y=volatilities,
                        mode='markers+text',
                        marker=dict(
                            size=volatilities,
                            color=volatilities,
                            colorscale='Viridis',
                            showscale=True,
                            colorbar=dict(title="ボラティリティ(%)")
                        ),
                        text=indicators_names,
                        textposition='top center',
                        hovertemplate='%{text}<br>ボラティリティ: %{y:.1f}%<extra></extra>'
                    ),
                    row=3, col=1
                )
            else:
                fig.add_annotation(
                    x=0.5, y=0.5,
                    text="ボラティリティデータがありません",
                    showarrow=False,
                    row=3, col=1
                )
                
        except Exception as e:
            logger.error(f"ボラティリティ分析チャート追加エラー: {e}")
    
    def _add_forecast_accuracy(self, fig, indicators: List[ProcessedIndicator]):
        """予測精度チャートを追加"""
        try:
            accuracies = []
            countries = []
            indicators_names = []
            
            for indicator in indicators:
                event = indicator.original_event
                if event.actual is not None and event.forecast is not None:
                    # 予測精度を計算（実際値と予想値の差の絶対値）
                    accuracy = 100 - abs((event.actual - event.forecast) / event.forecast * 100) if event.forecast != 0 else 0
                    accuracies.append(accuracy)
                    countries.append(event.country)
                    indicators_names.append(getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A'))
            
            if accuracies:
                fig.add_trace(
                    go.Scatter(
                        x=countries,
                        y=accuracies,
                        mode='markers+text',
                        marker=dict(
                            size=accuracies,
                            color=accuracies,
                            colorscale='RdYlGn',
                            showscale=True,
                            colorbar=dict(title="予測精度(%)")
                        ),
                        text=indicators_names,
                        textposition='top center',
                        hovertemplate='%{text}<br>予測精度: %{y:.1f}%<extra></extra>'
                    ),
                    row=3, col=2
                )
            else:
                fig.add_annotation(
                    x=0.5, y=0.5,
                    text="予測精度データがありません",
                    showarrow=False,
                    row=3, col=2
                )
                
        except Exception as e:
            logger.error(f"予測精度チャート追加エラー: {e}")
    
    def _configure_layout(self, fig):
        """レイアウトを設定"""
        fig.update_layout(
            title=dict(
                text=self.config.title,
                font=dict(size=20, family="Arial, sans-serif"),
                x=0.5
            ),
            width=self.config.width,
            height=self.config.height,
            showlegend=True,
            hovermode='closest',
            template=self.config.theme,
            font=dict(family="Arial, sans-serif", size=12)
        )
        
        # 各サブプロットの軸ラベル
        fig.update_xaxes(title_text="日付", row=1, col=1)
        fig.update_yaxes(title_text="値", row=1, col=1)
        
        fig.update_xaxes(title_text="指標", row=1, col=2)
        fig.update_yaxes(title_text="指標", row=1, col=2)
        
        fig.update_xaxes(title_text="リスクタイプ", row=2, col=1)
        fig.update_yaxes(title_text="影響指標数", row=2, col=1)
        
        fig.update_xaxes(title_text="国", row=2, col=2)
        fig.update_yaxes(title_text="サプライズ(%)", row=2, col=2)
        
        fig.update_xaxes(title_text="国", row=3, col=1)
        fig.update_yaxes(title_text="ボラティリティ(%)", row=3, col=1)
        
        fig.update_xaxes(title_text="国", row=3, col=2)
        fig.update_yaxes(title_text="予測精度(%)", row=3, col=2)
    
    def _generate_dashboard_info(self, indicators: List[ProcessedIndicator], trend_results: Optional[List[TrendResult]]) -> Dict[str, Any]:
        """ダッシュボード情報を生成"""
        try:
            # 基本統計
            total_indicators = len(indicators)
            countries = list(set(ind.original_event.country for ind in indicators))
            avg_quality = sum(ind.data_quality_score for ind in indicators) / total_indicators if indicators else 0
            
            # サプライズ統計
            surprises = []
            for indicator in indicators:
                event = indicator.original_event
                if event.actual and event.forecast:
                    surprise_info = event.calculate_surprise()
                    if surprise_info:
                        surprises.append(surprise_info['surprise_pct'])
            
            surprise_stats = {
                'count': len(surprises),
                'avg': np.mean(surprises) if surprises else 0,
                'std': np.std(surprises) if surprises else 0,
                'max': np.max(surprises) if surprises else 0,
                'min': np.min(surprises) if surprises else 0
            }
            
            # リスク評価
            risks = self._assess_risks(indicators, trend_results)
            
            # トレンド分布
            trend_distribution = {}
            for indicator in indicators:
                if indicator.trend_direction:
                    trend = indicator.trend_direction.value
                    trend_distribution[trend] = trend_distribution.get(trend, 0) + 1
            
            return {
                'metadata': {
                    'generation_time': datetime.now().isoformat(),
                    'total_indicators': total_indicators,
                    'countries': countries,
                    'avg_data_quality': round(avg_quality, 1)
                },
                'surprise_stats': surprise_stats,
                'risk_assessment': risks,
                'trend_distribution': trend_distribution,
                'key_insights': self._generate_key_insights(indicators, trend_results)
            }
            
        except Exception as e:
            logger.error(f"ダッシュボード情報生成エラー: {e}")
            return {}
    
    def _generate_key_insights(self, indicators: List[ProcessedIndicator], trend_results: Optional[List[TrendResult]]) -> List[str]:
        """主要なインサイトを生成"""
        insights = []
        
        try:
            # 最大サプライズ
            max_surprise = None
            max_surprise_value = 0
            
            for indicator in indicators:
                event = indicator.original_event
                if event.actual and event.forecast:
                    surprise_info = event.calculate_surprise()
                    if surprise_info and abs(surprise_info['surprise_pct']) > abs(max_surprise_value):
                        max_surprise = indicator
                        max_surprise_value = surprise_info['surprise_pct']
            
            if max_surprise:
                event = max_surprise.original_event
                insights.append(f"最大サプライズ: {event.country} {getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')} ({max_surprise_value:+.1f}%)")
            
            # 高ボラティリティ指標
            high_vol_indicators = [
                ind for ind in indicators 
                if hasattr(ind, 'volatility_index') and ind.volatility_index and ind.volatility_index > 20
            ]
            
            if high_vol_indicators:
                insights.append(f"高ボラティリティ指標: {len(high_vol_indicators)}件検出")
            
            # トレンド反転
            if trend_results:
                reversal_count = sum(1 for tr in trend_results if tr.trend_type.value == "反転")
                if reversal_count > 0:
                    insights.append(f"トレンド反転の可能性: {reversal_count}指標")
            
            # データ品質
            low_quality_count = sum(1 for ind in indicators if ind.data_quality_score < 50)
            if low_quality_count > 0:
                insights.append(f"データ品質注意: {low_quality_count}指標")
            
        except Exception as e:
            logger.error(f"インサイト生成エラー: {e}")
        
        return insights
    
    def _generate_html_dashboard(self, fig, dashboard_info: Dict[str, Any]) -> str:
        """HTMLダッシュボードを生成"""
        try:
            # PlotlyチャートのHTML
            chart_html = fig.to_html(include_plotlyjs='cdn', div_id="dashboard-chart")
            
            # ダッシュボード情報のHTML
            info_html = self._generate_info_html(dashboard_info)
            
            # 完全なHTMLページ
            full_html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.title}</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .dashboard-container {{
            display: flex;
            gap: 20px;
        }}
        .chart-section {{
            flex: 2;
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .info-section {{
            flex: 1;
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .info-card {{
            background: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
        }}
        .insight-item {{
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 5px;
        }}
        .metric {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self.config.title}</h1>
        <p>生成日時: {dashboard_info.get('metadata', {}).get('generation_time', 'N/A')}</p>
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
            logger.error(f"HTMLダッシュボード生成エラー: {e}")
            return fig.to_html(include_plotlyjs='cdn')
    
    def _generate_info_html(self, dashboard_info: Dict[str, Any]) -> str:
        """情報セクションのHTMLを生成"""
        try:
            metadata = dashboard_info.get('metadata', {})
            surprise_stats = dashboard_info.get('surprise_stats', {})
            insights = dashboard_info.get('key_insights', [])
            
            html = f"""
            <h3>📊 基本統計</h3>
            <div class="info-card">
                <div class="metric">{metadata.get('total_indicators', 0)}</div>
                <div class="metric-label">総指標数</div>
            </div>
            
            <div class="info-card">
                <div class="metric">{len(metadata.get('countries', []))}</div>
                <div class="metric-label">対象国数</div>
            </div>
            
            <div class="info-card">
                <div class="metric">{metadata.get('avg_data_quality', 0)}/100</div>
                <div class="metric-label">平均データ品質</div>
            </div>
            
            <h3>📈 サプライズ統計</h3>
            <div class="info-card">
                <div class="metric">{surprise_stats.get('count', 0)}</div>
                <div class="metric-label">サプライズ件数</div>
            </div>
            
            <div class="info-card">
                <div class="metric">{surprise_stats.get('avg', 0):+.1f}%</div>
                <div class="metric-label">平均サプライズ</div>
            </div>
            
            <h3>💡 主要インサイト</h3>
            """
            
            for insight in insights:
                html += f'<div class="insight-item">{insight}</div>'
            
            return html
            
        except Exception as e:
            logger.error(f"情報HTML生成エラー: {e}")
            return "<p>情報の生成中にエラーが発生しました。</p>"
    
    def _save_dashboard(self, fig, html_content: str, dashboard_info: Dict[str, Any]) -> List[str]:
        """ダッシュボードを保存"""
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
            
            # JSON保存（ダッシュボード情報）
            if 'json' in self.config.output_format:
                json_path = self.config.save_path.with_suffix('.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(dashboard_info, f, ensure_ascii=False, indent=2)
                saved_files.append(str(json_path))
            
            logger.info(f"ダッシュボードが保存されました: {saved_files}")
            
        except Exception as e:
            logger.error(f"ダッシュボード保存エラー: {e}")
        
        return saved_files
    
    def _get_key_indicators(self, indicators: List[ProcessedIndicator]) -> List[ProcessedIndicator]:
        """主要指標を取得"""
        # 重要度とデータ品質でソート
        def key_score(indicator):
            score = 0
            
            # 重要度スコア
            importance = indicator.original_event.importance
            if importance == 'High':
                score += 100
            elif importance == 'Medium':
                score += 50
            elif importance == 'Low':
                score += 10
            
            # データ品質スコア
            score += indicator.data_quality_score
            
            return score
        
        return sorted(indicators, key=key_score, reverse=True)
    
    def _generate_correlation_matrix(self, indicators: List[ProcessedIndicator]) -> Optional[pd.DataFrame]:
        """相関マトリクスを生成"""
        try:
            data_dict = {}
            for indicator in indicators:
                if indicator.historical_data is not None and len(indicator.historical_data) > 10:
                    event = indicator.original_event
                    key = f"{event.country}_{getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')}"
                    data_dict[key] = indicator.historical_data
            
            if len(data_dict) < 2:
                return None
            
            df = pd.DataFrame(data_dict)
            df = df.dropna()
            
            if df.empty:
                return None
            
            return df.corr()
            
        except Exception as e:
            logger.error(f"相関マトリクス生成エラー: {e}")
            return None
    
    def _assess_risks(self, indicators: List[ProcessedIndicator], trend_results: Optional[List[TrendResult]]) -> List[Dict[str, Any]]:
        """リスク評価"""
        risks = []
        
        try:
            # 高ボラティリティリスク
            high_vol_indicators = [
                ind for ind in indicators 
                if hasattr(ind, 'volatility_index') and ind.volatility_index and ind.volatility_index > 20
            ]
            
            if high_vol_indicators:
                risks.append({
                    'type': '高ボラティリティ',
                    'severity': 'medium',
                    'indicator_count': len(high_vol_indicators)
                })
            
            # データ品質リスク
            low_quality = [ind for ind in indicators if ind.data_quality_score < 50]
            if len(low_quality) > len(indicators) * 0.3:
                risks.append({
                    'type': 'データ品質低下',
                    'severity': 'medium',
                    'indicator_count': len(low_quality)
                })
            
            # トレンド反転リスク
            if trend_results:
                reversal_risks = [
                    tr for tr in trend_results 
                    if tr.trend_type.value == "反転"
                ]
                
                if reversal_risks:
                    risks.append({
                        'type': 'トレンド反転',
                        'severity': 'high',
                        'indicator_count': len(reversal_risks)
                    })
            
        except Exception as e:
            logger.error(f"リスク評価エラー: {e}")
        
        return risks
