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
class TopicDetailsContext:
    page_title: str
    width: int
    height: int
    palette: Palette
    brand_name: str
    date_label: str
    title: str
    intro: str
    topics: List[TopicCard]
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
        topics_cards = self._build_topic_cards(topics, include_keywords=True)
        intro = "市場の注目テーマを深掘りし、投資インパクトと監視ポイントを整理しました。"

        context = TopicDetailsContext(
            page_title=f"{title} | {self.brand_name}",
            width=self.width,
            height=self.height,
            palette=self.palette,
            brand_name=self.brand_name,
            date_label=self._format_date(date),
            title=title,
            intro=intro,
            topics=topics_cards[:3],
            disclaimer=self.DISCLAIMER,
            hashtags=self.hashtags,
        )

        return self._render_to_image(
            template_name="topic_deep_dive.html.j2",
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
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, chromium_sandbox=False, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": self.width, "height": self.height})
            page.set_content(html, wait_until="networkidle")
            page.wait_for_timeout(200)
            page.screenshot(path=str(output_file), full_page=False)
            browser.close()

    # --------- コンテンツ構築 ---------

    def _build_topic_cards(self, topics: Iterable, include_keywords: bool = False) -> List[TopicCard]:
        cards: List[TopicCard] = []
        if not topics:
            return cards
        for topic in topics:
            headline = self._sanitize_text(getattr(topic, "headline", ""))
            raw_summary = getattr(topic, "summary", None) or getattr(topic, "blurb", "")
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

            cards.append(
                TopicCard(
                    headline=headline,
                    summary=summary,
                    meta=meta,
                    points=points,
                    keywords=keywords,
                )
            )
        return cards

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
        indices_symbols = {
            "Nikkei 225": "^N225",
            "TOPIX": "^TPX",
            "S&P 500": "^GSPC",
            "NASDAQ": "^IXIC",
            "DAX": "^GDAXI",
            "FTSE 100": "^FTSE",
        }

        fx_symbols = {
            "USD/JPY": "JPY=X",
            "EUR/USD": "EURUSD=X",
            "US 10Y": "^TNX",
            "WTI": "CL=F",
            "Gold": "GC=F",
            "Bitcoin": "BTC-USD",
        }

        indices: List[Dict[str, str]] = []
        for name, symbol in indices_symbols.items():
            indices.append(self._fetch_quote(symbol, name, price_format="index"))

        fx_bonds: List[Dict[str, str]] = []
        for name, symbol in fx_symbols.items():
            price_format = "yield" if "10Y" in name else "commodity" if name in {"WTI", "Gold", "Bitcoin"} else "fx"
            fx_bonds.append(self._fetch_quote(symbol, name, price_format=price_format))

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

        if price_format == "fx":
            value = f"{current:.2f}"
        elif price_format == "yield":
            value = f"{current:.2f}%"
        elif price_format == "commodity":
            value = f"{current:.1f}"
        else:
            value = f"{current:,.0f}"

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
