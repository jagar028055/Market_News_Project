#!/usr/bin/env python3
"""
Google Cloud TTS 包括的診断ツール
API有効済み環境での403エラー完全診断
"""

import os
import sys
import logging
import json
import subprocess
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

def run_diagnostic_script(script_name, description):
    """診断スクリプトを実行"""
    logger = logging.getLogger(__name__)
    
    script_path = Path(__file__).parent / script_name
    if not script_path.exists():
        logger.warning(f"⚠️  {script_name} が見つかりません")
        return False, f"Script not found: {script_name}"
    
    try:
        logger.info(f"🔍 {description} 実行中...")
        
        # スクリプト実行
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5分タイムアウト
        )
        
        if result.returncode == 0:
            logger.info(f"✅ {description} 成功")
            return True, result.stdout
        else:
            logger.warning(f"⚠️  {description} で問題検出")
            return False, result.stderr or result.stdout
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {description} タイムアウト（5分超過）")
        return False, "Timeout after 5 minutes"
    except Exception as e:
        logger.error(f"❌ {description} 実行エラー: {e}")
        return False, str(e)

def analyze_github_actions_logs():
    """GitHub Actions ログ分析"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 GitHub Actions ログ分析...")
        
        # 最新のワークフロー実行ログを取得
        result = subprocess.run(
            ["gh", "run", "list", "--limit", "3", "--json", "conclusion,createdAt,displayTitle,databaseId"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.warning("⚠️  GitHub CLI アクセスに失敗")
            return None
        
        runs = json.loads(result.stdout)
        
        # TTS関連の実行を探す
        tts_runs = []
        for run in runs:
            if any(keyword in run.get('displayTitle', '').lower() for keyword in ['tts', 'podcast', 'broadcast']):
                tts_runs.append(run)
        
        if tts_runs:
            latest_run = tts_runs[0]
            run_id = latest_run['databaseId']
            
            logger.info(f"✅ 関連ワークフロー発見: {latest_run['displayTitle']}")
            logger.info(f"   実行ID: {run_id}")
            logger.info(f"   結果: {latest_run['conclusion']}")
            logger.info(f"   実行時刻: {latest_run['createdAt']}")
            
            # 詳細ログを取得して403エラーを検索
            log_result = subprocess.run(
                ["gh", "run", "view", str(run_id), "--log"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if log_result.returncode == 0:
                log_content = log_result.stdout
                
                # 403エラーパターンを検索
                error_patterns = [
                    '403',
                    'permission denied',
                    'access denied',
                    'forbidden',
                    'SERVICE_DISABLED',
                    'billing',
                    'quota'
                ]
                
                found_errors = []
                for pattern in error_patterns:
                    if pattern.lower() in log_content.lower():
                        # パターン周辺のコンテキストを取得
                        lines = log_content.split('\n')
                        for i, line in enumerate(lines):
                            if pattern.lower() in line.lower():
                                context_start = max(0, i-2)
                                context_end = min(len(lines), i+3)
                                context = '\n'.join(lines[context_start:context_end])
                                found_errors.append({
                                    'pattern': pattern,
                                    'context': context
                                })
                                break
                
                return {
                    'run_id': run_id,
                    'title': latest_run['displayTitle'],
                    'conclusion': latest_run['conclusion'],
                    'errors_found': found_errors,
                    'log_length': len(log_content)
                }
        
        logger.info("ℹ️  TTS関連のワークフロー実行が見つかりませんでした")
        return None
        
    except Exception as e:
        logger.warning(f"⚠️  GitHub Actions ログ分析エラー: {e}")
        return None

def test_different_tts_configurations():
    """異なるTTS設定でのテスト"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import texttospeech
        from google.auth import default
        
        logger.info("🔍 異なるTTS設定での動作テスト...")
        
        credentials, project_id = default()
        client = texttospeech.TextToSpeechClient(credentials=credentials)
        
        # テスト設定のバリエーション
        test_configs = [
            {
                'name': '最小設定',
                'input_text': 'テスト',
                'voice': {'language_code': 'ja-JP'},
                'audio_config': {'audio_encoding': texttospeech.AudioEncoding.MP3}
            },
            {
                'name': 'Standard音声',
                'input_text': 'スタンダード音声テスト',
                'voice': {'language_code': 'ja-JP', 'name': 'ja-JP-Standard-A'},
                'audio_config': {'audio_encoding': texttospeech.AudioEncoding.MP3}
            },
            {
                'name': 'Neural2音声',
                'input_text': 'ニューラル音声テスト',
                'voice': {'language_code': 'ja-JP', 'name': 'ja-JP-Neural2-D'},
                'audio_config': {'audio_encoding': texttospeech.AudioEncoding.MP3}
            },
            {
                'name': 'カスタム設定',
                'input_text': 'カスタム設定テスト',
                'voice': {'language_code': 'ja-JP', 'name': 'ja-JP-Neural2-D'},
                'audio_config': {
                    'audio_encoding': texttospeech.AudioEncoding.MP3,
                    'sample_rate_hertz': 44100,
                    'speaking_rate': 1.0,
                    'pitch': 0.0,
                    'volume_gain_db': 0.0
                }
            }
        ]
        
        results = []
        
        for i, config in enumerate(test_configs, 1):
            logger.info(f"   テスト {i}/{len(test_configs)}: {config['name']}")
            
            try:
                synthesis_input = texttospeech.SynthesisInput(text=config['input_text'])
                voice = texttospeech.VoiceSelectionParams(**config['voice'])
                audio_config = texttospeech.AudioConfig(**config['audio_config'])
                
                response = client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config
                )
                
                audio_size = len(response.audio_content)
                logger.info(f"     ✅ 成功: {audio_size}バイト")
                
                results.append({
                    'config_name': config['name'],
                    'success': True,
                    'audio_size': audio_size
                })
                
            except Exception as e:
                logger.error(f"     ❌ 失敗: {e}")
                results.append({
                    'config_name': config['name'],
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
        
        # 結果の分析
        success_count = sum(1 for r in results if r['success'])
        logger.info(f"✅ 設定テスト完了: {success_count}/{len(test_configs)} 成功")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ TTS設定テスト失敗: {e}")
        return [{'error': str(e)}]

def generate_comprehensive_diagnosis_report(diagnostic_results):
    """包括的診断レポートを生成"""
    logger = logging.getLogger(__name__)
    
    report = {
        'timestamp': str(Path(__file__).parent / 'comprehensive_tts_diagnosis.json'),
        'diagnostic_results': diagnostic_results,
        'summary': {
            'total_tests': len(diagnostic_results),
            'passed_tests': sum(1 for result in diagnostic_results.values() if result.get('success', False)),
            'critical_issues': [],
            'recommendations': []
        }
    }
    
    # 診断結果の分析
    permissions_result = diagnostic_results.get('permissions_diagnosis', {})
    project_result = diagnostic_results.get('project_settings_diagnosis', {})
    service_account_result = diagnostic_results.get('service_account_verification', {})
    config_test_result = diagnostic_results.get('configuration_tests', {})
    github_result = diagnostic_results.get('github_actions_analysis', {})
    
    # 重大な問題の特定
    if service_account_result.get('service_account_disabled', False):
        report['summary']['critical_issues'].append({
            'severity': 'CRITICAL',
            'issue': 'サービスアカウントが無効化されています',
            'impact': 'すべてのGoogle Cloud API呼び出しが失敗します',
            'action': 'Google Cloud Console でサービスアカウントを有効化'
        })
    
    if project_result.get('billing_disabled', False):
        report['summary']['critical_issues'].append({
            'severity': 'CRITICAL', 
            'issue': 'プロジェクトの請求が無効です',
            'impact': 'Text-to-Speech APIが利用できません',
            'action': 'プロジェクトで請求を有効化'
        })
    
    if permissions_result.get('tts_permission_missing', False):
        report['summary']['critical_issues'].append({
            'severity': 'HIGH',
            'issue': 'Text-to-Speech API使用権限が不足',
            'impact': '音声合成が実行できません',
            'action': 'サービスアカウントにCloud Text-to-Speech User権限を付与'
        })
    
    # GitHub Actions特有の問題
    if github_result.get('errors_found'):
        for error in github_result['errors_found']:
            if '403' in error.get('pattern', ''):
                report['summary']['critical_issues'].append({
                    'severity': 'HIGH',
                    'issue': 'GitHub Actions環境での403エラー',
                    'impact': 'ポッドキャスト自動生成が失敗',
                    'action': 'GitHub Actions環境変数と権限設定の確認'
                })
    
    # 推奨事項の生成
    if not report['summary']['critical_issues']:
        report['summary']['recommendations'].append({
            'priority': 'LOW',
            'action': '定期的な権限・設定の確認',
            'description': 'すべての設定が正常ですが、定期的な確認を推奨します'
        })
    else:
        report['summary']['recommendations'].append({
            'priority': 'HIGH',
            'action': '重大な問題の即座解決',
            'description': '特定された重大な問題を優先的に解決してください'
        })
    
    return report

def print_comprehensive_summary(report):
    """包括的診断サマリーを表示"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 80)
    logger.info("🎯 Google Cloud TTS 包括的診断結果")
    logger.info("=" * 80)
    
    summary = report['summary']
    total_tests = summary['total_tests']
    passed_tests = summary['passed_tests']
    critical_issues = summary['critical_issues']
    
    # 全体ステータス
    if not critical_issues:
        logger.info("🎉 診断完了: 重大な問題は検出されませんでした！")
        logger.info(f"   実行テスト: {passed_tests}/{total_tests} 成功")
        logger.info("   → 403エラーの原因は一時的な問題または環境固有の設定にある可能性があります")
    else:
        logger.info(f"❌ 診断完了: {len(critical_issues)}個の重大な問題を検出")
        logger.info(f"   実行テスト: {passed_tests}/{total_tests} 成功")
    
    # 重大な問題の詳細表示
    if critical_issues:
        logger.info("")
        logger.info("🚨 重大な問題:")
        for i, issue in enumerate(critical_issues, 1):
            severity_icon = "🚨" if issue['severity'] == 'CRITICAL' else "⚠️"
            logger.info(f"   {severity_icon} [{issue['severity']}] {issue['issue']}")
            logger.info(f"      影響: {issue['impact']}")
            logger.info(f"      対応: {issue['action']}")
    
    # 推奨事項
    logger.info("")
    logger.info("📋 次のステップ:")
    if critical_issues:
        logger.info("   1. 上記の重大な問題を優先的に解決")
        logger.info("   2. 解決後、このツールを再実行して確認")
        logger.info("   3. GitHub Actions でのポッドキャスト生成テスト")
    else:
        logger.info("   1. GitHub Actions環境での詳細ログ確認")
        logger.info("   2. 一時的なAPI制限やネットワーク問題の調査")
        logger.info("   3. 異なる時間帯での再実行テスト")
    
    # 生成されたレポートファイル
    logger.info("")
    logger.info("📄 生成されたレポートファイル:")
    for result_name, result_data in report['diagnostic_results'].items():
        if result_data.get('report_file'):
            logger.info(f"   - {result_data['report_file']}")

def main():
    """メイン処理"""
    logger = setup_logging()
    logger.info("🔍 Google Cloud TTS 包括的診断開始")
    logger.info("=" * 50)
    
    diagnostic_results = {}
    
    # 1. サービスアカウント権限診断
    success, output = run_diagnostic_script(
        'diagnose_service_account_permissions.py',
        'サービスアカウント権限診断'
    )
    diagnostic_results['permissions_diagnosis'] = {
        'success': success,
        'output': output,
        'report_file': 'service_account_permission_diagnosis.json'
    }
    
    # 2. プロジェクト設定診断
    success, output = run_diagnostic_script(
        'diagnose_project_settings.py',
        'プロジェクト設定診断'
    )
    diagnostic_results['project_settings_diagnosis'] = {
        'success': success,
        'output': output,
        'report_file': 'project_settings_diagnosis.json'
    }
    
    # 3. サービスアカウント詳細検証
    success, output = run_diagnostic_script(
        'verify_service_account_details.py',
        'サービスアカウント詳細検証'
    )
    diagnostic_results['service_account_verification'] = {
        'success': success,
        'output': output,
        'report_file': 'service_account_detailed_verification.json'
    }
    
    # 4. GitHub Actions ログ分析
    github_analysis = analyze_github_actions_logs()
    diagnostic_results['github_actions_analysis'] = github_analysis or {'success': False}
    
    # 5. 異なるTTS設定での動作テスト
    config_test_results = test_different_tts_configurations()
    diagnostic_results['configuration_tests'] = {
        'success': any(r.get('success', False) for r in config_test_results),
        'results': config_test_results
    }
    
    # 包括的診断レポート生成
    report = generate_comprehensive_diagnosis_report(diagnostic_results)
    
    # レポート保存
    report_file = Path("comprehensive_tts_diagnosis_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"📄 包括的診断レポート保存: {report_file}")
    
    # サマリー表示
    print_comprehensive_summary(report)
    
    return 0 if not report['summary']['critical_issues'] else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)