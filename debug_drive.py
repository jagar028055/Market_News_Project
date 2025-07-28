#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
サービスアカウントのGoogle Drive情報を確認するためのデバッグスクリプト
"""

from gdocs.client import authenticate_google_services, debug_drive_storage_info
from src.config.app_config import get_config

def main():
    print("=== サービスアカウントGoogle Drive情報確認 ===")
    
    # 設定読み込み
    config = get_config()
    
    # Google認証
    drive_service, docs_service = authenticate_google_services()
    if not drive_service:
        print("ERROR: Google認証に失敗しました")
        return
    
    # Drive情報をデバッグ出力
    debug_drive_storage_info(drive_service)
    
    # 対象フォルダ内のファイル詳細も表示
    print(f"\n=== 対象フォルダ内のファイル詳細 ===")
    print(f"フォルダID: {config.google.drive_output_folder_id}")
    
    try:
        # 対象フォルダ内の全ファイルを取得
        query = f"'{config.google.drive_output_folder_id}' in parents and trashed=false"
        response = drive_service.files().list(
            q=query,
            fields="files(id, name, size, createdTime, modifiedTime, mimeType)",
            orderBy="createdTime desc"
        ).execute()
        
        files = response.get('files', [])
        total_size = 0
        
        if not files:
            print("対象フォルダにファイルがありません。")
        else:
            print(f"フォルダ内ファイル数: {len(files)}件")
            print("\n--- ファイル詳細 ---")
            for file in files:
                file_size = int(file.get('size', 0)) if file.get('size') else 0
                total_size += file_size
                size_mb = file_size / (1024 * 1024) if file_size > 0 else 0
                
                print(f"名前: {file.get('name')}")
                print(f"  ID: {file.get('id')}")
                print(f"  サイズ: {file_size:,} bytes ({size_mb:.2f} MB)")
                print(f"  作成日: {file.get('createdTime')}")
                print(f"  更新日: {file.get('modifiedTime')}")
                print(f"  種類: {file.get('mimeType')}")
                print("  ---")
            
            total_mb = total_size / (1024 * 1024)
            print(f"\n合計サイズ: {total_size:,} bytes ({total_mb:.2f} MB)")
    
    except Exception as e:
        print(f"フォルダ情報の取得中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()