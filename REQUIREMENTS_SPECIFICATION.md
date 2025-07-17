# AI単独実装タスク - 詳細要件定義書

## 📋 概要

このドキュメントは、AI（Claude）が単独で実装可能なすべてのタスクについて、詳細な要件定義と技術仕様を記載します。

---

## 🏗️ 1. コード品質改善

### 1.1 型ヒント完全化

#### **要件**
- すべてのPythonファイル（`.py`）に完全な型アノテーションを追加
- Python 3.8+ の型ヒント構文を使用
- mypy静的型チェッカーでエラーなしになること

#### **技術仕様**
```python
# 対象ファイル
- main.py
- config.py
- ai_summarizer.py
- html_generator.py
- scrapers/reuters.py
- scrapers/bloomberg.py
- gdocs/client.py
- gdocs/__init__.py
- scrapers/__init__.py

# 型ヒント要件
from typing import List, Dict, Optional, Union, Callable, Tuple, Any
from datetime import datetime
from pathlib import Path

# 関数の型アノテーション例
def process_article_with_ai(
    api_key: str, 
    text: str
) -> Optional[Dict[str, Any]]:
    pass

# クラスの型アノテーション例
class ArticleData:
    title: str
    url: str
    published_jst: Optional[datetime]
    body: str
    summary: Optional[str]
    sentiment_label: Optional[str]
    sentiment_score: Optional[float]
```

#### **実装基準**
- 関数の引数・戻り値すべてに型ヒント
- クラス属性にも型アノテーション
- Union型、Optional型の適切な使用
- 複雑な型はTypeAlias使用を検討

#### **検証方法**
```bash
# mypy実行でエラーゼロ
mypy main.py config.py ai_summarizer.py html_generator.py scrapers/ gdocs/

# 型カバレッジ100%を目標
mypy --html-report mypy_report .
```

---

### 1.2 エラーハンドリング強化

#### **要件**
- 汎用的な`except Exception`を具体的な例外クラスに置き換え
- リトライ機能実装（exponential backoff）
- 構造化ログ（JSON形式）導入
- エラー状況の詳細記録

#### **技術仕様**

##### **1.2.1 具体的例外処理**
```python
# 現在（改善前）
try:
    response = requests.get(url)
except Exception as e:
    print(f"エラー: {e}")

# 改善後
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
except requests.exceptions.Timeout:
    logger.error("Request timeout", extra={"url": url, "timeout": 30})
except requests.exceptions.HTTPError as e:
    logger.error("HTTP error", extra={"url": url, "status_code": e.response.status_code})
except requests.exceptions.RequestException as e:
    logger.error("Request failed", extra={"url": url, "error": str(e)})
```

##### **1.2.2 リトライ機能**
```python
import time
import random
from functools import wraps

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple = (Exception,)
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        raise
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay:.2f}s", 
                                 extra={"function": func.__name__, "error": str(e)})
                    time.sleep(delay)
        return wrapper
    return decorator
```

##### **1.2.3 構造化ログ**
```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.setFormatter(self.JSONFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }
            if hasattr(record, 'extra_data'):
                log_entry.update(record.extra_data)
            return json.dumps(log_entry, ensure_ascii=False)
```

#### **対象ファイル・機能**
- ネットワーク通信（requests, selenium）
- ファイルI/O操作
- API呼び出し（Gemini, Google APIs）
- データ解析処理

---

### 1.3 設定管理改善（Pydantic化）

#### **要件**
- `config.py`をPydanticベースの設定クラスに変更
- 環境変数のバリデーション強化
- 設定値の型安全性確保
- デフォルト値と必須項目の明確化

#### **技術仕様**

##### **1.3.1 Pydantic設定クラス**
```python
from pydantic import BaseSettings, Field, validator
from typing import List, Optional
from pathlib import Path

class ScrapingConfig(BaseSettings):
    hours_limit: int = Field(24, ge=1, le=168, description="記事収集時間範囲（時間）")
    sentiment_analysis_enabled: bool = Field(True, description="感情分析有効化")
    
    class Config:
        env_prefix = "SCRAPING_"

class ReutersConfig(BaseSettings):
    query: str = Field(..., description="検索クエリ")
    max_pages: int = Field(5, ge=1, le=20)
    items_per_page: int = Field(20, ge=10, le=100)
    target_categories: List[str] = Field(default_factory=list)
    exclude_keywords: List[str] = Field(default_factory=list)
    
    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError('検索クエリは空にできません')
        return v.strip()

class GoogleConfig(BaseSettings):
    drive_output_folder_id: str = Field(..., description="Google Drive出力フォルダID")
    overwrite_doc_id: Optional[str] = Field(None, description="上書き更新ドキュメントID")
    service_account_json: str = Field(..., description="サービスアカウントJSON")
    
    @validator('service_account_json')
    def validate_json(cls, v):
        try:
            json.loads(v)
            return v
        except json.JSONDecodeError:
            raise ValueError('無効なJSON形式です')

class AIConfig(BaseSettings):
    gemini_api_key: str = Field(..., description="Gemini APIキー")
    model_name: str = Field("gemini-2.0-flash-lite-001", description="使用モデル")
    max_output_tokens: int = Field(1024, ge=256, le=8192)
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    
    class Config:
        env_prefix = "AI_"

class AppConfig(BaseSettings):
    scraping: ScrapingConfig = ScrapingConfig()
    reuters: ReutersConfig = ReutersConfig()
    bloomberg: BloombergConfig = BloombergConfig()
    google: GoogleConfig = GoogleConfig()
    ai: AIConfig = AIConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

##### **1.3.2 設定ファイル構造**
```
config/
├── __init__.py
├── base.py          # 基本設定クラス
├── scraping.py      # スクレイピング設定
├── ai.py           # AI関連設定
├── google.py       # Google APIs設定
└── validation.py   # カスタムバリデーター
```

---

### 1.4 関数分割・リファクタリング

#### **要件**
- 長大な関数（50行以上）を適切な単位に分割
- 単一責任原則の適用
- 関数の可読性・テスタビリティ向上
- コード重複の除去

#### **技術仕様**

##### **1.4.1 main.py リファクタリング**
```python
# 現在のmain()関数を以下に分割

