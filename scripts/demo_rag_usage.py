#!/usr/bin/env python3
"""
RAGシステム使用例デモスクリプト

このスクリプトは、実際のMarket Newsシステムでの
RAG機能の使用方法を示すデモンストレーションです。

使用方法:
1. 環境変数を設定
2. python scripts/demo_rag_usage.py

デモ内容:
- 日次サマリーのアーカイブ
- 記事検索
- トレンド分析
- システム統合例
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.app_config import AppConfig
from src.rag.rag_manager import RAGManager


class RAGUsageDemo:
    """RAGシステム使用例デモクラス"""
    
    def __init__(self):
        """デモクラス初期化"""
        self.config = AppConfig()
        self.rag_manager = None
        
    def run_demo(self):
        """デモを実行"""
        print("🎬 RAGシステム使用例デモ")
        print("=" * 50)
        
        # RAGマネージャー初期化
        if not self._initialize_rag_manager():
            return False
        
        # デモシーケンス
        demos = [
            ("📚 日次サマリーアーカイブ", self._demo_daily_summary_archive),
            ("📄 記事アーカイブ", self._demo_article_archive),
            ("🔍 コンテンツ検索", self._demo_content_search),
            ("📊 トレンド分析", self._demo_trending_topics),
            ("🏢 システム統合例", self._demo_system_integration),
            ("📈 システム状態確認", self._demo_system_status)
        ]
        
        for demo_name, demo_func in demos:
            print(f"\n{demo_name}")
            print("-" * 30)
            try:
                demo_func()
                print("✅ 完了")
            except Exception as e:
                print(f"❌ エラー: {str(e)}")
        
        self._print_integration_tips()
        return True
    
    def _initialize_rag_manager(self):
        """RAGマネージャー初期化"""
        try:
            self.rag_manager = RAGManager(self.config)
            print("✅ RAGマネージャー初期化成功")
            return True
        except Exception as e:
            print(f"❌ RAGマネージャー初期化失敗: {str(e)}")
            print("環境設定を確認してください。")
            return False
    
    def _demo_daily_summary_archive(self):
        """日次サマリーアーカイブデモ"""
        # サンプル日次サマリー
        sample_summary = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "market_overview": "今日の市場は全体的に上昇傾向を示しました。",
            "key_events": [
                "日経平均株価が2%上昇",
                "新しいAI技術が発表",
                "中央銀行の政策発表"
            ],
            "sector_analysis": {
                "technology": "AI関連株が大幅上昇",
                "finance": "銀行株は横ばい",
                "manufacturing": "製造業は堅調"
            },
            "outlook": "明日も上昇トレンドが継続する可能性が高い"
        }
        
        try:
            result = self.rag_manager.archive_daily_summary(sample_summary)
            print("📚 日次サマリーをアーカイブしました")
            print(f"   ドキュメントID: {result.get('document_id', 'N/A')}")
            print(f"   チャンク数: {result.get('chunks_created', 0)}")
        except Exception as e:
            print(f"❌ アーカイブエラー: {str(e)}")
    
    def _demo_article_archive(self):
        """記事アーカイブデモ"""
        # サンプル記事
        sample_articles = [
            {
                "id": "demo_001",
                "title": "AI技術の新発表が市場に与える影響",
                "content": """
                本日、大手テクノロジー企業が新しいAI技術を発表しました。
                この技術は自然言語処理の分野で革新的な進歩をもたらすと
                期待されており、関連銘柄の株価が大幅に上昇しています。
                
                市場アナリストは、この技術が今後5年間で
                業界全体に大きな変革をもたらすと予測しています。
                特に、金融サービスや医療分野での応用が
                注目されています。
                """,
                "published_at": datetime.now().isoformat(),
                "category": "technology",
                "summary": "新AI技術発表により関連株価が上昇"
            },
            {
                "id": "demo_002", 
                "title": "中央銀行の金利政策発表",
                "content": """
                中央銀行は本日、政策金利を0.25%引き上げることを
                発表しました。この決定は、最近のインフレ圧力に
                対応するものと見られています。
                
                金融業界では、この決定が銀行の収益性向上に
                つながると歓迎されている一方、
                企業の借入コストの増加を懸念する声もあります。
                
                エコノミストは、今回の利上げが経済成長に
                与える影響を注視していると述べています。
                """,
                "published_at": datetime.now().isoformat(),
                "category": "finance",
                "summary": "中央銀行が政策金利を0.25%引き上げ"
            }
        ]
        
        try:
            result = self.rag_manager.archive_articles(sample_articles)
            print("📄 記事をアーカイブしました")
            print(f"   処理記事数: {result.get('processed_articles', 0)}")
            print(f"   作成チャンク数: {result.get('created_chunks', 0)}")
        except Exception as e:
            print(f"❌ アーカイブエラー: {str(e)}")
    
    def _demo_content_search(self):
        """コンテンツ検索デモ"""
        search_queries = [
            "AI技術",
            "金利政策", 
            "市場動向",
            "株価上昇"
        ]
        
        for query in search_queries:
            try:
                results = self.rag_manager.search_content(query, limit=3)
                print(f"🔍 検索「{query}」: {len(results)}件")
                
                for i, result in enumerate(results[:2], 1):
                    print(f"   {i}. {result.title[:40]}...")
                    print(f"      類似度: {result.similarity:.3f}")
                    print(f"      スニペット: {result.content[:60]}...")
                    
            except Exception as e:
                print(f"❌ 検索エラー「{query}」: {str(e)}")
    
    def _demo_trending_topics(self):
        """トレンド分析デモ"""
        try:
            # 過去7日間のトレンド分析
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            trends = self.rag_manager.get_trending_topics(
                start_date=start_date,
                end_date=end_date,
                limit=5
            )
            
            print("📊 過去7日間のトレンドトピック:")
            for i, trend in enumerate(trends[:3], 1):
                print(f"   {i}. {trend.get('topic', 'N/A')}")
                print(f"      出現頻度: {trend.get('frequency', 0)}")
                print(f"      関連度: {trend.get('relevance_score', 0):.2f}")
                
        except Exception as e:
            print(f"❌ トレンド分析エラー: {str(e)}")
    
    def _demo_system_integration(self):
        """システム統合例デモ"""
        print("🏢 Market NewsシステムでのRAG統合例:")
        
        # 既存のワークフローにRAG機能を統合する例
        integration_examples = [
            {
                "scenario": "日次レポート生成",
                "description": "既存の日次レポート生成後、自動でRAGシステムにアーカイブ",
                "code_example": """
