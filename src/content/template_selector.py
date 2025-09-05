# -*- coding: utf-8 -*-

"""
市場状況に応じたテンプレート選択システム
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import logging
from datetime import datetime

from ..market_data.models import MarketSnapshot, MarketTrend


class TemplateType(Enum):
    """テンプレートタイプ"""

    MARKET_CRASH = "market_crash"  # 市場急落専用
    EARNINGS_SEASON = "earnings_season"  # 決算シーズン専用
    FED_POLICY = "fed_policy"  # 中央銀行政策専用
    GEOPOLITICAL = "geopolitical"  # 地政学リスク専用
    CRYPTO_FOCUS = "crypto_focus"  # 仮想通貨特化
    DEFAULT = "default"  # デフォルト


class TemplateSelector:
    """テンプレート選択クラス"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

        # テンプレート条件定義
        self.template_conditions = self._define_template_conditions()

    def select_template(
        self,
        market_snapshot: MarketSnapshot,
        articles: List[Dict[str, Any]],
        datetime_context: Optional[datetime] = None,
    ) -> TemplateType:
        """
        市場状況と記事内容からテンプレートを選択

        Args:
            market_snapshot: 現在の市場状況
            articles: 記事リスト
            datetime_context: 日時コンテキスト

        Returns:
            TemplateType: 選択されたテンプレートタイプ
        """
        self.logger.info("テンプレート選択を開始")

        # 優先度順でテンプレートを判定
        template_scores = {}

        for template_type, conditions in self.template_conditions.items():
            score = self._calculate_template_score(
                template_type, conditions, market_snapshot, articles, datetime_context
            )
            template_scores[template_type] = score

            self.logger.debug(f"テンプレート {template_type.value}: スコア {score}")

        # 最高スコアのテンプレートを選択
        selected_template = max(template_scores, key=template_scores.get)
        max_score = template_scores[selected_template]

        # 最低閾値チェック
        if max_score < 0.3:
            selected_template = TemplateType.DEFAULT

        self.logger.info(
            f"選択されたテンプレート: {selected_template.value} (スコア: {max_score:.2f})"
        )
        return selected_template

    def _define_template_conditions(self) -> Dict[TemplateType, Dict[str, Any]]:
        """テンプレート選択条件を定義"""
        return {
            TemplateType.MARKET_CRASH: {
                "volatility_threshold": 60.0,
                "negative_sentiment_threshold": -2.0,
                "major_decline_threshold": -3.0,
                "keywords": ["急落", "暴落", "売り", "パニック", "恐怖", "リスクオフ"],
                "priority": 10,  # 最高優先度
            },
            TemplateType.FED_POLICY: {
                "volatility_threshold": 40.0,
                "fed_keywords": ["FRB", "FOMC", "金利", "利上げ", "利下げ", "量的緩和", "金融政策"],
                "central_bank_keywords": ["日銀", "ECB", "中央銀行"],
                "min_relevant_articles": 2,
                "priority": 9,
            },
            TemplateType.EARNINGS_SEASON: {
                "earnings_keywords": ["決算", "業績", "四半期", "売上", "利益", "EPS"],
                "min_relevant_articles": 3,
                "seasonal_months": [1, 4, 7, 10],  # 決算月
                "priority": 7,
            },
            TemplateType.GEOPOLITICAL: {
                "geopolitical_keywords": [
                    "戦争",
                    "紛争",
                    "制裁",
                    "貿易戦争",
                    "関税",
                    "地政学",
                    "選挙",
                    "政治",
                    "外交",
                ],
                "min_relevant_articles": 2,
                "regions": ["china", "usa", "europe"],
                "priority": 8,
            },
            TemplateType.CRYPTO_FOCUS: {
                "crypto_symbols": ["BTC", "ETH", "ビットコイン", "イーサリアム", "仮想通貨"],
                "crypto_volatility_threshold": 80.0,
                "min_crypto_articles": 2,
                "priority": 6,
            },
            TemplateType.DEFAULT: {"priority": 1},  # 最低優先度
        }

    def _calculate_template_score(
        self,
        template_type: TemplateType,
        conditions: Dict[str, Any],
        market_snapshot: MarketSnapshot,
        articles: List[Dict[str, Any]],
        datetime_context: Optional[datetime],
    ) -> float:
        """テンプレートスコアを計算"""

        if template_type == TemplateType.DEFAULT:
            return 0.5  # 基準スコア

        score = 0.0
        max_score = 0.0

        # ボラティリティチェック
        if "volatility_threshold" in conditions:
            threshold = conditions["volatility_threshold"]
            max_score += 0.3
            if market_snapshot.volatility_score >= threshold:
                score += 0.3
            elif market_snapshot.volatility_score >= threshold * 0.8:
                score += 0.2

        # 市場センチメントチェック
        if "negative_sentiment_threshold" in conditions:
            threshold = conditions["negative_sentiment_threshold"]
            max_score += 0.2
            if market_snapshot.overall_sentiment == MarketTrend.BEARISH:
                # 主要株価指数の平均下落率を計算
                if market_snapshot.stock_indices:
                    avg_change = sum(
                        idx.change_percent for idx in market_snapshot.stock_indices
                    ) / len(market_snapshot.stock_indices)
                    if avg_change <= threshold:
                        score += 0.2
                    elif avg_change <= threshold * 0.5:
                        score += 0.1

        # 大幅下落チェック
        if "major_decline_threshold" in conditions:
            threshold = conditions["major_decline_threshold"]
            max_score += 0.3
            major_declines = [
                idx for idx in market_snapshot.stock_indices if idx.change_percent <= threshold
            ]
            if len(major_declines) >= 2:
                score += 0.3
            elif len(major_declines) >= 1:
                score += 0.2

        # キーワードマッチング
        if "keywords" in conditions:
            max_score += 0.2
            keyword_score = self._calculate_keyword_score(articles, conditions["keywords"])
            score += keyword_score * 0.2

        # 特定分野のキーワード
        for key in [
            "fed_keywords",
            "central_bank_keywords",
            "earnings_keywords",
            "geopolitical_keywords",
            "crypto_symbols",
        ]:
            if key in conditions:
                max_score += 0.15
                keyword_score = self._calculate_keyword_score(articles, conditions[key])
                score += keyword_score * 0.15

        # 最小関連記事数チェック
        if "min_relevant_articles" in conditions:
            max_score += 0.1
            relevant_count = self._count_relevant_articles(articles, conditions)
            if relevant_count >= conditions["min_relevant_articles"]:
                score += 0.1
            elif relevant_count >= conditions["min_relevant_articles"] * 0.5:
                score += 0.05

        # 季節性チェック（決算シーズンなど）
        if "seasonal_months" in conditions and datetime_context:
            max_score += 0.1
            if datetime_context.month in conditions["seasonal_months"]:
                score += 0.1

        # 仮想通貨特有のボラティリティチェック
        if "crypto_volatility_threshold" in conditions:
            max_score += 0.2
            crypto_data = [
                data
                for data in (
                    market_snapshot.stock_indices
                    + market_snapshot.currency_pairs
                    + market_snapshot.commodities
                )
                if any(
                    crypto_term in data.symbol.upper() for crypto_term in ["BTC", "ETH", "CRYPTO"]
                )
            ]
            if crypto_data:
                avg_crypto_volatility = sum(abs(d.change_percent) for d in crypto_data) / len(
                    crypto_data
                )
                if avg_crypto_volatility >= conditions["crypto_volatility_threshold"]:
                    score += 0.2

        # 正規化してスコアを返す
        normalized_score = score / max_score if max_score > 0 else 0

        # 優先度による重み付け
        priority_weight = conditions.get("priority", 5) / 10.0
        final_score = normalized_score * priority_weight

        return min(final_score, 1.0)

    def _calculate_keyword_score(
        self, articles: List[Dict[str, Any]], keywords: List[str]
    ) -> float:
        """キーワードスコアを計算"""
        if not articles or not keywords:
            return 0.0

        total_matches = 0
        total_words = 0

        for article in articles:
            title = article.get("title", "").lower()
            summary = article.get("summary", "").lower()
            text = f"{title} {summary}"

            words = text.split()
            total_words += len(words)

            for keyword in keywords:
                if keyword.lower() in text:
                    total_matches += 1

        return min(total_matches / len(articles), 1.0) if articles else 0.0

    def _count_relevant_articles(
        self, articles: List[Dict[str, Any]], conditions: Dict[str, Any]
    ) -> int:
        """関連記事数をカウント"""
        relevant_count = 0

        # 全てのキーワードを統合
        all_keywords = []
        for key in [
            "keywords",
            "fed_keywords",
            "central_bank_keywords",
            "earnings_keywords",
            "geopolitical_keywords",
            "crypto_symbols",
        ]:
            if key in conditions:
                all_keywords.extend(conditions[key])

        for article in articles:
            title = article.get("title", "").lower()
            summary = article.get("summary", "").lower()
            text = f"{title} {summary}"

            if any(keyword.lower() in text for keyword in all_keywords):
                relevant_count += 1

        return relevant_count

    def get_template_config(self, template_type: TemplateType) -> Dict[str, Any]:
        """テンプレート設定を取得"""
        configs = {
            TemplateType.MARKET_CRASH: {
                "emphasis": ["リスク分析", "安全資産", "市場心理"],
                "sections": ["緊急市場分析", "リスクファクター", "投資家行動"],
                "tone": "警戒",
                "priority_categories": ["市場動向", "金融政策", "経済指標"],
            },
            TemplateType.FED_POLICY: {
                "emphasis": ["金融政策影響", "金利見通し", "通貨動向"],
                "sections": ["政策分析", "市場反応", "今後の見通し"],
                "tone": "分析的",
                "priority_categories": ["金融政策", "経済指標", "市場動向"],
            },
            TemplateType.EARNINGS_SEASON: {
                "emphasis": ["企業業績", "セクター分析", "投資機会"],
                "sections": ["決算サマリー", "業績トレンド", "投資判断"],
                "tone": "楽観的",
                "priority_categories": ["企業業績", "市場動向"],
            },
            TemplateType.GEOPOLITICAL: {
                "emphasis": ["地政学影響", "リスク評価", "地域分析"],
                "sections": ["地政学分析", "市場への影響", "リスク対応"],
                "tone": "慎重",
                "priority_categories": ["国際情勢", "政治", "市場動向"],
            },
            TemplateType.CRYPTO_FOCUS: {
                "emphasis": ["仮想通貨動向", "技術分析", "規制影響"],
                "sections": ["暗号資産分析", "技術トレンド", "規制動向"],
                "tone": "革新的",
                "priority_categories": ["市場動向", "国際情勢"],
            },
            TemplateType.DEFAULT: {
                "emphasis": ["バランス分析", "全般動向", "基本情報"],
                "sections": ["市場概況", "主要ニュース", "今後の注目点"],
                "tone": "中立",
                "priority_categories": ["市場動向", "経済指標", "企業業績"],
            },
        }

        return configs.get(template_type, configs[TemplateType.DEFAULT])
