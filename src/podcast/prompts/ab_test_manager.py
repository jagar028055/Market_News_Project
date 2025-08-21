# -*- coding: utf-8 -*-

"""
A/Bテスト・プロンプト比較評価システム
複数のプロンプトパターンを同時実行して比較評価
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import time

from .prompt_manager import PromptManager


class ABTestManager:
    """A/Bテスト管理クラス"""
    
    def __init__(self, prompt_manager: Optional[PromptManager] = None):
        """
        初期化
        
        Args:
            prompt_manager: プロンプト管理インスタンス（オプション）
        """
        self.logger = logging.getLogger(__name__)
        self.prompt_manager = prompt_manager or PromptManager()
        
        # 結果保存ディレクトリ
        self.results_dir = self.prompt_manager.prompts_dir / "ab_test_results"
        self.results_dir.mkdir(exist_ok=True)
        
        self.logger.info("A/Bテスト管理システム初期化完了")
    
    def setup_comparison_test(self, comparison_mode: str) -> List[str]:
        """
        比較テストのセットアップ
        
        Args:
            comparison_mode: 比較モード（single/ab_test/multi_compare）
            
        Returns:
            List[str]: テスト対象パターンリスト
        """
        if comparison_mode == "single":
            # 単一パターン（環境変数から）
            pattern = self.prompt_manager.get_environment_prompt_pattern()
            return [pattern]
            
        elif comparison_mode == "ab_test":
            # A/Bテスト（2パターン比較）
            return self.prompt_manager.setup_ab_test()
            
        elif comparison_mode == "multi_compare":
            # 全パターン比較
            return self.prompt_manager.get_available_patterns()
            
        else:
            self.logger.warning(f"未知の比較モード: {comparison_mode}")
            return [self.prompt_manager.get_environment_prompt_pattern()]
    
    async def run_comparison_test(
        self, 
        script_generator,
        articles, 
        target_duration: float = 10.0,
        comparison_mode: str = "single"
    ) -> Dict[str, Any]:
        """
        比較テスト実行
        
        Args:
            script_generator: 台本生成器インスタンス
            articles: 記事データ
            target_duration: 目標時間
            comparison_mode: 比較モード
            
        Returns:
            Dict[str, Any]: 比較テスト結果
        """
        try:
            test_id = f"comparison_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.logger.info(f"比較テスト開始: {test_id} (モード: {comparison_mode})")
            
            # テスト対象パターンを決定
            test_patterns = self.setup_comparison_test(comparison_mode)
            
            if not test_patterns:
                raise ValueError("テスト対象パターンが見つかりません")
            
            self.logger.info(f"テスト対象パターン: {test_patterns}")
            
            # 各パターンで台本生成（並列実行）
            results = {}
            start_time = time.time()
            
            # ThreadPoolExecutorで並列実行
            with ThreadPoolExecutor(max_workers=min(len(test_patterns), 3)) as executor:
                futures = {}
                
                for pattern in test_patterns:
                    future = executor.submit(
                        self._generate_script_for_pattern,
                        script_generator, articles, target_duration, pattern
                    )
                    futures[pattern] = future
                
                # 結果収集
                for pattern, future in futures.items():
                    try:
                        pattern_result = future.result(timeout=300)  # 5分タイムアウト
                        results[pattern] = pattern_result
                        self.logger.info(f"パターン {pattern} 完了")
                    except Exception as e:
                        self.logger.error(f"パターン {pattern} エラー: {e}")
                        results[pattern] = {"error": str(e)}
            
            total_time = time.time() - start_time
            
            # 比較分析
            comparison_analysis = self._analyze_comparison_results(results)
            
            # 結果をまとめる
            final_result = {
                "test_id": test_id,
                "comparison_mode": comparison_mode,
                "test_patterns": test_patterns,
                "total_execution_time": total_time,
                "pattern_results": results,
                "comparison_analysis": comparison_analysis,
                "best_pattern": comparison_analysis.get("best_pattern"),
                "test_timestamp": datetime.now().isoformat()
            }
            
            # 結果保存
            self._save_comparison_results(test_id, final_result)
            
            self.logger.info(f"比較テスト完了: {test_id} (実行時間: {total_time:.1f}秒)")
            return final_result
            
        except Exception as e:
            self.logger.error(f"比較テスト実行エラー: {e}")
            raise
    
    def _generate_script_for_pattern(
        self, script_generator, articles, target_duration: float, pattern: str
    ) -> Dict[str, Any]:
        """
        特定パターンでの台本生成
        
        Args:
            script_generator: 台本生成器
            articles: 記事データ
            target_duration: 目標時間
            pattern: プロンプトパターン
            
        Returns:
            Dict[str, Any]: 生成結果
        """
        try:
            start_time = time.time()
            result = script_generator.generate_professional_script(
                articles, target_duration, prompt_pattern=pattern
            )
            generation_time = time.time() - start_time
            
            # 生成時間を追加
            result["generation_time"] = generation_time
            result["pattern_id"] = pattern
            
            return result
            
        except Exception as e:
            self.logger.error(f"パターン {pattern} での生成エラー: {e}")
            return {
                "error": str(e),
                "pattern_id": pattern,
                "generation_time": 0
            }
    
    def _analyze_comparison_results(self, results: Dict[str, Dict]) -> Dict[str, Any]:
        """
        比較結果の分析
        
        Args:
            results: パターン別結果
            
        Returns:
            Dict[str, Any]: 分析結果
        """
        analysis = {
            "total_patterns": len(results),
            "successful_patterns": 0,
            "failed_patterns": 0,
            "pattern_scores": {},
            "metrics_comparison": {},
            "best_pattern": None,
            "recommendations": []
        }
        
        successful_results = {}
        
        # 成功・失敗の分類
        for pattern, result in results.items():
            if "error" in result:
                analysis["failed_patterns"] += 1
            else:
                analysis["successful_patterns"] += 1
                successful_results[pattern] = result
        
        if not successful_results:
            analysis["recommendations"].append("すべてのパターンが失敗しました。システム設定を確認してください。")
            return analysis
        
        # メトリクス比較
        metrics = ["char_count", "quality_score", "generation_time", "estimated_duration"]
        
        for metric in metrics:
            metric_values = {}
            for pattern, result in successful_results.items():
                if metric in result:
                    metric_values[pattern] = result[metric]
            
            if metric_values:
                analysis["metrics_comparison"][metric] = {
                    "values": metric_values,
                    "best": max(metric_values.items(), key=lambda x: x[1] if metric != "generation_time" else -x[1]),
                    "worst": min(metric_values.items(), key=lambda x: x[1] if metric != "generation_time" else -x[1]),
                    "average": sum(metric_values.values()) / len(metric_values)
                }
        
        # 総合スコア計算
        for pattern, result in successful_results.items():
            score = 0.0
            weights = {"quality_score": 0.4, "char_count": 0.2, "generation_time": 0.2, "estimated_duration": 0.2}
            
            # 品質スコア（高いほど良い）
            if "quality_score" in result:
                score += result["quality_score"] * weights["quality_score"]
            
            # 文字数（目標2700に近いほど良い）
            if "char_count" in result:
                char_score = 1.0 - abs(result["char_count"] - 2700) / 2700
                score += max(0, char_score) * weights["char_count"]
            
            # 生成時間（短いほど良い）
            if "generation_time" in result:
                time_score = max(0, 1.0 - result["generation_time"] / 300)  # 5分を最大とする
                score += time_score * weights["generation_time"]
            
            # 推定時間（10分に近いほど良い）
            if "estimated_duration" in result:
                duration_score = 1.0 - abs(result["estimated_duration"] - 10.0) / 10.0
                score += max(0, duration_score) * weights["estimated_duration"]
            
            analysis["pattern_scores"][pattern] = score
        
        # 最優秀パターン決定
        if analysis["pattern_scores"]:
            best_pattern = max(analysis["pattern_scores"].items(), key=lambda x: x[1])
            analysis["best_pattern"] = {
                "pattern": best_pattern[0],
                "score": best_pattern[1],
                "details": successful_results[best_pattern[0]]
            }
        
        # 推奨事項生成
        analysis["recommendations"] = self._generate_recommendations(analysis, successful_results)
        
        return analysis
    
    def _generate_recommendations(self, analysis: Dict, successful_results: Dict) -> List[str]:
        """推奨事項生成"""
        recommendations = []
        
        if analysis["best_pattern"]:
            best = analysis["best_pattern"]
            recommendations.append(
                f"最優秀パターン: {best['pattern']} (スコア: {best['score']:.3f})"
            )
            
            pattern_info = self.prompt_manager.get_pattern_info(best['pattern'])
            if pattern_info:
                recommendations.append(
                    f"推奨設定: {pattern_info['name']} - {pattern_info['description']}"
                )
        
        # 品質に基づく推奨
        quality_scores = {p: r.get("quality_score", 0) for p, r in successful_results.items()}
        if quality_scores:
            highest_quality = max(quality_scores.items(), key=lambda x: x[1])
            if highest_quality[1] > 0.8:
                recommendations.append(f"高品質: {highest_quality[0]} (品質スコア: {highest_quality[1]:.3f})")
        
        # 速度に基づく推奨
        generation_times = {p: r.get("generation_time", float('inf')) for p, r in successful_results.items()}
        if generation_times:
            fastest = min(generation_times.items(), key=lambda x: x[1])
            if fastest[1] < 60:  # 1分以内
                recommendations.append(f"高速生成: {fastest[0]} (生成時間: {fastest[1]:.1f}秒)")
        
        return recommendations
    
    def _save_comparison_results(self, test_id: str, results: Dict[str, Any]) -> None:
        """比較結果保存"""
        try:
            result_file = self.results_dir / f"{test_id}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            
            self.logger.info(f"比較結果保存完了: {result_file}")
            
        except Exception as e:
            self.logger.error(f"比較結果保存エラー: {e}")
    
    def get_test_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """テスト履歴取得"""
        try:
            result_files = sorted(
                self.results_dir.glob("*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            history = []
            for result_file in result_files[:limit]:
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        result = json.load(f)
                        history.append({
                            "test_id": result.get("test_id"),
                            "timestamp": result.get("test_timestamp"),
                            "comparison_mode": result.get("comparison_mode"),
                            "best_pattern": result.get("best_pattern", {}).get("pattern"),
                            "total_patterns": result.get("total_patterns", 0)
                        })
                except Exception as e:
                    self.logger.warning(f"履歴ファイル読み込みエラー: {result_file} - {e}")
            
            return history
            
        except Exception as e:
            self.logger.error(f"テスト履歴取得エラー: {e}")
            return []
    
    def create_comparison_report(self, test_id: str) -> str:
        """比較レポート生成"""
        try:
            result_file = self.results_dir / f"{test_id}.json"
            if not result_file.exists():
                return f"テスト結果が見つかりません: {test_id}"
            
            with open(result_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            report_lines = [
                f"# プロンプトパターン比較レポート",
                f"",
                f"**テストID**: {results['test_id']}",
                f"**実行日時**: {results['test_timestamp']}",
                f"**比較モード**: {results['comparison_mode']}",
                f"**実行時間**: {results['total_execution_time']:.1f}秒",
                f"",
                f"## テスト結果サマリー",
                f"",
            ]
            
            analysis = results.get("comparison_analysis", {})
            
            if analysis.get("best_pattern"):
                best = analysis["best_pattern"]
                report_lines.extend([
                    f"**🏆 最優秀パターン**: {best['pattern']}",
                    f"**総合スコア**: {best['score']:.3f}",
                    f"",
                ])
            
            # パターン別結果
            report_lines.extend([
                f"## パターン別詳細結果",
                f"",
                f"| パターン | 文字数 | 品質スコア | 生成時間 | 推定時間 | 状態 |",
                f"|---------|-------|----------|---------|---------|------|",
            ])
            
            for pattern, result in results.get("pattern_results", {}).items():
                if "error" in result:
                    status = f"❌ エラー: {result['error'][:30]}..."
                    report_lines.append(f"| {pattern} | - | - | - | - | {status} |")
                else:
                    char_count = result.get("char_count", "-")
                    quality_score = f"{result.get('quality_score', 0):.3f}"
                    gen_time = f"{result.get('generation_time', 0):.1f}s"
                    est_duration = f"{result.get('estimated_duration', 0):.1f}min"
                    status = "✅ 成功"
                    report_lines.append(f"| {pattern} | {char_count} | {quality_score} | {gen_time} | {est_duration} | {status} |")
            
            # 推奨事項
            if analysis.get("recommendations"):
                report_lines.extend([
                    f"",
                    f"## 推奨事項",
                    f"",
                ])
                for rec in analysis["recommendations"]:
                    report_lines.append(f"- {rec}")
            
            return "\n".join(report_lines)
            
        except Exception as e:
            self.logger.error(f"比較レポート生成エラー: {e}")
            return f"レポート生成エラー: {e}"