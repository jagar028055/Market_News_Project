# -*- coding: utf-8 -*-

"""
ニュース処理のメインロジック
"""

import time
import logging
import concurrent.futures
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pytz

from src.logging_config import get_logger, log_with_context
from src.config.app_config import get_config, AppConfig

try:
    from src.database.database_manager import DatabaseManager
    from src.database.models import Article, AIAnalysis
    _DATABASE_AVAILABLE = True
except ImportError:
    DatabaseManager = None  # type: ignore
    Article = None  # type: ignore
    AIAnalysis = None  # type: ignore
    _DATABASE_AVAILABLE = False

try:
    from src.rag.archive_manager import ArchiveManager
    _RAG_AVAILABLE = True
except ImportError:
    ArchiveManager = None  # type: ignore
    _RAG_AVAILABLE = False

try:
    from src.file_search.uploader import FileSearchUploader
    _FILE_SEARCH_AVAILABLE = True
except ImportError:
    FileSearchUploader = None  # type: ignore
    _FILE_SEARCH_AVAILABLE = False

try:
    from scrapers import reuters, bloomberg
    _SCRAPERS_AVAILABLE = True
except ImportError:
    reuters = None  # type: ignore
    bloomberg = None  # type: ignore
    _SCRAPERS_AVAILABLE = False

try:
    from src.legacy.ai_summarizer import process_article_with_ai
    from src.legacy.article_grouper import group_articles_for_pro_summary
    _LEGACY_AVAILABLE = True
except ImportError:
    process_article_with_ai = None  # type: ignore
    group_articles_for_pro_summary = None  # type: ignore
    _LEGACY_AVAILABLE = False

try:
    from scripts.legacy.ai_pro_summarizer import create_integrated_summaries, ProSummaryConfig
    _PRO_SUMMARIZER_AVAILABLE = True
except ImportError:
    create_integrated_summaries = None  # type: ignore
    ProSummaryConfig = None  # type: ignore
    _PRO_SUMMARIZER_AVAILABLE = False

try:
    from tools.performance.cost_manager import check_pro_cost_limits, CostManager
    _COST_MANAGER_AVAILABLE = True
except ImportError:
    check_pro_cost_limits = None  # type: ignore
    CostManager = None  # type: ignore
    _COST_MANAGER_AVAILABLE = False

try:
    from src.html.html_generator import HTMLGenerator
    _HTML_GENERATOR_AVAILABLE = True
except ImportError:
    HTMLGenerator = None  # type: ignore
    _HTML_GENERATOR_AVAILABLE = False

try:
    from src.llm import BaseLLMClient, GeminiClient, OpenRouterClient
    _LLM_AVAILABLE = True
except ImportError:
    BaseLLMClient = None  # type: ignore
    GeminiClient = None  # type: ignore
    OpenRouterClient = None  # type: ignore
    _LLM_AVAILABLE = False

try:
    from gdocs.client import (
        authenticate_google_services,
        test_drive_connection,
        update_google_doc_with_full_text,
        create_daily_summary_doc_with_cleanup_retry,
        debug_drive_storage_info,
        cleanup_old_drive_documents,
        create_debug_spreadsheet,
        update_debug_spreadsheet,
        get_spreadsheet_url,
    )
    _GDOCS_AVAILABLE = True
except ImportError:
    authenticate_google_services = None  # type: ignore
    test_drive_connection = None  # type: ignore
    update_google_doc_with_full_text = None  # type: ignore
    create_daily_summary_doc_with_cleanup_retry = None  # type: ignore
    debug_drive_storage_info = None  # type: ignore
    cleanup_old_drive_documents = None  # type: ignore
    create_debug_spreadsheet = None  # type: ignore
    update_debug_spreadsheet = None  # type: ignore
    get_spreadsheet_url = None  # type: ignore
    _GDOCS_AVAILABLE = False


