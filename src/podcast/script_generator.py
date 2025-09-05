"""
台本生成機能

ニュース記事からポッドキャスト用の台本を生成する機能を提供します。
Gemini 2.5 Proを使用して専門的な単一ホスト形式の台本を生成します。
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import google.generativeai as genai
from src.config.app_config import AppConfig, get_config
from src.podcast.prompts.prompt_manager import PromptManager


@dataclass
class ArticlePriority:
    """記事の優先度を表すデータクラス"""

    title: str
    content: str
    priority_score: float
    category: str


class DialogueScriptGenerator:
    """台本生成クラス

    収集されたニュース記事を基に、専門的な単一ホスト形式の
    ポッドキャスト台本を生成します。
    """

    def __init__(self, api_key: str, prompt_pattern: str = "current_professional"):
        """
        初期化

        Args:
            api_key: Gemini APIキー
            prompt_pattern: 使用するプロンプトパターン
        """
        self.api_key = api_key
        self.model_name = "gemini-2.0-flash-exp"  # 2.5 Proが利用可能になるまでflash-expを使用
        self.prompt_pattern = prompt_pattern
        self.logger = logging.getLogger(__name__)

        # Gemini API設定
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name)

        # プロンプト管理システムの初期化
        self.prompt_manager = PromptManager()
        
        # 設定値
        config = get_config()
        self.target_char_min = config.podcast.target_character_count[0]
        self.target_char_max = config.podcast.target_character_count[1]

        # 発音辞書を読み込み
        self.pronunciation_dict = config.podcast.load_pronunciation_dict()
        self.logger.info(f"発音辞書を読み込み: {len(self.pronunciation_dict)}語")
        self.logger.info(f"プロンプトパターン: {prompt_pattern}")

    def generate_script(self, articles: List[Dict]) -> str:
        """
        記事リストから対話台本を生成

        Args:
            articles: ニュース記事のリスト

        Returns:
            単一ホスト形式の台本

        Raises:
            Exception: 台本生成に失敗した場合
        """
        try:
            self.logger.info(f"台本生成を開始: {len(articles)}件の記事を処理")

            # 記事を優先度順に並び替え
            prioritized_articles = self._prioritize_articles(articles)

            # 台本生成用のプロンプトを作成（テンプレート使用）
            prompt = self._create_script_prompt_with_template(prioritized_articles)

            # Gemini APIで台本生成（プロンプトマネージャーの設定を使用）
            generation_config = self.prompt_manager.get_generation_config(self.prompt_pattern)
            response = self.model.generate_content(prompt, generation_config=generation_config)
            raw_script = response.text

            # AI定型句を除去
            cleaned_script = self._clean_ai_preamble(raw_script)
            
            # 単一ホスト形式にフォーマット
            formatted_script = self._format_dialogue(cleaned_script)

            # 発音修正を適用
            corrected_script = self._apply_pronunciation_corrections(formatted_script)

            # 文字数チェック
            char_count = len(corrected_script)
            self.logger.info(f"生成された台本の文字数: {char_count}")

            if char_count < self.target_char_min:
                self.logger.warning(f"台本が短すぎます: {char_count} < {self.target_char_min}")
            elif char_count > self.target_char_max:
                self.logger.warning(f"台本が長すぎます: {char_count} > {self.target_char_max}")
                corrected_script = self._trim_script(corrected_script)

            return corrected_script

        except Exception as e:
            self.logger.error(f"台本生成に失敗: {str(e)}")
            raise

    def _prioritize_articles(self, articles: List[Dict]) -> List[ArticlePriority]:
        """
        記事を重要度順に並び替え

        Args:
            articles: ニュース記事のリスト

        Returns:
            優先度付きの記事リスト
        """
        prioritized = []

        for article in articles:
            # 重要度を計算（簡易版）
            priority_score = self._calculate_priority(article)

            prioritized.append(
                ArticlePriority(
                    title=article.get("title", ""),
                    content=article.get("content", article.get("summary", "")),
                    priority_score=priority_score,
                    category=self._categorize_article(article),
                )
            )

        # 優先度順にソート
        prioritized.sort(key=lambda x: x.priority_score, reverse=True)
        return prioritized

    def _calculate_priority(self, article: Dict) -> float:
        """
        記事の優先度を計算

        Args:
            article: ニュース記事

        Returns:
            優先度スコア（高いほど重要）
        """
        score = 0.0
        title = article.get("title", "").lower()
        content = article.get("content", article.get("summary", "")).lower()

        # キーワードベースの優先度付け
        high_priority_keywords = [
            "日銀",
            "金利",
            "fed",
            "fomc",
            "株価",
            "円安",
            "円高",
            "gdp",
            "cpi",
            "インフレ",
            "デフレ",
            "決算",
            "業績",
        ]

        medium_priority_keywords = ["企業", "業界", "市場", "投資", "経済", "政策"]

        for keyword in high_priority_keywords:
            if keyword in title:
                score += 3.0
            if keyword in content:
                score += 1.0

        for keyword in medium_priority_keywords:
            if keyword in title:
                score += 2.0
            if keyword in content:
                score += 0.5

        # 記事の新しさも考慮（publishedが最近ほど高得点）
        if "published" in article:
            # 簡易的な新しさスコア
            score += 1.0

        return score

    def _categorize_article(self, article: Dict) -> str:
        """
        記事をカテゴリ分類

        Args:
            article: ニュース記事

        Returns:
            カテゴリ名
        """
        title = article.get("title", "").lower()
        content = article.get("content", article.get("summary", "")).lower()

        if any(
            keyword in title or keyword in content for keyword in ["日銀", "fed", "金利", "政策"]
        ):
            return "金融政策"
        elif any(
            keyword in title or keyword in content for keyword in ["株価", "日経", "dow", "nasdaq"]
        ):
            return "株式市場"
        elif any(
            keyword in title or keyword in content for keyword in ["円安", "円高", "ドル", "ユーロ"]
        ):
            return "為替"
        elif any(
            keyword in title or keyword in content for keyword in ["決算", "業績", "売上", "利益"]
        ):
            return "企業業績"
        else:
            return "一般経済"

    def _create_script_prompt_with_template(self, articles: List[ArticlePriority]) -> str:
        """
        プロンプトテンプレートを使用した台本生成用プロンプトを作成

        Args:
            articles: 優先度付き記事リスト

        Returns:
            テンプレート適用済みプロンプト
        """
        # 記事データを整形
        articles_data = ""
        for i, article in enumerate(articles[:10]):  # 上位10記事のみ使用
            articles_data += f"\n{i+1}. 【{article.category}】{article.title}\n{article.content}\n"

        # 統合市場分析（簡易版）
        integrated_context = "本日の市場動向を総合的に分析し、投資家向けの洞察を提供します。"
        
        # テンプレート変数
        template_vars = {
            "target_duration": 15,
            "target_chars": (self.target_char_min + self.target_char_max) // 2,
            "target_chars_min": self.target_char_min,
            "target_chars_max": self.target_char_max,
            "main_content_chars": (self.target_char_min + self.target_char_max) // 2 - 400,  # オープニング・クロージング除く
            "main_content_chars_min": self.target_char_min - 400,
            "main_content_chars_max": self.target_char_max - 400,
            "generation_date": datetime.now().strftime("%Y年%m月%d日"),
            "integrated_context": integrated_context,
            "articles_data": articles_data
        }

        try:
            # プロンプトテンプレートを読み込み・適用
            prompt = self.prompt_manager.load_prompt_template(self.prompt_pattern, **template_vars)
            self.logger.info(f"プロンプトテンプレート適用完了: {self.prompt_pattern}")
            return prompt
            
        except Exception as e:
            self.logger.error(f"プロンプトテンプレート適用エラー: {e}")
            # フォールバック: 従来のプロンプトを使用
            return self._create_fallback_script_prompt(articles)
    
    def _create_fallback_script_prompt(self, articles: List[ArticlePriority]) -> str:
        """
        フォールバック用の従来プロンプト（AI定型句除去版）

        Args:
            articles: 優先度付き記事リスト

        Returns:
            フォールバック用プロンプト
        """
        self.logger.warning("フォールバックプロンプトを使用")
        
        articles_text = ""
        for i, article in enumerate(articles[:10]):
            articles_text += f"\n{i+1}. 【{article.category}】{article.title}\n{article.content}\n"

        return f"""
