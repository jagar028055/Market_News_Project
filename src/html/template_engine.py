# -*- coding: utf-8 -*-

"""
HTMLテンプレートエンジン
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import html


@dataclass
class TemplateData:
    """テンプレート用データ"""
    title: str
    articles: List[Dict[str, Any]]
    total_articles: int
    last_updated: str
    # sentiment_stats: Dict[str, int]  # 感情分析機能を削除
    source_stats: Dict[str, int]


class HTMLTemplateEngine:
    """HTMLテンプレート生成エンジン"""
    
    def __init__(self):
        # 感情分析機能を削除したため、sentiment_iconsは不要
        pass
    
    def generate_html(self, data: TemplateData) -> str:
        """HTMLファイルの生成"""
        # 記事データをJavaScript用に準備
        articles_json = self._prepare_articles_json(data.articles)
        
        # HTMLテンプレートの構築
        html_content = self._build_html_template(data, articles_json)
        
        return html_content
    
    def _prepare_articles_json(self, articles: List[Dict[str, Any]]) -> str:
        """記事データをJSON形式に変換"""
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
                'keywords': article.get('keywords', [])
            })
        
        return json.dumps(articles_json, ensure_ascii=False, indent=2)
    
    def _build_html_template(self, data: TemplateData, articles_json: str) -> str:
        """HTMLテンプレートの構築"""
        return f"""<!DOCTYPE html>
<html lang="ja" data-theme="auto">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>{data.title}</title>
    
    <!-- Meta Tags -->
    <meta name="description" content="AIが主要ニュースサイトから収集・要約した最新の市場ニュース">
    <meta name="keywords" content="ニュース,市場,AI,要約,株式,経済">
    <meta name="author" content="Market News AI">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{html.escape(data.title)}">
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
    {self._build_header()}
    {self._build_main_content(data)}
    {self._build_footer(data)}
    
    <!-- JavaScript -->
    <script>
        // 記事データをJavaScriptに渡す
        window.articlesData = {articles_json};
    </script>
    <script src="assets/js/app.js"></script>
</body>
</html>"""
    
    def _build_header(self) -> str:
        """ヘッダー部分の構築"""
        return """
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
    </header>"""
    
    def _build_main_content(self, data: TemplateData) -> str:
        """メインコンテンツの構築"""
        return f"""
    <main class="container">
        {self._build_stats_section(data)}
        {self._build_filter_section()}
        {self._build_articles_section(data)}
        {self._build_loading_section()}
    </main>"""
    
    def _build_stats_section(self, data: TemplateData) -> str:
        """統計セクションの構築"""
        return f"""
        <!-- 統計セクション -->
        <section class="stats-section">
            <div class="grid">
                <div class="stat-card">
                    <div class="stat-number" id="total-articles">{data.total_articles}</div>
                    <div class="stat-label">総記事数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="source-count">{len(data.source_stats)}</div>
                    <div class="stat-label">情報源数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="last-updated">{data.last_updated}</div>
                    <div class="stat-label">最終更新</div>
                </div>
            </div>
        </section>"""
    
    def _build_filter_section(self) -> str:
        """フィルター・検索セクションの構築"""
        return """
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
                    <label for="keyword-filter">🏷️ キーワード</label>
                    <input type="text" id="keyword-filter" placeholder="キーワードで絞込み">
                </div>
            </div>
        </section>"""
    
    def _build_articles_section(self, data: TemplateData) -> str:
        """記事セクションの構築（JavaScript動的描画用）"""
        if not data.articles:
            return self._build_empty_state()
        
        return """
        <!-- 記事一覧 -->
        <section class="articles-grid" id="articles-container">
            <!-- 記事はJavaScriptで動的に描画されます -->
        </section>"""
    
    def _build_article_card(self, article: Dict[str, Any]) -> str:
        """記事カードの構築"""
        title = article.get('title', 'タイトル不明')
        url = article.get('url', '#')
        summary = article.get('summary', '要約なし')
        source = article.get('source', '不明なソース')
        
        # 日時フォーマット
        published_jst_raw = article.get('published_jst', '日時不明')
        if hasattr(published_jst_raw, 'strftime'):
            published_jst = published_jst_raw.strftime('%Y-%m-%d %H:%M')
        else:
            published_jst = str(published_jst_raw)
        
        # キーワード情報
        keywords = article.get('keywords', [])
        keywords_str = ', '.join(keywords[:3]) if keywords else ''
        
        # HTMLエスケープ
        title_escaped = html.escape(title)
        summary_escaped = html.escape(summary)
        
        return f"""
            <article class="article-card">
                <div class="article-header">
                    <h3 class="article-title">
                        <a href="{url}" target="_blank" rel="noopener">{title_escaped}</a>
                    </h3>
                    {('<div class="keywords-badge" title="主要キーワード"><span>🏷️</span><span>' + keywords_str + '</span></div>') if keywords_str else ''}
                </div>
                <div class="article-meta">
                    <span class="source-badge">[{source}]</span>
                    <span>{published_jst}</span>
                </div>
                <p class="article-summary">{summary_escaped}</p>
            </article>"""
    
    def _build_empty_state(self) -> str:
        """空の状態の構築"""
        return """
        <!-- 記事一覧 -->
        <section class="articles-grid" id="articles-container">
            <div class="empty-state">
                <div class="empty-state-icon">📰</div>
                <h3>記事が見つかりませんでした</h3>
                <p>本日、新しいニュース記事は見つかりませんでした。</p>
            </div>
        </section>"""
    
    def _build_loading_section(self) -> str:
        """ローディングセクションの構築"""
        return """
        <!-- ローディング -->
        <div id="loading" class="loading" style="display: none;">
            <div class="spinner"></div>
            <p>記事を読み込み中...</p>
        </div>"""
    
    def _build_footer(self, data: TemplateData) -> str:
        """フッターの構築"""
        return f"""
    <!-- Footer -->
    <footer class="container main-footer">
        <div class="footer-content">
            <div class="footer-section">
                <h4>Market News Dashboard</h4>
                <p>AIによる市場ニュース分析</p>
            </div>
            <div class="footer-section">
                <h4>最終更新</h4>
                <p>{data.last_updated}</p>
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
    </footer>"""