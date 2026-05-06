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
import os
from pathlib import Path

from src.config.app_config import get_config

# --- 設定の読み込み ---
config = get_config()
reuters_config = config.reuters
scraping_config = config.scraping

# ゼロ幅文字などの不可視文字を除去する正規表現
_INVISIBLE_CHARS = re.compile(r'[\u200b-\u200f\u00ad\u2060\ufeff\u2028\u2029\u180e]')

# 定型文フィルター（共通）
_BOILERPLATE_PATTERNS = [
    '信頼の原則',
    'Thomson Reuters',
    'トムソン・ロイター',
    '掲載の情報は',
    '© 2025 Reuters',
    '© 2026 Reuters',
]


def _build_chrome_options(user_data_dir: str) -> Options:
    """Reuters スクレイパー共通の Chrome オプションを生成する"""
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920x1080")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_argument("--blink-settings=imagesEnabled=false")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-plugins")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_argument("--disable-features=VizDisplayCompositor")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('prefs', {
        'profile.default_content_setting_values.notifications': 2,
        'profile.default_content_settings.popups': 0,
        'profile.managed_default_content_settings.images': 2,
    })
    opts.add_argument(f"--user-data-dir={user_data_dir}")
    return opts


def _extract_body_from_soup(soup: BeautifulSoup, article_url: str) -> str:
    """
    BeautifulSoup オブジェクトから記事本文を抽出する。
    Selenium・requests どちらの取得結果にも使える共通ロジック。
    """
    # --- コンテナ特定 ---
    # 優先度順: data-testid="ArticleBody" → class パターン → article タグ → main タグ
    body_container = None

    # 1. data-testid="ArticleBody" (現行の確実な構造)
    body_container = soup.find(attrs={"data-testid": "ArticleBody"})

    if not body_container:
        container_selectors = [
            ('div', re.compile(r'article-body-module__content__')),
            ('div', re.compile(r'article-body-module__container__')),
            ('div', re.compile(r'article-body__content__')),
            ('div', re.compile(r'article.*body|body.*content', re.I)),
            ('article', None),
            ('div', re.compile(r'story.*body|content.*body', re.I)),
            ('main', None),
        ]
        for tag, class_pattern in container_selectors:
            if class_pattern:
                container = soup.find(tag, class_=class_pattern)
            else:
                container = soup.find(tag)
            if container:
                body_container = container
                print(f"  [記事本文取得] 本文コンテナ発見: {tag}要素 ({class_pattern})")
                break

    if not body_container:
        print(f"  [記事本文取得] 本文コンテナが見つかりません: {article_url}")
        return ""

    # --- 段落抽出 ---
    paragraphs = []

    # 1. data-testid="paragraph-N" (現行の確実な構造)
    para_divs = body_container.find_all(
        'div', attrs={"data-testid": re.compile(r'^paragraph-\d+$')}
    )
    if para_divs:
        for elem in para_divs:
            text = _INVISIBLE_CHARS.sub('', elem.get_text(separator=' ', strip=True))
            if (len(text) > 20
                    and not any(bp in text for bp in _BOILERPLATE_PATTERNS)):
                paragraphs.append(text)
        if paragraphs:
            print(f"  [記事本文取得] 段落抽出成功 (data-testid=paragraph-N): {len(paragraphs)}個")

    # 2. クラスベースの段落
    if not paragraphs:
        paragraph_selectors = [
            ('p', re.compile(r'article-body-module__paragraph__')),
            ('p', re.compile(r'article-body-module__element__')),
            ('p', re.compile(r'text__text__')),
            ('p', None),
        ]
        for tag, class_or_test in paragraph_selectors:
            if class_or_test:
                elements = body_container.find_all(tag, class_=class_or_test)
            else:
                elements = body_container.find_all(tag)

            if elements:
                candidates = []
                for elem in elements:
                    text = _INVISIBLE_CHARS.sub('', elem.get_text(separator=' ', strip=True))
                    if (len(text) > 20
                            and not any(bp in text for bp in _BOILERPLATE_PATTERNS)):
                        candidates.append(text)
                if candidates:
                    paragraphs = candidates
                    print(f"  [記事本文取得] 段落抽出成功 ({tag}/{class_or_test}): {len(paragraphs)}個")
                    break

    # 3. 全テキストフォールバック
    if not paragraphs:
        print(f"  [記事本文取得] 段落が見つからないため全テキストを使用: {article_url}")
        full_text = body_container.get_text(separator='\n', strip=True)
        paragraphs = [
            _INVISIBLE_CHARS.sub('', line.strip())
            for line in full_text.split('\n')
            if line.strip() and len(line.strip()) > 10
            and not any(bp in line for bp in _BOILERPLATE_PATTERNS)
        ]

    article_text = '\n'.join(paragraphs)

    # 短すぎる場合は meta description にフォールバック
    if len(article_text.strip()) < 50:
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            fallback = _INVISIBLE_CHARS.sub('', meta_desc['content'].strip())
            if len(fallback) >= 50:
                print(f"  [記事本文取得] meta description から取得 (長さ: {len(fallback)}文字): {article_url}")
                return re.sub(r'\s+', ' ', fallback).strip()

    return re.sub(r'\s+', ' ', article_text).strip()


