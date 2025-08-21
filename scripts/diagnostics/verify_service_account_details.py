#!/usr/bin/env python3
"""
サービスアカウント詳細検証スクリプト
一意のID 113181736073894522460 を活用した包括的検証
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

def extract_and_analyze_credentials():
    """認証情報の抽出と詳細分析"""
    logger = logging.getLogger(__name__)
    
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if not credentials_json:
        logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS_JSON 環境変数が設定されていません")
        return None
    
    try:
        credentials_data = json.loads(credentials_json)
        
        logger.info("🔍 サービスアカウント詳細分析:")
        logger.info("=" * 50)
        
        # 基本情報
        project_id = credentials_data.get('project_id')
        client_email = credentials_data.get('client_email')
        client_id = credentials_data.get('client_id')
        private_key_id = credentials_data.get('private_key_id')
        auth_uri = credentials_data.get('auth_uri', 'N/A')
        token_uri = credentials_data.get('token_uri', 'N/A')
        
        logger.info(f"プロジェクトID: {project_id}")
        logger.info(f"サービスアカウント: {client_email}")
        logger.info(f"一意のID: {client_id}")
        logger.info(f"プライベートキーID: {private_key_id}")
        logger.info(f"認証URI: {auth_uri}")
        logger.info(f"トークンURI: {token_uri}")
        
        # プロジェクト名の分析
        if '@' in client_email:
            email_parts = client_email.split('@')
            account_name = email_parts[0]
            domain_parts = email_parts[1].split('.')
            
            logger.info("")
            logger.info("📧 メールアドレス分析:")
            logger.info(f"   アカウント名: {account_name}")
            logger.info(f"   ドメイン: {email_parts[1]}")
            
            if len(domain_parts) >= 2 and domain_parts[0] != project_id:
                logger.info(f"   プロジェクト表示名: {domain_parts[0]}")
                logger.info(f"   実際のプロジェクトID: {project_id}")
                logger.info("   → プロジェクト表示名と実IDが異なります")
        
        # 認証情報の整合性チェック
        integrity_check = {
            'has_project_id': bool(project_id),
            'has_client_email': bool(client_email),
            'has_client_id': bool(client_id),
            'has_private_key_id': bool(private_key_id),
            'has_private_key': bool(credentials_data.get('private_key')),
            'client_id_matches_expected': client_id == "113181736073894522460"
        }
        
        logger.info("")
        logger.info("🔒 認証情報整合性チェック:")
        for key, value in integrity_check.items():
            status = "✅" if value else "❌"
            logger.info(f"   {status} {key}: {value}")
        
        return credentials_data, integrity_check
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON解析エラー: {e}")
        return None, None
    except Exception as e:
        logger.error(f"❌ 認証情報分析エラー: {e}")
        return None, None

def test_service_account_identity(credentials_data):
    """サービスアカウントのアイデンティティ詳細テスト"""
    logger = logging.getLogger(__name__)
    
    try:
        # 認証情報を一時ファイルに設定
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(credentials_data, f)
            temp_file = f.name
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file
        
        from google.auth import default
        from google.auth.transport.requests import Request
        
        logger.info("🔍 サービスアカウントアイデンティティテスト:")
        
        # 認証情報取得
        credentials, project_id = default()
        
        logger.info(f"✅ 認証されたプロジェクトID: {project_id}")
        logger.info(f"   認証情報タイプ: {type(credentials).__name__}")
        
        # 認証情報の詳細プロパティを確認
        if hasattr(credentials, 'service_account_email'):
            logger.info(f"   サービスアカウントメール: {credentials.service_account_email}")
        
        if hasattr(credentials, 'project_id'):
            logger.info(f"   認証情報内プロジェクトID: {credentials.project_id}")
        
        # トークン情報の取得
        request = Request()
        credentials.refresh(request)
        
        if hasattr(credentials, 'token'):
            token_info = {
                'has_token': bool(credentials.token),
                'token_length': len(credentials.token) if credentials.token else 0,
                'expires': str(credentials.expiry) if hasattr(credentials, 'expiry') and credentials.expiry else 'N/A'
            }
            logger.info(f"✅ アクセストークン取得成功:")
            logger.info(f"   トークン長: {token_info['token_length']}文字")
            logger.info(f"   有効期限: {token_info['expires']}")
        
        # プロジェクトID一致確認
        expected_project_id = credentials_data.get('project_id')
        project_id_match = project_id == expected_project_id
        
        logger.info("")
        logger.info("🎯 プロジェクトID照合:")
        logger.info(f"   期待値: {expected_project_id}")
        logger.info(f"   実際値: {project_id}")
        logger.info(f"   一致: {'✅' if project_id_match else '❌'} {project_id_match}")
        
        # クリーンアップ
        try:
            os.unlink(temp_file)
        except:
            pass
        
        return True, {
            'authenticated_project_id': project_id,
            'project_id_match': project_id_match,
            'credentials_type': type(credentials).__name__,
            'has_valid_token': bool(credentials.token if hasattr(credentials, 'token') else False)
        }
        
    except Exception as e:
        logger.error(f"❌ サービスアカウントアイデンティティテスト失敗: {e}")
        return False, {'error': str(e)}

def test_iam_service_account_api(credentials, service_account_email, client_id):
    """IAM Service Account API を使ったサービスアカウント詳細確認"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import iam_admin_v1
        
        logger.info("🔍 IAM Service Account API 詳細確認:")
        
        client = iam_admin_v1.IAMClient(credentials=credentials)
        
        # サービスアカウントのリソース名を構築
        name = f"projects/-/serviceAccounts/{service_account_email}"
        
        # サービスアカウントの詳細情報を取得
        try:
            service_account = client.get_service_account(name=name)
            
            logger.info("✅ サービスアカウント詳細取得成功:")
            logger.info(f"   名前: {service_account.name}")
            logger.info(f"   メール: {service_account.email}")
            logger.info(f"   一意のID: {service_account.unique_id}")
            logger.info(f"   表示名: {service_account.display_name}")
            logger.info(f"   説明: {service_account.description}")
            logger.info(f"   無効化: {service_account.disabled}")
            
            # 一意のIDの照合
            unique_id_match = service_account.unique_id == client_id
            logger.info("")
            logger.info("🎯 一意のID照合:")
            logger.info(f"   期待値: {client_id}")
            logger.info(f"   実際値: {service_account.unique_id}")
            logger.info(f"   一致: {'✅' if unique_id_match else '❌'} {unique_id_match}")
            
            if service_account.disabled:
                logger.warning("⚠️  サービスアカウントが無効化されています！")
                logger.warning("   → これが403エラーの原因の可能性があります")
            
            return True, {
                'service_account_exists': True,
                'unique_id_match': unique_id_match,
                'is_disabled': service_account.disabled,
                'display_name': service_account.display_name,
                'description': service_account.description
            }
            
        except Exception as api_error:
            logger.error(f"❌ サービスアカウント詳細取得失敗: {api_error}")
            
            # エラー分析
            if '403' in str(api_error):
                logger.error("   → 権限不足: IAM Service Account Admin 権限が必要")
            elif '404' in str(api_error):
                logger.error("   → サービスアカウントが見つからない")
            
            return False, {'api_error': str(api_error)}
            
    except ImportError:
        logger.warning("⚠️  google-cloud-iam ライブラリがインストールされていません")
        return False, {'import_error': 'google-cloud-iam not installed'}
    except Exception as e:
        logger.error(f"❌ IAM API テスト失敗: {e}")
        return False, {'error': str(e)}

