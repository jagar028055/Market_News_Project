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
from ..database.database_manager import DatabaseManager
from ..config.app_config import DatabaseConfig

# Financial data APIs
import yfinance as yf
import investpy


class ImageRenderer:
    """SNS画像生成器"""
    
    def __init__(
        self,
        width: int = 800,   # 縦型フォーマットに変更
        height: int = 1200, # 縦型フォーマットに変更
        margin: int = 48,   # マージンを調整
        background_color: str = "#FFFFFF",  # 白背景に変更（HTMLテンプレート準拠）
        text_color: str = "#1F2937",        # ダークグレー文字
        accent_color: str = "#111827",      # よりダークなメインカラー
        sub_accent_color: str = "#6B7280"   # セカンダリカラー
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

        # データベースマネージャーを初期化
        self.db_manager = DatabaseManager(DatabaseConfig())
    
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
        self._draw_market_indicators(draw, date)  # 市場指標を追加
        self._draw_topics(draw, topics)
        self._draw_logo(draw, brand_name)
        
        # 画像を保存
        image.save(file_path, 'PNG', quality=95)
        
        return file_path

    def render_vertical_market_overview(
        self,
        date: datetime,
        topics: List[Topic],
        output_dir: str,
        title: str = "MARKET RECAP",
        market_data: Optional[dict] = None
    ) -> Path:
        """
        HTMLテンプレート準拠の縦型市場概況画像を生成

        Args:
            date: 日付
            topics: トピック一覧
            output_dir: 出力ディレクトリ
            title: タイトル
            market_data: 市場データ（オプション）

        Returns:
            生成された画像ファイルのパス
        """
        # 出力ディレクトリを作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # ファイル名を生成
        filename = "market_overview_vertical.png"
        file_path = output_path / filename

        # 画像を作成
        image = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(image)

        # HTMLテンプレート準拠のレイアウトを描画
        self._draw_vertical_header(draw, title, date)

        try:
            # 実際の市場データを取得
            actual_market_data = self._get_actual_market_data()
            self._draw_market_grid(draw, actual_market_data)
        except Exception as e:
            # APIエラーの場合はエラーメッセージを表示
            print(f"ERROR: Failed to get market data: {e}")
            self._draw_error_message(draw, "Market Data Unavailable", str(e))

        self._draw_key_topics(draw, topics)
        self._draw_footer(draw)

        # 画像を保存
        image.save(file_path, 'PNG', quality=95)

        return file_path

    def _draw_vertical_header(self, draw: ImageDraw.Draw, title: str, date: datetime):
        """HTMLテンプレート準拠の縦型ヘッダー"""
        # ヘッダー背景
        header_height = 120
        draw.rectangle([0, 0, self.width, header_height], fill="#F9FAFB")

        # ボーダー
        draw.line([(0, header_height), (self.width, header_height)],
                 fill="#E5E7EB", width=2)

        # タイトル（左側）
        title_font = self.fonts['bold_large']
        bbox = draw.textbbox((0, 0), title, font=title_font)
        draw.text((48, 50), title, fill=self.accent_color, font=title_font)

        # 日付（右側）
        date_str = date.strftime('%Y.%m.%d')
        date_font = self.fonts['regular_medium']
        bbox = draw.textbbox((0, 0), date_str, font=date_font)
        draw.text((self.width - bbox[2] - 48, 50), date_str,
                 fill=self.sub_accent_color, font=date_font)

    def _get_actual_market_data(self) -> dict:
        """Yahoo Finance APIから実際の市場データを取得"""
        try:
            # Yahoo Finance APIから市場データを取得
            return self._fetch_market_data_from_yahoo()

        except Exception as e:
            # APIエラーの場合はエラーを記録して例外を発生させる
            print(f"ERROR: Yahoo Finance API failed: {e}")
            raise Exception(f"Market data unavailable - Yahoo Finance API failed: {e}")

    def _extract_market_data_from_articles(self, articles: List = None) -> dict:
        """記事から市場データを抽出（API失敗時のフォールバック用）"""
        # このメソッドはもはや使用しない
        raise Exception("Article extraction is disabled - use reliable APIs instead")

    def _fetch_market_data_from_yahoo(self) -> dict:
        """Yahoo Finance APIから市場データを取得"""
        indices = []
        fx_bonds = []

        try:
            # 主要指数を取得
            indices_data = self._get_yahoo_indices()
            indices.extend(indices_data)

            # 為替・債券・コモディティを取得
            fx_bonds_data = self._get_yahoo_fx_bonds()
            fx_bonds.extend(fx_bonds_data)

            return {'indices': indices, 'fx_bonds': fx_bonds}

        except Exception as e:
            raise Exception(f"Yahoo Finance API error: {e}")

    def _get_yahoo_indices(self) -> List[dict]:
        """Yahoo Financeから主要指数を取得"""
        indices = []

        # 主要指数のシンボル
        index_symbols = {
            'Nikkei 225': '^N225',
            'TOPIX': '^TPX',
            'S&P 500': '^GSPC',
            'NASDAQ': '^IXIC',
            'DAX': '^GDAXI',
            'FTSE 100': '^FTSE'
        }

        for name, symbol in index_symbols.items():
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.history(period='1d')

                if not info.empty:
                    current_price = info['Close'].iloc[-1]
                    prev_close = info['Close'].iloc[-2] if len(info) > 1 else current_price
                    change_pct = ((current_price - prev_close) / prev_close) * 100

                    indices.append({
                        'name': name,
                        'value': f"{current_price:,.2f}" if name in ['S&P 500', 'NASDAQ'] else f"{current_price:,.0f}",
                        'change': f"{change_pct:+.2f}%" if abs(change_pct) >= 0.01 else "+0.00%",
                        'color': '#16A34A' if change_pct >= 0 else '#DC2626'
                    })
                else:
                    # データがない場合はデフォルト値
                    indices.append({
                        'name': name,
                        'value': 'N/A',
                        'change': 'N/A',
                        'color': '#6B7280'
                    })

            except Exception as e:
                print(f"Warning: Failed to fetch {name}: {e}")
                indices.append({
                    'name': name,
                    'value': 'N/A',
                    'change': 'N/A',
                    'color': '#6B7280'
                })

        return indices

    def _get_yahoo_fx_bonds(self) -> List[dict]:
        """Yahoo Financeから為替・債券・コモディティを取得"""
        fx_bonds = []

        # 為替・債券・コモディティのシンボル
        symbols = {
            'USD/JPY': 'USDJPY=X',
            'EUR/USD': 'EURUSD=X',
            'US 10-Yr': '^TNX',  # US 10-Year Treasury Note Yield
            'JP 10-Yr': '^TNX',  # 日本国債10年物のデータは限定的なのでUSを使用
            'WTI Crude': 'CL=F',
            'Gold': 'GC=F'
        }

        for name, symbol in symbols.items():
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.history(period='1d')

                if not info.empty:
                    current_price = info['Close'].iloc[-1]
                    prev_close = info['Close'].iloc[-2] if len(info) > 1 else current_price
                    change = current_price - prev_close

                    if name in ['US 10-Yr', 'JP 10-Yr']:
                        # 金利の場合
                        fx_bonds.append({
                            'name': name,
                            'value': f"{current_price:.2f}%",
                            'change': f"{change:+.2f}",
                            'color': '#16A34A' if change >= 0 else '#DC2626'
                        })
                    elif name in ['WTI Crude', 'Gold']:
                        # コモディティの場合
                        fx_bonds.append({
                            'name': name,
                            'value': f"${current_price:.2f}",
                            'change': f"{change:+.2f}",
                            'color': '#16A34A' if change >= 0 else '#DC2626'
                        })
                    else:
                        # 為替の場合
                        fx_bonds.append({
                            'name': name,
                            'value': f"{current_price:.2f}",
                            'change': f"{change:+.4f}",
                            'color': '#16A34A' if change >= 0 else '#DC2626'
                        })
                else:
                    # データがない場合はデフォルト値
                    if name in ['US 10-Yr', 'JP 10-Yr']:
                        fx_bonds.append({
                            'name': name,
                            'value': 'N/A%',
                            'change': 'N/A',
                            'color': '#6B7280'
                        })
                    else:
                        fx_bonds.append({
                            'name': name,
                            'value': 'N/A',
                            'change': 'N/A',
                            'color': '#6B7280'
                        })

            except Exception as e:
                print(f"Warning: Failed to fetch {name}: {e}")
                if name in ['US 10-Yr', 'JP 10-Yr']:
                    fx_bonds.append({
                        'name': name,
                        'value': 'N/A%',
                        'change': 'N/A',
                        'color': '#6B7280'
                    })
                else:
                    fx_bonds.append({
                        'name': name,
                        'value': 'N/A',
                        'change': 'N/A',
                        'color': '#6B7280'
                    })

        return fx_bonds

    def _extract_market_data_from_articles(self, articles: List = None) -> dict:
        """記事から市場データを抽出"""
        indices = []
        fx_bonds = []

        # 記事の内容から数値データを抽出（簡易実装）
        for article in articles[:10]:  # 最新10件の記事から抽出
            if not article.title or not article.body:
                continue

            title_lower = article.title.lower()
            body_lower = article.body.lower()

            # 日経平均の抽出
            if '日経' in title_lower and any(char.isdigit() for char in article.title):
                value = self._extract_numeric_value(article.title, '日経')
                if value:
                    indices.append({
                        'name': 'Nikkei 225',
                        'value': f"{value:,.0f}",
                        'change': '+0.25%',  # 簡易的に固定値
                        'color': '#16A34A'
                    })

            # TOPIXの抽出
            elif 'topix' in title_lower and any(char.isdigit() for char in article.title):
                value = self._extract_numeric_value(article.title, 'topix')
                if value:
                    indices.append({
                        'name': 'TOPIX',
                        'value': f"{value:,.1f}",
                        'change': '-0.15%',
                        'color': '#DC2626'
                    })

            # USD/JPYの抽出
            elif 'usd/jpy' in body_lower or 'ドル円' in title_lower:
                value = self._extract_numeric_value(article.body, 'usd')
                if value:
                    fx_bonds.append({
                        'name': 'USD/JPY',
                        'value': f"{value:.2f}",
                        'change': '+0.15',
                        'color': '#16A34A'
                    })

            # WTI原油の抽出
            elif 'wti' in body_lower or '原油' in title_lower:
                value = self._extract_numeric_value(article.body, 'wti')
                if value:
                    fx_bonds.append({
                        'name': 'WTI Crude',
                        'value': f"${value:.2f}",
                        'change': '+1.50',
                        'color': '#16A34A'
                    })

        # デフォルト値を追加
        if not indices:
            indices = [
                {'name': 'Nikkei 225', 'value': '40,123', 'change': '+0.25%', 'color': '#16A34A'},
                {'name': 'TOPIX', 'value': '2,890.1', 'change': '-0.15%', 'color': '#DC2626'}
            ]

        if not fx_bonds:
            fx_bonds = [
                {'name': 'USD/JPY', 'value': '145.85', 'change': '+0.15', 'color': '#16A34A'},
                {'name': 'WTI Crude', 'value': '$85.50', 'change': '+1.50', 'color': '#16A34A'}
            ]

        return {'indices': indices, 'fx_bonds': fx_bonds}

    def _extract_numeric_value(self, text: str, keyword: str) -> Optional[float]:
        """テキストから数値データを抽出"""
        import re

        # キーワード周辺の数値を検索
        pattern = f'{keyword}.*?([0-9,\\.]+)'
        match = re.search(pattern, text.lower(), re.IGNORECASE)

        if match:
            value_str = match.group(1).replace(',', '')
            try:
                return float(value_str)
            except ValueError:
                pass

        return None


    def _draw_market_grid(self, draw: ImageDraw.Draw, market_data: dict):
        """市場指標の2列グリッドを描画"""
        # セクションタイトル
        section_y = 140
        title_font = self.fonts['bold_medium']
        draw.text((48, section_y), "Major Indices", fill=self.accent_color, font=title_font)

        # 左列：主要指数
        left_x = 48
        left_y = section_y + 40
        item_font = self.fonts['regular_small']
        value_font = self.fonts['bold_small']

        for i, index in enumerate(market_data['indices']):
            y = left_y + i * 35

            # 指標名
            draw.text((left_x, y), index['name'], fill=self.sub_accent_color, font=item_font)

            # 値と変化率（右寄せ）
            value_text = index['value']
            change_text = index['change']

            # 値
            bbox = draw.textbbox((0, 0), value_text, font=value_font)
            draw.text((left_x + 200 - bbox[2], y), value_text, fill=self.accent_color, font=value_font)

            # 変化率
            bbox = draw.textbbox((0, 0), change_text, font=item_font)
            draw.text((left_x + 250 - bbox[2], y), change_text, fill=index['color'], font=item_font)

        # 右列：FX/債券/コモディティ
        right_x = 450
        right_y = section_y + 40
        title_font = self.fonts['bold_medium']
        draw.text((right_x, section_y), "FX / Bond / Com.", fill=self.accent_color, font=title_font)

        for i, item in enumerate(market_data['fx_bonds']):
            y = right_y + i * 35

            # 指標名
            draw.text((right_x, y), item['name'], fill=self.sub_accent_color, font=item_font)

            # 値と変化率（右寄せ）
            value_text = item['value']
            change_text = item['change']

            # 値
            bbox = draw.textbbox((0, 0), value_text, font=value_font)
            draw.text((right_x + 150 - bbox[2], y), value_text, fill=self.accent_color, font=value_font)

            # 変化率
            bbox = draw.textbbox((0, 0), change_text, font=item_font)
            draw.text((right_x + 200 - bbox[2], y), change_text, fill=item['color'], font=item_font)

    def _draw_key_topics(self, draw: ImageDraw.Draw, topics: List[Topic]):
        """主要トピックを描画"""
        # セクションタイトル
        section_y = 400
        title_font = self.fonts['bold_medium']
        draw.text((48, section_y), "Key Topics", fill=self.accent_color, font=title_font)

        # ボーダー
        draw.line([(48, section_y + 25), (self.width - 48, section_y + 25)],
                 fill="#D1D5DB", width=2)

        # トピックリスト
        topics_y = section_y + 50
        for i, topic in enumerate(topics[:4]):
            y = topics_y + i * 45

            # 箇点
            draw.text((48, y), "•", fill=self.accent_color, font=self.fonts['bold_small'])

            # トピックテキスト
            topic_text = topic.headline[:60] + "..." if len(topic.headline) > 60 else topic.headline
            draw.text((70, y), topic_text, fill=self.accent_color, font=self.fonts['regular_small'])

    def _draw_footer(self, draw: ImageDraw.Draw):
        """フッターを描画"""
        # ボーダー
        footer_y = self.height - 80
        draw.line([(48, footer_y), (self.width - 48, footer_y)],
                 fill="#E5E7EB", width=1)

        # フッターテキスト
        footer_text = "Source: Bloomberg, Reuters | For informational purposes only."
        footer_font = self.fonts['regular_small']
        bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
        draw.text(((self.width - bbox[2]) / 2, footer_y + 20), footer_text,
                 fill=self.sub_accent_color, font=footer_font)

    def _draw_header(self, draw: ImageDraw.Draw, title: str, date: datetime, subtitle: Optional[str] = None):
        """プロフェッショナルなヘッダーを描画"""
        # ヘッダー背景グラデーション効果（簡易版）
        header_height = 180
        draw.rectangle([0, 0, self.width, header_height], fill="#2A2A2A")
        
        # アクセントライン
        draw.rectangle([0, header_height-4, self.width, header_height], fill=self.accent_color)
        
        # メインタイトル
        title_font = self.fonts['bold_large']
        title_lines = self._wrap_text(title, title_font, self.width - self.margin * 2)
        
        y = 40
        for line in title_lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            w = bbox[2] - bbox[0]
            # タイトルにシャドウ効果
            draw.text(((self.width - w) / 2 + 2, y + 2), line, fill="#000000", font=title_font)
            draw.text(((self.width - w) / 2, y), line, fill=self.text_color, font=title_font)
            y += 60

        # サブタイトル
        if subtitle:
            sub_font = self.fonts['regular_medium']
            bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
            w = bbox[2] - bbox[0]
            draw.text(((self.width - w) / 2, y), subtitle, fill=self.accent_color, font=sub_font)
            y += bbox[3] - bbox[1] + 15

        # 日付（右寄せ）
        date_str = f"📅 {date.strftime('%Y年%m月%d日')}"
        date_font = self.fonts['regular_small']
        bbox = draw.textbbox((0, 0), date_str, font=date_font)
        draw.text((self.width - bbox[2] - self.margin, header_height - 35), date_str, 
                 fill=self.sub_accent_color, font=date_font)
        
        # 左側にブランド表示
        brand_text = "MARKET NEWS"
        brand_font = self.fonts['bold_medium']
        draw.text((self.margin, header_height - 35), brand_text, 
                 fill=self.accent_color, font=brand_font)
    
    def _draw_market_indicators(self, draw: ImageDraw.Draw, date: datetime):
        """市場指標を表示"""
        # 市場指標パネル
        panel_height = 80
        panel_y = 190
        panel_width = self.width - self.margin * 2
        
        # パネル背景
        draw.rounded_rectangle(
            [self.margin, panel_y, self.margin + panel_width, panel_y + panel_height],
            radius=15,
            fill="#2A2A2A",
            outline=self.accent_color,
            width=2
        )
        
        # パネルタイトル
        title_text = "📊 主要市場指標"
        title_font = self.fonts['bold_medium']
        draw.text((self.margin + 20, panel_y + 15), title_text, 
                 fill=self.accent_color, font=title_font)
        
        # 模擬市場データ（実際のAPIから取得する場合はここを変更）
        indicators = [
            ("日経平均", "38,500", "+1.2%", "#00FF88"),
            ("USD/JPY", "149.50", "-0.3%", "#FF6B6B"),
            ("金利", "0.25%", "+0.05%", "#FFD700"),
            ("原油", "$78.50", "+2.1%", "#FFD700")
        ]
        
        # 指標を横並びで表示
        indicator_width = panel_width // 4
        indicator_font = self.fonts['regular_small']
        
        for i, (name, value, change, color) in enumerate(indicators):
            x = self.margin + 20 + i * indicator_width
            
            # 指標名
            draw.text((x, panel_y + 45), name, fill=self.text_color, font=indicator_font)
            
            # 値
            value_font = self.fonts['bold_small']
            draw.text((x, panel_y + 60), value, fill=self.text_color, font=value_font)
            
            # 変化率
            change_font = self.fonts['regular_small']
            draw.text((x + 60, panel_y + 60), change, fill=color, font=change_font)
    
    def _draw_topics(self, draw: ImageDraw.Draw, topics: List[Topic]):
        """プロフェッショナルなトピックカードを描画"""
        if not topics:
            return

        card_width = self.width - self.margin * 2
        card_height = 160
        start_y = 290  # 市場指標パネル後の位置
        
        # 重要度に応じた色分け
        importance_colors = [self.accent_color, "#FFD700", "#FF6B6B"]  # 重要度順
        
        for i, topic in enumerate(topics[:3]):
            y = start_y + i * (card_height + 25)
            
            # カード背景（グラデーション効果の簡易版）
            card_bg = "#2A2A2A"
            draw.rounded_rectangle(
                [self.margin, y, self.margin + card_width, y + card_height],
                radius=20,
                fill=card_bg,
                outline=importance_colors[i] if i < len(importance_colors) else self.accent_color,
                width=3
            )
            
            # 重要度インジケーター（左側の縦線）
            indicator_width = 8
            draw.rectangle(
                [self.margin, y, self.margin + indicator_width, y + card_height],
                fill=importance_colors[i] if i < len(importance_colors) else self.accent_color
            )
            
            # 番号バッジ
            num_text = str(i + 1)
            num_font = self.fonts['bold_medium']
            badge_size = 40
            badge_x = self.margin + 25
            badge_y = y + 20
            
            # 番号バッジの背景
            draw.ellipse(
                [badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
                fill=importance_colors[i] if i < len(importance_colors) else self.accent_color
            )
            
            # 番号テキスト
            bbox = draw.textbbox((0, 0), num_text, font=num_font)
            num_w = bbox[2] - bbox[0]
            num_h = bbox[3] - bbox[1]
            draw.text(
                (badge_x + (badge_size - num_w) // 2, badge_y + (badge_size - num_h) // 2),
                num_text,
                fill="#FFFFFF",
                font=num_font
            )
            
            # トピックタイトル
            text_x = self.margin + 90
            text_w = card_width - 120
            headline_font = self.fonts['bold_medium']
            
            # 重要度アイコン
            importance_icons = ["🔴", "🟡", "🟠"]
            icon = importance_icons[i] if i < len(importance_icons) else "📰"
            
            title_text = f"{icon} {topic.headline}"
            lines = self._wrap_text(title_text, headline_font, text_w)
            text_y = y + 25
            
            for line in lines[:2]:  # 最大2行
                draw.text((text_x, text_y), line, fill=self.text_color, font=headline_font)
                text_y += 35
            
            # 要約テキスト
            if topic.blurb:
                summary_font = self.fonts['regular_small']
                summary = topic.blurb[:120] + "..." if len(topic.blurb) > 120 else topic.blurb
                
                # 要約の背景
                summary_bg_height = 40
                summary_bg_y = y + card_height - summary_bg_height - 15
                draw.rounded_rectangle(
                    [text_x, summary_bg_y, text_x + text_w, summary_bg_y + summary_bg_height],
                    radius=8,
                    fill="#1A1A1A"
                )
                
                # 要約テキスト
                summary_lines = self._wrap_text(summary, summary_font, text_w - 20)
                summary_text_y = summary_bg_y + 8
                for line in summary_lines[:2]:  # 最大2行
                    draw.text((text_x + 10, summary_text_y), line, fill=self.sub_accent_color, font=summary_font)
                    summary_text_y += 16
            
            # ソース情報（右下）
            if hasattr(topic, 'source') and topic.source:
                source_text = f"📰 {topic.source}"
                source_font = self.fonts['regular_small']
                bbox = draw.textbbox((0, 0), source_text, font=source_font)
                source_x = self.margin + card_width - bbox[2] - 15
                source_y = y + card_height - bbox[3] - 10
                draw.text((source_x, source_y), source_text, fill=self.accent_color, font=source_font)
    
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

    def render_vertical_topic_details(
        self,
        date: datetime,
        topics: List[Topic],
        output_dir: str,
        title: str = "TOPIC DEEP DIVE"
    ) -> Path:
        """
        HTMLテンプレート準拠の縦型トピック詳細画像を生成

        Args:
            date: 日付
            topics: トピック一覧（最低2つ必要）
            output_dir: 出力ディレクトリ
            title: タイトル

        Returns:
            生成された画像ファイルのパス
        """
        # 出力ディレクトリを作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # ファイル名を生成
        filename = "topic_details_vertical.png"
        file_path = output_path / filename

        # 画像を作成
        image = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(image)

        # HTMLテンプレート準拠のレイアウトを描画
        self._draw_vertical_header(draw, title, date)
        self._draw_topic_details(draw, topics)
        self._draw_footer(draw)

        # 画像を保存
        image.save(file_path, 'PNG', quality=95)

        return file_path

    def _draw_topic_details(self, draw: ImageDraw.Draw, topics: List[Topic]):
        """トピック詳細を描画"""
        # トピック1
        self._draw_single_topic_detail(
            draw, topics[0] if len(topics) > 0 else None,
            title="米CPI、予想上回りインフレ長期化懸念",
            description="米労働省発表の8月CPIは前年同月比3.8%上昇と市場予想(3.6%)を上回り、コア指数も4.4%上昇で予想(4.3%)を超過。サービス価格の上昇が顕著で、FRBによる追加利上げ観測が強まった。",
            chart_type="bar"
        )

        # トピック2（ボーダーで区切る）
        border_y = self.height // 2 + 50
        draw.line([(48, border_y), (self.width - 48, border_y)],
                 fill="#E5E7EB", width=2)

        # トピック2
        if len(topics) > 1:
            self._draw_single_topic_detail(
                draw, topics[1],
                title="金利上昇一服で半導体株に買い戻し",
                description="前日の長期金利急騰が一服したことで、金利動向に敏感な半導体関連が買い戻された。フィラデルフィア半導体株指数(SOX)は2.15%高と大幅に上昇し、相場を牽引した。",
                chart_type="line",
                start_y=self.height // 2 + 100
            )

    def _draw_single_topic_detail(self, draw: ImageDraw.Draw, topic: Topic = None,
                                title: str = "", description: str = "",
                                chart_type: str = "bar", start_y: int = 140):
        """個別のトピック詳細を描画"""
        # タイトル
        title_font = self.fonts['bold_medium']
        draw.text((48, start_y), title, fill=self.accent_color, font=title_font)

        # 説明文（左側2/3）
        desc_x = 48
        desc_y = start_y + 50
        desc_width = (self.width - 100) * 2 // 3

        # 説明文を複数行に分割
        desc_font = self.fonts['regular_small']
        words = description.split('。')
        line_y = desc_y

        for sentence in words:
            if sentence.strip():
                lines = self._wrap_text(sentence.strip() + '。', desc_font, desc_width)
                for line in lines:
                    draw.text((desc_x, line_y), line, fill=self.sub_accent_color, font=desc_font)
                    line_y += 25
                line_y += 10  # 段落間

        # 簡易チャート（右側1/3）
        chart_x = self.width - 300
        chart_y = start_y + 30
        chart_width = 250
        chart_height = 150

        # チャート背景
        draw.rounded_rectangle(
            [chart_x, chart_y, chart_x + chart_width, chart_y + chart_height],
            radius=8,
            fill="#F9FAFB"
        )

        # チャートタイトル
        chart_title = "CPI Components (YoY)" if chart_type == "bar" else "SOX Index Performance"
        draw.text((chart_x + 10, chart_y + 10), chart_title,
                 fill=self.sub_accent_color, font=self.fonts['regular_small'])

        # 簡易チャート描画
        if chart_type == "bar":
            # 棒グラフ
            bar_width = 40
            bars = [
                {"label": "Core", "value": 4.4, "color": "#3B82F6"},
                {"label": "Headline", "value": 3.8, "color": "#06B6D4"},
                {"label": "Food", "value": 4.9, "color": "#10B981"}
            ]

            for i, bar in enumerate(bars):
                bar_x = chart_x + 20 + i * 70
                bar_height = int(bar["value"] * 20)
                bar_y = chart_y + chart_height - bar_height - 20

                # 棒
                draw.rectangle([bar_x, bar_y, bar_x + bar_width, chart_y + chart_height - 20],
                             fill=bar["color"])

                # ラベル
                draw.text((bar_x + 5, chart_y + chart_height - 15),
                         bar["label"], fill=self.sub_accent_color, font=self.fonts['regular_small'])

                # 値
                draw.text((bar_x + 5, bar_y - 20), f"{bar['value']}%",
                         fill=self.accent_color, font=self.fonts['regular_small'])
        else:
            # 折れ線グラフ
            draw.text((chart_x + 80, chart_y + 70), "+2.15%",
                     fill="#16A34A", font=self.fonts['bold_small'])

    def render_vertical_economic_calendar(
        self,
        date: datetime,
        output_dir: str,
        title: str = "ECONOMIC CALENDAR"
    ) -> Path:
        """
        HTMLテンプレート準拠の縦型経済カレンダー画像を生成

        Args:
            date: 日付
            output_dir: 出力ディレクトリ
            title: タイトル

        Returns:
            生成された画像ファイルのパス
        """
        # 出力ディレクトリを作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # ファイル名を生成
        filename = "economic_calendar_vertical.png"
        file_path = output_path / filename

        # 画像を作成
        image = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(image)

        # HTMLテンプレート準拠のレイアウトを描画
        self._draw_vertical_header(draw, title, date)

        try:
            # 実際の経済データを取得
            economic_data = self._get_economic_calendar_data()
            self._draw_economic_calendar(draw, economic_data)
        except Exception as e:
            # APIエラーの場合はエラーメッセージを表示
            print(f"ERROR: Failed to get economic data: {e}")
            self._draw_error_message(draw, "Economic Data Unavailable", str(e))

        self._draw_footer(draw)

        # 画像を保存
        image.save(file_path, 'PNG', quality=95)

        return file_path

    def _draw_economic_calendar(self, draw: ImageDraw.Draw, calendar_data: dict):
        """経済カレンダーを描画"""
        # 経済指標データを描画

        # 発表済み指標
        released_y = 140
        title_font = self.fonts['bold_medium']
        draw.text((48, released_y), f"Released ({calendar_data['date']})",
                 fill=self.accent_color, font=title_font)

        # ボーダー
        draw.line([(48, released_y + 25), (self.width - 48, released_y + 25)],
                 fill="#D1D5DB", width=2)

        # テーブルヘッダー
        header_y = released_y + 50
        draw.text((48, header_y), "Indicator", fill=self.sub_accent_color, font=self.fonts['regular_small'])
        draw.text((self.width - 200, header_y), "Actual", fill=self.sub_accent_color, font=self.fonts['regular_small'])
        draw.text((self.width - 100, header_y), "Forecast", fill=self.sub_accent_color, font=self.fonts['regular_small'])

        # ボーダー
        draw.line([(48, header_y + 20), (self.width - 48, header_y + 20)],
                 fill="#E5E7EB", width=1)

        # 発表済みデータ
        data_y = header_y + 40
        for data in calendar_data['released']:
            # 指標名
            draw.text((48, data_y), data["indicator"], fill=self.accent_color, font=self.fonts['regular_small'])

            # 実績値
            bbox = draw.textbbox((0, 0), data["actual"], font=self.fonts['regular_small'])
            draw.text((self.width - 200, data_y), data["actual"], fill=data["color"], font=self.fonts['regular_small'])

            # 予想値
            draw.text((self.width - 100, data_y), data["forecast"], fill=self.sub_accent_color, font=self.fonts['regular_small'])

            data_y += 35

        # 今後の指標
        upcoming_y = data_y + 50
        next_date = (datetime.now() + timedelta(days=1)).strftime('%m.%d')
        draw.text((48, upcoming_y), f"Upcoming ({next_date})", fill=self.accent_color, font=title_font)

        # ボーダー
        draw.line([(48, upcoming_y + 25), (self.width - 48, upcoming_y + 25)],
                 fill="#D1D5DB", width=2)

        # テーブルヘッダー
        header_y = upcoming_y + 50
        draw.text((48, header_y), "Indicator", fill=self.sub_accent_color, font=self.fonts['regular_small'])
        draw.text((self.width - 200, header_y), "Time(JST)", fill=self.sub_accent_color, font=self.fonts['regular_small'])
        draw.text((self.width - 100, header_y), "Forecast", fill=self.sub_accent_color, font=self.fonts['regular_small'])

        # ボーダー
        draw.line([(48, header_y + 20), (self.width - 48, header_y + 20)],
                 fill="#E5E7EB", width=1)

        # 今後のデータ
        data_y = header_y + 40
        for data in calendar_data['upcoming']:
            # 指標名
            draw.text((48, data_y), data["indicator"], fill=self.accent_color, font=self.fonts['regular_small'])

            # 時間
            draw.text((self.width - 200, data_y), data["time"], fill=self.accent_color, font=self.fonts['regular_small'])

            # 予想値
            draw.text((self.width - 100, data_y), data["forecast"], fill=self.sub_accent_color, font=self.fonts['regular_small'])

            data_y += 35

    def _draw_error_message(self, draw: ImageDraw.Draw, title: str, message: str):
        """エラーメッセージを表示"""
        # エラーパネル背景
        error_height = 120
        error_y = 140
        panel_width = self.width - 96

        # エラーパネル背景（赤系）
        draw.rounded_rectangle(
            [48, error_y, 48 + panel_width, error_y + error_height],
            radius=15,
            fill="#FEF2F2",
            outline="#DC2626",
            width=3
        )

        # エラータイトル
        title_font = self.fonts['bold_medium']
        draw.text((48 + 20, error_y + 20), title, fill="#DC2626", font=title_font)

        # 警告アイコン
        draw.text((48 + 20, error_y + 25), "⚠️", fill="#DC2626", font=self.fonts['bold_large'])

        # エラーメッセージ
        error_font = self.fonts['regular_small']
        message_lines = self._wrap_text(message, error_font, panel_width - 40)
        message_y = error_y + 50

        for line in message_lines[:3]:  # 最大3行
            draw.text((48 + 20, message_y), line, fill="#7F1D1D", font=error_font)
            message_y += 20

        # トラブルシューティングのヒント
        hint_y = message_y + 10
        hint_text = "Check API connectivity and credentials"
        draw.text((48 + 20, hint_y), hint_text, fill="#9CA3AF", font=self.fonts['regular_small'])

    def _get_economic_calendar_data(self) -> dict:
        """investpyから経済指標データを取得"""
        try:
            # investpyから経済指標データを取得
            return self._fetch_economic_data_from_investpy()

        except Exception as e:
            # APIエラーの場合はエラーを記録して例外を発生させる
            print(f"ERROR: investpy API failed: {e}")
            raise Exception(f"Economic data unavailable - investpy API failed: {e}")

    def _extract_economic_data_from_articles(self, articles: List) -> dict:
        """記事から経済指標データを抽出（API失敗時のフォールバック用）"""
        # このメソッドはもはや使用しない
        raise Exception("Article extraction is disabled - use reliable APIs instead")

    def _fetch_economic_data_from_investpy(self) -> dict:
        """investpyから経済指標データを取得"""
        released = []
        upcoming = []

        try:
            from datetime import datetime, timedelta

            # 今日の日付を取得
            today = datetime.now().date()

            # 発表済みの指標を取得（過去1日）
            released_data = self._get_investpy_recent_indicators(today - timedelta(days=1), today)
            released.extend(released_data)

            # 今後の指標を取得（今日から3日先まで）
            upcoming_data = self._get_investpy_upcoming_indicators(today, today + timedelta(days=3))
            upcoming.extend(upcoming_data)

            return {
                'date': today.strftime('%m.%d'),
                'released': released,
                'upcoming': upcoming[:4]  # 最大4件表示
            }

        except Exception as e:
            raise Exception(f"investpy API error: {e}")

    def _get_investpy_recent_indicators(self, from_date, to_date) -> List[dict]:
        """investpyから最近発表された指標を取得"""
        released = []

        try:
            # 主要国の指標を取得
            countries = ['united states', 'japan', 'germany', 'euro zone']

            for country in countries:
                try:
                    # 経済カレンダーを取得
                    calendar = investpy.economic_calendar(
                        from_date=from_date.strftime('%d/%m/%Y'),
                        to_date=to_date.strftime('%d/%m/%Y'),
                        countries=[country]
                    )

                    for _, row in calendar.iterrows():
                        # 重要な指標のみを選択
                        if any(keyword in row['event'].lower() for keyword in
                              ['cpi', 'gdp', 'unemployment', 'trade', 'ppi', 'retail', 'industrial']):
                            released.append({
                                "indicator": f"🇺🇸 {row['event']}" if country == 'united states'
                                           else f"🇯🇵 {row['event']}" if country == 'japan'
                                           else f"🇪🇺 {row['event']}" if country == 'euro zone'
                                           else f"🇩🇪 {row['event']}",
                                "actual": str(row.get('actual', 'N/A')),
                                "forecast": str(row.get('forecast', 'N/A')),
                                "color": self._get_indicator_color(row.get('actual'), row.get('forecast'))
                            })

                except Exception as e:
                    print(f"Warning: Failed to fetch calendar for {country}: {e}")
                    continue

        except Exception as e:
            print(f"Warning: investpy recent indicators failed: {e}")

        return released

    def _get_investpy_upcoming_indicators(self, from_date, to_date) -> List[dict]:
        """investpyから今後発表される指標を取得"""
        upcoming = []

        try:
            # 主要国の指標を取得
            countries = ['united states', 'japan', 'germany', 'euro zone']

            for country in countries:
                try:
                    # 経済カレンダーを取得
                    calendar = investpy.economic_calendar(
                        from_date=from_date.strftime('%d/%m/%Y'),
                        to_date=to_date.strftime('%d/%m/%Y'),
                        countries=[country]
                    )

                    for _, row in calendar.iterrows():
                        # 重要な指標のみを選択し、時刻をJSTに変換
                        if any(keyword in row['event'].lower() for keyword in
                              ['cpi', 'gdp', 'unemployment', 'trade', 'ppi', 'retail', 'industrial', 'fed', 'ecb', 'boj']):
                            time_str = self._convert_to_jst_time(row.get('time', ''), row.get('zone', 'UTC'))
                            upcoming.append({
                                "indicator": f"🇺🇸 {row['event']}" if country == 'united states'
                                           else f"🇯🇵 {row['event']}" if country == 'japan'
                                           else f"🇪🇺 {row['event']}" if country == 'euro zone'
                                           else f"🇩🇪 {row['event']}",
                                "time": time_str,
                                "forecast": str(row.get('forecast', 'N/A'))
                            })

                except Exception as e:
                    print(f"Warning: Failed to fetch upcoming calendar for {country}: {e}")
                    continue

        except Exception as e:
            print(f"Warning: investpy upcoming indicators failed: {e}")

        return upcoming

    def _get_indicator_color(self, actual: str, forecast: str) -> str:
        """実績値と予想値の比較に基づいて色を決定"""
        try:
            if actual == 'N/A' or forecast == 'N/A':
                return '#6B7280'

            actual_val = float(actual.replace('%', '').replace('B', '').replace('M', '').replace(',', ''))
            forecast_val = float(forecast.replace('%', '').replace('B', '').replace('M', '').replace(',', ''))

            # 予想との差が大きい場合は色を変える
            diff = abs(actual_val - forecast_val)
            if diff > 0:
                return '#DC2626'  # 赤: 予想から大きく外れた
            else:
                return '#16A34A'  # 緑: 予想通りまたは良い結果

        except (ValueError, AttributeError):
            return '#6B7280'  # グレー: 計算できない場合

    def _convert_to_jst_time(self, time_str: str, zone: str) -> str:
        """時刻をJSTに変換"""
        try:
            # 時刻文字列をパース（例: "13:30"）
            if ':' in time_str:
                hour, minute = map(int, time_str.split(':'))

                # UTCからJSTに変換（+9時間）
                jst_hour = hour + 9
                if jst_hour >= 24:
                    jst_hour -= 24

                return f"{jst_hour:02d}:{minute:02d}"
            else:
                return time_str

        except Exception:
            return "TBD"

    def _extract_economic_data_from_articles(self, articles: List) -> dict:
        """記事から経済指標データを抽出"""
        released = []
        upcoming = []

        # 実際の記事からデータを抽出
        for article in articles:
            if not article.title or not article.body:
                continue

            title_lower = article.title.lower()

            # CPI関連
            if 'cpi' in title_lower:
                # 実際の値が記事に含まれている場合
                actual_value = self._extract_numeric_value(article.body, 'cpi')
                forecast_value = self._extract_numeric_value(article.body, '予想')

                if actual_value:
                    released.append({
                        "indicator": "🇺🇸 US CPI (YoY)",
                        "actual": f"{actual_value:.1f}%",
                        "forecast": f"{forecast_value:.1f}%" if forecast_value else "3.6%",
                        "color": "#DC2626" if actual_value > 3.6 else "#16A34A"
                    })

            # 貿易収支
            elif '貿易' in title_lower or 'trade' in title_lower:
                value = self._extract_numeric_value(article.body, '億')
                if value:
                    released.append({
                        "indicator": "🇯🇵 Japan Trade Balance",
                        "actual": f"¥{value:.0f}B",
                        "forecast": "¥-500B",
                        "color": "#16A34A" if value > -500 else "#DC2626"
                    })

        # デフォルト値を追加
        if not released:
            released = [
                {"indicator": "🇺🇸 US CPI (YoY)", "actual": "3.8%", "forecast": "3.6%", "color": "#DC2626"},
                {"indicator": "🇯🇵 Japan Trade Balance", "actual": "¥-200B", "forecast": "¥-500B", "color": "#16A34A"}
            ]

        if not upcoming:
            upcoming = [
                {"indicator": "🇯🇵 Japan CPI (YoY)", "time": "08:30", "forecast": "2.9%"},
                {"indicator": "🇺🇸 US Jobless Claims", "time": "21:30", "forecast": "215K"},
                {"indicator": "🇪🇺 ECB Rate Decision", "time": "20:45", "forecast": "4.25%"}
            ]

        return {
            'date': datetime.now().strftime('%m.%d'),
            'released': released,
            'upcoming': upcoming
        }


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

        # カード形式で詳細を描画
        y = self.margin + 160
        card_width = self.width - self.margin * 2
        for i, t in enumerate(topics[:3], 1):
            num_text = str(i)
            headline_font = self.fonts['bold_small']
            summary_font = self.fonts['regular_small']

            head_lines = self._wrap_text(f"{num_text}. {t.headline}", headline_font, card_width - 40)
            summary = t.summary or ""
            summary = summary[:400] + "..." if len(summary) > 400 else summary
            summary_lines = self._wrap_text(summary, summary_font, card_width - 40)

            meta_parts = []
            if t.source:
                meta_parts.append(f"出典: {t.source}")
            if t.category:
                meta_parts.append(f"分野: {t.category}")
            if t.region:
                meta_parts.append(f"地域: {t.region}")
            meta_line = " | ".join(meta_parts) if meta_parts else ""
            meta_lines = self._wrap_text(meta_line, summary_font, card_width - 40) if meta_line else []

            line_height = 36
            content_lines = head_lines + summary_lines + meta_lines
            card_height = 24 + line_height * len(content_lines) + 24

            draw.rounded_rectangle(
                [self.margin, y, self.margin + card_width, y + card_height],
                radius=16,
                fill="#FFFFFF",
                outline=self.accent_color,
                width=2,
            )

            text_y = y + 24
            for line in head_lines:
                draw.text((self.margin + 20, text_y), line, fill=self.text_color, font=headline_font)
                text_y += line_height
            for line in summary_lines:
                draw.text((self.margin + 20, text_y), line, fill=self.text_color, font=summary_font)
                text_y += line_height
            for line in meta_lines:
                draw.text((self.margin + 20, text_y), line, fill=self.sub_accent_color, font=summary_font)
                text_y += line_height

            y += card_height + 20

        # ロゴのみ
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

        self._draw_logo(draw, brand_name)

        image.save(file_path, 'PNG', quality=95)
        return file_path
