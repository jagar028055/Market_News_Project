#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import pytz
from pathlib import Path

from gdocs.client import authenticate_google_services
from src.config.app_config import get_config


class GoogleDocsManualCurator:
    """Google Docs手動キュレーション機能"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self.jst = pytz.timezone('Asia/Tokyo')
        
        # Google Docs認証サービス（失敗してもワークフローを継続）
        self.drive_service = None
        self.docs_service = None
        try:
            services = authenticate_google_services()
            self.drive_service = services.get('drive')
            self.docs_service = services.get('docs')
            self.logger.info("Google Docs認証完了")
        except Exception as e:
            self.logger.warning(f"Google Docs認証失敗（手動キュレーション機能は無効）: {e}")
            # エラーを吸収してワークフローを継続
    
    def is_available(self) -> bool:
        """手動キュレーション機能が利用可能かチェック"""
        return (
            self.drive_service is not None and 
            self.docs_service is not None and
            self.config.social.generation_mode in ["manual", "hybrid"]
        )
    
    def check_for_manual_content(self, date: datetime) -> Optional[Dict[str, Any]]:
        """指定日付の手動キュレーション済みコンテンツを検索"""
        if not self.is_available():
            return None
        
        try:
            date_str = date.strftime('%Y-%m-%d')
            
            # Google Drive内でキュレーション済みドキュメントを検索
            query = (
                f"name contains 'MarketNews_Curated_{date_str}' and "
                f"mimeType='application/vnd.google-apps.document' and "
                f"trashed=false"
            )
            
            if hasattr(self.config.google, 'drive_output_folder_id') and self.config.google.drive_output_folder_id:
                query += f" and '{self.config.google.drive_output_folder_id}' in parents"
            
            results = self.drive_service.files().list(
                q=query,
                orderBy='modifiedTime desc',
                pageSize=5
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                self.logger.info(f"手動キュレーション済みドキュメントが見つかりません: {date_str}")
                return None
            
            # 最新のドキュメントを取得
            latest_doc = files[0]
            doc_id = latest_doc['id']
            
            self.logger.info(f"手動キュレーション済みドキュメントを発見: {latest_doc['name']}")
            
            # ドキュメント内容を取得
            content = self._extract_document_content(doc_id)
            
            if content:
                return {
                    'document_id': doc_id,
                    'document_name': latest_doc['name'],
                    'modified_time': latest_doc.get('modifiedTime'),
                    'content': content
                }
            
        except Exception as e:
            self.logger.error(f"手動キュレーション済みコンテンツの検索中にエラー: {e}")
        
        return None
    
    def _extract_document_content(self, doc_id: str) -> Optional[Dict[str, str]]:
        """Google Docsから構造化されたコンテンツを抽出"""
        try:
            # ドキュメントを取得
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            
            # ドキュメントの内容を解析
            content = doc.get('body', {}).get('content', [])
            full_text = ""
            
            for element in content:
                if 'paragraph' in element:
                    paragraph = element['paragraph']
                    if 'elements' in paragraph:
                        for elem in paragraph['elements']:
                            if 'textRun' in elem:
                                full_text += elem['textRun'].get('content', '')
            
            # 構造化されたコンテンツを抽出
            parsed_content = self._parse_structured_content(full_text)
            
            if parsed_content:
                self.logger.info("Google Docsコンテンツの解析完了")
                return parsed_content
            
        except Exception as e:
            self.logger.error(f"Google Docsコンテンツの抽出中にエラー: {e}")
        
        return None
    
    def _parse_structured_content(self, text: str) -> Optional[Dict[str, str]]:
        """テキストから構造化されたコンテンツを解析"""
        try:
            lines = text.strip().split('\n')
            sections = {}
            current_section = None
            current_content = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # セクションヘッダーを検出（例: "## SNSコンテンツ"）
                if line.startswith('##') or line.startswith('#'):
                    if current_section:
                        sections[current_section] = '\n'.join(current_content).strip()
                    
                    current_section = line.replace('#', '').strip().lower()
                    current_content = []
                elif current_section:
                    current_content.append(line)
            
            # 最後のセクションを追加
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # 標準的なセクション名にマッピング
            mapped_content = {}
            
            if 'snsコンテンツ' in sections or 'sns' in sections:
                mapped_content['sns_content'] = sections.get('snsコンテンツ', sections.get('sns', ''))
            
            if 'note記事' in sections or 'note' in sections:
                mapped_content['note_article'] = sections.get('note記事', sections.get('note', ''))
            
            if 'トピック' in sections or 'topics' in sections:
                mapped_content['topics'] = sections.get('トピック', sections.get('topics', ''))
            
            return mapped_content if mapped_content else None
            
        except Exception as e:
            self.logger.error(f"構造化コンテンツの解析中にエラー: {e}")
            return None
    
    def create_curation_template(self, articles: List[Dict[str, Any]], date: datetime) -> Optional[str]:
        """手動キュレーション用のテンプレートドキュメントを作成"""
        if not self.is_available():
            return None
        
        try:
            date_str = date.strftime('%Y-%m-%d')
            doc_title = f"MarketNews_Curated_{date_str}"
            
            # テンプレート内容を生成
            template_content = self._generate_template_content(articles, date)
            
            # 新しいドキュメントを作成
            doc_body = {
                'title': doc_title
            }
            
            doc = self.docs_service.documents().create(body=doc_body).execute()
            doc_id = doc.get('documentId')
            
            # テンプレート内容を挿入
            requests = [{
                'insertText': {
                    'location': {'index': 1},
                    'text': template_content
                }
            }]
            
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            # フォルダに移動（設定されている場合）
            if hasattr(self.config.google, 'drive_output_folder_id') and self.config.google.drive_output_folder_id:
                self.drive_service.files().update(
                    fileId=doc_id,
                    addParents=self.config.google.drive_output_folder_id,
                    removeParents='root'
                ).execute()
            
            self.logger.info(f"キュレーション用テンプレートドキュメント作成完了: {doc_title}")
            
            # ドキュメントのURLを返す
            return f"https://docs.google.com/document/d/{doc_id}/edit"
            
        except Exception as e:
            self.logger.error(f"テンプレートドキュメント作成中にエラー: {e}")
            return None
    
    def _generate_template_content(self, articles: List[Dict[str, Any]], date: datetime) -> str:
        """キュレーション用テンプレートコンテンツを生成"""
        date_str = date.strftime('%Y年%m月%d日')
        
        content = f"""# Market News キュレーション - {date_str}

このドキュメントを編集して、SNS投稿とnote記事をカスタマイズしてください。

## SNSコンテンツ

以下のSNS投稿用テキストを編集してください（140字以内推奨）：

[ここにSNS投稿用テキストを記述]

## note記事

以下のnote記事内容を編集してください：

### タイトル
{date_str} - 今日のマーケットハイライト

### 記事本文

[ここにnote記事の本文を記述]

## 参考データ

### 収集された記事（上位10件）
"""
        
        # 記事データを追加
        for i, article in enumerate(articles[:10], 1):
            content += f"""
{i}. **{article.get('title', 'タイトル不明')}**
   - 要約: {article.get('summary', 'N/A')}
   - ソース: {article.get('source', 'N/A')}
   - カテゴリ: {article.get('category', 'N/A')}
   - 地域: {article.get('region', 'N/A')}
   - URL: {article.get('url', 'N/A')}
"""
        
        content += """

---
**編集指示:**
1. 「## SNSコンテンツ」セクションにSNS投稿用テキストを記述
2. 「## note記事」セクションに詳細記事を記述
3. 保存後、システムが自動的に検出・生成します

**注意:** セクションヘッダー（##）は変更しないでください。
"""
        
        return content