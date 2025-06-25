# -*- coding: utf-8 -*-

import time
from datetime import datetime, timedelta
import re
import pytz
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def scrape_reuters_article_body(article_url: str) -> str:
    """指定されたロイター記事URLから本文を抽出する"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}
        response = requests.get(article_url, headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.content, 'html.parser')
        body_container = soup.find('div', class_='article-body__content__17Yit')
        if not body_container: return ""
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
    articles_data, processed_urls = [], set()
    base_search_url = "https://jp.reuters.com/site-search/"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36')

    driver = None
    print("\n--- ロイター記事のスクレイピング開始 ---")
    try:
        # ここでは `webdriver-manager` を使うか、
        # または事前にChromeDriverのパスが通っていることを前提とします。
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(15)
        driver.set_page_load_timeout(120) # タイムアウトを120秒に延長
        
        jst = pytz.timezone('Asia/Tokyo')
        time_threshold_jst = datetime.now(jst) - timedelta(hours=hours_limit)

        for page_num in range(max_pages):
            offset = page_num * items_per_page
            search_url = f"{base_search_url}?query={requests.utils.quote(query)}&offset={offset}"
            print(f"  ロイター: ページ {page_num + 1}/{max_pages} を処理中 ({search_url})...")
            try:
                driver.get(search_url)
                time.sleep(7)  # JavaScriptの描画を待つ
            except Exception as e:
                print(f"    [!] ページの読み込み中にタイムアウトまたはエラーが発生しました: {e}")
                print("    このページをスキップして次に進みます。")
                continue
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            articles_on_page = soup.find_all('li', attrs={"data-testid": "StoryCard"})
            
            if not articles_on_page:
                if page_num == 0:
                    print("    [!] 最初のページで記事が見つかりませんでした。サイト構造が変更された可能性があります。")
                break

            for article_li in articles_on_page:
                title_container = article_li.find('div', class_=re.compile(r'title__title'))
                link_element = title_container.find('a', attrs={"data-testid": "TitleLink"}) if title_container else None
                if not link_element:
                    continue

                article_url = link_element.get('href', '')
                if article_url.startswith('/'):
                    article_url = "https://jp.reuters.com" + article_url
                
                if not article_url.startswith('http') or article_url in processed_urls:
                    continue

                time_element = article_li.find('time', attrs={"data-testid": "DateLineText"})
                try:
                    dt_utc = datetime.fromisoformat(time_element.get('datetime').replace('Z', '+00:00'))
                    article_time_jst = dt_utc.astimezone(jst)
                except (ValueError, AttributeError):
                    continue  # 日時が取得できないものはスキップ

                if article_time_jst < time_threshold_jst:
                    continue

                title = link_element.get_text(strip=True)
                if any(keyword.lower() in title.lower() for keyword in exclude_keywords):
                    continue

                kicker = article_li.find('span', attrs={"data-testid": "KickerLabel"})
                category_text = kicker.get_text(strip=True).replace(" category", "") if kicker else "不明"
                
                if target_categories and category_text not in target_categories:
                    continue

                print(f"    > 記事発見: {title}")
                articles_data.append({
                    'title': title,
                    'url': article_url,
                    'published_jst': article_time_jst,
                    'category': category_text,
                    'body': scrape_reuters_article_body(article_url) or "[本文取得失敗/空]"
                })
                processed_urls.add(article_url)

            if len(articles_on_page) < items_per_page:
                break  # 最後のページに到達した
            
            time.sleep(1)

    except Exception as e:
        print(f"  ロイタースクレイピング処理全体でエラーが発生しました: {e}")
    finally:
        if driver:
            driver.quit()
            
    print(f"--- ロイター記事取得完了: {len(articles_data)} 件 ---")
    return articles_data
