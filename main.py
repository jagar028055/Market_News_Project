# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv
import concurrent.futures # 並行処理のために追加
from datetime import datetime # datetimeをインポート

# --- 設定とモジュールのインポート ---
# .envファイルから環境変数を読み込む
load_dotenv()

# プロジェクトモジュール
import config
from scrapers import reuters, bloomberg
from gdocs import client
from ai_summarizer import summarize_text # 追加
from html_generator import create_html_file # 追加

def main():
    """
    スクリプト全体のメイン処理を実行する
    """
    print("=== ニュース記事取得・ドキュメント出力処理開始 ===")

    # --- 1. 事前チェックと認証 ---
    # .envからGoogle DriveのフォルダIDとGemini APIキーを取得
    folder_id = os.getenv("GOOGLE_DRIVE_OUTPUT_FOLDER_ID")
    gemini_api_key = os.getenv("GEMINI_API_KEY") # 追加

    if not folder_id or "YOUR_FOLDER_ID" in folder_id:
        print("\n!!!!!!!!!!!!!!!!!! 設定エラー !!!!!!!!!!!!!!!!!!")
        print("'.env'ファイルに 'GOOGLE_DRIVE_OUTPUT_FOLDER_ID' が設定されていません。")
        print("'.env'ファイルを開き、ご自身のGoogle DriveのフォルダIDに書き換えてください。")
        print("例: GOOGLE_DRIVE_OUTPUT_FOLDER_ID=\"1aBcDeFgHiJkLmNoPqRsTuVwXyZ123456\"")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        return
    
    if not gemini_api_key: # 追加
        print("\n!!!!!!!!!!!!!!!!!! 設定エラー !!!!!!!!!!!!!!!!!!")
        print("'.env'ファイルに 'GEMINI_API_KEY' が設定されていません。")
        print("Google AI StudioでAPIキーを取得し、'.env'ファイルに設定してください。")
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

    # 全記事を結合し、公開日時でソート
    all_articles = sorted(
        fetched_reuters_articles + fetched_bloomberg_articles,
        key=lambda x: x.get('published_jst', datetime.min), # datetime.minはNoneの場合のフォールバック
        reverse=True
    )
    print(f"\n合計取得記事数: {len(all_articles)}")

    # --- 3. AIによる記事要約とHTML生成 ---
    print("\n--- AIによる記事要約を開始します ---")
    articles_with_summary = []
    # ThreadPoolExecutorを使って要約処理を並行実行
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor: # 同時実行数を調整
        future_to_article = {executor.submit(summarize_text, gemini_api_key, article.get('body', '')): article for article in all_articles}
        for future in concurrent.futures.as_completed(future_to_article):
            original_article = future_to_article[future]
            try:
                summary = future.result()
                original_article['summary'] = summary
                articles_with_summary.append(original_article)
            except Exception as exc:
                print(f"記事 '{original_article.get('title', '不明なタイトル')}' の要約中にエラーが発生しました: {exc}")
                original_article['summary'] = "要約の生成に失敗しました。" # エラー時のフォールバック
                articles_with_summary.append(original_article)
    
    # 要約された記事を再度公開日時でソート（並行処理で順序が崩れる可能性があるため）
    articles_with_summary = sorted(
        articles_with_summary,
        key=lambda x: x.get('published_jst', datetime.min),
        reverse=True
    )

    print(f"要約完了記事数: {len(articles_with_summary)}")

    print("\n--- HTMLファイルの生成を開始します ---")
    create_html_file(articles_with_summary, "index.html") # index.htmlを生成

    # --- 4. Googleドキュメントへ出力 (並行処理) ---
    # ドキュメント出力は時間がかかる可能性があるため、要約・HTML生成と並行して実行
    # ただし、ここではメインスレッドで実行し、処理の完了を待つ
    # 実際の並行処理はGitHub Actionsで複数のステップに分けることで実現可能
    print("\n--- Googleドキュメントへの出力を開始します (バックアップ/ログ用) ---")
    client.export_all_news_to_one_document(
        drive_service=drive_service,
        docs_service=docs_service,
        reuters_articles=fetched_reuters_articles, # 元のスクレイピング結果を渡す
        bloomberg_articles=fetched_bloomberg_articles, # 元のスクレイピング結果を渡す
        folder_id=folder_id
    )
    
    print("\n=== 全ての処理が完了しました ===")

if __name__ == "__main__":
    main()
