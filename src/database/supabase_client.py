"""
Supabaseクライアント管理

Supabaseへの接続と基本操作を提供します。
"""

import logging
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager
from supabase import create_client, Client
from src.config.app_config import SupabaseConfig, get_config


class SupabaseClient:
    """Supabaseクライアント管理クラス"""

    def __init__(self, config: Optional[SupabaseConfig] = None):
        self.config = config or get_config().supabase
        self.logger = logging.getLogger("supabase_client")
        self._client: Optional[Client] = None
        
        if not self.config.enabled:
            self.logger.info("Supabase機能は無効化されています")
            return
            
        if not self.config.url or not self.config.anon_key:
            self.logger.warning("Supabase設定が不完全です。URL、APIキーを確認してください")
            return

    @property
    def client(self) -> Optional[Client]:
        """Supabaseクライアントを取得"""
        if not self.config.enabled:
            return None
            
        if self._client is None:
            try:
                self._client = create_client(
                    self.config.url,
                    self.config.anon_key
                )
                self.logger.info("Supabaseクライアント接続成功")
            except Exception as e:
                self.logger.error(f"Supabaseクライアント接続失敗: {e}")
                return None
                
        return self._client

    def is_available(self) -> bool:
        """Supabaseが利用可能かチェック"""
        return (
            self.config.enabled 
            and bool(self.config.url) 
            and bool(self.config.anon_key)
            and self.client is not None
        )

    async def test_connection(self) -> bool:
        """接続テスト"""
        if not self.is_available():
            return False
            
        try:
            # documentsテーブルへの簡単なクエリでテスト
            result = self.client.table('documents').select('id').limit(1).execute()
            return True
        except Exception as e:
            self.logger.error(f"Supabase接続テスト失敗: {e}")
            return False

    # Document操作
    def create_document(self, doc_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """ドキュメント作成"""
        if not self.is_available():
            return None
            
        try:
            result = self.client.table('documents').insert(doc_data).execute()
            if result.data:
                self.logger.info(f"ドキュメント作成成功: {result.data[0].get('id')}")
                return result.data[0]
        except Exception as e:
            self.logger.error(f"ドキュメント作成失敗: {e}")
        return None

    def get_document_by_date(self, doc_date: str, doc_type: str = 'daily_summary') -> Optional[Dict[str, Any]]:
        """日付でドキュメント取得"""
        if not self.is_available():
            return None
            
        try:
            result = self.client.table('documents').select('*').eq('doc_date', doc_date).eq('doc_type', doc_type).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            self.logger.error(f"ドキュメント取得失敗: {e}")
        return None

    def upsert_document(self, doc_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """ドキュメントのUpsert（存在すれば更新、存在しなければ作成）"""
        if not self.is_available():
            return None
            
        try:
            result = self.client.table('documents').upsert(doc_data).execute()
            if result.data:
                self.logger.info(f"ドキュメントUpsert成功: {result.data[0].get('id')}")
                return result.data[0]
        except Exception as e:
            self.logger.error(f"ドキュメントUpsert失敗: {e}")
        return None

    # Chunk操作
    def create_chunks(self, chunks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """チャンク一括作成"""
        if not self.is_available():
            return []
            
        try:
            result = self.client.table('chunks').insert(chunks_data).execute()
            if result.data:
                self.logger.info(f"チャンク作成成功: {len(result.data)}件")
                return result.data
        except Exception as e:
            self.logger.error(f"チャンク作成失敗: {e}")
        return []

    def delete_chunks_by_document_id(self, document_id: str) -> bool:
        """ドキュメントIDでチャンクを削除"""
        if not self.is_available():
            return False
            
        try:
            result = self.client.table('chunks').delete().eq('document_id', document_id).execute()
            self.logger.info(f"チャンク削除成功: document_id={document_id}")
            return True
        except Exception as e:
            self.logger.error(f"チャンク削除失敗: {e}")
        return False

    def search_chunks(
        self, 
        query_embedding: List[float], 
        match_count: int = 8,
        region_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        date_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """チャンクベクター検索"""
        if not self.is_available():
            return []
            
        try:
            # search_chunks関数を呼び出し
            result = self.client.rpc('search_chunks', {
                'query_embedding': query_embedding,
                'match_count': match_count,
                'region_filter': region_filter,
                'category_filter': category_filter,
                'date_since': date_since
            }).execute()
            
            if result.data:
                self.logger.info(f"ベクター検索成功: {len(result.data)}件")
                return result.data
        except Exception as e:
            self.logger.error(f"ベクター検索失敗: {e}")
        return []

    # Storage操作
    def upload_file(self, bucket_name: str, file_path: str, file_data: bytes) -> Optional[str]:
        """ファイルアップロード"""
        if not self.is_available():
            return None
            
        try:
            result = self.client.storage.from_(bucket_name).upload(file_path, file_data)
            if result:
                self.logger.info(f"ファイルアップロード成功: {file_path}")
                return file_path
        except Exception as e:
            self.logger.error(f"ファイルアップロード失敗: {e}")
        return None

    def download_file(self, bucket_name: str, file_path: str) -> Optional[bytes]:
        """ファイルダウンロード"""
        if not self.is_available():
            return None
            
        try:
            result = self.client.storage.from_(bucket_name).download(file_path)
            if result:
                self.logger.info(f"ファイルダウンロード成功: {file_path}")
                return result
        except Exception as e:
            self.logger.error(f"ファイルダウンロード失敗: {e}")
        return None

    def get_file_url(self, bucket_name: str, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """署名付きURL取得"""
        if not self.is_available():
            return None
            
        try:
            result = self.client.storage.from_(bucket_name).create_signed_url(file_path, expires_in)
            if result:
                return result.get('signedURL')
        except Exception as e:
            self.logger.error(f"署名付きURL取得失敗: {e}")
        return None

    # 統計・メンテナンス
    def get_storage_stats(self) -> Dict[str, Any]:
        """ストレージ使用量統計"""
        if not self.is_available():
            return {}
            
        try:
            # ドキュメント数
            doc_result = self.client.table('documents').select('id', count='exact').execute()
            doc_count = doc_result.count if hasattr(doc_result, 'count') else 0
            
            # チャンク数
            chunk_result = self.client.table('chunks').select('id', count='exact').execute()
            chunk_count = chunk_result.count if hasattr(chunk_result, 'count') else 0
            
            return {
                'documents_count': doc_count,
                'chunks_count': chunk_count,
                'bucket_name': self.config.bucket_name
            }
        except Exception as e:
            self.logger.error(f"統計取得失敗: {e}")
            return {}

    def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """古いデータのクリーンアップ"""
        if not self.is_available():
            return {'deleted_documents': 0, 'deleted_chunks': 0}
            
        try:
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
            
            # 古いドキュメントを削除（CASCADE設定によりチャンクも自動削除）
            result = self.client.table('documents').delete().lt('doc_date', cutoff_date).execute()
            deleted_docs = len(result.data) if result.data else 0
            
            self.logger.info(f"データクリーンアップ完了: {deleted_docs}件のドキュメント削除")
            
            return {
                'deleted_documents': deleted_docs,
                'cutoff_date': cutoff_date
            }
        except Exception as e:
            self.logger.error(f"データクリーンアップ失敗: {e}")
            return {'deleted_documents': 0, 'deleted_chunks': 0}


# シングルトンインスタンス
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Supabaseクライアントを取得（シングルトン）"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client