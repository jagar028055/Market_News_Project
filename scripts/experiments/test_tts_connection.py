#!/usr/bin/env python3
"""
Google Cloud TTS 接続テストスクリプト
基本的な認証・API呼び出しをテスト
"""

import os
import sys
import logging
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.podcast.tts.gemini_tts_engine import GeminiTTSEngine
except ImportError as e:
    print(f"Import error: {e}")
    print("Required dependencies may be missing. Please install: pip install google-cloud-texttospeech")
    print("また、src/podcast/tts/gemini_tts_engine.py が存在することを確認してください")
    sys.exit(1)

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)

def test_tts_connection():
    """TTS接続テスト"""
    logger = setup_logging()
    logger.info("=== Google Cloud TTS Connection Test ===")
    
    try:
        # 環境変数から認証情報を取得
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if not credentials_json:
            # ファイルパス指定の場合
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not credentials_path:
                logger.error("認証情報が設定されていません")
                logger.info("環境変数を設定してください:")
                logger.info("  GOOGLE_APPLICATION_CREDENTIALS_JSON='{...}' または")
                logger.info("  GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json")
                return False
            credentials_json = credentials_path
        
        # TTSエンジンを初期化
        logger.info("TTSエンジンを初期化中...")
        tts_engine = GeminiTTSEngine(credentials_json=credentials_json)
        
        # 短いテストテキストで音声合成
        test_text = "こんにちは。Google Cloud Text-to-Speech のテストです。"
        logger.info(f"テスト音声合成実行: '{test_text}'")
        
        audio_data = tts_engine.synthesize_dialogue(test_text)
        
        if audio_data and len(audio_data) > 0:
            # テスト音声ファイルを保存
            output_path = Path("test_output.mp3")
            with open(output_path, 'wb') as f:
                f.write(audio_data)
            
            logger.info(f"✅ 音声合成成功!")
            logger.info(f"   ファイルサイズ: {len(audio_data)}バイト")
            logger.info(f"   出力ファイル: {output_path}")
            return True
        else:
            logger.error("❌ 音声データが生成されませんでした")
            return False
            
    except Exception as e:
        logger.error(f"❌ テスト失敗: {e}")
        return False

def main():
    """メイン処理"""
    success = test_tts_connection()
    
    if success:
        print("\n🎉 Google Cloud TTS接続テスト成功!")
        print("ポッドキャスト機能の実装準備が整いました。")
        return 0
    else:
        print("\n❌ Google Cloud TTS接続テスト失敗")
        print("認証設定や依存関係を確認してください。")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)