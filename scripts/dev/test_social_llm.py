#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM最適化されたSNSコンテンツ生成のテストスクリプト
"""

import sys
from pathlib import Path
from datetime import datetime
import pytz

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.core.llm_content_optimizer import LLMContentOptimizer
from src.config.app_config import get_config
import logging

def main():
    """テスト実行"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("social_llm_test")
    
    config = get_config()
    logger.info(f"LLM最適化設定: {config.social.enable_llm_optimization}")
    logger.info(f"生成モード: {config.social.generation_mode}")
    
    optimizer = LLMContentOptimizer()
    
    # テスト用記事データ
    test_articles = [
        {
            'title': '日銀、政策金利を0.5%に引き上げ決定',
            'summary': '日本銀行は金融政策決定会合で、政策金利を現行の0.25%から0.5%に引き上げることを決定した。インフレ率が目標の2%を上回る状況が継続していることを受けた措置。',
            'category': '金融政策',
            'region': '日本'
        },
        {
            'title': 'トヨタ自動車、第3四半期純利益20%増',
            'summary': 'トヨタ自動車が発表した第3四半期決算は、純利益が前年同期比20%増の8,500億円となった。北米での販売好調と円安効果が寄与した。',
            'category': '企業決算',
            'region': '日本'
        },
        {
            'title': '米FRB、利下げ示唆の発言',
            'summary': 'パウエルFRB議長は講演で、インフレ圧力の緩和を受けて今後の利下げの可能性を示唆した。市場では年内0.25%の利下げ観測が高まっている。',
            'category': '金融政策',
            'region': '米国'
        }
    ]
    
    logger.info("=== SNS最適化テスト ===")
    
    # 各記事のSNS最適化をテスト
    for i, article in enumerate(test_articles, 1):
        logger.info(f"\n--- 記事 {i}: {article['title'][:30]}... ---")
        
        optimized = optimizer.optimize_for_sns(
            title=article['title'],
            summary=article['summary'],
            category=article['category'],
            region=article['region']
        )
        
        if optimized:
            logger.info(f"SNSテキスト: {optimized.sns_text}")
            logger.info(f"キーワード: {', '.join(optimized.keywords)}")
            logger.info(f"文字数: {len(optimized.sns_text)}文字")
        else:
            logger.warning("SNS最適化に失敗")
    
    logger.info("\n=== note記事生成テスト ===")
    
    # note記事生成テスト
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    
    topics_data = [
        {
            'headline': article['title'],
            'blurb': article['summary'],
            'source': 'テストソース',
            'category': article['category'],
            'region': article['region']
        }
        for article in test_articles
    ]
    
    note_article = optimizer.generate_note_article(
        date=now,
        topics=topics_data,
        market_summary="市場は堅調な推移を見せており、投資家心理は改善傾向にある。",
        integrated_summary="本日の主要ニュースは金融政策と企業決算に関する内容が中心となった。"
    )
    
    if note_article:
        logger.info("note記事生成完了")
        logger.info(f"記事文字数: {len(note_article)}文字")
        logger.info("--- 生成された記事（冒頭200文字） ---")
        logger.info(note_article[:200] + "...")
        
        # ファイルに保存
        output_file = project_root / "test_note_article.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(note_article)
        logger.info(f"記事を保存: {output_file}")
    else:
        logger.error("note記事生成に失敗")
    
    logger.info("\n=== テスト完了 ===")

if __name__ == "__main__":
    main()