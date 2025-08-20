# -*- coding: utf-8 -*-

"""
Enhanced Database Article Fetcher
高度な記事選択アルゴリズムを実装したデータベース記事取得システム
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from src.database.database_manager import DatabaseManager
from src.database.models import Article, AIAnalysis


@dataclass
class ArticleScore:
    """記事スコアリング結果"""
    article: Article
    analysis: AIAnalysis
    score: float
    score_breakdown: Dict[str, float]


class EnhancedDatabaseArticleFetcher:
    """拡張データベース記事取得クラス"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        初期化
        
        Args:
            db_manager: データベース管理オブジェクト
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # スコアリング重み設定
        self.scoring_weights = {
            'sentiment': 2.0,        # センチメント重要度
            'summary_length': 1.0,   # 要約詳細度
            'category': 1.5,         # カテゴリ重要度
            'region': 1.0,           # 地域バランス
            'freshness': -0.1        # 新着度（時間経過でマイナス）
        }
        
        # カテゴリ重要度マッピング
        self.category_weights = {
            '金融政策': 3.0,
            '経済指標': 2.5,
            '企業業績': 2.0,
            'マーケット': 2.0,
            'ビジネス': 1.5,
            'テクノロジー': 1.5,
            'その他': 1.0
        }
        
        # 地域重要度マッピング
        self.region_weights = {
            'japan': 2.0,
            'usa': 1.8,
            'china': 1.5,
            'europe': 1.3,
            'other': 1.0
        }
    
    def fetch_articles_for_podcast(
        self,
        target_count: int = 6,
        hours_back: int = 24
    ) -> List[ArticleScore]:
        """
        ポッドキャスト用記事を取得
        
        Args:
            target_count: 目標記事数
            hours_back: 取得範囲時間
            
        Returns:
            スコアリング済み記事リスト
        """
        try:
            self.logger.info(f"ポッドキャスト用記事取得開始 - 目標数: {target_count}, 時間範囲: {hours_back}時間")
            
            with self.db_manager.get_session() as session:
                # 基本記事取得
                cutoff_time = datetime.now() - timedelta(hours=hours_back)
                
                articles_with_analysis = session.query(Article, AIAnalysis).join(
                    AIAnalysis, Article.id == AIAnalysis.article_id
                ).filter(
                    Article.scraped_at >= cutoff_time
                ).order_by(
                    desc(Article.scraped_at)
                ).limit(50).all()  # 候補記事を多めに取得
                
                if not articles_with_analysis:
                    self.logger.warning("分析済み記事が見つかりません")
                    return []
                
                self.logger.info(f"候補記事数: {len(articles_with_analysis)}")
                
                # 記事スコアリング
                scored_articles = []
                for article, analysis in articles_with_analysis:
                    score_data = self._calculate_article_score(article, analysis)
                    scored_articles.append(score_data)
                
                # スコア順でソート
                scored_articles.sort(key=lambda x: x.score, reverse=True)
                
                # バランス調整された記事選択
                selected_articles = self._select_balanced_articles(
                    scored_articles, target_count
                )
                
                self.logger.info(f"選択記事数: {len(selected_articles)}")
                for i, article_score in enumerate(selected_articles, 1):
                    self.logger.info(
                        f"選択記事{i}: {article_score.article.title[:50]}... "
                        f"(スコア: {article_score.score:.2f})"
                    )
                
                return selected_articles
                
        except Exception as e:
            self.logger.error(f"記事取得エラー: {e}", exc_info=True)
            return []
    
    def _calculate_article_score(
        self,
        article: Article,
        analysis: AIAnalysis
    ) -> ArticleScore:
        """
        記事スコア計算
        
        Args:
            article: 記事オブジェクト
            analysis: AI分析結果
            
        Returns:
            スコアリング結果
        """
        score_breakdown = {}
        
        # センチメントスコア
        sentiment_score = abs(analysis.sentiment_score or 0.0)
        score_breakdown['sentiment'] = sentiment_score * self.scoring_weights['sentiment']
        
        # 要約詳細度スコア
        summary_length = len(analysis.summary or '')
        summary_score = min(summary_length / 200.0, 1.0)  # 200文字を最大として正規化
        score_breakdown['summary_length'] = summary_score * self.scoring_weights['summary_length']
        
        # カテゴリスコア
        category = getattr(analysis, 'category', None) or 'その他'
        category_weight = self.category_weights.get(category, 1.0)
        score_breakdown['category'] = category_weight * self.scoring_weights['category']
        
        # 地域スコア
        region = getattr(analysis, 'region', None) or 'other'
        region_weight = self.region_weights.get(region, 1.0)
        score_breakdown['region'] = region_weight * self.scoring_weights['region']
        
        # 新着度スコア（時間経過でペナルティ）
        hours_since_published = (datetime.now() - article.scraped_at).total_seconds() / 3600
        freshness_score = hours_since_published * self.scoring_weights['freshness']
        score_breakdown['freshness'] = freshness_score
        
        # 総合スコア計算
        total_score = sum(score_breakdown.values())
        
        return ArticleScore(
            article=article,
            analysis=analysis,
            score=total_score,
            score_breakdown=score_breakdown
        )
    
    def _select_balanced_articles(
        self,
        scored_articles: List[ArticleScore],
        target_count: int
    ) -> List[ArticleScore]:
        """
        バランス調整された記事選択
        
        Args:
            scored_articles: スコアリング済み記事リスト
            target_count: 目標記事数
            
        Returns:
            バランス調整された記事リスト
        """
        if len(scored_articles) <= target_count:
            return scored_articles
        
        selected = []
        category_counts = {}
        region_counts = {}
        
        for article_score in scored_articles:
            if len(selected) >= target_count:
                break
            
            category = getattr(article_score.analysis, 'category', None) or 'その他'
            region = getattr(article_score.analysis, 'region', None) or 'other'
            
            # カテゴリバランスチェック（1つのカテゴリから最大3記事）
            if category_counts.get(category, 0) >= 3:
                continue
            
            # 地域バランスチェック（1つの地域から最大4記事）
            if region_counts.get(region, 0) >= 4:
                continue
            
            selected.append(article_score)
            category_counts[category] = category_counts.get(category, 0) + 1
            region_counts[region] = region_counts.get(region, 0) + 1
        
        # 目標数に達しない場合、残りを高スコア順で追加
        if len(selected) < target_count:
            remaining_articles = [a for a in scored_articles if a not in selected]
            needed = target_count - len(selected)
            selected.extend(remaining_articles[:needed])
        
        self.logger.info(f"カテゴリ分布: {category_counts}")
        self.logger.info(f"地域分布: {region_counts}")
        
        return selected
    
    def get_article_statistics(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        記事統計情報を取得
        
        Args:
            hours_back: 統計範囲時間
            
        Returns:
            統計情報辞書
        """
        try:
            with self.db_manager.get_session() as session:
                cutoff_time = datetime.now() - timedelta(hours=hours_back)
                
                # 基本統計
                total_count = session.query(Article).filter(
                    Article.scraped_at >= cutoff_time
                ).count()
                
                analyzed_count = session.query(Article).join(AIAnalysis).filter(
                    Article.scraped_at >= cutoff_time
                ).count()
                
                # カテゴリ分布
                category_dist = {}
                if hasattr(AIAnalysis, 'category'):
                    category_results = session.query(
                        AIAnalysis.category,
                        func.count(AIAnalysis.id)
                    ).join(Article).filter(
                        Article.scraped_at >= cutoff_time
                    ).group_by(AIAnalysis.category).all()
                    
                    category_dist = {cat: count for cat, count in category_results}
                
                # 地域分布
                region_dist = {}
                if hasattr(AIAnalysis, 'region'):
                    region_results = session.query(
                        AIAnalysis.region,
                        func.count(AIAnalysis.id)
                    ).join(Article).filter(
                        Article.scraped_at >= cutoff_time
                    ).group_by(AIAnalysis.region).all()
                    
                    region_dist = {region: count for region, count in region_results}
                
                return {
                    'total_articles': total_count,
                    'analyzed_articles': analyzed_count,
                    'analysis_rate': analyzed_count / total_count if total_count > 0 else 0,
                    'category_distribution': category_dist,
                    'region_distribution': region_dist,
                    'time_range_hours': hours_back
                }
                
        except Exception as e:
            self.logger.error(f"統計情報取得エラー: {e}", exc_info=True)
            return {}