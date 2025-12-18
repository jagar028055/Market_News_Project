#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AIAnalysisテーブルにcategoryとregion列を追加するマイグレーションスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, inspect
from src.config.app_config import get_config


def _has_column(conn, table_name: str, column_name: str) -> bool:
    inspector = inspect(conn)
    cols = inspector.get_columns(table_name)
    return any(col.get("name") == column_name for col in cols)


def _has_index(conn, table_name: str, index_name: str) -> bool:
    inspector = inspect(conn)
    idx = inspector.get_indexes(table_name)
    return any(i.get("name") == index_name for i in idx)

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
            if not _has_column(conn, "ai_analysis", "category"):
                print("category列を追加中...")
                conn.execute(text("ALTER TABLE ai_analysis ADD COLUMN category VARCHAR(100)"))
            else:
                print("category列は既に存在するためスキップ")

            if not _has_column(conn, "ai_analysis", "region"):
                print("region列を追加中...")
                conn.execute(text("ALTER TABLE ai_analysis ADD COLUMN region VARCHAR(100)"))
            else:
                print("region列は既に存在するためスキップ")
            
            # インデックス作成
            if not _has_index(conn, "ai_analysis", "idx_category_region"):
                print("インデックス idx_category_region を作成中...")
                conn.execute(text("CREATE INDEX idx_category_region ON ai_analysis (category, region)"))
            else:
                print("idx_category_region は既に存在するためスキップ")

            if not _has_index(conn, "ai_analysis", "idx_category_analyzed"):
                print("インデックス idx_category_analyzed を作成中...")
                conn.execute(text("CREATE INDEX idx_category_analyzed ON ai_analysis (category, analyzed_at)"))
            else:
                print("idx_category_analyzed は既に存在するためスキップ")

            if not _has_index(conn, "ai_analysis", "idx_region_analyzed"):
                print("インデックス idx_region_analyzed を作成中...")
                conn.execute(text("CREATE INDEX idx_region_analyzed ON ai_analysis (region, analyzed_at)"))
            else:
                print("idx_region_analyzed は既に存在するためスキップ")
            
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
