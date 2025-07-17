# -*- coding: utf-8 -*-

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import json


def create_html_file(articles: List[Dict[str, Any]], output_path: str = "index.html") -> None:
    """
    要約された記事リストからHTMLファイルを生成します。
    
    Args:
        articles (List[Dict[str, Any]]): 要約済みの記事データを含む辞書のリスト。
                         各辞書は 'title', 'url', 'published_jst', 'summary' キーを持つことを想定。
        output_path (str): 生成するHTMLファイルのパス。
    """
    
    # 統計計算
    total_articles = len(articles)
    source_stats = {}
    sentiment_stats = {'Positive': 0, 'Negative': 0, 'Neutral': 0, 'Error': 0}
    
    for article in articles:
        source = article.get('source', 'Unknown')
        source_stats[source] = source_stats.get(source, 0) + 1
        
        sentiment = article.get('sentiment_label', 'Neutral')
        if sentiment in sentiment_stats:
            sentiment_stats[sentiment] += 1
    
    # 最終更新時刻計算
    last_updated: str = "N/A"
    if articles:
        latest_time = max(
            (article.get('published_jst') for article in articles if article.get('published_jst')),
            default=None
        )
        if latest_time and hasattr(latest_time, 'strftime'):
            last_updated = latest_time.strftime('%Y-%m-%d %H:%M')
    
    # 記事データをJavaScript用に準備
    articles_json = []
    for article in articles:
        pub_date = article.get('published_jst')
        if hasattr(pub_date, 'isoformat'):
            pub_date_str = pub_date.isoformat()
        else:
            pub_date_str = str(pub_date) if pub_date else None
            
        articles_json.append({
            'title': article.get('title', 'タイトル不明'),
            'url': article.get('url', '#'),
            'summary': article.get('summary', '要約なし'),
            'source': article.get('source', '不明'),
            'published_jst': pub_date_str,
            'sentiment_label': article.get('sentiment_label', 'Neutral'),
            'sentiment_score': article.get('sentiment_score', 0.0)
        })
    
    html_content = f"""<!DOCTYPE html>
<html lang="ja" data-theme="auto">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market News Dashboard - AIニュース分析</title>
    
    <!-- Meta Tags -->
    <meta name="description" content="AIが主要ニュースサイトから収集・要約した最新の市場ニュース">
    <meta name="keywords" content="ニュース,市場,AI,要約,感情分析,株式,経済">
    <meta name="author" content="Market News AI">
    
    <!-- Open Graph -->
    <meta property="og:title" content="Market News Dashboard">
    <meta property="og:description" content="AIが分析した最新マーケットニュース">
    <meta property="og:type" content="website">
    
    <!-- CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2.0.6/css/pico.min.css">
    <link rel="stylesheet" href="assets/css/custom.css">
    
    <!-- PWA -->
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#1976d2">
    
    <!-- Icons -->
    <link rel="icon" type="image/x-icon" href="favicon.ico">
</head>
<body>
    <!-- Header -->
    <header class="container main-header">
        <div class="header-content">
            <h1 class="header-title">
                📊 Market News Dashboard
            </h1>
            <div class="header-controls">
                <button id="theme-toggle" class="theme-toggle" aria-label="テーマ切り替え">🌙</button>
                <button id="refresh-button" class="refresh-button">🔄 更新</button>
            </div>
        </div>
        <p>AIが主要ニュースサイトから収集・要約した最新情報</p>
    </header>

    <main class="container">
        <!-- 統計セクション -->
        <section class="stats-section">
            <div class="grid">
                <div class="stat-card">
                    <div class="stat-number" id="total-articles">{total_articles}</div>
                    <div class="stat-label">総記事数</div>
                </div>
                <div class="stat-card">
                    <div id="sentiment-chart"></div>
                    <div class="stat-label">感情分布</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="last-updated">{last_updated}</div>
                    <div class="stat-label">最終更新</div>
                </div>
            </div>
        </section>

        <!-- フィルター・検索 -->
        <section class="filter-section">
            <div class="filter-row">
                <div class="filter-group">
                    <label for="search-input">🔍 記事を検索</label>
                    <input type="search" id="search-input" placeholder="キーワードで検索... (Ctrl+K)">
                </div>
                <div class="filter-group">
                    <label for="source-filter">📰 ソース</label>
                    <select id="source-filter">
                        <option value="">全てのソース</option>
                        <option value="Reuters">Reuters</option>
                        <option value="Bloomberg">Bloomberg</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label for="sentiment-filter">😊 感情</label>
                    <select id="sentiment-filter">
                        <option value="">全ての感情</option>
                        <option value="Positive">ポジティブ</option>
                        <option value="Negative">ネガティブ</option>
                        <option value="Neutral">ニュートラル</option>
                    </select>
                </div>
            </div>
        </section>

        <!-- 記事一覧 -->
        <section class="articles-grid" id="articles-container">"""

    if not articles:
        html_content += """
            <div class="empty-state">
                <div class="empty-state-icon">📰</div>
                <h3>記事が見つかりませんでした</h3>
                <p>本日、新しいニュース記事は見つかりませんでした。</p>
            </div>"""
    else:
        # 感情アイコンのマッピング
        sentiment_icons = {
            "Positive": "😊",
            "Negative": "😠",
            "Neutral": "😐",
            "N/A": "🤔",
            "Error": "⚠️"
        }

        for article in articles:
            title: str = article.get('title', 'タイトル不明')
            url: str = article.get('url', '#')
            published_jst_raw = article.get('published_jst', '日時不明')
            published_jst: str = published_jst_raw.strftime('%Y-%m-%d %H:%M') if hasattr(published_jst_raw, 'strftime') else str(published_jst_raw)
            summary: str = article.get('summary', '要約なし')
            source: str = article.get('source', '不明なソース')
            
            # 感情分析の結果を取得
            sentiment_label: str = article.get('sentiment_label', 'Neutral')
            sentiment_score: float = float(article.get('sentiment_score', 0.0))
            sentiment_icon: str = sentiment_icons.get(sentiment_label, "🤔")
            sentiment_class: str = sentiment_label.lower() if sentiment_label != "N/A" else "neutral"
            
            # HTMLエスケープ
            title_escaped = title.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
            summary_escaped = summary.replace('<', '&lt;').replace('>', '&gt;')
            
            html_content += f"""
            <article class="article-card {sentiment_class}">
                <div class="article-header">
                    <h3 class="article-title">
                        <a href="{url}" target="_blank" rel="noopener">{title_escaped}</a>
                    </h3>
                    <div class="sentiment-badge {sentiment_class}" title="Sentiment: {sentiment_label} (Score: {sentiment_score:.2f})">
                        <span>{sentiment_icon}</span>
                        <span>{sentiment_score:.2f}</span>
                    </div>
                </div>
                <div class="article-meta">
                    <span class="source-badge">[{source}]</span>
                    <span>{published_jst}</span>
                </div>
                <p class="article-summary">{summary_escaped}</p>
            </article>"""

    html_content += f"""
        </section>

        <!-- ローディング -->
        <div id="loading" class="loading" style="display: none;">
            <div class="spinner"></div>
            <p>記事を読み込み中...</p>
        </div>
    </main>

    <!-- Footer -->
    <footer class="container main-footer">
        <div class="footer-content">
            <div class="footer-section">
                <h4>Market News Dashboard</h4>
                <p>AIによる市場ニュース分析</p>
            </div>
            <div class="footer-section">
                <h4>最終更新</h4>
                <p>{last_updated}</p>
            </div>
            <div class="footer-section">
                <h4>データソース</h4>
                <p>Reuters, Bloomberg</p>
            </div>
        </div>
        <hr>
        <div style="text-align: center;">
            <small>Powered by Gemini AI & Python Scrapers | 🤖 Generated with Claude Code</small>
        </div>
    </footer>

    <!-- JavaScript -->
    <script>
        // 記事データをJavaScriptに渡す
        window.articlesData = {json.dumps(articles_json, ensure_ascii=False, indent=2)};
    </script>
    <script src="assets/js/app.js"></script>
</body>
</html>"""

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logging.info(f"HTMLファイル '{output_path}' を生成しました。")
    except IOError as e:
        logging.error(f"HTMLファイルの書き込み中にエラーが発生しました: {e}")


