# Git Cherry-Pick Conflict Report: Dynamic Article Collection Feature

## 概要

`master` ブランチ (`HEAD`) に、コミット `62ce74943b9298eebb923db538d9bcbbe57d060a` (feat: 動的記事取得システム実装による月曜日記事不足問題の解決) を `cherry-pick` しようとした際に、コンフリクトが発生しました。

ユーザーの意図としては、変更を廃棄することはなく、手動で統合し、`master` ブランチの内容を優先的に採用しつつ、`cherry-pick` コミットの機能（動的記事取得）も取り込むことを希望しています。また、再実装の可能性も検討されています。

## コンフリクトの状況

### Cherry-Pick 対象コミット

*   **コミットID:** `62ce74943b9298eebb923db538d9bcbbe57d060a`
*   **コミットメッセージ:** `feat: 動的記事取得システム実装による月曜日記事不足問題の解決`

### コンフリクト発生ファイル

1.  `src/config/app_config.py`
2.  `src/core/news_processor.py`

---

## 各ファイルのコンフリクト詳細

### 1. `src/config/app_config.py`

#### コンフリクト箇所: `PodcastConfig` クラスの定義

このコンフリクトは、`PodcastConfig` クラスの定義部分で発生しています。`master` ブランチ側では `__post_init__` メソッドが定義されているのに対し、`cherry-pick` コミット側ではポッドキャスト関連の新しい設定フィールド（音声設定、配信設定、ファイルパス設定など）と `load_pronunciation_dict` メソッドが追加されています。

```python
@dataclass
class PodcastConfig:
    """ポッドキャスト設定"""
    rss_base_url: str = ""
    author_name: str = "Market News Bot"
    author_email: str = "market-news@example.com"
    rss_title: str = "マーケットニュースポッドキャスト"
    rss_description: str = "AIが生成する毎日のマーケットニュース"
    monthly_cost_limit_usd: float = 10.0
    target_duration_minutes: float = 10.0
    max_file_size_mb: int = 15
    
<<<<<<< HEAD
    def __post_init__(self):
        """環境変数から設定を読み込み"""
        self.rss_base_url = os.getenv('PODCAST_RSS_BASE_URL', '')
        self.author_name = os.getenv('PODCAST_AUTHOR_NAME', self.author_name)
        self.author_email = os.getenv('PODCAST_AUTHOR_EMAIL', self.author_email)
        self.rss_title = os.getenv('PODCAST_RSS_TITLE', self.rss_title)
        self.rss_description = os.getenv('PODCAST_RSS_DESCRIPTION', self.rss_description)
        self.monthly_cost_limit_usd = float(os.getenv('PODCAST_MONTHLY_COST_LIMIT', str(self.monthly_cost_limit_usd)))
        self.target_duration_minutes = float(os.getenv('PODCAST_TARGET_DURATION_MINUTES', str(self.target_duration_minutes)))
        self.max_file_size_mb = int(os.getenv('PODCAST_MAX_FILE_SIZE_MB', str(self.max_file_size_mb)))
=======
    # 音声設定
    audio_format: str = "mp3"
    sample_rate: int = 44100
    bitrate: str = "128k"
    lufs_target: float = -16.0
    peak_target: float = -1.0
    
    # 配信設定
    rss_title: str = "マーケットニュース10分"
    rss_description: str = "AIが生成する毎日のマーケットニュース"
    episode_prefix: str = "第"
    episode_suffix: str = "回"
    
    # ファイルパス設定
    assets_path: str = "assets/audio"
    pronunciation_dict_path: str = "config/pronunciation_dict.yaml"
    
    # API設定
    gemini_api_key: str = ""
    line_channel_access_token: str = ""
    
    # GitHub Pages設定
    github_pages_url: str = ""
    rss_feed_path: str = "podcast/feed.xml"
    
    # コスト制限設定
    monthly_cost_limit_usd: float = 10.0
    
    def load_pronunciation_dict(self) -> Dict[str, str]:
        """発音辞書を読み込み"""
        try:
            with open(self.pronunciation_dict_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                # YAMLファイルが辞書形式の場合はそのまま返す
                if isinstance(data, dict):
                    return data
                return {}
            except FileNotFoundError:
                return {}
            except yaml.YAMLError:
                return {}
>>>>>>> 62ce749 (feat: 動的記事取得システム実装による月曜日記事不足問題の解決)
```

**解説:** 
`master` 側の `__post_init__` メソッドは、環境変数からポッドキャスト設定を読み込むためのものです。`cherry-pick` 側は、ポッドキャスト機能の拡張に伴う新しい設定項目と、発音辞書を読み込むためのメソッドを追加しています。これらは統合可能ですが、`__post_init__` の役割をどうするか、`PodcastConfig` 内で環境変数を読み込むべきか、`AppConfig` の `__post_init__` で一元的に読み込むべきか、設計の検討が必要です。

