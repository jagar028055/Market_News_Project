#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
サービスアカウントのGoogle Drive全体をスキャンして容量使用状況を詳細に調査
"""

from gdocs.client import authenticate_google_services
from datetime import datetime
import pytz

def scan_all_files(drive_service):
    """サービスアカウントの全ファイルを詳細スキャン"""
    print("=== Google Drive全ファイルスキャン ===")
    
    try:
        # 全ファイル（ゴミ箱含む）を取得
        all_files = []
        page_token = None
        
        while True:
            response = drive_service.files().list(
                fields="nextPageToken, files(id, name, size, createdTime, modifiedTime, mimeType, trashed, parents)",
                pageSize=100,
                pageToken=page_token
            ).execute()
            
            files = response.get('files', [])
            all_files.extend(files)
            page_token = response.get('nextPageToken')
            
            if not page_token:
                break
        
        print(f"総ファイル数: {len(all_files)}件")
        
        # ファイルを分類
        active_files = [f for f in all_files if not f.get('trashed', False)]
        trashed_files = [f for f in all_files if f.get('trashed', False)]
        
        print(f"アクティブファイル: {len(active_files)}件")
        print(f"ゴミ箱ファイル: {len(trashed_files)}件")
        
        # 容量計算
        total_size = 0
        active_size = 0
        trashed_size = 0
        
        print("\n=== アクティブファイル詳細 ===")
        for file in active_files:
            file_size = int(file.get('size', 0)) if file.get('size') else 0
            total_size += file_size
            active_size += file_size
            
            size_mb = file_size / (1024 * 1024) if file_size > 0 else 0
            parents = file.get('parents', [])
            parent_info = f"親フォルダ: {parents[0] if parents else 'なし'}"
            
            print(f"名前: {file.get('name')}")
            print(f"  サイズ: {file_size:,} bytes ({size_mb:.2f} MB)")
            print(f"  作成日: {file.get('createdTime')}")
            print(f"  種類: {file.get('mimeType')}")
            print(f"  {parent_info}")
            print("  ---")
        
        print("\n=== ゴミ箱ファイル詳細 ===")
        for file in trashed_files:
            file_size = int(file.get('size', 0)) if file.get('size') else 0
            total_size += file_size
            trashed_size += file_size
            
            size_mb = file_size / (1024 * 1024) if file_size > 0 else 0
            
            print(f"名前: {file.get('name')} (削除済み)")
            print(f"  サイズ: {file_size:,} bytes ({size_mb:.2f} MB)")
            print(f"  作成日: {file.get('createdTime')}")
            print(f"  種類: {file.get('mimeType')}")
            print("  ---")
        
        print(f"\n=== 容量サマリー ===")
        print(f"アクティブファイル合計: {active_size:,} bytes ({active_size/(1024*1024):.2f} MB)")
        print(f"ゴミ箱ファイル合計: {trashed_size:,} bytes ({trashed_size/(1024*1024):.2f} MB)")
        print(f"総使用容量: {total_size:,} bytes ({total_size/(1024*1024):.2f} MB)")
        
        # ゴミ箱削除の提案
        if trashed_size > 0:
            print(f"\n💡 ゴミ箱に {trashed_size:,} bytes のファイルがあります。")
            print("   完全削除すれば容量を確保できる可能性があります。")
        
    except Exception as e:
        print(f"ファイルスキャン中にエラーが発生しました: {e}")

def main():
    # Google認証
    drive_service, _ = authenticate_google_services()
    if not drive_service:
        print("ERROR: Google認証に失敗しました")
        return
    
    scan_all_files(drive_service)

if __name__ == "__main__":
    main()