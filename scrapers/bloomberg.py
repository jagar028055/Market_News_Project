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
scraping_config = config.scraping

def scrape_bloomberg_article_body(article_url: str, timeout: int = 15) -> str:
    """指定されたBloomberg記事URLから本文を抽出する"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}
        response = requests.get(article_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.content, 'html.parser')
        
        body_container = soup.find('div', class_=re.compile(r'(body-copy|article-body|content-well)'))
        if not body_container:
            article_tag = soup.find('article')
            if not article_tag: return ""
            for unwanted_tag in article_tag.find_all(['script', 'style', 'aside', 'figure', 'figcaption', 'iframe', 'header', 'footer', 'nav']):
                unwanted_tag.decompose()
            body_container = article_tag

        paragraphs = body_container.find_all('p')
        paragraphs_text = [p.get_text(separator=' ', strip=True) for p in paragraphs if p.get_text(strip=True)] if paragraphs else []
        
        if not paragraphs_text:
            full_text = body_container.get_text(separator='\n', strip=True)
            paragraphs_text = [line.strip() for line in full_text.split('\n') if line.strip()]

        article_text = '\n'.join(paragraphs_text)
        return re.sub(r'\s+', ' ', article_text).strip()
        
    except requests.exceptions.RequestException as e:
        print(f"  [本文取得エラー] Bloomberg記事 ({article_url}) の取得に失敗: {e}")
        return ""
    except Exception as e:
        print(f"  [本文取得エラー] Bloomberg記事 ({article_url}) の解析中に予期せぬエラー: {e}")
        return ""

def scrape_bloomberg_top_page_articles(hours_limit: int, exclude_keywords: list) -> list:
    """Bloombergのトップページから記事情報を収集する"""
    base_url = "https://www.bloomberg.co.jp"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36')
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")

    driver = None
    print("\n--- Bloomberg記事のスクレイピング開始 ---")
    
    articles_to_process = []
    processed_urls = set()

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(scraping_config.selenium_timeout)
        wait = WebDriverWait(driver, scraping_config.selenium_timeout)
        
        print(f"  Bloomberg: トップページ ({base_url}) を取得中...")
        for attempt in range(scraping_config.selenium_max_retries):
            try:
                # 段階的タイムアウト: 初回25秒、リトライ時45秒
                current_timeout = 25 if attempt == 0 else 45
                wait_with_timeout = WebDriverWait(driver, current_timeout)
                
                driver.get(base_url)
                # 主要な記事コンテナが表示されるまで待機
                wait_with_timeout.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component="story-list"], [class*="hub-page-body"], main')))
                break
            except TimeoutException:
                print(f"    [!] ページ読み込みタイムアウト ({current_timeout}秒, {attempt + 1}/{scraping_config.selenium_max_retries})。リトライします...")
                if attempt + 1 == scraping_config.selenium_max_retries:
                    print(f"    [!] リトライ上限に達したため、Bloombergのスクレイピングを中止します。")
                    return []
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        article_elements = soup.find_all('article', class_=re.compile(r'story|module', re.I))
        
        if not article_elements:
            print("    [!] Bloombergトップページで記事候補が見つかりませんでした。サイト構造を確認してください。")
            return []
            
        print(f"    - トップページで記事候補: {len(article_elements)} 件発見。")
        
        jst = pytz.timezone('Asia/Tokyo')
        now_jst = datetime.now(jst)
        time_threshold_jst = now_jst - timedelta(hours=hours_limit)

        for article_element in article_elements:
            link_el = article_element.find('a', href=True)
            if not link_el or not link_el.has_attr('href'): continue
                
            raw_url = link_el['href']
            article_url = base_url + raw_url if raw_url.startswith('/') else raw_url
            article_url = article_url.split('?')[0].split('#')[0]

            if not article_url.startswith('http') or article_url in processed_urls: continue
            processed_urls.add(article_url)

            time_tag = article_element.find('time', datetime=True)
            article_time_jst = now_jst
            if time_tag and time_tag.has_attr('datetime'):
                try:
                    dt_utc = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                    article_time_jst = dt_utc.astimezone(jst)
                except ValueError:
                    pass # パース失敗時は現在時刻のまま

            if article_time_jst < time_threshold_jst: continue

            title_element = article_element.find(['h1','h2','h3','a'], class_=re.compile(r'story-title', re.I)) or link_el
            title = title_element.get_text(strip=True)
            if not title or any(keyword.lower() in title.lower() for keyword in exclude_keywords): continue

            print(f"    > 記事発見: {title}")
            articles_to_process.append({
                'source': 'Bloomberg', 'title': title, 'url': article_url,
                'published_jst': article_time_jst, 'category': "Bloomberg Top"
            })

    except Exception as e:
        print(f"  Bloombergスクレイピング処理全体でエラーが発生しました: {e}")
    finally:
        if driver:
            driver.quit()

    if not articles_to_process:
        print("--- Bloomberg: 処理対象の記事が見つかりませんでした ---")
        return []

    print(f"\n--- {len(articles_to_process)}件の記事本文を並列取得開始 (最大{config.bloomberg.num_parallel_requests}スレッド) ---")
    final_articles_data = []
    with ThreadPoolExecutor(max_workers=config.bloomberg.num_parallel_requests) as executor:
        future_to_article = {executor.submit(scrape_bloomberg_article_body, article['url']): article for article in articles_to_process}
        
        for i, future in enumerate(as_completed(future_to_article)):
            article = future_to_article[future]
            try:
                body = future.result()
                article['body'] = body or "[本文取得失敗/空]"
                final_articles_data.append(article)
                print(f"  ({i+1}/{len(articles_to_process)}) 完了: {article['title']}")
            except Exception as exc:
                print(f"  [!!] 記事取得中に例外発生 ({article['url']}): {exc}")
                article['body'] = f"[本文取得エラー: {exc}]"
                final_articles_data.append(article)

    print(f"--- Bloomberg記事取得完了: {len(final_articles_data)} 件 ---")
    return final_articles_data
