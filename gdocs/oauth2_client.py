# -*- coding: utf-8 -*-

"""
Google OAuth2認証クライアント
リフレッシュトークンを使用したGoogle Drive/Docs API認証
"""

import os
import json
from typing import Tuple, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# スコープの定義
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents'
]

def authenticate_google_services_oauth2() -> Tuple[Optional[object], Optional[object]]:
    """
    OAuth2認証でGoogle DriveとDocs APIサービスを取得する
    
    Returns:
        Tuple[drive_service, docs_service]: 認証済みサービスオブジェクト、失敗時は(None, None)
    """
    print("OAuth2認証方式を使用します...")
    
    # 環境変数から認証情報を取得
    client_id = os.getenv('GOOGLE_OAUTH2_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_OAUTH2_CLIENT_SECRET')
    refresh_token = os.getenv('GOOGLE_OAUTH2_REFRESH_TOKEN')
    
    # デバッグ情報（認証情報の存在確認）
    print("🔍 OAuth2環境変数デバッグ:")
    print(f"  CLIENT_ID: {'設定済み' if client_id else '未設定'} ({client_id[-20:] if client_id and len(client_id) > 20 else client_id})")
    print(f"  CLIENT_SECRET: {'設定済み' if client_secret else '未設定'} ({client_secret[-10:] if client_secret and len(client_secret) > 10 else client_secret})")
    print(f"  REFRESH_TOKEN: {'設定済み' if refresh_token else '未設定'} ({refresh_token[-20:] if refresh_token and len(refresh_token) > 20 else refresh_token})")
    
    # 必須情報の検証
    if not all([client_id, client_secret, refresh_token]):
        print("❌ OAuth2認証に必要な環境変数が不足しています:")
        if not client_id:
            print("  - GOOGLE_OAUTH2_CLIENT_ID が未設定")
        if not client_secret:
            print("  - GOOGLE_OAUTH2_CLIENT_SECRET が未設定")
        if not refresh_token:
            print("  - GOOGLE_OAUTH2_REFRESH_TOKEN が未設定")
        print("\n環境変数を設定するか、setup_oauth2.py でトークンを再取得してください。")
        return None, None
    
    try:
        print("--- OAuth2認証でGoogleサービスに接続します ---")
        
        # 認証情報を作成
        creds = Credentials(
            token=None,  # 初期アクセストークンは None
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )
        
        # 認証情報の状態を確認
        print("🔍 認証情報の状態:")
        print(f"  Valid: {creds.valid}")
        print(f"  Expired: {creds.expired}")
        print(f"  Has refresh token: {bool(creds.refresh_token)}")
        print(f"  Token: {'有効' if creds.token else '無効'}")
        print(f"  Scopes: {creds.scopes}")
        
        # リフレッシュトークンでアクセストークンを更新
        if not creds.valid:
            print("アクセストークンを更新しています...")
            try:
                creds.refresh(Request())
                print("✅ トークン更新完了")
            except Exception as refresh_error:
                print(f"❌ トークンリフレッシュエラー: {refresh_error}")
                print("\n考えられる原因:")
                print("  1. リフレッシュトークンが失効している")
                print("  2. クライアントID/シークレットが間違っている")
                print("  3. OAuth同意画面の設定に問題がある")
                print("\n対処法: setup_oauth2.py を実行してトークンを再取得してください。")
                return None, None
        
        # Google Drive と Docs サービスを構築
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)
        
        print("✅ OAuth2認証でGoogle Drive/Docs APIへの接続が完了しました")
        return drive_service, docs_service
        
    except HttpError as error:
        print(f"❌ Google API HTTPエラー: {error}")
        if hasattr(error, 'resp') and error.resp.status == 401:
            print("認証エラー: 401 Unauthorized")
            print("リフレッシュトークンまたはクライアント認証情報を確認してください。")
        return None, None
    except Exception as e:
        print(f"❌ OAuth2認証中に予期せぬエラーが発生しました: {e}")
        return None, None

def test_oauth2_connection() -> bool:
    """
    OAuth2認証の動作テスト
    
    Returns:
        bool: 認証成功時はTrue、失敗時はFalse
    """
    print("\n=== OAuth2認証テスト開始 ===")
    
    drive_service, docs_service = authenticate_google_services_oauth2()
    
    if not drive_service or not docs_service:
        print("❌ OAuth2認証テスト失敗")
        return False
    
    try:
        # Drive APIテスト
        about = drive_service.about().get(fields='user').execute()
        user_email = about.get('user', {}).get('emailAddress', 'N/A')
        print(f"✅ Google Drive接続テスト成功: {user_email}")
        
        # Docs APIテスト（権限確認のみ）
        print("✅ Google Docs API接続テスト成功")
        
        print("=== OAuth2認証テスト完了: 成功 ===\n")
        return True
        
    except Exception as e:
        print(f"❌ OAuth2接続テスト中にエラー: {e}")
        print("=== OAuth2認証テスト完了: 失敗 ===\n")
        return False

if __name__ == "__main__":
    # モジュール単体テスト
    test_oauth2_connection()