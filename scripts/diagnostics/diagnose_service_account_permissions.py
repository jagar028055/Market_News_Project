#!/usr/bin/env python3
"""
Google Cloud サービスアカウント権限詳細診断スクリプト
API有効済み環境での403エラー原因特定用
"""

import os
import sys
import logging
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List

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

def setup_credentials_and_get_info():
    """認証情報を設定し、詳細情報を取得"""
    logger = logging.getLogger(__name__)
    
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if not credentials_json:
        logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS_JSON 環境変数が設定されていません")
        return None, None
    
    try:
        if credentials_json.startswith('{'):
            # JSON文字列をパースして詳細情報を取得
            credentials_data = json.loads(credentials_json)
            
            # 一時ファイルに保存して環境変数に設定
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(credentials_json)
                temp_file = f.name
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file
            
            logger.info("🔍 認証情報詳細:")
            logger.info(f"   プロジェクトID: {credentials_data.get('project_id')}")
            logger.info(f"   サービスアカウント: {credentials_data.get('client_email')}")
            logger.info(f"   一意のID: {credentials_data.get('client_id')}")
            logger.info(f"   キーID: {credentials_data.get('private_key_id', 'N/A')}")
            
            return credentials_data, temp_file
        else:
            # ファイルパスの場合
            with open(credentials_json, 'r') as f:
                credentials_data = json.load(f)
            return credentials_data, credentials_json
            
    except Exception as e:
        logger.error(f"❌ 認証情報処理エラー: {e}")
        return None, None

def test_google_cloud_access():
    """Google Cloud基本アクセステスト"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.auth import default
        from google.auth.transport.requests import Request
        
        logger.info("🔐 Google Cloud基本認証テスト...")
        
        # 認証情報取得
        credentials, project_id = default()
        logger.info(f"✅ 基本認証成功: プロジェクト {project_id}")
        
        # 認証情報更新テスト
        request = Request()
        credentials.refresh(request)
        logger.info("✅ 認証情報更新成功")
        
        return True, project_id, credentials
        
    except Exception as e:
        logger.error(f"❌ Google Cloud基本認証失敗: {e}")
        return False, None, None

def test_resource_manager_access(credentials, project_id):
    """Resource Manager API アクセステスト（プロジェクト詳細取得）"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import resourcemanager
        
        logger.info("🔍 プロジェクト詳細情報取得テスト...")
        
        client = resourcemanager.ProjectsClient(credentials=credentials)
        project_name = f"projects/{project_id}"
        project = client.get_project(name=project_name)
        
        logger.info("✅ プロジェクト情報取得成功:")
        logger.info(f"   プロジェクト表示名: {project.display_name}")
        logger.info(f"   プロジェクトID: {project.project_id}")
        logger.info(f"   状態: {project.state.name}")
        
        return True, {
            'display_name': project.display_name,
            'project_id': project.project_id,
            'state': project.state.name
        }
        
    except Exception as e:
        logger.warning(f"⚠️  プロジェクト詳細取得失敗: {e}")
        logger.info("   → Resource Manager API権限が不足している可能性")
        return False, None

