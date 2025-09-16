# -*- coding: utf-8 -*-

"""
独立ポッドキャスト配信ワークフロー
6つのコンポーネントを統合した包括的なオーケストレータークラス
"""

import os
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
import json

# 6つのコンポーネントをインポート
from ..standalone.gdrive_document_reader import GoogleDriveDocumentReader, DocumentReaderWithRetry
from ..script_generation.dialogue_script_generator import DialogueScriptGenerator
from ..tts.gemini_tts_engine import GeminiTTSEngine
from ..audio.audio_processor import AudioProcessor
from ..publisher.independent_github_pages_publisher import IndependentGitHubPagesPublisher
from ..integration.message_templates import MessageTemplates
from ..integration.distribution_error_handler import (
    DistributionErrorHandler,
    ErrorType,
    ErrorSeverity,
)


@dataclass
class WorkflowConfig:
    """ワークフローの設定"""

    # Google Drive設定
    google_document_id: str

    # Gemini API設定
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash-lite-001"

    # GitHub Pages設定
    github_repo_url: str
    github_pages_base_url: str

    # ポッドキャスト設定
    podcast_title: str = "マーケットニュース15分"
    podcast_description: str = "AIが生成する15分間の毎日マーケットニュース（拡張情報版）"
    podcast_author: str = "Market News Team"
    podcast_email: str = "podcast@example.com"

    # 処理設定（拡張版）
    max_articles: int = 12
    target_script_length: int = 4200
    audio_bitrate: str = "128k"
    enable_line_notification: bool = True

    # リトライ設定
    max_retries: int = 3
    retry_delay: float = 60.0

    # 出力設定
    output_dir: str = "output/podcast"
    assets_dir: str = "src/podcast/assets"

    # デバッグ設定
    debug_mode: bool = False
    save_intermediates: bool = True


@dataclass
class WorkflowResult:
    """ワークフロー実行結果"""

    success: bool
    episode_id: str
    audio_url: Optional[str] = None
    rss_url: Optional[str] = None
    processing_time: float = 0.0
    articles_processed: int = 0
    file_size_mb: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    script_info: Optional[Dict[str, Any]] = None  # 台本情報（テストモード用）
    message: Optional[str] = None  # 追加メッセージ


@dataclass
class WorkflowProgress:
    """ワークフロー進行状況"""

    current_step: str
    total_steps: int
    completed_steps: int
    step_start_time: datetime
    overall_start_time: datetime
    estimated_remaining_time: Optional[float] = None

    @property
    def progress_percentage(self) -> float:
        """進行率（%）"""
        return (self.completed_steps / self.total_steps) * 100 if self.total_steps > 0 else 0.0

    @property
    def elapsed_time(self) -> float:
        """経過時間（秒）"""
        return (datetime.now() - self.overall_start_time).total_seconds()


