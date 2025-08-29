#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import google.generativeai as genai

from src.config.app_config import get_config


@dataclass
class OptimizedContent:
    """LLM最適化されたコンテンツ"""
    sns_text: str
    keywords: List[str]
    note_article: Optional[str] = None


class LLMContentOptimizer:
    """LLMを使用したSNS・記事コンテンツ最適化エンジン"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        
        # Gemini API設定
        if self.config.ai.gemini_api_key:
            genai.configure(api_key=self.config.ai.gemini_api_key)
            self.model = genai.GenerativeModel(
                model_name=self.config.ai.model_name,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.config.ai.max_output_tokens,
                    temperature=self.config.ai.temperature,
                )
            )
        else:
            self.model = None
            self.logger.warning("Gemini API key not configured - LLM optimization disabled")
    
    def optimize_for_sns(self, title: str, summary: str, category: str = "", region: str = "") -> Optional[OptimizedContent]:
        """記事要約をSNS投稿用に最適化"""
        if not self.model or not self.config.social.enable_llm_optimization:
            return None
        
        try:
            prompt = self.config.social.sns_optimization_prompt.format(
                title=title,
                summary=summary,
                category=category,
                region=region
            )
            
            self.logger.info(f"SNS最適化実行: {title[:50]}...")
            
            response = self.model.generate_content(prompt)
            
            if not response.text:
                self.logger.error("Gemini APIからレスポンスが取得できませんでした")
                return None
            
            # JSON形式の応答をパース
            try:
                result = json.loads(response.text.strip())
                return OptimizedContent(
                    sns_text=result.get("sns_text", ""),
                    keywords=result.get("keywords", [])
                )
            except json.JSONDecodeError as e:
                self.logger.error(f"Gemini応答のJSONパースに失敗: {e}")
                self.logger.debug(f"Raw response: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"SNS最適化中にエラーが発生: {e}")
            return None
    
    def generate_note_article(self, 
                            date: datetime, 
                            topics: List[Dict[str, Any]], 
                            market_summary: str = "", 
                            integrated_summary: str = "") -> Optional[str]:
        """note用の詳細記事を生成"""
        if not self.model or not self.config.social.enable_llm_optimization:
            return None
        
        try:
            # トピック情報を整形
            topics_text = []
            for i, topic in enumerate(topics[:3], 1):
                topic_info = f"{i}. {topic.get('headline', 'タイトル不明')}\n   概要: {topic.get('blurb', 'N/A')}\n   ソース: {topic.get('source', 'N/A')}"
                topics_text.append(topic_info)
            
            prompt = self.config.social.note_article_prompt.format(
                date=date.strftime("%Y年%m月%d日"),
                topics="\n".join(topics_text),
                market_summary=market_summary,
                integrated_summary=integrated_summary
            )
            
            self.logger.info(f"note記事生成実行: {date.strftime('%Y-%m-%d')}")
            
            # より長い記事用に出力トークン数を増やす
            model_config = genai.types.GenerationConfig(
                max_output_tokens=4096,  # note記事用に増量
                temperature=0.3,
            )
            
            response = self.model.generate_content(prompt, generation_config=model_config)
            
            if not response.text:
                self.logger.error("note記事生成でGemini APIからレスポンスが取得できませんでした")
                return None
            
            self.logger.info("note記事生成完了")
            return response.text.strip()
                
        except Exception as e:
            self.logger.error(f"note記事生成中にエラーが発生: {e}")
            return None
    
    def optimize_topic_for_sns(self, topic: Dict[str, Any]) -> Optional[OptimizedContent]:
        """単一トピックをSNS用に最適化"""
        return self.optimize_for_sns(
            title=topic.get('headline', ''),
            summary=topic.get('blurb', ''),
            category=topic.get('category', ''),
            region=topic.get('region', '')
        )
    
    def batch_optimize_topics(self, topics: List[Dict[str, Any]]) -> List[OptimizedContent]:
        """複数トピックを一括でSNS最適化"""
        optimized_content = []
        
        for topic in topics:
            optimized = self.optimize_topic_for_sns(topic)
            if optimized:
                optimized_content.append(optimized)
            else:
                # フォールバック: 元の内容をそのまま使用
                optimized_content.append(OptimizedContent(
                    sns_text=f"{topic.get('headline', '')} {self.config.social.hashtags}",
                    keywords=[]
                ))
        
        return optimized_content