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
        比較結果の分析（拡張版）
        
        Args:
            results: パターン別結果
            
        Returns:
            Dict[str, Any]: 詳細分析結果
        """
        analysis = {
            "total_patterns": len(results),
            "successful_patterns": 0,
            "failed_patterns": 0,
            "pattern_scores": {},
            "metrics_comparison": {},
            "quality_analysis": {},
            "performance_analysis": {},
            "cost_analysis": {},
            "best_pattern": None,
            "recommendations": [],
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        successful_results = {}
        failed_patterns = []
        
        # 成功・失敗の分類
        for pattern, result in results.items():
            if "error" in result:
                analysis["failed_patterns"] += 1
                failed_patterns.append({
                    "pattern": pattern,
                    "error": result["error"]
                })
            else:
                analysis["successful_patterns"] += 1
                successful_results[pattern] = result
        
        if not successful_results:
            analysis["recommendations"].append("すべてのパターンが失敗しました。システム設定を確認してください。")
            analysis["failed_pattern_details"] = failed_patterns
            return analysis
        
        # 拡張メトリクス比較
        metrics = ["char_count", "quality_score", "generation_time", "estimated_duration"]
        
        for metric in metrics:
            metric_values = {}
            for pattern, result in successful_results.items():
                if metric in result:
                    metric_values[pattern] = result[metric]
            
            if metric_values:
                values_list = list(metric_values.values())
                analysis["metrics_comparison"][metric] = {
                    "values": metric_values,
                    "best": max(metric_values.items(), key=lambda x: x[1] if metric != "generation_time" else -x[1]),
                    "worst": min(metric_values.items(), key=lambda x: x[1] if metric != "generation_time" else -x[1]),
                    "average": sum(values_list) / len(values_list),
                    "median": sorted(values_list)[len(values_list) // 2],
                    "std_deviation": self._calculate_std_deviation(values_list),
                    "range": max(values_list) - min(values_list)
                }
        
        # 品質分析
        analysis["quality_analysis"] = self._analyze_quality_metrics(successful_results)
        
        # パフォーマンス分析
        analysis["performance_analysis"] = self._analyze_performance_metrics(successful_results)
        
        # コスト分析（推定）
        analysis["cost_analysis"] = self._analyze_cost_metrics(successful_results)
        
        # 総合スコア計算（拡張版）
        analysis["pattern_scores"] = self._calculate_comprehensive_scores(successful_results)
        
        # 最優秀パターン決定
        if analysis["pattern_scores"]:
            best_pattern = max(analysis["pattern_scores"].items(), key=lambda x: x[1])
            analysis["best_pattern"] = {
                "pattern": best_pattern[0],
                "score": best_pattern[1],
                "details": successful_results[best_pattern[0]],
                "reasons": self._get_best_pattern_reasons(best_pattern[0], successful_results, analysis)
            }
        
        # 推奨事項生成（拡張版）
        analysis["recommendations"] = self._generate_enhanced_recommendations(analysis, successful_results, failed_patterns)
        
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
    
    async def create_google_document_report(
        self, 
        comparison_results: Dict[str, Any], 
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        比較結果をGoogleドキュメントで出力
        
        Args:
            comparison_results: 比較結果データ
            title: ドキュメントタイトル（オプション）
            
        Returns:
            Dict[str, Any]: Googleドキュメント作成結果
        """
        try:
            # Googleドキュメント比較生成器をインポート
            from ..gdocs.comparison_doc_generator import ComparisonDocGenerator
            
            doc_generator = ComparisonDocGenerator()
            
            # Googleドキュメント生成
            doc_result = await doc_generator.create_comparison_document(
                comparison_results=comparison_results,
                title=title
            )
            
            self.logger.info(f"Googleドキュメントレポート生成: {doc_result.get('success', False)}")
            return doc_result
            
        except ImportError as e:
            self.logger.warning(f"Googleドキュメント生成器インポートエラー: {e}")
            return {"error": "ComparisonDocGenerator not available", "success": False}
        except Exception as e:
            self.logger.error(f"Googleドキュメントレポート生成エラー: {e}")
            return {"error": str(e), "success": False}
    
    def _calculate_std_deviation(self, values: List[float]) -> float:
        """標準偏差計算"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def _analyze_quality_metrics(self, results: Dict[str, Dict]) -> Dict[str, Any]:
        """品質メトリクスの詳細分析"""
        quality_analysis = {
            "high_quality_patterns": [],
            "medium_quality_patterns": [],
            "low_quality_patterns": [],
            "quality_distribution": {},
            "consistency_analysis": {}
        }
        
        # 品質スコア別分類
        for pattern, result in results.items():
            quality_score = result.get("quality_score", 0)
            char_count = result.get("char_count", 0)
            
            if quality_score >= 0.8:
                quality_analysis["high_quality_patterns"].append({
                    "pattern": pattern,
                    "quality_score": quality_score,
                    "char_count": char_count
                })
            elif quality_score >= 0.6:
                quality_analysis["medium_quality_patterns"].append({
                    "pattern": pattern, 
                    "quality_score": quality_score,
                    "char_count": char_count
                })
            else:
                quality_analysis["low_quality_patterns"].append({
                    "pattern": pattern,
                    "quality_score": quality_score, 
                    "char_count": char_count
                })
        
        # 品質分布
        quality_scores = [r.get("quality_score", 0) for r in results.values()]
        if quality_scores:
            quality_analysis["quality_distribution"] = {
                "average": sum(quality_scores) / len(quality_scores),
                "median": sorted(quality_scores)[len(quality_scores) // 2],
                "min": min(quality_scores),
                "max": max(quality_scores),
                "std_dev": self._calculate_std_deviation(quality_scores)
            }
        
        return quality_analysis
    
    def _analyze_performance_metrics(self, results: Dict[str, Dict]) -> Dict[str, Any]:
        """パフォーマンスメトリクスの詳細分析"""
        performance_analysis = {
            "fast_patterns": [],
            "medium_speed_patterns": [],
            "slow_patterns": [],
            "generation_time_analysis": {},
            "efficiency_ranking": []
        }
        
        # 生成時間別分類
        for pattern, result in results.items():
            gen_time = result.get("generation_time", 0)
            quality_score = result.get("quality_score", 0)
            
            efficiency = quality_score / max(gen_time, 1)  # 品質/時間の効率性
            
            if gen_time <= 60:  # 1分以内
                performance_analysis["fast_patterns"].append({
                    "pattern": pattern,
                    "generation_time": gen_time,
                    "efficiency": efficiency
                })
            elif gen_time <= 120:  # 2分以内
                performance_analysis["medium_speed_patterns"].append({
                    "pattern": pattern,
                    "generation_time": gen_time,
                    "efficiency": efficiency
                })
            else:  # 2分以上
                performance_analysis["slow_patterns"].append({
                    "pattern": pattern,
                    "generation_time": gen_time,
                    "efficiency": efficiency
                })
            
            performance_analysis["efficiency_ranking"].append({
                "pattern": pattern,
                "efficiency": efficiency,
                "generation_time": gen_time,
                "quality_score": quality_score
            })
        
        # 効率性でソート
        performance_analysis["efficiency_ranking"].sort(key=lambda x: x["efficiency"], reverse=True)
        
        # 生成時間分析
        generation_times = [r.get("generation_time", 0) for r in results.values()]
        if generation_times:
            performance_analysis["generation_time_analysis"] = {
                "average": sum(generation_times) / len(generation_times),
                "median": sorted(generation_times)[len(generation_times) // 2],
                "min": min(generation_times),
                "max": max(generation_times),
                "total": sum(generation_times),
                "std_dev": self._calculate_std_deviation(generation_times)
            }
        
        return performance_analysis
    
    def _analyze_cost_metrics(self, results: Dict[str, Dict]) -> Dict[str, Any]:
        """コストメトリクスの分析（推定）"""
        cost_analysis = {
            "estimated_api_costs": {},
            "cost_efficiency": {},
            "total_estimated_cost": 0.0,
            "cost_per_quality_point": {}
        }
        
        # Gemini API推定コスト計算（概算）
        # 入力トークン単価: $0.000125/1K tokens
        # 出力トークン単価: $0.000375/1K tokens
        input_cost_per_1k = 0.000125
        output_cost_per_1k = 0.000375
        
        for pattern, result in results.items():
            char_count = result.get("char_count", 0)
            generation_time = result.get("generation_time", 0)
            quality_score = result.get("quality_score", 0)
            
            # 推定トークン数（日本語文字数の約1.5倍）
            estimated_output_tokens = char_count * 1.5
            estimated_input_tokens = 2000  # 記事+プロンプトの推定トークン数
            
            # 推定コスト
            estimated_cost = (
                (estimated_input_tokens / 1000) * input_cost_per_1k + 
                (estimated_output_tokens / 1000) * output_cost_per_1k
            )
            
            cost_analysis["estimated_api_costs"][pattern] = estimated_cost
            cost_analysis["total_estimated_cost"] += estimated_cost
            
            # コスト効率性（品質/コスト）
            if estimated_cost > 0:
                cost_efficiency = quality_score / estimated_cost
                cost_analysis["cost_efficiency"][pattern] = cost_efficiency
                cost_analysis["cost_per_quality_point"][pattern] = estimated_cost / max(quality_score, 0.1)
        
        return cost_analysis
    
    def _calculate_comprehensive_scores(self, results: Dict[str, Dict]) -> Dict[str, float]:
        """包括的スコア計算（拡張版）"""
        pattern_scores = {}
        
        # 重み設定（合計1.0）
        weights = {
            "quality_score": 0.35,      # 品質を重視
            "char_count": 0.15,         # 文字数適合性
            "generation_time": 0.25,    # 生成効率
            "estimated_duration": 0.15, # 配信時間適合性
            "consistency": 0.10         # 一貫性ボーナス
        }
        
        target_chars = int(os.getenv('PODCAST_TARGET_SCRIPT_CHARS', '2700'))
        target_duration = float(os.getenv('PODCAST_TARGET_DURATION_MINUTES', '10.0'))
        
        for pattern, result in results.items():
            score = 0.0
            
            # 品質スコア（高いほど良い）
            if "quality_score" in result:
                quality = result["quality_score"]
                score += quality * weights["quality_score"]
            
            # 文字数適合性（目標に近いほど良い）
            if "char_count" in result:
                char_count = result["char_count"]
                char_deviation = abs(char_count - target_chars) / target_chars
                char_score = max(0, 1.0 - char_deviation)
                score += char_score * weights["char_count"]
            
            # 生成効率（短いほど良い、ただし極端に短い場合は減点）
            if "generation_time" in result:
                gen_time = result["generation_time"]
                if gen_time < 10:  # 10秒未満は不自然
                    time_score = 0.5
                elif gen_time > 300:  # 5分以上は遅すぎる
                    time_score = 0.0
                else:
                    time_score = max(0, 1.0 - (gen_time - 10) / 290)
                score += time_score * weights["generation_time"]
            
            # 配信時間適合性（目標に近いほど良い）
            if "estimated_duration" in result:
                duration = result["estimated_duration"]
                duration_deviation = abs(duration - target_duration) / target_duration
                duration_score = max(0, 1.0 - duration_deviation)
                score += duration_score * weights["estimated_duration"]
            
            # 一貫性ボーナス（エラーなしで完了した場合）
            consistency_bonus = 1.0 if "error" not in result else 0.0
            score += consistency_bonus * weights["consistency"]
            
            pattern_scores[pattern] = score
        
        return pattern_scores
    
    def _get_best_pattern_reasons(self, best_pattern: str, results: Dict, analysis: Dict) -> List[str]:
        """最優秀パターンの選定理由"""
        reasons = []
        result = results[best_pattern]
        
        # 品質面での優位性
        quality_score = result.get("quality_score", 0)
        if quality_score >= 0.8:
            reasons.append(f"高い品質スコア: {quality_score:.3f}/1.000")
        
        # 効率性での優位性
        gen_time = result.get("generation_time", 0)
        if gen_time <= 60:
            reasons.append(f"高速な生成時間: {gen_time:.1f}秒")
        
        # 文字数適合性
        char_count = result.get("char_count", 0)
        target_chars = int(os.getenv('PODCAST_TARGET_SCRIPT_CHARS', '2700'))
        char_deviation = abs(char_count - target_chars) / target_chars
        if char_deviation < 0.1:
            reasons.append(f"適切な文字数: {char_count:,}文字（目標: {target_chars:,}文字）")
        
        # 配信時間適合性
        est_duration = result.get("estimated_duration", 0)
        target_duration = float(os.getenv('PODCAST_TARGET_DURATION_MINUTES', '10.0'))
        duration_deviation = abs(est_duration - target_duration) / target_duration
        if duration_deviation < 0.1:
            reasons.append(f"適切な配信時間: {est_duration:.1f}分（目標: {target_duration}分）")
        
        return reasons
    
    def _generate_enhanced_recommendations(
        self, 
        analysis: Dict, 
        successful_results: Dict, 
        failed_patterns: List[Dict]
    ) -> List[str]:
        """拡張版推奨事項生成"""
        recommendations = []
        
        # 最優秀パターンの推奨
        if analysis.get("best_pattern"):
            best = analysis["best_pattern"]
            recommendations.append(
                f"🏆 最優秀パターン: {best['pattern']} (スコア: {best['score']:.3f})"
            )
            
            # 選定理由を追加
            for reason in best.get("reasons", []):
                recommendations.append(f"  → {reason}")
        
        # 品質分析に基づく推奨
        quality_analysis = analysis.get("quality_analysis", {})
        high_quality = quality_analysis.get("high_quality_patterns", [])
        if len(high_quality) > 1:
            recommendations.append(f"高品質パターン: {len(high_quality)}個のパターンが0.8以上の品質スコア")
        
        # パフォーマンス分析に基づく推奨
        performance_analysis = analysis.get("performance_analysis", {})
        fast_patterns = performance_analysis.get("fast_patterns", [])
        if fast_patterns:
            fastest = min(fast_patterns, key=lambda x: x["generation_time"])
            recommendations.append(f"⚡ 最高速パターン: {fastest['pattern']} ({fastest['generation_time']:.1f}秒)")
        
        # 効率性に基づく推奨
        efficiency_ranking = performance_analysis.get("efficiency_ranking", [])
        if efficiency_ranking:
            most_efficient = efficiency_ranking[0]
            recommendations.append(
                f"🎯 最高効率パターン: {most_efficient['pattern']} "
                f"(効率値: {most_efficient['efficiency']:.3f})"
            )
        
        # コスト分析に基づく推奨
        cost_analysis = analysis.get("cost_analysis", {})
        cost_efficiency = cost_analysis.get("cost_efficiency", {})
        if cost_efficiency:
            most_cost_efficient = max(cost_efficiency.items(), key=lambda x: x[1])
            recommendations.append(
                f"💰 最高コスト効率パターン: {most_cost_efficient[0]} "
                f"(効率値: {most_cost_efficient[1]:.3f})"
            )
        
        # 失敗パターンに対する対策
        if failed_patterns:
            recommendations.append(f"⚠️ 失敗パターン数: {len(failed_patterns)}個")
            for failed in failed_patterns:
                recommendations.append(f"  → {failed['pattern']}: {failed['error'][:50]}...")
        
        # 総合的な推奨事項
        successful_count = len(successful_results)
        total_count = analysis["total_patterns"]
        success_rate = (successful_count / total_count) * 100 if total_count > 0 else 0
        
        if success_rate >= 80:
            recommendations.append(f"✅ システム安定性良好 (成功率: {success_rate:.1f}%)")
        elif success_rate >= 60:
            recommendations.append(f"⚠️ システム安定性要注意 (成功率: {success_rate:.1f}%)")
        else:
            recommendations.append(f"🔧 システム改善が必要 (成功率: {success_rate:.1f}%)")
        
        return recommendations