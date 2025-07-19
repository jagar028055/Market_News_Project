# -*- coding: utf-8 -*-

"""
Pydantic設定システムへの移行ブリッジファイル
既存コードとの互換性を保ちながら、新しい設定システムを利用
"""

import os

# デフォルト設定値（環境変数に依存しない）
HOURS_LIMIT = 24
SENTIMENT_ANALYSIS_ENABLED = True

# AI関連設定
AI_PROCESS_PROMPT_TEMPLATE = """
あなたは優秀なニュース編集者兼アナリストです。
以下の記事を分析し、次の2つのタスクを実行してください。

1.  **要約**: 記事の最も重要なポイントを抽出し、日本語で200字以内にまとめてください。要約は自然で完結した一つの段落にしてください。
2.  **感情分析**: 記事全体の論調が市場に与える影響を考慮し、センチメントを「Positive」、「Negative」、「Neutral」のいずれかで判定してください。

回答は必ず以下のJSONオブジェクトのみを、他のテキストは一切含めずに返してください。
```json
{{
  "summary": "ここに記事の要約",
  "sentiment_label": "ここに判定結果（Positive, Negative, Neutral）",
  "sentiment_score": ここに判定の確信度（0.0〜1.0の数値）
}}
```

---記事本文---
{text}
---分析結果---
"""

# GoogleドキュメントのID (上書き更新用)
GOOGLE_OVERWRITE_DOC_ID = None

# ロイターに関する設定
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
        "経済category"
    ],
    "exclude_keywords": [
        "スポーツ", "エンタメ", "五輪", "サッカー", "映画", 
        "将棋", "囲碁", "芸能", "ライフ", "アングル："
    ],
    "max_pages": 5,
    "items_per_page": 20
}

# ブルームバーグに関する設定
BLOOMBERG_CONFIG = {
    "exclude_keywords": [
        "動画", "ポッドキャスト", "Bloomberg TV", 
        "意見広告", "ライブブログ", "コラム"
    ]
}