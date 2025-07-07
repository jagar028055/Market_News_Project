# -*- coding: utf-8 -*-

import os
import json
import pytz
import pandas as pd
from datetime import datetime
import traceback

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- 定数 ---
SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/docs"]
TOKEN_FILE = "token.json"
OAUTH_CREDENTIALS_FILE = "credentials.json" # OAuthクライアントIDのファイル名

def authenticate_google_services():
    """
    Google DriveおよびDocs APIへの認証を行う。
    環境変数に応じて、サービスアカウント認証またはOAuth認証を自動で切り替える。
    """
    creds = None
    
    # 1. サービスアカウント認証 (GitHub Actionsなど、サーバー環境向け)
    if "GCP_SA_KEY" in os.environ:
        try:
            sa_key_info = json.loads(os.environ["GCP_SA_KEY"])
            creds = service_account.Credentials.from_service_account_info(sa_key_info, scopes=SCOPES)
            print("サービスアカウント認証情報を環境変数から読み込みました。")
        except Exception as e:
            print(f"サービスアカウント認証に失敗しました: {e}")
            return None, None
            
    # 2. OAuth認証 (ローカル環境向け)
    else:
        # 既存のtoken.jsonファイルから認証情報を読み込む
        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
                print(f"ファイル '{TOKEN_FILE}' からOAuth認証情報を読み込みました。")
            except Exception as e:
                print(f"'{TOKEN_FILE}' の読み込みに失敗しました: {e}")
                creds = None

        # 認証情報が無効または期限切れの場合
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("OAuth認証トークンをリフレッシュしました。")
                except Exception as e:
                    print(f"トークンのリフレッシュに失敗しました。再度認証が必要です。エラー: {e}")
                    creds = None
            
            # トークンがない、またはリフレッシュできない場合、新規認証フローを開始
            if not creds:
                if not os.path.exists(OAUTH_CREDENTIALS_FILE):
                    print_oauth_error_message()
                    return None, None
                
                print_oauth_guidance()
                flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # 新しい認証情報をtoken.jsonに保存
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
                print(f"新しい認証情報を '{TOKEN_FILE}' に保存しました。")

    # 認証情報を使ってAPIサービスを構築
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)
        print("Google DriveおよびDocs APIへの認証が完了しました。")
        return drive_service, docs_service
    except HttpError as error:
        print(f"APIサービス構築中にエラーが発生しました: {error}")
        return None, None
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        return None, None

def update_google_doc_with_full_text(docs_service, document_id: str, articles: list):
    """
    指定されたGoogleドキュメントの内容をクリアし、新しい記事全文で上書きする。
    """
    if not document_id:
        print("上書き対象のGoogleドキュメントIDが指定されていません。")
        return
    if not articles:
        print("上書きする記事がありません。")
        return

    print(f"--- Googleドキュメント (ID: {document_id}) の上書き更新開始 ---")
    
    try:
        # 1. ドキュメントの既存のコンテンツをすべて削除
        doc = docs_service.documents().get(documentId=document_id, fields='body(content)').execute()
        existing_text_len = len(doc.get('body').get('content')[1].get('paragraph').get('elements')[0].get('textRun').get('content'))
        if existing_text_len > 1:
             delete_requests = [{'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': existing_text_len}}}]
             docs_service.documents().batchUpdate(documentId=document_id, body={'requests': delete_requests}).execute()

        # 2. 新しいコンテンツを作成
        jst = pytz.timezone('Asia/Tokyo')
        update_time_str = f"最終更新: {datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S JST')}"
        reuters_header = "Reuters ニュース"
        bloomberg_header = "Bloomberg ニュース"
        
        reuters_articles = [a for a in articles if a['source'] == 'Reuters']
        bloomberg_articles = [a for a in articles if a['source'] == 'Bloomberg']

        full_text = f"{update_time_str}\n\n"
        full_text += format_articles_for_doc(reuters_articles, reuters_header, include_body=True)
        if reuters_articles and bloomberg_articles:
            full_text += "\n\n\n"
        full_text += format_articles_for_doc(bloomberg_articles, bloomberg_header, include_body=True)

        # 3. 新しいコンテンツを挿入
        insert_requests = [{'insertText': {'location': {'index': 1}, 'text': full_text}}]
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': insert_requests}).execute()
        
        print(f"ドキュメント (ID: {document_id}) の更新が完了しました。")
        doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
        print(f"確認用URL: {doc_url}")

    except HttpError as error:
        print(f"ドキュメント上書き更新中にAPIエラーが発生しました: {error}")
    except Exception as e:
        print(f"ドキュメント上書き更新中に予期せぬエラーが発生しました: {e}")
        traceback.print_exc()

