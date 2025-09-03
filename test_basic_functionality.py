#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SNSコンテンツ機能改善システムの基本機能テスト
外部依存関係なしでテスト可能な部分を確認する
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
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)

def test_model_imports():
    """モデルクラスのインポートテスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== モデルクラスインポートテスト開始 ===")
    
    try:
        from src.market_data.models import (
            MarketData, MarketDataType, StockIndex, CurrencyPair, 
            CommodityPrice, MarketSnapshot, MarketSentiment
        )
        logger.info("✅ マーケットデータモデルインポート成功")
        
        # データクラスのインスタンス作成テスト
        test_data = MarketData(
            symbol="TEST",
            name="Test Asset",
            current_price=100.0,
            previous_close=99.0,
            change=1.0,
            change_percent=1.01,
            timestamp=datetime.now(),
            data_type=MarketDataType.STOCK_INDEX
        )
        logger.info(f"✅ MarketDataインスタンス作成成功: {test_data.symbol}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ モデルクラスインポートテストでエラー: {e}")
        return False

def test_content_models():
    """コンテンツ関連モデルのテスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== コンテンツモデルテスト開始 ===")
    
    try:
        from src.content.models import TemplateType, ContentSection
        logger.info("✅ コンテンツモデルインポート成功")
        
        # Enumの値確認
        template_types = list(TemplateType)
        logger.info(f"✅ テンプレートタイプ定義確認: {len(template_types)}種類")
        for template in template_types:
            logger.info(f"  - {template.value}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ コンテンツモデルテストでエラー: {e}")
        return False

def test_quality_models():
    """品質チェック関連モデルのテスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== 品質モデルテスト開始 ===")
    
    try:
        # 類似度チェッカー（外部依存なし部分）
        from src.quality.similarity_checker import SimilarityChecker
        
        checker = SimilarityChecker(logger=logger)
        logger.info("✅ SimilarityCheckerインスタンス作成成功")
        
        # 単純なテキスト処理テスト
        test_text = "これはテストです。日本語のトークン化をテストします。"
        tokens = checker._tokenize_japanese(test_text)
        logger.info(f"✅ 日本語トークン化テスト成功: {len(tokens)}トークン")
        
        # 空の記事リストでの類似度チェック
        empty_result = checker.check_similarity_batch([])
        logger.info(f"✅ 空記事リストでの処理成功: 多様性スコア={empty_result['diversity_score']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 品質モデルテストでエラー: {e}")
        return False

def test_template_logic():
    """テンプレート選択ロジックのテスト（外部依存なし部分）"""
    logger = logging.getLogger(__name__)
    logger.info("=== テンプレート選択ロジックテスト開始 ===")
    
    try:
        from src.content.template_selector import TemplateSelector
        from src.content.models import TemplateType
        
        selector = TemplateSelector(logger=logger)
        logger.info("✅ TemplateSelectorインスタンス作成成功")
        
        # テンプレート設定の取得テスト
        for template_type in TemplateType:
            config = selector.get_template_config(template_type)
            logger.info(f"✅ {template_type.value}設定取得成功: 優先度={config.get('priority', 'N/A')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ テンプレート選択ロジックテストでエラー: {e}")
        return False

def test_basic_similarity_check():
    """基本的な類似度チェック機能のテスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== 基本類似度チェック機能テスト開始 ===")
    
    try:
        from src.quality.similarity_checker import SimilarityChecker
        
        checker = SimilarityChecker(logger=logger)
        
        # テスト用記事データ
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
            },
            {
                'title': 'FRB金利据え置き、パウエル議長が会見',
                'summary': 'FRBは政策金利を維持し、パウエル議長が今後の見通しについて説明した。',
                'category': '金融政策',
                'region': 'usa',
                'source': 'AP'
            }
        ]
        
        # 類似度チェック実行
        similarity_results = checker.check_similarity_batch(test_articles)
        
        logger.info(f"✅ 類似度チェック成功:")
        logger.info(f"  - 記事数: {similarity_results['total_articles']}")
        logger.info(f"  - 類似ペア: {len(similarity_results['similar_pairs'])}組")
        logger.info(f"  - 多様性スコア: {similarity_results['diversity_score']}")
        
        # レポート生成テスト
        report = checker.get_similarity_report(similarity_results)
        logger.info(f"✅ 類似度レポート生成成功 (長さ: {len(report)}文字)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 基本類似度チェック機能テストでエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    logger = setup_logging()
    logger.info("🚀 SNSコンテンツ機能改善システム基本機能テスト開始")
    
    test_results = {}
    
    # 各テストを実行
    tests = [
        ("モデルクラスインポート", test_model_imports),
        ("コンテンツモデル", test_content_models),
        ("品質モデル", test_quality_models),
        ("テンプレート選択ロジック", test_template_logic),
        ("基本類似度チェック", test_basic_similarity_check)
    ]
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"テスト実行: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            test_results[test_name] = "✅ 成功" if result else "❌ 失敗"
        except Exception as e:
            logger.error(f"テスト {test_name} で予期しないエラー: {e}")
            test_results[test_name] = "❌ エラー"
    
    # テスト結果サマリー
    logger.info(f"\n{'='*50}")
    logger.info("📊 基本機能テスト結果サマリー")
    logger.info(f"{'='*50}")
    
    success_count = 0
    for test_name, result in test_results.items():
        logger.info(f"{result} {test_name}")
        if "✅" in result:
            success_count += 1
    
    success_rate = success_count / len(test_results) * 100
    logger.info(f"\n📈 成功率: {success_count}/{len(test_results)} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        logger.info("🎉 基本機能テスト成功！")
    elif success_rate >= 60:
        logger.info("⚠️  基本機能テスト部分的に成功。")
    else:
        logger.error("💥 基本機能テストで多くの問題発生。")
    
    return success_rate >= 60

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)