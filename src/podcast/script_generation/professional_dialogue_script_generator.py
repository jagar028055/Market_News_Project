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

from src.podcast.data_fetcher.enhanced_database_article_fetcher import ArticleScore


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
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-pro-001"):
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
        
        # 品質基準設定
        self.target_char_count = (2600, 2800)
        self.target_duration_minutes = (9.0, 11.0)
        
        self.logger.info(f"Gemini {model_name} 初期化完了")
    
    def generate_professional_script(
        self,
        articles: List[ArticleScore],
        target_duration: float = 10.0
    ) -> Dict[str, Any]:
        """
        プロフェッショナル版台本生成
        
        Args:
            articles: 選択済み記事リスト
            target_duration: 目標配信時間（分）
            
        Returns:
            生成結果辞書
        """
        try:
            self.logger.info(f"プロフェッショナル台本生成開始 - 記事数: {len(articles)}, 目標時間: {target_duration}分")
            
            # 記事情報準備
            article_summaries = self._prepare_article_summaries(articles)
            
            # プロンプト生成
            prompt = self._create_professional_prompt(article_summaries, target_duration)
            
            # Gemini 2.5 Pro で台本生成
            self.logger.info("Gemini 2.5 Pro による高品質台本生成中...")
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=4096,
                    candidate_count=1
                )
            )
            
            if not response.text:
                raise ValueError("Geminiからの応答が空です")
            
            raw_script = response.text.strip()
            self.logger.info(f"台本生成完了 - 文字数: {len(raw_script)}")
            
            # 品質評価・調整
            quality_result = self._evaluate_script_quality(raw_script)
            adjusted_script = self._adjust_script_quality(raw_script, quality_result)
            
            # 最終品質確認
            final_quality = self._evaluate_script_quality(adjusted_script)
            
            result = {
                'script': adjusted_script,
                'char_count': len(adjusted_script),
                'estimated_duration': final_quality.estimated_duration_minutes,
                'quality_score': final_quality.overall_score,
                'quality_details': final_quality,
                'articles_used': len(articles),
                'generation_model': self.model_name,
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.info(
                f"台本生成成功 - 文字数: {result['char_count']}, "
                f"推定時間: {result['estimated_duration']:.1f}分, "
                f"品質スコア: {result['quality_score']:.2f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"台本生成エラー: {e}", exc_info=True)
            raise
    
    def _prepare_article_summaries(self, articles: List[ArticleScore]) -> List[Dict[str, Any]]:
        """記事情報準備"""
        summaries = []
        
        for i, article_score in enumerate(articles, 1):
            article = article_score.article
            analysis = article_score.analysis
            
            category = getattr(analysis, 'category', None) or 'その他'
            region = getattr(analysis, 'region', None) or 'other'
            
            summaries.append({
                'index': i,
                'title': article.title,
                'summary': analysis.summary,
                'sentiment_score': analysis.sentiment_score,
                'category': category,
                'region': region,
                'importance_score': article_score.score,
                'published_at': article.published_at.strftime('%Y年%m月%d日') if article.published_at else '不明',
                'source': article.source
            })
        
        return summaries
    
    def _create_professional_prompt(
        self,
        article_summaries: List[Dict[str, Any]],
        target_duration: float
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

#### **2. メインコンテンツ** ({target_chars-400}文字程度)
**重要度順記事分析**:
- **最重要記事**: 400文字（詳細分析・市場影響・背景解説）
- **重要記事**: 350文字（投資家視点・セクター分析）
- **補完記事**: 250-300文字×4記事（簡潔・要点整理・相互関連）

**総合市場分析**: 300文字
- 本日の市場全体動向
- 投資家が注意すべきリスク要因
- 今後1週間の注目材料

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

### 📈 分析対象記事
{articles_text}

### 🎯 品質基準
- 文字数: {target_chars-100}〜{target_chars+100}文字（厳密）
- 読みやすさ: TTS音声での自然な発話
- 専門性: 投資判断に資する深い洞察
- 実践性: 具体的なリスク評価・市場見通し

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
        structure_indicators = ['おはようございます', 'こんにちは', '本日', '今日']
        closing_indicators = ['以上', 'ありがとう', '次回', 'また']
        
        has_opening = any(indicator in script[:300] for indicator in structure_indicators)
        has_closing = any(indicator in script[-300:] for indicator in closing_indicators)
        
        structure_score = (int(has_opening) + int(has_closing)) / 2.0
        
        # 読みやすさ評価（適切な句読点・文長）
        sentences = script.split('。')
        long_sentences = [s for s in sentences if len(s) > 40]
        readability_score = max(0.0, 1.0 - len(long_sentences) / len(sentences))
        
        # プロフェッショナル度評価（専門用語・分析深度）
        professional_terms = ['市場', '投資', '企業', '業績', '経済', '金融', '政策', '分析']
        professional_count = sum(script.count(term) for term in professional_terms)
        professional_score = min(1.0, professional_count / 20.0)  # 20回以上で満点
        
        # 総合評価
        overall_score = (
            char_score * 0.3 +
            duration_score * 0.2 +
            structure_score * 0.2 +
            readability_score * 0.15 +
            professional_score * 0.15
        )
        
        return ScriptQuality(
            char_count=char_count,
            estimated_duration_minutes=estimated_duration,
            structure_score=structure_score,
            readability_score=readability_score,
            professional_score=professional_score,
            overall_score=overall_score,
            issues=issues
        )
    
    def _adjust_script_quality(self, script: str, quality: ScriptQuality) -> str:
        """台本品質調整"""
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
                        temperature=0.2,
                        max_output_tokens=4096
                    )
                )
                
                if response.text:
                    adjusted = response.text.strip()
                    self.logger.info(f"文字数調整完了: {len(script)} → {len(adjusted)}")
                    return adjusted
                    
            except Exception as e:
                self.logger.error(f"台本調整エラー: {e}")
        
        return script