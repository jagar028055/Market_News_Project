# -*- coding: utf-8 -*-

"""
Yahoo Finance連携クライアント
無料のyfinanceライブラリを使用して市場データを取得
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import pandas as pd

from .models import MarketData, StockIndex, CurrencyPair, CommodityPrice, MarketDataType


class YahooFinanceClient:
    """Yahoo Finance APIクライアント"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def get_current_price(self, symbol: str) -> Optional[MarketData]:
        """
        指定シンボルの現在価格を取得

        Args:
            symbol: 銘柄シンボル (例: "^GSPC", "USDJPY=X", "GC=F")

        Returns:
            MarketData: 取得したデータ、失敗時はNone
        """
        try:
            # Yahoo Finance形式にシンボルを変換
            yf_symbol = self._convert_to_yahoo_symbol(symbol)

            # ティッカーオブジェクト作成
            ticker = yf.Ticker(yf_symbol)

            # 基本情報を取得
            info = ticker.info
            if not info or "regularMarketPrice" not in info:
                self.logger.warning(f"No market data available for symbol: {symbol}")
                return None

            # 価格データを取得
            current_price = info.get("regularMarketPrice", 0)
            previous_close = info.get("previousClose", 0)

            if current_price == 0 or previous_close == 0:
                self.logger.warning(f"Invalid price data for symbol: {symbol}")
                return None

            change = current_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close != 0 else 0

            # 追加データを取得
            volume = info.get("volume") or info.get("regularMarketVolume")
            market_cap = info.get("marketCap")
            currency = info.get("currency", "USD")

            # データタイプと名前を判定
            data_type, name = self._determine_data_type_and_name(symbol, info)

            # 適切なデータクラスを作成
            common_attrs = {
                "symbol": symbol,
                "name": name,
                "current_price": current_price,
                "previous_close": previous_close,
                "change": change,
                "change_percent": change_percent,
                "timestamp": datetime.now(),
                "currency": currency,
                "volume": volume,
                "market_cap": market_cap,
                "source": "yahoo_finance",
            }

            if data_type == MarketDataType.STOCK_INDEX:
                region = self._determine_region(symbol)
                return StockIndex(region=region, **common_attrs)
            elif data_type == MarketDataType.CURRENCY_PAIR:
                return CurrencyPair(**common_attrs)
            elif data_type == MarketDataType.COMMODITY:
                unit = self._determine_commodity_unit(symbol)
                return CommodityPrice(unit=unit, **common_attrs)
            else:
                return MarketData(data_type=data_type, **common_attrs)

        except Exception as e:
            self.logger.error(f"Yahoo Finance API failed for {symbol}: {e}")
            return None

    def get_historical_data(self, symbol: str, period: str = "5d") -> Optional[pd.DataFrame]:
        """
        履歴データを取得

        Args:
            symbol: 銘柄シンボル
            period: 取得期間 ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")

        Returns:
            pd.DataFrame: 履歴データ、失敗時はNone
        """
        try:
            yf_symbol = self._convert_to_yahoo_symbol(symbol)
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                self.logger.warning(f"No historical data available for {symbol}")
                return None

            return hist

        except Exception as e:
            self.logger.error(f"Failed to get historical data for {symbol}: {e}")
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

        # Yahoo Financeの一括取得機能を使用
        try:
            yf_symbols = [self._convert_to_yahoo_symbol(symbol) for symbol in symbols]
            tickers = yf.Tickers(" ".join(yf_symbols))

            for i, symbol in enumerate(symbols):
                try:
                    yf_symbol = yf_symbols[i]
                    ticker = (
                        tickers.tickers[yf_symbol]
                        if hasattr(tickers, "tickers")
                        else yf.Ticker(yf_symbol)
                    )

                    info = ticker.info
                    if not info or "regularMarketPrice" not in info:
                        continue

                    data = self.get_current_price(symbol)
                    if data:
                        results.append(data)

                except Exception as e:
                    self.logger.warning(f"Failed to process {symbol}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Batch fetch failed, falling back to individual requests: {e}")
            # フォールバック: 個別取得
            for symbol in symbols:
                data = self.get_current_price(symbol)
                if data:
                    results.append(data)

        self.logger.info(
            f"Successfully fetched {len(results)}/{len(symbols)} symbols from Yahoo Finance"
        )
        return results

    def _convert_to_yahoo_symbol(self, symbol: str) -> str:
        """
        シンボルをYahoo Finance形式に変換

        Args:
            symbol: 元のシンボル

        Returns:
            str: Yahoo Finance形式のシンボル
        """
        # Yahoo Finance形式への変換ルール
        conversions = {
            # 通貨ペアの変換
            "USDJPY": "USDJPY=X",
            "EURUSD": "EURUSD=X",
            "GBPUSD": "GBPUSD=X",
            "USDCHF": "USDCHF=X",
            "AUDUSD": "AUDUSD=X",
            "USDCAD": "USDCAD=X",
            "USD/JPY": "USDJPY=X",
            "EUR/USD": "EURUSD=X",
            "GBP/USD": "GBPUSD=X",
            "USD/CHF": "USDCHF=X",
            "AUD/USD": "AUDUSD=X",
            "USD/CAD": "USDCAD=X",
            # 仮想通貨の変換
            "BTCUSD": "BTC-USD",
            "ETHUSD": "ETH-USD",
            "BTC/USD": "BTC-USD",
            "ETH/USD": "ETH-USD",
        }

        # 既に正しい形式の場合はそのまま返す
        if symbol in conversions.values():
            return symbol

        return conversions.get(symbol, symbol)

    def _determine_data_type_and_name(
        self, symbol: str, info: Dict[str, Any]
    ) -> tuple[MarketDataType, str]:
        """
        シンボルと情報からデータタイプと名前を判定

        Args:
            symbol: 銘柄シンボル
            info: Yahoo Finance情報辞書

        Returns:
            tuple: (データタイプ, 名前)
        """
        # Yahoo Financeの種別情報を使用
        quote_type = info.get("quoteType", "").upper()
        long_name = info.get("longName", symbol)
        short_name = info.get("shortName", symbol)

        # クォートタイプによる判定
        if quote_type in ["INDEX", "EQUITY"] and (
            symbol.startswith("^") or "index" in long_name.lower()
        ):
            return MarketDataType.STOCK_INDEX, long_name or short_name
        elif quote_type == "CURRENCY" or symbol.endswith("=X"):
            return MarketDataType.CURRENCY_PAIR, short_name or symbol
        elif quote_type == "FUTURE" or symbol.endswith("=F"):
            return MarketDataType.COMMODITY, long_name or short_name
        elif quote_type == "CRYPTOCURRENCY" or symbol.endswith("-USD"):
            return MarketDataType.CRYPTOCURRENCY, long_name or short_name
        elif "bond" in long_name.lower() or "treasury" in long_name.lower():
            return MarketDataType.BOND_YIELD, long_name or short_name
        elif "vix" in symbol.lower() or "volatility" in long_name.lower():
            return MarketDataType.VOLATILITY_INDEX, long_name or short_name
        else:
            return MarketDataType.STOCK_INDEX, long_name or short_name  # デフォルト

    def _determine_region(self, symbol: str) -> str:
        """株価指数の地域を判定"""
        region_mapping = {
            "^GSPC": "usa",
            "^DJI": "usa",
            "^IXIC": "usa",
            "^RUT": "usa",
            "^N225": "japan",
            "^NKX": "japan",
            "^FTSE": "europe",
            "^GDAXI": "europe",
            "^FCHI": "europe",
            "^HSI": "china",
            "000001.SS": "china",
        }
        return region_mapping.get(symbol, "global")

    def _determine_commodity_unit(self, symbol: str) -> str:
        """商品の単位を判定"""
        unit_mapping = {
            "GC=F": "ounce",  # 金
            "SI=F": "ounce",  # 銀
            "PL=F": "ounce",  # プラチナ
            "CL=F": "barrel",  # WTI原油
            "BZ=F": "barrel",  # ブレント原油
            "NG=F": "MMBtu",  # 天然ガス
            "HG=F": "pound",  # 銅
            "ZC=F": "bushel",  # トウモロコシ
            "ZW=F": "bushel",  # 小麦
        }
        return unit_mapping.get(symbol, "unit")

    def get_market_summary(self) -> Dict[str, Any]:
        """主要市場のサマリーを取得"""
        major_symbols = [
            "^GSPC",  # S&P 500
            "^DJI",  # Dow Jones
            "^IXIC",  # NASDAQ
            "^N225",  # 日経平均
            "^FTSE",  # FTSE 100
            "USDJPY=X",  # USD/JPY
            "EURUSD=X",  # EUR/USD
            "GC=F",  # Gold
            "CL=F",  # WTI Oil
        ]

        summary_data = self.get_multiple_prices(major_symbols)

        return {
            "timestamp": datetime.now().isoformat(),
            "data_count": len(summary_data),
            "symbols": [data.symbol for data in summary_data],
            "major_movers": [
                data.to_dict() for data in summary_data if abs(data.change_percent) >= 1.0
            ][
                :5
            ],  # 上位5つの値動き
        }

    def test_connection(self) -> bool:
        """接続テスト"""
        try:
            test_data = self.get_current_price("^GSPC")
            return test_data is not None
        except Exception as e:
            self.logger.error(f"Yahoo Finance connection test failed: {e}")
            return False
