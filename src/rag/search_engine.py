"""
RAG検索エンジン

ベクター類似検索とメタデータフィルタリングを組み合わせた検索機能を提供します。
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.config.app_config import SupabaseConfig, get_config
from src.database.supabase_client import get_supabase_client
from src.database.embedding_generator import get_embedding_generator
from src.rag.chunk_processor import TextChunk


@dataclass
class SearchResult:
    """検索結果"""
    chunk_id: int
    document_id: str
    content: str
    similarity: float
    region: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    doc_date: Optional[str] = None


class RAGSearchEngine:
    """RAG検索エンジンクラス"""

    def __init__(self, config: Optional[SupabaseConfig] = None):
        self.config = config or get_config().supabase
        self.logger = logging.getLogger("rag_search_engine")
        self.supabase_client = get_supabase_client()
        self.embedding_generator = get_embedding_generator()

    def search(
        self,
        query: str,
        top_k: int = 8,
        region_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        date_since: Optional[datetime] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """類似検索実行"""
        
        if not self.supabase_client.is_available():
            self.logger.warning("Supabaseが利用できません")
            return []

        if not self.embedding_generator.is_available():
            self.logger.warning("埋め込み生成器が利用できません")
            return []

        try:
            # クエリの埋め込み生成
            query_embedding = self.embedding_generator.generate_embedding(query)
            if not query_embedding:
                self.logger.error("クエリの埋め込み生成に失敗しました")
                return []

            # 日付フィルターの準備
            date_since_str = None
            if date_since:
                date_since_str = date_since.strftime('%Y-%m-%d')

            # Supabaseで類似検索実行
            search_results = self.supabase_client.search_chunks(
                query_embedding=query_embedding,
                match_count=top_k,
                region_filter=region_filter,
                category_filter=category_filter,
                date_since=date_since_str
            )

            # 類似度フィルタリング
            threshold = similarity_threshold or self.config.similarity_threshold
            filtered_results = [
                result for result in search_results 
                if result.get('similarity', 0) >= threshold
            ]

            # SearchResultオブジェクトに変換
            results = []
            for result in filtered_results:
                search_result = SearchResult(
                    chunk_id=result.get('chunk_id'),
                    document_id=result.get('document_id'),
                    content=result.get('content', ''),
                    similarity=result.get('similarity', 0.0),
                    region=result.get('region'),
                    category=result.get('category'),
                    source=result.get('source'),
                    url=result.get('url'),
                    doc_date=None  # 必要に応じてdocument情報から取得
                )
                results.append(search_result)

            self.logger.info(f"検索完了: {len(results)}件（閾値: {threshold}）")
            return results

        except Exception as e:
            self.logger.error(f"検索失敗: {e}")
            return []

    def search_by_keywords(
        self,
        keywords: List[str],
        **kwargs
    ) -> List[SearchResult]:
        """キーワードリストによる検索"""
        if not keywords:
            return []

        # キーワードを結合してクエリ作成
        query = " ".join(keywords)
        return self.search(query, **kwargs)

    def search_similar_to_chunk(
        self,
        chunk_id: int,
        top_k: int = 5,
        exclude_self: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """既存チャンクに類似したチャンクを検索"""
        try:
            # 指定されたチャンクの埋め込みを取得
            # 注意: この実装では簡略化のため、チャンクの内容から埋め込みを再生成
            # 本来はSupabaseからembeddingを直接取得すべき
            
            # チャンク内容を取得（簡略実装）
            if not self.supabase_client.is_available():
                return []

            # チャンクの内容を取得してクエリとして使用
            chunk_result = self.supabase_client.client.table('chunks').select('content').eq('id', chunk_id).execute()
            if not chunk_result.data:
                self.logger.warning(f"チャンクが見つかりません: {chunk_id}")
                return []

            chunk_content = chunk_result.data[0].get('content', '')
            if not chunk_content:
                return []

            # 類似検索実行
            results = self.search(chunk_content, top_k=top_k + (1 if exclude_self else 0), **kwargs)
            
            # 自分自身を除外
            if exclude_self:
                results = [r for r in results if r.chunk_id != chunk_id][:top_k]

            return results

        except Exception as e:
            self.logger.error(f"類似チャンク検索失敗: {e}")
            return []

    def search_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        query: Optional[str] = None,
        **kwargs
    ) -> List[SearchResult]:
        """日付範囲での検索"""
        if not query:
            # クエリが指定されていない場合は全体検索
            query = "マーケット ニュース 経済"

        # 日付フィルターを適用
        kwargs['date_since'] = start_date
        
        results = self.search(query, **kwargs)
        
        # 終了日でのフィルタリング（Supabase側でサポートされていない場合）
        end_date_str = end_date.strftime('%Y-%m-%d')
        filtered_results = []
        
        for result in results:
            if result.doc_date and result.doc_date <= end_date_str:
                filtered_results.append(result)
            elif not result.doc_date:  # doc_dateが取得できない場合は含める
                filtered_results.append(result)
                
        return filtered_results

    def get_trending_topics(
        self, 
        days_back: int = 7,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """トレンディングトピックの分析"""
        try:
            # 過去N日間のデータを取得
            date_since = datetime.now() - timedelta(days=days_back)
            
            # 幅広いキーワードで検索
            broad_results = self.search(
                query="経済 市場 企業 政策 技術",
                top_k=100,
                date_since=date_since
            )

            if not broad_results:
                return []

            # カテゴリ・地域別に集計
            category_counts = {}
            region_counts = {}
            
            for result in broad_results:
                if result.category:
                    category_counts[result.category] = category_counts.get(result.category, 0) + 1
                if result.region:
                    region_counts[result.region] = region_counts.get(result.region, 0) + 1

            # トップ項目を抽出
            trending_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:top_k//2]
            trending_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:top_k//2]

            trends = []
            
            # カテゴリトレンド
            for category, count in trending_categories:
                trends.append({
                    'type': 'category',
                    'topic': category,
                    'count': count,
                    'trend_score': count / len(broad_results)
                })
            
            # 地域トレンド
            for region, count in trending_regions:
                trends.append({
                    'type': 'region',
                    'topic': region,
                    'count': count,
                    'trend_score': count / len(broad_results)
                })

            # トレンドスコア順にソート
            trends.sort(key=lambda x: x['trend_score'], reverse=True)
            
            self.logger.info(f"トレンド分析完了: {len(trends)}件")
            return trends[:top_k]

        except Exception as e:
            self.logger.error(f"トレンド分析失敗: {e}")
            return []

    def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """検索候補の生成"""
        try:
            # 部分クエリに基づく検索
            results = self.search(partial_query, top_k=20)
            
            if not results:
                return []

            # カテゴリと地域から候補を生成
            suggestions = set()
            
            for result in results:
                if result.category:
                    suggestions.add(f"{partial_query} {result.category}")
                if result.region:
                    suggestions.add(f"{partial_query} {result.region}")
                if result.source:
                    suggestions.add(f"{partial_query} {result.source}")

            return list(suggestions)[:limit]

        except Exception as e:
            self.logger.error(f"検索候補生成失敗: {e}")
            return []

    def get_related_content(self, search_results: List[SearchResult]) -> Dict[str, List[SearchResult]]:
        """関連コンテンツの取得"""
        if not search_results:
            return {}

        related_content = {
            'same_category': [],
            'same_region': [],
            'same_source': []
        }

        try:
            # 最初の結果を基準にして関連コンテンツを検索
            base_result = search_results[0]
            
            # 同じカテゴリ
            if base_result.category:
                category_results = self.search(
                    query="",  # 空クエリでメタフィルタのみ適用
                    category_filter=base_result.category,
                    top_k=5
                )
                related_content['same_category'] = [
                    r for r in category_results if r.chunk_id != base_result.chunk_id
                ]

            # 同じ地域
            if base_result.region:
                region_results = self.search(
                    query="",
                    region_filter=base_result.region,
                    top_k=5
                )
                related_content['same_region'] = [
                    r for r in region_results if r.chunk_id != base_result.chunk_id
                ]

            # 同じソース（簡略実装）
            # 注意: この実装ではsource_filterがSupabase関数でサポートされていないと仮定

        except Exception as e:
            self.logger.error(f"関連コンテンツ取得失敗: {e}")

        return related_content

    def explain_search_results(self, query: str, results: List[SearchResult]) -> Dict[str, Any]:
        """検索結果の説明生成"""
        if not results:
            return {
                'total_results': 0,
                'explanation': 'マッチする結果が見つかりませんでした。',
                'suggestions': ['キーワードを変更してみてください', 'より一般的な用語を使用してください']
            }

        # 統計分析
        categories = [r.category for r in results if r.category]
        regions = [r.region for r in results if r.region]
        sources = [r.source for r in results if r.source]
        
        avg_similarity = sum(r.similarity for r in results) / len(results)

        return {
            'total_results': len(results),
            'average_similarity': avg_similarity,
            'top_categories': list(set(categories)),
            'top_regions': list(set(regions)),
            'top_sources': list(set(sources)),
            'explanation': f'"{query}"に関連する{len(results)}件の結果が見つかりました。',
            'quality_note': '高い' if avg_similarity > 0.8 else '中程度' if avg_similarity > 0.6 else '低い'
        }

    def get_search_history_insights(self, search_history: List[str]) -> Dict[str, Any]:
        """検索履歴からのインサイト生成"""
        if not search_history:
            return {}

        try:
            # 検索履歴の分析
            query_analysis = {}
            
            for query in search_history[-10:]:  # 最新10件を分析
                results = self.search(query, top_k=5)
                
                if results:
                    categories = [r.category for r in results if r.category]
                    regions = [r.region for r in results if r.region]
                    
                    query_analysis[query] = {
                        'result_count': len(results),
                        'top_categories': list(set(categories)),
                        'top_regions': list(set(regions))
                    }

            return {
                'analyzed_queries': len(query_analysis),
                'query_patterns': query_analysis,
                'recommendations': ['検索履歴に基づく個別推奨を実装予定']
            }

        except Exception as e:
            self.logger.error(f"検索履歴分析失敗: {e}")
            return {}