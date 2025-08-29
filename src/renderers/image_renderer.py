"""
SNS画像レンダラ（Pillow使用）
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont

from ..personalization.topic_selector import Topic


class ImageRenderer:
    """SNS画像生成器"""
    
    def __init__(
        self, 
        width: int = 1920,
        height: int = 1080,
        margin: int = 96,
        background_color: str = "#FFF5F5",
        text_color: str = "#1F1F1F",
        accent_color: str = "#FF6B6B",
        sub_accent_color: str = "#4ECDC4"
    ):
        """
        Args:
            width: 画像幅
            height: 画像高さ
            margin: マージン
            background_color: 背景色
            text_color: テキスト色
            accent_color: アクセント色
            sub_accent_color: サブアクセント色
        """
        self.width = width
        self.height = height
        self.margin = margin
        self.background_color = background_color
        self.text_color = text_color
        self.accent_color = accent_color
        self.sub_accent_color = sub_accent_color
        
        # フォントパスを設定
        self.fonts = self._setup_fonts()
    
    def _setup_fonts(self) -> dict:
        """フォントを設定"""
        fonts = {}

        # プロジェクトルートのフォントディレクトリ
        project_root = Path(__file__).parent.parent.parent
        font_dir = project_root / "assets" / "brand" / "fonts"

        # フォントファイルのパス
        regular_font = font_dir / "NotoSansJP-Regular.ttf"
        bold_font = font_dir / "NotoSansJP-Bold.ttf"

        def _first_existing(paths: list) -> Optional[str]:
            for p in paths:
                try:
                    path = Path(p)
                    if path.exists():
                        return str(path)
                except Exception:
                    continue
            return None

        # 代替候補（環境依存）
        mac_regular_candidates = [
            "/System/Library/Fonts/HiraginoSans-W3.ttc",
            "/Library/Fonts/HiraginoSans-W3.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        ]
        mac_bold_candidates = [
            "/System/Library/Fonts/HiraginoSans-W6.ttc",
            "/Library/Fonts/HiraginoSans-W6.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        ]

        win_regular_candidates = [
            r"C:\\Windows\\Fonts\\meiryo.ttc",
            r"C:\\Windows\\Fonts\\YuGothM.ttc",
        ]
        win_bold_candidates = [
            r"C:\\Windows\\Fonts\\meiryob.ttc",
            r"C:\\Windows\\Fonts\\YuGothB.ttc",
        ]

        linux_regular_candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        linux_bold_candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        
        try:
            # カスタムフォントを読み込み
            if regular_font.exists():
                reg_path = str(regular_font)
            else:
                reg_path = _first_existing(mac_regular_candidates) or _first_existing(win_regular_candidates) or _first_existing(linux_regular_candidates)

            if reg_path:
                fonts['regular_large'] = ImageFont.truetype(reg_path, 64)
                fonts['regular_medium'] = ImageFont.truetype(reg_path, 40)
                fonts['regular_small'] = ImageFont.truetype(reg_path, 32)
            else:
                fonts['regular_large'] = ImageFont.load_default()
                fonts['regular_medium'] = ImageFont.load_default()
                fonts['regular_small'] = ImageFont.load_default()
            
            if bold_font.exists():
                bold_path = str(bold_font)
            else:
                bold_path = _first_existing(mac_bold_candidates) or _first_existing(win_bold_candidates) or _first_existing(linux_bold_candidates)

            if bold_path:
                fonts['bold_large'] = ImageFont.truetype(bold_path, 64)
                fonts['bold_medium'] = ImageFont.truetype(bold_path, 48)
                fonts['bold_small'] = ImageFont.truetype(bold_path, 36)
            else:
                fonts['bold_large'] = ImageFont.load_default()
                fonts['bold_medium'] = ImageFont.load_default()
                fonts['bold_small'] = ImageFont.load_default()
                
        except Exception:
            # フォント読み込みに失敗した場合はデフォルトフォント
            default_font = ImageFont.load_default()
            for key in ['regular_large', 'regular_medium', 'regular_small', 
                       'bold_large', 'bold_medium', 'bold_small']:
                fonts[key] = default_font
        
        return fonts
    
    def render_16x9(
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
    ) -> Path:
        """
        16:9 SNS画像を生成
        
        Args:
            date: 日付
            title: タイトル
            topics: トピック一覧
            output_dir: 出力ディレクトリ
            brand_name: ブランド名
            website_url: ウェブサイトURL
            hashtags: ハッシュタグ
            
        Returns:
            生成された画像ファイルのパス
        """
        # 出力ディレクトリを作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # ファイル名を生成
        filename = "news_01_16x9.png"
        file_path = output_path / filename
        
        # 画像を作成
        image = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(image)
        
        # レイアウトを描画
        self._draw_header(draw, title, date, subtitle=subtitle)
        self._draw_topics(draw, topics)
        self._draw_footer(draw, brand_name, website_url, hashtags)
        # 新デザインでは右側のチャート/指標パネルを廃止
        self._draw_logo(draw, brand_name)
        
        # 画像を保存
        image.save(file_path, 'PNG', quality=95)
        
        return file_path
    
    def _draw_header(self, draw: ImageDraw.Draw, title: str, date: datetime, subtitle: Optional[str] = None):
        """ヘッダーを中央寄せで描画"""
        title_font = self.fonts['bold_large']
        title_lines = self._wrap_text(title, title_font, self.width - self.margin * 2)

        y = self.margin
        for line in title_lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            w = bbox[2] - bbox[0]
            draw.text(((self.width - w) / 2, y), line, fill=self.text_color, font=title_font)
            y += 70

        if subtitle:
            sub_font = self.fonts['regular_medium']
            bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
            w = bbox[2] - bbox[0]
            draw.text(((self.width - w) / 2, y), subtitle, fill=self.accent_color, font=sub_font)
            y += bbox[3] - bbox[1] + 20

        date_str = date.strftime('%Y-%m-%d')
        date_font = self.fonts['regular_small']
        bbox = draw.textbbox((0, 0), date_str, font=date_font)
        w = bbox[2] - bbox[0]
        draw.text(((self.width - w) / 2, y), date_str, fill=self.accent_color, font=date_font)
        y += bbox[3] - bbox[1] + 30

        draw.line([(self.margin, y), (self.width - self.margin, y)], fill=self.accent_color, width=3)
    
    def _draw_topics(self, draw: ImageDraw.Draw, topics: List[Topic]):
        """トピックをカード形式で描画"""
        if not topics:
            return

        card_width = self.width - self.margin * 2
        card_height = 140
        start_y = self.margin + 220
        card_color = "#FFFFFF"

        for i, topic in enumerate(topics[:3]):
            y = start_y + i * (card_height + 20)

            draw.rounded_rectangle(
                [self.margin, y, self.margin + card_width, y + card_height],
                radius=16,
                fill=card_color,
                outline=self.accent_color,
                width=2
            )

            num_text = str(i + 1)
            num_font = self.fonts['bold_medium']
            bbox = draw.textbbox((0, 0), num_text, font=num_font)
            draw.text(
                (self.margin + 24, y + (card_height - (bbox[3] - bbox[1])) / 2),
                num_text,
                fill=self.accent_color,
                font=num_font
            )

            text_x = self.margin + 80
            text_w = card_width - 100
            headline_font = self.fonts['regular_medium']
            lines = self._wrap_text(topic.headline, headline_font, text_w)
            text_y = y + 24
            for line in lines[:2]:
                draw.text((text_x, text_y), line, fill=self.text_color, font=headline_font)
                text_y += 42

            if topic.blurb:
                summary = topic.blurb[:100] + "..." if len(topic.blurb) > 100 else topic.blurb
                draw.text(
                    (text_x, text_y),
                    summary,
                    fill=self.sub_accent_color,
                    font=self.fonts['regular_small']
                )
    
    def _draw_footer(
        self, 
        draw: ImageDraw.Draw, 
        brand_name: str, 
        website_url: str, 
        hashtags: str
    ):
        """フッターを描画"""
        footer_y = self.height - self.margin - 50
        
        # ウェブサイトURL
        draw.text(
            (self.margin, footer_y),
            website_url,
            fill=self.accent_color,
            font=self.fonts['regular_small']
        )
        
        # ハッシュタグ（右寄せ）
        hashtag_width = draw.textlength(hashtags, font=self.fonts['regular_small'])
        draw.text(
            (self.width - self.margin - hashtag_width, footer_y),
            hashtags,
            fill=self.sub_accent_color,
            font=self.fonts['regular_small']
        )

        # CTA（右下の上に）
        cta_text = "詳細はnoteで / プロフィールのリンクから"
        cta_width = draw.textlength(cta_text, font=self.fonts['regular_small'])
        draw.text(
            (self.width - self.margin - cta_width, footer_y - 40),
            cta_text,
            fill=self.text_color,
            font=self.fonts['regular_small']
        )
    
    def _draw_logo(self, draw: ImageDraw.Draw, brand_name: str):
        """ロゴを描画"""
        # ロゴファイルの確認
        project_root = Path(__file__).parent.parent.parent
        logo_path = project_root / "assets" / "brand" / "logo_mn_square.png"
        
        logo_x = self.width - self.margin - 96
        logo_y = self.height - self.margin - 96
        
        try:
            if logo_path.exists():
                # ロゴファイルを読み込み
                logo = Image.open(logo_path)
                logo = logo.resize((96, 96), Image.Resampling.LANCZOS)
                
                # アルファチャンネルがある場合は適切に合成
                if logo.mode == 'RGBA':
                    # 透明度を考慮して合成
                    logo_img = Image.new('RGB', (96, 96), self.background_color)
                    logo_img.paste(logo, (0, 0), logo)
                    logo = logo_img
                
                # メイン画像にロゴを貼り付け
                draw._image.paste(logo, (logo_x, logo_y))
            else:
                # ロゴファイルがない場合はテキストロゴ
                self._draw_text_logo(draw, brand_name, logo_x, logo_y)
                
        except Exception:
            # エラーが発生した場合はテキストロゴ
            self._draw_text_logo(draw, brand_name, logo_x, logo_y)
    
    def _draw_text_logo(self, draw: ImageDraw.Draw, brand_name: str, x: int, y: int):
        """テキストロゴを描画"""
        # 背景の角丸四角形
        draw.rounded_rectangle(
            [x, y, x + 96, y + 96],
            radius=12,
            fill=self.accent_color
        )
        
        # ブランド名の頭文字を取得
        initials = ''.join([word[0].upper() for word in brand_name.split()[:2]])
        if not initials:
            initials = "MN"
        
        # テキストを中央に描画
        text_width = draw.textlength(initials, font=self.fonts['bold_medium'])
        text_x = x + (96 - text_width) // 2
        text_y = y + 20
        
        draw.text(
            (text_x, text_y),
            initials,
            fill="white",
            font=self.fonts['bold_medium']
        )
    
    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
        """テキストを指定幅で折り返し（CJK対応: textlengthで測定）"""
        if not text:
            return []

        # 計測用の描画コンテキスト
        measure_img = Image.new('RGB', (1, 1))
        measure_draw = ImageDraw.Draw(measure_img)

        lines: List[str] = []
        current: str = ""

        for ch in text:
            test = current + ch
            width = measure_draw.textlength(test, font=font)
            if width <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = ch

        if current:
            lines.append(current)

        return lines

    # 追加: 詳細スライド
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
        # 出力ディレクトリ
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / "news_02_16x9.png"

        # 画像キャンバス
        image = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(image)

        # ヘッダー
        self._draw_header(draw, title, date, subtitle=subtitle)

        # 詳細分析リスト（AI要約を活用）
        start_y = self.margin + 140  # 開始位置を上に
        line_gap = 28  # 行間を縮小
        content_width = self.width - self.margin * 2

        y = start_y
        for i, t in enumerate(topics[:3], 1):
            # 見出し（より小さいフォント）
            head = f"{i}. {t.headline}"
            head_lines = self._wrap_text(head, self.fonts['bold_small'], content_width)
            for line in head_lines[:2]:
                draw.text((self.margin, y), line, fill=self.text_color, font=self.fonts['bold_small'])
                y += line_gap

            # AI生成詳細要約（メインコンテンツ）
            if t.summary:
                detailed_summary = t.summary[:400] + "..." if len(t.summary) > 400 else t.summary
                summary_lines = self._wrap_text(detailed_summary, self.fonts['regular_small'], content_width)

                y += 8  # 少し間隔を空ける
                for line in summary_lines[:6]:  # 最大6行の詳細説明
                    draw.text((self.margin, y), line, fill=self.text_color, font=self.fonts['regular_small'])
                    y += line_gap

                # 市場への影響度を表示
                impact_text = "📊 市場への影響度: " + self._assess_market_impact(t)
                draw.text((self.margin, y + 8), impact_text, fill=self.accent_color, font=self.fonts['regular_small'])
                y += line_gap + 8

            # ソース・カテゴリ情報
            meta_parts = []
            if t.source:
                meta_parts.append(f"出典: {t.source}")
            if t.category:
                meta_parts.append(f"分野: {t.category}")
            if t.region:
                meta_parts.append(f"地域: {t.region}")

            if meta_parts:
                meta = " | ".join(meta_parts)
                draw.text((self.margin, y), meta, fill=self.sub_accent_color, font=self.fonts['regular_small'])
                y += line_gap + 5

            # 区切り線
            if i < len(topics[:3]):  # 最後以外
                draw.line([(self.margin, y), (self.width - self.margin, y)], fill=self.text_color + "40")
                y += 20

        # フッター/ロゴ
        self._draw_footer(draw, brand_name, website_url, hashtags)
        self._draw_logo(draw, brand_name)

        image.save(file_path, 'PNG', quality=95)
        return file_path

    def _domain_from_url(self, url: str) -> str:
        try:
            netloc = urlparse(url).netloc
            return netloc or ""
        except Exception:
            return ""
    
    def _assess_market_impact(self, topic: Topic) -> str:
        """トピックの市場への影響度を評価"""
        # スコアベースの簡易評価
        if topic.score >= 1.5:
            return "高（全市場に影響）"
        elif topic.score >= 1.0:
            return "中（セクター影響）"
        else:
            return "低（限定的影響）"

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
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / "news_03_16x9.png"

        image = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(image)

        self._draw_header(draw, title, date, subtitle=subtitle)

        # 全幅テーブル
        panel_x = self.margin
        panel_y = self.margin + 150
        panel_w = self.width - self.margin * 2
        row_h = 46

        headers = ["指標", "値", "前日比", "前日比%"]
        col_w = [int(panel_w * 0.4), int(panel_w * 0.25), int(panel_w * 0.18), int(panel_w * 0.17)]
        x = panel_x
        for i, h in enumerate(headers):
            draw.text((x, panel_y), h, fill=self.text_color, font=self.fonts['regular_small'])
            x += col_w[i]
        y = panel_y + row_h
        draw.line([(panel_x, y - 10), (panel_x + panel_w, y - 10)], fill=self.text_color)

        for item in indicators[:14]:
            name = str(item.get('name', '—'))
            value = str(item.get('value', '—'))
            change = str(item.get('change', '—'))
            pct = str(item.get('pct', '—'))

            x = panel_x
            vals = [name, value, change, pct]
            for i, v in enumerate(vals):
                color = self.text_color
                if i in (2, 3):
                    if isinstance(item.get('change', ''), str) and item.get('change', '').startswith('-'):
                        color = self.accent_color
                    elif isinstance(item.get('change', ''), str) and item.get('change', '').startswith('+'):
                        color = self.sub_accent_color
                draw.text((x, y), v, fill=color, font=self.fonts['regular_small'])
                x += col_w[i]
            y += row_h

        self._draw_footer(draw, brand_name, website_url, hashtags)
        self._draw_logo(draw, brand_name)
        image.save(file_path, 'PNG', quality=95)
        return file_path

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
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / "news_03_16x9.png"

        image = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(image)

        self._draw_header(draw, title, date, subtitle=subtitle)

        # テキストエリア
        x = self.margin
        y = self.margin + 160
        max_w = self.width - self.margin * 2
        font = self.fonts['regular_small']

        # 段落ごとに描画
        paragraphs = [p.strip() for p in (summary_text or "").split("\n") if p.strip()]
        for p in paragraphs:
            lines = self._wrap_text(p, font, max_w)
            for line in lines:
                draw.text((x, y), line, fill=self.text_color, font=font)
                y += 36
            y += 12

        self._draw_footer(draw, brand_name, website_url, hashtags)
        self._draw_logo(draw, brand_name)

        image.save(file_path, 'PNG', quality=95)
        return file_path
