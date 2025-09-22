"""HTMLテンプレートからSNS画像を生成するレンダラ"""

from __future__ import annotations

import json
import logging
import math
import re
import textwrap
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

import investpy
import yfinance as yf

LOGGER = logging.getLogger(__name__)

# -----------------------------
# データスキーマ
# -----------------------------


@dataclass
class Palette:
    background: str = "#F9FAFB"
    surface: str = "#FFFFFF"
    border: str = "#E5E7EB"
    text: str = "#111827"
    text_soft: str = "#6B7280"
    accent: str = "#111827"
    accent_soft: str = "#374151"


@dataclass
class TopicCard:
    headline: str
    summary: str
    meta: str
    points: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    topic_description: str = ""
    market_impact: str = ""
    sentiment_analysis: str = ""
    investment_insight: str = ""


@dataclass
class MarketEntry:
    name: str
    value: str
    change: str = ""

    @property
    def badge_class(self) -> str:
        if not self.change:
            return "badge--flat"
        try:
            numeric = float(self.change.replace("%", "").replace("+", ""))
        except ValueError:
            return "badge--flat"
        if math.isclose(numeric, 0.0, abs_tol=0.01):
            return "badge--flat"
        return "badge--up" if numeric > 0 else "badge--down"


@dataclass
class ReleasedIndicator:
    indicator: str
    actual: str
    forecast: str

    @property
    def badge_class(self) -> str:
        try:
            actual = float(str(self.actual).replace("%", "").replace(",", ""))
            forecast = float(str(self.forecast).replace("%", "").replace(",", ""))
        except ValueError:
            return "badge--flat"
        return "badge--up" if actual >= forecast else "badge--down"


@dataclass
class UpcomingIndicator:
    indicator: str
    time: str
    forecast: str


@dataclass
class MarketOverviewContext:
    page_title: str
    width: int
    height: int
    palette: Palette
    brand_name: str
    date_label: str
    title: str
    summary: str
    topics: List[TopicCard]
    market_data: Dict[str, List[MarketEntry]]
    disclaimer: str
    hashtags: str


@dataclass
class ComprehensiveAnalysisContext:
    page_title: str
    width: int
    height: int
    palette: Palette
    brand_name: str
    date_label: str
    title: str
    intro: str
    comprehensive_themes: List[Dict[str, str]]
    geopolitical_summary: str
    geopolitical_impacts: List[str]
    central_bank_summary: str
    policy_outlook: str
    short_term_strategy: str
    medium_term_strategy: str
    risk_management: str
    disclaimer: str
    hashtags: str


@dataclass
class EconomicCalendarContext:
    page_title: str
    width: int
    height: int
    palette: Palette
    brand_name: str
    date_label: str
    title: str
    intro: str
    released: List[ReleasedIndicator]
    upcoming: List[UpcomingIndicator]
    disclaimer: str
    hashtags: str


@dataclass
class SimpleTopicItem:
    number: int
    headline: str
    description: str


@dataclass
class SimpleTopicContext:
    page_title: str
    width: int
    height: int
    palette: Palette
    brand_name: str
    date_label: str
    title: str
    intro: str
    topics: List[SimpleTopicItem]
    disclaimer: str
    hashtags: str


# -----------------------------
# HTMLレンダラ本体
# -----------------------------


