# -*- coding: utf-8 -*-

"""
HTMLテンプレートエンジン
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import html
import markdown


@dataclass
class TemplateData:
    """テンプレート用データ"""

    title: str
    articles: List[Dict[str, Any]]
    total_articles: int
    last_updated: str
    # sentiment_stats: Dict[str, int]  # 感情分析機能を削除
    source_stats: Dict[str, int]
    region_stats: Dict[str, int]  # 地域統計データ
    category_stats: Dict[str, int]  # カテゴリ統計データ
    # Pro統合要約データ
    integrated_summaries: Optional[Dict[str, Any]] = None
    # ワードクラウドデータ
    wordcloud_data: Optional[Dict[str, Any]] = None


class HTMLTemplateEngine:
    """HTMLテンプレート生成エンジン"""

    def __init__(self):
        # 感情分析機能を削除したため、sentiment_iconsは不要
        # マークダウンコンバーター初期化
        self.markdown_converter = markdown.Markdown(extensions=["extra", "codehilite"])

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
            pub_date = article.get("published_jst")
            if hasattr(pub_date, "isoformat"):
                pub_date_str = pub_date.isoformat()
            else:
                pub_date_str = str(pub_date) if pub_date else None

            articles_json.append(
                {
                    "title": article.get("title", "タイトル不明"),
                    "url": article.get("url", "#"),
                    "summary": article.get("summary", "要約なし"),
                    "source": article.get("source", "不明"),
                    "published_jst": pub_date_str,
                    "keywords": article.get("keywords", []),
                    "category": article.get("category", "その他"),
                    "region": article.get("region", "その他"),
                    "sentiment_label": article.get("sentiment_label", "N/A"),
                    "sentiment_score": article.get("sentiment_score", 0.0),
                }
            )

        return json.dumps(articles_json, ensure_ascii=False, indent=2)

    def _markdown_to_html(self, markdown_text: str) -> str:
        """マークダウンテキストをHTMLに変換

        Args:
            markdown_text: マークダウン形式のテキスト

        Returns:
            HTML形式のテキスト
        """
        if not markdown_text:
            return ""

        try:
            # マークダウンをHTMLに変換
            html_content = self.markdown_converter.convert(markdown_text)
            # リセット（次回の変換で前回の状態が残らないように）
            self.markdown_converter.reset()

            # 地域別市場概況の改行処理を改善
            html_content = self._improve_regional_formatting(html_content)

            # 不要な文言を除去
            html_content = self._remove_unwanted_text(html_content)

            return html_content
        except Exception as e:
            # 変換に失敗した場合はエスケープしたプレーンテキストを返す
            return html.escape(markdown_text).replace("\n", "<br>")

    def _build_html_template(self, data: TemplateData, articles_json: str) -> str:
        """HTMLテンプレートの構築"""
        cache_buster = datetime.now().strftime('%Y%m%d-%H%M%S')
        return f"""<!DOCTYPE html>
<html lang="ja" data-theme="auto">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; connect-src 'self'; font-src 'self' https://cdn.jsdelivr.net; object-src 'none'; media-src 'self'; frame-src 'none';">
    <meta http-equiv="X-Content-Type-Options" content="nosniff">
    <meta http-equiv="X-Frame-Options" content="DENY">
    <meta http-equiv="X-XSS-Protection" content="1; mode=block">
    <meta http-equiv="Referrer-Policy" content="strict-origin-when-cross-origin">
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
    
    <!-- Chart.js削除 - SVG実装のため不要 -->
    
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
    
    {self._build_chart_modal()}
    
    <!-- JavaScript -->
    <script>
        // Safari 対応のための Polyfill
        if (!Array.prototype.includes) {{
            Array.prototype.includes = function(searchElement /*, fromIndex*/) {{
                'use strict';
                var O = Object(this);
                var len = parseInt(O.length) || 0;
                if (len === 0) {{
                    return false;
                }}
                var n = parseInt(arguments[1]) || 0;
                var k;
                if (n >= 0) {{
                    k = n;
                }} else {{
                    k = len + n;
                    if (k < 0) {{k = 0;}}
                }}
                for (; k < len; k++) {{
                    if (searchElement === O[k]) {{
                        return true;
                    }}
                }}
                return false;
            }};
        }}

        // app.jsとの連携のためのグローバル関数
        window.clearFilters = () => {{
            if (window.app) {{
                window.app.clearFilters();
            }}
        }};
    </script>
    
    <!-- Data Loading Script for Chart Rendering -->
    <script>
        // 記事データと統計データをJavaScriptに渡す
        window.articlesData = {articles_json};
        window.statisticsData = {{
            "source": {json.dumps(data.source_stats, ensure_ascii=False)},
            "region": {json.dumps(data.region_stats, ensure_ascii=False)},
            "category": {json.dumps(data.category_stats, ensure_ascii=False)}
        }};
        
        // Load articles data for chart generation (fallback)
        async function loadArticlesData() {{
            try {{
                const response = await fetch('data/articles.json');
                if (!response.ok) {{
                    throw new Error(`HTTP error! status: ${{response.status}}`);
                }}
                const data = await response.json();
                if (!window.articlesData || window.articlesData.length === 0) {{
                    window.articlesData = data;
                }}
                console.log('✅ Articles data loaded successfully:', (window.articlesData || []).length, 'articles');
            }} catch (error) {{
                console.error('❌ Failed to load articles data:', error);
                if (!window.articlesData) {{
                    window.articlesData = [];
                }}
            }}
        }}
        
        // Load data before initializing the app
        loadArticlesData();
    </script>
    <script src="assets/js/app.js?v={cache_buster}"></script>
