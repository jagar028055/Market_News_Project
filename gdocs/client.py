# -*- coding: utf-8 -*-

import os
import json
import pytz
import pandas as pd
from datetime import datetime
import traceback

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- 定数 ---
SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/docs"]
# サービスアカウントキーのファイルパス。環境変数から取得、なければデフォルト値を使用
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
# 環境変数からサービスアカウントのJSON文字列を直接読み込む場合
SERVICE_ACCOUNT_JSON_STR = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

def test_drive_connection(drive_service, folder_id: str) -> bool:
    """
    指定されたGoogle Driveフォルダへの接続と書き込み権限をテストする。
    """
    print("--- Google Driveへの接続と権限を確認します ---")
    try:
        # フォルダのメタデータを取得しようと試みる
        file_metadata = drive_service.files().get(
            fileId=folder_id,
            fields='id, name, capabilities'
        ).execute()
        
        # フォルダが存在し、コンテンツを追加できるか確認
        if file_metadata and file_metadata.get('capabilities', {}).get('canAddChildren'):
            print(f"フォルダ '{file_metadata.get('name')}' へのアクセスと書き込み権限を確認しました。")
            return True
        else:
            print(f"エラー: フォルダ (ID: {folder_id}) は存在しますが、書き込み権限がありません。")
            print("サービスアカウントのメールアドレスに、Google Driveフォルダの「編集者」権限が付与されているか確認してください。")
            return False
            
    except HttpError as error:
        if error.resp.status == 404:
            print(f"エラー: 指定されたフォルダ (ID: {folder_id}) が見つかりません。")
            print("'.env' ファイルの 'GOOGLE_DRIVE_OUTPUT_FOLDER_ID' が正しいか確認してください。")
        else:
            print(f"Google Driveへの接続中に予期せぬAPIエラーが発生しました: {error}")
        return False
    except Exception as e:
        print(f"Google Driveへの接続テスト中に予期せぬエラーが発生しました: {e}")
        return False

def authenticate_google_services():
    """
    Google DriveおよびDocs APIへの認証を行う。
    サービスアカウント認証を使用する。
    """
    creds = None
    print("--- Googleサービスへの認証を行います ---")

    try:
        # 環境変数 GOOGLE_SERVICE_ACCOUNT_JSON が設定されている場合、その内容を優先して使用
        if SERVICE_ACCOUNT_JSON_STR:
            try:
                # JSON文字列をパースして認証情報を作成
                service_account_info = json.loads(SERVICE_ACCOUNT_JSON_STR)
                creds = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=SCOPES
                )
                print("環境変数 'GOOGLE_SERVICE_ACCOUNT_JSON' から認証情報を読み込みました。")
            except json.JSONDecodeError as e:
                print(f"エラー: 環境変数 'GOOGLE_SERVICE_ACCOUNT_JSON' のJSON形式が正しくありません: {e}")
                return None, None
            except Exception as e:
                print(f"エラー: 環境変数の認証情報読み込み中にエラーが発生しました: {e}")
                return None, None
        
        # 環境変数がない場合、ファイルから読み込みを試行
        elif os.path.exists(SERVICE_ACCOUNT_FILE):
            try:
                creds = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_FILE, scopes=SCOPES
                )
                print(f"ファイル '{SERVICE_ACCOUNT_FILE}' から認証情報を読み込みました。")
            except Exception as e:
                print(f"エラー: サービスアカウントファイル '{SERVICE_ACCOUNT_FILE}' の読み込み中にエラーが発生しました: {e}")
                return None, None
        
        else:
            print(f"認証エラー: 認証情報が見つかりません。")
            print(f"環境変数 'GOOGLE_SERVICE_ACCOUNT_JSON' を設定するか、")
            print(f"'{SERVICE_ACCOUNT_FILE}' をプロジェクトルートに配置してください。")
            return None, None

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
        # ドキュメントの末尾のインデックスを取得
        end_index = doc.get('body').get('content')[-1].get('endIndex') -1
        if end_index > 1:
             delete_requests = [{'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': end_index}}}]
             docs_service.documents().batchUpdate(documentId=document_id, body={'requests': delete_requests}).execute()

        # 2. 新しいコンテンツを作成
        jst = pytz.timezone('Asia/Tokyo')
        update_time_str = f"最終更新: {datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S JST')}"
        reuters_header = "Reuters ニュース"
        bloomberg_header = "Bloomberg ニュース"
        
        reuters_articles = [a for a in articles if a.get('source') == 'Reuters']
        bloomberg_articles = [a for a in articles if a.get('source') == 'Bloomberg']

        full_text = f"{update_time_str}\n\n"
        full_text += format_articles_for_doc(reuters_articles, reuters_header, include_body=True)
        if reuters_articles and bloomberg_articles:
            full_text += "\n\n\n"
        full_text += format_articles_for_doc(bloomberg_articles, bloomberg_header, include_body=True)

        # 3. 新しいコンテンツを挿入 (コンテンツがある場合のみ)
        if full_text.strip():
            insert_requests = [{'insertText': {'location': {'index': 1}, 'text': full_text}}]
            docs_service.documents().batchUpdate(documentId=document_id, body={'requests': insert_requests}).execute()
            print(f"ドキュメント (ID: {document_id}) の更新が完了しました。")
        else:
            print("書き込むコンテンツがないため、ドキュメントの更新をスキップしました。")
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

        reuters_articles = [a for a in articles_with_summary if a.get('source') == 'Reuters']
        bloomberg_articles = [a for a in articles_with_summary if a.get('source') == 'Bloomberg']

        summary_text = format_articles_for_doc(reuters_articles, reuters_header, include_body=False)
        if reuters_articles and bloomberg_articles:
            summary_text += "\n\n\n"
        summary_text += format_articles_for_doc(bloomberg_articles, bloomberg_header, include_body=False)

        # 3. コンテンツを挿入 (コンテンツがある場合のみ)
        if summary_text.strip():
            requests_list = [{'insertText': {'location': {'index': 1}, 'text': summary_text}}]
            docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests_list}).execute()
            print(f"日次サマリードキュメント (ID: {document_id}) への書き込みが完了しました。")
        else:
            print("書き込むコンテンツがないため、日次サマリードキュメントへの書き込みをスキップしました。")
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