def scrape_reuters_article_body_with_selenium(
    driver: webdriver.Chrome,
    article_url: str,
    selenium_timeout: int = 20,
) -> str:
    """
    既存の Selenium driver を使って記事本文を取得する。
    401 対策として requests を使わず Selenium 経由でアクセスする。
    """
    max_retries = 1  # driver 共有なので過剰リトライは避ける
    for attempt in range(max_retries + 1):
        try:
            print(
                f"  [記事本文取得/Selenium] URL: {article_url} "
                f"(試行 {attempt + 1}/{max_retries + 1})"
            )
            driver.get(article_url)

            # ArticleBody が現れるまで待機（最大 selenium_timeout 秒）
            try:
                WebDriverWait(driver, selenium_timeout).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '[data-testid="ArticleBody"], [data-testid="Body"]')
                    )
                )
            except TimeoutException:
                # タイムアウトしても page_source は取得を試みる
                print(f"  [記事本文取得/Selenium] ArticleBody 待機タイムアウト: {article_url}")

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            body_text = _extract_body_from_soup(soup, article_url)

            if body_text:
                print(f"  [記事本文取得/Selenium] 成功 (長さ: {len(body_text)}文字): {article_url}")
                return body_text

            # 本文が取れなかった場合リトライ
            if attempt < max_retries:
                print(f"  [記事本文取得/Selenium] 本文なし、リトライします...")
                time.sleep(2)
                continue

        except Exception as e:
            print(f"  [記事本文取得/Selenium] エラー ({article_url}): {e}")
            if attempt < max_retries:
                time.sleep(2)
                continue

    print(f"  [記事本文取得失敗] 全試行失敗: {article_url}")
    return ""


