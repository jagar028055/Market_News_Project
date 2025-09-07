"""
Detailed Report Generator for Economic Indicators
経済指標詳細レポート生成システム

各指標についてプロフェッショナルレベルの詳細分析レポートを生成
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
from dataclasses import dataclass, field

# 既存モジュール
from ..config.settings import EconConfig
from ..normalize.data_processor import ProcessedIndicator
from ..normalize.trend_analyzer import TrendResult
from .comprehensive_data_collector import ComprehensiveData

logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """レポート設定"""
    # 基本設定
    language: str = "ja"
    format: str = "html"  # html, markdown, pdf
    
    # レポート内容設定
    include_executive_summary: bool = True
    include_technical_analysis: bool = True
    include_fundamental_analysis: bool = True
    include_market_impact: bool = True
    include_forecast_analysis: bool = True
    include_risk_assessment: bool = True
    include_investment_implications: bool = True
    
    # 出力設定
    output_path: Optional[Path] = None
    include_charts: bool = True
    include_tables: bool = True
    include_appendix: bool = True


class DetailedReportGenerator:
    """詳細レポート生成システム"""
    
    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()
    
    def generate_detailed_report(
        self,
        comprehensive_data: ComprehensiveData,
        enhanced_visualization: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """詳細レポートを生成"""
        
        try:
            logger.info("詳細レポート生成開始")
            
            # レポートセクションを生成
            sections = {}
            
            if self.config.include_executive_summary:
                sections['executive_summary'] = self._generate_executive_summary(comprehensive_data)
            
            if self.config.include_technical_analysis:
                sections['technical_analysis'] = self._generate_technical_analysis(comprehensive_data)
            
            if self.config.include_fundamental_analysis:
                sections['fundamental_analysis'] = self._generate_fundamental_analysis(comprehensive_data)
            
            if self.config.include_market_impact:
                sections['market_impact'] = self._generate_market_impact_analysis(comprehensive_data)
            
            if self.config.include_forecast_analysis:
                sections['forecast_analysis'] = self._generate_forecast_analysis(comprehensive_data)
            
            if self.config.include_risk_assessment:
                sections['risk_assessment'] = self._generate_risk_assessment(comprehensive_data)
            
            if self.config.include_investment_implications:
                sections['investment_implications'] = self._generate_investment_implications(comprehensive_data)
            
            if self.config.include_appendix:
                sections['appendix'] = self._generate_appendix(comprehensive_data)
            
            # レポートメタデータ
            metadata = self._generate_report_metadata(comprehensive_data)
            
            # 最終レポートを構築
            if self.config.format == "html":
                final_report = self._build_html_report(sections, metadata, enhanced_visualization)
            elif self.config.format == "markdown":
                final_report = self._build_markdown_report(sections, metadata)
            else:
                final_report = self._build_html_report(sections, metadata, enhanced_visualization)
            
            # ファイル保存
            saved_files = []
            if self.config.output_path:
                saved_files = self._save_report(final_report, metadata)
            
            return {
                'content': final_report,
                'sections': sections,
                'metadata': metadata,
                'saved_files': saved_files,
                'type': 'detailed_report'
            }
            
        except Exception as e:
            logger.error(f"詳細レポート生成エラー: {e}")
            return {'error': str(e)}
    
    def _generate_executive_summary(self, data: ComprehensiveData) -> str:
        """エグゼクティブサマリーを生成"""
        try:
            event = data.main_indicator.original_event
            surprise_info = event.calculate_surprise() if event.actual and event.forecast else None
            
            summary = f"""
## 📊 エグゼクティブサマリー

### 重要ポイント
- **指標**: {event.country} {getattr(event, 'indicator', 'N/A')}
- **発表日時**: {event.datetime.strftime('%Y年%m月%d日 %H:%M') if event.datetime else 'N/A'}
- **重要度**: {event.importance}

### 主要結果
- **実際値**: {event.actual or 'N/A'}
- **予想値**: {event.forecast or 'N/A'}
- **前回値**: {event.previous or 'N/A'}
"""
            
            if surprise_info:
                impact = "ポジティブ" if surprise_info['surprise'] > 0 else "ネガティブ"
                summary += f"""
