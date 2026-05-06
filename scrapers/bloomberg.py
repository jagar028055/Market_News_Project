# -*- coding: utf-8 -*-

import time
import re
import pytz
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import tempfile
from pathlib import Path
import shutil

from src.config.app_config import get_config

# --- 設定の読み込み ---
config = get_config()
scraping_config = config.scraping

# Bloomberg は bloomberg.co.jp → bloomberg.com/jp にリダイレクトされるが
# Selenium でアクセスすると bloomberg.co.jp のまま記事一覧が取得できる
_BLOOMBERG_BASE = "https://www.bloomberg.co.jp"

# 記事 URL として認める正規表現（bloomberg.co.jp / bloomberg.com 両方）
_ARTICLE_URL_RE = re.compile(
    r'https?://(?:www\.bloomberg\.co\.jp|www\.bloomberg\.com)/(?:news/articles|news/videos|markets|technology|business|finance|economics)',
    re.I,
)


def scrape_bloomberg_article_body(article_url: str, timeout: int = 15) -> str:
    """指定された Bloomberg 記事 URL から本文を抽出する (requests ベース)"""
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Referer': 'https://www.bloomberg.co.jp/',
    }

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            current_timeout = timeout if attempt == 0 else timeout + 10
            print(
                f"  [Bloomberg本文取得] URL: {article_url} "
                f"(試行 {attempt + 1}/{max_retries + 1}, タイムアウト: {current_timeout}秒)"
            )

            response = requests.get(article_url, headers=headers, timeout=current_timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding

            soup = BeautifulSoup(response.content, 'html.parser')

            # 本文コンテナを複数パターンで探索
            body_container = None
            container_candidates = [
                soup.find('div', class_=re.compile(r'body-copy|article-body|content-well', re.I)),
                soup.find('article'),
                soup.find('main'),
                soup.find('div', class_=re.compile(r'story.*content|content.*story', re.I)),
            ]
            for candidate in container_candidates:
                if candidate:
                    body_container = candidate
                    break

            if not body_container:
                print(f"  [Bloomberg本文取得] 本文コンテナが見つかりません: {article_url}")
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return ""

            # 不要タグを除去
            for unwanted in body_container.find_all(
                ['script', 'style', 'aside', 'figure', 'figcaption', 'iframe', 'header', 'footer', 'nav']
            ):
                unwanted.decompose()

            paragraphs = [
                p.get_text(separator=' ', strip=True)
                for p in body_container.find_all('p')
                if p.get_text(strip=True)
            ]

            if not paragraphs:
                full_text = body_container.get_text(separator='\n', strip=True)
                paragraphs = [l.strip() for l in full_text.split('\n') if l.strip()]

            article_text = '\n'.join(paragraphs)
            if len(article_text.strip()) < 50:
                print(f"  [Bloomberg本文取得] 本文が短すぎます (長さ: {len(article_text)}文字): {article_url}")
                if attempt < max_retries:
                    time.sleep(2)
                    continue
            else:
                print(f"  [Bloomberg本文取得] 成功 (長さ: {len(article_text)}文字): {article_url}")

            return re.sub(r'\s+', ' ', article_text).strip()

        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            print(f"  [Bloomberg本文取得エラー] {article_url} (試行 {attempt + 1}): {e}")
            if attempt < max_retries:
                time.sleep(2)
                continue
        except Exception as e:
            print(f"  [Bloomberg本文取得エラー] 解析中に予期せぬエラー: {e}")
            if attempt < max_retries:
                time.sleep(2)
                continue

    print(f"  [Bloomberg本文取得失敗] 全試行失敗: {article_url}")
    return ""


def scrape_bloomberg_top_page_articles(hours_limit: int, exclude_keywords: list) -> list:
    """Bloomberg トップページから記事情報を収集する (Selenium ベース)"""

    user_data_dir = tempfile.mkdtemp(prefix="chrome-bloomberg-", dir=str(Path.cwd()))

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--remote-debugging-port=0")
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('prefs', {
        'profile.default_content_setting_values.notifications': 2,
        'profile.default_content_settings.popups': 0,
        'profile.managed_default_content_settings.images': 2,
    })
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    driver = None
    print("\n--- Bloomberg記事のスクレイピング開始 ---")

    articles_to_process = []
    processed_urls = set()

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(scraping_config.page_load_timeout)

        print(f"  Bloomberg: トップページ ({_BLOOMBERG_BASE}) を取得中...")

        # ── 待機戦略 ──────────────────────────────────────────────────────────
        # 旧コード: 'article[class*="story"], article[class*="module"]' を待機
        #   → Bloomberg はそのクラスを持つ article タグを JS 描画しないため
        #     常にタイムアウトしていた
        #
        # 新コード:
        #   1. まず body タグ出現を待機（ページ自体の読み込み完了を確認）
        #   2. さらに <a href> を含む要素が現れるまで短時間待機
        #   3. JS 描画を待つため追加スリープ
        # ─────────────────────────────────────────────────────────────────────
        page_loaded = False
        for attempt in range(scraping_config.selenium_max_retries):
            try:
                current_timeout = 30 if attempt == 0 else 50
                driver.get(_BLOOMBERG_BASE)

                # body タグの出現を待つ（最低限のページロード確認）
                WebDriverWait(driver, current_timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                # JS 描画のための追加待機
                time.sleep(3)
                page_loaded = True
                break

            except TimeoutException:
                print(
                    f"    [!] ページ読み込みタイムアウト "
                    f"({current_timeout}秒, {attempt + 1}/{scraping_config.selenium_max_retries})。"
                    f"リトライします..."
                )
                if attempt + 1 == scraping_config.selenium_max_retries:
                    print("    [!] リトライ上限に達したため、Bloombergのスクレイピングを中止します。")
                    return []

        if not page_loaded:
            return []

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # ── 記事要素の抽出 ────────────────────────────────────────────────────
        # 優先度順にセレクターを試行:
        #   1. <article> タグ（任意クラス）
        #   2. クラスに "story" または "module" を含む任意タグ
        #   3. ニュースリンク (<a href="/news/..."> ) を直接収集
        # ─────────────────────────────────────────────────────────────────────

        article_elements = soup.find_all('article')

        if not article_elements:
            # クラスに story / module を含むブロック要素
            article_elements = soup.find_all(
                True,
                class_=re.compile(r'\bstory\b|\bmodule\b', re.I)
            )

        jst = pytz.timezone('Asia/Tokyo')
        now_jst = datetime.now(jst)
        time_threshold_jst = now_jst - timedelta(hours=hours_limit)

        if article_elements:
            print(f"    - トップページで記事候補: {len(article_elements)} 件発見。")
            _extract_from_article_elements(
                article_elements, processed_urls, articles_to_process,
                now_jst, time_threshold_jst, exclude_keywords,
            )

        # article 要素から記事が取れなかった場合はリンク直接収集にフォールバック
        if not articles_to_process:
            print("    [フォールバック] article 要素が空のため、ニュースリンクを直接収集します。")
            _extract_from_news_links(
                soup, processed_urls, articles_to_process,
                now_jst, time_threshold_jst, exclude_keywords,
            )

        if not articles_to_process:
            print("--- Bloomberg: 処理対象の記事が見つかりませんでした ---")
            # デバッグ情報
            all_links = soup.find_all('a', href=True)
            print(f"    [デバッグ] ページ内の全 <a> タグ数: {len(all_links)}")
            sample = [l['href'] for l in all_links if l['href'].startswith('/')][:10]
            print(f"    [デバッグ] href サンプル: {sample}")
            return []

    except Exception as e:
        print(f"  Bloomberg スクレイピング処理全体でエラーが発生しました: {e}")
    finally:
        if driver:
            driver.quit()
        try:
            shutil.rmtree(user_data_dir, ignore_errors=True)
        except Exception:
            pass

    if not articles_to_process:
        return []

    print(
        f"\n--- {len(articles_to_process)}件の記事本文を並列取得開始 "
        f"(最大{config.bloomberg.num_parallel_requests}スレッド) ---"
    )
    final_articles_data = []
    with ThreadPoolExecutor(max_workers=config.bloomberg.num_parallel_requests) as executor:
        future_to_article = {
            executor.submit(scrape_bloomberg_article_body, article['url']): article
            for article in articles_to_process
        }
        for i, future in enumerate(as_completed(future_to_article)):
            article = future_to_article[future]
            try:
                body = future.result()
                article['body'] = body or "[本文取得失敗/空]"
                final_articles_data.append(article)
                print(f"  ({i + 1}/{len(articles_to_process)}) 完了: {article['title']}")
            except Exception as exc:
                print(f"  [!!] 記事取得中に例外発生 ({article['url']}): {exc}")
                article['body'] = f"[本文取得エラー: {exc}]"
                final_articles_data.append(article)

    print(f"--- Bloomberg記事取得完了: {len(final_articles_data)} 件 ---")
    return final_articles_data


def _extract_from_article_elements(
    article_elements, processed_urls, articles_to_process,
    now_jst, time_threshold_jst, exclude_keywords,
):
    """<article> / クラス要素から記事情報を抽出する"""
    for article_element in article_elements:
        link_el = article_element.find('a', href=True)
        if not link_el:
            continue

        raw_url = link_el['href']
        article_url = (
            _BLOOMBERG_BASE + raw_url if raw_url.startswith('/') else raw_url
        )
        article_url = article_url.split('?')[0].split('#')[0]

        if not article_url.startswith('http') or article_url in processed_urls:
            continue
        processed_urls.add(article_url)

        time_tag = article_element.find('time', datetime=True)
        article_time_jst = now_jst
        if time_tag and time_tag.has_attr('datetime'):
            try:
                dt_utc = datetime.fromisoformat(
                    time_tag['datetime'].replace('Z', '+00:00')
                )
                article_time_jst = dt_utc.astimezone(now_jst.tzinfo)
            except ValueError:
                pass

        if article_time_jst < time_threshold_jst:
            continue

        title_el = (
            article_element.find(['h1', 'h2', 'h3'], True)
            or article_element.find('a', class_=re.compile(r'title|headline', re.I))
            or link_el
        )
        title = title_el.get_text(strip=True)
        if not title or any(kw.lower() in title.lower() for kw in exclude_keywords):
            continue

        print(f"    > 記事発見: {title}")
        articles_to_process.append({
            'source': 'Bloomberg',
            'title': title,
            'url': article_url,
            'published_jst': article_time_jst,
            'category': 'Bloomberg Top',
        })


def _extract_from_news_links(
    soup, processed_urls, articles_to_process,
    now_jst, time_threshold_jst, exclude_keywords,
):
    """
    <a href="/news/..."> を直接収集するフォールバック。
    article 要素が JS 描画されていない場合に使用。
    """
    news_links = soup.find_all(
        'a',
        href=re.compile(r'^/(?:news/articles|news/videos|markets|technology|business|economics)/', re.I),
    )
    print(f"    [フォールバック] ニュースリンク候補: {len(news_links)} 件")

    for link_el in news_links:
        raw_url = link_el['href']
        article_url = _BLOOMBERG_BASE + raw_url if raw_url.startswith('/') else raw_url
        article_url = article_url.split('?')[0].split('#')[0]

        if article_url in processed_urls:
            continue
        processed_urls.add(article_url)

        title = link_el.get_text(strip=True)
        if not title or len(title) < 10:
            continue
        if any(kw.lower() in title.lower() for kw in exclude_keywords):
            continue

        # リンク収集フォールバックでは時刻情報が取れないため現在時刻を使用
        print(f"    > 記事発見 [FB]: {title}")
        articles_to_process.append({
            'source': 'Bloomberg',
            'title': title,
            'url': article_url,
            'published_jst': now_jst,
            'category': 'Bloomberg Top',
        })
