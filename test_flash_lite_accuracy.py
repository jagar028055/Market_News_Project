# -*- coding: utf-8 -*-

"""
Flash-liteの分類精度テスト
現在の地域・カテゴリ分類がどの程度正確かを確認
"""

import os
import sys
from dotenv import load_dotenv

# プロジェクトのルートを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_summarizer import process_article_with_ai

# 環境変数読み込み
load_dotenv()

def test_flash_lite_classification():
    """Flash-liteの分類精度をテスト"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY環境変数が設定されていません")
        return
    
    # テスト記事データ（実際の経済ニュースの例）
    test_articles = [
        {
            "title": "日銀、政策金利を据え置き　インフレ目標達成まで緩和継続",
            "content": "日本銀行は26日の金融政策決定会合で、政策金利を-0.1%に据え置くことを決定した。植田和男総裁は記者会見で、2%のインフレ目標達成まで緩和的な金融政策を継続する方針を示した。",
            "expected_region": "japan",
            "expected_category": "金融政策"
        },
        {
            "title": "FRB、0.25%利上げ実施　インフレ抑制優先の姿勢鮮明に",
            "content": "米連邦準備制度理事会（FRB）は25日、連邦公開市場委員会（FOMC）で政策金利を0.25ポイント引き上げ、年5.0-5.25%とすることを決定した。パウエル議長はインフレ抑制を最優先課題とする姿勢を改めて強調した。",
            "expected_region": "usa",
            "expected_category": "金融政策"
        },
        {
            "title": "トヨタ自動車、四半期決算で過去最高益　海外販売好調",
            "content": "トヨタ自動車は8日、2024年4-6月期の連結決算を発表し、純利益が前年同期比1.7倍の1兆3311億円となった。北米や欧州での販売が好調で、四半期ベースで過去最高益を更新した。",
            "expected_region": "japan",
            "expected_category": "企業業績"
        },
        {
            "title": "中国GDP成長率、第2四半期は6.3%　回復ペース鈍化",
            "content": "中国国家統計局は17日、2024年第2四半期の国内総生産（GDP）成長率が前年同期比6.3%だったと発表した。第1四半期の8.1%から大幅に減速し、経済回復のペースが鈍化している。",
            "expected_region": "china",
            "expected_category": "経済指標"
        },
        {
            "title": "ECB、金利据え置き　ユーロ圏インフレ減速受け",
            "content": "欧州中央銀行（ECB）は26日、政策金利を4.0%に据え置くことを決定した。ユーロ圏のインフレ率が目標の2%に近づいていることを受け、追加利上げを見送った。ラガルド総裁は慎重な姿勢を示した。",
            "expected_region": "europe",
            "expected_category": "金融政策"
        },
        {
            "title": "Apple、iPhone15発表　AI機能を大幅強化",
            "content": "米アップルは12日、新型スマートフォン「iPhone 15」シリーズを発表した。生成AI機能を大幅に強化し、カメラ性能も向上させた。価格は999ドルからで、9月22日に発売予定。",
            "expected_region": "usa",
            "expected_category": "企業業績"
        }
    ]
    
    print("🧪 Flash-lite分類精度テスト開始")
    print("=" * 50)
    
    total_tests = len(test_articles)
    region_correct = 0
    category_correct = 0
    
    for i, article in enumerate(test_articles, 1):
        print(f"\n📰 テスト {i}/{total_tests}")
        print(f"タイトル: {article['title']}")
        print(f"期待値: 地域={article['expected_region']}, カテゴリ={article['expected_category']}")
        
        # Flash-liteでAI分析実行
        result = process_article_with_ai(api_key, article['content'])
        
        if result:
            actual_region = result.get('region', 'その他')
            actual_category = result.get('category', 'その他')
            summary = result.get('summary', '')
            
            print(f"実際の値: 地域={actual_region}, カテゴリ={actual_category}")
            print(f"要約: {summary[:100]}...")
            
            # 正解判定
            region_match = actual_region == article['expected_region']
            category_match = actual_category == article['expected_category']
            
            if region_match:
                region_correct += 1
                print("✅ 地域判定: 正解")
            else:
                print("❌ 地域判定: 不正解")
            
            if category_match:
                category_correct += 1
                print("✅ カテゴリ判定: 正解")
            else:
                print("❌ カテゴリ判定: 不正解")
                
        else:
            print("❌ AI分析失敗")
        
        print("-" * 30)
    
    # 結果サマリー
    print(f"\n📊 テスト結果サマリー")
    print("=" * 50)
    print(f"地域判定精度: {region_correct}/{total_tests} ({region_correct/total_tests*100:.1f}%)")
    print(f"カテゴリ判定精度: {category_correct}/{total_tests} ({category_correct/total_tests*100:.1f}%)")
    print(f"総合精度: {(region_correct + category_correct)}/{total_tests*2} ({(region_correct + category_correct)/(total_tests*2)*100:.1f}%)")
    
    # 推奨アクション
    if region_correct / total_tests < 0.7:
        print("\n⚠️  地域判定精度が低いです（70%未満）")
        print("推奨: プロンプト改善またはモデル変更を検討")
    elif region_correct / total_tests < 0.9:
        print("\n📈 地域判定精度は中程度です（70-90%）")
        print("推奨: プロンプト調整で改善可能")
    else:
        print("\n✅ 地域判定精度は良好です（90%以上）")
    
    if category_correct / total_tests < 0.7:
        print("\n⚠️  カテゴリ判定精度が低いです（70%未満）")
        print("推奨: プロンプト改善またはモデル変更を検討")
    elif category_correct / total_tests < 0.9:
        print("\n📈 カテゴリ判定精度は中程度です（70-90%）")
        print("推奨: プロンプト調整で改善可能")
    else:
        print("\n✅ カテゴリ判定精度は良好です（90%以上）")

if __name__ == "__main__":
    test_flash_lite_classification()