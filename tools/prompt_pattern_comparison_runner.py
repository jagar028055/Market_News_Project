#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
7プロンプトパターン一括実行・Googleドキュメント比較出力システム
すべてのプロンプトパターンで台本生成を実行し、結果をGoogleドキュメントで比較出力
"""

import os
import sys
import json
import logging
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# プロジェクトルートを追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.podcast.prompts.ab_test_manager import ABTestManager
from src.podcast.prompts.prompt_manager import PromptManager
from src.podcast.script_generator import ScriptGenerator
from src.podcast.data_fetcher.enhanced_database_article_fetcher import EnhancedDatabaseArticleFetcher


class PromptPatternComparisonRunner:
    """7プロンプトパターン一括実行・比較システム"""
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
        self.prompt_manager = PromptManager()
        self.ab_test_manager = ABTestManager(self.prompt_manager)
        self.results_dir = Path("prompt_comparison_results")
        self.results_dir.mkdir(exist_ok=True)
        
        # 設定
        self.target_duration = float(os.getenv('PODCAST_TARGET_DURATION_MINUTES', '10.0'))
        self.target_articles = int(os.getenv('COMPARISON_TARGET_ARTICLES', '15'))
        self.skip_audio_generation = True  # 音声生成をスキップ
        
        self.logger.info("プロンプトパターン比較システム初期化完了")
    
    async def run_full_comparison(self) -> Dict[str, Any]:
        """
        7つのプロンプトパターンで一括比較実行
        
        Returns:
            Dict[str, Any]: 比較結果
        """
        start_time = time.time()
        comparison_id = f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(f"7プロンプトパターン一括比較開始: {comparison_id}")
        
        try:
            # 記事データ取得
            articles = await self._fetch_articles()
            if not articles:
                raise ValueError("記事データの取得に失敗しました")
                
            self.logger.info(f"記事データ取得完了: {len(articles)}件")
            
            # スクリプトジェネレーター初期化
            script_generator = ScriptGenerator()
            
            # 全プロンプトパターンで比較実行
            comparison_result = await self.ab_test_manager.run_comparison_test(
                script_generator=script_generator,
                articles=articles,
                target_duration=self.target_duration,
                comparison_mode="multi_compare"
            )
            
            total_time = time.time() - start_time
            
            # 結果を拡張
            enhanced_result = {
                "comparison_id": comparison_id,
                "execution_timestamp": datetime.now().isoformat(),
                "total_execution_time_seconds": total_time,
                "system_config": {
                    "target_duration_minutes": self.target_duration,
                    "target_articles_count": self.target_articles,
                    "skip_audio_generation": self.skip_audio_generation,
                    "gemini_model": os.getenv('GEMINI_PODCAST_MODEL', 'gemini-2.5-pro')
                },
                "articles_metadata": {
                    "total_articles": len(articles),
                    "selected_articles": [
                        {
                            "title": article.get("title", "")[:100],
                            "category": article.get("category", "unknown"),
                            "pub_date": article.get("pub_date", "")
                        } for article in articles[:10]  # 最初の10記事の情報
                    ]
                },
                "comparison_results": comparison_result
            }
            
            # 結果保存
            await self._save_comparison_results(comparison_id, enhanced_result)
            
            # Googleドキュメント出力
            if self._should_generate_gdoc():
                gdoc_result = await self._generate_google_document(enhanced_result)
                enhanced_result["google_document"] = gdoc_result
                
            self.logger.info(f"7プロンプトパターン比較完了: {comparison_id} (実行時間: {total_time:.1f}秒)")
            return enhanced_result
            
        except Exception as e:
            self.logger.error(f"比較実行エラー: {e}", exc_info=True)
            return {
                "comparison_id": comparison_id,
                "error": str(e),
                "execution_timestamp": datetime.now().isoformat(),
                "total_execution_time_seconds": time.time() - start_time
            }
    
    async def _fetch_articles(self) -> List[Dict[str, Any]]:
        """記事データを取得"""
        try:
            # データソースに応じた記事取得
            data_source = os.getenv('PODCAST_DATA_SOURCE', 'database')
            
            if data_source == 'database':
                # データベースから記事取得
                fetcher = EnhancedDatabaseArticleFetcher()
                articles = await fetcher.fetch_articles(limit=self.target_articles)
                return articles
                
            elif data_source == 'google_document':
                # Googleドキュメントから記事取得
                from src.podcast.data_fetcher.google_document_data_fetcher import GoogleDocumentDataFetcher
                fetcher = GoogleDocumentDataFetcher()
                articles = await fetcher.fetch_articles()
                return articles[:self.target_articles]
                
            else:
                self.logger.warning(f"未知のデータソース: {data_source}")
                return []
                
        except Exception as e:
            self.logger.error(f"記事取得エラー: {e}")
            return []
    
    async def _save_comparison_results(self, comparison_id: str, results: Dict[str, Any]) -> None:
        """比較結果をJSONファイルに保存"""
        try:
            result_file = self.results_dir / f"{comparison_id}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            
            self.logger.info(f"比較結果保存: {result_file}")
            
        except Exception as e:
            self.logger.error(f"比較結果保存エラー: {e}")
    
    def _should_generate_gdoc(self) -> bool:
        """Googleドキュメント生成が必要かチェック"""
        # Google認証情報の確認
        google_vars = [
            'GOOGLE_OAUTH2_CLIENT_ID',
            'GOOGLE_OAUTH2_CLIENT_SECRET', 
            'GOOGLE_OAUTH2_REFRESH_TOKEN'
        ]
        
        return all(os.getenv(var) for var in google_vars)
    
    async def _generate_google_document(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Googleドキュメントで比較レポートを生成"""
        try:
            # Googleドキュメント比較生成器をインポート
            from src.podcast.gdocs.comparison_doc_generator import ComparisonDocGenerator
            
            doc_generator = ComparisonDocGenerator()
            
            # Googleドキュメント生成
            doc_result = await doc_generator.create_comparison_document(
                comparison_results=results,
                title=f"プロンプトパターン比較レポート_{results['comparison_id']}"
            )
            
            self.logger.info(f"Googleドキュメント生成完了: {doc_result.get('document_url', 'N/A')}")
            return doc_result
            
        except ImportError:
            self.logger.warning("Googleドキュメント生成器が見つかりません")
            return {"error": "ComparisonDocGenerator not found"}
        except Exception as e:
            self.logger.error(f"Googleドキュメント生成エラー: {e}")
            return {"error": str(e)}
    
    def print_execution_summary(self, results: Dict[str, Any]) -> None:
        """実行結果のサマリーを表示"""
        print("\n" + "="*80)
        print("🔍 7プロンプトパターン一括比較実行結果")
        print("="*80)
        
        if "error" in results:
            print(f"❌ 実行エラー: {results['error']}")
            return
            
        # 基本情報
        print(f"📊 比較ID: {results['comparison_id']}")
        print(f"⏱️  実行時間: {results['total_execution_time_seconds']:.1f}秒")
        print(f"📰 対象記事数: {results['articles_metadata']['total_articles']}")
        
        # 比較結果
        comparison_results = results.get("comparison_results", {})
        pattern_results = comparison_results.get("pattern_results", {})
        
        print(f"\n📋 パターン別実行結果:")
        print("-" * 50)
        
        successful_patterns = 0
        failed_patterns = 0
        
        for pattern_id, result in pattern_results.items():
            if "error" in result:
                print(f"❌ {pattern_id}: エラー - {result['error'][:50]}...")
                failed_patterns += 1
            else:
                char_count = result.get("char_count", 0)
                quality_score = result.get("quality_score", 0)
                gen_time = result.get("generation_time", 0)
                
                print(f"✅ {pattern_id}:")
                print(f"   文字数: {char_count:,}, 品質: {quality_score:.3f}, 時間: {gen_time:.1f}秒")
                successful_patterns += 1
        
        print(f"\n📈 実行サマリー:")
        print(f"  成功: {successful_patterns}パターン")
        print(f"  失敗: {failed_patterns}パターン")
        
        # 最優秀パターン
        best_pattern = comparison_results.get("comparison_analysis", {}).get("best_pattern")
        if best_pattern:
            print(f"\n🏆 最優秀パターン: {best_pattern['pattern']}")
            print(f"  総合スコア: {best_pattern['score']:.3f}")
        
        # Googleドキュメント
        if "google_document" in results:
            gdoc_result = results["google_document"]
            if "document_url" in gdoc_result:
                print(f"\n📄 Googleドキュメント: {gdoc_result['document_url']}")
            elif "error" in gdoc_result:
                print(f"\n❌ Googleドキュメント生成エラー: {gdoc_result['error']}")


async def main():
    """メイン実行関数"""
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/prompt_comparison.log', encoding='utf-8')
        ]
    )
    
    # ログディレクトリ作成
    Path('logs').mkdir(exist_ok=True)
    
    logger = logging.getLogger(__name__)
    
    try:
        # 必須環境変数チェック
        required_env_vars = ['GEMINI_API_KEY']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"❌ 必要な環境変数が未設定: {', '.join(missing_vars)}")
            return False
        
        print("🚀 7プロンプトパターン一括比較システム開始")
        print("-" * 60)
        
        # 比較システム実行
        runner = PromptPatternComparisonRunner()
        results = await runner.run_full_comparison()
        
        # 結果表示
        runner.print_execution_summary(results)
        
        return not ("error" in results)
        
    except KeyboardInterrupt:
        print("\n\n⏹️ ユーザーによって中断されました")
        return False
        
    except Exception as e:
        logger.error(f"メイン実行エラー: {e}", exc_info=True)
        print(f"\n❌ 予期せぬエラー: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        print("\n🎉 比較システム実行完了")
    else:
        print("\n💥 比較システム実行失敗")
        sys.exit(1)