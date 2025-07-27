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

def debug_drive_storage_info(drive_service) -> None:
    """
    サービスアカウントのGoogle Drive容量情報とファイル一覧をデバッグ出力する。
    """
    print("\n--- Google Drive容量情報とファイル詳細 ---")
    try:
        # Drive容量情報を取得
        about = drive_service.about().get(fields='storageQuota,user').execute()
        storage = about.get('storageQuota', {})
        user_info = about.get('user', {})
        
        print(f"ユーザー情報: {user_info.get('emailAddress', 'N/A')}")
        print(f"使用容量: {storage.get('usage', 'N/A')} bytes")
        print(f"総容量: {storage.get('limit', 'N/A')} bytes")
        print(f"使用率: {float(storage.get('usage', 0)) / float(storage.get('limit', 1)) * 100:.2f}%" if storage.get('limit') else "無制限")
        
        # サービスアカウントのファイル一覧を取得（最新20件）
        print("\n--- サービスアカウントのファイル一覧（最新20件） ---")
        files_result = drive_service.files().list(
            pageSize=20,
            fields="files(id, name, size, createdTime, mimeType, trashed)",
            orderBy="createdTime desc"
        ).execute()
        files = files_result.get('files', [])
        
        if not files:
            print("ファイルが見つかりません。")
        else:
            for file in files:
                file_size = int(file.get('size', 0)) if file.get('size') else 0
                trashed = file.get('trashed', False)
                status = "(削除済み)" if trashed else ""
                print(f"- {file.get('name')} | {file_size} bytes | {file.get('createdTime')} {status}")
        
        print(f"合計ファイル数: {len(files)}")
        
    except Exception as e:
        print(f"Drive容量情報の取得中にエラーが発生しました: {e}")

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


def update_google_doc_with_full_text(docs_service, document_id: str, articles: list) -> bool:
    """
    指定されたGoogleドキュメントの内容をクリアし、新しい記事全文で上書きする。
    成功した場合はTrue、失敗した場合はFalseを返す。
    """
    if not document_id:
        print("上書き対象のGoogleドキュメントIDが指定されていません。")
        return True # エラーではないのでTrue
    if not articles:
        print("上書きする記事がありません。")
        return True # エラーではないのでTrue

    print(f"--- Googleドキュメント (ID: {document_id}) の上書き更新開始 ---")
    
    try:
        # 1. ドキュメントの既存のコンテンツをすべて削除
        doc = docs_service.documents().get(documentId=document_id, fields='body(content)').execute()
        end_index = doc.get('body').get('content')[-1].get('endIndex') - 1
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

        # 3. 新しいコンテンツを挿入
        if full_text.strip():
            insert_requests = [{'insertText': {'location': {'index': 1}, 'text': full_text}}]
            docs_service.documents().batchUpdate(documentId=document_id, body={'requests': insert_requests}).execute()
            print(f"ドキュメント (ID: {document_id}) の更新が完了しました。")
        else:
            print("書き込むコンテンツがないため、ドキュメントの更新をスキップしました。")
        
        doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
        print(f"確認用URL: {doc_url}")
        return True

    except HttpError as error:
        print(f"ドキュメント上書き更新中にAPIエラーが発生しました: {error}")
        return False
    except Exception as e:
        print(f"ドキュメント上書き更新中に予期せぬエラーが発生しました: {e}")
        traceback.print_exc()
        return False

