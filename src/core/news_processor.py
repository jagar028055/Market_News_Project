# -*- coding: utf-8 -*-

"""
ニュース処理のメインロジック
"""

import os
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.logging_config import get_logger
from src.error_handling import ErrorContext, retry_with_backoff
from src.config import get_config
from scrapers import reuters, bloomberg
from gdocs import client
from ai_summarizer import process_article_with_ai
from src.html import HTMLGenerator


class NewsProcessor:
    """ニュース処理のメインクラス"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.folder_id = self.config.google.drive_output_folder_id
        self.gemini_api_key = self.config.ai.gemini_api_key
        
    def validate_environment(self) -> bool:
        """環境変数の検証"""
        if not self.folder_id or not self.gemini_api_key:
            self.logger.error("必要な環境変数が設定されていません")
            self.logger.error(f"GOOGLE_DRIVE_OUTPUT_FOLDER_ID: {self.folder_id}")
            self.logger.error(f"GEMINI_API_KEY: {'設定済み' if self.gemini_api_key else '未設定'}")
            return False
        return True
    
    def collect_articles(self) -> List[Dict[str, Any]]:
        """記事の収集"""
        self.logger.info(f"記事取得対象時間: 過去 {self.config.scraping.hours_limit} 時間以内")
        
        all_articles = []
        
        # ロイター記事収集
        try:
            reuters_articles = reuters.scrape_reuters_articles(
                query=self.config.reuters.query,
                hours_limit=self.config.scraping.hours_limit,
                max_pages=self.config.reuters.max_pages,
                items_per_page=self.config.reuters.items_per_page,
                target_categories=self.config.reuters.target_categories,
                exclude_keywords=self.config.reuters.exclude_keywords
            )
            self.logger.info(f"取得したロイター記事数: {len(reuters_articles)}")
            all_articles.extend(reuters_articles)
        except Exception as e:
            self.logger.error(f"ロイター記事取得エラー: {e}")
        
        # ブルームバーグ記事収集
        try:
            bloomberg_articles = bloomberg.scrape_bloomberg_top_page_articles(
                hours_limit=self.config.scraping.hours_limit,
                exclude_keywords=self.config.bloomberg.exclude_keywords
            )
            self.logger.info(f"取得したBloomberg記事数: {len(bloomberg_articles)}")
            all_articles.extend(bloomberg_articles)
        except Exception as e:
            self.logger.error(f"ブルームバーグ記事取得エラー: {e}")
        
        # 公開日時でソート
        return sorted(
            all_articles,
            key=lambda x: x.get('published_jst', datetime.min),
            reverse=True
        )
    
    def process_articles_with_ai(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """AI処理（要約と感情分析）"""
        self.logger.info("AIによる記事処理（要約＆感情分析）を開始")
        processed_articles = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_article = {
                executor.submit(process_article_with_ai, self.gemini_api_key, article.get('body', '')): article 
                for article in articles
            }
            
            for future in concurrent.futures.as_completed(future_to_article):
                original_article = future_to_article[future]
                processed_article = original_article.copy()
                
                try:
                    ai_result = future.result()
                    if ai_result:
                        processed_article.update(ai_result)
                    else:
                        self._set_fallback_ai_result(processed_article)
                except Exception as exc:
                    self.logger.error(f"記事 '{original_article.get('title', '不明')}' のAI処理エラー: {exc}")
                    self._set_error_ai_result(processed_article)
                
                processed_articles.append(processed_article)
        
        return sorted(
            processed_articles,
            key=lambda x: x.get('published_jst', datetime.min),
            reverse=True
        )
    
    def _set_fallback_ai_result(self, article: Dict[str, Any]) -> None:
        """AI処理失敗時のフォールバック"""
        article['summary'] = "AI処理に失敗しました。"
        article['sentiment_label'] = "N/A"
        article['sentiment_score'] = 0.0
    
    def _set_error_ai_result(self, article: Dict[str, Any]) -> None:
        """AI処理エラー時の設定"""
        article['summary'] = "AI処理中にエラーが発生しました。"
        article['sentiment_label'] = "Error"
        article['sentiment_score'] = 0.0
    
    def generate_html_output(self, articles: List[Dict[str, Any]]) -> None:
        """HTMLファイル生成"""
        self.logger.info("HTMLファイルの生成を開始")
        try:
            html_generator = HTMLGenerator(self.logger)
            html_generator.generate_html_file(articles, "index.html")
            self.logger.info("HTMLファイルの生成が完了しました")
        except Exception as e:
            self.logger.error(f"HTMLファイル生成エラー: {e}")
            raise
    
    def process_google_docs_output(self, articles: List[Dict[str, Any]]) -> None:
        """Google ドキュメント出力（認証情報がある場合のみ）"""
        self.logger.info("Googleドキュメントへの出力処理を開始します。")
        
        # Googleサービスへの認証
        drive_service, docs_service = client.authenticate_google_services()
        
        # 認証情報がない、または認証に失敗した場合は処理を中断
        if not drive_service or not docs_service:
            self.logger.warning("Google認証に失敗したため、ドキュメント出力をスキップします。")
            self.logger.warning("環境変数 'GOOGLE_SERVICE_ACCOUNT_JSON' が正しく設定されているか確認してください。")
            return
            
        self.logger.info("Google認証に成功しました。")

        # フォルダ接続テスト
        if not client.test_drive_connection(drive_service, self.folder_id):
            self.logger.error("Google Driveフォルダへの接続に失敗しました。処理を中断します。")
            return

        # ドキュメント更新処理
        try:
            all_success = True
            
            # 全文上書きドキュメント
            if self.config.google.overwrite_doc_id:
                if not client.update_google_doc_with_full_text(
                    docs_service,
                    self.config.google.overwrite_doc_id,
                    articles
                ):
                    all_success = False
            
            # 日次サマリードキュメント
            if not client.create_daily_summary_doc(
                drive_service,
                docs_service,
                articles,
                self.folder_id
            ):
                all_success = False

            if all_success:
                self.logger.info("Googleドキュメントの出力が正常に完了しました。")
            else:
                self.logger.error("Googleドキュメントの出力処理中に一部エラーが発生しました。詳細は前のログを確認してください。")

        except Exception as e:
            self.logger.error(f"Googleドキュメント出力中に予期せぬエラーが発生しました: {e}")
    
    def run(self) -> None:
        """メイン処理の実行"""
        self.logger.info("=== ニュース記事取得・ドキュメント出力処理開始 ===")
        
        try:
            # 環境変数検証
            if not self.validate_environment():
                return
            
            self.logger.info("環境変数チェック完了")
            self.logger.info("✓ プログラムを実行します...")
            
            # 記事収集
            articles = self.collect_articles()
            if not articles:
                self.logger.warning("収集された記事がありません")
                return
            
            self.logger.info(f"合計取得記事数: {len(articles)}")
            
            # AI処理
            processed_articles = self.process_articles_with_ai(articles)
            self.logger.info(f"処理完了記事数: {len(processed_articles)}")
            
            # HTML生成
            self.generate_html_output(processed_articles)
            
            # Google Docs出力（実行条件を満たす場合のみ）
            if self.config.is_document_creation_day_and_time:
                self.logger.info("実行条件を満たしているため、Googleドキュメントの処理を実行します。")
                self.process_google_docs_output(processed_articles)
            else:
                self.logger.info("ドキュメント生成はスキップされました（実行対象外の日時です）")
            
            self.logger.info("=== 全ての処理が完了しました ===")
            
        except Exception as e:
            self.logger.error(f"処理中にエラーが発生しました: {e}")
            raise
