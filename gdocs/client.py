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
SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/docs", "https://www.googleapis.com/auth/spreadsheets"]
# サービスアカウントキーのファイルパス。環境変数から取得、なければデフォルト値を使用
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
# 環境変数からサービスアカウントのJSON文字列を直接読み込む場合
SERVICE_ACCOUNT_JSON_STR = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

def cleanup_old_drive_documents(drive_service, folder_id: str, days_to_keep: int = 30) -> int:
    """
    指定されたフォルダ内の古いドキュメントを削除する。
    
    Args:
        drive_service: Google Drive APIサービス
        folder_id: 対象フォルダのID
        days_to_keep: 保持する日数（デフォルト: 30日）
    
    Returns:
        int: 削除したファイル数
    """
    from datetime import datetime, timedelta
    import pytz
    
    print(f"\n--- Google Drive古いドキュメントのクリーンアップ（{days_to_keep}日より古いファイル） ---")
    
    try:
        # 保持期限を計算
        jst = pytz.timezone('Asia/Tokyo')
        cutoff_date = datetime.now(jst) - timedelta(days=days_to_keep)
        cutoff_date_str = cutoff_date.isoformat()
        
        print(f"削除対象: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S JST')} より古いファイル")
        
        # 古いドキュメントを検索
        query = (
            f"'{folder_id}' in parents and "
            f"mimeType='application/vnd.google-apps.document' and "
            f"trashed=false and "
            f"createdTime < '{cutoff_date_str}'"
        )
        
        response = drive_service.files().list(
            q=query,
            fields='files(id, name, createdTime)',
            orderBy='createdTime asc'
        ).execute()
        
        old_files = response.get('files', [])
        deleted_count = 0
        
        if not old_files:
            print("削除対象のファイルはありません。")
            return 0
        
        print(f"削除対象ファイル: {len(old_files)}件")
        
        # ファイルを削除
        for file in old_files:
            try:
                drive_service.files().delete(fileId=file['id']).execute()
                print(f"削除完了: {file['name']} (作成日: {file['createdTime']})")
                deleted_count += 1
            except Exception as e:
                print(f"削除失敗: {file['name']} - {e}")
        
        print(f"クリーンアップ完了: {deleted_count}件のファイルを削除しました。")
        return deleted_count
        
    except Exception as e:
        print(f"ドキュメントクリーンアップ中にエラーが発生しました: {e}")
        return 0

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

def create_daily_summary_doc_with_cleanup_retry(drive_service, docs_service, articles_with_summary: list, folder_id: str, retention_days: int = 30) -> bool:
    """
    AI要約を含む日次サマリードキュメントを作成・更新する（容量エラー時の自動クリーンアップ・リトライ付き）。
    """
    # 最初の試行
    success = create_daily_summary_doc(drive_service, docs_service, articles_with_summary, folder_id)
    
    if success:
        return True
    
    # 失敗した場合、クリーンアップしてリトライ
    print("\n--- 容量エラーのため古いドキュメントをクリーンアップしてリトライします ---")
    try:
        deleted_count = cleanup_old_drive_documents(drive_service, folder_id, retention_days)
        if deleted_count > 0:
            print(f"{deleted_count}件のファイルを削除しました。再実行します...")
            return create_daily_summary_doc(drive_service, docs_service, articles_with_summary, folder_id)
        else:
            print("削除できるファイルがありませんでした。")
            return False
    except Exception as e:
        print(f"クリーンアップ・リトライ中にエラーが発生しました: {e}")
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
        
        # include_bodyがTrueの場合は記事全文のみ出力（要約重複削除）
        if include_body:
            text_parts.append(f"\n--- 記事全文 ---\n{article.get('body', '[本文なし]')}\n")
        # include_bodyがFalseの場合はAI要約のみ
        else:
            content = article.get('summary', '[要約なし]')
            text_parts.append(f"{content}\n")
        
        if i < len(articles_list) - 1:
            text_parts.append("\n--------------------------------------------------\n\n")
    return "".join(text_parts)