class NewsAggregator:
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = StructuredLogger(__name__)
    
    async def run(self) -> None:
        """メイン実行処理"""
        await self._validate_environment()
        articles = await self._collect_articles()
        processed_articles = await self._process_articles_with_ai(articles)
        await self._generate_outputs(processed_articles)
    
    async def _validate_environment(self) -> None:
        """環境設定検証"""
        pass
    
    async def _collect_articles(self) -> List[ArticleData]:
        """記事収集"""
        pass
    
    async def _process_articles_with_ai(self, articles: List[ArticleData]) -> List[ProcessedArticle]:
        """AI処理"""
        pass
    
    async def _generate_outputs(self, articles: List[ProcessedArticle]) -> None:
        """出力生成"""
        pass
```

##### **1.4.2 スクレイパーリファクタリング**
```python
# 基底クラス作成
from abc import ABC, abstractmethod

class NewsScraper(ABC):
    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.logger = StructuredLogger(self.__class__.__name__)
    
    @abstractmethod
    async def scrape_articles(self) -> List[ArticleData]:
        """記事収集の抽象メソッド"""
        pass
    
    def _setup_webdriver(self) -> webdriver.Chrome:
        """WebDriver設定の共通化"""
        pass
    
    def _parse_article_time(self, time_str: str) -> Optional[datetime]:
        """日時解析の共通化"""
        pass

class ReutersScraper(NewsScraper):
    async def scrape_articles(self) -> List[ArticleData]:
        pass

class BloombergScraper(NewsScraper):
    async def scrape_articles(self) -> List[ArticleData]:
        pass
```

---

## 🗄️ 2. データベース機能

### 2.1 SQLiteデータベース導入

#### **要件**
- 軽量なSQLiteデータベースで記事データを永続化
- 重複記事の効率的な検出・排除
- 過去データとの比較・分析機能
- データマイグレーション機能

#### **技術仕様**

##### **2.1.1 データベーススキーマ**
```sql
-- articles テーブル
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    url_hash TEXT UNIQUE NOT NULL,  -- URL正規化後のハッシュ
    title TEXT NOT NULL,
    body TEXT,
    source TEXT NOT NULL,  -- 'Reuters', 'Bloomberg'
    category TEXT,
    published_at DATETIME,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    content_hash TEXT,  -- 本文のハッシュ（重複検出用）
    
    -- インデックス
    INDEX idx_url_hash (url_hash),
    INDEX idx_content_hash (content_hash),
    INDEX idx_published_at (published_at),
    INDEX idx_source (source)
);

-- ai_analysis テーブル
CREATE TABLE ai_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    summary TEXT,
    sentiment_label TEXT,  -- 'Positive', 'Negative', 'Neutral'
    sentiment_score REAL,
    analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    model_version TEXT,  -- 使用したAIモデル
    
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    INDEX idx_article_id (article_id),
    INDEX idx_sentiment_label (sentiment_label),
    INDEX idx_analyzed_at (analyzed_at)
);

-- scraping_sessions テーブル
CREATE TABLE scraping_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    articles_found INTEGER DEFAULT 0,
    articles_processed INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running'  -- 'running', 'completed', 'failed'
);
```

##### **2.1.2 ORMモデル（SQLAlchemy）**
```python
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Article(Base):
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    url_hash = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text)
    source = Column(String, nullable=False)
    category = Column(String)
    published_at = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    content_hash = Column(String)
    
    # リレーション
    ai_analysis = relationship("AIAnalysis", back_populates="article", cascade="all, delete-orphan")

class AIAnalysis(Base):
    __tablename__ = 'ai_analysis'
    
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False)
    summary = Column(Text)
    sentiment_label = Column(String)
    sentiment_score = Column(Float)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    model_version = Column(String)
    
    # リレーション
    article = relationship("Article", back_populates="ai_analysis")

class ScrapingSession(Base):
    __tablename__ = 'scraping_sessions'
    
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    articles_found = Column(Integer, default=0)
    articles_processed = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    status = Column(String, default='running')
