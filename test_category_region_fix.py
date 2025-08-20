# -*- coding: utf-8 -*-

"""
個別記事の地域・カテゴリ表示問題の修正を検証するテストスクリプト
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# 環境変数を読み込む
load_dotenv()

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.core.news_processor import NewsProcessor
from src.database.database_manager import DatabaseManager
from src.config.app_config import get_config
from ai_summarizer import process_article_with_ai

def test_ai_analysis_with_category_region():
    """AI分析結果にcategory/regionが含まれているかテスト"""
    print("=== AI分析結果のcategory/region確認テスト ===")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEYが設定されていません")
        return False
    
    test_text = """
    米連邦準備制度理事会（FRB）は26日、連邦公開市場委員会（FOMC）で政策金利を据え置くことを決定した。
    これは市場の予想通りであり、インフレ抑制と経済成長のバランスを慎重に見極める姿勢を示している。
    パウエル議長は記者会見で、今後の金融政策について「データ次第」と繰り返し述べ、
    利下げの時期については具体的な言及を避けた。
    """
    
    result = process_article_with_ai(api_key, test_text)
    
    if result:
        print(f"✅ AI分析結果取得成功:")
        print(f"   要約: {result.get('summary', 'なし')[:50]}...")
        print(f"   地域: {result.get('region', 'なし')}")
        print(f"   カテゴリ: {result.get('category', 'なし')}")
        
        if result.get('region') != 'その他' and result.get('category') != 'その他':
            print("✅ category/regionが正しく設定されています")
            return True
        else:
            print("⚠️  category/regionが「その他」のままです")
            return False
    else:
        print("❌ AI分析結果の取得に失敗しました")
        return False

def test_database_save_load():
    """データベースのcategory/region保存・読み込みテスト"""
    print("\n=== データベースsave/load確認テスト ===")
    
    try:
        config = get_config()
        db_manager = DatabaseManager(config.database)
        
        # テスト記事を保存
        test_article = {
            'url': 'https://test.example.com/test-article-category-region',
            'title': 'FRB政策金利据え置きテスト記事',
            'body': 'テスト用の記事本文です',
            'source': 'TestSource',
            'published_at': datetime.utcnow()
        }
        
        article_id, is_new = db_manager.save_article(test_article)
        
        if article_id:
            print(f"✅ テスト記事保存成功 (ID: {article_id})")
            
            # AI分析結果を保存
            analysis_data = {
                'summary': 'FRBが政策金利を据え置いたテスト要約',
                'sentiment_label': 'Neutral',
                'sentiment_score': 0.0,
                'category': '金融政策',
                'region': 'usa'
            }
            
            ai_analysis = db_manager.save_ai_analysis(article_id, analysis_data)
            print(f"✅ AI分析結果保存成功")
            
            # データ取得テスト
            article_with_analysis = db_manager.get_article_by_url_with_analysis(test_article['url'])
            
            if article_with_analysis and article_with_analysis.ai_analysis:
                analysis = article_with_analysis.ai_analysis[0]
                print(f"✅ データ取得成功:")
                print(f"   カテゴリ: {analysis.category}")
                print(f"   地域: {analysis.region}")
                
                if analysis.category == '金融政策' and analysis.region == 'usa':
                    print("✅ category/regionが正しく保存・取得されました")
                    return True
                else:
                    print("❌ category/regionが正しく保存されていません")
                    return False
            else:
                print("❌ AI分析結果の取得に失敗しました")
                return False
        else:
            print("❌ テスト記事の保存に失敗しました")
            return False
            
    except Exception as e:
        print(f"❌ データベーステスト中にエラー: {e}")
        return False

def test_html_generation():
    """HTML生成時のcategory/region表示テスト"""
    print("\n=== HTML生成確認テスト ===")
    
    try:
        processor = NewsProcessor()
        
        # テストデータ
        test_articles = [
            {
                'title': 'FRB政策金利据え置き',
                'url': 'https://test.example.com/frb-test',
                'source': 'TestSource',
                'published_jst': datetime.now(),
                'summary': 'FRBが政策金利を据え置いた',
                'sentiment_label': 'Neutral',
                'sentiment_score': 0.0,
                'category': '金融政策',
                'region': 'usa'
            },
            {
                'title': '日銀の金融政策決定',
                'url': 'https://test.example.com/boj-test',
                'source': 'TestSource', 
                'published_jst': datetime.now(),
                'summary': '日銀が金融政策を決定した',
                'sentiment_label': 'Positive',
                'sentiment_score': 0.8,
                'category': '金融政策',
                'region': 'japan'
            }
        ]
        
        # HTMLジェネレーターのテスト
        processor.html_generator.generate_html_file(test_articles, "test_category_region.html")
        
        # 生成されたHTMLファイルを確認
        if os.path.exists("test_category_region.html"):
            with open("test_category_region.html", 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # category/regionが含まれているかチェック
            if 'data-region="usa"' in html_content and 'data-category="金融政策"' in html_content:
                print("✅ HTMLに正しくcategory/regionが含まれています")
                
                # バッジ表示もチェック
                if '🇺🇸' in html_content and '🏦' in html_content:
                    print("✅ 地域・カテゴリバッジも正しく表示されています")
                    return True
                else:
                    print("⚠️  バッジ表示に問題がある可能性があります")
                    return False
            else:
                print("❌ HTMLにcategory/regionが含まれていません")
                return False
        else:
            print("❌ テスト用HTMLファイルが生成されませんでした")
            return False
            
    except Exception as e:
        print(f"❌ HTML生成テスト中にエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("個別記事の地域・カテゴリ表示問題の修正検証を開始します\n")
    
    test_results = []
    
    # AI分析テスト
    test_results.append(test_ai_analysis_with_category_region())
    
    # データベーステスト
    test_results.append(test_database_save_load())
    
    # HTML生成テスト
    test_results.append(test_html_generation())
    
    # 結果サマリー
    print("\n" + "="*50)
    print("テスト結果サマリー:")
    print(f"総テスト数: {len(test_results)}")
    print(f"成功: {sum(test_results)}")
    print(f"失敗: {len(test_results) - sum(test_results)}")
    
    if all(test_results):
        print("🎉 すべてのテストが成功しました！")
        print("個別記事の地域・カテゴリ表示問題は修正されています。")
    else:
        print("⚠️  一部のテストが失敗しました。修正を確認してください。")
    
    # クリーンアップ
    if os.path.exists("test_category_region.html"):
        os.remove("test_category_region.html")
        print("\nテスト用ファイルをクリーンアップしました。")

if __name__ == "__main__":
    main()