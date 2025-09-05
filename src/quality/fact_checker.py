# -*- coding: utf-8 -*-

"""
ファクトチェッカー
記事内容とマーケットデータの整合性をチェック
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import re
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..market_data.fetcher import MarketDataFetcher
from ..market_data.models import MarketSnapshot


@dataclass
class FactCheckResult:
    """ファクトチェック結果"""

    accuracy_score: float  # 0-100の精度スコア
    verified_facts: List[str]  # 検証された事実
    inconsistencies: List[str]  # 発見された不整合
    warnings: List[str]  # 警告事項
    confidence_level: str  # 信頼度レベル


class FactChecker:
    """ファクトチェッカー"""

    def __init__(
        self,
        market_fetcher: Optional[MarketDataFetcher] = None,
        tolerance_percentage: float = 2.0,
        logger: Optional[logging.Logger] = None,
    ):
        """
        初期化

        Args:
            market_fetcher: マーケットデータ取得インスタンス
            tolerance_percentage: 許容誤差（パーセント）
            logger: ロガー
        """
        self.market_fetcher = market_fetcher or MarketDataFetcher()
        self.tolerance = tolerance_percentage
        self.logger = logger or logging.getLogger(__name__)

        # 数値抽出パターン
        self.number_patterns = {
            "percentage": r"([-+]?\d+\.?\d*)[%％]",
            "price": r"(\d+(?:,\d{3})*(?:\.\d+)?)円",
            "points": r"([-+]?\d+(?:,\d{3})*(?:\.\d+)?)ポイント",
            "yen_rate": r"1ドル[=＝](\d+(?:\.\d+)?)円",
            "index_value": r"(\d+(?:,\d{3})*(?:\.\d+)?)で",
        }

        # 市場指標マッピング
        self.market_indicators = {
            "日経平均": "^N225",
            "ダウ": "^DJI",
            "ナスダック": "^IXIC",
            "S&P500": "^GSPC",
            "ドル円": "USDJPY",
            "ユーロドル": "EURUSD",
        }

    def check_article_facts(self, article: Dict[str, Any]) -> FactCheckResult:
        """
        記事のファクトチェックを実行

        Args:
            article: チェック対象の記事

        Returns:
            FactCheckResult: ファクトチェック結果
        """
        self.logger.info(f"ファクトチェック開始: {article.get('title', 'No Title')[:50]}")

        verified_facts = []
        inconsistencies = []
        warnings = []
        accuracy_score = 100.0

        try:
            # 現在の市場データを取得
            market_snapshot = self.market_fetcher.get_current_market_snapshot()

            # 記事から数値情報を抽出
            extracted_numbers = self._extract_numerical_claims(article)

            # 各数値情報を検証
            for claim in extracted_numbers:
                result = self._verify_numerical_claim(claim, market_snapshot, article)

                if result["verified"]:
                    verified_facts.append(result["description"])
                elif result["inconsistent"]:
                    inconsistencies.append(result["description"])
                    accuracy_score -= result["penalty"]
                else:
                    warnings.append(result["description"])
                    accuracy_score -= result["penalty"] * 0.5

            # 日付整合性チェック
            date_check = self._check_date_consistency(article, market_snapshot)
            if date_check["issues"]:
                warnings.extend(date_check["issues"])
                accuracy_score -= 5

            # 市場トレンド整合性チェック
            trend_check = self._check_trend_consistency(article, market_snapshot)
            if not trend_check["consistent"]:
                inconsistencies.append(trend_check["description"])
                accuracy_score -= 15

        except Exception as e:
            self.logger.error(f"ファクトチェック処理でエラー: {e}")
            warnings.append(f"ファクトチェック処理でエラーが発生: {str(e)[:100]}")
            accuracy_score -= 20

        # 信頼度レベル決定
        confidence_level = self._determine_confidence_level(accuracy_score, len(inconsistencies))

        result = FactCheckResult(
            accuracy_score=max(0, min(100, accuracy_score)),
            verified_facts=verified_facts,
            inconsistencies=inconsistencies,
            warnings=warnings,
            confidence_level=confidence_level,
        )

        self.logger.info(
            f"ファクトチェック完了: スコア={result.accuracy_score:.1f}, 信頼度={confidence_level}"
        )
        return result

    def _extract_numerical_claims(self, article: Dict[str, Any]) -> List[Dict[str, Any]]:
        """記事から数値的な主張を抽出"""
        claims = []
        text = f"{article.get('title', '')} {article.get('summary', '')}"

        # パーセンテージの抽出
        percentage_matches = re.finditer(self.number_patterns["percentage"], text)
        for match in percentage_matches:
            context_start = max(0, match.start() - 20)
            context_end = min(len(text), match.end() + 20)
            context = text[context_start:context_end]

            claims.append(
                {
                    "type": "percentage",
                    "value": float(match.group(1)),
                    "context": context.strip(),
                    "position": match.span(),
                }
            )

        # 価格の抽出
        price_matches = re.finditer(self.number_patterns["price"], text)
        for match in price_matches:
            context_start = max(0, match.start() - 30)
            context_end = min(len(text), match.end() + 30)
            context = text[context_start:context_end]

            # カンマを除去して数値に変換
            value = float(match.group(1).replace(",", ""))

            claims.append(
                {
                    "type": "price",
                    "value": value,
                    "context": context.strip(),
                    "position": match.span(),
                }
            )

        # 為替レートの抽出
        yen_rate_matches = re.finditer(self.number_patterns["yen_rate"], text)
        for match in yen_rate_matches:
            context_start = max(0, match.start() - 20)
            context_end = min(len(text), match.end() + 20)
            context = text[context_start:context_end]

            claims.append(
                {
                    "type": "usdjpy_rate",
                    "value": float(match.group(1)),
                    "context": context.strip(),
                    "position": match.span(),
                }
            )

        return claims

    def _verify_numerical_claim(
        self, claim: Dict[str, Any], market_snapshot: MarketSnapshot, article: Dict[str, Any]
    ) -> Dict[str, Any]:
        """数値的主張を検証"""

        claim_type = claim["type"]
        claim_value = claim["value"]
        context = claim["context"].lower()

        if claim_type == "percentage":
            return self._verify_percentage_claim(claim_value, context, market_snapshot)
        elif claim_type == "usdjpy_rate":
            return self._verify_usdjpy_rate(claim_value, market_snapshot)
        elif claim_type == "price":
            return self._verify_price_claim(claim_value, context, market_snapshot)
        else:
            return {
                "verified": False,
                "inconsistent": False,
                "description": f"未対応の主張タイプ: {claim_type}",
                "penalty": 0,
            }

    def _verify_percentage_claim(
        self, percentage: float, context: str, market_snapshot: MarketSnapshot
    ) -> Dict[str, Any]:
        """パーセンテージ主張を検証"""

        # コンテキストから対象指標を特定
        target_instrument = None
        actual_change = None

        for indicator_name, symbol in self.market_indicators.items():
            if indicator_name.lower() in context:
                # 対応するマーケットデータを検索
                for idx in market_snapshot.stock_indices:
                    if symbol in [idx.symbol, "^" + idx.symbol.replace("^", "")]:
                        target_instrument = indicator_name
                        actual_change = idx.change_percent
                        break

                # 通貨ペアもチェック
                if not target_instrument:
                    for pair in market_snapshot.currency_pairs:
                        if symbol in pair.symbol:
                            target_instrument = indicator_name
                            actual_change = pair.change_percent
                            break

                break

        if target_instrument and actual_change is not None:
            difference = abs(percentage - actual_change)

            if difference <= self.tolerance:
                return {
                    "verified": True,
                    "inconsistent": False,
                    "description": f"{target_instrument}の変化率{percentage}%は市場データ({actual_change:.2f}%)と整合",
                    "penalty": 0,
                }
            else:
                return {
                    "verified": False,
                    "inconsistent": True,
                    "description": f"{target_instrument}の変化率{percentage}%が市場データ({actual_change:.2f}%)と不整合（差: {difference:.2f}%）",
                    "penalty": min(difference * 2, 20),  # 最大20点減点
                }
        else:
            return {
                "verified": False,
                "inconsistent": False,
                "description": f"パーセンテージ{percentage}%の対象指標を特定できず",
                "penalty": 2,
            }

    def _verify_usdjpy_rate(
        self, claimed_rate: float, market_snapshot: MarketSnapshot
    ) -> Dict[str, Any]:
        """USD/JPY為替レートを検証"""

        # USD/JPY レートを検索
        usdjpy_data = None
        for pair in market_snapshot.currency_pairs:
            if "USD" in pair.symbol and "JPY" in pair.symbol:
                usdjpy_data = pair
                break

        if usdjpy_data:
            actual_rate = usdjpy_data.current_price
            difference = abs(claimed_rate - actual_rate)
            tolerance_yen = actual_rate * (self.tolerance / 100)  # 相対的な許容誤差

            if difference <= tolerance_yen:
                return {
                    "verified": True,
                    "inconsistent": False,
                    "description": f"USD/JPYレート{claimed_rate}円は市場データ({actual_rate:.2f}円)と整合",
                    "penalty": 0,
                }
            else:
                return {
                    "verified": False,
                    "inconsistent": True,
                    "description": f"USD/JPYレート{claimed_rate}円が市場データ({actual_rate:.2f}円)と不整合",
                    "penalty": min(difference, 15),
                }
        else:
            return {
                "verified": False,
                "inconsistent": False,
                "description": "USD/JPY市場データが取得できず、検証不可",
                "penalty": 5,
            }

    def _verify_price_claim(
        self, price: float, context: str, market_snapshot: MarketSnapshot
    ) -> Dict[str, Any]:
        """価格主張を検証"""

        # コンテキストから対象を推定（簡易版）
        if "日経" in context:
            for idx in market_snapshot.stock_indices:
                if "^N225" in idx.symbol:
                    difference = abs(price - idx.current_price)
                    tolerance_price = idx.current_price * (self.tolerance / 100)

                    if difference <= tolerance_price:
                        return {
                            "verified": True,
                            "inconsistent": False,
                            "description": f"日経平均{price:.0f}円は市場データ({idx.current_price:.0f}円)と整合",
                            "penalty": 0,
                        }
                    else:
                        return {
                            "verified": False,
                            "inconsistent": True,
                            "description": f"日経平均{price:.0f}円が市場データ({idx.current_price:.0f}円)と不整合",
                            "penalty": min(difference / 100, 15),
                        }

        return {
            "verified": False,
            "inconsistent": False,
            "description": f"価格{price:.0f}円の対象を特定できず",
            "penalty": 1,
        }

    def _check_date_consistency(
        self, article: Dict[str, Any], market_snapshot: MarketSnapshot
    ) -> Dict[str, Any]:
        """日付整合性をチェック"""
        issues = []

        published_jst = article.get("published_jst")
        if published_jst:
            try:
                if hasattr(published_jst, "date"):
                    pub_date = published_jst
                else:
                    pub_date = datetime.fromisoformat(str(published_jst))

                # 市場時間との整合性チェック
                market_time = market_snapshot.timestamp
                time_diff = abs((pub_date - market_time).total_seconds() / 3600)  # 時間差

                if time_diff > 24:
                    issues.append(
                        f"記事公開時刻({pub_date})と市場データ時刻({market_time})の差が大きすぎます"
                    )

            except Exception as e:
                issues.append(f"日付解析エラー: {e}")

        return {"issues": issues}

    def _check_trend_consistency(
        self, article: Dict[str, Any], market_snapshot: MarketSnapshot
    ) -> Dict[str, Any]:
        """市場トレンド整合性をチェック"""

        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()

        # ポジティブ・ネガティブな表現を検出
        positive_words = ["上昇", "高", "増加", "好調", "改善", "強い", "買い"]
        negative_words = ["下落", "低", "減少", "悪化", "弱い", "売り", "下がる"]

        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in negative_words)

        # 記事のトーンを判定
        if positive_count > negative_count:
            article_sentiment = "positive"
        elif negative_count > positive_count:
            article_sentiment = "negative"
        else:
            article_sentiment = "neutral"

        # 市場の実際のトレンドと比較
        market_sentiment = "neutral"
        if market_snapshot.overall_sentiment.value == "bullish":
            market_sentiment = "positive"
        elif market_snapshot.overall_sentiment.value == "bearish":
            market_sentiment = "negative"

        consistent = (article_sentiment == market_sentiment) or (article_sentiment == "neutral")

        return {
            "consistent": consistent,
            "description": f"記事のトーン({article_sentiment})と市場センチメント({market_sentiment})が{'整合' if consistent else '不整合'}",
        }

    def _determine_confidence_level(self, accuracy_score: float, inconsistency_count: int) -> str:
        """信頼度レベルを決定"""
        if accuracy_score >= 90 and inconsistency_count == 0:
            return "高"
        elif accuracy_score >= 70 and inconsistency_count <= 1:
            return "中"
        elif accuracy_score >= 50:
            return "低"
        else:
            return "要注意"

    def check_batch_consistency(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """記事バッチの一貫性をチェック"""
        self.logger.info(f"バッチ一貫性チェック開始: {len(articles)}件")

        results = []
        overall_accuracy = 0.0
        high_confidence_count = 0

        for article in articles:
            try:
                result = self.check_article_facts(article)
                results.append(
                    {
                        "title": article.get("title", "")[:100],
                        "accuracy_score": result.accuracy_score,
                        "confidence_level": result.confidence_level,
                        "verified_facts_count": len(result.verified_facts),
                        "inconsistencies_count": len(result.inconsistencies),
                        "warnings_count": len(result.warnings),
                    }
                )

                overall_accuracy += result.accuracy_score
                if result.confidence_level in ["高", "中"]:
                    high_confidence_count += 1

            except Exception as e:
                self.logger.error(f"記事ファクトチェックでエラー: {e}")
                results.append(
                    {
                        "title": article.get("title", "")[:100],
                        "accuracy_score": 0.0,
                        "confidence_level": "エラー",
                        "error": str(e),
                    }
                )

        avg_accuracy = overall_accuracy / len(articles) if articles else 0
        reliability_rate = high_confidence_count / len(articles) * 100 if articles else 0

        return {
            "total_articles": len(articles),
            "average_accuracy": round(avg_accuracy, 1),
            "reliability_rate": round(reliability_rate, 1),
            "high_confidence_articles": high_confidence_count,
            "individual_results": results,
            "analysis_timestamp": datetime.now().isoformat(),
        }