---


### 2. `src/core/news_processor.py`

#### コンフリクト箇所1: `validate_environment` メソッド

このコンフリクトは、`validate_environment` メソッドの環境変数検証ロジックで発生しています。`master` ブランチ側は `GEMINI_API_KEY` のみを検証しているのに対し、`cherry-pick` コミット側はGoogle Drive関連のIDや動的記事取得設定のログ出力など、より多くの環境変数と設定を表示・検証しています。

```python
    def validate_environment(self) -> bool:
        """環境変数の検証"""
        self.logger.info("=== 環境変数設定状況 ===")
<<<<<<< HEAD
        gemini_api_key = self.config.ai.gemini_api_key
        self.logger.info(f"GEMINI_API_KEY: {'設定済み' if gemini_api_key else '未設定'}")

        if not gemini_api_key:
            self.logger.error("必要な環境変数（GEMINI_API_KEY）が設定されていません")
            return False
        return True
=======
        self.logger.info(f"GOOGLE_DRIVE_OUTPUT_FOLDER_ID: {'設定済み' if self.folder_id else '未設定'}")
        self.logger.info(f"GOOGLE_OVERWRITE_DOC_ID: {'設定済み' if self.config.google.overwrite_doc_id else '未設定'}")
        self.logger.info(f"GEMINI_API_KEY: {'設定済み' if self.gemini_api_key else '未設定'}")
        self.logger.info(f"GOOGLE_SERVICE_ACCOUNT_JSON: {'設定済み' if self.config.google.service_account_json else '未設定'}")
        
        # 動的記事取得設定の表示
        self.logger.info("=== 動的記事取得設定 ===")
        self.logger.info(f"基本時間範囲: {self.config.scraping.hours_limit}時間")
        self.logger.info(f"最低記事数閾値: {self.config.scraping.minimum_article_count}件")
        self.logger.info(f"最大時間範囲: {self.config.scraping.max_hours_limit}時間")
        self.logger.info(f"週末拡張時間: {self.config.scraping.weekend_hours_extension}時間")
        
        if not self.folder_id or not self.gemini_api_key:
            self.logger.error("必要な環境変数が設定されていません")
            return False
        return True
>>>>>>> 62ce749 (feat: 動的記事取得システム実装による月曜日記事不足問題の解決)
```

**解説:** 
`cherry-pick` 側の変更は、動的記事取得機能とGoogle Drive関連の機能が追加されたことによる、環境変数検証の拡張です。`master` 側の `GEMINI_API_KEY` 検証は維持しつつ、`cherry-pick` 側で追加されたログ出力と検証ロジックを統合する必要があります。また、`self.folder_id` や `self.gemini_api_key` が `NewsProcessor` の `__init__` で適切に初期化されているか確認が必要です。

#### コンフリクト箇所2: `collect_articles` メソッドとスクレイピングロジック

このコンフリクトは、記事収集の主要ロジックで発生しています。`master` ブランチ側は `concurrent.futures.ThreadPoolExecutor` を使用した並列スクレイピングのフレームワークを保持しているのに対し、`cherry-pick` コミット側は動的記事取得の新しいメソッド (`get_dynamic_hours_limit`, `collect_articles_with_dynamic_range`, `_collect_articles_with_hours`) を導入し、`collect_articles` が新しい動的収集メソッドを呼び出すように変更されています。

