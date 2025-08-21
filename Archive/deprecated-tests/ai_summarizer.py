# -*- coding: utf-8 -*-

import google.generativeai as genai
import os
import json
import re
from typing import Optional, Dict, Any
import logging

# プロジェクトモジュール
import market_news_config as config

def process_article_with_ai(api_key: str, text: str) -> Optional[Dict[str, Any]]:
    """
    Gemini APIを使用して、記事の要約を実行します。
    
    Args:
        api_key (str): Google Gemini APIキー。
        text (str): 分析する元の記事本文。
        
    Returns:
        Optional[Dict[str, Any]]: 要約結果を含む辞書、またはエラーの場合はNone。
                                  例: {'summary': '...', 'keywords': ['keyword1', 'keyword2']}
    """
    if not api_key:
        logging.error("エラー: Gemini APIキーが設定されていません。")
        return None

    # 空データや短すぎるデータの早期チェック
    if not text or len(text.strip()) < 50:
        logging.warning(f"記事本文が空または短すぎるためスキップ (長さ: {len(text.strip()) if text else 0}文字)")
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    try:
        prompt = config.AI_PROCESS_PROMPT_TEMPLATE.format(text=text)
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=1024, # 要約とJSONの両方を出力するためトークンを増やす
                temperature=0.2,
            )
        )
        
        # レスポンスからJSON部分を抽出
        response_text = response.text.strip()
        # ```json ... ``` または ``` ... ``` ブロックを探す正規表現
        match = re.search(r"```(json)?\s*({.*?})\s*```", response_text, re.DOTALL)
        if match:
            json_str = match.group(2)
        else:
            # フォールバックとして、最も内側にあるJSONオブジェクトを探す
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end != 0:
                json_str = response_text[json_start:json_end]
            else:
                logging.warning(f"AI要約: レスポンスにJSONが含まれていません。レスポンス: {response_text[:100]}...")
                return None
        
        # JSONをパース
        result: Dict[str, Any] = json.loads(json_str)
        
        # 結果の検証
        summary: Optional[str] = result.get("summary")
        region: Optional[str] = result.get("region")
        category: Optional[str] = result.get("category")
        
        if not summary:
             logging.warning(f"AI要約: 要約テキストが取得できませんでした。受信データ: {result}")
             return None

        # 要約の文字数チェック（180-220字の範囲を推奨）
        if len(summary) < 150 or len(summary) > 250:
            logging.warning(f"要約文字数が推奨範囲外です: {len(summary)}字")

        return {
            "summary": summary,
            "region": region if region else "その他",
            "category": category if category else "その他",
            "keywords": []  # 互換性のため空配列を維持
        }
        
    except json.JSONDecodeError as e:
        logging.warning(f"AI要約: JSONパース失敗。{str(e)[:50]}")
        return None
    except Exception as e:
        logging.warning(f"AI要約処理エラー: {str(e)[:50]}")
        return None

if __name__ == '__main__':
    # .envファイルから環境変数を読み込む
    from dotenv import load_dotenv
    load_dotenv()
    
    test_api_key = os.getenv("GEMINI_API_KEY")
    if not test_api_key:
        raise ValueError("環境変数 'GEMINI_API_KEY' が設定されていません。")

    test_text = """
    米連邦準備制度理事会（FRB）は26日、連邦公開市場委員会（FOMC）で政策金利を据え置くことを決定した。
    これは市場の予想通りであり、インフレ抑制と経済成長のバランスを慎重に見極める姿勢を示している。
    パウエル議長は記者会見で、今後の金融政策について「データ次第」と繰り返し述べ、
    利下げの時期については具体的な言及を避けた。
    市場では、早ければ9月にも利下げが開始されるとの見方が強まっているが、
    FRBは依然として高止まりするインフレ率を警戒している。
    """
    
    print("--- 統合AI処理テスト ---")
    ai_result = process_article_with_ai(test_api_key, test_text)
    
    if ai_result:
        print(f"要約: {ai_result['summary']}")
        print(f"地域: {ai_result['region']}")
        print(f"カテゴリ: {ai_result['category']}")
        print(f"要約文字数: {len(ai_result['summary'])}字")
    else:
        print("テストに失敗しました。")