# 既存のレポート生成後に追加
summary = generate_daily_summary()
rag_manager.archive_daily_summary(summary)
                """
            },
            {
                "scenario": "記事検索API",
                "description": "WebアプリケーションでのAI検索機能提供",
                "code_example": """
@app.route('/api/search')
def search_articles():
    query = request.args.get('q')
    results = rag_manager.search_content(query)
    return jsonify([r.to_dict() for r in results])
                """
            },
            {
                "scenario": "トレンド監視",
                "description": "定期的なトレンド分析による市場洞察",
                "code_example": """
# 毎日実行されるスケジュールタスク
def daily_trend_analysis():
    trends = rag_manager.get_trending_topics()
    send_trend_alert(trends)
                """
            }
        ]
        
        for example in integration_examples:
            print(f"\n   📋 {example['scenario']}")
            print(f"      {example['description']}")
            # コード例は長いので省略表示
            print(f"      実装例: {example['code_example'].split()[0]}...")
    
    def _demo_system_status(self):
        """システム状態確認デモ"""
        try:
            status = self.rag_manager.get_system_status()
            
            print("📈 RAGシステム状態:")
            print(f"   システム健全性: {'✅ OK' if status.get('system_healthy') else '❌ NG'}")
            print(f"   Supabase接続: {'✅ OK' if status.get('supabase_available') else '❌ NG'}")
            print(f"   総ドキュメント数: {status.get('total_documents', 0)}")
            print(f"   総チャンク数: {status.get('total_chunks', 0)}")
            
            # 記憶使用量（推定）
            embedding_size = status.get('total_chunks', 0) * 384 * 4  # float32
            print(f"   推定メモリ使用量: {embedding_size / 1024 / 1024:.1f} MB")
            
        except Exception as e:
            print(f"❌ システム状態確認エラー: {str(e)}")
    
    def _print_integration_tips(self):
        """統合のヒントを表示"""
        print("\n" + "=" * 50)
        print("💡 統合のヒント")
        print("=" * 50)
        
        tips = [
            "🔧 バッチ処理: 大量のデータは一度に処理せず、小さなバッチに分けて実行",
            "⏰ スケジューリング: cronやcelerを使って定期的なアーカイブジョブを設定",
            "🚦 エラーハンドリング: Supabase接続エラーに対する適切な例外処理を実装",
            "📊 監視: システム状態とパフォーマンスを定期的に監視",
            "💾 バックアップ: 重要なデータの定期バックアップを設定",
            "🔒 セキュリティ: サービスロールキーの適切な管理とアクセス制御"
        ]
        
        for tip in tips:
            print(f"   {tip}")
        
        print("\n📚 詳細な実装例:")
        print("   - scripts/test_rag_system.py: 完全なテストスイート")
        print("   - src/rag/rag_manager.py: メイン統合ポイント")
        print("   - docs/SUPABASE_USAGE_GUIDE.md: 設計ドキュメント")


def main():
    """メイン実行関数"""
    demo = RAGUsageDemo()
    success = demo.run_demo()
    
    if success:
        print("\n🎉 RAGシステムデモ完了！")
        print("実際の運用環境での統合の準備ができました。")
    else:
        print("\n❗ デモ実行中にエラーが発生しました。")
        print("設定を確認して再度実行してください。")
    
    return success


if __name__ == "__main__":
    exit(0 if main() else 1)