# -*- coding: utf-8 -*-

"""
このファイルには、スクレイピングの挙動を制御するための設定が含まれています。
検索クエリ、対象カテゴリ、除外キーワードなどをここで管理します。
"""

# --- グローバル設定 ---
HOURS_LIMIT = 24  # 記事を収集する時間範囲（過去何時間か）

# GoogleドキュメントのID (上書き更新用) - ここに更新したいドキュメントのIDを設定してください
# 例: GOOGLE_OVERWRITE_DOC_ID = "1aBcDeFgHiJkLmNoPqRsTuVwXyZ123456"
GOOGLE_OVERWRITE_DOC_ID = "1-Fun3I_0iiv0vH1vut6fUYJ5tUC3Ls1KsE3xyQP9YxQ"

# --- ロイターに関する設定 ---
REUTERS_CONFIG = {
    "query": "米 OR 金融 OR 経済 OR 株価 OR FRB OR FOMC OR 決算 OR 利上げ OR インフレ",
    "target_categories": [
        "ビジネスcategory",
        "マーケットcategory",
        "トップニュースcategory",
        "ワールドcategory",
        "テクノロジーcategory",
        "アジア市場category",
        "不明",
        "ワールドcategory",
        "経済category"
    ],
    "exclude_keywords": [
        "スポーツ", "エンタメ", "五輪", "サッカー", "映画", "将棋", "囲碁", "芸能", "ライフ", "アングル："
    ],
    "max_pages": 5,
    "items_per_page": 20
}

# --- ブルームバーグに関する設定 ---
BLOOMBERG_CONFIG = {
    "exclude_keywords": [
        "動画", "ポッドキャスト", "Bloomberg TV", "意見広告", "ライブブログ", "コラム"
    ]
}