# === Google Sheets API機能とデバッグ用スプレッドシート ===

def authenticate_google_services():
    """
    Google Drive、Docs、Sheets APIの統合認証
    設定に応じてOAuth2認証またはサービスアカウント認証を使用する。
    
    Returns:
        tuple: (drive_service, docs_service, sheets_service) または (None, None, None)
    """
    print("Google Services統合認証を開始します...")
    
    # 認証方式を判定
    auth_method = os.getenv('GOOGLE_AUTH_METHOD', 'service_account')
    print(f"認証方式: {auth_method}")
    
    # OAuth2認証を使用
    if auth_method == "oauth2":
        from .oauth2_client import authenticate_google_services_oauth2
        return authenticate_google_services_oauth2()
    
    # サービスアカウント認証を使用（デフォルト/フォールバック）
    creds = None
    try:
        # 環境変数 GOOGLE_SERVICE_ACCOUNT_JSON から認証情報を取得
        if SERVICE_ACCOUNT_JSON_STR:
            try:
                service_account_info = json.loads(SERVICE_ACCOUNT_JSON_STR)
                creds = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=SCOPES
                )
                print("環境変数から認証情報を読み込みました（Drive + Docs + Sheets対応）")
            except json.JSONDecodeError as e:
                print(f"認証エラー: JSON形式が正しくありません: {e}")
                return None, None, None
        
        # フォールバック: ファイルから読み込み
        elif os.path.exists(SERVICE_ACCOUNT_FILE):
            try:
                creds = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_FILE, scopes=SCOPES
                )
                print(f"ファイル '{SERVICE_ACCOUNT_FILE}' から認証情報を読み込みました")
            except Exception as e:
                print(f"認証エラー: ファイル読み込み失敗: {e}")
                return None, None, None
        
        else:
            print("認証エラー: 認証情報が見つかりません")
            return None, None, None

        # 各サービスを構築
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        print("✅ Google Drive、Docs、Sheets API認証完了")
        return drive_service, docs_service, sheets_service

    except Exception as e:
        print(f"認証中に予期せぬエラーが発生: {e}")
        return None, None, None


def create_debug_spreadsheet(sheets_service, drive_service, folder_id: str, session_id: int) -> str:
    """
    記事データ用スプレッドシートを作成
    
    Args:
        sheets_service: Google Sheets APIサービス
        drive_service: Google Drive APIサービス  
        folder_id: 作成先フォルダID
        session_id: セッションID
    
    Returns:
        str: 作成されたスプレッドシートのID
    """
    try:
        # スプレッドシート作成
        jst = pytz.timezone('Asia/Tokyo')
        timestamp = datetime.now(jst).strftime('%Y%m%d_%H%M%S')
        title = f"Market_News_Articles_{timestamp}_Session{session_id}"
        
        spreadsheet = {
            'properties': {
                'title': title
            },
            'sheets': [{
                'properties': {
                    'title': 'Articles_Data',
                    'gridProperties': {
                        'columnCount': 11,
                        'rowCount': 1000
                    }
                }
            }]
        }
        
        spreadsheet_result = sheets_service.spreadsheets().create(
            body=spreadsheet
        ).execute()
        
        spreadsheet_id = spreadsheet_result['spreadsheetId']
        print(f"✅ 記事データスプレッドシート作成: {title}")
        
        # 指定フォルダに移動
        if folder_id:
            drive_service.files().update(
                fileId=spreadsheet_id,
                addParents=folder_id,
                removeParents='root'
            ).execute()
            print(f"✅ スプレッドシートを指定フォルダに移動完了")
        
        return spreadsheet_id
        
    except Exception as e:
        print(f"❌ 記事データスプレッドシート作成エラー: {e}")
        return None

