#!/usr/bin/env python3
"""HTMLテンプレートを用いたSNS画像生成スクリプト"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import List

from dateutil import parser as date_parser

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.renderers.html_image_renderer import HtmlImageRenderer

DEFAULT_SAMPLE = {
    "brand_name": "Market News",
    "hashtags": "#MarketNews #GlobalMarkets",
    "topics": [
        {
            "headline": "米FOMC、政策金利を据え置きも年内利下げ見通しを縮小",
            "summary": "米連邦公開市場委員会（FOMC）は政策金利を5.25-5.50%で据え置いたものの、最新のドットチャートでは年内利下げ回数を従来の3回から1回へ下方修正。パウエル議長はインフレ進展が限定的であるとし、データ次第でタカ派的姿勢を維持する姿勢を示した。",
            "source": "Federal Reserve",
            "published_jst": datetime.now().isoformat(),
            "category": "Monetary Policy",
            "region": "US",
        },
        {
            "headline": "日本のコアCPI、前年比+2.8%と予想を上回り円高圧力",
            "summary": "日本の8月コアCPIは前年同月比+2.8%となり市場予想の+2.6%を上回った。エネルギー補助金の縮小とサービス価格の上昇が寄与し、日銀の政策正常化観測が再燃。円相場は一時147円台まで買い戻され、国債利回りも上昇した。",
            "source": "総務省統計局",
            "published_jst": datetime.now().isoformat(),
            "category": "Inflation",
            "region": "Japan",
        },
        {
            "headline": "欧州PMIが連続低下、製造業の縮小が続く",
            "summary": "ユーロ圏9月製造業PMI速報値は43.4と前月から低下し、市場予想の44.2も下回った。輸出需要の減速と在庫調整が重荷となり、景気後退懸念が再燃。ECB理事は追加引き締めに慎重姿勢を示す一方、エネルギー価格の再上昇がインフレ見通しを不安定にしている。",
            "source": "S&P Global",
            "published_jst": datetime.now().isoformat(),
            "category": "Macro",
            "region": "EU",
        },
    ],
}


def load_topics(path: Path) -> dict:
    if not path.exists():
        return DEFAULT_SAMPLE
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    return payload


def payload_to_topics(payload: dict) -> List[SimpleNamespace]:
    topics = []
    for item in payload.get("topics", []):
        published = item.get("published_jst")
        if isinstance(published, str):
            try:
                published_dt = date_parser.parse(published)
            except Exception:
                published_dt = None
        else:
            published_dt = published
        topics.append(
            SimpleNamespace(
                headline=item.get("headline", ""),
                summary=item.get("summary"),
                blurb=item.get("summary", ""),
                source=item.get("source", ""),
                published_jst=published_dt,
                category=item.get("category"),
                region=item.get("region"),
            )
        )
    return topics


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate social assets via HTML templates")
    parser.add_argument("--input", type=Path, default=Path("data/social_topics_sample.json"))
    parser.add_argument("--output", type=Path, default=Path("build/social/sample"))
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=1200)
    args = parser.parse_args()

    payload = load_topics(args.input)
    topics = payload_to_topics(payload)

    date_value = datetime.fromisoformat(f"{args.date}T00:00:00")

    renderer = HtmlImageRenderer(
        width=args.width,
        height=args.height,
        brand_name=payload.get("brand_name", "Market News"),
        hashtags=payload.get("hashtags", "#MarketNews"),
    )

    args.output.mkdir(parents=True, exist_ok=True)

    result_paths = {
        "market_overview": renderer.render_vertical_market_overview(date_value, topics, str(args.output)),
        "topic_details": renderer.render_vertical_topic_details(date_value, topics, str(args.output)),
        "economic_calendar": renderer.render_vertical_economic_calendar(date_value, str(args.output)),
    }

    for name, path in result_paths.items():
        print(f"Generated {name}: {path}")


if __name__ == "__main__":
    main()
