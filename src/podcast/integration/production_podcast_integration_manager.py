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
from src.database.models import Article, AIAnalysis
from src.podcast.data_fetcher.enhanced_database_article_fetcher import EnhancedDatabaseArticleFetcher
from src.podcast.script_generation.professional_dialogue_script_generator import ProfessionalDialogueScriptGenerator
from src.podcast.audio_generation.google_cloud_tts_engine import GoogleCloudTTSEngine
from src.podcast.publisher.github_pages_publisher import GitHubPagesPublisher
from src.podcast.integration.line_broadcaster import LineBroadcaster
from config.base import Config, DatabaseConfig, TTSConfig, GitHubConfig, LineConfig
from src.logging_config import get_logger, log_with_context


class ProductionPodcastIntegrationManager:
    """プロダクション版ポッドキャスト統合管理クラス"""
    
    def __init__(self, config: Config):
        """
        初期化
        
        Args:
            config: 設定オブジェクト
        """
        self.config = config
        self.logger = get_logger("production_podcast_manager")
        
        # 各コンポーネント初期化
        self.db_manager = DatabaseManager(config.database)
        self.article_fetcher = EnhancedDatabaseArticleFetcher(self.db_manager)
        
        # Gemini 2.5 Pro台本生成器（設定から取得）
        gemini_model = os.getenv('GEMINI_PODCAST_MODEL', 'gemini-2.0-flash-lite-001')
        self.script_generator = ProfessionalDialogueScriptGenerator(
            api_key=config.gemini.api_key,
            model_name=gemini_model
        )
        
        # 音声生成・配信システム
        self.tts_engine = GoogleCloudTTSEngine(config.tts)
        self.github_publisher = GitHubPagesPublisher(config.github)
        self.line_broadcaster = LineBroadcaster(config.line)
        
        # プロダクション設定
        self.is_production_mode = not config.podcast.test_mode
        self.target_length_minutes = 10
        self.target_character_count = (2600, 2800)
        
        log_with_context(
            self.logger, logging.INFO, "プロダクション版ポッドキャスト管理システム初期化完了",
            operation="init",
            production_mode=self.is_production_mode,
            gemini_model=gemini_model,
            target_minutes=self.target_length_minutes
        )
    
    def generate_complete_podcast(
        self,
        hours_lookback: int = 24,
        max_articles: int = 6,
        test_mode: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        完全版ポッドキャスト生成・配信
        
        Args:
            hours_lookback: 記事取得時間範囲
            max_articles: 最大記事数
            test_mode: テストモード（Noneの場合は設定値使用）
            
        Returns:
            実行結果辞書
        """
        # テストモード判定
        actual_test_mode = test_mode if test_mode is not None else not self.is_production_mode
        
        log_with_context(
            self.logger, logging.INFO, "完全版ポッドキャスト生成開始",
            operation="generate_complete_podcast",
            test_mode=actual_test_mode,
            hours_lookback=hours_lookback,
            max_articles=max_articles
        )
        
        try:
            # Phase 1: 高品質記事選択
            selected_articles = self._select_high_quality_articles(
                hours_lookback, max_articles
            )
            
            if not selected_articles:
                return self._create_error_result("記事データが見つかりません")
            
            # Phase 2: プロ版台本生成
            script_content = self._generate_professional_script(selected_articles)
            
            # Phase 3: 高品質音声生成
            audio_result = self._generate_professional_audio(
                script_content, actual_test_mode
            )
            
            # Phase 4: GitHub Pages配信
            publish_result = self._publish_to_github_pages(
                audio_result, actual_test_mode
            )
            
            # Phase 5: LINE配信
            line_result = self._broadcast_to_line(
                publish_result, selected_articles, actual_test_mode
            )
            
            # 結果統合
            complete_result = self._compile_complete_result(
                selected_articles, script_content, audio_result,
                publish_result, line_result, actual_test_mode
            )
            
            log_with_context(
                self.logger, logging.INFO, "完全版ポッドキャスト生成完了",
                operation="generate_complete_podcast",
                success=complete_result['success'],
                script_length=len(script_content),
                audio_duration_seconds=audio_result.get('duration_seconds', 0),
                line_broadcast_success=line_result.get('success', False)
            )
            
            return complete_result
            
        except Exception as e:
            error_msg = f"完全版ポッドキャスト生成エラー: {e}"
            self.logger.error(error_msg)
            return self._create_error_result(error_msg)
    
    def _select_high_quality_articles(self, hours: int, max_articles: int) -> List[Dict[str, Any]]:
        """
        高品質記事選択
        
        Args:
            hours: 取得時間範囲
            max_articles: 最大記事数
            
        Returns:
            選択された記事リスト
        """
        log_with_context(
            self.logger, logging.INFO, "高品質記事選択開始",
            operation="select_articles",
            hours=hours,
            max_articles=max_articles
        )
        
        try:
            # バランス取れた記事選択を実行
            articles = self.article_fetcher.get_balanced_article_selection(
                hours=hours,
                max_articles=max_articles
            )
            
            # 品質検証
            validated_articles = self._validate_article_quality(articles)
            
            log_with_context(
                self.logger, logging.INFO, "高品質記事選択完了",
                operation="select_articles",
                selected_count=len(validated_articles),
                avg_importance=sum(a.get('importance_score', 0) for a in validated_articles) / len(validated_articles) if validated_articles else 0
            )
            
            return validated_articles
            
        except Exception as e:
            self.logger.error(f"記事選択エラー: {e}")
            raise
    
    def _validate_article_quality(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """記事品質検証"""
        validated = []
        
        for article in articles:
            # 必須フィールド検証
            if not article.get('title') or not article.get('summary'):
                continue
                
            # AI分析データ検証
            if not article.get('has_ai_analysis'):
                continue
                
            # 重要度スコア検証
            if article.get('importance_score', 0) < 2.0:
                continue
                
            validated.append(article)
        
        return validated
    
    def _generate_professional_script(self, articles: List[Dict[str, Any]]) -> str:
        """
        プロ版台本生成
        
        Args:
            articles: 記事データ
            
        Returns:
            生成台本
        """
        log_with_context(
            self.logger, logging.INFO, "プロ版台本生成開始",
            operation="generate_script",
            articles_count=len(articles),
            model_name=self.script_generator.model_name
        )
        
        try:
            script = self.script_generator.generate_professional_script(articles)
            
            # 品質メトリクス
            char_count = len(script)
            target_min, target_max = self.target_character_count
            quality_score = self._calculate_script_quality_score(script, articles)
            
            log_with_context(
                self.logger, logging.INFO, "プロ版台本生成完了",
                operation="generate_script",
                script_length=char_count,
                target_range=f"{target_min}-{target_max}",
                quality_score=quality_score,
                meets_length_target=target_min <= char_count <= target_max
            )
            
            return script
            
        except Exception as e:
            self.logger.error(f"台本生成エラー: {e}")
            raise
    
    def _calculate_script_quality_score(self, script: str, articles: List[Dict[str, Any]]) -> float:
        """台本品質スコア計算"""
        score = 0.0
        
        # 長さスコア（40%）
        char_count = len(script)
        target_min, target_max = self.target_character_count
        if target_min <= char_count <= target_max:
            score += 40.0
        else:
            ratio = min(char_count / target_min, target_max / char_count) if char_count > 0 else 0
            score += 40.0 * ratio
        
        # 記事カバレッジスコア（30%）
        article_titles_mentioned = sum(
            1 for article in articles 
            if article.get('title', '')[:20] in script
        )
        coverage_ratio = article_titles_mentioned / len(articles) if articles else 0
        score += 30.0 * coverage_ratio
        
        # プロ表現スコア（30%）
        professional_terms = ['について', 'ございます', 'と思われます', '見込まれます']
        professional_count = sum(1 for term in professional_terms if term in script)
        professional_score = min(professional_count / 4, 1.0)
        score += 30.0 * professional_score
        
        return round(score, 1)
    
    def _generate_professional_audio(self, script: str, test_mode: bool) -> Dict[str, Any]:
        """
        プロ版音声生成
        
        Args:
            script: 台本
            test_mode: テストモード
            
        Returns:
            音声生成結果
        """
        log_with_context(
            self.logger, logging.INFO, "プロ版音声生成開始",
            operation="generate_audio",
            script_length=len(script),
            test_mode=test_mode
        )
        
        try:
            # ファイル名生成（プロダクション vs テスト）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if test_mode:
                filename = f"test_market_news_{timestamp}.mp3"
            else:
                filename = f"market_news_{datetime.now().strftime('%Y%m%d')}.mp3"
            
            # 高品質音声生成
            audio_result = self.tts_engine.generate_audio(
                text=script,
                output_filename=filename,
                voice_settings={
                    'language_code': 'ja-JP',
                    'name': 'ja-JP-Standard-A',
                    'ssml_gender': 'FEMALE'
                },
                audio_config={
                    'audio_encoding': 'MP3',
                    'sample_rate_hertz': 24000,
                    'speaking_rate': 1.0,
                    'pitch': 0.0
                }
            )
            
            log_with_context(
                self.logger, logging.INFO, "プロ版音声生成完了",
                operation="generate_audio",
                filename=filename,
                file_size_mb=audio_result.get('file_size_mb', 0),
                duration_seconds=audio_result.get('duration_seconds', 0)
            )
            
            return audio_result
            
        except Exception as e:
            self.logger.error(f"音声生成エラー: {e}")
            raise
    
    def _publish_to_github_pages(self, audio_result: Dict[str, Any], test_mode: bool) -> Dict[str, Any]:
        """
        GitHub Pages配信
        
        Args:
            audio_result: 音声生成結果
            test_mode: テストモード
            
        Returns:
            配信結果
        """
        log_with_context(
            self.logger, logging.INFO, "GitHub Pages配信開始",
            operation="publish_github",
            filename=audio_result.get('filename'),
            test_mode=test_mode
        )
        
        try:
            publish_result = self.github_publisher.publish_podcast_file(
                local_audio_path=audio_result['file_path'],
                test_mode=test_mode
            )
            
            log_with_context(
                self.logger, logging.INFO, "GitHub Pages配信完了",
                operation="publish_github",
                success=publish_result.get('success', False),
                public_url=publish_result.get('public_url', ''),
                github_pages_url=publish_result.get('github_pages_url', '')
            )
            
            return publish_result
            
        except Exception as e:
            self.logger.error(f"GitHub Pages配信エラー: {e}")
            raise
    
    def _broadcast_to_line(
        self, 
        publish_result: Dict[str, Any], 
        articles: List[Dict[str, Any]], 
        test_mode: bool
    ) -> Dict[str, Any]:
        """
        LINE配信
        
        Args:
            publish_result: 配信結果
            articles: 記事データ
            test_mode: テストモード
            
        Returns:
            LINE配信結果
        """
        log_with_context(
            self.logger, logging.INFO, "LINE配信開始",
            operation="broadcast_line",
            test_mode=test_mode,
            articles_count=len(articles)
        )
        
        try:
            # メッセージ内容構築
            message_content = self._build_line_message_content(
                publish_result, articles, test_mode
            )
            
            # LINE配信実行
            line_result = self.line_broadcaster.broadcast_podcast_to_line(
                podcast_url=publish_result.get('public_url', ''),
                articles_summary=message_content,
                test_mode=test_mode
            )
            
            log_with_context(
                self.logger, logging.INFO, "LINE配信完了",
                operation="broadcast_line",
                success=line_result.get('success', False),
                message_length=len(message_content)
            )
            
            return line_result
            
        except Exception as e:
            self.logger.error(f"LINE配信エラー: {e}")
            raise
    
    def _build_line_message_content(
        self, 
        publish_result: Dict[str, Any], 
        articles: List[Dict[str, Any]], 
        test_mode: bool
    ) -> str:
        """LINE配信メッセージ内容構築"""
        
        # ヘッダー
        if test_mode:
            header = "🧪【テスト配信】マーケットニュースポッドキャスト"
        else:
            header = "📻【本日のマーケットニュース】10分完全版"
        
        # 日時情報
        today = datetime.now().strftime("%Y年%m月%d日")
        time_info = f"📅 {today} 配信"
        
        # 音声情報
        duration = publish_result.get('duration_seconds', 0)
        duration_min = f"{duration // 60}分{duration % 60:02d}秒" if duration > 0 else "約10分"
        audio_info = f"🎧 音声時間: {duration_min}"
        
        # 記事サマリー
        article_summary = "📰 今日の主要トピック:\\n"
        for i, article in enumerate(articles[:4], 1):
            category = article.get('category', '市場')
            region = article.get('region', '')
            region_flag = {'usa': '🇺🇸', 'japan': '🇯🇵', 'china': '🇨🇳', 'europe': '🇪🇺'}.get(region, '🌍')
            title_short = article.get('title', '')[:30] + '...' if len(article.get('title', '')) > 30 else article.get('title', '')
            
            article_summary += f"{i}. {region_flag} {title_short}\\n"
        
        # フッター
        if test_mode:
            footer = "\\n⚠️ これはテスト配信です\\n🔍 品質確認用"
        else:
            footer = "\\n💼 投資判断の参考にお役立てください\\n📈 #MarketNews #投資情報"
        
        # 最終組み立て
        message_parts = [
            header,
            time_info,
            audio_info,
            "",
            article_summary,
            footer
        ]
        
        return "\\n".join(message_parts)
    
    def _compile_complete_result(
        self,
        articles: List[Dict[str, Any]],
        script: str,
        audio_result: Dict[str, Any],
        publish_result: Dict[str, Any],
        line_result: Dict[str, Any],
        test_mode: bool
    ) -> Dict[str, Any]:
        """完全実行結果コンパイル"""
        
        success = all([
            len(articles) > 0,
            len(script) >= 2000,
            audio_result.get('success', False),
            publish_result.get('success', False),
            line_result.get('success', False)
        ])
        
        result = {
            'success': success,
            'test_mode': test_mode,
            'timestamp': datetime.now().isoformat(),
            'execution_summary': {
                'articles_selected': len(articles),
                'script_length': len(script),
                'audio_duration_seconds': audio_result.get('duration_seconds', 0),
                'file_size_mb': audio_result.get('file_size_mb', 0),
                'public_url': publish_result.get('public_url', ''),
                'line_broadcast_success': line_result.get('success', False)
            },
            'quality_metrics': {
                'script_quality_score': self._calculate_script_quality_score(script, articles),
                'article_importance_avg': sum(a.get('importance_score', 0) for a in articles) / len(articles) if articles else 0,
                'category_diversity': len(set(a.get('category', 'other') for a in articles)),
                'region_diversity': len(set(a.get('region', 'other') for a in articles))
            },
            'detailed_results': {
                'articles': articles,
                'script_content': script,
                'audio_result': audio_result,
                'publish_result': publish_result,
                'line_result': line_result
            }
        }
        
        return result
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """エラー結果作成"""
        return {
            'success': False,
            'error': error_message,
            'timestamp': datetime.now().isoformat(),
            'execution_summary': {
                'articles_selected': 0,
                'script_length': 0,
                'audio_duration_seconds': 0,
                'file_size_mb': 0,
                'public_url': '',
                'line_broadcast_success': False
            }
        }
    
    def get_production_statistics(self) -> Dict[str, Any]:
        """プロダクション統計取得"""
        try:
            db_stats = self.article_fetcher.get_database_statistics(hours=24)
            
            stats = {
                'database_status': db_stats,
                'system_status': {
                    'production_mode': self.is_production_mode,
                    'gemini_model': self.script_generator.model_name,
                    'target_duration_minutes': self.target_length_minutes,
                    'target_character_range': self.target_character_count
                },
                'timestamp': datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"統計取得エラー: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}