class NewsProcessor:
    """ニュース処理のメインクラス"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config: AppConfig = get_config()
        self.db_manager = DatabaseManager(self.config.database) if DatabaseManager else None
        self.html_generator = HTMLGenerator(self.logger) if HTMLGenerator else None
        self.archive_manager = ArchiveManager() if ArchiveManager else None
        self.file_search_uploader = FileSearchUploader() if FileSearchUploader else None

        # 動的記事取得機能で使用する属性
        self.folder_id = self.config.google.drive_output_folder_id
        self.gemini_api_key = self.config.ai.gemini_api_key
        self.openrouter_api_key = self.config.ai.openrouter_api_key
        self.llm_provider = (self.config.ai.provider or "gemini").lower()
        self.article_model_name = self.config.ai.model_name
        self.openrouter_model = self.config.ai.openrouter_model
        self.openrouter_http_referer = self.config.ai.openrouter_http_referer
        self.openrouter_app_title = self.config.ai.openrouter_app_title

        self.pro_summary_provider = (
            self.config.ai.pro_summary_provider or self.llm_provider
        ).lower()
        self.pro_model_name = self.config.ai.pro_summary_model

        # Pro統合要約関連の初期化
        self.cost_manager = CostManager() if CostManager else None
        pro_summary_enabled = os.getenv("PRO_SUMMARY_ENABLED", "true").lower() == "true"
        self.pro_config = ProSummaryConfig(
            enabled=pro_summary_enabled,
            min_articles_threshold=10,
            max_daily_executions=3,
            cost_limit_monthly=50.0,
            timeout_seconds=self.config.ai.pro_summary_timeout_seconds,
            model_name=self.pro_model_name,
            provider=self.pro_summary_provider,
        ) if ProSummaryConfig else None
        self.article_llm_client: Optional[BaseLLMClient] = None
        self.pro_llm_client: Optional[BaseLLMClient] = None

    @staticmethod
    def _get_non_negative_int_env(name: str, default: int) -> int:
        """非負の整数環境変数を取得し、不正値や負の値は既定値へフォールバックする。"""
        raw_value = os.getenv(name)
        if raw_value is None or raw_value == "":
            return default

        try:
            value = int(raw_value)
        except ValueError:
            return default

        return value if value >= 0 else default

    def _limit_article_ids_for_ai(
        self, article_ids: List[int], *, env_name: str, default_limit: int, operation: str
    ) -> List[int]:
        """AI処理対象の記事ID数を環境変数で制限する。"""
        limit = self._get_non_negative_int_env(env_name, default_limit)
        if len(article_ids) <= limit:
            return article_ids

        limited_ids = article_ids[:limit]
        log_with_context(
            self.logger,
            logging.WARNING,
            f"AI処理対象を{limit}件に制限します ({len(article_ids)}件中)",
            operation=operation,
            env_name=env_name,
            original_count=len(article_ids),
            limited_count=len(limited_ids),
        )
        return limited_ids

    def validate_environment(self) -> bool:
        """環境変数の検証"""
        self.logger.info("=== 環境変数設定状況 ===")
        self.logger.info(
            f"GOOGLE_DRIVE_OUTPUT_FOLDER_ID: {'設定済み' if self.folder_id else '未設定'}"
        )
        self.logger.info(
            f"GOOGLE_OVERWRITE_DOC_ID: {'設定済み' if self.config.google.overwrite_doc_id else '未設定'}"
        )
        self.logger.info(f"LLM_PROVIDER: {self.llm_provider}")
        self.logger.info(f"PRO_SUMMARY_PROVIDER: {self.pro_summary_provider}")
        self.logger.info(f"GEMINI_API_KEY: {'設定済み' if self.gemini_api_key else '未設定'}")
        self.logger.info(
            f"OPENROUTER_API_KEY: {'設定済み' if self.openrouter_api_key else '未設定'}"
        )
        self.logger.info(
            f"GOOGLE_SERVICE_ACCOUNT_JSON: {'設定済み' if self.config.google.service_account_json else '未設定'}"
        )

        # 動的記事取得設定の表示
        self.logger.info("=== 動的記事取得設定 ===")
        self.logger.info(f"基本時間範囲: {self.config.scraping.hours_limit}時間")
        self.logger.info(f"最低記事数閾値: {self.config.scraping.minimum_article_count}件")
        self.logger.info(f"最大時間範囲: {self.config.scraping.max_hours_limit}時間")
        self.logger.info(f"週末拡張時間: {self.config.scraping.weekend_hours_extension}時間")

        missing_keys = []
        if self.llm_provider == "openrouter":
            if not self.openrouter_api_key:
                missing_keys.append("OPENROUTER_API_KEY")
        else:
            if not self.gemini_api_key:
                missing_keys.append("GEMINI_API_KEY")

        if self.pro_summary_provider == "openrouter" and not self.openrouter_api_key:
            missing_keys.append("OPENROUTER_API_KEY (Pro統合要約)")
        if self.pro_summary_provider == "gemini" and not self.gemini_api_key:
            missing_keys.append("GEMINI_API_KEY (Pro統合要約)")

        if missing_keys:
            for key in missing_keys:
                self.logger.error(f"必要な環境変数が不足しています: {key}")
            return False
        return True

    def _create_llm_client(
        self,
        provider: str,
        model_name: str,
        *,
        purpose: str,
    ) -> BaseLLMClient:
        provider = (provider or "gemini").lower()

        if provider == "openrouter":
            api_key = self.openrouter_api_key
            if not api_key:
                raise ValueError("OpenRouter APIキーが設定されていません")

            timeout = (
                self.config.ai.pro_summary_timeout_seconds
                if purpose == "pro"
                else 180
            )
            client = OpenRouterClient(
                api_key=api_key,
                model_name=model_name,
                http_referer=self.openrouter_http_referer,
                app_title=self.openrouter_app_title,
                default_timeout=timeout,
            )
        else:
            api_key = self.gemini_api_key
            if not api_key:
                raise ValueError("Gemini APIキーが設定されていません")

            timeout = (
                self.config.ai.pro_summary_timeout_seconds
                if purpose == "pro"
                else 600
            )
            client = GeminiClient(
                api_key=api_key,
                model_name=model_name,
                default_timeout=timeout,
            )

        self.logger.debug(
            "LLMクライアントを生成しました (purpose=%s, provider=%s, model=%s)",
            purpose,
            provider,
            model_name,
        )
        return client

    def _ensure_article_client(self) -> BaseLLMClient:
        if self.article_llm_client is None:
            self.article_llm_client = self._create_llm_client(
                self.llm_provider,
                self.article_model_name,
                purpose="article",
            )
        return self.article_llm_client

    def _ensure_pro_client(self) -> BaseLLMClient:
        if self.pro_llm_client is None:
            self.pro_llm_client = self._create_llm_client(
                self.pro_summary_provider,
                self.pro_model_name,
                purpose="pro",
            )
        return self.pro_llm_client

    def get_dynamic_hours_limit(self) -> int:
        """
        曜日と記事数に基づく動的時間範囲決定

        Returns:
            int: 動的に決定された時間範囲（時間）
        """
        jst_tz = pytz.timezone("Asia/Tokyo")
        jst_now = datetime.now(jst_tz)
        weekday = jst_now.weekday()  # 月曜日=0, 日曜日=6

        # 月曜日・土曜日・日曜日は自動的に最大時間範囲を適用（週末や休日明けは記事が少ないため）
        if weekday == 0:  # Monday
            self.logger.info(
                f"月曜日検出: 自動的に{self.config.scraping.max_hours_limit}時間範囲を適用"
            )
            return self.config.scraping.max_hours_limit
        elif weekday == 5:  # Saturday
            self.logger.info(
                f"土曜日検出: 自動的に{self.config.scraping.max_hours_limit}時間範囲を適用"
            )
            return self.config.scraping.max_hours_limit
        elif weekday == 6:  # Sunday
            self.logger.info(
                f"日曜日検出: 自動的に{self.config.scraping.max_hours_limit}時間範囲を適用"
            )
            return self.config.scraping.max_hours_limit

        # 平日（火-金）は基本時間範囲から開始
        return self.config.scraping.hours_limit

    def collect_articles_with_dynamic_range(self) -> List[Dict[str, Any]]:
        """
        動的時間範囲を使用した記事収集
        記事数が不足している場合は段階的に時間範囲を拡張
        """
        import datetime
        import pytz

        # 実行時刻の詳細ログ
        jst_tz = pytz.timezone("Asia/Tokyo")
        jst_now = datetime.datetime.now(jst_tz)
        weekday_names = ["月", "火", "水", "木", "金", "土", "日"]

        self.logger.info(f"=== 動的記事取得開始 ===")
        self.logger.info(
            f"実行日時: {jst_now.strftime('%Y/%m/%d %H:%M:%S')} ({weekday_names[jst_now.weekday()]}曜日)"
        )

        initial_hours = self.get_dynamic_hours_limit()
        current_hours = initial_hours

        self.logger.info(
            f"初期時間範囲: {current_hours}時間 (設定 - 基本: {self.config.scraping.hours_limit}h, 最大: {self.config.scraping.max_hours_limit}h)"
        )
        self.logger.info(f"最低記事数閾値: {self.config.scraping.minimum_article_count}件")

        attempts = 0
        while current_hours <= self.config.scraping.max_hours_limit:
            attempts += 1
            self.logger.info(f"--- 取得試行 {attempts}回目 (時間範囲: {current_hours}時間) ---")

            articles = self._collect_articles_with_hours(current_hours)
            article_count = len(articles)

            # 記事の詳細分析
            source_breakdown = {}
            for article in articles:
                source = article.get("source", "Unknown")
                source_breakdown[source] = source_breakdown.get(source, 0) + 1

            self.logger.info(f"取得結果: 総記事数 {article_count}件")
            for source, count in source_breakdown.items():
                self.logger.info(f"  - {source}: {count}件")

            # 最低記事数を満たしているかチェック
            if article_count >= self.config.scraping.minimum_article_count:
                self.logger.info(
                    f"✅ 成功: 最低記事数({self.config.scraping.minimum_article_count}件)を満たしました"
                )
                self.logger.info(
                    f"=== 動的記事取得完了 (試行回数: {attempts}回, 最終時間範囲: {current_hours}時間) ==="
                )
                return articles
            elif current_hours >= self.config.scraping.max_hours_limit:
                self.logger.warning(
                    f"⚠️  最大時間範囲({self.config.scraping.max_hours_limit}時間)に到達"
                )
                self.logger.warning(
                    f"   最終記事数: {article_count}件 (目標: {self.config.scraping.minimum_article_count}件)"
                )
                self.logger.info(f"=== 動的記事取得完了 (記事不足, 試行回数: {attempts}回) ===")
                return articles
            else:
                # 時間範囲を段階的に拡張
                next_hours = min(current_hours + 24, self.config.scraping.max_hours_limit)
                self.logger.info(
                    f"📈 記事数不足 → 時間範囲拡張: {current_hours}時間 → {next_hours}時間"
                )
                current_hours = next_hours

        self.logger.info(f"=== 動的記事取得完了 (ループ終了) ===")
        return articles

    def _collect_articles_with_hours(self, hours_limit: int) -> List[Dict[str, Any]]:
        """指定された時間範囲で記事を収集（並列処理対応）"""
        all_articles = []

        # 各スクレイパーを並列実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Reutersには hours_limit パラメータを明示的に追加
            reuters_params = self.config.reuters.to_dict()
            reuters_params["hours_limit"] = hours_limit

            # Bloomberg用のパラメータ
            bloomberg_params = self.config.bloomberg.to_dict()
            bloomberg_params["hours_limit"] = hours_limit

            future_to_scraper = {
                executor.submit(reuters.scrape_reuters_articles, **reuters_params): "Reuters",
                executor.submit(
                    bloomberg.scrape_bloomberg_top_page_articles, **bloomberg_params
                ): "Bloomberg",
            }

            for future in concurrent.futures.as_completed(future_to_scraper):
                scraper_name = future_to_scraper[future]
                try:
                    articles = future.result()
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"{scraper_name} 記事取得完了",
                        operation="collect_articles",
                        scraper=scraper_name,
                        count=len(articles),
                    )
                    all_articles.extend(articles)
                except Exception as e:
                    log_with_context(
                        self.logger,
                        logging.ERROR,
                        f"{scraper_name} 記事取得エラー",
                        operation="collect_articles",
                        scraper=scraper_name,
                        error=str(e),
                        exc_info=True,
                    )

        # 公開日時でソート
        sorted_articles = sorted(
            all_articles, key=lambda x: x.get("published_jst", datetime.min), reverse=True
        )

        log_with_context(
            self.logger,
            logging.INFO,
            "記事収集完了",
            operation="collect_articles",
            total_count=len(sorted_articles),
        )
        return sorted_articles

    def collect_articles(self) -> List[Dict[str, Any]]:
        """記事の収集（動的時間範囲対応）"""
        # 新しい動的収集メソッドを使用
        return self.collect_articles_with_dynamic_range()

    def save_articles_to_db(self, articles: List[Dict[str, Any]]) -> List[int]:
        """収集した記事をデータベースに保存（重複は自動で排除）"""
        log_with_context(
            self.logger,
            logging.INFO,
            "記事のDB保存開始",
            operation="save_articles_to_db",
            count=len(articles),
        )
        new_article_ids = []

        for article_data in articles:
            # データベースに保存し、新規かどうかを判定
            article_id, is_new = self.db_manager.save_article(article_data)
            if article_id and is_new:
                new_article_ids.append(article_id)

        log_with_context(
            self.logger,
            logging.INFO,
            "記事のDB保存完了",
            operation="save_articles_to_db",
            new_articles=len(new_article_ids),
            total_attempted=len(articles),
        )
        return new_article_ids

    def process_new_articles_with_ai(self, new_article_ids: List[int]):
        """新規記事のみをAIで処理"""
        if not new_article_ids:
            log_with_context(
                self.logger,
                logging.INFO,
                "AI処理対象の新規記事なし",
                operation="process_new_articles",
            )
            return

        new_article_ids = self._limit_article_ids_for_ai(
            new_article_ids,
            env_name="AI_MAX_ARTICLES_PER_RUN",
            default_limit=25,
            operation="process_new_articles",
        )
        if not new_article_ids:
            log_with_context(
                self.logger,
                logging.INFO,
                "AI処理対象の新規記事が上限設定により0件になりました",
                operation="process_new_articles",
            )
            return

        log_with_context(
            self.logger,
            logging.INFO,
            f"AI処理開始（新規{len(new_article_ids)}件）",
            operation="process_new_articles",
        )

        articles_to_process = self.db_manager.get_articles_by_ids(new_article_ids)

        try:
            client = self._ensure_article_client()
        except ValueError as exc:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"AIクライアントの初期化に失敗: {exc}",
                operation="process_new_articles",
            )
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_article = {
                executor.submit(
                    process_article_with_ai,
                    client,
                    article.body,
                ): article
                for article in articles_to_process
                if article.body
            }

            for future in concurrent.futures.as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    ai_result = future.result()
                    if ai_result:
                        self.db_manager.save_ai_analysis(article.id, ai_result)
                        log_with_context(
                            self.logger, logging.DEBUG, "AI分析結果を保存", article_id=article.id
                        )
                except Exception as e:
                    log_with_context(
                        self.logger,
                        logging.ERROR,
                        f"記事ID {article.id} のAI処理エラー",
                        operation="process_new_articles",
                        article_id=article.id,
                        error=str(e),
                        exc_info=True,
                    )

        log_with_context(self.logger, logging.INFO, "AI処理完了", operation="process_new_articles")

    def process_recent_articles_without_ai(self):
        """AI分析がない24時間以内の記事を処理"""
        # AI分析がない記事のIDを取得
        with self.db_manager.get_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.config.scraping.hours_limit)
            unprocessed_ids = (
                session.query(Article.id)
                .outerjoin(AIAnalysis)
                .filter(
                    Article.published_at >= cutoff_time,
                    AIAnalysis.id.is_(None),
                    Article.body.isnot(None),
                    Article.body != "",
                )
                .order_by(Article.published_at.desc())
                .all()
            )
            unprocessed_ids = [row[0] for row in unprocessed_ids]

        unprocessed_ids = self._limit_article_ids_for_ai(
            unprocessed_ids,
            env_name="AI_MAX_RECENT_ARTICLES_PER_RUN",
            default_limit=10,
            operation="process_recent_articles",
        )

        if not unprocessed_ids:
            log_with_context(
                self.logger,
                logging.INFO,
                "AI処理対象の未処理記事なし",
                operation="process_recent_articles",
            )
            return

        log_with_context(
            self.logger,
            logging.INFO,
            f"未処理記事のAI処理開始（{len(unprocessed_ids)}件）",
            operation="process_recent_articles",
        )

        # 記事を取得してAI処理
        articles_to_process = self.db_manager.get_articles_by_ids(unprocessed_ids)

        try:
            client = self._ensure_article_client()
        except ValueError as exc:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"AIクライアントの初期化に失敗: {exc}",
                operation="process_recent_articles",
            )
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_article = {
                executor.submit(
                    process_article_with_ai,
                    client,
                    article.body,
                ): article
                for article in articles_to_process
                if article.body
            }

            for future in concurrent.futures.as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    ai_result = future.result()
                    if ai_result:
                        self.db_manager.save_ai_analysis(article.id, ai_result)
                        log_with_context(
                            self.logger, logging.DEBUG, "AI分析結果を保存", article_id=article.id
                        )
                except Exception as e:
                    log_with_context(
                        self.logger,
                        logging.ERROR,
                        f"記事ID {article.id} のAI処理エラー",
                        operation="process_recent_articles",
                        article_id=article.id,
                        error=str(e),
                        exc_info=True,
                    )

        log_with_context(
            self.logger, logging.INFO, "未処理記事のAI処理完了", operation="process_recent_articles"
        )

    def process_pro_integration_summaries(
        self, session_id: int, scraped_articles: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Pro統合要約処理を実行（エラーハンドリング・フォールバック対応）

        Args:
            session_id (int): セッションID
            scraped_articles (List[Dict[str, Any]]): 今回スクレイピングした記事データ

        Returns:
            Optional[Dict[str, Any]]: 統合要約結果、失敗時はNone
        """
        # 前提条件の検証
        if not self._validate_pro_integration_prerequisites():
            return None

        if len(scraped_articles) < self.pro_config.min_articles_threshold:
            log_with_context(
                self.logger,
                logging.INFO,
                f"記事数が閾値未満のためPro統合要約をスキップ ({len(scraped_articles)} < {self.pro_config.min_articles_threshold})",
                operation="pro_integration",
            )
            return None

        # コスト制限チェック
        cost_check_config = {
            "monthly_limit": self.pro_config.cost_limit_monthly,
            "daily_limit": self.pro_config.cost_limit_monthly / 30,  # 日次制限は月次制限の1/30
        }

        if not check_pro_cost_limits(cost_check_config):
            log_with_context(
                self.logger,
                logging.WARNING,
                "コスト制限に達しているためPro統合要約をスキップ",
                operation="pro_integration",
            )
            return None

        try:
            log_with_context(
                self.logger,
                logging.INFO,
                f"Pro統合要約処理開始 (記事数: {len(scraped_articles)})",
                operation="pro_integration",
            )

            # 記事をHTML表示用データから取得してAI分析結果を含める
            enriched_articles = []
            for article_data in scraped_articles:
                try:
                    url = article_data.get("url")
                    if not url:
                        continue

                    # データベースからAI分析結果を取得
                    normalized_url = self.db_manager.url_normalizer.normalize_url(url)
                    article_with_analysis = self.db_manager.get_article_by_url_with_analysis(
                        normalized_url
                    )

                    if article_with_analysis and article_with_analysis.ai_analysis:
                        analysis = article_with_analysis.ai_analysis[0]
                        enriched_article = {
                            "title": article_data.get("title", ""),
                            "url": url,
                            "summary": (
                                analysis.summary
                                if analysis.summary
                                else article_data.get("summary", "")
                            ),
                            "category": article_data.get("category", "その他"),
                            "region": self._determine_article_region(article_data),
                            "source": article_data.get("source", ""),
                        }
                        enriched_articles.append(enriched_article)

                except Exception as e:
                    self._handle_pro_integration_error(
                        e, f"記事データ処理中 (URL: {article_data.get('url', 'N/A')})"
                    )
                    continue  # 個別記事のエラーは続行

            if len(enriched_articles) < self.pro_config.min_articles_threshold:
                log_with_context(
                    self.logger,
                    logging.WARNING,
                    f"AI分析済み記事数が不足 ({len(enriched_articles)} < {self.pro_config.min_articles_threshold})",
                    operation="pro_integration",
                )
                # フォールバック処理を実行
                self._pro_integration_fallback_mode(session_id)
                return None

            # 記事を地域別にグループ化
            try:
                grouped_articles = group_articles_for_pro_summary(enriched_articles)
                if not grouped_articles:
                    raise ValueError("記事のグループ化結果が空です")
            except Exception as e:
                self._handle_pro_integration_error(e, "記事グループ化処理中")
                self._pro_integration_fallback_mode(session_id)
                return None

            # Pro統合要約を生成（タイムアウト対応）
            try:
                client = self._ensure_pro_client()
            except ValueError as exc:
                self._handle_pro_integration_error(exc, "Pro統合要約クライアント初期化")
                self._pro_integration_fallback_mode(session_id)
                return None

            try:
                integration_result = create_integrated_summaries(
                    client,
                    grouped_articles,
                    self.pro_config,
                )

                if not integration_result:
                    raise ValueError("統合要約の生成結果が空です")

            except Exception as e:
                self._handle_pro_integration_error(e, "Pro統合要約生成中")
                self._pro_integration_fallback_mode(session_id)
                return None

            # データベースに保存
            try:
                self._save_integrated_summaries_to_db(session_id, integration_result)
            except Exception as e:
                self._handle_pro_integration_error(e, "データベース保存中")
                # 保存に失敗しても要約結果は返す（メモリ上では成功）
                log_with_context(
                    self.logger,
                    logging.WARNING,
                    "統合要約の保存は失敗しましたが、処理結果は正常に生成されました",
                    operation="pro_integration",
                )

            # 新構造に対応した統計情報表示
            if "unified_summary" in integration_result:
                unified_summary = integration_result["unified_summary"]
                section_count = sum(1 for section in unified_summary.values() if section)
                log_with_context(
                    self.logger,
                    logging.INFO,
                    f"Pro統合要約処理完了 (統合要約セクション数: {section_count})",
                    operation="pro_integration",
                )
            else:
                # 従来構造への対応
                regional_count = len(integration_result.get("regional_summaries", {}))
                log_with_context(
                    self.logger,
                    logging.INFO,
                    f"Pro統合要約処理完了 (地域数: {regional_count}, 全体要約: 1件)",
                    operation="pro_integration",
                )

            return integration_result

        except Exception as e:
            # 予期しない例外に対する最終的なエラーハンドリング
            self._handle_pro_integration_error(e, "Pro統合要約処理全体")
            self._pro_integration_fallback_mode(session_id)
            return None

    def _determine_article_region(self, article_data: Dict[str, Any]) -> str:
        """記事の地域を決定（強化版）"""
        title = article_data.get("title", "").lower()
        summary = article_data.get("summary", "").lower()
        text = f"{title} {summary}"

        # 日本関連キーワード
        japan_keywords = ["日本", "日銀", "東京", "円", "toyota", "sony", "nintendo", "softbank", "nissan", "honda", "japan", "yen", "boj", "tokyo", "nikkei"]
        if any(keyword in text for keyword in japan_keywords):
            return "japan"
        
        # アメリカ関連キーワード
        usa_keywords = ["米国", "fed", "dollar", "apple", "microsoft", "google", "amazon", "tesla", "nvidia", "usa", "us", "america", "washington", "wall street", "nasdaq", "s&p"]
        if any(keyword in text for keyword in usa_keywords):
            return "usa"
        
        # 中国関連キーワード
        china_keywords = ["中国", "yuan", "china", "beijing", "shanghai", "alibaba", "tencent", "baidu", "pboc", "renminbi", "hong kong"]
        if any(keyword in text for keyword in china_keywords):
            return "china"
        
        # 欧州関連キーワード
        europe_keywords = ["欧州", "ecb", "euro", "europe", "germany", "france", "uk", "britain", "london", "frankfurt", "european", "brexit"]
        if any(keyword in text for keyword in europe_keywords):
            return "europe"
        
        # その他
        return "other"

    def _determine_article_category(self, article_data: Dict[str, Any]) -> str:
        """記事のカテゴリーを決定"""
        title = article_data.get("title", "").lower()
        summary = article_data.get("summary", "").lower()
        text = f"{title} {summary}"

        # 市場・金融
        if any(keyword in text for keyword in ["market", "stock", "share", "trading", "investment", "fund", "bond", "currency", "forex", "金利", "株式", "市場", "投資", "債券", "為替"]):
            return "market"
        
        # 企業・業績
        elif any(keyword in text for keyword in ["earnings", "revenue", "profit", "company", "corporate", "business", "enterprise", "財務", "業績", "企業", "売上", "利益"]):
            return "corporate"
        
        # 政治・政策
        elif any(keyword in text for keyword in ["policy", "government", "political", "regulation", "law", "election", "政治", "政策", "政府", "規制", "法律", "選挙"]):
            return "politics"
        
        # テクノロジー
        elif any(keyword in text for keyword in ["technology", "tech", "ai", "artificial intelligence", "software", "hardware", "digital", "テクノロジー", "技術", "AI", "人工知能", "ソフトウェア"]):
            return "technology"
        
        # エネルギー・資源
        elif any(keyword in text for keyword in ["energy", "oil", "gas", "renewable", "solar", "wind", "coal", "エネルギー", "石油", "ガス", "再生可能", "太陽光"]):
            return "energy"
        
        # その他
        else:
            return "other"

    def _save_integrated_summaries_to_db(self, session_id: int, integration_result: Dict[str, Any]):
        """統合要約結果をデータベースに保存（新構造対応）"""
        try:
            from src.database.models import IntegratedSummary

            with self.db_manager.get_session() as session:
                # 新構造（unified_summary）に対応
                if "unified_summary" in integration_result:
                    unified_summary = integration_result["unified_summary"]
                    metadata = integration_result.get("metadata", {})

                    # 統合要約全体をグローバル要約として保存
                    # 各セクションを結合して一つの要約テキストとして保存
                    summary_sections = []

                    # 地域別市場概況
                    if unified_summary.get("regional_summaries"):
                        summary_sections.append(
                            f"【地域別市場概況】\n{unified_summary['regional_summaries']}"
                        )

                    # グローバル市場総括
                    if unified_summary.get("global_overview"):
                        summary_sections.append(
                            f"【グローバル市場総括】\n{unified_summary['global_overview']}"
                        )

                    # 地域間相互影響分析（最重要）
                    if unified_summary.get("cross_regional_analysis"):
                        summary_sections.append(
                            f"【地域間相互影響分析】\n{unified_summary['cross_regional_analysis']}"
                        )

                    # 注目トレンド・将来展望
                    if unified_summary.get("key_trends"):
                        summary_sections.append(
                            f"【注目トレンド・将来展望】\n{unified_summary['key_trends']}"
                        )

                    # リスク要因・投資機会
                    if unified_summary.get("risk_factors"):
                        summary_sections.append(
                            f"【リスク要因・投資機会】\n{unified_summary['risk_factors']}"
                        )

                    combined_summary_text = "\n\n".join(summary_sections)

                    global_summary = IntegratedSummary(
                        session_id=session_id,
                        summary_type="global",
                        region=None,
                        summary_text=combined_summary_text,
                        articles_count=metadata.get("total_articles", 0),
                        model_version=metadata.get("model_version", "gemini-2.5-pro"),
                        processing_time_ms=metadata.get("processing_time_ms", 0),
                    )
                    session.add(global_summary)

                else:
                    # 従来構造（global_summary + regional_summaries）への対応（フォールバック）
                    if "global_summary" in integration_result:
                        global_summary_data = integration_result["global_summary"]
                        global_summary = IntegratedSummary(
                            session_id=session_id,
                            summary_type="global",
                            region=None,
                            summary_text=global_summary_data["summary_text"],
                            articles_count=global_summary_data["articles_count"],
                            model_version=global_summary_data["model_version"],
                            processing_time_ms=global_summary_data["processing_time_ms"],
                        )
                        session.add(global_summary)

                    # 地域別要約を保存（従来構造）
                    if "regional_summaries" in integration_result:
                        for region, summary_data in integration_result[
                            "regional_summaries"
                        ].items():
                            regional_summary = IntegratedSummary(
                                session_id=session_id,
                                summary_type="regional",
                                region=region,
                                summary_text=summary_data["summary_text"],
                                articles_count=summary_data["articles_count"],
                                model_version=summary_data["model_version"],
                                processing_time_ms=summary_data["processing_time_ms"],
                            )
                            session.add(regional_summary)

                session.commit()

            log_with_context(
                self.logger,
                logging.INFO,
                f"統合要約をデータベースに保存完了 (セッション: {session_id})",
                operation="save_integrated_summaries",
            )

        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"統合要約のデータベース保存エラー: {e}",
                operation="save_integrated_summaries",
                exc_info=True,
            )

    def _handle_pro_integration_error(self, error: Exception, context: str) -> None:
        """
        Pro統合要約のエラーハンドリング

        Args:
            error (Exception): 発生したエラー
            context (str): エラー発生コンテキスト
        """
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
        }

        log_with_context(
            self.logger,
            logging.ERROR,
            f"Pro統合要約エラー ({context}): {error}",
            operation="pro_integration_error",
            error_details=error_details,
            exc_info=True,
        )

        # 特定のエラータイプに対する対処
        if "rate limit" in str(error).lower() or "quota" in str(error).lower():
            log_with_context(
                self.logger,
                logging.WARNING,
                "API制限に達しました。しばらく時間をおいて再試行してください",
                operation="pro_integration_error",
            )
        elif "timeout" in str(error).lower():
            log_with_context(
                self.logger,
                logging.WARNING,
                "API応答がタイムアウトしました。記事数を減らすか設定を確認してください",
                operation="pro_integration_error",
            )
        elif "authentication" in str(error).lower() or "api key" in str(error).lower():
            log_with_context(
                self.logger,
                logging.ERROR,
                "API認証に失敗しました。APIキーを確認してください",
                operation="pro_integration_error",
            )

    def _pro_integration_fallback_mode(self, session_id: int) -> bool:
        """
        Pro統合要約失敗時のフォールバック処理

        Args:
            session_id (int): セッションID

        Returns:
            bool: フォールバック処理が成功したかどうか
        """
        try:
            log_with_context(
                self.logger,
                logging.INFO,
                "Pro統合要約フォールバック処理開始",
                operation="pro_fallback",
            )

            # フォールバック: Flash-Liteによる簡易統合要約を作成
            with self.db_manager.get_session() as db_session:
                from src.database.models import IntegratedSummary

                # 簡易フォールバック要約を作成
                fallback_summary = IntegratedSummary(
                    session_id=session_id,
                    summary_type="global",
                    region=None,
                    summary_text="Pro統合要約の生成に失敗しました。個別記事の要約をご確認ください。",
                    articles_count=0,
                    model_version="fallback",
                    processing_time_ms=0,
                )
                db_session.add(fallback_summary)
                db_session.commit()

            log_with_context(
                self.logger,
                logging.INFO,
                "Pro統合要約フォールバック処理完了",
                operation="pro_fallback",
            )
            return True

        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"フォールバック処理でもエラーが発生: {e}",
                operation="pro_fallback",
                exc_info=True,
            )
            return False

    def _validate_pro_integration_prerequisites(self) -> bool:
        """
        Pro統合要約の前提条件を検証

        Returns:
            bool: 前提条件を満たしているかどうか
        """
        # APIクライアントの検証
        try:
            self._ensure_pro_client()
        except ValueError as exc:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Pro統合要約用LLMクライアントの初期化に失敗: {exc}",
                operation="pro_validation",
            )
            return False

        # 設定の検証
        if not self.pro_config.enabled:
            log_with_context(
                self.logger,
                logging.INFO,
                "Pro統合要約機能が無効になっています",
                operation="pro_validation",
            )
            return False

        # データベース接続の検証
        try:
            from sqlalchemy import text

            with self.db_manager.get_session() as session:
                session.execute(text("SELECT 1"))
        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"データベース接続に失敗: {e}",
                operation="pro_validation",
            )
            return False

        return True

    def _log_pro_integration_statistics(
        self,
        integration_result: Optional[Dict[str, Any]],
        session_id: int,
        scraped_articles_count: int,
    ):
        """
        Pro統合要約の統計情報をログに記録

        Args:
            integration_result: 統合要約結果
            session_id: セッションID
            scraped_articles_count: 処理対象記事数
        """
        try:
            log_with_context(
                self.logger, logging.INFO, "=== Pro統合要約処理統計 ===", operation="pro_statistics"
            )

            log_with_context(
                self.logger, logging.INFO, f"セッションID: {session_id}", operation="pro_statistics"
            )

            log_with_context(
                self.logger,
                logging.INFO,
                f"処理対象記事数: {scraped_articles_count}件",
                operation="pro_statistics",
            )

            if integration_result:
                # 新構造に対応した統計情報
                metadata = integration_result.get("metadata", {})

                log_with_context(
                    self.logger, logging.INFO, f"統合要約生成: 成功", operation="pro_statistics"
                )

                # 新構造（unified_summary）の場合
                if "unified_summary" in integration_result:
                    unified_summary = integration_result["unified_summary"]
                    total_chars = sum(
                        len(str(section)) for section in unified_summary.values() if section
                    )

                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"統合要約文字数: {total_chars}字",
                        operation="pro_statistics",
                    )

                    # 各セクションの文字数
                    section_names = {
                        "regional_summaries": "地域別市場概況",
                        "global_overview": "グローバル市場総括",
                        "cross_regional_analysis": "地域間相互影響分析",
                        "key_trends": "注目トレンド・将来展望",
                        "risk_factors": "リスク要因・投資機会",
                    }

                    for section_key, section_name in section_names.items():
                        if section_key in unified_summary and unified_summary[section_key]:
                            char_count = len(unified_summary[section_key])
                            log_with_context(
                                self.logger,
                                logging.INFO,
                                f"  {section_name}: {char_count}字",
                                operation="pro_statistics",
                            )

                else:
                    # 従来構造への対応
                    global_summary = integration_result.get("global_summary", {})
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"全体要約文字数: {len(global_summary.get('summary_text', ''))}字",
                        operation="pro_statistics",
                    )

                # 処理時間統計
                processing_time_ms = metadata.get("processing_time_ms", 0)
                log_with_context(
                    self.logger,
                    logging.INFO,
                    f"統合要約処理時間: {processing_time_ms}ms",
                    operation="pro_statistics",
                )

                # 記事分布統計
                articles_by_region = metadata.get("articles_by_region", {})
                if articles_by_region:
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"記事地域分布: {articles_by_region}",
                        operation="pro_statistics",
                    )

                log_with_context(
                    self.logger,
                    logging.INFO,
                    f"総処理時間: {processing_time_ms}ms ({processing_time_ms/1000:.1f}秒)",
                    operation="pro_statistics",
                )

            else:
                # 失敗時の統計
                log_with_context(
                    self.logger,
                    logging.INFO,
                    f"統合要約生成: 失敗またはスキップ",
                    operation="pro_statistics",
                )

                # コスト統計を表示
                cost_stats = self.cost_manager.get_cost_statistics(days=1)  # 本日分
                log_with_context(
                    self.logger,
                    logging.INFO,
                    f"本日のAPI使用状況: ${cost_stats.get('daily_cost', 0):.6f}",
                    operation="pro_statistics",
                )

            log_with_context(
                self.logger, logging.INFO, "=== Pro統合要約統計終了 ===", operation="pro_statistics"
            )

        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"統計情報ログ記録中にエラー: {e}",
                operation="pro_statistics",
                exc_info=True,
            )

    def _monitor_system_performance(self, start_time: float, operation: str):
        """
        システムパフォーマンスの監視

        Args:
            start_time: 処理開始時刻
            operation: 操作名
        """
        try:
            import psutil
            import os

            elapsed_time = time.time() - start_time

            # メモリ使用量
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # CPU使用率
            cpu_percent = process.cpu_percent()

            log_with_context(
                self.logger,
                logging.INFO,
                f"パフォーマンス監視 ({operation}): "
                f"実行時間={elapsed_time:.2f}秒, "
                f"メモリ使用量={memory_mb:.1f}MB, "
                f"CPU使用率={cpu_percent:.1f}%",
                operation="performance_monitoring",
            )

        except ImportError:
            # psutilがインストールされていない場合は基本情報のみ
            elapsed_time = time.time() - start_time
            log_with_context(
                self.logger,
                logging.INFO,
                f"パフォーマンス監視 ({operation}): 実行時間={elapsed_time:.2f}秒",
                operation="performance_monitoring",
            )
        except Exception as e:
            log_with_context(
                self.logger,
                logging.DEBUG,
                f"パフォーマンス監視でエラー: {e}",
                operation="performance_monitoring",
            )

    def _get_integrated_summaries_for_html(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        指定されたセッションの統合要約データをHTML表示用に取得

        Args:
            session_id (int): セッションID

        Returns:
            Optional[Dict[str, Any]]: HTML表示用の統合要約データ
        """
        if not session_id:
            return None

        try:
            from src.database.models import IntegratedSummary

            with self.db_manager.get_session() as session:
                # セッションIDに基づいて統合要約を取得
                summaries = (
                    session.query(IntegratedSummary)
                    .filter(IntegratedSummary.session_id == session_id)
                    .all()
                )

                if not summaries:
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"セッション {session_id} の統合要約が見つかりません",
                        operation="get_integrated_summaries",
                    )
                    return None

                # DBから取得した統合要約データをHTML表示用に整理
                # 新構造（unified_summary）と従来構造の両方に対応

                unified_summary_dict = {}
                metadata = {"total_articles": 0, "processing_time_ms": 0}

                for summary in summaries:
                    if summary.summary_type == "global":
                        # 統合要約テキストから各セクションを抽出する試行
                        summary_text = summary.summary_text

                        # セクション分割を試行（セクション見出しに基づく）
                        sections = self._parse_combined_summary_text(summary_text)

                        if sections:
                            # セクション分割に成功した場合
                            unified_summary_dict = sections
                        else:
                            # セクション分割に失敗した場合は全体をglobal_overviewとして扱う
                            unified_summary_dict = {
                                "global_overview": summary_text,
                                "regional_summaries": "",
                                "cross_regional_analysis": "",
                                "key_trends": "",
                                "risk_factors": "",
                            }

                        metadata["total_articles"] = summary.articles_count
                        metadata["processing_time_ms"] += summary.processing_time_ms

                html_summaries = {"unified_summary": unified_summary_dict, "metadata": metadata}

                log_with_context(
                    self.logger,
                    logging.INFO,
                    f"統合要約データをHTML用に準備完了 (統合要約: {'あり' if unified_summary_dict.get('global_overview') else 'なし'})",
                    operation="get_integrated_summaries",
                )

                return html_summaries if unified_summary_dict.get("global_overview") else None

        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"統合要約データの取得でエラー: {e}",
                operation="get_integrated_summaries",
                exc_info=True,
            )
            return None

    def _parse_combined_summary_text(self, combined_text: str) -> Optional[Dict[str, str]]:
        """
        結合された統合要約テキストを各セクションに分割

        Args:
            combined_text (str): 結合された統合要約テキスト

        Returns:
            Optional[Dict[str, str]]: 分割されたセクション辞書、失敗時はNone
        """
        if not combined_text:
            return None

        try:
            sections = {
                "regional_summaries": "",
                "global_overview": "",
                "cross_regional_analysis": "",
                "key_trends": "",
                "risk_factors": "",
            }

            # セクション見出しのマッピング
            section_markers = {
                "【地域別市場概況】": "regional_summaries",
                "【グローバル市場総括】": "global_overview",
                "【地域間相互影響分析】": "cross_regional_analysis",
                "【注目トレンド・将来展望】": "key_trends",
                "【リスク要因・投資機会】": "risk_factors",
            }

            current_section = None
            current_content = []

            lines = combined_text.split("\n")

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # セクション見出しを検出
                section_found = False
                for marker, section_key in section_markers.items():
                    if marker in line:
                        # 前のセクションを保存
                        if current_section and current_content:
                            sections[current_section] = "\n".join(current_content).strip()

                        current_section = section_key
                        current_content = []
                        section_found = True
                        break

                if not section_found and current_section:
                    current_content.append(line)

            # 最後のセクションを保存
            if current_section and current_content:
                sections[current_section] = "\n".join(current_content).strip()

            # 有効なセクションが見つかった場合のみ返す
            if any(sections.values()):
                return sections
            else:
                return None

        except Exception as e:
            log_with_context(
                self.logger,
                logging.WARNING,
                f"統合要約テキストの分割でエラー: {e}",
                operation="parse_combined_summary",
            )
            return None

    def _log_session_summary(
        self, session_id: int, start_time: float, integration_result: Optional[Dict[str, Any]]
    ):
        """
        セッション全体のサマリーをログに記録

        Args:
            session_id: セッションID
            start_time: 処理開始時刻
            integration_result: 統合要約結果
        """
        try:
            total_elapsed = time.time() - start_time

            log_with_context(
                self.logger,
                logging.INFO,
                f"=== セッション {session_id} 完了サマリー ===",
                operation="session_summary",
            )

            log_with_context(
                self.logger,
                logging.INFO,
                f"総処理時間: {total_elapsed:.2f}秒",
                operation="session_summary",
            )

            # Pro統合要約の状況
            if integration_result:
                log_with_context(
                    self.logger, logging.INFO, "Pro統合要約: 成功", operation="session_summary"
                )

                # 新構造に対応した要約概要
                if "unified_summary" in integration_result:
                    unified_summary = integration_result["unified_summary"]
                    total_chars = sum(
                        len(str(section)) for section in unified_summary.values() if section
                    )
                    section_count = sum(1 for section in unified_summary.values() if section)

                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"  統合要約: {total_chars}字 ({section_count}セクション)",
                        operation="session_summary",
                    )
                else:
                    # 従来構造への対応
                    global_chars = len(
                        integration_result.get("global_summary", {}).get("summary_text", "")
                    )
                    regional_count = len(integration_result.get("regional_summaries", {}))

                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"  全体要約: {global_chars}字",
                        operation="session_summary",
                    )
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"  地域別要約: {regional_count}件",
                        operation="session_summary",
                    )
            else:
                log_with_context(
                    self.logger,
                    logging.INFO,
                    "Pro統合要約: スキップまたは失敗",
                    operation="session_summary",
                )

            # コスト情報
            try:
                monthly_cost = self.cost_manager.get_monthly_cost()
                daily_cost = self.cost_manager.get_daily_cost()

                log_with_context(
                    self.logger,
                    logging.INFO,
                    f"API使用コスト - 今月: ${monthly_cost:.6f}, 今日: ${daily_cost:.6f}",
                    operation="session_summary",
                )
            except Exception:
                pass  # コスト情報取得でのエラーは無視

            log_with_context(
                self.logger,
                logging.INFO,
                f"=== セッション {session_id} サマリー終了 ===",
                operation="session_summary",
            )

        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"セッションサマリー記録中にエラー: {e}",
                operation="session_summary",
                exc_info=True,
            )

    def prepare_current_session_articles_for_html(
        self, scraped_articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        今回実行分の記事をHTML表示用に準備（AI分析結果と組み合わせ）
        注：今回スクレイピングした記事データのみを使用し、過去の記事の混入を防ぐ
        """
        log_with_context(
            self.logger,
            logging.INFO,
            f"HTML用データ準備開始 (初期記事数: {len(scraped_articles)}件)",
            operation="prepare_current_session_articles",
        )

        final_articles = []
        processed_urls = set()
        ai_analysis_found = 0
        duplicates_skipped = 0

        for i, scraped_article in enumerate(scraped_articles):
            url = scraped_article.get("url")
            if not url:
                log_with_context(
                    self.logger,
                    logging.WARNING,
                    f"記事 {i} にURLがありません。スキップします。",
                    operation="prepare_html_data",
                )
                continue

            # URLを正規化して比較の精度を上げる
            normalized_url = self.db_manager.url_normalizer.normalize_url(url)

            if normalized_url in processed_urls:
                duplicates_skipped += 1
                log_with_context(
                    self.logger,
                    logging.DEBUG,
                    f"重複URLをスキップ: 元URL='{url}', 正規化URL='{normalized_url}'",
                    operation="prepare_html_data",
                )
                continue

            processed_urls.add(normalized_url)
            log_with_context(
                self.logger,
                logging.DEBUG,
                f"新規URLを処理: 元URL='{url}', 正規化URL='{normalized_url}'",
                operation="prepare_html_data",
            )

            article_data = {
                "title": scraped_article.get("title", ""),
                "url": url,  # 表示には元のURLを使用
                "source": scraped_article.get("source", ""),
                "published_jst": scraped_article.get("published_jst", ""),
                "content": scraped_article.get("body", ""),  # 本文を追加
                "summary": "要約はありません。",
                "sentiment_label": "N/A",
                "sentiment_score": 0.0,
                "category": "その他",
                "region": "その他",
            }

            try:
                # DBからは正規化済みURLで問い合わせるのが確実
                log_with_context(
                    self.logger,
                    logging.DEBUG,
                    f"AI分析結果を検索中: 正規化URL='{normalized_url}'",
                    operation="prepare_html_data",
                )
                article_with_analysis = self.db_manager.get_article_by_url_with_analysis(
                    normalized_url
                )
                
                if article_with_analysis:
                    log_with_context(
                        self.logger,
                        logging.DEBUG,
                        f"記事が見つかりました: title='{article_with_analysis.title}', ai_analysis_count={len(article_with_analysis.ai_analysis) if article_with_analysis.ai_analysis else 0}",
                        operation="prepare_html_data",
                    )
                    
                    if article_with_analysis.ai_analysis:
                        analysis = article_with_analysis.ai_analysis[0]
                        log_with_context(
                            self.logger,
                            logging.DEBUG,
                            f"AI分析結果が見つかりました: category='{analysis.category}', region='{analysis.region}', summary_length={len(analysis.summary) if analysis.summary else 0}",
                            operation="prepare_html_data",
                        )
                        
                        if analysis.summary:
                            article_data.update(
                                {
                                    "summary": analysis.summary,
                                    "sentiment_label": (
                                        analysis.sentiment_label if analysis.sentiment_label else "N/A"
                                    ),
                                    "sentiment_score": (
                                        analysis.sentiment_score
                                        if analysis.sentiment_score is not None
                                        else 0.0
                                    ),
                                    "category": analysis.category if analysis.category else "その他",
                                    "region": analysis.region if analysis.region else "その他",
                                }
                            )
                            ai_analysis_found += 1
                            log_with_context(
                                self.logger,
                                logging.INFO,
                                f"AI分析結果を記事データに設定完了: URL='{url}', category='{analysis.category}', region='{analysis.region}'",
                                operation="prepare_html_data",
                            )
                        else:
                            log_with_context(
                                self.logger,
                                logging.WARNING,
                                f"AI分析は存在するが要約が空です: URL='{url}'",
                                operation="prepare_html_data",
                            )
                    else:
                        log_with_context(
                            self.logger,
                            logging.WARNING,
                            f"記事は見つかったがAI分析結果がありません: URL='{url}'",
                            operation="prepare_html_data",
                        )
                else:
                    log_with_context(
                        self.logger,
                        logging.WARNING,
                        f"記事がデータベースに見つかりません: 正規化URL='{normalized_url}'",
                        operation="prepare_html_data",
                    )
            except Exception as e:
                log_with_context(
                    self.logger,
                    logging.ERROR,
                    f"AI分析結果の取得でエラー: URL='{url}', 正規化URL='{normalized_url}' - {e}",
                    operation="prepare_html_data",
                    exc_info=True,
                )

            final_articles.append(article_data)

        log_with_context(
            self.logger,
            logging.INFO,
            f"HTML用データ準備完了 (重複スキップ: {duplicates_skipped}件, 最終記事数: {len(final_articles)}件, AI分析あり: {ai_analysis_found}件)",
            operation="prepare_current_session_articles",
        )
        return final_articles

    def generate_final_html(
        self, current_session_articles: List[Dict[str, Any]] = None, session_id: int = None
    ):
        """最終的なHTMLを生成（今回実行分の記事のみ）"""
        log_with_context(
            self.logger, logging.INFO, "最終HTML生成開始", operation="generate_final_html"
        )

        # Pro統合要約データを取得
        integrated_summaries = (
            self._get_integrated_summaries_for_html(session_id) if session_id else None
        )

        # 今回実行分の記事が渡されない場合は空のHTMLを生成
        if not current_session_articles:
            log_with_context(
                self.logger,
                logging.WARNING,
                "HTML生成対象の記事なし",
                operation="generate_final_html",
            )
            self.html_generator.generate_html_file(
                [], "index.html", integrated_summaries=integrated_summaries
            )
            return

        # 今回実行分の記事をHTMLジェネレーター用に変換
        articles_for_html = []
        for article_data in current_session_articles:
            articles_for_html.append(
                {
                    "title": article_data.get("title", ""),
                    "url": article_data.get("url", ""),
                    "summary": article_data.get("summary", "要約はありません。"),
                    "source": article_data.get("source", ""),
                    "published_jst": article_data.get("published_jst", ""),
                    "sentiment_label": article_data.get("sentiment_label", "N/A"),
                    "sentiment_score": article_data.get("sentiment_score", 0.0),
                    "category": article_data.get("category", "その他"),
                    "region": article_data.get("region", "その他"),
                }
            )

        # 記事を公開時刻順（最新順）でソート
        articles_for_html = self._sort_articles_by_time(articles_for_html)

        self.html_generator.generate_html_file(
            articles_for_html, "index.html", integrated_summaries=integrated_summaries
        )
        log_with_context(
            self.logger,
            logging.INFO,
            "最終HTML生成完了",
            operation="generate_final_html",
            count=len(articles_for_html),
        )

    def _sort_articles_by_time(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        記事を公開時刻順（最新順）でソート

        Args:
            articles: ソート対象の記事リスト

        Returns:
            ソート済みの記事リスト
        """

        def get_sort_key(article):
            published_jst = article.get("published_jst")
            if not published_jst:
                return datetime.min  # 日時が不明な記事は最後尾に

            # datetimeオブジェクトの場合はそのまま使用
            if hasattr(published_jst, "year"):
                return published_jst

            # 文字列の場合は変換を試行
            if isinstance(published_jst, str):
                try:
                    # ISO形式のパース
                    return datetime.fromisoformat(published_jst.replace("Z", "+00:00"))
                except:
                    return datetime.min

            return datetime.min

        try:
            sorted_articles = sorted(articles, key=get_sort_key, reverse=True)
            log_with_context(
                self.logger,
                logging.INFO,
                f"記事を時刻順でソート完了 (最新: {get_sort_key(sorted_articles[0]) if sorted_articles else 'N/A'})",
                operation="sort_articles",
            )
            return sorted_articles
        except Exception as e:
            log_with_context(
                self.logger,
                logging.WARNING,
                f"記事ソート中にエラー: {e} - 元の順序を維持",
                operation="sort_articles",
            )
            return articles

    def generate_google_docs_and_sheets(self, session_id: int, current_session_articles: List[Dict[str, Any]]):
        """Googleドキュメント・スプレッドシート生成処理"""
        log_with_context(
            self.logger,
            logging.INFO,
            "Googleドキュメント・スプレッドシート生成開始",
            operation="generate_google_docs_and_sheets",
        )

        # Google認証（Sheets APIも含む）
        drive_service, docs_service, sheets_service = authenticate_google_services()
        if not drive_service or not docs_service:
            log_with_context(
                self.logger, logging.ERROR, "Google認証に失敗", operation="generate_google_docs_and_sheets"
            )
            return
        
        # Sheetsサービスが取得できない場合の警告
        if not sheets_service:
            log_with_context(
                self.logger, 
                logging.WARNING, 
                "Sheets APIが利用できません。スプレッドシート機能は無効化されます。",
                operation="generate_google_docs_and_sheets"
            )

        # 1. 既存のGoogleドキュメント処理を実行
        self._generate_google_docs_internal(drive_service, docs_service)

        # 2. 記事データスプレッドシートを生成
        if sheets_service and current_session_articles:
            self._generate_articles_spreadsheet(
                drive_service, sheets_service, session_id, current_session_articles
            )
        elif not sheets_service:
            log_with_context(
                self.logger,
                logging.INFO,
                "Sheets APIが利用できないため、記事データスプレッドシート生成をスキップします。",
                operation="generate_google_docs_and_sheets",
            )

        # 3. API使用量スプレッドシートを更新
        if sheets_service:
            self._update_api_usage_spreadsheet(
                drive_service, sheets_service, session_id
            )
        else:
            log_with_context(
                self.logger,
                logging.INFO,
                "Sheets APIが利用できないため、API使用量スプレッドシート更新をスキップします。",
                operation="generate_google_docs_and_sheets",
            )

    def _generate_articles_spreadsheet(
        self, drive_service, sheets_service, session_id: int, articles: List[Dict[str, Any]]
    ):
        """記事データスプレッドシートを生成"""
        try:
            log_with_context(
                self.logger,
                logging.INFO,
                f"記事データスプレッドシート生成開始 (記事数: {len(articles)})",
                operation="generate_articles_spreadsheet",
            )

            # スプレッドシート作成
            spreadsheet_id = create_debug_spreadsheet(
                sheets_service, drive_service, self.folder_id, session_id
            )
            
            if not spreadsheet_id:
                log_with_context(
                    self.logger,
                    logging.ERROR,
                    "記事データスプレッドシート作成に失敗",
                    operation="generate_articles_spreadsheet",
                )
                return

            # データを整形
            headers = [
                "記事タイトル", "公開時刻(JST)", "AI要約", "地域", "カテゴリー", 
                "感情分析", "感情スコア", "ソース", "URL", "セッションID", "処理日時"
            ]
            
            jst_tz = pytz.timezone("Asia/Tokyo")
            process_time = datetime.now(jst_tz).strftime('%Y-%m-%d %H:%M:%S')
            
            data_rows = [headers]
            
            for article in articles:
                # 地域とカテゴリーを自動分類
                region = self._determine_article_region(article)
                category = self._determine_article_category(article)
                
                # 公開時刻をフォーマット
                published_jst = article.get("published_jst", "")
                if hasattr(published_jst, "strftime"):
                    published_str = published_jst.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    published_str = str(published_jst)
                
                row = [
                    article.get("title", ""),
                    published_str,
                    article.get("summary", "要約なし"),
                    region,
                    category,
                    article.get("sentiment_label", "N/A"),
                    article.get("sentiment_score", 0.0),
                    article.get("source", ""),
                    article.get("url", ""),
                    session_id,
                    process_time
                ]
                data_rows.append(row)

            # スプレッドシートにデータを書き込み
            success = update_debug_spreadsheet(sheets_service, spreadsheet_id, data_rows)
            
            if success:
                spreadsheet_url = get_spreadsheet_url(spreadsheet_id)
                log_with_context(
                    self.logger,
                    logging.INFO,
                    f"記事データスプレッドシート生成完了: {spreadsheet_url}",
                    operation="generate_articles_spreadsheet",
                )
            else:
                log_with_context(
                    self.logger,
                    logging.ERROR,
                    "記事データスプレッドシート書き込みに失敗",
                    operation="generate_articles_spreadsheet",
                )

        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"記事データスプレッドシート生成でエラー: {e}",
                operation="generate_articles_spreadsheet",
                exc_info=True,
            )

    def _update_api_usage_spreadsheet(self, drive_service, sheets_service, session_id: int):
        """API使用量スプレッドシートを更新"""
        try:
            log_with_context(
                self.logger,
                logging.INFO,
                "API使用量スプレッドシート更新開始",
                operation="update_api_usage_spreadsheet",
            )

            # コスト管理から詳細統計情報を取得
            cost_stats = self.cost_manager.get_spreadsheet_cost_data(session_id)
            cost_alert = self.cost_manager.generate_cost_alert(monthly_limit=50.0, daily_limit=5.0)
            
            jst_tz = pytz.timezone("Asia/Tokyo")
            current_time = datetime.now(jst_tz).strftime('%Y-%m-%d %H:%M:%S')
            
            headers = [
                "日時(JST)", "モデル名", "API種別", "リクエスト回数", "入力トークン", 
                "出力トークン", "推定コスト(USD)", "セッションID", "累積月間コスト(USD)"
            ]
            
            # セッション毎のAPI使用量データを準備
            api_data_rows = [headers]
            
            # モデル別のAPI使用量を記録
            model_breakdown = cost_stats.get('model_breakdown', {})
            for model_name, model_data in model_breakdown.items():
                api_data_rows.append([
                    current_time,
                    model_name,
                    "記事要約・統合要約",
                    model_data.get('requests', 0),
                    model_data.get('input_tokens', 0),
                    model_data.get('output_tokens', 0),
                    model_data.get('cost', 0.0),
                    session_id,
                    cost_stats.get('monthly_cost', 0.0)
                ])
            
            # データがない場合の代替
            if not model_breakdown:
                api_data_rows.append([
                    current_time,
                    "gemini-1.5-flash",
                    "記事要約",
                    cost_stats.get('total_requests', 0),
                    cost_stats.get('total_input_tokens', 0),
                    cost_stats.get('total_output_tokens', 0),
                    cost_stats.get('total_cost', 0.0),
                    session_id,
                    cost_stats.get('monthly_cost', 0.0)
                ])
            
            # 既存のAPI使用量スプレッドシートを検索または作成
            api_spreadsheet_id = self._get_or_create_api_usage_spreadsheet(
                drive_service, sheets_service
            )
            
            if api_spreadsheet_id:
                # 既存データに追記
                self._append_api_usage_data(sheets_service, api_spreadsheet_id, api_data_rows[1:])
                
                api_spreadsheet_url = get_spreadsheet_url(api_spreadsheet_id)
                log_with_context(
                    self.logger,
                    logging.INFO,
                    f"API使用量スプレッドシート更新完了: {api_spreadsheet_url}",
                    operation="update_api_usage_spreadsheet",
                )

        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"API使用量スプレッドシート更新でエラー: {e}",
                operation="update_api_usage_spreadsheet",
                exc_info=True,
            )

    def _get_or_create_api_usage_spreadsheet(self, drive_service, sheets_service) -> str:
        """API使用量スプレッドシートを取得または作成"""
        try:
            # 既存のAPI使用量スプレッドシートを検索
            spreadsheet_name = "Market_News_API_Usage_Tracker"
            query = f"name='{spreadsheet_name}' and '{self.folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
            
            response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            existing_files = response.get('files', [])

            if existing_files:
                # 既存ファイルを使用
                spreadsheet_id = existing_files[0].get('id')
                log_with_context(
                    self.logger,
                    logging.INFO,
                    f"既存API使用量スプレッドシート使用: {spreadsheet_id}",
                    operation="get_or_create_api_usage_spreadsheet",
                )
                return spreadsheet_id
            else:
                # 新規作成
                return self._create_new_api_usage_spreadsheet(drive_service, sheets_service, spreadsheet_name)

        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"API使用量スプレッドシート取得・作成でエラー: {e}",
                operation="get_or_create_api_usage_spreadsheet",
                exc_info=True,
            )
            return None

    def _create_new_api_usage_spreadsheet(self, drive_service, sheets_service, title: str) -> str:
        """新規API使用量スプレッドシートを作成"""
        try:
            # スプレッドシート作成
            spreadsheet = {
                'properties': {
                    'title': title
                },
                'sheets': [{
                    'properties': {
                        'title': 'API_Usage_Log'
                    }
                }]
            }
            
            spreadsheet_result = sheets_service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = spreadsheet_result['spreadsheetId']
            
            # 指定フォルダに移動
            if self.folder_id:
                drive_service.files().update(
                    fileId=spreadsheet_id,
                    addParents=self.folder_id,
                    removeParents='root'
                ).execute()
            
            # ヘッダー行を設定
            headers = [
                "日時(JST)", "モデル名", "API種別", "リクエスト回数", "入力トークン", 
                "出力トークン", "推定コスト(USD)", "セッションID", "累積月間コスト(USD)"
            ]
            
            range_name = 'API_Usage_Log!A1:I1'
            body = {'values': [headers]}
            
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            log_with_context(
                self.logger,
                logging.INFO,
                f"新規API使用量スプレッドシート作成完了: {spreadsheet_id}",
                operation="create_new_api_usage_spreadsheet",
            )
            
            return spreadsheet_id

        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"新規API使用量スプレッドシート作成でエラー: {e}",
                operation="create_new_api_usage_spreadsheet",
                exc_info=True,
            )
            return None

    def _append_api_usage_data(self, sheets_service, spreadsheet_id: str, data_rows: List[List]):
        """API使用量データを既存スプレッドシートに追記"""
        try:
            # 既存データの最終行を取得
            range_name = 'API_Usage_Log!A:I'
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, 
                range=range_name
            ).execute()
            
            existing_values = result.get('values', [])
            next_row = len(existing_values) + 1
            
            # 新しいデータを追記
            append_range = f'API_Usage_Log!A{next_row}:I{next_row + len(data_rows) - 1}'
            body = {'values': data_rows}
            
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=append_range,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            log_with_context(
                self.logger,
                logging.INFO,
                f"API使用量データ追記完了: {len(data_rows)}行",
                operation="append_api_usage_data",
            )

        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"API使用量データ追記でエラー: {e}",
                operation="append_api_usage_data",
                exc_info=True,
            )

    def _generate_google_docs_internal(self, drive_service, docs_service):
        """内部Googleドキュメント生成処理"""
        # Drive容量とファイル情報をデバッグ出力
        debug_drive_storage_info(drive_service)

        # 古いドキュメントをクリーンアップ
        try:
            deleted_count = cleanup_old_drive_documents(
                drive_service,
                self.config.google.drive_output_folder_id,
                self.config.google.docs_retention_days,
            )
            log_with_context(
                self.logger,
                logging.INFO,
                f"古いGoogleドキュメントクリーンアップ完了",
                operation="generate_google_docs_internal",
                deleted_count=deleted_count,
            )
        except Exception as e:
            log_with_context(
                self.logger,
                logging.WARNING,
                f"Googleドキュメントクリーンアップでエラー: {e}",
                operation="generate_google_docs_internal",
            )

        # 権限確認
        if not test_drive_connection(drive_service, self.config.google.drive_output_folder_id):
            log_with_context(
                self.logger,
                logging.ERROR,
                "Google Drive接続テスト失敗",
                operation="generate_google_docs_internal",
            )
            return

        # DBから過去24時間分の全記事を取得
        recent_articles = self.db_manager.get_recent_articles_all(
            hours=self.config.scraping.hours_limit
        )

        if not recent_articles:
            log_with_context(
                self.logger,
                logging.WARNING,
                "Googleドキュメント生成対象の記事なし",
                operation="generate_google_docs_internal",
            )
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
                docs_service, self.config.google.overwrite_doc_id, articles_for_docs
            )
            if success:
                log_with_context(
                    self.logger,
                    logging.INFO,
                    "既存ドキュメント上書き完了",
                    operation="generate_google_docs_internal",
                    doc_id=self.config.google.overwrite_doc_id,
                )
            else:
                log_with_context(
                    self.logger,
                    logging.ERROR,
                    "既存ドキュメント上書き失敗",
                    operation="generate_google_docs_internal",
                    doc_id=self.config.google.overwrite_doc_id,
                )

        # 2. AI要約の新規ドキュメント作成（容量エラー時の自動クリーンアップ・リトライ付き）
        success = create_daily_summary_doc_with_cleanup_retry(
            drive_service,
            docs_service,
            articles_with_summary,
            self.config.google.drive_output_folder_id,
            self.config.google.docs_retention_days,
        )
        if success:
            log_with_context(
                self.logger,
                logging.INFO,
                "日次サマリードキュメント作成完了",
                operation="generate_google_docs_internal",
                ai_articles=len(articles_with_summary),
            )
        else:
            log_with_context(
                self.logger,
                logging.ERROR,
                "日次サマリードキュメント作成失敗",
                operation="generate_google_docs_internal",
            )

    def generate_google_docs(self):
        """Googleドキュメント生成処理（既存機能維持）"""
        log_with_context(
            self.logger,
            logging.INFO,
            "Googleドキュメント生成開始",
            operation="generate_google_docs",
        )

        # Google認証
        drive_service, docs_service, _ = authenticate_google_services()
        if not drive_service or not docs_service:
            log_with_context(
                self.logger, logging.ERROR, "Google認証に失敗", operation="generate_google_docs"
            )
            return

        # Drive容量とファイル情報をデバッグ出力
        debug_drive_storage_info(drive_service)

        # 古いドキュメントをクリーンアップ
        try:
            deleted_count = cleanup_old_drive_documents(
                drive_service,
                self.config.google.drive_output_folder_id,
                self.config.google.docs_retention_days,
            )
            log_with_context(
                self.logger,
                logging.INFO,
                f"古いGoogleドキュメントクリーンアップ完了",
                operation="generate_google_docs",
                deleted_count=deleted_count,
            )
        except Exception as e:
            log_with_context(
                self.logger,
                logging.WARNING,
                f"Googleドキュメントクリーンアップでエラー: {e}",
                operation="generate_google_docs",
            )

        # 権限確認
        if not test_drive_connection(drive_service, self.config.google.drive_output_folder_id):
            log_with_context(
                self.logger,
                logging.ERROR,
                "Google Drive接続テスト失敗",
                operation="generate_google_docs",
            )
            return

        # DBから過去24時間分の全記事を取得
        recent_articles = self.db_manager.get_recent_articles_all(
            hours=self.config.scraping.hours_limit
        )

        if not recent_articles:
            log_with_context(
                self.logger,
                logging.WARNING,
                "Googleドキュメント生成対象の記事なし",
                operation="generate_google_docs",
            )
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
                docs_service, self.config.google.overwrite_doc_id, articles_for_docs
            )
            if success:
                log_with_context(
                    self.logger,
                    logging.INFO,
                    "既存ドキュメント上書き完了",
                    operation="generate_google_docs",
                    doc_id=self.config.google.overwrite_doc_id,
                )
            else:
                log_with_context(
                    self.logger,
                    logging.ERROR,
                    "既存ドキュメント上書き失敗",
                    operation="generate_google_docs",
                    doc_id=self.config.google.overwrite_doc_id,
                )

        # 2. AI要約の新規ドキュメント作成（容量エラー時の自動クリーンアップ・リトライ付き）
        success = create_daily_summary_doc_with_cleanup_retry(
            drive_service,
            docs_service,
            articles_with_summary,
            self.config.google.drive_output_folder_id,
            self.config.google.docs_retention_days,
        )
        if success:
            log_with_context(
                self.logger,
                logging.INFO,
                "日次サマリードキュメント作成完了",
                operation="generate_google_docs",
                ai_articles=len(articles_with_summary),
            )
        else:
            log_with_context(
                self.logger,
                logging.ERROR,
                "日次サマリードキュメント作成失敗",
                operation="generate_google_docs",
            )

    def run(self):
        """メイン処理の実行"""
        self.logger.info("=== ニュース記事取得・処理開始 ===")
        overall_start_time = time.time()

        # スクレイピングセッション開始
        session_id = self.db_manager.start_scraping_session()

        try:
            if not self.validate_environment():
                self.db_manager.complete_scraping_session(
                    session_id, status="failed", error_details="環境変数未設定"
                )
                return

            # 1. 記事収集
            scraped_articles = self.collect_articles()
            log_with_context(
                self.logger,
                logging.INFO,
                f"=== 記事収集結果: {len(scraped_articles)}件の記事を取得 ===",
                operation="main_process",
            )

            self.db_manager.update_scraping_session(
                session_id, articles_found=len(scraped_articles)
            )
            if not scraped_articles:
                self.logger.error("スクレイピングで新しい記事が取得されませんでした。スクレイピング処理を確認してください。")
                self.db_manager.complete_scraping_session(
                    session_id, status="failed", error_details="No articles scraped"
                )
                raise RuntimeError("記事のスクレイピングに失敗しました。ソースサイトの構造変更やネットワーク問題を確認してください。")

            # 2. DBに保存 (重複排除)
            new_article_ids = self.save_articles_to_db(scraped_articles)
            log_with_context(
                self.logger,
                logging.INFO,
                f"=== DB保存結果: {len(scraped_articles)}件中{len(new_article_ids)}件が新規記事 ===",
                operation="main_process",
            )

            self.db_manager.update_scraping_session(
                session_id, articles_processed=len(new_article_ids)
            )

            # 3. 新規記事をAIで処理
            self.process_new_articles_with_ai(new_article_ids)

            # 3.5. AI分析がない24時間以内の記事も処理する
            self.process_recent_articles_without_ai()

            # 3.7. Pro統合要約処理（新規追加）
            integration_result = None
            pro_integration_start_time = time.time()

            try:
                integration_result = self.process_pro_integration_summaries(
                    session_id, scraped_articles
                )
                if integration_result:
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        "Pro統合要約が正常に生成されました",
                        operation="main_process",
                    )
                else:
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        "Pro統合要約はスキップされました",
                        operation="main_process",
                    )
            except Exception as e:
                log_with_context(
                    self.logger,
                    logging.ERROR,
                    f"Pro統合要約処理でエラー (フォールバック処理継続): {e}",
                    operation="main_process",
                    exc_info=True,
                )
            finally:
                # Pro統合要約の統計情報をログ記録
                self._log_pro_integration_statistics(
                    integration_result, session_id, len(scraped_articles)
                )
                # パフォーマンス監視
                self._monitor_system_performance(pro_integration_start_time, "Pro統合要約処理")

            # 4. 今回実行分の記事データをAI分析結果と組み合わせて準備
            current_session_articles = self.prepare_current_session_articles_for_html(
                scraped_articles
            )
            log_with_context(
                self.logger,
                logging.INFO,
                f"=== HTML用データ準備完了: {len(current_session_articles)}件の記事をHTMLに出力予定 ===",
                operation="main_process",
            )

            # 5. 最終的なHTMLを生成（今回実行分のみ）
            self.generate_final_html(current_session_articles, session_id)

            # 6. Googleドキュメント・スプレッドシート生成（時刻条件満たす場合のみ）
            # 環境変数でGoogle Services処理をON/OFF制御
            import os
            enable_google_services = os.getenv('ENABLE_GOOGLE_SERVICES', 'true').lower() == 'true'
            
            if enable_google_services:
                self.generate_google_docs_and_sheets(session_id, current_session_articles)
            else:
                log_with_context(
                    self.logger,
                    logging.INFO,
                    "ENABLE_GOOGLE_SERVICES=falseによりGoogle Services処理をスキップ",
                    operation="main_process",
                )

            # 8. Supabaseにアーカイブ（新規追加）
            self.archive_to_supabase(session_id, current_session_articles)

            # 7. 古いデータをクリーンアップ
            self.db_manager.cleanup_old_data(days_to_keep=30)

            self.db_manager.complete_scraping_session(session_id, status="completed_ok")

        except Exception as e:
            self.logger.error(f"処理全体で予期せぬエラーが発生: {e}", exc_info=True)
            self.db_manager.complete_scraping_session(
                session_id, status="failed", error_details=str(e)
            )
            raise
        finally:
            overall_elapsed_time = time.time() - overall_start_time

            # セッション全体のサマリーをログに記録
            self._log_session_summary(
                session_id,
                overall_start_time,
                integration_result if "integration_result" in locals() else None,
            )

            # 全体のパフォーマンス監視
            self._monitor_system_performance(overall_start_time, "処理全体")

            self.logger.info(
                f"=== 全ての処理が完了しました (総処理時間: {overall_elapsed_time:.2f}秒) ==="
            )

    def archive_to_supabase(self, session_id: int, articles: List[Dict[str, Any]]) -> None:
        """記事データをSupabaseにアーカイブ"""
        log_with_context(
            self.logger,
            logging.INFO,
            "Supabaseアーカイブ処理開始",
            operation="archive_to_supabase",
            session_id=session_id,
            article_count=len(articles),
        )

        try:
            if not self.archive_manager.supabase_client.is_available():
                log_with_context(
                    self.logger,
                    logging.WARNING,
                    "Supabaseが利用できないため、アーカイブをスキップ",
                    operation="archive_to_supabase",
                )
                return

            # セッションの記事データをアーカイブ
            archived_count = 0
            for article in articles:
                try:
                    # 公開日時を取得（published_jst または published_at）
                    published_date = article.get('published_jst') or article.get('published_at')
                    if published_date and hasattr(published_date, 'date'):
                        doc_date = published_date.date()
                    else:
                        doc_date = datetime.now().date()
                    
                    # AI分析結果からcategoryとregionを取得（存在する場合）
                    url = article.get('url')
                    if url:
                        normalized_url = self.db_manager.url_normalizer.normalize_url(url)
                        article_with_analysis = self.db_manager.get_article_by_url_with_analysis(
                            normalized_url
                        )
                        
                        if article_with_analysis and article_with_analysis.ai_analysis:
                            analysis = article_with_analysis.ai_analysis[0]
                            # AI分析結果をarticleデータに追加
                            if analysis.category and not article.get('category'):
                                article['category'] = analysis.category
                            if analysis.region and not article.get('region'):
                                article['region'] = analysis.region
                    
                    # ArchiveManagerで記事をアーカイブ
                    document_id = self.archive_manager.archive_article(
                        article_data=article,
                        doc_date=doc_date
                    )
                    if document_id:
                        archived_count += 1
                except Exception as e:
                    self.logger.error(f"記事アーカイブエラー: {e}", exc_info=True)

            log_with_context(
                self.logger,
                logging.INFO,
                f"Supabaseアーカイブ完了: {archived_count}/{len(articles)}件",
                operation="archive_to_supabase",
                archived_count=archived_count,
                total_count=len(articles),
            )

            # File Search へアップロード（オプション）
            if self.file_search_uploader.enabled:
                try:
                    doc_date = datetime.now().date().isoformat()
                    fs_result = self.file_search_uploader.upload_articles(articles, doc_date)
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        "File Search アップロード結果",
                        operation="archive_to_supabase",
                        file_search_uploaded=fs_result.get("uploaded", 0),
                        file_search_skipped=fs_result.get("skipped", 0),
                        file_search_errors=len(fs_result.get("errors", [])),
                    )
                except Exception as e:
                    log_with_context(
                        self.logger,
                        logging.ERROR,
                        f"File Search アップロード中にエラー: {e}",
                        operation="archive_to_supabase",
                        exc_info=True,
                    )

        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"Supabaseアーカイブ処理エラー: {e}",
                operation="archive_to_supabase",
                exc_info=True,
            )
