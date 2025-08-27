"""
ソーシャルコンテンツ生成モジュール
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
import pytz

from src.logging_config import log_with_context
from src.personalization.topic_selector import TopicSelector
from src.renderers.markdown_renderer import MarkdownRenderer
from src.renderers.image_renderer import ImageRenderer
from src.config.app_config import AppConfig


class SocialContentGenerator:
    """ソーシャルコンテンツ生成器"""
    
    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        # コンポーネントを初期化
        self.topic_selector = TopicSelector()
        self.markdown_renderer = MarkdownRenderer()
        self.image_renderer = ImageRenderer(
            width=self.config.social.image_width,
            height=self.config.social.image_height,
            margin=self.config.social.image_margin,
            background_color=self.config.social.background_color,
            text_color=self.config.social.text_color,
            accent_color=self.config.social.accent_color,
            sub_accent_color=self.config.social.sub_accent_color
        )
    
    def generate_social_content(self, articles: List[Dict[str, Any]]):
        """ソーシャルコンテンツ（画像・note記事）を生成"""
        try:
            now_jst = datetime.now(pytz.timezone('Asia/Tokyo'))
            
            log_with_context(
                self.logger,
                logging.INFO,
                f"ソーシャルコンテンツ生成開始 (記事数: {len(articles)}件)",
                operation="social_content_generation",
            )
            
            # トピック選定
            topics = self.topic_selector.select_top(articles, k=3, now_jst=now_jst)
            
            if not topics:
                log_with_context(
                    self.logger,
                    logging.WARNING,
                    "トピック選定で対象記事が0件のため、ソーシャルコンテンツ生成をスキップ",
                    operation="social_content_generation",
                )
                return
            
            log_with_context(
                self.logger,
                logging.INFO,
                f"トピック選定完了: {len(topics)}件のトピックを選定",
                operation="social_content_generation",
            )
            
            # 出力ディレクトリの設定
            date_str = now_jst.strftime('%Y%m%d')
            social_output_dir = f"{self.config.social.output_base_dir}/social/{date_str}"
            note_output_dir = f"{self.config.social.output_base_dir}/note"
            
            # 統合要約を取得（あれば使用）
            integrated_summary = self._get_integrated_summary_text(articles)
            
            # note記事生成
            if self.config.social.enable_note_md:
                try:
                    note_file = self.markdown_renderer.render(
                        date=now_jst,
                        topics=topics,
                        integrated_summary=integrated_summary,
                        output_dir=note_output_dir
                    )
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"note記事生成完了: {note_file}",
                        operation="social_content_generation",
                    )
                except Exception as e:
                    log_with_context(
                        self.logger,
                        logging.ERROR,
                        f"note記事生成エラー: {e}",
                        operation="social_content_generation",
                        exc_info=True,
                    )
            
            # SNS画像生成
            if self.config.social.enable_social_images:
                try:
                    title = f"マーケットニュース {now_jst.strftime('%Y/%m/%d')}"
                    image_file = self.image_renderer.render_16x9(
                        date=now_jst,
                        title=title,
                        topics=topics,
                        output_dir=social_output_dir,
                        brand_name=self.config.social.brand_name,
                        website_url=self.config.social.website_url,
                        hashtags=self.config.social.hashtags
                    )
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"SNS画像生成完了: {image_file}",
                        operation="social_content_generation",
                    )
                except Exception as e:
                    log_with_context(
                        self.logger,
                        logging.ERROR,
                        f"SNS画像生成エラー: {e}",
                        operation="social_content_generation",
                        exc_info=True,
                    )
            
            log_with_context(
                self.logger,
                logging.INFO,
                "ソーシャルコンテンツ生成完了",
                operation="social_content_generation",
            )
            
        except Exception as e:
            log_with_context(
                self.logger,
                logging.ERROR,
                f"ソーシャルコンテンツ生成で予期せぬエラー: {e}",
                operation="social_content_generation",
                exc_info=True,
            )
            raise
    
    def _get_integrated_summary_text(self, articles: List[Dict[str, Any]]) -> str:
        """統合要約テキストを取得（あれば使用、なければデフォルト）"""
        # 簡単な統合要約を生成
        if not articles:
            return "本日は主要なニュースがありませんでした。"
        
        # 上位記事のタイトルを組み合わせて簡易要約を作成
        top_articles = articles[:5]
        summary_parts = []
        
        for article in top_articles:
            title = article.get('title', '')
            if title:
                # タイトルを短縮
                short_title = title[:50] + "..." if len(title) > 50 else title
                summary_parts.append(short_title)
        
        if summary_parts:
            summary = "本日の主要ニュースでは、" + "、".join(summary_parts[:3]) + "などの動きが見られました。"
        else:
            summary = "本日の市場動向についてお伝えします。"
        
        return summary