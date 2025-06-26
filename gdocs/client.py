# -*- coding: utf-8 -*-

import os.path
import pytz
import pandas as pd
from datetime import datetime
import traceback
import json # 追加

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- 定数 ---
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/docs"
]
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "anscombe.json" # ユーザーがダウンロードするファイル

def authenticate_google_services():
    """
    ローカル環境でGoogle DriveおよびDocs APIへの認証を行う。
    GitHub Actions環境では環境変数 GOOGLE_TOKEN_JSON から認証情報を読み込む。
    """
    creds = None

    # GitHub Actions環境での認証 (環境変数からtoken.jsonの内容を読み込む)
    if os.getenv("GOOGLE_TOKEN_JSON"):
        try:
            token_json = json.loads(os.getenv("GOOGLE_TOKEN_JSON"))
            creds = Credentials.from_authorized_user_info(token_json, SCOPES)
            print("環境変数からGoogle認証情報を読み込みました。")
        except Exception as e:
            print(f"環境変数からの認証情報読み込みに失敗しました: {e}")
            creds = None
    
    # ローカル環境での認証 (token.jsonファイルから読み込む)
    if not creds and os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        print(f"ファイル '{TOKEN_FILE}' からGoogle認証情報を読み込みました。")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("Google認証トークンをリフレッシュしました。")
            except Exception as e:
                print(f"トークンのリフレッシュに失敗しました: {e}")
                creds = None
        
        if not creds:
            # ローカルでの初回認証 (anscombe.jsonを使用)
            if not os.path.exists(CREDENTIALS_FILE):
                print("\n!!!!!!!!!!!!!!!!!! 設定エラー !!!!!!!!!!!!!!!!!!")
                print(f"認証情報ファイル '{CREDENTIALS_FILE}' が見つかりません。")
                print("Google Cloud PlatformでOAuth 2.0クライアントIDを再作成してください。")
                print("----------------------------------------------------")
                print("【重要】設定手順:")
                print("1. Google Cloud Console (https://console.cloud.google.com/) にアクセスし、プロジェクトを選択。")
                print("2. [APIとサービス] > [ライブラリ] で、以下の2つのAPIを検索し、それぞれ【有効にする】ボタンを押してください。")
                print("   - Google Drive API")
                print("   - Google Docs API")
                print("3. [APIとサービス] > [認証情報] に移動。")
                print("4. [+ 認証情報を作成] > [OAuth クライアント ID] を選択。")
                print("5. アプリケーションの種類で【デスクトップアプリ】を必ず選択してください。")
                print("6. 作成されたクライアントIDの右側にあるダウンロードボタンをクリックし、")
                print(f"   ファイルを '{CREDENTIALS_FILE}' という名前でこのディレクトリに保存します。")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
                return None, None
            
            print("\n--- ブラウザでの認証が必要です ---")
            print("ブラウザが開き、Googleアカウントへのアクセス許可を求められます。")
            print("【注意】「Googleによる確認が完了していません」という画面が表示される場合があります。")
            print("これは個人開発のアプリでは正常な表示です。以下の手順で進めてください。")
            print("1. [詳細] または [Advanced] をクリック")
            print("2. [（アプリ名）に移動] をクリック")
            print("3. 表示される権限を許可してください。")
            print("【エラー403: access_denied が出る場合】")
            print("OAuth同意画面が「テスト中」になっています。以下の手順で「本番環境」に切り替えてください。")
            print("1. Google Cloud Consoleの[APIとサービス] > [OAuth同意画面]に移動")
            print("2. [アプリを公開] ボタンをクリックし、ステータスを「テスト中」から「本番環境」に変更します。")
            print("------------------------------------")
            
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 新しい認証情報が取得された場合、token.jsonに保存
        if creds and not os.getenv("GOOGLE_TOKEN_JSON"): # 環境変数からの認証でない場合のみファイルに保存
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
                print(f"認証情報を '{TOKEN_FILE}' に保存しました。")

    try:
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)
        print("Google DriveおよびDocs APIへの認証が完了しました。")
        return drive_service, docs_service
    except HttpError as error:
        print(f"サービス構築中にAPIエラーが発生しました: {error}")
        return None, None
    except Exception as e:
        print(f"サービス構築中に予期せぬエラーが発生しました: {e}")
        return None, None

