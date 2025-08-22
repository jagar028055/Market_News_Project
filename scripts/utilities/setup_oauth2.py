#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OAuth2認証セットアップスクリプト
Google Drive、Docs、Sheets APIへのOAuth2認証を設定し、リフレッシュトークンを取得する
"""

import os
import json
import webbrowser
from typing import Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# OAuth2スコープ（フルスコープ: Drive + Docs + Sheets）
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets'
]

# デフォルトのクレデンシャルファイル名
CREDENTIALS_FILE = 'credentials.json'

def setup_oauth2_authentication() -> bool:
    """
    OAuth2認証をセットアップし、リフレッシュトークンを取得する
    
    Returns:
        bool: 成功時はTrue、失敗時はFalse
    """
    print("=== Google OAuth2認証セットアップ ===")
    print()
    
    # 1. credentials.jsonファイルの確認
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ '{CREDENTIALS_FILE}' ファイルが見つかりません。")
        print()
        print("セットアップ手順:")
        print("1. Google Cloud Console (https://console.cloud.google.com/) にアクセス")
        print("2. プロジェクトを選択または作成")
        print("3. 「APIとサービス」→「認証情報」に移動")
        print("4. 「認証情報を作成」→「OAuth 2.0 クライアント ID」を選択")
        print("5. アプリケーションの種類: 「デスクトップアプリケーション」")
        print(f"6. 作成後、JSONファイルをダウンロードして '{CREDENTIALS_FILE}' として保存")
        print()
        return False
    
    try:
        print(f"✅ '{CREDENTIALS_FILE}' ファイルを発見しました。")
        
        # 2. OAuth2フローを開始
        print("OAuth2認証フローを開始します...")
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE, SCOPES)
        
        # ローカルサーバーを使用して認証
        print("ブラウザが開きます。Googleアカウントでログインしてください...")
        creds = flow.run_local_server(port=0)
        
        if not creds or not creds.refresh_token:
            print("❌ 認証に失敗しました。リフレッシュトークンが取得できませんでした。")
            return False
        
        # 3. 認証情報を確認
        print("✅ OAuth2認証が成功しました！")
        print()
        print("取得した認証情報:")
        print(f"  Client ID: {creds.client_id}")
        print(f"  Client Secret: {creds.client_secret}")
        print(f"  Refresh Token: {creds.refresh_token[:20]}...")
        print(f"  取得したスコープ: {', '.join(creds.scopes) if creds.scopes else 'なし'}")
        
        # スコープ診断
        print()
        print("=== スコープ診断 ===")
        _diagnose_scopes(creds.scopes) 
        
        # 4. .envファイルの更新提案
        env_content = generate_env_content(creds)
        print()
        print("=== .env ファイル設定 ===")
        print("以下の内容を .env ファイルに追加してください:")
        print()
        print(env_content)
        
        # 5. GitHub Secrets設定の提案
        print()
        print("=== GitHub Secrets 設定 ===")
        print("GitHub Actions で使用する場合、以下をRepository Secretsに追加してください:")
        print(f"GOOGLE_OAUTH2_CLIENT_ID: {creds.client_id}")
        print(f"GOOGLE_OAUTH2_CLIENT_SECRET: {creds.client_secret}")
        print(f"GOOGLE_OAUTH2_REFRESH_TOKEN: {creds.refresh_token}")
        print()
        
        # 6. .env ファイルの自動更新オプション
        response = input("自動的に .env ファイルを更新しますか？ (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            update_env_file(env_content)
        
        print("✅ OAuth2認証セットアップが完了しました！")
        return True
        
    except Exception as e:
        print(f"❌ OAuth2認証セットアップ中にエラーが発生しました: {e}")
        return False

def _diagnose_scopes(granted_scopes: list) -> None:
    """
    取得したスコープを診断し、不足しているスコープを報告する
    
    Args:
        granted_scopes: 実際に取得されたスコープのリスト
    """
    required_scopes = {
        'https://www.googleapis.com/auth/drive': 'Google Drive API',
        'https://www.googleapis.com/auth/documents': 'Google Docs API', 
        'https://www.googleapis.com/auth/spreadsheets': 'Google Sheets API'
    }
    
    granted_scopes = granted_scopes or []
    
    print("必要なスコープの確認:")
    all_granted = True
    
    for scope, description in required_scopes.items():
        if scope in granted_scopes:
            print(f"  ✅ {description}: 承認済み")
        else:
            print(f"  ❌ {description}: 未承認")
            all_granted = False
    
    if all_granted:
        print()
        print("🎉 全ての必要なスコープが正常に取得されました！")
        print("   スプレッドシート機能を含む全機能が利用可能です。")
    else:
        print()
        print("⚠️  一部のスコープが不足しています。")
        print("   Google Cloud Console で OAuth 同意画面のスコープ設定を確認してください。")
        print("   詳細: docs/Google_Cloud_Console_OAuth2_Setup.md")

def generate_env_content(creds: Credentials) -> str:
    """
    認証情報から.env用のコンテンツを生成する
    
    Args:
        creds: OAuth2認証情報
        
    Returns:
        str: .env用のコンテンツ
    """
    return f"""# Google OAuth2認証設定
