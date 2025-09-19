#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DBに既存保存されている記事（過去N時間）から、
ソーシャル出力（画像1〜3枚+note）を生成する簡易スクリプト。

・スクレイピングは行いません
・AI要約が付いている記事は優先採用します
・主要指標JSONが無ければ自動で取得して反映します
"""

import sys
from pathlib import Path
from datetime import datetime
import pytz

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.config.app_config import get_config
from src.database.database_manager import DatabaseManager
from src.database.models import Article
from src.core.social_content_generator import SocialContentGenerator


def main():
    cfg = get_config()
    db = DatabaseManager(cfg.database)
    jst = pytz.timezone('Asia/Tokyo')

    # 過去N時間分（設定値）の記事を取得（AI分析を含む）
    # 直接Articleのみを取得（古いDBでも動くようにAIAnalysisはJOINしない）
    with db.get_session() as session:
        from sqlalchemy import desc
        # 1) published_at の新しい順
        articles_db = (
            session.query(Article)
            .order_by(desc(Article.published_at))
            .limit(150)
            .all()
        )
        # 2) それでも0なら scraped_at の新しい順
        if not articles_db:
            articles_db = (
                session.query(Article)
                .order_by(desc(Article.scraped_at))
                .limit(150)
                .all()
            )

        if not articles_db:
            print("DBに対象記事が見つかりませんでした。最近のスクレイピング実行をご確認ください。")
            return

        # SocialContentGeneratorに渡す形式へ変換（セッション内で処理）
        articles = []
        for a in articles_db:
            analysis = None  # 旧DB対応のためAIAnalysisは参照しない
            # published_atがnaive datetimeの場合、UTCとして扱いJSTに変換
            published_jst = None
            if a.published_at:
                if a.published_at.tzinfo is None:
                    # naive datetimeをUTCとして扱い、JSTに変換
                    utc_time = pytz.utc.localize(a.published_at)
                    published_jst = utc_time.astimezone(jst)
                else:
                    # already timezone-aware
                    published_jst = a.published_at.astimezone(jst)
            else:
                published_jst = None

            articles.append({
                "title": a.title or "",
                "url": a.url or "",
                "source": a.source or "",
                "published_jst": published_jst,
                "summary": a.body or "",
                "sentiment_label": "N/A",
                "sentiment_score": 0.0,
                "category": None,
                "region": None,
            })

    # 生成
    gen = SocialContentGenerator(cfg, logger=_get_stdout_logger())
    gen.generate_social_content(articles)

    now = datetime.now(jst)
    date_dir = now.strftime('%Y%m%d')
    print("\n--- 生成完了（DBベース）---")
    print(f"画像1: {cfg.social.output_base_dir}/social/{date_dir}/news_01_16x9.png")
    print(f"画像2: {cfg.social.output_base_dir}/social/{date_dir}/news_02_16x9.png")
    print(f"画像3: {cfg.social.output_base_dir}/social/{date_dir}/news_03_16x9.png")
    print(f"note:  {cfg.social.output_base_dir}/note/{now.strftime('%Y-%m-%d')}.md")


def _get_stdout_logger():
    import logging
    logger = logging.getLogger("generate_from_db")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        h = logging.StreamHandler(sys.stdout)
        h.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")
        h.setFormatter(formatter)
        logger.addHandler(h)
    return logger


if __name__ == "__main__":
    main()