- **サプライズ**: {surprise_info['surprise']:+.2f} ({surprise_info['surprise_pct']:+.1f}%)
- **市場影響**: {impact}サプライズ
"""
            
            # データ品質評価
            overall_quality = data.data_quality_scores.get('overall', 0)
            quality_level = "優秀" if overall_quality >= 80 else "良好" if overall_quality >= 60 else "普通" if overall_quality >= 40 else "要注意"
            
            summary += f"""
### データ品質
- **総合品質スコア**: {overall_quality:.1f}/100 ({quality_level})
- **データソース数**: {len(data.data_sources)}
- **収集データ種類**: {len(data.historical_data) + len(data.forecast_data) + len(data.market_data)}種類
"""
            
            # 主要インサイト
            insights = self._extract_key_insights(data)
            if insights:
                summary += "\n### 主要インサイト\n"
                for insight in insights[:3]:  # 上位3つ
                    summary += f"- {insight}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"エグゼクティブサマリー生成エラー: {e}")
            return "エグゼクティブサマリーの生成中にエラーが発生しました。"
    
    def _generate_technical_analysis(self, data: ComprehensiveData) -> str:
        """テクニカル分析を生成"""
        try:
            analysis = "## 📈 テクニカル分析\n\n"
            
            # トレンド分析
            if data.trend_result:
                trend = data.trend_result
                analysis += f"""
### トレンド分析
- **トレンドタイプ**: {trend.trend_type.value}
- **信頼度**: {trend.confidence_level:.1f}%
- **パターン**: {trend.pattern_type.value}
- **パターン信頼度**: {trend.pattern_confidence:.1f}%
"""
                
                if trend.support_levels:
                    analysis += f"- **サポートレベル**: {', '.join(f'{level:.2f}' for level in trend.support_levels[:3])}\n"
                
                if trend.resistance_levels:
                    analysis += f"- **レジスタンスレベル**: {', '.join(f'{level:.2f}' for level in trend.resistance_levels[:3])}\n"
            
            # 統計分析
            if data.main_indicator.historical_data is not None:
                hist_data = data.main_indicator.historical_data
                analysis += f"""
### 統計分析
- **平均値**: {hist_data.mean():.2f}
- **中央値**: {hist_data.median():.2f}
- **標準偏差**: {hist_data.std():.2f}
- **最小値**: {hist_data.min():.2f}
- **最大値**: {hist_data.max():.2f}
- **歪度**: {hist_data.skew():.2f}
- **尖度**: {hist_data.kurtosis():.2f}
"""
            
            # ボラティリティ分析
            if hasattr(data.main_indicator, 'volatility_index') and data.main_indicator.volatility_index:
                vol = data.main_indicator.volatility_index
                vol_level = "高" if vol > 20 else "中" if vol > 10 else "低"
                analysis += f"""
### ボラティリティ分析
- **ボラティリティ指数**: {vol:.1f}% ({vol_level}ボラティリティ)
- **リスク評価**: {'高リスク' if vol > 20 else '中リスク' if vol > 10 else '低リスク'}
"""
            
            return analysis
            
        except Exception as e:
            logger.error(f"テクニカル分析生成エラー: {e}")
            return "テクニカル分析の生成中にエラーが発生しました。"
    
    def _generate_fundamental_analysis(self, data: ComprehensiveData) -> str:
        """ファンダメンタル分析を生成"""
        try:
            analysis = "## 🏛️ ファンダメンタル分析\n\n"
            
            event = data.main_indicator.original_event
            
            # 基本指標分析
            analysis += f"""
### 基本指標分析
- **指標名**: {getattr(event, 'indicator', 'N/A')}
- **国・地域**: {event.country}
- **重要度**: {event.importance}
- **発表頻度**: 月次/四半期/年次（要確認）
"""
            
            # サプライズ分析
            if event.actual is not None and event.forecast is not None:
                surprise_info = event.calculate_surprise()
                if surprise_info:
                    analysis += f"""
