# -*- coding: utf-8 -*-

import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Optional


class URLNormalizer:
    """URL正規化クラス"""

    def __init__(self):
        # 除去するトラッキングパラメータ
        self.tracking_params = {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "fbclid",
            "gclid",
            "msclkid",
            "ref",
            "referrer",
            "ref_src",
            "_ga",
            "_gid",
            "mc_cid",
            "mc_eid",
            "campaign",
            "source",
            "medium",
            "term",
            "content",
        }

        # サイト別記事ID抽出パターン
        self.article_id_patterns = {
            "reuters.com": r"/article/([a-zA-Z0-9\-]+)",
            "bloomberg.co.jp": r"/news/articles/([a-zA-Z0-9]+)",
            "nikkei.com": r"/article/([A-Z0-9]+)",
            "wsj.com": r"/articles/([a-zA-Z0-9\-]+)",
            "cnbc.com": r"/(\d{4}/\d{2}/\d{2}/[a-zA-Z0-9\-]+)",
        }

    def normalize_url(self, url: str) -> str:
        """
        URL正規化処理

        Args:
            url: 正規化対象URL

        Returns:
            正規化されたURL
        """
        if not url:
            return ""

        try:
            # URLをパース
            parsed = urlparse(url.lower().strip())

            # スキームの正規化
            if not parsed.scheme:
                parsed = urlparse(f"https://{url}")

            # ホスト名の正規化
            hostname = parsed.netloc
            if hostname.startswith("www."):
                hostname = hostname[4:]

            # パスの正規化
            path = parsed.path.rstrip("/")
            if not path:
                path = "/"

            # クエリパラメータの正規化
            query_params = parse_qs(parsed.query)

            # トラッキングパラメータを除去
            filtered_params = {
                k: v for k, v in query_params.items() if k.lower() not in self.tracking_params
            }

            # パラメータを辞書順でソート
            normalized_query = urlencode(sorted(filtered_params.items()), doseq=True)

            # 正規化されたURLを構築
            normalized = urlunparse(
                (
                    parsed.scheme,
                    hostname,
                    path,
                    parsed.params,
                    normalized_query,
                    "",  # フラグメント除去
                )
            )

            return normalized

        except Exception:
            # パースエラーの場合は元のURLを返す
            return url.strip()

    def extract_article_id(self, url: str) -> Optional[str]:
        """
        記事IDの抽出（サイト別対応）

        Args:
            url: 記事URL

        Returns:
            記事ID（抽出できない場合はNone）
        """
        if not url:
            return None

        try:
            parsed = urlparse(url.lower())
            hostname = parsed.netloc
            if hostname.startswith("www."):
                hostname = hostname[4:]

            # サイト別パターンマッチング
            for domain, pattern in self.article_id_patterns.items():
                if domain in hostname:
                    match = re.search(pattern, url, re.IGNORECASE)
                    if match:
                        return match.group(1)

            return None

        except Exception:
            return None

    def is_same_article(self, url1: str, url2: str) -> bool:
        """
        同一記事URL判定

        Args:
            url1: URL1
            url2: URL2

        Returns:
            同一記事かどうか
        """
        # URL正規化後の比較
        norm1 = self.normalize_url(url1)
        norm2 = self.normalize_url(url2)

        if norm1 == norm2:
            return True

        # 記事ID比較（同一サイト内）
        id1 = self.extract_article_id(url1)
        id2 = self.extract_article_id(url2)

        if id1 and id2 and id1 == id2:
            # 同じサイトドメインかチェック
            try:
                domain1 = urlparse(url1).netloc.replace("www.", "")
                domain2 = urlparse(url2).netloc.replace("www.", "")
                return domain1 == domain2
            except Exception:
                return False

        return False

    def get_canonical_url(self, url: str) -> str:
        """
        正規化URL取得（エイリアス）

        Args:
            url: 元URL

        Returns:
            正規化URL
        """
        return self.normalize_url(url)
