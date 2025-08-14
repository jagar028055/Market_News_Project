# -*- coding: utf-8 -*-

import google.generativeai as genai
import os
import json
import re
import time
from typing import Optional, Dict, Any, List
import logging
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ProSummaryConfig:
    """Pro統合要約の設定クラス"""
    enabled: bool = True
    min_articles_threshold: int = 10
    max_daily_executions: int = 3
    execution_hours: List[int] = None  # [9, 15, 21] # JST
    cost_limit_monthly: float = 50.0  # USD
    timeout_seconds: int = 180
    model_name: str = "gemini-2.5-pro"
    
    def __post_init__(self):
        if self.execution_hours is None:
            self.execution_hours = list(range(24))  # 24時間いつでも実行可能


class ProSummarizer:
    """Gemini 2.5 Proによる統合要約機能"""
    
    def __init__(self, api_key: str, config: ProSummaryConfig = None):
        """
        初期化
        
        Args:
            api_key (str): Google Gemini APIキー
            config (ProSummaryConfig): 設定オブジェクト
        """
        self.api_key = api_key
        self.config = config or ProSummaryConfig()
        self.logger = logging.getLogger(__name__)
        
        if not api_key:
            raise ValueError("Gemini APIキーが設定されていません")
        
        if len(api_key) < 20:  # 基本的な長さチェック
            raise ValueError("Gemini APIキーが無効です（長さが短すぎます）")
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.config.model_name)
            self.logger.info(f"Gemini APIが正常に初期化されました (モデル: {self.config.model_name})")
        except Exception as e:
            self.logger.error(f"Gemini API初期化失敗: {e}")
            raise
    
    def generate_unified_summary(self, grouped_articles: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        一括統合要約を生成（地域関連性を考慮）
        
        Args:
            grouped_articles (Dict[str, List[Dict]]): 地域別にグループ化された記事群
                例: {"japan": [{"summary": "...", "title": "...", "category": "..."}], ...}
        
        Returns:
            Dict[str, Any]: 統合要約結果（地域別+全体+関連性分析）
        """
        start_time = time.time()
        total_articles = sum(len(articles) for articles in grouped_articles.values())
        self.logger.info(f"一括統合要約生成開始 (総記事数: {total_articles}, 地域数: {len(grouped_articles)})")
        
        # 記事数制限（トークン制限対策）
        max_total_articles = 50
        limited_articles = {}
        
        for region, articles in grouped_articles.items():
            if len(articles) == 0:
                continue
            # 各地域最大15記事に制限
            max_per_region = min(15, max_total_articles // len(grouped_articles))
            if len(articles) > max_per_region:
                self.logger.warning(f"地域 {region}: {len(articles)}件 → {max_per_region}件に制限")
                articles = articles[:max_per_region]
            limited_articles[region] = articles
        
        try:
            prompt = self._build_unified_prompt(limited_articles)
            self.logger.info(f"統合プロンプト生成完了: {len(prompt)}文字")
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=4096,  # 一括処理なので出力トークン数を増加
                    temperature=0.3,
                ),
                request_options={"timeout": 120}  # 120秒タイムアウト
            )
            
            if not response:
                raise Exception("Gemini APIからレスポンスが返されませんでした")
            
            if not hasattr(response, 'text') or not response.text:
                raise Exception(f"Gemini APIレスポンスにテキストが含まれていません: {response}")
            
            self.logger.info(f"統合要約APIレスポンス受信: {len(response.text)}文字")
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # レスポンスを解析
            parsed_result = self._parse_unified_response(response.text)
            
            if parsed_result:
                result = {
                    "unified_summary": parsed_result,
                    "total_articles": total_articles,
                    "processing_time_ms": processing_time_ms,
                    "model_version": self.config.model_name
                }
                self.logger.info(f"一括統合要約完了 ({processing_time_ms}ms)")
                return result
            else:
                self.logger.error("統合要約の解析に失敗")
                return None
                
        except Exception as e:
            self.logger.error(f"🚨 一括統合要約エラー: {e}")
            print(f"🚨 UNIFIED SUMMARY FAILED: {e}")
            return None
    
    def generate_global_summary(self, all_articles: List[Dict[str, Any]], 
                              regional_summaries: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        全体市況要約を生成
        
        Args:
            all_articles (List[Dict]): 全記事のリスト
            regional_summaries (Dict): 地域別要約データ
        
        Returns:
            Optional[Dict[str, Any]]: 全体要約結果、失敗時はNone
        """
        start_time = time.time()
        self.logger.info(f"全体要約生成開始 (記事数: {len(all_articles)}, 地域数: {len(regional_summaries)})")
        
        try:
            prompt = self._build_global_prompt(all_articles, regional_summaries)
            self.logger.info(f"全体要約プロンプト生成完了: {len(prompt)}文字")
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=3072,
                    temperature=0.3,
                ),
                request_options={"timeout": 90}  # 90秒タイムアウト
            )
            
            if not response:
                raise Exception("Gemini APIからレスポンスが返されませんでした")
            
            if not hasattr(response, 'text') or not response.text:
                raise Exception(f"Gemini APIレスポンスにテキストが含まれていません: {response}")
            
            self.logger.info(f"全体要約Gemini APIレスポンス受信: {len(response.text)}文字")
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # レスポンスからテキストを抽出
            summary_text = self._extract_summary_text(response.text)
            
            if summary_text:
                result = {
                    "summary_text": summary_text,
                    "articles_count": len(all_articles),
                    "processing_time_ms": processing_time_ms,
                    "model_version": self.config.model_name
                }
                self.logger.info(f"全体要約完了 ({len(summary_text)}字, {processing_time_ms}ms)")
                return result
            else:
                self.logger.error("全体要約テキストの抽出に失敗")
                return None
                
        except Exception as e:
            self.logger.error(f"全体要約生成エラー: {e}")
            return None
    
    def _build_regional_prompt(self, region: str, articles: List[Dict[str, Any]]) -> str:
        """地域別要約用プロンプトを構築"""
        region_names = {
            "japan": "日本",
            "usa": "米国", 
            "china": "中国",
            "europe": "欧州",
            "other": "その他地域"
        }
        
        region_ja = region_names.get(region, region)
        
        # 記事データを整理
        article_summaries = []
        for i, article in enumerate(articles, 1):
            summary = article.get("summary", "").strip()
            title = article.get("title", "").strip()
            category = article.get("category", "その他")
            
            article_summaries.append(f"{i}. 【{category}】{title}\n   要約: {summary}")
        
        articles_text = "\n\n".join(article_summaries)
        
        prompt = f"""
以下の{region_ja}に関する{len(articles)}件のニュース記事を分析し、地域別の統合要約を400-600字で作成してください。

## 要約作成の指針
1. **主要トレンド**: {region_ja}市場の主要な動向と特徴
2. **重要な発表**: 経済指標、政策発表、企業業績等の重要な発表
3. **市場への影響**: 株価、為替、金利等への具体的な影響
4. **地域特有の課題**: {region_ja}特有の経済課題や機会

## 記事データ
{articles_text}

## 出力形式
400-600字の統合要約文を作成してください。専門用語は適度に使用し、市場関係者にとって有用で読みやすい内容にしてください。
"""
        return prompt
    
    def _build_global_prompt(self, all_articles: List[Dict[str, Any]], 
                           regional_summaries: Dict[str, Dict[str, Any]]) -> str:
        """全体要約用プロンプトを構築"""
        
        # 地域別要約をまとめる
        regional_text = []
        for region, summary_data in regional_summaries.items():
            region_names = {
                "japan": "日本",
                "usa": "米国",
                "china": "中国", 
                "europe": "欧州",
                "other": "その他地域"
            }
            region_ja = region_names.get(region, region)
            summary = summary_data.get("summary_text", "")
            article_count = summary_data.get("articles_count", 0)
            
            regional_text.append(f"### {region_ja}市況 ({article_count}記事)\n{summary}")
        
        regional_summaries_text = "\n\n".join(regional_text)
        
        # カテゴリ別統計
        category_counts = {}
        for article in all_articles:
            category = article.get("category", "その他")
            category_counts[category] = category_counts.get(category, 0) + 1
        
        category_stats = ", ".join([f"{cat}: {count}件" for cat, count in category_counts.items()])
        
        prompt = f"""
以下のグローバル市況データを分析し、全体市況の統合要約を800-1000字で作成してください。

## 分析データ
- **総記事数**: {len(all_articles)}件
- **カテゴリ別**: {category_stats}
- **分析対象地域**: {', '.join(regional_summaries.keys())}

## 地域別要約
{regional_summaries_text}

## 要約作成の指針
1. **グローバルトレンド**: 世界市場全体の主要な動向と方向性
2. **地域間相互作用**: 各地域市場間の相互影響と波及効果
3. **セクター分析**: 業界・分野別の注目すべき動向
4. **リスクと機会**: 市場参加者が注意すべきリスクと投資機会
5. **今後の見通し**: 短期的な市場予測と注目ポイント

## 出力形式
800-1000字の総合市況レポートを作成してください。投資家・市場関係者にとって実用的で洞察に富んだ内容にしてください。
"""
        return prompt
    
    def _build_unified_prompt(self, grouped_articles: Dict[str, List[Dict[str, Any]]]) -> str:
        """一括統合要約用プロンプトを構築（記事関連性を考慮）"""
        
        total_articles = sum(len(articles) for articles in grouped_articles.values())
        
        prompt = f"""あなたは金融・経済分野の専門アナリストです。
以下の {total_articles} 件の記事を分析し、地域間の関連性や相互影響を考慮した包括的な市場分析を提供してください。

【分析対象記事（地域別）】
"""
        
        # 地域別記事を整理
        for region, articles in grouped_articles.items():
            region_names = {
                "japan": "日本", "usa": "米国", "china": "中国", 
                "europe": "欧州", "asia": "アジア", "global": "グローバル", "other": "その他"
            }
            region_ja = region_names.get(region, region)
            
            prompt += f"\n■ {region_ja}地域 ({len(articles)}件)\n"
            
            for i, article in enumerate(articles, 1):
                title = article.get("title", "").strip()
                summary = article.get("summary", "").strip()
                category = article.get("category", "その他")
                
                prompt += f"{i}. 【{category}】{title}\n   {summary}\n"
        
        prompt += f"""

【分析要求】
以下の構造で包括的な分析を提供してください：

## 地域別要約
各地域の主要動向と重要ポイントを簡潔に要約

## グローバル市場概況
全体的な市場動向と主要テーマの総括

## 地域間相互影響分析
各地域の動向が他地域に与える影響や関連性

## 注目トレンド
記事全体から読み取れる重要な市場トレンドや将来の展望

## リスク要因
市場に影響を与える可能性のあるリスク要因の特定

回答は日本語で、各セクション300文字程度で簡潔かつ分かりやすく記述してください。
専門用語は適度に使用し、一般投資家にも理解しやすい表現を心がけてください。"""

        return prompt
    
    def _parse_unified_response(self, response_text: str) -> Optional[Dict[str, str]]:
        """統合要約レスポンスを解析してセクション別に分割"""
        if not response_text:
            return None
        
        # セクション分割
        sections = {}
        current_section = None
        current_content = []
        
        lines = response_text.split('\n')
        
        section_headers = {
            '地域別要約': 'regional_summaries',
            'グローバル市場概況': 'global_overview', 
            '地域間相互影響分析': 'cross_regional_analysis',
            '注目トレンド': 'key_trends',
            'リスク要因': 'risk_factors'
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # セクションヘッダーを検出
            header_found = False
            for header, key in section_headers.items():
                if header in line and ('##' in line or '■' in line or '●' in line):
                    # 前のセクションを保存
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    
                    current_section = key
                    current_content = []
                    header_found = True
                    break
            
            if not header_found and current_section:
                current_content.append(line)
        
        # 最後のセクションを保存
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        # セクションが見つからない場合は全体をglobal_overviewとして扱う
        if not sections:
            sections['global_overview'] = response_text.strip()
        
        return sections if sections else None
    
    def _extract_summary_text(self, response_text: str) -> Optional[str]:
        """レスポンステキストから要約部分を抽出"""
        if not response_text:
            return None
        
        # 不要な前後の装飾を除去
        text = response_text.strip()
        
        # ```markdown などのコードブロックがある場合は除去
        text = re.sub(r"```[a-zA-Z]*\n(.*?)\n```", r"\1", text, flags=re.DOTALL)
        
        # 最終的なテキストを返す
        return text.strip() if text.strip() else None


def create_integrated_summaries(api_key: str, grouped_articles: Dict[str, List[Dict[str, Any]]], 
                               config: ProSummaryConfig = None) -> Optional[Dict[str, Any]]:
    """
    統合要約を作成するメイン関数
    
    Args:
        api_key (str): Gemini APIキー
        grouped_articles (Dict): 地域別グループ化された記事
        config (ProSummaryConfig): 設定
    
    Returns:
        Optional[Dict[str, Any]]: 統合要約結果、失敗時はNone
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 記事数チェック
        total_articles = sum(len(articles) for articles in grouped_articles.values())
        if config and total_articles < config.min_articles_threshold:
            logger.warning(f"記事数が閾値未満です ({total_articles} < {config.min_articles_threshold})")
            return None
        
        # Pro Summarizerを初期化
        summarizer = ProSummarizer(api_key, config)
        
        # 地域別要約生成
        regional_summaries = summarizer.generate_regional_summaries(grouped_articles)
        
        if not regional_summaries:
            logger.error("地域別要約の生成に失敗しました")
            return None
        
        # 全記事をフラット化
        all_articles = []
        for articles in grouped_articles.values():
            all_articles.extend(articles)
        
        # 全体要約生成
        global_summary = summarizer.generate_global_summary(all_articles, regional_summaries)
        
        if not global_summary:
            logger.error("全体要約の生成に失敗しました")
            return None
        
        # 統計情報を整理
        articles_by_region = {region: len(articles) for region, articles in grouped_articles.items()}
        
        result = {
            "global_summary": global_summary,
            "regional_summaries": regional_summaries,
            "metadata": {
                "total_articles": total_articles,
                "articles_by_region": articles_by_region,
                "processing_timestamp": datetime.utcnow().isoformat()
            }
        }
        
        logger.info(f"統合要約生成完了: 全体1件, 地域別{len(regional_summaries)}件")
        return result
        
    except Exception as e:
        logger.error(f"統合要約生成中にエラーが発生: {e}")
        return None


if __name__ == '__main__':
    # テスト用コード
    from dotenv import load_dotenv
    load_dotenv()
    
    test_api_key = os.getenv("GEMINI_API_KEY")
    if not test_api_key:
        raise ValueError("環境変数 'GEMINI_API_KEY' が設定されていません。")
    
    # テスト用の記事データ
    test_grouped_articles = {
        "japan": [
            {
                "title": "日銀、政策金利据え置き決定",
                "summary": "日本銀行は金融政策決定会合で政策金利を据え置き、緩和的な金融政策を継続することを決定した。",
                "category": "金融政策"
            },
            {
                "title": "トヨタ自動車、増益を発表",
                "summary": "トヨタ自動車は四半期決算で前年同期比増益を発表、海外販売が好調だった。",
                "category": "企業業績"
            }
        ],
        "usa": [
            {
                "title": "FRB、利上げを検討",
                "summary": "米連邦準備制度理事会は次回会合での利上げ実施を示唆、インフレ抑制を優先する姿勢。",
                "category": "金融政策"
            }
        ]
    }
    
    print("--- Pro統合要約テスト ---")
    config = ProSummaryConfig(min_articles_threshold=2)
    result = create_integrated_summaries(test_api_key, test_grouped_articles, config)
    
    if result:
        print(f"\n=== 全体要約 ===")
        print(f"文字数: {len(result['global_summary']['summary_text'])}字")
        print(f"内容: {result['global_summary']['summary_text'][:100]}...")
        
        print(f"\n=== 地域別要約 ===")
        for region, summary_data in result['regional_summaries'].items():
            print(f"{region}: {len(summary_data['summary_text'])}字")
            print(f"  {summary_data['summary_text'][:50]}...")
        
        print(f"\n=== メタデータ ===")
        print(f"総記事数: {result['metadata']['total_articles']}")
        print(f"地域別: {result['metadata']['articles_by_region']}")
    else:
        print("テストに失敗しました。")