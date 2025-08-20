# -*- coding: utf-8 -*-

"""
AIAnalysisテーブルにcategory/regionカラムを追加するマイグレーション
"""

import sqlite3
import os
import logging
from datetime import datetime

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def backup_database(db_path: str) -> str:
    """データベースのバックアップを作成"""
    logger = logging.getLogger(__name__)
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"データベースバックアップ作成: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"バックアップ作成失敗: {e}")
        raise

def check_columns_exist(conn: sqlite3.Connection) -> dict:
    """既存カラムの確認"""
    logger = logging.getLogger(__name__)
    
    cursor = conn.cursor()
    
    # テーブルが存在するかチェック
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_analysis'")
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        logger.info("ai_analysisテーブルが存在しません")
        return {
            'table_exists': False,
            'category_exists': False,
            'region_exists': False,
            'existing_columns': {}
        }
    
    cursor.execute("PRAGMA table_info(ai_analysis)")
    columns = cursor.fetchall()
    
    existing_columns = {col[1]: col[2] for col in columns}
    logger.info(f"既存カラム: {list(existing_columns.keys())}")
    
    return {
        'table_exists': True,
        'category_exists': 'category' in existing_columns,
        'region_exists': 'region' in existing_columns,
        'existing_columns': existing_columns
    }

def migrate_ai_analysis_table(db_path: str) -> bool:
    """AIAnalysisテーブルにcategory/regionカラムを追加"""
    logger = logging.getLogger(__name__)
    
    if not os.path.exists(db_path):
        logger.error(f"データベースファイルが見つかりません: {db_path}")
        return False
    
    # バックアップ作成
    backup_path = backup_database(db_path)
    
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("BEGIN TRANSACTION")
        
        # 既存カラム確認
        column_status = check_columns_exist(conn)
        
        if not column_status['table_exists']:
            logger.info("ai_analysisテーブルが存在しません。新しいモデルでテーブルが作成されます。")
            conn.commit()
            conn.close()
            return True
        
        # カラム追加が必要かチェック
        needs_migration = False
        
        if not column_status['category_exists']:
            logger.info("categoryカラムを追加します")
            conn.execute("ALTER TABLE ai_analysis ADD COLUMN category VARCHAR(100)")
            needs_migration = True
        else:
            logger.info("categoryカラムは既に存在します")
        
        if not column_status['region_exists']:
            logger.info("regionカラムを追加します")
            conn.execute("ALTER TABLE ai_analysis ADD COLUMN region VARCHAR(50)")
            needs_migration = True
        else:
            logger.info("regionカラムは既に存在します")
        
        if needs_migration:
            # インデックス作成
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_category_region ON ai_analysis(category, region)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_region_analyzed ON ai_analysis(region, analyzed_at)")
                logger.info("インデックスを作成しました")
            except Exception as e:
                logger.warning(f"インデックス作成エラー（既に存在する可能性）: {e}")
            
            conn.commit()
            logger.info("マイグレーション完了")
        else:
            conn.rollback()
            logger.info("マイグレーション不要（カラムは既に存在）")
        
        # テーブル構造確認
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(ai_analysis)")
        columns_after = cursor.fetchall()
        logger.info("マイグレーション後のテーブル構造:")
        for col in columns_after:
            logger.info(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
        
        conn.close()
        
        # レコード数確認
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ai_analysis")
        count = cursor.fetchone()[0]
        logger.info(f"AIAnalysisレコード数: {count}")
        
        # 新カラムの値確認
        cursor.execute("SELECT COUNT(*) FROM ai_analysis WHERE category IS NOT NULL")
        category_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM ai_analysis WHERE region IS NOT NULL")
        region_count = cursor.fetchone()[0]
        
        logger.info(f"categoryが設定されているレコード: {category_count}")
        logger.info(f"regionが設定されているレコード: {region_count}")
        
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"マイグレーション失敗: {e}")
        logger.info(f"バックアップから復元してください: {backup_path}")
        return False

def main():
    """メイン処理"""
    logger = setup_logging()
    
    # データベースパスを取得
    db_path = "market_news.db"
    
    # 環境に応じてパスを調整
    if not os.path.exists(db_path):
        # 相対パスで試行
        possible_paths = [
            "./market_news.db",
            "../market_news.db",
            "../../market_news.db"
        ]
        
        # データベースが存在しない場合は作成
        logger.info("market_news.dbが見つかりません。新規作成します。")
        db_path = "./market_news.db"
        
        for path in possible_paths:
            if os.path.exists(path):
                db_path = path
                break
    
    logger.info(f"データベースパス: {os.path.abspath(db_path)}")
    
    # マイグレーション実行
    success = migrate_ai_analysis_table(db_path)
    
    if success:
        logger.info("✅ マイグレーション成功")
        logger.info("これで新しいFlash-lite分析結果がcategory/regionと共に保存されます")
        return True
    else:
        logger.error("❌ マイグレーション失敗")
        return False

if __name__ == "__main__":
    main()