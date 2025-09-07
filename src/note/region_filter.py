# -*- coding: utf-8 -*-

"""
地域別記事フィルタリング機能
既存のカテゴライズ機能を活用して記事を地域別に分類
"""

from typing import List, Dict, Any, Optional
import logging
from enum import Enum


class Region(Enum):
    """地域区分"""
    JAPAN = "japan"
    USA = "usa"
    EUROPE = "europe"
    OTHER = "other"


class RegionFilter:
    """地域別記事フィルタリングクラス"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # 地域判定キーワード
        self.region_keywords = {
            Region.JAPAN: {
                'country': ['日本', 'japan'],
                'indices': ['日経', 'nikkei', 'topix', '東証'],
                'institutions': ['日銀', 'boj', '金融庁', '財務省'],
                'companies': ['トヨタ', 'ソニー', 'ソフトバンク', 'ファーストリテイリング']
            },
            Region.USA: {
                'country': ['米国', 'アメリカ', 'usa', 'us', 'america'],
                'indices': ['s&p', 'sp500', 'nasdaq', 'dow', 'ダウ'],
                'institutions': ['fed', 'fomc', 'federal reserve', 'フェデラル'],
                'companies': ['apple', 'microsoft', 'google', 'amazon', 'tesla']
            },
            Region.EUROPE: {
                'country': ['欧州', 'ヨーロッパ', 'europe', 'eu', 'ドイツ', 'フランス', 'イタリア', 'イギリス'],
                'indices': ['dax', 'ftse', 'cac', 'stoxx'],
                'institutions': ['ecb', '欧州中銀', 'european central bank'],
                'companies': ['volkswagen', 'asml', 'nestle', 'lvmh']
            }
        }
    
    def filter_articles_by_region(self, articles: List[Dict[str, Any]]) -> Dict[Region, List[Dict[str, Any]]]:
        """
        記事を地域別に分類
        
        Args:
            articles: 記事リスト
            
        Returns:
            Dict[Region, List]: 地域別に分類された記事
        """
        self.logger.info(f"地域別記事分類開始: {len(articles)}件")
        
        regional_articles = {
            Region.JAPAN: [],
            Region.USA: [],
            Region.EUROPE: [],
            Region.OTHER: []
        }
        
        for article in articles:
            region = self._classify_article_region(article)
            regional_articles[region].append(article)
        
        # 結果ログ
        for region, article_list in regional_articles.items():
            self.logger.info(f"{region.value}: {len(article_list)}件")
        
        return regional_articles
    
    def _classify_article_region(self, article: Dict[str, Any]) -> Region:
        """
        個別記事の地域を判定
        
        Args:
            article: 記事データ
            
        Returns:
            Region: 判定された地域
        """
        # 既存のregionフィールドがあれば優先使用
        existing_region = article.get('region', '').lower()
        if existing_region:
            if existing_region in ['japan', '日本']:
                return Region.JAPAN
            elif existing_region in ['usa', 'us', '米国']:
                return Region.USA
            elif existing_region in ['europe', 'eu', '欧州']:
                return Region.EUROPE
        
        # テキストベースの判定
        text_content = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        
        region_scores = {
            Region.JAPAN: 0,
            Region.USA: 0,
            Region.EUROPE: 0
        }
        
        # キーワードマッチング
        for region, keywords in self.region_keywords.items():
            for category, keyword_list in keywords.items():
                for keyword in keyword_list:
                    if keyword.lower() in text_content:
                        # カテゴリ別の重み
                        weight = {
                            'country': 3,
                            'indices': 2,
                            'institutions': 2,
                            'companies': 1
                        }.get(category, 1)
                        
                        region_scores[region] += weight
        
        # 最高スコアの地域を返す
        if max(region_scores.values()) == 0:
            return Region.OTHER
        
        return max(region_scores, key=region_scores.get)
    
    def get_market_focus_keywords(self, region: Region) -> Dict[str, List[str]]:
        """
        地域別の市場重点キーワードを取得
        
        Args:
            region: 地域
            
        Returns:
            Dict: カテゴリ別キーワード
        """
        focus_keywords = {
            Region.JAPAN: {
                'indices': ['日経平均', 'TOPIX', '東証'],
                'institutions': ['日銀', 'BOJ'],
                'sectors': ['製造業', '自動車', 'テクノロジー']
            },
            Region.USA: {
                'indices': ['S&P500', 'NASDAQ', 'ダウ平均'],
                'institutions': ['FED', 'FOMC'],
                'sectors': ['テック株', 'GAFAM', 'エネルギー']
            },
            Region.EUROPE: {
                'indices': ['DAX', 'FTSE100', 'CAC40'],
                'institutions': ['ECB', '欧州中央銀行'],
                'sectors': ['金融', '自動車', 'エネルギー']
            }
        }
        
        return focus_keywords.get(region, {})
    
    def validate_regional_balance(self, regional_articles: Dict[Region, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        地域別記事バランスをチェック
        
        Args:
            regional_articles: 地域別記事データ
            
        Returns:
            Dict: バランス分析結果
        """
        total_articles = sum(len(articles) for articles in regional_articles.values())
        
        if total_articles == 0:
            return {"error": "記事が存在しません"}
        
        balance_report = {
            'total_articles': total_articles,
            'regional_distribution': {},
            'recommendations': []
        }
        
        for region, articles in regional_articles.items():
            if region != Region.OTHER:
                count = len(articles)
                percentage = (count / total_articles) * 100
                balance_report['regional_distribution'][region.value] = {
                    'count': count,
                    'percentage': round(percentage, 1)
                }
                
                # 推奨事項
                if count == 0:
                    balance_report['recommendations'].append(
                        f"{region.value}地域の記事が不足しています"
                    )
                elif count < 3:
                    balance_report['recommendations'].append(
                        f"{region.value}地域の記事がもう少し欲しいです（現在{count}件）"
                    )
        
        return balance_report