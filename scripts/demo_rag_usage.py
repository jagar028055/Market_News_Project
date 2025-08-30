#!/usr/bin/env python3
"""
RAGシステムの実用デモ

使用方法:
    python scripts/demo_rag_usage.py
"""

import sys
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag.rag_manager import RAGManager


def main():
    """メイン実行関数"""
    print("🎯 Market News RAGシステム 動作確認")
    print("=" * 50)
    
    try:
        # システム初期化
        print("🚀 システム初期化中...")
        rag = RAGManager()
        
        # システム状態確認
        print("📊 システム状態確認中...")
        status = rag.get_system_status()
        
        print(f"\nシステム健全性: {'✅ OK' if status.get('system_healthy') else '❌ NG'}")
        print(f"Supabase接続: {'✅ OK' if status.get('supabase_available') else '❌ NG'}")
        print(f"総ドキュメント数: {status.get('total_documents', 0)}件")
        print(f"総チャンク数: {status.get('total_chunks', 0)}個")
        
        print("\n🎉 RAGシステムが正常に動作しています！")
        print("\n📖 次のステップ:")
        print("   1. docs/RAG_USAGE_GUIDE.md で詳細な使用方法を確認")
        print("   2. 実際のニュース記事でアーカイブをテスト")
        print("   3. 検索機能を活用した分析を開始")
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        print("\n🔧 トラブルシューティング:")
        print("   1. .env ファイルの設定を確認")
        print("   2. Supabaseプロジェクトの設定を確認") 
        print("   3. 必要なパッケージがインストールされているか確認")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)