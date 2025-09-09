"""
SNS画像生成用データ統合マネージャー
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pytz
import requests

from ..config.app_config import AppConfig
from ..personalization.topic_selector import Topic
from ..indicators.fetcher import fetch_indicators
from .economic_calendar_fetcher import EconomicCalendarFetcher

# SupabaseClientの条件付きインポート
try:
    from ..database.supabase_client import SupabaseClient
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    SupabaseClient = None


class SocialDataManager:
    """SNS画像生成用のデータ統合マネージャー"""
    
    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.supabase_client = SupabaseClient(config, logger) if (config.supabase.enabled and SUPABASE_AVAILABLE) else None
        self.economic_calendar_fetcher = EconomicCalendarFetcher(logger)
        
    def get_social_content_data(
        self, 
        target_date: Optional[datetime] = None,
        use_artifacts: bool = True,
        use_supabase: bool = True,
        use_local_db: bool = True
    ) -> Dict[str, Any]:
        """
        SNS画像生成用の統合データを取得
        
        Args:
            target_date: 対象日（Noneの場合は今日）
            use_artifacts: GitHub Actionsアーティファクトを使用するか
            use_supabase: Supabaseを使用するか
            use_local_db: ローカルDBを使用するか
            
        Returns:
            統合データ辞書
        """
        if target_date is None:
            target_date = datetime.now(pytz.timezone('Asia/Tokyo'))
        
        self.logger.info(f"SNS画像用データ取得開始: {target_date.strftime('%Y-%m-%d')}")
        
        # データ収集
        topics = self._get_topics(target_date, use_artifacts, use_supabase, use_local_db)
        indicators = self._get_indicators(target_date)
        economic_calendar = self._get_economic_calendar(target_date)
        market_notes = self._generate_market_notes(topics, indicators)
        
        # データ統合
        integrated_data = {
            'date': target_date,
            'topics': topics,
            'indicators': indicators,
            'economic_calendar': economic_calendar,
            'market_notes': market_notes,
            'data_sources': self._get_data_sources_info()
        }
        
        self.logger.info(f"データ取得完了: トピック {len(topics)}件, 指標 {len(indicators)}件")
        return integrated_data
    
    def _get_topics(
        self, 
        target_date: datetime, 
        use_artifacts: bool, 
        use_supabase: bool, 
        use_local_db: bool
    ) -> List[Topic]:
        """トピックデータを取得（優先順位付き）"""
        
        # 1. GitHub Actionsアーティファクトから取得
        if use_artifacts:
            topics = self._get_topics_from_artifacts(target_date)
            if topics:
                self.logger.info(f"アーティファクトからトピック取得: {len(topics)}件")
                return topics
        
        # 2. Supabaseから取得
        if use_supabase and self.supabase_client:
            topics = self._get_topics_from_supabase(target_date)
            if topics:
                self.logger.info(f"Supabaseからトピック取得: {len(topics)}件")
                return topics
        
        # 3. ローカルDBから取得
        if use_local_db:
            topics = self._get_topics_from_local_db(target_date)
            if topics:
                self.logger.info(f"ローカルDBからトピック取得: {len(topics)}件")
                return topics
        
        # 4. 最終フォールバック: サンプルデータ（最小限）
        self.logger.warning("すべてのデータソースからトピックを取得できませんでした。最小限のサンプルデータを使用")
        return self._get_minimal_sample_topics(target_date)
    
    def _get_topics_from_artifacts(self, target_date: datetime) -> List[Topic]:
        """GitHub Actionsアーティファクトからトピックを取得"""
        try:
            # アーティファクトのパスを構築（日付順に検索）
            date_str = target_date.strftime('%Y%m%d')
            artifact_paths = [
                f"build/social/{date_str}/topics.json",
                f"logs/social/{date_str}/topics.json",
                f"data/articles_{date_str}.json"
            ]
            
            # 過去の日付も検索（最新のデータを取得）
            for days_back in range(1, 8):  # 過去1週間分を検索
                past_date = target_date - timedelta(days=days_back)
                past_date_str = past_date.strftime('%Y%m%d')
                artifact_paths.extend([
                    f"build/social/{past_date_str}/topics.json",
                    f"logs/social/{past_date_str}/topics.json"
                ])
            
            for path in artifact_paths:
                if Path(path).exists():
                    self.logger.info(f"アーティファクトファイル発見: {path}")
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # データ形式に応じてトピックを抽出
                    topics_data = []
                    if 'topics' in data:
                        topics_data = data['topics']
                    elif isinstance(data, list):
                        topics_data = data
                    else:
                        continue
                    
                    topics = []
                    for topic_data in topics_data[:3]:  # 上位3件
                        # データの正規化
                        headline = topic_data.get('headline') or topic_data.get('title', '')
                        blurb = topic_data.get('blurb') or topic_data.get('summary', '')
                        
                        if not headline:
                            continue
                            
                        topic = Topic(
                            headline=headline,
                            blurb=blurb,
                            url=topic_data.get('url', ''),
                            source=topic_data.get('source', ''),
                            score=topic_data.get('score', 1.0),
                            published_jst=datetime.fromisoformat(
                                topic_data.get('published_jst', target_date.isoformat())
                            ),
                            category=topic_data.get('category', ''),
                            region=topic_data.get('region', '')
                        )
                        topics.append(topic)
                    
                    if topics:
                        self.logger.info(f"アーティファクトからトピック取得成功: {len(topics)}件")
                        return topics
                    
        except Exception as e:
            self.logger.error(f"アーティファクトからのトピック取得エラー: {e}")
        
        return []
    
    def _get_topics_from_supabase(self, target_date: datetime) -> List[Topic]:
        """Supabaseからトピックを取得"""
        try:
            if not self.supabase_client or not self.supabase_client.is_available():
                return []
            
            # 日付範囲でドキュメントを検索
            start_date = target_date.strftime('%Y-%m-%d')
            end_date = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # 簡易実装: 実際のSupabaseクエリに置き換え
            # result = self.supabase_client.search_documents(
            #     date_from=start_date,
            #     date_to=end_date,
            #     limit=3
            # )
            
            # 現在は空のリストを返す（実装待ち）
            return []
            
        except Exception as e:
            self.logger.error(f"Supabaseからのトピック取得エラー: {e}")
            return []
    
    def _get_topics_from_local_db(self, target_date: datetime) -> List[Topic]:
        """ローカルDBからトピックを取得"""
        try:
            # 1. data/articles.jsonから最新記事を取得
            articles_file = Path("data/articles.json")
            if articles_file.exists():
                with open(articles_file, 'r', encoding='utf-8') as f:
                    articles_data = json.load(f)
                
                if articles_data and len(articles_data) > 0:
                    # 最新の記事を上位3件取得
                    recent_articles = articles_data[:3]
                    topics = []
                    
                    for article in recent_articles:
                        topic = Topic(
                            headline=article.get('title', ''),
                            blurb=article.get('summary', ''),
                            url=article.get('url', ''),
                            source=article.get('source', ''),
                            score=1.0,  # デフォルトスコア
                            published_jst=datetime.fromisoformat(
                                article.get('published_jst', target_date.isoformat())
                            ),
                            category=article.get('category', ''),
                            region=article.get('region', '')
                        )
                        topics.append(topic)
                    
                    if topics:
                        self.logger.info(f"ローカルDBからトピック取得成功: {len(topics)}件")
                        return topics
            
            # 2. その他のローカルファイルから検索
            local_paths = [
                "data/integrated_summary.txt",
                "build/reports/daily_indicators/",
                "build/note/"
            ]
            
            for path in local_paths:
                if Path(path).exists():
                    # ファイルの場合は内容を確認
                    if Path(path).is_file():
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            if content and len(content) > 100:  # 十分な内容がある場合
                                # 簡易的なトピック抽出（実装は簡略化）
                                self.logger.info(f"ローカルファイルからデータ発見: {path}")
                                break
                        except:
                            continue
            
            return []
            
        except Exception as e:
            self.logger.error(f"ローカルDBからのトピック取得エラー: {e}")
            return []
    
    def _get_minimal_sample_topics(self, target_date: datetime) -> List[Topic]:
        """最小限のサンプルトピックデータを生成（最終フォールバック）"""
        return [
            Topic(
                headline="マーケットニュース更新中",
                blurb="最新のマーケット情報を取得中です。しばらくお待ちください。",
                url="",
                source="Market News",
                score=1.0,
                published_jst=target_date,
                category="system",
                region="global"
            )
        ]
    
    def _get_indicators(self, target_date: datetime) -> List[Dict[str, Any]]:
        """マーケット指標データを取得"""
        try:
            # 既存のStooq APIを使用
            indicators = fetch_indicators()
            
            # データを整形
            formatted_indicators = []
            for indicator in indicators:
                formatted_indicators.append({
                    'name': indicator['name'],
                    'value': indicator['value'],
                    'change': indicator['change'],
                    'pct': indicator['pct'],
                    'note': None
                })
            
            # データを保存（キャッシュ用）
            self._save_indicators_cache(target_date, formatted_indicators)
            
            return formatted_indicators
            
        except Exception as e:
            self.logger.error(f"指標データ取得エラー: {e}")
            # フォールバック: キャッシュから取得
            return self._get_indicators_from_cache(target_date)
    
    def _get_economic_calendar(self, target_date: datetime) -> Dict[str, List[Dict[str, Any]]]:
        """経済指標カレンダーを取得"""
        try:
            # キャッシュから取得を試行
            cached_data = self.economic_calendar_fetcher.load_calendar_cache(target_date)
            if cached_data:
                self.logger.info("キャッシュから経済カレンダー取得")
                return cached_data
            
            # 新規取得
            calendar_data = self.economic_calendar_fetcher.get_economic_calendar(target_date)
            
            # キャッシュに保存
            self.economic_calendar_fetcher.save_calendar_cache(target_date, calendar_data)
            
            return calendar_data
            
        except Exception as e:
            self.logger.error(f"経済カレンダー取得エラー: {e}")
            return {'previous_day': [], 'today': []}
    
    def _generate_market_notes(self, topics: List[Topic], indicators: List[Dict[str, Any]]) -> List[str]:
        """市場メモを生成"""
        notes = []
        
        # 騰落概況
        positive_count = len([t for t in topics if hasattr(t, 'sentiment') and t.sentiment == 'positive'])
        negative_count = len([t for t in topics if hasattr(t, 'sentiment') and t.sentiment == 'negative'])
        notes.append(f"騰落概況：上昇 {positive_count} / 下落 {negative_count}")
        
        # 出来高（サンプル）
        notes.append("出来高：前日比 +5%")
        
        # イベント
        notes.append("イベント：FOMC前のポジション調整")
        
        return notes
    
    def _save_indicators_cache(self, target_date: datetime, indicators: List[Dict[str, Any]]):
        """指標データをキャッシュに保存"""
        try:
            date_str = target_date.strftime('%Y%m%d')
            cache_dir = Path(self.config.social.output_base_dir) / 'indicators'
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            cache_file = cache_dir / f"{date_str}.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(indicators, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"指標キャッシュ保存エラー: {e}")
    
    def _get_indicators_from_cache(self, target_date: datetime) -> List[Dict[str, Any]]:
        """キャッシュから指標データを取得"""
        try:
            date_str = target_date.strftime('%Y%m%d')
            cache_file = Path(self.config.social.output_base_dir) / 'indicators' / f"{date_str}.json"
            
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
                    
        except Exception as e:
            self.logger.error(f"指標キャッシュ取得エラー: {e}")
        
        return []
    
    def _get_data_sources_info(self) -> Dict[str, Any]:
        """データソース情報を取得"""
        return {
            'artifacts_available': self._check_artifacts_availability(),
            'supabase_available': self.supabase_client.is_available() if self.supabase_client else False,
            'local_db_available': True,  # 常に利用可能
            'indicators_api_available': True,  # Stooq API
            'economic_calendar_available': self._check_economic_calendar_availability()
        }
    
    def _check_artifacts_availability(self) -> bool:
        """アーティファクトの利用可能性をチェック"""
        try:
            # 最新のアーティファクトファイルの存在確認
            today = datetime.now(pytz.timezone('Asia/Tokyo'))
            date_str = today.strftime('%Y%m%d')
            
            artifact_paths = [
                f"build/social/{date_str}/topics.json",
                f"logs/social/{date_str}/topics.json"
            ]
            
            return any(Path(path).exists() for path in artifact_paths)
            
        except Exception:
            return False
    
    def _check_economic_calendar_availability(self) -> bool:
        """経済カレンダーAPIの利用可能性をチェック"""
        try:
            # investpyの利用可能性をチェック
            import investpy
            return True
        except ImportError:
            return False
        except Exception:
            return False
