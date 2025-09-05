# -*- coding: utf-8 -*-

"""
コンテンツ品質バリデーター
記事の品質をチェックし、スコアリングする
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import re
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """バリデーション結果"""

    score: float  # 0-100のスコア
    passed: bool  # 最低品質基準をクリアしているか
    issues: List[str]  # 発見された問題点
    recommendations: List[str]  # 改善推奨事項
    details: Dict[str, Any]  # 詳細情報


class ContentValidator:
    """コンテンツ品質バリデーター"""

    def __init__(
        self,
        min_summary_length: int = 150,
        max_summary_length: int = 280,
        min_quality_score: float = 60.0,
        logger: Optional[logging.Logger] = None,
    ):
        """
        初期化

        Args:
            min_summary_length: 要約最小文字数
            max_summary_length: 要約最大文字数
            min_quality_score: 最低品質スコア
            logger: ロガー
        """
        self.min_summary_length = min_summary_length
        self.max_summary_length = max_summary_length
        self.min_quality_score = min_quality_score
        self.logger = logger or logging.getLogger(__name__)

        # 品質チェック項目の重み
        self.quality_weights = {
            "summary_length": 0.15,
            "summary_quality": 0.25,
            "information_completeness": 0.20,
            "language_quality": 0.15,
            "consistency": 0.10,
            "relevance": 0.15,
        }

        # 不適切なパターン
        self.inappropriate_patterns = [
            r"エラー",
            r"失敗",
            r"取得できません",
            r"不明",
            r"[？\?]{2,}",  # 連続する疑問符
            r"\.{3,}",  # 連続するピリオド
        ]

        # 高品質指標パターン
        self.quality_patterns = [
            r"\d+[%％]",  # パーセンテージ
            r"\d+[億万千百十]",  # 数値
            r"[0-9,]+円",  # 金額
            r"\d+年\d+月",  # 日付
            r"(上昇|下落|増加|減少)",  # 変化を表す語
        ]

    def validate_article(self, article: Dict[str, Any]) -> ValidationResult:
        """
        記事の品質をバリデーション

        Args:
            article: 記事データ

        Returns:
            ValidationResult: バリデーション結果
        """
        self.logger.debug(f"記事バリデーション開始: {article.get('title', 'No Title')[:50]}")

        issues = []
        recommendations = []
        scores = {}
        details = {}

        # 各項目をチェック
        scores["summary_length"] = self._check_summary_length(article, issues, recommendations)
        scores["summary_quality"] = self._check_summary_quality(article, issues, recommendations)
        scores["information_completeness"] = self._check_information_completeness(
            article, issues, recommendations
        )
        scores["language_quality"] = self._check_language_quality(article, issues, recommendations)
        scores["consistency"] = self._check_consistency(article, issues, recommendations)
        scores["relevance"] = self._check_relevance(article, issues, recommendations)

        # 詳細情報を収集
        details = self._collect_details(article)

        # 総合スコア計算
        total_score = sum(scores[item] * weight for item, weight in self.quality_weights.items())

        # 合格判定（スコアベース、軽微なissuesは許容）
        critical_issues = [
            issue
            for issue in issues
            if any(
                critical in issue for critical in ["重大な", "致命的", "不適切", "不正", "著作権"]
            )
        ]
        passed = total_score >= self.min_quality_score and len(critical_issues) == 0

        result = ValidationResult(
            score=round(total_score, 1),
            passed=passed,
            issues=issues,
            recommendations=recommendations,
            details={**details, "individual_scores": scores},
        )

        self.logger.info(f"バリデーション完了: スコア={result.score}, 合格={result.passed}")
        return result

    def validate_article_batch(self, articles: List[Dict[str, Any]]) -> List[ValidationResult]:
        """記事バッチの品質バリデーション"""
        self.logger.info(f"バッチバリデーション開始: {len(articles)}件")

        results = []
        for i, article in enumerate(articles):
            try:
                result = self.validate_article(article)
                results.append(result)
            except Exception as e:
                self.logger.error(f"記事{i}のバリデーションでエラー: {e}")
                # エラー時のデフォルト結果
                results.append(
                    ValidationResult(
                        score=0.0,
                        passed=False,
                        issues=[f"バリデーション処理エラー: {str(e)[:100]}"],
                        recommendations=["記事データの確認が必要"],
                        details={"error": str(e)},
                    )
                )

        # バッチ統計を計算
        passed_count = sum(1 for r in results if r.passed)
        avg_score = sum(r.score for r in results) / len(results) if results else 0

        self.logger.info(
            f"バッチバリデーション完了: 合格={passed_count}/{len(articles)}, 平均スコア={avg_score:.1f}"
        )
        return results

    def _check_summary_length(
        self, article: Dict[str, Any], issues: List[str], recommendations: List[str]
    ) -> float:
        """要約文字数チェック"""
        summary = article.get("summary", "")
        if not summary or summary == "要約はありません。":
            issues.append("要約が存在しません")
            recommendations.append("AI要約の生成を確認してください")
            return 0.0

        length = len(summary)

        if length < self.min_summary_length:
            issues.append(f"要約が短すぎます({length}字)")
            recommendations.append(f"要約を{self.min_summary_length}字以上にしてください")
            return max(0, 50 * (length / self.min_summary_length))
        elif length > self.max_summary_length:
            issues.append(f"要約が長すぎます({length}字)")
            recommendations.append(f"要約を{self.max_summary_length}字以下にしてください")
            return max(0, 100 - (length - self.max_summary_length) * 2)
        else:
            return 100.0

    def _check_summary_quality(
        self, article: Dict[str, Any], issues: List[str], recommendations: List[str]
    ) -> float:
        """要約品質チェック"""
        summary = article.get("summary", "")
        if not summary:
            return 0.0

        score = 0.0

        # 不適切なパターンをチェック
        inappropriate_count = 0
        for pattern in self.inappropriate_patterns:
            if re.search(pattern, summary, re.IGNORECASE):
                inappropriate_count += 1

        if inappropriate_count > 0:
            issues.append(f"要約に不適切な表現が含まれています({inappropriate_count}箇所)")
            recommendations.append("要約の表現を見直してください")
            score -= inappropriate_count * 20

        # 高品質指標をチェック
        quality_indicators = 0
        for pattern in self.quality_patterns:
            if re.search(pattern, summary):
                quality_indicators += 1

        score += min(quality_indicators * 20, 60)  # 最大60点

        # 文構造の確認
        sentences = [s.strip() for s in re.split(r"[。．]", summary) if s.strip()]
        if len(sentences) >= 2:
            score += 20  # 複数文で構成されている

        # 文字種の多様性（ひらがな、カタカナ、漢字、数字）
        has_hiragana = bool(re.search(r"[あ-ひ]", summary))
        has_katakana = bool(re.search(r"[ア-ン]", summary))
        has_kanji = bool(re.search(r"[一-龯]", summary))
        has_numbers = bool(re.search(r"[0-9]", summary))

        diversity_score = sum([has_hiragana, has_katakana, has_kanji, has_numbers]) * 5
        score += diversity_score

        return max(0, min(score, 100))

    def _check_information_completeness(
        self, article: Dict[str, Any], issues: List[str], recommendations: List[str]
    ) -> float:
        """情報完全性チェック"""
        score = 100.0

        # 必須フィールドの確認
        required_fields = {
            "title": "記事タイトル",
            "url": "記事URL",
            "source": "情報源",
            "published_jst": "公開日時",
        }

        for field, name in required_fields.items():
            if not article.get(field):
                issues.append(f"{name}が不足しています")
                recommendations.append(f"{name}の取得を確認してください")
                score -= 20

        # カテゴリ・地域分類の確認
        category = article.get("category")
        region = article.get("region")

        if not category or category == "その他":
            issues.append("記事カテゴリが適切に分類されていません")
            recommendations.append("AI分類の精度向上を検討してください")
            score -= 15

        if not region or region == "その他":
            recommendations.append("地域分類の精度向上を検討してください")
            score -= 10

        return max(0, score)

    def _check_language_quality(
        self, article: Dict[str, Any], issues: List[str], recommendations: List[str]
    ) -> float:
        """言語品質チェック"""
        text_to_check = f"{article.get('title', '')} {article.get('summary', '')}"
        if not text_to_check.strip():
            return 0.0

        score = 100.0

        # 文字化けチェック
        if re.search(r"[□◆●▲■]", text_to_check):
            issues.append("文字化けの可能性があります")
            recommendations.append("テキストエンコーディングを確認してください")
            score -= 30

        # 異常な文字の連続
        if re.search(r"(.)\1{4,}", text_to_check):  # 同じ文字が5回以上連続
            issues.append("異常な文字の連続があります")
            recommendations.append("テキスト処理の確認が必要です")
            score -= 20

        # HTMLタグの残存
        if re.search(r"<[^>]+>", text_to_check):
            issues.append("HTMLタグが残存しています")
            recommendations.append("テキストクリーニング処理を確認してください")
            score -= 25

        # 改行の確認（過度な改行）
        if text_to_check.count("\n") > len(text_to_check) * 0.1:
            recommendations.append("改行の処理を見直してください")
            score -= 10

        return max(0, score)

    def _check_consistency(
        self, article: Dict[str, Any], issues: List[str], recommendations: List[str]
    ) -> float:
        """一貫性チェック"""
        score = 100.0

        # タイトルと要約の関連性
        title = article.get("title", "").lower()
        summary = article.get("summary", "").lower()

        if title and summary:
            # タイトルの主要単語が要約に含まれているかチェック
            title_words = set(re.findall(r"[一-龯ア-ンあ-ん]+", title))  # 日本語単語を抽出
            title_words = {word for word in title_words if len(word) >= 2}  # 2文字以上

            if title_words:
                overlap = sum(1 for word in title_words if word in summary)
                overlap_ratio = overlap / len(title_words)

                if overlap_ratio < 0.3:
                    issues.append("タイトルと要約の関連性が低いです")
                    recommendations.append("要約内容の見直しが必要です")
                    score -= 40
                elif overlap_ratio < 0.5:
                    recommendations.append("タイトルと要約の関連性向上を検討してください")
                    score -= 20

        # センチメント分析との整合性
        sentiment_label = article.get("sentiment_label", "")
        if sentiment_label and summary:
            positive_words = ["上昇", "増加", "好調", "改善", "成長"]
            negative_words = ["下落", "減少", "悪化", "低下", "懸念"]

            positive_count = sum(1 for word in positive_words if word in summary)
            negative_count = sum(1 for word in negative_words if word in summary)

            if sentiment_label == "positive" and positive_count < negative_count:
                recommendations.append("センチメント分析の精度確認を推奨します")
                score -= 15
            elif sentiment_label == "negative" and negative_count < positive_count:
                recommendations.append("センチメント分析の精度確認を推奨します")
                score -= 15

        return max(0, score)

    def _check_relevance(
        self, article: Dict[str, Any], issues: List[str], recommendations: List[str]
    ) -> float:
        """関連性チェック"""
        score = 100.0

        # 市場関連キーワードの存在チェック
        market_keywords = [
            "株価",
            "市場",
            "投資",
            "経済",
            "金融",
            "企業",
            "業績",
            "売上",
            "利益",
            "金利",
            "GDP",
            "インフレ",
            "為替",
            "通貨",
            "政策",
            "銀行",
            "証券",
        ]

        text = f"{article.get('title', '')} {article.get('summary', '')}"
        relevant_keywords = sum(1 for keyword in market_keywords if keyword in text)

        if relevant_keywords == 0:
            issues.append("市場関連性が低い記事です")
            recommendations.append("市場ニュースに特化したフィルタリングを強化してください")
            score -= 50
        elif relevant_keywords < 2:
            recommendations.append("市場関連キーワードを増やすことを検討してください")
            score -= 20

        # 日付の新しさチェック
        published_jst = article.get("published_jst")
        if published_jst:
            try:
                if hasattr(published_jst, "date"):
                    pub_date = published_jst
                else:
                    pub_date = datetime.fromisoformat(str(published_jst))

                days_old = (datetime.now() - pub_date).days
                if days_old > 7:
                    recommendations.append("記事が古い可能性があります")
                    score -= min(days_old * 2, 30)  # 最大30点減点
            except Exception as e:
                self.logger.warning(f"日付解析エラー: {e}")

        return max(0, score)

    def _collect_details(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """詳細情報収集"""
        summary = article.get("summary", "")

        return {
            "summary_length": len(summary),
            "title_length": len(article.get("title", "")),
            "has_sentiment": bool(article.get("sentiment_label")),
            "has_category": bool(article.get("category")),
            "has_region": bool(article.get("region")),
            "word_count": len(summary.split()) if summary else 0,
            "sentence_count": (
                len([s for s in re.split(r"[。．]", summary) if s.strip()]) if summary else 0
            ),
            "validation_timestamp": datetime.now().isoformat(),
        }

    def get_quality_report(self, validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """品質レポート生成"""
        if not validation_results:
            return {"error": "バリデーション結果がありません"}

        total_articles = len(validation_results)
        passed_articles = sum(1 for r in validation_results if r.passed)
        failed_articles = total_articles - passed_articles

        average_score = sum(r.score for r in validation_results) / total_articles
        min_score = min(r.score for r in validation_results)
        max_score = max(r.score for r in validation_results)

        # 最も多い問題点を特定
        all_issues = [issue for r in validation_results for issue in r.issues]
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        top_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # 品質分布
        score_ranges = {
            "excellent": sum(1 for r in validation_results if r.score >= 90),
            "good": sum(1 for r in validation_results if 70 <= r.score < 90),
            "average": sum(1 for r in validation_results if 50 <= r.score < 70),
            "poor": sum(1 for r in validation_results if r.score < 50),
        }

        return {
            "summary": {
                "total_articles": total_articles,
                "passed_articles": passed_articles,
                "failed_articles": failed_articles,
                "pass_rate": (
                    round(passed_articles / total_articles * 100, 1) if total_articles > 0 else 0
                ),
            },
            "score_statistics": {
                "average": round(average_score, 1),
                "min": round(min_score, 1),
                "max": round(max_score, 1),
            },
            "quality_distribution": score_ranges,
            "top_issues": top_issues,
            "generated_at": datetime.now().isoformat(),
        }
