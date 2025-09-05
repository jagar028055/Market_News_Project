"""
Employment Statistics Deep Analysis Demo
雇用統計深度分析デモ

米国雇用統計を例に、視認性を改善した深度分析システムのデモンストレーション
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, Any

# 既存モジュール
from ..config.settings import EconConfig
from ..normalize.data_processor import ProcessedIndicator, TrendDirection
from ..normalize.trend_analyzer import TrendResult, TrendType, PatternType
from .enhanced_analysis_system import EnhancedAnalysisSystem

logger = logging.getLogger(__name__)


class EmploymentStatisticsDemo:
    """雇用統計深度分析デモ"""
    
    def __init__(self):
        self.econ_config = EconConfig()
        self.analysis_system = EnhancedAnalysisSystem(self.econ_config)
        
    def create_realistic_employment_data(self) -> ProcessedIndicator:
        """現実的な雇用統計データを作成"""
        
        # 過去24ヶ月のデータ
        dates = pd.date_range(start='2022-01-01', end='2024-01-01', freq='MS')
        
        # 現実的な雇用統計データ（Non-Farm Payrolls）
        # 実際のデータに近いパターンで生成
        base_employment = 150000  # ベース雇用者数（千人）
        seasonal_pattern = np.sin(np.arange(len(dates)) * 2 * np.pi / 12) * 5000  # 季節性
        trend = np.arange(len(dates)) * 200  # 上昇トレンド
        noise = np.random.normal(0, 10000, len(dates))  # ノイズ
        
        employment_data = base_employment + seasonal_pattern + trend + noise
        
        # 最新月のデータ（2024年1月）
        latest_employment = employment_data[-1]
        forecast_employment = latest_employment + np.random.normal(0, 5000)  # 予想値
        previous_employment = employment_data[-2]  # 前回値
        
        # 実際値（予想より少し高い）
        actual_employment = forecast_employment + np.random.normal(15000, 5000)
        
        # イベントオブジェクト作成
        class EmploymentEvent:
            def __init__(self):
                self.country = 'US'
                self.indicator = 'Non-Farm Payrolls'
                self.title = 'Non-Farm Payrolls'
                self.actual = actual_employment
                self.forecast = forecast_employment
                self.previous = previous_employment
                self.importance = 'High'
                self.datetime = datetime(2024, 1, 5, 8, 30)  # 米国時間 8:30 AM
                self.currency = 'USD'
                self.unit = 'Thousands'
                
            def calculate_surprise(self):
                if self.actual and self.forecast:
                    surprise = self.actual - self.forecast
                    surprise_pct = (surprise / self.forecast) * 100
                    return {'surprise': surprise, 'surprise_pct': surprise_pct}
                return None
        
        # ProcessedIndicator作成
        class EmploymentIndicator:
            def __init__(self):
                self.original_event = EmploymentEvent()
                self.historical_data = pd.Series(employment_data, index=dates)
                self.data_quality_score = 95.0  # 高品質データ
                self.mom_change = ((actual_employment - previous_employment) / previous_employment) * 100
                self.yoy_change = ((actual_employment - employment_data[-13]) / employment_data[-13]) * 100
                self.z_score = (actual_employment - employment_data.mean()) / employment_data.std()
                self.trend_direction = TrendDirection.UP
                self.volatility_index = pd.Series(employment_data).pct_change().std() * 100 * np.sqrt(12)  # 年率ボラティリティ
                self.data_quality = "HIGH"
        
        return EmploymentIndicator()
    
    def create_trend_analysis(self, indicator: ProcessedIndicator) -> TrendResult:
        """トレンド分析結果を作成"""
        
        # 現実的なトレンド分析結果
        class EmploymentTrendResult:
            def __init__(self):
                self.trend_type = TrendType.BULL
                self.confidence_level = 85.5
                self.pattern_type = PatternType.CHANNEL
                self.pattern_confidence = 78.2
                self.slope = 180.5  # 月次平均増加数
                self.r_squared = 0.76
                self.support_levels = [145000, 148000, 151000]
                self.resistance_levels = [158000, 162000, 165000]
                self.breakout_probability = 0.65
                self.reversal_probability = 0.15
        
        return EmploymentTrendResult()
    
    async def run_comprehensive_demo(self) -> Dict[str, Any]:
        """包括的デモを実行"""
        
        try:
            logger.info("雇用統計深度分析デモ開始")
            
            # 1. 現実的なデータ作成
            print("📊 現実的な雇用統計データを作成中...")
            employment_indicator = self.create_realistic_employment_data()
            trend_result = self.create_trend_analysis(employment_indicator)
            
            print(f"✅ データ作成完了:")
            print(f"  - 国: {employment_indicator.original_event.country}")
            print(f"  - 指標: {employment_indicator.original_event.indicator}")
            print(f"  - 実際値: {employment_indicator.original_event.actual:,.0f}千人")
            print(f"  - 予想値: {employment_indicator.original_event.forecast:,.0f}千人")
            print(f"  - 前回値: {employment_indicator.original_event.previous:,.0f}千人")
            
            # サプライズ計算
            surprise_info = employment_indicator.original_event.calculate_surprise()
            if surprise_info:
                print(f"  - サプライズ: {surprise_info['surprise']:+,.0f}千人 ({surprise_info['surprise_pct']:+.1f}%)")
            
            # 2. 包括的分析実行
            print("\n🔍 包括的分析を実行中...")
            analysis_result = await self.analysis_system.analyze_indicator_comprehensively(
                employment_indicator,
                trend_result,
                include_visualization=True,
                include_data_collection=False,  # デモではスキップ
                include_detailed_report=False   # デモではスキップ
            )
            
            if 'error' in analysis_result:
                print(f"❌ 分析エラー: {analysis_result['error']}")
                return analysis_result
            
            # 3. 結果表示
            print("\n✅ 分析完了!")
            print(f"  - 分析時間: {analysis_result['analysis_time']}")
            print(f"  - コンポーネント数: {len(analysis_result.get('components', {}))}")
            
            # 4. 生成されたファイルのURL
            urls = self.analysis_system.get_analysis_urls(analysis_result)
            if urls:
                print("\n📁 生成されたファイル:")
                for name, url in urls.items():
                    print(f"  - {name}: {url}")
            
            # 5. 分析サマリー
            summary = analysis_result.get('summary', {})
            if summary:
                print("\n📋 分析サマリー:")
                key_findings = summary.get('key_findings', [])
                for finding in key_findings:
                    print(f"  - {finding}")
            
            # 6. 雇用統計特有の分析
            self._display_employment_specific_analysis(employment_indicator, trend_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"雇用統計デモエラー: {e}")
            return {'error': str(e)}
    
    def _display_employment_specific_analysis(self, indicator: ProcessedIndicator, trend_result: TrendResult):
        """雇用統計特有の分析を表示"""
        
        print("\n💼 雇用統計特有の分析:")
        
        # 労働市場の健全性
        actual = indicator.original_event.actual
        forecast = indicator.original_event.forecast
        previous = indicator.original_event.previous
        
        print(f"  📈 労働市場の健全性:")
        print(f"    - 月次雇用増加: {actual - previous:+,.0f}千人")
        print(f"    - 年次雇用増加: {indicator.yoy_change:+.1f}%")
        print(f"    - トレンド: {trend_result.trend_type.value}")
        print(f"    - 信頼度: {trend_result.confidence_level:.1f}%")
        
        # 経済への影響
        surprise_info = indicator.original_event.calculate_surprise()
        if surprise_info:
            surprise_pct = surprise_info['surprise_pct']
            if surprise_pct > 5:
                impact = "強くポジティブ"
            elif surprise_pct > 2:
                impact = "ポジティブ"
            elif surprise_pct < -5:
                impact = "強くネガティブ"
            elif surprise_pct < -2:
                impact = "ネガティブ"
            else:
                impact = "中立"
            
            print(f"  🎯 経済への影響:")
            print(f"    - サプライズ影響: {impact}")
            print(f"    - 市場予想との乖離: {surprise_pct:+.1f}%")
        
        # 政策含意
        print(f"  🏛️ 政策含意:")
        if actual > forecast:
            print(f"    - 雇用市場は予想以上に堅調")
            print(f"    - 金融政策の引き締め圧力が増加する可能性")
            print(f"    - インフレ圧力の上昇懸念")
        else:
            print(f"    - 雇用市場は予想を下回る")
            print(f"    - 金融政策の緩和余地が生まれる可能性")
            print(f"    - 経済成長への懸念")
        
        # 投資含意
        print(f"  💰 投資含意:")
        if actual > forecast:
            print(f"    - ドル高の可能性")
            print(f"    - 金利上昇期待で金融株にプラス")
            print(f"    - 成長株よりバリュー株が有利")
        else:
            print(f"    - ドル安の可能性")
            print(f"    - 金利低下期待で成長株にプラス")
            print(f"    - 債券市場にプラス")
    
    def create_comparative_analysis_demo(self) -> Dict[str, Any]:
        """比較分析デモを作成"""
        
        print("\n🔄 複数指標比較分析デモ:")
        
        # 複数の雇用関連指標を作成
        indicators = []
        trend_results = []
        
        # Non-Farm Payrolls
        nfp_indicator = self.create_realistic_employment_data()
        nfp_trend = self.create_trend_analysis(nfp_indicator)
        indicators.append(nfp_indicator)
        trend_results.append(nfp_trend)
        
        # Unemployment Rate (簡易版)
        class UnemploymentIndicator:
            def __init__(self):
                self.original_event = type('obj', (object,), {
                    'country': 'US',
                    'indicator': 'Unemployment Rate',
                    'actual': 3.7,
                    'forecast': 3.8,
                    'previous': 3.8,
                    'importance': 'High',
                    'datetime': datetime(2024, 1, 5, 8, 30)
                })()
                self.historical_data = pd.Series(np.random.normal(3.8, 0.2, 24))
                self.data_quality_score = 92.0
                self.mom_change = -0.1
                self.yoy_change = -0.3
                self.z_score = -0.5
                self.trend_direction = TrendDirection.DOWN
                self.volatility_index = 0.8
        
        # Average Hourly Earnings (簡易版)
        class EarningsIndicator:
            def __init__(self):
                self.original_event = type('obj', (object,), {
                    'country': 'US',
                    'indicator': 'Average Hourly Earnings',
                    'actual': 0.4,
                    'forecast': 0.3,
                    'previous': 0.3,
                    'importance': 'High',
                    'datetime': datetime(2024, 1, 5, 8, 30)
                })()
                self.historical_data = pd.Series(np.random.normal(0.3, 0.1, 24))
                self.data_quality_score = 88.0
                self.mom_change = 0.1
                self.yoy_change = 4.2
                self.z_score = 1.0
                self.trend_direction = TrendDirection.UP
                self.volatility_index = 0.5
        
        indicators.extend([UnemploymentIndicator(), EarningsIndicator()])
        trend_results.extend([None, None])  # 簡易版のためトレンド分析はスキップ
        
        print(f"✅ 比較分析対象: {len(indicators)}指標")
        for i, indicator in enumerate(indicators):
            print(f"  {i+1}. {indicator.original_event.country} - {indicator.original_event.indicator}")
            print(f"     実際値: {indicator.original_event.actual}")
            print(f"     予想値: {indicator.original_event.forecast}")
        
        return {
            'indicators': indicators,
            'trend_results': trend_results,
            'analysis_type': 'comparative_employment_analysis'
        }


async def main():
    """メイン関数"""
    
    print("🚀 雇用統計深度分析デモ開始")
    print("=" * 60)
    
    # デモ実行
    demo = EmploymentStatisticsDemo()
    
    # 包括的分析デモ
    result = await demo.run_comprehensive_demo()
    
    if 'error' not in result:
        print("\n" + "=" * 60)
        print("🎉 雇用統計深度分析デモ完了!")
        print("\n💡 このシステムの特徴:")
        print("  ✅ 視認性の大幅改善（大きなチャート、明確な色分け）")
        print("  ✅ 深度のある分析（6つの分析セクション）")
        print("  ✅ 網羅的なデータ収集（複数ソース対応）")
        print("  ✅ プロフェッショナルレベルのレポート生成")
        print("  ✅ インタラクティブな可視化")
        print("  ✅ 雇用統計特有の詳細分析")
        
        # 比較分析デモ
        comparative_data = demo.create_comparative_analysis_demo()
        print(f"\n📊 比較分析デモも準備完了: {len(comparative_data['indicators'])}指標")
        
    else:
        print(f"\n❌ デモ実行エラー: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
