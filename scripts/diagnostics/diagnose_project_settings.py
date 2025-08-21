#!/usr/bin/env python3
"""
Google Cloud プロジェクト設定詳細診断スクリプト
請求・クォータ・API制限設定の確認
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

def setup_credentials():
    """認証情報設定"""
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if not credentials_json:
        return None, "GOOGLE_APPLICATION_CREDENTIALS_JSON 環境変数が設定されていません"
    
    try:
        if credentials_json.startswith('{'):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(credentials_json)
                temp_file = f.name
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file
            return json.loads(credentials_json), None
        else:
            with open(credentials_json, 'r') as f:
                return json.load(f), None
    except Exception as e:
        return None, f"認証情報処理エラー: {e}"

def test_service_usage_api(credentials, project_id):
    """Service Usage API テスト（API有効化状況確認）"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import service_usage_v1
        
        logger.info("🔍 API有効化状況確認...")
        
        client = service_usage_v1.ServiceUsageClient(credentials=credentials)
        parent = f"projects/{project_id}"
        
        # 有効化されたサービス一覧を取得
        services = client.list_services(
            request={"parent": parent, "filter": "state:ENABLED"}
        )
        
        enabled_services = []
        tts_enabled = False
        
        for service in services:
            service_name = service.config.name
            enabled_services.append(service_name)
            if 'texttospeech' in service_name:
                tts_enabled = True
                logger.info(f"✅ Text-to-Speech API有効: {service_name}")
        
        logger.info(f"✅ 有効化されたAPI総数: {len(enabled_services)}個")
        
        # 重要なAPIの確認
        important_apis = [
            'texttospeech.googleapis.com',
            'iam.googleapis.com',
            'iamcredentials.googleapis.com',
            'serviceusage.googleapis.com'
        ]
        
        for api in important_apis:
            if any(api in service for service in enabled_services):
                logger.info(f"✅ {api}: 有効")
            else:
                logger.warning(f"⚠️  {api}: 無効または未確認")
        
        return True, {
            'tts_api_enabled': tts_enabled,
            'total_enabled_services': len(enabled_services),
            'enabled_services': enabled_services[:10]  # 最初の10個のみ記録
        }
        
    except Exception as e:
        logger.error(f"❌ Service Usage API アクセス失敗: {e}")
        return False, {'error': str(e)}

def test_cloud_billing_api(credentials, project_id):
    """Cloud Billing API テスト（請求設定確認）"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import billing_v1
        
        logger.info("🔍 請求設定確認...")
        
        client = billing_v1.CloudBillingClient(credentials=credentials)
        project_name = f"projects/{project_id}"
        
        # プロジェクトの請求情報を取得
        billing_info = client.get_project_billing_info(name=project_name)
        
        billing_enabled = billing_info.billing_enabled
        billing_account_name = billing_info.billing_account_name if billing_info.billing_account_name else "未設定"
        
        if billing_enabled:
            logger.info(f"✅ 請求設定: 有効")
            logger.info(f"   請求アカウント: {billing_account_name}")
        else:
            logger.warning("⚠️  請求設定: 無効")
            logger.warning("   → 請求を有効化しないとText-to-Speech APIが使用できません")
        
        return True, {
            'billing_enabled': billing_enabled,
            'billing_account': billing_account_name
        }
        
    except Exception as e:
        logger.warning(f"⚠️  Cloud Billing API アクセス失敗: {e}")
        logger.info("   → 請求情報の確認権限が不足している可能性があります")
        return False, {'error': str(e)}

def test_monitoring_api_quotas(credentials, project_id):
    """Monitoring API テスト（クォータ・使用量確認）"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import monitoring_v3
        
        logger.info("🔍 API使用量・クォータ確認...")
        
        client = monitoring_v3.MetricServiceClient(credentials=credentials)
        project_name = f"projects/{project_id}"
        
        # 過去24時間のTTS API使用量を取得
        from google.cloud.monitoring_v3 import query
        import datetime
        
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(hours=24)
        
        # メトリックフィルター（TTS API呼び出し回数）
        filter_str = 'metric.type="serviceruntime.googleapis.com/api/request_count" AND resource.label.service="texttospeech.googleapis.com"'
        
        interval = monitoring_v3.TimeInterval({
            "end_time": {"seconds": int(end_time.timestamp())},
            "start_time": {"seconds": int(start_time.timestamp())},
        })
        
        request = monitoring_v3.ListTimeSeriesRequest({
            "name": project_name,
            "filter": filter_str,
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        })
        
        results = client.list_time_series(request=request)
        
        total_requests = 0
        error_requests = 0
        
        for result in results:
            for point in result.points:
                if hasattr(point.value, 'int64_value'):
                    total_requests += point.value.int64_value
                
                # エラーレスポンスのチェック
                if (hasattr(result.metric, 'labels') and 
                    result.metric.labels.get('response_code', '').startswith('4')):
                    error_requests += point.value.int64_value
        
        logger.info(f"✅ 過去24時間のTTS API使用量:")
        logger.info(f"   総リクエスト数: {total_requests}")
        logger.info(f"   エラーレスポンス: {error_requests}")
        
        if error_requests > 0:
            error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0
            logger.warning(f"⚠️  エラー率: {error_rate:.1f}%")
        
        return True, {
            'total_requests_24h': total_requests,
            'error_requests_24h': error_requests,
            'error_rate': (error_requests / total_requests * 100) if total_requests > 0 else 0
        }
        
    except Exception as e:
        logger.warning(f"⚠️  Monitoring API アクセス失敗: {e}")
        logger.info("   → 使用量データの確認権限が不足している可能性があります")
        return False, {'error': str(e)}