```python
    def collect_articles(self) -> List[Dict[str, Any]]:
        """スクレイピングによる記事の収集"""
        log_with_context(self.logger, logging.INFO, "記事収集開始", operation="collect_articles")
        
<<<<<<< HEAD
        # 各スクレイパーを並列実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Reutersには hours_limit パラメータを明示的に追加
            reuters_params = self.config.reuters.to_dict()
            reuters_params['hours_limit'] = self.config.scraping.hours_limit
=======
    def get_dynamic_hours_limit(self) -> int:
        """
        曜日と記事数に基づく動的時間範囲決定
        
        Returns:
            int: 動的に決定された時間範囲（時間）
        """
        from datetime import datetime
        import pytz
        
        jst_tz = pytz.timezone('Asia/Tokyo')
        jst_now = datetime.now(jst_tz)
        weekday = jst_now.weekday()  # 月曜日=0, 日曜日=6
        
        # 月曜日は自動的に最大時間範囲を適用
        if weekday == 0:  # Monday
            self.logger.info(f"月曜日検出: 自動的に{self.config.scraping.max_hours_limit}時間範囲を適用")
            return self.config.scraping.max_hours_limit
        
        # 平日は基本時間範囲から開始
        return self.config.scraping.hours_limit
    
    def collect_articles_with_dynamic_range(self) -> List[Dict[str, Any]]:
        """
        動的時間範囲を使用した記事収集
        記事数が不足している場合は段階的に時間範囲を拡張
        """
        initial_hours = self.get_dynamic_hours_limit()
        current_hours = initial_hours
        
        self.logger.info(f"記事取得開始: 初期時間範囲 {current_hours} 時間")
        
        while current_hours <= self.config.scraping.max_hours_limit:
            articles = self._collect_articles_with_hours(current_hours)
            article_count = len(articles)
            
            self.logger.info(f"取得記事数: {article_count}件 (時間範囲: {current_hours}時間)")
            
            # 最低記事数を満たしているかチェック
            if article_count >= self.config.scraping.minimum_article_count:
                self.logger.info(f"最低記事数({self.config.scraping.minimum_article_count}件)を満たしました")
                return articles
            elif current_hours >= self.config.scraping.max_hours_limit:
                self.logger.warning(
                    f"最大時間範囲({self.config.scraping.max_hours_limit}時間)に到達しました。"\
                    f"記事数: {article_count}件 (目標: {self.config.scraping.minimum_article_count}件)"
                )
                return articles
            else:
                # 時間範囲を段階的に拡張
                next_hours = min(current_hours + 24, self.config.scraping.max_hours_limit)
                self.logger.info(
                    f"記事数不足のため時間範囲を拡張: {current_hours}時間 → {next_hours}時間"
                )
                current_hours = next_hours
        
        return articles

    def _collect_articles_with_hours(self, hours_limit: int) -> List[Dict[str, Any]]:
        """指定された時間範囲で記事を収集"""
        all_articles = []
        
        # ロイター記事収集
        try:
            reuters_articles = reuters.scrape_reuters_articles(
                query=self.config.reuters.query,\ 
                hours_limit=hours_limit,\ 
                max_pages=self.config.reuters.max_pages,\ 
                items_per_page=self.config.reuters.items_per_page,\ 
                target_categories=self.config.reuters.target_categories,\ 
                exclude_keywords=self.config.reuters.exclude_keywords
            )
            self.logger.info(f"取得したロイター記事数: {len(reuters_articles)}")\
            all_articles.extend(reuters_articles)\
        except Exception as e:\
            self.logger.error(f"ロイター記事取得エラー: {e}")\
        
        # ブルームバーグ記事収集\
        try:
            bloomberg_articles = bloomberg.scrape_bloomberg_top_page_articles(
                hours_limit=hours_limit,\ 
                exclude_keywords=self.config.bloomberg.exclude_keywords
            )
            self.logger.info(f"取得したBloomberg記事数: {len(bloomberg_articles)}")\
            all_articles.extend(bloomberg_articles)\
        except Exception as e:\
            self.logger.error(f"ブルームバーグ記事取得エラー: {e}")\
        
        # 公開日時でソート\
        return sorted(
            all_articles,
            key=lambda x: x.get("published_jst", datetime.min),
            reverse=True
        )
    
    def collect_articles(self) -> List[Dict[str, Any]]:
        """記事の収集（動的時間範囲対応）"""
        # 新しい動的収集メソッドを使用
        return self.collect_articles_with_dynamic_range()
    
    def remove_duplicate_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """記事の重複除去処理"""
        if not articles:
            return articles
        
        self.logger.info("記事の重複除去処理を開始")
        original_count = len(articles)
        
        # ContentDeduplicatorを使用して重複除去
        unique_articles = self.content_deduplicator.remove_duplicates(articles)
        
        unique_count = len(unique_articles)
        removed_count = original_count - unique_count
        
        self.logger.info(f"重複除去完了: 元記事数={original_count}, ユニーク記事数={unique_count}, 除去数={removed_count}")
        
        if removed_count > 0:
            self.logger.info(f"重複除去により {removed_count} 件の記事が除去されました")
>>>>>>> 62ce749 (feat: 動的記事取得システム実装による月曜日記事不足問題の解決)
            
            future_to_scraper = {
                executor.submit(reuters.scrape_reuters_articles, **reuters_params): "Reuters",
                executor.submit(bloomberg.scrape_bloomberg_top_page_articles, **self.config.bloomberg.to_dict()): "Bloomberg"
            }
            
            for future in concurrent.futures.as_completed(future_to_scraper):
                scraper_name = future_to_scraper[future]
                try:
                    articles = future.result()
                    log_with_context(self.logger, logging.INFO, f"{scraper_name} 記事取得完了", 
                                     operation="collect_articles", scraper=scraper_name, count=len(articles))
                    all_articles.extend(articles)
                except Exception as e:
                    log_with_context(self.logger, logging.ERROR, f"{scraper_name} 記事取得エラー",
                                     operation="collect_articles", scraper=scraper_name, error=str(e), exc_info=True)
        
        log_with_context(self.logger, logging.INFO, "記事収集完了", operation="collect_articles", total_count=len(all_articles))
        return all_articles
```

