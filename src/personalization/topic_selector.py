"""
感情スコア非依存のトピック選定ユーティリティ
"""

import math
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from dataclasses import dataclass


@dataclass
class Topic:
    """選定されたトピック"""
    headline: str
    blurb: str
    url: str
    source: str
    score: float
    published_jst: datetime
    category: Optional[str] = None
    region: Optional[str] = None


class TopicSelector:
    """感情スコア非依存のトピック選定器"""
    
    # 信頼できるソースの重み
    SOURCE_WEIGHTS = {
        'reuters': 1.3,
        'bloomberg': 1.3,
        'nikkei': 1.2,
        'wsj': 1.2,
        'ft': 1.1,
    }
    
    # 重要キーフレーズ（日英対応）
    KEY_PHRASES = {
        # 市場・経済
        'market', 'markets', '市場', '相場',
        'economy', 'economic', '経済', '景気',
        'inflation', 'インフレ', '物価',
        'interest rate', 'rates', '金利',
        'fed', 'federal reserve', 'fomc', '連邦準備制度',
        'central bank', '中央銀行', '日銀', 'boj',
        'gdp', '国内総生産',
        'unemployment', '失業率',
        
        # 株式・金融
        'stock', 'stocks', 'equity', '株式', '株価',
        'nasdaq', 'dow', 's&p', 'nikkei', '日経',
        'dividend', '配当',
        'earnings', '決算', '業績',
        'ipo', '上場',
        'merger', 'acquisition', 'M&A', '買収', '合併',
        
        # 通貨・商品
        'dollar', 'yen', 'euro', 'currency', '通貨', '為替',
        'oil', 'crude', '原油', '石油',
        'gold', '金', 'silver', '銀',
        'bitcoin', 'cryptocurrency', '仮想通貨', '暗号資産',
        
        # 地政学・政策
        'policy', '政策', 'regulation', '規制',
        'trade', 'tariff', '貿易', '関税',
        'china', '中国', 'us', 'america', 'アメリカ',
        'japan', '日本', 'europe', 'ヨーロッパ',
        'war', 'conflict', '戦争', '紛争',
        
        # 技術・産業
        'tech', 'technology', '技術', 'テクノロジー',
        'ai', 'artificial intelligence', '人工知能',
        'semiconductor', '半導体', 'chip',
        'energy', 'renewable', 'エネルギー', '再生可能',
        'automotive', '自動車', 'ev', '電気自動車',
    }
    
    def __init__(self, tau_hours: float = 8.0):
        """
        Args:
            tau_hours: 新規性スコアの時定数（時間）
        """
        self.tau_hours = tau_hours
    
    def select_top(
        self, 
        articles: List[Dict], 
        k: int = 3, 
        now_jst: Optional[datetime] = None
    ) -> List[Topic]:
        """
        トピックを選定して上位k件を返す
        
        Args:
            articles: 記事リスト（title, summary, published_jst, source, url, category?, region?）
            k: 選定件数
            now_jst: 現在時刻（JST）
            
        Returns:
            選定されたトピックリスト（スコア降順）
        """
        if not articles:
            return []
            
        if now_jst is None:
            now_jst = datetime.now()
        
        # 各記事のスコアを計算
        scored_articles = []
        for article in articles:
            score = self._calculate_score(article, now_jst)
            if score > 0:  # スコア0以下は除外
                scored_articles.append((article, score))
        
        # スコア降順でソート
        scored_articles.sort(key=lambda x: x[1], reverse=True)
        
        # カバレッジを考慮して上位k件を選択
        selected = self._select_with_coverage(scored_articles, k)
        
        # Topicオブジェクトに変換
        topics = []
        for article, score in selected:
            headline = self._truncate_headline(article.get('title', ''))
            blurb = self._create_blurb(article.get('summary', ''), article.get('title', ''))
            
            topic = Topic(
                headline=headline,
                blurb=blurb,
                url=article.get('url', ''),
                source=article.get('source', ''),
                score=score,
                published_jst=article.get('published_jst', now_jst),
                category=article.get('category'),
                region=article.get('region')
            )
            topics.append(topic)
        
        return topics
    
    def _calculate_score(self, article: Dict, now_jst: datetime) -> float:
        """記事のスコアを計算"""
        # 新規性スコア
        published = article.get('published_jst')
        if published:
            hours_diff = (now_jst - published).total_seconds() / 3600
            freshness_score = math.exp(-hours_diff / self.tau_hours)
        else:
            freshness_score = 0.5  # デフォルト
        
        # ソース重み
        source = article.get('source', '').lower()
        source_weight = 1.0
        for key, weight in self.SOURCE_WEIGHTS.items():
            if key in source:
                source_weight = weight
                break
        
        # キーフレーズスコア
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        phrase_score = self._calculate_phrase_score(text)
        
        # 総合スコア
        total_score = freshness_score * source_weight * (1 + phrase_score)
        
        return total_score
    
    def _calculate_phrase_score(self, text: str) -> float:
        """キーフレーズスコアを計算"""
        score = 0.0
        matched_phrases = set()
        
        for phrase in self.KEY_PHRASES:
            if phrase in text and phrase not in matched_phrases:
                # フレーズの長さに応じてスコア調整
                phrase_weight = 1.0 + len(phrase.split()) * 0.1
                score += phrase_weight
                matched_phrases.add(phrase)
                
                # 最大2フレーズまで
                if len(matched_phrases) >= 2:
                    break
        
        return min(score, 2.0)  # 上限設定
    
    def _select_with_coverage(
        self, 
        scored_articles: List[Tuple[Dict, float]], 
        k: int
    ) -> List[Tuple[Dict, float]]:
        """カバレッジを考慮した選択"""
        if len(scored_articles) <= k:
            return scored_articles
        
        selected = []
        used_categories = set()
        used_regions = set()
        
        # まず各カテゴリ・地域から1つずつ選択
        for article, score in scored_articles:
            if len(selected) >= k:
                break
                
            category = article.get('category')
            region = article.get('region')
            
            # 新しいカテゴリまたは地域なら優先選択
            is_new_category = category and category not in used_categories
            is_new_region = region and region not in used_regions
            
            if is_new_category or is_new_region or not selected:
                selected.append((article, score))
                if category:
                    used_categories.add(category)
                if region:
                    used_regions.add(region)
        
        # 残りはスコア順で選択
        remaining = [item for item in scored_articles if item not in selected]
        for item in remaining:
            if len(selected) >= k:
                break
            selected.append(item)
        
        return selected[:k]
    
    def _truncate_headline(self, title: str, max_chars: int = 50) -> str:
        """見出しを適切な長さに切り詰める"""
        if len(title) <= max_chars:
            return title
        
        # 句読点で区切って自然な位置で切断
        for i, char in enumerate(title):
            if i >= max_chars - 3 and char in '。、.,;':
                return title[:i+1]
        
        # 適当な位置で切断
        return title[:max_chars-1] + '…'
    
    def _create_blurb(self, summary: str, title: str, max_chars: int = 100) -> str:
        """1文補足を作成"""
        if not summary:
            return ""
        
        # summaryの最初の文を抽出
        sentences = re.split(r'[。.!?]', summary)
        if sentences:
            blurb = sentences[0].strip()
            if blurb and not blurb.endswith(('。', '.', '!', '?')):
                blurb += '。'
            
            # 長すぎる場合は切り詰め
            if len(blurb) > max_chars:
                blurb = blurb[:max_chars-1] + '…'
            
            return blurb
        
        return ""