if __name__ == '__main__':
    # テスト用のコード
    from datetime import datetime
    import pytz

    jst = pytz.timezone('Asia/Tokyo')

    test_articles = [
        {
            'title': 'テスト記事1: FRB、政策金利を据え置き', 
            'url': 'https://example.com/article1',
            'published_jst': datetime(2025, 6, 26, 10, 30, tzinfo=jst),
            'summary': '米連邦準備制度理事会（FRB）は、市場の予想通り政策金利を据え置いた。パウエル議長は今後の金融政策について「データ次第」と述べ、利下げ時期の明言を避けた。',
            'source': 'Reuters',
            'sentiment_label': 'Neutral',
            'sentiment_score': 0.6
        },
        {
            'title': 'テスト記事2: テック企業の決算発表', 
            'url': 'https://example.com/article2',
            'published_jst': datetime(2025, 6, 26, 11, 0, tzinfo=jst),
            'summary': '主要テック企業が好調な四半期決算を発表し、株価が上昇した。特にクラウド部門の成長が顕著で、今後の市場を牽引する見込み。',
            'source': 'Bloomberg',
            'sentiment_label': 'Positive',
            'sentiment_score': 0.8
        }
    ]

    create_html_file(test_articles)
    create_html_file([])  # 記事がない場合のテスト