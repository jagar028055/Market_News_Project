# -*- coding: utf-8 -*-

"""
分類修正のテスト
修正前後の地域・カテゴリ分類結果を比較
"""

import os
import sys
from typing import Dict, Any

# プロジェクトのルートを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_old_region_determination(article_data: Dict[str, Any]) -> str:
    """修正前の地域判定ロジック"""
    title = article_data.get("title", "").lower()
    summary = article_data.get("summary", "").lower()
    text = f"{title} {summary}"
    
    # 修正前の簡易地域判定
    if any(keyword in text for keyword in ["日本", "日銀", "東京", "円", "toyota", "sony"]):
        return "japan"
    elif any(keyword in text for keyword in ["米国", "fed", "dollar", "apple", "microsoft"]):
        return "usa"  
    elif any(keyword in text for keyword in ["中国", "yuan", "china", "beijing"]):
        return "china"
    elif any(keyword in text for keyword in ["欧州", "ecb", "euro", "europe"]):
        return "europe"
    else:
        return "other"

def test_new_region_determination(article_data: Dict[str, Any]) -> str:
    """修正後の地域判定ロジック"""
    title = article_data.get("title", "").lower()
    summary = article_data.get("summary", "").lower()
    text = f"{title} {summary}"
    
    # 地域別キーワード（拡張版）
    region_keywords = {
        "japan": [
            # 機関・通貨
            "日本", "日銀", "円相場", "円高", "円安", "日本円", "yen", "jpy",
            # 場所・市場
            "東京", "tokyo", "日経", "nikkei", "topix", "jasdaq",
            # 企業（主要）
            "toyota", "sony", "nintendo", "softbank", "ntt", "kddi", 
            "三菱", "mitsubishi", "sumitomo", "住友", "みずほ", "mizuho",
            # 政府・政策
            "岸田", "自民党", "政府", "japan", "japanese"
        ],
        "usa": [
            # 機関・通貨
            "米国", "アメリカ", "fed", "fomc", "dollar", "usd", "ドル",
            # 場所・市場
            "ニューヨーク", "new york", "nasdaq", "s&p", "dow", "wall street",
            # 企業（主要）
            "apple", "microsoft", "google", "amazon", "tesla", "meta",
            "nvidia", "disney", "goldman", "jp morgan", "boeing",
            # 政府・政策
            "biden", "trump", "congress", "senate", "white house", "us", "american"
        ],
        "china": [
            # 機関・通貨
            "中国", "china", "chinese", "人民銀行", "人民元", "yuan", "cny",
            # 場所・市場
            "北京", "beijing", "上海", "shanghai", "深圳", "shenzhen",
            # 企業・経済
            "alibaba", "tencent", "baidu", "xiaomi", "huawei", "byd",
            # 政府・政策
            "習近平", "communist party", "prc"
        ],
        "europe": [
            # 機関・通貨
            "欧州", "europe", "european", "ecb", "euro", "eur", "ユーロ",
            # 場所・市場
            "ロンドン", "london", "パリ", "paris", "ベルリン", "berlin",
            "フランクフルト", "frankfurt", "dax", "ftse", "cac",
            # 企業・経済
            "volkswagen", "bmw", "mercedes", "siemens", "sap", "asml",
            # 政府・政策
            "eu", "brexit", "uk", "germany", "france", "italy"
        ]
    }
    
    # 各地域のスコア計算
    region_scores = {}
    for region, keywords in region_keywords.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > 0:
            region_scores[region] = score
    
    # 最高スコアの地域を返す
    if region_scores:
        best_region = max(region_scores, key=region_scores.get)
        return best_region
    else:
        return "other"

