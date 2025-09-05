# -*- coding: utf-8 -*-

"""
独立ポッドキャスト配信システム メインエントリーポイント
GitHub Actionsとの連携、コマンドライン実行、設定管理を提供
"""

import asyncio
import argparse
import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# 独立ポッドキャストシステムのコンポーネント
from .workflow.independent_podcast_workflow import (
    IndependentPodcastWorkflow,
    WorkflowResult,
    WorkflowConfig,
)
from .config.podcast_config import get_podcast_config, validate_podcast_config, PodcastConfig
from .standalone.logging_config import setup_podcast_logging


class PodcastMainApplication:
    """
    ポッドキャストメインアプリケーション

    機能:
    - コマンドライン実行
    - GitHub Actions連携
    - 設定管理
    - ログ管理
    - エラーハンドリング
    - 結果出力
    """

    def __init__(self, config: Optional[PodcastConfig] = None):
        """
        初期化

        Args:
            config: ポッドキャスト設定（オプション）
        """
        self.config = config or get_podcast_config()
        self.logger = logging.getLogger(__name__)

        # ログシステムの初期化
        setup_podcast_logging(
            log_level=logging.DEBUG if self.config.debug_mode else logging.INFO,
            log_dir=str(self.config.directories.log_dir),
            enable_file_logging=True,
        )

        self.logger.info("ポッドキャストメインアプリケーション初期化完了")

    async def run_workflow(self, dry_run: bool = False) -> WorkflowResult:
        """
        ワークフローを実行

        Args:
            dry_run: ドライランモード（実際の処理は実行しない）

        Returns:
            WorkflowResult: 実行結果
        """
        self.logger.info("🚀 独立ポッドキャストワークフロー開始")

        if dry_run:
            self.logger.info("⚡ ドライランモード - 実際の処理はスキップします")

        try:
            # 設定バリデーション
            self._validate_environment()

            # ワークフロー設定の作成
            workflow_config = self.config.to_workflow_config()

            if dry_run:
                # ドライランの場合は設定チェックのみ
                return self._create_dry_run_result()

            # ワークフロー実行
            workflow = IndependentPodcastWorkflow(workflow_config)
            result = await workflow.execute_workflow()

            # 結果ログ出力
            self._log_workflow_result(result)

            # GitHub Actions出力（環境変数が設定されている場合）
            self._output_github_actions_results(result)

            return result

        except Exception as e:
            self.logger.error(f"❌ ワークフロー実行エラー: {e}")

            # エラー結果の作成
            error_result = WorkflowResult(
                success=False,
                episode_id=f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                errors=[str(e)],
            )

            return error_result

    def _validate_environment(self) -> None:
        """環境設定の検証"""
        self.logger.info("📋 環境設定の検証中...")

        try:
            validate_podcast_config()
            self.logger.info("✅ 環境設定検証完了")
        except ValueError as e:
            self.logger.error(f"❌ 環境設定エラー: {e}")
            raise

        # 設定サマリーの出力
        if self.config.debug_mode:
            summary = self.config.get_summary()
            self.logger.debug(f"設定サマリー: {json.dumps(summary, ensure_ascii=False, indent=2)}")

    def _create_dry_run_result(self) -> WorkflowResult:
        """ドライラン結果を作成"""
        return WorkflowResult(
            success=True,
            episode_id=f"dryrun_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            processing_time=0.0,
            metadata={"dry_run": True, "config_valid": True},
        )

    def _log_workflow_result(self, result: WorkflowResult) -> None:
        """ワークフロー結果をログ出力"""
        if result.success:
            self.logger.info("✅ ワークフロー実行成功")
            self.logger.info(f"  エピソードID: {result.episode_id}")
            self.logger.info(f"  処理時間: {result.processing_time:.2f}秒")
            self.logger.info(f"  処理記事数: {result.articles_processed}件")

            if result.audio_url:
                self.logger.info(f"  音声URL: {result.audio_url}")

            if result.rss_url:
                self.logger.info(f"  RSS URL: {result.rss_url}")

            if result.file_size_mb > 0:
                self.logger.info(f"  ファイルサイズ: {result.file_size_mb:.1f}MB")
        else:
            self.logger.error("❌ ワークフロー実行失敗")
            self.logger.error(f"  エピソードID: {result.episode_id}")

            if result.errors:
                self.logger.error("  エラー詳細:")
                for error in result.errors:
                    self.logger.error(f"    - {error}")

        if result.warnings:
            self.logger.warning("⚠️ 警告:")
            for warning in result.warnings:
                self.logger.warning(f"  - {warning}")

    def _output_github_actions_results(self, result: WorkflowResult) -> None:
        """GitHub Actions用の出力を生成"""
        github_output = os.getenv("GITHUB_OUTPUT")
        if not github_output:
            return

        try:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write(f"success={str(result.success).lower()}\\n")
                f.write(f"episode_id={result.episode_id}\\n")
                f.write(f"processing_time={result.processing_time}\\n")
                f.write(f"articles_processed={result.articles_processed}\\n")

                if result.audio_url:
                    f.write(f"audio_url={result.audio_url}\\n")

                if result.rss_url:
                    f.write(f"rss_url={result.rss_url}\\n")

                if result.file_size_mb > 0:
                    f.write(f"file_size_mb={result.file_size_mb}\\n")

                # エラーがある場合は最初のエラーメッセージを出力
                if result.errors:
                    error_message = result.errors[0].replace("\\n", " ")
                    f.write(f"error_message={error_message}\\n")

            self.logger.info("📊 GitHub Actions出力生成完了")

        except Exception as e:
            self.logger.warning(f"GitHub Actions出力生成エラー: {e}")

    def get_status_summary(self) -> Dict[str, Any]:
        """ステータスサマリーを取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "config": self.config.get_summary(),
            "system_status": {
                "podcast_enabled": self.config.enabled,
                "debug_mode": self.config.debug_mode,
                "production_mode": self.config.production_mode,
            },
        }


def create_argument_parser() -> argparse.ArgumentParser:
    """コマンドライン引数パーサーを作成"""
    parser = argparse.ArgumentParser(
        description="独立ポッドキャスト配信システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python -m src.podcast.main run                    # 通常実行
  python -m src.podcast.main run --dry-run          # ドライラン
  python -m src.podcast.main status                 # ステータス確認
  python -m src.podcast.main validate               # 設定検証のみ
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="実行コマンド")

    # run コマンド
    run_parser = subparsers.add_parser("run", help="ポッドキャストワークフローを実行")
    run_parser.add_argument(
        "--dry-run", action="store_true", help="ドライランモード（実際の処理はしない）"
    )
    run_parser.add_argument("--config", type=str, help="設定ファイルのパス")
    run_parser.add_argument("--debug", action="store_true", help="デバッグモードで実行")

    # status コマンド
    status_parser = subparsers.add_parser("status", help="システムステータスを表示")
    status_parser.add_argument("--json", action="store_true", help="JSON形式で出力")

    # validate コマンド
    validate_parser = subparsers.add_parser("validate", help="設定の妥当性を検証")
    validate_parser.add_argument("--config", type=str, help="設定ファイルのパス")

    return parser


async def main():
    """メイン関数"""
    parser = create_argument_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        # 設定読み込み
        config = get_podcast_config()

        # デバッグモードの設定
        if hasattr(args, "debug") and args.debug:
            config.debug_mode = True

        # アプリケーション初期化
        app = PodcastMainApplication(config)

        if args.command == "run":
            # ワークフロー実行
            result = await app.run_workflow(dry_run=args.dry_run)
            return 0 if result.success else 1

        elif args.command == "status":
            # ステータス表示
            status = app.get_status_summary()

            if args.json:
                print(json.dumps(status, ensure_ascii=False, indent=2))
            else:
                print("📊 ポッドキャストシステムステータス:")
                print(f"  実行時刻: {status['timestamp']}")
                print(f"  機能有効: {status['config']['enabled']}")
                print(f"  デバッグモード: {status['config']['debug_mode']}")
                print(f"  プロダクションモード: {status['config']['production_mode']}")
                print(f"  認証方式: {status['config']['google_auth_method']}")
                print(f"  Geminiモデル: {status['config']['gemini_model']}")
                print(f"  ポッドキャストタイトル: {status['config']['podcast_title']}")
                print(f"  最大記事数: {status['config']['max_articles']}")

            return 0

        elif args.command == "validate":
            # 設定検証
            try:
                validate_podcast_config()
                print("✅ 設定検証成功")
                return 0
            except ValueError as e:
                print(f"❌ 設定検証エラー: {e}")
                return 1

        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\\n⚠️ 実行が中断されました")
        return 1
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return 1


if __name__ == "__main__":
    import os

    # 非同期実行
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
