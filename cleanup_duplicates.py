#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
重複した日付のドキュメントを削除するスクリプト
"""

from gdocs.client import authenticate_google_services
from collections import defaultdict

def cleanup_duplicate_documents(drive_service, folder_id):
    """重複したドキュメントを削除（最新のみ保持）"""
    print("=== 重複ドキュメントのクリーンアップ ===")
    
    try:
        # フォルダ内のドキュメントを取得
        query = (
            f"'{folder_id}' in parents and "
            f"mimeType='application/vnd.google-apps.document' and "
            f"trashed=false"
        )
        
        response = drive_service.files().list(
            q=query,
            fields='files(id, name, createdTime)',
            orderBy='createdTime desc'
        ).execute()
        
        files = response.get('files', [])
        
        if not files:
            print("削除対象のファイルはありません。")
            return 0
        
        # 日付別にグループ化
        date_groups = defaultdict(list)
        for file in files:
            name = file.get('name', '')
            # ドキュメント名から日付を抽出（例: 20250710_Market_News_AI_Summary）
            if '_Market_News_AI_Summary' in name:
                date_part = name.split('_')[0]  # 20250710
                date_groups[date_part].append(file)
        
        deleted_count = 0
        
        # 各日付グループで重複を削除
        for date, group_files in date_groups.items():
            if len(group_files) > 1:
                print(f"\n日付 {date}: {len(group_files)}件の重複を発見")
                
                # 作成日時で降順ソート（最新が先頭）
                group_files.sort(key=lambda x: x['createdTime'], reverse=True)
                
                # 最新以外を削除
                keep_file = group_files[0]
                delete_files = group_files[1:]
                
                print(f"保持: {keep_file['name']} (作成日: {keep_file['createdTime']})")
                
                for file in delete_files:
                    try:
                        drive_service.files().delete(fileId=file['id']).execute()
                        print(f"削除: {file['name']} (作成日: {file['createdTime']})")
                        deleted_count += 1
                    except Exception as e:
                        print(f"削除失敗: {file['name']} - {e}")
            else:
                print(f"日付 {date}: 重複なし")
        
        print(f"\nクリーンアップ完了: {deleted_count}件の重複ファイルを削除しました。")
        return deleted_count
        
    except Exception as e:
        print(f"重複削除中にエラーが発生しました: {e}")
        return 0

def main():
    # Google認証
    drive_service, _ = authenticate_google_services()
    if not drive_service:
        print("ERROR: Google認証に失敗しました")
        return
    
    # 対象フォルダID（設定から取得）
    from src.config.app_config import get_config
    config = get_config()
    folder_id = "0ADPc94RF26tLUk9PVA"  # スキャン結果から判明した実際のフォルダID
    
    print(f"対象フォルダID: {folder_id}")
    
    cleanup_duplicate_documents(drive_service, folder_id)

if __name__ == "__main__":
    main()