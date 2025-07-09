# -*- coding: utf-8 -*-

import time
from datetime import datetime, timedelta
import re
import pytz
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def scrape_bloomberg_article_body(article_url: str) -> str:
    """指定されたBloomberg記事URLから本文を抽出する"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}
        response = requests.get(article_url, headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 複数の可能性のあるクラス名に対応
        body_container = soup.find('div', class_=re.compile(r'(body-copy|article-body|content-well)'))
        
        if not body_container:
            article_tag = soup.find('article')
            if not article_tag: return ""
            # 不要な要素を削除
            for unwanted_tag in article_tag.find_all(['script', 'style', 'aside', 'figure', 'figcaption', 'iframe', 'header', 'footer', 'nav']):
                unwanted_tag.decompose()
            body_container = article_tag

        paragraphs = body_container.find_all('p')
        if paragraphs:
            paragraphs_text = [p.get_text(separator=' ', strip=True) for p in paragraphs if p.get_text(strip=True)]
        else:
            # pタグがない場合のフォールバック
            full_text = body_container.get_text(separator='\n', strip=True)
            paragraphs_text = [line.strip() for line in full_text.split('\n') if line.strip()]

        if not paragraphs_text: return ""
        
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
    articles_data, processed_urls = [], set()
    base_url = "https://www.bloomberg.co.jp"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36')

    driver = None
    print("\n--- Bloomberg記事のスクレイピング開始 ---")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        driver.set_page_load_timeout(45)
        
        print(f"  Bloomberg: トップページ ({base_url}) を取得中...")
        driver.get(base_url)
        time.sleep(10) # 動的コンテンツの読み込みを待つ
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # 記事要素の候補を広めに取る
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
            if not link_el or not link_el.has_attr('href'):
                continue
                
            raw_url = link_el['href']
            article_url = base_url + raw_url if raw_url.startswith('/') else raw_url
            article_url = article_url.split('?')[0].split('#')[0] # クエリパラメータ等を削除

            if not article_url.startswith('http') or article_url in processed_urls:
                continue

            time_tag = article_element.find('time', datetime=True)
            if time_tag:
                try:
                    dt_utc = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                    article_time_jst = dt_utc.astimezone(jst)
                except ValueError:
                    article_time_jst = now_jst # パース失敗時は現在時刻
            else:
                article_time_jst = now_jst # timeタグがない場合も現在時刻

            if article_time_jst < time_threshold_jst:
                continue

            # タイトル取得を試みる
            title = link_el.get_text(strip=True) or (article_element.find(['h1','h2','h3']) or link_el).get_text(strip=True)
            if not title or any(keyword.lower() in title.lower() for keyword in exclude_keywords):
                continue

            print(f"    > 記事発見: {title}")
            articles_data.append({
                'source': 'Bloomberg',
                'title': title,
                'url': article_url,
                'published_jst': article_time_jst,
                'category': "Bloomberg Top",
                'body': scrape_bloomberg_article_body(article_url) or "[本文取得失敗/空]"
            })
            processed_urls.add(article_url)
            time.sleep(0.2)

    except Exception as e:
        print(f"  Bloombergスクレイピング処理全体でエラーが発生しました: {e}")
    finally:
        if driver:
            driver.quit()
            
    print(f"--- Bloomberg記事取得完了: {len(articles_data)} 件 ---")
    return articles_data
