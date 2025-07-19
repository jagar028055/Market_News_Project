# GitHub Actions 信頼性向上計画

## 問題点

GitHub Actionsのワークフローにおいて、ロイターのスクレイピング処理中にSeleniumのタイムアウトエラーが頻発している。

- **エラーログ**: `HTTPConnectionPool(host='localhost', ...): Read timed out.`
- **原因**: GitHub Actionsの共有ランナー環境ではリソースが限られており、現在のSeleniumタイムアウト設定（30秒）では、ページの読み込みが完了する前にタイムアウトが発生している。

## 対策案

以下の変更を実施し、処理の安定性を向上させる。

### 1. Seleniumのタイムアウト時間を延長

- **ファイル**: `src/config/app_config.py`
- **変更内容**: `ScrapingConfig` クラス内の `selenium_timeout` の値を `30` から `120` に変更する。
- **目的**: ページの読み込みに十分な時間を確保し、タイムアウトエラーを防ぐ。

```python
@dataclass
class ScrapingConfig:
    """スクレイピング設定"""
    hours_limit: int = 24
    sentiment_analysis_enabled: bool = True
    selenium_timeout: int = 120  # 30秒から延長
    selenium_max_retries: int = 3
```

### 2. 不要なリソース（画像）の読み込みを無効化

- **ファイル**: `scrapers/reuters.py`
- **変更内容**: `scrape_reuters_articles` 関数内のChromeオプションに、画像の読み込みを無効にする設定を追加する。
- **目的**: ページの読み込みを高速化し、データ転送量を削減することで、タイムアウトのリスクをさらに低減する。

```python
def scrape_reuters_articles(...):
    # ...
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument('user-agent=...')
    # ↓ この行を追加
    chrome_options.add_argument("--blink-settings=imagesEnabled=false") 
    # ...
