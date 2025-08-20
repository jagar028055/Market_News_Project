# -*- coding: utf-8 -*-

"""
プロダクション版ポッドキャスト統合管理システム
10分完全版・高品質自動化システム
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.database.database_manager import DatabaseManager
from src.podcast.data_fetcher.enhanced_database_article_fetcher import EnhancedDatabaseArticleFetcher
from src.podcast.data_fetcher.google_document_data_fetcher import GoogleDocumentDataFetcher
from src.podcast.script_generation.professional_dialogue_script_generator import ProfessionalDialogueScriptGenerator
from src.podcast.integration.podcast_integration_manager import PodcastIntegrationManager
from src.config.app_config import AppConfig


class ProductionPodcastIntegrationManager:
    """プロダクション版ポッドキャスト統合管理クラス"""
    
    def __init__(self, config=None):
        """
        初期化
        
        Args:
            config: 設定オブジェクト（省略時は自動取得）
        """
        self.config = config or AppConfig()
        self.logger = logging.getLogger(__name__)
        
        # データソース設定
        self.data_source = os.getenv('PODCAST_DATA_SOURCE', 'database')  # database | google_document
        self.google_doc_id = os.getenv('GOOGLE_DOCUMENT_ID') or os.getenv('GOOGLE_OVERWRITE_DOC_ID')
        
        # 基本コンポーネント初期化
        if self.data_source == 'google_document' and self.google_doc_id:
            self.article_fetcher = GoogleDocumentDataFetcher(self.google_doc_id)
            self.logger.info(f"データソース: Googleドキュメント (ID: {self.google_doc_id})")
        else:
            # デフォルトはデータベース
            self.db_manager = DatabaseManager(self.config.database)
            self.article_fetcher = EnhancedDatabaseArticleFetcher(self.db_manager)
            self.logger.info("データソース: データベース")
        
        # Gemini 2.5 Pro台本生成器
        gemini_model = os.getenv('GEMINI_PODCAST_MODEL', 'gemini-2.5-pro-001')
        gemini_api_key = os.getenv('GEMINI_API_KEY') or getattr(self.config, 'gemini_api_key', None)
        
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY環境変数が設定されていません")
        
        self.script_generator = ProfessionalDialogueScriptGenerator(
            api_key=gemini_api_key,
            model_name=gemini_model
        )
        
        # 既存システム活用（音声生成・配信）
        self.base_manager = PodcastIntegrationManager(config=self.config)
        
        self.logger.info(f"プロダクション版ポッドキャスト統合マネージャー初期化完了 - モデル: {gemini_model}")
    
    def generate_complete_podcast(
        self,
        test_mode: bool = False,
        target_duration: float = None
    ) -> Dict[str, Any]:
        """
        完全版ポッドキャスト生成
        
        Args:
            test_mode: テストモード（実際の配信を行わない）
            target_duration: 目標配信時間（分）
            
        Returns:
            生成結果辞書
        """
        try:
            start_time = datetime.now()
            
            # 設定値取得
            target_duration = target_duration or float(os.getenv('PODCAST_TARGET_DURATION_MINUTES', '10.0'))
            production_mode = os.getenv('PODCAST_PRODUCTION_MODE', 'false').lower() == 'true'
            
            self.logger.info(
                f"プロダクション版ポッドキャスト生成開始 - "
                f"テストモード: {test_mode}, プロダクションモード: {production_mode}, "
                f"目標時間: {target_duration}分, データソース: {self.data_source}"
            )
            
            # Phase 1: 高度記事選択
            self.logger.info("Phase 1: 高度記事選択システム実行")
            articles = self.article_fetcher.fetch_articles_for_podcast(
                target_count=6,
                hours_back=24
            )
            
            if not articles:
                raise ValueError("選択可能な記事が見つかりません")
            
            self.logger.info(f"記事選択完了 - 選択数: {len(articles)}")
            
            # Phase 2: プロフェッショナル台本生成
            self.logger.info("Phase 2: Gemini 2.5 Pro による高品質台本生成")
            script_result = self.script_generator.generate_professional_script(
                articles=articles,
                target_duration=target_duration
            )
            
            # Phase 3: 音声生成・配信（既存システム活用）
            self.logger.info("Phase 3: 音声生成・配信システム実行")
            
            # 台本を一時保存
            script_content = script_result['script']
            temp_script_path = Path('temp_podcast_script.txt')
            with open(temp_script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            try:
                # 既存の音声生成・配信システムを使用
                broadcast_result = self.base_manager.run_daily_podcast_workflow(
                    test_mode=test_mode,
                    custom_script_path=str(temp_script_path)
                )
                
            finally:
                # 一時ファイル削除
                if temp_script_path.exists():
                    temp_script_path.unlink()
            
            # 結果統合
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # 記事統計取得
            article_stats = self.article_fetcher.get_article_statistics(hours_back=24)
            
            result = {
                'success': broadcast_result,
                'production_mode': production_mode,
                'test_mode': test_mode,
                'script_generation': script_result,
                'articles_analysis': {
                    'selected_count': len(articles),
                    'data_source': self.data_source,
                    'article_scores': [
                        {
                            'title': a.article.title[:100],
                            'score': a.score,
                            'category': getattr(a.analysis, 'category', 'その他'),
                            'region': getattr(a.analysis, 'region', 'other'),
                            'source': getattr(a.article, 'source', 'Unknown')
                        } for a in articles
                    ]
                },
                'system_metrics': {
                    'total_processing_time_seconds': processing_time,
                    'script_generation_model': script_result.get('generation_model'),
                    'database_statistics': article_stats
                },
                'quality_assessment': {
                    'script_char_count': script_result.get('char_count'),
                    'estimated_duration_minutes': script_result.get('estimated_duration'),
                    'quality_score': script_result.get('quality_score'),
                    'quality_details': script_result.get('quality_details')
                },
                'generated_at': start_time.isoformat(),
                'completed_at': end_time.isoformat()
            }
            
            # 品質レポート出力
            self._generate_quality_report(result)
            
            if broadcast_result:
                self.logger.info(
                    f"プロダクション版ポッドキャスト生成完了 - "
                    f"処理時間: {processing_time:.1f}秒, "
                    f"品質スコア: {script_result.get('quality_score', 0):.2f}"
                )
            else:
                self.logger.error("プロダクション版ポッドキャスト生成に失敗しました")
            
            return result
            
        except Exception as e:
            self.logger.error(f"プロダクション版ポッドキャスト生成エラー: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'generated_at': datetime.now().isoformat()
            }
    
    def run_daily_podcast_workflow(self, test_mode: bool = False) -> bool:
        """
        日次ポッドキャストワークフロー実行
        
        Args:
            test_mode: テストモード
            
        Returns:
            成功可否
        """
        try:
            result = self.generate_complete_podcast(test_mode=test_mode)
            return result.get('success', False)
            
        except Exception as e:
            self.logger.error(f"日次ワークフローエラー: {e}", exc_info=True)
            return False
    
    def _generate_quality_report(self, result: Dict[str, Any]) -> None:
        """品質レポート生成"""
        try:
            report_lines = [
                "=== プロダクション版ポッドキャスト品質レポート ===",
                f"生成日時: {result['generated_at']}",
                f"完了日時: {result['completed_at']}",
                f"処理時間: {result['system_metrics']['total_processing_time_seconds']:.1f}秒",
                "",
                "## 台本品質",
                f"文字数: {result['quality_assessment']['script_char_count']}文字",
                f"推定再生時間: {result['quality_assessment']['estimated_duration_minutes']:.1f}分",
                f"品質スコア: {result['quality_assessment']['quality_score']:.2f}/1.0",
                "",
                "## 記事選択",
                f"選択記事数: {result['articles_analysis']['selected_count']}",
                "カテゴリ分布:"
            ]
            
            # カテゴリ分布
            category_count = {}
            for article in result['articles_analysis']['article_scores']:
                cat = article['category']
                category_count[cat] = category_count.get(cat, 0) + 1
            
            for category, count in category_count.items():
                report_lines.append(f"  - {category}: {count}記事")
            
            # 地域分布
            region_count = {}
            for article in result['articles_analysis']['article_scores']:
                region = article['region']
                region_count[region] = region_count.get(region, 0) + 1
            
            report_lines.append("\n地域分布:")
            for region, count in region_count.items():
                report_lines.append(f"  - {region}: {count}記事")
            
            # データベース統計
            db_stats = result['system_metrics']['database_statistics']
            if db_stats:
                report_lines.extend([
                    "",
                    "## データベース統計",
                    f"総記事数: {db_stats.get('total_articles', 0)}",
                    f"分析済記事数: {db_stats.get('analyzed_articles', 0)}",
                    f"分析率: {db_stats.get('analysis_rate', 0):.1%}"
                ])
            
            report_lines.append("\n" + "="*50)
            
            # レポート出力
            report_content = "\n".join(report_lines)
            self.logger.info(f"品質レポート:\n{report_content}")
            
            # ファイル保存
            report_path = Path('logs') / f"podcast_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            report_path.parent.mkdir(exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            self.logger.info(f"品質レポートをファイルに保存: {report_path}")
            
        except Exception as e:
            self.logger.error(f"品質レポート生成エラー: {e}", exc_info=True)
    
    def get_system_status(self) -> Dict[str, Any]:
        """システム状態取得"""
        try:
            # データベース接続確認（データベース使用時のみ）
            db_status = True
            if self.data_source == 'database' and hasattr(self, 'db_manager'):
                try:
                    with self.db_manager.get_session() as session:
                        session.execute("SELECT 1")
                except Exception:
                    db_status = False
            
            # 記事統計
            article_stats = self.article_fetcher.get_article_statistics(hours_back=24)
            
            # 設定確認
            gemini_model = os.getenv('GEMINI_PODCAST_MODEL', 'gemini-2.5-pro-001')
            production_mode = os.getenv('PODCAST_PRODUCTION_MODE', 'false').lower() == 'true'
            
            return {
                'system_healthy': db_status,
                'database_connected': db_status,
                'data_source': self.data_source,
                'google_document_id': self.google_doc_id if self.data_source == 'google_document' else None,
                'article_statistics': article_stats,
                'configuration': {
                    'gemini_model': gemini_model,
                    'production_mode': production_mode,
                    'target_duration': float(os.getenv('PODCAST_TARGET_DURATION_MINUTES', '10.0')),
                    'target_script_chars': int(os.getenv('PODCAST_TARGET_SCRIPT_CHARS', '2700'))
                },
                'checked_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"システム状態取得エラー: {e}", exc_info=True)
            return {
                'system_healthy': False,
                'error': str(e),
                'checked_at': datetime.now().isoformat()
            }