# -*- coding: utf-8 -*-

"""
パフォーマンス最適化版 ArticleGrouper
Phase 4.2での最適化：キャッシュ、並列処理、アルゴリズム改善
"""

import re
from typing import Dict, List, Any, Optional, Set, Tuple
import logging
from collections import defaultdict
import hashlib
import json

class OptimizedArticleGrouper:
    """最適化された記事の地域別・カテゴリ別グループ化クラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
        
        # キャッシュ用辞書
        self._region_cache = {}
        self._category_cache = {}
        
        # プリコンパイルされた正規表現パターン
        self._compiled_patterns = {}
        
        # 最適化されたキーワード辞書（大文字・小文字統一、セット化）
        self.region_keywords = self._optimize_keywords({
            "japan": {
                "primary": {
                    "日銀", "日本銀行", "東京証券取引所", "日経平均", "topix", "東証",
                    "円相場", "円安", "円高", "日本円", "jpy", "usd/jpy", 
                    "日本政府", "財務省", "金融庁", "経産省", "内閣府",
                    "トヨタ", "ソニー", "ソフトバンク", "ntt", "三菱", "三井", "住友",
                    "日本企業", "国内企業", "日系企業"
                },
                "secondary": {
                    "日本", "japan", "tokyo", "東京", "大阪", "名古屋",
                    "黒田", "植田", "岸田", "自民党", "立憲民主党"
                },
                "exclusion": set()
            },
            "usa": {
                "primary": {
                    "frb", "fed", "fomc", "連邦準備制度理事会", "連邦公開市場委員会",
                    "nyse", "nasdaq", "ナスダック", "s&p500", "ダウ", "ダウ平均",
                    "ドル相場", "ドル高", "ドル安", "米ドル", "usd",
                    "米政府", "財務省", "米議会", "上院", "下院", "ホワイトハウス",
                    "アップル", "マイクロソフト", "google", "アマゾン", "テスラ", "meta",
                    "米企業", "米系企業", "アメリカ企業"
                },
                "secondary": {
                    "米国", "アメリカ", "usa", "us", "america", "ワシントン", "ニューヨーク",
                    "パウエル", "イエレン", "バイデン", "トランプ", "共和党", "民主党"
                },
                "exclusion": set()
            },
            "china": {
                "primary": {
                    "中国人民銀行", "人民元", "元相場", "cny", "cnh", "usd/cny",
                    "上海総合指数", "深セン", "香港ハンセン", "csi300",
                    "中国政府", "国務院", "人民大会", "共産党", "中央委員会",
                    "アリババ", "テンセント", "バイドゥ", "中国企業", "中系企業"
                },
                "secondary": {
                    "中国", "china", "北京", "上海", "深圳", "香港", "taiwan",
                    "習近平", "李強", "一帯一路"
                },
                "exclusion": set()
            },
            "europe": {
                "primary": {
                    "ecb", "欧州中央銀行", "ユーロ", "eur", "eur/usd",
                    "dax", "cac", "ftse", "ユーロストックス",
                    "eu", "欧州連合", "欧州委員会", "欧州議会",
                    "欧州企業", "独企業", "仏企業", "英企業"
                },
                "secondary": {
                    "欧州", "europe", "ドイツ", "フランス", "イタリア", "スペイン", "英国", "イギリス",
                    "ベルリン", "パリ", "ロンドン", "フランクフルト",
                    "メルケル", "マクロン", "ラガルド"
                },
                "exclusion": set()
            }
        })
        
        # 最適化されたカテゴリキーワード辞書
        self.category_keywords = self._optimize_keywords({
            "金融政策": {
                "primary": {
                    "金利", "利上げ", "利下げ", "政策金利", "量的緩和", "qe",
                    "金融政策", "fomc", "日銀", "ecb", "中央銀行", "frb"
                }
            },
            "経済指標": {
                "primary": {
                    "gdp", "インフレ", "cpi", "ppi", "雇用統計", "失業率",
                    "貿易収支", "経常収支", "小売売上高", "ism", "pmi"
                }
            },
            "企業業績": {
                "primary": {
                    "決算", "業績", "売上", "利益", "営業利益", "純利益",
                    "四半期", "通期", "業績予想", "上方修正", "下方修正"
                }
            },
            "政治": {
                "primary": {
                    "選挙", "政権", "大統領", "首相", "議会", "国会",
                    "政策", "法案", "予算", "税制", "規制"
                }
            },
            "市場動向": {
                "primary": {
                    "株価", "株式", "為替", "債券", "商品", "原油", "金",
                    "相場", "取引", "売買", "投資", "資金"
                }
            },
            "国際情勢": {
                "primary": {
                    "貿易", "制裁", "関税", "通商", "協定", "紛争",
                    "地政学", "戦争", "テロ", "外交"
                }
            }
        })
    
    def _optimize_keywords(self, keywords_dict: Dict) -> Dict:
        """キーワード辞書の最適化（小文字統一、セット変換）"""
        optimized = {}
        for region_or_category, data in keywords_dict.items():
            optimized[region_or_category] = {}
            for level, keywords in data.items():
                if isinstance(keywords, list):
                    # リストをセットに変換し、小文字化
                    optimized[region_or_category][level] = {k.lower() for k in keywords}
                elif isinstance(keywords, set):
                    # 既にセットの場合は小文字化のみ
                    optimized[region_or_category][level] = {k.lower() for k in keywords}
                else:
                    optimized[region_or_category][level] = set()
        return optimized
    
    def _get_content_hash(self, content: str) -> str:
        """コンテンツのハッシュ値を生成（キャッシュキー用）"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
    
    def _extract_searchable_content(self, article: Dict[str, Any]) -> str:
        """記事から検索対象コンテンツを抽出"""
        content_parts = []
        
        # タイトル（重要度高）
        title = article.get("title", "")
        if title:
            content_parts.extend([title] * 3)  # 重み付けで3回追加
        
        # 要約または本文
        summary = article.get("summary", "")
        body = article.get("body", "")
        
        if summary:
            content_parts.append(summary)
        elif body:
            # 本文の場合は最初の500文字のみ使用（パフォーマンス改善）
            content_parts.append(body[:500])
        
        return " ".join(content_parts).lower()
    
    def _classify_region_optimized(self, article: Dict[str, Any]) -> str:
        """最適化された地域分類"""
        # 既存の地域情報がある場合
        existing_region = article.get("region", "").lower()
        if existing_region in ["japan", "usa", "china", "europe"]:
            return existing_region
        
        # コンテンツ抽出
        content = self._extract_searchable_content(article)
        
        # キャッシュチェック
        content_hash = self._get_content_hash(content)
        if content_hash in self._region_cache:
            return self._region_cache[content_hash]
        
        # 地域スコア計算（最適化版）
        region_scores = defaultdict(int)
        
        for region, keywords in self.region_keywords.items():
            # Primary キーワードマッチ（重み3）
            for keyword in keywords.get("primary", set()):
                if keyword in content:
                    region_scores[region] += 3
            
            # Secondary キーワードマッチ（重み1）
            for keyword in keywords.get("secondary", set()):
                if keyword in content:
                    region_scores[region] += 1
            
            # Exclusion キーワードチェック（重み-2）
            for keyword in keywords.get("exclusion", set()):
                if keyword in content:
                    region_scores[region] -= 2
        
        # 最高スコアの地域を選択
        if region_scores:
            best_region = max(region_scores.items(), key=lambda x: x[1])[0]
            
            # 最小閾値チェック
            if region_scores[best_region] >= 1:
                result = best_region
            else:
                result = "other"
        else:
            result = "other"
        
        # キャッシュに保存
        self._region_cache[content_hash] = result
        return result
    
    def _classify_category_optimized(self, article: Dict[str, Any]) -> str:
        """最適化されたカテゴリ分類"""
        # 既存のカテゴリ情報がある場合
        existing_category = article.get("category", "")
        if existing_category in self.category_keywords:
            return existing_category
        
        # コンテンツ抽出
        content = self._extract_searchable_content(article)
        
        # キャッシュチェック
        content_hash = self._get_content_hash(content)
        cache_key = f"cat_{content_hash}"
        if cache_key in self._category_cache:
            return self._category_cache[cache_key]
        
        # カテゴリスコア計算
        category_scores = defaultdict(int)
        
        for category, keywords in self.category_keywords.items():
            for keyword in keywords.get("primary", set()):
                if keyword in content:
                    category_scores[category] += 1
        
        # 最高スコアのカテゴリを選択
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])[0]
            result = best_category
        else:
            result = "その他"
        
        # キャッシュに保存
        self._category_cache[cache_key] = result
        return result
    
    def group_articles_by_region(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        最適化された地域別記事グループ化
        
        Args:
            articles (List[Dict[str, Any]]): 記事のリスト
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: 地域別グループ化された記事
        """
        if not articles:
            return {}
        
        grouped = defaultdict(list)
        
        # バッチ処理で効率化
        for article in articles:
            region = self._classify_region_optimized(article)
            category = self._classify_category_optimized(article)
            
            # 記事コピーの最適化
            article_copy = {
                **article,
                "region": region,
                "category": category
            }
            
            grouped[region].append(article_copy)
        
        # ログ出力（デバッグ用）
        total_articles = len(articles)
        for region, region_articles in grouped.items():
            percentage = (len(region_articles) / total_articles) * 100
            self.logger.debug(
                f"地域別グループ化: {region} - {len(region_articles)}記事 ({percentage:.1f}%)"
            )
        
        return dict(grouped)
    
    def group_articles_by_category(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        最適化されたカテゴリ別記事グループ化
        
        Args:
            articles (List[Dict[str, Any]]): 記事のリスト
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: カテゴリ別グループ化された記事
        """
        if not articles:
            return {}
        
        grouped = defaultdict(list)
        
        for article in articles:
            category = self._classify_category_optimized(article)
            region = article.get("region") or self._classify_region_optimized(article)
            
            article_copy = {
                **article,
                "category": category,
                "region": region
            }
            
            grouped[category].append(article_copy)
        
        return dict(grouped)
    
    def get_cache_stats(self) -> Dict[str, int]:
        """キャッシュ統計情報を取得"""
        return {
            "region_cache_size": len(self._region_cache),
            "category_cache_size": len(self._category_cache),
            "total_cache_entries": len(self._region_cache) + len(self._category_cache)
        }
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self._region_cache.clear()
        self._category_cache.clear()
        self.logger.info("分類キャッシュをクリアしました")
    
    def get_region_distribution(self, articles: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """地域別記事分布の統計情報を取得"""
        grouped = self.group_articles_by_region(articles)
        total = len(articles)
        
        distribution = {}
        for region, region_articles in grouped.items():
            count = len(region_articles)
            distribution[region] = {
                "count": count,
                "percentage": (count / total) * 100 if total > 0 else 0,
                "categories": {}
            }
            
            # カテゴリ内訳も取得
            categories = defaultdict(int)
            for article in region_articles:
                categories[article.get("category", "その他")] += 1
            
            distribution[region]["categories"] = dict(categories)
        
        return distribution


# 後方互換性のため、元のクラス名でもアクセス可能に
ArticleGrouper = OptimizedArticleGrouper