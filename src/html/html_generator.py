# -*- coding: utf-8 -*-

"""
改善されたHTMLジェネレーター
"""
import os
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
        # HTMLファイルの完全クリア処理を強化
        self._ensure_clean_html_file(output_path)

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
                # sentiment_stats=stats['sentiment'],  # 感情分析機能を削除
                source_stats=stats['source']
            )
            
            # HTML生成
            html_content = self.template_engine.generate_html(template_data)
            
            # ファイル出力
            self._write_html_file(html_content, output_path)
            
            self.logger.info(f"HTMLファイルが正常に生成されました: {output_path} (記事数: {len(articles)}件)")
    
    def _ensure_clean_html_file(self, output_path: str) -> None:
        """
        HTMLファイルの完全クリア処理
        
        Args:
            output_path: 出力ファイルパス
        """
        try:
            # 既存ファイルが存在する場合は削除
            if os.path.exists(output_path):
                os.remove(output_path)
                self.logger.info(f"既存のHTMLファイルを削除しました: {output_path}")
            
            # 空のHTMLファイルを新規作成して、ファイルの存在を確認
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("")  # 空ファイル作成
            
            # ファイル作成の確認
            if os.path.exists(output_path):
                self.logger.info(f"新しいHTMLファイルを作成しました: {output_path}")
            else:
                raise HTMLGenerationError(f"HTMLファイルの作成に失敗: {output_path}")
                
        except Exception as e:
            raise HTMLGenerationError(f"HTMLファイルのクリア処理に失敗: {e}")
    
    def _calculate_statistics(self, articles: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
        """統計情報の計算"""
        source_stats = {}
        
        for article in articles:
            # ソース統計
            source = article.get('source', 'Unknown')
            source_stats[source] = source_stats.get(source, 0) + 1
        
        return {
            'source': source_stats
        }
    
    def _calculate_last_updated(self, articles: List[Dict[str, Any]]) -> str:
        """
        HTMLファイル生成時刻の計算（東京時間）
        注：記事の公開時刻ではなく、実際のHTMLファイル生成時刻を返す
        """
        try:
            import pytz
            # 東京時間で現在時刻を取得
            jst = pytz.timezone('Asia/Tokyo')
            current_time = datetime.now(jst)
            return current_time.strftime('%Y/%m/%d %H:%M')
        except Exception as e:
            self.logger.warning(f"更新時刻の計算でエラー: {e}")
            # フォールバック: UTCから東京時間に変換
            try:
                import pytz
                utc_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
                jst_time = utc_time.astimezone(pytz.timezone('Asia/Tokyo'))
                return jst_time.strftime('%Y/%m/%d %H:%M')
            except:
                # 最終フォールバック: システム時刻（注: これは東京時間でない可能性あり）
                return datetime.now().strftime('%Y/%m/%d %H:%M')
    
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