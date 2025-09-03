"""
台本生成機能

ニュース記事からポッドキャスト用の台本を生成する機能を提供します。
Gemini 2.5 Proを使用して専門的な単一ホスト形式の台本を生成します。
"""

import json
import logging
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import google.generativeai as genai
from src.config.app_config import AppConfig, get_config


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

    def __init__(self, api_key: str):
        """
        初期化

        Args:
            api_key: Gemini APIキー
        """
        self.api_key = api_key
        self.model_name = "gemini-2.0-flash-exp"  # 2.5 Proが利用可能になるまでflash-expを使用
        self.logger = logging.getLogger(__name__)

        # Gemini API設定
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name)

        # 設定値
        config = get_config()
        self.target_char_min = config.podcast.target_character_count[0]
        self.target_char_max = config.podcast.target_character_count[1]

        # 発音辞書を読み込み
        self.pronunciation_dict = config.podcast.load_pronunciation_dict()
        self.logger.info(f"発音辞書を読み込み: {len(self.pronunciation_dict)}語")

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

            # 台本生成用のプロンプトを作成
            prompt = self._create_script_prompt(prioritized_articles)

            # Gemini APIで台本生成
            response = self.model.generate_content(prompt)
            raw_script = response.text

            # 単一ホスト形式にフォーマット
            formatted_script = self._format_dialogue(raw_script)

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

    def _create_script_prompt(self, articles: List[ArticlePriority]) -> str:
        """
        台本生成用のプロンプトを作成

        Args:
            articles: 優先度付き記事リスト

        Returns:
            Gemini用プロンプト
        """
        articles_text = ""
        for i, article in enumerate(articles[:10]):  # 上位10記事のみ使用
            articles_text += f"\n{i+1}. 【{article.category}】{article.title}\n{article.content}\n"

        prompt = f"""
あなたは15年以上の経験を持つ金融市場専門のポッドキャストホストです。
機関投資家・経営者向けの高品質な市場分析番組を担当し、複雑な金融情報を専門性を保ちながら分かりやすく伝えるプロフェッショナルです。

以下のニュース記事を基に、15分間の専門的な市場ニュースポッドキャストの台本を作成してください。

# 台本作成の要件
- 1人のホストによる専門的な解説形式
- 全体で4,000〜6,000文字程度（完全な内容を重視し、途中で終わらせない）
- 重要なニュースから順に取り上げる
- 専門用語は分かりやすく説明
- 投資家・経営者に役立つ実践的な視点を含める
- オープニングとクロージングを含める
- 台本は自然な流れで完結させ、途中で切れることの無いようにする

# 構成
1. オープニング（挨拶、今日の市場概要）
2. メイン（重要ニュース3-5項目の詳細解説）
3. クロージング（まとめ、投資判断への影響、次回予告）

# クロージング必須要件
- 「以上、本日の市場ニュースポッドキャストでした。明日もよろしくお願いします。」で必ず終了

# ニュース記事
{articles_text}

台本を作成してください：
"""
        return prompt

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