def generate_comprehensive_verification_report(credentials_data, integrity_check, identity_test, iam_test):
    """包括的検証レポートを生成"""
    
    report = {
        'timestamp': str(Path(__file__).parent / 'service_account_verification.json'),
        'service_account_info': {
            'project_id': credentials_data.get('project_id'),
            'client_email': credentials_data.get('client_email'),
            'client_id': credentials_data.get('client_id'),
            'private_key_id': credentials_data.get('private_key_id')
        },
        'integrity_check': integrity_check,
        'identity_verification': identity_test,
        'iam_verification': iam_test,
        'overall_status': 'UNKNOWN',
        'critical_issues': [],
        'recommendations': []
    }
    
    # 全体ステータスの判定
    if (integrity_check.get('client_id_matches_expected', False) and
        identity_test.get('project_id_match', False) and
        not iam_test.get('is_disabled', True)):
        report['overall_status'] = 'HEALTHY'
    elif iam_test.get('is_disabled', False):
        report['overall_status'] = 'DISABLED'
        report['critical_issues'].append('サービスアカウントが無効化されています')
    elif not identity_test.get('project_id_match', False):
        report['overall_status'] = 'PROJECT_MISMATCH'
        report['critical_issues'].append('プロジェクトIDが不一致です')
    else:
        report['overall_status'] = 'ISSUES_DETECTED'
    
    # 推奨事項の生成
    if report['overall_status'] == 'DISABLED':
        report['recommendations'].append({
            'priority': 'CRITICAL',
            'action': 'サービスアカウントを有効化',
            'description': 'Google Cloud Console でサービスアカウントを有効化してください'
        })
    
    if not identity_test.get('project_id_match', False):
        report['recommendations'].append({
            'priority': 'HIGH', 
            'action': 'プロジェクトID確認',
            'description': '認証情報のプロジェクトIDと実際のプロジェクトが一致しているか確認'
        })
    
    return report