def test_simple_tts_api_call(credentials):
    """シンプルなTTS API呼び出しテスト"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import texttospeech
        import time
        
        logger.info("🔍 実際のTTS API呼び出しテスト...")
        
        client = texttospeech.TextToSpeechClient(credentials=credentials)
        
        # 最小限のリクエストでテスト
        synthesis_input = texttospeech.SynthesisInput(text="テスト")
        voice = texttospeech.VoiceSelectionParams(
            language_code="ja-JP",
            name="ja-JP-Neural2-D"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        start_time = time.time()
        
        try:
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # ミリ秒
            audio_size = len(response.audio_content)
            
            logger.info(f"✅ TTS API呼び出し成功:")
            logger.info(f"   応答時間: {response_time:.0f}ms")
            logger.info(f"   音声データサイズ: {audio_size}バイト")
            
            # テスト音声保存
            test_file = Path("project_settings_test_output.mp3")
            with open(test_file, 'wb') as f:
                f.write(response.audio_content)
            logger.info(f"   テスト音声保存: {test_file}")
            
            return True, {
                'success': True,
                'response_time_ms': response_time,
                'audio_size': audio_size
            }
            
        except Exception as api_error:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            logger.error(f"❌ TTS API呼び出し失敗: {api_error}")
            
            # エラー詳細分析
            error_analysis = {
                'error_type': type(api_error).__name__,
                'error_message': str(api_error),
                'response_time_ms': response_time,
                'is_403_error': '403' in str(api_error),
                'is_quota_error': any(word in str(api_error).lower() for word in ['quota', 'limit', 'rate']),
                'is_billing_error': any(word in str(api_error).lower() for word in ['billing', 'payment', 'account']),
                'is_permission_error': any(word in str(api_error).lower() for word in ['permission', 'denied', 'unauthorized'])
            }
            
            # 具体的な指摘
            if error_analysis['is_billing_error']:
                logger.error("   → 請求設定の問題: プロジェクトで請求が有効化されていません")
            elif error_analysis['is_permission_error']:
                logger.error("   → 権限問題: サービスアカウントにTTS権限が付与されていません")
            elif error_analysis['is_quota_error']:
                logger.error("   → クォータ問題: API使用制限に達しています")
            elif error_analysis['is_403_error']:
                logger.error("   → アクセス禁止: 複数の原因が考えられます（権限・請求・API有効化）")
            
            return False, error_analysis
            
    except Exception as e:
        logger.error(f"❌ TTS クライアント初期化失敗: {e}")
        return False, {'client_error': str(e)}

def generate_project_settings_report(credentials_data, test_results):
    """プロジェクト設定診断レポートを生成"""
    project_id = credentials_data.get('project_id')
    service_account = credentials_data.get('client_email')
    
    report = {
        'timestamp': str(Path(__file__).parent / 'project_settings_diagnosis.json'),
        'project_info': {
            'project_id': project_id,
            'service_account': service_account
        },
        'test_results': test_results,
        'recommendations': []
    }
    
    # 推奨事項の生成
    if not test_results.get('tts_api_test', {}).get('success', False):
        api_error = test_results.get('tts_api_test', {})
        
        if api_error.get('is_billing_error'):
            report['recommendations'].append({
                'priority': 'HIGH',
                'category': 'billing',
                'action': 'プロジェクトで請求を有効化してください',
                'url': f"https://console.cloud.google.com/billing?project={project_id}"
            })
        
        if api_error.get('is_permission_error'):
            report['recommendations'].append({
                'priority': 'HIGH',
                'category': 'permissions',
                'action': f'サービスアカウント {service_account} にText-to-Speech User権限を付与',
                'url': f"https://console.cloud.google.com/iam-admin/iam?project={project_id}"
            })
        
        if api_error.get('is_quota_error'):
            report['recommendations'].append({
                'priority': 'MEDIUM',
                'category': 'quotas',
                'action': 'Text-to-Speech APIのクォータ制限を確認・調整',
                'url': f"https://console.cloud.google.com/apis/api/texttospeech.googleapis.com/quotas?project={project_id}"
            })
    
    return report

def print_project_settings_summary(report):
    """プロジェクト設定診断サマリーを表示"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 70)
    logger.info("🎯 プロジェクト設定診断サマリー")
    logger.info("=" * 70)
    
    project_id = report['project_info']['project_id']
    tts_test = report['test_results'].get('tts_api_test', {})
    
    if tts_test.get('success', False):
        logger.info("🎉 プロジェクト設定は正常です！")
        logger.info(f"   TTS API応答時間: {tts_test.get('response_time_ms', 0):.0f}ms")
        logger.info(f"   音声データサイズ: {tts_test.get('audio_size', 0)}バイト")
        logger.info("")
        logger.info("✅ 確認された正常設定:")
        
        if report['test_results'].get('service_usage', {}).get('tts_api_enabled'):
            logger.info("   - Text-to-Speech API: 有効")
        
        billing_info = report['test_results'].get('billing', {})
        if billing_info.get('billing_enabled'):
            logger.info("   - 請求設定: 有効")
        
    else:
        logger.info("❌ プロジェクト設定に問題があります")
        logger.info("")
        logger.info("📋 優先度別対応リスト:")
        
        for rec in sorted(report['recommendations'], key=lambda x: x['priority']):
            priority_icon = "🚨" if rec['priority'] == 'HIGH' else "⚠️"
            logger.info(f"   {priority_icon} {rec['action']}")
            logger.info(f"      👉 {rec['url']}")
    
    # 追加の診断情報
    logger.info("")
    logger.info("📊 診断詳細:")
    
    service_usage = report['test_results'].get('service_usage', {})
    if service_usage:
        logger.info(f"   有効API数: {service_usage.get('total_enabled_services', 0)}個")
    
    monitoring = report['test_results'].get('monitoring', {})
    if monitoring:
        logger.info(f"   24時間API使用量: {monitoring.get('total_requests_24h', 0)}回")
        if monitoring.get('error_requests_24h', 0) > 0:
            logger.info(f"   エラー率: {monitoring.get('error_rate', 0):.1f}%")

