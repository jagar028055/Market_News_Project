#!/usr/bin/env python3
"""
GitHub Actions統合テストスクリプト
ローカル環境でGitHub Actionsと同様の処理をテスト
"""

import os
import sys
import logging
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from standalone_podcast_main import main as standalone_main
except ImportError as e:
    print(f"Import error: {e}")
    print("Required dependencies may be missing.")
    sys.exit(1)

def setup_test_environment():
    """テスト環境変数を設定"""
    # GitHub Actionsでテストモードを有効に
    os.environ['PODCAST_TEST_MODE'] = 'true'
    os.environ['PODCAST_FORCE_RUN'] = 'true'
    os.environ['PODCAST_WEEKDAYS_ONLY'] = 'false'
    
    # 必要最小限の設定（実際の値は環境変数から取得）
    test_env_vars = {
        'GEMINI_API_KEY': 'test_key_placeholder',
        'LINE_CHANNEL_ACCESS_TOKEN': 'test_token_placeholder',
        'LINE_CHANNEL_SECRET': 'test_secret_placeholder',
        'GOOGLE_OAUTH2_CLIENT_ID': 'test_client_id',
        'GOOGLE_OAUTH2_CLIENT_SECRET': 'test_client_secret',
        'GOOGLE_OAUTH2_REFRESH_TOKEN': 'test_refresh_token',
        'PODCAST_RSS_BASE_URL': 'https://test.github.io/test-repo',
        'PODCAST_AUTHOR_NAME': 'Test Author',
        'PODCAST_AUTHOR_EMAIL': 'test@example.com',
    }
    
    # 環境変数が設定されていない場合のみテスト値を設定
    for key, value in test_env_vars.items():
        if not os.getenv(key):
            os.environ[key] = value
    
    print("テスト環境変数設定完了")
    
    # 重要: Google Cloud認証情報は実際の値が必要
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON') and not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print("⚠️  Google Cloud認証情報が設定されていません")
        print("実際のテスト実行には以下の環境変数が必要です:")
        print("  GOOGLE_APPLICATION_CREDENTIALS_JSON または")
        print("  GOOGLE_APPLICATION_CREDENTIALS")
        return False
    
    return True

def test_github_actions_integration():
    """GitHub Actions統合テスト実行"""
    logger = logging.getLogger(__name__)
    logger.info("=== GitHub Actions統合テスト開始 ===")
    
    # テスト環境を設定
    if not setup_test_environment():
        logger.error("テスト環境設定に失敗")
        return False
    
    try:
        # standalone_podcast_main.py と同じ処理を実行
        logger.info("standalone_podcast_main.py 実行中...")
        exit_code = standalone_main()
        
        if exit_code == 0:
            logger.info("✅ GitHub Actions統合テスト成功!")
            
            # 生成されたファイルをチェック
            output_dir = Path("output/podcast")
            if output_dir.exists():
                test_files = list(output_dir.glob("test_*.mp3"))
                if test_files:
                    for file_path in test_files:
                        file_size = file_path.stat().st_size
                        logger.info(f"  生成ファイル: {file_path} ({file_size:,}バイト)")
                else:
                    logger.warning("  テスト音声ファイルが見つかりません")
            
            return True
        else:
            logger.error(f"❌ standalone_podcast_main.py が失敗 (exit_code: {exit_code})")
            return False
            
    except Exception as e:
        logger.error(f"❌ GitHub Actions統合テスト失敗: {e}")
        return False

def main():
    """メイン処理"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    success = test_github_actions_integration()
    
    if success:
        print("\n🎉 GitHub Actions統合テスト完了!")
        print("GitHub Actionsでのポッドキャスト生成準備が整いました。")
        return 0
    else:
        print("\n❌ GitHub Actions統合テスト失敗")
        print("設定を確認してください。")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)