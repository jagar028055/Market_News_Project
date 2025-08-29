#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
data/articles.jsonファイルから記事を取得して、
ソーシャル出力（画像1〜3枚+note）を生成するスクリプト。

・data/articles.jsonが存在する場合はそれを使用
・存在しない場合はデモモードにフォールバック
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import pytz

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.config.app_config import get_config
from src.core.social_content_generator import SocialContentGenerator


def main():
    cfg = get_config()
    jst = pytz.timezone('Asia/Tokyo')
    
    # data/articles.jsonから記事を読み込み
    articles_file = project_root / "data" / "articles.json"
    
    if not articles_file.exists():
        print("data/articles.jsonが見つかりません。デモモードスクリプトを実行します。")
        import subprocess
        subprocess.run([sys.executable, str(project_root / "scripts" / "dev" / "generate_social_demo.py")])
        return
    
    try:
        with open(articles_file, 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
        
        if not articles_data:
            print("data/articles.jsonに記事がありません。デモモードで実行します。")
            import subprocess
            subprocess.run([sys.executable, str(project_root / "scripts" / "dev" / "generate_social_demo.py")])
            return
            
        print(f"✅ data/articles.jsonから {len(articles_data)} 件の記事を読み込みました")
        
        # デバッグ: 実際のデータの最初の3件を表示
        print("=== DEBUG: 最初の3件の記事タイトル ===")
        for i, article in enumerate(articles_data[:3]):
            print(f"  {i+1}. {article.get('title', 'NO_TITLE')}")
        print("==============================")
        
        # SocialContentGeneratorに渡す形式へ変換
        articles = []
        for a in articles_data:
            # published_jstまたはpublished_atが文字列の場合は日時に変換
            published_jst = None
            published_field = a.get('published_jst') or a.get('published_at')  # published_jstを優先
            if published_field:
                try:
                    if isinstance(published_field, str):
                        # ISO形式の文字列をdatetimeに変換
                        published_jst = datetime.fromisoformat(published_field.replace('Z', '+00:00'))
                    else:
                        published_jst = published_field
                except Exception as e:
                    print(f"DEBUG: 日時変換エラー: {published_field} -> {e}")
                    published_jst = None
            
            articles.append({
                "title": a.get('title', ''),
                "url": a.get('url', ''),
                "source": a.get('source', ''),
                "published_jst": published_jst,
                "summary": a.get('summary', ''),
                "sentiment_label": a.get('sentiment_label', 'N/A'),
                "sentiment_score": a.get('score', 0.0),
                "category": a.get('category'),
                "region": a.get('region'),
            })
        
        # デバッグ: 変換後のデータも確認
        print("=== DEBUG: 変換後の最初の3件の記事タイトルと日時 ===")
        for i, article in enumerate(articles[:3]):
            print(f"  {i+1}. {article.get('title', 'NO_TITLE')}")
            print(f"      published_jst: {article.get('published_jst')} (type: {type(article.get('published_jst'))})")
        print("=====================================================")
        
        # ソーシャルコンテンツ生成
        gen = SocialContentGenerator(cfg, logger=_get_stdout_logger())
        
        # デバッグ: 実際にSocialContentGeneratorに渡される記事数を確認
        print(f"=== DEBUG: SocialContentGeneratorに渡される記事数: {len(articles)} 件 ===")
        if articles:
            print(f"=== DEBUG: 最初の記事のデータ構造確認 ===")
            first_article = articles[0]
            print(f"  title: {first_article.get('title', 'NO_TITLE')}")
            print(f"  published_jst type: {type(first_article.get('published_jst'))}")
            print(f"  published_jst: {first_article.get('published_jst')}")
            print("==================================")
        
        gen.generate_social_content(articles)
        
        now = datetime.now(jst)
        date_dir = now.strftime('%Y%m%d')
        print("\n--- 生成完了（アーティファクトベース）---")
        print(f"📊 使用記事数: {len(articles)} 件")
        print(f"画像1: {cfg.social.output_base_dir}/social/{date_dir}/news_01_16x9.png")
        print(f"画像2: {cfg.social.output_base_dir}/social/{date_dir}/news_02_16x9.png") 
        print(f"画像3: {cfg.social.output_base_dir}/social/{date_dir}/news_03_16x9.png")
        print(f"note:  {cfg.social.output_base_dir}/note/{now.strftime('%Y-%m-%d')}.md")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        print("デモモードで実行します。")
        import subprocess
        subprocess.run([sys.executable, str(project_root / "scripts" / "dev" / "generate_social_demo.py")])


def _get_stdout_logger():
    import logging
    logger = logging.getLogger("generate_from_artifacts")
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