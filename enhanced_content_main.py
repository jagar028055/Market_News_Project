#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
拡張SNSコンテンツ機能改善システム - メインワークフロー

独立したワークフローとして、以下の機能を提供：
1. リアルタイムマーケットデータ統合
2. AI記事要約・分析の高度化
3. 市場状況に応じた動的テンプレート選択
4. 品質管理・バリデーション

従来のニュース処理システムとは独立して動作する。
"""

import sys
import os
import logging
import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

# プロジェクトパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 環境変数読み込み
from dotenv import load_dotenv
load_dotenv()

# 地域分類関数をインポート
from classify_article_region import classify_article_region

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """ログ設定"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'enhanced_content_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)

class EnhancedContentProcessor:
    """拡張SNSコンテンツ処理システム"""
    
    def __init__(self, 
                 quality_threshold: float = 70.0,
                 similarity_threshold: float = 0.7,
                 enable_fact_check: bool = True,
                 logger: Optional[logging.Logger] = None):
        """
        初期化
        
        Args:
            quality_threshold: 品質スコア閾値
            similarity_threshold: 類似度判定閾値
            enable_fact_check: ファクトチェック有効化フラグ
            logger: ロガー
        """
        self.quality_threshold = quality_threshold
        self.similarity_threshold = similarity_threshold
        self.enable_fact_check = enable_fact_check
        self.logger = logger or logging.getLogger(__name__)
        
        # コンポーネントの初期化（遅延読み込み）
        self._market_fetcher = None
        self._template_selector = None
        self._content_validator = None
        self._similarity_checker = None
        self._fact_checker = None
        
        self.logger.info("拡張SNSコンテンツ処理システム初期化完了")
    
    @property
    def market_fetcher(self):
        """MarketDataFetcher の遅延初期化"""
        if self._market_fetcher is None:
            try:
                from src.market_data.fetcher import MarketDataFetcher
                self._market_fetcher = MarketDataFetcher(logger=self.logger)
                self.logger.info("MarketDataFetcher 初期化成功")
            except ImportError as e:
                self.logger.error(f"MarketDataFetcher 初期化失敗: {e}")
                self._market_fetcher = None
        return self._market_fetcher
    
    @property
    def template_selector(self):
        """TemplateSelector の遅延初期化"""
        if self._template_selector is None:
            try:
                from src.content.template_selector import TemplateSelector
                self._template_selector = TemplateSelector(logger=self.logger)
                self.logger.info("TemplateSelector 初期化成功")
            except ImportError as e:
                self.logger.error(f"TemplateSelector 初期化失敗: {e}")
                self._template_selector = None
        return self._template_selector
    
    @property
    def content_validator(self):
        """ContentValidator の遅延初期化"""
        if self._content_validator is None:
            try:
                from src.quality.content_validator import ContentValidator
                self._content_validator = ContentValidator(
                    min_quality_score=self.quality_threshold,
                    logger=self.logger
                )
                self.logger.info("ContentValidator 初期化成功")
            except ImportError as e:
                self.logger.error(f"ContentValidator 初期化失敗: {e}")
                self._content_validator = None
        return self._content_validator
    
    @property
    def similarity_checker(self):
        """SimilarityChecker の遅延初期化"""
        if self._similarity_checker is None:
            try:
                from src.quality.similarity_checker import SimilarityChecker
                self._similarity_checker = SimilarityChecker(
                    similarity_threshold=self.similarity_threshold,
                    logger=self.logger
                )
                self.logger.info("SimilarityChecker 初期化成功")
            except ImportError as e:
                self.logger.error(f"SimilarityChecker 初期化失敗: {e}")
                self._similarity_checker = None
        return self._similarity_checker
    
    @property
    def fact_checker(self):
        """FactChecker の遅延初期化"""
        if self._fact_checker is None and self.enable_fact_check:
            try:
                from src.quality.fact_checker import FactChecker
                self._fact_checker = FactChecker(
                    market_fetcher=self.market_fetcher,
                    logger=self.logger
                )
                self.logger.info("FactChecker 初期化成功")
            except ImportError as e:
                self.logger.error(f"FactChecker 初期化失敗: {e}")
                self._fact_checker = None
        return self._fact_checker
    
    def process_enhanced_content(self, input_articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        拡張コンテンツ処理のメイン実行
        
        Args:
            input_articles: 入力記事リスト
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        self.logger.info(f"=== 拡張コンテンツ処理開始 ===")
        self.logger.info(f"入力記事数: {len(input_articles)}")
        
        results = {
            'input_article_count': len(input_articles),
            'market_context': None,
            'selected_template': None,
            'quality_check_results': None,
            'similarity_check_results': None,
            'fact_check_results': None,
            'enhanced_articles': [],
            'processing_timestamp': datetime.now().isoformat(),
            'warnings': [],
            'errors': []
        }
        
        if not input_articles:
            results['warnings'].append("入力記事が空です")
            return results
        
        try:
            # 1. マーケットデータ取得・コンテキスト生成
            self.logger.info("🌍 マーケットデータ取得中...")
            market_context = self._get_market_context()
            results['market_context'] = market_context
            
            # 2. 動的テンプレート選択
            self.logger.info("📋 動的テンプレート選択中...")
            template_info = self._select_optimal_template(input_articles)
            results['selected_template'] = template_info
            
            # 3. 記事の品質チェック
            self.logger.info("✅ 品質チェック実行中...")
            quality_results = self._perform_quality_check(input_articles)
            results['quality_check_results'] = quality_results
            
            # 4. 類似度・重複チェック
            self.logger.info("🔍 類似度チェック実行中...")
            similarity_results = self._perform_similarity_check(input_articles)
            results['similarity_check_results'] = similarity_results
            
            # 5. ファクトチェック（有効な場合のみ）
            if self.enable_fact_check:
                self.logger.info("🧐 ファクトチェック実行中...")
                fact_results = self._perform_fact_check(input_articles)
                results['fact_check_results'] = fact_results
            
            # 6. 拡張記事生成
            self.logger.info("📝 拡張記事生成中...")
            enhanced_articles = self._generate_enhanced_articles(
                input_articles, market_context, template_info, quality_results
            )
            results['enhanced_articles'] = enhanced_articles
            
            # 地域別分析を追加
            region_analysis = self._analyze_articles_by_region(input_articles)
            results['region_analysis'] = region_analysis
            
            # 7. 最終品質レポート生成
            report = self._generate_final_report(results)
            results['final_report'] = report
            
            self.logger.info(f"✅ 拡張コンテンツ処理完了")
            self.logger.info(f"拡張記事生成数: {len(enhanced_articles)}")
            
        except Exception as e:
            error_msg = f"拡張コンテンツ処理でエラー: {e}"
            self.logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)
        
        return results
    
    def _get_market_context(self) -> Optional[Dict[str, Any]]:
        """マーケットコンテキスト取得"""
        if not self.market_fetcher:
            self.logger.warning("MarketDataFetcher が利用できません")
            return None
        
        try:
            snapshot = self.market_fetcher.get_current_market_snapshot()
            context_text = self.market_fetcher.get_market_context_for_llm()
            
            return {
                'snapshot': {
                    'sentiment': snapshot.overall_sentiment.value,
                    'volatility_score': snapshot.volatility_score,
                    'stock_indices_count': len(snapshot.stock_indices),
                    'currency_pairs_count': len(snapshot.currency_pairs),
                    'timestamp': snapshot.timestamp.isoformat()
                },
                'llm_context_text': context_text
            }
        except Exception as e:
            self.logger.error(f"マーケットコンテキスト取得エラー: {e}")
            return None
    
    def _select_optimal_template(self, articles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """最適テンプレート選択"""
        if not self.template_selector or not self.market_fetcher:
            self.logger.warning("テンプレート選択に必要なコンポーネントが利用できません")
            return None
        
        try:
            market_snapshot = self.market_fetcher.get_current_market_snapshot()
            selected_template = self.template_selector.select_template(
                market_snapshot, articles, datetime.now()
            )
            
            template_config = self.template_selector.get_template_config(selected_template)
            
            return {
                'template_type': selected_template.value,
                'config': template_config
            }
        except Exception as e:
            self.logger.error(f"テンプレート選択エラー: {e}")
            return None
    
    def _perform_quality_check(self, articles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """品質チェック実行"""
        if not self.content_validator:
            self.logger.warning("ContentValidator が利用できません")
            return None
        
        try:
            validation_results = self.content_validator.validate_article_batch(articles)
            quality_report = self.content_validator.get_quality_report(validation_results)
            
            return {
                'individual_results': [
                    {
                        'score': result.score,
                        'passed': result.passed,
                        'issues_count': len(result.issues),
                        'recommendations_count': len(result.recommendations)
                    }
                    for result in validation_results
                ],
                'summary': quality_report
            }
        except Exception as e:
            self.logger.error(f"品質チェックエラー: {e}")
            return None
    
    def _perform_similarity_check(self, articles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """類似度チェック実行"""
        if not self.similarity_checker:
            self.logger.warning("SimilarityChecker が利用できません")
            return None
        
        try:
            return self.similarity_checker.check_similarity_batch(articles)
        except Exception as e:
            self.logger.error(f"類似度チェックエラー: {e}")
            return None
    
    def _perform_fact_check(self, articles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """ファクトチェック実行"""
        if not self.fact_checker:
            self.logger.warning("FactChecker が利用できません")
            return None
        
        try:
            return self.fact_checker.check_batch_consistency(articles)
        except Exception as e:
            self.logger.error(f"ファクトチェックエラー: {e}")
            return None
    
    def _generate_enhanced_articles(self, 
                                   articles: List[Dict[str, Any]], 
                                   market_context: Optional[Dict[str, Any]],
                                   template_info: Optional[Dict[str, Any]],
                                   quality_results: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """拡張記事生成"""
        enhanced_articles = []
        
        for i, article in enumerate(articles):
            try:
                # 品質チェック結果を取得
                quality_passed = True
                if quality_results and 'individual_results' in quality_results:
                    if i < len(quality_results['individual_results']):
                        quality_passed = quality_results['individual_results'][i]['passed']
                
                # 実際のコンテンツ拡張を実行
                enhanced_content = self._create_enhanced_content(article, market_context, template_info)
                
                enhanced_article = {
                    'original_article': article,
                    'enhanced_content': enhanced_content,
                    'market_context_applied': market_context is not None,
                    'template_type': template_info['template_type'] if template_info else 'default',
                    'quality_passed': quality_passed,
                    'enhancement_timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # マーケットコンテキストが利用可能な場合の拡張処理
                if market_context:
                    enhanced_article['market_insights'] = {
                        'market_sentiment': market_context['snapshot']['sentiment'],
                        'volatility_level': 'High' if market_context['snapshot']['volatility_score'] > 70 else 'Normal',
                        'volatility_score': market_context['snapshot']['volatility_score']
                    }
                
                enhanced_articles.append(enhanced_article)
                
            except Exception as e:
                self.logger.error(f"記事 {i+1} の拡張処理でエラー: {e}")
                # エラーが発生しても他の記事の処理を続行
                enhanced_articles.append({
                    'original_article': article,
                    'enhancement_error': str(e),
                    'enhancement_timestamp': datetime.now().isoformat()
                })
        
        return enhanced_articles
    
    def _analyze_articles_by_region(self, articles: List[Dict[str, Any]]) -> Dict[str, int]:
        """地域別記事分析（日本・米国・欧州の3地域のみ）"""
        region_count = {
            'japan': 0,
            'usa': 0,
            'europe': 0
        }
        
        for article in articles:
            # 地域分類関数を使用
            region = classify_article_region(article)
            region_count[region] += 1
        
        return region_count
    
    def _generate_final_report(self, results: Dict[str, Any]) -> str:
        """最終レポート生成"""
        report_lines = [
            "=== 拡張SNSコンテンツ処理レポート ===",
            f"処理日時: {results['processing_timestamp']}",
            f"入力記事数: {results['input_article_count']}",
            f"拡張記事生成数: {len(results['enhanced_articles'])}",
            ""
        ]
        
        # 地域別分析を追加（日本・米国・欧州の3地域のみ）
        if 'region_analysis' in results:
            report_lines.append("地域別分析:")
            # 3地域のみ表示
            for region in ['japan', 'usa', 'europe']:
                count = results['region_analysis'].get(region, 0)
                if count > 0:
                    region_name = {'japan': '日本', 'usa': '米国', 'europe': '欧州'}[region]
                    report_lines.append(f"  - {region_name}: {count}件")
            report_lines.append("")
        
        # マーケットコンテキスト情報
        if results['market_context']:
            mc = results['market_context']['snapshot']
            report_lines.extend([
                f"市場センチメント: {mc['sentiment']}",
                f"ボラティリティ: {mc['volatility_score']:.1f}",
                f"データ取得時刻: {mc['timestamp']}",
                ""
            ])
        
        # テンプレート情報
        if results['selected_template']:
            report_lines.append(f"選択テンプレート: {results['selected_template']['template_type']}")
            report_lines.append("")
        
        # 品質チェック結果
        if results['quality_check_results']:
            qr = results['quality_check_results']['summary']
            report_lines.extend([
                f"品質チェック合格率: {qr['summary']['pass_rate']}%",
                f"平均品質スコア: {qr['score_statistics']['average']:.1f}",
                ""
            ])
        
        # 類似度チェック結果
        if results['similarity_check_results']:
            sr = results['similarity_check_results']
            report_lines.extend([
                f"類似記事ペア: {len(sr['similar_pairs'])}組",
                f"コンテンツ多様性スコア: {sr['diversity_score']:.3f}",
                ""
            ])
        
        # ファクトチェック結果
        if results['fact_check_results']:
            fr = results['fact_check_results']
            report_lines.extend([
                f"ファクトチェック平均精度: {fr['average_accuracy']:.1f}%",
                f"高信頼度記事: {fr['high_confidence_articles']}/{fr['total_articles']}",
                ""
            ])
        
        # 警告・エラー
        if results['warnings']:
            report_lines.append("警告:")
            for warning in results['warnings']:
                report_lines.append(f"  - {warning}")
            report_lines.append("")
        
        if results['errors']:
            report_lines.append("エラー:")
            for error in results['errors']:
                report_lines.append(f"  - {error}")
        
        return "\\n".join(report_lines)

def create_sample_articles() -> List[Dict[str, Any]]:
    """サンプル記事データ生成（テスト用）"""
    return [
        {
            'title': 'FRBが政策金利を0.25%引き上げ、インフレ抑制策を強化',
            'summary': '米連邦準備制度理事会（FRB）は26日、連邦公開市場委員会（FOMC）で政策金利を0.25%引き上げ、5.25-5.50%の範囲とすることを決定した。インフレ率が目標の2%を上回る状況が続いているため、引き締め策を継続する方針を示した。',
            'category': '金融政策',
            'region': 'usa',
            'source': 'Reuters',
            'published_jst': datetime.now(timezone.utc),
            'sentiment_label': 'neutral'
        },
        {
            'title': '日経平均、3万8500円台で推移　米金利上昇懸念で上値重い',
            'summary': '4日の東京株式市場では、日経平均株価が3万8500円台で推移している。米国の金利上昇懸念から投資家心理が慎重になっており、上値の重い展開が続いている。市場では今後の米金融政策動向に注目が集まっている。',
            'category': '市場動向',
            'region': 'japan',
            'source': 'Bloomberg',
            'published_jst': datetime.now(timezone.utc),
            'sentiment_label': 'bearish'
        }
    ]

def extract_recent_articles_by_region(articles_file: str, hours_back: int = 24) -> Dict[str, List[Dict[str, Any]]]:
    """
    過去N時間以内の記事を地域別に抽出
    
    Args:
        articles_file: 記事データファイルパス
        hours_back: 抽出対象時間（時間）
    
    Returns:
        Dict[str, List[Dict]]: 地域別記事リスト
    """
    try:
        with open(articles_file, 'r', encoding='utf-8') as f:
            all_articles = json.load(f)
        
        # 現在時刻から指定時間前までの範囲（UTC統一）
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        # 地域別記事分類（日本・米国・欧州の3地域のみ）
        region_articles = {
            'japan': [],
            'usa': [], 
            'europe': []
        }
        
        logging.info(f"記事フィルタリング開始: {len(all_articles)}件の記事を確認中")
        logging.info(f"カットオフ時刻: {cutoff_time} (UTC)")
        logging.info(f"現在時刻: {datetime.now(timezone.utc)} (UTC)")
        
        passed_count = 0
        skipped_count = 0
        
        for i, article in enumerate(all_articles):
            try:
                # 公開時刻の解析
                published_str = article.get('published_jst', '')
                if i < 5:  # 最初の5件をデバッグ表示
                    logging.info(f"記事{i+1}: published_jst='{published_str}', title='{article.get('title', 'N/A')[:50]}...'")
                
                if published_str:
                    # ISO形式の日時文字列を解析（UTC統一）
                    if isinstance(published_str, str):
                        # タイムゾーン情報を除去して解析し、UTCとして明示的に設定
                        dt_naive = datetime.fromisoformat(published_str.replace('Z', '+00:00').split('+')[0])
                        published_dt = dt_naive.replace(tzinfo=timezone.utc)
                    else:
                        published_dt = published_str
                        if published_dt.tzinfo is None:
                            published_dt = published_dt.replace(tzinfo=timezone.utc)
                    
                    # 指定時間以内の記事のみ抽出
                    if published_dt >= cutoff_time:
                        # 地域分類関数を使用
                        region = classify_article_region(article)
                        region_articles[region].append(article)
                        passed_count += 1
                        if i < 5:
                            logging.info(f"記事{i+1}を{region}地域に分類 (公開: {published_dt})")
                    else:
                        skipped_count += 1
                        if i < 5:
                            time_diff = cutoff_time - published_dt
                            logging.info(f"記事{i+1}は古すぎるためスキップ: {published_dt} (カットオフより{time_diff}前)")
                            
            except Exception as e:
                if i < 5:
                    logging.info(f"記事{i+1}の日時解析エラー: {e}")
                continue
        
        logging.info(f"フィルタリング結果: 通過={passed_count}件, スキップ={skipped_count}件")
        
        # 各地域の記事を新しい順にソート
        for region in region_articles:
            region_articles[region].sort(
                key=lambda x: x.get('published_jst', ''), 
                reverse=True
            )
        
        return region_articles
        
    except Exception as e:
        logging.error(f"記事抽出エラー: {e}")
        return {
            'japan': [],
            'usa': [], 
            'europe': []
        }

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='拡張SNSコンテンツ処理システム')
    parser.add_argument('--input-file', type=str, help='入力記事JSONファイルパス')
    parser.add_argument('--output-file', type=str, help='出力結果JSONファイルパス') 
    parser.add_argument('--quality-threshold', type=float, default=70.0, help='品質スコア閾値')
    parser.add_argument('--similarity-threshold', type=float, default=0.7, help='類似度判定閾値')
    parser.add_argument('--disable-fact-check', action='store_true', help='ファクトチェック無効化')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='ログレベル')
    parser.add_argument('--test-mode', action='store_true', help='テストモード（サンプルデータ使用）')
    
    args = parser.parse_args()
    
    # ログ設定
    logger = setup_logging(args.log_level)
    logger.info("🚀 拡張SNSコンテンツ処理システム開始")
    
    try:
        # 処理システム初期化
        processor = EnhancedContentProcessor(
            quality_threshold=args.quality_threshold,
            similarity_threshold=args.similarity_threshold,
            enable_fact_check=not args.disable_fact_check,
            logger=logger
        )
        
        # 入力データ読み込み
        if args.test_mode:
            logger.info("テストモードでサンプルデータを使用")
            input_articles = create_sample_articles()
        elif args.input_file:
            logger.info(f"入力ファイル読み込み: {args.input_file}")
            # 24時間以内の記事を地域別に抽出
            region_articles = extract_recent_articles_by_region(args.input_file)
            
            # 全地域の記事を統合
            input_articles = []
            for region, articles in region_articles.items():
                input_articles.extend(articles)
            
            logger.info(f"記事抽出結果:")
            for region, articles in region_articles.items():
                if articles:
                    region_name = {'japan': '日本', 'usa': '米国', 'europe': '欧州'}[region]
                    logger.info(f"  - {region_name}: {len(articles)}件")
            logger.info(f"総記事数: {len(input_articles)}件")
        else:
            logger.info("デフォルトでサンプルデータを使用")
            input_articles = create_sample_articles()
        
        # メイン処理実行
        results = processor.process_enhanced_content(input_articles)
        
        # 結果出力
        if args.output_file:
            logger.info(f"結果をファイルに保存: {args.output_file}")
            import json
            with open(args.output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        # レポート表示
        if 'final_report' in results:
            print("\\n" + results['final_report'])
        
        logger.info("✅ 拡張SNSコンテンツ処理システム完了")
        
    except Exception as e:
        logger.error(f"💥 システム実行エラー: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()