def create_daily_summary_doc(drive_service, docs_service, articles_with_summary: list, folder_id: str) -> bool:
    """
    AI要約を含む日次サマリードキュメントを作成・更新する。
    成功した場合はTrue、失敗した場合はFalseを返す。
    """
    if not articles_with_summary:
        print("要約記事がないため、日次サマリーのGoogleドキュメント作成をスキップします。")
        return True # エラーではないのでTrue

    print("\n--- 日次サマリーのGoogleドキュメント作成/更新開始 ---")
    jst = pytz.timezone('Asia/Tokyo')
    today_str = datetime.now(jst).strftime('%Y%m%d')
    doc_title = f"{today_str}_Market_News_AI_Summary"
    document_id = None

    try:
        # 1. 同じ日付のドキュメントが既に存在するか検索
        query = f"name='{doc_title}' and '{folder_id}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        existing_files = response.get('files', [])

        if existing_files:
            document_id = existing_files[0].get('id')
            print(f"既存の日次サマリードキュメント '{doc_title}' (ID: {document_id}) を発見しました。内容を更新します。")
            doc = docs_service.documents().get(documentId=document_id, fields='body(content)').execute()
            end_index = doc.get('body').get('content')[-1].get('endIndex') - 1
            if end_index > 1:
                delete_requests = [{'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': end_index}}}]
                docs_service.documents().batchUpdate(documentId=document_id, body={'requests': delete_requests}).execute()
        else:
            # 2. 存在しない場合は新規作成
            file_metadata = {
                'name': doc_title,
                'mimeType': 'application/vnd.google-apps.document',
                'parents': [folder_id]
            }
            file = drive_service.files().create(body=file_metadata, fields='id').execute()
            document_id = file.get('id')
            print(f"新規の日次サマリードキュメント '{doc_title}' (ID: {document_id}) を作成しました。")

        # 3. コンテンツを作成
        reuters_header = "Reuters ニュース (AI要約)"
        bloomberg_header = "Bloomberg ニュース (AI要約)"
        reuters_articles = [a for a in articles_with_summary if a.get('source') == 'Reuters']
        bloomberg_articles = [a for a in articles_with_summary if a.get('source') == 'Bloomberg']

        summary_text = format_articles_for_doc(reuters_articles, reuters_header, include_body=False)
        if reuters_articles and bloomberg_articles:
            summary_text += "\n\n\n"
        summary_text += format_articles_for_doc(bloomberg_articles, bloomberg_header, include_body=False)
        
        update_time_str = f"最終更新: {datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S JST')}\n\n"
        final_content = update_time_str + summary_text

        # 4. コンテンツを挿入
        if final_content.strip():
            requests_list = [{'insertText': {'location': {'index': 1}, 'text': final_content}}]
            docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests_list}).execute()
            print(f"ドキュメント (ID: {document_id}) への書き込みが完了しました。")
        else:
            print("書き込むコンテンツがないため、ドキュメントへの書き込みをスキップしました。")
        
        doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
        print(f"確認用URL: {doc_url}")
        return True

    except HttpError as error:
        print(f"日次サマリードキュメント処理中にAPIエラーが発生しました: {error}")
        print(f"HTTPステータスコード: {error.resp.status}")
        print(f"エラーレスポンス内容: {error.content}")
        print(f"エラー詳細: {error.error_details if hasattr(error, 'error_details') else 'N/A'}")
        
        if error.resp.status == 403:
            error_content_str = str(error.content)
            if 'storageQuotaExceeded' in error_content_str:
                print("\n*** Google Driveの保存容量が上限に達しているようです。 ***")
                print("サービスアカウントのDriveから不要なファイルを削除してください。")
            elif 'quotaExceeded' in error_content_str:
                print("\n*** Google Drive APIの使用量制限に達した可能性があります。 ***")
                print("しばらく時間をおいてから再実行してください。")
            elif 'insufficientPermissions' in error_content_str:
                print("\n*** Google Driveへのアクセス権限が不足しています。 ***")
                print("サービスアカウントに適切な権限が付与されているか確認してください。")
            else:
                print(f"\n*** 403エラーの詳細原因: {error_content_str} ***")
        elif error.resp.status == 404:
            print("\n*** 指定されたフォルダまたはドキュメントが見つかりません。 ***")
            print("GOOGLE_DRIVE_OUTPUT_FOLDER_IDの設定を確認してください。")
        
        return False
    except Exception as e:
        print(f"日次サマリードキュメント処理中に予期せぬエラーが発生しました: {e}")
        traceback.print_exc()
        return False

def format_articles_for_doc(articles_list: list, header: str, include_body: bool) -> str:
    """
    記事リストをGoogleドキュメント用にフォーマットする。
    include_bodyフラグで、記事本文（または要約）を含めるか制御する。
    """
    if not articles_list:
        return ""
    
    # 感情アイコンのマッピング
    sentiment_icons = {
        "Positive": "😊",
        "Negative": "😠",
        "Neutral": "😐",
        "N/A": "🤔",
        "Error": "⚠️"
    }
    
    text_parts = [f"{header}\n\n"]
    for i, article in enumerate(articles_list):
        pub_jst_str = article.get('published_jst').strftime('%Y-%m-%d %H:%M') if pd.notnull(article.get('published_jst')) else 'N/A'
        
        # 感情分析アイコンを追加
        sentiment_label = article.get('sentiment_label')
        icon = ""
        if sentiment_label:
            icon = sentiment_icons.get(sentiment_label, "🤔") + " "

        text_parts.append(f"({pub_jst_str}) {icon}{article.get('title', '[タイトル不明]')}\n")
        text_parts.append(f"{article.get('url', '[URL不明]')}\n")
        
        # include_bodyがTrueの場合は本文とAI処理結果の両方を出力
        if include_body:
            text_parts.append(f"\n--- 元記事 ---\n{article.get('body', '[本文なし]')}\n")
            if article.get('summary'):
                 text_parts.append(f"\n--- AI要約 ---\n{article.get('summary', '[要約なし]')}\n")
        # include_bodyがFalseの場合はAI要約のみ
        else:
            content = article.get('summary', '[要約なし]')
            text_parts.append(f"{content}\n")
        
        if i < len(articles_list) - 1:
            text_parts.append("\n--------------------------------------------------\n\n")
    return "".join(text_parts)
