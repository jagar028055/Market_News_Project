# -*- coding: utf-8 -*-

"""
ポッドキャスト統合管理クラス
メインのニュース処理システムとポッドキャスト生成・LINE配信を統合
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging
import pytz

from src.config.app_config import AppConfig
from src.podcast.script_generation.dialogue_script_generator import DialogueScriptGenerator
from src.podcast.tts.gemini_tts_engine import GeminiTTSEngine
from src.podcast.audio.audio_processor import AudioProcessor
from src.podcast.integration.line_broadcaster import LineBroadcaster
from src.podcast.integration.exceptions import PodcastConfigurationError, CostLimitExceededError
from src.podcast.publisher.github_pages_publisher import GitHubPagesPublisher


class PodcastIntegrationManager:
    """
    ポッドキャスト統合管理クラス
    
    ニュース処理システムとポッドキャスト生成・LINE配信を統合し、
    設定チェック、コスト管理、エラーハンドリングを提供
    """
    
    def __init__(self, config: AppConfig, logger: logging.Logger):
        """
        初期化
        
        Args:
            config: アプリケーション設定
            logger: ロガー
        """
        self.config = config
        self.logger = logger
        self.line_broadcaster = LineBroadcaster(config, logger)
        self.github_publisher = GitHubPagesPublisher(config, logger)
        
        # ポッドキャスト生成コンポーネント
        self.script_generator = None
        self.tts_engine = None
        self.audio_processor = None
        
    def is_podcast_enabled(self) -> bool:
        """
        ポッドキャスト機能が有効かチェック
        
        Returns:
            bool: ポッドキャスト機能が有効な場合True
        """
        # 環境変数でのポッドキャスト有効化チェック
        enabled = os.getenv('ENABLE_PODCAST_GENERATION', '').lower() == 'true'
        
        if not enabled:
            self.logger.info("ポッドキャスト生成が無効化されています (ENABLE_PODCAST_GENERATION != 'true')")
            return False
            
        return True
    
    def check_configuration(self) -> bool:
        """
        ポッドキャスト設定の妥当性をチェック
        
        Returns:
            bool: 設定が有効な場合True
            
        Raises:
            PodcastConfigurationError: 設定が無効な場合
        """
        errors = []
        
        # Gemini API キーチェック
        if not self.config.ai.gemini_api_key:
            errors.append("GEMINI_API_KEY が設定されていません")
        
        # LINE設定チェック
        if not self.config.line.is_configured():
            errors.append("LINE設定が不完全です (LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET)")
        
        # ポッドキャスト基本設定チェック
        if not self.config.podcast.rss_base_url:
            errors.append("PODCAST_RSS_BASE_URL が設定されていません")
        
        if not self.config.podcast.author_name:
            errors.append("PODCAST_AUTHOR_NAME が設定されていません")
        
        if not self.config.podcast.author_email:
            errors.append("PODCAST_AUTHOR_EMAIL が設定されていません")
        
        # 音声アセットディレクトリチェック
        assets_dir = Path("src/podcast/assets")
        if not assets_dir.exists():
            errors.append(f"音声アセットディレクトリが存在しません: {assets_dir}")
        
        if errors:
            error_msg = "ポッドキャスト設定エラー: " + ", ".join(errors)
            raise PodcastConfigurationError(error_msg)
        
        self.logger.info("ポッドキャスト設定チェック完了")
        return True
    
    def check_cost_limits(self) -> bool:
        """
        月間コスト制限をチェック
        
        Returns:
            bool: コスト制限内の場合True
            
        Raises:
            CostLimitExceededError: コスト制限を超過している場合
        """
        # TODO: 実際のコスト追跡システムと連携
        # 現在は簡易実装として常にTrue
        
        monthly_limit = self.config.podcast.monthly_cost_limit_usd
        self.logger.info(f"月間コスト制限チェック (制限: ${monthly_limit})")
        
        # 実際の実装では、データベースから今月の使用量を取得
        # current_usage = self.get_monthly_usage()
        # if current_usage >= monthly_limit:
        #     raise CostLimitExceededError(f"月間コスト制限を超過: ${current_usage} >= ${monthly_limit}")
        
        return True
    
    def _initialize_components(self):
        """ポッドキャスト生成コンポーネントを初期化"""
        if not self.script_generator:
            self.script_generator = DialogueScriptGenerator(self.config.ai.gemini_api_key)
        
        if not self.tts_engine:
            self.tts_engine = GeminiTTSEngine(self.config.ai.gemini_api_key)
        
        if not self.audio_processor:
            self.audio_processor = AudioProcessor('src/podcast/assets')
    
    def generate_podcast_from_articles(self, articles: List[Dict[str, Any]]) -> Optional[str]:
        """
        記事からポッドキャストを生成
        
        Args:
            articles: ニュース記事のリスト
            
        Returns:
            Optional[str]: 生成されたポッドキャストファイルのパス（失敗時はNone）
        """
        if not articles:
            self.logger.warning("ポッドキャスト生成対象の記事がありません")
            return None
        
        try:
            self.logger.info(f"ポッドキャスト生成開始 (記事数: {len(articles)})")
            
            # コンポーネント初期化
            self._initialize_components()
            
            # 記事をポッドキャスト用に変換
            podcast_articles = self._prepare_articles_for_podcast(articles)
            
            # 台本生成
            self.logger.info("台本生成中...")
            script = self.script_generator.generate_script(podcast_articles)
            self.logger.info(f"台本生成完了 ({len(script)}文字)")
            
            # 音声合成
            self.logger.info("音声合成中...")
            audio_data = self.tts_engine.synthesize_dialogue(script)
            self.logger.info(f"音声合成完了 ({len(audio_data)}バイト)")
            
            # 音声処理
            self.logger.info("音声処理中...")
            episode_id = f"episode_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            audio_path = self.audio_processor.process_audio(audio_data, episode_id)
            self.logger.info(f"ポッドキャスト生成完了: {audio_path}")
            
            return audio_path
            
        except Exception as e:
            self.logger.error(f"ポッドキャスト生成エラー: {e}", exc_info=True)
            return None
    
    def _prepare_articles_for_podcast(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        記事をポッドキャスト生成用に変換
        
        Args:
            articles: 元の記事データ
            
        Returns:
            List[Dict[str, Any]]: ポッドキャスト用記事データ
        """
        podcast_articles = []
        
        for article in articles:
            # 必要な情報を抽出・変換
            podcast_article = {
                'title': article.get('title', ''),
                'summary': article.get('summary', ''),
                'sentiment': self._convert_sentiment(article.get('sentiment_label', 'Neutral')),
                'url': article.get('url', ''),
                'source': article.get('source', ''),
                'published_at': self._format_published_date(article.get('published_jst'))
            }
            
            # 要約がある記事のみを対象
            if podcast_article['summary'] and podcast_article['summary'] != '要約はありません。':
                podcast_articles.append(podcast_article)
        
        self.logger.info(f"ポッドキャスト用記事準備完了 ({len(podcast_articles)}/{len(articles)}件)")
        return podcast_articles
    
    def _convert_sentiment(self, sentiment_label: str) -> str:
        """
        センチメントラベルをポッドキャスト用に変換
        
        Args:
            sentiment_label: 元のセンチメントラベル
            
        Returns:
            str: 変換されたセンチメント
        """
        sentiment_map = {
            'Positive': 'positive',
            'Negative': 'negative',
            'Neutral': 'neutral'
        }
        return sentiment_map.get(sentiment_label, 'neutral')
    
    def _format_published_date(self, published_jst) -> str:
        """
        公開日時をISO形式に変換
        
        Args:
            published_jst: 公開日時（様々な形式）
            
        Returns:
            str: ISO形式の日時文字列
        """
        if not published_jst:
            return datetime.now().isoformat()
        
        # datetimeオブジェクトの場合
        if hasattr(published_jst, 'isoformat'):
            return published_jst.isoformat()
        
        # 文字列の場合はそのまま返す（既にISO形式と仮定）
        return str(published_jst)
    
    def broadcast_podcast_to_line(self, podcast_path: str, articles: List[Dict[str, Any]]) -> bool:
        """
        ポッドキャストをLINEで配信
        
        Args:
            podcast_path: ポッドキャストファイルのパス
            articles: 元の記事データ（メッセージ作成用）
            
        Returns:
            bool: 配信成功時True
        """
        if not podcast_path or not Path(podcast_path).exists():
            self.logger.error(f"ポッドキャストファイルが存在しません: {podcast_path}")
            return False
        
        try:
            # ファイル情報を取得
            file_path = Path(podcast_path)
            file_size_mb = file_path.stat().st_size / 1024 / 1024
            
            # JST時刻でエピソード情報を作成
            jst = pytz.timezone('Asia/Tokyo')
            now_jst = datetime.now(jst)
            
            episode_info = {
                'file_path': podcast_path,
                'file_size_mb': file_size_mb,
                'article_count': len(articles),
                'published_at': now_jst
            }
            
            # GitHub Pages に配信
            self.logger.info("GitHub Pages へのポッドキャスト配信開始")
            audio_url = self.github_publisher.publish_podcast_episode(podcast_path, episode_info)
            
            if audio_url:
                self.logger.info(f"GitHub Pages 配信成功: {audio_url}")
                
                # RSS フィード生成
                self.logger.info("RSSフィード生成開始")
                self.logger.info(f"エピソード情報: {episode_info}")
                self.logger.info(f"音声URL: {audio_url}")
                
                try:
                    episode_data = {
                        'title': f"マーケットニュース {episode_info['published_at'].strftime('%Y年%m月%d日')}",
                        'description': f"本日のマーケットニュースポッドキャスト（{episode_info['article_count']}件の記事を解説）",
                        'url': audio_url,
                        'audio_url': audio_url,
                        'published_at': episode_info['published_at'],
                        'file_size': int(episode_info['file_size_mb'] * 1024 * 1024)  # バイト単位に変換
                    }
                    
                    self.logger.info(f"RSS用エピソードデータ: {episode_data}")
                    
                    rss_success = self.github_publisher.generate_rss_feed([episode_data])
                    if rss_success:
                        self.logger.info("✅ RSSフィード生成成功")
                        # RSS ファイルの存在確認
                        rss_path = Path("output/podcast/feed.xml")
                        if rss_path.exists():
                            self.logger.info(f"✅ RSSファイル確認成功: {rss_path} ({rss_path.stat().st_size}バイト)")
                        else:
                            self.logger.error(f"❌ RSSファイルが見つかりません: {rss_path}")
                    else:
                        self.logger.error("❌ RSSフィード生成失敗")
                        
                except Exception as e:
                    self.logger.error(f"❌ RSSフィード生成エラー: {e}", exc_info=True)
            else:
                self.logger.warning("GitHub Pages 配信失敗、音声URLなしでLINE配信を続行")
            
            # LINE配信実行（音声URLを含める）
            return self.line_broadcaster.broadcast_podcast_notification(episode_info, articles, audio_url)
            
        except Exception as e:
            self.logger.error(f"LINE配信エラー: {e}", exc_info=True)
            return False
    
    def cleanup_old_podcast_files(self, days_to_keep: int = 7) -> None:
        """
        古いポッドキャストファイルをクリーンアップ
        
        Args:
            days_to_keep: 保持する日数
        """
        try:
            output_dir = Path("output/podcast")
            if not output_dir.exists():
                return
            
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            deleted_count = 0
            
            for file_path in output_dir.glob("*.mp3"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
                    self.logger.debug(f"古いポッドキャストファイルを削除: {file_path}")
            
            if deleted_count > 0:
                self.logger.info(f"古いポッドキャストファイルクリーンアップ完了 ({deleted_count}件削除)")
                
        except Exception as e:
            self.logger.warning(f"ポッドキャストファイルクリーンアップエラー: {e}")