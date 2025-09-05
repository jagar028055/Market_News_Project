# -*- coding: utf-8 -*-

"""
マーケットデータ用のモデル定義
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class MarketDataType(Enum):
    """マーケットデータの種類"""

    STOCK_INDEX = "stock_index"
    CURRENCY_PAIR = "currency_pair"
    COMMODITY = "commodity"
    CRYPTOCURRENCY = "cryptocurrency"
    BOND_YIELD = "bond_yield"
    VOLATILITY_INDEX = "volatility_index"


class MarketTrend(Enum):
    """市場トレンド"""

    BULLISH = "bullish"  # 上昇トレンド
    BEARISH = "bearish"  # 下降トレンド
    NEUTRAL = "neutral"  # 中立
    VOLATILE = "volatile"  # 高ボラティリティ


@dataclass
class MarketData:
    """基本マーケットデータクラス"""

    symbol: str
    name: str
    current_price: float
    previous_close: float
    change: float
    change_percent: float
    timestamp: datetime
    data_type: MarketDataType
    currency: str = "USD"
    volume: Optional[float] = None
    market_cap: Optional[float] = None
    source: str = "unknown"

    @property
    def is_positive_change(self) -> bool:
        """価格変化がプラスかどうか"""
        return self.change > 0

    @property
    def trend(self) -> MarketTrend:
        """トレンド判定"""
        abs_change = abs(self.change_percent)

        if abs_change >= 3.0:
            return MarketTrend.VOLATILE
        elif self.change_percent > 0.5:
            return MarketTrend.BULLISH
        elif self.change_percent < -0.5:
            return MarketTrend.BEARISH
        else:
            return MarketTrend.NEUTRAL

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で返す"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "current_price": self.current_price,
            "previous_close": self.previous_close,
            "change": self.change,
            "change_percent": self.change_percent,
            "timestamp": self.timestamp.isoformat(),
            "data_type": self.data_type.value,
            "currency": self.currency,
            "volume": self.volume,
            "market_cap": self.market_cap,
            "source": self.source,
            "trend": self.trend.value,
        }


@dataclass
class StockIndex(MarketData):
    """株価指数データ"""

    region: str = "global"
    data_type: MarketDataType = MarketDataType.STOCK_INDEX

    def __post_init__(self):
        # data_typeは既に設定されているので、追加処理のみ
        pass


@dataclass
class CurrencyPair(MarketData):
    """通貨ペアデータ"""

    base_currency: str = ""
    quote_currency: str = ""
    data_type: MarketDataType = MarketDataType.CURRENCY_PAIR

    def __post_init__(self):
        # 通貨ペアから base/quote を抽出
        if "/" in self.symbol:
            self.base_currency, self.quote_currency = self.symbol.split("/")


@dataclass
class CommodityPrice(MarketData):
    """商品価格データ"""

    unit: str = ""  # 単位 (barrel, ounce, etc.)
    data_type: MarketDataType = MarketDataType.COMMODITY

    def __post_init__(self):
        # data_typeは既に設定されているので、追加処理のみ
        pass


@dataclass
class MarketSnapshot:
    """市場全体のスナップショット"""

    timestamp: datetime
    stock_indices: List[StockIndex]
    currency_pairs: List[CurrencyPair]
    commodities: List[CommodityPrice]
    overall_sentiment: MarketTrend
    volatility_score: float  # 0-100

    @property
    def major_movers(self) -> List[MarketData]:
        """主要な値動きのあった銘柄"""
        all_data = self.stock_indices + self.currency_pairs + self.commodities
        return sorted(
            [data for data in all_data if abs(data.change_percent) >= 1.0],
            key=lambda x: abs(x.change_percent),
            reverse=True,
        )[:10]

    @property
    def risk_on_sentiment(self) -> bool:
        """リスクオン相場かどうか"""
        # 株式が上昇、VIXが低下、高リスク通貨が強い場合はリスクオン
        positive_stocks = sum(1 for idx in self.stock_indices if idx.is_positive_change)
        total_stocks = len(self.stock_indices)

        if total_stocks == 0:
            return False

        return (positive_stocks / total_stocks) > 0.6 and self.volatility_score < 30

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で返す"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "stock_indices": [idx.to_dict() for idx in self.stock_indices],
            "currency_pairs": [pair.to_dict() for pair in self.currency_pairs],
            "commodities": [commodity.to_dict() for commodity in self.commodities],
            "overall_sentiment": self.overall_sentiment.value,
            "volatility_score": self.volatility_score,
            "major_movers": [mover.to_dict() for mover in self.major_movers],
            "risk_on_sentiment": self.risk_on_sentiment,
        }


# よく使用される市場データシンボル定義
MAJOR_STOCK_INDICES = {
    "^N225": {"name": "日経平均株価", "region": "japan"},
    "^IXIC": {"name": "NASDAQ Composite", "region": "usa"},
    "^GSPC": {"name": "S&P 500", "region": "usa"},
    "^DJI": {"name": "Dow Jones", "region": "usa"},
    "^FTSE": {"name": "FTSE 100", "region": "europe"},
    "^GDAXI": {"name": "DAX", "region": "europe"},
    "000001.SS": {"name": "上海総合指数", "region": "china"},
}

MAJOR_CURRENCY_PAIRS = {
    "USD/JPY": {"name": "米ドル/日本円"},
    "EUR/USD": {"name": "ユーロ/米ドル"},
    "GBP/USD": {"name": "ポンド/米ドル"},
    "USD/CHF": {"name": "米ドル/スイスフラン"},
    "AUD/USD": {"name": "豪ドル/米ドル"},
    "USD/CAD": {"name": "米ドル/カナダドル"},
}

MAJOR_COMMODITIES = {
    "CL=F": {"name": "WTI原油", "unit": "barrel"},
    "BZ=F": {"name": "ブレント原油", "unit": "barrel"},
    "GC=F": {"name": "金", "unit": "ounce"},
    "SI=F": {"name": "銀", "unit": "ounce"},
    "HG=F": {"name": "銅", "unit": "pound"},
}