def test_iam_access(credentials, project_id, service_account_email):
    """IAM API アクセステスト（サービスアカウント権限確認）"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import iam_credentials_v1
        
        logger.info("🔍 サービスアカウント権限テスト...")
        
        # IAM Credentials API クライアント
        client = iam_credentials_v1.IamCredentialsServiceClient(credentials=credentials)
        
        # サービスアカウントのリソース名を構築
        name = f"projects/-/serviceAccounts/{service_account_email}"
        
        # アクセストークン生成テスト（権限確認）
        request = iam_credentials_v1.GenerateAccessTokenRequest(
            name=name,
            scope=["https://www.googleapis.com/auth/cloud-platform"],
            include_email=True
        )
        
        response = client.generate_access_token(request=request)
        logger.info("✅ サービスアカウント権限テスト成功")
        logger.info(f"   アクセストークン生成: OK")
        logger.info(f"   有効期限: {response.expire_time}")
        
        return True, {
            'access_token_generation': True,
            'expire_time': str(response.expire_time)
        }
        
    except Exception as e:
        logger.warning(f"⚠️  サービスアカウント権限テスト失敗: {e}")
        return False, None

def test_tts_specific_permissions(credentials):
    """Text-to-Speech API 特有の権限テスト"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import texttospeech
        
        logger.info("🔍 Text-to-Speech API権限詳細テスト...")
        
        client = texttospeech.TextToSpeechClient(credentials=credentials)
        
        # テスト1: 音声一覧取得（読み取り権限）
        try:
            voices = client.list_voices()
            japanese_voices = [v for v in voices.voices if v.language_codes and any('ja' in lang for lang in v.language_codes)]
            logger.info(f"✅ 音声一覧取得成功: 日本語音声 {len(japanese_voices)}個")
            list_voices_ok = True
        except Exception as e:
            logger.error(f"❌ 音声一覧取得失敗: {e}")
            list_voices_ok = False
        
        # テスト2: 音声合成（実行権限）
        synthesis_ok = False
        error_details = None
        
        if list_voices_ok:
            try:
                logger.info("🔍 実際の音声合成権限テスト実行...")
                
                synthesis_input = texttospeech.SynthesisInput(text="権限テスト")
                voice = texttospeech.VoiceSelectionParams(
                    language_code="ja-JP",
                    name="ja-JP-Neural2-D"
                )
                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                    sample_rate_hertz=44100
                )
                
                response = client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config
                )
                
                audio_size = len(response.audio_content)
                logger.info(f"✅ 音声合成権限テスト成功: {audio_size}バイト生成")
                
                # テスト音声保存
                test_file = Path("permission_test_output.mp3")
                with open(test_file, 'wb') as f:
                    f.write(response.audio_content)
                logger.info(f"   テスト音声保存: {test_file}")
                
                synthesis_ok = True
                
            except Exception as e:
                logger.error(f"❌ 音声合成権限テスト失敗: {e}")
                error_details = {
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'is_permission_error': '403' in str(e) or 'permission' in str(e).lower(),
                    'is_quota_error': 'quota' in str(e).lower() or 'rate' in str(e).lower(),
                    'is_billing_error': 'billing' in str(e).lower() or 'payment' in str(e).lower()
                }
                
                # エラーの詳細分析
                if error_details['is_permission_error']:
                    logger.error("   → 権限エラー: サービスアカウントにText-to-Speech User権限が必要")
                elif error_details['is_quota_error']:
                    logger.error("   → クォータエラー: API使用制限に達している可能性")
                elif error_details['is_billing_error']:
                    logger.error("   → 請求エラー: プロジェクトで請求が有効化されていない")
                else:
                    logger.error("   → その他のエラー: 詳細な調査が必要")
        
        return {
            'list_voices_success': list_voices_ok,
            'synthesis_success': synthesis_ok,
            'error_details': error_details,
            'japanese_voice_count': len(japanese_voices) if list_voices_ok else 0
        }
        
    except Exception as e:
        logger.error(f"❌ Text-to-Speech クライアント初期化失敗: {e}")
        return {
            'client_initialization': False,
            'error': str(e)
        }

def generate_permission_diagnosis_report(credentials_data, tts_test_results):
    """権限診断レポートを生成"""
    logger = logging.getLogger(__name__)
    
    report = {
        'timestamp': str(Path(__file__).parent / 'permission_diagnosis_report.json'),
        'service_account_info': {
            'project_id': credentials_data.get('project_id'),
            'client_email': credentials_data.get('client_email'),
            'client_id': credentials_data.get('client_id'),
            'private_key_id': credentials_data.get('private_key_id')
        },
        'permission_test_results': tts_test_results,
        'diagnosis': {}
    }
    
    # 診断結果の判定
    if tts_test_results.get('synthesis_success', False):
        report['diagnosis']['status'] = 'WORKING'
        report['diagnosis']['message'] = 'すべての権限が正常に動作しています'
    elif tts_test_results.get('list_voices_success', False):
        report['diagnosis']['status'] = 'PARTIAL_PERMISSION'
        report['diagnosis']['message'] = '読み取り権限はあるが、実行権限が不足している可能性'
    else:
        report['diagnosis']['status'] = 'NO_PERMISSION'
        report['diagnosis']['message'] = '基本的なTTS権限が不足しています'
    
    return report

