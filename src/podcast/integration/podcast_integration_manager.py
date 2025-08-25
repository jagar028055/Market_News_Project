# -*- coding: utf-8 -*-

"""
ポッドキャスト統合管理クラス
メインのニュース処理システムとポッドキャスト生成・LINE配信を統合
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging

from src.config.app_config import AppConfig
from src.podcast.script_generation.dialogue_script_generator import DialogueScriptGenerator
from src.podcast.tts.gemini_tts_engine import GeminiTTSEngine
from src.podcast.audio.audio_processor import AudioProcessor
from src.podcast.integration.line_broadcaster import LineBroadcaster
from src.podcast.integration.exceptions import PodcastConfigurationError, CostLimitExceededError
from src.podcast.publisher.github_pages_publisher import GitHubPagesPublisher


class PodcastIntegrationManager:
    """
    ポッドキャスト統合管理クラス

    ニュース処理システムとポッドキャスト生成・LINE配信を統合し、
    設定チェック、コスト管理、エラーハンドリングを提供
    """

    def __init__(self, config: Optional[AppConfig] = None, logger: Optional[logging.Logger] = None):
        """
        初期化

        Args:
            config: アプリケーション設定（オプション、自動生成される場合）
            logger: ロガー（オプション、自動生成される場合）
        """
        # 引数が提供されない場合は自動生成
        if config is None:
            from src.config.app_config import AppConfig

            self.config = AppConfig()
        else:
            self.config = config

        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        self.line_broadcaster = LineBroadcaster(self.config, self.logger)
        self.github_publisher = GitHubPagesPublisher(self.config, self.logger)

        # ポッドキャスト生成コンポーネント
        self.script_generator = None
        self.tts_engine = None
        self.audio_processor = None

    def is_podcast_enabled(self) -> bool:
        """
        ポッドキャスト機能が有効かチェック

        Returns:
            bool: ポッドキャスト機能が有効な場合True
        """
        # 環境変数でのポッドキャスト有効化チェック
        enabled = os.getenv("ENABLE_PODCAST_GENERATION", "").lower() == "true"

        if not enabled:
            self.logger.info(
                "ポッドキャスト生成が無効化されています (ENABLE_PODCAST_GENERATION != 'true')"
            )
            return False

        return True

    def check_configuration(self) -> bool:
        """
        ポッドキャスト設定の妥当性をチェック

        Returns:
            bool: 設定が有効な場合True

        Raises:
            PodcastConfigurationError: 設定が無効な場合
        """
        errors = []

        # Gemini API キーチェック
        if not self.config.ai.gemini_api_key:
            errors.append("GEMINI_API_KEY が設定されていません")

        # LINE設定チェック
        if not self.config.line.is_configured():
            errors.append("LINE設定が不完全です (LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET)")

        # ポッドキャスト基本設定チェック
        if not self.config.podcast.rss_base_url:
            errors.append("PODCAST_RSS_BASE_URL が設定されていません")

        if not self.config.podcast.author_name:
            errors.append("PODCAST_AUTHOR_NAME が設定されていません")

        if not self.config.podcast.author_email:
            errors.append("PODCAST_AUTHOR_EMAIL が設定されていません")

        # 音声アセットディレクトリチェック
        assets_dir = Path("src/podcast/assets")
        if not assets_dir.exists():
            errors.append(f"音声アセットディレクトリが存在しません: {assets_dir}")

        if errors:
            error_msg = "ポッドキャスト設定エラー: " + ", ".join(errors)
            raise PodcastConfigurationError(error_msg)

        self.logger.info("ポッドキャスト設定チェック完了")
        return True

    def check_cost_limits(self) -> bool:
        """
        月間コスト制限をチェック

        Returns:
            bool: コスト制限内の場合True

        Raises:
            CostLimitExceededError: コスト制限を超過している場合
        """
        # TODO: 実際のコスト追跡システムと連携
        # 現在は簡易実装として常にTrue

        monthly_limit = self.config.podcast.monthly_cost_limit_usd
        self.logger.info(f"月間コスト制限チェック (制限: ${monthly_limit})")

        # 実際の実装では、データベースから今月の使用量を取得
        # current_usage = self.get_monthly_usage()
        # if current_usage >= monthly_limit:
        #     raise CostLimitExceededError(f"月間コスト制限を超過: ${current_usage} >= ${monthly_limit}")

        return True

    def _initialize_components(self):
        """ポッドキャスト生成コンポーネントを初期化"""
        if not self.script_generator:
            self.script_generator = DialogueScriptGenerator(self.config.ai.gemini_api_key)

        if not self.tts_engine:
            self.tts_engine = GeminiTTSEngine(self.config.ai.gemini_api_key)

        if not self.audio_processor:
            self.audio_processor = AudioProcessor("src/podcast/assets")

    def generate_podcast_from_articles(self, articles: List[Dict[str, Any]]) -> Optional[str]:
        """
        記事からポッドキャストを生成

        Args:
            articles: ニュース記事のリスト

        Returns:
            Optional[str]: 生成されたポッドキャストファイルのパス（失敗時はNone）
        """
        if not articles:
            self.logger.warning("ポッドキャスト生成対象の記事がありません")
            return None

        try:
            self.logger.info(f"ポッドキャスト生成開始 (記事数: {len(articles)})")

            # コンポーネント初期化
            self._initialize_components()

            # 記事をポッドキャスト用に変換
            podcast_articles = self._prepare_articles_for_podcast(articles)

            # 台本生成
            self.logger.info("台本生成中...")
            script = self.script_generator.generate_script(podcast_articles)
            self.logger.info(f"台本生成完了 ({len(script)}文字)")

            # 音声合成
            self.logger.info("音声合成中...")
            audio_data = self.tts_engine.synthesize_dialogue(script)
            self.logger.info(f"音声合成完了 ({len(audio_data)}バイト)")

            # 音声処理
            self.logger.info("音声処理中...")
            episode_id = f"episode_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            audio_path = self.audio_processor.process_audio(audio_data, episode_id)
            self.logger.info(f"ポッドキャスト生成完了: {audio_path}")

            return audio_path

        except Exception as e:
            self.logger.error(f"ポッドキャスト生成エラー: {e}", exc_info=True)
            return None

    def _prepare_articles_for_podcast(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        記事をポッドキャスト生成用に変換

        Args:
            articles: 元の記事データ

        Returns:
            List[Dict[str, Any]]: ポッドキャスト用記事データ
        """
        podcast_articles = []

        for article in articles:
            # 必要な情報を抽出・変換
            podcast_article = {
                "title": article.get("title", ""),
                "summary": article.get("summary", ""),
                "sentiment": self._convert_sentiment(article.get("sentiment_label", "Neutral")),
                "url": article.get("url", ""),
                "source": article.get("source", ""),
                "published_at": self._format_published_date(article.get("published_jst")),
            }

            # 要約がある記事のみを対象
            if podcast_article["summary"] and podcast_article["summary"] != "要約はありません。":
                podcast_articles.append(podcast_article)

        self.logger.info(
            f"ポッドキャスト用記事準備完了 ({len(podcast_articles)}/{len(articles)}件)"
        )
        return podcast_articles

    def _convert_sentiment(self, sentiment_label: str) -> str:
        """
        センチメントラベルをポッドキャスト用に変換

        Args:
            sentiment_label: 元のセンチメントラベル

        Returns:
            str: 変換されたセンチメント
        """
        sentiment_map = {"Positive": "positive", "Negative": "negative", "Neutral": "neutral"}
        return sentiment_map.get(sentiment_label, "neutral")

    def _format_published_date(self, published_jst) -> str:
        """
        公開日時をISO形式に変換

        Args:
            published_jst: 公開日時（様々な形式）

        Returns:
            str: ISO形式の日時文字列
        """
        if not published_jst:
            return datetime.now().isoformat()

        # datetimeオブジェクトの場合
        if hasattr(published_jst, "isoformat"):
            return published_jst.isoformat()

        # 文字列の場合はそのまま返す（既にISO形式と仮定）
        return str(published_jst)

    def broadcast_podcast_to_line(
        self, podcast_path: str, articles: List[Dict[str, Any]], test_mode: bool = False
    ) -> bool:
        """
        ポッドキャストをLINEで配信

        Args:
            podcast_path: ポッドキャストファイルのパス
            articles: 元の記事データ（メッセージ作成用）
            test_mode: テストモード（テスト識別メッセージを含む）

        Returns:
            bool: 配信成功時True
        """
        if not podcast_path or not Path(podcast_path).exists():
            self.logger.error(f"ポッドキャストファイルが存在しません: {podcast_path}")
            return False

        try:
            # ファイル情報を取得
            file_path = Path(podcast_path)
            file_size_mb = file_path.stat().st_size / 1024 / 1024

            # エピソード情報を作成
            episode_info = {
                "file_path": podcast_path,
                "file_size_mb": file_size_mb,
                "article_count": len(articles),
                "published_at": datetime.now(),
                "test_mode": test_mode,
            }

            # GitHub Pages に配信
            self.logger.info("GitHub Pages へのポッドキャスト配信開始")
            audio_url = self.github_publisher.publish_podcast_episode(podcast_path, episode_info)

            if audio_url:
                self.logger.info(f"GitHub Pages 配信成功: {audio_url}")
            else:
                self.logger.warning("GitHub Pages 配信失敗、音声URLなしでLINE配信を続行")

            # LINE配信実行（音声URLを含める）
            return self.line_broadcaster.broadcast_podcast_notification(
                episode_info, articles, audio_url
            )

        except Exception as e:
            self.logger.error(f"LINE配信エラー: {e}", exc_info=True)
            return False

    def cleanup_old_podcast_files(self, days_to_keep: int = 7) -> None:
        """
        古いポッドキャストファイルをクリーンアップ

        Args:
            days_to_keep: 保持する日数
        """
        try:
            output_dir = Path("output/podcast")
            if not output_dir.exists():
                return

            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            deleted_count = 0

            for file_path in output_dir.glob("*.mp3"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
                    self.logger.debug(f"古いポッドキャストファイルを削除: {file_path}")

            if deleted_count > 0:
                self.logger.info(
                    f"古いポッドキャストファイルクリーンアップ完了 ({deleted_count}件削除)"
                )

        except Exception as e:
            self.logger.warning(f"ポッドキャストファイルクリーンアップエラー: {e}")

    def run_daily_podcast_workflow(
        self, test_mode: bool = False, custom_script_path: str = None
    ) -> bool:
        """
        日次ポッドキャストワークフロー実行

        Args:
            test_mode: テストモード（実際の配信を行わない）
            custom_script_path: カスタム台本ファイルパス（オプション）

        Returns:
            bool: 成功時True
        """
        try:
            self.logger.info(f"日次ポッドキャストワークフロー開始 (テストモード: {test_mode})")

            # ポッドキャスト機能有効性チェック
            if not self.is_podcast_enabled() and not test_mode:
                self.logger.info("ポッドキャスト機能が無効化されています")
                return False

            # 設定チェック（テストモードでは一部スキップ）
            if not test_mode:
                self.check_configuration()

            # 台本準備
            if custom_script_path and Path(custom_script_path).exists():
                # カスタム台本使用
                with open(custom_script_path, "r", encoding="utf-8") as f:
                    script = f.read()
                self.logger.info(f"カスタム台本を使用: {custom_script_path}")
            elif test_mode:
                # テストモード用の短縮台本生成
                script = self._generate_test_script()
                self.logger.info("テストモード: 短縮台本を使用")
            else:
                # 通常モード: ニュース記事を取得して台本生成
                self.logger.error("実際の台本生成機能が実装されていません")
                self.logger.error("ニュース記事からの台本生成システムが見つかりません")
                self.logger.error("本番モードで実行するには、実際の台本生成実装が必要です")
                raise NotImplementedError(
                    "台本生成機能が実装されていません。"
                    "ニュース記事からのポッドキャスト台本生成システムを実装してください。"
                )

            # 音声合成実行
            try:
                output_path = self._generate_podcast_audio(script, test_mode)
                if not output_path:
                    self.logger.error("音声合成に失敗しました")
                    self.logger.error("🚨 CRITICAL: 音声ファイルが生成されませんでした")
                    raise RuntimeError("音声合成完全失敗")
                
                # 音声ファイルの最終確認
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    self.logger.error(f"🚨 CRITICAL: 生成された音声ファイルが無効 - {output_path}")
                    self.logger.error(f"ファイル存在: {os.path.exists(output_path)}")
                    self.logger.error(f"ファイルサイズ: {os.path.getsize(output_path) if os.path.exists(output_path) else 'N/A'}")
                    raise RuntimeError(f"音声ファイル無効: {output_path}")
                
                self.logger.info(f"✅ 音声ファイル生成・検証完了: {output_path}")
                
            except Exception as e:
                self.logger.error(f"音声生成・検証エラー: {e}")
                raise e

            # 配信実行（テストモードでも実際にLINE配信を行う）
            if test_mode:
                self.logger.info(
                    f"テストモード: LINE配信も含めて実行 (音声ファイル: {output_path})"
                )
                # テストモード用のメッセージを作成してLINE配信実行
                return self.broadcast_podcast_to_line(str(output_path), [], test_mode=True)
            else:
                return self.broadcast_podcast_to_line(str(output_path), [])

        except Exception as e:
            self.logger.error(f"日次ポッドキャストワークフロー失敗: {e}", exc_info=True)
            self.logger.error("🚨 CRITICAL: ポッドキャストワークフローが例外で終了")
            raise e

    def run_script_only_workflow(self) -> bool:
        """
        台本生成専用ワークフロー（標準版）
        台本生成と分析のみを実行し、音声生成は行わない
        
        Returns:
            bool: 成功時True
        """
        try:
            self.logger.info("🎬 台本生成専用ワークフロー開始（標準版）")
            
            # テスト用スクリプト生成（既存のメソッドを使用）
            script = self._generate_test_script()
            
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
            
            self.logger.info("✅ 台本生成専用ワークフロー完了（標準版）")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 台本生成ワークフローでエラー（標準版）: {e}", exc_info=True)
            return False

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
        from datetime import datetime
        from pathlib import Path
        
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
        import os
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

    def _generate_test_script(self) -> str:
        """テスト用の短縮台本を生成"""
        return f"""
こんにちは、マーケットニュースポッドキャストへようこそ。
今日は{datetime.now().strftime('%Y年%m月%d日')}です。

これはGoogle Cloud Text-to-Speechのテスト配信です。

本日の主要なマーケット情報をお伝えします。

まず、日本株市場では、日経平均株価が前日比で小幅に上昇しました。
テクノロジー関連株が買われる一方、金融株には売り圧力が見られました。

次に、為替市場では、ドル円相場が安定した動きを見せています。
アメリカの経済指標の発表を控え、様子見の展開が続いています。

最後に、注目の材料として、来週発表予定の日本のGDP速報値に市場の関心が集まっています。

以上、本日のマーケットニュースをお伝えしました。
また明日お会いしましょう。ありがとうございました。
""".strip()

    def _generate_podcast_audio(self, script: str, test_mode: bool = False) -> Optional[Path]:
        """
        台本から音声ファイルを生成

        Args:
            script: 台本テキスト
            test_mode: テストモード

        Returns:
            Optional[Path]: 生成された音声ファイルのパス
        """
        try:
            # 出力ディレクトリを準備
            output_dir = Path("output/podcast")
            output_dir.mkdir(parents=True, exist_ok=True)

            # ファイル名を生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "test_" if test_mode else ""
            output_path = output_dir / f"{prefix}market_news_{timestamp}.mp3"

            # テストモードでは認証なしでダミーファイルを生成
            if test_mode:
                self.logger.info("テストモード: ダミー音声ファイルを生成します")
                # 短いサイレント音声を生成（約1秒）
                import subprocess
                try:
                    subprocess.run([
                        'ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=duration=1', 
                        '-acodec', 'mp3', str(output_path)
                    ], check=True, capture_output=True)
                    self.logger.info(f"テストモード: ダミーファイル生成完了 {output_path}")
                    return output_path
                except subprocess.CalledProcessError as e:
                    self.logger.error(f"ダミーファイル生成失敗: {e}")
                    # ダミーファイル生成失敗時は空のMP3ファイルを作成
                    output_path.write_bytes(b'')
                    return output_path

            # プロダクションモード: TTS エンジンを初期化（複数の候補変数名をチェック）
            credentials_json = None
            used_var = None

            # どの変数が使用されたかを記録
            if os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
                credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
                used_var = "GOOGLE_APPLICATION_CREDENTIALS_JSON"
            elif os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
                credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
                used_var = "GOOGLE_SERVICE_ACCOUNT_JSON"
            elif os.getenv("GCP_SA_KEY"):
                credentials_json = os.getenv("GCP_SA_KEY")
                used_var = "GCP_SA_KEY"

            if not credentials_json:
                credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if not credentials_path:
                    raise ValueError(
                        "Google Cloud認証情報が設定されていません（GOOGLE_APPLICATION_CREDENTIALS_JSON、GOOGLE_SERVICE_ACCOUNT_JSON、GCP_SA_KEY、GOOGLE_APPLICATION_CREDENTIALSのいずれも未設定）"
                    )
                credentials_json = credentials_path
                used_var = "GOOGLE_APPLICATION_CREDENTIALS"

            self.logger.info(
                f"Google Cloud認証に使用された変数: {used_var} ({len(credentials_json) if credentials_json else 0}文字)"
            )

            tts_engine = GeminiTTSEngine(credentials_json=credentials_json)

            # 音声合成実行
            self.logger.info(f"音声合成開始: {len(script)}文字の台本")
            audio_data = tts_engine.synthesize_dialogue(script, output_path)

            if audio_data and len(audio_data) > 0:
                # ファイル存在確認
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    self.logger.info(f"音声合成成功: {output_path} ({len(audio_data):,}バイト)")
                    self.logger.info(f"ファイル検証: サイズ {os.path.getsize(output_path):,}バイト")
                    return output_path
                else:
                    self.logger.error("音声ファイルの保存に失敗しました")
                    self.logger.error(f"🚨 CRITICAL: 音声ファイルが存在しないか空です - {output_path}")
                    raise RuntimeError(f"音声ファイル保存失敗: {output_path}")
            else:
                self.logger.error("音声データが生成されませんでした")
                self.logger.error("🚨 CRITICAL: 音声合成から空のデータが返されました")
                raise RuntimeError("音声データ生成失敗: 空のデータ")

        except Exception as e:
            self.logger.error(f"音声生成エラー: {e}", exc_info=True)
            self.logger.error("🚨 音声生成プロセスが例外で終了しました")
            raise e