def scrape_reuters_articles(query: str, hours_limit: int, max_pages: int,
                            items_per_page: int, target_categories: list,
                            exclude_keywords: list) -> list:
    """ロイターのサイト内検索を利用して記事情報を収集する"""

    base_search_url = "https://jp.reuters.com/site-search/"

    # Chrome プロファイルを一時ディレクトリに作成（他インスタンスとの衝突を防ぐ）
    user_data_dir = tempfile.mkdtemp(prefix="chrome-reuters-", dir=str(Path.cwd()))
    chrome_options = _build_chrome_options(user_data_dir)
    # 記事一覧ページと本文ページの両方を同一 driver で扱うため
    # remote-debugging-port は衝突回避のためポートを固定しない
    chrome_options.add_argument("--remote-debugging-port=0")

    driver = None
    print("\n--- ロイター記事のスクレイピング開始 ---")

    articles_to_process = []
    processed_urls = set()

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(scraping_config.page_load_timeout)
        driver.implicitly_wait(scraping_config.implicit_wait)

        jst = pytz.timezone('Asia/Tokyo')
        time_threshold_jst = datetime.now(jst) - timedelta(hours=hours_limit)

        # ────────────────────────────────────────────
        # Step 1: 記事一覧をスクレイピング
        # ────────────────────────────────────────────
        for page_num in range(max_pages):
            offset = page_num * items_per_page
            search_url = (
                f"{base_search_url}"
                f"?query={requests.utils.quote(query)}&offset={offset}"
            )
            print(f"  ロイター: ページ {page_num + 1}/{max_pages} を処理中 ({search_url})...")

            page_loaded = False
            for attempt in range(scraping_config.selenium_max_retries):
                try:
                    current_timeout = 30 if attempt == 0 else 50
                    wait_with_timeout = WebDriverWait(driver, current_timeout)
                    driver.get(search_url)
                    wait_with_timeout.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, 'li[data-testid="StoryCard"]')
                        )
                    )
                    page_loaded = True
                    break
                except TimeoutException:
                    print(
                        f"    [!] ページ読み込みタイムアウト "
                        f"({current_timeout}秒, {attempt + 1}/{scraping_config.selenium_max_retries})。"
                        f"リトライします..."
                    )
                    if attempt + 1 == scraping_config.selenium_max_retries:
                        print(
                            f"    [!] リトライ上限に達したため、"
                            f"このページ ({search_url}) をスキップします。"
                        )

            if not page_loaded:
                continue

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            articles_on_page = soup.find_all('li', attrs={"data-testid": "StoryCard"})

            print(f"    - ページで見つかった記事候補: {len(articles_on_page)}件")

            if not articles_on_page:
                if page_num == 0:
                    print("    [!] 最初のページで記事が見つかりませんでした。サイト構造が変更された可能性があります。")
                    fallback_articles = soup.find_all(
                        'li', class_=lambda x: x and 'search-result' in x.lower()
                    )
                    print(f"    [デバッグ] フォールバック検索結果: {len(fallback_articles)}件")
                else:
                    print(f"    - ページ{page_num + 1}で記事が見つからなかったため処理を終了します。")
                break

            articles_found_on_page = 0
            for article_li in articles_on_page:
                link_element = article_li.find('a', attrs={"data-testid": "TitleLink"})
                if not link_element:
                    print("    [デバッグ] リンク要素が見つからない記事をスキップ")
                    continue

                article_url = link_element.get('href', '')
                if not article_url.startswith('http'):
                    article_url = "https://jp.reuters.com" + article_url

                if article_url in processed_urls:
                    print(f"    [デバッグ] 重複URL をスキップ: {article_url}")
                    continue
                processed_urls.add(article_url)

                title = link_element.get_text(strip=True) or "タイトル不明"
                print(f"    > 記事候補発見: {title}")
                articles_found_on_page += 1

                time_element = article_li.find('time', attrs={"data-testid": "DateLineText"})
                try:
                    dt_utc = datetime.fromisoformat(
                        time_element.get('datetime').replace('Z', '+00:00')
                    )
                    article_time_jst = dt_utc.astimezone(jst)
                except (ValueError, AttributeError):
                    print(f"    [デバッグ] 時刻解析失敗のためスキップ: {title}")
                    continue

                if article_time_jst < time_threshold_jst:
                    print(f"    [デバッグ] 時間制限外のためスキップ: {title} ({article_time_jst})")
                    continue

                title_text = link_element.get_text(strip=True)
                if any(kw.lower() in title_text.lower() for kw in exclude_keywords):
                    print(f"    [デバッグ] 除外キーワードでスキップ: {title_text}")
                    continue

                kicker = article_li.find('span', attrs={"data-testid": "KickerLabel"})
                category_text = (
                    kicker.get_text(strip=True).replace(" category", "")
                    if kicker else "不明"
                )

                if target_categories and category_text not in target_categories:
                    print(f"    [デバッグ] カテゴリ対象外でスキップ: {title_text} (カテゴリ: {category_text})")
                    continue

                print(f"    > 記事発見: {title_text}")
                articles_to_process.append({
                    'source': 'Reuters',
                    'title': title_text,
                    'url': article_url,
                    'published_jst': article_time_jst,
                    'category': category_text,
                })

            print(
                f"    - ページ{page_num + 1}の処理完了: "
                f"候補{articles_found_on_page}件中、条件に合致した記事数を追加"
            )

            if len(articles_on_page) < items_per_page:
                print("    [i] 記事がページあたりのアイテム数より少ないため、最終ページと判断し終了します。")
                break

            time.sleep(1)

        if not articles_to_process:
            print("--- ロイター: 処理対象の記事が見つかりませんでした ---")
            return []

        # ────────────────────────────────────────────
        # Step 2: 同一 driver で記事本文を順次取得
        #         （401 対策: requests を使わず Selenium 経由）
        # ────────────────────────────────────────────
        print(
            f"\n--- {len(articles_to_process)}件の記事本文を Selenium で順次取得開始 ---"
        )

        final_articles_data = []
        for i, article in enumerate(articles_to_process):
            try:
                body = scrape_reuters_article_body_with_selenium(
                    driver, article['url'],
                    selenium_timeout=scraping_config.selenium_timeout,
                )
                article['body'] = body if body else "[本文取得失敗/空]"
                final_articles_data.append(article)
                print(f"  ({i + 1}/{len(articles_to_process)}) 完了: {article['title']}")
            except Exception as exc:
                print(f"  [!!] 記事取得中に例外発生 ({article['url']}): {exc}")
                article['body'] = f"[本文取得エラー: {exc}]"
                final_articles_data.append(article)

    except Exception as e:
        print(f"  ロイタースクレイピングのブラウザ操作中に予期せぬエラーが発生しました: {e}")
    finally:
        if driver:
            driver.quit()
        # 一時プロファイルディレクトリを削除
        try:
            import shutil
            shutil.rmtree(user_data_dir, ignore_errors=True)
        except Exception:
            pass

    print(f"--- ロイター記事取得完了: {len(final_articles_data)} 件 ---")
    return final_articles_data