### サプライズ分析
- **サプライズ値**: {surprise_info['surprise']:+.2f}
- **サプライズ率**: {surprise_info['surprise_pct']:+.1f}%
- **市場予想との乖離**: {'予想を上回る' if surprise_info['surprise'] > 0 else '予想を下回る'}
"""
            
            # 関連指標分析
            if data.related_indicators:
                analysis += "\n### 関連指標分析\n"
                for related in data.related_indicators[:5]:  # 上位5つ
                    related_event = related.original_event
                    analysis += f"- **{getattr(related_event, 'indicator', 'N/A')}**: {related_event.actual or 'N/A'}\n"
            
            # 経済的背景
            analysis += f"""
### 経済的背景
{self._generate_economic_context(event)}
"""
            
            return analysis
            
        except Exception as e:
            logger.error(f"ファンダメンタル分析生成エラー: {e}")
            return "ファンダメンタル分析の生成中にエラーが発生しました。"
    
    def _generate_market_impact_analysis(self, data: ComprehensiveData) -> str:
        """市場影響分析を生成"""
        try:
            analysis = "## 💹 市場影響分析\n\n"
            
            # 通貨市場影響
            if 'currency' in data.market_data:
                analysis += "### 通貨市場への影響\n"
                for pair, info in data.market_data['currency'].items():
                    analysis += f"- **{pair}**: {info.get('current_rate', 'N/A'):.4f} (24時間変化: {info.get('change_24h', 0):+.2%})\n"
            
            # 株式市場影響
            if 'stock_market' in data.market_data:
                analysis += "\n### 株式市場への影響\n"
                for index, info in data.market_data['stock_market'].items():
                    analysis += f"- **{index}**: {info.get('current_value', 'N/A'):.2f} (1日変化: {info.get('change_1d', 0):+.2%})\n"
            
            # 債券市場影響
            if 'bond_market' in data.market_data:
                analysis += "\n### 債券市場への影響\n"
                for bond, info in data.market_data['bond_market'].items():
                    analysis += f"- **{bond}**: 利回り {info.get('yield', 'N/A'):.2f}% (1日変化: {info.get('change_1d', 0):+.2%})\n"
            
            # 商品市場影響
            if 'commodities' in data.market_data:
                analysis += "\n### 商品市場への影響\n"
                for commodity, info in data.market_data['commodities'].items():
                    analysis += f"- **{commodity}**: {info.get('price', 'N/A'):.2f} (1日変化: {info.get('change_1d', 0):+.2%})\n"
            
            return analysis
            
        except Exception as e:
            logger.error(f"市場影響分析生成エラー: {e}")
            return "市場影響分析の生成中にエラーが発生しました。"
    
    def _generate_forecast_analysis(self, data: ComprehensiveData) -> str:
        """予測分析を生成"""
        try:
            analysis = "## 🔮 予測分析\n\n"
            
            # 予測データ分析
            if data.forecast_data:
                analysis += "### 予測データ分析\n"
                for source, forecast_df in data.forecast_data.items():
                    analysis += f"\n#### {source.upper()} 予測\n"
                    if not forecast_df.empty:
                        latest_forecast = forecast_df.iloc[-1]
                        analysis += f"- **最新予測**: {latest_forecast.get('forecast', 'N/A')}\n"
                        if 'actual' in latest_forecast and pd.notna(latest_forecast['actual']):
                            analysis += f"- **実際値**: {latest_forecast['actual']}\n"
            
            # トレンド予測
            if data.trend_result:
                trend = data.trend_result
                analysis += f"""
### トレンド予測
- **予想トレンド**: {trend.trend_type.value}
- **信頼度**: {trend.confidence_level:.1f}%
- **予想パターン**: {trend.pattern_type.value}
"""
            
            # リスク要因
            analysis += """
### 予測リスク要因
- 地政学的リスク
- 中央銀行政策変更
- 経済ショック
- データ修正の可能性
"""
            
            return analysis
            
        except Exception as e:
            logger.error(f"予測分析生成エラー: {e}")
            return "予測分析の生成中にエラーが発生しました。"
    
    def _generate_risk_assessment(self, data: ComprehensiveData) -> str:
        """リスク評価を生成"""
        try:
            analysis = "## ⚠️ リスク評価\n\n"
            
            # データ品質リスク
            overall_quality = data.data_quality_scores.get('overall', 0)
            quality_risk = "高" if overall_quality < 50 else "中" if overall_quality < 70 else "低"
            analysis += f"""
