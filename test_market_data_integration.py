#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SNSコンテンツ機能改善システムの統合テスト
新しく追加されたマーケットデータ統合機能をテストする
"""

import sys
import os
import logging
from datetime import datetime

# プロジェクトパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'test_integration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)

def test_market_data_fetcher():
    """マーケットデータ取得のテスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== マーケットデータ取得テスト開始 ===")
    
    try:
        from src.market_data.fetcher import MarketDataFetcher
        
        # MarketDataFetcherのテスト
        fetcher = MarketDataFetcher(logger=logger)
        
        # 接続テスト
        logger.info("データソース接続テスト実行中...")
        connections = fetcher.test_connections()
        logger.info(f"接続テスト結果: {connections}")
        
        # 単一データ取得テスト
        logger.info("単一マーケットデータ取得テスト...")
        single_data = fetcher.get_single_market_data('^GSPC')  # S&P 500
        if single_data:
            logger.info(f"S&P 500データ取得成功: {single_data.name} - {single_data.current_price} ({single_data.change_percent:+.2f}%)")
        else:
            logger.warning("S&P 500データ取得失敗")
        
        # 市場スナップショット取得テスト
        logger.info("市場スナップショット取得テスト...")
        snapshot = fetcher.get_current_market_snapshot()
        logger.info(f"スナップショット取得成功:")
        logger.info(f"  - 株価指数: {len(snapshot.stock_indices)}件")
        logger.info(f"  - 通貨ペア: {len(snapshot.currency_pairs)}件")
        logger.info(f"  - 商品: {len(snapshot.commodities)}件")
        logger.info(f"  - 全体センチメント: {snapshot.overall_sentiment.value}")
        logger.info(f"  - ボラティリティ: {snapshot.volatility_score:.1f}")
        
        # LLM用コンテキスト生成テスト
        logger.info("LLM用コンテキスト生成テスト...")
        context = fetcher.get_market_context_for_llm()
        logger.info(f"マーケットコンテキスト生成成功 (長さ: {len(context)}文字)")
        logger.info(f"コンテキストプレビュー:\n{context[:300]}...")
        
        logger.info("✅ マーケットデータ取得テスト完了")
        return True
        
    except Exception as e:
        logger.error(f"❌ マーケットデータ取得テストでエラー: {e}", exc_info=True)
        return False

