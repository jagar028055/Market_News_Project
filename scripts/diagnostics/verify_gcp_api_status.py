#!/usr/bin/env python3
"""
Google Cloud Text-to-Speech API 状況確認スクリプト
API有効化前後の状況を詳細に診断
"""

import os
import sys
import logging
import json
import tempfile
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

def setup_credentials():
    """認証情報を設定"""
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if not credentials_json:
        return None, "GOOGLE_APPLICATION_CREDENTIALS_JSON 環境変数が設定されていません"
    
    try:
        if credentials_json.startswith('{'):
            # JSON文字列の場合、一時ファイルに保存
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(credentials_json)
                temp_file = f.name
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file
            return json.loads(credentials_json), None
        else:
            # ファイルパスの場合
            with open(credentials_json, 'r') as f:
                return json.load(f), None
    except Exception as e:
        return None, f"認証情報の読み込みに失敗: {e}"

def test_basic_auth():
    """基本認証テスト"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.auth import default
        from google.auth.transport.requests import Request
        
        # デフォルト認証情報を取得
        credentials, project_id = default()
        logger.info(f"✅ 基本認証成功:")
        logger.info(f"   プロジェクトID: {project_id}")
        logger.info(f"   認証情報タイプ: {type(credentials).__name__}")
        
        # 認証情報の有効性を確認
        if hasattr(credentials, 'refresh'):
            request = Request()
            credentials.refresh(request)
            logger.info("✅ 認証情報の更新に成功")
        
        return True, project_id, None
        
    except Exception as e:
        logger.error(f"❌ 基本認証失敗: {e}")
        return False, None, str(e)

def test_tts_client_initialization():
    """TTS クライアント初期化テスト"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import texttospeech
        
        client = texttospeech.TextToSpeechClient()
        logger.info("✅ Text-to-Speech クライアント初期化成功")
        return True, client, None
        
    except Exception as e:
        logger.error(f"❌ TTS クライアント初期化失敗: {e}")
        return False, None, str(e)

def test_api_operations(client):
    """API操作テスト"""
    logger = logging.getLogger(__name__)
    
    # テスト1: 音声リスト取得
    try:
        logger.info("🔍 テスト1: 利用可能音声リスト取得...")
        voices = client.list_voices()
        
        japanese_voices = [v for v in voices.voices if v.language_codes and any('ja' in lang for lang in v.language_codes)]
        logger.info(f"✅ 音声リスト取得成功: 日本語音声 {len(japanese_voices)}個")
        
        # 利用可能な日本語音声の詳細表示
        if japanese_voices:
            logger.info("   利用可能な日本語音声:")
            for voice in japanese_voices[:8]:  # 最初の8つを表示
                gender = voice.ssml_gender.name if voice.ssml_gender else "UNKNOWN"
                logger.info(f"     - {voice.name} ({gender})")
        
        list_voices_success = True
        voice_count = len(japanese_voices)
        
    except Exception as e:
        logger.error(f"❌ 音声リスト取得失敗: {e}")
        list_voices_success = False
        voice_count = 0
    
    # テスト2: 短いテキストの音声合成
    synthesis_success = False
    audio_size = 0
    
    if list_voices_success:
        try:
            logger.info("🔍 テスト2: 音声合成テスト...")
            
            # 合成リクエストを作成
            synthesis_input = texttospeech.SynthesisInput(text="テストです。")
            voice = texttospeech.VoiceSelectionParams(
                language_code="ja-JP",
                name="ja-JP-Neural2-D"  # 高品質な女性音声
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                sample_rate_hertz=44100
            )
            
            # 音声合成実行
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            audio_size = len(response.audio_content)
            logger.info(f"✅ 音声合成成功: {audio_size}バイト生成")
            
            # テスト音声ファイルを保存
            test_file = Path("api_test_output.mp3")
            with open(test_file, 'wb') as f:
                f.write(response.audio_content)
            logger.info(f"   テスト音声保存: {test_file}")
            
            synthesis_success = True
            
        except Exception as e:
            logger.error(f"❌ 音声合成失敗: {e}")
            # 403エラーの詳細解析
            if "403" in str(e) and "SERVICE_DISABLED" in str(e):
                logger.error("   → Text-to-Speech APIが無効化されています")
                logger.error("   → APIを有効化してください:")
                logger.error("     https://console.developers.google.com/apis/api/texttospeech.googleapis.com/overview")
            elif "403" in str(e):
                logger.error("   → 権限不足の可能性があります")
                logger.error("   → サービスアカウントに 'Cloud Text-to-Speech User' 権限を付与してください")
    
    return {
        'list_voices_success': list_voices_success,
        'voice_count': voice_count,
        'synthesis_success': synthesis_success,
        'audio_size': audio_size
    }

