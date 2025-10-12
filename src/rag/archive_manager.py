"""
アーカイブマネージャー

日次サマリーと記事データをSupabaseにアーカイブし、長期保存・検索を可能にします。
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from dataclasses import asdict

from src.config.app_config import SupabaseConfig, get_config
from src.database.supabase_client import get_supabase_client
from src.database.embedding_generator import get_embedding_generator
from src.rag.chunk_processor import ChunkProcessor, TextChunk


class ArchiveManager:
    """アーカイブマネージャークラス"""

    def __init__(self, config: Optional[SupabaseConfig] = None):
        self.config = config or get_config().supabase
        self.logger = logging.getLogger("archive_manager")
        self.supabase_client = get_supabase_client()
        self.embedding_generator = get_embedding_generator()
        self.chunk_processor = ChunkProcessor(config)

    def archive_daily_summary(
        self,
        summary_data: Dict[str, Any],
        doc_date: Optional[date] = None
    ) -> Optional[str]:
        """日次サマリーをアーカイブ"""
        
        if not self.supabase_client.is_available():
            self.logger.warning("Supabaseが利用できないため、アーカイブをスキップします")
            return None

        doc_date = doc_date or date.today()
        
        try:
            # 1. ドキュメントレコードを作成
            document_data = {
                'doc_date': doc_date.isoformat(),
                'doc_type': 'daily_summary',
                'url': summary_data.get('url', ''),
                'tokens': self._estimate_token_count(summary_data),
            }

            # 既存ドキュメントをチェック
            existing_doc = self.supabase_client.get_document_by_date(
                doc_date.isoformat(), 
                'daily_summary'
            )

            if existing_doc:
                self.logger.info(f"既存の日次サマリーを更新: {doc_date}")
                document_data['id'] = existing_doc['id']
                # 既存のチャンクを削除
                self.supabase_client.delete_chunks_by_document_id(existing_doc['id'])
            else:
                self.logger.info(f"新しい日次サマリーを作成: {doc_date}")

            # ドキュメントをUpsert
            document = self.supabase_client.upsert_document(document_data)
            if not document:
                self.logger.error("ドキュメント作成に失敗しました")
                return None

            document_id = document['id']

            # 2. チャンクを作成
            chunks = self.chunk_processor.create_chunks_for_summary(summary_data)
            if not chunks:
                self.logger.warning("チャンクが作成されませんでした")
                return document_id

            # 3. 埋め込み生成
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_generator.generate_embeddings_batch(chunk_texts)

            if len(embeddings) != len(chunks):
                self.logger.error("埋め込み生成数がチャンク数と一致しません")
                return document_id

            # 4. チャンクデータを準備
            chunk_records = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                if embedding is None:
                    self.logger.warning(f"チャンク{i+1}の埋め込み生成に失敗")
                    continue

                if not self.embedding_generator.validate_embedding(embedding):
                    self.logger.warning(f"チャンク{i+1}の埋め込みが無効")
                    continue

                chunk_record = {
                    'document_id': document_id,
                    'chunk_no': chunk.chunk_no,
                    'content': chunk.content,
                    'region': chunk.region,
                    'category': chunk.category,
                    'source': chunk.source,
                    'url': chunk.url,
                    'embedding': embedding
                }
                chunk_records.append(chunk_record)

            # 5. チャンクを一括保存
            if chunk_records:
                saved_chunks = self.supabase_client.create_chunks(chunk_records)
                self.logger.info(f"日次サマリーアーカイブ完了: {len(saved_chunks)}チャンク保存")
            else:
                self.logger.warning("保存可能なチャンクがありませんでした")

            # 6. Storageにも保存（JSON形式）
            self._save_to_storage(summary_data, doc_date, 'daily_summary')

            return document_id

        except Exception as e:
            self.logger.error(f"日次サマリーアーカイブ失敗: {e}")
            return None

    def _archive_single_article_document(
        self,
        article: Dict[str, Any],
        doc_date: date
    ) -> Optional[str]:
        """単一記事を個別ドキュメントとしてアーカイブ"""
        try:
            # 記事本文は 'content' または 'body' キーから取得
            article_content = article.get('content') or article.get('body', '')
            
            # 1. ドキュメントレコードを作成
            document_data = {
                'title': article.get('title', ''),
                'content': article_content,
                'doc_date': doc_date.isoformat(),
                'doc_type': 'article',
                'url': article.get('url', ''),
                'tokens': self._estimate_article_tokens(article),
                # トップレベルフィールドとしてcategory, region, sourceを保存
                'source': article.get('source', 'google_drive_recovery'),
                'category': article.get('category', ''),
                'region': article.get('region', ''),
                'metadata': {
                    'source_type': 'google_drive_recovery',
                    'published_at': article.get('published_at', ''),
                }
            }

            # 既存ドキュメントをチェック（タイトルで）
            existing_doc = None
            if document_data.get('title'):
                try:
                    result = self.supabase_client.client.table('documents').select('*').eq('title', document_data['title']).execute()
                    if result.data:
                        existing_doc = result.data[0]
                except Exception as e:
                    self.logger.warning(f"既存ドキュメントチェック失敗: {e}")

            if existing_doc:
                self.logger.info(f"既存の記事を更新: {document_data['title'][:50]}...")
                document_data['id'] = existing_doc['id']
                self.supabase_client.delete_chunks_by_document_id(existing_doc['id'])
            else:
                self.logger.info(f"新しい記事を作成: {document_data['title'][:50]}...")

            document = self.supabase_client.upsert_document(document_data)
            if not document:
                self.logger.error("ドキュメント作成に失敗しました")
                return None

            document_id = document['id']

            # 2. 記事からチャンクを作成
            chunks = self.chunk_processor.create_chunks_from_articles([article])
            if not chunks:
                self.logger.warning("記事からチャンクが作成されませんでした")
                return document_id

            # 3. 埋め込み生成
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_generator.generate_embeddings_batch(chunk_texts)

            if len(embeddings) != len(chunks):
                self.logger.error("埋め込み生成数がチャンク数と一致しません")
                return document_id

            # 4. チャンクデータを保存
            chunk_records = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                if embedding is None:
                    self.logger.warning(f"チャンク{i+1}の埋め込み生成に失敗")
                    continue

                if not self.embedding_generator.validate_embedding(embedding):
                    self.logger.warning(f"チャンク{i+1}の埋め込みが無効")
                    continue

                chunk_record = {
                    'document_id': document_id,
                    'content': chunk.content,
                    'chunk_index': i,
                    'embedding': embedding.tolist(),
                    'metadata': {
                        'start_pos': chunk.start_pos,
                        'end_pos': chunk.end_pos,
                    }
                }
                chunk_records.append(chunk_record)

            # チャンクをバルク保存
            if chunk_records:
                saved_chunks = self.supabase_client.create_chunks_bulk(chunk_records)
                self.logger.info(f"チャンク保存完了: {saved_chunks}件")

            return document_id

        except Exception as e:
            self.logger.error(f"単一記事アーカイブ失敗: {e}")
            return None

    def archive_single_article(
        self,
        article: Dict[str, Any],
        doc_date: Optional[date] = None
    ) -> Optional[str]:
        """単一記事をアーカイブ"""
        doc_date = doc_date or date.today()
        return self._archive_single_article_document(article, doc_date)

    def archive_articles(
        self,
        articles: List[Dict[str, Any]],
        doc_date: Optional[date] = None
    ) -> Optional[str]:
        """記事リストをアーカイブ"""

        if not self.supabase_client.is_available():
            self.logger.warning("Supabaseが利用できないため、アーカイブをスキップします")
            return None

        if not articles:
            self.logger.warning("アーカイブする記事がありません")
            return None

        doc_date = doc_date or date.today()

        try:
            # 単一記事の場合は個別ドキュメントとして保存
            if len(articles) == 1:
                article = articles[0]
                return self._archive_single_article_document(article, doc_date)

            # 複数記事の場合はコーパスとして保存
            # 1. ドキュメントレコードを作成
            document_data = {
                'doc_date': doc_date.isoformat(),
                'doc_type': 'full_corpus',
                'tokens': sum(self._estimate_article_tokens(article) for article in articles),
            }

            # 既存ドキュメントをチェック
            existing_doc = self.supabase_client.get_document_by_date(
                doc_date.isoformat(),
                'full_corpus'
            )

            if existing_doc:
                self.logger.info(f"既存の記事コーパスを更新: {doc_date}")
                document_data['id'] = existing_doc['id']
                self.supabase_client.delete_chunks_by_document_id(existing_doc['id'])
            else:
                self.logger.info(f"新しい記事コーパスを作成: {doc_date}")

            document = self.supabase_client.upsert_document(document_data)
            if not document:
                self.logger.error("ドキュメント作成に失敗しました")
                return None

            document_id = document['id']

            # 2. 記事からチャンクを作成
            chunks = self.chunk_processor.create_chunks_from_articles(articles)
            if not chunks:
                self.logger.warning("記事からチャンクが作成されませんでした")
                return document_id

            # チャンク数制限
            max_chunks = self.config.max_chunks_per_document
            if len(chunks) > max_chunks:
                self.logger.info(f"チャンク数を制限: {len(chunks)} → {max_chunks}")
                chunks = chunks[:max_chunks]

            # 3. 埋め込み生成（バッチ処理）
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_generator.generate_embeddings_batch(chunk_texts)

            # 4. チャンクデータを準備
            chunk_records = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                if embedding is None or not self.embedding_generator.validate_embedding(embedding):
                    continue

                chunk_record = {
                    'document_id': document_id,
                    'content': chunk.content,
                    'chunk_index': chunk.chunk_no,
                    'embedding': embedding.tolist(),
                    'metadata': {
                        'region': chunk.region,
                        'category': chunk.category,
                        'source': chunk.source,
                        'url': chunk.url,
                    }
                }
                chunk_records.append(chunk_record)

            # 5. チャンクを一括保存
            if chunk_records:
                saved_chunks = self.supabase_client.create_chunks(chunk_records)
                self.logger.info(f"記事アーカイブ完了: {len(articles)}記事 → {len(saved_chunks)}チャンク保存")
            
            # 6. Storageにも保存
            corpus_data = {
                'articles': articles,
                'metadata': {
                    'total_articles': len(articles),
                    'total_chunks': len(chunk_records),
                    'archived_at': datetime.now().isoformat()
                }
            }
            self._save_to_storage(corpus_data, doc_date, 'full_corpus')

            return document_id

        except Exception as e:
            self.logger.error(f"記事アーカイブ失敗: {e}")
            return None

    def get_archive_stats(self, days_back: int = 30) -> Dict[str, Any]:
        """アーカイブ統計情報取得"""
        if not self.supabase_client.is_available():
            return {}

        try:
            stats = self.supabase_client.get_storage_stats()
            
            # 追加統計情報
            from datetime import timedelta
            date_since = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            # 期間内の文書・チャンク統計
            recent_docs = self.supabase_client.client.table('documents')\
                .select('*', count='exact')\
                .gte('doc_date', date_since)\
                .execute()
            
            recent_chunks = self.supabase_client.client.table('chunks')\
                .select('id', count='exact')\
                .gte('created_at', date_since)\
                .execute()

            stats.update({
                'recent_documents': recent_docs.count if hasattr(recent_docs, 'count') else 0,
                'recent_chunks': recent_chunks.count if hasattr(recent_chunks, 'count') else 0,
                'analysis_period_days': days_back,
                'embedding_model': self.config.embedding_model,
                'chunk_size': self.config.chunk_size
            })

            return stats

        except Exception as e:
            self.logger.error(f"アーカイブ統計取得失敗: {e}")
            return {}

    def cleanup_old_archives(self, days_to_keep: int = 90) -> Dict[str, int]:
        """古いアーカイブのクリーンアップ"""
        if not self.supabase_client.is_available():
            return {'deleted': 0}

        try:
            result = self.supabase_client.cleanup_old_data(days_to_keep)
            self.logger.info(f"アーカイブクリーンアップ完了: {result}")
            return result

        except Exception as e:
            self.logger.error(f"アーカイブクリーンアップ失敗: {e}")
            return {'deleted': 0}

    def export_archive_data(
        self,
        start_date: date,
        end_date: date,
        doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """アーカイブデータのエクスポート"""
        if not self.supabase_client.is_available():
            return []

        try:
            # 日付範囲でドキュメントを検索
            query = self.supabase_client.client.table('documents')\
                .select('*')\
                .gte('doc_date', start_date.isoformat())\
                .lte('doc_date', end_date.isoformat())

            if doc_type:
                query = query.eq('doc_type', doc_type)

            documents = query.execute()

            if not documents.data:
                return []

            # 各ドキュメントのチャンクを取得
            export_data = []
            for doc in documents.data:
                chunks = self.supabase_client.client.table('chunks')\
                    .select('*')\
                    .eq('document_id', doc['id'])\
                    .execute()

                export_item = {
                    'document': doc,
                    'chunks': chunks.data if chunks.data else []
                }
                export_data.append(export_item)

            self.logger.info(f"アーカイブエクスポート完了: {len(export_data)}ドキュメント")
            return export_data

        except Exception as e:
            self.logger.error(f"アーカイブエクスポート失敗: {e}")
            return []

    def _save_to_storage(self, data: Dict[str, Any], doc_date: date, doc_type: str):
        """Supabase Storageにデータを保存"""
        if not self.supabase_client.is_available():
            return

        try:
            # ファイルパス生成
            year = doc_date.year
            month = doc_date.month
            day = doc_date.day
            
            if doc_type == 'daily_summary':
                file_path = f"{year}/{month:02d}/{day:02d}/daily_summary.json"
            else:
                file_path = f"{year}/{month:02d}/{day:02d}/corpus.json"

            # JSONデータを準備
            storage_data = {
                'data': data,
                'metadata': {
                    'doc_date': doc_date.isoformat(),
                    'doc_type': doc_type,
                    'created_at': datetime.now().isoformat(),
                    'version': '1.0'
                }
            }

            # バイトデータに変換
            json_bytes = json.dumps(storage_data, ensure_ascii=False, indent=2).encode('utf-8')

            # アップロード
            result = self.supabase_client.upload_file(
                bucket_name=self.config.bucket_name,
                file_path=file_path,
                file_data=json_bytes
            )

            if result:
                self.logger.info(f"Storage保存成功: {file_path}")
            else:
                self.logger.warning(f"Storage保存失敗: {file_path}")

        except Exception as e:
            self.logger.error(f"Storage保存エラー: {e}")

    def _estimate_token_count(self, data: Dict[str, Any]) -> int:
        """概算トークン数計算"""
        # 簡易実装: 文字数の1/4をトークン数として概算
        total_chars = 0
        
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, str):
                    total_chars += len(value)
                elif isinstance(value, dict):
                    total_chars += self._estimate_token_count(value)
                    
        return total_chars // 4

    def _estimate_article_tokens(self, article: Dict[str, Any]) -> int:
        """記事の概算トークン数計算"""
        total_chars = 0
        # 記事本文は 'content' または 'body' のいずれかに格納されている
        for field in ['title', 'summary', 'content', 'body']:
            if field in article and article[field]:
                total_chars += len(str(article[field]))
        return total_chars // 4

    def verify_archive_integrity(self, document_id: str) -> Dict[str, Any]:
        """アーカイブの整合性確認"""
        if not self.supabase_client.is_available():
            return {'valid': False, 'error': 'Supabaseが利用できません'}

        try:
            # ドキュメント存在確認
            doc_result = self.supabase_client.client.table('documents')\
                .select('*')\
                .eq('id', document_id)\
                .execute()

            if not doc_result.data:
                return {'valid': False, 'error': 'ドキュメントが見つかりません'}

            document = doc_result.data[0]

            # チャンク存在確認
            chunks_result = self.supabase_client.client.table('chunks')\
                .select('id, embedding', count='exact')\
                .eq('document_id', document_id)\
                .execute()

            chunks_count = chunks_result.count if hasattr(chunks_result, 'count') else 0
            
            # 埋め込み妥当性確認
            invalid_embeddings = 0
            if chunks_result.data:
                for chunk in chunks_result.data:
                    embedding = chunk.get('embedding')
                    if not embedding or not self.embedding_generator.validate_embedding(embedding):
                        invalid_embeddings += 1

            return {
                'valid': invalid_embeddings == 0,
                'document_id': document_id,
                'doc_type': document.get('doc_type'),
                'doc_date': document.get('doc_date'),
                'chunks_count': chunks_count,
                'invalid_embeddings': invalid_embeddings,
                'integrity_score': 1.0 - (invalid_embeddings / max(chunks_count, 1))
            }

        except Exception as e:
            self.logger.error(f"整合性確認失敗: {e}")
            return {'valid': False, 'error': str(e)}

    def archive_article(
        self,
        article_data: Dict[str, Any],
        doc_date: Optional[date] = None
    ) -> Optional[str]:
        """個別の記事をアーカイブ"""

        if not self.supabase_client.is_available():
            self.logger.warning("Supabaseが利用できないため、アーカイブをスキップします")
            return None

        doc_date = doc_date or date.today()

        try:
            # 1. ドキュメントレコードを作成
            # datetimeオブジェクトをISO文字列に変換
            # published_at または published_jst から取得
            published_at = article_data.get('published_at') or article_data.get('published_jst', '')
            if hasattr(published_at, 'isoformat'):  # datetimeオブジェクトの場合
                published_at = published_at.isoformat()

            # 基本的なドキュメントデータ
            # 記事本文は 'content' または 'body' キーから取得
            article_content = article_data.get('content') or article_data.get('body', '')
            
            document_data = {
                'title': article_data.get('title', ''),
                'content': article_content,
                'doc_type': 'article',
                'doc_date': doc_date.isoformat(),
                'tokens': self._estimate_article_tokens(article_data),
                # トップレベルフィールドとしてcategory, region, source, urlを保存
                'url': article_data.get('url', ''),
                'source': article_data.get('source', ''),
                'category': article_data.get('category', ''),
                'region': article_data.get('region', ''),
                'metadata': {
                    'article_id': article_data.get('id'),
                    'published_at': published_at,
                    'ai_summary': article_data.get('ai_summary', ''),
                    'tags': article_data.get('tags', []),
                }
            }

            # 既存ドキュメントをチェック（タイトルで重複確認）
            try:
                existing_result = self.supabase_client.client.table('documents')\
                    .select('*')\
                    .eq('title', document_data['title'])\
                    .eq('doc_type', 'article')\
                    .execute()

                if existing_result.data:
                    existing_doc = existing_result.data[0]
                    self.logger.info(f"記事は既にアーカイブされています: {existing_doc['id']}")
                    return existing_doc['id']
            except Exception as e:
                self.logger.warning(f"重複チェックエラー: {e}")

            # 新規ドキュメント作成
            document = self.supabase_client.upsert_document(document_data)

            if not document:
                self.logger.error("ドキュメント作成に失敗しました")
                return None

            document_id = document['id']
            self.logger.info(f"記事ドキュメント作成成功: {document_id}")

            # 2. チャンク分割と埋め込み生成
            text_chunks = self.chunk_processor.create_chunks_from_text(document_data['content'])

            if not text_chunks:
                self.logger.warning("チャンク分割でコンテンツが生成されませんでした")
                return document_id

            # 3. チャンクを保存
            chunk_data_list = []
            for i, chunk in enumerate(text_chunks):
                try:
                    embedding = self.embedding_generator.generate_embedding(chunk.content)

                    chunk_data = {
                        'document_id': document_id,
                        'content': chunk.content,
                        'embedding': embedding,
                        'chunk_index': i,
                        'metadata': {
                            'start_pos': chunk.start_pos,
                            'end_pos': chunk.end_pos,
                        }
                    }

                    # 記事固有のメタデータを追加（chunk_typeがないので簡略化）
                    # if hasattr(chunk, 'chunk_type'):
                    #     if chunk.chunk_type == 'title':
                    #         chunk_data['metadata']['is_title'] = True
                    #     elif chunk.chunk_type == 'summary':
                    #         chunk_data['metadata']['is_summary'] = True

                    chunk_data_list.append(chunk_data)

                except Exception as e:
                    self.logger.error(f"チャンク処理エラー (インデックス {i}): {e}")
                    continue

            # チャンクをバッチ保存
            if chunk_data_list:
                success_count = self.supabase_client.upsert_chunks(chunk_data_list)
                self.logger.info(f"記事チャンク保存成功: {success_count}/{len(chunk_data_list)}個")

            return document_id

        except Exception as e:
            self.logger.error(f"記事アーカイブ失敗: {e}")
            return None