GOOGLE_AUTH_METHOD="oauth2"
GOOGLE_OAUTH2_CLIENT_ID="{creds.client_id}"
GOOGLE_OAUTH2_CLIENT_SECRET="{creds.client_secret}"
GOOGLE_OAUTH2_REFRESH_TOKEN="{creds.refresh_token}"
"""

def update_env_file(oauth2_content: str) -> bool:
    """
    .envファイルを更新する
    
    Args:
        oauth2_content: OAuth2設定のコンテンツ
        
    Returns:
        bool: 成功時はTrue、失敗時はFalse
    """
    try:
        env_file_path = '.env'
        
        # 既存の.envファイルを読み込み
        existing_content = ""
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        
        # OAuth2設定を既存のコンテンツから削除（重複回避）
        lines = existing_content.split('\n')
        filtered_lines = []
        oauth2_section = False
        
        for line in lines:
            if line.strip().startswith('# Google OAuth2認証設定'):
                oauth2_section = True
                continue
            elif oauth2_section and line.strip().startswith('GOOGLE_OAUTH2_'):
                continue
            elif oauth2_section and line.strip().startswith('GOOGLE_AUTH_METHOD='):
                continue
            elif oauth2_section and line.strip() == "":
                oauth2_section = False
                continue
            else:
                oauth2_section = False
                filtered_lines.append(line)
        
        # 新しいコンテンツを作成
        new_content = '\n'.join(filtered_lines).rstrip() + '\n\n' + oauth2_content
        
        # ファイルに書き込み
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ .env ファイルを更新しました: {env_file_path}")
        return True
        
    except Exception as e:
        print(f"❌ .env ファイルの更新中にエラーが発生しました: {e}")
        return False

def test_oauth2_credentials() -> bool:
    """
    設定されたOAuth2認証情報をテストする
    
    Returns:
        bool: 成功時はTrue、失敗時はFalse
    """
    try:
        from gdocs.oauth2_client import test_oauth2_connection
        return test_oauth2_connection()
    except ImportError:
        print("❌ OAuth2クライアントモジュールが見つかりません。")
        return False
    except Exception as e:
        print(f"❌ OAuth2認証テスト中にエラーが発生しました: {e}")
        return False

def diagnose_existing_token() -> bool:
    """
    既存のリフレッシュトークンを診断する
    
    Returns:
        bool: 診断成功時はTrue、失敗時はFalse
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        client_id = os.getenv('GOOGLE_OAUTH2_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_OAUTH2_CLIENT_SECRET')
        refresh_token = os.getenv('GOOGLE_OAUTH2_REFRESH_TOKEN')
        
        print("=== 既存トークン診断 ===")
        print()
        
        # 環境変数の確認
        print("環境変数の確認:")
        print(f"  CLIENT_ID: {'設定済み' if client_id else '未設定'}")
        print(f"  CLIENT_SECRET: {'設定済み' if client_secret else '未設定'}")
        print(f"  REFRESH_TOKEN: {'設定済み' if refresh_token else '未設定'}")
        
        if not all([client_id, client_secret, refresh_token]):
            print()
            print("❌ 必要な環境変数が不足しています。新しいトークンを生成してください。")
            return False
        
        # トークンの有効性テスト
        print()
        print("トークンの有効性テスト中...")
        
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        
        # 現在のスコープでテスト
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )
        
        try:
            creds.refresh(Request())
            print("✅ トークンの更新に成功しました。")
            print(f"   有効なスコープ: {', '.join(creds.scopes) if creds.scopes else '不明'}")
            
            # スコープ診断
            print()
            _diagnose_scopes(creds.scopes)
            return True
            
        except Exception as refresh_error:
            print(f"❌ トークン更新エラー: {refresh_error}")
            
            if 'invalid_scope' in str(refresh_error):
                print("   → スプレッドシートスコープが未承認の可能性があります。")
                print("   → 新しいトークンを生成してください。")
            elif 'invalid_grant' in str(refresh_error):
                print("   → リフレッシュトークンが失効している可能性があります。")
                print("   → 新しいトークンを生成してください。")
            
            return False
            
    except Exception as e:
        print(f"❌ 診断中にエラーが発生しました: {e}")
        return False

def main():
    """メイン処理"""
    print("Market News OAuth2認証セットアップ")
    print("=" * 50)
    print()
    
    # 既存トークンの診断オプション
    print("1. 既存のリフレッシュトークンを診断")
    print("2. 新しいリフレッシュトークンを生成")
    print()
    choice = input("選択してください (1/2): ").strip()
    
    if choice == '1':
        print()
        if diagnose_existing_token():
            print()
            print("✅ 既存のトークンは正常に動作しています！")
        else:
            print()
            print("❌ 既存のトークンに問題があります。新しいトークンの生成をお勧めします。")
            print()
            response = input("新しいトークンを生成しますか？ (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                setup_oauth2_authentication()
    else:
        # OAuth2認証をセットアップ
        if setup_oauth2_authentication():
            print()
            print("認証情報のテストを実行しますか？ (y/N): ", end="")
            response = input().strip().lower()
            
            if response in ['y', 'yes']:
                print()
                print("=== OAuth2認証テスト ===")
                if test_oauth2_credentials():
                    print("✅ すべてのセットアップが完了し、正常に動作しています！")
                else:
                    print("❌ 認証テストに失敗しました。設定を確認してください。")
        else:
            print("❌ OAuth2認証セットアップに失敗しました。")

if __name__ == "__main__":
    main()