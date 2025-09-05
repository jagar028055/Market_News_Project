# -*- coding: utf-8 -*-

"""
Stooq API連携クライアント
無料のStooq APIを使用して市場データを取得
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
from urllib.parse import urljoin

from .models import MarketData, StockIndex, CurrencyPair, CommodityPrice, MarketDataType


class StooqClient:
    """Stooq APIクライアント"""

    BASE_URL = "https://stooq.com/q/d/l/"

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

    def get_current_price(self, symbol: str) -> Optional[MarketData]:
        """
        指定シンボルの現在価格を取得

        Args:
            symbol: 銘柄シンボル (例: "^SPX", "USDJPY", "GC")

        Returns:
            MarketData: 取得したデータ、失敗時はNone
        """
        try:
            # Stooq形式にシンボルを変換
            stooq_symbol = self._convert_to_stooq_symbol(symbol)

            # 過去2日分のデータを取得して現在価格と前日比を算出
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)  # 週末を考慮して5日前から

            params = {
                "s": stooq_symbol,
                "d1": start_date.strftime("%Y%m%d"),
                "d2": end_date.strftime("%Y%m%d"),
                "i": "d",  # daily
                "c": "0",  # CSV format
            }

            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            # CSVデータをパース
            lines = response.text.strip().split("\n")
            if len(lines) < 2:
                self.logger.warning(f"Insufficient data for symbol: {symbol}")
                return None

            # ヘッダーをスキップして最新データを取得
            data_lines = [line for line in lines[1:] if line.strip()]
            if len(data_lines) < 2:
                self.logger.warning(f"Need at least 2 data points for {symbol}")
                return None

            # 最新データと前日データを解析
            latest_data = data_lines[-1].split(",")
            previous_data = data_lines[-2].split(",")

            if len(latest_data) < 6 or len(previous_data) < 6:
                self.logger.warning(f"Invalid data format for {symbol}")
                return None

            # データ解析
            current_price = float(latest_data[4])  # Close price
            previous_close = float(previous_data[4])
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close != 0 else 0
            volume = float(latest_data[5]) if latest_data[5] and latest_data[5] != "0" else None

            # データタイプと名前を判定
            data_type, name = self._determine_data_type_and_name(symbol)

            # 適切なデータクラスを作成
            if data_type == MarketDataType.STOCK_INDEX:
                return StockIndex(
                    symbol=symbol,
                    name=name,
                    current_price=current_price,
                    previous_close=previous_close,
                    change=change,
                    change_percent=change_percent,
                    timestamp=datetime.now(),
                    data_type=data_type,
                    currency="USD",  # デフォルト
                    volume=volume,
                    source="stooq",
                )
            elif data_type == MarketDataType.CURRENCY_PAIR:
                return CurrencyPair(
                    symbol=symbol,
                    name=name,
                    current_price=current_price,
                    previous_close=previous_close,
                    change=change,
                    change_percent=change_percent,
                    timestamp=datetime.now(),
                    data_type=data_type,
                    currency="USD",
                    volume=volume,
                    source="stooq",
                )
            elif data_type == MarketDataType.COMMODITY:
                return CommodityPrice(
                    symbol=symbol,
                    name=name,
                    current_price=current_price,
                    previous_close=previous_close,
                    change=change,
                    change_percent=change_percent,
                    timestamp=datetime.now(),
                    data_type=data_type,
                    currency="USD",
                    volume=volume,
                    source="stooq",
                )
            else:
                return MarketData(
                    symbol=symbol,
                    name=name,
                    current_price=current_price,
                    previous_close=previous_close,
                    change=change,
                    change_percent=change_percent,
                    timestamp=datetime.now(),
                    data_type=data_type,
                    currency="USD",
                    volume=volume,
                    source="stooq",
                )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Stooq API request failed for {symbol}: {e}")
            return None
        except (ValueError, IndexError) as e:
            self.logger.error(f"Data parsing failed for {symbol}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error for {symbol}: {e}")
            return None

    def get_multiple_prices(self, symbols: List[str]) -> List[MarketData]:
        """
        複数銘柄の価格を一括取得

        Args:
            symbols: 銘柄シンボルのリスト

        Returns:
            List[MarketData]: 取得成功したデータのリスト
        """
        results = []
        for symbol in symbols:
            data = self.get_current_price(symbol)
            if data:
                results.append(data)
            else:
                self.logger.warning(f"Failed to fetch data for {symbol}")

        self.logger.info(f"Successfully fetched {len(results)}/{len(symbols)} symbols from Stooq")
        return results

    def _convert_to_stooq_symbol(self, symbol: str) -> str:
        """
        シンボルをStooq形式に変換

        Args:
            symbol: 元のシンボル

        Returns:
            str: Stooq形式のシンボル
        """
        # 主要な変換ルール
        conversions = {
            # 株価指数
            "^SPX": "spx.us",
            "^GSPC": "spx.us",
            "^DJI": "dji.us",
            "^IXIC": "ndq.us",
            "^N225": "nk225.jp",
            "^FTSE": "ftse.uk",
            "^GDAXI": "wig20.pl",  # DAXは直接取得が困難な場合の代替
            # 通貨ペア
            "USDJPY": "usdjpy",
            "EURUSD": "eurusd",
            "GBPUSD": "gbpusd",
            "USDCHF": "usdchf",
            "AUDUSD": "audusd",
            "USDCAD": "usdcad",
            # 商品
            "GC=F": "gc.f",  # 金
            "SI=F": "si.f",  # 銀
            "CL=F": "cl.f",  # WTI原油
            "BZ=F": "bz.f",  # ブレント原油
        }

        return conversions.get(symbol, symbol.lower())

    def _determine_data_type_and_name(self, symbol: str) -> tuple[MarketDataType, str]:
        """
        シンボルからデータタイプと名前を判定

        Args:
            symbol: 銘柄シンボル

        Returns:
            tuple: (データタイプ, 名前)
        """
        # シンボルパターンによる判定
        if symbol.startswith("^") or "index" in symbol.lower():
            return MarketDataType.STOCK_INDEX, self._get_stock_index_name(symbol)
        elif any(pair in symbol.upper() for pair in ["USD", "EUR", "GBP", "JPY"]):
            return MarketDataType.CURRENCY_PAIR, self._get_currency_pair_name(symbol)
        elif any(commodity in symbol.upper() for commodity in ["GC", "SI", "CL", "BZ", "HG"]):
            return MarketDataType.COMMODITY, self._get_commodity_name(symbol)
        else:
            return MarketDataType.STOCK_INDEX, symbol  # デフォルト

    def _get_stock_index_name(self, symbol: str) -> str:
        """株価指数名を取得"""
        names = {
            "^SPX": "S&P 500",
            "^GSPC": "S&P 500",
            "^DJI": "Dow Jones Industrial Average",
            "^IXIC": "NASDAQ Composite",
            "^N225": "日経平均株価",
            "^FTSE": "FTSE 100",
            "^GDAXI": "DAX",
        }
        return names.get(symbol, symbol)

    def _get_currency_pair_name(self, symbol: str) -> str:
        """通貨ペア名を取得"""
        names = {
            "USDJPY": "USD/JPY",
            "EURUSD": "EUR/USD",
            "GBPUSD": "GBP/USD",
            "USDCHF": "USD/CHF",
            "AUDUSD": "AUD/USD",
            "USDCAD": "USD/CAD",
        }
        return names.get(symbol.upper(), symbol)

    def _get_commodity_name(self, symbol: str) -> str:
        """商品名を取得"""
        names = {
            "GC=F": "Gold",
            "SI=F": "Silver",
            "CL=F": "WTI Crude Oil",
            "BZ=F": "Brent Crude Oil",
            "HG=F": "Copper",
        }
        return names.get(symbol, symbol)

    def test_connection(self) -> bool:
        """接続テスト"""
        try:
            test_data = self.get_current_price("^SPX")
            return test_data is not None
        except Exception as e:
            self.logger.error(f"Stooq connection test failed: {e}")
            return False
