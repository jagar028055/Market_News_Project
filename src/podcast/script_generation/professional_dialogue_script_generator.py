# -*- coding: utf-8 -*-

"""
プロ版対話形式ポッドキャスト台本生成 (Gemini 2.5 Pro対応)
10分完全版・高品質台本生成システム
"""

import google.generativeai as genai
import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.logging_config import get_logger, log_with_context


class ProfessionalDialogueScriptGenerator:
    """プロ版対話形式ポッドキャスト台本生成クラス"""
    
    # 10分完全版プロンプトテンプレート（Gemini 2.5 Pro最適化）
    PROFESSIONAL_SCRIPT_PROMPT = """
あなたは経験豊富なプロ金融ニュースキャスターです。投資家・経営者向けの高品質な10分間ポッドキャスト台本を生成してください。

【最重要要件】
- **台本長**: 2600-2800文字（10分間の音声配信用）
- **対象聴衆**: 投資家・金融従事者・経営者
- **品質要求**: プロフェッショナルレベルの分析・洞察
- **実用性**: 当日の投資判断に活用可能な情報提供

【台本構成（厳密遵守）】

## 1. オープニング（200文字・30-60秒）
- 親しみやすいが品格ある挨拶
- 今日の日付・曜日・市場状況概観
- 本日の重要トピック予告（具体的に）
- 聞き手への感謝と番組価値の簡潔な説明

## 2. メインコンテンツ（2200文字・8-8.5分）

### 記事1: 最重要ニュース（400文字・90秒）
- 詳細な背景説明・市場コンテキスト
- 専門的な影響分析（短期・中長期）
- 他市場・セクターへの波及効果
- 投資家が注目すべきポイント

### 記事2: 重要市場動向（400文字・90秒）
- セクター別・地域別影響評価
- 過去事例との比較・類似性分析
- リスク要因・機会要因の整理
- 実践的な注意点・監視項目

### 記事3-4: 関連重要情報（各300文字・各60秒）
- 地域バランス重視（日本・米国・中国・欧州等）
- 異なるカテゴリーからの選択
- 相互関連性・連鎖反応の解説
- 市場全体への影響度評価

### 記事5-6: 補完・展望情報（各200文字・各45秒）
- 簡潔だが価値ある要点整理
- 明日以降の展開予測・注目事項
- 他ニュースとの関連性・文脈

### 総合分析・まとめ（400文字・90秒）
- 本日の市場全体動向総括
- 重要リスク要因・機会要因の統合評価
- 投資家への実践的アドバイス（推奨は避ける）
- 次週・次月の注目ポイント予告

## 3. クロージング（200文字・30-60秒）
- 本日の核心ポイント再確認
- 明日の注目事項・経済指標予告
- 感謝の言葉・継続視聴への誘導
- ブランド価値の簡潔な再表現

【プロフェッショナル表現指針】

**必須品質要素**:
- **話し言葉の自然さ**: 「〜ですね」「〜になります」等の流暢な表現
- **専門用語の丁寧な解説**: 「FOMC（エフオーエムシー・連邦公開市場委員会）」等
- **数値の聞き取りやすさ**: 「1兆2500億円」「前年同期比プラス2.1%」等
- **適切な間・強調**: 句読点での自然な区切り・重要部分の強調

**高度分析要素**:
- **因果関係の明確化**: 出来事の背景・結果の論理的説明
- **相関性の指摘**: 異なる市場・指標間の関連性
- **時系列分析**: 過去・現在・未来の時間軸での整理
- **リスク評価**: 楽観・悲観シナリオの均衡的提示

**回避すべき要素**:
- 30文字超の長文（音声配信に不適切）
- 投資推薦・断定的予測（コンプライアンス配慮）
- 感情的すぎる表現（客観性重視）
- 専門用語の過度な連続使用（理解促進重視）

【記事データ】
{articles_data}

【市場分析メタデータ】
- 生成日時: {generation_date}
- 総記事数: {total_articles}
- カテゴリ分布: {category_distribution}
- 地域分布: {region_distribution}
- 平均重要度: {average_importance}

【出力指示】
上記要件に従い、プロフェッショナルな10分間ポッドキャスト台本を生成してください。聞き手が投資判断に活用できる実践的価値を最優先し、音声として自然に読み上げられる高品質な台本を作成してください。
"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-lite-001"):
        """
        初期化
        
        Args:
            api_key: Gemini API キー
            model_name: 使用するGeminiモデル名（デフォルト: 2.0 Flash Lite）
        """
        self.api_key = api_key
        self.model_name = model_name
        self.logger = get_logger("professional_script_generator")
        
        if not api_key:
            raise ValueError("Gemini APIキーが設定されていません")
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        # Gemini 2.5 Proの場合の最適化設定
        self.is_pro_model = "2.5" in model_name.lower() and "pro" in model_name.lower()
        
        log_with_context(
            self.logger, logging.INFO, "プロ版台本生成器初期化完了",
            operation="init",
            model_name=model_name,
            is_pro_model=self.is_pro_model
        )
    
    def generate_professional_script(self, articles: List[Dict[str, Any]]) -> str:
        """
        プロ版10分完全台本生成
        
        Args:
            articles: 記事データリスト（重要度順・詳細データ付き）
            
        Returns:
            str: 生成された高品質台本
            
        Raises:
            Exception: 台本生成に失敗した場合
        """
        if not articles:
            raise ValueError("記事データが提供されていません")
            
        log_with_context(
            self.logger, logging.INFO, "プロ版台本生成開始",
            operation="generate_professional_script",
            articles_count=len(articles),
            model_name=self.model_name
        )
        
        try:
            # 記事データの高度分析・整理
            articles_analysis = self._analyze_articles_comprehensively(articles)
            
            # プロ版プロンプト構築
            prompt = self._build_professional_prompt(articles, articles_analysis)
            
            # Gemini API呼び出し（プロ版設定）
            script = self._generate_with_professional_settings(prompt)
            
            # 高品質検証・調整
            validated_script = self._validate_professional_quality(script, articles)
            
            log_with_context(
                self.logger, logging.INFO, "プロ版台本生成完了",
                operation="generate_professional_script",
                script_length=len(validated_script),
                target_length="2600-2800",
                quality_check="passed"
            )
            
            return validated_script
            
        except Exception as e:
            self.logger.error(f"プロ版台本生成エラー: {e}")
            # 高品質フォールバック処理
            return self._generate_professional_fallback(articles)
    
    def _analyze_articles_comprehensively(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        記事データの包括的分析
        
        Args:
            articles: 記事データリスト
            
        Returns:
            分析結果辞書
        """
        # カテゴリ分布分析
        categories = {}
        regions = {}
        sentiment_distribution = {'positive': 0, 'negative': 0, 'neutral': 0}
        total_importance = 0
        
        for article in articles:
            # カテゴリ統計
            category = article.get('category', 'other')
            categories[category] = categories.get(category, 0) + 1
            
            # 地域統計
            region = article.get('region', 'other')
            regions[region] = regions.get(region, 0) + 1
            
            # センチメント統計
            sentiment = article.get('sentiment_label', 'neutral').lower()
            if sentiment in sentiment_distribution:
                sentiment_distribution[sentiment] += 1
            
            # 重要度統計
            total_importance += article.get('importance_score', 0)
        
        analysis = {
            'category_distribution': categories,
            'region_distribution': regions,
            'sentiment_distribution': sentiment_distribution,
            'average_importance': round(total_importance / len(articles), 2) if articles else 0,
            'total_articles': len(articles),
            'dominant_category': max(categories.items(), key=lambda x: x[1])[0] if categories else 'none',
            'dominant_region': max(regions.items(), key=lambda x: x[1])[0] if regions else 'none',
            'market_sentiment': self._determine_overall_sentiment(sentiment_distribution)
        }
        
        return analysis
    
    def _determine_overall_sentiment(self, sentiment_dist: Dict[str, int]) -> str:
        """全体的市場センチメント判定"""
        total = sum(sentiment_dist.values())
        if total == 0:
            return 'neutral'
        
        positive_ratio = sentiment_dist['positive'] / total
        negative_ratio = sentiment_dist['negative'] / total
        
        if positive_ratio > 0.6:
            return 'strongly_positive'
        elif positive_ratio > 0.4:
            return 'moderately_positive'
        elif negative_ratio > 0.6:
            return 'strongly_negative'
        elif negative_ratio > 0.4:
            return 'moderately_negative'
        else:
            return 'mixed'
    
    def _build_professional_prompt(self, articles: List[Dict[str, Any]], analysis: Dict[str, Any]) -> str:
        """
        プロ版プロンプト構築
        
        Args:
            articles: 記事データ
            analysis: 分析結果
            
        Returns:
            完全プロンプト
        """
        # 記事データを詳細フォーマット
        articles_summary = self._format_articles_for_professional_analysis(articles)
        
        # メタデータ準備
        category_dist_str = ', '.join([f"{k}: {v}件" for k, v in analysis['category_distribution'].items()])
        region_dist_str = ', '.join([f"{k}: {v}件" for k, v in analysis['region_distribution'].items()])
        
        prompt = self.PROFESSIONAL_SCRIPT_PROMPT.format(
            articles_data=articles_summary,
            generation_date=datetime.now().strftime("%Y年%m月%d日 %H:%M JST"),
            total_articles=analysis['total_articles'],
            category_distribution=category_dist_str,
            region_distribution=region_dist_str,
            average_importance=analysis['average_importance']
        )
        
        return prompt
    
    def _format_articles_for_professional_analysis(self, articles: List[Dict[str, Any]]) -> str:
        """
        プロ版記事データフォーマット
        
        Args:
            articles: 記事データリスト
            
        Returns:
            フォーマット済み記事テキスト
        """
        formatted_articles = []
        
        for i, article in enumerate(articles, 1):
            # 重要度ランク表示
            importance_rank = "🔴 最重要" if article.get('importance_score', 0) >= 8 else \
                           "🟠 重要" if article.get('importance_score', 0) >= 6 else \
                           "🟡 注目" if article.get('importance_score', 0) >= 4 else "🔵 補完"
            
            article_text = f"""
【記事 {i}】 {importance_rank} (スコア: {article.get('importance_score', 0)})
タイトル: {article.get('title', 'タイトル不明')}
分類: {article.get('category', '未分類')} | 地域: {article.get('region', '不明')}
センチメント: {article.get('sentiment_label', '中立')} (スコア: {article.get('sentiment_score', 0)})
公開: {article.get('published_date', '不明')} | ソース: {article.get('source', '不明')}
要約: {article.get('summary', '要約なし')}
URL: {article.get('url', '')}
---
"""
            formatted_articles.append(article_text)
        
        return "\\n".join(formatted_articles)
    
    def _generate_with_professional_settings(self, prompt: str) -> str:
        """
        プロ版設定でGemini API呼び出し
        
        Args:
            prompt: 生成プロンプト
            
        Returns:
            生成された台本
        """
        try:
            # プロモデル用の最適化設定
            if self.is_pro_model:
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=4000,    # より長い出力を許可
                    temperature=0.2,           # 高品質・一貫性重視
                    top_p=0.9,                # 創造性と品質のバランス
                    top_k=50                  # 多様性を適度に確保
                )
            else:
                # 既存モデル用設定
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=3000,
                    temperature=0.3,
                    top_p=0.8,
                    top_k=40
                )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            if not response.text:
                raise Exception("Gemini APIからの応答が空です")
                
            return response.text.strip()
            
        except Exception as e:
            self.logger.error(f"Gemini API呼び出しエラー: {e}")
            raise
    
    def _validate_professional_quality(self, script: str, articles: List[Dict[str, Any]]) -> str:
        """
        プロ版品質検証・調整
        
        Args:
            script: 生成台本
            articles: 元記事データ
            
        Returns:
            品質調整済み台本
        """
        # 文字数チェック
        char_count = len(script)
        target_min, target_max = 2600, 2800
        
        if char_count < target_min:
            log_with_context(
                self.logger, logging.WARNING, "台本が短すぎます - 拡張処理実行",
                operation="quality_check",
                current_length=char_count,
                target_range=f"{target_min}-{target_max}"
            )
            script = self._expand_script_professionally(script, articles, target_min - char_count)
            
        elif char_count > target_max:
            log_with_context(
                self.logger, logging.WARNING, "台本が長すぎます - 最適化処理実行",
                operation="quality_check",
                current_length=char_count,
                target_range=f"{target_min}-{target_max}"
            )
            script = self._optimize_script_length(script, target_max)
        
        # プロ表現の品質向上
        script = self._enhance_professional_expressions(script)
        
        # 最終検証
        final_char_count = len(script)
        log_with_context(
            self.logger, logging.INFO, "プロ版品質検証完了",
            operation="quality_validation",
            initial_length=char_count,
            final_length=final_char_count,
            target_achieved=target_min <= final_char_count <= target_max
        )
        
        return script
    
    def _expand_script_professionally(self, script: str, articles: List[Dict[str, Any]], needed_chars: int) -> str:
        """プロ品質での台本拡張"""
        # より詳細な市場分析を追加
        expansion_content = "\\n\\n【補足市場分析】\\n"
        expansion_content += "本日取り上げた各ニュースの相互関連性を見ますと、"
        
        if len(articles) >= 2:
            top_categories = list(set([a.get('category', 'other') for a in articles[:3]]))
            expansion_content += f"{', '.join(top_categories)}の分野で重要な動きが見られており、"
        
        expansion_content += "これらの動向は今後数週間にわたって市場参加者の注目を集め続けると予想されます。"
        
        return script + expansion_content
    
    def _optimize_script_length(self, script: str, target_max: int) -> str:
        """台本長さ最適化"""
        if len(script) <= target_max:
            return script
        
        # 段落単位で調整
        paragraphs = script.split('\\n\\n')
        optimized_paragraphs = []
        total_chars = 0
        
        for paragraph in paragraphs:
            if total_chars + len(paragraph) <= target_max:
                optimized_paragraphs.append(paragraph)
                total_chars += len(paragraph) + 2  # \n\n分を考慮
            else:
                # 締めくくりの段落は保持
                if any(word in paragraph for word in ['ありがとう', 'お聞きください', 'また明日']):
                    optimized_paragraphs.append(paragraph)
                break
        
        return '\\n\\n'.join(optimized_paragraphs)
    
    def _enhance_professional_expressions(self, script: str) -> str:
        """プロ表現の品質向上"""
        # 専門用語の読み方強化
        professional_replacements = {
            'FRB': 'FRB（エフアールビー・米連邦準備制度理事会）',
            'FOMC': 'FOMC（エフオーエムシー・連邦公開市場委員会）',
            'GDP': 'GDP（ジーディーピー・国内総生産）',
            'CPI': 'CPI（シーピーアイ・消費者物価指数）',
            'S&P500': 'S&P500（エスアンドピー500）',
            'NASDAQ': 'NASDAQ（ナスダック）',
            'ECB': 'ECB（イーシービー・欧州中央銀行）',
            'BOJ': 'BOJ（ビーオージェー・日本銀行）'
        }
        
        for term, professional_form in professional_replacements.items():
            # 初回出現時のみ詳細形式に置換
            if term in script and professional_form not in script:
                script = script.replace(term, professional_form, 1)
        
        return script
    
    def _generate_professional_fallback(self, articles: List[Dict[str, Any]]) -> str:
        """
        プロ版フォールバック台本生成
        
        Args:
            articles: 記事データリスト
            
        Returns:
            基本的な高品質台本
        """
        log_with_context(
            self.logger, logging.WARNING, "プロ版フォールバック台本生成を実行",
            operation="fallback_generation",
            articles_count=len(articles)
        )
        
        # プロ水準の基本構造で台本生成
        script_parts = [
            "おはようございます。本日のマーケットニュースをお届けします。",
            f"今日は{datetime.now().strftime('%Y年%m月%d日')}、重要な市場動向をお伝えします。\\n"
        ]
        
        # 上位4記事を選択
        top_articles = articles[:4]
        
        for i, article in enumerate(top_articles, 1):
            title = article.get('title', 'タイトル不明')
            summary = article.get('summary', '詳細は後ほどお伝えします')
            category = article.get('category', '市場')
            importance = article.get('importance_score', 0)
            
            script_parts.extend([
                f"\\n【{i}つ目のニュース】 重要度: {importance}ポイント",
                f"{title}\\n",
                f"この{category}関連のニュースについて詳しく見てみましょう。",
                f"{summary}\\n",
                f"この動向は投資家の皆様にとって重要な判断材料となりそうです。\\n"
            ])
        
        # プロ水準のまとめ
        script_parts.extend([
            "\\n【本日の総合分析】",
            "今日お伝えしたニュースを総合的に分析しますと、",
            f"市場では{len(top_articles)}つの重要な動きが注目されており、",
            "これらの動向は相互に関連しながら、今後の投資環境に影響を与えることが予想されます。",
            "\\n投資家の皆様におかれましては、これらの情報を踏まえて",
            "慎重かつ戦略的な判断をされることをお勧めします。",
            "\\n本日も貴重なお時間をいただき、ありがとうございました。",
            "明日も重要な市場情報をお届けします。"
        ])
        
        fallback_script = "".join(script_parts)
        
        # 最低限の品質調整
        if len(fallback_script) < 2000:
            fallback_script += "\\n\\n【追加解説】\\n今回の各ニュースが市場に与える影響について、引き続き注意深く監視していく必要があります。"
        
        return fallback_script