def test_classification_improvements():
    """分類精度の改善をテスト"""
    
    test_articles = [
        {
            "title": "岸田首相、経済対策の追加検討を表明",
            "summary": "岸田文雄首相は25日、経済対策の追加検討を表明した。日本の経済成長を促進するため、新たな政策パッケージを年内に策定する方針。",
            "expected_region": "japan"
        },
        {
            "title": "パウエルFRB議長、インフレ警戒を継続",
            "summary": "パウエル米連邦準備制度理事会（FRB）議長は24日、インフレに対する警戒を継続する必要があると述べた。米国経済の動向を注視していく。",
            "expected_region": "usa"
        },
        {
            "title": "習近平主席、経済改革の加速を指示",
            "summary": "中国の習近平国家主席は23日、経済改革の加速を関係部門に指示した。中国経済の持続的成長に向けた新たな施策を検討する。",
            "expected_region": "china"
        },
        {
            "title": "Nvidia決算、AI需要で大幅増益",
            "summary": "米半導体大手Nvidiaが22日発表した四半期決算は、人工知能（AI）向けチップの需要急増により大幅な増益となった。株価も急上昇している。",
            "expected_region": "usa"
        },
        {
            "title": "BMW、電気自動車の販売目標を上方修正",
            "summary": "独自動車大手BMWは21日、電気自動車（EV）の販売目標を上方修正すると発表した。欧州での需要拡大を受けた措置。",
            "expected_region": "europe"
        },
        {
            "title": "アリババ、クラウド事業の分離を検討",
            "summary": "中国電子商取引大手のアリババグループは20日、クラウド事業の分離を検討していると発表した。事業の専門性向上が狙い。",
            "expected_region": "china"
        },
        {
            "title": "ソニー、ゲーム事業の収益が好調",
            "summary": "ソニーグループは19日、ゲーム事業の収益が好調に推移していると発表した。PlayStation 5の販売台数が前年を大幅に上回っている。",
            "expected_region": "japan"
        },
        {
            "title": "ユーロ圏GDP、予想上回る成長",
            "summary": "欧州連合（EU）統計局は18日、ユーロ圏の第2四半期GDP成長率が予想を上回ったと発表した。欧州経済の回復が鮮明になっている。",
            "expected_region": "europe"
        }
    ]
    
    print("🔬 分類改善テスト開始")
    print("=" * 60)
    
    old_correct = 0
    new_correct = 0
    total_tests = len(test_articles)
    
    for i, article in enumerate(test_articles, 1):
        print(f"\n📰 テスト {i}/{total_tests}")
        print(f"タイトル: {article['title']}")
        print(f"期待値: {article['expected_region']}")
        
        # 修正前の判定
        old_result = test_old_region_determination(article)
        old_match = old_result == article['expected_region']
        if old_match:
            old_correct += 1
        
        # 修正後の判定
        new_result = test_new_region_determination(article)
        new_match = new_result == article['expected_region']
        if new_match:
            new_correct += 1
        
        print(f"修正前: {old_result} {'✅' if old_match else '❌'}")
        print(f"修正後: {new_result} {'✅' if new_match else '❌'}")
        
        if not old_match and new_match:
            print("🎉 改善されました！")
        elif old_match and not new_match:
            print("⚠️ 悪化しました")
        
        print("-" * 40)
    
    # 結果サマリー
    print(f"\n📊 改善テスト結果")
    print("=" * 60)
    print(f"修正前の精度: {old_correct}/{total_tests} ({old_correct/total_tests*100:.1f}%)")
    print(f"修正後の精度: {new_correct}/{total_tests} ({new_correct/total_tests*100:.1f}%)")
    
    improvement = new_correct - old_correct
    if improvement > 0:
        print(f"🎯 改善: +{improvement}件 (+{improvement/total_tests*100:.1f}%)")
    elif improvement < 0:
        print(f"⚠️  悪化: {improvement}件 ({improvement/total_tests*100:.1f}%)")
    else:
        print("📊 変化なし")
    
    # Flash-liteの分析結果活用をシミュレーション
    print(f"\n🤖 Flash-lite結果活用のシミュレーション")
    print("=" * 60)
    
    # Flash-liteが正しく分類するケースをシミュレーション
    flash_lite_cases = [
        {"ai_region": "japan", "ai_category": "企業業績", "fallback_region": "other"},
        {"ai_region": "usa", "ai_category": "金融政策", "fallback_region": "other"},
        {"ai_region": "china", "ai_category": "経済指標", "fallback_region": "other"},
        {"ai_region": "europe", "ai_category": "市場動向", "fallback_region": "other"},
    ]
    
    flash_lite_improved = 0
    for case in flash_lite_cases:
        ai_region = case["ai_region"]
        fallback_region = case["fallback_region"]
        
        # 修正前: Flash-lite結果を無視してフォールバック
        old_final = fallback_region
        
        # 修正後: Flash-lite結果を優先
        new_final = ai_region if ai_region != "その他" else fallback_region
        
        if old_final == "other" and new_final != "other":
            flash_lite_improved += 1
    
    print(f"Flash-lite結果活用による改善見込み: {flash_lite_improved}/{len(flash_lite_cases)}件")
    print(f"「その他」分類削減効果: {flash_lite_improved/len(flash_lite_cases)*100:.1f}%")

if __name__ == "__main__":
    test_classification_improvements()