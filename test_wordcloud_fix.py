#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ワードクラウド文字化け修正テスト

日本語フォント検出と描画テストを行います。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.wordcloud.config import WordCloudConfig
from src.wordcloud.visualizer import WordCloudVisualizer

def test_font_detection():
    """フォント検出テスト"""
    print("=== フォント検出テスト ===")
    
    config = WordCloudConfig()
    visualizer = WordCloudVisualizer(config)
    
    font_path = visualizer._get_best_font_path()
    if font_path:
        print(f"✓ フォント検出成功: {font_path}")
        return True
    else:
        print("✗ フォント検出失敗")
        return False

def test_wordcloud_generation():
    """ワードクラウド生成テスト"""
    print("\n=== ワードクラウド生成テスト ===")
    
    # テスト用の日本語単語頻度データ
    test_frequencies = {
        "株価": 10,
        "市場": 8,
        "投資": 7,
        "経済": 6,
        "金融": 5,
        "ドル": 4,
        "円": 4,
        "トレード": 3,
        "収益": 3,
        "分析": 2
    }
    
    config = WordCloudConfig()
    visualizer = WordCloudVisualizer(config)
    
    try:
        result = visualizer.create_wordcloud_image(test_frequencies)
        
        if result.success:
            print(f"✓ ワードクラウド生成成功")
            print(f"  画像サイズ: {result.image_size_bytes} bytes")
            print(f"  品質スコア: {result.quality_score:.1f}")
            return True
        else:
            print(f"✗ ワードクラウド生成失敗: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"✗ 例外発生: {e}")
        return False

def main():
    """メインテスト"""
    print("ワードクラウド文字化け修正テスト開始\n")
    
    # 1. フォント検出テスト
    font_ok = test_font_detection()
    
    # 2. ワードクラウド生成テスト
    wordcloud_ok = test_wordcloud_generation()
    
    # 結果サマリー
    print("\n=== テスト結果サマリー ===")
    print(f"フォント検出: {'✓' if font_ok else '✗'}")
    print(f"ワードクラウド生成: {'✓' if wordcloud_ok else '✗'}")
    
    if font_ok and wordcloud_ok:
        print("\n🎉 すべてのテストが成功しました！")
        return 0
    else:
        print("\n⚠️  一部のテストが失敗しました。")
        return 1

if __name__ == "__main__":
    sys.exit(main())