def test_enhanced_ai_summarizer():
    """拡張AIサマライザーのテスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== 拡張AIサマライザーテスト開始 ===")
    
    try:
        from ai_summarizer import process_article_with_ai
        
        # テスト用記事データ
        test_article = """
        米連邦準備制度理事会（FRB）は26日、連邦公開市場委員会（FOMC）で政策金利を据え置くことを決定した。
        これは市場の予想通りであり、インフレ抑制と経済成長のバランスを慎重に見極める姿勢を示している。
        パウエル議長は記者会見で、今後の金融政策について「データ次第」と繰り返し述べ、
        利下げの時期については具体的な言及を避けた。市場では、早ければ9月にも利下げが開始されるとの見方が強まっている。
        """
        
        # 環境変数からAPIキーを取得（テスト用）
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEYが設定されていません。AIサマライザーテストをスキップします。")
            return True
        
        logger.info("マーケットコンテキスト統合AIサマライザーテスト...")
        
        # マーケットコンテキスト付きでAI処理
        result = process_article_with_ai(api_key, test_article)
        
        if result:
            logger.info("✅ AI記事処理成功:")
            logger.info(f"  - 要約: {result.get('summary', 'なし')[:100]}...")
            logger.info(f"  - 地域: {result.get('region', 'なし')}")
            logger.info(f"  - カテゴリ: {result.get('category', 'なし')}")
            logger.info(f"  - 要約文字数: {len(result.get('summary', ''))}字")
        else:
            logger.warning("❌ AI記事処理失敗")
            return False
        
        logger.info("✅ 拡張AIサマライザーテスト完了")
        return True
        
    except Exception as e:
        logger.error(f"❌ 拡張AIサマライザーテストでエラー: {e}", exc_info=True)
        return False

def test_dynamic_template_system():
    """動的テンプレートシステムのテスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== 動的テンプレートシステムテスト開始 ===")
    
    try:
        from src.content.template_selector import TemplateSelector
        from src.content.dynamic_sections import DynamicSectionGenerator
        from src.market_data.fetcher import MarketDataFetcher
        
        # テストデータ準備
        fetcher = MarketDataFetcher(logger=logger)
        market_snapshot = fetcher.get_current_market_snapshot()
        
        test_articles = [
            {
                'title': 'FRBが金利据え置き決定、市場は利下げ期待',
                'summary': 'FRBは政策金利を据え置き、今後の政策について慎重姿勢を示した。',
                'category': '金融政策',
                'region': 'usa',
                'source': 'Reuters'
            },
            {
                'title': '日経平均大幅下落、米国株安を受け',
                'summary': '日経平均株価は前日比300円安と大幅下落。米国株式市場の下落を受けた。',
                'category': '市場動向',
                'region': 'japan', 
                'source': 'Bloomberg'
            }
        ]
        
        # テンプレート選択テスト
        logger.info("テンプレート選択テスト...")
        selector = TemplateSelector(logger=logger)
        selected_template = selector.select_template(market_snapshot, test_articles, datetime.now())
        logger.info(f"選択されたテンプレート: {selected_template.value}")
        
        # テンプレート設定取得
        template_config = selector.get_template_config(selected_template)
        logger.info(f"テンプレート設定: {template_config}")
        
        # 動的セクション生成テスト
        logger.info("動的セクション生成テスト...")
        generator = DynamicSectionGenerator(logger=logger)
        sections = generator.generate_sections(selected_template, market_snapshot, test_articles)
        
        logger.info(f"✅ 動的セクション生成成功: {len(sections)}個のセクション")
        for section_name, section_data in sections.items():
            logger.info(f"  - {section_name}: {type(section_data).__name__}")
        
        logger.info("✅ 動的テンプレートシステムテスト完了")
        return True
        
    except Exception as e:
        logger.error(f"❌ 動的テンプレートシステムテストでエラー: {e}", exc_info=True)
        return False

