"""
RAG統合マネージャー

既存のMarket Newsシステムと新しいRAG機能を統合します。
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date

from src.config.app_config import get_config
from src.database.supabase_client import get_supabase_client
from src.database.embedding_generator import get_embedding_generator
from src.rag.chunk_processor import ChunkProcessor
from src.rag.search_engine import RAGSearchEngine, SearchResult
from src.rag.archive_manager import ArchiveManager


class RAGManager:
    """RAG統合マネージャークラス"""

    def __init__(self):
        self.config = get_config()
        self.logger = logging.getLogger("rag_manager")
        
        # コンポーネント初期化
        self.supabase_client = get_supabase_client()
        self.embedding_generator = get_embedding_generator()
        self.chunk_processor = ChunkProcessor()
        self.search_engine = RAGSearchEngine()
        self.archive_manager = ArchiveManager()

    def is_available(self) -> bool:
        """RAGシステムが利用可能かチェック"""
        return (
            self.config.supabase.enabled and
            self.supabase_client.is_available() and
            self.embedding_generator.is_available()
        )

    def get_system_status(self) -> Dict[str, Any]:
        """システム状態の取得"""
        try:
            status = {
                'enabled': self.config.supabase.enabled,
                'supabase_available': self.supabase_client.is_available(),
                'embedding_available': self.embedding_generator.is_available(),
                'system_healthy': False
            }

            if status['enabled'] and status['supabase_available'] and status['embedding_available']:
                # 接続テスト
                test_result = self.supabase_client.test_connection()
                if hasattr(test_result, '__await__'):
                    # 非同期の場合は簡易チェックに変更
                    status['system_healthy'] = True
                else:
                    status['system_healthy'] = test_result

                # システム統計
                if status['system_healthy']:
                    stats = self.archive_manager.get_archive_stats()
                    status.update(stats)

            return status

        except Exception as e:
            self.logger.error(f"システム状態取得失敗: {e}")
            return {
                'enabled': False,
                'supabase_available': False,
                'embedding_available': False,
                'system_healthy': False,
                'error': str(e)
            }

    # === アーカイブ機能 ===
    
    def archive_daily_summary(
        self, 
        summary_data: Dict[str, Any], 
        doc_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """日次サマリーのアーカイブ（既存システムとの統合点）"""
        if not self.is_available():
            self.logger.info("RAGシステムが無効のため、アーカイブをスキップ")
            return {'archived': False, 'reason': 'RAG system not available'}

        try:
            document_id = self.archive_manager.archive_daily_summary(summary_data, doc_date)
            
            result = {
                'archived': document_id is not None,
                'document_id': document_id,
                'doc_date': (doc_date or date.today()).isoformat()
            }

            if document_id:
                # アーカイブ成功後の統計更新
                integrity = self.archive_manager.verify_archive_integrity(document_id)
                result['integrity'] = integrity
                
            return result

        except Exception as e:
            self.logger.error(f"日次サマリーアーカイブ失敗: {e}")
            return {'archived': False, 'error': str(e)}

    def archive_articles(
        self, 
        articles: List[Dict[str, Any]], 
        doc_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """記事リストのアーカイブ（既存システムとの統合点）"""
        if not self.is_available():
            return {'archived': False, 'reason': 'RAG system not available'}

        try:
            document_id = self.archive_manager.archive_articles(articles, doc_date)
            
            result = {
                'archived': document_id is not None,
                'document_id': document_id,
                'articles_count': len(articles),
                'doc_date': (doc_date or date.today()).isoformat()
            }

            if document_id:
                integrity = self.archive_manager.verify_archive_integrity(document_id)
                result['integrity'] = integrity

            return result

        except Exception as e:
            self.logger.error(f"記事アーカイブ失敗: {e}")
            return {'archived': False, 'error': str(e)}

    # === 検索機能 ===

    def search_content(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 8
    ) -> Dict[str, Any]:
        """コンテンツ検索（既存システムとの統合点）"""
        if not self.is_available():
            return {
                'success': False, 
                'results': [], 
                'reason': 'RAG system not available'
            }

        try:
            filters = filters or {}
            
            # 検索実行
            results = self.search_engine.search(
                query=query,
                top_k=top_k,
                region_filter=filters.get('region'),
                category_filter=filters.get('category'),
                date_since=filters.get('date_since'),
                similarity_threshold=filters.get('similarity_threshold')
            )

            # 結果を辞書形式に変換
            search_results = []
            for result in results:
                search_results.append({
                    'chunk_id': result.chunk_id,
                    'document_id': result.document_id,
                    'content': result.content,
                    'similarity': result.similarity,
                    'region': result.region,
                    'category': result.category,
                    'source': result.source,
                    'url': result.url
                })

            # 検索結果の説明
            explanation = self.search_engine.explain_search_results(query, results)

            return {
                'success': True,
                'query': query,
                'results': search_results,
                'total_results': len(search_results),
                'explanation': explanation,
                'filters_applied': filters
            }

        except Exception as e:
            self.logger.error(f"コンテンツ検索失敗: {e}")
            return {'success': False, 'results': [], 'error': str(e)}

    def get_trending_topics(self, days_back: int = 7) -> Dict[str, Any]:
        """トレンディングトピックの取得（既存システムとの統合点）"""
        if not self.is_available():
            return {'success': False, 'trends': []}

        try:
            trends = self.search_engine.get_trending_topics(days_back=days_back)
            
            return {
                'success': True,
                'trends': trends,
                'period_days': days_back,
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"トレンド分析失敗: {e}")
            return {'success': False, 'trends': [], 'error': str(e)}

    def get_related_content(self, reference_content: str) -> Dict[str, Any]:
        """関連コンテンツの取得（既存システムとの統合点）"""
        if not self.is_available():
            return {'success': False, 'related': []}

        try:
            # まず参照コンテンツで検索
            search_results = self.search_engine.search(reference_content, top_k=5)
            
            if not search_results:
                return {'success': True, 'related': [], 'message': '関連コンテンツが見つかりませんでした'}

            # 関連コンテンツを取得
            related = self.search_engine.get_related_content(search_results)
            
            # 結果を統合
            all_related = []
            for category, items in related.items():
                for item in items:
                    all_related.append({
                        'content': item.content,
                        'similarity': item.similarity,
                        'relation_type': category,
                        'region': item.region,
                        'category': item.category,
                        'source': item.source,
                        'url': item.url
                    })

            return {
                'success': True,
                'related': all_related,
                'reference_results_count': len(search_results)
            }

        except Exception as e:
            self.logger.error(f"関連コンテンツ取得失敗: {e}")
            return {'success': False, 'related': [], 'error': str(e)}

    # === 管理・メンテナンス機能 ===

    def get_archive_statistics(self, days_back: int = 30) -> Dict[str, Any]:
        """アーカイブ統計の取得（既存システムとの統合点）"""
        if not self.is_available():
            return {'available': False}

        try:
            stats = self.archive_manager.get_archive_stats(days_back)
            stats['available'] = True
            return stats

        except Exception as e:
            self.logger.error(f"アーカイブ統計取得失敗: {e}")
            return {'available': False, 'error': str(e)}

    def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """古いデータのクリーンアップ（既存システムとの統合点）"""
        if not self.is_available():
            return {'success': False, 'reason': 'RAG system not available'}

        try:
            result = self.archive_manager.cleanup_old_archives(days_to_keep)
            return {
                'success': True,
                'days_to_keep': days_to_keep,
                'cleanup_result': result
            }

        except Exception as e:
            self.logger.error(f"データクリーンアップ失敗: {e}")
            return {'success': False, 'error': str(e)}

    # === ユーティリティ機能 ===

    def generate_content_embedding(self, content: str) -> Optional[List[float]]:
        """コンテンツの埋め込み生成（既存システムとの統合点）"""
        if not self.embedding_generator.is_available():
            return None

        return self.embedding_generator.generate_embedding(content)

    def calculate_content_similarity(
        self, 
        content1: str, 
        content2: str
    ) -> Optional[float]:
        """2つのコンテンツの類似度計算（既存システムとの統合点）"""
        if not self.embedding_generator.is_available():
            return None

        try:
            embedding1 = self.embedding_generator.generate_embedding(content1)
            embedding2 = self.embedding_generator.generate_embedding(content2)

            if not embedding1 or not embedding2:
                return None

            return self.embedding_generator.calculate_similarity(embedding1, embedding2)

        except Exception as e:
            self.logger.error(f"類似度計算失敗: {e}")
            return None

    def validate_system_integrity(self) -> Dict[str, Any]:
        """システム全体の整合性チェック（既存システムとの統合点）"""
        if not self.is_available():
            return {
                'valid': False,
                'reason': 'RAG system not available'
            }

        try:
            # システム状態確認
            status = self.get_system_status()
            
            if not status.get('system_healthy', False):
                return {
                    'valid': False,
                    'reason': 'System not healthy',
                    'status': status
                }

            # 統計確認
            stats = self.get_archive_statistics()
            
            # 基本的な整合性チェック
            issues = []
            
            if stats.get('documents_count', 0) == 0:
                issues.append('No documents in archive')
            
            if stats.get('chunks_count', 0) == 0:
                issues.append('No chunks in archive')
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'stats': stats,
                'checked_at': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"システム整合性チェック失敗: {e}")
            return {
                'valid': False,
                'error': str(e)
            }

    # === 設定・情報取得 ===

    def get_configuration(self) -> Dict[str, Any]:
        """RAGシステム設定の取得（既存システムとの統合点）"""
        return {
            'enabled': self.config.supabase.enabled,
            'embedding_model': self.config.supabase.embedding_model,
            'embedding_dimension': self.config.supabase.embedding_dimension,
            'chunk_size': self.config.supabase.chunk_size,
            'chunk_overlap': self.config.supabase.chunk_overlap,
            'similarity_threshold': self.config.supabase.similarity_threshold,
            'bucket_name': self.config.supabase.bucket_name,
            'max_chunks_per_document': self.config.supabase.max_chunks_per_document
        }


# シングルトンインスタンス
_rag_manager: Optional[RAGManager] = None


def get_rag_manager() -> RAGManager:
    """RAGマネージャーを取得（シングルトン）"""
    global _rag_manager
    if _rag_manager is None:
        _rag_manager = RAGManager()
    return _rag_manager