# -*- coding: utf-8 -*-

import google.generativeai as genai
import os
import json
from typing import Optional, Dict, Any
import logging

# プロジェクトモジュール
import market_news_config as config

def process_article_with_ai(api_key: str, text: str) -> Optional[Dict[str, Any]]:
    """
    Gemini APIを使用して、記事の要約と感情分析を一度に実行します。
    
    Args:
        api_key (str): Google Gemini APIキー。
        text (str): 分析する元の記事本文。
        
    Returns:
        Optional[Dict[str, Any]]: 要約と感情分析結果を含む辞書、またはエラーの場合はNone。
                                  例: {'summary': '...', 'sentiment_label': '...', 'sentiment_score': 0.9}
    """
    if not api_key:
        logging.error("エラー: Gemini APIキーが設定されていません。")
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-lite-001')

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
        response_text: str = response.text.strip()
        json_start: int = response_text.find('{')
        json_end: int = response_text.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            logging.error(f"エラー: レスポンスに有効なJSONが含まれていません。レスポンス: {response_text}")
            return None
            
        json_str: str = response_text[json_start:json_end]
        
        # JSONをパース
        result: Dict[str, Any] = json.loads(json_str)
        
        # 結果の検証
        summary: Optional[str] = result.get("summary")
        label: Optional[str] = result.get("sentiment_label")
        score: float = float(result.get("sentiment_score", 0.0))
        
        if not summary or not label or label not in ["Positive", "Negative", "Neutral"]:
             logging.error(f"エラー: AIからのレスポンス形式が不正です。受信データ: {result}")
             return None

        return {
            "summary": summary,
            "sentiment_label": label,
            "sentiment_score": score
        }
        
    except json.JSONDecodeError as e:
        logging.error(f"AI応答のJSONパースに失敗しました: {e}\nレスポンス: {response_text}")
        return None
    except Exception as e:
        logging.error(f"AI処理中に予期せぬエラーが発生しました: {e}")
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
        print(f"感情: {ai_result['sentiment_label']} (スコア: {ai_result['sentiment_score']})")
    else:
        print("テストに失敗しました。")
