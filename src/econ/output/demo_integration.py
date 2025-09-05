"""
Economic Indicators Output Integration Demo
経済指標出力統合デモ

実装した全ての出力・可視化機能を統合したデモンストレーション
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# 既存モジュール
from ..config.settings import EconConfig
from ..normalize.data_processor import ProcessedIndicator
from ..normalize.trend_analyzer import TrendResult
from .sheets_dashboard import SheetsDashboardManager
from .advanced_dashboard import AdvancedDashboard, DashboardConfig
from .realtime_updater import RealTimeUpdater, UpdateConfig, UpdateFrequency
from .visualization_enhancer import VisualizationEnhancer, VisualizationConfig, VisualizationType

logger = logging.getLogger(__name__)


class EconomicIndicatorsOutputDemo:
    """経済指標出力統合デモ"""
    
    def __init__(self, config: Optional[EconConfig] = None):
        self.config = config or EconConfig()
        
        # 出力コンポーネント初期化
        self.sheets_manager = SheetsDashboardManager(self.config)
        self.advanced_dashboard = AdvancedDashboard()
        self.realtime_updater = RealTimeUpdater()
        self.visualization_enhancer = VisualizationEnhancer()
        
        # デモ用設定
        self.demo_output_dir = Path(self.config.output.output_base_dir) / "demo_output"
        self.demo_output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_comprehensive_demo(self) -> Dict[str, Any]:
        """包括的なデモを実行"""
        logger.info("🚀 経済指標出力・可視化統合デモを開始します")
        
        demo_results = {
            'start_time': datetime.now(),
            'components': {},
            'urls': {},
            'files': {},
            'status': 'running'
        }
        
        try:
            # 1. サンプルデータ生成
            logger.info("📊 サンプルデータを生成中...")
            indicators, trend_results = self._generate_sample_data()
            demo_results['components']['sample_data'] = {
                'indicators_count': len(indicators),
                'trend_results_count': len(trend_results)
            }
            
            # 2. Google Sheets ダッシュボード作成
            logger.info("📈 Google Sheets ダッシュボードを作成中...")
            sheets_result = self._demo_sheets_dashboard(indicators, trend_results)
            demo_results['components']['sheets_dashboard'] = sheets_result
            if sheets_result.get('spreadsheet_id'):
                demo_results['urls']['sheets'] = f"https://docs.google.com/spreadsheets/d/{sheets_result['spreadsheet_id']}"
            
            # 3. 高度なダッシュボード作成
            logger.info("🎨 高度なダッシュボードを作成中...")
            advanced_result = self._demo_advanced_dashboard(indicators, trend_results)
            demo_results['components']['advanced_dashboard'] = advanced_result
            if advanced_result.get('saved_files'):
                demo_results['files']['advanced_dashboard'] = advanced_result['saved_files']
            
            # 4. 高度な可視化作成
            logger.info("📊 高度な可視化を作成中...")
            visualization_result = self._demo_advanced_visualizations(indicators, trend_results)
            demo_results['components']['visualizations'] = visualization_result
            if visualization_result.get('saved_files'):
                demo_results['files']['visualizations'] = visualization_result['saved_files']
            
            # 5. リアルタイム更新システムデモ
            logger.info("⚡ リアルタイム更新システムをデモ中...")
            realtime_result = self._demo_realtime_system(indicators, trend_results)
            demo_results['components']['realtime_system'] = realtime_result
            
            # 6. 統合レポート生成
            logger.info("📋 統合レポートを生成中...")
            report_result = self._generate_integration_report(demo_results)
            demo_results['components']['integration_report'] = report_result
            if report_result.get('report_file'):
                demo_results['files']['integration_report'] = report_result['report_file']
            
            demo_results['status'] = 'completed'
            demo_results['end_time'] = datetime.now()
            demo_results['duration'] = (demo_results['end_time'] - demo_results['start_time']).total_seconds()
            
            logger.info(f"✅ デモが完了しました（実行時間: {demo_results['duration']:.1f}秒）")
            
            # 結果サマリーを表示
            self._display_demo_summary(demo_results)
            
            return demo_results
            
        except Exception as e:
            logger.error(f"❌ デモ実行エラー: {e}")
            demo_results['status'] = 'error'
            demo_results['error'] = str(e)
            return demo_results
    
    def _generate_sample_data(self) -> tuple[List[ProcessedIndicator], List[TrendResult]]:
        """サンプルデータを生成"""
        try:
            # 既存のデータ取得機能を使用
            from ..adapters.investpy_calendar import InvestPyCalendar
            from ..normalize.data_processor import DataProcessor
            from ..normalize.trend_analyzer import TrendAnalyzer
            
            # カレンダー取得
            calendar = InvestPyCalendar()
            events = calendar.get_economic_calendar(
                countries=self.config.targets.target_countries[:3],  # デモ用に3カ国に制限
                importance=self.config.targets.importance_threshold
            )
            
            # データ処理
            processor = DataProcessor()
            indicators = []
            
            for event in events[:10]:  # デモ用に10指標に制限
                try:
                    processed = processor.process_indicator(event)
                    if processed:
                        indicators.append(processed)
                except Exception as e:
                    logger.warning(f"指標処理エラー: {e}")
                    continue
            
            # トレンド分析
            trend_analyzer = TrendAnalyzer()
            trend_results = []
            
            for indicator in indicators:
                try:
                    if indicator.historical_data is not None:
                        trend_result = trend_analyzer.analyze_trend(indicator.historical_data)
                        trend_results.append(trend_result)
                    else:
                        trend_results.append(None)
                except Exception as e:
                    logger.warning(f"トレンド分析エラー: {e}")
                    trend_results.append(None)
            
            logger.info(f"サンプルデータ生成完了: {len(indicators)}指標, {len(trend_results)}トレンド結果")
            return indicators, trend_results
            
        except Exception as e:
            logger.error(f"サンプルデータ生成エラー: {e}")
            return [], []
    
    def _demo_sheets_dashboard(self, indicators: List[ProcessedIndicator], trend_results: List[TrendResult]) -> Dict[str, Any]:
        """Google Sheets ダッシュボードデモ"""
        try:
            # ダッシュボード作成
            spreadsheet_id = self.sheets_manager.create_economic_dashboard(
                indicators, trend_results, "経済指標デモダッシュボード"
            )
            
            if spreadsheet_id:
                return {
                    'status': 'success',
                    'spreadsheet_id': spreadsheet_id,
                    'url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                    'message': 'Google Sheets ダッシュボードが正常に作成されました'
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Google Sheets ダッシュボードの作成に失敗しました'
                }
                
        except Exception as e:
            logger.error(f"Google Sheets ダッシュボードデモエラー: {e}")
            return {
                'status': 'error',
                'message': f'Google Sheets ダッシュボードエラー: {e}'
            }
    
    def _demo_advanced_dashboard(self, indicators: List[ProcessedIndicator], trend_results: List[TrendResult]) -> Dict[str, Any]:
        """高度なダッシュボードデモ"""
        try:
            # ダッシュボード設定
            dashboard_config = DashboardConfig(
                title="経済指標高度分析ダッシュボード（デモ）",
                save_path=self.demo_output_dir / "advanced_dashboard"
            )
            
            # 高度なダッシュボード作成
            advanced_dashboard = AdvancedDashboard(dashboard_config)
            result = advanced_dashboard.create_comprehensive_dashboard(indicators, trend_results)
            
            if 'error' not in result:
                return {
                    'status': 'success',
                    'saved_files': result.get('saved_files', []),
                    'dashboard_info': result.get('dashboard_info', {}),
                    'message': '高度なダッシュボードが正常に作成されました'
                }
            else:
                return {
                    'status': 'error',
                    'message': f'高度なダッシュボードエラー: {result["error"]}'
                }
                
        except Exception as e:
            logger.error(f"高度なダッシュボードデモエラー: {e}")
            return {
                'status': 'error',
                'message': f'高度なダッシュボードエラー: {e}'
            }
    
    def _demo_advanced_visualizations(self, indicators: List[ProcessedIndicator], trend_results: List[TrendResult]) -> Dict[str, Any]:
        """高度な可視化デモ"""
        try:
            # 可視化設定
            viz_config = VisualizationConfig(
                save_path=self.demo_output_dir / "advanced_visualizations"
            )
            
            # 可視化エンハンサー作成
            viz_enhancer = VisualizationEnhancer(viz_config)
            
            # 主要な可視化タイプを選択
            viz_types = [
                VisualizationType.TREND_ANALYSIS,
                VisualizationType.CORRELATION_MATRIX,
                VisualizationType.VOLATILITY_SURFACE,
                VisualizationType.FORECAST_ACCURACY,
                VisualizationType.RISK_METRICS,
                VisualizationType.COUNTRY_COMPARISON
            ]
            
            # 可視化作成
            results = viz_enhancer.create_advanced_visualizations(
                indicators, trend_results, viz_types
            )
            
            # ファイル保存
            saved_files = []
            for viz_type, result in results.items():
                if 'error' not in result and 'figure' in result:
                    try:
                        # HTML保存
                        html_path = self.demo_output_dir / f"{viz_type}.html"
                        with open(html_path, 'w', encoding='utf-8') as f:
                            f.write(result['html'])
                        saved_files.append(str(html_path))
                        
                        # PNG保存
                        png_path = self.demo_output_dir / f"{viz_type}.png"
                        result['figure'].write_image(str(png_path), width=1200, height=800, scale=2)
                        saved_files.append(str(png_path))
                        
                    except Exception as e:
                        logger.warning(f"{viz_type}保存エラー: {e}")
            
            return {
                'status': 'success',
                'visualizations': list(results.keys()),
                'saved_files': saved_files,
                'results': results,
                'message': f'{len(results)}種類の高度な可視化が作成されました'
            }
            
        except Exception as e:
            logger.error(f"高度な可視化デモエラー: {e}")
            return {
                'status': 'error',
                'message': f'高度な可視化エラー: {e}'
            }
    
    def _demo_realtime_system(self, indicators: List[ProcessedIndicator], trend_results: List[TrendResult]) -> Dict[str, Any]:
        """リアルタイム更新システムデモ"""
        try:
            # 更新設定
            update_config = UpdateConfig(
                enabled=True,
                frequency=UpdateFrequency.HOURLY,
                update_sheets=True,
                update_dashboard=True,
                update_reports=True,
                notify_on_success=False,
                notify_on_error=True
            )
            
            # リアルタイム更新システム作成
            realtime_updater = RealTimeUpdater(update_config, self.config)
            
            # コールバック関数追加
            def on_data_update(updated_indicators, updated_trend_results):
                logger.info(f"データ更新コールバック: {len(updated_indicators)}指標")
            
            def on_status_change(status):
                logger.info(f"ステータス変更: {status.status}")
            
            realtime_updater.add_data_update_callback(on_data_update)
            realtime_updater.add_status_change_callback(on_status_change)
            
            # システム開始（デモ用に短時間）
            realtime_updater.start()
            
            # 強制更新を実行
            realtime_updater.force_update()
            
            # ステータス取得
            status = realtime_updater.get_status()
            urls = realtime_updater.get_dashboard_urls()
            
            # システム停止
            realtime_updater.stop()
            
            return {
                'status': 'success',
                'update_status': {
                    'last_update': status.last_update.isoformat() if status.last_update else None,
                    'status': status.status,
                    'success_count': status.success_count,
                    'error_count': status.error_count
                },
                'dashboard_urls': urls,
                'message': 'リアルタイム更新システムのデモが完了しました'
            }
            
        except Exception as e:
            logger.error(f"リアルタイム更新システムデモエラー: {e}")
            return {
                'status': 'error',
                'message': f'リアルタイム更新システムエラー: {e}'
            }
    
    def _generate_integration_report(self, demo_results: Dict[str, Any]) -> Dict[str, Any]:
        """統合レポート生成"""
        try:
            report_content = f"""# 経済指標出力・可視化統合デモ レポート

