"""
埋め込み生成器

sentence-transformersを使用してテキストの埋め込みベクターを生成します。
"""

import logging
from typing import List, Optional, Dict, Any
import numpy as np
from src.config.app_config import SupabaseConfig, get_config

# heavy importは遅延させるためここでは読み込まない
SentenceTransformer = None


class EmbeddingGenerator:
    """埋め込み生成クラス"""

    def __init__(self, config: Optional[SupabaseConfig] = None):
        self.config = config or get_config().supabase
        self.logger = logging.getLogger("embedding_generator")
        self._model: Optional[SentenceTransformer] = None

        if not self.config.enabled:
            self.logger.info("Supabase機能が無効のため、埋め込み生成器を初期化しません")
            return

    @property
    def model(self) -> Optional[SentenceTransformer]:
        """sentence-transformersモデルを遅延読み込み"""
        if not self.config.enabled:
            return None

        if self._model is None:
            try:
                # 遅延インポート（初回のみ）
                global SentenceTransformer
                if SentenceTransformer is None:
                    from sentence_transformers import SentenceTransformer as ST
                    SentenceTransformer = ST

                self.logger.info(f"埋め込みモデル読み込み中: {self.config.embedding_model}")
                self._model = SentenceTransformer(self.config.embedding_model)
                self.logger.info(f"埋め込みモデル読み込み成功")
            except Exception as e:
                self.logger.error(f"埋め込みモデル読み込み失敗: {e}")
                return None

        return self._model

    def is_available(self) -> bool:
        """埋め込み生成器が利用可能かチェック"""
        return self.config.enabled and self.model is not None

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """単一テキストの埋め込み生成"""
        if not self.is_available():
            return None

        if not text or not text.strip():
            self.logger.warning("空のテキストが入力されました")
            return None

        try:
            # テキストを正規化
            normalized_text = self._normalize_text(text)
            
            # 埋め込み生成
            embedding = self.model.encode(normalized_text, convert_to_numpy=True)
            
            # 次元数チェック
            if len(embedding) != self.config.embedding_dimension:
                self.logger.warning(
                    f"埋め込み次元数が設定と異なります: {len(embedding)} != {self.config.embedding_dimension}"
                )
            
            return embedding.tolist()

        except Exception as e:
            self.logger.error(f"埋め込み生成失敗: {e}")
            return None

    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """複数テキストの埋め込み一括生成"""
        if not self.is_available():
            return [None] * len(texts)

        if not texts:
            return []

        try:
            # テキストを正規化
            normalized_texts = [self._normalize_text(text) for text in texts if text and text.strip()]
            
            if not normalized_texts:
                self.logger.warning("有効なテキストがありません")
                return [None] * len(texts)

            # 埋め込み一括生成
            embeddings = self.model.encode(normalized_texts, convert_to_numpy=True)
            
            # リスト形式に変換
            result = []
            valid_idx = 0
            
            for text in texts:
                if text and text.strip():
                    if valid_idx < len(embeddings):
                        result.append(embeddings[valid_idx].tolist())
                        valid_idx += 1
                    else:
                        result.append(None)
                else:
                    result.append(None)

            self.logger.info(f"埋め込み一括生成成功: {len(normalized_texts)}件")
            return result

        except Exception as e:
            self.logger.error(f"埋め込み一括生成失敗: {e}")
            return [None] * len(texts)

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """コサイン類似度計算"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # コサイン類似度計算
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)

        except Exception as e:
            self.logger.error(f"類似度計算失敗: {e}")
            return 0.0

    def find_most_similar(
        self, 
        query_embedding: List[float], 
        candidate_embeddings: List[List[float]], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """最も類似した埋め込みを検索"""
        if not candidate_embeddings:
            return []

        try:
            similarities = []
            
            for i, candidate in enumerate(candidate_embeddings):
                similarity = self.calculate_similarity(query_embedding, candidate)
                similarities.append({
                    'index': i,
                    'similarity': similarity
                })
            
            # 類似度順にソート
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 上位top_k件を返す
            return similarities[:top_k]

        except Exception as e:
            self.logger.error(f"類似検索失敗: {e}")
            return []

    def _normalize_text(self, text: str) -> str:
        """テキスト正規化"""
        if not text:
            return ""
        
        # 基本的な正規化
        normalized = text.strip()
        
        # 改行を空白に変換
        normalized = normalized.replace('\n', ' ').replace('\r', ' ')
        
        # 複数の空白を単一空白に変換
        import re
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized

    def validate_embedding(self, embedding: List[float]) -> bool:
        """埋め込みの妥当性チェック"""
        if not embedding:
            return False
            
        if len(embedding) != self.config.embedding_dimension:
            self.logger.warning(f"埋め込み次元数エラー: {len(embedding)} != {self.config.embedding_dimension}")
            return False
            
        # NaN, Inf チェック
        if any(np.isnan(val) or np.isinf(val) for val in embedding):
            self.logger.warning("埋め込みに不正な値が含まれています")
            return False
            
        return True

    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報取得"""
        if not self.is_available():
            return {}
            
        try:
            return {
                'model_name': self.config.embedding_model,
                'dimension': self.config.embedding_dimension,
                'max_seq_length': getattr(self.model, 'max_seq_length', 'unknown'),
                'device': str(self.model.device) if hasattr(self.model, 'device') else 'unknown'
            }
        except Exception as e:
            self.logger.error(f"モデル情報取得失敗: {e}")
            return {}


# シングルトンインスタンス
_embedding_generator: Optional[EmbeddingGenerator] = None


def get_embedding_generator() -> EmbeddingGenerator:
    """埋め込み生成器を取得（シングルトン）"""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator
