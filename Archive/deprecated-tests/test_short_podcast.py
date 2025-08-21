#!/usr/bin/env python3
"""
短縮版ポッドキャストテストスクリプト
30秒〜1分程度の短いポッドキャストを生成してテスト
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.podcast.tts.gemini_tts_engine import GeminiTTSEngine
except ImportError as e:
    print(f"Import error: {e}")
    print("Required dependencies may be missing. Please install: pip install google-cloud-texttospeech")
    sys.exit(1)

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)

def generate_short_script():
    """短縮版台本を生成"""
    return """
こんにちは、マーケットニュースポッドキャストへようこそ。
今日は{date}です。

本日の主要なマーケット情報をお伝えします。

まず、日本株市場では、日経平均株価が前日比で小幅に上昇しました。
テクノロジー関連株が買われる一方、金融株には売り圧力が見られました。

次に、為替市場では、ドル円相場が安定した動きを見せています。
アメリカの経済指標の発表を控え、様子見の展開が続いています。

最後に、注目の材料として、来週発表予定の日本のGDP速報値に市場の関心が集まっています。

以上、本日のマーケットニュースをお伝えしました。
また明日お会いしましょう。ありがとうございました。
""".format(date=datetime.now().strftime("%Y年%m月%d日")).strip()

def test_short_podcast_generation():
    """短縮版ポッドキャスト生成テスト"""
    logger = setup_logging()
    logger.info("=== 短縮版ポッドキャスト生成テスト ===")
    
    try:
        # 環境変数から認証情報を取得
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if not credentials_json:
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not credentials_path:
                logger.error("認証情報が設定されていません")
                return False
            credentials_json = credentials_path
        
        # TTSエンジンを初期化
        logger.info("TTSエンジンを初期化中...")
        tts_engine = GeminiTTSEngine(credentials_json=credentials_json)
        
        # 短縮版台本を生成
        script = generate_short_script()
        logger.info(f"台本生成完了 ({len(script)}文字)")
        logger.info(f"台本内容:\n{script[:200]}...")
        
        # 音声合成実行
        logger.info("音声合成を開始...")
        start_time = datetime.now()
        
        output_path = Path(f"short_podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")
        audio_data = tts_engine.synthesize_dialogue(script, output_path)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        if audio_data and len(audio_data) > 0:
            logger.info(f"✅ 音声合成成功!")
            logger.info(f"   ファイルサイズ: {len(audio_data):,}バイト ({len(audio_data)/1024:.1f}KB)")
            logger.info(f"   出力ファイル: {output_path}")
            logger.info(f"   処理時間: {processing_time:.1f}秒")
            
            # 推定再生時間（平均的な音声ビットレート基準）
            estimated_duration = len(audio_data) / (128 * 1024 / 8)  # 128kbps想定
            logger.info(f"   推定再生時間: {estimated_duration:.1f}秒")
            
            return True
        else:
            logger.error("❌ 音声データが生成されませんでした")
            return False
            
    except Exception as e:
        logger.error(f"❌ テスト失敗: {e}")
        return False

def main():
    """メイン処理"""
    success = test_short_podcast_generation()
    
    if success:
        print("\n🎉 短縮版ポッドキャスト生成テスト成功!")
        print("GitHub Actionsでのテスト実行準備が整いました。")
        return 0
    else:
        print("\n❌ 短縮版ポッドキャスト生成テスト失敗")
        print("設定を確認してください。")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)