## 📊 デモ実行概要

- **実行日時**: {demo_results['start_time'].strftime('%Y年%m月%d日 %H:%M:%S')}
- **実行時間**: {demo_results.get('duration', 0):.1f}秒
- **ステータス**: {demo_results['status']}

## 🎯 実装機能

### 1. Google Sheets ダッシュボード
- **ステータス**: {demo_results['components']['sheets_dashboard']['status']}
- **メッセージ**: {demo_results['components']['sheets_dashboard']['message']}
- **URL**: {demo_results['urls'].get('sheets', 'N/A')}

### 2. 高度なダッシュボード
- **ステータス**: {demo_results['components']['advanced_dashboard']['status']}
- **メッセージ**: {demo_results['components']['advanced_dashboard']['message']}
- **保存ファイル**: {len(demo_results['files'].get('advanced_dashboard', []))}件

### 3. 高度な可視化
- **ステータス**: {demo_results['components']['visualizations']['status']}
- **可視化種類**: {len(demo_results['components']['visualizations'].get('visualizations', []))}種類
- **保存ファイル**: {len(demo_results['files'].get('visualizations', []))}件

### 4. リアルタイム更新システム
- **ステータス**: {demo_results['components']['realtime_system']['status']}
- **メッセージ**: {demo_results['components']['realtime_system']['message']}

