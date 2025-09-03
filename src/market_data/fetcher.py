# -*- coding: utf-8 -*-

"""
統合マーケットデータ取得クラス
複数のデータソースから市場データを取得し、統合する
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
import logging
import asyncio
import concurrent.futures
from dataclasses import asdict

from .models import (
    MarketData, MarketSnapshot, MarketTrend, MarketDataType,
    MAJOR_STOCK_INDICES, MAJOR_CURRENCY_PAIRS, MAJOR_COMMODITIES
)
from .yahoo_finance_client import YahooFinanceClient
from .stooq_client import StooqClient


class MarketDataFetcher:
    """統合マーケットデータ取得クラス"""
    
    def __init__(self, 
                 prefer_yahoo: bool = True,
                 enable_fallback: bool = True,
                 cache_duration_minutes: int = 5,
                 logger: Optional[logging.Logger] = None):
        """
        初期化
        
        Args:
            prefer_yahoo: Yahoo Financeを優先するかどうか
            enable_fallback: フォールバック機能を有効にするか
            cache_duration_minutes: キャッシュ保持時間（分）
            logger: ログ出力用
        """
        self.logger = logger or logging.getLogger(__name__)
        self.prefer_yahoo = prefer_yahoo
        self.enable_fallback = enable_fallback
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        
        # クライアント初期化
        self.yahoo_client = YahooFinanceClient(logger)
        self.stooq_client = StooqClient(logger)
        
        # キャッシュ
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._last_cache_clear = datetime.now()
        
        # 設定
        self.default_symbols = self._get_default_symbols()
        
        self.logger.info("MarketDataFetcher initialized")
    
    def get_current_market_snapshot(self, 
                                  custom_symbols: Optional[List[str]] = None,
                                  use_cache: bool = True) -> MarketSnapshot:
        """
        現在の市場スナップショットを取得
        
        Args:
            custom_symbols: カスタムシンボルリスト（Noneの場合はデフォルト使用）
            use_cache: キャッシュを使用するか
        
        Returns:
            MarketSnapshot: 市場データのスナップショット
        """
        symbols = custom_symbols or self.default_symbols
        
        self.logger.info(f"Fetching market snapshot for {len(symbols)} symbols")
        start_time = datetime.now()
        
        # データ取得
        all_data = self._fetch_multiple_with_fallback(symbols, use_cache)
        
        # データを種類別に分類
        stock_indices = []
        currency_pairs = []
        commodities = []
        other_data = []
        
        for data in all_data:
            if data.data_type == MarketDataType.STOCK_INDEX:
                stock_indices.append(data)
            elif data.data_type == MarketDataType.CURRENCY_PAIR:
                currency_pairs.append(data)
            elif data.data_type == MarketDataType.COMMODITY:
                commodities.append(data)
            else:
                other_data.append(data)
        
        # 全体的な市場センチメントを計算
        overall_sentiment = self._calculate_overall_sentiment(all_data)
        
        # ボラティリティスコアを計算
        volatility_score = self._calculate_volatility_score(all_data)
        
        snapshot = MarketSnapshot(
            timestamp=datetime.now(),
            stock_indices=stock_indices,
            currency_pairs=currency_pairs,
            commodities=commodities,
            overall_sentiment=overall_sentiment,
            volatility_score=volatility_score
        )
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"Market snapshot completed in {elapsed_time:.2f}s: "
                        f"{len(stock_indices)} indices, {len(currency_pairs)} pairs, "
                        f"{len(commodities)} commodities")
        
        return snapshot
    
    def get_single_market_data(self, symbol: str, use_cache: bool = True) -> Optional[MarketData]:
        """
        単一シンボルのマーケットデータを取得
        
        Args:
            symbol: 取得するシンボル
            use_cache: キャッシュを使用するか
        
        Returns:
            MarketData: 取得したデータ、失敗時はNone
        """
        # キャッシュチェック
        if use_cache and self._is_cached(symbol):
            cached_data = self._get_from_cache(symbol)
            if cached_data:
                return self._dict_to_market_data(cached_data)
        
        # データ取得
        if self.prefer_yahoo:
            data = self.yahoo_client.get_current_price(symbol)
            if not data and self.enable_fallback:
                self.logger.info(f"Yahoo Finance failed for {symbol}, trying Stooq")
                data = self.stooq_client.get_current_price(symbol)
        else:
            data = self.stooq_client.get_current_price(symbol)
            if not data and self.enable_fallback:
                self.logger.info(f"Stooq failed for {symbol}, trying Yahoo Finance")
                data = self.yahoo_client.get_current_price(symbol)
        
        # キャッシュに保存
        if data and use_cache:
            self._save_to_cache(symbol, data.to_dict())
        
        return data
    
    def _fetch_multiple_with_fallback(self, symbols: List[str], use_cache: bool = True) -> List[MarketData]:
        """複数シンボルをフォールバック付きで取得"""
        all_data = []
        
        # 並列処理で高速化
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_symbol = {
                executor.submit(self.get_single_market_data, symbol, use_cache): symbol 
                for symbol in symbols
            }
            
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    data = future.result(timeout=30)
                    if data:
                        all_data.append(data)
                except Exception as e:
                    self.logger.warning(f"Failed to fetch data for {symbol}: {e}")
        
        return all_data
    
    def _get_default_symbols(self) -> List[str]:
        """デフォルトで取得するシンボルリスト"""
        return (
            list(MAJOR_STOCK_INDICES.keys())[:7] +  # 主要株価指数
            list(MAJOR_CURRENCY_PAIRS.keys())[:6] +  # 主要通貨ペア
            list(MAJOR_COMMODITIES.keys())[:5] +     # 主要商品
            ['^VIX', 'BTC-USD', 'ETH-USD']           # VIX、仮想通貨
        )
    
    def _calculate_overall_sentiment(self, data_list: List[MarketData]) -> MarketTrend:
        """全体的な市場センチメントを計算"""
        if not data_list:
            return MarketTrend.NEUTRAL
        
        # 株価指数の動きを重視
        stock_indices = [d for d in data_list if d.data_type == MarketDataType.STOCK_INDEX]
        
        if stock_indices:
            avg_change = sum(d.change_percent for d in stock_indices) / len(stock_indices)
            
            # 高ボラティリティをチェック
            volatility = sum(abs(d.change_percent) for d in stock_indices) / len(stock_indices)
            if volatility >= 2.0:
                return MarketTrend.VOLATILE
            elif avg_change >= 0.5:
                return MarketTrend.BULLISH
            elif avg_change <= -0.5:
                return MarketTrend.BEARISH
            else:
                return MarketTrend.NEUTRAL
        
        # 株価指数がない場合は全データで判定
        avg_change = sum(d.change_percent for d in data_list) / len(data_list)
        if avg_change >= 1.0:
            return MarketTrend.BULLISH
        elif avg_change <= -1.0:
            return MarketTrend.BEARISH
        else:
            return MarketTrend.NEUTRAL
    
    def _calculate_volatility_score(self, data_list: List[MarketData]) -> float:
        """ボラティリティスコア（0-100）を計算"""
        if not data_list:
            return 0.0
        
        # 変化率の絶対値の平均を計算
        avg_abs_change = sum(abs(d.change_percent) for d in data_list) / len(data_list)
        
        # 0-100スケールに変換（5%変化で100点）
        return min(avg_abs_change * 20, 100.0)
    
    def _is_cached(self, symbol: str) -> bool:
        """キャッシュにデータが存在し、有効期限内かチェック"""
        if symbol not in self._cache:
            return False
        
        cached_time = datetime.fromisoformat(self._cache[symbol]['cached_at'])
        return datetime.now() - cached_time < self.cache_duration
    
    def _get_from_cache(self, symbol: str) -> Optional[Dict[str, Any]]:
        """キャッシュからデータを取得"""
        return self._cache.get(symbol, {}).get('data')
    
    def _save_to_cache(self, symbol: str, data: Dict[str, Any]):
        """データをキャッシュに保存"""
        self._cache[symbol] = {
            'data': data,
            'cached_at': datetime.now().isoformat()
        }
        
        # 定期的にキャッシュをクリア
        if datetime.now() - self._last_cache_clear > timedelta(hours=1):
            self._clear_expired_cache()
            self._last_cache_clear = datetime.now()
    
    def _clear_expired_cache(self):
        """期限切れキャッシュをクリア"""
        current_time = datetime.now()
        expired_keys = []
        
        for symbol, cache_data in self._cache.items():
            cached_time = datetime.fromisoformat(cache_data['cached_at'])
            if current_time - cached_time > self.cache_duration:
                expired_keys.append(symbol)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            self.logger.info(f"Cleared {len(expired_keys)} expired cache entries")
    
    def _dict_to_market_data(self, data_dict: Dict[str, Any]) -> MarketData:
        """辞書からMarketDataオブジェクトを復元"""
        # timestampを復元
        data_dict = data_dict.copy()
        data_dict['timestamp'] = datetime.fromisoformat(data_dict['timestamp'])
        data_dict['data_type'] = MarketDataType(data_dict['data_type'])
        
        # 適切なクラスで復元
        if data_dict['data_type'] == MarketDataType.STOCK_INDEX:
            from .models import StockIndex
            return StockIndex(**{k: v for k, v in data_dict.items() if k != 'trend'})
        elif data_dict['data_type'] == MarketDataType.CURRENCY_PAIR:
            from .models import CurrencyPair
            return CurrencyPair(**{k: v for k, v in data_dict.items() if k != 'trend'})
        elif data_dict['data_type'] == MarketDataType.COMMODITY:
            from .models import CommodityPrice
            return CommodityPrice(**{k: v for k, v in data_dict.items() if k != 'trend'})
        else:
            return MarketData(**{k: v for k, v in data_dict.items() if k != 'trend'})
    
    def get_market_context_for_llm(self) -> str:
        """LLM用の市場コンテキストテキストを生成"""
        try:
            snapshot = self.get_current_market_snapshot()
            
            context_parts = [
                f"=== 現在の市場状況 ({snapshot.timestamp.strftime('%Y-%m-%d %H:%M JST')}) ===",
                f"全体センチメント: {snapshot.overall_sentiment.value}",
                f"ボラティリティスコア: {snapshot.volatility_score:.1f}/100",
                f"リスクオン相場: {'はい' if snapshot.risk_on_sentiment else 'いいえ'}"
            ]
            
            # 主要株価指数
            if snapshot.stock_indices:
                context_parts.append("\n【主要株価指数】")
                for idx in snapshot.stock_indices[:5]:  # 上位5つ
                    direction = "↑" if idx.change > 0 else "↓" if idx.change < 0 else "→"
                    context_parts.append(
                        f"• {idx.name}: {idx.current_price:,.0f} "
                        f"({direction}{idx.change_percent:+.2f}%)"
                    )
            
            # 主要通貨ペア
            if snapshot.currency_pairs:
                context_parts.append("\n【主要通貨】")
                for pair in snapshot.currency_pairs[:4]:  # 上位4つ
                    direction = "↑" if pair.change > 0 else "↓" if pair.change < 0 else "→"
                    context_parts.append(
                        f"• {pair.name}: {pair.current_price:.4f} "
                        f"({direction}{pair.change_percent:+.2f}%)"
                    )
            
            # 主要商品
            if snapshot.commodities:
                context_parts.append("\n【主要商品】")
                for commodity in snapshot.commodities[:3]:  # 上位3つ
                    direction = "↑" if commodity.change > 0 else "↓" if commodity.change < 0 else "→"
                    context_parts.append(
                        f"• {commodity.name}: ${commodity.current_price:.2f} "
                        f"({direction}{commodity.change_percent:+.2f}%)"
                    )
            
            # 大きな値動き
            if snapshot.major_movers:
                context_parts.append("\n【注目の値動き】")
                for mover in snapshot.major_movers[:3]:
                    direction = "急上昇" if mover['change_percent'] > 2 else "急落" if mover['change_percent'] < -2 else "大幅変動"
                    context_parts.append(
                        f"• {mover['name']}: {direction} ({mover['change_percent']:+.2f}%)"
                    )
            
            return "\n".join(context_parts)
            
        except Exception as e:
            self.logger.error(f"Failed to generate market context: {e}")
            return f"市場データの取得に失敗しました。エラー: {str(e)[:100]}"
    
    def test_connections(self) -> Dict[str, bool]:
        """各データソースの接続テスト"""
        results = {}
        
        try:
            results['yahoo_finance'] = self.yahoo_client.test_connection()
        except Exception as e:
            self.logger.error(f"Yahoo Finance test failed: {e}")
            results['yahoo_finance'] = False
        
        try:
            results['stooq'] = self.stooq_client.test_connection()
        except Exception as e:
            self.logger.error(f"Stooq test failed: {e}")
            results['stooq'] = False
        
        return results