def main():
    """メイン処理"""
    logger = setup_logging()
    logger.info("🔍 プロジェクト設定詳細診断開始")
    
    # 認証情報設定
    credentials_data, error = setup_credentials()
    if error:
        logger.error(f"❌ {error}")
        return 1
    
    try:
        from google.auth import default
        credentials, project_id = default()
        logger.info(f"✅ 基本認証成功: プロジェクト {project_id}")
    except Exception as e:
        logger.error(f"❌ 基本認証失敗: {e}")
        return 1
    
    # 各種テスト実行
    test_results = {}
    
    # Service Usage API テスト
    success, result = test_service_usage_api(credentials, project_id)
    test_results['service_usage'] = result
    
    # Cloud Billing API テスト  
    success, result = test_cloud_billing_api(credentials, project_id)
    test_results['billing'] = result
    
    # Monitoring API テスト
    success, result = test_monitoring_api_quotas(credentials, project_id)
    test_results['monitoring'] = result
    
    # 実際のTTS API呼び出しテスト
    success, result = test_simple_tts_api_call(credentials)
    test_results['tts_api_test'] = result
    
    # レポート生成・保存
    report = generate_project_settings_report(credentials_data, test_results)
    
    report_file = Path("project_settings_diagnosis.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"📄 診断レポート保存: {report_file}")
    
    # サマリー表示
    print_project_settings_summary(report)
    
    return 0 if test_results.get('tts_api_test', {}).get('success', False) else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)