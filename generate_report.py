#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Content Processing結果レポート生成スクリプト
"""

import json
import sys
from pathlib import Path

def generate_summary_report(results_file: str):
    """処理結果サマリーをMarkdown形式で生成"""
    try:
        if not Path(results_file).exists():
            print("⚠️ 処理結果ファイルが生成されませんでした")
            return
        
        with open(results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        print(f"- 入力記事数: {results.get('input_article_count', 'N/A')}")
        print(f"- 拡張記事生成数: {len(results.get('enhanced_articles', []))}")
        print(f"- マーケットコンテキスト: {'利用' if results.get('market_context') else '利用不可'}")
        print(f"- 選択テンプレート: {results.get('selected_template', {}).get('template_type', 'N/A')}")
        
        # 地域分析結果
        if results.get('region_analysis'):
            print("\n### 地域別記事数")
            region_names = {'japan': '日本', 'usa': '米国', 'europe': '欧州'}
            for region, count in results.get('region_analysis', {}).items():
                if region in region_names and count > 0:
                    print(f"- {region_names[region]}: {count}件")
        
        # 品質チェック結果
        if results.get('quality_check_results'):
            qr_summary = results['quality_check_results']['summary']
            if 'summary' in qr_summary:
                qr = qr_summary['summary']
                print(f"- 品質合格率: {qr.get('pass_rate', 'N/A')}%")
                if 'average_score' in qr:
                    print(f"- 平均品質スコア: {qr['average_score']:.1f}")
        
        # 類似度チェック結果
        if results.get('similarity_check_results'):
            sr = results['similarity_check_results']
            print(f"- 類似記事ペア: {len(sr.get('similar_pairs', []))}組")
            print(f"- 多様性スコア: {sr.get('diversity_score', 'N/A')}")
        
        # ファクトチェック結果
        if results.get('fact_check_results'):
            fr = results['fact_check_results']
            print(f"- ファクトチェック平均精度: {fr.get('average_accuracy', 'N/A')}%")
            if 'high_confidence_articles' in fr and 'total_articles' in fr:
                print(f"- 高信頼度記事: {fr['high_confidence_articles']}/{fr['total_articles']}")
        
        # 警告とエラー
        if results.get('warnings'):
            print(f"- 警告: {len(results['warnings'])}件")
        if results.get('errors'):
            print(f"- エラー: {len(results['errors'])}件")
            
    except Exception as e:
        print(f"結果ファイル読み込みエラー: {e}")

if __name__ == "__main__":
    results_file = sys.argv[1] if len(sys.argv) > 1 else "results/enhanced_content_results.json"
    generate_summary_report(results_file)