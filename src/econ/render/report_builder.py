"""
Report building module for economic analysis.

経済指標の詳細分析レポートを生成するモジュール。
Markdown、HTML、PDFフォーマットでの出力をサポート。
"""

from typing import List, Dict, Optional, Union, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import logging
from pathlib import Path
import base64
import io
from jinja2 import Template, Environment, FileSystemLoader

# TYPE_CHECKINGで循環importを回避
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..normalize.data_processor import ProcessedIndicator
    from ..normalize.trend_analyzer import TrendResult
    from ..adapters.investpy_calendar import EconomicEvent

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """レポートフォーマット"""
    MARKDOWN = "markdown"
    HTML = "html" 
    PDF = "pdf"
    JSON = "json"


class ReportSection(Enum):
    """レポートセクション"""
    EXECUTIVE_SUMMARY = "executive_summary"
    DATA_OVERVIEW = "data_overview"
    TREND_ANALYSIS = "trend_analysis" 
    TECHNICAL_ANALYSIS = "technical_analysis"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    FORECAST = "forecast"
    APPENDIX = "appendix"


@dataclass
class ReportConfig:
    """レポート設定"""
    format: ReportFormat = ReportFormat.HTML
    sections: List[ReportSection] = field(default_factory=lambda: [
        ReportSection.EXECUTIVE_SUMMARY,
        ReportSection.DATA_OVERVIEW,
        ReportSection.TREND_ANALYSIS
    ])
    
    # 言語・スタイル
    language: str = "ja"
    include_charts: bool = True
    include_raw_data: bool = False
    
    # フィルタリング
    min_data_quality_score: float = 30.0
    include_low_confidence: bool = False
    
    # 出力設定
    output_path: Optional[Path] = None
    template_path: Optional[Path] = None
    
    # メタデータ
    report_title: Optional[str] = None
    author: str = "Economic Indicators System"
    include_disclaimers: bool = True


