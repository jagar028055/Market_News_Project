"""
Modern Dashboard System for Economic Indicators
経済指標モダンダッシュボードシステム

スタイリッシュでスマートなダッシュボードシステム
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
from dataclasses import dataclass, field

# 既存モジュール
from .modern_design_system import ModernDesignSystem, ModernDesignConfig
from .real_chart_generator import RealChartGenerator
from .latest_data_fetcher import LatestDataFetcher, LatestDataConfig

logger = logging.getLogger(__name__)


@dataclass
class ModernDashboardConfig:
    """モダンダッシュボード設定"""
    # 基本設定
    country: str = "US"
    screen_size: str = "desktop"
    
    # 出力設定
    output_path: Optional[Path] = None
    output_format: List[str] = field(default_factory=lambda: ["html", "json"])
    
    # デザイン設定
    design_config: Optional[ModernDesignConfig] = None
    
    # データ設定
    data_config: Optional[LatestDataConfig] = None


class ModernDashboard:
    """モダンダッシュボードシステム"""
    
    def __init__(self, config: Optional[ModernDashboardConfig] = None):
        self.config = config or ModernDashboardConfig()
        
        # コンポーネント初期化
        self.design_system = ModernDesignSystem(self.config.design_config)
        self.chart_generator = RealChartGenerator()
        self.data_fetcher = LatestDataFetcher(self.config.data_config)
        
        # 出力ディレクトリ作成
        if self.config.output_path:
            self.config.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def generate_modern_dashboard(self) -> Dict[str, Any]:
        """モダンダッシュボードを生成"""
        
        try:
            logger.info("モダンダッシュボード生成開始")
            
            # 1. 最新データを取得
            logger.info("最新データを取得中...")
            latest_data = self.data_fetcher.get_comprehensive_employment_info()
            
            # 2. 実際のチャートを生成
            logger.info("実際のチャートを生成中...")
            charts = self.chart_generator.generate_all_charts(latest_data)
            latest_data['charts'] = charts
            
            # 3. モダンなHTMLを生成
            logger.info("モダンなHTMLを生成中...")
            html_content = self.design_system.generate_modern_html(
                latest_data, self.config.screen_size
            )
            
            # 4. ファイル保存
            saved_files = []
            if self.config.output_path:
                saved_files = self._save_dashboard(html_content, latest_data)
            
            result = {
                'html': html_content,
                'data': latest_data,
                'saved_files': saved_files,
                'screen_size': self.config.screen_size,
                'type': 'modern_dashboard',
                'generated_at': datetime.now().isoformat()
            }
            
            logger.info("モダンダッシュボード生成完了")
            return result
            
        except Exception as e:
            logger.error(f"モダンダッシュボード生成エラー: {e}")
            return {'error': str(e)}
    
    def _save_dashboard(self, html_content: str, data: Dict[str, Any]) -> List[str]:
        """ダッシュボードを保存"""
        
        saved_files = []
        
        try:
            if not self.config.output_path:
                return saved_files
            
            # HTML保存
            if 'html' in self.config.output_format:
                html_path = self.config.output_path.with_name(
                    f"modern_dashboard_{self.config.screen_size}.html"
                )
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                saved_files.append(str(html_path))
            
            # JSON保存
            if 'json' in self.config.output_format:
                json_path = self.config.output_path.with_name(
                    f"modern_dashboard_{self.config.screen_size}.json"
                )
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                saved_files.append(str(json_path))
            
            logger.info(f"モダンダッシュボードが保存されました: {saved_files}")
            
        except Exception as e:
            logger.error(f"モダンダッシュボード保存エラー: {e}")
        
        return saved_files
    
    def generate_responsive_dashboards(self) -> Dict[str, Any]:
        """複数画面サイズのレスポンシブダッシュボードを生成"""
        
        try:
            logger.info("レスポンシブダッシュボード生成開始")
            
            # 最新データを取得
            latest_data = self.data_fetcher.get_comprehensive_employment_info()
            
            # 実際のチャートを生成
            charts = self.chart_generator.generate_all_charts(latest_data)
            latest_data['charts'] = charts
            
            # 複数画面サイズでダッシュボードを生成
            screen_sizes = ['mobile', 'tablet', 'desktop', 'large_desktop']
            results = {}
            
            for screen_size in screen_sizes:
                logger.info(f"{screen_size}サイズのダッシュボードを生成中...")
                
                # 画面サイズを更新
                self.config.screen_size = screen_size
                
                # HTML生成
                html_content = self.design_system.generate_modern_html(
                    latest_data, screen_size
                )
                
                # ファイル保存
                saved_files = []
                if self.config.output_path:
                    saved_files = self._save_responsive_dashboard(html_content, latest_data, screen_size)
                
                results[screen_size] = {
                    'html': html_content,
                    'saved_files': saved_files,
                    'screen_size': screen_size
                }
            
            logger.info("レスポンシブダッシュボード生成完了")
            return results
            
        except Exception as e:
            logger.error(f"レスポンシブダッシュボード生成エラー: {e}")
            return {'error': str(e)}
    
    def _save_responsive_dashboard(
        self, 
        html_content: str, 
        data: Dict[str, Any], 
        screen_size: str
    ) -> List[str]:
        """レスポンシブダッシュボードを保存"""
        
        saved_files = []
        
        try:
            if not self.config.output_path:
                return saved_files
            
            # HTML保存
            if 'html' in self.config.output_format:
                html_path = self.config.output_path.with_name(
                    f"modern_dashboard_{screen_size}.html"
                )
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                saved_files.append(str(html_path))
            
            # JSON保存
            if 'json' in self.config.output_format:
                json_path = self.config.output_path.with_name(
                    f"modern_dashboard_{screen_size}.json"
                )
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                saved_files.append(str(json_path))
            
        except Exception as e:
            logger.error(f"レスポンシブダッシュボード保存エラー: {e}")
        
        return saved_files
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """ダッシュボードサマリーを取得"""
        
        try:
            # 最新データを取得
            latest_data = self.data_fetcher.get_comprehensive_employment_info()
            
            # サマリーを構築
            summary = {
                'title': latest_data.get('title', '経済指標ダッシュボード'),
                'analysis_date': latest_data.get('analysis_date', 'N/A'),
                'release_date': latest_data.get('release_date', 'N/A'),
                'total_indicators': len(latest_data.get('indicators', {})),
                'screen_size': self.config.screen_size,
                'features': [
                    'スタイリッシュなモダンデザイン',
                    '実際のPlotlyチャート',
                    '最新の経済データ',
                    'レスポンシブ対応',
                    '包括的な雇用統計分析',
                    '市場影響分析',
                    '投資含意',
                    '政策含意'
                ],
                'charts_count': 6,  # 生成されるチャート数
                'tables_count': len(latest_data.get('tables', [])),
                'summary_cards_count': len(latest_data.get('summary_cards', []))
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"ダッシュボードサマリー取得エラー: {e}")
            return {'error': str(e)}
