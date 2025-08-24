# -*- coding: utf-8 -*-

"""
Professional Dialogue Script Generator
プロフェッショナル版対話台本生成システム
Gemini 2.5 Pro使用による高品質10分完全版台本生成
"""

import os
import logging
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

        # 品質基準設定（拡張版）
        self.target_char_count = (4000, 4500)
        self.target_duration_minutes = (14.0, 16.0)

        self.logger.info(f"Gemini {model_name} 初期化完了（プロンプト管理システム統合済み）")

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
            self.logger.info(f"台本生成完了 - 文字数: {len(raw_script)}")

            # エンディング完全性チェック
            if not self._validate_script_completeness(raw_script):
                self.logger.warning("台本が不完全です - エンディングが検出されません")
                # 不完全な場合の再生成またはエンディング補完処理
                raw_script = self._ensure_complete_ending(raw_script)

            # 品質評価・調整
            quality_result = self._evaluate_script_quality(raw_script)
            adjusted_script = self._adjust_script_quality(raw_script, quality_result)

            # 最終品質確認
            final_quality = self._evaluate_script_quality(adjusted_script)

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
        """記事情報準備（セッションセーフ版）"""
        summaries = []

        for i, article_score in enumerate(articles, 1):
            article_data = article_score['article']
            analysis_data = article_score['analysis']

            category = analysis_data.get('category') or "その他"
            region = analysis_data.get('region') or "other"

            summaries.append(
                {
                    "index": i,
                    "title": article_data['title'],
                    "summary": analysis_data['summary'],
                    "sentiment_score": analysis_data['sentiment_score'],
                    "category": category,
                    "region": region,
                    "importance_score": article_score['score'],
                    "published_at": (
                        article_data['published_at'].strftime("%Y年%m月%d日")
                        if article_data['published_at']
                        else "不明"
                    ),
                    "source": article_data['source'],
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
            # フォールバック: 従来のプロンプト生成
            return self._create_professional_prompt(article_summaries, target_duration)

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
                    
                    # 地域別要約も取得
                    regional_summaries = (
                        session.query(IntegratedSummary)
                        .filter(
                            IntegratedSummary.summary_type == "regional",
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
                                
                    # 統合文脈テキストを生成
                    if context_parts:
                        context_text = "\n".join(context_parts)
                        self.logger.info("データベース統合要約コンテキスト取得成功")
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
        """プロフェッショナル版プロンプト作成"""
        target_chars = int(target_duration * 270)  # 1分あたり約270文字

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

## 台本作成指示

### 📊 番組仕様
- **配信時間**: {target_duration}分完全版（約{target_chars}文字）
- **対象者**: 投資家・経営者・金融専門家
- **品質レベル**: プロフェッショナル級（Bloomberg, Reuters水準）
- **配信形式**: 音声ポッドキャスト（TTS合成対応）

### 🎯 台本構成（必須構造）

#### **1. オープニング** (200文字程度)
- 日付・曜日の確認（{datetime.now().strftime('%Y年%m月%d日・%A')}）
- 今日の市場注目ポイント3点の予告
- 聞き手への親しみやすい語りかけ

#### **2. メインコンテンツ** ({target_chars-600}文字程度・拡張版)
**多層構造記事分析**:
- **Tier 1（最重要記事）**: 3記事×450文字（詳細分析・市場影響・背景解説）
- **Tier 2（重要記事）**: 5記事×250文字（投資家視点・セクター分析）
- **Tier 3（補完記事）**: 7記事×100文字（簡潔・要点整理・相互関連）

**総合市場分析**: 400文字（拡張）
- 本日の市場全体動向と相互関連性
- 投資家が注意すべきリスク要因と対応策
- 今後1週間の注目材料と投資戦略

#### **3. クロージング** (200文字程度)
- 本日のキーポイント整理
- 明日以降の注目事項
- 感謝の言葉・次回予告

### 🎨 表現要件

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

### 🎯 品質基準（拡張版）
- 文字数: {target_chars-200}〜{target_chars+200}文字（拡張レンジ）
- 構成: 重要度別多層構造（詳細・中程度・簡潔）
- 読みやすさ: TTS音声での自然な発話
- 専門性: 投資判断に資する深い洞察
- 実践性: 具体的なリスク評価・市場見通し
- 情報密度: 15記事を効果的に紹介、漏れなくカバー

---

**上記要件に従い、プロフェッショナル級の10分間ポッドキャスト台本を作成してください。**
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

        if quality.overall_score >= 0.8 and not quality.issues:
            return script

        self.logger.info(f"台本品質調整実行 - 現品質: {quality.overall_score:.2f}")

        # 文字数調整が必要な場合
        char_min, char_max = self.target_char_count
        if quality.char_count < char_min or quality.char_count > char_max:
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

        # 補完に失敗した場合、最低限のエンディングを追加
        fallback_ending = "\n\n本日の重要ポイントをまとめますと、市場は様々な要因で動いています。明日も引き続き注目してまいります。以上、本日の市場ニュースポッドキャストでした。明日もよろしくお願いします。"
        
        self.logger.warning("エンディング補完失敗 - フォールバックエンディングを追加")
        return incomplete_script + fallback_ending