### データ品質リスク
- **総合品質スコア**: {overall_quality:.1f}/100
- **リスクレベル**: {quality_risk}
"""
            
            # ボラティリティリスク
            if hasattr(data.main_indicator, 'volatility_index') and data.main_indicator.volatility_index:
                vol = data.main_indicator.volatility_index
                vol_risk = "高" if vol > 20 else "中" if vol > 10 else "低"
                analysis += f"""
### ボラティリティリスク
- **ボラティリティ指数**: {vol:.1f}%
- **リスクレベル**: {vol_risk}
"""
            
            # サプライズリスク
            event = data.main_indicator.original_event
            if event.actual is not None and event.forecast is not None:
                surprise_info = event.calculate_surprise()
                if surprise_info:
                    surprise_risk = "高" if abs(surprise_info['surprise_pct']) > 10 else "中" if abs(surprise_info['surprise_pct']) > 5 else "低"
                    analysis += f"""
### サプライズリスク
- **サプライズ率**: {surprise_info['surprise_pct']:+.1f}%
- **リスクレベル**: {surprise_risk}
"""
            
            # 総合リスク評価
            risk_factors = []
            if overall_quality < 70:
                risk_factors.append("データ品質低下")
            if hasattr(data.main_indicator, 'volatility_index') and data.main_indicator.volatility_index and data.main_indicator.volatility_index > 15:
                risk_factors.append("高ボラティリティ")
            if event.actual and event.forecast and abs(event.calculate_surprise()['surprise_pct']) > 8:
                risk_factors.append("大きなサプライズ")
            
            total_risk = "高" if len(risk_factors) >= 2 else "中" if len(risk_factors) == 1 else "低"
            
            analysis += f"""
### 総合リスク評価
- **リスクレベル**: {total_risk}
- **主要リスク要因**: {', '.join(risk_factors) if risk_factors else 'なし'}
"""
            
            return analysis
            
        except Exception as e:
            logger.error(f"リスク評価生成エラー: {e}")
            return "リスク評価の生成中にエラーが発生しました。"
    
    def _generate_investment_implications(self, data: ComprehensiveData) -> str:
        """投資含意を生成"""
        try:
            analysis = "## 💰 投資含意\n\n"
            
            event = data.main_indicator.original_event
            
            # 投資戦略
            analysis += "### 投資戦略への含意\n"
            
            if event.actual is not None and event.forecast is not None:
                surprise_info = event.calculate_surprise()
                if surprise_info:
                    if surprise_info['surprise'] > 0:
                        analysis += "- **ポジティブサプライズ**: リスクオン戦略を検討\n"
                        analysis += "- **通貨**: 該当通貨の買い材料\n"
                        analysis += "- **株式**: 関連セクターの上昇期待\n"
                    else:
                        analysis += "- **ネガティブサプライズ**: リスクオフ戦略を検討\n"
                        analysis += "- **通貨**: 該当通貨の売り材料\n"
                        analysis += "- **株式**: 関連セクターの下落リスク\n"
            
            # セクター別影響
            analysis += "\n### セクター別影響\n"
            indicator_name = getattr(event, 'indicator', 'N/A')
            
            if 'CPI' in indicator_name:
                analysis += "- **消費者関連**: インフレ影響で価格転嫁能力が重要\n"
                analysis += "- **金融**: 金利上昇期待で銀行セクターにプラス\n"
            elif 'GDP' in indicator_name:
                analysis += "- **全セクター**: 経済成長率に応じて全般的な影響\n"
                analysis += "- **サイクリカル**: 成長率向上で特に恩恵\n"
            elif 'Unemployment' in indicator_name:
                analysis += "- **消費者関連**: 雇用改善で消費拡大期待\n"
                analysis += "- **住宅**: 雇用安定で住宅需要増加\n"
            
            # リスク管理
            analysis += "\n### リスク管理\n"
            analysis += "- **ポジションサイズ**: サプライズの大きさに応じて調整\n"
            analysis += "- **ストップロス**: 予想外の動きに対する防御\n"
            analysis += "- **分散投資**: 単一指標への過度な依存を回避\n"
            
            return analysis
            
        except Exception as e:
            logger.error(f"投資含意生成エラー: {e}")
            return "投資含意の生成中にエラーが発生しました。"
    
    def _generate_appendix(self, data: ComprehensiveData) -> str:
        """付録を生成"""
        try:
            appendix = "## 📋 付録\n\n"
            
            # データソース
            appendix += "### データソース\n"
            for source in data.data_sources:
                appendix += f"- {source}\n"
            
            # データ品質詳細
            appendix += "\n### データ品質詳細\n"
            for source, score in data.data_quality_scores.items():
                appendix += f"- **{source}**: {score:.1f}/100\n"
            
            # 収集時刻
            appendix += f"\n### データ収集情報\n"
            appendix += f"- **収集時刻**: {data.collection_time.strftime('%Y年%m月%d日 %H:%M:%S')}\n"
            appendix += f"- **履歴データ数**: {len(data.historical_data)}\n"
            appendix += f"- **予測データ数**: {len(data.forecast_data)}\n"
            appendix += f"- **関連指標数**: {len(data.related_indicators)}\n"
            appendix += f"- **ニュース記事数**: {len(data.news_data)}\n"
            
            # 免責事項
            appendix += """