def create_daily_summary_doc(drive_service, docs_service, articles_with_summary: list, folder_id: str):
    """
    AI要約を含む新しいGoogleドキュメントを毎日作成する。
    """
    if not articles_with_summary:
        print("要約記事がないため、日次サマリーのGoogleドキュメント作成をスキップします。")
        return

    print("\n--- 日次サマリーのGoogleドキュメント作成開始 ---")
    jst = pytz.timezone('Asia/Tokyo')
    doc_title = f"{datetime.now(jst).strftime('%Y%m%d')}_Market_News_AI_Summary"
    
    try:
        # 1. 新規ドキュメント作成
        file_metadata = {
            'name': doc_title,
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [folder_id]
        }
        file = drive_service.files().create(body=file_metadata, fields='id').execute()
        document_id = file.get('id')
        print(f"日次サマリードキュメント '{doc_title}' (ID: {document_id}) を作成しました。")

        # 2. コンテンツを作成
        reuters_header = "Reuters ニュース (AI要約)"
        bloomberg_header = "Bloomberg ニュース (AI要約)"

        reuters_articles = [a for a in articles_with_summary if a['source'] == 'Reuters']
        bloomberg_articles = [a for a in articles_with_summary if a['source'] == 'Bloomberg']

        summary_text = format_articles_for_doc(reuters_articles, reuters_header, include_body=False)
        if reuters_articles and bloomberg_articles:
            summary_text += "\n\n\n"
        summary_text += format_articles_for_doc(bloomberg_articles, bloomberg_header, include_body=False)

        # 3. コンテンツを挿入
        requests_list = [{'insertText': {'location': {'index': 1}, 'text': summary_text}}]
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests_list}).execute()
        
        print(f"日次サマリードキュメント (ID: {document_id}) への書き込みが完了しました。")
        doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
        print(f"確認用URL: {doc_url}")

    except HttpError as error:
        print(f"日次サマリードキュメント作成中にAPIエラーが発生しました: {error}")
    except Exception as e:
        print(f"日次サマリードキュメント作成中に予期せぬエラーが発生しました: {e}")
        traceback.print_exc()

def format_articles_for_doc(articles_list: list, header: str, include_body: bool) -> str:
    """
    記事リストをGoogleドキュメント用にフォーマットする。
    include_bodyフラグで、記事本文（または要約）を含めるか制御する。
    """
    if not articles_list:
        return ""
    
    text_parts = [f"{header}\n\n"]
    for i, article in enumerate(articles_list):
        pub_jst_str = article.get('published_jst').strftime('%Y-%m-%d %H:%M') if pd.notnull(article.get('published_jst')) else 'N/A'
        text_parts.append(f"({pub_jst_str}) {article.get('title', '[タイトル不明]')}\n")
        text_parts.append(f"{article.get('url', '[URL不明]')}\n")
        if include_body:
            content = article.get('body', '[本文なし]')
        else:
            content = article.get('summary', '[要約なし]')
        text_parts.append(f"{content}\n")
        
        if i < len(articles_list) - 1:
            text_parts.append("\n--------------------------------------------------\n\n")
    return "".join(text_parts)

def print_oauth_error_message():
    """OAuth認証ファイルが見つからない場合のエラーメッセージを表示する"""
    print("\n!!!!!!!!!!!!!!!!!! 設定エラー !!!!!!!!!!!!!!!!!!")
    print(f"ローカル実行用の認証情報ファイル '{OAUTH_CREDENTIALS_FILE}' が見つかりません。")
    print("Google Cloud PlatformでOAuth 2.0クライアントIDを作成し、配置してください。")
    print("----------------------------------------------------")
    print("【重要】設定手順:")
    print("1. Google Cloud Console (https://console.cloud.google.com/) にアクセス。")
    print("2. [APIとサービス] > [ライブラリ] で 'Google Drive API' と 'Google Docs API' を有効化。")
    print("3. [APIとサービス] > [認証情報] > [+ 認証情報を作成] > [OAuth クライアント ID] を選択。")
    print("4. アプリケーションの種類で【デスクトップアプリ】を選択。")
    print(f"5. 作成後、JSONファイルをダウンロードし、'{OAUTH_CREDENTIALS_FILE}' という名前で保存。")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")

def print_oauth_guidance():
    """OAuthの初回認証時の案内メッセージを表示する"""
    print("\n--- ブラウザでの初回認証が必要です ---")
    print("ブラウザが開き、Googleアカウントへのアクセス許可を求められます。")
    print("【注意】「Googleによる確認が完了していません」という画面が表示された場合は、")
    print("       [詳細] > [（アプリ名）に移動] の順にクリックして進めてください。")
    print("【エラー403: access_denied が出る場合】")
    print("       GCPの[OAuth同意画面]で、公開ステータスを「テスト中」から「本番環境」に変更してください。")
    print("------------------------------------")