```

##### **2.1.3 データベース操作クラス**
```python
class DatabaseManager:
    def __init__(self, db_path: str = "market_news.db"):
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self):
        return self.SessionLocal()
    
    def save_article(self, article_data: dict) -> Optional[Article]:
        """記事保存（重複チェック付き）"""
        with self.get_session() as session:
            # URL正規化とハッシュ生成
            normalized_url = self._normalize_url(article_data['url'])
            url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()
            
            # 重複チェック
            existing = session.query(Article).filter_by(url_hash=url_hash).first()
            if existing:
                return existing
            
            # 新規記事保存
            article = Article(
                url=article_data['url'],
                url_hash=url_hash,
                title=article_data['title'],
                body=article_data.get('body', ''),
                source=article_data['source'],
                category=article_data.get('category'),
                published_at=article_data.get('published_jst'),
                content_hash=self._generate_content_hash(article_data.get('body', ''))
            )
            session.add(article)
            session.commit()
            return article
    
    def save_ai_analysis(self, article_id: int, analysis_data: dict) -> AIAnalysis:
        """AI分析結果保存"""
        with self.get_session() as session:
            analysis = AIAnalysis(
                article_id=article_id,
                summary=analysis_data.get('summary'),
                sentiment_label=analysis_data.get('sentiment_label'),
                sentiment_score=analysis_data.get('sentiment_score'),
                model_version=analysis_data.get('model_version', 'gemini-2.0-flash-lite-001')
            )
            session.add(analysis)
            session.commit()
            return analysis
    
    def get_recent_articles(self, hours: int = 24) -> List[Article]:
        """最新記事取得"""
        with self.get_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            return session.query(Article).filter(
                Article.published_at >= cutoff_time
            ).order_by(Article.published_at.desc()).all()
    
    def detect_duplicate_articles(self) -> List[Tuple[Article, Article]]:
        """重複記事検出"""
        with self.get_session() as session:
            # 同一content_hashの記事を検出
            duplicates = session.query(Article).filter(
                Article.content_hash.in_(
                    session.query(Article.content_hash).group_by(Article.content_hash).having(func.count() > 1)
                )
            ).order_by(Article.content_hash, Article.scraped_at).all()
            
            # ペアとして返す
            result = []
            current_hash = None
            current_group = []
            
            for article in duplicates:
                if article.content_hash != current_hash:
                    if len(current_group) > 1:
                        for i in range(len(current_group) - 1):
                            result.append((current_group[0], current_group[i + 1]))
                    current_hash = article.content_hash
                    current_group = [article]
                else:
                    current_group.append(article)
            
            return result
```

---

### 2.2 記事重複排除機能

#### **要件**
- URL正規化による重複検出
- 記事本文の類似度判定
- 効率的な重複チェック
- 重複記事の統合・管理

#### **技術仕様**

##### **2.2.1 URL正規化**
```python
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class URLNormalizer:
    @staticmethod
    def normalize_url(url: str) -> str:
        """URL正規化処理"""
        parsed = urlparse(url.lower())
        
        # クエリパラメータの正規化
        query_params = parse_qs(parsed.query)
        # 不要なトラッキングパラメータを除去
        tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid'}
        filtered_params = {k: v for k, v in query_params.items() if k not in tracking_params}
        normalized_query = urlencode(sorted(filtered_params.items()), doseq=True)
        
        # フラグメント除去
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip('/'),
            parsed.params,
            normalized_query,
            ''  # フラグメント除去
        ))
        
        return normalized
    
    @staticmethod
    def extract_article_id(url: str) -> Optional[str]:
        """記事IDの抽出（サイト別対応）"""
        patterns = {
            'reuters.com': r'/article/([a-zA-Z0-9\-]+)',
            'bloomberg.co.jp': r'/news/articles/([a-zA-Z0-9]+)',
        }
        
        for domain, pattern in patterns.items():
            if domain in url:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
        return None
```

##### **2.2.2 コンテンツ類似度判定**
```python
import hashlib
from difflib import SequenceMatcher
from typing import Set

class ContentDeduplicator:
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
    
    def generate_content_hash(self, content: str) -> str:
        """コンテンツハッシュ生成"""
        # 正規化処理
        normalized = self._normalize_content(content)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def _normalize_content(self, content: str) -> str:
        """コンテンツ正規化"""
        # 空白・改行の正規化
        normalized = re.sub(r'\s+', ' ', content.strip())
        # 句読点の統一
        normalized = normalized.replace('、', ',').replace('。', '.')
        return normalized.lower()
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """テキスト類似度計算"""
        norm1 = self._normalize_content(text1)
        norm2 = self._normalize_content(text2)
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def is_duplicate(self, article1: dict, article2: dict) -> bool:
        """重複記事判定"""
        # URL正規化後の比較
        url1 = URLNormalizer.normalize_url(article1['url'])
        url2 = URLNormalizer.normalize_url(article2['url'])
        if url1 == url2:
            return True
        
        # 記事ID比較（同一サイト内）
        id1 = URLNormalizer.extract_article_id(article1['url'])
        id2 = URLNormalizer.extract_article_id(article2['url'])
        if id1 and id2 and id1 == id2:
            return True
        
        # タイトル類似度
        title_similarity = self.calculate_similarity(article1['title'], article2['title'])
        if title_similarity > 0.9:
            return True
        
        # 本文類似度（存在する場合）
        if article1.get('body') and article2.get('body'):
            content_similarity = self.calculate_similarity(article1['body'], article2['body'])
            if content_similarity > self.similarity_threshold:
                return True
        
        return False
    
    def remove_duplicates(self, articles: List[dict]) -> List[dict]:
        """重複記事除去"""
        unique_articles = []
        seen_hashes = set()
        
        for article in articles:
            # コンテンツハッシュによる高速チェック
            content_hash = self.generate_content_hash(article.get('body', article['title']))
            if content_hash in seen_hashes:
                continue
            
            # 詳細重複チェック
            is_duplicate = any(
                self.is_duplicate(article, existing)
                for existing in unique_articles
            )
            
            if not is_duplicate:
                unique_articles.append(article)
                seen_hashes.add(content_hash)
        
        return unique_articles
```

---

## 🧪 3. テスト実装

### 3.1 pytest基盤

#### **要件**
- pytest + pytest-asyncio による非同期テスト対応
- 単体テスト・統合テスト・エンドツーエンドテストの実装
- モックを使用した外部依存の分離
- 高いコードカバレッジの達成

#### **技術仕様**

##### **3.1.1 テスト構造**
```
tests/
├── __init__.py
├── conftest.py              # pytest設定・フィクスチャ
├── unit/                    # 単体テスト
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_ai_summarizer.py
│   ├── test_html_generator.py
│   ├── test_scrapers/
│   │   ├── test_reuters.py
│   │   └── test_bloomberg.py
│   └── test_gdocs/
│       └── test_client.py
├── integration/             # 統合テスト
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_scraping_flow.py
│   └── test_ai_processing.py
├── e2e/                     # エンドツーエンドテスト
│   ├── __init__.py
│   └── test_full_pipeline.py
├── fixtures/                # テストデータ
│   ├── sample_articles.json
│   ├── mock_responses/
│   └── test_config.json
└── utils/                   # テストユーティリティ
    ├── __init__.py
    ├── mock_helpers.py
    └── test_data_generators.py
