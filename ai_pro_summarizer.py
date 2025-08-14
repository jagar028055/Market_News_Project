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
                request_options={"timeout": 600}  # 600秒タイムアウト（10分）
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
    
    
    
    
    def _build_unified_prompt(self, grouped_articles: Dict[str, List[Dict[str, Any]]]) -> str:
        """統合要約用プロンプトを構築（地域間関連性分析を重視）"""
        
        total_articles = sum(len(articles) for articles in grouped_articles.values())
        
        prompt = f"""あなたはグローバル金融市場の专門アナリストです。
以下の{total_articles}件のニュース記事を分析し、地域間の相互関連性と影響を深く考慮した包括的な市場分析レポートを作成してください。

【分析対象ニュース】"""
        
        # 地域別記事を整理
        for region, articles in grouped_articles.items():
            region_names = {
                "japan": "日本", "usa": "米国", "china": "中国", 
                "europe": "欧州", "asia": "アジア", "global": "グローバル", "other": "その他"
            }
            region_ja = region_names.get(region, region)
            
            prompt += f"\n\n■■ {region_ja}市場 ({len(articles)}件)\n"
            
            for i, article in enumerate(articles, 1):
                title = article.get("title", "").strip()
                summary = article.get("summary", "").strip()
                category = article.get("category", "その他")
                
                prompt += f"{i}. 【{category}】{title}\n   要約: {summary}\n"
        
        prompt += f"""

【分析レポート構成】
以下の構造で、地域間の相互作用と波及効果を重視した総合分析を提供してください：

## 地域別市場概況
各地域の主要動向、重要指標、政策発表、企業業績などを簡潔に整理
(地域ごとに250-300文字程度)

## グローバル市場総括
世界全体の市場トレンド、セクター別動向、主要テーマを総合的に分析
(400-500文字程度)

## 地域間相互影響分析
**ここが最重要**: 各地域の動向が他地域に与える影響、相互関連性、波及効果を具体例で詳細分析
- 米国金融政策が他地域に与える影響
- 中国経済動向のグローバル波及
- 日本の政策変更がアジア地域に与える影響
- 欧州情勢の他地域への波及
(400-500文字程度)

## 注目トレンド・将来展望
記事全体から読み取れる重要な市場トレンド、技術進歩、政策方向性、今後の注目ポイント
(300-400文字程度)

## リスク要因・投資機会
短期・中期的なリスク要因、地政学的リスク、投資機会の特定
(250-300文字程度)

【出力指定】
- 各セクションは必ず "##" で開始し、明確に区分する
- 地域間相互影響分析を特に詳細に記述する
- 投資家・市場関係者にとって実用的な情報を提供
- 数値データや具体例を積極的に含める
- 日本語で分かりやすく記述する"""

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
            '地域別市場概況': 'regional_summaries',
            'グローバル市場総括': 'global_overview', 
            '地域間相互影響分析': 'cross_regional_analysis',
            '注目トレンド': 'key_trends',
            'リスク要因': 'risk_factors',
            '将来展望': 'future_outlook',
            '投資機会': 'investment_opportunities'
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
            # 基本セクションを確保
            sections['regional_summaries'] = '地域別情報が不十分です'
            sections['cross_regional_analysis'] = '地域間関連性の分析が不十分です'
        
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
    1回のAPI呼び出しで統合要約を作成するメイン関数（地域間関連性分析重視）
    
    Args:
        api_key (str): Gemini APIキー
        grouped_articles (Dict): 地域別グループ化された記事
        config (ProSummaryConfig): 設定
    
    Returns:
        Optional[Dict[str, Any]]: 統合要約結果（地域別+グローバル+関連性分析）、失敗時はNone
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
        
        # 1回API呼び出しで統合要約生成
        unified_result = summarizer.generate_unified_summary(grouped_articles)
        
        if not unified_result:
            logger.error("統合要約の生成に失敗しました")
            return None
        
        # 結果を整理
        articles_by_region = {region: len(articles) for region, articles in grouped_articles.items()}
        
        result = {
            "unified_summary": unified_result["unified_summary"],
            "metadata": {
                "total_articles": total_articles,
                "articles_by_region": articles_by_region,
                "processing_timestamp": datetime.utcnow().isoformat(),
                "processing_time_ms": unified_result.get("processing_time_ms", 0),
                "model_version": unified_result.get("model_version", "gemini-2.5-pro")
            }
        }
        
        logger.info(f"1回API呼び出し統合要約生成完了: {total_articles}件の記事を処理")
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
        print(f"\n=== 統合要約結果 ===")
        unified_summary = result['unified_summary']
        
        # 各セクションを表示
        for section_name, content in unified_summary.items():
            section_names = {
                'regional_summaries': '地域別市場概況',
                'global_overview': 'グローバル市場総括',
                'cross_regional_analysis': '地域間相互影響分析',
                'key_trends': '注目トレンド・将来展望',
                'risk_factors': 'リスク要因・投資機会'
            }
            display_name = section_names.get(section_name, section_name)
            print(f"\n--- {display_name} ---")
            print(f"文字数: {len(content)}字")
            print(f"内容: {content[:100]}...")
        
        print(f"\n=== メタデータ ===")
        print(f"総記事数: {result['metadata']['total_articles']}")
        print(f"地域別: {result['metadata']['articles_by_region']}")
        print(f"処理時間: {result['metadata']['processing_time_ms']}ms")
        print(f"モデル: {result['metadata']['model_version']}")
    else:
        print("テストに失敗しました。")