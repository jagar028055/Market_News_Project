# -*- coding: utf-8 -*-

import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from config.base import DatabaseConfig
from .models import Base, Article, AIAnalysis, ScrapingSession, ProcessingStats
from .url_normalizer import URLNormalizer
from .content_deduplicator import ContentDeduplicator
from src.error_handling import DatabaseError, retry_with_backoff
from src.logging_config import get_logger, log_with_context


class DatabaseManager:
    """データベース管理クラス"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.logger = get_logger("database")
        self.engine = create_engine(
            config.url,
            echo=config.echo,
            pool_pre_ping=True,  # 接続の健全性チェック
            pool_recycle=300     # 5分でコネクションをリサイクル
        )
        
        # テーブル作成
        Base.metadata.create_all(self.engine)
        
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.url_normalizer = URLNormalizer()
        self.content_deduplicator = ContentDeduplicator()
        
        log_with_context(
            self.logger, logging.INFO, "データベース初期化完了",
            operation="database_init",
            database_url=config.url
        )
    
    @contextmanager
    def get_session(self):
        """データベースセッション取得（コンテキストマネージャー）"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"データベースセッションエラー: {e}")
            raise DatabaseError(f"Database session error: {e}")
        finally:
            session.close()
    
    @retry_with_backoff(max_retries=3, exceptions=(SQLAlchemyError,))
    def save_article(self, article_data: Dict[str, Any]) -> Tuple[Optional[int], bool]:
        """
        記事保存（重複チェック付き）
        
        Args:
            article_data: 記事データ辞書
        
        Returns:
            (保存された記事ID, 新規作成フラグ)
        """
        with self.get_session() as session:
            try:
                normalized_url = self.url_normalizer.normalize_url(article_data['url'])
                url_hash = hashlib.sha256(normalized_url.encode('utf-8')).hexdigest()
                
                existing = session.query(Article).filter_by(url_hash=url_hash).first()
                if existing:
                    return existing.id, False
                
                content_hash = None
                if article_data.get('body'):
                    content_hash = self.content_deduplicator.generate_content_hash(article_data['body'])
                
                article = Article(
                    url=article_data['url'],
                    url_hash=url_hash,
                    title=article_data['title'],
                    body=article_data.get('body', ''),
                    source=article_data['source'],
                    category=article_data.get('category'),
                    published_at=article_data.get('published_jst'),
                    content_hash=content_hash
                )
                
                session.add(article)
                session.flush()
                
                article_id = article.id
                
                log_with_context(self.logger, logging.INFO, "新規記事保存完了",
                                 operation="save_article", article_id=article_id)
                
                return article_id, True
                
            except IntegrityError:
                session.rollback()
                existing = session.query(Article).filter_by(url_hash=url_hash).first()
                return existing.id if existing else None, False

    def get_articles_by_ids(self, article_ids: List[int]) -> List[Article]:
        """IDリストで記事を取得"""
        if not article_ids:
            return []
        with self.get_session() as session:
            articles = session.query(Article).filter(Article.id.in_(article_ids)).all()
            # セッションから明示的に切り離して返す
            for article in articles:
                session.expunge(article)
            return articles

    def get_recent_articles_with_analysis(self, hours: int = 24) -> List[Article]:
        """AI分析結果を含む最新記事を取得"""
        with self.get_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            articles = session.query(Article).join(AIAnalysis).filter(
                Article.published_at >= cutoff_time
            ).order_by(desc(Article.published_at)).all()
            # セッションから明示的に切り離して返す
            for article in articles:
                session.expunge(article)
            return articles

    def get_recent_articles_all(self, hours: int = 24) -> List[Article]:
        """最新記事を全て取得（AI分析の有無に関わらず）"""
        with self.get_session() as session:
            from sqlalchemy.orm import joinedload
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            articles = session.query(Article).options(
                joinedload(Article.ai_analysis)
            ).filter(
                Article.published_at >= cutoff_time
            ).order_by(desc(Article.published_at)).all()
            # セッションから明示的に切り離して返す
            for article in articles:
                session.expunge(article)
            return articles
    
    def get_article_by_url_with_analysis(self, url: str) -> Optional[Article]:
        """URLから記事を検索し、AI分析結果も含めて取得"""
        with self.get_session() as session:
            from sqlalchemy.orm import joinedload
            normalized_url = self.url_normalizer.normalize_url(url)
            url_hash = hashlib.sha256(normalized_url.encode('utf-8')).hexdigest()
            
            article = session.query(Article).options(
                joinedload(Article.ai_analysis)
            ).filter_by(url_hash=url_hash).first()
            
            if article:
                # セッションから明示的に切り離して返す
                session.expunge(article)
            
            return article
    
    @retry_with_backoff(max_retries=3, exceptions=(SQLAlchemyError,))
    def save_ai_analysis(
        self, 
        article_id: int, 
        analysis_data: Dict[str, Any],
        processing_time_ms: Optional[int] = None
    ) -> AIAnalysis:
        """
        AI分析結果保存
        
        Args:
            article_id: 記事ID
            analysis_data: AI分析結果
            processing_time_ms: 処理時間（ミリ秒）
        
        Returns:
            保存されたAI分析オブジェクト
        """
        with self.get_session() as session:
            # 既存の分析結果があるかチェック
            existing = session.query(AIAnalysis).filter_by(article_id=article_id).first()
            if existing:
                # 更新
                existing.summary = analysis_data.get('summary')
                existing.sentiment_label = analysis_data.get('sentiment_label')
                existing.sentiment_score = analysis_data.get('sentiment_score')
                existing.category = analysis_data.get('category')
                existing.region = analysis_data.get('region')
                existing.analyzed_at = datetime.utcnow()
                existing.model_version = analysis_data.get('model_version', 'unknown')
                if processing_time_ms:
                    existing.processing_time_ms = processing_time_ms
                
                log_with_context(
                    self.logger, logging.INFO, "AI分析結果更新完了",
                    operation="update_ai_analysis",
                    article_id=article_id,
                    summary_length=len(analysis_data.get('summary', '')),
                    category=analysis_data.get('category'),
                    region=analysis_data.get('region'),
                    sentiment=analysis_data.get('sentiment_label'),
                    all_keys=list(analysis_data.keys())
                )
                
                return existing
            else:
                # 新規作成
                analysis = AIAnalysis(
                    article_id=article_id,
                    summary=analysis_data.get('summary'),
                    sentiment_label=analysis_data.get('sentiment_label'),
                    sentiment_score=analysis_data.get('sentiment_score'),
                    category=analysis_data.get('category'),
                    region=analysis_data.get('region'),
                    model_version=analysis_data.get('model_version', 'unknown'),
                    processing_time_ms=processing_time_ms
                )
                
                session.add(analysis)
                session.flush()
                
                log_with_context(
                    self.logger, logging.INFO, "AI分析結果保存完了",
                    operation="save_ai_analysis",
                    analysis_id=analysis.id,
                    article_id=article_id,
                    summary_length=len(analysis_data.get('summary', '')),
                    category=analysis_data.get('category'),
                    region=analysis_data.get('region'),
                    sentiment=analysis_data.get('sentiment_label'),
                    all_keys=list(analysis_data.keys())
                )
                
                return analysis
    
    def get_recent_articles(
        self, 
        hours: int = 24, 
        include_analysis: bool = True,
        source: Optional[str] = None
    ) -> List[Article]:
        """
        最新記事取得
        
        Args:
            hours: 取得時間範囲（時間）
            include_analysis: AI分析結果を含むか
            source: ソース指定
        
        Returns:
            記事リスト
        """
        with self.get_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = session.query(Article).filter(
                Article.published_at >= cutoff_time
            )
            
            if source:
                query = query.filter(Article.source == source)
            
            if include_analysis:
                query = query.options(relationship(Article.ai_analysis))
            
            articles = query.order_by(desc(Article.published_at)).all()
            
            log_with_context(
                self.logger, logging.INFO, "最新記事取得完了",
                operation="get_recent_articles",
                count=len(articles),
                hours=hours,
                source=source
            )
            
            return articles
    
    def detect_duplicate_articles(self) -> List[Tuple[Article, Article]]:
        """
        重複記事検出
        
        Returns:
            重複記事のペアリスト
        """
        with self.get_session() as session:
            # 同一content_hashの記事を検出
            subquery = session.query(Article.content_hash).filter(
                Article.content_hash.isnot(None)
            ).group_by(Article.content_hash).having(func.count() > 1).subquery()
            
            duplicates = session.query(Article).filter(
                Article.content_hash.in_(subquery)
            ).order_by(Article.content_hash, Article.scraped_at).all()
            
            # ペアとして返す
            result = []
            current_hash = None
            current_group = []
            
            for article in duplicates:
                if article.content_hash != current_hash:
                    if len(current_group) > 1:
                        for i in range(len(current_group) - 1):
                            result.append((current_group[0], current_group[i + 1]))
                    current_hash = article.content_hash
                    current_group = [article]
                else:
                    current_group.append(article)
            
            # 最後のグループも処理
            if len(current_group) > 1:
                for i in range(len(current_group) - 1):
                    result.append((current_group[0], current_group[i + 1]))
            
            log_with_context(
                self.logger, logging.INFO, "重複記事検出完了",
                operation="detect_duplicates",
                duplicate_pairs=len(result)
            )
            
            return result
    
    def start_scraping_session(self) -> int:
        """スクレイピングセッション開始"""
        with self.get_session() as session:
            scraping_session = ScrapingSession()
            session.add(scraping_session)
            session.flush()
            
            session_id = scraping_session.id
            
            log_with_context(
                self.logger, logging.INFO, "スクレイピングセッション開始",
                operation="start_session",
                session_id=session_id
            )
            
            return session_id
    
    def update_scraping_session(
        self, 
        session_id: int, 
        **kwargs
    ) -> Optional[ScrapingSession]:
        """スクレイピングセッション更新"""
        with self.get_session() as session:
            scraping_session = session.query(ScrapingSession).filter_by(id=session_id).first()
            if not scraping_session:
                return None
            
            for key, value in kwargs.items():
                if hasattr(scraping_session, key):
                    setattr(scraping_session, key, value)
            
            return scraping_session
    
    def complete_scraping_session(
        self, 
        session_id: int, 
        status: str = 'completed',
        error_details: Optional[str] = None
    ) -> Optional[ScrapingSession]:
        """スクレイピングセッション完了"""
        with self.get_session() as session:
            scraping_session = session.query(ScrapingSession).filter_by(id=session_id).first()
            if not scraping_session:
                return None
            
            scraping_session.completed_at = datetime.utcnow()
            scraping_session.status = status
            if error_details:
                scraping_session.error_details = error_details
            
            # 総処理時間計算
            if scraping_session.started_at:
                total_duration = (scraping_session.completed_at - scraping_session.started_at).total_seconds() * 1000
                scraping_session.total_duration_ms = int(total_duration)
            
            log_with_context(
                self.logger, logging.INFO, "スクレイピングセッション完了",
                operation="complete_session",
                session_id=session_id,
                status=status,
                articles_found=scraping_session.articles_found
            )
            
            return scraping_session
    
    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        統計情報取得
        
        Args:
            days: 統計期間（日数）
        
        Returns:
            統計情報辞書
        """
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # 基本統計
            total_articles = session.query(Article).filter(
                Article.scraped_at >= cutoff_date
            ).count()
            
            # ソース別統計
            source_stats = session.query(
                Article.source, func.count(Article.id)
            ).filter(
                Article.scraped_at >= cutoff_date
            ).group_by(Article.source).all()
            
            # 感情分析統計
            sentiment_stats = session.query(
                AIAnalysis.sentiment_label, func.count(AIAnalysis.id)
            ).join(Article).filter(
                Article.scraped_at >= cutoff_date
            ).group_by(AIAnalysis.sentiment_label).all()
            
            # 最近のセッション統計
            recent_sessions = session.query(ScrapingSession).filter(
                ScrapingSession.started_at >= cutoff_date
            ).order_by(desc(ScrapingSession.started_at)).limit(10).all()
            
            statistics = {
                'period_days': days,
                'total_articles': total_articles,
                'source_breakdown': dict(source_stats),
                'sentiment_breakdown': dict(sentiment_stats),
                'recent_sessions': [
                    {
                        'id': s.id,
                        'started_at': s.started_at.isoformat() if s.started_at else None,
                        'status': s.status,
                        'articles_found': s.articles_found,
                        'articles_processed': s.articles_processed
                    }
                    for s in recent_sessions
                ]
            }
            
            return statistics
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """
        古いデータのクリーンアップ
        
        Args:
            days_to_keep: 保持日数
        
        Returns:
            削除された記事数
        """
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # 古い記事を削除（CASCADE設定により関連データも削除される）
            deleted_count = session.query(Article).filter(
                Article.scraped_at < cutoff_date
            ).delete()
            
            # 古いセッション情報も削除
            session.query(ScrapingSession).filter(
                ScrapingSession.started_at < cutoff_date
            ).delete()
            
            log_with_context(
                self.logger, logging.INFO, "データクリーンアップ完了",
                operation="cleanup_data",
                deleted_articles=deleted_count,
                cutoff_date=cutoff_date.isoformat()
            )
            
            return deleted_count