def generate_status_report(credentials_info, auth_result, api_results):
    """状況レポートを生成"""
    logger = logging.getLogger(__name__)
    
    report = {
        'timestamp': str(Path(__file__).parent / 'api_status_check.json'),
        'credentials_info': {
            'project_id': credentials_info.get('project_id') if credentials_info else None,
            'service_account': credentials_info.get('client_email') if credentials_info else None,
            'has_credentials': credentials_info is not None
        },
        'auth_status': {
            'basic_auth_success': auth_result[0],
            'detected_project_id': auth_result[1],
            'auth_error': auth_result[2]
        },
        'api_status': api_results,
        'overall_status': 'READY' if (auth_result[0] and api_results.get('synthesis_success', False)) else 'NEEDS_SETUP'
    }
    
    return report

def print_summary_and_recommendations(report):
    """サマリーと推奨事項を表示"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("🎯 診断サマリーと推奨事項")
    logger.info("=" * 60)
    
    status = report['overall_status']
    creds = report['credentials_info']
    auth = report['auth_status']
    api = report['api_status']
    
    if status == 'READY':
        logger.info("🎉 Google Cloud Text-to-Speech API は正常に動作します！")
        logger.info(f"   プロジェクト: {auth['detected_project_id']}")
        logger.info(f"   サービスアカウント: {creds['service_account']}")
        logger.info(f"   利用可能音声数: {api['voice_count']}個")
        logger.info("")
        logger.info("📋 次のステップ:")
        logger.info("   1. GitHub Actions でテスト実行")
        logger.info("   2. 本格的なポッドキャスト生成テスト")
        logger.info("   3. LINE Bot 配信機能の統合テスト")
        
    else:
        logger.info("⚠️  セットアップが必要です")
        logger.info("")
        logger.info("📋 必要な対応:")
        
        if not creds['has_credentials']:
            logger.info("   ❌ 認証情報が設定されていません")
            logger.info("      → GOOGLE_APPLICATION_CREDENTIALS_JSON 環境変数を設定")
            
        elif not auth['basic_auth_success']:
            logger.info("   ❌ Google Cloud 認証に失敗")
            logger.info("      → サービスアカウントの有効性を確認")
            logger.info("      → 認証情報の再生成を検討")
            
        elif not api['synthesis_success']:
            project_id = auth['detected_project_id']
            logger.info("   ❌ Text-to-Speech API が利用できません")
            logger.info(f"      → プロジェクト {project_id} で API を有効化:")
            logger.info(f"        https://console.developers.google.com/apis/api/texttospeech.googleapis.com/overview?project={project_id}")
            logger.info("      → サービスアカウントに 'Cloud Text-to-Speech User' 権限を付与")

def main():
    """メイン処理"""
    logger = setup_logging()
    logger.info("🔍 Google Cloud Text-to-Speech API 状況確認開始")
    
    # 認証情報設定
    credentials_info, creds_error = setup_credentials()
    if creds_error:
        logger.error(f"❌ {creds_error}")
        return 1
    
    # 基本認証テスト
    auth_result = test_basic_auth()
    if not auth_result[0]:
        report = generate_status_report(credentials_info, auth_result, {})
        print_summary_and_recommendations(report)
        return 1
    
    # TTSクライアント初期化テスト
    client_success, client, client_error = test_tts_client_initialization()
    if not client_success:
        logger.error(f"クライアント初期化エラー: {client_error}")
        return 1
    
    # API操作テスト
    api_results = test_api_operations(client)
    
    # レポート生成と表示
    report = generate_status_report(credentials_info, auth_result, api_results)
    
    # レポートをJSONファイルに保存
    report_file = Path("gcp_api_status_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"📄 詳細レポートを保存: {report_file}")
    
    print_summary_and_recommendations(report)
    
    return 0 if report['overall_status'] == 'READY' else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)