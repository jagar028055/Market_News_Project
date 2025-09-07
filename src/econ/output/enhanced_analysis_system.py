"""
Enhanced Analysis System for Economic Indicators
経済指標強化分析システム

視認性を改善し、各指標の深度のある分析を提供する統合システム
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from pathlib import Path
import asyncio

# 既存モジュール
from ..config.settings import EconConfig
from ..normalize.data_processor import ProcessedIndicator
from ..normalize.trend_analyzer import TrendResult
from .enhanced_visualization import EnhancedVisualizationEngine, EnhancedVisualizationConfig
from .comprehensive_data_collector import ComprehensiveDataCollector, DataCollectionConfig, ComprehensiveData
from .detailed_report_generator import DetailedReportGenerator, ReportConfig

logger = logging.getLogger(__name__)


class EnhancedAnalysisSystem:
    """強化分析システム"""
    
    def __init__(self, econ_config: Optional[EconConfig] = None):
        self.econ_config = econ_config or EconConfig()
        
        # コンポーネント初期化
        self.visualization_engine = EnhancedVisualizationEngine()
        self.data_collector = ComprehensiveDataCollector(econ_config=self.econ_config)
        self.report_generator = DetailedReportGenerator()
        
        # 出力ディレクトリ設定
        self.output_dir = Path(self.econ_config.output.output_base_dir) / "enhanced_analysis"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def analyze_indicator_comprehensively(
        self,
        indicator: ProcessedIndicator,
        trend_result: Optional[TrendResult] = None,
        include_visualization: bool = True,
        include_data_collection: bool = True,
        include_detailed_report: bool = True
    ) -> Dict[str, Any]:
        """指標の包括的分析を実行"""
        
        try:
            logger.info(f"包括的分析開始: {indicator.original_event.country} - {getattr(indicator.original_event, 'indicator', 'N/A')}")
            
            results = {
                'indicator': indicator,
                'trend_result': trend_result,
                'analysis_time': datetime.now(),
                'components': {}
            }
            
            # 1. 網羅的データ収集
            comprehensive_data = None
            if include_data_collection:
                logger.info("網羅的データ収集中...")
                comprehensive_data = await self.data_collector.collect_comprehensive_data(indicator, trend_result)
                results['components']['comprehensive_data'] = comprehensive_data
            
            # 2. 強化可視化生成
            enhanced_visualization = None
            if include_visualization:
                logger.info("強化可視化生成中...")
                viz_config = EnhancedVisualizationConfig(
                    save_path=self.output_dir / f"visualization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                self.visualization_engine.config = viz_config
                
                enhanced_visualization = self.visualization_engine.create_single_indicator_deep_analysis(
                    indicator, trend_result, comprehensive_data.__dict__ if comprehensive_data else None
                )
                results['components']['enhanced_visualization'] = enhanced_visualization
            
            # 3. 詳細レポート生成
            detailed_report = None
            if include_detailed_report and comprehensive_data:
                logger.info("詳細レポート生成中...")
                report_config = ReportConfig(
                    output_path=self.output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                self.report_generator.config = report_config
                
                detailed_report = self.report_generator.generate_detailed_report(
                    comprehensive_data, enhanced_visualization
                )
                results['components']['detailed_report'] = detailed_report
            
            # 4. 統合サマリー生成
            results['summary'] = self._generate_analysis_summary(
                indicator, trend_result, comprehensive_data, enhanced_visualization, detailed_report
            )
            
            logger.info("包括的分析完了")
            return results
            
        except Exception as e:
            logger.error(f"包括的分析エラー: {e}")
            return {'error': str(e)}
    
    def _generate_analysis_summary(
        self,
        indicator: ProcessedIndicator,
        trend_result: Optional[TrendResult],
        comprehensive_data: Optional[ComprehensiveData],
        enhanced_visualization: Optional[Dict[str, Any]],
        detailed_report: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析サマリーを生成"""
        
        try:
            event = indicator.original_event
            
            summary = {
                'indicator_info': {
                    'country': event.country,
                    'indicator': getattr(event, 'indicator', 'N/A'),
                    'importance': event.importance,
                    'actual': event.actual,
                    'forecast': event.forecast,
                    'previous': event.previous
                },
                'analysis_components': {
                    'comprehensive_data': comprehensive_data is not None,
                    'enhanced_visualization': enhanced_visualization is not None,
                    'detailed_report': detailed_report is not None
                },
                'data_quality': {},
                'key_findings': [],
                'files_generated': []
            }
            
            # データ品質情報
            if comprehensive_data:
                summary['data_quality'] = comprehensive_data.data_quality_scores
            
            # 主要発見
            if event.actual is not None and event.forecast is not None:
                surprise_info = event.calculate_surprise()
                if surprise_info:
                    summary['key_findings'].append(f"サプライズ: {surprise_info['surprise_pct']:+.1f}%")
            
            if trend_result:
                summary['key_findings'].append(f"トレンド: {trend_result.trend_type.value} (信頼度: {trend_result.confidence_level:.1f}%)")
            
            # 生成ファイル
            if enhanced_visualization and 'saved_files' in enhanced_visualization:
                summary['files_generated'].extend(enhanced_visualization['saved_files'])
            
            if detailed_report and 'saved_files' in detailed_report:
                summary['files_generated'].extend(detailed_report['saved_files'])
            
            return summary
            
        except Exception as e:
            logger.error(f"分析サマリー生成エラー: {e}")
            return {}
    
    async def analyze_multiple_indicators(
        self,
        indicators: List[ProcessedIndicator],
        trend_results: Optional[List[TrendResult]] = None
    ) -> Dict[str, Any]:
        """複数指標の分析を実行"""
        
        try:
            logger.info(f"複数指標分析開始: {len(indicators)}指標")
            
            results = {
                'indicators_count': len(indicators),
                'analysis_time': datetime.now(),
                'individual_analyses': [],
                'comparative_analysis': None
            }
            
            # 各指標の個別分析
            for i, indicator in enumerate(indicators):
                trend_result = trend_results[i] if trend_results and i < len(trend_results) else None
                
                individual_result = await self.analyze_indicator_comprehensively(
                    indicator, trend_result, 
                    include_visualization=True,
                    include_data_collection=True,
                    include_detailed_report=True
                )
                
                results['individual_analyses'].append(individual_result)
            
            # 比較分析
            results['comparative_analysis'] = self._generate_comparative_analysis(indicators, trend_results)
            
            logger.info("複数指標分析完了")
            return results
            
        except Exception as e:
            logger.error(f"複数指標分析エラー: {e}")
            return {'error': str(e)}
    
    def _generate_comparative_analysis(self, indicators: List[ProcessedIndicator], trend_results: Optional[List[TrendResult]]) -> Dict[str, Any]:
        """比較分析を生成"""
        
        try:
            comparative = {
                'countries': list(set(ind.original_event.country for ind in indicators)),
                'indicators': list(set(getattr(ind.original_event, 'indicator', 'N/A') for ind in indicators)),
                'surprise_analysis': {},
                'trend_analysis': {},
                'quality_analysis': {}
            }
            
            # サプライズ分析
            surprises = []
            for indicator in indicators:
                event = indicator.original_event
                if event.actual is not None and event.forecast is not None:
                    surprise_info = event.calculate_surprise()
                    if surprise_info:
                        surprises.append({
                            'country': event.country,
                            'indicator': getattr(event, 'indicator', 'N/A'),
                            'surprise_pct': surprise_info['surprise_pct']
                        })
            
            if surprises:
                comparative['surprise_analysis'] = {
                    'total_surprises': len(surprises),
                    'positive_surprises': len([s for s in surprises if s['surprise_pct'] > 0]),
                    'negative_surprises': len([s for s in surprises if s['surprise_pct'] < 0]),
                    'average_surprise': sum(s['surprise_pct'] for s in surprises) / len(surprises),
                    'largest_surprise': max(surprises, key=lambda x: abs(x['surprise_pct']))
                }
            
            # トレンド分析
            if trend_results:
                trends = [tr for tr in trend_results if tr]
                if trends:
                    trend_types = [tr.trend_type.value for tr in trends]
                    comparative['trend_analysis'] = {
                        'total_trends': len(trends),
                        'trend_distribution': {trend: trend_types.count(trend) for trend in set(trend_types)},
                        'average_confidence': sum(tr.confidence_level for tr in trends) / len(trends)
                    }
            
            # 品質分析
            quality_scores = [ind.data_quality_score for ind in indicators]
            comparative['quality_analysis'] = {
                'average_quality': sum(quality_scores) / len(quality_scores),
                'high_quality_count': len([q for q in quality_scores if q >= 80]),
                'low_quality_count': len([q for q in quality_scores if q < 50])
            }
            
            return comparative
            
        except Exception as e:
            logger.error(f"比較分析生成エラー: {e}")
            return {}
    
    def get_analysis_urls(self, analysis_result: Dict[str, Any]) -> Dict[str, str]:
        """分析結果のURLを取得"""
        urls = {}
        
        try:
            if 'components' in analysis_result:
                # 可視化URL
                if 'enhanced_visualization' in analysis_result['components']:
                    viz = analysis_result['components']['enhanced_visualization']
                    if 'saved_files' in viz:
                        for file_path in viz['saved_files']:
                            if file_path.endswith('.html'):
                                urls['visualization'] = f"file://{Path(file_path).absolute()}"
                
                # レポートURL
                if 'detailed_report' in analysis_result['components']:
                    report = analysis_result['components']['detailed_report']
                    if 'saved_files' in report:
                        for file_path in report['saved_files']:
                            if file_path.endswith('.html'):
                                urls['report'] = f"file://{Path(file_path).absolute()}"
            
        except Exception as e:
            logger.error(f"URL取得エラー: {e}")
        
        return urls
