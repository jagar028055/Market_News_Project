"""
対話台本生成機能

ニュース記事からポッドキャスト用の対話台本を生成する機能を提供します。
Gemini 2.5 Proを使用して自然な2人の対話形式の台本を生成します。
"""

import json
import logging
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import google.generativeai as genai
from ..config.app_config import AppConfig, get_config


@dataclass
class ArticlePriority:
    """記事の優先度を表すデータクラス"""

    title: str
    content: str
    priority_score: float
    category: str


class DialogueScriptGenerator:
    """対話台本生成クラス

    収集されたニュース記事を基に、2人のスピーカーによる
    自然な対話形式のポッドキャスト台本を生成します。
    """

    def __init__(self, api_key: str):
        """
        初期化

        Args:
            api_key: Gemini APIキー
        """
        self.api_key = api_key
        self.model_name = "gemini-2.5-pro"  # 統一してgemini-2.5-proを使用
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
            スピーカータグ付きの対話台本

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

            # 対話形式にフォーマット
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
あなたは金融・経済ニュースのポッドキャスト台本を作成する専門家です。
以下のニュース記事を基に、2人のホスト（田中さんと山田さん）による10分間のマーケットニュース番組の台本を作成してください。

# 台本作成の要件
- 2人の自然な対話形式で構成
- 各発言は<speaker1>田中</speaker1>または<speaker2>山田</speaker2>のタグで区別
- 全体で2,400〜2,800文字程度
- 重要なニュースから順に取り上げる
- 専門用語は分かりやすく説明
- 個人投資家に役立つ視点を含める
- オープニングとクロージングを含める

# 対話の構成
1. オープニング（挨拶、今日の概要）
2. メイン（重要ニュース3-5項目を対話形式で）
3. クロージング（まとめ、次回予告）

# ニュース記事
{articles_text}

台本を作成してください：
"""
        return prompt

    def _format_dialogue(self, raw_script: str) -> str:
        """
        生成された台本を対話形式にフォーマット

        Args:
            raw_script: 生成された生の台本

        Returns:
            スピーカータグ付きのフォーマット済み台本
        """
        # 既にタグが含まれている場合は整形して返す
        if "<speaker1>" in raw_script and "<speaker2>" in raw_script:
            return self._normalize_speaker_tags(raw_script)

        # タグが無い場合は対話形式に変換
        lines = raw_script.strip().split("\n")
        formatted_lines = []
        current_speaker = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 話者指定がある場合の処理
            speaker_indicators = {
                1: ["田中:", "田中さん:", "A:", "ホスト1:", "司会:", "男性:"],
                2: ["山田:", "山田さん:", "B:", "ホスト2:", "アシスタント:", "女性:"],
            }

            detected_speaker = None
            cleaned_line = line

            for speaker_id, indicators in speaker_indicators.items():
                for indicator in indicators:
                    if line.startswith(indicator):
                        detected_speaker = speaker_id
                        cleaned_line = line[len(indicator) :].strip()
                        break
                if detected_speaker:
                    break

            if detected_speaker:
                current_speaker = detected_speaker

            if cleaned_line:
                speaker_name = "田中" if current_speaker == 1 else "山田"
                formatted_lines.append(
                    f"<speaker{current_speaker}>{speaker_name}</speaker{current_speaker}>:{cleaned_line}"
                )

                # 自然な話者切り替え（長い発言の後は切り替え）
                if len(cleaned_line) > 100:
                    current_speaker = 2 if current_speaker == 1 else 1

        return "\n".join(formatted_lines)

    def _normalize_speaker_tags(self, script: str) -> str:
        """
        スピーカータグを正規化

        Args:
            script: タグ付きの台本

        Returns:
            正規化されたタグ付き台本
        """
        # 不正なタグパターンを修正
        patterns = [
            (r"<speaker(\d+)>([^<]+)</speaker\d+>", r"<speaker\1>\2</speaker\1>"),
            (r"<speaker(\d+)>([^:]+):</speaker\d+>:", r"<speaker\1>\2</speaker\1>:"),
        ]

        normalized = script
        for pattern, replacement in patterns:
            normalized = re.sub(pattern, replacement, normalized)

        return normalized

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
        台本を目標文字数まで短縮

        Args:
            script: 元の台本

        Returns:
            短縮された台本
        """
        if len(script) <= self.target_char_max:
            return script

        # 行ごとに分割
        lines = script.split("\n")
        result_lines = []
        current_length = 0

        # クロージング部分を保持するため、逆順で重要度を判定
        essential_lines = []
        optional_lines = []

        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["おはようございます", "こんにちは", "ありがとう", "また明日"]
            ):
                essential_lines.append(line)
            else:
                optional_lines.append(line)

        # 必須行を先に追加
        for line in essential_lines:
            if current_length + len(line) <= self.target_char_max:
                result_lines.append(line)
                current_length += len(line)

        # 残り容量でオプション行を追加
        for line in optional_lines:
            if current_length + len(line) <= self.target_char_max:
                result_lines.append(line)
                current_length += len(line)
            else:
                break

        return "\n".join(result_lines)