## 📈 サンプルデータ

- **指標数**: {demo_results['components']['sample_data']['indicators_count']}
- **トレンド結果数**: {demo_results['components']['sample_data']['trend_results_count']}

## 🔗 アクセスURL

"""
            
            for name, url in demo_results['urls'].items():
                report_content += f"- **{name}**: {url}\n"
            
            report_content += f"""
## 📁 生成ファイル

"""
            
            for category, files in demo_results['files'].items():
                report_content += f"### {category}\n"
                for file_path in files:
                    report_content += f"- {file_path}\n"
                report_content += "\n"
            
            report_content += f"""
## 🎉 デモ完了

経済指標システムの出力・可視化機能の統合デモが正常に完了しました。

### 実装された主要機能

1. **Google Sheets API連携**
   - リアルタイムデータ更新
   - マルチシート構成
   - 自動書式設定

2. **高度なダッシュボード**
   - インタラクティブチャート
   - リアルタイム更新
   - 包括的分析

3. **高度な可視化**
   - トレンド分析
   - 相関マトリクス
   - ボラティリティサーフェス
   - 予測精度分析
   - リスクメトリクス
   - 国別比較

4. **リアルタイム更新システム**
   - 自動データ更新
   - 並行処理
   - 通知機能
   - エラーハンドリング

