"""音声アセット管理機能のテスト"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
import yaml

from src.podcast.assets.asset_manager import AssetManager, AssetCredits, AudioAsset
from src.podcast.assets.credit_inserter import CreditInserter


class TestAssetManager:
    """AssetManagerクラスのテスト"""
    
    @pytest.fixture
    def temp_assets_dir(self):
        """テスト用一時ディレクトリ"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_credits_data(self):
        """サンプルクレジットデータ"""
        return {
            'audio_assets': {
                'intro_jingle': {
                    'file_path': 'test_intro.mp3',
                    'title': 'Test Intro',
                    'author': 'Test Author',
                    'license': 'CC BY 4.0',
                    'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                    'source_url': 'https://example.com/intro',
                    'description': 'Test intro jingle'
                },
                'outro_jingle': {
                    'file_path': 'test_outro.mp3',
                    'title': 'Test Outro',
                    'author': 'Test Author',
                    'license': 'CC BY 4.0',
                    'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                    'source_url': 'https://example.com/outro',
                    'description': 'Test outro jingle'
                },
                'background_music': {
                    'file_path': 'test_bgm.mp3',
                    'title': 'Test BGM',
                    'author': 'Test Musician',
                    'license': 'CC BY 4.0',
                    'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                    'source_url': 'https://example.com/bgm',
                    'description': 'Test background music'
                },
                'segment_transition': {
                    'file_path': 'test_transition.mp3',
                    'title': 'Test Transition',
                    'author': 'Test Designer',
                    'license': 'CC BY 4.0',
                    'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                    'source_url': 'https://example.com/transition',
                    'description': 'Test transition sound'
                }
            }
        }
    
    @pytest.fixture
    def asset_manager_with_data(self, temp_assets_dir, sample_credits_data):
        """サンプルデータ付きAssetManager"""
        # クレジットファイルを作成
        credits_file = Path(temp_assets_dir) / "credits.yaml"
        with open(credits_file, 'w', encoding='utf-8') as f:
            yaml.dump(sample_credits_data, f, default_flow_style=False, allow_unicode=True)
        
        # サンプル音声ファイルを作成（空ファイル）
        for asset_type, asset_data in sample_credits_data['audio_assets'].items():
            file_path = Path(temp_assets_dir) / asset_data['file_path']
            file_path.touch()
        
        return AssetManager(temp_assets_dir)
    
    def test_init_creates_directory(self, temp_assets_dir):
        """初期化時にディレクトリが作成されることを確認"""
        non_existent_dir = os.path.join(temp_assets_dir, "new_assets")
        manager = AssetManager(non_existent_dir)
        
        assert os.path.exists(non_existent_dir)
        assert os.path.exists(manager.credits_file)
    
    def test_init_creates_sample_credits(self, temp_assets_dir):
        """初期化時にサンプルクレジットファイルが作成されることを確認"""
        manager = AssetManager(temp_assets_dir)
        
        assert manager.credits_file.exists()
        
        # サンプルデータが正しく作成されているか確認
        with open(manager.credits_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        assert 'audio_assets' in data
        assert 'intro_jingle' in data['audio_assets']
        assert 'outro_jingle' in data['audio_assets']
        assert 'background_music' in data['audio_assets']
        assert 'segment_transition' in data['audio_assets']
    
    def test_get_asset_path_existing_file(self, asset_manager_with_data):
        """存在するアセットファイルのパス取得テスト"""
        path = asset_manager_with_data.get_asset_path('intro_jingle')
        
        assert path is not None
        assert os.path.exists(path)
        assert path.endswith('test_intro.mp3')
    
    def test_get_asset_path_non_existing_file(self, asset_manager_with_data):
        """存在しないアセットファイルのパス取得テスト"""
        # ファイルを削除
        intro_path = asset_manager_with_data.get_asset_path('intro_jingle')
        os.remove(intro_path)
        
        # キャッシュをクリア
        asset_manager_with_data._credits_cache = None
        
        path = asset_manager_with_data.get_asset_path('intro_jingle')
        assert path is None
    
    def test_get_asset_path_invalid_type(self, asset_manager_with_data):
        """無効なアセットタイプの場合のテスト"""
        path = asset_manager_with_data.get_asset_path('invalid_type')
        assert path is None
    
    def test_get_all_assets(self, asset_manager_with_data):
        """全アセットパス取得テスト"""
        assets = asset_manager_with_data.get_all_assets()
        
        expected_types = ['intro_jingle', 'outro_jingle', 'background_music', 'segment_transition']
        
        assert len(assets) == len(expected_types)
        for asset_type in expected_types:
            assert asset_type in assets
            assert assets[asset_type] is not None
            assert os.path.exists(assets[asset_type])
    
    def test_get_credits_info(self, asset_manager_with_data):
        """クレジット情報取得テスト"""
        credits = asset_manager_with_data.get_credits_info()
        
        assert isinstance(credits, AssetCredits)
        assert isinstance(credits.intro_jingle, AudioAsset)
        assert isinstance(credits.outro_jingle, AudioAsset)
        assert isinstance(credits.background_music, AudioAsset)
        assert isinstance(credits.segment_transition, AudioAsset)
        
        # 具体的な値をチェック
        assert credits.intro_jingle.title == 'Test Intro'
        assert credits.intro_jingle.author == 'Test Author'
        assert credits.intro_jingle.license == 'CC BY 4.0'
    
    def test_get_credits_text(self, asset_manager_with_data):
        """クレジットテキスト取得テスト"""
        credits_text = asset_manager_with_data.get_credits_text()
        
        assert isinstance(credits_text, str)
        assert len(credits_text) > 0
        assert 'Test Intro' in credits_text
        assert 'Test Author' in credits_text
        assert 'CC BY 4.0' in credits_text
        assert 'https://creativecommons.org/licenses/by/4.0/' in credits_text
    
    def test_validate_assets_all_exist(self, asset_manager_with_data):
        """全アセット存在時の検証テスト"""
        validation = asset_manager_with_data.validate_assets()
        
        expected_types = ['intro_jingle', 'outro_jingle', 'background_music', 'segment_transition']
        
        assert len(validation) == len(expected_types)
        for asset_type in expected_types:
            assert validation[asset_type] is True
    
    def test_validate_assets_some_missing(self, asset_manager_with_data):
        """一部アセット欠損時の検証テスト"""
        # intro_jingleファイルを削除
        intro_path = asset_manager_with_data.get_asset_path('intro_jingle')
        os.remove(intro_path)
        
        # キャッシュをクリア
        asset_manager_with_data._credits_cache = None
        
        validation = asset_manager_with_data.validate_assets()
        
        assert validation['intro_jingle'] is False
        assert validation['outro_jingle'] is True
        assert validation['background_music'] is True
        assert validation['segment_transition'] is True


class TestCreditInserter:
    """CreditInserterクラスのテスト"""
    
    @pytest.fixture
    def temp_assets_dir(self):
        """テスト用一時ディレクトリ"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def credit_inserter(self, temp_assets_dir):
        """CreditInserterインスタンス"""
        asset_manager = AssetManager(temp_assets_dir)
        return CreditInserter(asset_manager)
    
    def test_insert_rss_credits(self, credit_inserter):
        """RSSクレジット挿入テスト"""
        original_description = "これはテスト用の説明文です。"
        result = credit_inserter.insert_rss_credits(original_description)
        
        assert result.startswith(original_description)
        assert "【使用音源クレジット】" in result
        assert "CC BY" in result
    
    def test_insert_line_credits(self, credit_inserter):
        """LINEクレジット挿入テスト"""
        original_message = "テスト用のLINEメッセージです。"
        result = credit_inserter.insert_line_credits(original_message)
        
        assert result.startswith(original_message)
        assert "【音源クレジット】" in result
    
    def test_get_episode_credits(self, credit_inserter):
        """エピソードクレジット取得テスト"""
        credits = credit_inserter.get_episode_credits()
        
        assert isinstance(credits, dict)
        assert 'rss_credits' in credits
        assert 'line_credits' in credits
        assert 'short_credits' in credits
        assert 'full_credits' in credits
        
        # 各クレジットタイプが文字列であることを確認
        for credit_type, credit_text in credits.items():
            assert isinstance(credit_text, str)
    
    def test_validate_license_compliance(self, credit_inserter):
        """ライセンス準拠検証テスト"""
        validation = credit_inserter.validate_license_compliance()
        
        assert isinstance(validation, dict)
        assert 'assets_exist' in validation
        assert 'cc_by_compliance' in validation
        assert 'credits_complete' in validation
        
        # デフォルトサンプルはCC-BYなので準拠しているはず
        assert validation['cc_by_compliance'] is True
        assert validation['credits_complete'] is True
    
    def test_format_credits_for_rss(self, credit_inserter):
        """RSS用クレジット形式テスト"""
        rss_credits = credit_inserter._format_credits_for_rss()
        
        assert isinstance(rss_credits, str)
        if rss_credits:  # クレジット情報がある場合
            assert "•" in rss_credits  # RSS用の箇条書き形式
            assert "CC BY" in rss_credits
    
    def test_format_credits_for_line(self, credit_inserter):
        """LINE用クレジット形式テスト"""
        line_credits = credit_inserter._format_credits_for_line()
        
        assert isinstance(line_credits, str)
        if line_credits:  # クレジット情報がある場合
            assert len(line_credits) <= 500  # LINEメッセージの適切な長さ
            assert "音源提供" in line_credits or "ライセンス" in line_credits
    
    def test_format_credits_short(self, credit_inserter):
        """短縮クレジット形式テスト"""
        short_credits = credit_inserter._format_credits_short()
        
        assert isinstance(short_credits, str)
        if short_credits:  # クレジット情報がある場合
            assert len(short_credits) <= 100  # 短縮形式なので短い
            assert "音源" in short_credits
            assert "CC BY" in short_credits


class TestIntegration:
    """統合テスト"""
    
    @pytest.fixture
    def temp_assets_dir(self):
        """テスト用一時ディレクトリ"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_end_to_end_asset_management(self, temp_assets_dir):
        """エンドツーエンドのアセット管理テスト"""
        # AssetManagerを初期化
        asset_manager = AssetManager(temp_assets_dir)
        
        # CreditInserterを初期化
        credit_inserter = CreditInserter(asset_manager)
        
        # アセット検証
        validation = asset_manager.validate_assets()
        assert isinstance(validation, dict)
        
        # クレジット情報取得
        credits_info = asset_manager.get_credits_info()
        assert credits_info is not None
        
        # クレジット挿入
        test_description = "テストエピソードの説明"
        rss_result = credit_inserter.insert_rss_credits(test_description)
        line_result = credit_inserter.insert_line_credits(test_description)
        
        assert test_description in rss_result
        assert test_description in line_result
        assert len(rss_result) > len(test_description)
        assert len(line_result) > len(test_description)
        
        # ライセンス準拠確認
        compliance = credit_inserter.validate_license_compliance()
        assert compliance['credits_complete'] is True
    
    def test_missing_assets_handling(self, temp_assets_dir):
        """アセット欠損時の処理テスト"""
        # AssetManagerを初期化（サンプルファイルは作成されない）
        asset_manager = AssetManager(temp_assets_dir)
        credit_inserter = CreditInserter(asset_manager)
        
        # アセット検証（ファイルが存在しないので全てFalse）
        validation = asset_manager.validate_assets()
        assert all(result is False for result in validation.values())
        
        # クレジット挿入は正常動作するが、クレジット情報は空になる
        test_description = "テストエピソードの説明"
        rss_result = credit_inserter.insert_rss_credits(test_description)
        line_result = credit_inserter.insert_line_credits(test_description)
        
        # 元の説明文は保持される
        assert test_description in rss_result
        assert test_description in line_result