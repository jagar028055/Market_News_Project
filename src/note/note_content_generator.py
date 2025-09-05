# -*- coding: utf-8 -*-

"""
note投稿用コンテンツ生成クラス
Gemini 2.5 Flash-Lite APIを使用してカジュアルな記事を生成
"""

from typing import List, Dict, Any, Optional
import logging
import os
import json
from datetime import datetime, timezone
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    print("Warning: google-generativeai not installed. Using fallback mode.")
from .region_filter import Region, RegionFilter
from .note_templates import NoteTemplate
from .market_data_formatter import MarketDataFormatter


class NoteContentGenerator:
    """note投稿用コンテンツ生成クラス"""
    
    def __init__(self, 
                 gemini_api_key: Optional[str] = None,
                 logger: Optional[logging.Logger] = None):
        """
        初期化
        
        Args:
            gemini_api_key: Gemini APIキー
            logger: ロガー
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Gemini API設定
        api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        if not api_key and HAS_GENAI:
            raise ValueError("Gemini APIキーが設定されていません")
        
        if HAS_GENAI:
            genai.configure(api_key=api_key)
            
            # Gemini 2.5 Flash-Lite モデル設定
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # 生成設定
            self.generation_config = genai.types.GenerationConfig(
                temperature=0.7,  # カジュアルさのための適度なランダム性
                max_output_tokens=1500,  # 1000文字目安
                top_p=0.9
            )
        else:
            self.model = None
            self.generation_config = None
        
        # コンポーネント初期化
        self.region_filter = RegionFilter(logger)
        self.market_data_formatter = MarketDataFormatter(logger)
        
        # MarketDataFetcherを初期化（インポートエラー対応）
        try:
            from ..market_data.fetcher import MarketDataFetcher
            self.market_data_fetcher = MarketDataFetcher(logger=logger)
            self.logger.info("MarketDataFetcher initialized successfully")
        except ImportError as e:
            self.logger.warning(f"MarketDataFetcher not available: {e}")
            self.market_data_fetcher = None
        
        self.logger.info("NoteContentGenerator initialized with Gemini 2.5 Flash-Lite")
    
    def _generate_fallback_note(self, region: Region, articles: List[Dict[str, Any]], date: datetime) -> str:
        """
        フォールバック: テンプレートベースの記事生成
        
        Args:
            region: 地域
            articles: 記事データ
            date: 日付
            
        Returns:
            str: 生成されたマークダウン記事
        """
        self.logger.info(f"フォールバックモードで{region.value}記事を生成中...")
        
        # マーケットデータを取得（可能であれば）
        market_data = {}
        if self.market_data_fetcher:
            try:
                market_data = self._fetch_market_data()
            except Exception as e:
                self.logger.warning(f"Market data fetch failed in fallback mode: {e}")
        
        # テンプレート取得
        template = NoteTemplate.get_base_template(region, date)
        
        # マーケットデータテーブル
        market_data_table = self.market_data_formatter.format_market_data_table(market_data, region)
        
        # 記事要約（note向けフォーマット）
        main_news = "\n".join([f"{i+1}. {article['title']}\n\n{article.get('summary', '')[:150]}...\n\n出典: {article.get('source', '不明')}\n" 
                              for i, article in enumerate(articles[:3])])
        
        # 市場概況
        overview = self.market_data_formatter.format_market_summary(market_data, region)
        
        # 地域別展望カスタマイズ
        if region == Region.JAPAN:
            outlook = "• 日銀の金融政策動向\n• 主要企業の業績発表\n• 為替レートの影響\n\n今後も日本株式市場の動向に注目です 🇯🇵"
        elif region == Region.USA:
            outlook = "• FRBの政策金利動向\n• 主要テック企業の決算\n• インフレ動向\n\n引き続き米国株式市場の動きに注目しましょう 🇺🇸"
        else:  # EUROPE
            outlook = "• ECBの金融政策\n• ユーロ圏の経済指標\n• 地政学的リスク\n\n欧州経済の動向を引き続き注視していきます 🇪🇺"
        
        # タイムスタンプ
        timestamp = self.market_data_formatter.get_market_timestamp(market_data)
        
        # テンプレート埋め込み
        content = template.format(
            market_data_table=market_data_table,
            market_overview=overview,
            main_news=main_news,
            outlook=outlook,
            timestamp=timestamp
        )
        
        return content
    
    def _fetch_market_data(self) -> Dict[str, Any]:
        """
        マーケットデータを取得
        
        Returns:
            Dict[str, Any]: 取得した市場データ
        """
        if not self.market_data_fetcher:
            self.logger.warning("MarketDataFetcher not available")
            return {}
        
        try:
            self.logger.info("マーケットデータを取得中...")
            
            # 主要指数リスト
            major_symbols = [
                '^N225',    # 日経平均
                '^TOPX',    # TOPIX
                '^GSPC',    # S&P500
                '^IXIC',    # NASDAQ
                '^DJI',     # ダウ平均
                '^GDAXI',   # DAX
                '^FTSE',    # FTSE100
                '^FCHI',    # CAC40
                'USDJPY=X', # ドル円
                'EURUSD=X', # ユーロドル
                'GC=F',     # 金先物
                'CL=F'      # WTI原油
            ]
            
            # データ取得
            market_snapshot = self.market_data_fetcher.get_current_snapshot(
                symbols=major_symbols,
                include_trends=True
            )
            
            if market_snapshot and market_snapshot.data:
                self.logger.info(f"マーケットデータ取得完了: {len(market_snapshot.data)}件")
                
                # MarketDataオブジェクトを辞書形式に変換
                market_data_dict = {}
                for symbol, market_data in market_snapshot.data.items():
                    market_data_dict[symbol] = {
                        'current_price': market_data.current_price,
                        'change': market_data.change,
                        'change_percent': market_data.change_percent,
                        'timestamp': market_data.timestamp,
                        'volume': getattr(market_data, 'volume', None)
                    }
                
                return market_data_dict
            else:
                self.logger.warning("マーケットデータが取得できませんでした")
                return {}
                
        except Exception as e:
            self.logger.error(f"マーケットデータ取得エラー: {e}")
            return {}
    
    def generate_regional_notes(self, 
                              articles: List[Dict[str, Any]], 
                              date: Optional[datetime] = None,
                              market_data: Optional[Dict[str, Any]] = None) -> Dict[Region, str]:
        """
        地域別note記事を生成
        
        Args:
            articles: 記事リスト
            date: 生成日時
            market_data: 市場データ
            
        Returns:
            Dict[Region, str]: 地域別生成記事
        """
        if date is None:
            date = datetime.now(timezone.utc)
        
        self.logger.info(f"地域別note記事生成開始: {len(articles)}件の記事から")
        
        # マーケットデータを取得（まだ取得されていない場合）
        if market_data is None:
            market_data = self._fetch_market_data()
        
        # 記事を地域別に分類
        regional_articles = self.region_filter.filter_articles_by_region(articles)
        
        generated_notes = {}
        
        # 各地域の記事を生成
        for region in [Region.JAPAN, Region.USA, Region.EUROPE]:
            region_articles = regional_articles[region]
            
            if len(region_articles) == 0:
                self.logger.warning(f"{region.value}の記事が見つかりません")
                continue
            
            try:
                note_content = self._generate_single_regional_note(
                    region, region_articles, date, market_data
                )
                generated_notes[region] = note_content
                self.logger.info(f"{region.value}の記事生成完了")
                
            except Exception as e:
                self.logger.error(f"{region.value}の記事生成でエラー: {e}")
                # エラー時はテンプレートのみで生成
                generated_notes[region] = self._generate_fallback_note(region, region_articles, date)
        
        return generated_notes
    
    def _generate_single_regional_note(self, 
                                     region: Region,
                                     articles: List[Dict[str, Any]],
                                     date: datetime,
                                     market_data: Optional[Dict[str, Any]] = None) -> str:
        """
        単一地域のnote記事を生成
        
        Args:
            region: 地域
            articles: 記事リスト
            date: 日付
            market_data: 市場データ
            
        Returns:
            str: 生成されたnote記事
        """
        # プロンプト生成
        prompt = self._create_generation_prompt(region, articles, market_data)
        
        # Gemini APIで生成
        if not HAS_GENAI or self.model is None:
            # フォールバック: テンプレートベースの生成
            self.logger.warning("Gemini APIが利用できません。フォールバックモードを使用します")
            return self._generate_fallback_note(region, articles, date)
            
        response = self.model.generate_content(
            prompt,
            generation_config=self.generation_config
        )
        
        if not response.text:
            raise ValueError("Gemini APIからレスポンスが得られませんでした")
        
        # テンプレートと統合  
        base_template = NoteTemplate.get_base_template(region, date)
        
        # マーケットデータテーブル生成
        market_data_table = self.market_data_formatter.format_market_data_table(market_data or {}, region)
        
        # AI生成コンテンツをテンプレートに挿入
        note_content = self._integrate_with_template(
            base_template, response.text, region, articles, market_data or {}, market_data_table
        )
        
        return note_content
    
    def _create_generation_prompt(self, 
                                region: Region, 
                                articles: List[Dict[str, Any]], 
                                market_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Gemini用のプロンプトを生成
        
        Args:
            region: 地域
            articles: 記事リスト
            market_data: 市場データ
            
        Returns:
            str: 生成プロンプト
        """
        region_configs = {
            Region.JAPAN: {
                'name': '日本',
                'focus': '日経平均、TOPIX、東証、日本企業、日銀',
                'tone': 'カジュアルで親しみやすく、投資初心者にもわかりやすく'
            },
            Region.USA: {
                'name': '米国',
                'focus': 'S&P500、NASDAQ、ダウ、米国企業、FED',
                'tone': 'カジュアルで親しみやすく、投資初心者にもわかりやすく'
            },
            Region.EUROPE: {
                'name': '欧州',
                'focus': 'DAX、FTSE100、CAC40、欧州企業、ECB',
                'tone': 'カジュアルで親しみやすく、投資初心者にもわかりやすく'
            }
        }
        
        config = region_configs.get(region, region_configs[Region.JAPAN])
        
        # 記事データを整理
        article_summaries = []
        for i, article in enumerate(articles[:8]):  # 最大8件
            title = article.get('title', '')
            summary = article.get('summary', '')
            source = article.get('source', '')
            
            article_summaries.append(f"""
記事{i+1}:
タイトル: {title}
要約: {summary}
出典: {source}
""")
        
        market_context = ""
        if market_data:
            # 市場データから重要な指数を抽出
            relevant_data = {}
            regional_symbols = {
                Region.JAPAN: ['^N225', '^TOPX', 'USDJPY=X'],
                Region.USA: ['^GSPC', '^IXIC', '^DJI'],
                Region.EUROPE: ['^GDAXI', '^FTSE', '^FCHI', 'EURUSD=X']
            }
            
            for symbol in regional_symbols.get(region, []):
                if symbol in market_data:
                    relevant_data[symbol] = market_data[symbol]
            
            if relevant_data:
                market_context = f"""
市場データ (記事作成で必ず活用すること):
{json.dumps(relevant_data, ensure_ascii=False, indent=2)}
"""
        
        prompt = f"""
あなたは{config['name']}市場の専門知識を持つnoteライターです。
以下の記事情報を基に、{config['name']}市場に焦点を当てたnote投稿用の記事を生成してください。

## 要求仕様:
- 対象読者: 投資初心者〜中級者
- 文字数: 800-1000文字程度  
- トーン: {config['tone']}
- 重点分野: {config['focus']}
- 形式: 以下の3つのセクション

### 必要なセクション:
1. 市場概況 (150-200文字) - 上記の市場データを必ず含めて数値で説明
2. 主要ニュース解説 (500-600文字) - 3-4つの重要ニュースをピックアップ
3. 明日への展望 (150-200文字)

## 注意点:
- 市場データが提供されている場合は、必ず具体的な数値を記事に含める
- 専門用語は使うが、簡単な説明も添える  
- 断定的な投資アドバイスは避ける
- 「〜かもしれません」「〜と思われます」など推測表現を使う
- 絵文字は使わない（テンプレートで追加するため）
- 投資は自己責任である旨を適度に盛り込む
- note用のため、Markdown記法（#, **, *など）は一切使わない

{market_context}

## 記事データ:
{"".join(article_summaries)}

上記の情報を基に、{config['name']}市場に特化したnote記事を生成してください。
各セクションは明確に分けて出力し、読みやすく整理してください。
"""
        
        return prompt
    
    def _integrate_with_template(self, 
                               template: str, 
                               ai_content: str, 
                               region: Region,
                               articles: List[Dict[str, Any]],
                               market_data: Dict[str, Any],
                               market_data_table: str) -> str:
        """
        テンプレートとAI生成コンテンツを統合
        
        Args:
            template: ベーステンプレート
            ai_content: AI生成コンテンツ
            region: 地域
            articles: 記事リスト
            market_data: 市場データ
            market_data_table: フォーマット済み市場データ表
            
        Returns:
            str: 統合されたコンテンツ
        """
        try:
            # AI生成コンテンツをセクション別に分割
            sections = self._parse_ai_content(ai_content)
            
            # タイムスタンプ生成
            timestamp = self.market_data_formatter.get_market_timestamp(market_data)
            
            # テンプレートのプレースホルダーを置換
            integrated_content = template.replace(
                '{market_data_table}', market_data_table
            ).replace(
                '{market_overview}', sections.get('market_overview', '')
            ).replace(
                '{main_news}', sections.get('main_news', '')
            ).replace(
                '{outlook}', sections.get('outlook', '')
            ).replace(
                '{timestamp}', timestamp
            )
            
            return integrated_content
            
        except Exception as e:
            self.logger.error(f"テンプレート統合エラー: {e}")
            # フォールバックとしてテンプレートメソッドを使用
            return self._generate_fallback_note(region, articles, datetime.now(timezone.utc))
    
    def _parse_ai_content(self, content: str) -> Dict[str, str]:
        """
        AI生成コンテンツをセクション別に解析
        
        Args:
            content: AI生成コンテンツ
            
        Returns:
            Dict[str, str]: セクション別コンテンツ
        """
        sections = {
            'market_overview': '',
            'main_news': '',
            'outlook': ''
        }
        
        # 簡単なパターンマッチングでセクションを分割
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if '市場概況' in line or '概況' in line:
                current_section = 'market_overview'
                continue
            elif '主要ニュース' in line or 'ニュース' in line:
                current_section = 'main_news'
                continue
            elif '展望' in line or '明日' in line:
                current_section = 'outlook'
                continue
            
            if current_section and line:
                sections[current_section] += line + '\n'
        
        # セクションが空の場合はコンテンツ全体を分割
        if not any(sections.values()):
            content_parts = content.split('\n\n')
            if len(content_parts) >= 3:
                sections['market_overview'] = content_parts[0]
                sections['main_news'] = '\n\n'.join(content_parts[1:-1])
                sections['outlook'] = content_parts[-1]
            else:
                sections['main_news'] = content
        
        return sections
    
    def _generate_fallback_note(self, 
                              region: Region, 
                              articles: List[Dict[str, Any]], 
                              date: datetime) -> str:
        """
        フォールバック用のnote記事を生成（AI生成失敗時）
        
        Args:
            region: 地域
            articles: 記事リスト
            date: 日付
            
        Returns:
            str: フォールバック記事
        """
        self.logger.info(f"{region.value}のフォールバック記事を生成")
        
        template = NoteTemplate.get_base_template(region, date)
        market_overview = NoteTemplate.format_market_overview(region, articles)
        main_news = NoteTemplate.format_main_news(articles)
        outlook = NoteTemplate.format_outlook(region, articles)
        
        return template.replace(
            '{market_overview}', market_overview
        ).replace(
            '{main_news}', main_news
        ).replace(
            '{outlook}', outlook
        )
    
    def save_notes_to_files(self, 
                           regional_notes: Dict[Region, str], 
                           output_dir: str = "notes",
                           date: Optional[datetime] = None) -> Dict[Region, str]:
        """
        生成されたnoteをファイルに保存
        
        Args:
            regional_notes: 地域別note記事
            output_dir: 出力ディレクトリ
            date: 日付
            
        Returns:
            Dict[Region, str]: 地域別保存ファイルパス
        """
        if date is None:
            date = datetime.now(timezone.utc)
        
        os.makedirs(output_dir, exist_ok=True)
        saved_files = {}
        
        for region, content in regional_notes.items():
            filename = NoteTemplate.generate_filename(region, date)
            filepath = os.path.join(output_dir, filename)
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                saved_files[region] = filepath
                self.logger.info(f"{region.value}の記事を保存: {filepath}")
                
            except Exception as e:
                self.logger.error(f"{region.value}のファイル保存エラー: {e}")
        
        return saved_files
    
    def generate_and_save_all(self, 
                            articles: List[Dict[str, Any]],
                            output_dir: str = "notes",
                            date: Optional[datetime] = None,
                            market_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        全地域のnote記事生成・保存を一括実行
        
        Args:
            articles: 記事リスト
            output_dir: 出力ディレクトリ
            date: 日付
            market_data: 市場データ
            
        Returns:
            Dict: 実行結果
        """
        if date is None:
            date = datetime.now(timezone.utc)
        
        self.logger.info("note記事一括生成・保存開始")
        
        try:
            # 記事生成
            regional_notes = self.generate_regional_notes(articles, date, market_data)
            
            # ファイル保存
            saved_files = self.save_notes_to_files(regional_notes, output_dir, date)
            
            result = {
                'success': True,
                'generated_regions': list(regional_notes.keys()),
                'saved_files': saved_files,
                'generation_time': datetime.now(timezone.utc).isoformat(),
                'article_count': len(articles)
            }
            
            self.logger.info(f"note記事一括生成完了: {len(saved_files)}ファイル")
            return result
            
        except Exception as e:
            self.logger.error(f"note記事一括生成エラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'generation_time': datetime.now(timezone.utc).isoformat()
            }