"""
HTMLテンプレート + Playwright を使用したSNS画像レンダラ
"""

import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright, Browser, Page

from ..personalization.topic_selector import Topic


class HTMLImageRenderer:
    """HTMLテンプレート + Playwright を使用したSNS画像生成器"""
    
    def __init__(
        self, 
        template_dir: str = "assets/templates/social",
        width: int = 1600,
        height: int = 900,
        margin: int = 20,
        background_color: str = "#f7f9fc",
        text_color: str = "#0f1724",
        accent_color: str = "#2eaadc",
        sub_accent_color: str = "#5c7cfa"
    ):
        """
        Args:
            template_dir: HTMLテンプレートディレクトリ
            width: 画像幅
            height: 画像高さ
            margin: マージン
            background_color: 背景色
            text_color: テキスト色
            accent_color: アクセント色
            sub_accent_color: サブアクセント色
        """
        self.template_dir = Path(template_dir)
        self.width = width
        self.height = height
        self.margin = margin
        self.background_color = background_color
        self.text_color = text_color
        self.accent_color = accent_color
        self.sub_accent_color = sub_accent_color
        
        # Jinja2環境を設定
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True
        )
        
        self.logger = logging.getLogger(__name__)
    
    async def render_16x9(
        self,
        date: datetime,
        title: str,
        topics: List[Topic],
        output_dir: str,
        brand_name: str = "Market News",
        website_url: str = "https://market-news.example.com",
        hashtags: str = "#MarketNews",
        subtitle: Optional[str] = "本日のハイライト",
        indicators: Optional[List[dict]] = None,
        slide_type: str = "market_recap"
    ) -> Path:
        """
        16:9 SNS画像を生成（HTMLテンプレート + Playwright）
        
        Args:
            date: 日付
            title: タイトル
            topics: トピック一覧
            output_dir: 出力ディレクトリ
            brand_name: ブランド名
            website_url: ウェブサイトURL
            hashtags: ハッシュタグ
            subtitle: サブタイトル
            indicators: 指標データ
            slide_type: スライドタイプ ("market_recap", "deep_dive_1", "deep_dive_2", "econ_calendar")
            
        Returns:
            生成された画像ファイルのパス
        """
        # 出力ディレクトリを作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # ファイル名を生成
        filename = f"news_{slide_type}_16x9.png"
        file_path = output_path / filename
        
        # テンプレートデータを準備
        template_data = self._prepare_template_data(
            date, title, topics, brand_name, website_url, 
            hashtags, subtitle, indicators, slide_type
        )
        
        # HTMLを生成
        html_content = await self._generate_html(template_data, slide_type)
        
        # スクリーンショットを撮影
        await self._take_screenshot(html_content, file_path, slide_type)
        
        return file_path
    
    def _prepare_template_data(
        self,
        date: datetime,
        title: str,
        topics: List[Topic],
        brand_name: str,
        website_url: str,
        hashtags: str,
        subtitle: Optional[str],
        indicators: Optional[List[dict]],
        slide_type: str
    ) -> Dict[str, Any]:
        """テンプレート用のデータを準備"""
        
        # 日付文字列を生成
        date_str = date.strftime('%Y-%m-%d (%a)')
        
        # ハッシュタグをリストに変換
        hashtag_list = [tag.strip() for tag in hashtags.split() if tag.strip()]
        
        # 指標データを整形
        formatted_indicators = []
        if indicators:
            for indicator in indicators[:8]:  # 最大8件
                formatted_indicators.append({
                    'name': indicator.get('name', '—'),
                    'value': indicator.get('value', '—'),
                    'change': indicator.get('change', '—'),
                    'change_pct': indicator.get('pct', None),
                    'note': indicator.get('note', None)
                })
        
        # 市場メモを生成
        market_notes = [
            f"騰落概況：上昇 {len([t for t in topics if hasattr(t, 'sentiment') and t.sentiment == 'positive'])} / 下落 {len([t for t in topics if hasattr(t, 'sentiment') and t.sentiment == 'negative'])}",
            "出来高：前日比 +5%",
            "イベント：FOMC前のポジション調整"
        ]
        
        # 経済イベントを生成
        economic_events = [
            "米PPI総合（前月比）：+0.2%（予想 +0.1%）",
            "ミシガン確報：68.9（予想 69.1）",
            "本日CPI発表へ— コア +0.2% 予想"
        ]
        
        # トピックをシリアライズ可能な形式に変換
        serializable_topics = []
        for topic in topics:
            serializable_topics.append({
                'headline': topic.headline,
                'blurb': topic.blurb,
                'url': topic.url,
                'source': topic.source,
                'score': topic.score,
                'published_jst': topic.published_jst.isoformat(),
                'category': topic.category,
                'region': topic.region
            })
        
        # 深掘りトピックデータ
        deep_dive_topic_1 = {
            'title': 'FRBメッセージの転換',
            'points': [
                {'label': '何が起きたか', 'content': 'タカ派→中立寄りへシフト'},
                {'label': '背景', 'content': 'コアインフレ鈍化、需要の一服'},
                {'label': '市場への含意', 'content': 'ポリシーパスの不確実性低下'},
                {'label': 'リスク/反証', 'content': 'サービス価格の粘着性、賃金の底堅さ'}
            ],
            'quotes': [
                '【○○連銀総裁】「次回会合はデータ次第」',
                '【雇用】求人倍率のトレンド鈍化',
                '【家計】クレジット残高の伸び一服',
                'ToDo：発言原文リンク／会見書き起こしを差し込み'
            ]
        }
        
        deep_dive_topic_2 = {
            'title': '為替介入観測と当局スタンス',
            'points': [
                {'label': 'ポイント', 'content': '当局コミュニケーションと実弾のしきい値'},
                {'label': 'メカニズム', 'content': '実需/裁定/投機の駆動要因'},
                {'label': '短期の注目', 'content': '実効レート・裁定コスト・海外金利差'},
                {'label': '中期の注目', 'content': '国際収支/企業の為替感応度'}
            ],
            'evidence': [
                '関係者コメントの時系列整理（誰が/いつ/どこで）',
                '推定トリガーのレンジ（板の歪み等）',
                '外貨需給イベント（配当/決算期末等）のカレンダー',
                'ソースURL（短縮URL推奨）'
            ]
        }
        
        # 経済指標データ
        previous_day_indicators = [
            {
                'time': '21:30',
                'name': '米 卸売物価（PPI）総合 前月比',
                'result': '+0.2%',
                'forecast': '+0.1%',
                'previous': '+0.1%'
            },
            {
                'time': '23:00',
                'name': '米 ミシガン消費者信頼感（確報）',
                'result': '68.9',
                'forecast': '69.1',
                'previous': '69.5'
            }
        ]
        
        today_indicators = [
            {
                'time': '21:30',
                'name': '米 消費者物価（CPI）総合 前月比',
                'forecast': '+0.2%',
                'range': '+0.1〜0.3%',
                'important': True
            },
            {
                'time': '21:30',
                'name': '米 CPI コア 前月比',
                'forecast': '+0.2%',
                'range': '+0.1〜0.2%',
                'important': False
            },
            {
                'time': '23:00',
                'name': '加 中銀 金利',
                'forecast': '5.00%',
                'range': '据置見通し',
                'important': False
            }
        ]
        
        return {
            'badge_text': self._get_badge_text(slide_type),
            'title': title,
            'date_str': date_str,
            'indicators': formatted_indicators,
            'market_notes': market_notes,
            'topics': serializable_topics,
            'economic_events': economic_events,
            'hashtags': hashtag_list,
            'website_url': website_url,
            'deep_dive_topic_1': deep_dive_topic_1,
            'deep_dive_topic_2': deep_dive_topic_2,
            'previous_day_indicators': previous_day_indicators,
            'today_indicators': today_indicators
        }
    
    def _get_badge_text(self, slide_type: str) -> str:
        """スライドタイプに応じたバッジテキストを取得"""
        badge_map = {
            'market_recap': 'MARKET RECAP',
            'deep_dive_1': 'TOPIC DEEP DIVE',
            'deep_dive_2': 'TOPIC DEEP DIVE',
            'econ_calendar': 'ECON CALENDAR'
        }
        return badge_map.get(slide_type, 'MARKET NEWS')
    
    async def _generate_html(self, template_data: Dict[str, Any], slide_type: str) -> str:
        """HTMLを生成"""
        try:
            template = self.jinja_env.get_template('sns_template.html')
            html_content = template.render(**template_data)
            return html_content
        except Exception as e:
            self.logger.error(f"HTML生成エラー: {e}")
            raise
    
    async def _take_screenshot(self, html_content: str, output_path: Path, slide_type: str = "market_recap") -> None:
        """Playwrightを使用してスクリーンショットを撮影"""
        async with async_playwright() as p:
            # ブラウザを起動
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # ビューポートサイズを設定
            await page.set_viewport_size({"width": self.width, "height": self.height})
            
            # HTMLコンテンツを設定
            await page.set_content(html_content, wait_until="networkidle")
            
            # 特定のスライドをスクリーンショット
            slide_selector = self._get_slide_selector(slide_type)
            element = await page.query_selector(slide_selector)
            
            if element:
                await element.screenshot(path=str(output_path), type="png")
            else:
                # フォールバック: ページ全体をスクリーンショット
                await page.screenshot(path=str(output_path), type="png")
            
            await browser.close()
    
    def _get_slide_selector(self, slide_type: str) -> str:
        """スクリーンショット対象のスライドセレクタを取得"""
        slide_map = {
            'market_recap': '#slide-1',
            'deep_dive_1': '#slide-2',
            'deep_dive_2': '#slide-3',
            'econ_calendar': '#slide-4'
        }
        return slide_map.get(slide_type, '#slide-1')
    
    def _domain_from_url(self, url: str) -> str:
        """URLからドメインを抽出"""
        try:
            netloc = urlparse(url).netloc
            return netloc or ""
        except Exception:
            return ""
    
    # 既存のメソッドとの互換性のため（同期的なラッパー）
    def render_16x9_sync(
        self,
        date: datetime,
        title: str,
        topics: List[Topic],
        output_dir: str,
        brand_name: str = "Market News",
        website_url: str = "https://market-news.example.com",
        hashtags: str = "#MarketNews",
        subtitle: Optional[str] = "本日のハイライト",
        indicators: Optional[List[dict]] = None,
        slide_type: str = "market_recap"
    ) -> Path:
        """同期的な16:9画像生成ラッパー"""
        return asyncio.run(self.render_16x9(
            date, title, topics, output_dir, brand_name, 
            website_url, hashtags, subtitle, indicators, slide_type
        ))
    
    def render_16x9_details(
        self,
        date: datetime,
        title: str,
        topics: List[Topic],
        output_dir: str,
        brand_name: str = "Market News",
        website_url: str = "https://market-news.example.com",
        hashtags: str = "#MarketNews",
        subtitle: Optional[str] = "注目トピック詳細",
    ) -> Path:
        """詳細画像を生成（深掘り1）"""
        return self.render_16x9_sync(
            date, title, topics, output_dir, brand_name, 
            website_url, hashtags, subtitle, None, "deep_dive_1"
        )
    
    def render_16x9_summary(
        self,
        date: datetime,
        title: str,
        summary_text: str,
        output_dir: str,
        brand_name: str = "Market News",
        website_url: str = "https://market-news.example.com",
        hashtags: str = "#MarketNews",
        subtitle: Optional[str] = "Pro統合要約",
    ) -> Path:
        """統合要約画像を生成（深掘り2）"""
        # summary_textをtopicsに変換（簡易実装）
        topics = [Topic(
            headline="統合要約",
            blurb=summary_text[:200] + "..." if len(summary_text) > 200 else summary_text,
            url="",
            source="Market News",
            score=1.0,
            published_jst=date,
            category="summary",
            region="global"
        )]
        
        return self.render_16x9_sync(
            date, title, topics, output_dir, brand_name, 
            website_url, hashtags, subtitle, None, "deep_dive_2"
        )
    
    def render_16x9_indicators(
        self,
        date: datetime,
        title: str,
        indicators: List[dict],
        output_dir: str,
        brand_name: str = "Market News",
        website_url: str = "https://market-news.example.com",
        hashtags: str = "#MarketNews",
        subtitle: Optional[str] = "主要指標一覧",
    ) -> Path:
        """指標画像を生成（経済カレンダー）"""
        topics = [Topic(
            headline="経済指標",
            blurb="主要経済指標の一覧",
            url="",
            source="Market News",
            score=1.0,
            published_jst=date,
            category="indicators",
            region="global"
        )]
        
        return self.render_16x9_sync(
            date, title, topics, output_dir, brand_name, 
            website_url, hashtags, subtitle, indicators, "econ_calendar"
        )
