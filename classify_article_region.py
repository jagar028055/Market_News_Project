#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
記事地域分類関数 - 3地域対応
日本・米国・欧州の3地域のみに分類
"""

def classify_article_region(article):
    """
    記事の地域を分類（日本・米国・欧州の3地域のみ）
    
    Args:
        article: 記事データ（辞書形式）
    
    Returns:
        str: 'japan', 'usa', 'europe' のいずれか
    """
    title = article.get('title', '').lower()
    summary = article.get('summary', '').lower()
    text = f'{title} {summary}'
    
    # アメリカ関連キーワード
    usa_keywords = [
        '米', 'アメリカ', 'ドル', 'fed', 'fomc', 'ny', 'ニューヨーク', 
        'ダウ', 'ナスダック', 's&p', 'テスラ', 'アップル', 'マイクロソフト', 
        'トランプ', 'バイデン', 'ウォール街', '米国', 'アマゾン', 'google',
        'meta', 'nvidia', 'マイクロソフト'
    ]
    
    # 日本関連キーワード
    japan_keywords = [
        '日本', '日経', '円', '東京', '政府', '日銀', '自民', 
        '経産', '財務省', 'トヨタ', 'ソフトバンク', 'みずほ',
        '三菱', 'ホンダ', 'ニッサン', '任天堂', 'ソニー'
    ]
    
    # 欧州関連キーワード
    europe_keywords = [
        '欧', 'eu', 'ユーロ', 'イギリス', 'ドイツ', 'フランス',
        'ecb', 'ロンドン', 'パリ', 'ベルリン', 'ftse', 'dax',
        '英', '独', '仏', 'brexit'
    ]
    
    # キーワードマッチング（優先度順）
    if any(keyword in text for keyword in japan_keywords):
        return 'japan'
    elif any(keyword in text for keyword in europe_keywords):
        return 'europe'
    elif any(keyword in text for keyword in usa_keywords):
        return 'usa'
    else:
        # デフォルトは米国（最も多い記事数のため）
        return 'usa'