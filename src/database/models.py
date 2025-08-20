# -*- coding: utf-8 -*-

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Float,
    ForeignKey,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional

Base = declarative_base()


class Article(Base):
    """記事モデル"""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), unique=True, nullable=False, index=True)
    url_hash = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(1024), nullable=False)
    body = Column(Text)
    source = Column(String(100), nullable=False, index=True)
    category = Column(String(200))
    published_at = Column(DateTime, index=True)
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)
    content_hash = Column(String(64), index=True)

    # リレーション
    ai_analysis = relationship("AIAnalysis", back_populates="article", cascade="all, delete-orphan")

    # インデックス
    __table_args__ = (
        Index("idx_source_published", "source", "published_at"),
        Index("idx_scraped_published", "scraped_at", "published_at"),
    )

    def __repr__(self) -> str:
        return f"<Article(id={self.id}, title='{self.title[:50]}...', source='{self.source}')>"


class AIAnalysis(Base):
    """AI分析結果モデル"""

    __tablename__ = "ai_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    summary = Column(Text)
    sentiment_label = Column(String(20), index=True)  # 'Positive', 'Negative', 'Neutral'
    sentiment_score = Column(Float)
    analyzed_at = Column(DateTime, default=datetime.utcnow, index=True)
    model_version = Column(String(100))
    processing_time_ms = Column(Integer)  # 処理時間（ミリ秒）

    # リレーション
    article = relationship("Article", back_populates="ai_analysis")

    # インデックス
    __table_args__ = (
        Index("idx_sentiment_analyzed", "sentiment_label", "analyzed_at"),
        Index("idx_article_analyzed", "article_id", "analyzed_at"),
    )

    def __repr__(self) -> str:
        return f"<AIAnalysis(id={self.id}, article_id={self.article_id}, sentiment='{self.sentiment_label}')>"


class ScrapingSession(Base):
    """スクレイピングセッション管理モデル"""

    __tablename__ = "scraping_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    status = Column(String(20), default="running", index=True)  # 'running', 'completed', 'failed'

    # 統計情報
    articles_found = Column(Integer, default=0)
    articles_processed = Column(Integer, default=0)
    articles_new = Column(Integer, default=0)
    articles_duplicate = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)

    # 処理時間
    scraping_duration_ms = Column(Integer)
    ai_processing_duration_ms = Column(Integer)
    total_duration_ms = Column(Integer)

    # エラー詳細
    error_details = Column(Text)  # JSON形式でエラー詳細を保存

    def __repr__(self) -> str:
        return f"<ScrapingSession(id={self.id}, status='{self.status}', articles_found={self.articles_found})>"


class ProcessingStats(Base):
    """処理統計モデル"""

    __tablename__ = "processing_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)

    # 日次統計
    total_articles = Column(Integer, default=0)
    new_articles = Column(Integer, default=0)
    duplicate_articles = Column(Integer, default=0)

    # ソース別統計
    reuters_articles = Column(Integer, default=0)
    bloomberg_articles = Column(Integer, default=0)

    # 感情分析統計
    positive_articles = Column(Integer, default=0)
    negative_articles = Column(Integer, default=0)
    neutral_articles = Column(Integer, default=0)

    # パフォーマンス統計
    avg_processing_time_ms = Column(Float)
    total_processing_time_ms = Column(Integer)

    # インデックス
    __table_args__ = (Index("idx_date_stats", "date"),)

    def __repr__(self) -> str:
        return f"<ProcessingStats(date={self.date}, total_articles={self.total_articles})>"


class IntegratedSummary(Base):
    """統合要約モデル"""

    __tablename__ = "integrated_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("scraping_sessions.id"), nullable=False, index=True)
    summary_type = Column(String(20), nullable=False, index=True)  # 'regional' or 'global'
    region = Column(
        String(20), index=True
    )  # 地域別の場合のみ: 'japan', 'usa', 'china', 'europe', 'other'
    summary_text = Column(Text, nullable=False)
    articles_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    model_version = Column(String(100))  # 使用したGeminiモデルバージョン
    processing_time_ms = Column(Integer)  # 処理時間（ミリ秒）
    cost_usd = Column(Float)  # API使用コスト（USD）

    # リレーション
    session = relationship("ScrapingSession", backref="integrated_summaries")

    # インデックス
    __table_args__ = (
        Index("idx_session_type", "session_id", "summary_type"),
        Index("idx_type_region", "summary_type", "region"),
        Index("idx_created_session", "created_at", "session_id"),
    )

    def __repr__(self) -> str:
        return f"<IntegratedSummary(id={self.id}, type='{self.summary_type}', region='{self.region}', articles={self.articles_count})>"


class WordCloudData(Base):
    """ワードクラウドデータモデル"""

    __tablename__ = "wordcloud_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("scraping_sessions.id"), nullable=False, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    image_base64 = Column(Text, nullable=False)  # base64エンコードされた画像データ
    total_articles = Column(Integer, nullable=False)
    total_words = Column(Integer, nullable=False)
    unique_words = Column(Integer, nullable=False)
    generation_time_ms = Column(Integer)  # 生成時間（ミリ秒）
    config_version = Column(String(20))  # 設定バージョン

    # 品質指標
    image_size_bytes = Column(Integer)  # 画像ファイルサイズ
    word_coverage_ratio = Column(Float)  # 単語カバレッジ率
    quality_score = Column(Float)  # 画像品質スコア（0-100）

    # リレーション
    session = relationship("ScrapingSession", backref="wordcloud_data")
    frequencies = relationship(
        "WordCloudFrequency", back_populates="wordcloud_data", cascade="all, delete-orphan"
    )

    # インデックス
    __table_args__ = (
        Index("idx_session_generated", "session_id", "generated_at"),
        Index("idx_generated_quality", "generated_at", "quality_score"),
    )

    def __repr__(self) -> str:
        return f"<WordCloudData(id={self.id}, session_id={self.session_id}, articles={self.total_articles}, quality={self.quality_score})>"


class WordCloudFrequency(Base):
    """ワードクラウド単語頻度データモデル"""

    __tablename__ = "wordcloud_frequencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wordcloud_data_id = Column(Integer, ForeignKey("wordcloud_data.id"), nullable=False, index=True)
    word = Column(String(100), nullable=False, index=True)
    frequency = Column(Integer, nullable=False)
    weight_applied = Column(Float, default=1.0)  # 適用された重み
    tf_idf_score = Column(Float)  # TF-IDFスコア
    category = Column(String(50), index=True)  # 単語カテゴリ（金融、技術、地域等）

    # リレーション
    wordcloud_data = relationship("WordCloudData", back_populates="frequencies")

    # インデックス
    __table_args__ = (
        Index("idx_wordcloud_frequency", "wordcloud_data_id", "frequency"),
        Index("idx_word_frequency", "word", "frequency"),
        Index("idx_category_frequency", "category", "frequency"),
    )

    def __repr__(self) -> str:
        return f"<WordCloudFrequency(id={self.id}, word='{self.word}', frequency={self.frequency})>"
