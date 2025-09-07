#!/usr/bin/env python3
"""
Supabase接続とスキーマ確認テスト
"""

import sys
import os
sys.path.insert(0, '.')

from src.database.supabase_client import get_supabase_client

def test_supabase_connection():
    """Supabase接続とスキーマ確認"""
    print("=== Supabase接続テスト ===")
    
    client = get_supabase_client()
    
    # 1. 基本接続チェック
    print(f"設定確認:")
    print(f"  - enabled: {client.config.enabled}")
    print(f"  - URL: {client.config.url[:50]}...")
    print(f"  - available: {client.is_available()}")
    
    if not client.is_available():
        print("❌ Supabaseが利用不可能です")
        return False
    
    # 2. テーブルの存在確認
    try:
        # documentsテーブルの確認
        result = client.client.table('documents').select('id').limit(1).execute()
        print(f"✅ documentsテーブル: 存在確認済み")
        
        # chunksテーブルの確認
        result = client.client.table('chunks').select('id').limit(1).execute()
        print(f"✅ chunksテーブル: 存在確認済み")
        
        # pgvector拡張機能の確認
        result = client.client.rpc('search_chunks', {
            'query_embedding': [0.1] * 384,
            'match_count': 1
        }).execute()
        print(f"✅ search_chunks関数: 動作確認済み")
        
        print("✅ データベーススキーマは正常にセットアップされています")
        return True
        
    except Exception as e:
        print(f"❌ データベーススキーマエラー: {e}")
        print("📋 対応方法:")
        print("  1. Supabaseダッシュボード > SQL Editorを開く")
        print("  2. scripts/supabase_rag_setup.sql の内容を実行")
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    sys.exit(0 if success else 1)