以下のニュース記事を基に、金融ポッドキャスト番組の台本（{self.target_char_min}-{self.target_char_max}文字）を作成してください。
台本のみを出力し、説明や前置きは不要です。

記事データ:
{articles_text}

{datetime.now().strftime("%Y年%m月%d日")}から開始する台本:
"""

    def _format_dialogue(self, raw_script: str) -> str:
        """
        生成された台本を単一ホスト形式にフォーマット

        Args:
            raw_script: 生成された生の台本

        Returns:
            フォーマット済みの台本（単一ホスト形式）
        """
        # 単一ホスト形式では特別なタグは不要
        # ただし、不要な話者指示があれば除去
        lines = raw_script.strip().split("\n")
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 話者指示を除去（単一ホスト形式では不要）
            speaker_indicators = [
                "ホスト:", "司会:", "アナウンサー:", "解説:", "専門家:", "ナレーター:"
            ]

            cleaned_line = line
            for indicator in speaker_indicators:
                if line.startswith(indicator):
                    cleaned_line = line[len(indicator):].strip()
                    break

            if cleaned_line:
                formatted_lines.append(cleaned_line)

        return "\n".join(formatted_lines)
    
    def _clean_ai_preamble(self, script: str) -> str:
        """
        AI生成文の冒頭にある定型句を除去

        Args:
            script: 生成された台本

        Returns:
            定型句除去済みの台本
        """
        # AI応答の定型句パターン
        preamble_patterns = [
            r'^(はい、?承知(いたし)?ました。?\s*)',
            r'^(分かりました。?\s*)',
            r'^(了解です。?\s*)',
            r'^(以下が?台本です。?\s*)',
            r'^(台本を作成(いたし)?ました。?\s*)',
            r'^(現在の台本に適切な.*を追加し.*\s*)',
            r'^(完成させた台本を以下に.*\s*)',
            r'^(---+\s*)',
            r'^(###.*台本.*\s*)',
            r'^(```.*\s*)'
        ]
        
        cleaned_script = script.strip()
        
        for pattern in preamble_patterns:
            cleaned_script = re.sub(pattern, '', cleaned_script, flags=re.IGNORECASE | re.MULTILINE)
            cleaned_script = cleaned_script.strip()
        
        # 複数の空行を単一の空行に
        cleaned_script = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_script)
        
        return cleaned_script


    def _apply_pronunciation_corrections(self, script: str) -> str:
        """
        発音辞書を適用して専門用語を修正

        Args:
            script: 台本テキスト

        Returns:
            発音修正済みの台本
        """
        corrected_script = script
        corrections_applied = 0

        for original, corrected in self.pronunciation_dict.items():
            if original in corrected_script:
                corrected_script = corrected_script.replace(original, corrected)
                corrections_applied += 1

        if corrections_applied > 0:
            self.logger.info(f"発音修正を適用: {corrections_applied}箇所")

        return corrected_script

    def _trim_script(self, script: str) -> str:
        """
        台本を目標文字数まで短縮（ただし、完全性を重視し途中終了を避ける）

        Args:
            script: 元の台本

        Returns:
            短縮された台本
        """
        if len(script) <= self.target_char_max:
            return script

        self.logger.warning(f"台本が最大文字数を超過: {len(script)} > {self.target_char_max}")
        
        # 緩い制限の場合、完全性を重視して短縮しない
        if len(script) <= self.target_char_max * 1.2:  # 20%の超過まで許容
            self.logger.info("軽微な文字数超過のため、台本の完全性を優先し短縮せずに使用")
            return script

        # 行ごとに分割
        lines = script.split("\n")
        
        # オープニング、クロージングを特定
        opening_lines = []
        closing_lines = []
        main_lines = []
        
        in_opening = True
        in_closing = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # オープニングの終了を検出
            if in_opening and any(keyword in line_lower for keyword in ["それでは", "さて", "今日の", "本日の"]):
                opening_lines.append(line)
                in_opening = False
                continue
                
            # クロージングの開始を検出（後半部分で）
            if i > len(lines) * 0.7 and any(keyword in line_lower for keyword in ["まとめ", "以上", "ありがとう", "また明日", "次回"]):
                in_closing = True
                
            if in_opening:
                opening_lines.append(line)
            elif in_closing:
                closing_lines.append(line)
            else:
                main_lines.append(line)
        
        # オープニングとクロージングは必須として保持
        essential_content = "\n".join(opening_lines + closing_lines)
        essential_length = len(essential_content)
        
        # メインコンテンツで調整可能な文字数
        available_for_main = self.target_char_max - essential_length
        
        # メインコンテンツを必要に応じて短縮
        selected_main_lines = []
        current_main_length = 0
        
        for line in main_lines:
            if current_main_length + len(line) <= available_for_main:
                selected_main_lines.append(line)
                current_main_length += len(line)
            else:
                break
        
        # 最終的な台本を構築
        final_script = "\n".join(opening_lines + selected_main_lines + closing_lines)
        
        self.logger.info(f"台本短縮完了: {len(script)} → {len(final_script)} 文字")
        return final_script