def print_verification_summary(report):
    """検証サマリーを表示"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 70)
    logger.info("🎯 サービスアカウント検証サマリー")
    logger.info("=" * 70)
    
    status = report['overall_status']
    service_account = report['service_account_info']['client_email']
    client_id = report['service_account_info']['client_id']
    
    # ステータス表示
    if status == 'HEALTHY':
        logger.info("🎉 サービスアカウントは正常に動作します！")
        logger.info(f"   サービスアカウント: {service_account}")
        logger.info(f"   一意のID: {client_id}")
        logger.info("   → 403エラーの原因は他の設定にあります")
        
    elif status == 'DISABLED':
        logger.info("❌ サービスアカウントが無効化されています！")
        logger.info("   → これが403エラーの主要因です")
        
    elif status == 'PROJECT_MISMATCH':
        logger.info("⚠️  プロジェクトID不一致が検出されました")
        logger.info("   → 認証情報と実際のプロジェクトが異なります")
        
    else:
        logger.info("⚠️  複数の問題が検出されました")
    
    # 重大な問題の表示
    if report['critical_issues']:
        logger.info("")
        logger.info("🚨 重大な問題:")
        for issue in report['critical_issues']:
            logger.info(f"   - {issue}")
    
    # 推奨事項の表示
    if report['recommendations']:
        logger.info("")
        logger.info("📋 推奨対応:")
        for rec in sorted(report['recommendations'], key=lambda x: x['priority']):
            priority_icon = "🚨" if rec['priority'] == 'CRITICAL' else "⚠️" if rec['priority'] == 'HIGH' else "💡"
            logger.info(f"   {priority_icon} {rec['action']}")
            logger.info(f"      {rec['description']}")
    
    # 検証詳細
    logger.info("")
    logger.info("📊 検証詳細:")
    logger.info(f"   プロジェクトID一致: {'✅' if report['identity_verification'].get('project_id_match') else '❌'}")
    logger.info(f"   一意のID一致: {'✅' if report['integrity_check'].get('client_id_matches_expected') else '❌'}")
    
    iam_verification = report['iam_verification']
    if iam_verification and not iam_verification.get('error'):
        logger.info(f"   サービスアカウント状態: {'✅ 有効' if not iam_verification.get('is_disabled') else '❌ 無効'}")

def main():
    """メイン処理"""
    logger = setup_logging()
    logger.info("🔍 サービスアカウント詳細検証開始")
    
    # 認証情報の抽出と分析
    credentials_data, integrity_check = extract_and_analyze_credentials()
    if not credentials_data:
        return 1
    
    # サービスアカウントアイデンティティテスト
    identity_success, identity_result = test_service_account_identity(credentials_data)
    if not identity_success:
        return 1
    
    # IAM Service Account API テスト
    try:
        from google.auth import default
        credentials, _ = default()
    except Exception as e:
        logger.error(f"❌ 認証取得失敗: {e}")
        return 1
    
    iam_success, iam_result = test_iam_service_account_api(
        credentials, 
        credentials_data.get('client_email'),
        credentials_data.get('client_id')
    )
    
    # 包括的検証レポート生成
    report = generate_comprehensive_verification_report(
        credentials_data, integrity_check, identity_result, iam_result
    )
    
    # レポート保存
    report_file = Path("service_account_detailed_verification.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"📄 詳細検証レポート保存: {report_file}")
    
    # サマリー表示
    print_verification_summary(report)
    
    return 0 if report['overall_status'] == 'HEALTHY' else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)