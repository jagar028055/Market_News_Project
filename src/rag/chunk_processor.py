"""
チャンク処理器

テキストを適切なサイズのチャンクに分割し、RAGシステム用のデータを準備します。
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from src.config.app_config import SupabaseConfig, get_config


@dataclass
class TextChunk:
    """テキストチャンク"""
    content: str
    chunk_no: int
    start_pos: int
    end_pos: int
    region: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None


class ChunkProcessor:
    """チャンク処理クラス"""

    def __init__(self, config: Optional[SupabaseConfig] = None):
        self.config = config or get_config().supabase
        self.logger = logging.getLogger("chunk_processor")

    def create_chunks_from_text(
        self, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[TextChunk]:
        """テキストからチャンクを作成"""
        if not text or not text.strip():
            self.logger.warning("空のテキストが入力されました")
            return []

        metadata = metadata or {}
        
        try:
            # テキストを正規化
            normalized_text = self._normalize_text(text)
            
            # チャンクに分割
            chunks = self._split_text_into_chunks(normalized_text)
            
            # TextChunkオブジェクトに変換
            text_chunks = []
            for i, (chunk_text, start_pos, end_pos) in enumerate(chunks):
                if chunk_text.strip():  # 空でないチャンクのみ
                    text_chunk = TextChunk(
                        content=chunk_text.strip(),
                        chunk_no=i + 1,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        region=metadata.get('region'),
                        category=metadata.get('category'),
                        source=metadata.get('source'),
                        url=metadata.get('url')
                    )
                    text_chunks.append(text_chunk)

            self.logger.info(f"チャンク作成成功: {len(text_chunks)}個")
            return text_chunks

        except Exception as e:
            self.logger.error(f"チャンク作成失敗: {e}")
            return []

    def create_chunks_from_articles(self, articles: List[Dict[str, Any]]) -> List[TextChunk]:
        """記事リストからチャンクを作成"""
        all_chunks = []
        
        for article in articles:
            # 記事のテキスト結合
            title = article.get('title', '')
            summary = article.get('summary', '')
            # 記事本文は 'content' または 'body' キーから取得
            body = article.get('content') or article.get('body', '')
            
            # タイトル + 要約 + 本文を結合
            combined_text = self._combine_article_text(title, summary, body)
            
            if not combined_text.strip():
                continue
                
            # メタデータ準備
            metadata = {
                'region': self._extract_region(article),
                'category': self._extract_category(article),
                'source': article.get('source', ''),
                'url': article.get('url', '')
            }
            
            # チャンク作成
            chunks = self.create_chunks_from_text(combined_text, metadata)
            all_chunks.extend(chunks)

        self.logger.info(f"記事からチャンク作成完了: {len(articles)}記事 → {len(all_chunks)}チャンク")
        return all_chunks

    def create_chunks_for_summary(self, summary_data: Dict[str, Any]) -> List[TextChunk]:
        """日次サマリーからチャンクを作成"""
        if not summary_data:
            return []
            
        try:
            # サマリーテキストを結合
            combined_text = self._combine_summary_text(summary_data)
            
            if not combined_text.strip():
                self.logger.warning("サマリーテキストが空です")
                return []
            
            # 地域別・カテゴリ別にチャンクを作成
            chunks = []
            
            # 全体サマリー
            if summary_data.get('global_overview'):
                global_chunks = self.create_chunks_from_text(
                    summary_data['global_overview'],
                    {
                        'region': 'global',
                        'category': 'overview',
                        'source': 'daily_summary',
                        'url': summary_data.get('url', '')
                    }
                )
                chunks.extend(global_chunks)
            
            # 地域別サマリー
            if summary_data.get('regional_summaries'):
                for region, content in summary_data['regional_summaries'].items():
                    if content and content.strip():
                        regional_chunks = self.create_chunks_from_text(
                            content,
                            {
                                'region': region,
                                'category': 'regional_summary',
                                'source': 'daily_summary',
                                'url': summary_data.get('url', '')
                            }
                        )
                        chunks.extend(regional_chunks)
            
            # クロス地域分析
            if summary_data.get('cross_regional_analysis'):
                cross_chunks = self.create_chunks_from_text(
                    summary_data['cross_regional_analysis'],
                    {
                        'region': 'cross_regional',
                        'category': 'analysis',
                        'source': 'daily_summary',
                        'url': summary_data.get('url', '')
                    }
                )
                chunks.extend(cross_chunks)
                
            # キートレンド
            if summary_data.get('key_trends'):
                trend_chunks = self.create_chunks_from_text(
                    summary_data['key_trends'],
                    {
                        'region': 'global',
                        'category': 'trends',
                        'source': 'daily_summary',
                        'url': summary_data.get('url', '')
                    }
                )
                chunks.extend(trend_chunks)

            self.logger.info(f"サマリーからチャンク作成完了: {len(chunks)}個")
            return chunks

        except Exception as e:
            self.logger.error(f"サマリーチャンク作成失敗: {e}")
            return []

    def _split_text_into_chunks(self, text: str) -> List[Tuple[str, int, int]]:
        """テキストを指定サイズのチャンクに分割"""
        if not text:
            return []

        chunks = []
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        # 文単位で分割を試行
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            # 文分割に失敗した場合は文字数ベースで分割
            return self._split_by_characters(text)
        
        current_chunk = ""
        current_start = 0
        
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            
            # チャンクに追加可能かチェック
            if len(current_chunk) + len(sentence) <= chunk_size:
                if current_chunk:
                    current_chunk += " "
                current_chunk += sentence
                i += 1
            else:
                # 現在のチャンクを保存
                if current_chunk.strip():
                    current_end = current_start + len(current_chunk)
                    chunks.append((current_chunk.strip(), current_start, current_end))
                    
                    # オーバーラップ分を計算
                    overlap_text = self._get_overlap_text(current_chunk, overlap)
                    current_start = current_end - len(overlap_text)
                    current_chunk = overlap_text
                else:
                    # 現在のチャンクが空の場合、長すぎる文を強制分割
                    if len(sentence) > chunk_size:
                        char_chunks = self._split_by_characters(sentence)
                        for char_chunk, _, _ in char_chunks:
                            chunks.append((char_chunk, current_start, current_start + len(char_chunk)))
                            current_start += len(char_chunk)
                    else:
                        current_chunk = sentence
                    i += 1
        
        # 残りのチャンクを追加
        if current_chunk.strip():
            current_end = current_start + len(current_chunk)
            chunks.append((current_chunk.strip(), current_start, current_end))

        return chunks

    def _split_by_characters(self, text: str) -> List[Tuple[str, int, int]]:
        """文字数ベースでテキスト分割"""
        chunks = []
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            chunks.append((chunk, start, end))
            start = end - overlap
            
        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """テキストを文に分割"""
        # 日本語の文区切りパターン
        sentence_endings = r'[。！？]'
        
        # 文を分割
        sentences = re.split(f'({sentence_endings})', text)
        
        # 区切り文字を前の文に結合
        result = []
        current_sentence = ""
        
        for part in sentences:
            current_sentence += part
            if re.match(sentence_endings, part):
                if current_sentence.strip():
                    result.append(current_sentence.strip())
                current_sentence = ""
        
        # 残りの文を追加
        if current_sentence.strip():
            result.append(current_sentence.strip())
            
        return result

    def _get_overlap_text(self, text: str, overlap_chars: int) -> str:
        """オーバーラップ用のテキストを取得"""
        if len(text) <= overlap_chars:
            return text
            
        # 文字数からオーバーラップテキストを取得
        overlap_text = text[-overlap_chars:]
        
        # 単語の途中で切れないように調整
        space_pos = overlap_text.find(' ')
        if space_pos > 0:
            overlap_text = overlap_text[space_pos + 1:]
            
        return overlap_text

    def _normalize_text(self, text: str) -> str:
        """テキスト正規化"""
        if not text:
            return ""
            
        # 基本的な正規化
        normalized = text.strip()
        
        # 改行の統一
        normalized = normalized.replace('\r\n', '\n').replace('\r', '\n')
        
        # 複数改行を単一改行に変換
        normalized = re.sub(r'\n+', '\n', normalized)
        
        # 複数空白を単一空白に変換
        normalized = re.sub(r'[ \t]+', ' ', normalized)
        
        return normalized

    def _combine_article_text(self, title: str, summary: str, body: str) -> str:
        """記事のテキストを結合"""
        parts = []
        
        if title and title.strip():
            parts.append(f"タイトル: {title.strip()}")
            
        if summary and summary.strip():
            parts.append(f"要約: {summary.strip()}")
            
        if body and body.strip():
            parts.append(f"本文: {body.strip()}")
            
        return "\n\n".join(parts)

    def _combine_summary_text(self, summary_data: Dict[str, Any]) -> str:
        """サマリーデータからテキストを結合"""
        parts = []
        
        # 各セクションを結合
        for key in ['global_overview', 'cross_regional_analysis', 'key_trends', 'risk_factors']:
            if key in summary_data and summary_data[key]:
                parts.append(summary_data[key])
        
        # 地域別サマリーを追加
        if 'regional_summaries' in summary_data:
            for region, content in summary_data['regional_summaries'].items():
                if content and content.strip():
                    parts.append(f"【{region}】 {content}")
        
        return "\n\n".join(parts)

    def _extract_region(self, article: Dict[str, Any]) -> Optional[str]:
        """記事から地域を抽出"""
        # カテゴリや本文から地域を推定
        category = article.get('category', '').lower()
        title = article.get('title', '').lower()
        
        # 地域マッピング
        region_mapping = {
            'アジア': ['アジア', '日本', '中国', '韓国', 'インド'],
            'アメリカ': ['アメリカ', '米国', 'アメリカ合衆国', 'カナダ'],
            'ヨーロッパ': ['ヨーロッパ', 'ドイツ', 'フランス', 'イギリス', 'イタリア']
        }
        
        for region, keywords in region_mapping.items():
            if any(keyword.lower() in title or keyword.lower() in category for keyword in keywords):
                return region
                
        return 'その他'

    def _extract_category(self, article: Dict[str, Any]) -> Optional[str]:
        """記事からカテゴリを抽出"""
        category = article.get('category', '')
        
        # カテゴリを正規化
        category_mapping = {
            'ビジネス': ['ビジネス', 'business'],
            'マーケット': ['マーケット', 'market', '市場'],
            'テクノロジー': ['テクノロジー', 'technology', '技術'],
            '経済': ['経済', 'economy', '経済政策']
        }
        
        category_lower = category.lower()
        for mapped_category, keywords in category_mapping.items():
            if any(keyword.lower() in category_lower for keyword in keywords):
                return mapped_category
                
        return category if category else '一般'

    def validate_chunks(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """チャンクの妥当性を検証"""
        valid_chunks = []
        
        for chunk in chunks:
            # 最小文字数チェック
            if len(chunk.content) < 10:
                self.logger.debug(f"チャンクが短すぎます: {len(chunk.content)}文字")
                continue
                
            # 最大文字数チェック
            if len(chunk.content) > self.config.chunk_size * 1.5:
                self.logger.warning(f"チャンクが長すぎます: {len(chunk.content)}文字")
                continue
                
            # 内容の妥当性チェック
            if not chunk.content.strip():
                continue
                
            valid_chunks.append(chunk)
        
        self.logger.info(f"チャンク検証完了: {len(chunks)}個 → {len(valid_chunks)}個")
        return valid_chunks

    def get_chunk_stats(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """チャンクの統計情報を取得"""
        if not chunks:
            return {}
            
        chunk_lengths = [len(chunk.content) for chunk in chunks]
        
        # 地域別・カテゴリ別集計
        region_counts = {}
        category_counts = {}
        
        for chunk in chunks:
            if chunk.region:
                region_counts[chunk.region] = region_counts.get(chunk.region, 0) + 1
            if chunk.category:
                category_counts[chunk.category] = category_counts.get(chunk.category, 0) + 1
        
        return {
            'total_chunks': len(chunks),
            'avg_chunk_length': sum(chunk_lengths) / len(chunk_lengths),
            'min_chunk_length': min(chunk_lengths),
            'max_chunk_length': max(chunk_lengths),
            'region_distribution': region_counts,
            'category_distribution': category_counts
        }