```

##### **3.1.2 conftest.py**
```python
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, DatabaseManager
from src.config import AppConfig

@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_config():
    """テスト用設定"""
    return AppConfig(
        scraping=ScrapingConfig(hours_limit=1),
        ai=AIConfig(gemini_api_key="test_key"),
        google=GoogleConfig(
            drive_output_folder_id="test_folder",
            service_account_json='{"test": "data"}'
        )
    )

@pytest.fixture
def test_db():
    """インメモリテストデータベース"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    
    db = DatabaseManager(":memory:")
    yield db
    engine.dispose()

@pytest.fixture
def mock_webdriver():
    """MockedWebDriver"""
    with patch('selenium.webdriver.Chrome') as mock_driver:
        driver_instance = MagicMock()
        mock_driver.return_value = driver_instance
        driver_instance.page_source = "<html>Mock HTML</html>"
        yield driver_instance

@pytest.fixture
def mock_gemini_api():
    """Mocked Gemini API"""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        mock_response = MagicMock()
        mock_response.text = '{"summary": "Test summary", "sentiment_label": "Positive", "sentiment_score": 0.8}'
        mock_model.return_value.generate_content.return_value = mock_response
        yield mock_model

@pytest.fixture
def sample_articles():
    """サンプル記事データ"""
    return [
        {
            'title': 'テスト記事1',
            'url': 'https://example.com/article1',
            'body': 'テスト記事の本文です。',
            'source': 'Reuters',
            'category': 'ビジネス',
            'published_jst': datetime(2024, 1, 1, 12, 0, 0)
        },
        {
            'title': 'テスト記事2', 
            'url': 'https://example.com/article2',
            'body': 'もう一つのテスト記事です。',
            'source': 'Bloomberg',
            'category': 'マーケット',
            'published_jst': datetime(2024, 1, 1, 13, 0, 0)
        }
    ]
```

##### **3.1.3 単体テスト例**
```python
# tests/unit/test_ai_summarizer.py
import pytest
from unittest.mock import patch, MagicMock

from src.ai_summarizer import process_article_with_ai

@pytest.mark.asyncio
async def test_process_article_with_ai_success(mock_gemini_api):
    """AI処理成功テスト"""
    api_key = "test_key"
    text = "テスト記事本文"
    
    result = await process_article_with_ai(api_key, text)
    
    assert result is not None
    assert result['summary'] == "Test summary"
    assert result['sentiment_label'] == "Positive"
    assert result['sentiment_score'] == 0.8

@pytest.mark.asyncio
async def test_process_article_with_ai_api_error():
    """API エラーテスト"""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        mock_model.return_value.generate_content.side_effect = Exception("API Error")
        
        result = await process_article_with_ai("test_key", "text")
        assert result is None

@pytest.mark.parametrize("invalid_response", [
    "",  # 空のレスポンス
    "Invalid JSON",  # 無効なJSON
    '{"summary": ""}',  # 必須フィールド不足
])
@pytest.mark.asyncio
async def test_process_article_with_ai_invalid_response(invalid_response):
    """無効レスポンステスト"""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        mock_response = MagicMock()
        mock_response.text = invalid_response
        mock_model.return_value.generate_content.return_value = mock_response
        
        result = await process_article_with_ai("test_key", "text")
        assert result is None
```

##### **3.1.4 統合テスト例**
```python
# tests/integration/test_database.py
import pytest
from datetime import datetime

from src.database import DatabaseManager, Article, AIAnalysis

@pytest.mark.asyncio
async def test_save_and_retrieve_article(test_db):
    """記事保存・取得テスト"""
    article_data = {
        'title': 'テスト記事',
        'url': 'https://example.com/test',
        'body': 'テスト本文',
        'source': 'Reuters',
        'published_jst': datetime.now()
    }
    
    # 保存
    saved_article = test_db.save_article(article_data)
    assert saved_article.id is not None
    
    # 取得
    retrieved = test_db.get_recent_articles(hours=24)
    assert len(retrieved) == 1
    assert retrieved[0].title == 'テスト記事'

@pytest.mark.asyncio
async def test_duplicate_detection(test_db):
    """重複検出テスト"""
    # 同じURL記事を2回保存
    article_data = {
        'title': 'テスト記事',
        'url': 'https://example.com/test',
        'body': 'テスト本文',
        'source': 'Reuters'
    }
    
    first_save = test_db.save_article(article_data)
    second_save = test_db.save_article(article_data)
    
    # 同じ記事が返される（重複なし）
    assert first_save.id == second_save.id
    
    # データベース内は1件のみ
    all_articles = test_db.get_recent_articles(hours=24)
    assert len(all_articles) == 1
```

---

## 🎨 4. UI/UX改善

### 4.1 HTMLページ改善

#### **要件**
- レスポンシブデザイン対応
- ダークモード/ライトモード切り替え
- 検索・フィルタリング機能
- パフォーマンス最適化

#### **技術仕様**

##### **4.1.1 モダンHTML構造**
```html
<!DOCTYPE html>
<html lang="ja" data-theme="auto">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market News Dashboard</title>
    
    <!-- CSS Framework -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2.0.6/css/pico.min.css">
    
    <!-- Custom CSS -->
    <link rel="stylesheet" href="assets/css/custom.css">
    
    <!-- PWA対応 -->
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#1976d2">
    
    <!-- OG Tags -->
    <meta property="og:title" content="Market News Dashboard">
    <meta property="og:description" content="AIが要約した最新マーケットニュース">
    <meta property="og:type" content="website">
</head>
<body>
    <header class="container">
        <nav>
            <ul>
                <li><h1>📊 Market News</h1></li>
            </ul>
            <ul>
                <li>
                    <button id="theme-toggle" class="outline" aria-label="テーマ切り替え">
                        🌙
                    </button>
                </li>
            </ul>
        </nav>
    </header>

    <main class="container">
        <!-- フィルター・検索バー -->
        <section class="filter-section">
            <div class="grid">
                <div>
                    <input type="search" id="search-input" placeholder="記事を検索..." />
                </div>
                <div>
                    <select id="source-filter">
                        <option value="">全てのソース</option>
                        <option value="Reuters">Reuters</option>
                        <option value="Bloomberg">Bloomberg</option>
                    </select>
                </div>
                <div>
                    <select id="sentiment-filter">
                        <option value="">全ての感情</option>
                        <option value="Positive">ポジティブ</option>
                        <option value="Negative">ネガティブ</option>
                        <option value="Neutral">ニュートラル</option>
                    </select>
                </div>
            </div>
        </section>

        <!-- 統計情報 -->
        <section class="stats-section">
            <div class="grid">
                <div class="stat-card">
                    <h3>総記事数</h3>
                    <p class="stat-number" id="total-articles">0</p>
                </div>
                <div class="stat-card">
                    <h3>感情分布</h3>
                    <canvas id="sentiment-chart" width="200" height="100"></canvas>
                </div>
                <div class="stat-card">
                    <h3>最終更新</h3>
                    <p class="stat-number" id="last-updated">-</p>
                </div>
            </div>
        </section>

        <!-- 記事一覧 -->
        <section id="articles-container">
            <!-- JavaScript で動的生成 -->
        </section>

        <!-- 無限スクロール用ローダー -->
        <div id="loading" class="text-center" style="display: none;">
            <div class="spinner"></div>
        </div>
    </main>

    <footer class="container">
        <p><small>Powered by Gemini AI & Python Scrapers</small></p>
    </footer>

    <!-- JavaScript -->
    <script src="assets/js/chart.min.js"></script>
    <script src="assets/js/app.js"></script>
</body>
</html>
```

##### **4.1.2 CSS設計**
```css
/* assets/css/custom.css */

:root {
  --sentiment-positive: #22c55e;
  --sentiment-negative: #ef4444;
  --sentiment-neutral: #6b7280;
  --transition-fast: 150ms ease-in-out;
  --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* ダークモード対応 */
[data-theme="dark"] {
  --sentiment-positive: #16a34a;
  --sentiment-negative: #dc2626;
  --sentiment-neutral: #9ca3af;
}

/* レスポンシブグリッド */
.grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
}

/* 統計カード */
.stat-card {
  background: var(--pico-card-background-color);
  border-radius: var(--pico-border-radius);
  padding: 1.5rem;
  box-shadow: var(--shadow-card);
  text-align: center;
  transition: transform var(--transition-fast);
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-number {
  font-size: 2rem;
  font-weight: bold;
  margin: 0.5rem 0;
  color: var(--pico-primary);
}

/* 記事カード */
.article-card {
  background: var(--pico-card-background-color);
  border-radius: var(--pico-border-radius);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: var(--shadow-card);
  border-left: 4px solid transparent;
  transition: all var(--transition-fast);
}

.article-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.article-card.positive {
  border-left-color: var(--sentiment-positive);
}

.article-card.negative {
  border-left-color: var(--sentiment-negative);
}

.article-card.neutral {
  border-left-color: var(--sentiment-neutral);
}

/* 感情アイコン */
.sentiment-icon {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.2rem;
  margin-bottom: 0.5rem;
}

.sentiment-score {
  font-size: 0.8rem;
  opacity: 0.7;
}

/* 検索・フィルター */
.filter-section {
  background: var(--pico-card-background-color);
  border-radius: var(--pico-border-radius);
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: var(--shadow-card);
}

/* スピナー */
.spinner {
  border: 3px solid var(--pico-form-element-border-color);
  border-top: 3px solid var(--pico-primary);
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* レスポンシブ対応 */
@media (max-width: 768px) {
  .grid {
    grid-template-columns: 1fr;
  }
  
  .container {
    padding: 0 1rem;
  }
  
  .stat-card {
    padding: 1rem;
  }
  
  .article-card {
    padding: 1rem;
  }
}

/* プリント対応 */
@media print {
  .filter-section,
  #theme-toggle,
  .sentiment-icon {
    display: none;
  }
  
  .article-card {
    break-inside: avoid;
    margin-bottom: 1rem;
    box-shadow: none;
    border: 1px solid #ddd;
  }
}
```

##### **4.1.3 JavaScript機能**
```javascript
// assets/js/app.js

class MarketNewsApp {
    constructor() {
        this.articles = [];
        this.filteredArticles = [];
        this.currentPage = 1;
        this.articlesPerPage = 10;
        this.sentimentChart = null;
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        await this.loadArticles();
        this.renderStats();
        this.renderArticles();
        this.initChart();
        this.loadTheme();
    }
    
    setupEventListeners() {
        // テーマ切り替え
        document.getElementById('theme-toggle').addEventListener('click', () => {
            this.toggleTheme();
        });
        
        // 検索
        const searchInput = document.getElementById('search-input');
        searchInput.addEventListener('input', debounce(() => {
            this.filterArticles();
        }, 300));
        
        // フィルター
        document.getElementById('source-filter').addEventListener('change', () => {
            this.filterArticles();
        });
        
        document.getElementById('sentiment-filter').addEventListener('change', () => {
            this.filterArticles();
        });
        
        // 無限スクロール
        window.addEventListener('scroll', () => {
            if (this.isNearBottom()) {
                this.loadMoreArticles();
            }
        });
    }
    
    async loadArticles() {
        try {
            // 実際の実装では、APIエンドポイントから取得
            const response = await fetch('/api/articles');
            this.articles = await response.json();
            this.filteredArticles = [...this.articles];
        } catch (error) {
            console.error('記事の読み込みに失敗:', error);
            // フォールバック: 埋め込みデータを使用
            this.articles = window.articlesData || [];
            this.filteredArticles = [...this.articles];
        }
    }
    
    filterArticles() {
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        const sourceFilter = document.getElementById('source-filter').value;
        const sentimentFilter = document.getElementById('sentiment-filter').value;
        
        this.filteredArticles = this.articles.filter(article => {
            const matchesSearch = !searchTerm || 
                article.title.toLowerCase().includes(searchTerm) ||
                article.summary.toLowerCase().includes(searchTerm);
            
            const matchesSource = !sourceFilter || article.source === sourceFilter;
            const matchesSentiment = !sentimentFilter || article.sentiment_label === sentimentFilter;
            
            return matchesSearch && matchesSource && matchesSentiment;
        });
        
        this.currentPage = 1;
        this.renderArticles();
        this.renderStats();
    }
    
    renderArticles() {
        const container = document.getElementById('articles-container');
        const startIndex = 0;
        const endIndex = this.currentPage * this.articlesPerPage;
        const articlesToShow = this.filteredArticles.slice(startIndex, endIndex);
        
        if (this.currentPage === 1) {
            container.innerHTML = '';
        }
        
        articlesToShow.forEach((article, index) => {
            if (index >= (this.currentPage - 1) * this.articlesPerPage) {
                container.appendChild(this.createArticleElement(article));
            }
        });
    }
    
    createArticleElement(article) {
        const element = document.createElement('article');
        element.className = `article-card ${article.sentiment_label?.toLowerCase() || 'neutral'}`;
        
        const sentimentIcon = this.getSentimentIcon(article.sentiment_label);
        const publishedDate = new Date(article.published_jst).toLocaleDateString('ja-JP');
        
        element.innerHTML = `
            <div class="sentiment-icon">
                ${sentimentIcon}
                <span class="sentiment-score">${article.sentiment_score?.toFixed(2) || 'N/A'}</span>
            </div>
            <h3><a href="${article.url}" target="_blank" rel="noopener">${article.title}</a></h3>
            <small><strong>[${article.source}]</strong> ${publishedDate}</small>
            <p>${article.summary || 'サマリーがありません'}</p>
        `;
        
        return element;
    }
    
    getSentimentIcon(sentiment) {
        const icons = {
            'Positive': '😊',
            'Negative': '😠', 
            'Neutral': '😐'
        };
        return icons[sentiment] || '🤔';
    }
    
    renderStats() {
        document.getElementById('total-articles').textContent = this.filteredArticles.length;
        
        if (this.articles.length > 0) {
            const lastUpdated = new Date(Math.max(...this.articles.map(a => new Date(a.published_jst))));
            document.getElementById('last-updated').textContent = lastUpdated.toLocaleString('ja-JP');
        }
        
        this.updateChart();
    }
    
    initChart() {
        const ctx = document.getElementById('sentiment-chart').getContext('2d');
        this.sentimentChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['ポジティブ', 'ネガティブ', 'ニュートラル'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        'var(--sentiment-positive)',
                        'var(--sentiment-negative)',
                        'var(--sentiment-neutral)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            font: { size: 10 }
                        }
                    }
                }
            }
        });
    }
    
    updateChart() {
        const sentimentCounts = {
            'Positive': 0,
            'Negative': 0,
            'Neutral': 0
        };
        
        this.filteredArticles.forEach(article => {
            const sentiment = article.sentiment_label || 'Neutral';
            sentimentCounts[sentiment]++;
        });
        
        this.sentimentChart.data.datasets[0].data = [
            sentimentCounts.Positive,
            sentimentCounts.Negative,
            sentimentCounts.Neutral
        ];
        this.sentimentChart.update();
    }
    
    toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // アイコン更新
        const button = document.getElementById('theme-toggle');
        button.textContent = newTheme === 'dark' ? '☀️' : '🌙';
    }
    
    loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 'auto';
        document.documentElement.setAttribute('data-theme', savedTheme);
        
        const button = document.getElementById('theme-toggle');
        button.textContent = savedTheme === 'dark' ? '☀️' : '🌙';
    }
    
    isNearBottom() {
        return window.innerHeight + window.scrollY >= document.body.offsetHeight - 1000;
    }
    
    loadMoreArticles() {
        if (this.currentPage * this.articlesPerPage < this.filteredArticles.length) {
            this.currentPage++;
            this.renderArticles();
        }
    }
}

// ユーティリティ関数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// アプリ初期化
document.addEventListener('DOMContentLoaded', () => {
    new MarketNewsApp();
});
```

---

## ⚡ 5. パフォーマンス最適化

### 5.1 非同期処理導入

#### **要件**
- ThreadPoolExecutorからasyncio/aiohttpへの移行
- 並行スクレイピングの効率化
- メモリ使用量の最適化
- エラー時の影響範囲最小化

#### **技術仕様**

##### **5.1.1 非同期スクレイパー基底クラス**
```python
import asyncio
import aiohttp
from abc import ABC, abstractmethod
from typing import List, Optional, AsyncIterator
import logging

class AsyncNewsScraper(ABC):
    def __init__(self, config: ScrapingConfig, session: aiohttp.ClientSession):
        self.config = config
        self.session = session
        self.logger = logging.getLogger(self.__class__.__name__)
        self.semaphore = asyncio.Semaphore(5)  # 同時リクエスト数制限
    
    @abstractmethod
    async def scrape_articles(self) -> List[ArticleData]:
        """記事収集の抽象メソッド"""
        pass
    
    async def _fetch_with_retry(
        self, 
        url: str, 
        max_retries: int = 3,
        **kwargs
    ) -> Optional[aiohttp.ClientResponse]:
        """リトライ付きHTTPリクエスト"""
        async with self.semaphore:
            for attempt in range(max_retries + 1):
                try:
                    async with self.session.get(url, **kwargs) as response:
                        response.raise_for_status()
                        return response
                except aiohttp.ClientError as e:
                    if attempt == max_retries:
                        self.logger.error(f"Failed to fetch {url} after {max_retries} retries: {e}")
                        return None
                    await asyncio.sleep(2 ** attempt)  # exponential backoff
    
    async def _fetch_article_content(self, url: str) -> Optional[str]:
        """記事本文取得"""
        response = await self._fetch_with_retry(url)
        if response:
            content = await response.text()
            return await self._parse_article_body(content)
        return None
    
    @abstractmethod
    async def _parse_article_body(self, html_content: str) -> str:
        """HTML解析の抽象メソッド"""
        pass
```

##### **5.1.2 非同期Reuters スクレイパー**
```python
from playwright.async_api import async_playwright
import asyncio

class AsyncReutersScraper(AsyncNewsScraper):
    async def scrape_articles(self) -> List[ArticleData]:
        """非同期でロイター記事を収集"""
        articles = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                # 複数ページを並行処理
                tasks = []
                for page_num in range(self.config.reuters.max_pages):
                    task = self._scrape_page(browser, page_num)
                    tasks.append(task)
                
                # 全ページの結果をまとめる
                page_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in page_results:
                    if isinstance(result, list):
                        articles.extend(result)
                    elif isinstance(result, Exception):
                        self.logger.error(f"Page scraping failed: {result}")
                
            finally:
                await browser.close()
        
        return articles
    
    async def _scrape_page(self, browser, page_num: int) -> List[ArticleData]:
        """単一ページのスクレイピング"""
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # ページアクセス
            offset = page_num * self.config.reuters.items_per_page
            url = f"https://jp.reuters.com/site-search/?query={self.config.reuters.query}&offset={offset}"
            
            await page.goto(url, wait_until='networkidle')
            
            # 記事要素取得
            article_elements = await page.query_selector_all('[data-testid="StoryCard"]')
            
            # 各記事の詳細を並行取得
            tasks = []
            for element in article_elements:
                task = self._extract_article_data(element, context)
                tasks.append(task)
            
            articles = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 成功した結果のみ返す
            return [article for article in articles if isinstance(article, ArticleData)]
            
        finally:
            await context.close()
    
    async def _extract_article_data(self, element, context) -> Optional[ArticleData]:
        """記事要素から情報抽出"""
        try:
            # タイトルとURL取得
            title_element = await element.query_selector('[data-testid="TitleLink"]')
            if not title_element:
                return None
            
            title = await title_element.text_content()
            url = await title_element.get_attribute('href')
            
            if url.startswith('/'):
                url = f"https://jp.reuters.com{url}"
            
            # 本文を並行取得
            body = await self._fetch_article_content(url)
            
            # その他メタデータ取得
            time_element = await element.query_selector('[data-testid="DateLineText"]')
            published_jst = await self._parse_publish_time(time_element) if time_element else None
            
            return ArticleData(
                title=title,
                url=url,
                body=body or "",
                source="Reuters",
                published_jst=published_jst
            )
            
        except Exception as e:
            self.logger.error(f"Failed to extract article data: {e}")
            return None
```

##### **5.1.3 非同期AI処理**
```python
class AsyncAIProcessor:
    def __init__(self, api_key: str, max_concurrent: int = 10):
        self.api_key = api_key
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session = aiohttp.ClientSession()
        
    async def process_articles_batch(
        self, 
        articles: List[ArticleData]
    ) -> List[ProcessedArticle]:
        """記事の一括AI処理"""
        tasks = []
        for article in articles:
            task = self._process_single_article(article)
            tasks.append(task)
        
        # 並行処理実行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_articles = []
        for article, result in zip(articles, results):
            if isinstance(result, dict):
                processed_article = ProcessedArticle(
                    **article.__dict__,
                    **result
                )
                processed_articles.append(processed_article)
            else:
                # エラー時のフォールバック
                processed_article = ProcessedArticle(
                    **article.__dict__,
                    summary="AI処理に失敗しました",
                    sentiment_label="Error",
                    sentiment_score=0.0
                )
                processed_articles.append(processed_article)
        
        return processed_articles
    
    async def _process_single_article(self, article: ArticleData) -> dict:
        """単一記事のAI処理"""
        async with self.semaphore:
            try:
                # Gemini API呼び出し（非同期）
                result = await self._call_gemini_api(article.body)
                return result
            except Exception as e:
                logger.error(f"AI processing failed for article {article.url}: {e}")
                raise
    
    async def _call_gemini_api(self, text: str) -> dict:
        """Gemini API非同期呼び出し"""
        # 実際の実装では、google-generativeaiの非同期バージョンを使用
        # または、HTTPクライアントで直接API呼び出し
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        payload = {
            'contents': [{
                'parts': [{'text': config.AI_PROCESS_PROMPT_TEMPLATE.format(text=text)}]
            }],
            'generationConfig': {
                'maxOutputTokens': 1024,
                'temperature': 0.2
            }
        }
        
        async with self.session.post(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite-001:generateContent',
            headers=headers,
            json=payload
        ) as response:
            response.raise_for_status()
            data = await response.json()
            
            # レスポンス解析
            content = data['candidates'][0]['content']['parts'][0]['text']
            return self._parse_ai_response(content)
    
    def _parse_ai_response(self, response_text: str) -> dict:
        """AI レスポンス解析"""
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            
            result = json.loads(json_str)
            
            # バリデーション
            required_fields = ['summary', 'sentiment_label', 'sentiment_score']
            if not all(field in result for field in required_fields):
                raise ValueError("Required fields missing in AI response")
            
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid AI response format: {e}")
    
    async def close(self):
        """リソースクリーンアップ"""
        await self.session.close()
```

---

## 📊 6. 監視・ログ改善

### 6.1 構造化ログシステム

#### **要件**
- JSON形式の構造化ログ
- ログレベルの適切な分離
- 検索・集計可能な形式
- セキュリティ考慮（機密情報のマスキング）

#### **技術仕様**

##### **6.1.1 ログ設定**
```python
import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import os

class StructuredFormatter(logging.Formatter):
    """構造化ログフォーマッター"""
    
    def format(self, record: logging.LogRecord) -> str:
        # 基本ログエントリ
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process_id': os.getpid(),
            'thread_id': record.thread
        }
        
        # 例外情報
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # 追加のコンテキスト情報
        if hasattr(record, 'extra_data'):
            log_entry['context'] = record.extra_data
        
        # 機密情報のマスキング
        log_entry = self._mask_sensitive_data(log_entry)
        
        return json.dumps(log_entry, ensure_ascii=False)
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """機密情報のマスキング"""
        sensitive_keys = {
            'api_key', 'token', 'password', 'secret', 'credentials',
            'gemini_api_key', 'service_account_json'
        }
        
        def mask_recursive(obj):
            if isinstance(obj, dict):
                return {
                    key: '***MASKED***' if any(sensitive in key.lower() for sensitive in sensitive_keys)
                    else mask_recursive(value)
                    for key, value in obj.items()
                }
            elif isinstance(obj, list):
                return [mask_recursive(item) for item in obj]
            else:
                return obj
        
        return mask_recursive(data)

class LoggerManager:
    """ログ管理クラス"""
    
    def __init__(self, app_name: str = "market_news"):
        self.app_name = app_name
        self.setup_logging()
    
    def setup_logging(self):
        """ログ設定初期化"""
        # ルートロガー設定
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # 既存ハンドラー削除
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(console_handler)
        
        # ファイルハンドラー（ローテーション付き）
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            f'logs/{self.app_name}.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
        
        # エラーログ専用ファイル
        error_handler = RotatingFileHandler(
            f'logs/{self.app_name}_errors.log',
            maxBytes=10*1024*1024,
            backupCount=10
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(error_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """ロガー取得"""
        return logging.getLogger(f"{self.app_name}.{name}")

# コンテキスト付きログ関数
def log_with_context(logger: logging.Logger, level: int, message: str, **context):
    """コンテキスト情報付きログ出力"""
    extra_data = {
        'operation': context.get('operation'),
        'url': context.get('url'),
        'duration_ms': context.get('duration_ms'),
        'status': context.get('status'),
        'count': context.get('count'),
        **{k: v for k, v in context.items() if k not in ['operation', 'url', 'duration_ms', 'status', 'count']}
    }
    
    # None値を除去
    extra_data = {k: v for k, v in extra_data.items() if v is not None}
    
    logger.log(level, message, extra={'extra_data': extra_data})

# 使用例
logger_manager = LoggerManager()
scraper_logger = logger_manager.get_logger('scraper')

# 使用方法
log_with_context(
    scraper_logger, 
    logging.INFO, 
    "記事収集完了",
    operation="scrape_articles",
    source="Reuters",
    count=25,
    duration_ms=5420
)
```

---

## 🔧 実装依存関係と順序

### 実装順序（依存関係考慮）

#### **Phase 1: 基盤整備（1-2週間）**
1. **型ヒント追加** → 全ファイル
2. **設定管理改善** → Pydantic導入
3. **ログシステム構築** → 構造化ログ
4. **エラーハンドリング強化** → リトライ・例外処理

#### **Phase 2: データ基盤（1-2週間）**  
1. **SQLiteデータベース** → スキーマ設計・ORM
2. **重複排除機能** → URL正規化・コンテンツ比較
3. **基本テスト** → pytest設定・単体テスト

#### **Phase 3: パフォーマンス改善（2-3週間）**
1. **非同期処理** → asyncio/aiohttp導入
2. **UI改善** → レスポンシブ・ダークモード
3. **統合テスト** → エンドツーエンドテスト

### 必要な新しい依存関係

```txt
# requirements_new.txt（追加分）
pydantic>=2.0.0
sqlalchemy>=2.0.0
alembic>=1.12.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
aiohttp>=3.8.0
playwright>=1.40.0
structlog>=23.1.0
```

---

## 📋 実装完了時の検証項目

### **コード品質**
- [ ] mypy エラーゼロ
- [ ] pytest カバレッジ >80%
- [ ] flake8/black 準拠
- [ ] セキュリティスキャン通過

### **機能検証**
- [ ] 記事収集の正常動作
- [ ] AI処理の並行実行
- [ ] データベース操作
- [ ] 重複排除機能
- [ ] HTML生成・表示

### **パフォーマンス**
- [ ] メモリ使用量監視
- [ ] 処理時間測定
- [ ] エラー率監視
- [ ] ログ出力確認

---

*この要件定義書に基づいて、段階的に実装を進めていきます。各フェーズの完了時に動作確認と品質チェックを行い、次のフェーズに進みます。*