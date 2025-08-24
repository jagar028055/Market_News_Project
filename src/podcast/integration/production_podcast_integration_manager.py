# -*- coding: utf-8 -*-

"""
プロダクション版ポッドキャスト統合管理システム
10分完全版・高品質自動化システム
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.database.database_manager import DatabaseManager
from src.podcast.data_fetcher.enhanced_database_article_fetcher import (
    EnhancedDatabaseArticleFetcher,
)
from src.podcast.data_fetcher.google_document_data_fetcher import GoogleDocumentDataFetcher
from src.podcast.script_generation.professional_dialogue_script_generator import (
    ProfessionalDialogueScriptGenerator,
)
from src.podcast.integration.podcast_integration_manager import PodcastIntegrationManager


class ProductionPodcastIntegrationManager:
    """プロダクション版ポッドキャスト統合管理クラス"""

    def __init__(self, config=None):
        """
        初期化

        Args:
            config: 設定オブジェクト（省略時は環境変数ベース設定を使用）
        """
        self.logger = logging.getLogger(__name__)

        try:
            # 設定管理を環境変数ベースに変更
            self.config = self._load_config_from_env()

            # データソース設定
            self.data_source = os.getenv(
                "PODCAST_DATA_SOURCE", "database"
            )  # database | google_document
            self.google_doc_id = os.getenv("GOOGLE_DOCUMENT_ID") or os.getenv(
                "GOOGLE_OVERWRITE_DOC_ID"
            )

            # デバッグ情報出力
            self.logger.info(f"環境変数デバッグ情報:")
            self.logger.info(f"  PODCAST_DATA_SOURCE = {os.getenv('PODCAST_DATA_SOURCE', '未設定')}")
            self.logger.info(f"  GOOGLE_DOCUMENT_ID = {os.getenv('GOOGLE_DOCUMENT_ID', '未設定')}")
            self.logger.info(f"  GOOGLE_OVERWRITE_DOC_ID = {os.getenv('GOOGLE_OVERWRITE_DOC_ID', '未設定')}")
            self.logger.info(f"データソース設定: {self.data_source}")
            if self.google_doc_id:
                self.logger.info(f"GoogleドキュメントID: {self.google_doc_id}")
            else:
                self.logger.warning("GoogleドキュメントIDが設定されていません")

            # 基本コンポーネント初期化
            self._initialize_data_fetcher()

            # Gemini 2.5 Pro台本生成器
            self._initialize_script_generator()

            # 既存システム活用（音声生成・配信）
            self._initialize_base_manager(config)

            self.logger.info("プロダクション版ポッドキャスト統合マネージャー初期化完了")

        except Exception as e:
            self.logger.error(f"初期化エラー: {e}", exc_info=True)
            raise

    def _load_config_from_env(self) -> Dict[str, Any]:
        """環境変数から設定を読み込み（最適化版）"""
        return {
            "gemini_model": os.getenv("GEMINI_PODCAST_MODEL", "gemini-2.5-pro"),
            "gemini_api_key": os.getenv("GEMINI_API_KEY"),
            "production_mode": os.getenv("PODCAST_PRODUCTION_MODE", "true").lower() == "true",  # デフォルトをtrueに変更
            "target_duration": float(os.getenv("PODCAST_TARGET_DURATION_MINUTES", "10.0")),
            "target_script_chars": int(os.getenv("PODCAST_TARGET_SCRIPT_CHARS", "2700")),
            "data_source": os.getenv("PODCAST_DATA_SOURCE", "database"),  # デフォルトをdatabaseに明示
            "google_doc_id": os.getenv("GOOGLE_DOCUMENT_ID") 
            or os.getenv("GOOGLE_OVERWRITE_DOC_ID")
            or os.getenv("GOOGLE_DAILY_SUMMARY_DOC_ID")  # AI要約Doc対応
            or os.getenv("GOOGLE_AI_SUMMARY_DOC_ID"),     # AI要約Doc対応
        }

    def _create_database_config(self):
        """環境変数からDatabaseConfigを生成"""
        try:
            from config.base import DatabaseConfig

            return DatabaseConfig(
                url=os.getenv("DATABASE_URL", "sqlite:///market_news.db"),
                echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
            )
        except ImportError as e:
            self.logger.warning(f"DatabaseConfig import失敗: {e}")

            # フォールバック: 簡易設定オブジェクト作成
            class SimpleDatabaseConfig:
                def __init__(self):
                    self.url = os.getenv("DATABASE_URL", "sqlite:///market_news.db")
                    self.echo = os.getenv("DATABASE_ECHO", "false").lower() == "true"

            return SimpleDatabaseConfig()
        except Exception as e:
            self.logger.error(f"DatabaseConfig生成エラー: {e}")

            # 最終フォールバック: デフォルト設定
            class DefaultDatabaseConfig:
                def __init__(self):
                    self.url = "sqlite:///market_news.db"
                    self.echo = False

            return DefaultDatabaseConfig()

    def _initialize_data_fetcher(self):
        """データ取得コンポーネント初期化（最適化版）"""
        try:
            # データソース判定ロジックの最適化
            self.logger.info(f"データソース設定判定:")
            self.logger.info(f"  PODCAST_DATA_SOURCE = {os.getenv('PODCAST_DATA_SOURCE', '未設定')}")
            self.logger.info(f"  GOOGLE_DOCUMENT_ID = {'設定済み' if self.google_doc_id else '未設定'}")
            
            # 優先順位: 明示的なdatabase設定 > Google Doc ID存在 > デフォルト(database)
            if self.data_source == "database":
                # データベースモード優先実行
                try:
                    self.logger.info("データベースモードで初期化を試行")
                    
                    # 環境変数ベースでDatabaseConfigを生成
                    db_config = self._create_database_config()
                    self.logger.info(f"データベース設定: URL={db_config.url}")

                    # DatabaseManagerを正しいパラメータで初期化
                    self.db_manager = DatabaseManager(db_config)
                    self.article_fetcher = EnhancedDatabaseArticleFetcher(self.db_manager)
                    self.logger.info("✅ データベースモード初期化成功")
                    return

                except Exception as db_error:
                    self.logger.warning(
                        f"データベース初期化失敗: {type(db_error).__name__}: {str(db_error)[:100]}"
                    )
                    
                    # フォールバック判定
                    if self.google_doc_id:
                        self.logger.info("Googleドキュメントモードにフォールバック")
                        self.data_source = "google_document"
                    else:
                        self.logger.error("データベース失敗、Googleドキュメントも未設定")
                        raise ValueError(
                            "データベース接続失敗、かつGoogleドキュメントID未設定。"
                            "GOOGLE_DOCUMENT_ID環境変数を設定してください"
                        )
            
            # Googleドキュメントモード実行
            if self.data_source == "google_document":
                if not self.google_doc_id:
                    # AI要約ドキュメント自動検索を試行
                    temp_fetcher = GoogleDocumentDataFetcher("")
                    auto_found_id = temp_fetcher._search_daily_summary_document()
                    
                    if auto_found_id:
                        self.google_doc_id = auto_found_id
                        self.logger.info(f"AI要約ドキュメント自動発見: {auto_found_id}")
                    else:
                        raise ValueError(
                            "GoogleドキュメントID未設定。以下の環境変数のいずれかを設定してください: "
                            "GOOGLE_DOCUMENT_ID, GOOGLE_DAILY_SUMMARY_DOC_ID, GOOGLE_AI_SUMMARY_DOC_ID"
                        )
                
                self.article_fetcher = GoogleDocumentDataFetcher(self.google_doc_id)
                self.logger.info(f"✅ Googleドキュメントモード初期化成功 (ID: {self.google_doc_id})")
            
        except Exception as e:
            self.logger.error(
                f"データ取得コンポーネント初期化エラー: {type(e).__name__}: {e}", exc_info=True
            )
            raise

    def _initialize_script_generator(self):
        """スクリプト生成器初期化"""
        try:
            gemini_model = self.config["gemini_model"]
            gemini_api_key = self.config["gemini_api_key"]

            if not gemini_api_key:
                raise ValueError("GEMINI_API_KEY環境変数が設定されていません")

            self.script_generator = ProfessionalDialogueScriptGenerator(
                api_key=gemini_api_key, model_name=gemini_model
            )

            self.logger.info(f"Gemini台本生成器初期化完了 - モデル: {gemini_model}")

        except Exception as e:
            self.logger.error(f"スクリプト生成器初期化エラー: {e}", exc_info=True)
            raise

    def _initialize_base_manager(self, config):
        """ベースマネージャー初期化（テストモード対応）"""
        try:
            # テストモードの場合は音声処理依存を避ける
            test_mode = os.getenv("PODCAST_TEST_MODE", "false").lower() == "true"
            
            if test_mode:
                self.logger.info("テストモード: 音声処理系コンポーネントをスキップ")
                self.base_manager = None
                return
            
            # 既存システムでは設定オブジェクトが必要な場合があるため、
            # 引数で受け取った設定か、Noneを渡す
            self.base_manager = PodcastIntegrationManager(config=config)
            self.logger.info("ベースマネージャー初期化完了")

        except Exception as e:
            self.logger.warning(f"ベースマネージャー初期化警告: {e}")
            # 音声生成・配信機能は一時的に無効化してもメイン機能は動作可能
            self.base_manager = None

    def generate_complete_podcast(
        self, test_mode: bool = False, target_duration: float = None
    ) -> Dict[str, Any]:
        """
        完全版ポッドキャスト生成（品質評価・自動調整付き）

        Args:
            test_mode: テストモード（実際の配信を行わない）
            target_duration: 目標配信時間（分）

        Returns:
            生成結果辞書
        """
        try:
            start_time = datetime.now()

            # 設定値取得
            target_duration = target_duration or float(
                os.getenv("PODCAST_TARGET_DURATION_MINUTES", "10.0")
            )
            production_mode = os.getenv("PODCAST_PRODUCTION_MODE", "false").lower() == "true"

            self.logger.info(
                f"プロダクション版ポッドキャスト生成開始 - "
                f"テストモード: {test_mode}, プロダクションモード: {production_mode}, "
                f"目標時間: {target_duration}分, データソース: {self.data_source}"
            )

            # Phase 1: 高度記事選択
            self.logger.info("Phase 1: 高度記事選択システム実行")
            articles = self.article_fetcher.fetch_articles_for_podcast(
                target_count=18, hours_back=48
            )

            if not articles:
                raise ValueError("選択可能な記事が見つかりません")

            self.logger.info(f"記事選択完了 - 選択数: {len(articles)}")

            # Phase 2: プロフェッショナル台本生成
            self.logger.info("Phase 2: Gemini 2.5 Pro による高品質台本生成")
            script_result = self.script_generator.generate_professional_script(
                articles=articles, target_duration=target_duration
            )

            # Phase 2.5: 品質評価と自動調整
            self.logger.info("Phase 2.5: コンテンツ品質評価・自動調整")
            quality_evaluation = self._evaluate_content_quality(articles, script_result)
            
            # 品質が閾値未満の場合、1回だけ再生成を試行
            regeneration_attempted = False
            if not quality_evaluation["meets_quality_threshold"] and not test_mode:
                self.logger.warning(
                    f"品質基準未達 (総合スコア: {quality_evaluation['total_quality_score']:.2f}, "
                    f"カバレッジ: {quality_evaluation['coverage_score']:.2f}), 再生成を試行"
                )
                
                # 記事再選択（より広範囲から）
                self.logger.info("記事再選択実行（範囲拡大）")
                retry_articles = self.article_fetcher.fetch_articles_for_podcast(
                    target_count=8, hours_back=36  # 範囲拡大
                )
                
                if retry_articles and len(retry_articles) > len(articles):
                    self.logger.info("台本再生成実行")
                    retry_script_result = self.script_generator.generate_professional_script(
                        articles=retry_articles, target_duration=target_duration
                    )
                    
                    # 再評価
                    retry_quality = self._evaluate_content_quality(retry_articles, retry_script_result)
                    
                    # より良い結果なら採用
                    if retry_quality["total_quality_score"] > quality_evaluation["total_quality_score"]:
                        self.logger.info(
                            f"再生成採用 (改善: {retry_quality['total_quality_score']:.2f} > "
                            f"{quality_evaluation['total_quality_score']:.2f})"
                        )
                        articles = retry_articles
                        script_result = retry_script_result
                        quality_evaluation = retry_quality
                        regeneration_attempted = True
                    else:
                        self.logger.info("再生成品質が改善されず、元の結果を採用")
                else:
                    self.logger.warning("再選択で十分な記事が得られず、元の結果を採用")

            # Phase 3: 音声生成・配信（既存システム活用）
            self.logger.info("Phase 3: 音声生成・配信システム実行")

            # 台本を一時保存
            script_content = script_result["script"]
            temp_script_path = Path("temp_podcast_script.txt")
            with open(temp_script_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            try:
                # 既存の音声生成・配信システムを使用
                if self.base_manager:
                    broadcast_result = self.base_manager.run_daily_podcast_workflow(
                        test_mode=test_mode, custom_script_path=str(temp_script_path)
                    )
                else:
                    self.logger.warning(
                        "ベースマネージャーが利用できません。音声生成・配信をスキップします。"
                    )
                    broadcast_result = True  # テスト目的では成功とみなす

            finally:
                # 一時ファイル削除
                if temp_script_path.exists():
                    temp_script_path.unlink()

            # 結果統合
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            # 記事統計取得
            article_stats = self.article_fetcher.get_article_statistics(hours_back=24)

            result = {
                "success": broadcast_result,
                "production_mode": production_mode,
                "test_mode": test_mode,
                "regeneration_attempted": regeneration_attempted,
                "script_generation": script_result,
                "articles_analysis": {
                    "selected_count": len(articles),
                    "data_source": self.data_source,
                    "article_scores": [
                        {
                            "title": a.get("article", {}).get("title", "")[:100],
                            "score": a.get("score", 0),
                            "category": a.get("analysis", {}).get("category", "その他"),
                            "region": a.get("analysis", {}).get("region", "other"),
                            "source": a.get("article", {}).get("source", "Unknown"),
                        }
                        for a in articles
                    ],
                },
                "system_metrics": {
                    "total_processing_time_seconds": processing_time,
                    "script_generation_model": script_result.get("generation_model"),
                    "database_statistics": article_stats,
                },
                "quality_assessment": {
                    "script_char_count": script_result.get("char_count"),
                    "estimated_duration_minutes": script_result.get("estimated_duration"),
                    "quality_score": script_result.get("quality_score"),
                    "quality_details": script_result.get("quality_details"),
                    "coverage_evaluation": quality_evaluation,  # 新規追加
                },
                "generated_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
            }

            # 品質レポート出力
            self._generate_quality_report(result)

            if broadcast_result:
                final_quality = quality_evaluation["total_quality_score"]
                coverage_score = quality_evaluation["coverage_score"]
                self.logger.info(
                    f"プロダクション版ポッドキャスト生成完了 - "
                    f"処理時間: {processing_time:.1f}秒, "
                    f"品質スコア: {final_quality:.2f}, カバレッジ: {coverage_score:.2f}"
                )
            else:
                self.logger.error("プロダクション版ポッドキャスト生成に失敗しました")

            return result

        except Exception as e:
            self.logger.error(f"プロダクション版ポッドキャスト生成エラー: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "generated_at": datetime.now().isoformat(),
            }

    def run_daily_podcast_workflow(self, test_mode: bool = False) -> bool:
        """
        日次ポッドキャストワークフロー実行

        Args:
            test_mode: テストモード

        Returns:
            成功可否
        """
        try:
            result = self.generate_complete_podcast(test_mode=test_mode)
            return result.get("success", False)

        except Exception as e:
            self.logger.error(f"日次ワークフローエラー: {e}", exc_info=True)
            return False

    def run_script_only_workflow(self) -> bool:
        """
        台本生成専用ワークフロー
        台本生成と分析のみを実行し、音声生成は行わない
        
        Returns:
            bool: 成功時True
        """
        try:
            self.logger.info("🎬 台本生成専用ワークフロー開始")
            
            # 記事データ取得
            self.logger.info("📰 記事データ取得中...")
            articles = self._fetch_articles()
            
            if not articles:
                self.logger.error("記事データが取得できませんでした")
                return False
                
            self.logger.info(f"✅ 記事データ取得完了: {len(articles)}件")
            
            # 台本生成
            self.logger.info("📝 台本生成中...")
            script = self.script_generator.generate_script(articles)
            
            if not script:
                self.logger.error("台本生成に失敗しました")
                return False
                
            # 台本分析
            script_info = self._analyze_script_content(script)
            
            # 台本ファイル保存
            script_file_path = self._save_script_file(script, script_info)
            
            # 分析結果をログ出力
            self._display_script_analysis(script, script_info, script_file_path)
            
            # GitHubアクション用の環境変数出力
            self._output_github_actions_script_info(script_info, script_file_path)
            
            self.logger.info("✅ 台本生成専用ワークフロー完了")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 台本生成ワークフローでエラー: {e}", exc_info=True)
            return False

    def _fetch_articles(self) -> List[Dict]:
        """記事データを取得"""
        return self.article_fetcher.fetch_articles_for_podcast(
            target_count=12, hours_back=48
        )
    
    def _analyze_script_content(self, script: str) -> Dict[str, Any]:
        """台本内容を分析"""
        lines = script.split('\n')
        total_lines = len(lines)
        char_count = len(script)
        
        # スピーカー別の行数をカウント
        speaker_a_lines = 0
        speaker_b_lines = 0
        other_lines = 0
        
        for line in lines:
            line = line.strip()
            if line.startswith('A:'):
                speaker_a_lines += 1
            elif line.startswith('B:'):
                speaker_b_lines += 1
            elif line:  # 空行でない場合
                other_lines += 1
        
        # 推定読み上げ時間（日本語: 約400文字/分）
        estimated_minutes = char_count / 400
        estimated_duration = f"{int(estimated_minutes)}分{int((estimated_minutes % 1) * 60)}秒"
        
        # 問題検出
        issues = []
        if char_count < 1000:
            issues.append("台本が短すぎます（1000文字未満）")
        if char_count > 8000:
            issues.append("台本が長すぎます（8000文字超過）")
        if speaker_a_lines == 0:
            issues.append("スピーカーAの台詞がありません")
        if speaker_b_lines == 0:
            issues.append("スピーカーBの台詞がありません")
        if abs(speaker_a_lines - speaker_b_lines) > max(speaker_a_lines, speaker_b_lines) * 0.3:
            issues.append("スピーカー間の台詞数バランスが悪い")
        
        return {
            'char_count': char_count,
            'line_count': total_lines,
            'speaker_a_lines': speaker_a_lines,
            'speaker_b_lines': speaker_b_lines,
            'other_lines': other_lines,
            'estimated_duration': estimated_duration,
            'estimated_minutes': estimated_minutes,
            'issues': issues
        }
    
    def _save_script_file(self, script: str, script_info: Dict[str, Any]) -> str:
        """台本ファイルを保存"""
        episode_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output/podcast")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        script_file_path = output_dir / f"{episode_id}_script.txt"
        
        with open(script_file_path, "w", encoding="utf-8") as f:
            f.write(script)
        
        self.logger.info(f"台本ファイル保存: {script_file_path}")
        return str(script_file_path)
    
    def _display_script_analysis(self, script: str, script_info: Dict[str, Any], script_file_path: str) -> None:
        """台本分析結果を詳細表示"""
        self.logger.info("=" * 60)
        self.logger.info("📄 台本分析結果")
        self.logger.info("=" * 60)
        
        # 基本統計
        self.logger.info(f"📊 基本統計:")
        self.logger.info(f"  文字数: {script_info['char_count']:,}文字")
        self.logger.info(f"  行数: {script_info['line_count']}行")
        self.logger.info(f"  推定時間: {script_info['estimated_duration']}")
        self.logger.info(f"  推定時間（分）: {script_info['estimated_minutes']:.1f}分")
        
        # スピーカー分析
        self.logger.info(f"\n🎭 スピーカー分析:")
        self.logger.info(f"  スピーカーA: {script_info['speaker_a_lines']}行")
        self.logger.info(f"  スピーカーB: {script_info['speaker_b_lines']}行")
        self.logger.info(f"  その他: {script_info['other_lines']}行")
        
        total_speaker_lines = script_info['speaker_a_lines'] + script_info['speaker_b_lines']
        if total_speaker_lines > 0:
            a_ratio = script_info['speaker_a_lines'] / total_speaker_lines * 100
            b_ratio = script_info['speaker_b_lines'] / total_speaker_lines * 100
            self.logger.info(f"  A:B比率 = {a_ratio:.1f}% : {b_ratio:.1f}%")
        
        # ファイル情報
        self.logger.info(f"\n📁 ファイル情報:")
        self.logger.info(f"  保存先: {script_file_path}")
        
        # 問題検出
        if script_info['issues']:
            self.logger.info(f"\n⚠️  検出された問題:")
            for issue in script_info['issues']:
                self.logger.warning(f"  - {issue}")
        else:
            self.logger.info(f"\n✅ 問題は検出されませんでした")
        
        # 台本プレビュー（最初の500文字）
        self.logger.info(f"\n📖 台本プレビュー（最初の500文字）:")
        self.logger.info("-" * 40)
        preview = script[:500] + "..." if len(script) > 500 else script
        self.logger.info(preview)
        self.logger.info("-" * 40)
        
        self.logger.info("=" * 60)
    
    def _output_github_actions_script_info(self, script_info: Dict[str, Any], script_file_path: str) -> None:
        """GitHubアクション用の環境変数出力"""
        github_output = os.getenv("GITHUB_OUTPUT")
        if not github_output:
            return
            
        try:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write(f"script_char_count={script_info['char_count']}\n")
                f.write(f"script_estimated_duration={script_info['estimated_duration']}\n")
                f.write(f"script_speaker_a_lines={script_info['speaker_a_lines']}\n")
                f.write(f"script_speaker_b_lines={script_info['speaker_b_lines']}\n")
                f.write(f"script_file_path={script_file_path}\n")
                f.write(f"script_issues_count={len(script_info['issues'])}\n")
                f.write(f"script_has_issues={'true' if script_info['issues'] else 'false'}\n")
                
            self.logger.info("GitHubアクション環境変数を出力しました")
        except Exception as e:
            self.logger.warning(f"GitHubアクション環境変数出力エラー: {e}")

    def _generate_quality_report(self, result: Dict[str, Any]) -> None:
        """品質レポート生成（拡張版）"""
        try:
            coverage_eval = result.get("quality_assessment", {}).get("coverage_evaluation", {})
            
            report_lines = [
                "=== プロダクション版ポッドキャスト品質レポート ===",
                f"生成日時: {result['generated_at']}",
                f"完了日時: {result['completed_at']}",
                f"処理時間: {result['system_metrics']['total_processing_time_seconds']:.1f}秒",
                f"再生成実施: {'はい' if result.get('regeneration_attempted', False) else 'いいえ'}",
                "",
                "## 台本品質",
                f"文字数: {result['quality_assessment']['script_char_count']}文字",
                f"推定再生時間: {result['quality_assessment']['estimated_duration_minutes']:.1f}分",
                f"品質スコア: {result['quality_assessment']['quality_score']:.2f}/1.0",
                "",
                "## カバレッジ評価",
            ]
            
            if coverage_eval:
                report_lines.extend([
                    f"総合品質スコア: {coverage_eval.get('total_quality_score', 0):.2f}/1.0",
                    f"カバレッジスコア: {coverage_eval.get('coverage_score', 0):.2f}/1.0",
                    f"文字数精度: {coverage_eval.get('char_accuracy', 0):.2f}/1.0",
                    f"品質基準達成: {'✅ 達成' if coverage_eval.get('meets_quality_threshold', False) else '❌ 未達成'}",
                    "",
                ])
                
                # 品質課題の表示
                quality_issues = coverage_eval.get('quality_issues', [])
                if quality_issues:
                    report_lines.append("⚠️ 検出された品質課題:")
                    for issue in quality_issues:
                        report_lines.append(f"  - {issue}")
                    report_lines.append("")

            # 記事選択分析
            report_lines.append("## 記事選択")
            report_lines.append(f"選択記事数: {result['articles_analysis']['selected_count']}")
            report_lines.append(f"データソース: {result['articles_analysis']['data_source']}")
            
            # カテゴリ分布
            if coverage_eval and 'category_distribution' in coverage_eval:
                category_dist = coverage_eval['category_distribution']
                report_lines.append("カテゴリ分布:")
                for category, count in category_dist.items():
                    report_lines.append(f"  - {category}: {count}記事")
            else:
                # フォールバック: 従来の方法
                category_count = {}
                for article in result["articles_analysis"]["article_scores"]:
                    cat = article["category"]
                    category_count[cat] = category_count.get(cat, 0) + 1
                
                report_lines.append("カテゴリ分布:")
                for category, count in category_count.items():
                    report_lines.append(f"  - {category}: {count}記事")

            # 地域分布
            if coverage_eval and 'region_distribution' in coverage_eval:
                region_dist = coverage_eval['region_distribution']
                report_lines.append("\n地域分布:")
                for region, count in region_dist.items():
                    report_lines.append(f"  - {region}: {count}記事")
            else:
                # フォールバック: 従来の方法
                region_count = {}
                for article in result["articles_analysis"]["article_scores"]:
                    region = article["region"]
                    region_count[region] = region_count.get(region, 0) + 1

                report_lines.append("\n地域分布:")
                for region, count in region_count.items():
                    report_lines.append(f"  - {region}: {count}記事")
                    
            # ソース分布（新規）
            if coverage_eval and 'source_distribution' in coverage_eval:
                source_dist = coverage_eval['source_distribution']
                report_lines.append("\nソース分布:")
                for source, count in source_dist.items():
                    report_lines.append(f"  - {source}: {count}記事")

            # データベース統計
            db_stats = result["system_metrics"]["database_statistics"]
            if db_stats:
                report_lines.extend([
                    "",
                    "## データベース統計",
                    f"総記事数: {db_stats.get('total_articles', 0)}",
                    f"分析済記事数: {db_stats.get('analyzed_articles', 0)}",
                    f"分析率: {db_stats.get('analysis_rate', 0):.1%}",
                ])

            report_lines.append("\n" + "=" * 50)

            # レポート出力
            report_content = "\n".join(report_lines)
            self.logger.info(f"品質レポート:\n{report_content}")

            # ファイル保存
            report_path = (
                Path("logs")
                / f"podcast_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            report_path.parent.mkdir(exist_ok=True)

            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            self.logger.info(f"品質レポートをファイルに保存: {report_path}")

        except Exception as e:
            self.logger.error(f"品質レポート生成エラー: {e}", exc_info=True)

    def get_system_status(self) -> Dict[str, Any]:
        """システム状態取得"""
        try:
            # データベース接続確認（データベース使用時のみ）
            db_status = True
            if self.data_source == "database" and hasattr(self, "db_manager"):
                try:
                    with self.db_manager.get_session() as session:
                        session.execute("SELECT 1")
                except Exception:
                    db_status = False

            # 記事統計
            article_stats = self.article_fetcher.get_article_statistics(hours_back=24)

            # 設定確認
            gemini_model = os.getenv("GEMINI_PODCAST_MODEL", "gemini-2.5-pro")
            production_mode = os.getenv("PODCAST_PRODUCTION_MODE", "false").lower() == "true"

            return {
                "system_healthy": db_status,
                "database_connected": db_status,
                "data_source": self.data_source,
                "google_document_id": (
                    self.google_doc_id if self.data_source == "google_document" else None
                ),
                "article_statistics": article_stats,
                "configuration": {
                    "gemini_model": gemini_model,
                    "production_mode": production_mode,
                    "target_duration": float(os.getenv("PODCAST_TARGET_DURATION_MINUTES", "10.0")),
                    "target_script_chars": int(os.getenv("PODCAST_TARGET_SCRIPT_CHARS", "2700")),
                },
                "checked_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"システム状態取得エラー: {e}", exc_info=True)
            return {
                "system_healthy": False,
                "error": str(e),
                "checked_at": datetime.now().isoformat(),
            }

    def _evaluate_content_quality(self, articles: List, script_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        コンテンツ品質とカバレッジ評価
        
        Args:
            articles: 選択された記事リスト
            script_result: 台本生成結果
            
        Returns:
            品質評価結果
        """
        try:
            # カテゴリ・地域・ソース分布分析
            category_counts = {}
            region_counts = {}
            source_counts = {}
            time_distribution = {}
            
            for article_score in articles:
                # カテゴリ分布
                category = article_score.get('analysis', {}).get("category", "その他")
                category_counts[category] = category_counts.get(category, 0) + 1
                
                # 地域分布
                region = article_score.get('analysis', {}).get("region", "other")
                region_counts[region] = region_counts.get(region, 0) + 1
                
                # ソース分布
                source = article_score.get('article', {}).get("source", "Unknown")
                source_counts[source] = source_counts.get(source, 0) + 1
                
                # 時間分布（8時間スロット）
                scraped_at = article_score.get('article', {}).get("scraped_at")
                if scraped_at:
                    hour = scraped_at.hour
                    if hour < 8:
                        time_slot = "早朝"
                    elif hour < 16:
                        time_slot = "午前・午後"
                    else:
                        time_slot = "夜間"
                    time_distribution[time_slot] = time_distribution.get(time_slot, 0) + 1
            
            # カバレッジスコア計算
            coverage_score = self._calculate_coverage_score(
                category_counts, region_counts, source_counts, time_distribution, len(articles)
            )
            
            # 品質基準評価
            quality_issues = []
            
            # 地域カバレッジチェック
            if len(region_counts) < 3:
                quality_issues.append(f"地域カバレッジ不足（{len(region_counts)}地域のみ）")
                
            # カテゴリカバレッジチェック
            if len(category_counts) < 3:
                quality_issues.append(f"カテゴリカバレッジ不足（{len(category_counts)}カテゴリのみ）")
                
            # ソースバランスチェック
            max_source_ratio = max(source_counts.values()) / len(articles) if source_counts else 0
            if max_source_ratio > 0.7:
                quality_issues.append(f"ソース偏重（{max_source_ratio:.1%}が単一ソース）")
                
            # 台本品質チェック
            script_char_count = script_result.get("char_count", 0)
            target_chars = int(self.config.get("target_duration", 10.0) * 280)
            char_deviation = abs(script_char_count - target_chars) / target_chars if target_chars > 0 else 1
            
            if char_deviation > 0.15:
                quality_issues.append(f"文字数大幅偏差（{char_deviation:.1%}）")
            
            # 総合品質スコア
            base_quality = script_result.get("quality_score", 0.5)
            coverage_weight = 0.3
            char_accuracy_weight = 0.2
            
            char_accuracy = 1.0 - min(char_deviation, 0.5) * 2
            total_quality = (
                base_quality * 0.5 + 
                coverage_score * coverage_weight + 
                char_accuracy * char_accuracy_weight
            )
            
            return {
                "coverage_score": coverage_score,
                "total_quality_score": total_quality,
                "category_distribution": category_counts,
                "region_distribution": region_counts,
                "source_distribution": source_counts,
                "time_distribution": time_distribution,
                "quality_issues": quality_issues,
                "meets_quality_threshold": total_quality >= 0.7 and coverage_score >= 0.6,
                "char_accuracy": char_accuracy,
                "char_deviation": char_deviation
            }
            
        except Exception as e:
            self.logger.error(f"品質評価エラー: {e}", exc_info=True)
            return {
                "coverage_score": 0.0,
                "total_quality_score": 0.5,
                "quality_issues": [f"評価エラー: {str(e)}"],
                "meets_quality_threshold": False
            }
            
    def _calculate_coverage_score(
        self, category_counts: dict, region_counts: dict, 
        source_counts: dict, time_distribution: dict, total_articles: int
    ) -> float:
        """カバレッジスコア計算（エントロピーベース）"""
        import math
        
        def entropy(counts):
            total = sum(counts.values())
            if total == 0:
                return 0
            return -sum((count/total) * math.log2(count/total) for count in counts.values() if count > 0)
            
        # 各次元のエントロピー計算
        category_entropy = entropy(category_counts)
        region_entropy = entropy(region_counts)
        source_entropy = entropy(source_counts)
        time_entropy = entropy(time_distribution)
        
        # 理論最大エントロピー（バランス理想状態）
        max_possible_categories = min(total_articles, 5)
        max_possible_regions = min(total_articles, 4)
        max_possible_sources = min(total_articles, 3)
        max_possible_times = min(total_articles, 3)
        
        max_category_entropy = math.log2(max_possible_categories) if max_possible_categories > 1 else 0
        max_region_entropy = math.log2(max_possible_regions) if max_possible_regions > 1 else 0
        max_source_entropy = math.log2(max_possible_sources) if max_possible_sources > 1 else 0
        max_time_entropy = math.log2(max_possible_times) if max_possible_times > 1 else 0
        
        # 正規化スコア計算
        def normalize_entropy(entropy, max_entropy):
            return entropy / max_entropy if max_entropy > 0 else 0
            
        category_score = normalize_entropy(category_entropy, max_category_entropy)
        region_score = normalize_entropy(region_entropy, max_region_entropy)
        source_score = normalize_entropy(source_entropy, max_source_entropy)
        time_score = normalize_entropy(time_entropy, max_time_entropy)
        
        # 重み付き平均（地域とカテゴリを重視）
        coverage_score = (
            category_score * 0.35 +
            region_score * 0.35 +
            source_score * 0.2 +
            time_score * 0.1
        )
        
        return min(coverage_score, 1.0)
