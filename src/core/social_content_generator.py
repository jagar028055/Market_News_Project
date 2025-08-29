"""
ソーシャルコンテンツ生成モジュール
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
import pytz
import json
from pathlib import Path

from src.logging_config import log_with_context
from src.personalization.topic_selector import TopicSelector
from src.renderers.markdown_renderer import MarkdownRenderer
from src.renderers.image_renderer import ImageRenderer
from src.config.app_config import AppConfig
from src.core.llm_content_optimizer import LLMContentOptimizer
from src.core.gdocs_manual_curator import GoogleDocsManualCurator


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
        
        # LLM最適化エンジン
        self.llm_optimizer = LLMContentOptimizer()
        
        # Google Docs手動キュレーション
        self.gdocs_curator = GoogleDocsManualCurator()
    
    def generate_social_content(self, articles: List[Dict[str, Any]], integrated_summary_override: str = None):
        """ソーシャルコンテンツ（画像・note記事）を生成"""
        try:
            now_jst = datetime.now(pytz.timezone('Asia/Tokyo'))
            
            log_with_context(
                self.logger,
                logging.INFO,
                f"ソーシャルコンテンツ生成開始 (記事数: {len(articles)}件)",
                operation="social_content_generation",
            )
            
            # Google Docs手動キュレーション済みコンテンツをチェック
            manual_content = None
            if self.config.social.generation_mode in ["manual", "hybrid"]:
                manual_content = self.gdocs_curator.check_for_manual_content(now_jst)
                if manual_content:
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"手動キュレーション済みコンテンツを検出: {manual_content['document_name']}",
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

            # 選定トピックをJSONで保存（再現性確保）
            try:
                date_str = now_jst.strftime('%Y%m%d')
                logs_dir = Path("logs") / "social" / date_str
                logs_dir.mkdir(parents=True, exist_ok=True)
                topics_path = logs_dir / "topics.json"
                
                print(f"DEBUG: トピックJSON保存先: {topics_path}")
                print(f"DEBUG: 選定されたトピック数: {len(topics)}")
                if topics:
                    print(f"DEBUG: 最初のトピック: {topics[0].headline}")

                topics_payload = [
                    {
                        "headline": t.headline,
                        "blurb": t.blurb,
                        "url": t.url,
                        "source": t.source,
                        "score": t.score,
                        "published_jst": t.published_jst.isoformat(),
                        "category": t.category,
                        "region": t.region,
                    }
                    for t in topics
                ]
                with open(topics_path, "w", encoding="utf-8") as f:
                    json.dump({"date": now_jst.strftime('%Y-%m-%d'), "topics": topics_payload}, f, ensure_ascii=False, indent=2)

                log_with_context(
                    self.logger,
                    logging.INFO,
                    f"トピックJSONを保存: {topics_path}",
                    operation="social_content_generation",
                )
            except Exception as e:
                import traceback
                print(f"DEBUG: トピックJSON保存エラーの詳細:")
                print(f"  エラーメッセージ: {e}")
                print(f"  スタックトレース:")
                traceback.print_exc()
                log_with_context(
                    self.logger,
                    logging.WARNING,
                    f"トピックJSON保存に失敗: {e}",
                    operation="social_content_generation",
                )
            
            # 出力ディレクトリの設定
            date_str = now_jst.strftime('%Y%m%d')
            social_output_dir = f"{self.config.social.output_base_dir}/social/{date_str}"
            note_output_dir = f"{self.config.social.output_base_dir}/note"
            
            # 統合要約を取得（あれば使用）
            # Pro統合要約が渡された場合は優先採用
            integrated_summary = integrated_summary_override or self._get_integrated_summary_text(articles)

            # 指標データをロード（存在すれば使用）
            indicators = self._load_indicators(now_jst)
            if not indicators:
                # フォールバック: 直接取得して保存
                try:
                    from src.indicators.fetcher import fetch_indicators
                    fetched = fetch_indicators()
                    if fetched:
                        ind_dir = Path(self.config.social.output_base_dir) / 'indicators'
                        ind_dir.mkdir(parents=True, exist_ok=True)
                        ind_path = ind_dir / f"{now_jst.strftime('%Y%m%d')}.json"
                        import json
                        with open(ind_path, 'w', encoding='utf-8') as f:
                            json.dump(fetched, f, ensure_ascii=False, indent=2)
                        indicators = fetched
                        log_with_context(
                            self.logger,
                            logging.INFO,
                            f"指標データをオンライン取得して保存: {ind_path}",
                            operation="social_content_generation",
                        )
                except Exception as e:
                    log_with_context(
                        self.logger,
                        logging.WARNING,
                        f"指標データのオンライン取得に失敗: {e}",
                        operation="social_content_generation",
                    )
            
            # note記事生成（LLM最適化対応）
            if self.config.social.enable_note_md:
                try:
                    note_content = None
                    
                    # 手動キュレーション済みコンテンツが最優先
                    if manual_content and 'note_article' in manual_content['content']:
                        note_content = manual_content['content']['note_article']
                        log_with_context(
                            self.logger,
                            logging.INFO,
                            "手動キュレーション済みnote記事を使用",
                            operation="social_content_generation",
                        )
                    # LLM最適化が有効な場合はLLMで記事生成
                    elif self.config.social.enable_llm_optimization:
                        topics_data = [
                            {
                                'headline': t.headline,
                                'blurb': t.blurb,
                                'source': t.source,
                                'category': t.category,
                                'region': t.region
                            }
                            for t in topics
                        ]
                        
                        note_content = self.llm_optimizer.generate_note_article(
                            date=now_jst,
                            topics=topics_data,
                            market_summary="",  # 今後市場概況データを追加予定
                            integrated_summary=integrated_summary
                        )
                        
                        if note_content:
                            log_with_context(
                                self.logger,
                                logging.INFO,
                                "LLM最適化によるnote記事生成完了",
                                operation="social_content_generation",
                            )
                    
                    # LLM生成に失敗した場合は従来のテンプレート方式にフォールバック
                    if not note_content:
                        log_with_context(
                            self.logger,
                            logging.INFO,
                            "従来のテンプレート方式でnote記事生成",
                            operation="social_content_generation",
                        )
                    
                    note_file = self.markdown_renderer.render(
                        date=now_jst,
                        topics=topics,
                        integrated_summary=integrated_summary,
                        output_dir=note_output_dir,
                        llm_generated_content=note_content
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
                        hashtags=self.config.social.hashtags,
                        subtitle="本日のハイライト",
                        # 右側に簡易テーブル（上位6件）
                        # Noneの場合は従来のプレースホルダーを描画
                        indicators=indicators[:6] if indicators else None,
                    )
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"SNS画像生成完了: {image_file}",
                        operation="social_content_generation",
                    )

                    # 2枚目（詳細）
                    image_file2 = self.image_renderer.render_16x9_details(
                        date=now_jst,
                        title=title,
                        topics=topics,
                        output_dir=social_output_dir,
                        brand_name=self.config.social.brand_name,
                        website_url=self.config.social.website_url,
                        hashtags=self.config.social.hashtags,
                        subtitle="注目トピック詳細",
                    )
                    log_with_context(
                        self.logger,
                        logging.INFO,
                        f"SNS画像生成完了(2枚目): {image_file2}",
                        operation="social_content_generation",
                    )

                    # 3枚目（Pro統合要約）
                    if integrated_summary:
                        image_file3 = self.image_renderer.render_16x9_summary(
                            date=now_jst,
                            title=title,
                            summary_text=integrated_summary,
                            output_dir=social_output_dir,
                            brand_name=self.config.social.brand_name,
                            website_url=self.config.social.website_url,
                            hashtags=self.config.social.hashtags,
                            subtitle="Pro統合要約",
                        )
                        log_with_context(
                            self.logger,
                            logging.INFO,
                            f"SNS画像生成完了(3枚目: Pro要約): {image_file3}",
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

    def _load_indicators(self, now_jst: datetime) -> List[Dict[str, Any]]:
        """主要指標データをロード（存在すれば使用）
        期待形式: [{"name":"NKY","value":"40,123","change":"+123","pct":"+0.31%"}, ...]
        探索順: build/indicators/YYYYMMDD.json -> data/indicators/YYYYMMDD.json
        """
        import json
        date_key = now_jst.strftime('%Y%m%d')
        candidates = [
            Path(self.config.social.output_base_dir) / 'indicators' / f'{date_key}.json',
            Path('data') / 'indicators' / f'{date_key}.json',
        ]
        for p in candidates:
            try:
                if p.exists():
                    with open(p, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            return data
                        if isinstance(data, dict) and 'indicators' in data:
                            return data['indicators']
            except Exception:
                continue
        return []
