# -*- coding: utf-8 -*-

"""
Professional Dialogue Script Generator
プロフェッショナル版対話台本生成システム
Gemini 2.5 Pro使用による高品質10分完全版台本生成
"""

import os
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import google.generativeai as genai
from dataclasses import dataclass

# ArticleScore は辞書形式に変更されたためインポート不要
from src.podcast.prompts.prompt_manager import PromptManager


@dataclass
class ScriptQuality:
    """台本品質評価結果"""

    char_count: int
    estimated_duration_minutes: float
    structure_score: float
    readability_score: float
    professional_score: float
    overall_score: float
    issues: List[str]


class ProfessionalDialogueScriptGenerator:
    """プロフェッショナル版対話台本生成クラス"""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-pro"):
        """
        初期化

        Args:
            api_key: Gemini APIキー
            model_name: 使用モデル名
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name

        # Gemini設定
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

        # プロンプト管理システム初期化
        self.prompt_manager = PromptManager()

        # 【改善】品質基準設定（10分以上保証・途中切れ防止）
        # 10分 = 約2700文字、安全マージンで3000文字を下限に設定
        # 上限は12000文字に拡張（約45分相当、途中切れを確実に防止）
        self.target_char_count = (3000, 12000)  # 下限3000文字、上限12000文字
        self.target_duration_minutes = (10.0, 45.0)  # 10分から45分の範囲

        self.logger.info(f"Gemini {model_name} 初期化完了（文字数範囲: {self.target_char_count[0]}-{self.target_char_count[1]}文字、時間範囲: {self.target_duration_minutes[0]}-{self.target_duration_minutes[1]}分）")

    def generate_professional_script(
        self, articles: List[Dict[str, Any]], target_duration: float = 10.0, prompt_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        プロフェッショナル版台本生成

        Args:
            articles: 選択済み記事リスト
            target_duration: 目標配信時間（分）
            prompt_pattern: プロンプトパターン（None の場合は環境変数から取得）

        Returns:
            生成結果辞書
        """
        try:
            # プロンプトパターン決定
            if prompt_pattern is None:
                prompt_pattern = self.prompt_manager.get_environment_prompt_pattern()
            
            self.logger.info(
                f"プロフェッショナル台本生成開始 - 記事数: {len(articles)}, 目標時間: {target_duration}分, "
                f"プロンプトパターン: {prompt_pattern}"
            )

            # 記事情報準備
            article_summaries = self._prepare_article_summaries(articles)

            # プロンプト生成（プロンプト管理システム使用）
            prompt = self._create_dynamic_prompt(article_summaries, target_duration, prompt_pattern)

            # 生成設定取得（パターン別）
            generation_config = self.prompt_manager.get_generation_config(prompt_pattern)

            # Gemini 2.5 Pro で台本生成
            self.logger.info(f"Gemini 2.5 Pro による高品質台本生成中... (パターン: {prompt_pattern})")
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(**generation_config),
            )

            if not response.text:
                raise ValueError("Geminiからの応答が空です")

            raw_script = response.text.strip()
            self.logger.info(f"Gemini回答受信完了 - 文字数: {len(raw_script)}")
            
            # Gemini回答のサニタイゼーション（説明文除去）
            sanitized_script = self._sanitize_gemini_response(raw_script)
            self.logger.info(f"台本サニタイゼーション完了 - {len(raw_script)} → {len(sanitized_script)}文字")

            # エンディング完全性チェック
            if not self._validate_script_completeness(sanitized_script):
                self.logger.warning("台本が不完全です - エンディングが検出されません")
                # 不完全な場合の再生成またはエンディング補完処理
                sanitized_script = self._ensure_complete_ending(sanitized_script)

            # 品質評価・調整
            quality_result = self._evaluate_script_quality(sanitized_script)
            adjusted_script = self._adjust_script_quality(sanitized_script, quality_result)

            # 最終品質確認
            final_quality = self._evaluate_script_quality(adjusted_script)
            
            # 台本構造・不適切文言の検証
            structure_validation = self._validate_script_structure(adjusted_script)
            inappropriate_text_check = self._detect_inappropriate_content(adjusted_script)

            result = {
                "script": adjusted_script,
                "char_count": len(adjusted_script),
                "estimated_duration": final_quality.estimated_duration_minutes,
                "quality_score": final_quality.overall_score,
                "quality_details": {
                    "char_count": final_quality.char_count,
                    "estimated_duration_minutes": final_quality.estimated_duration_minutes,
                    "structure_score": final_quality.structure_score,
                    "readability_score": final_quality.readability_score,
                    "professional_score": final_quality.professional_score,
                    "overall_score": final_quality.overall_score,
                    "issues": final_quality.issues
                },
                "articles_used": len(articles),
                "generation_model": self.model_name,
                "prompt_pattern": prompt_pattern,
                "structure_validation": structure_validation,
                "inappropriate_content": inappropriate_text_check,
                "generation_config": generation_config,
                "generated_at": datetime.now().isoformat(),
            }

            # プロンプト管理システムに結果ログ
            self.prompt_manager.log_generation_result(prompt_pattern, result)

            self.logger.info(
                f"台本生成成功 - 文字数: {result['char_count']}, "
                f"推定時間: {result['estimated_duration']:.1f}分, "
                f"品質スコア: {result['quality_score']:.2f}, "
                f"パターン: {prompt_pattern}"
            )

            return result

        except Exception as e:
            self.logger.error(f"台本生成エラー: {e}", exc_info=True)
            raise

    def _prepare_article_summaries(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """記事情報準備（セッションセーフ版・修正版）"""
        summaries = []

        for i, article_score in enumerate(articles, 1):
            # ArticleScoreオブジェクトの場合と辞書の場合に対応
            if hasattr(article_score, 'article'):
                # ArticleScoreオブジェクトの場合（dataclass）
                article_data = article_score.article
                analysis_data = article_score.analysis
                score = article_score.score
            else:
                # 辞書形式の場合（従来方式）
                article_data = article_score['article']
                analysis_data = article_score['analysis']
                score = article_score['score']

            # 分析データから情報を抽出（属性アクセスと辞書アクセス両対応）
            if hasattr(analysis_data, 'category'):
                category = analysis_data.category or "その他"
                region = analysis_data.region or "other"
                summary = analysis_data.summary
                sentiment_score = analysis_data.sentiment_score
            else:
                category = analysis_data.get('category') or "その他"
                region = analysis_data.get('region') or "other"
                summary = analysis_data.get('summary')
                sentiment_score = analysis_data.get('sentiment_score')

            # 記事データから情報を抽出（属性アクセスと辞書アクセス両対応）
            if hasattr(article_data, 'title'):
                title = article_data.title
                source = article_data.source
                published_at = (
                    article_data.published_at.strftime("%Y年%m月%d日")
                    if article_data.published_at
                    else "不明"
                )
            else:
                title = article_data['title']
                source = article_data['source']
                published_at = (
                    article_data['published_at'].strftime("%Y年%m月%d日")
                    if article_data['published_at']
                    else "不明"
                )

            summaries.append(
                {
                    "index": i,
                    "title": title,
                    "summary": summary,
                    "sentiment_score": sentiment_score,
                    "category": category,
                    "region": region,
                    "importance_score": score,
                    "published_at": published_at,
                    "source": source,
                }
            )

        return summaries

    def _create_dynamic_prompt(
        self, article_summaries: List[Dict[str, Any]], target_duration: float, prompt_pattern: str
    ) -> str:
        """
        動的プロンプト生成（プロンプト管理システム使用、統合要約活用）
        
        Args:
            article_summaries: 記事サマリーリスト
            target_duration: 目標時間（分）
            prompt_pattern: プロンプトパターンID
            
        Returns:
            str: 生成されたプロンプト
        """
        try:
            target_chars = int(target_duration * 280)  # 1分あたり約280文字（拡張版で情報密度向上）

            # 統合要約コンテキストを取得
            integrated_context = self._get_integrated_summary_context()

            # 記事データをテキスト形式に変換
            articles_text = ""
            for summary in article_summaries:
                articles_text += f"""
【記事{summary['index']}】{summary['title']}
- 要約: {summary['summary']}
- カテゴリ: {summary['category']}
- 地域: {summary['region']}
- 重要度: {summary['importance_score']:.2f}
- 配信日: {summary['published_at']}
- 情報源: {summary['source']}
"""

            # プロンプトテンプレート変数
            template_vars = {
                "target_duration": target_duration,
                "target_chars": target_chars,
                "target_chars_min": target_chars - 100,
                "target_chars_max": target_chars + 100,
                "main_content_chars": target_chars - 400,
                "main_content_chars_min": target_chars - 500,
                "main_content_chars_max": target_chars - 300,
                "articles_data": articles_text,
                "integrated_context": integrated_context,  # 統合要約コンテキスト追加
                "generation_date": datetime.now().strftime('%Y年%m月%d日・%A'),
                "episode_number": self._generate_episode_number(),
            }

            # プロンプト管理システムからテンプレートを読み込み
            prompt = self.prompt_manager.load_prompt_template(prompt_pattern, **template_vars)
            
            context_info = "統合要約あり" if integrated_context else "統合要約なし"
            self.logger.info(f"動的プロンプト生成完了: {prompt_pattern} ({len(prompt)}文字, {context_info})")
            return prompt
            
        except Exception as e:
            self.logger.error(f"動的プロンプト生成エラー: {e}")
            # エラーの根本原因を隠蔽しないため、例外を再発生
            raise e

    def _generate_episode_number(self) -> int:
        """エピソード番号生成"""
        # 開始日からの日数でエピソード番号を計算
        start_date = datetime(2024, 1, 1)
        current_date = datetime.now()
        days_since_start = (current_date - start_date).days
        return days_since_start + 1

    def _get_integrated_summary_context(self) -> str:
        """
        統合要約から全体文脈を取得（データベース・Googleドキュメント対応）
        
        Returns:
            統合要約に基づく市場概況テキスト
        """
        try:
            import os
            
            # データソースの判定
            data_source = os.getenv("PODCAST_DATA_SOURCE", "database")
            
            if data_source == "database":
                return self._get_database_integrated_summary()
            elif data_source == "google_document":
                return self._get_google_document_integrated_summary()
            else:
                self.logger.warning(f"未知のデータソース: {data_source}")
                return ""
                
        except Exception as e:
            self.logger.warning(f"統合要約取得エラー: {e}")
            return ""
            
    def _get_database_integrated_summary(self) -> str:
        """データベースから統合要約を取得（エラーハンドリング強化版）"""
        try:
            # DatabaseManagerの取得を試行
            db_manager = None
            try:
                from src.database.database_manager import DatabaseManager
                from src.database.models import IntegratedSummary
                
                # 既存のDatabaseManagerインスタンスがあれば再利用
                import os
                if hasattr(self, '_db_manager_ref') and self._db_manager_ref:
                    db_manager = self._db_manager_ref
                else:
                    # 新しいインスタンスを作成
                    try:
                        from config.base import DatabaseConfig
                        db_config = DatabaseConfig(
                            url=os.getenv("DATABASE_URL", "sqlite:///market_news.db"),
                            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true"
                        )
                        db_manager = DatabaseManager(db_config)
                    except ImportError:
                        # フォールバック: 簡易設定
                        class SimpleDatabaseConfig:
                            def __init__(self):
                                self.url = os.getenv("DATABASE_URL", "sqlite:///market_news.db")
                                self.echo = False
                        db_manager = DatabaseManager(SimpleDatabaseConfig())
                
            except Exception as e:
                self.logger.warning(f"データベース接続失敗、統合要約をスキップ: {e}")
                return ""
                
            if not db_manager:
                return ""
                
            with db_manager.get_session() as session:
                try:
                    # 最新の統合要約を取得（当日分）
                    today = datetime.now().date()
                    
                    # グローバル統合要約を優先取得
                    global_summary = (
                        session.query(IntegratedSummary)
                        .filter(
                            IntegratedSummary.summary_type == "global",
                            IntegratedSummary.created_at >= today
                        )
                        .order_by(IntegratedSummary.created_at.desc())
                        .first()
                    )
                    
                    # 地域別要約も取得（より多くの記事参照のため拡張）
                    regional_summaries = (
                        session.query(IntegratedSummary)
                        .filter(
                            IntegratedSummary.summary_type == "regional",
                            IntegratedSummary.created_at >= today
                        )
                        .order_by(IntegratedSummary.created_at.desc())
                        .limit(8)  # 5 → 8に増加
                        .all()
                    )
                    
                    # 【改善】セクター別要約も取得
                    sector_summaries = (
                        session.query(IntegratedSummary)
                        .filter(
                            IntegratedSummary.summary_type == "sector",
                            IntegratedSummary.created_at >= today
                        )
                        .order_by(IntegratedSummary.created_at.desc())
                        .limit(5)
                        .all()
                    )
                    
                    context_parts = []
                    
                    # データを即座に文字列として取得（セッション切れを回避）
                    # 各オブジェクトの属性をセッション内で即座に文字列化
                    if global_summary and global_summary.summary_text:
                        context_parts.append("【グローバル市場概況】")
                        # セッション内で即座に文字列に変換
                        global_summary_text = str(global_summary.summary_text)
                        context_parts.append(global_summary_text)
                        
                    if regional_summaries:
                        context_parts.append("\n【地域別市場動向】")
                        for regional in regional_summaries:
                            if regional.summary_text:
                                # セッション内で即座に文字列に変換
                                region_name = str(regional.region) if regional.region else "その他地域"
                                summary_text = str(regional.summary_text)
                                context_parts.append(f"◆ {region_name}: {summary_text}")
                    
                    # 【改善】セクター別情報の追加
                    if sector_summaries:
                        context_parts.append("\n【セクター別動向】")
                        for sector in sector_summaries:
                            if sector.summary_text:
                                sector_name = str(sector.region) if sector.region else "その他セクター"
                                summary_text = str(sector.summary_text)
                                context_parts.append(f"◇ {sector_name}: {summary_text}")
                                
                    # 統合文脈テキストを生成
                    if context_parts:
                        context_text = "\n".join(context_parts)
                        # 【改善】統計情報をログに追加
                        total_summaries = len(regional_summaries) + len(sector_summaries) + (1 if global_summary else 0)
                        self.logger.info(f"データベース統合要約コンテキスト取得成功 - 総要約数: {total_summaries}")
                        self.logger.info(f"  - グローバル: {'1件' if global_summary else '0件'}")
                        self.logger.info(f"  - 地域別: {len(regional_summaries)}件") 
                        self.logger.info(f"  - セクター別: {len(sector_summaries)}件")
                        return context_text
                    else:
                        self.logger.info("データベース統合要約が見つからないため、コンテキストなしで実行")
                        return ""
                        
                except Exception as query_error:
                    self.logger.warning(f"統合要約クエリエラー: {query_error}")
                    return ""
                    
        except Exception as e:
            self.logger.warning(f"データベース統合要約取得エラー: {e}")
            return ""
            
    def _get_google_document_integrated_summary(self) -> str:
        """Googleドキュメントから統合要約を取得"""
        try:
            import os
            from src.podcast.data_fetcher.google_document_data_fetcher import GoogleDocumentDataFetcher
            
            # AI要約ドキュメントIDを取得
            summary_doc_id = (
                os.getenv("GOOGLE_DAILY_SUMMARY_DOC_ID") or 
                os.getenv("GOOGLE_AI_SUMMARY_DOC_ID") or
                os.getenv("GOOGLE_DOCUMENT_ID")
            )
            
            if not summary_doc_id:
                self.logger.warning("GoogleドキュメントAI要約のドキュメントIDが設定されていません")
                return ""
                
            # GoogleドキュメントからAI要約コンテキストを取得
            fetcher = GoogleDocumentDataFetcher(summary_doc_id)
            context_text = fetcher.fetch_integrated_summary_context()
            
            if context_text:
                self.logger.info("GoogleドキュメントAI要約コンテキスト取得成功")
                return context_text
            else:
                self.logger.warning("GoogleドキュメントからAI要約コンテキストを取得できませんでした")
                return ""
                
        except Exception as e:
            self.logger.warning(f"GoogleドキュメントAI要約取得エラー: {e}")
            return ""

    def _create_professional_prompt(
        self, article_summaries: List[Dict[str, Any]], target_duration: float
    ) -> str:
        """プロフェッショナル版プロンプト作成（改善版）"""
        # 【改善】より安全な文字数設定（途中切れ防止）
        target_chars = int(target_duration * 270)  # 1分あたり約270文字
        min_chars = max(3000, target_chars)  # 最低3000文字保証
        max_chars = min_chars + 2000  # 余裕をもった上限設定

        articles_text = ""
        for summary in article_summaries:
            articles_text += f"""
【記事{summary['index']}】{summary['title']}
- 要約: {summary['summary']}
- カテゴリ: {summary['category']}
- 地域: {summary['region']}
- 重要度: {summary['importance_score']:.2f}
- 配信日: {summary['published_at']}
- 情報源: {summary['source']}
"""

        prompt = f"""あなたは15年以上の経験を持つ金融市場専門のポッドキャストホストです。
機関投資家・経営者向けの高品質な市場分析番組を担当し、複雑な金融情報を専門性を保ちながら分かりやすく伝えるプロフェッショナルです。

## 台本作成指示（改善版）

### 📊 番組仕様
- **配信時間**: {target_duration}分以上の完全版（最低{min_chars}文字、推奨{max_chars}文字程度）
- **対象者**: 投資家・経営者・金融専門家
- **品質レベル**: プロフェッショナル級（Bloomberg, Reuters水準）
- **配信形式**: 音声ポッドキャスト（TTS合成対応）

### 🎯 内容構成（前日振り返り重視版）
**【重要】以下の配分で内容を構成してください：**

#### **1. オープニング** (300文字程度)
- 日付・曜日の確認（{datetime.now().strftime('%Y年%m月%d日・%A')}）
- 前日市場のキーポイント予告
- 聞き手への親しみやすい語りかけ

#### **2. 前日市場振り返り（メインコンテンツ）** ({int(max_chars * 0.7)}文字程度・70%配分)
**重要記事の詳細分析**:
- **Tier 1（最重要記事）**: 3-4記事×400文字（詳細分析・市場影響・背景解説）
- **Tier 2（重要記事）**: 4-5記事×200文字（投資家視点・セクター分析）
- **Tier 3（補完記事）**: 5-7記事×100文字（簡潔・要点整理・相互関連）

**前日総括分析**: 400文字
- 前日の市場全体動向と相互関連性
- 投資家が注意すべきリスク要因と対応策
- 重要な変化点と継続監視項目

#### **3. 今後の予定・見通し（サブコンテンツ）** ({int(max_chars * 0.3)}文字程度・30%配分)
- 本日以降の注目事項（経済指標・企業発表・政策動向）
- 短期的な市場見通しと注意点
- 投資戦略上のポイント

#### **4. クロージング** (200文字程度)
- 前日のキーポイント整理
- 本日の注目事項
- 感謝の言葉・次回予告

### 🎨 表現要件（完全性重視）

**必須要素**:
- **話し言葉**: 「〜ですね」「〜ますから」「〜でしょう」等の自然な表現
- **専門用語解説**: 「FRB（米連邦準備制度理事会）」「FOMC（連邦公開市場委員会）」等
- **数値読み上げ**: 「1兆2,500億円」→「1兆2500億円」（句読点なし）
- **適切な間**: 句読点による自然な区切り（1文30文字以内推奨）

**避ける要素**:
- 投資推奨・断定的予測
- 30文字超の長文
- 感情的すぎる表現
- 複雑な専門用語の連続

### 📈 分析対象記事（拡張版：15記事対応）
{articles_text}

### 🎯 品質基準（完全性優先）
- **文字数**: {min_chars}文字以上（途中切れ絶対防止）
- **構成**: 前日振り返り70% + 今後予定30%の配分
- **完全性**: 必ず完結した台本を最後まで生成すること
- **読みやすさ**: TTS音声での自然な発話
- **専門性**: 投資判断に資する深い洞察
- **実践性**: 具体的なリスク評価・市場見通し
- **情報密度**: 15記事を効果的に紹介、漏れなくカバー

### ⚠️ 【重要】完全性指示
- **絶対に途中で止めないこと**
- **台本は必ず自然な終了まで生成すること**
- **文字数制限よりも完全性を優先すること**
- **エンディングまで確実に含めること**

---

**上記要件に従い、前日振り返り重視の{target_duration}分間ポッドキャスト台本を完全版で作成してください。**
台本のみを出力し、他の説明文は不要です。"""

        return prompt

    def _evaluate_script_quality(self, script: str) -> ScriptQuality:
        """台本品質評価"""
        char_count = len(script)
        estimated_duration = char_count / 270.0  # 1分あたり270文字想定

        issues = []

        # 文字数評価
        char_min, char_max = self.target_char_count
        if char_count < char_min:
            issues.append(f"文字数不足: {char_count} < {char_min}")
        elif char_count > char_max:
            issues.append(f"文字数超過: {char_count} > {char_max}")

        char_score = 1.0
        if char_count < char_min:
            char_score = char_count / char_min
        elif char_count > char_max:
            char_score = char_max / char_count

        # 時間評価
        duration_min, duration_max = self.target_duration_minutes
        duration_score = 1.0
        if estimated_duration < duration_min:
            duration_score = estimated_duration / duration_min
        elif estimated_duration > duration_max:
            duration_score = duration_max / estimated_duration

        # 構造評価（オープニング・メイン・クロージングの存在）
        structure_indicators = ["おはようございます", "こんにちは", "本日", "今日"]
        closing_indicators = ["以上", "ありがとう", "次回", "また"]

        has_opening = any(indicator in script[:300] for indicator in structure_indicators)
        has_closing = any(indicator in script[-300:] for indicator in closing_indicators)

        structure_score = (int(has_opening) + int(has_closing)) / 2.0

        # 読みやすさ評価（適切な句読点・文長）
        sentences = script.split("。")
        long_sentences = [s for s in sentences if len(s) > 40]
        readability_score = max(0.0, 1.0 - len(long_sentences) / len(sentences))

        # プロフェッショナル度評価（専門用語・分析深度）
        professional_terms = ["市場", "投資", "企業", "業績", "経済", "金融", "政策", "分析"]
        professional_count = sum(script.count(term) for term in professional_terms)
        professional_score = min(1.0, professional_count / 20.0)  # 20回以上で満点

        # 総合評価
        overall_score = (
            char_score * 0.3
            + duration_score * 0.2
            + structure_score * 0.2
            + readability_score * 0.15
            + professional_score * 0.15
        )

        return ScriptQuality(
            char_count=char_count,
            estimated_duration_minutes=estimated_duration,
            structure_score=structure_score,
            readability_score=readability_score,
            professional_score=professional_score,
            overall_score=overall_score,
            issues=issues,
        )

    def _adjust_script_quality(self, script: str, quality: ScriptQuality) -> str:
        """台本品質調整"""
        # スクリプト専用モードの場合は調整をスキップ
        script_only_mode = os.getenv('PODCAST_SCRIPT_ONLY_MODE', 'false').lower() == 'true'
        if script_only_mode:
            self.logger.info("🔍 スクリプト専用モード: 文字数調整をスキップ - 完全な台本を保持")
            return script

        # 制限緩和: 品質に関係なく元の台本をそのまま使用（最後まで話すことを優先）
        self.logger.info(f"🎙️ 制限緩和モード: 台本品質調整をスキップ - 完全な台本を保持（現品質: {quality.overall_score:.2f}）")
        return script

        # 以下の文字数調整処理は無効化
        char_min, char_max = self.target_char_count
        if False:  # 文字数調整を完全に無効化
            try:
                adjustment_prompt = f"""以下の台本の文字数を調整してください。

目標文字数: {char_min}-{char_max}文字
現在文字数: {quality.char_count}文字

調整方針:
- 文字数不足の場合: 市場分析を深掘り、具体例や背景情報を追加
- 文字数超過の場合: 重複表現を削除、簡潔な表現に変更
- 品質・専門性は維持

台本:
{script}

調整後の台本のみを出力してください。"""

                response = self.model.generate_content(
                    adjustment_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2, max_output_tokens=4096
                    ),
                )

                if response.text:
                    adjusted = response.text.strip()
                    self.logger.info(f"文字数調整完了: {len(script)} → {len(adjusted)}")
                    return adjusted

            except Exception as e:
                self.logger.error(f"台本調整エラー: {e}")

        return script

    def _validate_script_completeness(self, script: str) -> bool:
        """台本完全性検証"""
        # エンディング必須文言の存在確認
        ending_phrases = [
            "明日もよろしくお願いします",
            "ポッドキャストでした",
            "以上",
            "ありがとうございました"
        ]
        
        # スクリプトの最後200文字を確認
        script_ending = script[-200:].lower()
        
        # 必須エンディング文言のいずれかが含まれているか確認
        has_ending_phrase = any(phrase.lower() in script_ending for phrase in ending_phrases)
        
        # 文字数が極端に不足していないか確認
        char_min, _ = self.target_char_count
        has_sufficient_length = len(script) >= char_min * 0.8  # 80%以上の長さ
        
        completeness = has_ending_phrase and has_sufficient_length
        
        if not completeness:
            self.logger.warning(f"完全性チェック失敗 - エンディング検出: {has_ending_phrase}, 十分な長さ: {has_sufficient_length}")
        
        return completeness

    def _ensure_complete_ending(self, incomplete_script: str) -> str:
        """不完全な台本にエンディングを補完"""
        try:
            # 台本が途中で切れている場合のエンディング補完
            completion_prompt = f"""以下の台本は途中で終わっているようです。適切なエンディングを追加して完成させてください。

エンディング要件:
- 本日のキーポイント整理（50文字程度）
- 明日以降の注目事項（80文字程度）  
- 番組終了宣言「以上、本日の市場ニュースポッドキャストでした。明日もよろしくお願いします。」（70文字）

現在の台本:
{incomplete_script}

完成した台本全体を出力してください。"""

            response = self.model.generate_content(
                completion_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2, max_output_tokens=4096
                ),
            )

            if response.text:
                completed_script = response.text.strip()
                self.logger.info(f"エンディング補完完了: {len(incomplete_script)} → {len(completed_script)}文字")
                return completed_script

        except Exception as e:
            self.logger.error(f"エンディング補完エラー: {e}")

        # 補完に失敗した場合、エラーの根本原因を明確化
        self.logger.error("エンディング補完に失敗しました - 台本が不完全な状態です")
        raise Exception("台本のエンディング補完が失敗しました。Gemini APIの応答を確認してください。")
    
    def _sanitize_gemini_response(self, raw_response: str) -> str:
        """
        Geminiの回答から台本以外の説明文を除去（強化版）
        
        Args:
            raw_response: Geminiからの生の回答
            
        Returns:
            str: サニタイゼーション済みの台本
        """
        import re
        
        script = raw_response.strip()
        original_length = len(script)
        
        # Geminiがよく使用する説明文パターン（強化版）
        explanation_patterns = [
            # 既存パターン
            r'^.*?以下が.*?台本.*?です.*?\n',
            r'^.*?台本を.*?作成.*?しました.*?\n',
            r'^.*?ポッドキャストの台本.*?\n',
            r'^.*?市場ニュース.*?台本.*?\n',
            r'^.*?以下の内容で.*?\n',
            r'^.*?こちらが.*?台本.*?\n',
            r'^.*?では.*?台本.*?ご提示.*?\n',
            r'^.*?\*\*台本\*\*.*?\n',
            r'^.*?## 台本.*?\n',
            r'^.*?# 台本.*?\n',
            r'^```.*?\n',  # コードブロック記号
            r'^---.*?\n',  # 区切り線
            
            # 新しい応答パターン（今回検出された問題）
            r'^.*?はい.*?承知.*?いたしました.*?\n',
            r'^.*?承知.*?いたしました.*?\n',
            r'^.*?分かりました.*?\n',
            r'^.*?了解.*?いたしました.*?\n',
            
            # 【改善】追加の応答パターン（より積極的除去）
            r'^.*?かしこまりました.*?\n',
            r'^.*?承諾.*?いたします.*?\n',
            r'^.*?対応.*?いたします.*?\n',
            r'^.*?実行.*?いたします.*?\n',
            r'^.*?作成.*?いたします.*?\n',
            r'^.*?生成.*?いたします.*?\n',
            r'^.*?お答え.*?します.*?\n',
            r'^.*?回答.*?します.*?\n',
            r'^.*?提供.*?します.*?\n',
            r'^.*?お作り.*?します.*?\n',
            r'^.*?ご用意.*?します.*?\n',
            r'^.*?準備.*?します.*?\n',
            
            # 【新規追加】より広範囲な問題応答パターン
            r'^.*?(はい|そうですね).*?(承知|理解|了解).*?\n',
            r'^.*?(ご要望|ご依頼|指示).*?(承り|受け|対応).*?\n',
            r'^.*?(台本|スクリプト).*?(作成|生成|用意).*?します.*?\n',
            r'^.*?要求.*?(満たす|応える).*?\n',
            r'^.*?条件.*?(満たす|考慮).*?\n',
            
            # 作業説明パターン（拡張）
            r'^.*?現在の台本.*?適切.*?エンディング.*?\n',
            r'^.*?完成させた台本.*?以下.*?示します.*?\n',
            r'^.*?台本.*?完成.*?させ.*?\n',
            r'^.*?適切なエンディングを追加.*?\n',
            r'^.*?以下の通り.*?台本.*?\n',
            r'^.*?ご要望.*?台本.*?\n',
            r'^.*?指示.*?従い.*?\n',
            
            # 【改善】英語での応答パターン
            r'^.*?Here is.*?script.*?\n',
            r'^.*?I will.*?create.*?\n',
            r'^.*?I\'ll.*?generate.*?\n',
            r'^.*?The script.*?follows.*?\n',
            r'^.*?Below is.*?script.*?\n',
            
            # マークダウン構造パターン（拡張）
            r'^.*?### 完成した台本.*?\n',
            r'^.*?##.*?完成.*?台本.*?\n',
            r'^.*?### 台本.*?\n',
            r'^.*?\*\*\*完成.*?\*\*\*.*?\n',
            r'^.*?\[台本\].*?\n',
            r'^.*?「台本」.*?\n',
            
            # 【改善】メタ情報パターン（積極的除去）
            r'^.*?文字数.*?約.*?\n',
            r'^.*?\d+文字.*?台本.*?\n',
            r'^.*?\d+分.*?想定.*?\n',
            r'^.*?約\d+分.*?\n',
            r'^.*?\d+:\d+.*?分.*?\n',
        ]
        
        # 冒頭の説明文除去（行単位）
        before_length = len(script)
        for pattern in explanation_patterns:
            script = re.sub(pattern, '', script, flags=re.IGNORECASE | re.MULTILINE)
        
        # 【新機能】より積極的なブロック除去（段落レベル）
        # 最初の段落が説明文の可能性が高い場合の除去
        paragraphs = script.split('\n\n')
        if len(paragraphs) > 1:
            first_paragraph = paragraphs[0]
            # 最初の段落が短く、説明的な文言を含む場合は除去
            if len(first_paragraph) < 200 and any(word in first_paragraph for word in [
                '台本', '作成', '生成', '提供', '以下', 'こちら', 'では', '承知', '了解', '対応'
            ]):
                script = '\n\n'.join(paragraphs[1:])
                self.logger.info(f"🎯 最初の説明段落を除去: '{first_paragraph[:50]}...'")
        
        # 【改善】より積極的なブロック除去（日付から台本開始位置を特定）
        date_match = re.search(r'\d{4}年\d+月\d+日', script)
        if date_match:
            # 日付より前の部分を全て除去
            script = script[date_match.start():]
            self.logger.info(f"🎯 日付パターンから台本開始位置を特定: {date_match.start()}文字目から")
        
        # 【改善】冒頭の挨拶パターンをチェック
        greeting_patterns = [
            r'(みなさん|皆さん|皆様).*?(おはよう|こんにちは|こんばんは)',
            r'(おはよう|こんにちは|こんばんは).*?(ございます|ます)',
            r'.*?(ポッドキャスト|番組).*?(時間|開始)',
        ]
        
        has_proper_greeting = False
        for pattern in greeting_patterns:
            if re.search(pattern, script[:200], re.IGNORECASE):
                has_proper_greeting = True
                break
        
        if not has_proper_greeting and date_match:
            # 日付の後で適切な挨拶を探す
            post_date_text = script[:500]  # 日付後500文字を確認
            greeting_start = re.search(r'(みなさん|皆さん|おはよう|こんにちは)', post_date_text, re.IGNORECASE)
            if greeting_start:
                script = script[greeting_start.start():]
                self.logger.info(f"🎯 挨拶パターンから台本開始位置を修正")
        
        # 【新機能】より確実な台本開始位置の検出
        # 典型的なポッドキャスト開始フレーズを探す
        podcast_start_patterns = [
            r'(おはよう|こんにちは|こんばんは).*?(ございます|ます)',
            r'\d{4}年\d+月\d+日.*?(の|、)',
            r'(本日|今日).*?(市場|マーケット|ニュース)',
            r'(皆さん|みなさん).*?(お疲れ|いかが)',
        ]
        
        for pattern in podcast_start_patterns:
            match = re.search(pattern, script, re.IGNORECASE)
            if match:
                # マッチした位置より前に不要な文言がある場合は除去
                pre_match = script[:match.start()].strip()
                if len(pre_match) < 100 and any(word in pre_match for word in [
                    '台本', '作成', '以下', 'こちら', '承知', '了解'
                ]):
                    script = script[match.start():]
                    self.logger.info(f"🎯 ポッドキャスト開始パターンから調整: '{pre_match[:30]}...'を除去")
                break
        
        # 末尾の説明文パターン（拡張）
        ending_patterns = [
            r'\n.*?以上が.*?台本.*?です.*?$',
            r'\n.*?台本の.*?完成.*?$',
            r'\n```.*?$',  # 末尾コードブロック
            r'\n---.*?$',  # 末尾区切り線
            r'\n.*?以上.*?内容.*?$',
            r'\n.*?この.*?台本.*?$',
            # 【改善】追加の末尾パターン
            r'\n.*?台本.*?終了.*?$',
            r'\n.*?放送.*?終了.*?$',
            r'\n.*?\[END\].*?$',
            r'\n.*?\[終了\].*?$',
            r'\n.*?以上で.*?$',
            r'\n.*?これで.*?終了.*?$',
        ]
        
        for pattern in ending_patterns:
            script = re.sub(pattern, '', script, flags=re.IGNORECASE | re.MULTILINE)
        
        # 余分な空行を整理
        script = re.sub(r'\n{3,}', '\n\n', script)
        script = script.strip()
        
        # 【改善】最終チェック：台本の開始・終了が適切か
        if script and not script.endswith(('。', '！', '？', '.')):
            # 文の途中で切れている可能性があるので警告
            self.logger.warning("⚠️ 台本が文の途中で終了している可能性があります")
        
        # サニタイゼーション結果の詳細ログ
        removed_chars = original_length - len(script)
        if removed_chars > 0:
            self.logger.info(f"🧹 Gemini説明文除去: {removed_chars}文字削除済み ({original_length} → {len(script)})")
            # 除去された内容の先頭部分をログ出力
            removed_content = raw_response[:min(100, removed_chars)]
            self.logger.info(f"🗑️ 除去内容プレビュー: '{removed_content[:50]}...'")
        else:
            self.logger.info("ℹ️ サニタイゼーション: 除去対象なし")
            
        # 台本が正しく開始されているか確認
        if not self._validate_script_start(script):
            self.logger.warning("⚠️ 台本の開始が不適切な可能性があります")
            script_start_preview = script[:100]
            self.logger.warning(f"📄 現在の開始部分: '{script_start_preview}...'")
        else:
            self.logger.info("✅ 台本開始部分は適切です")
            
        return script
    
    def _validate_script_start(self, script: str) -> bool:
        """
        台本が適切なオープニングで始まっているか検証
        
        Args:
            script: 検証する台本
            
        Returns:
            bool: 適切に開始されている場合True
        """
        script_start = script[:100].lower()
        
        # 適切なオープニングパターン
        valid_start_patterns = [
            '皆さん',
            'こんにちは',
            'おはようございます',
            'こんばんは', 
            '本日',
            '今日',
            '市場',
            r'\d+月\d+日',  # 日付
        ]
        
        # 不適切な開始パターン（Geminiの説明文残存）
        invalid_start_patterns = [
            '以下',
            '台本',
            'ポッドキャスト',
            '作成',
            'こちら',
            '内容',
        ]
        
        # 不適切パターンチェック
        for pattern in invalid_start_patterns:
            if pattern in script_start:
                return False
                
        # 適切パターンチェック  
        for pattern in valid_start_patterns:
            if re.search(pattern, script_start, re.IGNORECASE):
                return True
                
        return False
    
    def _validate_script_structure(self, script: str) -> dict:
        """
        台本の構造を検証（オープニング・メイン・クロージング）
        
        Args:
            script: 検証する台本
            
        Returns:
            dict: 構造検証結果
        """
        validation_result = {
            "valid": True,
            "issues": [],
            "sections": {
                "opening": False,
                "main_content": False,
                "closing": False
            }
        }
        
        script_lower = script.lower()
        
        # オープニング検証
        opening_indicators = ['皆さん', 'こんにちは', 'おはようございます', '本日', '今日']
        if any(indicator in script[:300] for indicator in opening_indicators):
            validation_result["sections"]["opening"] = True
        else:
            validation_result["issues"].append("オープニングが検出されません")
            validation_result["valid"] = False
        
        # メインコンテンツ検証
        main_indicators = ['市況', '株価', '為替', '指数', '銘柄', '経済', '金融']
        if any(indicator in script_lower for indicator in main_indicators):
            validation_result["sections"]["main_content"] = True
        else:
            validation_result["issues"].append("メインコンテンツが不足している可能性があります")
            validation_result["valid"] = False
        
        # クロージング検証  
        closing_indicators = ['以上', '明日も', 'よろしく', 'ありがとう']
        if any(indicator in script[-300:] for indicator in closing_indicators):
            validation_result["sections"]["closing"] = True
        else:
            validation_result["issues"].append("適切なクロージングが検出されません")
            validation_result["valid"] = False
            
        return validation_result
    
    def _detect_inappropriate_content(self, script: str) -> dict:
        """
        台本内の不適切な文言を検出（Gemini説明文の残存等）
        
        Args:
            script: 検証する台本
            
        Returns:
            dict: 不適切文言検出結果
        """
        detection_result = {
            "found": False,
            "issues": [],
            "inappropriate_phrases": []
        }
        
        # Gemini説明文パターン
        inappropriate_patterns = [
            "以下が台本",
            "台本を作成",
            "ポッドキャストの台本",
            "こちらが内容",
            "作成しました",
            "ご提示します",
            "完成しました",
            "台本です",
            "内容は以下の通り"
        ]
        
        script_lower = script.lower()
        
        for pattern in inappropriate_patterns:
            if pattern in script_lower:
                detection_result["found"] = True
                detection_result["inappropriate_phrases"].append(pattern)
                detection_result["issues"].append(f"Gemini説明文が残存: '{pattern}'")
        
        # マークダウン記号チェック
        markdown_patterns = ["```", "##", "**", "---", "- [", "* ["]
        for pattern in markdown_patterns:
            if pattern in script:
                detection_result["found"] = True
                detection_result["inappropriate_phrases"].append(pattern)
                detection_result["issues"].append(f"マークダウン記号が残存: '{pattern}'")
        
        return detection_result