def create_api_usage_spreadsheet(sheets_service, drive_service, folder_id: str) -> str:
    """
    API使用量トラッキング用スプレッドシートを作成
    
    Args:
        sheets_service: Google Sheets APIサービス
        drive_service: Google Drive APIサービス  
        folder_id: 作成先フォルダID
    
    Returns:
        str: 作成されたスプレッドシートのID
    """
    try:
        title = "Market_News_API_Usage_Tracker"
        
        # マルチシートスプレッドシート作成
        spreadsheet = {
            'properties': {
                'title': title
            },
            'sheets': [
                {
                    'properties': {
                        'title': 'API_Usage_Log',
                        'gridProperties': {
                            'columnCount': 9,
                            'rowCount': 10000,
                            'frozenRowCount': 1
                        }
                    }
                },
                {
                    'properties': {
                        'title': 'Monthly_Summary',
                        'gridProperties': {
                            'columnCount': 6,
                            'rowCount': 100
                        }
                    }
                },
                {
                    'properties': {
                        'title': 'Cost_Analysis',
                        'gridProperties': {
                            'columnCount': 8,
                            'rowCount': 500
                        }
                    }
                }
            ]
        }
        
        spreadsheet_result = sheets_service.spreadsheets().create(
            body=spreadsheet
        ).execute()
        
        spreadsheet_id = spreadsheet_result['spreadsheetId']
        print(f"✅ API使用量スプレッドシート作成: {title}")
        
        # 指定フォルダに移動
        if folder_id:
            drive_service.files().update(
                fileId=spreadsheet_id,
                addParents=folder_id,
                removeParents='root'
            ).execute()
            print(f"✅ スプレッドシートを指定フォルダに移動完了")
        
        # 各シートにヘッダーを設定
        _setup_api_usage_sheet_headers(sheets_service, spreadsheet_id)
        
        return spreadsheet_id
        
    except Exception as e:
        print(f"❌ API使用量スプレッドシート作成エラー: {e}")
        return None

def _setup_api_usage_sheet_headers(sheets_service, spreadsheet_id: str):
    """API使用量スプレッドシートのヘッダーを設定"""
    try:
        requests = []
        
        # API_Usage_Logシートのヘッダー
        api_log_headers = [
            "日時(JST)", "モデル名", "API種別", "リクエスト回数", "入力トークン", 
            "出力トークン", "推定コスト(USD)", "セッションID", "累積月間コスト(USD)"
        ]
        
        # Monthly_Summaryシートのヘッダー
        monthly_headers = [
            "年月", "総リクエスト数", "総トークン数", "総コスト(USD)", "平均コスト/日", "備考"
        ]
        
        # Cost_Analysisシートのヘッダー
        cost_headers = [
            "日付", "モデル別コスト", "API種別コスト", "効率指標", "予算進捗", "アラート", "推奨アクション", "メモ"
        ]
        
        # シートIDを取得
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        
        for sheet in sheets:
            sheet_title = sheet['properties']['title']
            sheet_id = sheet['properties']['sheetId']
            
            if sheet_title == 'API_Usage_Log':
                headers = api_log_headers
            elif sheet_title == 'Monthly_Summary':
                headers = monthly_headers
            elif sheet_title == 'Cost_Analysis':
                headers = cost_headers
            else:
                continue
                
            # ヘッダー行を追加
            requests.extend([
                {
                    'updateCells': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': len(headers)
                        },
                        'rows': [{
                            'values': [{'userEnteredValue': {'stringValue': header}} for header in headers]
                        }],
                        'fields': 'userEnteredValue'
                    }
                },
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': len(headers)
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
                                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                    }
                }
            ])
        
        # バッチ更新を実行
        if requests:
            body = {'requests': requests}
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            print(f"✅ API使用量スプレッドシートヘッダー設定完了")
        
    except Exception as e:
        print(f"API使用量スプレッドシートヘッダー設定エラー: {e}")


