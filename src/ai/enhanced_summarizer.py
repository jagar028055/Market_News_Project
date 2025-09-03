# -*- coding: utf-8 -*-

"""
拡張AI要約処理システム
独立ワークフロー専用のAI記事処理機能

従来のai_summarizer.pyとは独立して動作し、
マーケットデータ統合機能を含む高度な記事分析を提供
"""

import google.generativeai as genai
import os
import json
import re
import time
from typing import Optional, Dict, Any, List
import logging
from dataclasses import dataclass
from datetime import datetime

# 独立設定読み込み
from enhanced_content_config import CONFIG

@dataclass
class EnhancedSummaryResult:
    """拡張要約処理結果"""
    summary: str
    category: str
    region: str
    sentiment: str
    market_impact: str
    key_points: List[str]
    market_context_applied: bool
    processing_time: float
    quality_score: float
    warnings: List[str]

class EnhancedAISummarizer:
    """拡張AI要約処理システム"""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model_name: Optional[str] = None,
                 logger: Optional[logging.Logger] = None):
        """
        初期化
        
        Args:
            api_key: Gemini APIキー
            model_name: 使用するモデル名
            logger: ロガー
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or CONFIG.GEMINI_MODEL_NAME
        self.logger = logger or logging.getLogger(__name__)
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY が設定されていません")
        
        # Gemini設定
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        # マーケットデータフェッチャー（遅延初期化）
        self._market_fetcher = None
        
        self.logger.info(f"拡張AI要約処理システム初期化完了: {self.model_name}")
    
    @property
    def market_fetcher(self):
        """MarketDataFetcher の遅延初期化"""
        if self._market_fetcher is None:
            try:
                from src.market_data.fetcher import MarketDataFetcher
                self._market_fetcher = MarketDataFetcher(logger=self.logger)
                self.logger.info("MarketDataFetcher 初期化成功")
            except ImportError as e:
                self.logger.warning(f"MarketDataFetcher 初期化失敗: {e}")
                self._market_fetcher = None
        return self._market_fetcher
    
    def process_article_enhanced(self, 
                               text: str, 
                               title: Optional[str] = None,
                               market_context: Optional[str] = None) -> Optional[EnhancedSummaryResult]:
        """
        拡張記事処理
        
        Args:
            text: 記事本文
            title: 記事タイトル（任意）
            market_context: マーケットコンテキスト（任意、自動取得）
        
        Returns:
            EnhancedSummaryResult: 拡張要約結果
        """
        start_time = time.time()
        warnings = []
        
        # 入力検証
        if not text or len(text.strip()) < 50:
            self.logger.warning(f"記事本文が短すぎます (長さ: {len(text.strip()) if text else 0}文字)")
            return None
        
        try:
            # マーケットコンテキスト取得
            if not market_context and CONFIG.ENABLE_MARKET_CONTEXT:
                market_context = self._get_market_context()
                if not market_context:
                    warnings.append("マーケットデータ取得に失敗、標準処理を実行")
            
            # プロンプト生成
            prompt = self._build_enhanced_prompt(text, title, market_context)
            
            # AI処理実行
            response = self._generate_with_retry(prompt)
            if not response:
                return None
            
            # レスポンス解析
            result = self._parse_enhanced_response(response, market_context is not None)
            if not result:
                return None
            
            # 処理時間とメタデータ追加
            processing_time = time.time() - start_time
            
            return EnhancedSummaryResult(
                summary=result.get('summary', ''),
                category=result.get('category', 'その他'),
                region=result.get('region', 'global'),
                sentiment=result.get('sentiment', 'neutral'),
                market_impact=result.get('market_impact', 'limited'),
                key_points=result.get('key_points', []),
                market_context_applied=market_context is not None,
                processing_time=processing_time,
                quality_score=self._calculate_quality_score(result),
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.error(f"拡張記事処理でエラー: {e}", exc_info=True)
            return None
    
    def _get_market_context(self) -> Optional[str]:
        """マーケットコンテキスト取得"""
        if not self.market_fetcher:
            return None
        
        try:
            return self.market_fetcher.get_market_context_for_llm()
        except Exception as e:
            self.logger.warning(f"マーケットコンテキスト取得エラー: {e}")
            return None
    
    def _build_enhanced_prompt(self, 
                              text: str, 
                              title: Optional[str], 
                              market_context: Optional[str]) -> str:
        """拡張プロンプト構築"""
        
        # 基本プロンプト
        prompt = f"""あなたは金融・経済ニュースの専門分析者です。以下の記事を分析し、構造化されたマークダウン形式で出力してください。

