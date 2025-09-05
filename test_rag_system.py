#!/usr/bin/env python3
"""
RAGシステム機能テスト
データベーススキーマ作成後に実行
"""

import sys
import os
sys.path.insert(0, '.')

from src.rag.rag_manager import RAGManager
from datetime import datetime

def test_rag_system():
    """RAGシステムの包括的テスト"""
    print("=== RAGシステム機能テスト ===")
    
    # 1. システム状態確認
    manager = RAGManager()
    status = manager.get_system_status()
    print(f"システム状態:")
    for key, value in status.items():
        symbol = "✅" if value else "❌"
        print(f"  {symbol} {key}: {value}")
    
    if not status.get('system_healthy'):
        print("❌ システムが正常に動作していません")
        return False
    
    # 2. テスト記事データ
    test_articles = [
        {
            'id': 'test-001',
            'title': '日本経済の回復傾向について',
            'body': 'COVID-19パンデミック後、日本経済は徐々に回復の兆しを見せている。政府の経済対策効果により、企業の業績改善が期待されている。',
            'url': 'https://example.com/test-001',
            'source': 'Test News',
            'published_at': datetime.now(),
            'metadata': {'region': '日本', 'category': '経済'}
        },
        {
            'id': 'test-002', 
            'title': 'テクノロジー分野の投資動向',
            'body': '人工知能とクラウドコンピューティングへの投資が急増している。スタートアップ企業への資金調達も活発化している。',
            'url': 'https://example.com/test-002',
            'source': 'Tech News',
            'published_at': datetime.now(),
            'metadata': {'region': '全世界', 'category': 'テクノロジー'}
        }
    ]
    
    # 3. 記事アーカイブテスト
    print("\n=== アーカイブ機能テスト ===")
    try:
        archive_result = manager.archive_articles(test_articles, "2024-08-30")
        print(f"✅ アーカイブ完了: {archive_result}")
    except Exception as e:
        print(f"❌ アーカイブエラー: {e}")
        return False
    
    # 4. 検索機能テスト
    print("\n=== 検索機能テスト ===")
    try:
        search_queries = [
            "経済回復について",
            "人工知能投資",
            "テクノロジー分野"
        ]
        
        for query in search_queries:
            results = manager.search_content(query, max_results=3)
            print(f"✅ クエリ「{query}」: {len(results)}件の結果")
            for i, result in enumerate(results[:2], 1):
                print(f"   {i}. スコア: {result.similarity:.3f} - {result.content[:50]}...")
                
    except Exception as e:
        print(f"❌ 検索エラー: {e}")
        return False
    
    # 5. トレンド分析テスト
    print("\n=== トレンド分析テスト ===")
    try:
        trends = manager.get_trending_topics(days_back=30)
        print(f"✅ トレンド分析完了: {len(trends)}件のトピック")
        for trend in trends[:3]:
            print(f"   - {trend}")
    except Exception as e:
        print(f"❌ トレンド分析エラー: {e}")
        return False
    
    print("\n🎉 全てのテストが正常に完了しました！")
    return True

if __name__ == "__main__":
    success = test_rag_system()
    sys.exit(0 if success else 1)