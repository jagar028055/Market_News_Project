# -*- coding: utf-8 -*-

"""
改善されたHTMLジェネレーター
"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .template_engine import HTMLTemplateEngine, TemplateData
from ..error_handling import HTMLGenerationError, error_context

# ワードクラウド機能（オプショナル）
try:
    from ..wordcloud.generator import WordCloudGenerator
    from ..wordcloud.config import get_wordcloud_config
    WORDCLOUD_AVAILABLE = True
except ImportError as e:
    # ワードクラウド関連パッケージが見つからない場合
    WordCloudGenerator = None
    get_wordcloud_config = None
    WORDCLOUD_AVAILABLE = False


class HTMLGenerator:
    """HTMLファイル生成器"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.template_engine = HTMLTemplateEngine()

        # ワードクラウド生成器を初期化（利用可能な場合のみ）
        self.wordcloud_generator = None
        if WORDCLOUD_AVAILABLE:
            try:
                wordcloud_config = get_wordcloud_config()
                self.wordcloud_generator = WordCloudGenerator(wordcloud_config)
                self.logger.info("✅ ワードクラウド生成器を初期化しました")
            except Exception as e:
                self.logger.warning(f"⚠️ ワードクラウド生成器の初期化に失敗: {e}")
        else:
            self.logger.info("ℹ️ ワードクラウド機能は無効です（依存関係なし）")
            self.wordcloud_generator = None

    def generate_html_file(
        self,
        articles: List[Dict[str, Any]],
        output_path: str = "index.html",
        title: str = "Market News Dashboard - AIニュース分析",
        integrated_summaries: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        HTMLファイルの生成

        Args:
            articles: 記事データリスト
            output_path: 出力ファイルパス
            title: ページタイトル
            integrated_summaries: Pro統合要約データ（地域別要約、グローバル概況、地域間相互影響分析）
        """
        # HTMLファイルの完全クリア処理を強化
        self._ensure_clean_html_file(output_path)

        with error_context("html_generation", "HTMLGenerator", self.logger):
            # 統計計算
            stats = self._calculate_statistics(articles)

            # 最終更新時刻計算
            last_updated = self._calculate_last_updated(articles)

            # ワードクラウド生成（詳細ログ付き）
            self.logger.info("🚨 ワードクラウド生成を開始します")
            self.logger.info(f"🚨 ワードクラウド生成器利用可能: {WORDCLOUD_AVAILABLE}")
            self.logger.info(f"🚨 ワードクラウド生成器インスタンス: {self.wordcloud_generator is not None}")
            wordcloud_data = self._generate_wordcloud(articles)
            self.logger.info(f"🚨 ワードクラウド生成結果: {wordcloud_data is not None}")

            # テンプレートデータ作成
            template_data = TemplateData(
                title=title,
                articles=articles,
                total_articles=len(articles),
                last_updated=last_updated,
                # sentiment_stats=stats['sentiment'],  # 感情分析機能を削除
                source_stats=stats["source"],
                region_stats=stats["region"],  # 地域統計を追加
                category_stats=stats["category"],  # カテゴリ統計を追加
                integrated_summaries=integrated_summaries,  # Pro統合要約データを追加
                wordcloud_data=wordcloud_data,  # ワードクラウドデータを追加
            )

            # HTML生成
            html_content = self.template_engine.generate_html(template_data)

            # ファイル出力
            self._write_html_file(html_content, output_path)

            self.logger.info(
                f"HTMLファイルが正常に生成されました: {output_path} (記事数: {len(articles)}件)"
            )

    def _ensure_clean_html_file(self, output_path: str) -> None:
        """
        HTMLファイルの準備処理（SNSプレビューリンク付きindex.htmlを保護）

        Args:
            output_path: 出力ファイルパス
        """
        try:
            # index.htmlの場合は既存ファイルを保護（SNSプレビューリンク維持）
            if os.path.basename(output_path) == "index.html" and os.path.exists(output_path):
                # 既存のindex.htmlをバックアップ
                backup_path = output_path + ".backup"
                import shutil
                shutil.copy2(output_path, backup_path)
                self.logger.info(f"既存のindex.htmlをバックアップしました: {backup_path}")
                return
            
            # index.html以外のファイルは従来通り削除・作成
            if os.path.exists(output_path):
                os.remove(output_path)
                self.logger.info(f"既存のHTMLファイルを削除しました: {output_path}")

            # 空のHTMLファイルを新規作成して、ファイルの存在を確認
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("")  # 空ファイル作成

            # ファイル作成の確認
            if os.path.exists(output_path):
                self.logger.info(f"新しいHTMLファイルを作成しました: {output_path}")
            else:
                raise HTMLGenerationError(f"HTMLファイルの作成に失敗: {output_path}")

        except Exception as e:
            raise HTMLGenerationError(f"HTMLファイルの準備処理に失敗: {e}")

    def _calculate_statistics(self, articles: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
        """統計情報の計算"""
        source_stats = {}
        region_stats = {}
        category_stats = {}

        for article in articles:
            # ソース統計
            source = article.get("source", "Unknown")
            source_stats[source] = source_stats.get(source, 0) + 1
            
            # 地域統計
            region = article.get("region", "その他")
            region_stats[region] = region_stats.get(region, 0) + 1
            
            # カテゴリ統計
            category = article.get("category", "その他")
            category_stats[category] = category_stats.get(category, 0) + 1

        return {
            "source": source_stats,
            "region": region_stats,
            "category": category_stats
        }

    def _generate_wordcloud(self, articles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """ワードクラウドを生成"""
        self.logger.info("🚨 _generate_wordcloud関数が呼び出されました")
        self.logger.info(f"🚨 wordcloud_generatorが存在: {self.wordcloud_generator is not None}")
        self.logger.info(f"🚨 記事数: {len(articles) if articles else 0}")
        
        if not self.wordcloud_generator:
            self.logger.warning("🚨 ワードクラウド生成器が初期化されていません")
            return None
            
        if not articles:
            self.logger.warning("🚨 記事データが空です")
            return None

        try:
            self.logger.info("🚨 ワードクラウド生成処理を開始します")
            result = self.wordcloud_generator.generate_daily_wordcloud(articles)
            self.logger.info(f"🚨 ワードクラウド生成処理完了: success={result.success}")

            if result.success:
                self.logger.info(
                    f"🚨 ワードクラウド生成成功: 単語数={result.unique_words}, 品質スコア={result.quality_score:.1f}"
                )
                wordcloud_result = {
                    "image_base64": result.image_base64,
                    "total_articles": result.total_articles,
                    "total_words": result.total_words,
                    "unique_words": result.unique_words,
                    "generation_time_ms": result.generation_time_ms,
                    "quality_score": result.quality_score,
                    "word_frequencies": result.word_frequencies,
                }
                self.logger.info(f"🚨 ワードクラウド結果辞書作成完了: {len(wordcloud_result)}項目")
                return wordcloud_result
            else:
                self.logger.warning(f"🚨 ワードクラウド生成失敗: {result.error_message}")
                return None

        except Exception as e:
            self.logger.error(f"🚨 ワードクラウド生成でエラー: {e}")
            self.logger.error(f"🚨 エラー詳細: {type(e).__name__}: {str(e)}")
            import traceback
            self.logger.error(f"🚨 スタックトレース: {traceback.format_exc()}")
            return None

    def _calculate_last_updated(self, articles: List[Dict[str, Any]]) -> str:
        """
        HTMLファイル生成時刻の計算（東京時間）
        注：記事の公開時刻ではなく、実際のHTMLファイル生成時刻を返す
        """
        try:
            import pytz

            # 東京時間で現在時刻を取得
            jst = pytz.timezone("Asia/Tokyo")
            current_time = datetime.now(jst)
            return current_time.strftime("%Y/%m/%d %H:%M")
        except Exception as e:
            self.logger.warning(f"更新時刻の計算でエラー: {e}")
            # フォールバック: UTCから東京時間に変換
            try:
                import pytz

                utc_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
                jst_time = utc_time.astimezone(pytz.timezone("Asia/Tokyo"))
                return jst_time.strftime("%Y/%m/%d %H:%M")
            except:
                # 最終フォールバック: システム時刻（注: これは東京時間でない可能性あり）
                return datetime.now().strftime("%Y/%m/%d %H:%M")

    def _write_html_file(self, html_content: str, output_path: str) -> None:
        """HTMLファイルの書き込み"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception as e:
            raise HTMLGenerationError(f"HTMLファイルの書き込みに失敗しました: {e}")

    def validate_articles(self, articles: List[Dict[str, Any]]) -> List[str]:
        """記事データの検証"""
        errors = []

        for i, article in enumerate(articles):
            if not isinstance(article, dict):
                errors.append(f"記事 {i}: 辞書形式ではありません")
                continue

            # 必須フィールドのチェック
            required_fields = ["title", "url", "summary"]
            for field in required_fields:
                if not article.get(field):
                    errors.append(f"記事 {i}: {field} が不足しています")

            # URLの基本チェック
            url = article.get("url")
            if url and not (url.startswith("http://") or url.startswith("https://")):
                errors.append(f"記事 {i}: 不正なURL形式: {url}")

        return errors