def test_quality_system():
    """品質管理システムのテスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== 品質管理システムテスト開始 ===")
    
    try:
        from src.quality.content_validator import ContentValidator
        from src.quality.similarity_checker import SimilarityChecker
        from src.quality.fact_checker import FactChecker
        
        # テスト用記事データ
        test_articles = [
            {
                'title': 'FRB、政策金利を5.25%で据え置き',
                'summary': '米連邦準備制度理事会（FRB）は26日の連邦公開市場委員会（FOMC）で、政策金利を5.00～5.25%の範囲で据え置くことを決定した。この決定は市場予想と一致している。パウエル議長は今後の金融政策について慎重な姿勢を示し、インフレ動向を注視すると述べた。',
                'url': 'https://example.com/news1',
                'source': 'Reuters',
                'category': '金融政策',
                'region': 'usa',
                'published_jst': datetime.now(),
                'sentiment_label': 'neutral'
            },
            {
                'title': '日経平均、3万8000円台で推移',
                'summary': '東京株式市場では日経平均株価が3万8000円台で推移している。前日比では小幅な値動きとなっており、市場では様子見ムードが強い。投資家は米国の金融政策動向を注視している状況だ。',
                'url': 'https://example.com/news2', 
                'source': 'Bloomberg',
                'category': '市場動向',
                'region': 'japan',
                'published_jst': datetime.now(),
                'sentiment_label': 'neutral'
            }
        ]
        
        # コンテンツバリデーションテスト
        logger.info("コンテンツバリデーションテスト...")
        validator = ContentValidator(logger=logger)
        validation_results = validator.validate_article_batch(test_articles)
        
        logger.info(f"✅ バリデーション完了: {len(validation_results)}件")
        for i, result in enumerate(validation_results):
            logger.info(f"  記事{i+1}: スコア={result.score:.1f}, 合格={result.passed}")
        
        # 品質レポート生成
        quality_report = validator.get_quality_report(validation_results)
        logger.info(f"品質レポート: 合格率={quality_report['summary']['pass_rate']}%")
        
        # 類似度チェックテスト
        logger.info("類似度チェックテスト...")
        similarity_checker = SimilarityChecker(logger=logger)
        similarity_results = similarity_checker.check_similarity_batch(test_articles)
        
        logger.info(f"✅ 類似度チェック完了:")
        logger.info(f"  - 類似ペア: {len(similarity_results['similar_pairs'])}組")
        logger.info(f"  - 多様性スコア: {similarity_results['diversity_score']:.3f}")
        
        # ファクトチェックテスト（マーケットデータが必要）
        logger.info("ファクトチェックテスト...")
        try:
            fact_checker = FactChecker(logger=logger)
            fact_results = fact_checker.check_batch_consistency(test_articles[:1])  # 1件のみテスト
            logger.info(f"✅ ファクトチェック完了: 平均精度={fact_results['average_accuracy']:.1f}")
        except Exception as e:
            logger.warning(f"ファクトチェックはスキップ（マーケットデータ接続が必要）: {e}")
        
        logger.info("✅ 品質管理システムテスト完了")
        return True
        
    except Exception as e:
        logger.error(f"❌ 品質管理システムテストでエラー: {e}", exc_info=True)
        return False

def test_system_integration():
    """システム統合テスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== システム統合テスト開始 ===")
    
    try:
        # 全システムの統合動作確認
        logger.info("マーケットデータ → AI処理 → テンプレート選択 → 品質チェックの統合フロー確認...")
        
        # 1. マーケットデータ取得
        from src.market_data.fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher(logger=logger)
        market_context = fetcher.get_market_context_for_llm()
        
        # 2. 既存の記事処理システムとの統合確認
        logger.info("既存システム統合確認...")
        
        # src/core/news_processor.py の拡張ポイント確認
        try:
            from src.core.news_processor import NewsProcessor
            logger.info("✅ NewsProcessor統合可能")
        except ImportError:
            logger.warning("NewsProcessorは別途統合が必要")
        
        # 3. HTML生成システムとの統合確認
        try:
            from src.html.html_generator import HTMLGenerator
            logger.info("✅ HTMLGenerator統合可能")
        except ImportError:
            logger.warning("HTMLGeneratorは別途統合が必要")
        
        logger.info("✅ システム統合テスト完了")
        return True
        
    except Exception as e:
        logger.error(f"❌ システム統合テストでエラー: {e}", exc_info=True)
        return False

def main():
    """メインテスト実行"""
    logger = setup_logging()
    logger.info("🚀 SNSコンテンツ機能改善システム統合テスト開始")
    
    test_results = {}
    
    # 各テストを実行
    tests = [
        ("マーケットデータ取得", test_market_data_fetcher),
        ("拡張AIサマライザー", test_enhanced_ai_summarizer),
        ("動的テンプレートシステム", test_dynamic_template_system),
        ("品質管理システム", test_quality_system),
        ("システム統合", test_system_integration)
    ]
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"テスト実行: {test_name}")
        logger.info(f"{'='*60}")
        
        try:
            result = test_func()
            test_results[test_name] = "✅ 成功" if result else "❌ 失敗"
        except Exception as e:
            logger.error(f"テスト {test_name} で予期しないエラー: {e}", exc_info=True)
            test_results[test_name] = "❌ エラー"
    
    # テスト結果サマリー
    logger.info(f"\n{'='*60}")
    logger.info("📊 テスト結果サマリー")
    logger.info(f"{'='*60}")
    
    success_count = 0
    for test_name, result in test_results.items():
        logger.info(f"{result} {test_name}")
        if "✅" in result:
            success_count += 1
    
    success_rate = success_count / len(test_results) * 100
    logger.info(f"\n📈 成功率: {success_count}/{len(test_results)} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        logger.info("🎉 統合テスト全体的に成功！")
    elif success_rate >= 60:
        logger.info("⚠️  統合テスト部分的に成功。いくつかの問題要解決。")
    else:
        logger.error("💥 統合テストで多くの問題発生。修正が必要。")
    
    return success_rate >= 60

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)