# -*- coding: utf-8 -*-

"""
改善されたHTMLジェネレーター
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .template_engine import HTMLTemplateEngine, TemplateData
from ..error_handling import HTMLGenerationError, error_context


class HTMLGenerator:
    """HTMLファイル生成器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.template_engine = HTMLTemplateEngine()
    
    def generate_html_file(
        self,
        articles: List[Dict[str, Any]],
        output_path: str = "index.html",
        title: str = "Market News Dashboard - AIニュース分析"
    ) -> None:
        """
        HTMLファイルの生成
        
        Args:
            articles: 記事データリスト
            output_path: 出力ファイルパス
            title: ページタイトル
        """
        with error_context("html_generation", "HTMLGenerator", self.logger):
            # 統計計算
            stats = self._calculate_statistics(articles)
            
            # 最終更新時刻計算
            last_updated = self._calculate_last_updated(articles)
            
            # テンプレートデータ作成
            template_data = TemplateData(
                title=title,
                articles=articles,
                total_articles=len(articles),
                last_updated=last_updated,
                sentiment_stats=stats['sentiment'],
                source_stats=stats['source']
            )
            
            # HTML生成
            html_content = self.template_engine.generate_html(template_data)
            
            # ファイル出力
            self._write_html_file(html_content, output_path)
            
            self.logger.info(f"HTMLファイルが正常に生成されました: {output_path}")
    
    def _calculate_statistics(self, articles: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
        """統計情報の計算"""
        source_stats = {}
        sentiment_stats = {'Positive': 0, 'Negative': 0, 'Neutral': 0, 'Error': 0}
        
        for article in articles:
            # ソース統計
            source = article.get('source', 'Unknown')
            source_stats[source] = source_stats.get(source, 0) + 1
            
            # 感情統計
            sentiment = article.get('sentiment_label', 'Neutral')
            if sentiment in sentiment_stats:
                sentiment_stats[sentiment] += 1
            else:
                sentiment_stats['Neutral'] += 1
        
        return {
            'source': source_stats,
            'sentiment': sentiment_stats
        }
    
    def _calculate_last_updated(self, articles: List[Dict[str, Any]]) -> str:
        """最終更新時刻の計算"""
        if not articles:
            return "N/A"
        
        try:
            latest_time = max(
                (article.get('published_jst') for article in articles if article.get('published_jst')),
                default=None
            )
            
            if latest_time and hasattr(latest_time, 'strftime'):
                return latest_time.strftime('%Y-%m-%d %H:%M')
            else:
                return str(latest_time) if latest_time else "N/A"
        except Exception as e:
            self.logger.warning(f"最終更新時刻の計算でエラー: {e}")
            return "N/A"
    
    def _write_html_file(self, html_content: str, output_path: str) -> None:
        """HTMLファイルの書き込み"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception as e:
            raise HTMLGenerationError(f"HTMLファイルの書き込みに失敗しました: {e}")
    
    def validate_articles(self, articles: List[Dict[str, Any]]) -> List[str]:
        """記事データの検証"""
        errors = []
        
        for i, article in enumerate(articles):
            if not isinstance(article, dict):
                errors.append(f"記事 {i}: 辞書形式ではありません")
                continue
            
            # 必須フィールドのチェック
            required_fields = ['title', 'url', 'summary']
            for field in required_fields:
                if not article.get(field):
                    errors.append(f"記事 {i}: {field} が不足しています")
            
            # URLの基本チェック
            url = article.get('url')
            if url and not (url.startswith('http://') or url.startswith('https://')):
                errors.append(f"記事 {i}: 不正なURL形式: {url}")
        
        return errors