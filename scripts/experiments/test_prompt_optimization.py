#!/usr/bin/env python3
"""
プロンプト最適化テストスクリプト
新しいプロンプト管理システムとA/Bテスト機能をテスト
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.podcast.prompts import PromptManager, ABTestManager
from src.podcast.script_generation.professional_dialogue_script_generator import ProfessionalDialogueScriptGenerator

# 模擬記事データ
MOCK_ARTICLES = [
    {
        "index": 1,
        "title": "FRB、政策金利を据え置き決定",
        "summary": "米連邦準備制度理事会（FRB）は本日開催したFOMCで政策金利を5.25-5.5%で据え置くことを決定した。インフレ率の動向を注視しながら慎重に政策を検討する姿勢を示している。",
        "category": "金融政策",
        "region": "US",
        "importance_score": 0.95,
        "published_at": "2024年12月20日",
        "source": "Bloomberg"
    },
    {
        "index": 2,
        "title": "トヨタ自動車、四半期決算で増益",
        "summary": "トヨタ自動車が発表した2024年第3四半期決算は、売上高が前年同期比8%増の9兆2000億円、純利益は12%増の1兆2000億円となった。電動化戦略の進展が寄与している。",
        "category": "企業業績",
        "region": "Japan",
        "importance_score": 0.82,
        "published_at": "2024年12月19日",
        "source": "日経新聞"
    },
    {
        "index": 3,
        "title": "ビットコイン、10万ドル突破",
        "summary": "暗号資産ビットコインの価格が史上初めて10万ドルを突破した。機関投資家の参入拡大と規制環境の改善が背景にあるとの見方が強い。",
        "category": "暗号資産",
        "region": "Global",
        "importance_score": 0.78,
        "published_at": "2024年12月18日",
        "source": "Reuters"
    }
]

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('prompt_optimization_test.log')
        ]
    )
    return logging.getLogger(__name__)

def test_prompt_manager():
    """プロンプト管理システムテスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== プロンプト管理システムテスト開始 ===")
    
    try:
        # PromptManager初期化
        prompt_manager = PromptManager()
        
        # 利用可能パターン確認
        patterns = prompt_manager.get_available_patterns()
        logger.info(f"利用可能パターン: {patterns}")
        
        # 環境検証
        validation = prompt_manager.validate_environment()
        logger.info(f"環境検証結果: {validation}")
        
        # パターン別プロンプト生成テスト
        for pattern in patterns[:3]:  # 最初の3パターンをテスト
            try:
                logger.info(f"パターン {pattern} テスト中...")
                
                # プロンプト生成
                template_vars = {
                    "target_duration": 10.0,
                    "target_chars": 2700,
                    "target_chars_min": 2600,
                    "target_chars_max": 2800,
                    "main_content_chars": 2300,
                    "articles_data": "\n".join([f"【記事{i+1}】{article['title']}" for i, article in enumerate(MOCK_ARTICLES)]),
                    "generation_date": "2024年12月20日・金曜日",
                    "episode_number": 354
                }
                
                prompt = prompt_manager.load_prompt_template(pattern, **template_vars)
                logger.info(f"パターン {pattern}: プロンプト生成成功 ({len(prompt)}文字)")
                
            except Exception as e:
                logger.error(f"パターン {pattern} テストエラー: {e}")
        
        logger.info("=== プロンプト管理システムテスト完了 ===")
        return True
        
    except Exception as e:
        logger.error(f"プロンプト管理システムテストエラー: {e}")
        return False

