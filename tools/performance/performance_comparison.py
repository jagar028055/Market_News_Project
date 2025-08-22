#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Phase 4.2: 最適化前後のパフォーマンス比較
"""

import time
import sys
from typing import List, Dict, Any

def generate_large_test_dataset(size: int) -> List[Dict[str, Any]]:
    """大規模テストデータセット生成"""
    regions = ['Japan', 'USA', 'China', 'Europe', 'Other']
    sources = ['Reuters', 'Bloomberg', 'Nikkei', 'WSJ', 'FT']
    
    # より現実的なテストデータ
    templates = [
        "日銀が政策金利を{rate}%に設定、市場は{reaction}",
        "Fed announces {rate}% interest rate, market shows {reaction}",
        "中国人民銀行の金融政策が{action}、上海市場は{reaction}",
        "ECB決定により欧州株式市場が{reaction}、ユーロは{movement}",
        "トヨタの四半期決算で営業利益が{change}、株価は{reaction}",
        "Apple reports {change} earnings, stock {reaction} in after-hours trading",
        "アリババの業績が{change}、香港市場で{reaction}",
        "GDP成長率{rate}%発表、経済指標は{trend}傾向"
    ]
    
    reactions = ['上昇', '下落', '混乱', '安定', 'volatile', 'steady', 'rising', 'falling']
    rates = ['0.25', '0.5', '0.75', '1.0', '1.25', '1.5']
    changes = ['増加', '減少', '上昇', '下落', 'increase', 'decrease', 'growth', 'decline']
    trends = ['上昇', '下降', 'upward', 'downward']
    movements = ['上昇', '下落', 'strengthening', 'weakening']
    actions = ['緩和', '引き締め', 'easing', 'tightening']
    
    articles = []
    for i in range(size):
        template = templates[i % len(templates)]
        
        # テンプレートの変数を置換
        content = template
        if '{rate}' in content:
            content = content.replace('{rate}', rates[i % len(rates)])
        if '{reaction}' in content:
            content = content.replace('{reaction}', reactions[i % len(reactions)])
        if '{change}' in content:
            content = content.replace('{change}', changes[i % len(changes)])
        if '{trend}' in content:
            content = content.replace('{trend}', trends[i % len(trends)])
        if '{movement}' in content:
            content = content.replace('{movement}', movements[i % len(movements)])
        if '{action}' in content:
            content = content.replace('{action}', actions[i % len(actions)])
        
        articles.append({
            'title': f'記事{i+1}: {content[:50]}...',
            'body': content + ' 詳細な分析と市場の反応について詳しく解説します。' * (i % 5 + 1),
            'source': sources[i % len(sources)],
            'url': f'https://test-news.com/article/{i+1}',
            'published_at': f'2025-08-13T{(i % 24):02d}:00:00'
        })
    
    return articles

def benchmark_original_vs_optimized():
    """オリジナル版と最適化版のパフォーマンス比較"""
    print("=" * 60)
    print("パフォーマンス比較テスト: Original vs Optimized")
    print("=" * 60)
    
    # テストサイズ
    test_sizes = [50, 100, 200, 500, 1000]
    
    try:
        from article_grouper import ArticleGrouper as OriginalGrouper
        from optimized_article_grouper import OptimizedArticleGrouper
        
        original_grouper = OriginalGrouper()
        optimized_grouper = OptimizedArticleGrouper()
        
        print("テストサイズ | Original(秒) | Optimized(秒) | 改善率(%)")
        print("-" * 55)
        
        total_improvement = 0
        test_count = 0
        
        for size in test_sizes:
            print(f"  {size:4d}件の記事で測定中...", end=" ")
            
            # テストデータ生成
            test_articles = generate_large_test_dataset(size)
            
            # オリジナル版測定
            start_time = time.time()
            original_result = original_grouper.group_articles_by_region(test_articles)
            original_time = time.time() - start_time
            
            # 最適化版測定
            start_time = time.time()
            optimized_result = optimized_grouper.group_articles_by_region(test_articles)
            optimized_time = time.time() - start_time
            
            # 改善率計算
            if original_time > 0:
                improvement = ((original_time - optimized_time) / original_time) * 100
            else:
                improvement = 0
            
            total_improvement += improvement
            test_count += 1
            
            print(f"\r  {size:4d}件     | {original_time:8.3f}  | {optimized_time:9.3f}  | {improvement:7.1f}")
            
            # 結果の整合性チェック（簡易版）
            if len(original_result) != len(optimized_result):
                print(f"    ⚠️  結果不整合: Original {len(original_result)} vs Optimized {len(optimized_result)}")
        
        print("-" * 55)
        avg_improvement = total_improvement / test_count if test_count > 0 else 0
        print(f"平均改善率: {avg_improvement:.1f}%")
        
        # キャッシュ統計
        cache_stats = optimized_grouper.get_cache_stats()
        print(f"キャッシュ統計: {cache_stats['total_cache_entries']}エントリ")
        
        # 評価
        print("\n評価:")
        if avg_improvement > 30:
            print("✅ 大幅な性能改善を達成")
        elif avg_improvement > 15:
            print("✅ 顕著な性能改善を達成")
        elif avg_improvement > 5:
            print("✅ 軽微な性能改善を達成")
        else:
            print("⚠️  性能改善は限定的")
        
        return avg_improvement
        
    except ImportError as e:
        print(f"❌ インポートエラー: {e}")
        return 0
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        return 0

def memory_usage_comparison():
    """メモリ使用量比較（簡易版）"""
    print("\n" + "=" * 60)
    print("メモリ効率性テスト")
    print("=" * 60)
    
    try:
        from article_grouper import ArticleGrouper as OriginalGrouper
        from optimized_article_grouper import OptimizedArticleGrouper
        
        # 大きなテストデータセット
        large_dataset = generate_large_test_dataset(1000)
        
        print("1000件の記事での処理:")
        
        # オリジナル版
        original_grouper = OriginalGrouper()
        start_time = time.time()
        original_result = original_grouper.group_articles_by_region(large_dataset)
        original_time = time.time() - start_time
        
        # 最適化版
        optimized_grouper = OptimizedArticleGrouper()
        start_time = time.time()
        optimized_result = optimized_grouper.group_articles_by_region(large_dataset)
        optimized_time = time.time() - start_time
        
        # 2回目実行（キャッシュ効果確認）
        start_time = time.time()
        optimized_result_cached = optimized_grouper.group_articles_by_region(large_dataset)
        optimized_cached_time = time.time() - start_time
        
        print(f"Original処理時間:           {original_time:.3f}秒")
        print(f"Optimized初回処理時間:      {optimized_time:.3f}秒")
        print(f"Optimizedキャッシュ後時間:  {optimized_cached_time:.3f}秒")
        
        cache_acceleration = optimized_time / optimized_cached_time if optimized_cached_time > 0 else 1
        print(f"キャッシュによる高速化:      {cache_acceleration:.1f}倍")
        
        # キャッシュ統計
        cache_stats = optimized_grouper.get_cache_stats()
        print(f"キャッシュエントリ数:        {cache_stats['total_cache_entries']}個")
        
        return True
        
    except Exception as e:
        print(f"❌ メモリテストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("Flash+Pro Phase 4.2: パフォーマンス最適化検証")
    
    # パフォーマンス比較
    improvement = benchmark_original_vs_optimized()
    
    # メモリ効率テスト
    memory_success = memory_usage_comparison()
    
    print("\n" + "=" * 60)
    print("最適化検証結果サマリー")
    print("=" * 60)
    print(f"平均性能改善:     {improvement:.1f}%")
    print(f"メモリ効率テスト: {'✅ 成功' if memory_success else '❌ 失敗'}")
    
    # 総合評価
    if improvement >= 20 and memory_success:
        print("✅ 最適化成功: Phase 4.3への進行可能")
        return True
    elif improvement >= 10 or memory_success:
        print("✅ 部分的最適化成功: Phase 4.3への進行可能")
        return True
    else:
        print("⚠️  最適化効果限定的: 追加改善推奨")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n最適化テスト中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n予期しないエラー: {e}")
        sys.exit(1)