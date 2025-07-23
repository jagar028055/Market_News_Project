# -*- coding: utf-8 -*-

import hashlib
import re
from difflib import SequenceMatcher
from typing import List, Dict, Any, Set
import logging

from src.logging_config import get_logger


class ContentDeduplicator:
    """コンテンツ重複排除クラス"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.logger = get_logger("content_deduplicator")
        
        # 正規化で除去する一般的なパターン
        self.noise_patterns = [
            r'\s+',  # 連続空白
            r'[\r\n\t]+',  # 改行・タブ
            r'[　\u3000]+',  # 全角スペース
            r'\.{2,}',  # 連続ピリオド
            r'-{2,}',  # 連続ハイフン
            r'={2,}',  # 連続イコール
            # 日本語記事特有のパターン
            r'^\[.*?\]',  # 先頭の[カテゴリ]
            r'\d{4}年\d{1,2}月\d{1,2}日',  # 日付パターン
            r'\d{1,2}:\d{2}',  # 時刻パターン
            r'<[^>]*>',  # HTMLタグ
            r'&[a-zA-Z]+;',  # HTMLエンティティ
        ]
        
        # 除去する一般的なノイズワード
        self.noise_words = {
            '提供:', '【', '】', '（', '）', '(', ')', 
            'source:', 'reuters', 'bloomberg', 'edited by',
            '記者', '編集:', '配信', '更新:', '公開:', '発表:',
            'am', 'pm', 'jst', 'gmt', 'utc',
            # 日本語記事特有のノイズワード
            '速報', '続報', '詳報', '関連', '追記',
            'ロイター', 'ブルームバーグ', '日経', '共同',
            '特集', '解説', '分析', 'コラム',
            '時間', '分', '秒', '午前', '午後'
        }
    
    def generate_content_hash(self, content: str) -> str:
        """
        コンテンツハッシュ生成
        
        Args:
            content: ハッシュ対象コンテンツ
        
        Returns:
            SHA256ハッシュ値
        """
        if not content:
            return ""
        
        # コンテンツ正規化
        normalized = self._normalize_content(content)
        
        # SHA256ハッシュ生成
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def _normalize_content(self, content: str) -> str:
        """
        コンテンツ正規化
        
        Args:
            content: 正規化対象コンテンツ
        
        Returns:
            正規化されたコンテンツ
        """
        if not content:
            return ""
        
        normalized = content.strip()
        
        # ノイズパターンの除去
        for pattern in self.noise_patterns:
            normalized = re.sub(pattern, ' ', normalized)
        
        # 句読点の統一
        normalized = normalized.replace('、', ',').replace('。', '.')
        
        # 大文字小文字の統一
        normalized = normalized.lower()
        
        # ノイズワードの除去
        words = normalized.split()
        filtered_words = [
            word for word in words 
            if word.lower() not in self.noise_words and len(word) > 1
        ]
        
        # 単語を再結合
        normalized = ' '.join(filtered_words)
        
        # 余分な空白を除去
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        テキスト類似度計算
        
        Args:
            text1: テキスト1
            text2: テキスト2
        
        Returns:
            類似度（0.0-1.0）
        """
        if not text1 or not text2:
            return 0.0
        
        # 正規化
        norm1 = self._normalize_content(text1)
        norm2 = self._normalize_content(text2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # SequenceMatcher を使用した類似度計算
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        return similarity
    
    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        タイトル類似度計算（より厳密）
        
        Args:
            title1: タイトル1
            title2: タイトル2
        
        Returns:
            類似度（0.0-1.0）
        """
        if not title1 or not title2:
            return 0.0
        
        # タイトル専用の正規化
        norm1 = self._normalize_title(title1)
        norm2 = self._normalize_title(title2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # 完全一致チェック
        if norm1 == norm2:
            return 1.0
        
        # 部分文字列チェック
        if norm1 in norm2 or norm2 in norm1:
            shorter = min(len(norm1), len(norm2))
            longer = max(len(norm1), len(norm2))
            return shorter / longer if longer > 0 else 0.0
        
        # SequenceMatcher による類似度
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def _normalize_title(self, title: str) -> str:
        """
        タイトル専用正規化
        
        Args:
            title: タイトル
        
        Returns:
            正規化されたタイトル
        """
        if not title:
            return ""
        
        normalized = title.strip()
        
        # タイトル固有のノイズ除去
        title_noise_patterns = [
            r'^\[.*?\]',  # 先頭の[カテゴリ]
            r'【.*?】',    # 【見出し】
            r'\s*-\s*[^-]*$',  # 末尾の - ソース名
            r'\s*\|\s*[^|]*$',  # 末尾の | ソース名
            r'\s*：.*$',  # 末尾の：以降
        ]
        
        for pattern in title_noise_patterns:
            normalized = re.sub(pattern, '', normalized)
        
        # 一般的な正規化
        normalized = self._normalize_content(normalized)
        
        return normalized
    
    def is_duplicate_content(self, content1: str, content2: str) -> bool:
        """
        コンテンツ重複判定
        
        Args:
            content1: コンテンツ1
            content2: コンテンツ2
        
        Returns:
            重複かどうか
        """
        # ハッシュ比較（高速）
        hash1 = self.generate_content_hash(content1)
        hash2 = self.generate_content_hash(content2)
        
        if hash1 == hash2:
            return True
        
        # 類似度比較
        similarity = self.calculate_similarity(content1, content2)
        return similarity > self.similarity_threshold
    
    def is_duplicate_article(self, article1: Dict[str, Any], article2: Dict[str, Any]) -> bool:
        """
        記事重複判定
        
        Args:
            article1: 記事1
            article2: 記事2
        
        Returns:
            重複かどうか
        """
        # タイトル類似度チェック
        title_similarity = self.calculate_title_similarity(
            article1.get('title', ''),
            article2.get('title', '')
        )
        
        if title_similarity > 0.9:
            self.logger.debug(f"High title similarity detected: {title_similarity}")
            return True
        
        # 本文類似度チェック（存在する場合）
        body1 = article1.get('body', '')
        body2 = article2.get('body', '')
        
        if body1 and body2:
            content_similarity = self.calculate_similarity(body1, body2)
            if content_similarity > self.similarity_threshold:
                self.logger.debug(f"High content similarity detected: {content_similarity}")
                return True
        
        return False
    
    def remove_duplicates(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        重複記事除去
        
        Args:
            articles: 記事リスト
        
        Returns:
            重複除去後の記事リスト
        """
        if not articles:
            return []
        
        unique_articles = []
        seen_hashes = set()
        
        for article in articles:
            # コンテンツハッシュによる高速チェック
            content = article.get('body', article.get('title', ''))
            content_hash = self.generate_content_hash(content)
            
            if content_hash in seen_hashes:
                self.logger.debug(f"Duplicate detected by hash: {article.get('title', '')[:50]}")
                continue
            
            # 詳細重複チェック
            is_duplicate = any(
                self.is_duplicate_article(article, existing)
                for existing in unique_articles
            )
            
            if not is_duplicate:
                unique_articles.append(article)
                seen_hashes.add(content_hash)
                
                self.logger.debug(f"Unique article added: {article.get('title', '')[:50]}")
            else:
                self.logger.debug(f"Duplicate detected by similarity: {article.get('title', '')[:50]}")
        
        original_count = len(articles)
        unique_count = len(unique_articles)
        duplicate_count = original_count - unique_count
        
        self.logger.info(f"重複除去完了: 元記事数={original_count}, ユニーク記事数={unique_count}, 重複記事数={duplicate_count}")
        
        return unique_articles
    
    def get_duplicate_groups(self, articles: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        重複記事グループ取得
        
        Args:
            articles: 記事リスト
        
        Returns:
            重複記事グループのリスト
        """
        if not articles:
            return []
        
        groups = []
        processed = set()
        
        for i, article1 in enumerate(articles):
            if i in processed:
                continue
            
            current_group = [article1]
            processed.add(i)
            
            for j, article2 in enumerate(articles[i+1:], i+1):
                if j in processed:
                    continue
                
                if self.is_duplicate_article(article1, article2):
                    current_group.append(article2)
                    processed.add(j)
            
            # 2件以上のグループのみ追加
            if len(current_group) > 1:
                groups.append(current_group)
        
        return groups