def create_new_google_doc_in_folder(drive_service, doc_title: str, folder_id: str):
    """
    指定されたフォルダ内に新しいGoogleドキュメントを作成し、そのIDを返す
    """
    try:
        file_metadata = {
            'name': doc_title,
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [folder_id]
        }
        file = drive_service.files().create(body=file_metadata, fields='id').execute()
        doc_id = file.get('id')
        print(f"Googleドキュメント '{doc_title}' (ID: {doc_id}) を作成しました。")
        return doc_id
    except HttpError as error:
        print(f"Googleドキュメント作成中にAPIエラー: {error}")
        return None

def format_articles_for_doc(articles_list: list, source_header: str) -> str:
    """
    記事リストを、指定されたヘッダーを含むプレーンテキストにフォーマットする
    """
    if not articles_list:
        return ""
    
    text_parts = [f"{source_header}\n\n"]
    for i, article in enumerate(articles_list):
        pub_jst_str = article.get('published_jst').strftime('%Y-%m-%d %H:%M') if pd.notnull(article.get('published_jst')) else 'N/A'
        text_parts.append(f"({pub_jst_str}) {article.get('title', '[タイトル不明]')}\n")
        text_parts.append(f"{article.get('url', '[URL不明]')}\n")
        text_parts.append(f"{article.get('body', '[本文なし]')}\n")
        if i < len(articles_list) - 1:
            text_parts.append("\n--------------------------------------------------\n\n")
    return "".join(text_parts)

def export_all_news_to_one_document(drive_service, docs_service, reuters_articles: list, bloomberg_articles: list, folder_id: str):
    """
    収集した全記事を1つのGoogleドキュメントに出力する
    """
    if not reuters_articles and not bloomberg_articles:
        print("エクスポートする記事がありません。Googleドキュメント作成をスキップします。")
        return

    print("\n--- Googleドキュメントへの出力開始 ---")
    jst = pytz.timezone('Asia/Tokyo')
    doc_title = f"{datetime.now(jst).strftime('%Y%m%d_%H%M')}_Market_News_Summary"
    
    document_id = create_new_google_doc_in_folder(drive_service, doc_title, folder_id)
    if not document_id:
        print("ドキュメントの作成に失敗したため、処理を中断します。")
        return

    try:
        reuters_header = "Reuters ニュース"
        bloomberg_header = "Bloomberg ニュース"
        
        full_text = format_articles_for_doc(reuters_articles, reuters_header)
        if reuters_articles and bloomberg_articles:
            full_text += "\n\n\n"
        full_text += format_articles_for_doc(bloomberg_articles, bloomberg_header)

        if not full_text:
            print("書き込む内容がありません。")
            return

        requests_list = [{'insertText': {'location': {'index': 1}, 'text': full_text}}]
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests_list}).execute()
        print("ドキュメントへのテキスト挿入が完了しました。")

        styling_requests = []
        if reuters_articles:
            styling_requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': 1, 'endIndex': len(reuters_header)},
                    'paragraphStyle': {'namedStyleType': 'TITLE'},
                    'fields': 'namedStyleType'
                }
            })
        if bloomberg_articles:
            start_index = full_text.find(bloomberg_header) + 1
            if start_index > 0:
                styling_requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': start_index, 'endIndex': start_index + len(bloomberg_header) - 1},
                        'paragraphStyle': {'namedStyleType': 'TITLE'},
                        'fields': 'namedStyleType'
                    }
                })
        
        if styling_requests:
            docs_service.documents().batchUpdate(documentId=document_id, body={'requests': styling_requests}).execute()
            print("ヘッダースタイルを適用しました。")

        doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        print(f"\n処理完了!\nGoogleドキュメント: {doc_url}\n出力先フォルダ: {folder_url}")

    except HttpError as error:
        print(f"ドキュメント書き込み/スタイル適用中にAPIエラー: {error}")
    except Exception as e:
        print(f"ドキュメント処理中に予期せぬエラー: {e}")
        traceback.print_exc()