【記事分析】
"""
        
        if title:
            prompt += f"タイトル: {title}\n"
        
        prompt += f"本文: {text}\n\n"
        
        # マーケットコンテキスト追加
        if market_context:
            prompt += f"""【現在の市場状況】
{market_context}

上記の市場状況を踏まえて記事を分析してください。
"""
        
        # 出力形式指定
        prompt += """
【出力形式】
以下のマークダウン形式で厳密に出力してください：

## 要約
[記事の要約を150-300字で記載]

## カテゴリ
[以下から選択: 金融政策, 市場動向, 企業業績, 経済指標, 地政学, 暗号資産, その他]

## 地域
[以下から選択: japan, usa, europe, asia, global, other]

## センチメント
[以下から選択: bullish, bearish, neutral]

## 市場への影響
[以下から選択: high, moderate, limited, unclear]

## 重要ポイント
- [ポイント1]
- [ポイント2]
- [ポイント3]

## 分析品質
[HIGH/MEDIUM/LOW]
"""
        
        if market_context:
            prompt += """
## 市場コンテキスト分析
[現在の市場状況と記事内容の関連性を分析]
"""
        
        return prompt
    
    def _generate_with_retry(self, prompt: str) -> Optional[str]:
        """リトライ機能付きAI生成"""
        max_retries = CONFIG.GEMINI_MAX_RETRIES
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=1500,
                        temperature=0.3,
                        top_p=0.9,
                    )
                )
                
                if response and response.text:
                    return response.text
                else:
                    self.logger.warning(f"空のレスポンス (試行 {attempt + 1}/{max_retries})")
                    
            except Exception as e:
                self.logger.warning(f"AI生成エラー (試行 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(CONFIG.API_RETRY_DELAY * (attempt + 1))
        
        return None
    
    def _parse_enhanced_response(self, response_text: str, has_market_context: bool) -> Optional[Dict[str, Any]]:
        """拡張レスポンス解析"""
        try:
            result = {}
            
            # マークダウンセクション抽出
            sections = self._extract_markdown_sections(response_text)
            
            # 要約抽出
            result['summary'] = sections.get('要約', '').strip()
            
            # カテゴリ抽出・正規化
            category_text = sections.get('カテゴリ', '').strip()
            result['category'] = self._normalize_category(category_text)
            
            # 地域抽出・正規化
            region_text = sections.get('地域', '').strip()
            result['region'] = self._normalize_region(region_text)
            
            # センチメント抽出・正規化
            sentiment_text = sections.get('センチメント', '').strip()
            result['sentiment'] = self._normalize_sentiment(sentiment_text)
            
            # 市場影響度抽出・正規化
            impact_text = sections.get('市場への影響', '').strip()
            result['market_impact'] = self._normalize_market_impact(impact_text)
            
            # 重要ポイント抽出
            points_text = sections.get('重要ポイント', '')
            result['key_points'] = self._extract_bullet_points(points_text)
            
            # 品質レベル抽出
            quality_text = sections.get('分析品質', '').strip().lower()
            result['quality_level'] = quality_text if quality_text in ['high', 'medium', 'low'] else 'medium'
            
            # 市場コンテキスト分析抽出（存在する場合）
            if has_market_context:
                result['market_context_analysis'] = sections.get('市場コンテキスト分析', '').strip()
            
            # 必須フィールド検証
            if not result.get('summary'):
                self.logger.error("要約が抽出できませんでした")
                return None
            
            return result
            
        except Exception as e:
            self.logger.error(f"レスポンス解析エラー: {e}")
            return None
    
    def _extract_markdown_sections(self, text: str) -> Dict[str, str]:
        """マークダウンセクション抽出"""
        sections = {}
        current_section = None
        current_content = []
        
        for line in text.split('\n'):
            line = line.strip()
            
            # セクションヘッダー検出（## で始まる行）
            if line.startswith('## '):
                # 前のセクションを保存
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # 新しいセクション開始
                current_section = line[3:].strip()
                current_content = []
            else:
                # セクション内容追加
                if current_section:
                    current_content.append(line)
        
        # 最後のセクション保存
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def _normalize_category(self, text: str) -> str:
        """カテゴリ正規化"""
        category_map = {
            '金融政策': '金融政策',
            '市場動向': '市場動向', 
            '企業業績': '企業業績',
            '経済指標': '経済指標',
            '地政学': '地政学',
            '暗号資産': '暗号資産',
            'その他': 'その他'
        }
        
        for key in category_map.keys():
            if key in text:
                return category_map[key]
        
        return 'その他'
    
    def _normalize_region(self, text: str) -> str:
        """地域正規化"""
        region_map = {
            'japan': 'japan',
            'usa': 'usa',
            'europe': 'europe', 
            'asia': 'asia',
            'global': 'global',
            'other': 'other'
        }
        
        text_lower = text.lower()
        for key in region_map.keys():
            if key in text_lower:
                return region_map[key]
        
        return 'global'
    
    def _normalize_sentiment(self, text: str) -> str:
        """センチメント正規化"""
        text_lower = text.lower()
        
        if 'bullish' in text_lower or '強気' in text:
            return 'bullish'
        elif 'bearish' in text_lower or '弱気' in text:
            return 'bearish'
        else:
            return 'neutral'
    
    def _normalize_market_impact(self, text: str) -> str:
        """市場影響度正規化"""
        text_lower = text.lower()
        
        if 'high' in text_lower or '高' in text:
            return 'high'
        elif 'moderate' in text_lower or '中' in text:
            return 'moderate'
        elif 'limited' in text_lower or '限定' in text or '低' in text:
            return 'limited'
        else:
            return 'unclear'
    
    def _extract_bullet_points(self, text: str) -> List[str]:
        """箇条書きポイント抽出"""
        points = []
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                points.append(line[2:].strip())
        
        return points[:5]  # 最大5つまで
    
    def _calculate_quality_score(self, result: Dict[str, Any]) -> float:
        """品質スコア計算"""
        score = 0.0
        
        # 要約品質（50点満点）
        summary = result.get('summary', '')
        if len(summary) >= 100:
            score += 30
        elif len(summary) >= 50:
            score += 20
        else:
            score += 10
        
        if len(summary) <= 500:  # 長すぎない
            score += 10
        
        if '。' in summary or '.' in summary:  # 適切な句読点
            score += 10
        
        # カテゴリ・地域の適切性（20点満点）
        if result.get('category') != 'その他':
            score += 10
        if result.get('region') != 'other':
            score += 10
        
        # キーポイントの質（20点満点）
        key_points = result.get('key_points', [])
        score += min(len(key_points) * 4, 20)
        
        # 品質レベル（10点満点）
        quality_level = result.get('quality_level', 'medium')
        if quality_level == 'high':
            score += 10
        elif quality_level == 'medium':
            score += 7
        else:
            score += 4
        
        return min(100.0, score)

def create_enhanced_summarizer(logger: Optional[logging.Logger] = None) -> EnhancedAISummarizer:
    """拡張AI要約処理システムのファクトリ関数"""
    try:
        return EnhancedAISummarizer(logger=logger)
    except ValueError as e:
        if logger:
            logger.error(f"拡張AI要約処理システム初期化失敗: {e}")
        raise

# 後方互換性のための関数（独立ワークフロー専用）
def process_article_enhanced(text: str, 
                           title: Optional[str] = None,
                           api_key: Optional[str] = None,
                           logger: Optional[logging.Logger] = None) -> Optional[Dict[str, Any]]:
    """
    独立ワークフロー用の記事処理関数
    
    Args:
        text: 記事本文
        title: 記事タイトル
        api_key: Gemini APIキー
        logger: ロガー
    
    Returns:
        Dict[str, Any]: 処理結果（EnhancedSummaryResult を辞書として返却）
    """
    try:
        summarizer = EnhancedAISummarizer(api_key=api_key, logger=logger)
        result = summarizer.process_article_enhanced(text, title)
        
        if result:
            return {
                'summary': result.summary,
                'category': result.category,
                'region': result.region,
                'sentiment': result.sentiment,
                'market_impact': result.market_impact,
                'key_points': result.key_points,
                'market_context_applied': result.market_context_applied,
                'processing_time': result.processing_time,
                'quality_score': result.quality_score,
                'warnings': result.warnings
            }
        else:
            return None
            
    except Exception as e:
        if logger:
            logger.error(f"拡張記事処理でエラー: {e}")
        return None