#!/usr/bin/env python3
"""
台本生成改善のテスト

PromptManager統合とAI定型句除去機能のテストを実行します。
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.podcast.script_generator import DialogueScriptGenerator

def test_script_generation():
    """台本生成の基本テスト"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY環境変数が設定されていません")
        return False
    
    print("🧪 台本生成テスト開始")
    
    # テスト用記事データ
    test_articles = [
        {
            "title": "日銀が政策金利据え置き、追加緩和見送り",
            "content": "日本銀行は本日の金融政策決定会合で、政策金利を現行のマイナス0.1％のまま据え置くことを決定した。追加の金融緩和策は見送られ、市場関係者の注目を集めていた。",
            "published": "2024-01-15T10:00:00Z"
        },
        {
            "title": "東証大引け：3日続伸、33,000円台回復",
            "content": "15日の東京株式市場で日経平均株価は3日続伸し、終値は前営業日比234円67銭高の33,123円45銭となった。約1カ月ぶりに33,000円台を回復した。",
            "published": "2024-01-15T15:00:00Z"
        },
        {
            "title": "ドル円、一時150円台に下落",
            "content": "外国為替市場でドル円相場が軟調に推移し、一時150円台まで下落した。日銀の金融政策据え置きを受けて円買いが優勢となっている。",
            "published": "2024-01-15T14:30:00Z"
        }
    ]
    
    try:
        # DialogueScriptGeneratorを初期化（PromptManager統合版）
        generator = DialogueScriptGenerator(api_key, prompt_pattern="current_professional")
        
        print("🎯 台本生成実行中...")
        script = generator.generate_script(test_articles)
        
        print("✅ 台本生成成功")
        print(f"📊 生成された台本の文字数: {len(script)}")
        
        # AI定型句チェック
        problematic_phrases = [
            "はい、承知いたしました",
            "以下が台本です",
            "台本を作成しました",
            "完成させた台本を以下に",
            "承知しました",
            "分かりました"
        ]
        
        found_issues = []
        for phrase in problematic_phrases:
            if phrase in script:
                found_issues.append(phrase)
        
        if found_issues:
            print("⚠️  AI定型句が検出されました:")
            for issue in found_issues:
                print(f"   - '{issue}'")
        else:
            print("✅ AI定型句は検出されませんでした")
        
        # 台本の先頭を表示
        print("\n📄 生成された台本の先頭部分:")
        print("=" * 50)
        print(script[:500] + "..." if len(script) > 500 else script)
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        return False

def test_prompt_pattern_selection():
    """異なるプロンプトパターンのテスト"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY環境変数が設定されていません")
        return False
    
    print("\n🔄 プロンプトパターン選択テスト")
    
    try:
        # 利用可能なパターンを確認
        from src.podcast.prompts.prompt_manager import PromptManager
        
        prompt_manager = PromptManager()
        available_patterns = prompt_manager.get_available_patterns()
        
        print(f"📋 利用可能なプロンプトパターン: {available_patterns}")
        
        for pattern in available_patterns[:2]:  # 最初の2つをテスト
            print(f"\n🎯 パターン '{pattern}' をテスト中...")
            
            generator = DialogueScriptGenerator(api_key, prompt_pattern=pattern)
            pattern_info = prompt_manager.get_pattern_info(pattern)
            
            print(f"   パターン名: {pattern_info.get('name', 'N/A')}")
            print(f"   説明: {pattern_info.get('description', 'N/A')}")
            print(f"   温度設定: {pattern_info.get('temperature', 'N/A')}")
            
        return True
        
    except Exception as e:
        print(f"❌ プロンプトパターンテスト失敗: {e}")
        return False

if __name__ == "__main__":
    print("🚀 台本生成改善テスト開始")
    
    success = True
    success &= test_script_generation()
    success &= test_prompt_pattern_selection()
    
    if success:
        print("\n🎉 全テスト成功！台本生成の改善が正常に動作しています")
    else:
        print("\n❌ 一部テストに失敗しました")
    
    sys.exit(0 if success else 1)