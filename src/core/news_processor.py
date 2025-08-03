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
from gdocs.client import authenticate_google_services, test_drive_connection, update_google_doc_with_full_text, create_daily_summary_doc_with_cleanup_retry, debug_drive_storage_info, cleanup_old_drive_documents


class NewsProcessor:
    """ニュース処理のメインクラス"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config: AppConfig = get_config()
        self.db_manager = DatabaseManager(self.config.database)
        self.html_generator = HTMLGenerator(self.logger)
        
        # 動的記事取得機能で使用する属性
        self.folder_id = self.config.google.drive_output_folder_id
        self.gemini_api_key = self.config.ai.gemini_api_key

    def validate_environment(self) -> bool:
        """環境変数の検証"""
        self.logger.info("=== 環境変数設定状況 ===")
        self.logger.info(f"GOOGLE_DRIVE_OUTPUT_FOLDER_ID: {'設定済み' if self.folder_id else '未設定'}")
        self.logger.info(f"GOOGLE_OVERWRITE_DOC_ID: {'設定済み' if self.config.google.overwrite_doc_id else '未設定'}")
        self.logger.info(f"GEMINI_API_KEY: {'設定済み' if self.gemini_api_key else '未設定'}")
        self.logger.info(f"GOOGLE_SERVICE_ACCOUNT_JSON: {'設定済み' if self.config.google.service_account_json else '未設定'}")
        
        # 動的記事取得設定の表示
        self.logger.info("=== 動的記事取得設定 ===")
        self.logger.info(f"基本時間範囲: {self.config.scraping.hours_limit}時間")
        self.logger.info(f"最低記事数閾値: {self.config.scraping.minimum_article_count}件")
        self.logger.info(f"最大時間範囲: {self.config.scraping.max_hours_limit}時間")
        self.logger.info(f"週末拡張時間: {self.config.scraping.weekend_hours_extension}時間")
        
        if not self.gemini_api_key:
            self.logger.error("必要な環境変数（GEMINI_API_KEY）が設定されていません")
            return False
        return True
    
    def get_dynamic_hours_limit(self) -> int:
        """
        曜日と記事数に基づく動的時間範囲決定
        
        Returns:
            int: 動的に決定された時間範囲（時間）
        """
        from datetime import datetime
        import pytz
        
        jst_tz = pytz.timezone('Asia/Tokyo')
        jst_now = datetime.now(jst_tz)
        weekday = jst_now.weekday()  # 月曜日=0, 日曜日=6
        
        # 月曜日は自動的に最大時間範囲を適用
        if weekday == 0:  # Monday
            self.logger.info(f"月曜日検出: 自動的に{self.config.scraping.max_hours_limit}時間範囲を適用")
            return self.config.scraping.max_hours_limit
        
        # 平日は基本時間範囲から開始
        return self.config.scraping.hours_limit
    
    def collect_articles_with_dynamic_range(self) -> List[Dict[str, Any]]:
        """
        動的時間範囲を使用した記事収集
        記事数が不足している場合は段階的に時間範囲を拡張
        """
        initial_hours = self.get_dynamic_hours_limit()
        current_hours = initial_hours
        
        self.logger.info(f"記事取得開始: 初期時間範囲 {current_hours} 時間")
        
        while current_hours <= self.config.scraping.max_hours_limit:
            articles = self._collect_articles_with_hours(current_hours)
            article_count = len(articles)
            
            self.logger.info(f"取得記事数: {article_count}件 (時間範囲: {current_hours}時間)")
            
            # 最低記事数を満たしているかチェック
            if article_count >= self.config.scraping.minimum_article_count:
                self.logger.info(f"最低記事数({self.config.scraping.minimum_article_count}件)を満たしました")
                return articles
            elif current_hours >= self.config.scraping.max_hours_limit:
                self.logger.warning(
                    f"最大時間範囲({self.config.scraping.max_hours_limit}時間)に到達しました。"
                    f"記事数: {article_count}件 (目標: {self.config.scraping.minimum_article_count}件)"
                )
                return articles
            else:
                # 時間範囲を段階的に拡張
                next_hours = min(current_hours + 24, self.config.scraping.max_hours_limit)
                self.logger.info(
                    f"記事数不足のため時間範囲を拡張: {current_hours}時間 → {next_hours}時間"
                )
                current_hours = next_hours
        
        return articles

    def _collect_articles_with_hours(self, hours_limit: int) -> List[Dict[str, Any]]:
        """指定された時間範囲で記事を収集（並列処理対応）"""
        all_articles = []
        
        # 各スクレイパーを並列実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Reutersには hours_limit パラメータを明示的に追加
            reuters_params = self.config.reuters.to_dict()
            reuters_params['hours_limit'] = hours_limit
            
            # Bloomberg用のパラメータ
            bloomberg_params = self.config.bloomberg.to_dict()
            bloomberg_params['hours_limit'] = hours_limit
            
            future_to_scraper = {
                executor.submit(reuters.scrape_reuters_articles, **reuters_params): "Reuters",
                executor.submit(bloomberg.scrape_bloomberg_top_page_articles, **bloomberg_params): "Bloomberg"
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
        
        # 公開日時でソート
        sorted_articles = sorted(
            all_articles,
            key=lambda x: x.get('published_jst', datetime.min),
            reverse=True
        )
        
        log_with_context(self.logger, logging.INFO, "記事収集完了", operation="collect_articles", total_count=len(sorted_articles))
        return sorted_articles
    
    def collect_articles(self) -> List[Dict[str, Any]]:
        """記事の収集（動的時間範囲対応）"""
        # 新しい動的収集メソッドを使用
        return self.collect_articles_with_dynamic_range()

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
        """
        今回実行分の記事をHTML表示用に準備（AI分析結果と組み合わせ）
        注：今回スクレイピングした記事データのみを使用し、過去の記事の混入を防ぐ
        """
        log_with_context(self.logger, logging.INFO,
                         f"HTML用データ準備開始 (初期記事数: {len(scraped_articles)}件)",
                         operation="prepare_current_session_articles")

        final_articles = []
        processed_urls = set()
        ai_analysis_found = 0
        duplicates_skipped = 0

        for i, scraped_article in enumerate(scraped_articles):
            url = scraped_article.get("url")
            if not url:
                log_with_context(self.logger, logging.WARNING, f"記事 {i} にURLがありません。スキップします。", operation="prepare_html_data")
                continue

            # URLを正規化して比較の精度を上げる
            normalized_url = self.db_manager.url_normalizer.normalize_url(url)

            if normalized_url in processed_urls:
                duplicates_skipped += 1
                log_with_context(self.logger, logging.DEBUG,
                                 f"重複URLをスキップ: 元URL='{url}', 正規化URL='{normalized_url}'",
                                 operation="prepare_html_data")
                continue

            processed_urls.add(normalized_url)
            log_with_context(self.logger, logging.DEBUG, f"新規URLを処理: 元URL='{url}', 正規化URL='{normalized_url}'", operation="prepare_html_data")

            article_data = {
                "title": scraped_article.get("title", ""),
                "url": url, # 表示には元のURLを使用
                "source": scraped_article.get("source", ""),
                "published_jst": scraped_article.get("published_jst", ""),
                "summary": "要約はありません。",
                "sentiment_label": "N/A",
                "sentiment_score": 0.0,
            }

            try:
                # DBからは正規化済みURLで問い合わせるのが確実
                article_with_analysis = self.db_manager.get_article_by_url_with_analysis(normalized_url)
                if article_with_analysis and article_with_analysis.ai_analysis:
                    analysis = article_with_analysis.ai_analysis[0]
                    if analysis.summary:
                        article_data.update({
                            "summary": analysis.summary,
                            "sentiment_label": analysis.sentiment_label if analysis.sentiment_label else "N/A",
                            "sentiment_score": analysis.sentiment_score if analysis.sentiment_score is not None else 0.0,
                        })
                        ai_analysis_found += 1
            except Exception as e:
                log_with_context(self.logger, logging.WARNING,
                                 f"AI分析結果の取得でエラー: {url} - {e}",
                                 operation="prepare_html_data")

            final_articles.append(article_data)

        log_with_context(self.logger, logging.INFO,
                         f"HTML用データ準備完了 (重複スキップ: {duplicates_skipped}件, 最終記事数: {len(final_articles)}件, AI分析あり: {ai_analysis_found}件)",
                         operation="prepare_current_session_articles")
        return final_articles

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
        
        # 記事を公開時刻順（最新順）でソート
        articles_for_html = self._sort_articles_by_time(articles_for_html)
        
        self.html_generator.generate_html_file(articles_for_html, "index.html")
        log_with_context(self.logger, logging.INFO, "最終HTML生成完了", operation="generate_final_html", count=len(articles_for_html))

    def _sort_articles_by_time(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        記事を公開時刻順（最新順）でソート
        
        Args:
            articles: ソート対象の記事リスト
        
        Returns:
            ソート済みの記事リスト
        """
        def get_sort_key(article):
            published_jst = article.get('published_jst')
            if not published_jst:
                return datetime.min  # 日時が不明な記事は最後尾に
            
            # datetimeオブジェクトの場合はそのまま使用
            if hasattr(published_jst, 'year'):
                return published_jst
            
            # 文字列の場合は変換を試行
            if isinstance(published_jst, str):
                try:
                    # ISO形式のパース
                    return datetime.fromisoformat(published_jst.replace('Z', '+00:00'))
                except:
                    return datetime.min
            
            return datetime.min
        
        try:
            sorted_articles = sorted(articles, key=get_sort_key, reverse=True)
            log_with_context(self.logger, logging.INFO, 
                           f"記事を時刻順でソート完了 (最新: {get_sort_key(sorted_articles[0]) if sorted_articles else 'N/A'})", 
                           operation="sort_articles")
            return sorted_articles
        except Exception as e:
            log_with_context(self.logger, logging.WARNING, 
                           f"記事ソート中にエラー: {e} - 元の順序を維持", 
                           operation="sort_articles")
            return articles

    def generate_google_docs(self):
        """Googleドキュメント生成処理"""
        log_with_context(self.logger, logging.INFO, "Googleドキュメント生成開始", operation="generate_google_docs")
        
        # Google認証
        drive_service, docs_service = authenticate_google_services()
        if not drive_service or not docs_service:
            log_with_context(self.logger, logging.ERROR, "Google認証に失敗", operation="generate_google_docs")
            return

        # Drive容量とファイル情報をデバッグ出力
        debug_drive_storage_info(drive_service)
        
        # 古いドキュメントをクリーンアップ
        try:
            deleted_count = cleanup_old_drive_documents(
                drive_service,
                self.config.google.drive_output_folder_id,
                self.config.google.docs_retention_days
            )
            log_with_context(self.logger, logging.INFO, 
                            f"古いGoogleドキュメントクリーンアップ完了", 
                            operation="generate_google_docs", deleted_count=deleted_count)
        except Exception as e:
            log_with_context(self.logger, logging.WARNING, 
                            f"Googleドキュメントクリーンアップでエラー: {e}", 
                            operation="generate_google_docs")
        
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

        # 2. AI要約の新規ドキュメント作成（容量エラー時の自動クリーンアップ・リトライ付き）
        success = create_daily_summary_doc_with_cleanup_retry(
            drive_service,
            docs_service,
            articles_with_summary,
            self.config.google.drive_output_folder_id,
            self.config.google.docs_retention_days
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
            log_with_context(self.logger, logging.INFO, 
                            f"=== 記事収集結果: {len(scraped_articles)}件の記事を取得 ===", 
                            operation="main_process")
            
            self.db_manager.update_scraping_session(session_id, articles_found=len(scraped_articles))
            if not scraped_articles:
                self.logger.warning("収集された記事がありません")
                self.db_manager.complete_scraping_session(session_id, status='completed_no_articles')
                self.generate_final_html([])  # 空リストを渡す
                return

            # 2. DBに保存 (重複排除)
            new_article_ids = self.save_articles_to_db(scraped_articles)
            log_with_context(self.logger, logging.INFO, 
                            f"=== DB保存結果: {len(scraped_articles)}件中{len(new_article_ids)}件が新規記事 ===", 
                            operation="main_process")
            
            self.db_manager.update_scraping_session(session_id, articles_processed=len(new_article_ids))

            # 3. 新規記事をAIで処理
            self.process_new_articles_with_ai(new_article_ids)
            
            # 3.5. AI分析がない24時間以内の記事も処理する
            self.process_recent_articles_without_ai()

            # 4. 今回実行分の記事データをAI分析結果と組み合わせて準備
            current_session_articles = self.prepare_current_session_articles_for_html(scraped_articles)
            log_with_context(self.logger, logging.INFO, 
                            f"=== HTML用データ準備完了: {len(current_session_articles)}件の記事をHTMLに出力予定 ===", 
                            operation="main_process")

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