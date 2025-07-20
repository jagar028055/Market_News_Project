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

from src.config.app_config import get_config

# --- 設定の読み込み ---
config = get_config()
reuters_config = config.reuters
scraping_config = config.scraping

def scrape_reuters_article_body(article_url: str, timeout: int = 15) -> str:
    """指定されたロイター記事URLから本文を抽出する"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}
        response = requests.get(article_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.content, 'html.parser')
        
        body_container = soup.find('div', class_=re.compile(r'article-body__content__'))
        if not body_container:
            return ""
            
        paragraphs = [p.get_text(separator=' ', strip=True) for p in body_container.find_all('p', class_=re.compile(r'text__text__'))]
        if not paragraphs:
             # 'p' タグが見つからない場合のフォールバック
            paragraphs = [p_div.get_text(separator=' ', strip=True) for p_div in body_container.find_all('div', attrs={"data-testid": lambda x: x and x.startswith('paragraph-')})]

        article_text = '\n'.join(paragraphs)
        return re.sub(r'\s+', ' ', article_text).strip()

    except requests.exceptions.RequestException as e:
        print(f"  [本文取得エラー] ロイター記事 ({article_url}) の取得に失敗: {e}")
        return ""
    except Exception as e:
        print(f"  [本文取得エラー] ロイター記事 ({article_url}) の解析中に予期せぬエラー: {e}")
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
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36')
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")

    driver = None
    print("\n--- ロイター記事のスクレイピング開始 ---")
    
    articles_to_process = []
    processed_urls = set()

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(scraping_config.selenium_timeout)
        wait = WebDriverWait(driver, scraping_config.selenium_timeout)
        
        jst = pytz.timezone('Asia/Tokyo')
        time_threshold_jst = datetime.now(jst) - timedelta(hours=hours_limit)

        for page_num in range(max_pages):
            offset = page_num * items_per_page
            search_url = f"{base_search_url}?query={requests.utils.quote(query)}&offset={offset}"
            print(f"  ロイター: ページ {page_num + 1}/{max_pages} を処理中 ({search_url})...")

            for attempt in range(scraping_config.selenium_max_retries):
                try:
                    # 段階的タイムアウト: 初回25秒、リトライ時45秒
                    current_timeout = 25 if attempt == 0 else 45
                    wait_with_timeout = WebDriverWait(driver, current_timeout)
                    
                    driver.get(search_url)
                    # 記事リストコンテナが読み込まれるまで待機
                    wait_with_timeout.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'ul[class*="search-results__list__"]')))
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

