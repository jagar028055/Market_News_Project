# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv

# --- 設定とモジュールのインポート ---
# .envファイルから環境変数を読み込む
load_dotenv()

# プロジェクトモジュール
import config
from scrapers import reuters, bloomberg
from gdocs import client

def main():
    """
    スクリプト全体のメイン処理を実行する
    """
    print("=== ニュース記事取得・ドキュメント出力処理開始 ===")

    # --- 1. 事前チェックと認証 ---
    # .envからGoogle DriveのフォルダIDを取得
    folder_id = os.getenv("GOOGLE_DRIVE_OUTPUT_FOLDER_ID")
    if not folder_id or "YOUR_FOLDER_ID" in folder_id:
        print("\n!!!!!!!!!!!!!!!!!! 設定エラー !!!!!!!!!!!!!!!!!!")
        print("'.env'ファイルに 'GOOGLE_DRIVE_OUTPUT_FOLDER_ID' が設定されていません。")
        print("'.env'ファイルを開き、ご自身のGoogle DriveのフォルダIDに書き換えてください。")
        print("例: GOOGLE_DRIVE_OUTPUT_FOLDER_ID=\"1aBcDeFgHiJkLmNoPqRsTuVwXyZ123456\"")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        return

    # Googleサービスへの認証を先に行う
    print("\n--- Googleサービスへの認証を行います ---")
    drive_service, docs_service = client.authenticate_google_services()

    # 認証が失敗した場合はスクリプトを中止
    if not drive_service or not docs_service:
        print("\n!!!!!!!!!!!!!!!!!! 認証失敗 !!!!!!!!!!!!!!!!!!")
        print("Googleサービスへの認証に失敗しました。処理を中止します。")
        print("コンソールに出力された指示に従い、'credentials.json'を配置してください。")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        return

    # --- 2. メインのスクレイピング処理 ---
    print(f"\n記事取得対象時間: 過去 {config.HOURS_LIMIT} 時間以内")
    
    # ロイターの記事をスクレイピング
    fetched_reuters_articles = reuters.scrape_reuters_articles(
        query=config.REUTERS_CONFIG["query"],
        hours_limit=config.HOURS_LIMIT,
        max_pages=config.REUTERS_CONFIG["max_pages"],
        items_per_page=config.REUTERS_CONFIG["items_per_page"],
        target_categories=config.REUTERS_CONFIG["target_categories"],
        exclude_keywords=config.REUTERS_CONFIG["exclude_keywords"]
    )
    print(f"取得したロイター記事数: {len(fetched_reuters_articles)}")

    # ブルームバーグの記事をスクレイピング
    fetched_bloomberg_articles = bloomberg.scrape_bloomberg_top_page_articles(
        hours_limit=config.HOURS_LIMIT,
        exclude_keywords=config.BLOOMBERG_CONFIG["exclude_keywords"]
    )
    print(f"取得したBloomberg記事数: {len(fetched_bloomberg_articles)}")

    # --- 3. Googleドキュメントへ出力 ---
    client.export_all_news_to_one_document(
        drive_service=drive_service,
        docs_service=docs_service,
        reuters_articles=fetched_reuters_articles,
        bloomberg_articles=fetched_bloomberg_articles,
        folder_id=folder_id
    )
    
    print("\n=== 全ての処理が完了しました ===")

if __name__ == "__main__":
    main()
