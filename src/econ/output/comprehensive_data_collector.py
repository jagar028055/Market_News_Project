"""
Comprehensive Data Collection System for Economic Indicators
経済指標網羅的データ収集システム

各指標について関連する全てのデータを網羅的に収集・分析
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
import asyncio
import aiohttp
from dataclasses import dataclass, field
from enum import Enum

# 既存モジュール
from ..config.settings import EconConfig
from ..normalize.data_processor import ProcessedIndicator
from ..normalize.trend_analyzer import TrendResult

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """データソース"""
    FRED = "fred"
    BLS = "bls"
    BEA = "bea"
    ECB = "ecb"
    ONS = "ons"
    ESTAT = "estat"
    FMP = "fmp"
    FINNHUB = "finnhub"
    INVESTPY = "investpy"
    RSS = "rss"


@dataclass
class DataCollectionConfig:
    """データ収集設定"""
    # 基本設定
    max_concurrent_requests: int = 10
    request_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 2
    
    # データソース設定
    enabled_sources: List[DataSource] = field(default_factory=lambda: [
        DataSource.FRED, DataSource.BLS, DataSource.BEA, 
        DataSource.ECB, DataSource.ONS, DataSource.ESTAT
    ])
    
    # データ範囲設定
    historical_years: int = 10
    forecast_months: int = 12
    
    # 出力設定
    save_raw_data: bool = True
    save_processed_data: bool = True
    output_path: Optional[Path] = None


@dataclass
class ComprehensiveData:
    """網羅的データ"""
    # 基本データ
    main_indicator: ProcessedIndicator
    trend_result: Optional[TrendResult]
    
    # 関連データ
    historical_data: Dict[str, pd.DataFrame]
    forecast_data: Dict[str, pd.DataFrame]
    related_indicators: List[ProcessedIndicator]
    
    # 外部データ
    market_data: Dict[str, Any]
    news_data: List[Dict[str, Any]]
    sentiment_data: Dict[str, Any]
    
    # メタデータ
    collection_time: datetime
    data_sources: List[str]
    data_quality_scores: Dict[str, float]


class ComprehensiveDataCollector:
    """網羅的データ収集システム"""
    
    def __init__(self, config: Optional[DataCollectionConfig] = None, econ_config: Optional[EconConfig] = None):
        self.config = config or DataCollectionConfig()
        self.econ_config = econ_config or EconConfig()
        
    async def collect_comprehensive_data(
        self,
        main_indicator: ProcessedIndicator,
        trend_result: Optional[TrendResult] = None
    ) -> ComprehensiveData:
        """網羅的データを収集"""
        
        try:
            logger.info(f"網羅的データ収集開始: {main_indicator.original_event.country} - {getattr(main_indicator.original_event, 'indicator', 'N/A')}")
            
            # 並行データ収集
            tasks = [
                self._collect_historical_data(main_indicator),
                self._collect_forecast_data(main_indicator),
                self._collect_related_indicators(main_indicator),
                self._collect_market_data(main_indicator),
                self._collect_news_data(main_indicator),
                self._collect_sentiment_data(main_indicator)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 結果を整理
            historical_data = results[0] if not isinstance(results[0], Exception) else {}
            forecast_data = results[1] if not isinstance(results[1], Exception) else {}
            related_indicators = results[2] if not isinstance(results[2], Exception) else []
            market_data = results[3] if not isinstance(results[3], Exception) else {}
            news_data = results[4] if not isinstance(results[4], Exception) else []
            sentiment_data = results[5] if not isinstance(results[5], Exception) else {}
            
            # データ品質評価
            data_quality_scores = self._evaluate_data_quality(
                historical_data, forecast_data, related_indicators, market_data, news_data, sentiment_data
            )
            
            # 網羅的データオブジェクト作成
            comprehensive_data = ComprehensiveData(
                main_indicator=main_indicator,
                trend_result=trend_result,
                historical_data=historical_data,
                forecast_data=forecast_data,
                related_indicators=related_indicators,
                market_data=market_data,
                news_data=news_data,
                sentiment_data=sentiment_data,
                collection_time=datetime.now(),
                data_sources=[source.value for source in self.config.enabled_sources],
                data_quality_scores=data_quality_scores
            )
            
            # データ保存
            if self.config.save_raw_data or self.config.save_processed_data:
                await self._save_comprehensive_data(comprehensive_data)
            
            logger.info(f"網羅的データ収集完了: {len(historical_data)}履歴データ, {len(related_indicators)}関連指標")
            
            return comprehensive_data
            
        except Exception as e:
            logger.error(f"網羅的データ収集エラー: {e}")
            raise
    
    async def _collect_historical_data(self, indicator: ProcessedIndicator) -> Dict[str, pd.DataFrame]:
        """履歴データを収集"""
        historical_data = {}
        
        try:
            event = indicator.original_event
            country = event.country
            indicator_name = getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')
            
            # FRED API から履歴データ収集
            if DataSource.FRED in self.config.enabled_sources:
                fred_data = await self._collect_fred_data(country, indicator_name)
                if fred_data is not None:
                    historical_data['fred'] = fred_data
            
            # BLS API から履歴データ収集
            if DataSource.BLS in self.config.enabled_sources and country == 'US':
                bls_data = await self._collect_bls_data(indicator_name)
                if bls_data is not None:
                    historical_data['bls'] = bls_data
            
            # ECB API から履歴データ収集
            if DataSource.ECB in self.config.enabled_sources and country == 'EU':
                ecb_data = await self._collect_ecb_data(indicator_name)
                if ecb_data is not None:
                    historical_data['ecb'] = ecb_data
            
            # 既存の履歴データも追加
            if indicator.historical_data is not None:
                historical_data['main'] = indicator.historical_data.to_frame()
            
        except Exception as e:
            logger.error(f"履歴データ収集エラー: {e}")
        
        return historical_data
    
    async def _collect_forecast_data(self, indicator: ProcessedIndicator) -> Dict[str, pd.DataFrame]:
        """予測データを収集"""
        forecast_data = {}
        
        try:
            event = indicator.original_event
            country = event.country
            indicator_name = getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')
            
            # FMP API から予測データ収集
            if DataSource.FMP in self.config.enabled_sources:
                fmp_forecast = await self._collect_fmp_forecast(country, indicator_name)
                if fmp_forecast is not None:
                    forecast_data['fmp'] = fmp_forecast
            
            # Finnhub API から予測データ収集
            if DataSource.FINNHUB in self.config.enabled_sources:
                finnhub_forecast = await self._collect_finnhub_forecast(country, indicator_name)
                if finnhub_forecast is not None:
                    forecast_data['finnhub'] = finnhub_forecast
            
        except Exception as e:
            logger.error(f"予測データ収集エラー: {e}")
        
        return forecast_data
    
    async def _collect_related_indicators(self, indicator: ProcessedIndicator) -> List[ProcessedIndicator]:
        """関連指標を収集"""
        related_indicators = []
        
        try:
            event = indicator.original_event
            country = event.country
            
            # 同じ国の他の主要指標を収集
            related_indicator_names = self._get_related_indicator_names(event)
            
            for related_name in related_indicator_names:
                try:
                    # 既存のデータ取得機能を使用
                    from ..adapters.investpy_calendar import InvestPyCalendar
                    from ..normalize.data_processor import DataProcessor
                    
                    calendar = InvestPyCalendar()
                    related_events = calendar.get_economic_calendar(
                        countries=[country],
                        importance='High'
                    )
                    
                    # 関連指標をフィルタリング
                    for related_event in related_events:
                        if (getattr(related_event, 'indicator', None) == related_name or 
                            getattr(related_event, 'title', None) == related_name):
                            
                            processor = DataProcessor()
                            related_processed = processor.process_indicator(related_event)
                            if related_processed:
                                related_indicators.append(related_processed)
                            break
                            
                except Exception as e:
                    logger.warning(f"関連指標収集エラー ({related_name}): {e}")
                    continue
            
        except Exception as e:
            logger.error(f"関連指標収集エラー: {e}")
        
        return related_indicators
    
    async def _collect_market_data(self, indicator: ProcessedIndicator) -> Dict[str, Any]:
        """市場データを収集"""
        market_data = {}
        
        try:
            event = indicator.original_event
            country = event.country
            
            # 通貨データ
            currency_data = await self._collect_currency_data(country)
            if currency_data:
                market_data['currency'] = currency_data
            
            # 株式市場データ
            stock_data = await self._collect_stock_market_data(country)
            if stock_data:
                market_data['stock_market'] = stock_data
            
            # 債券市場データ
            bond_data = await self._collect_bond_market_data(country)
            if bond_data:
                market_data['bond_market'] = bond_data
            
            # 商品市場データ
            commodity_data = await self._collect_commodity_data()
            if commodity_data:
                market_data['commodities'] = commodity_data
            
        except Exception as e:
            logger.error(f"市場データ収集エラー: {e}")
        
        return market_data
    
    async def _collect_news_data(self, indicator: ProcessedIndicator) -> List[Dict[str, Any]]:
        """ニュースデータを収集"""
        news_data = []
        
        try:
            event = indicator.original_event
            country = event.country
            indicator_name = getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')
            
            # RSS フィードからニュース収集
            if DataSource.RSS in self.config.enabled_sources:
                rss_news = await self._collect_rss_news(country, indicator_name)
                news_data.extend(rss_news)
            
            # 既存のニュースデータベースから検索
            db_news = await self._collect_database_news(country, indicator_name)
            news_data.extend(db_news)
            
        except Exception as e:
            logger.error(f"ニュースデータ収集エラー: {e}")
        
        return news_data
    
    async def _collect_sentiment_data(self, indicator: ProcessedIndicator) -> Dict[str, Any]:
        """センチメントデータを収集"""
        sentiment_data = {}
        
        try:
            event = indicator.original_event
            country = event.country
            indicator_name = getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')
            
            # ソーシャルメディアセンチメント
            social_sentiment = await self._collect_social_sentiment(country, indicator_name)
            if social_sentiment:
                sentiment_data['social'] = social_sentiment
            
            # ニュースセンチメント
            news_sentiment = await self._collect_news_sentiment(country, indicator_name)
            if news_sentiment:
                sentiment_data['news'] = news_sentiment
            
            # アナリストセンチメント
            analyst_sentiment = await self._collect_analyst_sentiment(country, indicator_name)
            if analyst_sentiment:
                sentiment_data['analyst'] = analyst_sentiment
            
        except Exception as e:
            logger.error(f"センチメントデータ収集エラー: {e}")
        
        return sentiment_data
    
    async def _collect_fred_data(self, country: str, indicator_name: str) -> Optional[pd.DataFrame]:
        """FRED API からデータ収集"""
        try:
            # FRED API キーが必要
            fred_api_key = self.econ_config.apis.fred_api_key
            if not fred_api_key:
                return None
            
            # 指標名をFREDシリーズIDにマッピング
            series_id = self._map_indicator_to_fred_series(country, indicator_name)
            if not series_id:
                return None
            
            # FRED API 呼び出し
            url = f"https://api.stlouisfed.org/fred/series/observations"
            params = {
                'series_id': series_id,
                'api_key': fred_api_key,
                'file_type': 'json',
                'limit': 1000,
                'sort_order': 'desc'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=self.config.request_timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        observations = data.get('observations', [])
                        
                        if observations:
                            df_data = []
                            for obs in observations:
                                if obs.get('value') != '.':
                                    df_data.append({
                                        'date': pd.to_datetime(obs['date']),
                                        'value': float(obs['value'])
                                    })
                            
                            if df_data:
                                df = pd.DataFrame(df_data)
                                df.set_index('date', inplace=True)
                                df.sort_index(inplace=True)
                                return df
            
        except Exception as e:
            logger.error(f"FRED データ収集エラー: {e}")
        
        return None
    
    async def _collect_bls_data(self, indicator_name: str) -> Optional[pd.DataFrame]:
        """BLS API からデータ収集"""
        try:
            # BLS API キーが必要
            bls_api_key = self.econ_config.apis.bls_api_key
            if not bls_api_key:
                return None
            
            # 指標名をBLSシリーズIDにマッピング
            series_id = self._map_indicator_to_bls_series(indicator_name)
            if not series_id:
                return None
            
            # BLS API 呼び出し
            url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
            payload = {
                "seriesid": [series_id],
                "startyear": str(datetime.now().year - self.config.historical_years),
                "endyear": str(datetime.now().year),
                "registrationkey": bls_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=self.config.request_timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        series_data = data.get('Results', {}).get('series', [])
                        
                        if series_data:
                            observations = series_data[0].get('data', [])
                            df_data = []
                            
                            for obs in observations:
                                df_data.append({
                                    'date': pd.to_datetime(f"{obs['year']}-{obs['period'][1:]}-01"),
                                    'value': float(obs['value'])
                                })
                            
                            if df_data:
                                df = pd.DataFrame(df_data)
                                df.set_index('date', inplace=True)
                                df.sort_index(inplace=True)
                                return df
            
        except Exception as e:
            logger.error(f"BLS データ収集エラー: {e}")
        
        return None
    
    async def _collect_ecb_data(self, indicator_name: str) -> Optional[pd.DataFrame]:
        """ECB API からデータ収集"""
        try:
            # 指標名をECBシリーズキーにマッピング
            series_key = self._map_indicator_to_ecb_series(indicator_name)
            if not series_key:
                return None
            
            # ECB API 呼び出し
            url = f"https://data.ecb.europa.eu/api/v1/data/{series_key}"
            params = {
                'format': 'jsondata',
                'lastNObservations': 1000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=self.config.request_timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        observations = data.get('dataSets', [{}])[0].get('observations', {})
                        
                        if observations:
                            df_data = []
                            for key, obs in observations.items():
                                if obs.get('0') and obs['0'][0] is not None:
                                    # 日付を解析（ECBの形式に依存）
                                    date_str = key  # 実際の実装では適切な日付解析が必要
                                    df_data.append({
                                        'date': pd.to_datetime(date_str),
                                        'value': float(obs['0'][0])
                                    })
                            
                            if df_data:
                                df = pd.DataFrame(df_data)
                                df.set_index('date', inplace=True)
                                df.sort_index(inplace=True)
                                return df
            
        except Exception as e:
            logger.error(f"ECB データ収集エラー: {e}")
        
        return None
    
    async def _collect_fmp_forecast(self, country: str, indicator_name: str) -> Optional[pd.DataFrame]:
        """FMP API から予測データ収集"""
        try:
            # FMP API キーが必要
            fmp_api_key = self.econ_config.data_sources.fmp_api_key
            if not fmp_api_key:
                return None
            
            # FMP API 呼び出し（予測データ）
            url = f"https://financialmodelingprep.com/api/v3/economic_indicator_forecast"
            params = {
                'apikey': fmp_api_key,
                'country': country,
                'indicator': indicator_name
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=self.config.request_timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data:
                            df_data = []
                            for item in data:
                                df_data.append({
                                    'date': pd.to_datetime(item.get('date')),
                                    'forecast': float(item.get('forecast', 0)),
                                    'actual': float(item.get('actual', 0)) if item.get('actual') else None
                                })
                            
                            if df_data:
                                df = pd.DataFrame(df_data)
                                df.set_index('date', inplace=True)
                                df.sort_index(inplace=True)
                                return df
            
        except Exception as e:
            logger.error(f"FMP 予測データ収集エラー: {e}")
        
        return None
    
    async def _collect_finnhub_forecast(self, country: str, indicator_name: str) -> Optional[pd.DataFrame]:
        """Finnhub API から予測データ収集"""
        try:
            # Finnhub API キーが必要
            finnhub_api_key = self.econ_config.data_sources.finnhub_api_key
            if not finnhub_api_key:
                return None
            
            # Finnhub API 呼び出し（経済指標予測）
            url = f"https://finnhub.io/api/v1/economic_indicator_forecast"
            params = {
                'token': finnhub_api_key,
                'country': country,
                'indicator': indicator_name
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=self.config.request_timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data:
                            df_data = []
                            for item in data:
                                df_data.append({
                                    'date': pd.to_datetime(item.get('date')),
                                    'forecast': float(item.get('forecast', 0)),
                                    'actual': float(item.get('actual', 0)) if item.get('actual') else None
                                })
                            
                            if df_data:
                                df = pd.DataFrame(df_data)
                                df.set_index('date', inplace=True)
                                df.sort_index(inplace=True)
                                return df
            
        except Exception as e:
            logger.error(f"Finnhub 予測データ収集エラー: {e}")
        
        return None
    
    async def _collect_currency_data(self, country: str) -> Optional[Dict[str, Any]]:
        """通貨データを収集"""
        try:
            # 通貨ペアのマッピング
            currency_pairs = {
                'US': ['USD/JPY', 'EUR/USD', 'GBP/USD'],
                'EU': ['EUR/USD', 'EUR/JPY', 'EUR/GBP'],
                'JP': ['USD/JPY', 'EUR/JPY', 'GBP/JPY'],
                'UK': ['GBP/USD', 'EUR/GBP', 'GBP/JPY']
            }
            
            pairs = currency_pairs.get(country, [])
            if not pairs:
                return None
            
            currency_data = {}
            
            # 各通貨ペアのデータを収集
            for pair in pairs:
                try:
                    # 簡易的な通貨データ取得（実際の実装では適切なAPIを使用）
                    currency_data[pair] = {
                        'current_rate': np.random.uniform(0.8, 1.2),
                        'change_24h': np.random.uniform(-0.05, 0.05),
                        'volatility': np.random.uniform(0.01, 0.03)
                    }
                except Exception as e:
                    logger.warning(f"通貨データ収集エラー ({pair}): {e}")
                    continue
            
            return currency_data if currency_data else None
            
        except Exception as e:
            logger.error(f"通貨データ収集エラー: {e}")
        
        return None
    
    async def _collect_stock_market_data(self, country: str) -> Optional[Dict[str, Any]]:
        """株式市場データを収集"""
        try:
            # 主要指数のマッピング
            indices = {
                'US': ['SPX', 'DJI', 'IXIC'],
                'EU': ['STOXX50E', 'DAX', 'CAC40'],
                'JP': ['N225', 'TPX'],
                'UK': ['FTSE100', 'FTSE250']
            }
            
            country_indices = indices.get(country, [])
            if not country_indices:
                return None
            
            stock_data = {}
            
            # 各指数のデータを収集
            for index in country_indices:
                try:
                    # 簡易的な株式データ取得（実際の実装では適切なAPIを使用）
                    stock_data[index] = {
                        'current_value': np.random.uniform(2000, 5000),
                        'change_1d': np.random.uniform(-0.05, 0.05),
                        'change_1w': np.random.uniform(-0.1, 0.1),
                        'volume': np.random.uniform(1000000, 10000000)
                    }
                except Exception as e:
                    logger.warning(f"株式データ収集エラー ({index}): {e}")
                    continue
            
            return stock_data if stock_data else None
            
        except Exception as e:
            logger.error(f"株式市場データ収集エラー: {e}")
        
        return None
    
    async def _collect_bond_market_data(self, country: str) -> Optional[Dict[str, Any]]:
        """債券市場データを収集"""
        try:
            # 国債のマッピング
            bonds = {
                'US': ['10Y_US', '2Y_US', '30Y_US'],
                'EU': ['10Y_DE', '10Y_FR', '10Y_IT'],
                'JP': ['10Y_JP', '2Y_JP', '30Y_JP'],
                'UK': ['10Y_UK', '2Y_UK', '30Y_UK']
            }
            
            country_bonds = bonds.get(country, [])
            if not country_bonds:
                return None
            
            bond_data = {}
            
            # 各債券のデータを収集
            for bond in country_bonds:
                try:
                    # 簡易的な債券データ取得（実際の実装では適切なAPIを使用）
                    bond_data[bond] = {
                        'yield': np.random.uniform(0.5, 5.0),
                        'change_1d': np.random.uniform(-0.1, 0.1),
                        'spread': np.random.uniform(-0.5, 0.5)
                    }
                except Exception as e:
                    logger.warning(f"債券データ収集エラー ({bond}): {e}")
                    continue
            
            return bond_data if bond_data else None
            
        except Exception as e:
            logger.error(f"債券市場データ収集エラー: {e}")
        
        return None
    
    async def _collect_commodity_data(self) -> Optional[Dict[str, Any]]:
        """商品データを収集"""
        try:
            commodities = ['GOLD', 'SILVER', 'OIL', 'GAS', 'WHEAT', 'CORN']
            commodity_data = {}
            
            # 各商品のデータを収集
            for commodity in commodities:
                try:
                    # 簡易的な商品データ取得（実際の実装では適切なAPIを使用）
                    commodity_data[commodity] = {
                        'price': np.random.uniform(50, 2000),
                        'change_1d': np.random.uniform(-0.05, 0.05),
                        'change_1w': np.random.uniform(-0.1, 0.1)
                    }
                except Exception as e:
                    logger.warning(f"商品データ収集エラー ({commodity}): {e}")
                    continue
            
            return commodity_data if commodity_data else None
            
        except Exception as e:
            logger.error(f"商品データ収集エラー: {e}")
        
        return None
    
    async def _collect_rss_news(self, country: str, indicator_name: str) -> List[Dict[str, Any]]:
        """RSS フィードからニュース収集"""
        try:
            # RSS フィードのマッピング
            rss_feeds = {
                'US': [
                    'https://www.federalreserve.gov/feeds/press_all.xml',
                    'https://www.bea.gov/rss/news_releases.xml',
                    'https://www.bls.gov/bls.rss'
                ],
                'EU': [
                    'https://www.ecb.europa.eu/rss/press.html',
                    'https://ec.europa.eu/eurostat/news/rss'
                ],
                'JP': [
                    'https://www.boj.or.jp/en/news/feed/boj_news.rss',
                    'https://www.stat.go.jp/english/rss/index.html'
                ]
            }
            
            feeds = rss_feeds.get(country, [])
            news_data = []
            
            # 各RSSフィードからニュース収集
            for feed_url in feeds:
                try:
                    # 簡易的なRSS解析（実際の実装では適切なRSS解析ライブラリを使用）
                    # ここではダミーデータを生成
                    news_data.append({
                        'title': f"{indicator_name} 関連ニュース",
                        'url': f"https://example.com/news/{indicator_name}",
                        'published': datetime.now().isoformat(),
                        'source': feed_url,
                        'summary': f"{country} の {indicator_name} に関する最新ニュースです。"
                    })
                except Exception as e:
                    logger.warning(f"RSS ニュース収集エラー ({feed_url}): {e}")
                    continue
            
            return news_data
            
        except Exception as e:
            logger.error(f"RSS ニュース収集エラー: {e}")
        
        return []
    
    async def _collect_database_news(self, country: str, indicator_name: str) -> List[Dict[str, Any]]:
        """データベースからニュース収集"""
        try:
            # 既存のニュースデータベースから検索
            # ここでは簡易的な実装
            news_data = []
            
            # ダミーデータを生成（実際の実装ではデータベースクエリを実行）
            news_data.append({
                'title': f"{country} {indicator_name} 分析レポート",
                'url': f"https://example.com/analysis/{country}/{indicator_name}",
                'published': datetime.now().isoformat(),
                'source': 'Internal Database',
                'summary': f"{country} の {indicator_name} に関する詳細分析です。",
                'sentiment': 'positive' if np.random.random() > 0.5 else 'negative'
            })
            
            return news_data
            
        except Exception as e:
            logger.error(f"データベースニュース収集エラー: {e}")
        
        return []
    
    async def _collect_social_sentiment(self, country: str, indicator_name: str) -> Optional[Dict[str, Any]]:
        """ソーシャルメディアセンチメント収集"""
        try:
            # ソーシャルメディアAPIからセンチメントデータ収集
            # ここでは簡易的な実装
            sentiment_data = {
                'twitter': {
                    'sentiment_score': np.random.uniform(-1, 1),
                    'mention_count': np.random.randint(100, 10000),
                    'positive_ratio': np.random.uniform(0.3, 0.7)
                },
                'reddit': {
                    'sentiment_score': np.random.uniform(-1, 1),
                    'mention_count': np.random.randint(50, 5000),
                    'positive_ratio': np.random.uniform(0.3, 0.7)
                }
            }
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"ソーシャルセンチメント収集エラー: {e}")
        
        return None
    
    async def _collect_news_sentiment(self, country: str, indicator_name: str) -> Optional[Dict[str, Any]]:
        """ニュースセンチメント収集"""
        try:
            # ニュースAPIからセンチメントデータ収集
            # ここでは簡易的な実装
            sentiment_data = {
                'overall_sentiment': np.random.uniform(-1, 1),
                'news_count': np.random.randint(10, 100),
                'positive_news': np.random.randint(5, 50),
                'negative_news': np.random.randint(5, 50),
                'neutral_news': np.random.randint(0, 20)
            }
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"ニュースセンチメント収集エラー: {e}")
        
        return None
    
    async def _collect_analyst_sentiment(self, country: str, indicator_name: str) -> Optional[Dict[str, Any]]:
        """アナリストセンチメント収集"""
        try:
            # アナリストレポートからセンチメントデータ収集
            # ここでは簡易的な実装
            sentiment_data = {
                'bullish_count': np.random.randint(0, 10),
                'bearish_count': np.random.randint(0, 10),
                'neutral_count': np.random.randint(0, 5),
                'average_target': np.random.uniform(90, 110),
                'consensus': 'bullish' if np.random.random() > 0.5 else 'bearish'
            }
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"アナリストセンチメント収集エラー: {e}")
        
        return None
    
    def _get_related_indicator_names(self, event) -> List[str]:
        """関連指標名を取得"""
        # 指標タイプに基づいて関連指標を決定
        indicator_name = getattr(event, 'indicator', None) or getattr(event, 'title', 'N/A')
        
        related_indicators = {
            'CPI': ['Core CPI', 'PPI', 'Unemployment Rate', 'GDP'],
            'GDP': ['CPI', 'Unemployment Rate', 'Interest Rate', 'PMI'],
            'Unemployment Rate': ['Non-Farm Payrolls', 'CPI', 'GDP', 'Interest Rate'],
            'Interest Rate': ['CPI', 'GDP', 'Unemployment Rate', 'Currency'],
            'PMI': ['GDP', 'Industrial Production', 'Retail Sales', 'CPI']
        }
        
        return related_indicators.get(indicator_name, [])
    
    def _map_indicator_to_fred_series(self, country: str, indicator_name: str) -> Optional[str]:
        """指標名をFREDシリーズIDにマッピング"""
        # FREDシリーズIDのマッピング
        fred_mapping = {
            'US': {
                'CPI': 'CPIAUCSL',
                'GDP': 'GDP',
                'Unemployment Rate': 'UNRATE',
                'Interest Rate': 'FEDFUNDS',
                'PMI': 'NAPM'
            },
            'EU': {
                'CPI': 'CPHPTT01EZM661N',
                'GDP': 'CLVMNACSCAB1GQEZ',
                'Unemployment Rate': 'LRHUTTTTEZM156S',
                'Interest Rate': 'IR3TIB01EZM156N'
            }
        }
        
        return fred_mapping.get(country, {}).get(indicator_name)
    
    def _map_indicator_to_bls_series(self, indicator_name: str) -> Optional[str]:
        """指標名をBLSシリーズIDにマッピング"""
        # BLSシリーズIDのマッピング
        bls_mapping = {
            'CPI': 'CUUR0000SA0',
            'Unemployment Rate': 'LNS14000000',
            'Non-Farm Payrolls': 'CES0000000001',
            'Average Hourly Earnings': 'CES0500000003'
        }
        
        return bls_mapping.get(indicator_name)
    
    def _map_indicator_to_ecb_series(self, indicator_name: str) -> Optional[str]:
        """指標名をECBシリーズキーにマッピング"""
        # ECBシリーズキーのマッピング
        ecb_mapping = {
            'CPI': 'ICP.M.U2.N.000000.4.ANR',
            'GDP': 'MNA.Q.N.I8.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.N',
            'Unemployment Rate': 'STS.M.U2.S.UNEH.RTT000.4.000',
            'Interest Rate': 'FM.M.U2.EUR.4F.KR.MRR_FR.LEV'
        }
        
        return ecb_mapping.get(indicator_name)
    
    def _evaluate_data_quality(self, historical_data: Dict, forecast_data: Dict, related_indicators: List, 
                              market_data: Dict, news_data: List, sentiment_data: Dict) -> Dict[str, float]:
        """データ品質を評価"""
        quality_scores = {}
        
        try:
            # 履歴データ品質
            quality_scores['historical_data'] = min(100, len(historical_data) * 20)
            
            # 予測データ品質
            quality_scores['forecast_data'] = min(100, len(forecast_data) * 25)
            
            # 関連指標品質
            quality_scores['related_indicators'] = min(100, len(related_indicators) * 10)
            
            # 市場データ品質
            quality_scores['market_data'] = min(100, len(market_data) * 15)
            
            # ニュースデータ品質
            quality_scores['news_data'] = min(100, len(news_data) * 5)
            
            # センチメントデータ品質
            quality_scores['sentiment_data'] = min(100, len(sentiment_data) * 20)
            
            # 総合品質スコア
            quality_scores['overall'] = sum(quality_scores.values()) / len(quality_scores)
            
        except Exception as e:
            logger.error(f"データ品質評価エラー: {e}")
            quality_scores = {'overall': 0}
        
        return quality_scores
    
    async def _save_comprehensive_data(self, comprehensive_data: ComprehensiveData):
        """網羅的データを保存"""
        try:
            if not self.config.output_path:
                return
            
            self.config.output_path.mkdir(parents=True, exist_ok=True)
            
            # メタデータ保存
            metadata = {
                'main_indicator': {
                    'country': comprehensive_data.main_indicator.original_event.country,
                    'indicator': getattr(comprehensive_data.main_indicator.original_event, 'indicator', 'N/A'),
                    'collection_time': comprehensive_data.collection_time.isoformat(),
                    'data_sources': comprehensive_data.data_sources,
                    'data_quality_scores': comprehensive_data.data_quality_scores
                }
            }
            
            metadata_path = self.config.output_path / f"metadata_{comprehensive_data.collection_time.strftime('%Y%m%d_%H%M%S')}.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 履歴データ保存
            if self.config.save_raw_data:
                for source, data in comprehensive_data.historical_data.items():
                    data_path = self.config.output_path / f"historical_{source}_{comprehensive_data.collection_time.strftime('%Y%m%d_%H%M%S')}.csv"
                    data.to_csv(data_path)
            
            # 予測データ保存
            if self.config.save_raw_data:
                for source, data in comprehensive_data.forecast_data.items():
                    data_path = self.config.output_path / f"forecast_{source}_{comprehensive_data.collection_time.strftime('%Y%m%d_%H%M%S')}.csv"
                    data.to_csv(data_path)
            
            # 市場データ保存
            if self.config.save_raw_data:
                market_path = self.config.output_path / f"market_data_{comprehensive_data.collection_time.strftime('%Y%m%d_%H%M%S')}.json"
                with open(market_path, 'w', encoding='utf-8') as f:
                    json.dump(comprehensive_data.market_data, f, ensure_ascii=False, indent=2)
            
            # ニュースデータ保存
            if self.config.save_raw_data:
                news_path = self.config.output_path / f"news_data_{comprehensive_data.collection_time.strftime('%Y%m%d_%H%M%S')}.json"
                with open(news_path, 'w', encoding='utf-8') as f:
                    json.dump(comprehensive_data.news_data, f, ensure_ascii=False, indent=2)
            
            # センチメントデータ保存
            if self.config.save_raw_data:
                sentiment_path = self.config.output_path / f"sentiment_data_{comprehensive_data.collection_time.strftime('%Y%m%d_%H%M%S')}.json"
                with open(sentiment_path, 'w', encoding='utf-8') as f:
                    json.dump(comprehensive_data.sentiment_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"網羅的データが保存されました: {self.config.output_path}")
            
        except Exception as e:
            logger.error(f"網羅的データ保存エラー: {e}")