### 免責事項
- 本レポートは情報提供目的であり、投資助言ではありません
- 投資判断は自己責任で行ってください
- データの正確性については最大限注意を払っていますが、完全性を保証するものではありません
- 市場の状況により、分析結果が実際の動向と異なる場合があります
"""
            
            return appendix
            
        except Exception as e:
            logger.error(f"付録生成エラー: {e}")
            return "付録の生成中にエラーが発生しました。"
    
    def _generate_economic_context(self, event) -> str:
        """経済的背景を生成"""
        indicator_name = getattr(event, 'indicator', 'N/A')
        
        context_map = {
            'CPI': "消費者物価指数は経済のインフレ動向を示す重要な指標です。中央銀行の金融政策決定に大きな影響を与えます。",
            'GDP': "国内総生産は経済全体の成長率を示す最も重要な指標の一つです。経済の健全性を測る基本指標として機能します。",
            'Unemployment Rate': "失業率は労働市場の状況を示し、消費動向や経済政策に大きな影響を与えます。",
            'Interest Rate': "政策金利は中央銀行の金融政策の方向性を示し、通貨価値や投資判断に直接的な影響を与えます。",
            'PMI': "購買担当者指数は製造業の景気動向を示し、経済の先行指標として機能します。"
        }
        
        return context_map.get(indicator_name, "この指標は経済の重要な側面を示しており、市場動向に大きな影響を与える可能性があります。")
    
    def _extract_key_insights(self, data: ComprehensiveData) -> List[str]:
        """主要インサイトを抽出"""
        insights = []
        
        try:
            event = data.main_indicator.original_event
            
            # サプライズインサイト
            if event.actual is not None and event.forecast is not None:
                surprise_info = event.calculate_surprise()
                if surprise_info and abs(surprise_info['surprise_pct']) > 5:
                    insights.append(f"市場予想を{abs(surprise_info['surprise_pct']):.1f}%上回る/下回る大きなサプライズ")
            
            # トレンドインサイト
            if data.trend_result:
                trend = data.trend_result
                if trend.confidence_level > 70:
                    insights.append(f"強い{trend.trend_type.value}トレンドが確認されている（信頼度: {trend.confidence_level:.1f}%）")
            
            # データ品質インサイト
            overall_quality = data.data_quality_scores.get('overall', 0)
            if overall_quality >= 80:
                insights.append("高品質なデータに基づく信頼性の高い分析")
            elif overall_quality < 50:
                insights.append("データ品質に注意が必要")
            
            # ボラティリティインサイト
            if hasattr(data.main_indicator, 'volatility_index') and data.main_indicator.volatility_index:
                vol = data.main_indicator.volatility_index
                if vol > 20:
                    insights.append(f"高ボラティリティ環境（{vol:.1f}%）でリスク管理が重要")
            
        except Exception as e:
            logger.error(f"インサイト抽出エラー: {e}")
        
        return insights
    
    def _generate_report_metadata(self, data: ComprehensiveData) -> Dict[str, Any]:
        """レポートメタデータを生成"""
        try:
            event = data.main_indicator.original_event
            
            return {
                'title': f"{event.country} - {getattr(event, 'indicator', 'N/A')} 詳細分析レポート",
                'generation_time': datetime.now().isoformat(),
                'author': 'Economic Indicators Analysis System',
                'version': '1.0',
                'language': self.config.language,
                'format': self.config.format,
                'main_indicator': {
                    'country': event.country,
                    'indicator': getattr(event, 'indicator', 'N/A'),
                    'importance': event.importance,
                    'datetime': event.datetime.isoformat() if event.datetime else None
                },
                'data_quality': data.data_quality_scores,
                'data_sources': data.data_sources
            }
            
        except Exception as e:
            logger.error(f"レポートメタデータ生成エラー: {e}")
            return {}
    
    def _build_html_report(self, sections: Dict[str, str], metadata: Dict[str, Any], enhanced_visualization: Optional[Dict[str, Any]]) -> str:
        """HTMLレポートを構築"""
        try:
            # チャートHTML
            chart_html = ""
            if enhanced_visualization and 'html' in enhanced_visualization:
                chart_html = enhanced_visualization['html']
            
            html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{metadata.get('title', '経済指標詳細分析レポート')}</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .content {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .chart-section {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        h1, h2, h3 {{
            color: #333;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .highlight {{
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            border-left: 4px solid #ffc107;
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
        <h1>{metadata.get('title', '経済指標詳細分析レポート')}</h1>
        <p>生成日時: {metadata.get('generation_time', 'N/A')}</p>
        <p>作成者: {metadata.get('author', 'N/A')}</p>
    </div>
    
    <div class="content">
        {sections.get('executive_summary', '')}
    </div>
    
    <div class="content">
        {sections.get('technical_analysis', '')}
    </div>
    
    <div class="content">
        {sections.get('fundamental_analysis', '')}
    </div>
    
    <div class="content">
        {sections.get('market_impact', '')}
    </div>
    
    <div class="content">
        {sections.get('forecast_analysis', '')}
    </div>
    
    <div class="content">
        {sections.get('risk_assessment', '')}
    </div>
    
    <div class="content">
        {sections.get('investment_implications', '')}
    </div>
    
    {f'<div class="chart-section">{chart_html}</div>' if chart_html else ''}
    
    <div class="content">
        {sections.get('appendix', '')}
    </div>
</body>
</html>
"""
            
            return html_content
            
        except Exception as e:
            logger.error(f"HTMLレポート構築エラー: {e}")
            return "<html><body><h1>レポート生成エラー</h1></body></html>"
    
    def _build_markdown_report(self, sections: Dict[str, str], metadata: Dict[str, Any]) -> str:
        """Markdownレポートを構築"""
        try:
            markdown_content = f"""# {metadata.get('title', '経済指標詳細分析レポート')}

**生成日時**: {metadata.get('generation_time', 'N/A')}  
**作成者**: {metadata.get('author', 'N/A')}

---

"""
            
            # セクションを結合
            for section_name, section_content in sections.items():
                markdown_content += section_content + "\n\n---\n\n"
            
            return markdown_content
            
        except Exception as e:
            logger.error(f"Markdownレポート構築エラー: {e}")
            return "# レポート生成エラー"
    
    def _save_report(self, content: str, metadata: Dict[str, Any]) -> List[str]:
        """レポートを保存"""
        saved_files = []
        
        try:
            if not self.config.output_path:
                return saved_files
            
            self.config.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイル名生成
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = f"detailed_report_{timestamp}"
            
            # HTML保存
            if self.config.format == "html":
                html_path = self.config.output_path / f"{base_name}.html"
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved_files.append(str(html_path))
            
            # Markdown保存
            elif self.config.format == "markdown":
                md_path = self.config.output_path / f"{base_name}.md"
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved_files.append(str(md_path))
            
            # メタデータ保存
            metadata_path = self.config.output_path / f"{base_name}_metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            saved_files.append(str(metadata_path))
            
            logger.info(f"詳細レポートが保存されました: {saved_files}")
            
        except Exception as e:
            logger.error(f"詳細レポート保存エラー: {e}")
        
        return saved_files
