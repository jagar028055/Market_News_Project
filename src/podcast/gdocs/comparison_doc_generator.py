# -*- coding: utf-8 -*-

"""
プロンプトパターン比較レポート用Googleドキュメント生成器
7つのプロンプトパターンの比較結果を構造化されたGoogleドキュメントとして出力
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from gdocs.client import authenticate_google_services, create_daily_summary_doc_with_cleanup_retry


class ComparisonDocGenerator:
    """Googleドキュメント比較レポート生成器"""
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("比較ドキュメント生成器初期化完了")
    
    async def create_comparison_document(
        self, 
        comparison_results: Dict[str, Any], 
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        プロンプトパターン比較結果のGoogleドキュメントを作成
        
        Args:
            comparison_results: 比較結果データ
            title: ドキュメントタイトル（オプション）
            
        Returns:
            Dict[str, Any]: 作成結果（ドキュメントURL含む）
        """
        try:
            self.logger.info("プロンプトパターン比較ドキュメント生成開始")
            
            # タイトル設定
            if not title:
                timestamp = datetime.now().strftime('%Y年%m月%d日 %H:%M')
                title = f"🔍 7プロンプトパターン比較レポート - {timestamp}"
            
            # ドキュメント内容生成
            document_content = self._generate_comparison_content(comparison_results)
            
            # Googleドキュメント作成
            doc_result = await self._create_google_document(title, document_content)
            
            self.logger.info(f"比較ドキュメント生成完了: {doc_result.get('document_url', 'N/A')}")
            return doc_result
            
        except Exception as e:
            self.logger.error(f"比較ドキュメント生成エラー: {e}", exc_info=True)
            return {"error": str(e), "success": False}
    
    def _generate_comparison_content(self, results: Dict[str, Any]) -> str:
        """比較レポートの内容を生成"""
        content_parts = []
        
        # ヘッダー
        content_parts.append(self._generate_header(results))
        
        # 実行サマリー
        content_parts.append(self._generate_execution_summary(results))
        
        # パターン別詳細結果
        content_parts.append(self._generate_pattern_details(results))
        
        # 品質比較表
        content_parts.append(self._generate_quality_comparison_table(results))
        
        # 推奨パターン
        content_parts.append(self._generate_recommendations(results))
        
        # 詳細メトリクス
        content_parts.append(self._generate_detailed_metrics(results))
        
        # フッター
        content_parts.append(self._generate_footer(results))
        
        return "\n\n".join(content_parts)
    
    def _generate_header(self, results: Dict[str, Any]) -> str:
        """ヘッダー生成"""
        comparison_id = results.get("comparison_id", "N/A")
        timestamp = results.get("execution_timestamp", datetime.now().isoformat())
        
        return f"""# 🔍 7プロンプトパターン一括比較レポート

**比較ID**: {comparison_id}
**実行日時**: {timestamp}
**システム**: 市場ニュースポッドキャスト生成システム

---"""
    
    def _generate_execution_summary(self, results: Dict[str, Any]) -> str:
        """実行サマリー生成"""
        execution_time = results.get("total_execution_time_seconds", 0)
        articles_count = results.get("articles_metadata", {}).get("total_articles", 0)
        system_config = results.get("system_config", {})
        
        return f"""## 📊 実行サマリー

- **総実行時間**: {execution_time:.1f}秒
- **対象記事数**: {articles_count}記事
- **目標配信時間**: {system_config.get('target_duration_minutes', 0)}分
- **使用モデル**: {system_config.get('gemini_model', 'Unknown')}
- **音声生成**: {'スキップ' if system_config.get('skip_audio_generation') else '実行'}"""
    
    def _generate_pattern_details(self, results: Dict[str, Any]) -> str:
        """パターン別詳細結果生成"""
        comparison_results = results.get("comparison_results", {})
        pattern_results = comparison_results.get("pattern_results", {})
        
        if not pattern_results:
            return "## 📋 パターン別結果\n\nパターン別結果が見つかりません。"
        
        content = ["## 📋 パターン別詳細結果", ""]
        
        for i, (pattern_id, result) in enumerate(pattern_results.items(), 1):
            content.append(f"### {i}. {pattern_id}")
            
            if "error" in result:
                content.extend([
                    f"**ステータス**: ❌ エラー",
                    f"**エラー内容**: {result['error']}",
                    ""
                ])
            else:
                # 成功結果の詳細表示
                char_count = result.get("char_count", 0)
                quality_score = result.get("quality_score", 0)
                generation_time = result.get("generation_time", 0)
                estimated_duration = result.get("estimated_duration", 0)
                
                content.extend([
                    f"**ステータス**: ✅ 成功",
                    f"**文字数**: {char_count:,}文字",
                    f"**品質スコア**: {quality_score:.3f}/1.000",
                    f"**生成時間**: {generation_time:.1f}秒",
                    f"**推定配信時間**: {estimated_duration:.1f}分",
                    ""
                ])
                
                # 台本の一部を表示（最初の200文字）
                script_content = result.get("script_content", "")
                if script_content:
                    preview = script_content[:200] + "..." if len(script_content) > 200 else script_content
                    content.extend([
                        "**台本プレビュー**:",
                        f"```",
                        preview,
                        f"```",
                        ""
                    ])
        
        return "\n".join(content)
    
    def _generate_quality_comparison_table(self, results: Dict[str, Any]) -> str:
        """品質比較表生成"""
        comparison_results = results.get("comparison_results", {})
        pattern_results = comparison_results.get("pattern_results", {})
        
        if not pattern_results:
            return "## 📈 品質比較表\n\n比較データがありません。"
        
        content = [
            "## 📈 品質比較表",
            "",
            "| プロンプトパターン | 文字数 | 品質スコア | 生成時間 | 推定時間 | ステータス |",
            "|------------------|--------|----------|---------|---------|---------|"
        ]
        
        # 品質スコア順にソート
        sorted_patterns = []
        for pattern_id, result in pattern_results.items():
            if "error" not in result:
                sorted_patterns.append((pattern_id, result))
        
        sorted_patterns.sort(key=lambda x: x[1].get("quality_score", 0), reverse=True)
        
        # 成功したパターンを表示
        for pattern_id, result in sorted_patterns:
            char_count = f"{result.get('char_count', 0):,}"
            quality_score = f"{result.get('quality_score', 0):.3f}"
            gen_time = f"{result.get('generation_time', 0):.1f}s"
            est_duration = f"{result.get('estimated_duration', 0):.1f}min"
            status = "✅ 成功"
            
            content.append(f"| {pattern_id} | {char_count} | {quality_score} | {gen_time} | {est_duration} | {status} |")
        
        # エラーしたパターンを表示
        for pattern_id, result in pattern_results.items():
            if "error" in result:
                error_short = result["error"][:30] + "..." if len(result["error"]) > 30 else result["error"]
                content.append(f"| {pattern_id} | - | - | - | - | ❌ {error_short} |")
        
        return "\n".join(content)
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> str:
        """推奨事項生成"""
        comparison_results = results.get("comparison_results", {})
        analysis = comparison_results.get("comparison_analysis", {})
        best_pattern = analysis.get("best_pattern")
        recommendations = analysis.get("recommendations", [])
        
        content = ["## 🏆 推奨パターンと分析結果", ""]
        
        if best_pattern:
            content.extend([
                f"### 最優秀パターン: {best_pattern['pattern']}",
                f"**総合スコア**: {best_pattern['score']:.3f}/1.000",
                ""
            ])
            
            # 最優秀パターンの詳細
            pattern_details = best_pattern.get("details", {})
            if pattern_details:
                content.extend([
                    "**詳細評価**:",
                    f"- 文字数: {pattern_details.get('char_count', 0):,}文字",
                    f"- 品質スコア: {pattern_details.get('quality_score', 0):.3f}",
                    f"- 生成時間: {pattern_details.get('generation_time', 0):.1f}秒",
                    ""
                ])
        
        if recommendations:
            content.extend([
                "### 📝 推奨事項",
                ""
            ])
            for rec in recommendations:
                content.append(f"- {rec}")
        
        return "\n".join(content)
    
    def _generate_detailed_metrics(self, results: Dict[str, Any]) -> str:
        """詳細メトリクス生成"""
        comparison_results = results.get("comparison_results", {})
        analysis = comparison_results.get("comparison_analysis", {})
        metrics_comparison = analysis.get("metrics_comparison", {})
        
        content = ["## 📊 詳細メトリクス分析", ""]
        
        if not metrics_comparison:
            content.append("メトリクス比較データがありません。")
            return "\n".join(content)
        
        for metric, data in metrics_comparison.items():
            metric_name = {
                "char_count": "文字数",
                "quality_score": "品質スコア", 
                "generation_time": "生成時間",
                "estimated_duration": "推定配信時間"
            }.get(metric, metric)
            
            content.extend([
                f"### {metric_name}",
                ""
            ])
            
            values = data.get("values", {})
            best = data.get("best", ("N/A", 0))
            worst = data.get("worst", ("N/A", 0))
            average = data.get("average", 0)
            
            content.extend([
                f"**最高値**: {best[0]} ({best[1]})",
                f"**最低値**: {worst[0]} ({worst[1]})",
                f"**平均値**: {average:.2f}",
                ""
            ])
            
            # 各パターンの値
            content.append("**パターン別詳細**:")
            for pattern, value in sorted(values.items(), key=lambda x: x[1], reverse=True):
                content.append(f"- {pattern}: {value}")
            content.append("")
        
        return "\n".join(content)
    
    def _generate_footer(self, results: Dict[str, Any]) -> str:
        """フッター生成"""
        return f"""---

## 📝 注意事項

- この比較レポートは自動生成されたものです
- 品質スコアは複数の要因（文字数、構造、可読性等）を総合した指標です
- 推奨パターンは目標設定（{results.get('system_config', {}).get('target_duration_minutes', 10)}分配信）に基づいて算出されています
- 実際の使用時は、コンテンツの性質や目的に応じて適切なパターンを選択してください

**生成システム**: 市場ニュースポッドキャスト自動生成システム
**レポート生成日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}"""
    
    async def _create_google_document(self, title: str, content: str) -> Dict[str, Any]:
        """Googleドキュメントを作成"""
        try:
            # 既存のGoogleドキュメント作成機能を使用
            doc_result = await create_daily_summary_doc_with_cleanup_retry(
                title=title,
                content=content,
                doc_type="comparison_report"
            )
            
            if doc_result.get("success", False):
                return {
                    "success": True,
                    "document_url": doc_result.get("document_url"),
                    "document_id": doc_result.get("document_id"),
                    "title": title
                }
            else:
                return {
                    "success": False,
                    "error": doc_result.get("error", "Unknown error")
                }
                
        except Exception as e:
            self.logger.error(f"Googleドキュメント作成エラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }