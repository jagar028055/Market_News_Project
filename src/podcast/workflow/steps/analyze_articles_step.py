# -*- coding: utf-8 -*-

"""
ステップ3: 記事データの解析と厳選
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .step import IWorkflowStep, StepContext

class AnalyzeArticlesStep(IWorkflowStep):
    """
    記事を分析し、重要度に基づいて厳選するステップ。
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @property
    def step_name(self) -> str:
        return "記事データ解析"

    async def execute(self, context: StepContext) -> Optional[str]:
        """
        記事の重要度を計算し、上位の記事を厳選します。

        Args:
            context: ワークフローのコンテキスト。

        Returns:
            エラーメッセージ。成功した場合はNone。
        """
        try:
            articles = context.data.get('articles')
            if not articles:
                return "解析する記事がありません。"

            self.logger.info(f"{len(articles)}件の記事を解析しています...")

            scored_articles = []
            for article in articles:
                score = self._calculate_article_importance(article)
                article_with_score = article.copy()
                article_with_score["importance_score"] = score
                scored_articles.append(article_with_score)

            scored_articles.sort(key=lambda x: x["importance_score"], reverse=True)

            max_articles = context.config.max_articles
            selected_articles = scored_articles[:max_articles]

            self.logger.info(f"{len(articles)}件から{len(selected_articles)}件を厳選しました。")

            context.data['selected_articles'] = selected_articles
            context.result.articles_processed = len(selected_articles)

            return None

        except Exception as e:
            self.logger.error(f"記事解析中にエラーが発生しました: {e}", exc_info=True)
            return f"記事解析エラー: {e}"

    def _calculate_article_importance(self, article: Dict[str, Any]) -> float:
        """
        記事の重要度スコアを計算します。
        元のワークフロークラスから移植・改善されたロジック。
        """
        score = 0.0
        sentiment_score = abs(article.get("sentiment_score", 0.0))
        score += sentiment_score * 0.35

        summary_length = len(article.get("summary", ""))
        score += min(summary_length / 500.0, 1.0) * 0.25

        title_length = len(article.get("title", ""))
        score += min(title_length / 100.0, 1.0) * 0.15

        try:
            published_date_str = article.get("published_date")
            if published_date_str:
                published_date = datetime.fromisoformat(published_date_str.replace('Z', '+00:00'))
                now_aware = datetime.now(timezone.utc)
                hours_old = (now_aware - published_date).total_seconds() / 3600
                freshness_score = max(0, min(0.15, 0.15 * (1 - max(0, hours_old) / 48))) # 48時間でスコアが0になるように調整
                score += freshness_score
        except (ValueError, TypeError):
            pass

        source = article.get("source", "").lower()
        source_weights = {
            "reuters": 0.12, "bloomberg": 0.12, "nikkei": 0.10, "日経": 0.10,
            "wsj": 0.10, "wall street journal": 0.10, "ft.com": 0.10, "financial times": 0.10
        }
        for s, w in source_weights.items():
            if s in source:
                score += w
                break

        title_and_summary = (article.get("title", "") + " " + article.get("summary", "")).lower()

        high_impact_keywords = [
            "fed", "central bank", "interest rate", "gdp", "inflation", "recession",
            "market crash", "stimulus", "bailout", "merger", "acquisition",
            "中央銀行", "金利", "インフレ", "景気後退", "刺激策"
        ]
        if any(keyword in title_and_summary for keyword in high_impact_keywords):
            score += 0.08

        medium_impact_keywords = [
            "earnings", "revenue", "profit", "dividend", "stock split", "ipo",
            "決算", "売上", "利益", "配当", "株式分割", "新規上場"
        ]
        if any(keyword in title_and_summary for keyword in medium_impact_keywords):
            score += 0.05

        return min(score, 2.0)
