"""
SNS画像レンダラ（Pillow使用）
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from ..personalization.topic_selector import Topic


class ImageRenderer:
    """SNS画像生成器"""
    
    def __init__(
        self, 
        width: int = 1920,
        height: int = 1080,
        margin: int = 96,
        background_color: str = "#0B0F1A",
        text_color: str = "#E6EDF3",
        accent_color: str = "#2F81F7",
        sub_accent_color: str = "#F78166"
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
        
        try:
            # カスタムフォントを読み込み
            if regular_font.exists():
                fonts['regular_large'] = ImageFont.truetype(str(regular_font), 64)
                fonts['regular_medium'] = ImageFont.truetype(str(regular_font), 40)
                fonts['regular_small'] = ImageFont.truetype(str(regular_font), 32)
            else:
                # システムフォントへのフォールバック
                fonts['regular_large'] = ImageFont.load_default()
                fonts['regular_medium'] = ImageFont.load_default()
                fonts['regular_small'] = ImageFont.load_default()
            
            if bold_font.exists():
                fonts['bold_large'] = ImageFont.truetype(str(bold_font), 64)
                fonts['bold_medium'] = ImageFont.truetype(str(bold_font), 48)
                fonts['bold_small'] = ImageFont.truetype(str(bold_font), 36)
            else:
                # システムフォントへのフォールバック
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
        hashtags: str = "#MarketNews"
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
        self._draw_header(draw, title, date)
        self._draw_topics(draw, topics)
        self._draw_footer(draw, brand_name, website_url, hashtags)
        self._draw_chart_placeholder(draw)
        self._draw_logo(draw, brand_name)
        
        # 画像を保存
        image.save(file_path, 'PNG', quality=95)
        
        return file_path
    
    def _draw_header(self, draw: ImageDraw.Draw, title: str, date: datetime):
        """ヘッダーを描画"""
        # タイトル（左上）
        title_font = self.fonts['bold_large']
        title_wrapped = self._wrap_text(title, title_font, self.width - self.margin * 2 - 200)
        
        y_pos = self.margin
        for line in title_wrapped:
            draw.text((self.margin, y_pos), line, fill=self.text_color, font=title_font)
            y_pos += 70
        
        # 日付（右上）
        date_str = date.strftime('%Y年%m月%d日')
        date_font = self.fonts['regular_medium']
        draw.text(
            (self.width - self.margin - 200, self.margin),
            date_str,
            fill=self.accent_color,
            font=date_font
        )
    
    def _draw_topics(self, draw: ImageDraw.Draw, topics: List[Topic]):
        """トピックを描画"""
        if not topics:
            return
        
        # トピック領域の開始位置
        start_y = self.margin + 150
        content_width = (self.width - self.margin * 2) // 2 - 50  # 左半分を使用
        
        for i, topic in enumerate(topics[:3]):  # 最大3件
            y_pos = start_y + i * 180
            
            # トピック番号と見出し
            number_text = f"{i + 1}."
            draw.text(
                (self.margin, y_pos),
                number_text,
                fill=self.accent_color,
                font=self.fonts['bold_medium']
            )
            
            # 見出し
            headline_wrapped = self._wrap_text(
                topic.headline,
                self.fonts['bold_small'],
                content_width - 60
            )
            
            headline_y = y_pos
            for line in headline_wrapped[:2]:  # 最大2行
                draw.text(
                    (self.margin + 60, headline_y),
                    line,
                    fill=self.text_color,
                    font=self.fonts['bold_small']
                )
                headline_y += 40
            
            # 補足文
            if topic.blurb and len(headline_wrapped) <= 1:
                blurb_wrapped = self._wrap_text(
                    topic.blurb,
                    self.fonts['regular_small'],
                    content_width - 60
                )
                
                blurb_y = headline_y + 10
                for line in blurb_wrapped[:2]:  # 最大2行
                    draw.text(
                        (self.margin + 60, blurb_y),
                        line,
                        fill=self.text_color,
                        font=self.fonts['regular_small']
                    )
                    blurb_y += 35
    
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
    
    def _draw_chart_placeholder(self, draw: ImageDraw.Draw):
        """チャート用のプレースホルダーを描画"""
        # 右側にチャート枠を描画
        chart_x = self.width // 2 + 50
        chart_y = self.margin + 200
        chart_width = self.width - chart_x - self.margin
        chart_height = 400
        
        # 点線の枠を描画
        for i in range(0, chart_width, 20):
            draw.rectangle(
                [chart_x + i, chart_y, chart_x + i + 10, chart_y + 2],
                fill=self.text_color + "40"  # 透明度を追加
            )
            draw.rectangle(
                [chart_x + i, chart_y + chart_height, chart_x + i + 10, chart_y + chart_height + 2],
                fill=self.text_color + "40"
            )
        
        for i in range(0, chart_height, 20):
            draw.rectangle(
                [chart_x, chart_y + i, chart_x + 2, chart_y + i + 10],
                fill=self.text_color + "40"
            )
            draw.rectangle(
                [chart_x + chart_width, chart_y + i, chart_x + chart_width + 2, chart_y + i + 10],
                fill=self.text_color + "40"
            )
        
        # プレースホルダーテキスト
        placeholder_text = "チャート・図表エリア"
        text_width = draw.textlength(placeholder_text, font=self.fonts['regular_medium'])
        draw.text(
            (chart_x + (chart_width - text_width) // 2, chart_y + chart_height // 2),
            placeholder_text,
            fill=self.text_color + "60",
            font=self.fonts['regular_medium']
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
        """テキストを指定幅で折り返し"""
        if not text:
            return []
        
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = current_line + [word]
            test_text = ' '.join(test_line)
            
            if len(test_text) * 20 <= max_width:  # 概算での幅チェック
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines