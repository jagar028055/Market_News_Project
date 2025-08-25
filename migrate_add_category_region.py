#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AIAnalysisテーブルにcategoryとregion列を追加するマイグレーションスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from src.config.app_config import get_config

def migrate_database():
    """データベースマイグレーション実行"""
    config = get_config()
    engine = create_engine(config.database.url)
    
    print("=== AIAnalysisテーブルマイグレーション開始 ===")
    
    with engine.connect() as conn:
        # トランザクション開始
        trans = conn.begin()
        try:
            # category列とregion列を追加
            print("category列を追加中...")
            conn.execute(text("ALTER TABLE ai_analysis ADD COLUMN category VARCHAR(100)"))
            
            print("region列を追加中...")
            conn.execute(text("ALTER TABLE ai_analysis ADD COLUMN region VARCHAR(100)"))
            
            # インデックス作成
            print("インデックスを作成中...")
            conn.execute(text("CREATE INDEX idx_category_region ON ai_analysis (category, region)"))
            conn.execute(text("CREATE INDEX idx_category_analyzed ON ai_analysis (category, analyzed_at)"))
            conn.execute(text("CREATE INDEX idx_region_analyzed ON ai_analysis (region, analyzed_at)"))
            
            # コミット
            trans.commit()
            print("✅ マイグレーション完了")
            
        except Exception as e:
            # ロールバック
            trans.rollback()
            print(f"❌ マイグレーション失敗: {e}")
            raise

if __name__ == "__main__":
    migrate_database()