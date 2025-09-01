#!/usr/bin/env python3
"""
RAGシステムのテストスクリプト

使用方法:
1. 環境変数を設定:
   export SUPABASE_URL="your_supabase_url"
   export SUPABASE_ANON_KEY="your_anon_key"
   export SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"
   export SUPABASE_ENABLED="true"

2. 実行:
   python scripts/test_rag_system.py

このスクリプトは以下をテストします:
- Supabase接続
- 埋め込み生成
- テキストチャンキング
- ベクトル検索
- アーカイブ機能
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.app_config import AppConfig
from src.rag.rag_manager import RAGManager
from src.database.supabase_client import SupabaseClient
from src.database.embedding_generator import EmbeddingGenerator
from src.rag.chunk_processor import ChunkProcessor
from src.rag.search_engine import SearchEngine


class RAGSystemTester:
    """RAGシステムのテストクラス"""
    
    def __init__(self):
        """テスター初期化"""
        self.config = AppConfig()
        self.rag_manager = None
        self.test_results = []
        
    def run_all_tests(self):
        """全テストを実行"""
        print("🚀 RAGシステム テスト開始")
        print("=" * 50)
        
        # 設定確認
        if not self._check_configuration():
            return False
            
        # 各テストを実行
        tests = [
            ("Supabase接続テスト", self._test_supabase_connection),
            ("埋め込み生成テスト", self._test_embedding_generation),
            ("テキストチャンキングテスト", self._test_text_chunking),
            ("アーカイブ機能テスト", self._test_archiving),
            ("検索機能テスト", self._test_search),
            ("RAG統合テスト", self._test_rag_integration)
        ]
        
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}")
            print("-" * 30)
            try:
                success = test_func()
                status = "✅ 成功" if success else "❌ 失敗"
                print(f"結果: {status}")
                self.test_results.append((test_name, success))
            except Exception as e:
                print(f"結果: ❌ エラー - {str(e)}")
                self.test_results.append((test_name, False))
        
        # テスト結果サマリー
        self._print_test_summary()
        
        return all(result[1] for result in self.test_results)
    
    def _check_configuration(self):
        """設定確認"""
        print("🔧 設定確認")
        
        # Supabase設定確認
        supabase_config = self.config.supabase
        
        if not supabase_config.enabled:
            print("❌ SUPABASE_ENABLED=trueに設定してください")
            return False
            
        if not supabase_config.url or not supabase_config.anon_key:
            print("❌ SUPABASE_URLとSUPABASE_ANON_KEYを設定してください")
            return False
            
        print("✅ 基本設定OK")
        print(f"   URL: {supabase_config.url[:30]}...")
        print(f"   バケット: {supabase_config.bucket_name}")
        print(f"   埋め込みモデル: {supabase_config.embedding_model}")
        
        return True
    
    def _test_supabase_connection(self):
        """Supabase接続テスト"""
        try:
            client = SupabaseClient(self.config.supabase)
            
            # テスト用ドキュメント作成
            test_doc = {
                "title": "テストドキュメント",
                "content": "これはRAGシステムのテスト用ドキュメントです。",
                "doc_type": "test",
                "metadata": {"test": True}
            }
            
            # ドキュメント作成テスト
            doc_id = client.create_document(**test_doc)
            print(f"✅ ドキュメント作成成功: {doc_id}")
            
            # クリーンアップ
            # Note: 実際の環境では適切なクリーンアップを実装
            
            return True
            
        except Exception as e:
            print(f"❌ 接続エラー: {str(e)}")
            return False
    
    def _test_embedding_generation(self):
        """埋め込み生成テスト"""
        try:
            generator = EmbeddingGenerator(self.config.supabase.embedding_model)
            
            # テストテキスト
            test_texts = [
                "これは日本の経済ニュースです。",
                "株式市場が上昇しています。",
                "新しい技術が発表されました。"
            ]
            
            # 埋め込み生成
            embeddings = generator.generate_embeddings(test_texts)
            
            print(f"✅ 埋め込み生成成功")
            print(f"   テキスト数: {len(test_texts)}")
            print(f"   埋め込み形状: {embeddings.shape}")
            print(f"   次元数: {embeddings.shape[1]}")
            
            # 類似度計算テスト
            similarity = generator.calculate_similarity(embeddings[0], embeddings[1])
            print(f"   類似度例: {similarity:.3f}")
            
            return embeddings.shape[1] == self.config.supabase.embedding_dimension
            
        except Exception as e:
            print(f"❌ 埋め込み生成エラー: {str(e)}")
            return False
    
    def _test_text_chunking(self):
        """テキストチャンキングテスト"""
        try:
            processor = ChunkProcessor(
                chunk_size=self.config.supabase.chunk_size,
                chunk_overlap=self.config.supabase.chunk_overlap
            )
            
            # テストテキスト
            test_content = """
            これは長いテストドキュメントです。複数の段落があります。
            
            第一段落では、市場の動向について説明します。
            株式市場は最近活発な動きを見せており、
            投資家の注目を集めています。
            
            第二段落では、技術の進歩について触れます。
            人工知能の分野で新しい発見があり、
            多くの企業が注目しています。
            
            第三段落では、経済政策について述べます。
            政府は新しい経済政策を発表し、
            市場に大きな影響を与える可能性があります。
            """
            
            # チャンク処理
            chunks = processor.process_article(
                title="テスト記事",
                content=test_content,
                metadata={"test": True}
            )
            
            print(f"✅ チャンキング成功")
            print(f"   元テキスト長: {len(test_content)}")
            print(f"   チャンク数: {len(chunks)}")
            
            for i, chunk in enumerate(chunks[:2]):  # 最初の2つだけ表示
                print(f"   チャンク{i+1}: {chunk.content[:50]}...")
            
            return len(chunks) > 0
            
        except Exception as e:
            print(f"❌ チャンキングエラー: {str(e)}")
            return False
    
    def _test_archiving(self):
        """アーカイブ機能テスト"""
        try:
            self.rag_manager = RAGManager(self.config)
            
            # テストデータ
            test_articles = [
                {
                    "id": "test_001",
                    "title": "テスト記事1",
                    "content": "これは市場分析に関するテスト記事です。",
                    "published_at": datetime.now().isoformat(),
                    "category": "market",
                    "summary": "市場分析のテスト"
                }
            ]
            
            # アーカイブ実行
            result = self.rag_manager.archive_articles(test_articles)
            
            print(f"✅ アーカイブ成功")
            print(f"   処理記事数: {result.get('processed_articles', 0)}")
            print(f"   作成チャンク数: {result.get('created_chunks', 0)}")
            
            return result.get('processed_articles', 0) > 0
            
        except Exception as e:
            print(f"❌ アーカイブエラー: {str(e)}")
            return False
    
    def _test_search(self):
        """検索機能テスト"""
        try:
            if not self.rag_manager:
                self.rag_manager = RAGManager(self.config)
            
            # 検索テスト
            search_queries = [
                "市場",
                "経済",
                "技術"
            ]
            
            for query in search_queries:
                results = self.rag_manager.search_content(
                    query=query,
                    limit=3
                )
                
                print(f"✅ 検索「{query}」: {len(results)}件")
                
                for result in results[:1]:  # 最初の結果だけ表示
                    print(f"   - {result.title[:30]}... (類似度: {result.similarity:.3f})")
            
            return True
            
        except Exception as e:
            print(f"❌ 検索エラー: {str(e)}")
            return False
    
    def _test_rag_integration(self):
        """RAG統合テスト"""
        try:
            if not self.rag_manager:
                self.rag_manager = RAGManager(self.config)
            
            # システム状態確認
            status = self.rag_manager.get_system_status()
            
            print(f"✅ RAG統合確認")
            print(f"   システム健全性: {'OK' if status.get('system_healthy') else 'NG'}")
            print(f"   Supabase接続: {'OK' if status.get('supabase_available') else 'NG'}")
            print(f"   ドキュメント数: {status.get('total_documents', 0)}")
            print(f"   チャンク数: {status.get('total_chunks', 0)}")
            
            return status.get('system_healthy', False)
            
        except Exception as e:
            print(f"❌ RAG統合エラー: {str(e)}")
            return False
    
    def _print_test_summary(self):
        """テスト結果サマリー表示"""
        print("\n" + "=" * 50)
        print("📊 テスト結果サマリー")
        print("=" * 50)
        
        passed = sum(1 for _, success in self.test_results if success)
        total = len(self.test_results)
        
        for test_name, success in self.test_results:
            status = "✅" if success else "❌"
            print(f"{status} {test_name}")
        
        print(f"\n合計: {passed}/{total} テスト成功")
        
        if passed == total:
            print("🎉 全テスト成功！RAGシステムは正常に動作しています。")
        else:
            print("⚠️  一部テストが失敗しました。設定を確認してください。")


def main():
    """メイン実行関数"""
    tester = RAGSystemTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✨ RAGシステムの準備が完了しました！")
        print("\n次のステップ:")
        print("1. 実際のニュース記事でアーカイブを実行")
        print("2. 検索機能をWebアプリケーションに統合")
        print("3. 定期的なアーカイブジョブの設定")
    else:
        print("\n❗ いくつかの問題が見つかりました。")
        print("設定を確認して再度テストしてください。")
    
    return success


if __name__ == "__main__":
    exit(0 if main() else 1)