class IndependentPodcastWorkflow:
    """
    独立ポッドキャスト配信ワークフロー

    6つのコンポーネントを統合したオーケストレータークラス:
    1. GoogleDriveDocumentReader - 記事データ読み取り
    2. DialogueScriptGenerator - 台本生成
    3. GeminiTTSEngine - 音声合成
    4. AudioProcessor - 音声処理
    5. IndependentGitHubPagesPublisher - 配信
    6. MessageTemplates + DistributionErrorHandler - 通知・エラー処理

    Features:
    - 包括的なエラーハンドリング
    - 進行状況管理
    - 並列処理最適化
    - 自動リトライ機能
    - 品質管理
    - 詳細なログとメトリクス
    """

    WORKFLOW_STEPS = [
        "初期化",
        "Google Drive文書読み取り",
        "記事データ解析",
        "台本生成",
        "音声合成",
        "音声処理",
        "GitHub Pages配信",
        "通知送信",
        "クリーンアップ",
    ]

    def __init__(self, config: WorkflowConfig):
        """
        初期化

        Args:
            config: ワークフロー設定
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 進行状況管理
        self.progress = WorkflowProgress(
            current_step="",
            total_steps=len(self.WORKFLOW_STEPS),
            completed_steps=0,
            step_start_time=datetime.now(),
            overall_start_time=datetime.now(),
        )

        # 出力ディレクトリ作成
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # コンポーネント初期化（遅延初期化）
        self._gdrive_reader: Optional[GoogleDriveDocumentReader] = None
        self._script_generator: Optional[DialogueScriptGenerator] = None
        self._tts_engine: Optional[GeminiTTSEngine] = None
        self._audio_processor: Optional[AudioProcessor] = None
        self._publisher: Optional[IndependentGitHubPagesPublisher] = None
        self._message_templates: Optional[MessageTemplates] = None
        self._error_handler: Optional[DistributionErrorHandler] = None

        # 一時ファイル管理
        self._temp_files: List[Path] = []

        # メトリクス
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "processing_times": {},
            "component_stats": {},
            "errors": [],
            "warnings": [],
        }

        self.logger.info(f"IndependentPodcastWorkflow初期化完了 - 出力: {self.output_dir}")

    @property
    def gdrive_reader(self) -> GoogleDriveDocumentReader:
        """Google Drive文書リーダー（遅延初期化）"""
        if self._gdrive_reader is None:
            if self.config.max_retries > 1:
                self._gdrive_reader = DocumentReaderWithRetry(
                    max_retries=self.config.max_retries, retry_delay=self.config.retry_delay
                )
            else:
                self._gdrive_reader = GoogleDriveDocumentReader()
            self.logger.debug("Google Drive Reader初期化完了")
        return self._gdrive_reader

    @property
    def script_generator(self) -> DialogueScriptGenerator:
        """台本生成器（遅延初期化）"""
        if self._script_generator is None:
            self._script_generator = DialogueScriptGenerator(
                api_key=self.config.gemini_api_key, model_name=self.config.gemini_model
            )
            self.logger.debug("Script Generator初期化完了")
        return self._script_generator

    @property
    def tts_engine(self) -> GeminiTTSEngine:
        """音声合成エンジン（遅延初期化）"""
        if self._tts_engine is None:
            self._tts_engine = GeminiTTSEngine(api_key=self.config.gemini_api_key)
            self.logger.debug("TTS Engine初期化完了")
        return self._tts_engine

    @property
    def audio_processor(self) -> AudioProcessor:
        """音声処理器（遅延初期化）"""
        if self._audio_processor is None:
            self._audio_processor = AudioProcessor(assets_dir=self.config.assets_dir)
            # ビットレート設定更新
            self._audio_processor.update_settings({"bitrate": self.config.audio_bitrate})
            self.logger.debug("Audio Processor初期化完了")
        return self._audio_processor

    @property
    def publisher(self) -> IndependentGitHubPagesPublisher:
        """配信システム（遅延初期化）"""
        if self._publisher is None:
            podcast_info = {
                "title": self.config.podcast_title,
                "description": self.config.podcast_description,
                "author": self.config.podcast_author,
                "email": self.config.podcast_email,
            }

            self._publisher = IndependentGitHubPagesPublisher(
                github_repo_url=self.config.github_repo_url,
                base_url=self.config.github_pages_base_url,
                podcast_info=podcast_info,
            )
            self.logger.debug("Publisher初期化完了")
        return self._publisher

    @property
    def message_templates(self) -> MessageTemplates:
        """メッセージテンプレート（遅延初期化）"""
        if self._message_templates is None:
            self._message_templates = MessageTemplates(base_url=self.config.github_pages_base_url)
            self.logger.debug("Message Templates初期化完了")
        return self._message_templates

    @property
    def error_handler(self) -> DistributionErrorHandler:
        """エラーハンドラー（遅延初期化）"""
        if self._error_handler is None:
            self._error_handler = DistributionErrorHandler(
                base_url=self.config.github_pages_base_url
            )
            self.logger.debug("Error Handler初期化完了")
        return self._error_handler

    async def execute_workflow(self) -> WorkflowResult:
        """
        ワークフロー全体を実行

        Returns:
            WorkflowResult: 実行結果
        """
        self.logger.info("🚀 独立ポッドキャストワークフロー実行開始")
        self.metrics["start_time"] = datetime.now()

        result = WorkflowResult(
            success=False, episode_id=self._generate_episode_id(), processing_time=0.0
        )

        try:
            # ステップ1: 初期化
            await self._execute_step("初期化", self._step_initialization, result)

            # ステップ2: Google Drive文書読み取り
            articles_data = await self._execute_step(
                "Google Drive文書読み取り", self._step_read_articles, result
            )

            # ステップ3: 記事データ解析・厳選
            selected_articles = await self._execute_step(
                "記事データ解析", lambda: self._step_analyze_articles(articles_data), result
            )
            result.articles_processed = len(selected_articles)

            # ステップ4: 台本生成
            script = await self._execute_step(
                "台本生成", lambda: self._step_generate_script(selected_articles), result
            )

            # ステップ5: 音声合成
            audio_data = await self._execute_step(
                "音声合成", lambda: self._step_synthesize_audio(script, result.episode_id), result
            )

            # ステップ6: 音声処理
            processed_audio_path = await self._execute_step(
                "音声処理",
                lambda: self._step_process_audio(audio_data, result.episode_id, selected_articles),
                result,
            )

            # ステップ7: GitHub Pages配信
            audio_url = await self._execute_step(
                "GitHub Pages配信",
                lambda: self._step_publish_to_github(
                    processed_audio_path, result.episode_id, selected_articles
                ),
                result,
            )
            result.audio_url = audio_url
            result.rss_url = self.publisher.get_rss_url()

            # ファイルサイズ記録
            if Path(processed_audio_path).exists():
                result.file_size_mb = Path(processed_audio_path).stat().st_size / (1024 * 1024)

            # ステップ8: 通知送信
            if self.config.enable_line_notification:
                await self._execute_step(
                    "通知送信",
                    lambda: self._step_send_notifications(result, selected_articles),
                    result,
                )

            # ステップ9: クリーンアップ
            await self._execute_step("クリーンアップ", self._step_cleanup, result)

            # 成功完了
            result.success = True
            self.logger.info("✅ ワークフロー実行完了")

        except Exception as e:
            self.logger.error(f"❌ ワークフロー実行エラー: {e}")

            # エラー処理
            error_info = self.error_handler.handle_error(
                ErrorType.UNKNOWN_ERROR,
                str(e),
                context={"episode_id": result.episode_id, "step": self.progress.current_step},
            )

            result.errors.append(str(e))
            result.success = False

            # クリーンアップは常に実行
            try:
                await self._step_cleanup()
            except Exception as cleanup_error:
                self.logger.warning(f"クリーンアップエラー: {cleanup_error}")

        finally:
            # 最終処理
            self.metrics["end_time"] = datetime.now()
            result.processing_time = self.progress.elapsed_time

            # メトリクス記録
            await self._record_metrics(result)

        return result

    async def execute_script_test_mode(self) -> WorkflowResult:
        """
        台本確認専用モード - 台本生成まで実行して詳細分析を行う
        
        Returns:
            WorkflowResult: 台本テスト結果
        """
        self.logger.info("📄 台本テストモード開始")
        
        episode_id = self._generate_episode_id()
        
        try:
            # ステップ1: 初期化
            await self._step_initialization()
            
            # ステップ2: 記事データ読み込み
            articles = await self._step_read_articles()
            
            # ステップ3: 記事分析
            analyzed_articles = await self._step_analyze_articles(articles)
            
            # ステップ4: 台本生成
            script = await self._step_generate_script(analyzed_articles)
            
            # 台本の詳細分析
            script_info = self._analyze_script_content(script, episode_id)
            
            # 台本表示
            self._display_script_analysis(script, script_info)
            
            # 成功結果を作成
            result = WorkflowResult(
                success=True,
                episode_id=episode_id,
                script_info=script_info,
                message="台本生成テスト完了"
            )
            
            self.logger.info("✅ 台本テストモード完了")
            return result
            
        except Exception as e:
            error_message = f"台本テストモードでエラー: {str(e)}"
            self.logger.error(f"❌ {error_message}")
            
            return WorkflowResult(
                success=False,
                episode_id=episode_id,
                errors=[error_message]
            )

    def _analyze_script_content(self, script: str, episode_id: str) -> Dict[str, Any]:
        """
        台本の詳細分析を実行（強化版）
        
        Args:
            script: 台本テキスト
            episode_id: エピソードID
            
        Returns:
            Dict[str, Any]: 分析結果
        """
        lines = script.split('\n')
        total_lines = len(lines)
        char_count = len(script)
        
        # スピーカー別の行数をカウント
        speaker_a_lines = 0
        speaker_b_lines = 0
        other_lines = 0
        
        # 【改善】より詳細な発話分析
        speaker_a_chars = 0
        speaker_b_chars = 0
        long_lines = 0
        empty_lines = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                empty_lines += 1
                continue
                
            if line.startswith('A:'):
                speaker_a_lines += 1
                speaker_a_chars += len(line[2:].strip())  # "A:"を除いた文字数
            elif line.startswith('B:'):
                speaker_b_lines += 1
                speaker_b_chars += len(line[2:].strip())  # "B:"を除いた文字数
            elif line:  # 空行でない場合
                other_lines += 1
            
            # 長すぎる行の検出（TTS向け）
            if len(line) > 120:  # 1行120文字超は読みにくい
                long_lines += 1
        
        # 推定読み上げ時間（日本語: 約400文字/分）
        estimated_minutes = char_count / 400
        estimated_duration = f"{int(estimated_minutes)}分{int((estimated_minutes % 1) * 60)}秒"
        
        # 台本ファイルのパス
        script_file = self.output_dir / f"{episode_id}_script.txt"
        
        # 【改善】問題検出の拡張
        issues = []
        warnings = []
        
        # 基本的な長さチェック
        if char_count < 1000:
            issues.append("台本が短すぎます（1000文字未満）")
        if char_count > 8000:
            issues.append("台本が長すぎます（8000文字超過）")
        
        # スピーカーバランスチェック
        if speaker_a_lines == 0:
            issues.append("スピーカーAの台詞がありません")
        if speaker_b_lines == 0:
            issues.append("スピーカーBの台詞がありません")
        
        total_speaker_lines = speaker_a_lines + speaker_b_lines
        if total_speaker_lines > 0:
            if abs(speaker_a_lines - speaker_b_lines) > max(speaker_a_lines, speaker_b_lines) * 0.3:
                warnings.append("スピーカー間の台詞数バランスが悪い")
        
        # 【改善】新しい品質チェック
        if long_lines > 0:
            warnings.append(f"長すぎる行が{long_lines}行あります（TTS読み上げに不適切）")
        
        if other_lines > total_speaker_lines * 0.3:
            warnings.append("ナレーション行が多すぎます（対話形式台本として不適切）")
        
        # 文字数バランスチェック
        if speaker_a_chars > 0 and speaker_b_chars > 0:
            char_ratio = max(speaker_a_chars, speaker_b_chars) / min(speaker_a_chars, speaker_b_chars)
            if char_ratio > 2.0:
                warnings.append("スピーカー間の発話量に大きな偏りがあります")
        
        # 【改善】台本構造チェック
        structure_score = 100
        if not script.strip():
            structure_score = 0
        elif char_count < 2000:
            structure_score -= 20
        elif char_count > 6000:
            structure_score -= 10
        
        if long_lines > 0:
            structure_score -= min(20, long_lines * 2)
        
        if len(issues) > 0:
            structure_score -= len(issues) * 15
        if len(warnings) > 0:
            structure_score -= len(warnings) * 5
        
        structure_score = max(0, structure_score)
        
        # 【改善】開始・終了パターンチェック
        proper_start = False
        proper_end = False
        
        # 適切な開始パターンの検索
        start_patterns = [
            r'(みなさん|皆さん|皆様).*?(おはよう|こんにちは)',
            r'\d{4}年\d+月\d+日',
            r'(ポッドキャスト|番組).*?(時間|開始)',
        ]
        
        script_start = script[:200]
        for pattern in start_patterns:
            if re.search(pattern, script_start, re.IGNORECASE):
                proper_start = True
                break
        
        # 適切な終了パターンの検索  
        end_patterns = [
            r'明日.*?よろしく.*?お願い.*?します',
            r'以上.*?ポッドキャスト.*?でした',
            r'また.*?(明日|次回).*?お会い',
        ]
        
        script_end = script[-300:]
        for pattern in end_patterns:
            if re.search(pattern, script_end, re.IGNORECASE):
                proper_end = True
                break
        
        if not proper_start:
            warnings.append("適切な開始挨拶が見つかりません")
        if not proper_end:
            warnings.append("適切な終了挨拶が見つかりません")
        
        return {
            'char_count': char_count,
            'line_count': total_lines,
            'empty_lines': empty_lines,
            'speaker_a_lines': speaker_a_lines,
            'speaker_b_lines': speaker_b_lines,
            'speaker_a_chars': speaker_a_chars,
            'speaker_b_chars': speaker_b_chars,
            'other_lines': other_lines,
            'long_lines': long_lines,
            'estimated_duration': estimated_duration,
            'estimated_minutes': estimated_minutes,
            'script_file': str(script_file),
            'issues': issues,
            'warnings': warnings,
            'structure_score': structure_score,
            'proper_start': proper_start,
            'proper_end': proper_end,
            'speaker_balance_ratio': speaker_a_chars / speaker_b_chars if speaker_b_chars > 0 else 0,
        }

    def _display_script_analysis(self, script: str, script_info: Dict[str, Any]) -> None:
        """
        台本分析結果を詳細表示（強化版）
        
        Args:
            script: 台本テキスト
            script_info: 分析結果
        """
        self.logger.info("=" * 60)
        self.logger.info("📄 台本分析結果（詳細版）")
        self.logger.info("=" * 60)
        
        # 基本統計
        self.logger.info(f"📊 基本統計:")
        self.logger.info(f"  文字数: {script_info['char_count']:,}文字")
        self.logger.info(f"  総行数: {script_info['line_count']}行")
        self.logger.info(f"  空行数: {script_info.get('empty_lines', 0)}行")
        self.logger.info(f"  推定時間: {script_info['estimated_duration']}")
        self.logger.info(f"  推定時間（分）: {script_info['estimated_minutes']:.1f}分")
        
        # スピーカー分析（拡張）
        self.logger.info(f"\n🎭 スピーカー分析:")
        self.logger.info(f"  スピーカーA: {script_info['speaker_a_lines']}行 ({script_info.get('speaker_a_chars', 0)}文字)")
        self.logger.info(f"  スピーカーB: {script_info['speaker_b_lines']}行 ({script_info.get('speaker_b_chars', 0)}文字)")
        self.logger.info(f"  その他: {script_info['other_lines']}行")
        
        total_speaker_lines = script_info['speaker_a_lines'] + script_info['speaker_b_lines']
        if total_speaker_lines > 0:
            a_ratio = script_info['speaker_a_lines'] / total_speaker_lines * 100
            b_ratio = script_info['speaker_b_lines'] / total_speaker_lines * 100
            self.logger.info(f"  A:B行数比率 = {a_ratio:.1f}% : {b_ratio:.1f}%")
            
            # 【改善】文字数比率も表示
            if script_info.get('speaker_balance_ratio', 0) > 0:
                char_ratio = script_info['speaker_balance_ratio']
                self.logger.info(f"  A:B文字数比率 = {char_ratio:.2f} : 1")
        
        # 【改善】品質スコア表示
        structure_score = script_info.get('structure_score', 0)
        score_emoji = "🟢" if structure_score >= 80 else "🟡" if structure_score >= 60 else "🔴"
        self.logger.info(f"\n{score_emoji} 品質スコア: {structure_score}/100")
        
        # 【改善】構造チェック結果
        self.logger.info(f"\n🏗️ 構造チェック:")
        proper_start = script_info.get('proper_start', False)
        proper_end = script_info.get('proper_end', False)
        self.logger.info(f"  適切な開始: {'✅' if proper_start else '❌'}")
        self.logger.info(f"  適切な終了: {'✅' if proper_end else '❌'}")
        
        long_lines = script_info.get('long_lines', 0)
        if long_lines > 0:
            self.logger.info(f"  長すぎる行: {long_lines}行 ⚠️")
        else:
            self.logger.info(f"  長すぎる行: なし ✅")
        
        # ファイル情報
        self.logger.info(f"\n📁 ファイル情報:")
        self.logger.info(f"  保存先: {script_info['script_file']}")
        
        # 【改善】問題検出結果（詳細表示）
        issues = script_info.get('issues', [])
        warnings = script_info.get('warnings', [])
        
        if issues:
            self.logger.info(f"\n🚨 重大な問題 ({len(issues)}件):")
            for i, issue in enumerate(issues, 1):
                self.logger.error(f"  {i}. {issue}")
        
        if warnings:
            self.logger.info(f"\n⚠️  警告 ({len(warnings)}件):")
            for i, warning in enumerate(warnings, 1):
                self.logger.warning(f"  {i}. {warning}")
        
        if not issues and not warnings:
            self.logger.info(f"\n✅ 問題は検出されませんでした")
        
        # 【改善】推奨事項
        recommendations = []
        
        if script_info['char_count'] < 2000:
            recommendations.append("台本をもう少し長くすることを推奨します")
        elif script_info['char_count'] > 6000:
            recommendations.append("台本が長めです。重要な内容に絞ることを検討してください")
        
        if long_lines > 0:
            recommendations.append("長い行を短く分割してTTS読み上げを改善してください")
        
        balance_ratio = script_info.get('speaker_balance_ratio', 1)
        if balance_ratio > 2.0 or (balance_ratio > 0 and balance_ratio < 0.5):
            recommendations.append("スピーカー間の発話バランスを調整してください")
        
        if not proper_start:
            recommendations.append("適切な開始挨拶を追加してください")
        if not proper_end:
            recommendations.append("適切な終了挨拶を追加してください")
        
        if recommendations:
            self.logger.info(f"\n💡 推奨事項:")
            for i, rec in enumerate(recommendations, 1):
                self.logger.info(f"  {i}. {rec}")
        
        # 台本プレビュー（最初の500文字）
        self.logger.info(f"\n📖 台本プレビュー（最初の500文字）:")
        self.logger.info("-" * 40)
        preview = script[:500] + "..." if len(script) > 500 else script
        self.logger.info(preview)
        self.logger.info("-" * 40)
        
        # 【改善】最後の100文字もプレビュー
        if len(script) > 500:
            self.logger.info(f"\n📖 台本終了部分（最後の200文字）:")
            self.logger.info("-" * 40)
            ending_preview = script[-200:]
            self.logger.info(ending_preview)
            self.logger.info("-" * 40)
        
        self.logger.info("=" * 60)

    async def _execute_step(self, step_name: str, step_func, result: WorkflowResult):
        """
        単一ステップの実行

        Args:
            step_name: ステップ名
            step_func: ステップ実行関数
            result: 結果オブジェクト

        Returns:
            Any: ステップの実行結果
        """
        self.progress.current_step = step_name
        self.progress.step_start_time = datetime.now()

        self.logger.info(
            f"📍 ステップ開始: {step_name} ({self.progress.completed_steps + 1}/{self.progress.total_steps})"
        )

        step_start = datetime.now()

        try:
            # ステップ実行
            if asyncio.iscoroutinefunction(step_func):
                step_result = await step_func()
            else:
                step_result = step_func()

            # 成功処理
            self.progress.completed_steps += 1
            processing_time = (datetime.now() - step_start).total_seconds()
            self.metrics["processing_times"][step_name] = processing_time

            self.logger.info(f"✅ ステップ完了: {step_name} ({processing_time:.2f}秒)")

            return step_result

        except Exception as e:
            # エラー処理
            processing_time = (datetime.now() - step_start).total_seconds()
            self.metrics["processing_times"][step_name] = processing_time

            self.logger.error(f"❌ ステップ失敗: {step_name} - {e}")

            # エラー記録
            result.errors.append(f"{step_name}: {str(e)}")

            raise

    def _generate_episode_id(self) -> str:
        """エピソードIDを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        return f"market_news_{timestamp}"

    async def _step_initialization(self) -> None:
        """ステップ1: 初期化"""
        # 必要なディレクトリの作成
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # コンポーネントの事前チェック
        try:
            # Google Drive アクセステスト
            is_accessible = self.gdrive_reader.validate_document_access(
                self.config.google_document_id
            )
            if not is_accessible:
                raise Exception("Google Driveドキュメントにアクセスできません")

            self.logger.info("✅ 初期化チェック完了")

        except Exception as e:
            raise Exception(f"初期化エラー: {e}")

    async def _step_read_articles(self) -> List[Dict[str, Any]]:
        """ステップ2: Google Drive文書読み取り"""
        try:
            metadata, articles = self.gdrive_reader.read_and_parse_document(
                self.config.google_document_id, use_cache=True
            )

            if not articles:
                raise Exception("記事データが取得できませんでした")

            self.logger.info(f"✅ {len(articles)}件の記事を読み取り")

            # 記事データをDict形式に変換
            articles_dict = []
            for article in articles:
                articles_dict.append(
                    {
                        "title": article.title,
                        "url": article.url,
                        "summary": article.summary,
                        "sentiment_label": article.sentiment_label,
                        "sentiment_score": article.sentiment_score,
                        "source": article.source,
                        "published_date": article.published_jst.isoformat(),
                    }
                )

            return articles_dict

        except Exception as e:
            raise Exception(f"記事読み取りエラー: {e}")

    async def _step_analyze_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """ステップ3: 記事データ解析・厳選"""
        if not articles:
            raise Exception("解析する記事がありません")

        # 記事の重要度スコア計算
        scored_articles = []
        for article in articles:
            score = self._calculate_article_importance(article)
            article_with_score = article.copy()
            article_with_score["importance_score"] = score
            scored_articles.append(article_with_score)

        # 重要度順でソート
        scored_articles.sort(key=lambda x: x["importance_score"], reverse=True)

        # 最大記事数まで厳選
        selected_articles = scored_articles[: self.config.max_articles]

        self.logger.info(f"✅ {len(articles)}件から{len(selected_articles)}件を厳選")

        return selected_articles

    def _calculate_article_importance(self, article: Dict[str, Any]) -> float:
        """記事の重要度スコアを計算（改善版）"""
        score = 0.0

        # センチメントスコアの絶対値（話題性）
        sentiment_score = abs(article.get("sentiment_score", 0.0))
        score += sentiment_score * 0.35  # 0.4 → 0.35 に調整

        # 要約の長さ（詳細度）
        summary_length = len(article.get("summary", ""))
        score += min(summary_length / 500.0, 1.0) * 0.25  # 0.3 → 0.25 に調整

        # タイトルの長さ（詳細度）
        title_length = len(article.get("title", ""))
        score += min(title_length / 100.0, 1.0) * 0.15  # 0.2 → 0.15 に調整

        # 【改善】記事の新鮮度評価を追加
        try:
            from datetime import datetime
            published_date_str = article.get("published_date", "")
            if published_date_str:
                published_date = datetime.fromisoformat(published_date_str.replace('Z', '+00:00'))
                hours_old = (datetime.now().replace(tzinfo=published_date.tzinfo) - published_date).total_seconds() / 3600
                # 24時間以内は最大0.15ポイント、それ以降は減衰
                freshness_score = max(0, min(0.15, 0.15 * (1 - hours_old / 24)))
                score += freshness_score
        except Exception:
            pass  # 日付解析エラーは無視

        # ソースの信頼度（拡張）
        source = article.get("source", "").lower()
        if "reuters" in source:
            score += 0.12  # 0.1 → 0.12 に増加
        elif "bloomberg" in source:
            score += 0.12  # 0.1 → 0.12 に増加
        elif "nikkei" in source or "日経" in source:
            score += 0.10  # 日経追加
        elif "wsj" in source or "wall street journal" in source:
            score += 0.10  # WSJ追加
        elif "ft.com" in source or "financial times" in source:
            score += 0.10  # FT追加

        # 【改善】キーワードベースの重要度評価
        title_and_summary = (article.get("title", "") + " " + article.get("summary", "")).lower()
        
        # 高重要度キーワード（市場に大きな影響を与える事象）
        high_impact_keywords = ["fed", "central bank", "interest rate", "gdp", "inflation", "recession", 
                               "market crash", "stimulus", "bailout", "merger", "acquisition",
                               "中央銀行", "金利", "インフレ", "景気後退", "刺激策"]
        for keyword in high_impact_keywords:
            if keyword in title_and_summary:
                score += 0.08
                break  # 複数該当でも1回のみ加算

        # 中重要度キーワード（投資家が注目する事象）
        medium_impact_keywords = ["earnings", "revenue", "profit", "dividend", "stock split", "ipo",
                                 "決算", "売上", "利益", "配当", "株式分割", "新規上場"]
        for keyword in medium_impact_keywords:
            if keyword in title_and_summary:
                score += 0.05
                break

        return min(score, 2.0)  # 最大スコア制限を追加

    async def _step_generate_script(self, articles: List[Dict[str, Any]]) -> str:
        """ステップ4: 台本生成"""
        try:
            script = self.script_generator.generate_script(articles)

            if not script or len(script) < 1000:
                raise Exception("台本が短すぎます")

            # 中間ファイル保存（デバッグ用）
            if self.config.save_intermediates:
                script_path = self.output_dir / f"{self._generate_episode_id()}_script.txt"
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(script)
                self._temp_files.append(script_path)

            self.logger.info(f"✅ 台本生成完了 - {len(script)}文字")

            return script

        except Exception as e:
            raise Exception(f"台本生成エラー: {e}")

    async def _step_synthesize_audio(self, script: str, episode_id: str) -> bytes:
        """ステップ5: 音声合成"""
        try:
            audio_data = self.tts_engine.synthesize_dialogue(script)

            if not audio_data:
                raise Exception("音声データが生成されませんでした")

            # 中間ファイル保存（デバッグ用）
            if self.config.save_intermediates:
                raw_audio_path = self.output_dir / f"{episode_id}_raw.mp3"
                with open(raw_audio_path, "wb") as f:
                    f.write(audio_data)
                self._temp_files.append(raw_audio_path)

            self.logger.info(f"✅ 音声合成完了 - {len(audio_data)}バイト")

            return audio_data

        except Exception as e:
            raise Exception(f"音声合成エラー: {e}")

    async def _step_process_audio(
        self, audio_data: bytes, episode_id: str, articles: List[Dict[str, Any]]
    ) -> str:
        """ステップ6: 音声処理"""
        try:
            # メタデータ作成
            metadata = {
                "title": f"{self.config.podcast_title} - {datetime.now().strftime('%Y年%m月%d日')}",
                "artist": self.config.podcast_author,
                "album": self.config.podcast_title,
                "date": datetime.now().strftime("%Y"),
                "genre": "News",
                "comment": f"記事数: {len(articles)}件",
            }

            processed_path = self.audio_processor.process_audio(
                audio_data=audio_data, episode_id=episode_id, metadata=metadata
            )

            self.logger.info(f"✅ 音声処理完了 - 出力: {processed_path}")

            return processed_path

        except Exception as e:
            raise Exception(f"音声処理エラー: {e}")

    async def _step_publish_to_github(
        self, audio_file_path: str, episode_id: str, articles: List[Dict[str, Any]]
    ) -> Optional[str]:
        """ステップ7: GitHub Pages配信"""
        try:
            # エピソードメタデータ作成
            episode_metadata = {
                "title": f"{self.config.podcast_title} - {datetime.now().strftime('%Y年%m月%d日')}",
                "description": f"本日の市場動向を{len(articles)}件の記事から解説",
                "published_date": datetime.now(),
                "duration": "00:10:00",  # 固定値（実際の再生時間は音声処理後に取得可能）
                "keywords": ["market", "news", "finance", "japan", "ai"],
                "episode_number": self._get_next_episode_number(),
            }

            audio_url = self.publisher.publish_episode(
                audio_file=Path(audio_file_path), episode_metadata=episode_metadata
            )

            if not audio_url:
                raise Exception("配信URLが取得できませんでした")

            self.logger.info(f"✅ 配信完了 - URL: {audio_url}")

            return audio_url

        except Exception as e:
            raise Exception(f"配信エラー: {e}")

    def _get_next_episode_number(self) -> int:
        """次のエピソード番号を取得"""
        try:
            episodes = self.publisher.get_episode_list()
            if episodes:
                max_episode = max([ep.get("episode_number", 0) for ep in episodes])
                return max_episode + 1
            return 1
        except:
            return 1

    async def _step_send_notifications(
        self, result: WorkflowResult, articles: List[Dict[str, Any]]
    ) -> None:
        """ステップ8: 通知送信"""
        try:
            # 通知メッセージ作成
            episode_data = {
                "title": f"{self.config.podcast_title} - {datetime.now().strftime('%Y年%m月%d日')}",
                "duration": "約10分",
                "date": datetime.now().strftime("%Y年%m月%d日"),
                "summary": self._create_articles_summary(articles),
                "filename": Path(result.audio_url).name if result.audio_url else "",
                "file_size_mb": result.file_size_mb,
                "episode_number": self._get_next_episode_number() - 1,  # 既に配信済みなので-1
            }

            notification_message = self.message_templates.create_podcast_notification(episode_data)

            # 実際の通知送信は外部システムに依存するため、ここではログ出力
            self.logger.info("📢 通知メッセージ生成完了")
            if self.config.debug_mode:
                self.logger.debug(f"通知内容:\n{notification_message}")

        except Exception as e:
            # 通知エラーは致命的ではないため、警告レベル
            self.logger.warning(f"通知送信エラー: {e}")

    def _create_articles_summary(self, articles: List[Dict[str, Any]]) -> str:
        """記事から要約を作成"""
        if not articles:
            return "本日の重要な市場動向をお届けします。"

        summaries = []
        for i, article in enumerate(articles[:3], 1):
            title = article.get("title", "").strip()
            if title and len(title) > 10:
                if len(title) > 40:
                    title = title[:37] + "..."
                summaries.append(f"{i}. {title}")

        return "\n".join(summaries) if summaries else "本日の重要な市場動向をお届けします。"

    async def _step_cleanup(self) -> None:
        """ステップ9: クリーンアップ"""
        try:
            # 一時ファイルの削除
            deleted_count = 0
            for temp_file in self._temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                        deleted_count += 1
                except Exception as e:
                    self.logger.warning(f"一時ファイル削除エラー: {temp_file} - {e}")

            # キャッシュクリーンアップ
            if self._gdrive_reader:
                cache_cleaned = self.gdrive_reader.cleanup_cache()

            # 古いエラーレコードのクリーンアップ
            if self._error_handler:
                self.error_handler.cleanup_old_errors()

            self.logger.info(f"✅ クリーンアップ完了 - 一時ファイル{deleted_count}件削除")

        except Exception as e:
            self.logger.warning(f"クリーンアップエラー: {e}")

    async def _record_metrics(self, result: WorkflowResult) -> None:
        """メトリクス記録"""
        try:
            metrics_data = {
                "execution_id": result.episode_id,
                "timestamp": datetime.now().isoformat(),
                "success": result.success,
                "processing_time": result.processing_time,
                "articles_processed": result.articles_processed,
                "file_size_mb": result.file_size_mb,
                "step_times": self.metrics["processing_times"],
                "errors": result.errors,
                "warnings": result.warnings,
                "config": {
                    "max_articles": self.config.max_articles,
                    "target_script_length": self.config.target_script_length,
                    "audio_bitrate": self.config.audio_bitrate,
                },
            }

            # メトリクスファイルに記録
            metrics_file = self.output_dir / "workflow_metrics.jsonl"
            with open(metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(metrics_data, ensure_ascii=False) + "\n")

            self.logger.info("📊 メトリクス記録完了")

        except Exception as e:
            self.logger.warning(f"メトリクス記録エラー: {e}")

    def get_progress_info(self) -> Dict[str, Any]:
        """現在の進行状況を取得"""
        return {
            "current_step": self.progress.current_step,
            "progress_percentage": self.progress.progress_percentage,
            "completed_steps": self.progress.completed_steps,
            "total_steps": self.progress.total_steps,
            "elapsed_time": self.progress.elapsed_time,
            "estimated_remaining_time": self.progress.estimated_remaining_time,
            "processing_times": self.metrics["processing_times"],
        }

    def get_component_status(self) -> Dict[str, Any]:
        """コンポーネントの状態を取得"""
        return {
            "gdrive_reader": {
                "initialized": self._gdrive_reader is not None,
                "info": self._gdrive_reader.get_processing_info() if self._gdrive_reader else None,
            },
            "script_generator": {
                "initialized": self._script_generator is not None,
                "model": self.config.gemini_model,
            },
            "tts_engine": {
                "initialized": self._tts_engine is not None,
                "config": self._tts_engine.get_voice_config() if self._tts_engine else None,
            },
            "audio_processor": {
                "initialized": self._audio_processor is not None,
                "info": (
                    self._audio_processor.get_processing_info() if self._audio_processor else None
                ),
            },
            "publisher": {
                "initialized": self._publisher is not None,
                "stats": self._publisher.get_stats() if self._publisher else None,
            },
            "error_handler": {
                "initialized": self._error_handler is not None,
                "stats": (
                    self._error_handler.get_error_statistics() if self._error_handler else None
                ),
            },
        }


# テストとデモ用のヘルパー関数
async def demo_workflow_execution():
    """デモワークフロー実行"""
    # 設定例
    config = WorkflowConfig(
        google_document_id="your_document_id_here",
        gemini_api_key="your_gemini_api_key",
        github_repo_url="https://github.com/username/repo.git",
        github_pages_base_url="https://username.github.io/repo",
        debug_mode=True,
    )

    # ワークフロー実行
    workflow = IndependentPodcastWorkflow(config)

    try:
        result = await workflow.execute_workflow()

        print(f"ワークフロー実行結果:")
        print(f"  成功: {result.success}")
        print(f"  エピソードID: {result.episode_id}")
        print(f"  処理時間: {result.processing_time:.2f}秒")
        print(f"  音声URL: {result.audio_url}")
        print(f"  記事処理数: {result.articles_processed}")
        print(f"  ファイルサイズ: {result.file_size_mb:.1f}MB")

        if result.errors:
            print(f"  エラー: {result.errors}")

        return result

    except Exception as e:
        print(f"ワークフロー実行エラー: {e}")
        return None


if __name__ == "__main__":
    import asyncio

    # デモ実行
    asyncio.run(demo_workflow_execution())