def print_detailed_recommendations(report):
    """詳細な推奨事項を表示"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 70)
    logger.info("🎯 権限診断結果と推奨対応")
    logger.info("=" * 70)
    
    diagnosis = report['diagnosis']['status']
    service_account = report['service_account_info']['client_email']
    project_id = report['service_account_info']['project_id']
    
    if diagnosis == 'WORKING':
        logger.info("🎉 権限設定は正常です！")
        logger.info("   Text-to-Speech APIが完全に動作します")
        logger.info("   → GitHub Actionsで403エラーが発生する原因は他にあります")
        logger.info("   → 一時的なAPI制限やネットワーク問題の可能性を調査してください")
        
    elif diagnosis == 'PARTIAL_PERMISSION':
        logger.info("⚠️  部分的な権限不足が検出されました")
        logger.info("📋 必要な対応:")
        logger.info(f"   1. Google Cloud Console IAM画面を開く:")
        logger.info(f"      https://console.cloud.google.com/iam-admin/iam?project={project_id}")
        logger.info(f"   2. サービスアカウント '{service_account}' を検索")
        logger.info(f"   3. 以下の権限を追加:")
        logger.info(f"      - Cloud Text-to-Speech User (roles/texttospeech.user)")
        logger.info(f"      - または Editor (roles/editor)")
        
    else:
        logger.info("❌ 重大な権限不足が検出されました")
        logger.info("📋 緊急対応が必要:")
        logger.info(f"   1. サービスアカウント '{service_account}' の存在確認")
        logger.info(f"   2. プロジェクト '{project_id}' でのアクセス権限確認") 
        logger.info(f"   3. 新しいサービスアカウントの作成を検討")
    
    # エラー詳細がある場合の追加情報
    error_details = report['permission_test_results'].get('error_details')
    if error_details:
        logger.info("")
        logger.info("🔍 エラー詳細分析:")
        logger.info(f"   エラータイプ: {error_details.get('error_type', 'Unknown')}")
        logger.info(f"   エラーメッセージ: {error_details.get('error_message', 'N/A')}")
        
        if error_details.get('is_billing_error'):
            logger.info("   💳 請求設定を確認してください:")
            logger.info(f"      https://console.cloud.google.com/billing?project={project_id}")
        elif error_details.get('is_quota_error'):
            logger.info("   📊 API使用量・制限を確認してください:")
            logger.info(f"      https://console.cloud.google.com/apis/api/texttospeech.googleapis.com/quotas?project={project_id}")

def main():
    """メイン処理"""
    logger = setup_logging()
    logger.info("🔍 サービスアカウント権限詳細診断開始")
    
    # 認証情報設定と詳細取得
    credentials_data, temp_file = setup_credentials_and_get_info()
    if not credentials_data:
        return 1
    
    # Google Cloud基本アクセステスト
    auth_success, project_id, credentials = test_google_cloud_access()
    if not auth_success:
        return 1
    
    # Text-to-Speech権限詳細テスト
    tts_results = test_tts_specific_permissions(credentials)
    
    # 診断レポート生成
    report = generate_permission_diagnosis_report(credentials_data, tts_results)
    
    # レポート保存
    report_file = Path("service_account_permission_diagnosis.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"📄 診断レポート保存: {report_file}")
    
    # 詳細推奨事項表示
    print_detailed_recommendations(report)
    
    # 一時ファイルクリーンアップ
    if temp_file and temp_file != credentials_data:
        try:
            os.unlink(temp_file)
        except:
            pass
    
    return 0 if tts_results.get('synthesis_success', False) else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)