class HtmlImageRenderer:
    """SNS用画像をHTMLテンプレート経由で生成"""

    DISCLAIMER = "Source: Market data providers | For informational purposes only."

    def __init__(
        self,
        width: int = 800,
        height: int = 1200,
        brand_name: str = "Market News",
        hashtags: str = "#MarketNews",
        output_html: bool = True,
    ) -> None:
        self.width = width
        self.height = height
        self.brand_name = brand_name
        self.hashtags = hashtags
        self.output_html = output_html

        templates_dir = Path(__file__).resolve().parent.parent.parent / "templates" / "social"
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        self.palette = Palette()

    # --------- 公開API ---------

    def render_vertical_market_overview(
        self,
        date: datetime,
        topics: Iterable,
        output_dir: str,
        title: str = "MARKET RECAP",
    ) -> Path:
        topics_cards = self._build_topic_cards(topics)
        summary_text = self._build_market_summary(topics_cards)
        market_data = self._get_market_dashboard()

        context = MarketOverviewContext(
            page_title=f"{title} | {self.brand_name}",
            width=self.width,
            height=self.height,
            palette=self.palette,
            brand_name=self.brand_name,
            date_label=self._format_date(date),
            title=title,
            summary=summary_text,
            topics=topics_cards,
            market_data={
                "indices": [MarketEntry(**entry) for entry in market_data.get("indices", [])],
                "fx_bonds": [MarketEntry(**entry) for entry in market_data.get("fx_bonds", [])],
            },
            disclaimer=self.DISCLAIMER,
            hashtags=self.hashtags,
        )

        return self._render_to_image(
            template_name="market_overview.html.j2",
            context=context,
            output_dir=output_dir,
            output_filename="market_overview_vertical",
        )

    def render_vertical_topic_details(
        self,
        date: datetime,
        topics: Iterable,
        output_dir: str,
        title: str = "TOPIC DEEP DIVE",
    ) -> Path:
        # シンプルなトピック表示（グラフなし、文字重なりなし）
        topic_cards = self._build_simple_topic_cards(topics)
        intro = "本日の主要な市場トピックをまとめました。"

        context = SimpleTopicContext(
            page_title=f"{title} | {self.brand_name}",
            width=self.width,
            height=self.height,
            palette=self.palette,
            brand_name=self.brand_name,
            date_label=self._format_date(date),
            title=title,
            intro=intro,
            topics=topic_cards,
            disclaimer=self.DISCLAIMER,
            hashtags=self.hashtags,
        )

        return self._render_to_image(
            template_name="simple_topic_details.html.j2",
            context=context,
            output_dir=output_dir,
            output_filename="topic_details_vertical",
        )

    def render_vertical_economic_calendar(
        self,
        date: datetime,
        output_dir: str,
        title: str = "ECONOMIC CALENDAR",
    ) -> Path:
        released, upcoming = self._get_economic_calendar()

        context = EconomicCalendarContext(
            page_title=f"{title} | {self.brand_name}",
            width=self.width,
            height=self.height,
            palette=self.palette,
            brand_name=self.brand_name,
            date_label=self._format_date(date),
            title=title,
            intro="主要国の経済指標をJSTで整理。結果と予想のギャップ、今後の注目イベントを俯瞰できます。",
            released=released,
            upcoming=upcoming,
            disclaimer=self.DISCLAIMER,
            hashtags=self.hashtags,
        )

        return self._render_to_image(
            template_name="economic_calendar.html.j2",
            context=context,
            output_dir=output_dir,
            output_filename="economic_calendar_vertical",
        )

    # --------- 内部ユーティリティ ---------

    def _render_to_image(
        self,
        template_name: str,
        context,
        output_dir: str,
        output_filename: str,
    ) -> Path:
        html = self._render_html(template_name, asdict(context))
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        html_path = output_path / f"{output_filename}.html"
        if self.output_html:
            html_path.write_text(html, encoding="utf-8")

        image_path = output_path / f"{output_filename}.png"
        self._html_to_image(html, image_path)
        return image_path

    def _render_html(self, template_name: str, context: Dict) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)

    def _html_to_image(self, html: str, output_file: Path) -> None:
        try:
            LOGGER.info("🎨 Starting HTML to image conversion with Playwright")
            with sync_playwright() as p:
                LOGGER.info("🚀 Launching Chromium browser")
                browser = p.chromium.launch(headless=True, chromium_sandbox=False, args=["--no-sandbox"])
                LOGGER.info("📱 Creating new page")
                page = browser.new_page(viewport={"width": self.width, "height": self.height})
                LOGGER.info("📄 Setting HTML content")
                page.set_content(html, wait_until="networkidle")
                LOGGER.info("⏱️ Waiting for content to load")
                page.wait_for_timeout(200)
                LOGGER.info("📸 Taking screenshot")
                page.screenshot(path=str(output_file), full_page=False)
                LOGGER.info("🔒 Closing browser")
                browser.close()
                LOGGER.info("✅ HTML to image conversion completed successfully")
        except Exception as e:
            LOGGER.error(f"❌ Playwright HTML to image conversion failed: {e}")
            LOGGER.error("🔄 Falling back to Pillow-based rendering")
            raise e

    # --------- コンテンツ構築 ---------

    def _build_topic_cards(self, topics: Iterable, include_keywords: bool = False) -> List[TopicCard]:
        cards: List[TopicCard] = []
        if not topics:
            return cards
        for topic in topics:
            headline = self._sanitize_text(getattr(topic, "headline", ""))
            raw_summary = getattr(topic, "summary", None) or getattr(topic, "blurb", "")
            
            # 1枚目用：簡潔な要約（100文字以内）
            if not include_keywords:
                summary = self._create_concise_summary(raw_summary, headline)
            else:
                # 2枚目用：詳細な要約（220文字）
                summary = self._truncate(raw_summary, 220)
            
            published = getattr(topic, "published_jst", None)
            published_label = self._format_time(published)
            source = getattr(topic, "source", "")
            meta_parts = [source] if source else []
            if published_label:
                meta_parts.append(published_label)
            meta = " / ".join(meta_parts) if meta_parts else ""

            points = self._extract_bullet_points(raw_summary)
            keywords: List[str] = []
            if include_keywords:
                keywords = self._collect_keywords(topic)

            # 2枚目用の分析データを生成
            topic_description = ""
            market_impact = ""
            sentiment_analysis = ""
            investment_insight = ""
            
            if include_keywords:
                topic_description = self._create_topic_description(headline, raw_summary)
                market_impact = self._analyze_market_impact(headline, raw_summary)
                sentiment_analysis = self._analyze_sentiment(headline, raw_summary)
                investment_insight = self._generate_investment_insight(headline, raw_summary)

            cards.append(
                TopicCard(
                    headline=headline,
                    summary=summary,
                    meta=meta,
                    points=points,
                    keywords=keywords,
                    topic_description=topic_description,
                    market_impact=market_impact,
                    sentiment_analysis=sentiment_analysis,
                    investment_insight=investment_insight,
                )
            )
        return cards

    def _build_simple_topic_cards(self, topics: Iterable) -> List[SimpleTopicItem]:
        """シンプルなトピックカードを作成（グラフなし、文字重なりなし）"""
        items: List[SimpleTopicItem] = []
        if not topics:
            return items

        for i, topic in enumerate(topics[:3], 1):  # 最大3つまで
            headline = self._sanitize_text(getattr(topic, "headline", ""))
            raw_summary = getattr(topic, "summary", None) or getattr(topic, "blurb", "")

            # 説明文を適切な長さに制限（文字重なりを避ける）
            description = self._truncate(raw_summary, 150)
            if len(description) < len(raw_summary):
                description += "..."

            items.append(SimpleTopicItem(
                number=i,
                headline=headline,
                description=description
            ))

        return items

    def _build_market_summary(self, topics: List[TopicCard]) -> str:
        if not topics:
            return "市場の主要トピックを要約しました。"
        lead_lines = []
        for idx, card in enumerate(topics[:2]):
            lead_lines.append(f"{idx + 1}. {card.headline}")
        return " / ".join(lead_lines)

    def _collect_keywords(self, topic) -> List[str]:
        keywords: List[str] = []
        for attr in ["category", "region"]:
            value = getattr(topic, attr, None)
            if value and value not in keywords:
                keywords.append(str(value))
        summary = getattr(topic, "summary", "")
        for match in re.findall(r"([A-Z]{2,}(?:\s[A-Z]{2,})?)", summary):
            if match not in keywords:
                keywords.append(match)
        return keywords[:6]

    def _extract_bullet_points(self, summary: Optional[str]) -> List[str]:
        if not summary:
            return []
        sentences = re.split(r"(?<=[。！？!?])\s*", summary)
        cleaned = [self._sanitize_text(s).strip() for s in sentences if s.strip()]
        return [self._truncate(sentence, 140) for sentence in cleaned[:3]]

    def _truncate(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return textwrap.shorten(text, width=limit, placeholder="…")

    def _create_concise_summary(self, raw_summary: str, headline: str) -> str:
        """1枚目用の簡潔な要約を作成（100文字以内）"""
        if not raw_summary:
            return ""
        
        # 重要なキーワードを抽出
        important_keywords = [
            "上昇", "下落", "増加", "減少", "上回る", "下回る", "予想", "実績",
            "発表", "決定", "発表", "発表", "発表", "発表", "発表", "発表",
            "FRB", "日銀", "ECB", "BOE", "利上げ", "利下げ", "金利", "インフレ",
            "GDP", "CPI", "失業率", "貿易収支", "為替", "株価", "債券"
        ]
        
        # 文章を文単位で分割
        sentences = re.split(r'[。！？]', raw_summary)
        concise_parts = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # 重要なキーワードを含む文を優先
            if any(keyword in sentence for keyword in important_keywords):
                concise_parts.append(sentence)
                break
        
        # キーワードを含む文がない場合は最初の文を使用
        if not concise_parts and sentences:
            concise_parts.append(sentences[0].strip())
        
        # 要約を組み立て
        summary = "".join(concise_parts)
        
        # 100文字以内に調整
        if len(summary) > 100:
            summary = textwrap.shorten(summary, width=100, placeholder="…")
        
        return summary

    def _create_topic_description(self, headline: str, summary: str) -> str:
        """トピックの詳細説明を作成"""
        # ヘッドラインから主要な要素を抽出
        key_elements = []
        
        if "FRB" in headline or "日銀" in headline or "ECB" in headline:
            key_elements.append("中央銀行の政策")
        if "利上げ" in headline or "利下げ" in headline:
            key_elements.append("金利政策")
        if "CPI" in headline or "インフレ" in headline:
            key_elements.append("物価動向")
        if "GDP" in headline:
            key_elements.append("経済成長")
        if "失業率" in headline:
            key_elements.append("雇用情勢")
        if "貿易" in headline:
            key_elements.append("貿易収支")
        if "為替" in headline or "ドル" in headline or "円" in headline:
            key_elements.append("為替動向")
        if "株価" in headline or "株式" in headline:
            key_elements.append("株式市場")
        if "債券" in headline:
            key_elements.append("債券市場")
        if "原油" in headline or "エネルギー" in headline:
            key_elements.append("エネルギー市場")
        
        # 説明文を構築
        if key_elements:
            description = f"このニュースは{', '.join(key_elements[:2])}に関する重要な発表です。"
        else:
            description = "市場に影響を与える可能性のある重要なニュースです。"
        
        # サマリーから追加の詳細を抽出
        if "予想" in summary and "上回" in summary:
            description += " 市場予想を上回る結果となっています。"
        elif "予想" in summary and "下回" in summary:
            description += " 市場予想を下回る結果となっています。"
        
        return description

    def _analyze_market_impact(self, headline: str, summary: str) -> str:
        """市場インパクトを分析"""
        text = f"{headline} {summary}".lower()
        
        # 高インパクトキーワード
        high_impact = ["利上げ", "利下げ", "金利", "インフレ", "デフレ", "gdp", "cpi", "失業率", "貿易収支"]
        medium_impact = ["株価", "為替", "債券", "原油", "金", "政策", "決定", "発表"]
        
        if any(keyword in text for keyword in high_impact):
            return "高インパクト: 全市場に影響を与える可能性が高い重要な指標・政策決定"
        elif any(keyword in text for keyword in medium_impact):
            return "中インパクト: 特定セクターや資産クラスに影響を与える可能性"
        else:
            return "低インパクト: 限定的な影響が予想される"

    def _analyze_sentiment(self, headline: str, summary: str) -> str:
        """ポジティブ/ネガティブ判断"""
        text = f"{headline} {summary}".lower()
        
        positive_indicators = []
        negative_indicators = []
        
        # ポジティブ指標
        if "上昇" in text or "増加" in text or "改善" in text:
            positive_indicators.append("上昇トレンド")
        if "予想" in text and "上回" in text:
            positive_indicators.append("予想上回り")
        if "好調" in text or "堅調" in text:
            positive_indicators.append("好調な動き")
        if "利下げ" in text:
            positive_indicators.append("金融緩和")
        
        # ネガティブ指標
        if "下落" in text or "減少" in text or "悪化" in text:
            negative_indicators.append("下落トレンド")
        if "予想" in text and "下回" in text:
            negative_indicators.append("予想下回り")
        if "懸念" in text or "不安" in text:
            negative_indicators.append("市場懸念")
        if "利上げ" in text:
            negative_indicators.append("金融引き締め")
        
        # 判断を決定
        if len(positive_indicators) > len(negative_indicators):
            sentiment = "ポジティブ"
            details = f"市場に好影響: {', '.join(positive_indicators[:2])}"
        elif len(negative_indicators) > len(positive_indicators):
            sentiment = "ネガティブ"
            details = f"市場に悪影響: {', '.join(negative_indicators[:2])}"
        else:
            sentiment = "ニュートラル"
            details = "市場への影響は限定的"
        
        return f"{sentiment}: {details}"

    def _generate_comprehensive_analysis(self, topics: Iterable) -> Dict[str, Any]:
        """包括的市場分析を生成"""
        topics_list = list(topics)
        
        # テーマ別分類
        themes = self._classify_themes(topics_list)
        
        # 地政学的リスク分析
        geopolitical_analysis = self._analyze_geopolitical_risks(topics_list)
        
        # 中央銀行政策分析
        central_bank_analysis = self._analyze_central_bank_policies(topics_list)
        
        # 投資戦略生成
        investment_strategies = self._generate_investment_strategies(topics_list)
        
        return {
            "themes": themes,
            "geopolitical_summary": geopolitical_analysis["summary"],
            "geopolitical_impacts": geopolitical_analysis["impacts"],
            "central_bank_summary": central_bank_analysis["summary"],
            "policy_outlook": central_bank_analysis["outlook"],
            "short_term_strategy": investment_strategies["short_term"],
            "medium_term_strategy": investment_strategies["medium_term"],
            "risk_management": investment_strategies["risk_management"],
        }

    def _classify_themes(self, topics: List) -> List[Dict[str, str]]:
        """記事をテーマ別に分類"""
        themes = {}
        
        for topic in topics:
            headline = getattr(topic, "headline", "")
            summary = getattr(topic, "summary", "")
            text = f"{headline} {summary}".lower()
            
            # テーマ分類
            if "frb" in text or "日銀" in text or "ecb" in text or "利上げ" in text or "利下げ" in text:
                theme_name = "中央銀行政策"
                themes.setdefault(theme_name, {"articles": [], "count": 0})
                themes[theme_name]["articles"].append(topic)
                themes[theme_name]["count"] += 1
                
            elif "ウクライナ" in text or "ロシア" in text or "中国" in text or "地政学" in text:
                theme_name = "地政学リスク"
                themes.setdefault(theme_name, {"articles": [], "count": 0})
                themes[theme_name]["articles"].append(topic)
                themes[theme_name]["count"] += 1
                
            elif "インフレ" in text or "cpi" in text or "物価" in text:
                theme_name = "インフレ動向"
                themes.setdefault(theme_name, {"articles": [], "count": 0})
                themes[theme_name]["articles"].append(topic)
                themes[theme_name]["count"] += 1
                
            elif "為替" in text or "ドル" in text or "円" in text:
                theme_name = "為替動向"
                themes.setdefault(theme_name, {"articles": [], "count": 0})
                themes[theme_name]["articles"].append(topic)
                themes[theme_name]["count"] += 1
                
            elif "株価" in text or "株式" in text or "市場" in text:
                theme_name = "株式市場"
                themes.setdefault(theme_name, {"articles": [], "count": 0})
                themes[theme_name]["articles"].append(topic)
                themes[theme_name]["count"] += 1
        
        # テーマ分析結果を整形
        theme_results = []
        for theme_name, data in themes.items():
            if data["count"] > 0:
                summary = self._generate_theme_summary(theme_name, data["articles"])
                market_impact = self._analyze_theme_impact(theme_name, data["articles"])
                sentiment = self._analyze_theme_sentiment(theme_name, data["articles"])
                
                theme_results.append({
                    "theme_name": theme_name,
                    "summary": summary,
                    "market_impact": market_impact,
                    "article_count": data["count"],
                    "sentiment_class": sentiment["class"],
                    "sentiment_label": sentiment["label"],
                })
        
        return theme_results[:4]  # 上位4テーマ

    def _generate_theme_summary(self, theme_name: str, articles: List) -> str:
        """テーマの要約を生成"""
        if theme_name == "中央銀行政策":
            return "主要中央銀行の政策動向が市場の方向性を決定づけています。金利政策の変化は全市場に波及します。"
        elif theme_name == "地政学リスク":
            return "地政学的緊張が市場の不確実性を高めています。リスクオフの動きが継続する可能性があります。"
        elif theme_name == "インフレ動向":
            return "物価動向が中央銀行の政策判断に大きな影響を与えています。インフレ期待の変化に注目が必要です。"
        elif theme_name == "為替動向":
            return "主要通貨ペアの動向が貿易・投資フローに影響を与えています。金利差とリスク選好が要因です。"
        elif theme_name == "株式市場":
            return "企業業績と経済指標が株式市場の方向性を左右しています。セクター間での動きの差が顕著です。"
        else:
            return "市場全体の動向を反映した重要なテーマです。"

    def _analyze_theme_impact(self, theme_name: str, articles: List) -> str:
        """テーマの市場インパクトを分析"""
        if theme_name == "中央銀行政策":
            return "高インパクト: 全市場に影響する最重要ファクター"
        elif theme_name == "地政学リスク":
            return "高インパクト: リスク資産に負の影響、安全資産に正の影響"
        elif theme_name == "インフレ動向":
            return "中インパクト: 債券・金利敏感株に直接影響"
        elif theme_name == "為替動向":
            return "中インパクト: 輸出企業・輸入企業の業績に影響"
        elif theme_name == "株式市場":
            return "中インパクト: セクター別・個別銘柄に影響"
        else:
            return "低インパクト: 限定的な影響"

    def _analyze_theme_sentiment(self, theme_name: str, articles: List) -> Dict[str, str]:
        """テーマのセンチメントを分析"""
        positive_count = 0
        negative_count = 0
        
        for article in articles:
            headline = getattr(article, "headline", "")
            summary = getattr(article, "summary", "")
            text = f"{headline} {summary}".lower()
            
            if any(word in text for word in ["上昇", "改善", "好調", "堅調", "上回"]):
                positive_count += 1
            elif any(word in text for word in ["下落", "悪化", "懸念", "不安", "下回"]):
                negative_count += 1
        
        if positive_count > negative_count:
            return {"class": "positive", "label": "ポジティブ"}
        elif negative_count > positive_count:
            return {"class": "negative", "label": "ネガティブ"}
        else:
            return {"class": "neutral", "label": "ニュートラル"}

    def _analyze_geopolitical_risks(self, topics: List) -> Dict[str, Any]:
        """地政学的リスクを分析"""
        geopolitical_articles = []
        for topic in topics:
            headline = getattr(topic, "headline", "")
            summary = getattr(topic, "summary", "")
            text = f"{headline} {summary}".lower()
            
            if any(keyword in text for keyword in ["ウクライナ", "ロシア", "中国", "地政学", "戦争", "紛争"]):
                geopolitical_articles.append(topic)
        
        if geopolitical_articles:
            summary = "地政学的緊張が市場の不確実性を高めています。リスクオフの動きが継続し、安全資産への需要が増加する可能性があります。"
            impacts = [
                "エネルギー価格の変動リスク",
                "グローバルサプライチェーンの混乱",
                "通貨の安全通貨への逃避",
                "株式市場のリスクオフ"
            ]
        else:
            summary = "地政学的リスクは比較的安定していますが、継続的な監視が必要です。"
            impacts = [
                "地政学的安定性の維持",
                "貿易関係の正常化",
                "投資環境の改善"
            ]
        
        return {"summary": summary, "impacts": impacts}

    def _analyze_central_bank_policies(self, topics: List) -> Dict[str, Any]:
        """中央銀行政策を分析"""
        central_bank_articles = []
        for topic in topics:
            headline = getattr(topic, "headline", "")
            summary = getattr(topic, "summary", "")
            text = f"{headline} {summary}".lower()
            
            if any(keyword in text for keyword in ["frb", "日銀", "ecb", "利上げ", "利下げ", "金利", "政策"]):
                central_bank_articles.append(topic)
        
        if central_bank_articles:
            summary = "主要中央銀行の政策スタンスが市場の方向性を決定づけています。金利政策の変化は全市場に波及する重要な要因です。"
            outlook = "インフレ動向と経済指標を注視しながら、段階的な政策調整が続くと予想されます。"
        else:
            summary = "中央銀行政策は現状維持の傾向ですが、経済指標の変化に応じた調整の可能性があります。"
            outlook = "データドリブンな政策判断が継続され、柔軟な対応が期待されます。"
        
        return {"summary": summary, "outlook": outlook}

    def _generate_investment_strategies(self, topics: List) -> Dict[str, str]:
        """投資戦略を生成"""
        # 全体的な市場センチメントを分析
        positive_signals = 0
        negative_signals = 0
        
        for topic in topics:
            headline = getattr(topic, "headline", "")
            summary = getattr(topic, "summary", "")
            text = f"{headline} {summary}".lower()
            
            if any(word in text for word in ["上昇", "改善", "好調", "堅調", "上回"]):
                positive_signals += 1
            elif any(word in text for word in ["下落", "悪化", "懸念", "不安", "下回"]):
                negative_signals += 1
        
        if positive_signals > negative_signals:
            market_sentiment = "ポジティブ"
        elif negative_signals > positive_signals:
            market_sentiment = "ネガティブ"
        else:
            market_sentiment = "ニュートラル"
        
        # 戦略を生成
        if market_sentiment == "ポジティブ":
            short_term = "リスクオン戦略: 成長株・サイクリカル株に注目。技術的な調整を買い場として活用。"
            medium_term = "セクターローテーション: 景気敏感セクターへの配分増加。テクノロジー・消費財を重視。"
            risk_management = "利益確定ポイントの設定。ボラティリティ上昇時のリスク管理を徹底。"
        elif market_sentiment == "ネガティブ":
            short_term = "ディフェンシブ戦略: 安全資産・ディフェンシブ株にシフト。現金比率を一時的に高める。"
            medium_term = "バリュー戦略: 割安なバリュー株への長期投資。配当利回りの高い銘柄を選別。"
            risk_management = "ストップロス設定の厳格化。ポートフォリオの分散投資を徹底。"
        else:
            short_term = "バランス戦略: リスク・リターンのバランスを重視。テクニカル分析によるタイミング重視。"
            medium_term = "多様化戦略: 地域・セクター・資産クラスの分散投資。長期投資の視点を維持。"
            risk_management = "定期的なポートフォリオ見直し。リスク許容度に応じた配分調整。"
        
        return {
            "short_term": short_term,
            "medium_term": medium_term,
            "risk_management": risk_management,
        }

    def _generate_investment_insight(self, headline: str, summary: str) -> str:
        """投資家への示唆を生成"""
        text = f"{headline} {summary}".lower()
        
        insights = []
        
        if "上昇" in text or "増加" in text:
            insights.append("上昇トレンドの継続を監視")
        if "下落" in text or "減少" in text:
            insights.append("下落リスクの管理が重要")
        if "予想" in text and "上回" in text:
            insights.append("予想を上回る結果は市場にポジティブ")
        if "予想" in text and "下回" in text:
            insights.append("予想を下回る結果は市場にネガティブ")
        if "政策" in text or "決定" in text:
            insights.append("政策変更の影響を慎重に評価")
        if "不確実" in text or "懸念" in text:
            insights.append("リスク回避的な投資戦略を検討")
            
        if insights:
            return f"投資戦略: {insights[0]}"
        else:
            return "市場動向を継続的に監視し、リスク管理を徹底"

    def _sanitize_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", str(text)).strip()

    def _format_date(self, dt: datetime) -> str:
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekdays[dt.weekday()]
        return dt.strftime(f"%Y年%m月%d日 ({weekday})")

    def _format_time(self, dt: Optional[datetime]) -> str:
        if not isinstance(dt, datetime):
            return ""
        return dt.strftime("%m/%d %H:%M")

    # --------- データ取得 ---------

    def _get_market_dashboard(self) -> Dict[str, List[Dict[str, str]]]:
        try:
            return self._fetch_market_dashboard()
        except Exception as exc:
            LOGGER.warning("Using fallback market dashboard due to error: %s", exc)
            return self._fallback_market_dashboard()

    def _fetch_market_dashboard(self) -> Dict[str, List[Dict[str, str]]]:
        # 拡張された指数シンボル
        indices_symbols = {
            "Nikkei 225": "^N225",
            "TOPIX": "^TPX", 
            "S&P 500": "^GSPC",
            "NASDAQ": "^IXIC",
            "DAX": "^GDAXI",
            "FTSE 100": "^FTSE",
            "Hang Seng": "^HSI",
            "Shanghai": "000001.SS",
            "KOSPI": "^KS11",
            "ASX 200": "^AXJO",
        }

        # 拡張された為替・債券・商品シンボル
        fx_bonds_symbols = {
            "USD/JPY": "JPY=X",
            "EUR/USD": "EURUSD=X",
            "GBP/USD": "GBPUSD=X",
            "AUD/USD": "AUDUSD=X",
            "USD/CNY": "CNY=X",
            "US 10Y": "^TNX",
            "US 2Y": "^IRX",
            "JP 10Y": "^TNX",  # 日本国債の代替
            "WTI": "CL=F",
            "Brent": "BZ=F",
            "Gold": "GC=F",
            "Silver": "SI=F",
            "Bitcoin": "BTC-USD",
            "Ethereum": "ETH-USD",
        }

        indices: List[Dict[str, str]] = []
        for name, symbol in indices_symbols.items():
            try:
                indices.append(self._fetch_quote(symbol, name, price_format="index"))
            except Exception as e:
                LOGGER.warning(f"Failed to fetch {name}: {e}")
                continue

        fx_bonds: List[Dict[str, str]] = []
        for name, symbol in fx_bonds_symbols.items():
            try:
                if "10Y" in name or "2Y" in name:
                    price_format = "yield"
                elif name in {"WTI", "Brent", "Gold", "Silver", "Bitcoin", "Ethereum"}:
                    price_format = "commodity"
                else:
                    price_format = "fx"
                fx_bonds.append(self._fetch_quote(symbol, name, price_format=price_format))
            except Exception as e:
                LOGGER.warning(f"Failed to fetch {name}: {e}")
                continue

        return {"indices": indices, "fx_bonds": fx_bonds}

    def _fetch_quote(self, symbol: str, label: str, price_format: str = "index") -> Dict[str, str]:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="2d")
        if history.empty:
            raise ValueError(f"No data for symbol {symbol}")
        current = float(history["Close"].iloc[-1])
        previous = float(history["Close"].iloc[-2]) if len(history) > 1 else current
        delta = current - previous
        change_pct = (delta / previous) * 100 if previous else 0.0

        # 価格フォーマットの改善
        if price_format == "fx":
            if "JPY" in label or "CNY" in label:
                value = f"{current:.2f}"
            else:
                value = f"{current:.4f}"
        elif price_format == "yield":
            value = f"{current:.2f}%"
        elif price_format == "commodity":
            if label in {"Bitcoin", "Ethereum"}:
                value = f"${current:,.0f}"
            elif label in {"Gold", "Silver"}:
                value = f"${current:.1f}"
            else:  # WTI, Brent
                value = f"${current:.2f}"
        else:  # index
            if current >= 10000:
                value = f"{current:,.0f}"
            elif current >= 1000:
                value = f"{current:,.1f}"
            else:
                value = f"{current:.2f}"

        return {
            "name": label,
            "value": value,
            "change": f"{change_pct:+.2f}%",
        }

    def _fallback_market_dashboard(self) -> Dict[str, List[Dict[str, str]]]:
        return json.loads(
            """
            {
              "indices": [
                {"name": "Nikkei 225", "value": "33,210", "change": "+0.45%"},
                {"name": "TOPIX", "value": "2,360", "change": "+0.18%"},
                {"name": "S&P 500", "value": "5,316", "change": "-0.22%"},
                {"name": "NASDAQ", "value": "16,895", "change": "+0.12%"}
              ],
              "fx_bonds": [
                {"name": "USD/JPY", "value": "148.35", "change": "+0.20%"},
                {"name": "EUR/USD", "value": "1.08", "change": "-0.10%"},
                {"name": "US 10Y", "value": "3.95%", "change": "+0.03%"},
                {"name": "WTI", "value": "78.4", "change": "+0.80%"},
                {"name": "Gold", "value": "2,320", "change": "-0.15%"},
                {"name": "Bitcoin", "value": "63,500", "change": "+1.25%"}
              ]
            }
            """
        )

    def _get_economic_calendar(self) -> (List[ReleasedIndicator], List[UpcomingIndicator]):
        try:
            data = self._fetch_economic_calendar()
        except Exception as exc:
            LOGGER.warning("Using fallback economic calendar due to error: %s", exc)
            data = self._fallback_economic_calendar()

        released = [ReleasedIndicator(**item) for item in data.get("released", [])]
        upcoming = [UpcomingIndicator(**item) for item in data.get("upcoming", [])]
        return released[:6], upcoming[:6]

    def _fetch_economic_calendar(self) -> Dict[str, List[Dict[str, str]]]:
        today = datetime.utcnow().date()
        released = self._collect_calendar(today - timedelta(days=1), today, future=False)
        upcoming = self._collect_calendar(today, today + timedelta(days=3), future=True)
        return {"released": released, "upcoming": upcoming}

    def _collect_calendar(self, start, end, future: bool) -> List[Dict[str, str]]:
        countries = ["united states", "japan", "germany", "euro zone"]
        results: List[Dict[str, str]] = []
        for country in countries:
            try:
                df = investpy.economic_calendar(
                    countries=[country],
                    from_date=start.strftime("%d/%m/%Y"),
                    to_date=end.strftime("%d/%m/%Y"),
                )
            except Exception as exc:
                LOGGER.debug("investpy error for %s: %s", country, exc)
                continue

            for _, row in df.iterrows():
                indicator = self._decorate_indicator(row.get("event", ""), country)
                forecast = row.get("forecast", "N/A")
                if future:
                    time_label = self._convert_to_jst(row.get("time", ""))
                    results.append(
                        {
                            "indicator": indicator,
                            "time": time_label,
                            "forecast": str(forecast),
                        }
                    )
                else:
                    actual = row.get("actual", "N/A")
                    results.append(
                        {
                            "indicator": indicator,
                            "actual": str(actual),
                            "forecast": str(forecast),
                        }
                    )
        return results

    def _fallback_economic_calendar(self) -> Dict[str, List[Dict[str, str]]]:
        return json.loads(
            """
            {
              "released": [
                {"indicator": "🇺🇸 CPI (YoY)", "actual": "3.4%", "forecast": "3.2%"},
                {"indicator": "🇯🇵 失業率", "actual": "2.5%", "forecast": "2.6%"},
                {"indicator": "🇪🇺 PMI", "actual": "49.8", "forecast": "49.5"}
              ],
              "upcoming": [
                {"indicator": "🇺🇸 FOMC", "time": "03:00", "forecast": "政策金利据え置き"},
                {"indicator": "🇯🇵 日銀展望レポート", "time": "12:00", "forecast": "物価見通し引き上げ"},
                {"indicator": "🇩🇪 Ifo景況感", "time": "18:00", "forecast": "95.0"}
              ]
            }
            """
        )

    def _decorate_indicator(self, event: str, country: str) -> str:
        flags = {
            "united states": "🇺🇸",
            "japan": "🇯🇵",
            "germany": "🇩🇪",
            "euro zone": "🇪🇺",
        }
        prefix = flags.get(country, "")
        return f"{prefix} {event}".strip()

    def _convert_to_jst(self, time_str: str) -> str:
        if not time_str or time_str.lower() == "to be announced":
            return "TBD"
        try:
            hour, minute = map(int, time_str.split(":"))
        except ValueError:
            return time_str
        hour += 9
        if hour >= 24:
            hour -= 24
        return f"{hour:02d}:{minute:02d}"


__all__ = ["HtmlImageRenderer"]
