# -*- coding: utf-8 -*-

import pytest
from src.database.content_deduplicator import ContentDeduplicator


class TestContentDeduplicator:
    """ContentDeduplicator のテストクラス"""
    
    @pytest.fixture
    def deduplicator(self):
        """ContentDeduplicator インスタンス"""
        return ContentDeduplicator(similarity_threshold=0.85)
    
    def test_generate_content_hash(self, deduplicator):
        """コンテンツハッシュ生成テスト"""
        content1 = "これはテスト記事です。"
        content2 = "これはテスト記事です。"  # 同じ内容
        content3 = "これは異なる記事です。"
        
        hash1 = deduplicator.generate_content_hash(content1)
        hash2 = deduplicator.generate_content_hash(content2)
        hash3 = deduplicator.generate_content_hash(content3)
        
        # 同じ内容は同じハッシュ
        assert hash1 == hash2
        # 異なる内容は異なるハッシュ
        assert hash1 != hash3
        # ハッシュは64文字のHEX文字列
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)
    
    def test_generate_content_hash_empty(self, deduplicator):
        """空コンテンツのハッシュ生成テスト"""
        assert deduplicator.generate_content_hash("") == ""
        assert deduplicator.generate_content_hash(None) == ""
    
    def test_normalize_content(self, deduplicator):
        """コンテンツ正規化テスト"""
        content = "  これは　　テスト記事です。\n\n複数の\t空白があります。  "
        normalized = deduplicator._normalize_content(content)
        
        # 余分な空白が除去されている
        assert "  " not in normalized
        assert "\n" not in normalized
        assert "\t" not in normalized
        # 小文字に変換されている
        assert normalized == normalized.lower()
    
    def test_calculate_similarity(self, deduplicator):
        """類似度計算テスト"""
        text1 = "株価が上昇しています。投資家は楽観的です。"
        text2 = "株価が上昇している。投資家は楽観的。"  # ほぼ同じ
        text3 = "為替が下落しています。市場は悲観的です。"  # 異なる内容
        
        # 類似したテキストは高い類似度
        similarity_high = deduplicator.calculate_similarity(text1, text2)
        assert similarity_high > 0.7
        
        # 異なるテキストは低い類似度
        similarity_low = deduplicator.calculate_similarity(text1, text3)
        assert similarity_low < 0.5
        
        # 同じテキストは類似度1.0
        similarity_same = deduplicator.calculate_similarity(text1, text1)
        assert similarity_same == 1.0
    
    def test_calculate_title_similarity(self, deduplicator):
        """タイトル類似度計算テスト"""
        title1 = "【速報】株価が急上昇 - ロイター"
        title2 = "株価が急上昇"  # ノイズ除去後は同じ
        title3 = "為替が急下落"  # 異なる内容
        
        # ノイズを除去しても同じタイトルは高い類似度
        similarity_high = deduplicator.calculate_title_similarity(title1, title2)
        assert similarity_high > 0.8
        
        # 異なるタイトルは低い類似度
        similarity_low = deduplicator.calculate_title_similarity(title1, title3)
        assert similarity_low < 0.5
    
    def test_normalize_title(self, deduplicator):
        """タイトル正規化テスト"""
        title = "【速報】株価上昇 - 日本経済新聞"
        normalized = deduplicator._normalize_title(title)
        
        # ノイズが除去されている
        assert "【" not in normalized
        assert "】" not in normalized
        assert " - " not in normalized
        assert "日本経済新聞" not in normalized
    
    def test_is_duplicate_content(self, deduplicator):
        """コンテンツ重複判定テスト"""
        content1 = "これは重要なニュースです。市場に大きな影響を与えるでしょう。"
        content2 = "これは重要なニュースです。市場に大きな影響を与えるでしょう。"  # 同じ
        content3 = "これは少し違うニュースです。市場にはあまり影響しないでしょう。"  # 異なる
        
        # 同じコンテンツは重複
        assert deduplicator.is_duplicate_content(content1, content2) == True
        
        # 異なるコンテンツは重複なし
        assert deduplicator.is_duplicate_content(content1, content3) == False
    
    def test_is_duplicate_article(self, deduplicator):
        """記事重複判定テスト"""
        article1 = {
            'title': '株価が上昇しています',
            'body': '本日の株式市場では、主要指数が軒並み上昇しました。',
            'url': 'https://example1.com/article1'
        }
        
        article2 = {
            'title': '株価が上昇している',  # 類似タイトル
            'body': '本日の株式市場では、主要指数が軒並み上昇した。',  # 類似本文
            'url': 'https://example2.com/article2'
        }
        
        article3 = {
            'title': '為替が下落しています',  # 異なるタイトル
            'body': '本日の為替市場では、円安が進行しました。',  # 異なる本文
            'url': 'https://example3.com/article3'
        }
        
        # 類似記事は重複
        assert deduplicator.is_duplicate_article(article1, article2) == True
        
        # 異なる記事は重複なし
        assert deduplicator.is_duplicate_article(article1, article3) == False
    
    def test_remove_duplicates(self, deduplicator):
        """重複記事除去テスト"""
        articles = [
            {
                'title': '株価上昇のニュース',
                'body': '株価が上昇しています。',
                'url': 'https://site1.com/article1'
            },
            {
                'title': '株価上昇のニュース',  # 重複
                'body': '株価が上昇しています。',
                'url': 'https://site2.com/article1'
            },
            {
                'title': '為替下落のニュース',  # ユニーク
                'body': '為替が下落しています。',
                'url': 'https://site1.com/article2'
            },
            {
                'title': '株価上昇について',  # 類似（重複）
                'body': '株価が上昇している。',
                'url': 'https://site3.com/article1'
            }
        ]
        
        unique_articles = deduplicator.remove_duplicates(articles)
        
        # 重複が除去されている
        assert len(unique_articles) == 2
        
        # ユニークな記事が残っている
        titles = [article['title'] for article in unique_articles]
        assert any('株価' in title for title in titles)
        assert any('為替' in title for title in titles)
    
    def test_get_duplicate_groups(self, deduplicator):
        """重複記事グループ取得テスト"""
        articles = [
            {'title': 'ニュース1', 'body': '内容1', 'url': 'url1'},
            {'title': 'ニュース1', 'body': '内容1', 'url': 'url2'},  # グループ1
            {'title': 'ニュース1', 'body': '内容1', 'url': 'url3'},  # グループ1
            {'title': 'ニュース2', 'body': '内容2', 'url': 'url4'},  # ユニーク
            {'title': 'ニュース3', 'body': '内容3', 'url': 'url5'},
            {'title': 'ニュース3', 'body': '内容3', 'url': 'url6'},  # グループ2
        ]
        
        groups = deduplicator.get_duplicate_groups(articles)
        
        # 2つの重複グループが検出される
        assert len(groups) == 2
        
        # 最初のグループは3件
        assert len(groups[0]) == 3
        
        # 2番目のグループは2件
        assert len(groups[1]) == 2
    
    def test_empty_input_handling(self, deduplicator):
        """空入力の処理テスト"""
        # 空リストの処理
        assert deduplicator.remove_duplicates([]) == []
        assert deduplicator.get_duplicate_groups([]) == []
        
        # None値の処理
        assert deduplicator.calculate_similarity("", "") == 0.0
        assert deduplicator.calculate_similarity(None, "text") == 0.0
        assert deduplicator.calculate_title_similarity("", "") == 0.0