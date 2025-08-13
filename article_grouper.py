# -*- coding: utf-8 -*-

import re
from typing import Dict, List, Any, Optional
import logging
from collections import defaultdict

class ArticleGrouper:
    """記事の地域別・カテゴリ別グループ化を行うクラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
        
        # 地域判定用キーワード辞書
        self.region_keywords = {
            "japan": {
                "primary": [
                    "日銀", "日本銀行", "東京証券取引所", "日経平均", "TOPIX", "東証",
                    "円相場", "円安", "円高", "日本円", "JPY", "USD/JPY", 
                    "日本政府", "財務省", "金融庁", "経産省", "内閣府",
                    "トヨタ", "ソニー", "ソフトバンク", "NTT", "三菱", "三井", "住友",
                    "日本企業", "国内企業", "日系企業"
                ],
                "secondary": [
                    "日本", "Japan", "Tokyo", "東京", "大阪", "名古屋",
                    "黒田", "植田", "岸田", "自民党", "立憲民主党"
                ],
                "exclusion": []
            },
            "usa": {
                "primary": [
                    "FRB", "Fed", "FOMC", "連邦準備制度理事会", "連邦公開市場委員会",
                    "NYSE", "NASDAQ", "ナスダック", "S&P500", "ダウ", "ダウ平均",
                    "ドル相場", "ドル高", "ドル安", "米ドル", "USD",
                    "米政府", "財務省", "米議会", "上院", "下院", "ホワイトハウス",
                    "アップル", "マイクロソフト", "Google", "アマゾン", "テスラ", "Meta",
                    "米企業", "米系企業", "アメリカ企業"
                ],
                "secondary": [
                    "米国", "アメリカ", "USA", "US", "America", "ワシントン", "ニューヨーク",
                    "パウエル", "イエレン", "バイデン", "トランプ", "共和党", "民主党"
                ],
                "exclusion": []
            },
            "china": {
                "primary": [
                    "中国人民銀行", "人民元", "元相場", "CNY", "CNH", "USD/CNY",
                    "上海総合指数", "深セン", "香港ハンセン", "CSI300",
                    "中国政府", "国務院", "人民大会", "共産党", "中央委員会",
                    "アリババ", "テンセント", "バイドゥ", "中国企業", "中系企業"
                ],
                "secondary": [
                    "中国", "China", "北京", "上海", "深圳", "香港", "Taiwan",
                    "習近平", "李強", "一帯一路"
                ],
                "exclusion": []
            },
            "europe": {
                "primary": [
                    "ECB", "欧州中央銀行", "ユーロ", "EUR", "EUR/USD",
                    "DAX", "CAC", "FTSE", "ユーロストックス",
                    "EU", "欧州連合", "欧州委員会", "欧州議会",
                    "欧州企業", "独企業", "仏企業", "英企業"
                ],
                "secondary": [
                    "欧州", "Europe", "ドイツ", "フランス", "イタリア", "スペイン", "英国", "イギリス",
                    "ベルリン", "パリ", "ロンドン", "フランクフルト",
                    "メルケル", "マクロン", "ラガルド"
                ],
                "exclusion": []
            }
        }
        
        # カテゴリ判定用キーワード辞書
        self.category_keywords = {
            "金融政策": [
                "金利", "利上げ", "利下げ", "政策金利", "量的緩和", "QE",
                "金融政策", "FOMC", "日銀", "ECB", "中央銀行", "FRB"
            ],
            "経済指標": [
                "GDP", "インフレ", "CPI", "PPI", "雇用統計", "失業率",
                "貿易収支", "経常収支", "小売売上高", "ISM", "PMI"
            ],
            "企業業績": [
                "決算", "業績", "売上", "利益", "営業利益", "純利益",
                "四半期", "通期", "業績予想", "上方修正", "下方修正"
            ],
            "政治": [
                "選挙", "政権", "大統領", "首相", "議会", "国会",
                "政策", "法案", "予算", "税制", "規制"
            ],
            "市場動向": [
                "株価", "株式", "為替", "債券", "商品", "原油", "金",
                "相場", "取引", "売買", "投資", "資金"
            ],
            "国際情勢": [
                "貿易", "制裁", "関税", "通商", "協定", "紛争",
                "地政学", "戦争", "テロ", "外交"
            ]
        }
    
    def group_articles_by_region(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        記事を地域別にグループ化
        
        Args:
            articles (List[Dict[str, Any]]): 記事のリスト
                各記事は {"title": str, "summary": str, "region": str, "category": str} を含む
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: 地域別グループ化された記事
        """
        grouped = defaultdict(list)
        
        for article in articles:
            # 既存の地域分類がある場合はそれを使用
            region = article.get("region", "").lower()
            
            # 地域分類の正規化
            normalized_region = self._normalize_region(region, article)
            
            # カテゴリの再分類（必要に応じて）
            category = self._classify_category(article)
            article_copy = article.copy()
            article_copy["category"] = category
            article_copy["region"] = normalized_region
            
            grouped[normalized_region].append(article_copy)
        
        # 結果をログに出力
        for region, region_articles in grouped.items():
            self.logger.info(f"地域別グループ化: {region} - {len(region_articles)}記事")
        
        return dict(grouped)
    
    def group_articles_by_category(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        記事をカテゴリ別にグループ化
        
        Args:
            articles (List[Dict[str, Any]]): 記事のリスト
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: カテゴリ別グループ化された記事
        """
        grouped = defaultdict(list)
        
        for article in articles:
            category = self._classify_category(article)
            article_copy = article.copy()
            article_copy["category"] = category
            grouped[category].append(article_copy)
        
        return dict(grouped)
    
    def _normalize_region(self, region: str, article: Dict[str, Any]) -> str:
        """
        地域名を正規化（日本語→英語キー）
        
        Args:
            region (str): 元の地域名
            article (Dict[str, Any]): 記事データ（再分類用）
        
        Returns:
            str: 正規化された地域キー
        """
        # 地域名の正規化マッピング
        region_mapping = {
            "日本": "japan",
            "米国": "usa", 
            "アメリカ": "usa",
            "中国": "china",
            "欧州": "europe",
            "ヨーロッパ": "europe",
            "その他": "other"
        }
        
        # 既存の地域分類を確認
        if region in region_mapping:
            return region_mapping[region]
        elif region in ["japan", "usa", "china", "europe", "other"]:
            return region
        
        # 既存の分類が不明な場合は再分類を試行
        reclassified = self._reclassify_region(article)
        if reclassified:
            return reclassified
        
        return "other"
    
    def _reclassify_region(self, article: Dict[str, Any]) -> Optional[str]:
        """
        記事内容から地域を再分類
        
        Args:
            article (Dict[str, Any]): 記事データ
        
        Returns:
            Optional[str]: 分類された地域、不明な場合はNone
        """
        # 分析対象テキスト（タイトル + 要約）
        text = f"{article.get('title', '')} {article.get('summary', '')}"
        text_lower = text.lower()
        
        region_scores = {}
        
        # 各地域のスコア計算
        for region, keywords in self.region_keywords.items():
            score = 0
            
            # プライマリキーワード（高重み）
            for keyword in keywords["primary"]:
                if keyword.lower() in text_lower:
                    score += 3
            
            # セカンダリキーワード（低重み）
            for keyword in keywords["secondary"]:
                if keyword.lower() in text_lower:
                    score += 1
            
            # 除外キーワード（負のスコア）
            for keyword in keywords.get("exclusion", []):
                if keyword.lower() in text_lower:
                    score -= 2
            
            if score > 0:
                region_scores[region] = score
        
        # 最高スコアの地域を返す
        if region_scores:
            best_region = max(region_scores, key=region_scores.get)
            if region_scores[best_region] >= 2:  # 閾値
                return best_region
        
        return None
    
    def _classify_category(self, article: Dict[str, Any]) -> str:
        """
        記事のカテゴリを分類
        
        Args:
            article (Dict[str, Any]): 記事データ
        
        Returns:
            str: 分類されたカテゴリ
        """
        # 既存のカテゴリがある場合は使用（信頼度チェック付き）
        existing_category = article.get("category", "")
        if existing_category and existing_category in self.category_keywords:
            return existing_category
        
        # 分析対象テキスト
        text = f"{article.get('title', '')} {article.get('summary', '')}"
        text_lower = text.lower()
        
        category_scores = {}
        
        # 各カテゴリのスコア計算
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    score += text_lower.count(keyword.lower())
            
            if score > 0:
                category_scores[category] = score
        
        # 最高スコアのカテゴリを返す
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return "その他"
    
    def get_grouping_statistics(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        グループ化統計を取得
        
        Args:
            articles (List[Dict[str, Any]]): 記事のリスト
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        regional_groups = self.group_articles_by_region(articles)
        category_groups = self.group_articles_by_category(articles)
        
        stats = {
            "total_articles": len(articles),
            "regional_distribution": {
                region: len(articles) for region, articles in regional_groups.items()
            },
            "category_distribution": {
                category: len(articles) for category, articles in category_groups.items()
            },
            "regional_groups": len(regional_groups),
            "category_groups": len(category_groups)
        }
        
        return stats


def group_articles_for_pro_summary(articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Pro統合要約用に記事をグループ化するメイン関数
    
    Args:
        articles (List[Dict[str, Any]]): 記事のリスト
    
    Returns:
        Dict[str, List[Dict[str, Any]]]: 地域別グループ化された記事
    """
    logger = logging.getLogger(__name__)
    
    if not articles:
        logger.warning("グループ化対象の記事がありません")
        return {}
    
    grouper = ArticleGrouper()
    grouped_articles = grouper.group_articles_by_region(articles)
    
    # 統計情報をログ出力
    stats = grouper.get_grouping_statistics(articles)
    logger.info(f"記事グループ化完了: 総記事数={stats['total_articles']}, "
                f"地域数={stats['regional_groups']}, "
                f"分布={stats['regional_distribution']}")
    
    return grouped_articles


if __name__ == '__main__':
    # テスト用コード
    logging.basicConfig(level=logging.INFO)
    
    test_articles = [
        {
            "title": "日銀、政策金利据え置き決定",
            "summary": "日本銀行は金融政策決定会合で政策金利を据え置き決定。植田総裁は記者会見で緩和継続を表明。",
            "region": "日本",
            "category": "金融政策"
        },
        {
            "title": "FRB、利上げ検討を示唆",
            "summary": "米連邦準備制度理事会のパウエル議長は講演で追加利上げの可能性を示唆した。",
            "region": "米国", 
            "category": "金融政策"
        },
        {
            "title": "トヨタ自動車、増益発表",
            "summary": "トヨタ自動車は四半期決算で前年同期比20%増益を発表。海外販売好調が寄与。",
            "region": "日本",
            "category": "企業業績"
        },
        {
            "title": "中国GDP成長率鈍化",
            "summary": "中国の第3四半期GDP成長率は前年同期比4.9%と予想を下回った。",
            "region": "中国",
            "category": "経済指標"
        },
        {
            "title": "欧州株式市場続伸",
            "summary": "欧州主要株価指数は続伸。ECBの金融政策への期待が支援材料。",
            "region": "欧州",
            "category": "市場動向"
        }
    ]
    
    print("=== 記事グループ化テスト ===")
    
    # 地域別グループ化
    grouped = group_articles_for_pro_summary(test_articles)
    
    print(f"\n地域別グループ化結果:")
    for region, articles in grouped.items():
        print(f"  {region}: {len(articles)}記事")
        for article in articles:
            print(f"    - {article['title']}")
    
    # 統計情報
    grouper = ArticleGrouper()
    stats = grouper.get_grouping_statistics(test_articles)
    print(f"\n統計情報:")
    print(f"  総記事数: {stats['total_articles']}")
    print(f"  地域別分布: {stats['regional_distribution']}")
    print(f"  カテゴリ別分布: {stats['category_distribution']}")