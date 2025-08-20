# -*- coding: utf-8 -*-

"""
拡張データベース記事フェッチャー
category/regionフィールド対応・重要度スコアリング機能付き
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import joinedload
from sqlalchemy import desc, func, case, and_

from src.database.database_manager import DatabaseManager
from src.database.models import Article, AIAnalysis
from src.logging_config import get_logger, log_with_context


class EnhancedDatabaseArticleFetcher:
    """拡張データベース記事フェッチャークラス"""
    
    # カテゴリ重要度重み（記事選択アルゴリズム用）
    CATEGORY_WEIGHTS = {
        'monetary_policy': 3.0,      # 金融政策（最重要）
        'economic_indicators': 2.8,   # 経済指標
        'central_bank': 2.8,         # 中央銀行
        'market_volatility': 2.6,    # 市場変動
        'corporate_earnings': 2.4,   # 企業業績
        'geopolitical': 2.2,         # 地政学
        'energy_commodities': 2.0,   # エネルギー・商品
        'technology': 1.8,           # 技術
        'regulatory': 1.6,           # 規制・政策
        'other': 1.0                 # その他
    }
    
    # 地域重要度重み
    REGION_WEIGHTS = {
        'usa': 2.0,      # 米国（最重要）
        'japan': 1.8,    # 日本
        'china': 1.6,    # 中国
        'europe': 1.4,   # 欧州
        'other': 1.0     # その他
    }
    
    def __init__(self, database_manager: DatabaseManager):
        """
        初期化
        
        Args:
            database_manager: データベース管理インスタンス
        """
        self.db_manager = database_manager
        self.logger = get_logger("enhanced_article_fetcher")
        
        log_with_context(
            self.logger, logging.INFO, "拡張記事フェッチャー初期化完了",
            operation="init",
            category_weights_count=len(self.CATEGORY_WEIGHTS),
            region_weights_count=len(self.REGION_WEIGHTS)
        )
    
    def get_articles_for_podcast(
        self, 
        hours: int = 24,
        max_articles: int = 6,
        category_filter: Optional[List[str]] = None,
        region_filter: Optional[List[str]] = None,
        min_sentiment_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        ポッドキャスト用記事を重要度順で取得
        
        Args:
            hours: 取得時間範囲（時間）
            max_articles: 最大記事数
            category_filter: カテゴリフィルター
            region_filter: 地域フィルター
            min_sentiment_score: 最小センチメントスコア（絶対値）
            
        Returns:
            重要度順記事リスト（詳細データ付き）
        """
        with self.db_manager.get_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # 基本クエリ（AI分析済み記事のみ）
            query = session.query(Article).join(AIAnalysis).options(
                joinedload(Article.ai_analysis)
            ).filter(
                Article.published_at >= cutoff_time
            )
            
            # フィルター適用
            if category_filter:
                query = query.filter(AIAnalysis.category.in_(category_filter))
            
            if region_filter:
                query = query.filter(AIAnalysis.region.in_(region_filter))
            
            if min_sentiment_score is not None:
                query = query.filter(
                    func.abs(AIAnalysis.sentiment_score) >= min_sentiment_score
                )
            
            # 記事を取得
            articles = query.order_by(desc(Article.published_at)).all()
            
            log_with_context(
                self.logger, logging.INFO, "記事フィルタリング完了",
                operation="filter_articles",
                total_found=len(articles),
                hours=hours,
                category_filter=category_filter,
                region_filter=region_filter
            )
            
            # 重要度スコア計算・ソート
            scored_articles = self._calculate_importance_scores(articles)
            
            # 上位記事を選択
            selected_articles = scored_articles[:max_articles]
            
            # 詳細データを構築
            detailed_articles = self._build_detailed_article_data(selected_articles)
            
            log_with_context(
                self.logger, logging.INFO, "ポッドキャスト用記事選択完了",
                operation="select_podcast_articles",
                selected_count=len(detailed_articles),
                max_articles=max_articles,
                avg_importance_score=sum(a['importance_score'] for a in detailed_articles) / len(detailed_articles) if detailed_articles else 0
            )
            
            return detailed_articles
    
    def _calculate_importance_scores(self, articles: List[Article]) -> List[Tuple[Article, float]]:
        """
        記事重要度スコア計算
        
        Args:
            articles: 記事リスト
            
        Returns:
            (記事, 重要度スコア)のリスト（重要度順ソート済み）
        """
        scored_articles = []
        
        for article in articles:
            if not article.ai_analysis:
                continue
                
            analysis = article.ai_analysis[0]  # 最新の分析結果
            
            # 基本スコア計算
            sentiment_weight = abs(analysis.sentiment_score or 0) * 2.0
            summary_weight = len(analysis.summary or '') / 100.0
            
            # 新着度（時間が新しいほど高スコア）
            hours_since_published = (datetime.utcnow() - article.published_at).total_seconds() / 3600
            recency_weight = max(0, 24 - hours_since_published) * 0.1
            
            # カテゴリ重み
            category_weight = self.CATEGORY_WEIGHTS.get(analysis.category or 'other', 1.0) * 1.5
            
            # 地域重み
            region_weight = self.REGION_WEIGHTS.get(analysis.region or 'other', 1.0) * 1.0
            
            # 総合スコア
            total_score = (
                sentiment_weight + 
                summary_weight + 
                recency_weight + 
                category_weight + 
                region_weight
            )
            
            scored_articles.append((article, total_score))
        
        # 重要度順でソート
        scored_articles.sort(key=lambda x: x[1], reverse=True)
        
        log_with_context(
            self.logger, logging.DEBUG, "重要度スコア計算完了",
            operation="calculate_scores",
            articles_count=len(scored_articles),
            top_score=scored_articles[0][1] if scored_articles else 0,
            bottom_score=scored_articles[-1][1] if scored_articles else 0
        )
        
        return scored_articles
    
    def _build_detailed_article_data(self, scored_articles: List[Tuple[Article, float]]) -> List[Dict[str, Any]]:
        """
        詳細記事データ構築
        
        Args:
            scored_articles: (記事, スコア)リスト
            
        Returns:
            詳細記事データのリスト
        """
        detailed_articles = []
        
        for article, importance_score in scored_articles:
            analysis = article.ai_analysis[0] if article.ai_analysis else None
            
            article_data = {
                # 基本情報
                'id': article.id,
                'title': article.title,
                'url': article.url,
                'source': article.source,
                'published_date': article.published_at.strftime('%Y-%m-%d') if article.published_at else None,
                'published_at': article.published_at,
                'scraped_at': article.scraped_at,
                
                # AI分析情報
                'summary': analysis.summary if analysis else None,
                'sentiment_label': analysis.sentiment_label if analysis else None,
                'sentiment_score': analysis.sentiment_score if analysis else None,
                'category': analysis.category if analysis else None,
                'region': analysis.region if analysis else None,
                'analyzed_at': analysis.analyzed_at if analysis else None,
                'model_version': analysis.model_version if analysis else None,
                
                # 重要度情報
                'importance_score': round(importance_score, 2),
                'category_weight': self.CATEGORY_WEIGHTS.get(analysis.category if analysis else 'other', 1.0),
                'region_weight': self.REGION_WEIGHTS.get(analysis.region if analysis else 'other', 1.0),
                
                # 追加メタデータ
                'character_count': len(article.title or '') + len(analysis.summary if analysis else ''),
                'has_ai_analysis': analysis is not None
            }
            
            detailed_articles.append(article_data)
        
        return detailed_articles
    
    def get_articles_by_category(
        self, 
        category: str, 
        hours: int = 24,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        カテゴリ別記事取得
        
        Args:
            category: 対象カテゴリ
            hours: 取得時間範囲
            limit: 最大記事数
            
        Returns:
            カテゴリ記事リスト
        """
        return self.get_articles_for_podcast(
            hours=hours,
            max_articles=limit,
            category_filter=[category]
        )
    
    def get_articles_by_region(
        self, 
        region: str, 
        hours: int = 24,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        地域別記事取得
        
        Args:
            region: 対象地域
            hours: 取得時間範囲
            limit: 最大記事数
            
        Returns:
            地域記事リスト
        """
        return self.get_articles_for_podcast(
            hours=hours,
            max_articles=limit,
            region_filter=[region]
        )
    
    def get_balanced_article_selection(
        self, 
        hours: int = 24,
        max_articles: int = 6
    ) -> List[Dict[str, Any]]:
        """
        バランス取れた記事選択
        カテゴリ・地域の多様性を考慮した選択
        
        Args:
            hours: 取得時間範囲
            max_articles: 最大記事数
            
        Returns:
            バランス記事リスト
        """
        # 全記事を重要度順で取得
        all_articles = self.get_articles_for_podcast(
            hours=hours,
            max_articles=max_articles * 3  # 候補を多めに取得
        )
        
        if not all_articles:
            return []
        
        # カテゴリ・地域の多様性を考慮した選択
        selected_articles = []
        used_categories = set()
        used_regions = set()
        
        for article in all_articles:
            if len(selected_articles) >= max_articles:
                break
                
            category = article.get('category', 'other')
            region = article.get('region', 'other')
            
            # 多様性を優先（新しいカテゴリ・地域を優先）
            category_new = category not in used_categories
            region_new = region not in used_regions
            
            # 新しいカテゴリ・地域の記事を優先選択
            if category_new or region_new or len(selected_articles) < max_articles // 2:
                selected_articles.append(article)
                used_categories.add(category)
                used_regions.add(region)
        
        # 残り枠は重要度順で埋める
        for article in all_articles:
            if len(selected_articles) >= max_articles:
                break
            if article not in selected_articles:
                selected_articles.append(article)
        
        log_with_context(
            self.logger, logging.INFO, "バランス記事選択完了",
            operation="balanced_selection",
            selected_count=len(selected_articles),
            categories_count=len(used_categories),
            regions_count=len(used_regions),
            categories=list(used_categories),
            regions=list(used_regions)
        )
        
        return selected_articles[:max_articles]
    
    def get_database_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        データベース統計情報取得
        
        Args:
            hours: 統計対象期間
            
        Returns:
            統計情報辞書
        """
        with self.db_manager.get_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # 基本統計
            total_articles = session.query(Article).filter(
                Article.published_at >= cutoff_time
            ).count()
            
            analyzed_articles = session.query(Article).join(AIAnalysis).filter(
                Article.published_at >= cutoff_time
            ).count()
            
            # カテゴリ別統計
            category_stats = session.query(
                AIAnalysis.category, func.count(AIAnalysis.id)
            ).join(Article).filter(
                Article.published_at >= cutoff_time
            ).group_by(AIAnalysis.category).all()
            
            # 地域別統計
            region_stats = session.query(
                AIAnalysis.region, func.count(AIAnalysis.id)
            ).join(Article).filter(
                Article.published_at >= cutoff_time
            ).group_by(AIAnalysis.region).all()
            
            # センチメント統計
            sentiment_stats = session.query(
                AIAnalysis.sentiment_label, func.count(AIAnalysis.id)
            ).join(Article).filter(
                Article.published_at >= cutoff_time
            ).group_by(AIAnalysis.sentiment_label).all()
            
            statistics = {
                'period_hours': hours,
                'total_articles': total_articles,
                'analyzed_articles': analyzed_articles,
                'analysis_coverage_rate': analyzed_articles / total_articles if total_articles > 0 else 0,
                'category_breakdown': dict(category_stats),
                'region_breakdown': dict(region_stats),
                'sentiment_breakdown': dict(sentiment_stats),
                'category_weights': self.CATEGORY_WEIGHTS,
                'region_weights': self.REGION_WEIGHTS
            }
            
            log_with_context(
                self.logger, logging.INFO, "データベース統計取得完了",
                operation="get_statistics",
                total_articles=total_articles,
                analyzed_articles=analyzed_articles,
                analysis_rate=f"{statistics['analysis_coverage_rate']:.1%}"
            )
            
            return statistics