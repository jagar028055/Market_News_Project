# -*- coding: utf-8 -*-

"""
Google Document Data Fetcher
Googleドキュメントから記事データを取得し、ポッドキャスト用データソースとして提供
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from gdocs.client import authenticate_google_services
from src.database.models import Article, AIAnalysis
from src.podcast.data_fetcher.enhanced_database_article_fetcher import ArticleScore


@dataclass
class ParsedArticle:
    """解析済み記事データ"""

    title: str
    url: str
    published_time: str
    body: str
    sentiment_icon: str


class GoogleDocumentDataFetcher:
    """Googleドキュメントデータ取得クラス"""

    def __init__(self, document_id: str):
        """
        初期化

        Args:
            document_id: 取得対象のGoogleドキュメントID
        """
        self.document_id = document_id
        self.logger = logging.getLogger(__name__)

        # 感情アイコンマッピング
        self.sentiment_mapping = {
            "😊": ("Positive", 0.7),
            "😠": ("Negative", -0.7),
            "😐": ("Neutral", 0.0),
            "🤔": ("N/A", 0.0),
            "⚠️": ("Error", 0.0),
        }

    def fetch_articles_for_podcast(self, target_count: int = 6, **kwargs) -> List[ArticleScore]:
        """
        Googleドキュメントからポッドキャスト用記事を取得

        Args:
            target_count: 目標記事数
            **kwargs: 互換性のための引数（使用しない）

        Returns:
            記事スコアリストへ変換されたArticleScore形式
        """
        try:
            self.logger.info(f"Googleドキュメント記事取得開始 - 目標数: {target_count}")

            # Google Docsサービス認証
            drive_service, docs_service, _ = authenticate_google_services()
            if not docs_service:
                self.logger.error("Google Docs認証に失敗しました")
                return []

            # ドキュメント内容取得
            parsed_articles = self._fetch_and_parse_document(docs_service)
            if not parsed_articles:
                self.logger.warning("Googleドキュメントから記事を取得できませんでした")
                return []

            # Article/AIAnalysisオブジェクトへ変換
            article_scores = self._convert_to_article_scores(parsed_articles)

            # 目標数に制限
            selected_articles = article_scores[:target_count]

            self.logger.info(f"選択記事数: {len(selected_articles)}")
            for i, article_score in enumerate(selected_articles, 1):
                self.logger.info(
                    f"選択記事{i}: {article_score.article.title[:50]}... "
                    f"(推定スコア: {article_score.score:.2f})"
                )

            return selected_articles

        except Exception as e:
            self.logger.error(f"Googleドキュメント記事取得エラー: {e}", exc_info=True)
            return []

    def _fetch_and_parse_document(self, docs_service) -> List[ParsedArticle]:
        """
        Googleドキュメントを取得・解析

        Args:
            docs_service: Google Docs APIサービス

        Returns:
            解析済み記事リスト
        """
        try:
            # ドキュメント取得
            doc = docs_service.documents().get(documentId=self.document_id).execute()
            doc_content = doc.get("body", {}).get("content", [])

            # テキスト内容を抽出
            full_text = ""
            for element in doc_content:
                if "paragraph" in element:
                    paragraph = element.get("paragraph", {})
                    elements = paragraph.get("elements", [])
                    for elem in elements:
                        if "textRun" in elem:
                            content = elem.get("textRun", {}).get("content", "")
                            full_text += content

            self.logger.info(f"ドキュメント内容取得完了 - 文字数: {len(full_text)}")

            # 記事データを解析
            parsed_articles = self._parse_article_content(full_text)

            return parsed_articles

        except Exception as e:
            self.logger.error(f"ドキュメント取得・解析エラー: {e}", exc_info=True)
            return []

    def _parse_article_content(self, content: str) -> List[ParsedArticle]:
        """
        ドキュメント内容から記事データを解析

        Args:
            content: ドキュメント内容

        Returns:
            解析済み記事リスト
        """
        articles = []

        try:
            # 記事分割パターン（区切り線で分割）
            article_sections = re.split(r"-{10,}", content)

            for section in article_sections:
                section = section.strip()
                if not section:
                    continue

                # 記事情報を抽出
                parsed_article = self._extract_article_info(section)
                if parsed_article:
                    articles.append(parsed_article)

            self.logger.info(f"記事解析完了 - 解析記事数: {len(articles)}")
            return articles

        except Exception as e:
            self.logger.error(f"記事内容解析エラー: {e}", exc_info=True)
            return []

    def _extract_article_info(self, section: str) -> Optional[ParsedArticle]:
        """
        セクションから記事情報を抽出

        Args:
            section: 記事セクション

        Returns:
            解析済み記事データ（失敗時はNone）
        """
        try:
            lines = section.split("\n")
            lines = [line.strip() for line in lines if line.strip()]

            if len(lines) < 3:
                return None

            # タイトル行を探す（日時+アイコン+タイトル形式）
            title_line = None
            url_line = None
            body_start_idx = None

            for i, line in enumerate(lines):
                # 日時パターンとアイコンを含む行を探す
                if re.match(r"\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}\)", line):
                    title_line = line
                    # 次の行がURLの可能性
                    if i + 1 < len(lines) and lines[i + 1].startswith("http"):
                        url_line = lines[i + 1]
                        body_start_idx = i + 2
                    break

            if not title_line or not url_line:
                return None

            # タイトル行から情報抽出
            title_match = re.match(
                r"\((\d{4}-\d{2}-\d{2} \d{2}:\d{2})\)\s*([😊😠😐🤔⚠️]?)\s*(.+)", title_line
            )
            if not title_match:
                return None

            published_time = title_match.group(1)
            sentiment_icon = title_match.group(2) or "😐"
            title = title_match.group(3).strip()
            url = url_line.strip()

            # 記事本文を抽出（複数のパターンを試行）
            body = ""
            body_found = False

            # 複数の記事本文開始パターンを定義
            body_start_patterns = [
                "--- 記事全文 ---",
                "記事全文",
                "全文",
                "本文",
                "---"
            ]

            for i in range(body_start_idx or 2, len(lines)):
                line = lines[i].strip()
                
                # 記事本文開始パターンをチェック
                if not body_found:
                    for pattern in body_start_patterns:
                        if pattern in line:
                            body_found = True
                            break
                    if body_found:
                        continue
                
                # 記事本文開始が見つからない場合、3行目以降を本文として扱う
                if not body_found and i >= (body_start_idx or 2) + 1:
                    body_found = True

                if body_found:
                    # 空行や区切り線をスキップ
                    if line and not line.startswith("---") and not line.startswith("="):
                        body += line + "\n"
                    # 次の記事の開始を検出したら終了
                    elif line.startswith("(202") or re.match(r"^\(\d{4}-\d{2}-\d{2}", line):
                        break

            body = body.strip()

            # 本文が短すぎる場合、タイトルの後の全テキストを使用
            if len(body) < 100:
                self.logger.info(f"本文が短いため、代替抽出を実行: {title[:50]}...")
                body = ""
                for i in range(2, len(lines)):
                    line = lines[i].strip()
                    if line and not line.startswith("---") and not line.startswith("="):
                        body += line + "\n"
                    # 次の記事の開始を検出したら終了
                    elif line.startswith("(202") or re.match(r"^\(\d{4}-\d{2}-\d{2}", line):
                        break
                body = body.strip()

            if not body or len(body) < 50:
                self.logger.warning(f"記事本文が見つからないか短すぎます: {title[:50]}...")
                return None

            return ParsedArticle(
                title=title,
                url=url,
                published_time=published_time,
                body=body,
                sentiment_icon=sentiment_icon,
            )

        except Exception as e:
            self.logger.error(f"記事情報抽出エラー: {e}", exc_info=True)
            return None

    def _convert_to_article_scores(
        self, parsed_articles: List[ParsedArticle]
    ) -> List[ArticleScore]:
        """
        解析済み記事をArticleScoreオブジェクトに変換

        Args:
            parsed_articles: 解析済み記事リスト

        Returns:
            ArticleScoreリスト
        """
        article_scores = []

        for i, parsed in enumerate(parsed_articles):
            try:
                # 疑似Articleオブジェクト作成
                article = Article()
                article.id = f"gdoc_{i + 1}"
                article.title = parsed.title
                article.url = parsed.url
                article.body = parsed.body
                article.source = self._detect_source(parsed.url)
                article.scraped_at = self._parse_published_time(parsed.published_time)

                # 疑似AIAnalysisオブジェクト作成
                analysis = AIAnalysis()
                analysis.article_id = article.id

                # センチメント情報を設定
                sentiment_label, sentiment_score = self.sentiment_mapping.get(
                    parsed.sentiment_icon, ("Neutral", 0.0)
                )
                analysis.sentiment_label = sentiment_label
                analysis.sentiment_score = sentiment_score

                # 簡易要約生成（本文の最初の200文字）
                analysis.summary = self._generate_simple_summary(parsed.body)

                # カテゴリと地域を推定
                analysis.category = self._estimate_category(parsed.title, parsed.body)
                analysis.region = self._estimate_region(parsed.title, parsed.body)

                # スコア計算（感情強度 + 文字数ベース）
                score = abs(sentiment_score) + (min(len(parsed.body) / 1000.0, 1.0) * 2.0)

                article_score = ArticleScore(
                    article=article,
                    analysis=analysis,
                    score=score,
                    score_breakdown={
                        "sentiment": abs(sentiment_score),
                        "content_length": min(len(parsed.body) / 1000.0, 1.0) * 2.0,
                        "source": "google_document",
                    },
                )

                article_scores.append(article_score)

            except Exception as e:
                self.logger.error(f"記事変換エラー: {e}", exc_info=True)
                continue

        # スコア順でソート
        article_scores.sort(key=lambda x: x.score, reverse=True)

        return article_scores

    def _detect_source(self, url: str) -> str:
        """URLからソースを検出"""
        if "reuters.com" in url.lower():
            return "Reuters"
        elif "bloomberg.com" in url.lower():
            return "Bloomberg"
        else:
            return "Unknown"

    def _parse_published_time(self, time_str: str) -> datetime:
        """公開時間をdatetimeオブジェクトに変換"""
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except:
            return datetime.now()

    def _generate_simple_summary(self, body: str) -> str:
        """簡易要約生成"""
        # 最初の200文字を要約として使用
        summary = body[:200].strip()
        if len(body) > 200:
            summary += "..."
        return summary

    def _estimate_category(self, title: str, body: str) -> str:
        """カテゴリ推定"""
        content = (title + " " + body).lower()

        if any(word in content for word in ["金利", "政策金利", "日銀", "frb", "fomc", "連邦準備"]):
            return "金融政策"
        elif any(word in content for word in ["gdp", "cpi", "失業率", "経済指標", "経済成長"]):
            return "経済指標"
        elif any(word in content for word in ["決算", "業績", "売上", "利益", "株価"]):
            return "企業業績"
        elif any(word in content for word in ["市場", "株式", "債券", "為替"]):
            return "マーケット"
        elif any(word in content for word in ["技術", "ai", "it", "テクノロジー", "デジタル"]):
            return "テクノロジー"
        else:
            return "ビジネス"

    def _estimate_region(self, title: str, body: str) -> str:
        """地域推定"""
        content = (title + " " + body).lower()

        if any(word in content for word in ["日銀", "日本", "東京", "円"]):
            return "japan"
        elif any(word in content for word in ["fed", "frb", "fomc", "アメリカ", "米国", "ドル"]):
            return "usa"
        elif any(word in content for word in ["中国", "人民銀行", "元", "北京", "上海"]):
            return "china"
        elif any(word in content for word in ["欧州", "ecb", "ユーロ", "ドイツ", "フランス"]):
            return "europe"
        else:
            return "other"

    def get_article_statistics(self, **kwargs) -> Dict[str, Any]:
        """
        統計情報取得（互換性のため）

        Returns:
            基本統計情報
        """
        return {
            "data_source": "google_document",
            "document_id": self.document_id,
            "last_fetch_time": datetime.now().isoformat(),
        }
