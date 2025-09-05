"""
Google Sheets 経済指標ダッシュボード連携モジュール

経済指標データをGoogle Sheetsにリアルタイムで出力し、
高度なダッシュボード機能を提供する。
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import logging
from pathlib import Path
import json

# Google API
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# 既存モジュール
from ..config.settings import EconConfig
from ..normalize.data_processor import ProcessedIndicator
from ..normalize.trend_analyzer import TrendResult
from ..render.chart_generator import ChartGenerator, ChartConfig

logger = logging.getLogger(__name__)


class SheetsDashboardManager:
    """Google Sheets ダッシュボード管理クラス"""
    
    def __init__(self, config: Optional[EconConfig] = None):
        self.config = config or EconConfig()
        self.sheets_service = None
        self.drive_service = None
        self._authenticate()
        
        # ダッシュシート設定
        self.dashboard_spreadsheet_id = None
        self.dashboard_folder_id = None
        
    def _authenticate(self):
        """Google API認証"""
        try:
            # 既存の認証システムを利用
            from gdocs.client import authenticate_google_services
            self.drive_service, _, self.sheets_service = authenticate_google_services()
            
            if not self.sheets_service:
                logger.error("Google Sheets認証に失敗しました")
                return
                
            logger.info("Google Sheets認証が完了しました")
            
        except Exception as e:
            logger.error(f"Google API認証エラー: {e}")
            self.sheets_service = None
            self.drive_service = None
    
    def create_economic_dashboard(
        self, 
        indicators: List[ProcessedIndicator],
        trend_results: Optional[List[TrendResult]] = None,
        folder_name: str = "Economic Indicators Dashboard"
    ) -> Optional[str]:
        """経済指標ダッシュボードを作成"""
        
        if not self.sheets_service:
            logger.error("Google Sheetsサービスが利用できません")
            return None
        
        try:
            # フォルダ作成
            folder_id = self._create_dashboard_folder(folder_name)
            if not folder_id:
                return None
            
            # メインダッシュボードスプレッドシート作成
            spreadsheet_id = self._create_main_dashboard(indicators, folder_id)
            if not spreadsheet_id:
                return None
            
            # 各シートを設定
            self._setup_summary_sheet(spreadsheet_id, indicators)
            self._setup_indicators_sheet(spreadsheet_id, indicators)
            self._setup_trend_analysis_sheet(spreadsheet_id, indicators, trend_results)
            self._setup_correlation_sheet(spreadsheet_id, indicators)
            self._setup_risk_assessment_sheet(spreadsheet_id, indicators, trend_results)
            
            # チャート埋め込み
            self._embed_charts(spreadsheet_id, indicators, trend_results)
            
            # 自動更新設定
            self._setup_auto_refresh(spreadsheet_id)
            
            self.dashboard_spreadsheet_id = spreadsheet_id
            self.dashboard_folder_id = folder_id
            
            logger.info(f"経済指標ダッシュボードが作成されました: {spreadsheet_id}")
            return spreadsheet_id
            
        except Exception as e:
            logger.error(f"ダッシュボード作成エラー: {e}")
            return None
    
    def _create_dashboard_folder(self, folder_name: str) -> Optional[str]:
        """ダッシュボード用フォルダを作成"""
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"ダッシュボードフォルダを作成: {folder_id}")
            return folder_id
            
        except Exception as e:
            logger.error(f"フォルダ作成エラー: {e}")
            return None
    
    def _create_main_dashboard(self, indicators: List[ProcessedIndicator], folder_id: str) -> Optional[str]:
        """メインダッシュボードスプレッドシートを作成"""
        try:
            # マルチシート構成
            sheets = [
                {
                    'properties': {
                        'title': '📊 サマリー',
                        'gridProperties': {
                            'columnCount': 12,
                            'rowCount': 50,
                            'frozenRowCount': 2
                        }
                    }
                },
                {
                    'properties': {
                        'title': '📈 指標詳細',
                        'gridProperties': {
                            'columnCount': 15,
                            'rowCount': 1000,
                            'frozenRowCount': 1
                        }
                    }
                },
                {
                    'properties': {
                        'title': '📉 トレンド分析',
                        'gridProperties': {
                            'columnCount': 10,
                            'rowCount': 500,
                            'frozenRowCount': 1
                        }
                    }
                },
                {
                    'properties': {
                        'title': '🔗 相関分析',
                        'gridProperties': {
                            'columnCount': 20,
                            'rowCount': 20,
                            'frozenRowCount': 1
                        }
                    }
                },
                {
                    'properties': {
                        'title': '⚠️ リスク評価',
                        'gridProperties': {
                            'columnCount': 8,
                            'rowCount': 200,
                            'frozenRowCount': 1
                        }
                    }
                }
            ]
            
            spreadsheet = {
                'properties': {
                    'title': f'経済指標ダッシュボード - {datetime.now().strftime("%Y年%m月%d日")}',
                    'locale': 'ja_JP',
                    'timeZone': 'Asia/Tokyo'
                },
                'sheets': sheets
            }
            
            spreadsheet_result = self.sheets_service.spreadsheets().create(
                body=spreadsheet
            ).execute()
            
            spreadsheet_id = spreadsheet_result['spreadsheetId']
            
            # フォルダに移動
            self.drive_service.files().update(
                fileId=spreadsheet_id,
                addParents=folder_id,
                removeParents='root'
            ).execute()
            
            return spreadsheet_id
            
        except Exception as e:
            logger.error(f"スプレッドシート作成エラー: {e}")
            return None
    
    def _setup_summary_sheet(self, spreadsheet_id: str, indicators: List[ProcessedIndicator]):
        """サマリーシートを設定"""
        try:
            # ヘッダー
            headers = [
                ['経済指標ダッシュボード - サマリー'],
                [''],
                ['更新日時', datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')],
                [''],
                ['📊 全体統計'],
                ['総指標数', len(indicators)],
                ['対象国数', len(set(ind.original_event.country for ind in indicators))],
                ['平均データ品質', f"{sum(ind.data_quality_score for ind in indicators) / len(indicators):.1f}/100"],
                [''],
                ['🎯 注目指標'],
                ['国', '指標名', '最新値', '予想値', 'サプライズ', '重要度', '品質スコア']
            ]
            
            # 注目指標データ
            highlights = self._get_highlights(indicators)
            for highlight in highlights[:10]:  # 上位10件
                event = highlight.original_event
                surprise_info = event.calculate_surprise() if event.actual and event.forecast else None
                
                row = [
                    event.country,
                    getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A'),
                    event.actual or 'N/A',
                    event.forecast or 'N/A',
                    f"{surprise_info['surprise']:+.2f}" if surprise_info else 'N/A',
                    event.importance or 'N/A',
                    f"{highlight.data_quality_score:.0f}"
                ]
                headers.append(row)
            
            # データを書き込み
            self._write_to_sheet(
                spreadsheet_id, 
                '📊 サマリー', 
                headers,
                start_row=1,
                start_col=1
            )
            
            # 書式設定
            self._format_summary_sheet(spreadsheet_id)
            
        except Exception as e:
            logger.error(f"サマリーシート設定エラー: {e}")
    
    def _setup_indicators_sheet(self, spreadsheet_id: str, indicators: List[ProcessedIndicator]):
        """指標詳細シートを設定"""
        try:
            # ヘッダー
            headers = [
                ['国', '指標名', '発表日時', '重要度', '最新値', '前回値', '予想値', 
                 'サプライズ', 'MoM変化', 'YoY変化', 'Z-Score', 'トレンド', '品質スコア', 'ボラティリティ', '備考']
            ]
            
            # データ行
            for indicator in indicators:
                event = indicator.original_event
                surprise_info = event.calculate_surprise() if event.actual and event.forecast else None
                
                row = [
                    event.country,
                    getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A'),
                    event.datetime.strftime('%Y-%m-%d %H:%M') if event.datetime else 'N/A',
                    event.importance or 'N/A',
                    event.actual or 'N/A',
                    event.previous or 'N/A',
                    event.forecast or 'N/A',
                    f"{surprise_info['surprise']:+.2f}" if surprise_info else 'N/A',
                    f"{indicator.mom_change:+.2f}%" if indicator.mom_change else 'N/A',
                    f"{indicator.yoy_change:+.2f}%" if indicator.yoy_change else 'N/A',
                    f"{indicator.z_score:.2f}" if indicator.z_score else 'N/A',
                    indicator.trend_direction.value if indicator.trend_direction else 'N/A',
                    f"{indicator.data_quality_score:.0f}",
                    f"{getattr(indicator, 'volatility_index', 0):.1f}%" if hasattr(indicator, 'volatility_index') else 'N/A',
                    self._get_indicator_notes(indicator)
                ]
                headers.append(row)
            
            # データを書き込み
            self._write_to_sheet(
                spreadsheet_id,
                '📈 指標詳細',
                headers,
                start_row=1,
                start_col=1
            )
            
            # 書式設定
            self._format_indicators_sheet(spreadsheet_id)
            
        except Exception as e:
            logger.error(f"指標詳細シート設定エラー: {e}")
    
    def _setup_trend_analysis_sheet(self, spreadsheet_id: str, indicators: List[ProcessedIndicator], trend_results: Optional[List[TrendResult]]):
        """トレンド分析シートを設定"""
        try:
            headers = [
                ['国', '指標名', 'トレンドタイプ', '信頼度', 'パターン', 'サポートレベル', 'レジスタンスレベル', 'トレンド強度', '変化率', '備考']
            ]
            
            for i, indicator in enumerate(indicators):
                trend_result = trend_results[i] if trend_results and i < len(trend_results) else None
                event = indicator.original_event
                
                row = [
                    event.country,
                    getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A'),
                    trend_result.trend_type.value if trend_result else 'N/A',
                    f"{trend_result.confidence_level:.1f}%" if trend_result else 'N/A',
                    trend_result.pattern_type.value if trend_result else 'N/A',
                    ', '.join(f'{level:.2f}' for level in trend_result.support_levels[:3]) if trend_result and trend_result.support_levels else 'N/A',
                    ', '.join(f'{level:.2f}' for level in trend_result.resistance_levels[:3]) if trend_result and trend_result.resistance_levels else 'N/A',
                    f"{getattr(indicator, 'trend_strength', 0):.1f}" if hasattr(indicator, 'trend_strength') else 'N/A',
                    f"{indicator.yoy_change:+.2f}%" if indicator.yoy_change else 'N/A',
                    self._get_trend_notes(trend_result) if trend_result else 'N/A'
                ]
                headers.append(row)
            
            self._write_to_sheet(
                spreadsheet_id,
                '📉 トレンド分析',
                headers,
                start_row=1,
                start_col=1
            )
            
        except Exception as e:
            logger.error(f"トレンド分析シート設定エラー: {e}")
    
    def _setup_correlation_sheet(self, spreadsheet_id: str, indicators: List[ProcessedIndicator]):
        """相関分析シートを設定"""
        try:
            # 相関マトリクスを生成
            correlation_data = self._generate_correlation_matrix(indicators)
            
            if not correlation_data:
                return
            
            # ヘッダー行
            headers = [['指標名'] + list(correlation_data.columns)]
            
            # データ行
            for index, row in correlation_data.iterrows():
                data_row = [index] + [f"{value:.3f}" for value in row.values]
                headers.append(data_row)
            
            self._write_to_sheet(
                spreadsheet_id,
                '🔗 相関分析',
                headers,
                start_row=1,
                start_col=1
            )
            
            # 条件付き書式設定（相関の強さに応じて色分け）
            self._format_correlation_sheet(spreadsheet_id, len(correlation_data))
            
        except Exception as e:
            logger.error(f"相関分析シート設定エラー: {e}")
    
    def _setup_risk_assessment_sheet(self, spreadsheet_id: str, indicators: List[ProcessedIndicator], trend_results: Optional[List[TrendResult]]):
        """リスク評価シートを設定"""
        try:
            headers = [
                ['リスクタイプ', '重要度', '影響指標数', '説明', '推奨アクション', '監視項目']
            ]
            
            risks = self._assess_risks(indicators, trend_results)
            
            for risk in risks:
                row = [
                    risk['type'],
                    risk['severity'],
                    risk.get('indicator_count', 0),
                    risk['description'],
                    risk.get('recommended_action', '継続監視'),
                    risk.get('monitoring_items', 'N/A')
                ]
                headers.append(row)
            
            self._write_to_sheet(
                spreadsheet_id,
                '⚠️ リスク評価',
                headers,
                start_row=1,
                start_col=1
            )
            
        except Exception as e:
            logger.error(f"リスク評価シート設定エラー: {e}")
    
    def _embed_charts(self, spreadsheet_id: str, indicators: List[ProcessedIndicator], trend_results: Optional[List[TrendResult]]):
        """チャートを埋め込み"""
        try:
            chart_generator = ChartGenerator()
            
            # 主要指標のチャートを生成
            for i, indicator in enumerate(indicators[:5]):  # 上位5指標
                trend_result = trend_results[i] if trend_results and i < len(trend_results) else None
                
                # チャート生成
                chart_config = ChartConfig(
                    width=800,
                    height=400,
                    output_format=['png'],
                    save_path=Path(f"./temp_chart_{i}.png")
                )
                
                chart_result = chart_generator.generate_indicator_chart(
                    indicator, trend_result, chart_config
                )
                
                if 'saved_files' in chart_result:
                    # チャートをスプレッドシートに挿入
                    self._insert_chart_to_sheet(
                        spreadsheet_id,
                        '📊 サマリー',
                        f"K{i*10+1}",  # チャート挿入位置
                        chart_result['saved_files'][0]
                    )
            
        except Exception as e:
            logger.error(f"チャート埋め込みエラー: {e}")
    
    def _setup_auto_refresh(self, spreadsheet_id: str):
        """自動更新設定"""
        try:
            # 更新時刻を記録
            update_info = {
                'last_update': datetime.now().isoformat(),
                'next_update': (datetime.now() + timedelta(hours=6)).isoformat(),
                'update_frequency': '6時間毎'
            }
            
            # メタデータシートに記録
            self._write_to_sheet(
                spreadsheet_id,
                '📊 サマリー',
                [['最終更新', update_info['last_update']], ['次回更新予定', update_info['next_update']]],
                start_row=1,
                start_col=10
            )
            
        except Exception as e:
            logger.error(f"自動更新設定エラー: {e}")
    
    def _write_to_sheet(self, spreadsheet_id: str, sheet_name: str, data: List[List], start_row: int = 1, start_col: int = 1):
        """シートにデータを書き込み"""
        try:
            range_name = f"{sheet_name}!{self._get_cell_range(start_row, start_col, len(data), len(data[0]) if data else 0)}"
            
            body = {
                'values': data
            }
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
        except Exception as e:
            logger.error(f"シート書き込みエラー: {e}")
    
    def _get_cell_range(self, start_row: int, start_col: int, num_rows: int, num_cols: int) -> str:
        """セル範囲を取得"""
        start_cell = f"{self._col_num_to_letter(start_col)}{start_row}"
        end_cell = f"{self._col_num_to_letter(start_col + num_cols - 1)}{start_row + num_rows - 1}"
        return f"{start_cell}:{end_cell}"
    
    def _col_num_to_letter(self, col_num: int) -> str:
        """列番号を文字に変換"""
        result = ""
        while col_num > 0:
            col_num -= 1
            result = chr(col_num % 26 + ord('A')) + result
            col_num //= 26
        return result
    
    def _get_highlights(self, indicators: List[ProcessedIndicator]) -> List[ProcessedIndicator]:
        """注目指標を取得"""
        # サプライズ、Z-score、変化率でソート
        def highlight_score(indicator):
            score = 0
            event = indicator.original_event
            
            # サプライズスコア
            if event.actual and event.forecast:
                surprise_info = event.calculate_surprise()
                if surprise_info:
                    score += abs(surprise_info['surprise_pct'])
            
            # Z-score
            if indicator.z_score:
                score += abs(indicator.z_score) * 10
            
            # 変化率
            if indicator.yoy_change:
                score += abs(indicator.yoy_change)
            
            return score
        
        return sorted(indicators, key=highlight_score, reverse=True)
    
    def _get_indicator_notes(self, indicator: ProcessedIndicator) -> str:
        """指標の備考を生成"""
        notes = []
        
        if indicator.z_score and abs(indicator.z_score) > 2:
            notes.append("統計的異常値")
        
        if hasattr(indicator, 'volatility_index') and indicator.volatility_index and indicator.volatility_index > 20:
            notes.append("高ボラティリティ")
        
        if indicator.data_quality_score < 50:
            notes.append("データ品質注意")
        
        return ", ".join(notes) if notes else "正常"
    
    def _get_trend_notes(self, trend_result: TrendResult) -> str:
        """トレンドの備考を生成"""
        notes = []
        
        if trend_result.confidence_level < 50:
            notes.append("信頼度低")
        
        if trend_result.pattern_type.value != "パターンなし":
            notes.append(f"パターン検出: {trend_result.pattern_type.value}")
        
        return ", ".join(notes) if notes else "標準"
    
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
        
        # 高ボラティリティリスク
        high_vol_indicators = [
            ind for ind in indicators 
            if hasattr(ind, 'volatility_index') and ind.volatility_index and ind.volatility_index > 20
        ]
        
        if high_vol_indicators:
            risks.append({
                'type': '高ボラティリティ',
                'severity': '中',
                'indicator_count': len(high_vol_indicators),
                'description': f"{len(high_vol_indicators)}つの指標で高ボラティリティを検出",
                'recommended_action': '市場動向の継続監視',
                'monitoring_items': '価格変動、出来高'
            })
        
        # データ品質リスク
        low_quality = [ind for ind in indicators if ind.data_quality_score < 50]
        if len(low_quality) > len(indicators) * 0.3:
            risks.append({
                'type': 'データ品質低下',
                'severity': '中',
                'indicator_count': len(low_quality),
                'description': f"分析対象の{len(low_quality)}/{len(indicators)}指標でデータ品質が低下",
                'recommended_action': 'データソースの確認・更新',
                'monitoring_items': 'API接続状況、データ取得エラー'
            })
        
        return risks
    
    def _format_summary_sheet(self, spreadsheet_id: str):
        """サマリーシートの書式設定"""
        # 実装は省略（色分け、フォント設定など）
        pass
    
    def _format_indicators_sheet(self, spreadsheet_id: str):
        """指標詳細シートの書式設定"""
        # 実装は省略
        pass
    
    def _format_correlation_sheet(self, spreadsheet_id: str, matrix_size: int):
        """相関分析シートの書式設定"""
        # 実装は省略
        pass
    
    def _insert_chart_to_sheet(self, spreadsheet_id: str, sheet_name: str, cell_position: str, chart_file_path: str):
        """チャートをシートに挿入"""
        # 実装は省略（画像アップロードとシート挿入）
        pass
    
    def update_dashboard(self, indicators: List[ProcessedIndicator], trend_results: Optional[List[TrendResult]] = None):
        """ダッシュボードを更新"""
        if not self.dashboard_spreadsheet_id:
            logger.error("ダッシュボードが作成されていません")
            return False
        
        try:
            # 各シートを更新
            self._setup_summary_sheet(self.dashboard_spreadsheet_id, indicators)
            self._setup_indicators_sheet(self.dashboard_spreadsheet_id, indicators)
            self._setup_trend_analysis_sheet(self.dashboard_spreadsheet_id, indicators, trend_results)
            self._setup_correlation_sheet(self.dashboard_spreadsheet_id, indicators)
            self._setup_risk_assessment_sheet(self.dashboard_spreadsheet_id, indicators, trend_results)
            
            # 更新時刻を記録
            self._setup_auto_refresh(self.dashboard_spreadsheet_id)
            
            logger.info("ダッシュボードが更新されました")
            return True
            
        except Exception as e:
            logger.error(f"ダッシュボード更新エラー: {e}")
            return False
    
    def get_dashboard_url(self) -> Optional[str]:
        """ダッシュボードURLを取得"""
        if self.dashboard_spreadsheet_id:
            return f"https://docs.google.com/spreadsheets/d/{self.dashboard_spreadsheet_id}"
        return None
