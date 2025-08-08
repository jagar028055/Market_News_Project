# -*- coding: utf-8 -*-

import pytest
import asyncio
import tempfile
import os
from unittest.mock import MagicMock, patch
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.base import AppConfig, DatabaseConfig, LoggingConfig, AIConfig, GoogleConfig
from src.database import Base, DatabaseManager
from src.logging_config import setup_logging


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """一時ディレクトリ作成"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_dir):
    """テスト用設定"""
    log_path = temp_dir / "test.log"
    
    # 最小限の設定でテスト用コンフィグ作成
    return AppConfig(
        google=GoogleConfig(
            drive_output_folder_id="test_folder_id",
            service_account_json='{"type": "service_account", "test": "data"}'
        ),
        ai=AIConfig(
            gemini_api_key="test_api_key"
        ),
        database=DatabaseConfig(
            url="sqlite:///:memory:",
            echo=False
        ),
        logging=LoggingConfig(
            level="DEBUG",
            file_enabled=True,
            file_path=str(log_path)
        )
    )


@pytest.fixture
def test_db(test_config):
    """インメモリテストデータベース"""
    db_manager = DatabaseManager(test_config.database)
    yield db_manager
    # テスト後のクリーンアップは自動的に行われる（インメモリのため）


@pytest.fixture
def test_db_session(test_db):
    """テスト用データベースセッション"""
    with test_db.get_session() as session:
        yield session


@pytest.fixture
def sample_articles():
    """サンプル記事データ"""
    return [
        {
            'title': 'テスト記事1: 株価上昇',
            'url': 'https://example.com/article1',
            'body': 'テスト記事の本文です。株価が上昇しています。',
            'source': 'Reuters',
            'category': 'ビジネス',
            'published_jst': datetime(2024, 1, 1, 12, 0, 0)
        },
        {
            'title': 'テスト記事2: 金利政策',
            'url': 'https://example.com/article2',
            'body': 'もう一つのテスト記事です。金利政策について解説。',
            'source': 'Bloomberg',
            'category': 'マーケット',
            'published_jst': datetime(2024, 1, 1, 13, 0, 0)
        },
        {
            'title': 'テスト記事3: 経済指標',
            'url': 'https://example.com/article3',
            'body': '経済指標が発表されました。',
            'source': 'Reuters',
            'category': '経済',
            'published_jst': datetime(2024, 1, 1, 14, 0, 0)
        }
    ]


@pytest.fixture
def sample_ai_analysis():
    """サンプルAI分析結果"""
    return [
        {
            'summary': 'テスト要約1: 株価が上昇している。市場は好調な業績発表を受けて活況となっている。',
            'keywords': ['株価', '上昇', '市場', '業績'],
            'model_version': 'test-model-v1'
        },
        {
            'summary': 'テスト要約2: 金利政策に注目が集まる。中央銀行の次回会合での決定が市場の焦点となっている。',
            'keywords': ['金利政策', '中央銀行', '市場'],
            'model_version': 'test-model-v1'
        },
        {
            'summary': 'テスト要約3: 経済指標は予想通りの結果。GDP成長率は前期比で安定した水準を維持している。',
            'keywords': ['経済指標', 'GDP', '成長率'],
            'model_version': 'test-model-v1'
        }
    ]


@pytest.fixture
def mock_webdriver():
    """MockedWebDriver"""
    with patch('selenium.webdriver.Chrome') as mock_driver:
        driver_instance = MagicMock()
        mock_driver.return_value = driver_instance
        driver_instance.page_source = """
        <html>
            <body>
                <div data-testid="StoryCard">
                    <a data-testid="TitleLink" href="/article/test123">テストニュース</a>
                    <time data-testid="DateLineText" datetime="2024-01-01T12:00:00Z">2024-01-01</time>
                </div>
            </body>
        </html>
        """
        yield driver_instance


@pytest.fixture
def mock_gemini_api():
    """Mocked Gemini API"""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        mock_response = MagicMock()
        mock_response.text = '''
        {
            "summary": "Test summary from Gemini 2.5 Flash-Lite",
            "keywords": ["test", "summary", "gemini"]
        }
        '''
        mock_model.return_value.generate_content.return_value = mock_response
        yield mock_model


@pytest.fixture
def mock_requests():
    """Mocked requests"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.content = b"<html><body>Test content</body></html>"
        mock_response.apparent_encoding = 'utf-8'
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_google_services():
    """Mocked Google Services"""
    with patch('gdocs.client.authenticate_google_services') as mock_auth:
        mock_drive = MagicMock()
        mock_docs = MagicMock()
        mock_auth.return_value = (mock_drive, mock_docs)
        yield mock_drive, mock_docs


@pytest.fixture(autouse=True)
def setup_test_logging(test_config):
    """テスト用ログ設定（全テストで自動適用）"""
    setup_logging(test_config.logging)


# 共通のテストヘルパー関数
def create_test_article(
    title: str = "テスト記事",
    url: str = "https://test.com/article",
    source: str = "Test",
    **kwargs
):
    """テスト用記事データ作成ヘルパー"""
    article_data = {
        'title': title,
        'url': url,
        'body': kwargs.get('body', 'テスト記事の本文'),
        'source': source,
        'category': kwargs.get('category', 'テスト'),
        'published_jst': kwargs.get('published_jst', datetime.now())
    }
    article_data.update(kwargs)
    return article_data


def create_test_ai_analysis(
    sentiment_label: str = "Neutral",
    sentiment_score: float = 0.5,
    **kwargs
):
    """テスト用AI分析結果作成ヘルパー"""
    analysis_data = {
        'summary': kwargs.get('summary', 'テスト要約'),
        'sentiment_label': sentiment_label,
        'sentiment_score': sentiment_score,
        'model_version': kwargs.get('model_version', 'test-model')
    }
    analysis_data.update(kwargs)
    return analysis_data