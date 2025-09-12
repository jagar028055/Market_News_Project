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

def scrape_reuters_article_body(article_url: str, timeout: int = 15) -> str:
    """指定されたロイター記事URLから本文を抽出する"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none'
    }
    
    # リトライ機能付きで記事本文を取得
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            # リトライ時はタイムアウトを延長
            current_timeout = timeout if attempt == 0 else timeout + 10
            print(f"  [記事本文取得] URL: {article_url} を処理中... (試行 {attempt + 1}/{max_retries + 1}, タイムアウト: {current_timeout}秒)")
            
            response = requests.get(article_url, headers=headers, timeout=current_timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 複数の本文コンテナパターンを試行
            body_container = None
            container_selectors = [
                ('div', re.compile(r'article-body-module__content__')),  # 最新の構造
                ('div', re.compile(r'article-body-module__container__')),  # コンテナ
                ('div', re.compile(r'article-body__content__')),  # 元の
                ('div', re.compile(r'article.*body|body.*content', re.I)),  # 汎用
                ('article', None),  # article要素全体
                ('div', re.compile(r'story.*body|content.*body', re.I)),  # ストーリー本文
                ('main', None),  # main要素
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
                print(f"  [記事本文取得] 全ての本文コンテナパターンで検索失敗: {article_url}")
                if attempt < max_retries:
                    print(f"  [記事本文取得] リトライします...")
                    time.sleep(2)
                    continue
                return ""
                
            # 複数の段落抽出パターンを試行
            paragraphs = []
            paragraph_selectors = [
                ('div', 'data-testid-paragraph'),  # 最新構造: data-testid="paragraph-X"
                ('p', re.compile(r'article-body-module__element__')),  # 新しい構造
                ('p', re.compile(r'text__text__')),  # 元の
                ('p', None),  # 全てのp要素
                ('div', lambda x: x and x.startswith('paragraph-') if isinstance(x, str) else False),  # data-testid
                ('div', re.compile(r'paragraph|content.*text', re.I)),  # 段落div
            ]
            
            for tag, class_or_test in paragraph_selectors:
                if class_or_test == 'data-testid-paragraph':  # 最新構造
                    # data-testid="paragraph-X" パターンの要素を取得
                    elements = body_container.find_all('div', attrs={"data-testid": re.compile(r'^paragraph-\d+$')})
                elif callable(class_or_test):  # data-testid用
                    elements = body_container.find_all('div', attrs={"data-testid": class_or_test})
                elif class_or_test:  # class pattern
                    elements = body_container.find_all(tag, class_=class_or_test)
                else:  # 全て
                    elements = body_container.find_all(tag)
                    
                if elements:
                    # 定型文をフィルタリングして段落抽出
                    paragraphs = []
                    for elem in elements:
                        text = elem.get_text(separator=' ', strip=True)
                        # 定型文を除外
                        if (text and len(text) > 20 and 
                            '信頼の原則' not in text and 
                            'Thomson Reuters' not in text and
                            'トムソン・ロイター' not in text and
                            '掲載の情報は' not in text and
                            '© 2025 Reuters' not in text):
                            paragraphs.append(text)
                    
                    if paragraphs:
                        print(f"  [記事本文取得] 段落抽出成功: {tag}要素 {len(paragraphs)}個")
                        break
                        
            if not paragraphs:
                print(f"  [記事本文取得] 段落が見つからないため、全テキストを取得: {article_url}")
                full_text = body_container.get_text(separator='\n', strip=True)
                paragraphs = [line.strip() for line in full_text.split('\n') if line.strip() and len(line.strip()) > 10]

            article_text = '\n'.join(paragraphs)
            if len(article_text.strip()) < 50:
                print(f"  [記事本文取得] 取得した本文が短すぎます (長さ: {len(article_text)}文字): {article_url}")
                # meta descriptionからフォールバック取得を試行
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    fallback_text = meta_desc['content'].strip()
                    if len(fallback_text) >= 50:
                        print(f"  [記事本文取得] meta descriptionから取得成功 (長さ: {len(fallback_text)}文字): {article_url}")
                        return re.sub(r'\s+', ' ', fallback_text).strip()
                
                if attempt < max_retries:
                    print(f"  [記事本文取得] リトライします...")
                    time.sleep(2)
                    continue
            else:
                print(f"  [記事本文取得] 本文取得成功 (長さ: {len(article_text)}文字): {article_url}")
            
            return re.sub(r'\s+', ' ', article_text).strip()
            
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            print(f"  [本文取得エラー] ロイター記事 ({article_url}) の取得に失敗 (試行 {attempt + 1}): {e}")
            if attempt < max_retries:
                print(f"  [記事本文取得] {2}秒後にリトライします...")
                time.sleep(2)
                continue
        except Exception as e:
            print(f"  [本文取得エラー] ロイター記事 ({article_url}) の解析中に予期せぬエラー: {e}")
            if attempt < max_retries:
                print(f"  [記事本文取得] リトライします...")
                time.sleep(2)
                continue
    
    # 全ての試行が失敗した場合
    print(f"  [本文取得失敗] 全ての試行が失敗しました: {article_url}")
    return ""

def scrape_reuters_articles(query: str, hours_limit: int, max_pages: int,
                            items_per_page: int, target_categories: list,
                            exclude_keywords: list) -> list:
    """ロイターのサイト内検索を利用して記事情報を収集する"""
    
    base_search_url = "https://jp.reuters.com/site-search/"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36')
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('prefs', {
        'profile.default_content_setting_values.notifications': 2,
        'profile.default_content_settings.popups': 0,
        'profile.managed_default_content_settings.images': 2
    })
    # ユーザーディレクトリ衝突対策（ワークスペース内に一時プロファイルを作成）
    user_data_dir = tempfile.mkdtemp(prefix="chrome-profile-", dir=str(Path.cwd()))
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    driver = None
    print("\n--- ロイター記事のスクレイピング開始 ---")
    
    articles_to_process = []
    processed_urls = set()

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(scraping_config.page_load_timeout)
        driver.implicitly_wait(scraping_config.implicit_wait)
        wait = WebDriverWait(driver, scraping_config.selenium_timeout)
        
        jst = pytz.timezone('Asia/Tokyo')
        time_threshold_jst = datetime.now(jst) - timedelta(hours=hours_limit)

        for page_num in range(max_pages):
            offset = page_num * items_per_page
            search_url = f"{base_search_url}?query={requests.utils.quote(query)}&offset={offset}"
            print(f"  ロイター: ページ {page_num + 1}/{max_pages} を処理中 ({search_url})...")

            for attempt in range(scraping_config.selenium_max_retries):
                try:
                    # 段階的タイムアウト: 初回30秒、リトライ時50秒
                    current_timeout = 30 if attempt == 0 else 50
                    wait_with_timeout = WebDriverWait(driver, current_timeout)
                    
                    driver.get(search_url)
                    # 記事要素が読み込まれるまで待機
                    wait_with_timeout.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'li[data-testid="StoryCard"]')))
                    break 
                except TimeoutException:
                    print(f"    [!] ページ読み込みタイムアウト ({current_timeout}秒, {attempt + 1}/{scraping_config.selenium_max_retries})。リトライします...")
                    if attempt + 1 == scraping_config.selenium_max_retries:
                        print(f"    [!] リトライ上限に達したため、このページ ({search_url}) をスキップします。")
                        # continue to the next page_num
                        break  
            else: # for-else: break しなかった場合 (リトライ全部失敗)
                continue

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            articles_on_page = soup.find_all('li', attrs={"data-testid": "StoryCard"})
            
            print(f"    - ページで見つかった記事候補: {len(articles_on_page)}件")
            
            if not articles_on_page:
                if page_num == 0:
                    print("    [!] 最初のページで記事が見つかりませんでした。サイト構造が変更された可能性があります。")
                    # デバッグ用: 他の可能性のあるセレクターを試す
                    fallback_articles = soup.find_all('li', class_=lambda x: x and 'search-result' in x.lower())
                    print(f"    [デバッグ] フォールバック検索結果: {len(fallback_articles)}件")
                else:
                    print(f"    - ページ{page_num + 1}で記事が見つからなかったため処理を終了します。")
                break

            articles_found_on_page = 0
            for article_li in articles_on_page:
                link_element = article_li.find('a', attrs={"data-testid": "TitleLink"})
                if not link_element: 
                    print(f"    [デバッグ] リンク要素が見つからない記事をスキップ")
                    continue

                article_url = link_element.get('href', '')
                if not article_url.startswith('http'):
                    article_url = "https://jp.reuters.com" + article_url
                
                if article_url in processed_urls: 
                    print(f"    [デバッグ] 重複URL をスキップ: {article_url}")
                    continue
                processed_urls.add(article_url)
                
                # タイトルを取得してログ出力
                title = link_element.get_text(strip=True) if link_element else "タイトル不明"
                print(f"    > 記事候補発見: {title}")
                articles_found_on_page += 1

                time_element = article_li.find('time', attrs={"data-testid": "DateLineText"})
                try:
                    dt_utc = datetime.fromisoformat(time_element.get('datetime').replace('Z', '+00:00'))
                    article_time_jst = dt_utc.astimezone(jst)
                except (ValueError, AttributeError):
                    print(f"    [デバッグ] 時刻解析失敗のためスキップ: {title}")
                    continue

                if article_time_jst < time_threshold_jst: 
                    print(f"    [デバッグ] 時間制限外のためスキップ: {title} ({article_time_jst})")
                    continue

                title_text = link_element.get_text(strip=True)
                if any(keyword.lower() in title_text.lower() for keyword in exclude_keywords): 
                    print(f"    [デバッグ] 除外キーワードでスキップ: {title_text}")
                    continue

                kicker = article_li.find('span', attrs={"data-testid": "KickerLabel"})
                category_text = kicker.get_text(strip=True).replace(" category", "") if kicker else "不明"
                
                if target_categories and category_text not in target_categories: 
                    print(f"    [デバッグ] カテゴリ対象外でスキップ: {title_text} (カテゴリ: {category_text})")
                    continue

                print(f"    > 記事発見: {title_text}")
                articles_to_process.append({
                    'source': 'Reuters', 'title': title_text, 'url': article_url,
                    'published_jst': article_time_jst, 'category': category_text
                })

            print(f"    - ページ{page_num + 1}の処理完了: 候補{articles_found_on_page}件中、条件に合致した記事数を追加")
            
            if len(articles_on_page) < items_per_page:
                print("    [i] 記事がページあたりのアイテム数より少ないため、最終ページと判断し終了します。")
                break
            
            time.sleep(1) # サーバー負荷軽減のための短い待機

    except Exception as e:
        print(f"  ロイタースクレイピングのブラウザ操作中に予期せぬエラーが発生しました: {e}")
    finally:
        if driver:
            driver.quit()

    if not articles_to_process:
        print("--- ロイター: 処理対象の記事が見つかりませんでした ---")
        return []

    print(f"\n--- {len(articles_to_process)}件の記事本文を並列取得開始 (最大{reuters_config.num_parallel_requests}スレッド) ---")
    
    final_articles_data = []
    with ThreadPoolExecutor(max_workers=reuters_config.num_parallel_requests) as executor:
        future_to_article = {executor.submit(scrape_reuters_article_body, article['url']): article for article in articles_to_process}
        
        for i, future in enumerate(as_completed(future_to_article)):
            article = future_to_article[future]
            try:
                body = future.result()
                if body:
                    article['body'] = body
                    final_articles_data.append(article)
                else:
                    article['body'] = "[本文取得失敗/空]"
                    final_articles_data.append(article) # 本文がなくても追加
                print(f"  ({i+1}/{len(articles_to_process)}) 完了: {article['title']}")
            except Exception as exc:
                print(f"  [!!] 記事取得中に例外発生 ({article['url']}): {exc}")
                article['body'] = f"[本文取得エラー: {exc}]"
                final_articles_data.append(article)

    print(f"--- ロイター記事取得完了: {len(final_articles_data)} 件 ---")
    return final_articles_data