</body>
</html>"""

    def _check_section_completeness(self, content: str, section_type: str) -> bool:
        """セクション内容の完全性をチェック

        Args:
            content: セクション内容
            section_type: セクションタイプ

        Returns:
            不完全と判断される場合True
        """
        if not content:
            return True

        content = content.strip()

        # 地域間相互影響分析の特別チェック
        if section_type == "cross_regional_analysis":
            # 特定の不完全パターンをチェック
            incomplete_patterns = [
                "**米国の通",  # 実際に発生した切り詰めパターン
                "- **",
                "**",
                "- ",
                "。**",
                "）**",
            ]

            for pattern in incomplete_patterns:
                if content.endswith(pattern):
                    return True

            # 文字数が極端に少ない場合
            if len(content) < 100:
                return True

            # 文が途中で終わっているかチェック（日本語の句読点で終わっていない）
            if not any(
                content.endswith(char) for char in ["。", "！", "？", "）", "」", "』", "、"]
            ):
                return True

        return False

    def _get_incomplete_warning(self) -> str:
        """不完全セクション用の警告HTMLを取得"""
        return """
        <div class="incomplete-warning" style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 8px; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="color: #d63031;">⚠️</span>
                <small style="color: #6c5700; font-weight: 500;">
                    この分析は不完全な可能性があります。次回の更新で完全版が表示される予定です。
                </small>
            </div>
        </div>"""

    def _improve_regional_formatting(self, html_content: str) -> str:
        """HTMLテンプレート駆動での軽量フォーマット改善

        Args:
            html_content: HTML形式のコンテンツ

        Returns:
            改善されたHTML
        """
        # HTMLテンプレートが既に構造化されているため、最小限の処理のみ
        # 既にGeminiが適切なHTMLを生成しているはず
        return html_content

    def _remove_unwanted_text(self, html_content: str) -> str:
        """不要な文言やプロンプト由来のテキストを除去（簡素版）

        Args:
            html_content: HTML形式のコンテンツ

        Returns:
            クリーンなHTML
        """
        import re

        # HTMLテンプレート駆動のため、最小限のクリーンアップのみ

        # プロンプト指示文の除去（念のため）
        unwanted_patterns = [
            r"\[.*?の分析内容\]",  # テンプレートのプレースホルダー
            r"以下のHTMLテンプレートに従って出力：",
            r"【重要：HTMLテンプレート形式で出力してください】",
        ]

        for pattern in unwanted_patterns:
            html_content = re.sub(pattern, "", html_content, flags=re.IGNORECASE)

        # 不要な記号を除去
        html_content = re.sub(r"\*+(?=\s*</)", "", html_content)  # タグ前の*記号
        html_content = re.sub(r"\*+$", "", html_content, flags=re.MULTILINE)  # 行末の*記号

        return html_content.strip()

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
                <a href="pro-summary.html" class="pro-summary-link">📈 詳細分析</a>
            </div>
        </div>
        <p>AIが主要ニュースサイトから収集・要約した最新情報</p>
    </header>"""

    def _build_main_content(self, data: TemplateData) -> str:
        """メインコンテンツの構築"""
        integrated_summary_section = (
            self._build_integrated_summary_section(data) if data.integrated_summaries else ""
        )
        wordcloud_section = self._build_wordcloud_section(data) if data.wordcloud_data else ""

        return f"""
    <main class="container">
        {self._build_stats_section(data)}
        {integrated_summary_section}
        {wordcloud_section}
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
                <div class="stat-card info-card">
                    <div class="info-row">
                        <div class="stat-number" id="total-articles">{data.total_articles}</div>
                        <div class="stat-label">総記事数</div>
                    </div>
                    <div class="info-row">
                        <div class="stat-number" id="last-updated">{data.last_updated}</div>
                        <div class="stat-label">最終更新</div>
                    </div>
                </div>
                <div class="stat-card chart-card">
                    <div class="stat-label">地域分布</div>
                    <div class="chart-container">
                        <div id="region-chart" class="svg-chart"></div>
                    </div>
                </div>
                <div class="stat-card chart-card">
                    <div class="stat-label">カテゴリ分布</div>
                    <div class="chart-container">
                        <div id="category-chart" class="svg-chart"></div>
                    </div>
                </div>
            </div>
        </section>"""

    def _build_integrated_summary_section(self, data: TemplateData) -> str:
        """統合要約セクションの構築"""
        if not data.integrated_summaries:
            return ""

        summaries = data.integrated_summaries

        # 統合要約の構造に対応（unified_summaryキーがある場合）
        if "unified_summary" in summaries:
            unified = summaries["unified_summary"]
            global_summary = unified.get("global_overview", "")
            regional_summaries_text = unified.get("regional_summaries", "")
            cross_regional_analysis = unified.get("cross_regional_analysis", "")
            key_trends = unified.get("key_trends", "")
            risk_factors = unified.get("risk_factors", "")
            regional_summaries = {}  # 地域別は個別表示しない
        else:
            # 従来の構造に対応
            global_summary = summaries.get("global_summary", "")
            regional_summaries = summaries.get("regional_summaries", {})
            regional_summaries_text = ""
            cross_regional_analysis = ""
            key_trends = ""
            risk_factors = ""

        metadata = summaries.get("metadata", {})

        # 地域別要約カードの構築
        regional_cards = ""
        for region, summary_text in regional_summaries.items():
            if summary_text:  # 空でない場合のみ表示
                article_count = metadata.get("articles_by_region", {}).get(region, 0)
                regional_cards += f"""
                <div class="summary-card regional-summary" data-region="{html.escape(region)}">
                    <div class="summary-header">
                        <h4>🌍 {html.escape(region)}市況</h4>
                        <span class="article-count">{article_count}記事</span>
                    </div>
                    <div class="summary-content">
                        <div>{self._markdown_to_html(summary_text)}</div>
                    </div>
                </div>"""

        # Pro統合要約の場合は複数セクションを表示
        if "unified_summary" in summaries:
            content_sections = ""

            # 地域別市場概況
            if regional_summaries_text:
                content_sections += f"""
                <div class="summary-card regional-overview">
                    <div class="summary-header">
                        <h3>🗺️ 地域別市場概況</h3>
                    </div>
                    <div class="summary-content">
                        <style>
                            .region-item {{
                                margin-bottom: 16px;
                                padding: 12px;
                                background-color: #f8f9fa;
                                border-radius: 6px;
                                border-left: 4px solid #007bff;
                            }}
                            .region-item h4 {{
                                margin: 0 0 8px 0;
                                color: #2c3e50;
                                font-size: 1.1em;
                            }}
                            .region-item p {{
                                margin: 0;
                                line-height: 1.6;
                            }}
                        </style>
                        <div class="summary-text regional-summaries">
                            <div>{self._markdown_to_html(regional_summaries_text)}</div>
                        </div>
                    </div>
                </div>"""

            # グローバル市場総括
            if global_summary:
                content_sections += f"""
                <div class="summary-card global-summary">
                    <div class="summary-header">
                        <h3>📊 グローバル市場総括</h3>
                        <span class="article-count">全{metadata.get('total_articles', 0)}記事</span>
                    </div>
                    <div class="summary-content">
                        <style>
                            .global-overview {{
                                padding: 16px;
                                background-color: #f1f3f4;
                                border-radius: 6px;
                                border-left: 4px solid #28a745;
                            }}
                            .global-overview p {{
                                margin: 0;
                                line-height: 1.6;
                            }}
                        </style>
                        <div class="summary-text">
                            <div>{self._markdown_to_html(global_summary)}</div>
                        </div>
                    </div>
                </div>"""

            # 地域間相互影響分析（最重要）
            if cross_regional_analysis:
                # 不完全性チェック
                is_incomplete = self._check_section_completeness(
                    cross_regional_analysis, "cross_regional_analysis"
                )
                incomplete_warning = self._get_incomplete_warning() if is_incomplete else ""

                content_sections += f"""
                <div class="summary-card cross-regional-analysis highlight">
                    <div class="summary-header">
                        <h3>🌏 地域間相互影響分析</h3>
                        <span class="priority-badge">最重要</span>
                    </div>
                    <div class="summary-content">
                        <style>
                            .influence-item {{
                                margin-bottom: 16px;
                                padding: 12px;
                                background-color: #fff3cd;
                                border-radius: 6px;
                                border-left: 4px solid #ffc107;
                            }}
                            .influence-item h5 {{
                                margin: 0 0 8px 0;
                                color: #856404;
                                font-size: 1.05em;
                            }}
                            .influence-item p {{
                                margin: 0;
                                line-height: 1.6;
                                color: #6c5700;
                            }}
                        </style>
                        {incomplete_warning}
                        <div class="summary-text cross-regional-content">
                            <div>{self._markdown_to_html(cross_regional_analysis)}</div>
                        </div>
                    </div>
                </div>"""

            # 注目トレンド・将来展望
            if key_trends:
                content_sections += f"""
                <div class="summary-card key-trends">
                    <div class="summary-header">
                        <h3>📈 注目トレンド・将来展望</h3>
                    </div>
                    <div class="summary-content">
                        <style>
                            .key-trends {{
                                padding: 16px;
                                background-color: #e7f3ff;
                                border-radius: 6px;
                                border-left: 4px solid #007bff;
                            }}
                            .key-trends p {{
                                margin: 0;
                                line-height: 1.6;
                            }}
                        </style>
                        <div class="summary-text">
                            <div>{self._markdown_to_html(key_trends)}</div>
                        </div>
                    </div>
                </div>"""

            # リスク要因・投資機会
            if risk_factors:
                content_sections += f"""
                <div class="summary-card risk-factors">
                    <div class="summary-header">
                        <h3>⚠️ リスク要因・投資機会</h3>
                    </div>
                    <div class="summary-content">
                        <style>
                            .risk-item {{
                                margin-bottom: 16px;
                                padding: 12px;
                                background-color: #f8d7da;
                                border-radius: 6px;
                                border-left: 4px solid #dc3545;
                            }}
                            .risk-item h5 {{
                                margin: 0 0 8px 0;
                                color: #721c24;
                                font-size: 1.05em;
                            }}
                            .risk-item p {{
                                margin: 0;
                                line-height: 1.6;
                                color: #721c24;
                            }}
                        </style>
                        <div class="summary-text">
                            <div>{self._markdown_to_html(risk_factors)}</div>
                        </div>
                    </div>
                </div>"""

            return f"""
        <!-- 統合要約セクション -->
        <section class="integrated-summary-section">
            <div class="section-header">
                <h2>🤖 AI統合市況分析</h2>
                <p>Gemini 2.5 Proによる地域間関連性を重視した包括的市場分析</p>
            </div>
            
            {content_sections}
            
            <div class="summary-footer">
                <small>
                    📅 更新時刻: {data.last_updated} | 
                    🚀 Powered by Gemini 2.5 Pro | 地域間相互影響分析重視
                </small>
            </div>
        </section>"""

        else:
            # 従来の表示形式
            return f"""
        <!-- 統合要約セクション -->
        <section class="integrated-summary-section">
            <div class="section-header">
                <h2>🤖 AI統合市況分析</h2>
                <p>Gemini 2.5 Proによる総合的な市場動向の分析</p>
            </div>
            
            {('<!-- 全体市況要約 -->' + '''
            <div class="summary-card global-summary">
                <div class="summary-header">
                    <h3>📊 総合市況レポート</h3>
                    <span class="article-count">全''' + str(metadata.get('total_articles', 0)) + '''記事</span>
                </div>
                <div class="summary-content">
                    <div class="summary-text">
                        <div>''' + self._markdown_to_html(global_summary) + '''</div>
                    </div>
                </div>
            </div>''') if global_summary else ''}
            
            {('<!-- 地域別要約 -->' + '''
            <div class="regional-summaries">
                <h3>🗺️ 地域別市況分析</h3>
                <div class="regional-grid">''' + regional_cards + '''
                </div>
            </div>''') if regional_cards else ''}
            
            <div class="summary-footer">
                <small>
                    📅 更新時刻: {data.last_updated} | 
                    🚀 Powered by Gemini 2.5 Pro
                </small>
            </div>
        </section>"""

    def _build_wordcloud_section(self, data: TemplateData) -> str:
        """ワードクラウドセクションの構築"""
        if not data.wordcloud_data:
            return ""

        wordcloud = data.wordcloud_data
        image_base64 = wordcloud.get("image_base64", "")
        total_articles = wordcloud.get("total_articles", 0)
        quality_score = wordcloud.get("quality_score", 0.0)

        # 品質スコアに応じたステータス表示
        if quality_score >= 0.8:
            quality_status = "🟢 高品質"
            quality_class = "quality-excellent"
        elif quality_score >= 0.6:
            quality_status = "🟡 良好"
            quality_class = "quality-good"
        else:
            quality_status = "🔴 要改善"
            quality_class = "quality-poor"

        return f"""
        <!-- ワードクラウドセクション -->
        <section class="wordcloud-section">
            <div class="section-header">
                <h2>☁️ 今日のキーワードクラウド</h2>
                <p>本日の記事から抽出した重要キーワードの可視化</p>
            </div>
            
            <div class="wordcloud-container">
                <div class="wordcloud-image-wrapper">
                    {f'<img src="data:image/png;base64,{image_base64}" alt="本日のワードクラウド" class="wordcloud-image">' if image_base64 else '<div class="wordcloud-error">ワードクラウドを生成できませんでした</div>'}
                </div>
                
                <div class="wordcloud-stats">
                    <div class="stat-row">
                        <div class="stat-item">
                            <span class="stat-label">対象記事</span>
                            <span class="stat-value">{total_articles}件</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">品質スコア</span>
                            <span class="stat-value {quality_class}">{quality_status}</span>
                        </div>
                    </div>
                    <div class="wordcloud-description">
                        <p>日本語形態素解析により抽出されたキーワードを、TF-IDF手法で重み付けして可視化。</p>
                        <p>金融・経済用語は特別な重み付けが適用されています。</p>
                    </div>
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
                    <label for="region-filter">🌍 地域</label>
                    <select id="region-filter">
                        <option value="">全ての地域</option>
                        <option value="japan">日本</option>
                        <option value="usa">アメリカ</option>
                        <option value="europe">欧州</option>
                        <option value="asia">アジア</option>
                        <option value="global">グローバル</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label for="sort-filter">📊 並び順</label>
                    <select id="sort-filter">
                        <option value="date-desc">日時（新しい順）</option>
                        <option value="date-asc">日時（古い順）</option>
                        <option value="source">ソース順</option>
                    </select>
                </div>
            </div>
        </section>
        
        <!-- Loading Indicator -->
        <div id="loading" style="text-align: center; padding: 2rem; display: block;">
            <div style="font-size: 2rem;">⏳</div>
            <p>記事を読み込み中...</p>
        </div>"""

    def _build_articles_section(self, data: TemplateData) -> str:
        """記事セクションの構築（JavaScript動的描画用）"""
        return """
        <!-- 記事一覧 -->
        <section id="articles-section">
            <h2>📰 記事一覧 <span id="articles-count"></span></h2>
            <div id="articles-container" class="articles-grid">
                <!-- 記事はJavaScriptで動的に生成 -->
            </div>
        </section>"""

    def _build_article_card(self, article: Dict[str, Any]) -> str:
        """記事カードの構築"""
        title = article.get("title", "タイトル不明")
        url = article.get("url", "#")
        summary = article.get("summary", "要約なし")
        source = article.get("source", "不明なソース")
        
        # AI分析結果からcategory/regionを取得
        category = article.get('category', 'その他')
        region = article.get('region', 'その他')

        # 日時フォーマット
        published_jst_raw = article.get("published_jst", "日時不明")
        if hasattr(published_jst_raw, "strftime"):
            published_jst = published_jst_raw.strftime("%Y-%m-%d %H:%M")
        else:
            published_jst = str(published_jst_raw)

        # キーワード情報
        keywords = article.get("keywords", [])
        keywords_str = ", ".join(keywords[:3]) if keywords else ""
        
        # 地域・カテゴリの表示名変換
        region_display = self._get_region_display_name(region)
        category_display = self._get_category_display_name(category)
        
        # 地域・カテゴリの絵文字
        region_emoji = self._get_region_emoji(region)
        category_emoji = self._get_category_emoji(category)

        # HTMLエスケープ
        title_escaped = html.escape(title)
        summary_html = self._markdown_to_html(summary)

        return f"""
            <article class="article-card" data-region="{region}" data-category="{category}">
                <div class="article-header">
                    <h3 class="article-title">
                        <a href="{url}" target="_blank" rel="noopener">{title_escaped}</a>
                    </h3>
                    <div class="article-badges">
                        <div class="region-badge" title="地域: {region_display}">
                            <span>{region_emoji}</span><span>{region_display}</span>
                        </div>
                        <div class="category-badge" title="カテゴリ: {category_display}">
                            <span>{category_emoji}</span><span>{category_display}</span>
                        </div>
                        {('<div class="keywords-badge" title="主要キーワード"><span>🏷️</span><span>' + keywords_str + '</span></div>') if keywords_str else ''}
                    </div>
                </div>
                <div class="article-meta">
                    <span class="source-badge">[{source}]</span>
                    <span>{published_jst}</span>
                </div>
                <div class="article-summary">{summary_html}</div>
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
    
    def _get_region_display_name(self, region: str) -> str:
        """地域コードを表示名に変換"""
        region_map = {
            'japan': '日本',
            'usa': '米国',
            'china': '中国', 
            'europe': '欧州',
            'その他': 'その他'
        }
        return region_map.get(region, 'その他')
    
    def _get_category_display_name(self, category: str) -> str:
        """カテゴリコードを表示名に変換"""
        category_map = {
            '金融政策': '金融政策',
            '経済指標': '経済指標',
            '企業業績': '企業業績',
            '市場動向': '市場動向',
            '地政学': '地政学',
            'その他': 'その他'
        }
        return category_map.get(category, 'その他')
    
    def _get_region_emoji(self, region: str) -> str:
        """地域に対応する絵文字を取得"""
        emoji_map = {
            'japan': '🇯🇵',
            'usa': '🇺🇸', 
            'china': '🇨🇳',
            'europe': '🇪🇺',
            'その他': '🌍'
        }
        return emoji_map.get(region, '🌍')
    
    def _get_category_emoji(self, category: str) -> str:
        """カテゴリに対応する絵文字を取得"""
        emoji_map = {
            '金融政策': '🏦',
            '経済指標': '📈',
            '企業業績': '🏢',
            '市場動向': '📊',
            '地政学': '🌐',
            'その他': '📰'
        }
        return emoji_map.get(category, '📰')

    def _build_footer(self, data: TemplateData) -> str:
        """フッターの構築"""
        return f"""
    <!-- Footer -->
    <footer class="footer">
        <div class="footer-content">
            <div class="footer-section">
                <h4>Market News Dashboard</h4>
                <p>AIによる市場ニュース分析</p>
            </div>
            <div class="footer-section">
                <h4>最終更新</h4>
                <p id="footer-last-updated">{data.last_updated}</p>
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

    def _build_chart_modal(self) -> str:
        """チャートモーダルの構築"""
        return """
    <!-- モーダル拡大ビュー -->
    <div id="chart-modal" class="chart-modal" onclick="closeChartModal()">
        <div class="chart-modal-content" onclick="event.stopPropagation()">
            <div class="chart-modal-header">
                <h2 id="modal-title">グラフ詳細表示</h2>
                <button class="modal-close" onclick="closeChartModal()">×</button>
            </div>
            <div class="chart-modal-body">
                <div id="modal-chart-container" class="modal-chart-container">
                    <div id="modal-chart" class="svg-chart"></div>
                </div>
                <div id="modal-legend" class="chart-legend"></div>
                <div id="modal-summary" class="chart-summary"></div>
            </div>
        </div>
    </div>"""
