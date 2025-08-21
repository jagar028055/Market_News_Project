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
        
        # 記事数制限なし（全記事を統合要約に使用）
        try:
            prompt = self._build_unified_prompt(grouped_articles)
            self.logger.info(f"統合プロンプト生成完了: {len(prompt)}文字")
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=8192,  # 出力トークン数を倍増（地域間相互影響分析の完全性確保）
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
                # レスポンス完全性を検証
                validation_result = self._validate_response_completeness(parsed_result)
                
                result = {
                    "unified_summary": parsed_result,
                    "total_articles": total_articles,
                    "processing_time_ms": processing_time_ms,
                    "model_version": self.config.model_name,
                    "validation": validation_result  # 検証結果を追加
                }
                
                if validation_result['is_complete']:
                    self.logger.info(f"一括統合要約完了 ({processing_time_ms}ms) - 完全")
                else:
                    self.logger.warning(f"一括統合要約完了 ({processing_time_ms}ms) - 不完全: {validation_result['issues']}")
                
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
        
        # 地域別記事を整理（表示順序を調整：米国→欧州→日本→中国・新興国）
        region_order = ["usa", "europe", "japan", "china", "asia", "global", "other"]
        sorted_regions = sorted(grouped_articles.keys(), key=lambda x: region_order.index(x) if x in region_order else 999)
        
        for region in sorted_regions:
            articles = grouped_articles[region]
            region_names = {
                "japan": "日本", "usa": "米国", "china": "中国・その他新興国", 
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

【重要：HTMLテンプレート形式で出力してください】
以下のHTMLテンプレート構造に従って、地域間の相互作用と波及効果を重視した総合分析を提供してください：

## 地域別市場概況
以下のHTMLテンプレートに従って出力：
<div class="regional-summaries">
<div class="region-item">
<h4>米国市場</h4>
<p>[米国市場の分析内容]</p>
</div>
<div class="region-item">
<h4>欧州市場</h4>
<p>[欧州市場の分析内容]</p>
</div>
<div class="region-item">
<h4>日本市場</h4>
<p>[日本市場の分析内容]</p>
</div>
<div class="region-item">
<h4>中国・その他新興国市場</h4>
<p>[中国・新興国市場の分析内容]</p>
</div>
</div>

## グローバル市場総括
<div class="global-overview">
<p>[世界全体の市場トレンド、セクター別動向を400字程度で総合分析]</p>
</div>

## 地域間相互影響分析
<div class="cross-regional-analysis">
<div class="influence-item">
<h5>米国金融政策の影響</h5>
<p>[米国の政策が他地域に与える影響]</p>
</div>
<div class="influence-item">
<h5>中国経済のグローバル波及</h5>
<p>[中国経済動向の世界への影響]</p>
</div>
<div class="influence-item">
<h5>欧州・日本の市場動向</h5>
<p>[欧州・日本の動向と地域間相互作用]</p>
</div>
</div>

## 注目トレンド・将来展望
<div class="key-trends">
<p>[重要な市場トレンド、技術進歩、政策方向性を300字程度]</p>
</div>

## リスク要因・投資機会
<div class="risk-factors">
<div class="risk-item">
<h5>短期リスク要因</h5>
<p>[短期的なリスク要因の分析]</p>
</div>
<div class="risk-item">
<h5>投資機会</h5>
<p>[投資機会の特定]</p>
</div>
</div>

【出力指定】
- 必ず上記HTMLテンプレート構造に従って出力する
- 説明文や指示文は一切含めない（[内容]部分のみ実際の分析内容に置換）
- 投資家・市場関係者にとって実用的な情報を提供
- 数値データや具体例を積極的に含める
- 簡潔で読みやすい日本語で記述する"""

        return prompt
    
    def _parse_unified_response(self, response_text: str) -> Optional[Dict[str, str]]:
        """HTMLテンプレート構造での統合要約レスポンスを解析"""
        if not response_text:
            return None
        
        import re
        
        # HTMLテンプレート構造から各セクションを抽出
        sections = {}
        
        # 地域別市場概況
        regional_match = re.search(r'<div class="regional-summaries">(.*?)</div>(?=\s*##|\s*<div class="global-overview"|$)', response_text, re.DOTALL)
        if regional_match:
            sections['regional_summaries'] = regional_match.group(1).strip()
        
        # グローバル市場総括
        global_match = re.search(r'<div class="global-overview">(.*?)</div>(?=\s*##|\s*<div class="cross-regional-analysis"|$)', response_text, re.DOTALL)
        if global_match:
            sections['global_overview'] = global_match.group(1).strip()
        
        # 地域間相互影響分析
        cross_regional_match = re.search(r'<div class="cross-regional-analysis">(.*?)</div>(?=\s*##|\s*<div class="key-trends"|$)', response_text, re.DOTALL)
        if cross_regional_match:
            sections['cross_regional_analysis'] = cross_regional_match.group(1).strip()
        
        # 注目トレンド・将来展望
        trends_match = re.search(r'<div class="key-trends">(.*?)</div>(?=\s*##|\s*<div class="risk-factors"|$)', response_text, re.DOTALL)
        if trends_match:
            sections['key_trends'] = trends_match.group(1).strip()
        
        # リスク要因・投資機会
        risk_match = re.search(r'<div class="risk-factors">(.*?)</div>(?=\s*##|$)', response_text, re.DOTALL)
        if risk_match:
            sections['risk_factors'] = risk_match.group(1).strip()
        
        # フォールバック：従来のセクション分割も試行
        if not sections:
            return self._parse_traditional_response(response_text)
        
        return sections if sections else None
    
    def _parse_traditional_response(self, response_text: str) -> Optional[Dict[str, str]]:
        """従来形式のレスポンス解析（フォールバック用）"""
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
        
        return sections if sections else None
    
    def _validate_response_completeness(self, parsed_sections: Dict[str, str]) -> Dict[str, Any]:
        """レスポンスの完全性を検証
        
        Args:
            parsed_sections: 解析されたセクション辞書
            
        Returns:
            検証結果辞書
        """
        issues = []
        is_complete = True
        
        # 必須セクションの存在チェック
        required_sections = [
            'regional_summaries',
            'global_overview', 
            'cross_regional_analysis'
        ]
        
        for section in required_sections:
            if section not in parsed_sections:
                issues.append(f"必須セクション '{section}' が見つかりません")
                is_complete = False
                continue
                
            content = parsed_sections[section].strip()
            
            # 最低文字数チェック
            min_lengths = {
                'regional_summaries': 100,
                'global_overview': 100,
                'cross_regional_analysis': 50  # 地域間相互影響分析の最低文字数
            }
            
            min_length = min_lengths.get(section, 50)
            if len(content) < min_length:
                issues.append(f"セクション '{section}' の文字数が不足 ({len(content)}字 < {min_length}字)")
                is_complete = False
            
            # 切り詰められた可能性のチェック（不完全な文で終わっているか）
            if section == 'cross_regional_analysis':
                # 地域間相互影響分析の特別チェック
                if content.endswith('**') or content.endswith('- ') or content.endswith('**米国の通'):
                    issues.append("地域間相互影響分析が途中で切り詰められています")
                    is_complete = False
                elif len(content) < 200:  # 地域間相互影響分析は特に重要なので200字以上必要
                    issues.append(f"地域間相互影響分析の内容が短すぎます ({len(content)}字)")
                    is_complete = False
        
        return {
            'is_complete': is_complete,
            'issues': issues,
            'section_lengths': {section: len(content) for section, content in parsed_sections.items()}
        }
    
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