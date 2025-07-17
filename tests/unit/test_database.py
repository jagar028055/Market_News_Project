# -*- coding: utf-8 -*-

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.database import DatabaseManager, Article, AIAnalysis
from tests.conftest import create_test_article, create_test_ai_analysis


class TestDatabaseManager:
    """DatabaseManager のテストクラス"""
    
    def test_save_article_success(self, test_db, sample_articles):
        """記事保存成功テスト"""
        article_data = sample_articles[0]
        
        # 記事保存
        saved_article = test_db.save_article(article_data)
        
        assert saved_article is not None
        assert saved_article.id is not None
        assert saved_article.title == article_data['title']
        assert saved_article.url == article_data['url']
        assert saved_article.source == article_data['source']
        assert saved_article.url_hash is not None
        assert saved_article.content_hash is not None
    
    def test_save_article_duplicate_detection(self, test_db, sample_articles):
        """重複記事検出テスト"""
        article_data = sample_articles[0]
        
        # 同じ記事を2回保存
        first_save = test_db.save_article(article_data)
        second_save = test_db.save_article(article_data)
        
        # 同じ記事オブジェクトが返される
        assert first_save.id == second_save.id
        
        # データベース内には1件のみ
        with test_db.get_session() as session:
            count = session.query(Article).count()
            assert count == 1
    
    def test_save_ai_analysis_success(self, test_db, sample_articles, sample_ai_analysis):
        """AI分析結果保存成功テスト"""
        # 記事を先に保存
        article = test_db.save_article(sample_articles[0])
        analysis_data = sample_ai_analysis[0]
        
        # AI分析結果保存
        saved_analysis = test_db.save_ai_analysis(
            article.id, 
            analysis_data,
            processing_time_ms=1500
        )
        
        assert saved_analysis is not None
        assert saved_analysis.id is not None
        assert saved_analysis.article_id == article.id
        assert saved_analysis.summary == analysis_data['summary']
        assert saved_analysis.sentiment_label == analysis_data['sentiment_label']
        assert saved_analysis.sentiment_score == analysis_data['sentiment_score']
        assert saved_analysis.processing_time_ms == 1500
    
    def test_save_ai_analysis_update_existing(self, test_db, sample_articles, sample_ai_analysis):
        """既存AI分析結果の更新テスト"""
        # 記事とAI分析結果を保存
        article = test_db.save_article(sample_articles[0])
        original_analysis = test_db.save_ai_analysis(article.id, sample_ai_analysis[0])
        
        # 異なる分析結果で更新
        updated_data = {
            'summary': '更新された要約',
            'sentiment_label': 'Negative',
            'sentiment_score': 0.2,
            'model_version': 'updated-model'
        }
        
        updated_analysis = test_db.save_ai_analysis(article.id, updated_data)
        
        # 同じIDで内容が更新されている
        assert updated_analysis.id == original_analysis.id
        assert updated_analysis.summary == '更新された要約'
        assert updated_analysis.sentiment_label == 'Negative'
        assert updated_analysis.sentiment_score == 0.2
    
    def test_get_recent_articles(self, test_db, sample_articles):
        """最新記事取得テスト"""
        # 複数記事を保存
        for article_data in sample_articles:
            test_db.save_article(article_data)
        
        # 過去24時間の記事取得
        recent_articles = test_db.get_recent_articles(hours=24)
        
        assert len(recent_articles) == len(sample_articles)
        # 公開日時の降順で並んでいることを確認
        for i in range(len(recent_articles) - 1):
            assert recent_articles[i].published_at >= recent_articles[i + 1].published_at
    
    def test_get_recent_articles_source_filter(self, test_db, sample_articles):
        """ソース別記事取得テスト"""
        # 複数記事を保存
        for article_data in sample_articles:
            test_db.save_article(article_data)
        
        # ロイターの記事のみ取得
        reuters_articles = test_db.get_recent_articles(hours=24, source="Reuters")
        
        # ロイターの記事のみが返される
        assert len(reuters_articles) == 2  # sample_articlesのうち2件がReuters
        for article in reuters_articles:
            assert article.source == "Reuters"
    
    def test_detect_duplicate_articles(self, test_db):
        """重複記事検出テスト"""
        # 同じ内容の記事を作成
        article1 = create_test_article(
            title="同じタイトル",
            url="https://test1.com/article1",
            body="同じ内容の記事です。"
        )
        article2 = create_test_article(
            title="同じタイトル",
            url="https://test2.com/article2", 
            body="同じ内容の記事です。"
        )
        
        # 記事保存
        test_db.save_article(article1)
        test_db.save_article(article2)
        
        # 重複検出
        duplicates = test_db.detect_duplicate_articles()
        
        assert len(duplicates) == 1  # 1つの重複ペア
        pair = duplicates[0]
        assert len(pair) == 2
    
    def test_scraping_session_lifecycle(self, test_db):
        """スクレイピングセッションライフサイクルテスト"""
        # セッション開始
        session = test_db.start_scraping_session()
        
        assert session is not None
        assert session.id is not None
        assert session.status == 'running'
        assert session.started_at is not None
        
        # セッション更新
        updated_session = test_db.update_scraping_session(
            session.id,
            articles_found=10,
            articles_processed=8
        )
        
        assert updated_session.articles_found == 10
        assert updated_session.articles_processed == 8
        
        # セッション完了
        completed_session = test_db.complete_scraping_session(
            session.id,
            status='completed'
        )
        
        assert completed_session.status == 'completed'
        assert completed_session.completed_at is not None
        assert completed_session.total_duration_ms is not None
    
    def test_get_statistics(self, test_db, sample_articles, sample_ai_analysis):
        """統計情報取得テスト"""
        # テストデータ準備
        articles = []
        for i, article_data in enumerate(sample_articles):
            article = test_db.save_article(article_data)
            articles.append(article)
            
            # AI分析結果も保存
            test_db.save_ai_analysis(article.id, sample_ai_analysis[i])
        
        # 統計取得
        stats = test_db.get_statistics(days=7)
        
        assert 'total_articles' in stats
        assert 'source_breakdown' in stats
        assert 'sentiment_breakdown' in stats
        assert 'recent_sessions' in stats
        
        assert stats['total_articles'] == 3
        assert 'Reuters' in stats['source_breakdown']
        assert 'Bloomberg' in stats['source_breakdown']
    
    def test_cleanup_old_data(self, test_db):
        """古いデータクリーンアップテスト"""
        # 古い記事を作成
        old_article = create_test_article(
            title="古い記事",
            url="https://old.com/article",
            published_jst=datetime.now() - timedelta(days=100)
        )
        
        # 新しい記事を作成
        new_article = create_test_article(
            title="新しい記事", 
            url="https://new.com/article",
            published_jst=datetime.now()
        )
        
        # 記事保存
        test_db.save_article(old_article)
        test_db.save_article(new_article)
        
        # クリーンアップ実行（30日以上古いデータを削除）
        deleted_count = test_db.cleanup_old_data(days_to_keep=30)
        
        assert deleted_count == 1
        
        # 新しい記事は残っている
        with test_db.get_session() as session:
            remaining_count = session.query(Article).count()
            assert remaining_count == 1
    
    @patch('src.database.database_manager.log_with_context')
    def test_logging_integration(self, mock_log, test_db, sample_articles):
        """ログ統合テスト"""
        # 記事保存（ログが出力されることを確認）
        test_db.save_article(sample_articles[0])
        
        # ログ関数が呼ばれていることを確認
        assert mock_log.called
        
        # ログの内容を確認
        calls = mock_log.call_args_list
        assert any('save_article' in str(call) for call in calls)