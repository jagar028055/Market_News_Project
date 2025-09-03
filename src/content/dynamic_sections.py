# -*- coding: utf-8 -*-

"""
動的セクション生成システム
市場状況に応じてコンテンツセクションを動的に生成
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from .template_selector import TemplateType
from ..market_data.models import MarketSnapshot, MarketTrend


class DynamicSectionGenerator:
    """動的セクション生成クラス"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
    def generate_sections(self,
                         template_type: TemplateType,
                         market_snapshot: MarketSnapshot,
                         articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        テンプレートタイプと市場状況に応じてセクションを生成
        
        Args:
            template_type: テンプレートタイプ
            market_snapshot: 市場スナップショット
            articles: 記事リスト
        
        Returns:
            Dict[str, Any]: 生成されたセクションデータ
        """
        self.logger.info(f"動的セクション生成開始: {template_type.value}")
        
        sections = {
            "market_overview": self._generate_market_overview(market_snapshot),
            "key_indicators": self._generate_key_indicators(market_snapshot),
            "article_insights": self._generate_article_insights(articles, template_type),
            "risk_assessment": self._generate_risk_assessment(market_snapshot, articles),
            "template_specific": self._generate_template_specific_section(template_type, market_snapshot, articles)
        }
        
        # テンプレート特有の追加セクション
        if template_type == TemplateType.MARKET_CRASH:
            sections["emergency_analysis"] = self._generate_emergency_analysis(market_snapshot)
            sections["safe_haven_assets"] = self._generate_safe_haven_analysis(market_snapshot)
            
        elif template_type == TemplateType.FED_POLICY:
            sections["policy_impact"] = self._generate_policy_impact_analysis(market_snapshot, articles)
            sections["currency_outlook"] = self._generate_currency_outlook(market_snapshot)
            
        elif template_type == TemplateType.EARNINGS_SEASON:
            sections["sector_performance"] = self._generate_sector_performance(articles)
            sections["earnings_highlights"] = self._generate_earnings_highlights(articles)
            
        elif template_type == TemplateType.GEOPOLITICAL:
            sections["regional_impact"] = self._generate_regional_impact(articles)
            sections["risk_scenario"] = self._generate_risk_scenarios(market_snapshot, articles)
            
        elif template_type == TemplateType.CRYPTO_FOCUS:
            sections["crypto_analysis"] = self._generate_crypto_analysis(market_snapshot)
            sections["regulatory_watch"] = self._generate_regulatory_analysis(articles)
        
        self.logger.info(f"動的セクション生成完了: {len(sections)}個のセクション")
        return sections
    
    def _generate_market_overview(self, snapshot: MarketSnapshot) -> Dict[str, Any]:
        """市場概況セクション生成"""
        sentiment_labels = {
            MarketTrend.BULLISH: "強気",
            MarketTrend.BEARISH: "弱気", 
            MarketTrend.NEUTRAL: "中立",
            MarketTrend.VOLATILE: "高ボラティリティ"
        }
        
        # 主要指数のパフォーマンス
        top_performers = []
        worst_performers = []
        
        if snapshot.stock_indices:
            sorted_indices = sorted(snapshot.stock_indices, key=lambda x: x.change_percent, reverse=True)
            top_performers = sorted_indices[:3]
            worst_performers = sorted_indices[-3:]
        
        return {
            "timestamp": snapshot.timestamp.strftime("%Y年%m月%d日 %H:%M"),
            "overall_sentiment": sentiment_labels.get(snapshot.overall_sentiment, "不明"),
            "volatility_score": round(snapshot.volatility_score, 1),
            "risk_on_sentiment": "リスクオン" if snapshot.risk_on_sentiment else "リスクオフ",
            "total_instruments": len(snapshot.stock_indices + snapshot.currency_pairs + snapshot.commodities),
            "major_movers_count": len(snapshot.major_movers),
            "top_performers": [
                {"name": idx.name, "change": f"{idx.change_percent:+.2f}%"} 
                for idx in top_performers
            ],
            "worst_performers": [
                {"name": idx.name, "change": f"{idx.change_percent:+.2f}%"}
                for idx in worst_performers
            ]
        }
    
    def _generate_key_indicators(self, snapshot: MarketSnapshot) -> Dict[str, Any]:
        """主要指標セクション生成"""
        indicators = {}
        
        # 株価指数
        if snapshot.stock_indices:
            indicators["stock_indices"] = [
                {
                    "name": idx.name,
                    "value": f"{idx.current_price:,.0f}",
                    "change": f"{idx.change_percent:+.2f}%",
                    "trend": "↑" if idx.change > 0 else "↓" if idx.change < 0 else "→"
                }
                for idx in snapshot.stock_indices[:5]  # 上位5つ
            ]
        
        # 通貨ペア
        if snapshot.currency_pairs:
            indicators["currencies"] = [
                {
                    "name": pair.name,
                    "value": f"{pair.current_price:.4f}",
                    "change": f"{pair.change_percent:+.2f}%",
                    "trend": "↑" if pair.change > 0 else "↓" if pair.change < 0 else "→"
                }
                for pair in snapshot.currency_pairs[:4]  # 上位4つ
            ]
        
        # 商品
        if snapshot.commodities:
            indicators["commodities"] = [
                {
                    "name": commodity.name,
                    "value": f"${commodity.current_price:.2f}",
                    "change": f"{commodity.change_percent:+.2f}%",
                    "trend": "↑" if commodity.change > 0 else "↓" if commodity.change < 0 else "→"
                }
                for commodity in snapshot.commodities[:3]  # 上位3つ
            ]
        
        return indicators
    
    def _generate_article_insights(self, articles: List[Dict[str, Any]], template_type: TemplateType) -> Dict[str, Any]:
        """記事洞察セクション生成"""
        if not articles:
            return {"count": 0, "insights": []}
        
        # カテゴリ別集計
        category_counts = {}
        region_counts = {}
        
        for article in articles:
            category = article.get("category", "その他")
            region = article.get("region", "その他")
            
            category_counts[category] = category_counts.get(category, 0) + 1
            region_counts[region] = region_counts.get(region, 0) + 1
        
        # トップ記事を選定
        top_articles = sorted(
            articles,
            key=lambda x: abs(x.get("sentiment_score", 0)) if x.get("sentiment_score") is not None else 0,
            reverse=True
        )[:5]
        
        insights = []
        
        # カテゴリ分析
        if category_counts:
            top_category = max(category_counts, key=category_counts.get)
            insights.append({
                "type": "category_trend",
                "title": f"主要トピック: {top_category}",
                "description": f"{top_category}関連の記事が{category_counts[top_category]}件で最多",
                "data": dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True))
            })
        
        # 地域分析
        if region_counts:
            top_region = max(region_counts, key=region_counts.get)
            insights.append({
                "type": "regional_focus",
                "title": f"注目地域: {top_region}",
                "description": f"{top_region}関連の記事が{region_counts[top_region]}件",
                "data": dict(sorted(region_counts.items(), key=lambda x: x[1], reverse=True))
            })
        
        return {
            "count": len(articles),
            "category_distribution": category_counts,
            "region_distribution": region_counts,
            "insights": insights,
            "top_articles": [
                {
                    "title": article.get("title", "")[:100],
                    "category": article.get("category", "その他"),
                    "region": article.get("region", "その他"),
                    "sentiment": article.get("sentiment_label", "中立")
                }
                for article in top_articles
            ]
        }
    
    def _generate_risk_assessment(self, snapshot: MarketSnapshot, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """リスク評価セクション生成"""
        risk_level = "低"
        risk_factors = []
        
        # ボラティリティによるリスク評価
        if snapshot.volatility_score >= 70:
            risk_level = "極高"
            risk_factors.append("市場ボラティリティが極めて高い水準")
        elif snapshot.volatility_score >= 50:
            risk_level = "高"
            risk_factors.append("市場ボラティリティが高い水準")
        elif snapshot.volatility_score >= 30:
            risk_level = "中"
            risk_factors.append("市場ボラティリティが中程度")
        
        # センチメントによるリスク評価
        if snapshot.overall_sentiment == MarketTrend.BEARISH:
            risk_factors.append("市場センチメントが悲観的")
        elif snapshot.overall_sentiment == MarketTrend.VOLATILE:
            risk_factors.append("市場が不安定な状況")
        
        # 大幅下落の確認
        major_declines = [
            idx for idx in snapshot.stock_indices 
            if idx.change_percent <= -3.0
        ]
        if major_declines:
            risk_factors.append(f"{len(major_declines)}の主要指数で大幅下落")
        
        # 記事からリスクキーワードを検出
        risk_keywords = ["戦争", "紛争", "危機", "破綻", "暴落", "パニック"]
        risk_articles = []
        
        for article in articles:
            title = article.get("title", "").lower()
            summary = article.get("summary", "").lower()
            text = f"{title} {summary}"
            
            if any(keyword in text for keyword in risk_keywords):
                risk_articles.append(article.get("title", "")[:80])
        
        if risk_articles:
            risk_factors.append(f"地政学・経済リスク関連記事が{len(risk_articles)}件")
        
        return {
            "risk_level": risk_level,
            "volatility_score": round(snapshot.volatility_score, 1),
            "risk_factors": risk_factors,
            "risk_articles": risk_articles[:3],  # 最大3件
            "recommendation": self._get_risk_recommendation(risk_level, snapshot)
        }
    
    def _get_risk_recommendation(self, risk_level: str, snapshot: MarketSnapshot) -> str:
        """リスクレベルに応じた推奨事項"""
        recommendations = {
            "極高": "ポジション縮小と安全資産への避難を検討",
            "高": "リスク管理の強化と慎重な投資判断が必要",
            "中": "適度な注意を払いつつ、機会を見極める",
            "低": "比較的安定した環境での投資機会を模索"
        }
        return recommendations.get(risk_level, "市場動向を注意深く監視")
    
    def _generate_template_specific_section(self, template_type: TemplateType, snapshot: MarketSnapshot, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """テンプレート特有のセクション生成"""
        if template_type == TemplateType.MARKET_CRASH:
            return {"type": "emergency", "message": "緊急市場分析モードが有効です"}
        elif template_type == TemplateType.FED_POLICY:
            return {"type": "policy", "message": "金融政策分析に重点を置いています"}
        elif template_type == TemplateType.EARNINGS_SEASON:
            return {"type": "earnings", "message": "決算シーズン分析モードです"}
        elif template_type == TemplateType.GEOPOLITICAL:
            return {"type": "geopolitical", "message": "地政学リスク分析に注力しています"}
        elif template_type == TemplateType.CRYPTO_FOCUS:
            return {"type": "crypto", "message": "仮想通貨市場に特化した分析です"}
        else:
            return {"type": "default", "message": "総合的な市場分析を提供します"}
    
    def _generate_emergency_analysis(self, snapshot: MarketSnapshot) -> Dict[str, Any]:
        """緊急市場分析セクション"""
        emergency_indicators = []
        
        # VIX相当のボラティリティ指標
        if snapshot.volatility_score >= 80:
            emergency_indicators.append("ボラティリティが危険水域に到達")
        
        # 複数市場での同時下落
        declining_markets = sum(1 for idx in snapshot.stock_indices if idx.change_percent < -2.0)
        if declining_markets >= 3:
            emergency_indicators.append(f"{declining_markets}の主要市場で同時下落")
        
        return {
            "alert_level": "高" if len(emergency_indicators) >= 2 else "中",
            "indicators": emergency_indicators,
            "timestamp": snapshot.timestamp.isoformat()
        }
    
    def _generate_safe_haven_analysis(self, snapshot: MarketSnapshot) -> Dict[str, Any]:
        """安全資産分析セクション"""
        safe_havens = []
        
        # 金の動向
        gold_data = next((c for c in snapshot.commodities if "gold" in c.name.lower() or "金" in c.name), None)
        if gold_data:
            safe_havens.append({
                "asset": "金",
                "performance": f"{gold_data.change_percent:+.2f}%",
                "status": "買われている" if gold_data.change_percent > 0 else "売られている"
            })
        
        # 円の動向（安全通貨として）
        jpy_pairs = [p for p in snapshot.currency_pairs if "JPY" in p.symbol or "円" in p.name]
        for pair in jpy_pairs:
            safe_havens.append({
                "asset": pair.name,
                "performance": f"{pair.change_percent:+.2f}%",
                "status": "円高" if "JPY" in pair.symbol and pair.change_percent < 0 else "円安"
            })
        
        return {"safe_havens": safe_havens}
    
    def _generate_policy_impact_analysis(self, snapshot: MarketSnapshot, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """金融政策影響分析"""
        policy_keywords = ["金利", "利上げ", "利下げ", "量的緩和", "金融政策"]
        policy_articles = [
            article for article in articles
            if any(keyword in (article.get("title", "") + " " + article.get("summary", "")).lower() 
                  for keyword in policy_keywords)
        ]
        
        return {
            "policy_related_articles": len(policy_articles),
            "market_reaction": "強い反応" if snapshot.volatility_score > 40 else "穏やか"
        }
    
    def _generate_currency_outlook(self, snapshot: MarketSnapshot) -> Dict[str, Any]:
        """通貨見通し分析"""
        currency_trends = []
        
        for pair in snapshot.currency_pairs[:4]:
            trend = "上昇" if pair.change_percent > 0.1 else "下落" if pair.change_percent < -0.1 else "横ばい"
            currency_trends.append({
                "pair": pair.name,
                "trend": trend,
                "strength": "強い" if abs(pair.change_percent) > 0.5 else "弱い"
            })
        
        return {"currency_trends": currency_trends}
    
    def _generate_sector_performance(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """セクターパフォーマンス分析"""
        # 記事からセクター関連キーワードを抽出
        sector_keywords = {
            "テクノロジー": ["AI", "半導体", "ソフトウェア", "テック"],
            "金融": ["銀行", "保険", "証券"],
            "エネルギー": ["石油", "ガス", "エネルギー"],
            "ヘルスケア": ["製薬", "医療", "バイオ"]
        }
        
        sector_mentions = {sector: 0 for sector in sector_keywords}
        
        for article in articles:
            text = (article.get("title", "") + " " + article.get("summary", "")).lower()
            for sector, keywords in sector_keywords.items():
                if any(keyword.lower() in text for keyword in keywords):
                    sector_mentions[sector] += 1
        
        return {"sector_mentions": sector_mentions}
    
    def _generate_earnings_highlights(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """決算ハイライト"""
        earnings_keywords = ["決算", "業績", "売上", "利益", "EPS"]
        earnings_articles = [
            article for article in articles
            if any(keyword in (article.get("title", "") + " " + article.get("summary", "")).lower()
                  for keyword in earnings_keywords)
        ]
        
        return {
            "earnings_articles_count": len(earnings_articles),
            "highlights": [article.get("title", "")[:100] for article in earnings_articles[:5]]
        }
    
    def _generate_regional_impact(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """地域影響分析"""
        region_distribution = {}
        for article in articles:
            region = article.get("region", "その他")
            region_distribution[region] = region_distribution.get(region, 0) + 1
        
        return {"region_distribution": region_distribution}
    
    def _generate_risk_scenarios(self, snapshot: MarketSnapshot, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """リスクシナリオ分析"""
        risk_scenarios = []
        
        if snapshot.volatility_score > 60:
            risk_scenarios.append("高ボラティリティ継続シナリオ")
        
        geopolitical_articles = len([
            a for a in articles 
            if any(keyword in (a.get("title", "") + " " + a.get("summary", "")).lower()
                  for keyword in ["戦争", "制裁", "貿易", "選挙"])
        ])
        
        if geopolitical_articles > 0:
            risk_scenarios.append("地政学リスク拡大シナリオ")
        
        return {"scenarios": risk_scenarios}
    
    def _generate_crypto_analysis(self, snapshot: MarketSnapshot) -> Dict[str, Any]:
        """仮想通貨分析"""
        # この実装は仮想通貨データがsnapshotに含まれている場合に機能
        # 実際の実装では仮想通貨特有のデータ構造が必要
        return {
            "analysis": "仮想通貨市場の動向を分析中",
            "volatility": "高い" if snapshot.volatility_score > 50 else "通常"
        }
    
    def _generate_regulatory_analysis(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """規制動向分析"""
        regulatory_keywords = ["規制", "法律", "承認", "禁止", "政策"]
        regulatory_articles = [
            article for article in articles
            if any(keyword in (article.get("title", "") + " " + article.get("summary", "")).lower()
                  for keyword in regulatory_keywords)
        ]
        
        return {
            "regulatory_articles_count": len(regulatory_articles),
            "impact": "高い" if len(regulatory_articles) > 2 else "限定的"
        }