def update_debug_spreadsheet(sheets_service, spreadsheet_id: str, debug_data: list):
    """
    記事データをスプレッドシートに書き込み
    
    Args:
        sheets_service: Google Sheets APIサービス
        spreadsheet_id: スプレッドシートID
        debug_data: 記事データ（ヘッダー + データ行のリスト）
    """
    try:
        if not debug_data:
            print("❌ 記事データが空です")
            return False
            
        # データ範囲を指定してバッチ更新
        range_name = f'Articles_Data!A1:{chr(ord("A") + len(debug_data[0]) - 1)}{len(debug_data)}'
        
        body = {
            'values': debug_data
        }
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        # ヘッダー行と記事データのフォーマット設定
        format_articles_spreadsheet(sheets_service, spreadsheet_id, len(debug_data))
        
        print(f"✅ 記事データ書き込み完了: {len(debug_data)-1}件の記事データ")
        return True
        
    except Exception as e:
        print(f"❌ 記事データ書き込みエラー: {e}")
        return False

def format_articles_spreadsheet(sheets_service, spreadsheet_id: str, data_rows: int):
    """記事データスプレッドシートのフォーマット設定"""
    try:
        # シートIDを取得
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        sheet_id = sheets[0]['properties']['sheetId']  # 最初のシート

        requests = []
        
        # ヘッダー行の書式設定
        requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.1, 'green': 0.4, 'blue': 0.6},
                        'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                        'horizontalAlignment': 'CENTER'
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
            }
        })
        
        # データ行の条件付き書式設定（地域別色分け）
        requests.extend([
            # 日本関連記事の色分け
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1, 'endRowIndex': data_rows, 'startColumnIndex': 0, 'endColumnIndex': 11}],
                        'booleanRule': {
                            'condition': {'type': 'TEXT_CONTAINS', 'values': [{'userEnteredValue': 'japan'}]},
                            'format': {'backgroundColor': {'red': 1.0, 'green': 0.9, 'blue': 0.9}}
                        }
                    },
                    'index': 0
                }
            },
            # アメリカ関連記事の色分け
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1, 'endRowIndex': data_rows, 'startColumnIndex': 0, 'endColumnIndex': 11}],
                        'booleanRule': {
                            'condition': {'type': 'TEXT_CONTAINS', 'values': [{'userEnteredValue': 'usa'}]},
                            'format': {'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 1.0}}
                        }
                    },
                    'index': 1
                }
            },
            # 中国関連記事の色分け
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{'sheetId': sheet_id, 'startRowIndex': 1, 'endRowIndex': data_rows, 'startColumnIndex': 0, 'endColumnIndex': 11}],
                        'booleanRule': {
                            'condition': {'type': 'TEXT_CONTAINS', 'values': [{'userEnteredValue': 'china'}]},
                            'format': {'backgroundColor': {'red': 1.0, 'green': 1.0, 'blue': 0.9}}
                        }
                    },
                    'index': 2
                }
            }
        ])
        
        # 列幅の自動調整
        requests.append({
            'autoResizeDimensions': {
                'dimensions': {
                    'sheetId': sheet_id,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': 11
                }
            }
        })
        
        # フィルターの追加
        requests.append({
            'setBasicFilter': {
                'filter': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': data_rows,
                        'startColumnIndex': 0,
                        'endColumnIndex': 11
                    }
                }
            }
        })
        
        body = {'requests': requests}
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        print(f"✅ 記事データスプレッドシート書式設定完了")
        
    except Exception as e:
        print(f"記事データスプレッドシート書式設定エラー: {e}")


def format_header_row(sheets_service, spreadsheet_id: str):
    """ヘッダー行の書式設定"""
    try:
        requests = [{
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8},
                        'textFormat': {'bold': True}
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
            }
        }]
        
        body = {'requests': requests}
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
    except Exception as e:
        print(f"ヘッダー書式設定エラー: {e}")


def get_spreadsheet_url(spreadsheet_id: str) -> str:
    """スプレッドシートのURLを生成"""
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
