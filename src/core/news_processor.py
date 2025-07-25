# -*- coding: utf-8 -*-

"""
ニュース処理のメインロジック
"""

import time
import logging
import concurrent.futures
from typing import List, Dict, Any
from datetime import datetime, timedelta

from src.logging_config import get_logger, log_with_context
from src.config.app_config import get_config, AppConfig
from src.database.database_manager import DatabaseManager
from src.database.models import Article, AIAnalysis
from scrapers import reuters, bloomberg
from ai_summarizer import process_article_with_ai
from src.html.html_generator import HTMLGenerator
from gdocs.client import authenticate_google_services, test_drive_connection, update_google_doc_with_full_text, create_daily_summary_doc


class NewsProcessor:
    """ニュース処理のメインクラス"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config: AppConfig = get_config()
        self.db_manager = DatabaseManager(self.config.database)
        self.html_generator = HTMLGenerator(self.logger)

    def validate_environment(self) -> bool:
        """環境変数の検証"""
        self.logger.info("=== 環境変数設定状況 ===")
        gemini_api_key = self.config.ai.gemini_api_key
        self.logger.info(f"GEMINI_API_KEY: {'設定済み' if gemini_api_key else '未設定'}")

        if not gemini_api_key:
            self.logger.error("必要な環境変数（GEMINI_API_KEY）が設定されていません")
            return False
        return True

    def collect_articles(self) -> List[Dict[str, Any]]:
        """スクレイピングによる記事の収集"""
        log_with_context(self.logger, logging.INFO, "記事収集開始", operation="collect_articles")
        
        all_articles = []
        
        # 各スクレイパーを並列実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Reutersには hours_limit パラメータを明示的に追加
            reuters_params = self.config.reuters.to_dict()
            reuters_params['hours_limit'] = self.config.scraping.hours_limit
            
            future_to_scraper = {
                executor.submit(reuters.scrape_reuters_articles, **reuters_params): "Reuters",
                executor.submit(bloomberg.scrape_bloomberg_top_page_articles, **self.config.bloomberg.to_dict()): "Bloomberg"
            }
            
            for future in concurrent.futures.as_completed(future_to_scraper):
                scraper_name = future_to_scraper[future]
                try:
                    articles = future.result()
                    log_with_context(self.logger, logging.INFO, f"{scraper_name} 記事取得完了", 
                                     operation="collect_articles", scraper=scraper_name, count=len(articles))
                    all_articles.extend(articles)
                except Exception as e:
                    log_with_context(self.logger, logging.ERROR, f"{scraper_name} 記事取得エラー",
                                     operation="collect_articles", scraper=scraper_name, error=str(e), exc_info=True)
        
        log_with_context(self.logger, logging.INFO, "記事収集完了", operation="collect_articles", total_count=len(all_articles))
        return all_articles

    def save_articles_to_db(self, articles: List[Dict[str, Any]]) -> List[int]:
        """収集した記事をデータベースに保存（重複は自動で排除）"""
        log_with_context(self.logger, logging.INFO, "記事のDB保存開始", operation="save_articles_to_db", count=len(articles))
        new_article_ids = []
        
        for article_data in articles:
            # データベースに保存し、新規かどうかを判定
            article_id, is_new = self.db_manager.save_article(article_data)
            if article_id and is_new:
                new_article_ids.append(article_id)

        log_with_context(self.logger, logging.INFO, "記事のDB保存完了", operation="save_articles_to_db", 
                         new_articles=len(new_article_ids), total_attempted=len(articles))
        return new_article_ids

    def process_new_articles_with_ai(self, new_article_ids: List[int]):
        """新規記事のみをAIで処理"""
        if not new_article_ids:
            log_with_context(self.logger, logging.INFO, "AI処理対象の新規記事なし", operation="process_new_articles")
            return

        log_with_context(self.logger, logging.INFO, f"AI処理開始（新規{len(new_article_ids)}件）", operation="process_new_articles")
        
        articles_to_process = self.db_manager.get_articles_by_ids(new_article_ids)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_article = {
                executor.submit(process_article_with_ai, self.config.ai.gemini_api_key, article.body): article
                for article in articles_to_process if article.body
            }

            for future in concurrent.futures.as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    ai_result = future.result()
                    if ai_result:
                        self.db_manager.save_ai_analysis(article.id, ai_result)
                        log_with_context(self.logger, logging.DEBUG, "AI分析結果を保存", article_id=article.id)
                except Exception as e:
                    log_with_context(self.logger, logging.ERROR, f"記事ID {article.id} のAI処理エラー",
                                     operation="process_new_articles", article_id=article.id, error=str(e), exc_info=True)

        log_with_context(self.logger, logging.INFO, "AI処理完了", operation="process_new_articles")

    def process_recent_articles_without_ai(self):
        """AI分析がない24時間以内の記事を処理"""
        # AI分析がない記事のIDを取得
        with self.db_manager.get_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.config.scraping.hours_limit)
            unprocessed_ids = session.query(Article.id).outerjoin(AIAnalysis).filter(
                Article.published_at >= cutoff_time,
                AIAnalysis.id.is_(None),
                Article.body.isnot(None),
                Article.body != ''
            ).all()
            unprocessed_ids = [row[0] for row in unprocessed_ids]
        
        if not unprocessed_ids:
            log_with_context(self.logger, logging.INFO, "AI処理対象の未処理記事なし", operation="process_recent_articles")
            return
        
        log_with_context(self.logger, logging.INFO, f"未処理記事のAI処理開始（{len(unprocessed_ids)}件）", operation="process_recent_articles")
        
        # 記事を取得してAI処理
        articles_to_process = self.db_manager.get_articles_by_ids(unprocessed_ids)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_article = {
                executor.submit(process_article_with_ai, self.config.ai.gemini_api_key, article.body): article
                for article in articles_to_process if article.body
            }

            for future in concurrent.futures.as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    ai_result = future.result()
                    if ai_result:
                        self.db_manager.save_ai_analysis(article.id, ai_result)
                        log_with_context(self.logger, logging.DEBUG, "AI分析結果を保存", article_id=article.id)
                except Exception as e:
                    log_with_context(self.logger, logging.ERROR, f"記事ID {article.id} のAI処理エラー",
                                     operation="process_recent_articles", article_id=article.id, error=str(e), exc_info=True)

        log_with_context(self.logger, logging.INFO, "未処理記事のAI処理完了", operation="process_recent_articles")

    def prepare_current_session_articles_for_html(self, scraped_articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """今回実行分の記事をHTML表示用に準備（AI分析結果と組み合わせ）"""
        log_with_context(self.logger, logging.INFO, "今回実行分記事のHTML用データ準備開始", operation="prepare_current_session_articles")
        
        current_session_articles = []
        
        for scraped_article in scraped_articles:
            # URLから記事をDBで検索し、AI分析結果を取得
            article_with_analysis = self.db_manager.get_article_by_url_with_analysis(scraped_article['url'])
            
            # 基本的な記事データを設定
            article_data = {
                "title": scraped_article.get("title", ""),
                "url": scraped_article.get("url", ""),
                "source": scraped_article.get("source", ""),
                "published_jst": scraped_article.get("published_jst", ""),
                "summary": "要約はありません。",
                "sentiment_label": "N/A",
                "sentiment_score": 0.0,
            }
            
            # AI分析結果が存在する場合は反映
            if article_with_analysis and article_with_analysis.ai_analysis:
                analysis = article_with_analysis.ai_analysis[0]  # 1対1関係
                article_data.update({
                    "summary": analysis.summary if analysis.summary else "要約はありません。",
                    "sentiment_label": analysis.sentiment_label if analysis.sentiment_label else "N/A",
                    "sentiment_score": analysis.sentiment_score if analysis.sentiment_score is not None else 0.0,
                })
            
            current_session_articles.append(article_data)
        
        log_with_context(self.logger, logging.INFO, "今回実行分記事のHTML用データ準備完了", 
                         operation="prepare_current_session_articles", count=len(current_session_articles))
        return current_session_articles

    def generate_final_html(self, current_session_articles: List[Dict[str, Any]] = None):
        """最終的なHTMLを生成（今回実行分の記事のみ）"""
        log_with_context(self.logger, logging.INFO, "最終HTML生成開始", operation="generate_final_html")
        
        # 今回実行分の記事が渡されない場合は空のHTMLを生成
        if not current_session_articles:
            log_with_context(self.logger, logging.WARNING, "HTML生成対象の記事なし", operation="generate_final_html")
            self.html_generator.generate_html_file([], "index.html")
            return

        # 今回実行分の記事をHTMLジェネレーター用に変換
        articles_for_html = []
        for article_data in current_session_articles:
            articles_for_html.append({
                "title": article_data.get("title", ""),
                "url": article_data.get("url", ""),
                "summary": article_data.get("summary", "要約はありません。"),
                "source": article_data.get("source", ""),
                "published_jst": article_data.get("published_jst", ""),
                "sentiment_label": article_data.get("sentiment_label", "N/A"),
                "sentiment_score": article_data.get("sentiment_score", 0.0),
            })
        
        self.html_generator.generate_html_file(articles_for_html, "index.html")
        log_with_context(self.logger, logging.INFO, "最終HTML生成完了", operation="generate_final_html", count=len(articles_for_html))

    def generate_google_docs(self):
        """Googleドキュメント生成処理"""
        # 時刻条件チェック
        if not self.config.google.is_document_creation_day_and_time():
            log_with_context(self.logger, logging.INFO, "Googleドキュメント生成条件未満（時刻・曜日制限）", operation="generate_google_docs")
            return

        log_with_context(self.logger, logging.INFO, "Googleドキュメント生成開始", operation="generate_google_docs")
        
        # Google認証
        drive_service, docs_service = authenticate_google_services()
        if not drive_service or not docs_service:
            log_with_context(self.logger, logging.ERROR, "Google認証に失敗", operation="generate_google_docs")
            return

        # 権限確認
        if not test_drive_connection(drive_service, self.config.google.drive_output_folder_id):
            log_with_context(self.logger, logging.ERROR, "Google Drive接続テスト失敗", operation="generate_google_docs")
            return

        # DBから過去24時間分の全記事を取得
        recent_articles = self.db_manager.get_recent_articles_all(hours=self.config.scraping.hours_limit)
        
        if not recent_articles:
            log_with_context(self.logger, logging.WARNING, "Googleドキュメント生成対象の記事なし", operation="generate_google_docs")
            return

        # 記事データを整形
        articles_for_docs = []
        articles_with_summary = []
        
        for a in recent_articles:
            analysis = a.ai_analysis[0] if a.ai_analysis else None
            
            # 全記事用（記事本文含む）
            article_data = {
                "title": a.title,
                "url": a.url,
                "source": a.source,
                "published_jst": a.published_at,
                "body": a.body,
                "summary": analysis.summary if analysis else None,
                "sentiment_label": analysis.sentiment_label if analysis else "N/A",
                "sentiment_score": analysis.sentiment_score if analysis else 0.0,
            }
            articles_for_docs.append(article_data)
            
            # AI要約がある記事のみ
            if analysis and analysis.summary:
                articles_with_summary.append(article_data)

        # 1. 既存ドキュメントの全削除・新規記載（全記事本文）
        if self.config.google.overwrite_doc_id:
            success = update_google_doc_with_full_text(
                docs_service, 
                self.config.google.overwrite_doc_id, 
                articles_for_docs
            )
            if success:
                log_with_context(self.logger, logging.INFO, "既存ドキュメント上書き完了", 
                                operation="generate_google_docs", doc_id=self.config.google.overwrite_doc_id)
            else:
                log_with_context(self.logger, logging.ERROR, "既存ドキュメント上書き失敗", 
                                operation="generate_google_docs", doc_id=self.config.google.overwrite_doc_id)

        # 2. AI要約の新規ドキュメント作成
        success = create_daily_summary_doc(
            drive_service,
            docs_service,
            articles_with_summary,
            self.config.google.drive_output_folder_id
        )
        if success:
            log_with_context(self.logger, logging.INFO, "日次サマリードキュメント作成完了", 
                            operation="generate_google_docs", ai_articles=len(articles_with_summary))
        else:
            log_with_context(self.logger, logging.ERROR, "日次サマリードキュメント作成失敗", 
                            operation="generate_google_docs")

    def run(self):
        """メイン処理の実行"""
        self.logger.info("=== ニュース記事取得・処理開始 ===")
        overall_start_time = time.time()
        
        # スクレイピングセッション開始
        session_id = self.db_manager.start_scraping_session()
        
        try:
            if not self.validate_environment():
                self.db_manager.complete_scraping_session(session_id, status='failed', error_details="環境変数未設定")
                return

            # 1. 記事収集
            scraped_articles = self.collect_articles()
            self.db_manager.update_scraping_session(session_id, articles_found=len(scraped_articles))
            if not scraped_articles:
                self.logger.warning("収集された記事がありません")
                self.db_manager.complete_scraping_session(session_id, status='completed_no_articles')
                self.generate_final_html([])  # 空リストを渡す
                return

            # 2. DBに保存 (重複排除)
            new_article_ids = self.save_articles_to_db(scraped_articles)
            self.db_manager.update_scraping_session(session_id, articles_processed=len(new_article_ids))

            # 3. 新規記事をAIで処理
            self.process_new_articles_with_ai(new_article_ids)
            
            # 3.5. AI分析がない24時間以内の記事も処理する
            self.process_recent_articles_without_ai()

            # 4. 今回実行分の記事データをAI分析結果と組み合わせて準備
            current_session_articles = self.prepare_current_session_articles_for_html(scraped_articles)

            # 5. 最終的なHTMLを生成（今回実行分のみ）
            self.generate_final_html(current_session_articles)
            
            # 6. Googleドキュメント生成（時刻条件満たす場合のみ）
            self.generate_google_docs()
            
            # 7. 古いデータをクリーンアップ
            self.db_manager.cleanup_old_data(days_to_keep=30)

            self.db_manager.complete_scraping_session(session_id, status='completed_ok')
            
        except Exception as e:
            self.logger.error(f"処理全体で予期せぬエラーが発生: {e}", exc_info=True)
            self.db_manager.complete_scraping_session(session_id, status='failed', error_details=str(e))
            raise
        finally:
            overall_elapsed_time = time.time() - overall_start_time
            self.logger.info(f"=== 全ての処理が完了しました (総処理時間: {overall_elapsed_time:.2f}秒) ===")