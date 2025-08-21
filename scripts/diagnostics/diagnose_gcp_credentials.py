#!/usr/bin/env python3
"""
Google Cloud プロジェクト・サービスアカウント診断スクリプト
現在の認証情報が指すプロジェクトとサービスアカウントの状況を確認
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)

def get_credentials_info():
    """認証情報を取得・解析"""
    logger = logging.getLogger(__name__)
    
    # GitHub Secretsから認証情報を取得
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if not credentials_json:
        logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS_JSON 環境変数が設定されていません")
        return None
    
    try:
        # JSON文字列をパース
        credentials = json.loads(credentials_json)
        
        logger.info("🔍 認証情報解析結果:")
        logger.info(f"  プロジェクトID: {credentials.get('project_id', 'N/A')}")
        logger.info(f"  サービスアカウント: {credentials.get('client_email', 'N/A')}")
        logger.info(f"  サービスアカウントID: {credentials.get('client_id', 'N/A')}")
        logger.info(f"  認証タイプ: {credentials.get('type', 'N/A')}")
        
        return credentials
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ 認証情報JSONの解析に失敗: {e}")
        return None

def test_google_cloud_auth():
    """Google Cloud認証テスト"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import texttospeech
        from google.auth import default
        import google.auth.exceptions
        
        logger.info("🔐 Google Cloud認証テスト開始...")
        
        # 認証情報を設定
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if credentials_json and credentials_json.startswith('{'):
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(credentials_json)
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = f.name
        
        # デフォルト認証情報を取得
        credentials, project_id = default()
        logger.info(f"✅ 認証成功:")
        logger.info(f"  使用プロジェクトID: {project_id}")
        logger.info(f"  認証情報タイプ: {type(credentials).__name__}")
        
        # Text-to-Speech クライアント初期化テスト
        try:
            tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
            logger.info("✅ Text-to-Speech クライアント初期化成功")
            
            # 使用可能な音声一覧取得テスト（権限確認）
            try:
                voices = tts_client.list_voices()
                japanese_voices = [v for v in voices.voices if v.language_codes and 'ja-JP' in v.language_codes[0]]
                logger.info(f"✅ 音声一覧取得成功: 日本語音声 {len(japanese_voices)}個利用可能")
                
                # 利用可能な日本語音声を表示
                if japanese_voices:
                    logger.info("  利用可能な日本語音声:")
                    for voice in japanese_voices[:5]:  # 最初の5つを表示
                        logger.info(f"    - {voice.name} ({voice.ssml_gender.name})")
                
                return True, project_id, len(japanese_voices)
                
            except Exception as api_error:
                logger.error(f"❌ Text-to-Speech API呼び出しエラー: {api_error}")
                logger.error("   → Text-to-Speech APIが有効化されていない可能性があります")
                return False, project_id, 0
                
        except Exception as client_error:
            logger.error(f"❌ Text-to-Speech クライアント初期化失敗: {client_error}")
            return False, project_id, 0
            
    except ImportError as e:
        logger.error(f"❌ 必要なライブラリがインストールされていません: {e}")
        return False, None, 0
    except Exception as e:
        logger.error(f"❌ 認証テスト失敗: {e}")
        return False, None, 0

def get_project_diagnosis():
    """プロジェクト診断情報を取得"""
    logger = logging.getLogger(__name__)
    
    credentials = get_credentials_info()
    if not credentials:
        return None
    
    auth_success, actual_project_id, voice_count = test_google_cloud_auth()
    
    diagnosis = {
        'credentials_project_id': credentials.get('project_id'),
        'service_account_email': credentials.get('client_email'),
        'auth_successful': auth_success,
        'actual_project_id': actual_project_id,
        'tts_api_working': voice_count > 0,
        'available_voices': voice_count
    }
    
    return diagnosis

def print_recommendation(diagnosis: Dict[str, Any]):
    """診断結果に基づく推奨対応を表示"""
    logger = logging.getLogger(__name__)
    
    logger.info("🎯 診断結果と推奨対応:")
    
    if not diagnosis:
        logger.error("❌ 診断情報を取得できませんでした")
        return
    
    cred_project = diagnosis['credentials_project_id']
    actual_project = diagnosis['actual_project_id']
    service_account = diagnosis['service_account_email']
    
    if diagnosis['auth_successful'] and diagnosis['tts_api_working']:
        logger.info("✅ 設定完了: Google Cloud TTS が正常に動作します")
        logger.info(f"   プロジェクト: {actual_project}")
        logger.info(f"   サービスアカウント: {service_account}")
        logger.info(f"   利用可能音声: {diagnosis['available_voices']}個")
        
    elif diagnosis['auth_successful'] and not diagnosis['tts_api_working']:
        logger.warning("⚠️  認証成功、但しText-to-Speech APIが利用不可")
        logger.info("📋 必要な対応:")
        logger.info(f"   1. Google Cloud Console で プロジェクト '{actual_project}' に移動")
        logger.info("   2. 「APIとサービス」→「ライブラリ」→「Cloud Text-to-Speech API」を検索")
        logger.info("   3. APIを有効化")
        logger.info("   4. サービスアカウントに「Cloud Text-to-Speech User」権限を付与")
        
    else:
        logger.error("❌ 認証失敗")
        logger.info("📋 可能な原因と対応:")
        logger.info("   1. サービスアカウントが無効化されている")
        logger.info("   2. プロジェクトが削除・無効化されている") 
        logger.info("   3. 認証情報が破損している")
        logger.info("   → 新しいサービスアカウント・認証情報の作成が必要")

def main():
    """メイン処理"""
    logger = setup_logging()
    logger.info("🔍 Google Cloud プロジェクト・認証情報診断開始")
    
    diagnosis = get_project_diagnosis()
    print_recommendation(diagnosis)
    
    # 診断結果をJSONファイルに保存
    if diagnosis:
        output_file = Path("gcp_diagnosis_result.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(diagnosis, f, indent=2, ensure_ascii=False)
        logger.info(f"📄 診断結果を保存: {output_file}")
    
    return 0 if diagnosis and diagnosis.get('tts_api_working', False) else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)