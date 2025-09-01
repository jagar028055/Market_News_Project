# -*- coding: utf-8 -*-

"""
Manual Audio Processor
NotebookLM手動音声配信処理システム
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re
from dataclasses import dataclass

from src.podcast.publisher.github_pages_publisher import GitHubPagesPublisher
from src.config.app_config import AppConfig


@dataclass
class ManualAudioFile:
    """手動アップロード音声ファイル情報"""
    file_path: Path
    original_name: str
    date_str: str
    parsed_date: datetime
    file_size_mb: float
    metadata_tags: List[str]
    audio_type: str  # 'morning', 'evening', 'special', 'weekly', 'standard'


class ManualAudioProcessor:
    """NotebookLM手動音声処理クラス"""
    
    def __init__(self, config: AppConfig, logger: logging.Logger):
        """
        初期化
        
        Args:
            config: アプリケーション設定
            logger: ロガー
        """
        self.config = config
        self.logger = logger
        
        # ディレクトリ設定
        self.upload_dir = Path("manual_audio/upload")
        self.processed_dir = Path("manual_audio/processed")
        self.public_dir = Path("podcast")
        
        # ディレクトリ作成
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.public_dir.mkdir(parents=True, exist_ok=True)
        
        # GitHub Pages配信システム初期化
        self.publisher = GitHubPagesPublisher(config, logger)
        
        # サポートする音声形式
        self.supported_formats = {'.mp3', '.wav', '.m4a', '.aac'}
        
        self.logger.info(f"ManualAudioProcessor初期化完了 - アップロード: {self.upload_dir}")
    
    def process_uploaded_files(self) -> List[Dict[str, Any]]:
        """
        アップロードされた音声ファイルを処理
        
        Returns:
            List[Dict[str, Any]]: 処理結果リスト
        """
        self.logger.info("手動アップロード音声ファイルの処理開始")
        
        # アップロードディレクトリをスキャン
        uploaded_files = self._scan_upload_directory()
        
        if not uploaded_files:
            self.logger.info("処理対象の音声ファイルが見つかりません")
            return []
        
        self.logger.info(f"{len(uploaded_files)}件の音声ファイルを発見")
        
        processing_results = []
        
        for audio_file in uploaded_files:
            try:
                result = self._process_single_file(audio_file)
                processing_results.append(result)
                
                # 処理済みディレクトリに移動
                self._move_to_processed(audio_file)
                
            except Exception as e:
                self.logger.error(f"ファイル処理エラー {audio_file.file_path.name}: {e}", exc_info=True)
                processing_results.append({
                    'file_name': audio_file.file_path.name,
                    'success': False,
                    'error': str(e),
                    'processed_at': datetime.now().isoformat()
                })
        
        self.logger.info(f"手動音声処理完了 - 成功: {sum(1 for r in processing_results if r.get('success'))}/{len(processing_results)}")
        return processing_results
    
    def _scan_upload_directory(self) -> List[ManualAudioFile]:
        """
        アップロードディレクトリをスキャンして音声ファイルを検出
        
        Returns:
            List[ManualAudioFile]: 検出された音声ファイル情報
        """
        audio_files = []
        
        for file_path in self.upload_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                try:
                    audio_file = self._parse_audio_file(file_path)
                    audio_files.append(audio_file)
                    self.logger.debug(f"音声ファイル検出: {audio_file.original_name}")
                except Exception as e:
                    self.logger.warning(f"ファイル解析失敗 {file_path.name}: {e}")
        
        # 日付順でソート（古い順）
        audio_files.sort(key=lambda x: x.parsed_date)
        
        return audio_files
    
    def _parse_audio_file(self, file_path: Path) -> ManualAudioFile:
        """
        音声ファイル情報を解析
        
        Args:
            file_path: ファイルパス
            
        Returns:
            ManualAudioFile: 解析結果
        """
        original_name = file_path.name
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        # 日付とタグを抽出
        date_str, parsed_date, metadata_tags, audio_type = self._extract_file_metadata(original_name, file_path)
        
        return ManualAudioFile(
            file_path=file_path,
            original_name=original_name,
            date_str=date_str,
            parsed_date=parsed_date,
            file_size_mb=file_size_mb,
            metadata_tags=metadata_tags,
            audio_type=audio_type
        )
    
    def _extract_file_metadata(self, filename: str, file_path: Path) -> Tuple[str, datetime, List[str], str]:
        """
        ファイル名からメタデータを抽出
        
        Args:
            filename: ファイル名
            file_path: ファイルパス
            
        Returns:
            Tuple[str, datetime, List[str], str]: 日付文字列, 日付オブジェクト, タグリスト, 音声タイプ
        """
        # 日付パターンマッチング（YYYYMMDD）
        date_pattern = r'(\d{4})(\d{2})(\d{2})'
        date_match = re.search(date_pattern, filename)
        
        if date_match:
            year, month, day = date_match.groups()
            date_str = f"{year}{month}{day}"
            try:
                parsed_date = datetime(int(year), int(month), int(day))
            except ValueError:
                # 無効な日付の場合はファイル作成日時を使用
                parsed_date = datetime.fromtimestamp(file_path.stat().st_mtime)
                date_str = parsed_date.strftime("%Y%m%d")
        else:
            # 日付が抽出できない場合はファイル作成日時を使用
            parsed_date = datetime.fromtimestamp(file_path.stat().st_mtime)
            date_str = parsed_date.strftime("%Y%m%d")
        
        # メタデータタグ抽出
        metadata_tags = []
        audio_type = 'standard'
        
        filename_lower = filename.lower()
        
        # タイプ別タグ検出
        if 'morning' in filename_lower:
            metadata_tags.append('morning')
            audio_type = 'morning'
        elif 'evening' in filename_lower:
            metadata_tags.append('evening')
            audio_type = 'evening'
        elif 'special' in filename_lower:
            metadata_tags.append('special')
            audio_type = 'special'
        elif 'weekly' in filename_lower:
            metadata_tags.append('weekly')
            audio_type = 'weekly'
        
        # その他のタグ検出
        if 'notebooklm' in filename_lower:
            metadata_tags.append('notebooklm')
        if 'ai' in filename_lower:
            metadata_tags.append('ai')
        
        return date_str, parsed_date, metadata_tags, audio_type
    
    def _process_single_file(self, audio_file: ManualAudioFile) -> Dict[str, Any]:
        """
        単一音声ファイルを処理
        
        Args:
            audio_file: 音声ファイル情報
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        self.logger.info(f"音声ファイル処理開始: {audio_file.original_name}")
        
        # エピソード情報を構築
        episode_info = self._create_episode_info(audio_file)
        
        # 公開用ファイル名生成
        public_filename = self._generate_public_filename(audio_file)
        public_path = self.public_dir / public_filename
        
        # ファイルをコピー
        shutil.copy2(audio_file.file_path, public_path)
        self.logger.info(f"ファイルコピー完了: {public_filename}")
        
        # GitHub Pages配信
        public_url = self.publisher.publish_podcast_episode(
            str(public_path), episode_info
        )
        
        if not public_url:
            raise Exception("GitHub Pages配信に失敗しました")
        
        # 処理結果
        result = {
            'file_name': audio_file.original_name,
            'success': True,
            'public_filename': public_filename,
            'public_url': public_url,
            'date': audio_file.date_str,
            'audio_type': audio_file.audio_type,
            'file_size_mb': audio_file.file_size_mb,
            'metadata_tags': audio_file.metadata_tags,
            'episode_info': episode_info,
            'processed_at': datetime.now().isoformat()
        }
        
        self.logger.info(f"音声ファイル処理完了: {public_url}")
        return result
    
    def _create_episode_info(self, audio_file: ManualAudioFile) -> Dict[str, Any]:
        """
        エピソード情報を作成
        
        Args:
            audio_file: 音声ファイル情報
            
        Returns:
            Dict[str, Any]: エピソード情報
        """
        # タイトル生成
        date_formatted = audio_file.parsed_date.strftime("%Y年%m月%d日")
        
        title_suffix = {
            'morning': '朝刊',
            'evening': '夕刊', 
            'special': '特別版',
            'weekly': '週間まとめ'
        }.get(audio_file.audio_type, '')
        
        title = f"マーケットニュース{title_suffix} - {date_formatted}"
        if 'notebooklm' in audio_file.metadata_tags:
            title += " (NotebookLM版)"
        
        # 説明文生成
        description_parts = [
            f"{date_formatted}の市場動向をお届けします。"
        ]
        
        if audio_file.audio_type != 'standard':
            type_descriptions = {
                'morning': '朝の市場開始前に重要なニュースを厳選してお届け。',
                'evening': '市場終了後の振り返りと明日への展望。',
                'special': '重要な市場イベントやニュースの特別解説。',
                'weekly': '1週間の市場動向を総括した週間レポート。'
            }
            description_parts.append(type_descriptions.get(audio_file.audio_type, ''))
        
        if 'notebooklm' in audio_file.metadata_tags:
            description_parts.append('Google NotebookLMで生成された高品質なAI音声でお届けします。')
        
        return {
            'title': title,
            'description': ' '.join(description_parts),
            'published_at': audio_file.parsed_date,
            'duration': None,  # 実際の再生時間は後で設定可能
            'file_size': int(audio_file.file_size_mb * 1024 * 1024),
            'keywords': ['market', 'news', 'finance', 'ai', 'notebooklm'] + audio_file.metadata_tags,
            'source': 'notebooklm_manual',
            'audio_type': audio_file.audio_type
        }
    
    def _generate_public_filename(self, audio_file: ManualAudioFile) -> str:
        """
        公開用ファイル名を生成
        
        Args:
            audio_file: 音声ファイル情報
            
        Returns:
            str: 公開用ファイル名
        """
        base_name = f"market_news_{audio_file.date_str}"
        
        # タイプ別サフィックス
        if audio_file.audio_type != 'standard':
            base_name += f"_{audio_file.audio_type}"
        
        # NotebookLM識別子
        if 'notebooklm' in audio_file.metadata_tags:
            base_name += "_notebooklm"
        
        # 拡張子
        original_ext = audio_file.file_path.suffix
        base_name += original_ext
        
        return base_name
    
    def _move_to_processed(self, audio_file: ManualAudioFile) -> None:
        """
        処理済みディレクトリにファイルを移動
        
        Args:
            audio_file: 音声ファイル情報
        """
        try:
            # タイムスタンプ付きファイル名で保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            processed_filename = f"{audio_file.date_str}_{timestamp}_{audio_file.original_name}"
            processed_path = self.processed_dir / processed_filename
            
            shutil.move(str(audio_file.file_path), str(processed_path))
            self.logger.info(f"ファイル移動完了: {audio_file.original_name} → processed/{processed_filename}")
            
        except Exception as e:
            self.logger.warning(f"ファイル移動エラー: {e}")
            # 移動に失敗してもエラーにはしない
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        処理統計を取得
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            # アップロード待ちファイル数
            upload_files = list(self.upload_dir.glob('*'))
            upload_count = len([f for f in upload_files if f.is_file()])
            
            # 処理済みファイル数
            processed_files = list(self.processed_dir.glob('*'))
            processed_count = len([f for f in processed_files if f.is_file()])
            
            # 公開済みファイル数
            public_files = list(self.public_dir.glob('market_news_*notebooklm*'))
            public_count = len(public_files)
            
            return {
                'upload_pending': upload_count,
                'processed_total': processed_count,
                'published_notebooklm': public_count,
                'last_check': datetime.now().isoformat(),
                'upload_directory': str(self.upload_dir),
                'processed_directory': str(self.processed_dir),
                'public_directory': str(self.public_dir)
            }
            
        except Exception as e:
            self.logger.error(f"統計取得エラー: {e}")
            return {
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    def cleanup_old_processed_files(self, days_to_keep: int = 30) -> int:
        """
        古い処理済みファイルをクリーンアップ
        
        Args:
            days_to_keep: 保持する日数
            
        Returns:
            int: 削除したファイル数
        """
        try:
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            deleted_count = 0
            
            for file_path in self.processed_dir.glob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
                    self.logger.debug(f"古い処理済みファイル削除: {file_path.name}")
            
            if deleted_count > 0:
                self.logger.info(f"古い処理済みファイルクリーンアップ完了: {deleted_count}件削除")
            
            return deleted_count
            
        except Exception as e:
            self.logger.warning(f"処理済みファイルクリーンアップエラー: {e}")
            return 0


def main():
    """テスト実行用メイン関数"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # テスト用の設定（実際の設定は別途読み込み）
    from src.config.app_config import AppConfig
    config = AppConfig()
    
    processor = ManualAudioProcessor(config, logger)
    
    # 統計情報表示
    stats = processor.get_processing_stats()
    logger.info(f"処理統計: {stats}")
    
    # アップロードファイル処理
    results = processor.process_uploaded_files()
    logger.info(f"処理結果: {len(results)}件")
    
    for result in results:
        if result.get('success'):
            logger.info(f"✅ {result['file_name']} → {result['public_url']}")
        else:
            logger.error(f"❌ {result['file_name']}: {result.get('error')}")


if __name__ == "__main__":
    main()