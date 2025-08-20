#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
プロダクション版ポッドキャストシステム + Googleドキュメント連携テスト
"""

import os
import sys
import logging
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.podcast.integration.production_podcast_integration_manager import ProductionPodcastIntegrationManager

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/production_podcast_gdocs_test.log', encoding='utf-8')
    ]
)

def main():
    """メイン実行"""
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("プロダクション版ポッドキャストシステム + Googleドキュメント連携テスト")
    print("=" * 60)
    
    try:
        # 環境変数設定確認
        required_env_vars = [
            'GEMINI_API_KEY',
            'PODCAST_DATA_SOURCE',
            'GOOGLE_DOCUMENT_ID'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ 必要な環境変数が未設定です: {', '.join(missing_vars)}")
            print("\n設定例:")
            print("export PODCAST_DATA_SOURCE=google_document")
            print("export GOOGLE_DOCUMENT_ID=<your_document_id>")
            print("export GEMINI_API_KEY=<your_gemini_api_key>")
            return False
        
        # 設定情報表示
        data_source = os.getenv('PODCAST_DATA_SOURCE')
        google_doc_id = os.getenv('GOOGLE_DOCUMENT_ID')
        gemini_model = os.getenv('GEMINI_PODCAST_MODEL', 'gemini-2.5-pro-001')
        target_duration = float(os.getenv('PODCAST_TARGET_DURATION_MINUTES', '10.0'))
        
        print(f"データソース: {data_source}")
        print(f"GoogleドキュメントID: {google_doc_id}")
        print(f"Geminiモデル: {gemini_model}")
        print(f"目標配信時間: {target_duration}分")
        print()
        
        # プロダクション版マネージャー初期化
        manager = ProductionPodcastIntegrationManager()
        
        # システム状態確認
        print("📊 システム状態確認")
        print("-" * 30)
        
        status = manager.get_system_status()
        print(f"システム健全性: {'✅ OK' if status.get('system_healthy') else '❌ NG'}")
        print(f"データソース: {status.get('data_source')}")
        if status.get('google_document_id'):
            print(f"GoogleドキュメントID: {status.get('google_document_id')}")
        
        stats = status.get('article_statistics', {})
        if stats:
            print(f"記事統計: {stats}")
        
        config = status.get('configuration', {})
        print(f"設定 - モデル: {config.get('gemini_model')}")
        print(f"設定 - プロダクションモード: {config.get('production_mode')}")
        print()
        
        # テスト実行選択
        print("テスト実行オプション:")
        print("1. テストモード（実際の配信なし）")
        print("2. プロダクションモード（実際に配信）")
        print("3. システム状態確認のみ")
        
        choice = input("選択してください (1-3): ").strip()
        
        if choice == '1':
            print("\n🧪 テストモード実行")
            print("-" * 30)
            result = manager.generate_complete_podcast(test_mode=True)
            
        elif choice == '2':
            print("\n🚀 プロダクションモード実行")
            print("-" * 30)
            confirm = input("実際にポッドキャストを生成・配信しますか？ (y/N): ").strip().lower()
            if confirm == 'y':
                result = manager.generate_complete_podcast(test_mode=False)
            else:
                print("プロダクション実行をキャンセルしました。")
                return True
                
        elif choice == '3':
            print("\n✅ システム状態確認完了")
            return True
            
        else:
            print("❌ 無効な選択です。")
            return False
        
        # 結果表示
        print("\n" + "=" * 60)
        print("実行結果")
        print("=" * 60)
        
        if result.get('success'):
            print("✅ ポッドキャスト生成成功")
            
            # 詳細結果表示
            articles_analysis = result.get('articles_analysis', {})
            print(f"📈 記事分析:")
            print(f"  - 選択記事数: {articles_analysis.get('selected_count', 0)}")
            print(f"  - データソース: {articles_analysis.get('data_source', 'Unknown')}")
            
            # 記事詳細
            article_scores = articles_analysis.get('article_scores', [])
            for i, article in enumerate(article_scores, 1):
                print(f"  記事{i}: {article.get('title', 'Unknown')[:80]}...")
                print(f"    スコア: {article.get('score', 0):.2f}, カテゴリ: {article.get('category', 'Unknown')}")
            
            # 品質評価
            quality = result.get('quality_assessment', {})
            print(f"\n📋 品質評価:")
            print(f"  - 台本文字数: {quality.get('script_char_count', 0):,}")
            print(f"  - 推定配信時間: {quality.get('estimated_duration_minutes', 0):.1f}分")
            print(f"  - 品質スコア: {quality.get('quality_score', 0):.2f}/1.0")
            
            # システム性能
            metrics = result.get('system_metrics', {})
            print(f"\n⚡ システム性能:")
            print(f"  - 処理時間: {metrics.get('total_processing_time_seconds', 0):.1f}秒")
            print(f"  - 使用モデル: {metrics.get('script_generation_model', 'Unknown')}")
            
        else:
            print("❌ ポッドキャスト生成失敗")
            error = result.get('error', 'Unknown error')
            error_type = result.get('error_type', 'UnknownError')
            print(f"エラー: {error_type} - {error}")
        
        print(f"\n完了時刻: {result.get('completed_at', result.get('generated_at', 'Unknown'))}")
        
        return result.get('success', False)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  ユーザーによって中断されました。")
        return False
        
    except Exception as e:
        logger.error(f"テスト実行エラー: {e}", exc_info=True)
        print(f"\n❌ 予期せぬエラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    # ログディレクトリ作成
    Path('logs').mkdir(exist_ok=True)
    
    success = main()
    
    if success:
        print("\n🎉 テスト完了")
    else:
        print("\n💥 テスト失敗")
        sys.exit(1)