# -*- coding: utf-8 -*-

"""
note投稿用マーケットデータフォーマッター
MarketDataFetcherから取得したデータをnote向けの表形式に整形
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from .region_filter import Region


class MarketDataFormatter:
    """マーケットデータをnote向けテキスト形式に整形するクラス"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初期化
        
        Args:
            logger: ロガー
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # 地域別主要指数マッピング
        self.regional_indices = {
            Region.JAPAN: {
                '^N225': '日経平均',
                '^TOPX': 'TOPIX', 
                'USDJPY=X': 'ドル/円',
                'GC=F': '金価格'
            },
            Region.USA: {
                '^GSPC': 'S&P500',
                '^IXIC': 'NASDAQ',
                '^DJI': 'ダウ平均',
                'GC=F': '金価格',
                'CL=F': 'WTI原油'
            },
            Region.EUROPE: {
                '^GDAXI': 'DAX',
                '^FTSE': 'FTSE100',
                '^FCHI': 'CAC40',
                'EURUSD=X': 'ユーロ/ドル',
                'GC=F': '金価格'
            }
        }
    
    def format_market_data_table(self, market_data: Dict[str, Any], region: Region) -> str:
        """
        市場データを地域別テーブル形式にフォーマット
        
        Args:
            market_data: MarketDataFetcherから取得した市場データ
            region: 対象地域
            
        Returns:
            str: フォーマットされた市場データテーブル
        """
        if not market_data:
            return "市場データを取得できませんでした"
        
        # 地域別の主要指数を取得
        target_indices = self.regional_indices.get(region, {})
        
        # ヘッダー
        table_lines = ["🔸 今日の主要指数・市況"]
        table_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # データが存在する指数のみ表示
        displayed_count = 0
        
        for symbol, display_name in target_indices.items():
            if symbol in market_data:
                data = market_data[symbol]
                formatted_line = self._format_single_index(display_name, data, symbol)
                if formatted_line:
                    table_lines.append(formatted_line)
                    displayed_count += 1
        
        # データがない場合
        if displayed_count == 0:
            table_lines.append("※ 市場データを取得中です")
        
        table_lines.append("")  # 空行
        return "\n".join(table_lines)
    
    def _format_single_index(self, display_name: str, data: Dict[str, Any], symbol: str) -> Optional[str]:
        """
        個別指数データをフォーマット
        
        Args:
            display_name: 表示名
            data: 指数データ
            symbol: シンボル
            
        Returns:
            str: フォーマットされた行、エラー時はNone
        """
        try:
            current_price = data.get('current_price')
            change = data.get('change')
            change_percent = data.get('change_percent')
            
            if current_price is None:
                return None
            
            # 価格フォーマット
            if 'JPY' in symbol or symbol == '^N225' or symbol == '^TOPX':
                # 日本円または日本の指数
                price_str = f"{current_price:,.0f}円" if symbol == 'USDJPY=X' else f"{current_price:,.0f}"
            elif symbol == 'EURUSD=X':
                # 為替レート
                price_str = f"{current_price:.4f}"
            elif 'GC=F' in symbol or 'CL=F' in symbol:
                # 商品
                price_str = f"{current_price:.2f}ドル"
            else:
                # その他（米国株式指数等）
                price_str = f"{current_price:,.2f}"
            
            # 変動表示
            if change is not None and change_percent is not None:
                change_sign = "+" if change > 0 else ""
                change_str = f"({change_sign}{change:.2f} / {change_sign}{change_percent:.2f}%)"
                
                # 絵文字による視覚化
                if change_percent > 0.5:
                    trend_emoji = "📈"
                elif change_percent < -0.5:
                    trend_emoji = "📉"
                else:
                    trend_emoji = "➡️"
            else:
                change_str = ""
                trend_emoji = ""
            
            # 行組み立て
            name_padded = display_name.ljust(12)  # 12文字で揃える
            return f"{trend_emoji} {name_padded}: {price_str} {change_str}"
            
        except Exception as e:
            self.logger.warning(f"指数データフォーマットエラー {display_name}: {e}")
            return None
    
    def format_market_summary(self, market_data: Dict[str, Any], region: Region) -> str:
        """
        市場サマリーをフォーマット
        
        Args:
            market_data: 市場データ
            region: 地域
            
        Returns:
            str: フォーマットされたサマリー
        """
        if not market_data:
            return "市場の動向を確認中です..."
        
        # 地域別の主要指数を分析
        target_indices = self.regional_indices.get(region, {})
        
        positive_count = 0
        negative_count = 0
        total_count = 0
        
        for symbol in target_indices.keys():
            if symbol in market_data:
                data = market_data[symbol]
                change_percent = data.get('change_percent')
                if change_percent is not None:
                    total_count += 1
                    if change_percent > 0:
                        positive_count += 1
                    elif change_percent < 0:
                        negative_count += 1
        
        if total_count == 0:
            return "市場データを分析中です..."
        
        # 市場センチメント判定
        if positive_count > negative_count:
            sentiment = "強気"
            emoji = "📈"
        elif negative_count > positive_count:
            sentiment = "弱気" 
            emoji = "📉"
        else:
            sentiment = "様子見"
            emoji = "➡️"
        
        region_names = {
            Region.JAPAN: "日本市場",
            Region.USA: "米国市場", 
            Region.EUROPE: "欧州市場"
        }
        
        market_name = region_names.get(region, "市場")
        
        return f"{emoji} {market_name}は全体的に{sentiment}ムードです（上昇{positive_count}・下落{negative_count}・横ばい{total_count-positive_count-negative_count}）"
    
    def format_currency_section(self, market_data: Dict[str, Any]) -> str:
        """
        為替セクションをフォーマット
        
        Args:
            market_data: 市場データ
            
        Returns:
            str: フォーマットされた為替情報
        """
        currency_symbols = {
            'USDJPY=X': 'ドル/円',
            'EURUSD=X': 'ユーロ/ドル',
            'GBPUSD=X': 'ポンド/ドル'
        }
        
        currency_lines = ["🔸 為替動向"]
        currency_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
        
        displayed = False
        for symbol, name in currency_symbols.items():
            if symbol in market_data:
                data = market_data[symbol]
                formatted_line = self._format_single_index(name, data, symbol)
                if formatted_line:
                    currency_lines.append(formatted_line)
                    displayed = True
        
        if not displayed:
            currency_lines.append("※ 為替データを取得中です")
        
        currency_lines.append("")
        return "\n".join(currency_lines)
    
    def format_commodities_section(self, market_data: Dict[str, Any]) -> str:
        """
        商品セクションをフォーマット
        
        Args:
            market_data: 市場データ
            
        Returns:
            str: フォーマットされた商品情報
        """
        commodity_symbols = {
            'GC=F': '金先物',
            'CL=F': 'WTI原油',
            'BTC-USD': 'ビットコイン'
        }
        
        commodity_lines = ["🔸 商品・暗号通貨"]
        commodity_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
        
        displayed = False
        for symbol, name in commodity_symbols.items():
            if symbol in market_data:
                data = market_data[symbol]
                formatted_line = self._format_single_index(name, data, symbol)
                if formatted_line:
                    commodity_lines.append(formatted_line)
                    displayed = True
        
        if not displayed:
            commodity_lines.append("※ 商品データを取得中です")
        
        commodity_lines.append("")
        return "\n".join(commodity_lines)
    
    def get_market_timestamp(self, market_data: Dict[str, Any]) -> str:
        """
        市場データのタイムスタンプを取得
        
        Args:
            market_data: 市場データ
            
        Returns:
            str: タイムスタンプ文字列
        """
        # 最初に見つかったデータからタイムスタンプを取得
        for data in market_data.values():
            if isinstance(data, dict) and 'timestamp' in data:
                timestamp = data['timestamp']
                if isinstance(timestamp, datetime):
                    return f"データ取得時刻: {timestamp.strftime('%Y/%m/%d %H:%M')}"
                elif isinstance(timestamp, str):
                    return f"データ取得時刻: {timestamp}"
        
        return f"データ取得時刻: {datetime.now().strftime('%Y/%m/%d %H:%M')}"