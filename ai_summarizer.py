# -*- coding: utf-8 -*

import google.generativeai as genai
import os

def summarize_text(api_key: str, text: str, max_length: int = 200) -> str:
    """
    Gemini APIを使用してテキストを要約します。
    
    Args:
        api_key (str): Google Gemini APIキー。
        text (str): 要約する元のテキスト。
        max_length (int): 要約の最大文字数（目安）。
        
    Returns:
        str: 要約されたテキスト、またはエラーメッセージ。
    """
    if not api_key:
        return "エラー: Gemini APIキーが設定されていません。"
    
    genai.configure(api_key=api_key)
    
    # 使用するモデルを設定
    # 'gemini-2.0-flash-lite-001' に変更
    model = genai.GenerativeModel('gemini-2.0-flash-lite-001')
    
    try:
        # プロンプトを工夫して、要約の品質と長さを制御します。
        prompt = f"""あなたは優秀なニュース編集者です。
以下の記事を、最も重要なポイントを抽出し、日本語で{max_length}字以内にまとめてください。
要約は必ず一つの段落とし、自然で完結した文章にしてください。文末は必ず句点（。）で終えてください。

---記事---
{text}
---要約---
"""
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                # 生成するテキストの最大トークン数を設定
                max_output_tokens=512,
                # 生成の多様性を設定 (0.0で最も決定論的になる)
                temperature=0.7,
            )
        )
        
        # レスポンスからテキストを抽出
        summary = response.text.strip()
            
        return summary
        
    except Exception as e:
        return f"要約中にエラーが発生しました: {e}"

if __name__ == '__main__':
    # テスト用のコード
    # .envファイルにGEMINI_API_KEYを設定してから実行してください
    from dotenv import load_dotenv
    load_dotenv()
    
    test_api_key = os.getenv("GEMINI_API_KEY")
    test_text = """
    米連邦準備制度理事会（FRB）は26日、連邦公開市場委員会（FOMC）で政策金利を据え置くことを決定した。
    これは市場の予想通りであり、インフレ抑制と経済成長のバランスを慎重に見極める姿勢を示している。
    パウエル議長は記者会見で、今後の金融政策について「データ次第」と繰り返し述べ、
    利下げの時期については具体的な言及を避けた。
    市場では、早ければ9月にも利下げが開始されるとの見方が強まっているが、
    FRBは依然として高止まりするインフレ率を警戒している。
    """
    
    print("--- テスト要約 ---")
    summary = summarize_text(test_api_key, test_text)
    print(summary)
    print(f"文字数: {len(summary)}")