### 次のステップ

1. 本番環境での設定調整
2. 通知チャネルの設定
3. スケジュール設定の最適化
4. ユーザー権限の設定
5. 監視・アラート機能の追加

---
*このレポートは自動生成されました - {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}*
"""
            
            # レポート保存
            report_file = self.demo_output_dir / "integration_demo_report.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            return {
                'status': 'success',
                'report_file': str(report_file),
                'message': '統合レポートが生成されました'
            }
            
        except Exception as e:
            logger.error(f"統合レポート生成エラー: {e}")
            return {
                'status': 'error',
                'message': f'統合レポート生成エラー: {e}'
            }
    
    def _display_demo_summary(self, demo_results: Dict[str, Any]):
        """デモサマリーを表示"""
        print("\n" + "="*80)
        print("🎉 経済指標出力・可視化統合デモ完了")
        print("="*80)
        
        print(f"📅 実行日時: {demo_results['start_time'].strftime('%Y年%m月%d日 %H:%M:%S')}")
        print(f"⏱️  実行時間: {demo_results.get('duration', 0):.1f}秒")
        print(f"📊 ステータス: {demo_results['status']}")
        
        print("\n📈 実装機能サマリー:")
        for component, result in demo_results['components'].items():
            status_icon = "✅" if result.get('status') == 'success' else "❌"
            print(f"  {status_icon} {component}: {result.get('message', 'N/A')}")
        
        print("\n🔗 アクセスURL:")
        for name, url in demo_results['urls'].items():
            print(f"  📌 {name}: {url}")
        
        print("\n📁 生成ファイル:")
        for category, files in demo_results['files'].items():
            print(f"  📂 {category}: {len(files)}件")
            for file_path in files:
                print(f"    - {file_path}")
        
        print("\n" + "="*80)
        print("✨ デモが正常に完了しました！")
        print("="*80 + "\n")


def main():
    """メイン実行関数"""
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # デモ実行
    demo = EconomicIndicatorsOutputDemo()
    results = demo.run_comprehensive_demo()
    
    return results


if __name__ == "__main__":
    main()
