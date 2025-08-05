#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OAuth2認証セットアップスクリプト
Google DriveとDocs APIへのOAuth2認証を設定し、リフレッシュトークンを取得する
"""

import os
import json
import webbrowser
from typing import Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# OAuth2スコープ
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents'
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

def main():
    """メイン処理"""
    print("Market News OAuth2認証セットアップ")
    print("=" * 50)
    
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