async def test_ab_test_system():
    """A/Bテストシステムテスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== A/Bテストシステムテスト開始 ===")
    
    try:
        # 必要な環境変数設定
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY環境変数が設定されていません")
            return False
        
        # A/Bテストマネージャー初期化
        ab_test_manager = ABTestManager()
        
        # 台本生成器初期化
        script_generator = ProfessionalDialogueScriptGenerator(gemini_api_key)
        
        # 模擬記事データの準備
        from src.podcast.data_fetcher.enhanced_database_article_fetcher import ArticleScore
        from dataclasses import dataclass
        
        # 簡易的なArticleScoreクラス作成
        @dataclass
        class MockAnalysis:
            summary: str
            sentiment_score: float
            category: str = "金融"
            region: str = "global"
        
        @dataclass
        class MockArticle:
            title: str
            published_at: str
            source: str
        
        mock_article_scores = []
        for article in MOCK_ARTICLES:
            mock_article = MockArticle(
                title=article["title"],
                published_at=article["published_at"],
                source=article["source"]
            )
            mock_analysis = MockAnalysis(
                summary=article["summary"],
                sentiment_score=0.5,
                category=article["category"],
                region=article["region"]
            )
            mock_article_scores.append(ArticleScore(
                article=mock_article,
                analysis=mock_analysis,
                score=article["importance_score"]
            ))
        
        # 単一パターンテスト
        logger.info("単一パターンテスト実行中...")
        os.environ["PODCAST_PROMPT_PATTERN"] = "cot_enhanced"
        
        single_result = await ab_test_manager.run_comparison_test(
            script_generator, mock_article_scores, comparison_mode="single"
        )
        logger.info(f"単一パターンテスト完了: {single_result['test_id']}")
        
        # A/Bテスト（2パターン比較）
        logger.info("A/Bテスト実行中...")
        
        ab_result = await ab_test_manager.run_comparison_test(
            script_generator, mock_article_scores, comparison_mode="ab_test"
        )
        logger.info(f"A/Bテスト完了: {ab_result['test_id']}")
        
        # 比較レポート生成
        report = ab_test_manager.create_comparison_report(ab_result['test_id'])
        logger.info("比較レポート生成完了")
        
        # レポートをファイルに保存
        report_file = Path("prompt_comparison_report.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"比較レポート保存: {report_file}")
        
        logger.info("=== A/Bテストシステムテスト完了 ===")
        return True
        
    except Exception as e:
        logger.error(f"A/Bテストシステムテストエラー: {e}")
        return False

def test_github_actions_integration():
    """GitHub Actions統合テスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== GitHub Actions統合テスト開始 ===")
    
    try:
        # 環境変数シミュレーション
        test_env_vars = {
            "PODCAST_PROMPT_PATTERN": "few_shot_learning",
            "PODCAST_COMPARISON_MODE": "ab_test",
            "PODCAST_AB_TEST_MODE": "true"
        }
        
        # 環境変数設定
        for key, value in test_env_vars.items():
            os.environ[key] = value
            logger.info(f"環境変数設定: {key}={value}")
        
        # プロンプト管理システムが環境変数を正しく読み取るかテスト
        prompt_manager = PromptManager()
        
        selected_pattern = prompt_manager.get_environment_prompt_pattern()
        logger.info(f"環境変数から選択されたパターン: {selected_pattern}")
        
        # 比較モードのセットアップテスト
        ab_test_manager = ABTestManager(prompt_manager)
        comparison_patterns = ab_test_manager.setup_comparison_test("ab_test")
        logger.info(f"A/Bテスト対象パターン: {comparison_patterns}")
        
        logger.info("=== GitHub Actions統合テスト完了 ===")
        return True
        
    except Exception as e:
        logger.error(f"GitHub Actions統合テストエラー: {e}")
        return False

async def main():
    """メイン関数"""
    logger = setup_logging()
    logger.info("プロンプト最適化テストスクリプト開始")
    
    # テスト実行
    tests = [
        ("プロンプト管理システム", test_prompt_manager),
        ("GitHub Actions統合", test_github_actions_integration),
        ("A/Bテストシステム", test_ab_test_system),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"テスト実行: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
            logger.info(f"テスト {test_name}: {'✅ 成功' if result else '❌ 失敗'}")
        except Exception as e:
            logger.error(f"テスト {test_name} で例外発生: {e}")
            results[test_name] = False
    
    # 結果サマリー
    logger.info(f"\n{'='*50}")
    logger.info("テスト結果サマリー")
    logger.info(f"{'='*50}")
    
    for test_name, result in results.items():
        status = "✅ 成功" if result else "❌ 失敗"
        logger.info(f"{test_name}: {status}")
    
    total_tests = len(results)
    successful_tests = sum(results.values())
    logger.info(f"\n総テスト数: {total_tests}, 成功: {successful_tests}, 失敗: {total_tests - successful_tests}")
    
    if successful_tests == total_tests:
        logger.info("🎉 すべてのテストが成功しました！")
        return 0
    else:
        logger.error("⚠️ 一部のテストが失敗しました。")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)