class ReportBuilder:
    """レポート構築エンジン"""
    
    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()
        
        # テンプレート環境の設定
        if self.config.template_path and self.config.template_path.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(self.config.template_path))
            )
        else:
            self.jinja_env = Environment(loader=FileSystemLoader([]))
            
        # 内部テンプレートを設定
        self._setup_default_templates()
    
    def _setup_default_templates(self):
        """デフォルトテンプレートを設定"""
        self.templates = {
            ReportFormat.MARKDOWN: self._get_markdown_template(),
            ReportFormat.HTML: self._get_html_template(),
        }
    
    def generate_comprehensive_report(
        self,
        indicators: List['ProcessedIndicator'],
        trend_results: Optional[List['TrendResult']] = None,
        charts: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """包括的な経済指標レポートを生成"""
        
        # データの品質フィルタリング
        filtered_indicators = self._filter_indicators(indicators)
        
        if not filtered_indicators:
            return {'error': 'フィルタリング後に有効な指標がありません'}
        
        try:
            # レポートデータを準備
            report_data = self._prepare_report_data(
                filtered_indicators, trend_results, charts
            )
            
            # セクション別にコンテンツを生成
            sections_content = {}
            for section in self.config.sections:
                sections_content[section.value] = self._generate_section_content(
                    section, report_data
                )
            
            # 最終レポートを構築
            final_report = self._build_final_report(sections_content, report_data)
            
            # ファイル保存
            if self.config.output_path:
                self._save_report(final_report, self.config.output_path)
            
            return {
                'content': final_report,
                'format': self.config.format.value,
                'sections': list(sections_content.keys()),
                'indicators_count': len(filtered_indicators),
                'generation_time': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate comprehensive report: {e}")
            return {'error': str(e)}
    
    def _filter_indicators(self, indicators: List['ProcessedIndicator']) -> List['ProcessedIndicator']:
        """指標をフィルタリング"""
        filtered = []
        
        for indicator in indicators:
            # データ品質スコアチェック
            if indicator.data_quality_score < self.config.min_data_quality_score:
                continue
            
            # 低信頼度の除外
            if not self.config.include_low_confidence:
                if (indicator.trend_direction and 
                    hasattr(indicator, 'trend_strength') and 
                    indicator.trend_strength and 
                    indicator.trend_strength < 30):
                    continue
            
            filtered.append(indicator)
        
        return filtered
    
    def _prepare_report_data(
        self,
        indicators: List['ProcessedIndicator'],
        trend_results: Optional[List['TrendResult']],
        charts: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """レポートデータを準備"""
        
        # 基本統計
        total_indicators = len(indicators)
        countries = list(set(ind.original_event.country for ind in indicators))
        avg_quality_score = sum(ind.data_quality_score for ind in indicators) / total_indicators
        
        # トレンド分析サマリー
        trend_summary = self._analyze_trend_summary(indicators, trend_results)
        
        # 注目指標の抽出
        highlights = self._extract_highlights(indicators)
        
        # リスク評価
        risks = self._assess_risks(indicators, trend_results)
        
        return {
            'metadata': {
                'report_title': self.config.report_title or "経済指標分析レポート",
                'generation_date': datetime.now(),
                'author': self.config.author,
                'total_indicators': total_indicators,
                'countries': countries,
                'avg_quality_score': round(avg_quality_score, 1)
            },
            'indicators': indicators,
            'trend_results': trend_results or [],
            'charts': charts or [],
            'trend_summary': trend_summary,
            'highlights': highlights,
            'risks': risks
        }
    
    def _analyze_trend_summary(
        self,
        indicators: List['ProcessedIndicator'],
        trend_results: Optional[List['TrendResult']]
    ) -> Dict[str, Any]:
        """トレンドサマリーを分析"""
        
        summary = {
            'trend_distribution': {},
            'avg_volatility': 0.0,
            'momentum_indicators': [],
            'pattern_detections': []
        }
        
        # トレンド分布
        trends = []
        volatilities = []
        
        for indicator in indicators:
            if indicator.trend_direction:
                trend_value = indicator.trend_direction.value
                trends.append(trend_value)
                summary['trend_distribution'][trend_value] = (
                    summary['trend_distribution'].get(trend_value, 0) + 1
                )
            
            # ボラティリティ
            if hasattr(indicator, 'volatility_index') and indicator.volatility_index:
                volatilities.append(indicator.volatility_index)
        
        if volatilities:
            summary['avg_volatility'] = sum(volatilities) / len(volatilities)
        
        # パターン検出（trend_resultsから）
        if trend_results:
            for result in trend_results:
                if result.pattern_type.value != "パターンなし":
                    summary['pattern_detections'].append({
                        'pattern': result.pattern_type.value,
                        'confidence': result.pattern_confidence
                    })
        
        return summary
    
    def _extract_highlights(self, indicators: List['ProcessedIndicator']) -> List[Dict[str, Any]]:
        """注目指標を抽出"""
        highlights = []
        
        for indicator in indicators:
            event = indicator.original_event
            
            # 大きなサプライズ
            if event.actual is not None and event.forecast is not None:
                surprise_info = event.calculate_surprise()
                if surprise_info and abs(surprise_info['surprise_pct']) > 10:  # 10%以上のサプライズ
                    highlights.append({
                        'type': 'big_surprise',
                        'indicator': f"{event.country} {getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')}",
                        'surprise_pct': surprise_info['surprise_pct'],
                        'description': f"{abs(surprise_info['surprise_pct']):.1f}%の大きなサプライズ"
                    })
            
            # 極端なZ-score
            if indicator.z_score and abs(indicator.z_score) > 2:
                highlights.append({
                    'type': 'extreme_value',
                    'indicator': f"{event.country} {getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')}",
                    'z_score': indicator.z_score,
                    'description': f"統計的に{'異常高値' if indicator.z_score > 0 else '異常低値'}"
                })
            
            # 大きな変化率
            if indicator.yoy_change and abs(indicator.yoy_change) > 5:  # 5%以上の変化
                highlights.append({
                    'type': 'big_change',
                    'indicator': f"{event.country} {getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')}",
                    'yoy_change': indicator.yoy_change,
                    'description': f"前年比{indicator.yoy_change:+.1f}%の大きな変化"
                })
        
        # 重要度順にソート
        highlights.sort(key=lambda x: abs(x.get('surprise_pct', 0)) + abs(x.get('z_score', 0)) + abs(x.get('yoy_change', 0)), reverse=True)
        
        return highlights[:5]  # 上位5つ
    
    def _assess_risks(
        self,
        indicators: List['ProcessedIndicator'],
        trend_results: Optional[List['TrendResult']]
    ) -> List[Dict[str, Any]]:
        """リスク評価"""
        risks = []
        
        # 高ボラティリティリスク
        high_vol_indicators = [
            ind for ind in indicators 
            if hasattr(ind, 'volatility_index') and ind.volatility_index and ind.volatility_index > 20
        ]
        
        if high_vol_indicators:
            risks.append({
                'type': 'high_volatility',
                'severity': 'medium',
                'description': f"{len(high_vol_indicators)}つの指標で高ボラティリティを検出",
                'indicators': [f"{ind.original_event.country} {getattr(ind.original_event, 'indicator', None) or getattr(ind.original_event, 'title', 'N/A')}" 
                              for ind in high_vol_indicators[:3]]
            })
        
        # トレンド反転リスク
        if trend_results:
            reversal_risks = [
                tr for tr in trend_results 
                if tr.trend_type.value == "反転"
            ]
            
            if reversal_risks:
                risks.append({
                    'type': 'trend_reversal',
                    'severity': 'high',
                    'description': f"{len(reversal_risks)}つの指標でトレンド反転の可能性",
                    'confidence': sum(tr.confidence_level for tr in reversal_risks) / len(reversal_risks)
                })
        
        # データ品質リスク
        low_quality = [ind for ind in indicators if ind.data_quality_score < 50]
        if len(low_quality) > len(indicators) * 0.3:  # 30%以上が低品質
            risks.append({
                'type': 'data_quality',
                'severity': 'medium',
                'description': f"分析対象の{len(low_quality)}/{len(indicators)}指標でデータ品質が低下",
                'avg_score': sum(ind.data_quality_score for ind in low_quality) / len(low_quality)
            })
        
        return risks
    
    def _generate_section_content(self, section: ReportSection, report_data: Dict[str, Any]) -> str:
        """セクション別のコンテンツを生成"""
        
        if section == ReportSection.EXECUTIVE_SUMMARY:
            return self._generate_executive_summary(report_data)
        elif section == ReportSection.DATA_OVERVIEW:
            return self._generate_data_overview(report_data)
        elif section == ReportSection.TREND_ANALYSIS:
            return self._generate_trend_analysis(report_data)
        elif section == ReportSection.TECHNICAL_ANALYSIS:
            return self._generate_technical_analysis(report_data)
        elif section == ReportSection.RISK_ASSESSMENT:
            return self._generate_risk_assessment(report_data)
        else:
            return f"# {section.value}\n\n（実装予定）\n\n"
    
    def _generate_executive_summary(self, report_data: Dict[str, Any]) -> str:
        """エグゼクティブサマリーを生成"""
        metadata = report_data['metadata']
        highlights = report_data['highlights']
        trend_summary = report_data['trend_summary']
        
        content = f"""# エグゼクティブサマリー

## 分析概要
- **分析日時**: {metadata['generation_date'].strftime('%Y年%m月%d日 %H:%M')}
- **対象指標数**: {metadata['total_indicators']}指標
- **対象国・地域**: {', '.join(metadata['countries'])}
- **平均データ品質スコア**: {metadata['avg_quality_score']}/100

## 主要な発見

### 注目すべき指標
"""
        
        if highlights:
            for i, highlight in enumerate(highlights, 1):
                content += f"{i}. **{highlight['indicator']}**: {highlight['description']}\n"
        else:
            content += "特に注目すべき動きは検出されませんでした。\n"
        
        content += f"""
### トレンド概況
"""
        
        trend_dist = trend_summary['trend_distribution']
        if trend_dist:
            content += "市場トレンド分布:\n"
            for trend, count in trend_dist.items():
                content += f"- {trend}: {count}指標\n"
        
        content += f"- 平均ボラティリティ: {trend_summary['avg_volatility']:.1f}%\n"
        
        if trend_summary['pattern_detections']:
            content += f"- 検出パターン: {len(trend_summary['pattern_detections'])}件\n"
        
        content += "\n"
        
        return content
    
    def _generate_data_overview(self, report_data: Dict[str, Any]) -> str:
        """データ概要を生成"""
        indicators = report_data['indicators']
        
        content = """# データ概要

## 指標別詳細

| 国 | 指標名 | 最新値 | 前回値 | 予想値 | サプライズ | データ品質 |
|---|------|------|------|------|----------|----------|
"""
        
        for indicator in indicators:
            event = indicator.original_event
            
            # サプライズ計算
            surprise_str = "N/A"
            if event.actual is not None and event.forecast is not None:
                surprise_info = event.calculate_surprise()
                if surprise_info:
                    surprise_str = f"{surprise_info['surprise']:+.2f}"
            
            indicator_name = getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')
            content += f"| {event.country} | {indicator_name} | "
            content += f"{event.actual or 'N/A'} | {event.previous or 'N/A'} | "
            content += f"{event.forecast or 'N/A'} | {surprise_str} | "
            content += f"{indicator.data_quality_score:.0f}/100 |\n"
        
        content += "\n"
        return content
    
    def _generate_trend_analysis(self, report_data: Dict[str, Any]) -> str:
        """トレンド分析を生成"""
        indicators = report_data['indicators']
        trend_results = report_data['trend_results']
        
        content = """# トレンド分析

## 指標別トレンド詳細

"""
        
        for indicator in indicators:
            event = indicator.original_event
            indicator_name = getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')
            content += f"### {event.country} - {indicator_name}\n\n"
            
            if indicator.trend_direction:
                content += f"- **トレンド方向**: {indicator.trend_direction.value}\n"
            
            if hasattr(indicator, 'trend_strength') and indicator.trend_strength:
                content += f"- **トレンド強度**: {indicator.trend_strength:.1f}/100\n"
            
            if indicator.mom_change:
                content += f"- **月次変化**: {indicator.mom_change:+.2f}%\n"
            
            if indicator.yoy_change:
                content += f"- **年次変化**: {indicator.yoy_change:+.2f}%\n"
            
            if hasattr(indicator, 'volatility_index') and indicator.volatility_index:
                content += f"- **ボラティリティ**: {indicator.volatility_index:.1f}%\n"
            
            content += "\n"
        
        return content
    
    def _generate_technical_analysis(self, report_data: Dict[str, Any]) -> str:
        """テクニカル分析を生成"""
        trend_results = report_data['trend_results']
        
        content = """# テクニカル分析

"""
        
        if not trend_results:
            content += "テクニカル分析結果は利用できません。\n"
            return content
        
        for result in trend_results:
            content += f"## 分析結果\n\n"
            content += f"- **トレンドタイプ**: {result.trend_type.value}\n"
            content += f"- **信頼度**: {result.confidence_level:.1f}%\n"
            content += f"- **パターン**: {result.pattern_type.value}\n"
            
            if result.support_levels:
                content += f"- **サポートレベル**: {', '.join(f'{level:.2f}' for level in result.support_levels[:3])}\n"
            
            if result.resistance_levels:
                content += f"- **レジスタンスレベル**: {', '.join(f'{level:.2f}' for level in result.resistance_levels[:3])}\n"
            
            content += "\n"
        
        return content
    
    def _generate_risk_assessment(self, report_data: Dict[str, Any]) -> str:
        """リスク評価を生成"""
        risks = report_data['risks']
        
        content = """# リスク評価

"""
        
        if not risks:
            content += "特別なリスクは検出されませんでした。\n"
            return content
        
        for risk in risks:
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk['severity'], "⚪")
            content += f"## {severity_icon} {risk['type'].title()}\n\n"
            content += f"**重要度**: {risk['severity']}\n\n"
            content += f"**説明**: {risk['description']}\n\n"
            
            if 'indicators' in risk:
                content += "**影響指標**:\n"
                for indicator in risk['indicators']:
                    content += f"- {indicator}\n"
                content += "\n"
        
        return content
    
    def _build_final_report(self, sections_content: Dict[str, str], report_data: Dict[str, Any]) -> str:
        """最終レポートを構築"""
        metadata = report_data['metadata']
        
        if self.config.format == ReportFormat.MARKDOWN:
            return self._build_markdown_report(sections_content, metadata)
        elif self.config.format == ReportFormat.HTML:
            return self._build_html_report(sections_content, metadata)
        else:
            # フォールバック
            return self._build_markdown_report(sections_content, metadata)
    
    def _build_markdown_report(self, sections_content: Dict[str, str], metadata: Dict[str, Any]) -> str:
        """Markdownレポートを構築"""
        content = f"""# {metadata['report_title']}

**生成日時**: {metadata['generation_date'].strftime('%Y年%m月%d日 %H:%M')}  
**作成者**: {metadata['author']}

---

"""
        
        # セクションを結合
        for section_name, section_content in sections_content.items():
            content += section_content + "\n---\n\n"
        
        # 免責事項
        if self.config.include_disclaimers:
            content += self._get_disclaimers()
        
        return content
    
    def _build_html_report(self, sections_content: Dict[str, str], metadata: Dict[str, Any]) -> str:
        """HTMLレポートを構築"""
        template_str = self.templates[ReportFormat.HTML]
        template = Template(template_str)
        
        return template.render(
            title=metadata['report_title'],
            generation_date=metadata['generation_date'].strftime('%Y年%m月%d日 %H:%M'),
            author=metadata['author'],
            sections=sections_content,
            disclaimers=self._get_disclaimers() if self.config.include_disclaimers else ""
        )
    
    def _get_disclaimers(self) -> str:
        """免責事項を取得"""
        return """
## 免責事項

- 本レポートは自動生成されており、投資判断の参考情報として提供されています。
- 最終的な投資判断は、投資家ご自身の責任で行ってください。
- データの正確性については最大限注意を払っていますが、完全性を保証するものではありません。
- 市場の状況により、分析結果が実際の動向と異なる場合があります。
"""
    
    def _get_markdown_template(self) -> str:
        """Markdownテンプレートを取得"""
        return """{{ content }}"""
    
    def _get_html_template(self) -> str:
        """HTMLテンプレートを取得"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body { font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; margin: 40px; }
        .header { border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }
        .section { margin-bottom: 40px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .highlight { background-color: #ffffcc; }
        .risk-high { color: #d32f2f; }
        .risk-medium { color: #f57c00; }
        .risk-low { color: #388e3c; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p><strong>生成日時:</strong> {{ generation_date }}</p>
        <p><strong>作成者:</strong> {{ author }}</p>
    </div>
    
    {% for section_name, section_content in sections.items() %}
    <div class="section">
        {{ section_content | safe }}
    </div>
    {% endfor %}
    
    {% if disclaimers %}
    <div class="section">
        {{ disclaimers | safe }}
    </div>
    {% endif %}
</body>
</html>
"""
    
    def _save_report(self, content: str, output_path: Path):
        """レポートを保存"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.config.format == ReportFormat.HTML:
            with open(output_path.with_suffix('.html'), 'w', encoding='utf-8') as f:
                f.write(content)
        elif self.config.format == ReportFormat.MARKDOWN:
            with open(output_path.with_suffix('.md'), 'w', encoding='utf-8') as f:
                f.write(content)
        
        logger.info(f"Report saved to {output_path}")
    
    def generate_single_indicator_report(
        self,
        indicator: 'ProcessedIndicator',
        trend_result: Optional['TrendResult'] = None,
        chart: Optional[Dict[str, Any]] = None
    ) -> str:
        """単一指標の詳細レポートを生成"""
        
        event = indicator.original_event
        
        indicator_name = getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')
        content = f"""# {event.country} - {indicator_name} 詳細分析

## 基本情報
- **国・地域**: {event.country}
- **指標名**: {indicator_name}
- **発表日時**: {event.datetime.strftime('%Y年%m月%d日 %H:%M') if event.datetime else 'N/A'}
- **重要度**: {event.importance or 'N/A'}

## データ詳細
- **最新値**: {event.actual or 'N/A'}
- **予想値**: {event.forecast or 'N/A'}
- **前回値**: {event.previous or 'N/A'}
"""
        
        # サプライズ分析
        if event.actual is not None and event.forecast is not None:
            surprise_info = event.calculate_surprise()
            if surprise_info:
                surprise_impact = "ポジティブサプライズ" if surprise_info['surprise'] > 0 else "ネガティブサプライズ"
                content += f"""
## サプライズ分析
- **サプライズ**: {surprise_info['surprise']:+.2f}
- **サプライズ率**: {surprise_info['surprise_pct']:+.2f}%
- **評価**: {surprise_impact}
"""
        
        # トレンド分析
        if indicator.trend_direction:
            content += f"""
## トレンド分析
- **トレンド方向**: {indicator.trend_direction.value}
"""
            if hasattr(indicator, 'trend_strength') and indicator.trend_strength:
                content += f"- **トレンド強度**: {indicator.trend_strength:.1f}/100\n"
        
        # 変化率分析
        if indicator.mom_change or indicator.yoy_change:
            content += "\n## 変化率分析\n"
            if indicator.mom_change:
                content += f"- **月次変化率**: {indicator.mom_change:+.2f}%\n"
            if indicator.yoy_change:
                content += f"- **年次変化率**: {indicator.yoy_change:+.2f}%\n"
        
        # 統計分析
        if indicator.z_score is not None:
            content += f"""
## 統計分析
- **Z-Score**: {indicator.z_score:.2f}
- **相対位置**: {self._interpret_z_score(indicator.z_score)}
"""
        
        # データ品質
        content += f"""
## データ品質評価
- **品質スコア**: {indicator.data_quality_score:.0f}/100
- **評価**: {self._interpret_quality_score(indicator.data_quality_score)}
"""
        
        return content
    
    def _interpret_z_score(self, z_score: float) -> str:
        """Z-scoreの解釈"""
        if z_score > 2:
            return "統計的に非常に高い"
        elif z_score > 1:
            return "統計的に高い"
        elif z_score > -1:
            return "平均的"
        elif z_score > -2:
            return "統計的に低い"
        else:
            return "統計的に非常に低い"
    
    def _interpret_quality_score(self, score: float) -> str:
        """品質スコアの解釈"""
        if score >= 80:
            return "優秀"
        elif score >= 60:
            return "良好"
        elif score >= 40:
            return "普通"
        else:
            return "要注意"