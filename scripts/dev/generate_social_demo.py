#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.config.app_config import get_config
from src.core.social_content_generator import SocialContentGenerator
import logging


def main():
    logger = logging.getLogger("social_demo")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setLevel(logging.INFO)
        logger.addHandler(h)

    config = get_config()

    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)

    # ダミー記事3件
    articles = [
        {
            "title": "日銀、政策金利の据え置きを決定 市場は円安を意識",
            "summary": "日銀は金融政策決定会合で政策金利の据え置きを発表。物価動向と賃金の推移を注視する姿勢を維持し、市場では円安圧力の継続が意識された。",
            "published_jst": now - timedelta(hours=2),
            "source": "Reuters",
            "url": "https://example.com/reuters/boj-policy",
            "category": "market",
            "region": "japan",
        },
        {
            "title": "米主要テック決算が相次ぎ発表、AI関連投資が拡大",
            "summary": "マイクロソフトやグーグルなど米大手テックの決算で、AI関連投資の拡大が継続。クラウドの需要底堅く、半導体への設備投資も追い風に。",
            "published_jst": now - timedelta(hours=5),
            "source": "Bloomberg",
            "url": "https://example.com/bloomberg/us-tech-earnings",
            "category": "technology",
            "region": "usa",
        },
        {
            "title": "中国の景気対策、インフラ投資を追加 実体経済の下支えへ",
            "summary": "中国政府はインフラ投資の追加策を発表し、地方財政の支援策も拡充。人民元の安定化を図りつつ、内需の回復を促す。",
            "published_jst": now - timedelta(hours=10),
            "source": "Nikkei",
            "url": "https://example.com/nikkei/china-stimulus",
            "category": "economy",
            "region": "china",
        },
    ]

    gen = SocialContentGenerator(config, logger)
    gen.generate_social_content(articles)

    print("\n--- 生成完了 ---")
    date_dir = now.strftime('%Y%m%d')
    print(f"画像: {config.social.output_base_dir}/social/{date_dir}/news_01_16x9.png")
    print(f"note: {config.social.output_base_dir}/note/{now.strftime('%Y-%m-%d')}.md")
    print(f"JSON: logs/social/{date_dir}/topics.json")


if __name__ == "__main__":
    main()

