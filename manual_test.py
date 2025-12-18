#!/usr/bin/env python3
"""
手動RAGシステムテスト
"""
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
    
    print("✅ 環境変数読み込み成功")
    print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'None')}")
    print(f"SUPABASE_ENABLED: {os.getenv('SUPABASE_ENABLED', 'None')}")
    
except ImportError as e:
    print(f"❌ dotenv import エラー: {e}")
    
try:
    from src.config.app_config import AppConfig
    config = AppConfig()
    print("✅ AppConfig読み込み成功")
    print(f"Supabase enabled: {config.supabase.enabled}")
    print(f"Supabase URL: {config.supabase.url}")
    
except ImportError as e:
    print(f"❌ AppConfig import エラー: {e}")
except Exception as e:
    print(f"❌ AppConfig エラー: {e}")

try:
    import supabase
    print("✅ supabase パッケージ利用可能")
    
    from src.database.supabase_client import SupabaseClient
    client = SupabaseClient(config.supabase)
    print("✅ SupabaseClient作成成功")
    
except ImportError as e:
    print(f"❌ supabase import エラー: {e}")
except Exception as e:
    print(f"❌ SupabaseClient エラー: {e}")

print("\n🎯 基本動作確認完了")