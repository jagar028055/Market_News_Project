# -*- coding: utf-8 -*-

"""
対話形式ポッドキャスト台本生成
高品質な10分間ポッドキャストの台本を生成します
"""

import google.generativeai as genai
import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime


class DialogueScriptGenerator:
    """対話形式ポッドキャスト台本生成クラス"""

    # 台本生成用プロンプトテンプレート
    SCRIPT_GENERATION_PROMPT = """
あなたは経験豊富な金融ニュースキャスターです。以下の記事から、10分間（約2600-2800文字）の自然で魅力的なポッドキャスト台本を生成してください。

【台本の構成要件】
1. **オープニング（30秒-1分）**: 親しみやすい挨拶と今日のトピック紹介
2. **メインコンテンツ（13-14分）**: 多層構造による記事解説
   - **Tier 1（メイン解説）**: 最重要3記事を詳細分析（各記事350文字程度）
   - **Tier 2（中程度解説）**: 重要5記事を要点整理（各記事200文字程度）
   - **Tier 3（簡潔紹介）**: 補完7記事を見出しレベル（各記事80文字程度）
   - 専門用語は分かりやすく説明、投資家への実践的アドバイス
3. **クロージング（30秒-1分）**: 全体まとめと次回予告、お礼

【音声配信用の表現指針】
- 話し言葉で自然なトーン
- 専門用語には必ず分かりやすい説明を付ける
- 数値や固有名詞は明確に発音しやすい形で記載
- 適度な間（、）と改行を使って読みやすく
- 聞き手を意識した親しみやすい語りかけ

【避けるべき要素】
- 複雑すぎる専門用語の連続使用
- 長すぎる一文（30文字以上の文は分割）
- 感情的すぎる表現
- 投資推薦や断定的な予測

【記事データ】
{articles_data}

【生成日時】
{generation_date}

台本を生成してください。文字数は4000-4500文字程度を目標とし（約15分の配信）、多層構造による情報密度の高い内容で、音声として自然に読み上げられる形式で出力してください。
"""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-lite-001"):
        """
        初期化

        Args:
            api_key: Gemini API キー
            model_name: 使用するGeminiモデル名
        """
        self.api_key = api_key
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)

        if not api_key:
            raise ValueError("Gemini APIキーが設定されていません")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate_script(self, articles: List[Dict[str, Any]]) -> str:
        """
        記事から対話形式の台本を生成

        Args:
            articles: 記事データのリスト

        Returns:
            str: 生成された台本

        Raises:
            Exception: 台本生成に失敗した場合
        """
        if not articles:
            raise ValueError("記事データが提供されていません")

        self.logger.info(f"台本生成開始 - {len(articles)}記事を処理")

        try:
            # 記事データを整理
            articles_summary = self._prepare_articles_data(articles)

            # プロンプト生成
            prompt = self.SCRIPT_GENERATION_PROMPT.format(
                articles_data=articles_summary,
                generation_date=datetime.now().strftime("%Y年%m月%d日 %H:%M"),
            )

            # Gemini APIで台本生成
            script = self._generate_with_gemini(prompt)

            # 品質チェック
            validated_script = self._validate_script_quality(script)

            self.logger.info(f"台本生成完了 - {len(validated_script)}文字")
            return validated_script

        except Exception as e:
            self.logger.error(f"台本生成エラー: {e}")
            # フォールバック処理
            return self._generate_fallback_script(articles)

    def _prepare_articles_data(self, articles: List[Dict[str, Any]]) -> str:
        """
        記事データを台本生成用に整理

        Args:
            articles: 記事データのリスト

        Returns:
            str: 整理された記事データのテキスト表現
        """
        prepared_articles = []

        # 重要度順にソート（sentimentスコアとsummaryの長さで判定）
        sorted_articles = sorted(
            articles,
            key=lambda x: (
                abs(x.get("sentiment_score", 0)),  # センチメントの絶対値
                len(x.get("summary", "")),  # サマリーの長さ
                len(x.get("title", "")),  # タイトルの長さ
            ),
            reverse=True,
        )

        # 記事を重要度別に階層化（最大15記事を使用）
        # Tier 1: 最重要記事（詳細解説用）
        tier1_articles = sorted_articles[:3]
        # Tier 2: 重要記事（中程度解説用） 
        tier2_articles = sorted_articles[3:8]
        # Tier 3: 補完記事（簡潔紹介用）
        tier3_articles = sorted_articles[8:15]
        
        all_selected_articles = tier1_articles + tier2_articles + tier3_articles
        
        for i, article in enumerate(all_selected_articles, 1):
            # 記事の階層を判定
            if i <= 3:
                tier = "メイン（詳細解説）"
            elif i <= 8:
                tier = "重要（中程度解説）"
            else:
                tier = "補完（簡潔紹介）"
            article_text = f"""
記事 {i} [{tier}]:
タイトル: {article.get('title', 'タイトルなし')}
要約: {article.get('summary', '要約なし')}
センチメント: {article.get('sentiment_label', 'なし')} (スコア: {article.get('sentiment_score', 0)})
公開日: {article.get('published_date', '不明')}
ソース: {article.get('source', '不明')}
"""
            prepared_articles.append(article_text)

        return "\n" + "=" * 50 + "\n".join(prepared_articles)

    def _generate_with_gemini(self, prompt: str) -> str:
        """
        Gemini APIを使用して台本を生成

        Args:
            prompt: 生成用プロンプト

        Returns:
            str: 生成された台本
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=3000,  # 台本用に長めに設定
                    temperature=0.3,  # 創造性と一貫性のバランス
                    top_p=0.8,  # 高品質な出力のため
                    top_k=40,
                ),
            )

            if not response.text:
                raise Exception("Gemini APIからの応答が空です")

            return response.text.strip()

        except Exception as e:
            self.logger.error(f"Gemini API呼び出しエラー: {e}")
            raise

    def _validate_script_quality(self, script: str) -> str:
        """
        生成された台本の品質をチェック・調整

        Args:
            script: 生成された台本

        Returns:
            str: 品質チェック済みの台本
        """
        # 文字数チェック（15分版に対応）
        char_count = len(script)
        if char_count < 3800:
            self.logger.warning(f"台本が短すぎます ({char_count}文字) - 目標: 4000-4500文字")
        elif char_count > 4800:
            self.logger.warning(f"台本が長すぎます ({char_count}文字) - 目標: 4000-4500文字")
            # 長すぎる場合は適度に短縮
            script = self._trim_script(script)

        # 読みやすさの調整
        script = self._improve_readability(script)

        return script

    def _trim_script(self, script: str) -> str:
        """
        台本を適切な長さに調整

        Args:
            script: 元の台本

        Returns:
            str: 調整された台本
        """
        # 段落単位で調整
        paragraphs = script.split("\n\n")
        trimmed_paragraphs = []
        total_chars = 0

        for paragraph in paragraphs:
            if total_chars + len(paragraph) <= 4500:
                trimmed_paragraphs.append(paragraph)
                total_chars += len(paragraph)
            else:
                # 最後の段落は締めくくりを保持
                if "ありがとう" in paragraph or "お聞きください" in paragraph:
                    trimmed_paragraphs.append(paragraph)
                break

        return "\n\n".join(trimmed_paragraphs)

    def _improve_readability(self, script: str) -> str:
        """
        台本の読みやすさを向上

        Args:
            script: 元の台本

        Returns:
            str: 読みやすさを改善した台本
        """
        # 専門用語の読み方注釈を追加
        replacements = {
            "FRB": "FRB（エフアールビー）",
            "FOMC": "FOMC（エフオーエムシー）",
            "GDP": "GDP（ジーディーピー）",
            "CPI": "CPI（シーピーアイ）",
            "S&P500": "S&P500（エスアンドピー500）",
            "NASDAQ": "NASDAQ（ナスダック）",
        }

        for term, readable in replacements.items():
            script = script.replace(term, readable)

        # 長い文を分割（句読点での自然な区切りを優先）
        sentences = script.split("。")
        improved_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 40 and "、" in sentence:
                # 長い文は読点で区切って読みやすく
                sentence = sentence.replace("、", "。\n")
            improved_sentences.append(sentence)

        return "。".join(improved_sentences)

    def _generate_fallback_script(self, articles: List[Dict[str, Any]]) -> str:
        """
        API呼び出し失敗時のフォールバック台本生成

        Args:
            articles: 記事データのリスト

        Returns:
            str: 基本的な台本
        """
        self.logger.warning("フォールバック台本生成を実行")

        # 基本的な構造で台本生成
        script_parts = [
            "こんにちは。マーケットニュースポッドキャストの時間です。",
            "本日も重要な市場動向をお伝えします。\n",
        ]

        # 上位3記事を選択
        top_articles = articles[:3]

        for i, article in enumerate(top_articles, 1):
            title = article.get("title", "タイトル不明")
            summary = article.get("summary", "詳細は後ほどお伝えします")

            script_parts.extend(
                [
                    f"\n{i}つ目のニュースです。",
                    f"{title}\n",
                    f"{summary}\n",
                    "このニュースは投資家の皆様にとって重要な情報となりそうです。\n",
                ]
            )

        script_parts.extend(
            [
                "\n以上、本日のマーケットニュースをお伝えしました。",
                "次回も重要な市場情報をお届けします。",
                "お聞きいただき、ありがとうございました。",
            ]
        )

        return " ".join(script_parts)