**解説:** 
このコンフリクトは非常に大きく、`collect_articles` メソッドの全体的な構造と、記事収集の具体的な実装が両ブランチで大きく異なっていることを示しています。

*   `master` 側は、`collect_articles` メソッド内で並列実行のフレームワーク (`ThreadPoolExecutor`) を使用し、スクレイパーへのパラメータ渡しを抽象化しています。
*   `cherry-pick` 側は、動的記事取得の新しいロジック（`get_dynamic_hours_limit`, `collect_articles_with_dynamic_range`, `_collect_articles_with_hours`）を導入し、`collect_articles` が新しい動的収集メソッドを呼び出すように変更されています。また、`_collect_articles_with_hours` 内でロイターとブルームバーグのスクレイパーを直接呼び出しています。

解決策としては、`cherry-pick` 側で導入された動的記事取得の新しいメソッド群をすべて取り込み、`master` 側の `collect_articles` メソッドを `cherry-pick` 側の `collect_articles` のように、新しい動的収集メソッドを呼び出す形に変更する必要があります。また、`_collect_articles_with_hours` 内のスクレイパー呼び出しと、`master` 側の並列実行フレームワークをどのように統合するかを検討する必要があります。

---

## 検討事項

このコンフリクトは、単なるコードの追加・削除ではなく、機能の設計思想が異なる部分で発生しています。

*   **`src/config/app_config.py` の `PodcastConfig`:**
    `master` 側の `__post_init__` は環境変数からの読み込みを担っています。`cherry-pick` 側は新しい設定項目と `load_pronunciation_dict` を追加しています。これらは統合可能ですが、`__post_init__` の役割をどうするか、`PodcastConfig` 内で環境変数を読み込むべきか、`AppConfig` の `__post_init__` で一元的に読み込むべきか、設計の検討が必要です。

*   **`src/core/news_processor.py` の `validate_environment`:**
    `master` 側はシンプルですが、`cherry-pick` 側はより詳細なログと検証を追加しています。これは統合すべきです。

*   **`src/core/news_processor.py` の `collect_articles` とスクレイピングロジック:**
    これが最も複雑なコンフリクトです。
    *   `cherry-pick` 側の動的記事取得ロジック (`get_dynamic_hours_limit`, `collect_articles_with_dynamic_range`, `_collect_articles_with_hours`) は、ユーザーが望む「記事取得件数拡張機能」の核心部分です。これは必ず取り込む必要があります。
    *   `master` 側の `collect_articles` 内の `ThreadPoolExecutor` を使った並列実行のフレームワークは、汎用的なスクレイピング処理には有用です。`_collect_articles_with_hours` 内でスクレイパーを直接呼び出すのではなく、この並列実行フレームワークを再利用できないか検討する価値があります。

### 解決方針の選択肢

1.  **手動で慎重に統合:**
    *   各コンフリクト箇所で、`master` 側の既存のロジックを尊重しつつ、`cherry-pick` 側で追加された動的記事取得機能のコードを慎重に組み込みます。
    *   特に `collect_articles` メソッド周辺は、新しい動的ロジックをメインとし、`master` 側の並列実行の考え方を `_collect_articles_with_hours` 内に適用するなど、コードの再構成が必要になるかもしれません。
    *   この方法は最も柔軟ですが、手作業が多く、バグを混入させるリスクがあります。

2.  **「記事取得件数拡張機能」の再実装:**
    *   `cherry-pick --abort` で現在の `cherry-pick` を中止し、`master` ブランチをクリーンな状態に戻します。
    *   `feature/dynamic-article-collection` ブランチのコードを参考に、`master` ブランチ上で「記事取得件数拡張機能」をゼロから実装し直します。
    *   この方法は、既存の `master` ブランチの構造に合わせた形で機能を組み込めるため、よりクリーンなコードになる可能性があります。ただし、実装の手間がかかります。

ユーザーの意図は「廃棄はありえない」とのことですので、どちらの選択肢も「記事取得件数拡張機能」を最終的に `master` に取り込むことを目指します。

---

このレポートをご確認いただき、どちらの解決方針で進めるかご指示ください。
作業は中断したままです。
