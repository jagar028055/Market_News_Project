# -*- coding: utf-8 -*-

"""
Enhanced Database Article Fetcher
高度な記事選択アルゴリズムを実装したデータベース記事取得システム
"""

import logging
import math
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
            "sentiment": 2.0,  # センチメント重要度
            "summary_length": 1.0,  # 要約詳細度
            "category": 1.5,  # カテゴリ重要度
            "region": 1.0,  # 地域バランス
            "freshness": -0.1,  # 新着度（時間経過でマイナス）
        }

        # カテゴリ重要度マッピング
        self.category_weights = {
            "金融政策": 3.0,
            "経済指標": 2.5,
            "企業業績": 2.0,
            "マーケット": 2.0,
            "ビジネス": 1.5,
            "テクノロジー": 1.5,
            "その他": 1.0,
        }

        # 地域重要度マッピング
        self.region_weights = {"japan": 2.0, "usa": 1.8, "china": 1.5, "europe": 1.3, "other": 1.0}

    def fetch_articles_for_podcast(
        self, target_count: int = 15, hours_back: int = 24
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
            self.logger.info(
                f"ポッドキャスト用記事取得開始 - 目標数: {target_count}, 時間範囲: {hours_back}時間"
            )

            with self.db_manager.get_session() as session:
                # 基本記事取得
                cutoff_time = datetime.now() - timedelta(hours=hours_back)

                articles_with_analysis = (
                    session.query(Article, AIAnalysis)
                    .join(AIAnalysis, Article.id == AIAnalysis.article_id)
                    .filter(Article.scraped_at >= cutoff_time)
                    .order_by(desc(Article.scraped_at))
                    .limit(100)
                    .all()
                )  # 候補記事を大幅に拡張（100件）

                if not articles_with_analysis:
                    # デバッグ情報を詳細に出力
                    total_articles = (
                        session.query(Article).filter(Article.scraped_at >= cutoff_time).count()
                    )

                    total_analysis = (
                        session.query(AIAnalysis)
                        .join(Article)
                        .filter(Article.scraped_at >= cutoff_time)
                        .count()
                    )

                    self.logger.warning(f"分析済み記事が見つかりません")
                    self.logger.info(f"デバッグ情報 - 期間内記事数: {total_articles}")
                    self.logger.info(f"デバッグ情報 - 期間内分析数: {total_analysis}")
                    self.logger.info(f"デバッグ情報 - カットオフ時間: {cutoff_time}")

                    return []

                self.logger.info(f"候補記事数: {len(articles_with_analysis)}")

                # 記事スコアリング
                scored_articles = []
                for article, analysis in articles_with_analysis:
                    score_data = self._calculate_article_score(article, analysis)
                    scored_articles.append(score_data)

                # スコア順でソート
                scored_articles.sort(key=lambda x: x['score'], reverse=True)

                # 高度多様性最適化記事選択
                selected_articles = self._select_articles_with_coverage_constraints(scored_articles, target_count)
                
                # フォールバック: カバレッジが不十分な場合は従来手法も併用
                if len(selected_articles) < target_count * 0.8:
                    self.logger.warning("カバレッジ制約による選択が不十分、従来手法で補完")
                    fallback_articles = self._select_balanced_articles(scored_articles, target_count)
                    # 重複を避けて結合
                    existing_ids = {a['article']['id'] for a in selected_articles}
                    for article in fallback_articles:
                        if article['article']['id'] not in existing_ids and len(selected_articles) < target_count:
                            selected_articles.append(article)

                self.logger.info(f"選択記事数: {len(selected_articles)}")
                for i, article_score in enumerate(selected_articles, 1):
                    self.logger.info(
                        f"選択記事{i}: {article_score['article']['title'][:50]}... "
                        f"(スコア: {article_score['score']:.2f})"
                    )

                return selected_articles

        except Exception as e:
            self.logger.error(f"記事取得エラー: {e}", exc_info=True)
            return []

    def _calculate_article_score(self, article: Article, analysis: AIAnalysis) -> Dict[str, Any]:
        """
        記事スコア計算（セッションセーフ版）

        Args:
            article: 記事オブジェクト
            analysis: AI分析結果

        Returns:
            辞書形式のスコアリング結果
        """
        # セッション内で必要なデータをすべて抽出
        article_data = {
            'id': article.id,
            'title': article.title or "無題",
            'body': article.body or "",  # content → body に修正
            'published_at': article.published_at,
            'source': article.source or "不明",
            'scraped_at': article.scraped_at,
            'url': getattr(article, 'url', None)
        }
        
        analysis_data = {
            'summary': analysis.summary or "",
            'sentiment_score': analysis.sentiment_score or 0.0,
            'category': getattr(analysis, 'category', None),
            'region': getattr(analysis, 'region', None),
            'analyzed_at': analysis.analyzed_at  # created_at → analyzed_at に修正
        }
        
        score_breakdown = {}

        # センチメントスコア
        sentiment_score = abs(analysis_data['sentiment_score'])
        score_breakdown["sentiment"] = sentiment_score * self.scoring_weights["sentiment"]

        # 要約詳細度スコア
        summary_length = len(analysis_data['summary'])
        summary_score = min(summary_length / 200.0, 1.0)  # 200文字を最大として正規化
        score_breakdown["summary_length"] = summary_score * self.scoring_weights["summary_length"]

        # カテゴリスコア（フィールドがない場合はデフォルト）
        category = analysis_data['category']
        if category is None:
            # category フィールドがない場合は、summaryから簡易推定
            category = self._estimate_category_from_summary(analysis.summary or "")
        category_weight = self.category_weights.get(category, 1.0)
        score_breakdown["category"] = category_weight * self.scoring_weights["category"]

        # 地域スコア（フィールドがない場合はデフォルト）
        region = analysis_data['region']
        if region is None:
            # region フィールドがない場合は、summaryから簡易推定
            region = self._estimate_region_from_summary(analysis_data['summary'])
        region_weight = self.region_weights.get(region, 1.0)
        score_breakdown["region"] = region_weight * self.scoring_weights["region"]

        # 新着度スコア（時間経過でペナルティ）
        hours_since_published = (datetime.now() - article_data['scraped_at']).total_seconds() / 3600
        freshness_score = hours_since_published * self.scoring_weights["freshness"]
        score_breakdown["freshness"] = freshness_score

        # 総合スコア計算
        total_score = sum(score_breakdown.values())

        # セッションセーフな辞書形式で返す
        return {
            'article': article_data,
            'analysis': analysis_data,
            'score': total_score,
            'score_breakdown': score_breakdown
        }

    def _select_balanced_articles(
        self, scored_articles: List[Dict[str, Any]], target_count: int
    ) -> List[Dict[str, Any]]:
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

            # カテゴリとリージョンを取得（推定含む）
            category = getattr(article_score.analysis, "category", None)
            if category is None:
                category = self._estimate_category_from_summary(
                    article_score.analysis.summary or ""
                )

            region = getattr(article_score.analysis, "region", None)
            if region is None:
                region = self._estimate_region_from_summary(article_score.analysis.summary or "")

            # カテゴリバランスチェック（1つのカテゴリから最大5記事に拡張）
            if category_counts.get(category, 0) >= 5:
                continue

            # 地域バランスチェック（1つの地域から最大6記事に拡張）
            if region_counts.get(region, 0) >= 6:
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

    def _select_articles_with_coverage_constraints(
        self, scored_articles: List[ArticleScore], target_count: int
    ) -> List[ArticleScore]:
        """
        カバレッジ制約による高度記事選択
        
        Args:
            scored_articles: スコアリング済み記事リスト
            target_count: 目標記事数
            
        Returns:
            多様性を最大化した記事リスト
        """
        if len(scored_articles) <= target_count:
            return scored_articles
            
        # 最小カバレッジ要件
        MIN_REGIONS = 3  # 最低3地域をカバー
        MIN_CATEGORIES = 3  # 最低3カテゴリをカバー
        
        selected = []
        category_counts = {}
        region_counts = {}
        source_counts = {}
        time_slots = {}  # 時間帯分散用
        
        # 重複抑制用のタイトル類似度チェック
        selected_titles = []
        
        # まず、多様性を確保するため各地域・カテゴリから最低1つずつ選択
        regions_covered = set()
        categories_covered = set()
        
        for article_score in scored_articles:
            if len(selected) >= target_count:
                break
                
            # カテゴリと地域を取得
            category = article_score['analysis'].get('category')
            if category is None:
                category = self._estimate_category_from_summary(
                    article_score['analysis']['summary'] or ""
                )
                
            region = article_score['analysis'].get('region')
            if region is None:
                region = self._estimate_region_from_summary(
                    article_score['analysis']['summary'] or ""
                )
                
            # 重複チェック
            if self._is_duplicate_article(article_score['article']['title'], selected_titles):
                continue
                
            # 時間帯計算
            time_slot = self._get_time_slot(article_score['article']['scraped_at'])
            
            # 優先選択: 未カバーの地域・カテゴリ
            should_select = False
            
            if region not in regions_covered and len(regions_covered) < MIN_REGIONS:
                should_select = True
                regions_covered.add(region)
            elif category not in categories_covered and len(categories_covered) < MIN_CATEGORIES:
                should_select = True
                categories_covered.add(category)
            elif len(selected) < target_count // 2:  # 前半は多様性優先
                # バランス制約チェック
                if (category_counts.get(category, 0) < 2 and 
                    region_counts.get(region, 0) < 2 and
                    source_counts.get(article_score['article']['source'], 0) < target_count // 3):
                    should_select = True
                    
            if should_select:
                selected.append(article_score)
                selected_titles.append(article_score['article']['title'])
                category_counts[category] = category_counts.get(category, 0) + 1
                region_counts[region] = region_counts.get(region, 0) + 1
                source_counts[article_score['article']['source']] = source_counts.get(article_score['article']['source'], 0) + 1
                time_slots[time_slot] = time_slots.get(time_slot, 0) + 1
                
        # 残りの枠を高スコア順で埋める（制約は緩和）
        for article_score in scored_articles:
            if len(selected) >= target_count:
                break
                
            if article_score in selected:
                continue
                
            category = article_score['analysis'].get('category') or self._estimate_category_from_summary(article_score['analysis']['summary'] or "")
            region = article_score['analysis'].get('region') or self._estimate_region_from_summary(article_score['analysis']['summary'] or "")
            
            # 重複チェック
            if self._is_duplicate_article(article_score['article']['title'], selected_titles):
                continue
                
            # 緩い制約チェック
            if (category_counts.get(category, 0) < target_count // 2 and 
                region_counts.get(region, 0) < target_count // 2):
                selected.append(article_score)
                selected_titles.append(article_score['article']['title'])
                category_counts[category] = category_counts.get(category, 0) + 1
                region_counts[region] = region_counts.get(region, 0) + 1
                source_counts[article_score['article']['source']] = source_counts.get(article_score['article']['source'], 0) + 1
                
        # カバレッジ評価
        coverage_score = self._calculate_coverage_score(
            category_counts, region_counts, source_counts, time_slots, target_count
        )
        
        self.logger.info(f"高度記事選択完了 - カバレッジスコア: {coverage_score:.2f}")
        self.logger.info(f"カテゴリ分布: {category_counts}")
        self.logger.info(f"地域分布: {region_counts}")
        self.logger.info(f"ソース分布: {source_counts}")
        
        return selected
        
    def _is_duplicate_article(self, title: str, existing_titles: List[str]) -> bool:
        """記事タイトルの重複チェック（簡易類似度）"""
        title_words = set(title.lower().split())
        for existing_title in existing_titles:
            existing_words = set(existing_title.lower().split())
            # 共通語が70%以上なら重複とみなす
            if len(title_words & existing_words) / max(len(title_words), len(existing_words)) > 0.7:
                return True
        return False
        
    def _get_time_slot(self, scraped_at) -> str:
        """時間帯スロット計算（8時間単位）"""
        hour = scraped_at.hour
        if hour < 8:
            return "early"
        elif hour < 16:
            return "mid"
        else:
            return "late"
            
    def _calculate_coverage_score(
        self, category_counts: dict, region_counts: dict, 
        source_counts: dict, time_slots: dict, target_count: int
    ) -> float:
        """カバレッジスコア計算"""
        # 各次元のエントロピー計算（多様性指標）
        def entropy(counts):
            total = sum(counts.values())
            if total == 0:
                return 0
            return -sum((count/total) * math.log2(count/total) for count in counts.values() if count > 0)
            
        category_entropy = entropy(category_counts)
        region_entropy = entropy(region_counts)
        source_entropy = entropy(source_counts)
        time_entropy = entropy(time_slots)
        
        # 正規化とスコア統合
        max_entropy = math.log2(min(target_count, 4))  # 理論最大エントロピー
        normalized_score = (
            category_entropy + region_entropy + source_entropy + time_entropy
        ) / (4 * max_entropy) if max_entropy > 0 else 0
        
        return min(normalized_score, 1.0)

    def _estimate_category_from_summary(self, summary: str) -> str:
        """要約からカテゴリを簡易推定"""
        summary_lower = summary.lower()

        # キーワードベースの簡易分類
        if any(
            word in summary_lower
            for word in ["金利", "政策金利", "日銀", "frb", "fomc", "連邦準備"]
        ):
            return "金融政策"
        elif any(
            word in summary_lower for word in ["gdp", "cpi", "失業率", "経済指標", "経済成長"]
        ):
            return "経済指標"
        elif any(word in summary_lower for word in ["決算", "業績", "売上", "利益", "株価"]):
            return "企業業績"
        elif any(word in summary_lower for word in ["市場", "株式", "債券", "為替"]):
            return "マーケット"
        elif any(
            word in summary_lower for word in ["技術", "ai", "it", "テクノロジー", "デジタル"]
        ):
            return "テクノロジー"
        else:
            return "ビジネス"

    def _estimate_region_from_summary(self, summary: str) -> str:
        """要約から地域を簡易推定"""
        summary_lower = summary.lower()

        # 地域キーワードベースの簡易分類
        if any(word in summary_lower for word in ["日銀", "日本", "東京", "円"]):
            return "japan"
        elif any(
            word in summary_lower for word in ["fed", "frb", "fomc", "アメリカ", "米国", "ドル"]
        ):
            return "usa"
        elif any(word in summary_lower for word in ["中国", "人民銀行", "元", "北京", "上海"]):
            return "china"
        elif any(word in summary_lower for word in ["欧州", "ecb", "ユーロ", "ドイツ", "フランス"]):
            return "europe"
        else:
            return "other"

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
                total_count = (
                    session.query(Article).filter(Article.scraped_at >= cutoff_time).count()
                )

                analyzed_count = (
                    session.query(Article)
                    .join(AIAnalysis)
                    .filter(Article.scraped_at >= cutoff_time)
                    .count()
                )

                # カテゴリ分布
                category_dist = {}
                if hasattr(AIAnalysis, "category"):
                    category_results = (
                        session.query(AIAnalysis.category, func.count(AIAnalysis.id))
                        .join(Article)
                        .filter(Article.scraped_at >= cutoff_time)
                        .group_by(AIAnalysis.category)
                        .all()
                    )

                    category_dist = {cat: count for cat, count in category_results}

                # 地域分布
                region_dist = {}
                if hasattr(AIAnalysis, "region"):
                    region_results = (
                        session.query(AIAnalysis.region, func.count(AIAnalysis.id))
                        .join(Article)
                        .filter(Article.scraped_at >= cutoff_time)
                        .group_by(AIAnalysis.region)
                        .all()
                    )

                    region_dist = {region: count for region, count in region_results}

                return {
                    "total_articles": total_count,
                    "analyzed_articles": analyzed_count,
                    "analysis_rate": analyzed_count / total_count if total_count > 0 else 0,
                    "category_distribution": category_dist,
                    "region_distribution": region_dist,
                    "time_range_hours": hours_back,
                }

        except Exception as e:
            self.logger.error(f"統計情報取得エラー: {e}", exc_info=True)
            return {}
