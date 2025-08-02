// -*- coding: utf-8 -*-

/**
 * Market News Dashboard Application
 */
class MarketNewsApp {
    constructor() {
        // データ関連
        this.articles = [];
        this.filteredArticles = [];
        
        // UI状態
        this.currentPage = 1;
        this.articlesPerPage = 20;
        this.isLoading = false;
        this.searchTimeout = null;
        
        // キャッシュ
        this.domCache = {};
        
        // 設定
        this.config = {
            debounceDelay: 300,
            animationDuration: 300,
            retryDelay: 1000,
            maxRetries: 3
        };
        
        // エラーハンドリング強化
        this.errorCount = 0;
        this.maxErrors = 10;
        this.setupErrorHandling();
        
        this.init();
    }
    
    async init() {
        try {
            this.loadTheme();
            this.setupEventListeners();
            await this.loadArticles();
            this.renderStats();
            this.renderArticles();
            this.updateLastUpdated();
        } catch (error) {
            this.handleError('初期化中にエラーが発生しました', error);
        }
    }
    
    setupErrorHandling() {
        // グローバルエラーハンドラー
        window.addEventListener('error', (event) => {
            this.handleError('JavaScript エラー', event.error);
        });
        
        // Promise の未処理エラーハンドラー
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError('Promise エラー', event.reason);
        });
    }
    
    handleError(message, error = null) {
        this.errorCount++;
        
        // エラーログ
        console.error(`[MarketNewsApp] ${message}:`, error);
        
        // エラーが多すぎる場合は機能を制限
        if (this.errorCount > this.maxErrors) {
            this.showError('エラーが多数発生しています。ページを再読み込みしてください。');
            return;
        }
        
        // ユーザーに表示
        this.showError(`${message}: ${error?.message || 'Unknown error'}`);
        
        // 必要に応じて復旧処理
        this.attemptRecovery(error);
    }
    
    attemptRecovery(error) {
        // DOM要素の再キャッシュ
        if (error?.message?.includes('null') || error?.message?.includes('undefined')) {
            console.log('DOM要素を再キャッシュします...');
            this.cacheElements();
        }
        
        // 記事データの再読み込み
        if (error?.message?.includes('articles') || this.articles.length === 0) {
            console.log('記事データを再読み込みします...');
            this.loadArticles().catch(e => {
                console.error('記事データの復旧に失敗:', e);
            });
        }
    }
    
    setupEventListeners() {
        // DOMキャッシュ
        this.cacheElements();
        
        // テーマ切り替え
        this.addEventListenerSafe('theme-toggle', 'click', () => this.toggleTheme());
        
        // 検索（最適化されたデバウンス）
        this.addEventListenerSafe('search-input', 'input', (e) => this.debouncedSearch(e.target.value));
        
        // フィルター
        this.addEventListenerSafe('source-filter', 'change', () => this.filterArticles());
        this.addEventListenerSafe('sentiment-filter', 'change', () => this.filterArticles());
        
        // リフレッシュボタン
        this.addEventListenerSafe('refresh-button', 'click', (e) => {
            e.preventDefault();
            this.refreshData();
        });
        
        // 無限スクロール（パフォーマンス最適化）
        this.setupInfiniteScroll();
        
        // キーボードショートカット
        this.setupKeyboardShortcuts();
        
        // リサイズハンドラー
        window.addEventListener('resize', this.debounce(() => this.handleResize(), 250));
    }
    
    cacheElements() {
        const elementIds = [
            'theme-toggle', 'search-input', 'source-filter', 'sentiment-filter',
            'refresh-button', 'articles-container', 'loading', 'total-articles',
            'sentiment-chart', 'last-updated'
        ];
        
        elementIds.forEach(id => {
            this.domCache[id] = document.getElementById(id);
        });
    }
    
    addEventListenerSafe(elementId, event, handler) {
        const element = this.domCache[elementId];
        if (element) {
            element.addEventListener(event, handler);
        }
    }
    
    setupInfiniteScroll() {
        let ticking = false;
        
        const scrollHandler = () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    if (this.isNearBottom() && !this.isLoading && this.hasMoreArticles()) {
                        this.loadMoreArticles();
                    }
                    ticking = false;
                });
                ticking = true;
            }
        };
        
        window.addEventListener('scroll', scrollHandler, { passive: true });
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'k':
                        e.preventDefault();
                        this.focusSearch();
                        break;
                    case 'r':
                        e.preventDefault();
                        this.refreshData();
                        break;
                    case 'f':
                        e.preventDefault();
                        this.focusFilter();
                        break;
                }
            }
        });
    }
    
    handleResize() {
        // レスポンシブ対応の調整
        if (window.innerWidth < 768) {
            this.articlesPerPage = 10;
        } else {
            this.articlesPerPage = 20;
        }
    }
    
    debouncedSearch(query) {
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        
        this.searchTimeout = setTimeout(() => {
            this.performSearch(query);
        }, this.config.debounceDelay);
    }
    
    performSearch(query) {
        this.searchQuery = query;
        this.filterArticles();
    }
    
    hasMoreArticles() {
        return this.currentPage * this.articlesPerPage < this.filteredArticles.length;
    }
    
    focusFilter() {
        const sourceFilter = this.domCache['source-filter'];
        if (sourceFilter) {
            sourceFilter.focus();
        }
    }
    
    async loadArticles() {
        try {
            this.setLoading(true);
            
            // 実際の実装では、APIエンドポイントから取得
            // 現在は埋め込みデータまたはファイルから読み込み
            if (window.articlesData && Array.isArray(window.articlesData)) {
                this.articles = window.articlesData;
                console.log(`記事データを読み込みました: ${this.articles.length}件`);
            } else {
                // フォールバック: 現在のHTMLから記事データを抽出
                console.warn('window.articlesDataが見つからないため、DOMから記事を抽出します');
                this.articles = this.extractArticlesFromDOM();
            }
            
            this.filteredArticles = [...this.articles];
            
            // データ検証
            if (this.articles.length === 0) {
                console.warn('記事データが見つかりませんでした');
            }
            
        } catch (error) {
            console.error('記事の読み込みに失敗:', error);
            this.showError('記事の読み込みに失敗しました。');
            this.articles = [];
            this.filteredArticles = [];
        } finally {
            this.setLoading(false);
        }
    }
    
    extractArticlesFromDOM() {
        const articles = [];
        const articleElements = document.querySelectorAll('.article-card');
        
        articleElements.forEach((element, index) => {
            const titleElement = element.querySelector('.article-title a');
            const metaElement = element.querySelector('.article-meta');
            const summaryElement = element.querySelector('.article-summary');
            const sentimentElement = element.querySelector('.sentiment-badge');
            
            if (titleElement && summaryElement) {
                const article = {
                    id: index,
                    title: titleElement.textContent.trim(),
                    url: titleElement.href,
                    summary: summaryElement.textContent.trim(),
                    published_jst: metaElement ? this.extractDateFromMeta(metaElement.textContent) : new Date(),
                    source: this.extractSourceFromMeta(metaElement ? metaElement.textContent : ''),
                    sentiment_label: sentimentElement ? this.extractSentimentFromBadge(sentimentElement) : 'Neutral',
                    sentiment_score: 0.5
                };
                articles.push(article);
            }
        });
        
        return articles;
    }
    
    extractDateFromMeta(metaText) {
        const dateMatch = metaText.match(/\d{4}-\d{2}-\d{2} \d{2}:\d{2}/);
        return dateMatch ? new Date(dateMatch[0]) : new Date();
    }
    
    extractSourceFromMeta(metaText) {
        const sourceMatch = metaText.match(/\[([^\]]+)\]/);
        return sourceMatch ? sourceMatch[1] : 'Unknown';
    }
    
    extractSentimentFromBadge(badgeElement) {
        if (badgeElement.classList.contains('positive')) return 'Positive';
        if (badgeElement.classList.contains('negative')) return 'Negative';
        if (badgeElement.classList.contains('error')) return 'Error';
        return 'Neutral';
    }
    
    filterArticles() {
        try {
            const searchTerm = this.getInputValue('search-input').toLowerCase();
            const sourceFilter = this.getInputValue('source-filter');
            const sentimentFilter = this.getInputValue('sentiment-filter');
            
            // パフォーマンス最適化: 検索条件が変更されていない場合はスキップ
            const filterKey = `${searchTerm}|${sourceFilter}|${sentimentFilter}`;
            if (this.lastFilterKey === filterKey) {
                return;
            }
            this.lastFilterKey = filterKey;
            
            // 効率的なフィルタリング
            this.filteredArticles = this.articles.filter(article => {
                // 検索条件のチェック（最も頻繁に変更される条件を最初に）
                if (searchTerm && !this.matchesSearch(article, searchTerm)) {
                    return false;
                }
                
                if (sourceFilter && article.source !== sourceFilter) {
                    return false;
                }
                
                if (sentimentFilter && article.sentiment_label !== sentimentFilter) {
                    return false;
                }
                
                return true;
            });
            
            this.currentPage = 1;
            this.renderArticles();
            this.renderStats();
            this.updateURL();
        } catch (error) {
            this.handleError('記事フィルタリング中にエラーが発生しました', error);
        }
    }
    
    matchesSearch(article, searchTerm) {
        // 検索フィールドのキャッシュ
        if (!article._searchCache) {
            article._searchCache = (article.title + ' ' + article.summary).toLowerCase();
        }
        
        return article._searchCache.includes(searchTerm);
    }
    
    renderArticles() {
        const container = this.domCache['articles-container'];
        if (!container) return;

        // フィルター適用時など、最初のページを描画する際はコンテナをクリア
        if (this.currentPage === 1) {
            container.innerHTML = '';
        }

        // 現在のページに表示する記事のスライスを計算
        const startIndex = (this.currentPage - 1) * this.articlesPerPage;
        const endIndex = this.currentPage * this.articlesPerPage;
        const articlesToShow = this.filteredArticles.slice(startIndex, endIndex);

        // フィルター結果が0件の場合のみ「記事なし」メッセージを表示
        if (this.filteredArticles.length === 0) {
            this.showEmptyState(container);
            return;
        }

        // 表示する記事がなくなれば、何もしない（無限スクロールの終端）
        if (articlesToShow.length === 0) {
            return;
        }

        // 現在のページの記事を描画（追加）
        this.renderArticlesBatch(container, articlesToShow);

        // スクロール位置の調整（新しい記事を読み込んだ場合）
        if (this.currentPage > 1) {
            this.smoothScrollAdjustment();
        }
    }
    
    renderArticlesBatch(container, articles) {
        const fragment = document.createDocumentFragment();
        const batchSize = 10;
        
        // バッチ処理でDOM操作を最適化
        const processBatch = (batchStart) => {
            const batchEnd = Math.min(batchStart + batchSize, articles.length);
            
            for (let i = batchStart; i < batchEnd; i++) {
                // 記事番号を計算（filteredArticlesリスト全体での順序）
                const articleIndex = this.filteredArticles.indexOf(articles[i]);
                const articleNumber = articleIndex + 1;
                const articleElement = this.createArticleElement(articles[i], articleNumber);
                fragment.appendChild(articleElement);
            }
            
            if (batchEnd < articles.length) {
                // 次のバッチを非同期で処理
                requestAnimationFrame(() => processBatch(batchEnd));
            } else {
                // 最後のバッチが完了したらDOMに追加
                container.appendChild(fragment);
                
                // パフォーマンスメトリクスを記録
                this.recordPerformanceMetrics(articles.length);
            }
        };
        
        processBatch(0);
    }
    
    smoothScrollAdjustment() {
        setTimeout(() => {
            const scrollOptions = {
                top: window.scrollY + 100,
                behavior: 'smooth'
            };
            
            // Safariでのスムーズスクロール対応
            if (typeof window.scrollTo === 'function') {
                window.scrollTo(scrollOptions);
            } else {
                window.scrollTo(scrollOptions.top, 0);
            }
        }, this.config.animationDuration);
    }
    
    createArticleElement(article, articleNumber = null) {
        const element = document.createElement('article');
        const sentimentLabel = article.sentiment_label || 'neutral';
        const sentimentClass = sentimentLabel.toLowerCase().replace('/', '-');
        element.className = `article-card ${sentimentClass}`;
        
        const sentimentIcon = this.getSentimentIcon(sentimentLabel);
        const publishedDate = this.formatDate(article.published_jst);
        const score = article.sentiment_score ? article.sentiment_score.toFixed(2) : 'N/A';
        
        // 記事番号の表示部分を追加
        const articleNumberHtml = articleNumber ? `<div class="article-number">${articleNumber}</div>` : '';
        
        element.innerHTML = `
            ${articleNumberHtml}
            <div class="article-content">
                <div class="article-header">
                    <h3 class="article-title">
                        <a href="${this.escapeHtml(article.url)}" target="_blank" rel="noopener">
                            ${this.escapeHtml(article.title)}
                        </a>
                    </h3>
                    <div class="sentiment-badge ${sentimentClass}" title="Sentiment: ${sentimentLabel} (Score: ${score})">
                        <span>${sentimentIcon}</span>
                        <span>${score}</span>
                    </div>
                </div>
                <div class="article-meta">
                    <span class="source-badge">[${this.escapeHtml(article.source)}]</span>
                    <span>${publishedDate}</span>
                </div>
                <p class="article-summary">${this.escapeHtml(article.summary || 'サマリーがありません')}</p>
            </div>
        `;
        
        // アニメーション効果
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            element.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, 50);
        
        return element;
    }
    
    showEmptyState(container) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📰</div>
                <h3>記事が見つかりませんでした</h3>
                <p>検索条件を変更してもう一度お試しください。</p>
                <button onclick="app.clearFilters()" class="refresh-button">
                    フィルターをクリア
                </button>
            </div>
        `;
    }
    
    clearFilters() {
        document.getElementById('search-input').value = '';
        document.getElementById('source-filter').value = '';
        document.getElementById('sentiment-filter').value = '';
        this.filterArticles();
    }
    
    renderStats() {
        this.updateElement('total-articles', this.filteredArticles.length);
        
        // ソース別統計
        const sourceStats = this.getSourceStats();
        this.updateElement('source-breakdown', this.formatSourceStats(sourceStats));
        
        // 感情別統計
        const sentimentStats = this.getSentimentStats();
        this.updateSentimentChart(sentimentStats);
    }
    
    getSourceStats() {
        const stats = {};
        this.filteredArticles.forEach(article => {
            const source = article.source || 'Unknown';
            stats[source] = (stats[source] || 0) + 1;
        });
        return stats;
    }
    
    getSentimentStats() {
        const stats = { Positive: 0, Negative: 0, Neutral: 0, Error: 0, 'N/A': 0 };
        this.filteredArticles.forEach(article => {
            const sentiment = article.sentiment_label || 'Neutral';
            if (stats.hasOwnProperty(sentiment)) {
                stats[sentiment]++;
            } else {
                // 未知の感情ラベルをNeutralとして扱う
                console.warn(`Unknown sentiment label: ${sentiment}, treating as Neutral`);
                stats['Neutral']++;
            }
        });
        console.log('感情統計:', stats);
        console.log('総記事数:', this.filteredArticles.length);
        return stats;
    }
    
    formatSourceStats(stats) {
        return Object.entries(stats)
            .map(([source, count]) => `${source}: ${count}`)
            .join(', ');
    }
    
    updateSentimentChart(stats) {
        const chartContainer = this.domCache['sentiment-chart'];
        if (!chartContainer) {
            console.warn('sentiment-chart element not found');
            return;
        }
        
        // シンプルな棒グラフ表示
        const total = Object.values(stats).reduce((sum, count) => sum + count, 0);
        if (total === 0) {
            chartContainer.innerHTML = '<p style="text-align: center; color: var(--pico-muted-color);">データがありません</p>';
            return;
        }
        
        console.log('Updating sentiment chart with stats:', stats, 'Total articles:', total);
        
        // パフォーマンス最適化: 統計が変更されていない場合はスキップ
        const statsKey = Object.values(stats).join(',');
        if (this.lastStatsKey === statsKey) {
            return;
        }
        this.lastStatsKey = statsKey;
        
        // DOM要素を効率的に構築
        const chartElement = document.createElement('div');
        chartElement.className = 'sentiment-chart-container';
        
        Object.entries(stats).forEach(([sentiment, count]) => {
            // すべての項目を表示（0の場合も含む）
            const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
            const color = this.getSentimentColor(sentiment);
            const icon = this.getSentimentIcon(sentiment);
            
            const rowElement = document.createElement('div');
            rowElement.className = 'sentiment-chart-row';
            
            const labelElement = document.createElement('span');
            labelElement.className = 'sentiment-label';
            labelElement.innerHTML = `<span style="margin-right: 4px;">${icon}</span>${sentiment}`;
            
            const barContainerElement = document.createElement('div');
            barContainerElement.className = 'sentiment-bar-container';
            
            const barElement = document.createElement('div');
            barElement.className = 'sentiment-bar';
            barElement.style.cssText = `width: ${percentage}%; background: ${color};`;
            
            const countElement = document.createElement('span');
            countElement.className = 'sentiment-count';
            countElement.textContent = count;
            
            const percentageElement = document.createElement('span');
            percentageElement.className = 'sentiment-percentage';
            percentageElement.textContent = `${percentage}%`;
            
            barContainerElement.appendChild(barElement);
            rowElement.appendChild(labelElement);
            rowElement.appendChild(barContainerElement);
            rowElement.appendChild(countElement);
            rowElement.appendChild(percentageElement);
            chartElement.appendChild(rowElement);
        });
        
        chartContainer.innerHTML = '';
        chartContainer.appendChild(chartElement);
    }
    
    getSentimentIcon(sentiment) {
        const icons = {
            'Positive': '😊',
            'Negative': '😠', 
            'Neutral': '😐',
            'Error': '⚠️',
            'N/A': '❓'
        };
        return icons[sentiment] || '🤔';
    }
    
    getSentimentColor(sentiment) {
        const colors = {
            'Positive': 'var(--sentiment-positive)',
            'Negative': 'var(--sentiment-negative)',
            'Neutral': 'var(--sentiment-neutral)',
            'Error': 'var(--sentiment-error)',
            'N/A': 'var(--sentiment-na)'
        };
        return colors[sentiment] || '#6b7280';
    }
    
    formatDate(date) {
        if (!date) return '日時不明';
        
        try {
            const d = new Date(date);
            return new Intl.DateTimeFormat('ja-JP', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }).format(d);
        } catch (error) {
            return String(date);
        }
    }
    
    updateLastUpdated() {
        if (this.articles.length > 0) {
            const latestDate = Math.max(...this.articles.map(a => {
                const date = new Date(a.published_jst);
                return isNaN(date.getTime()) ? 0 : date.getTime();
            }));
            
            if (latestDate > 0) {
                const formatted = this.formatDate(new Date(latestDate));
                this.updateElement('last-updated', formatted);
            }
        }
    }
    
    toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        // アニメーション効果を追加
        html.style.transition = 'background-color 0.3s ease, color 0.3s ease';
        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // アイコン更新とアニメーション
        const button = document.getElementById('theme-toggle');
        if (button) {
            button.style.transform = 'scale(0.9)';
            setTimeout(() => {
                button.textContent = newTheme === 'dark' ? '☀️' : '🌙';
                button.setAttribute('aria-label', newTheme === 'dark' ? 'ライトモードに切り替え' : 'ダークモードに切り替え');
                button.style.transform = 'scale(1)';
            }, 150);
        }
        
        // 感情分布チャートも更新（色が変わるため）
        this.renderStats();
    }
    
    loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 
                          (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        
        document.documentElement.setAttribute('data-theme', savedTheme);
        
        const button = document.getElementById('theme-toggle');
        if (button) {
            button.textContent = savedTheme === 'dark' ? '☀️' : '🌙';
        }
    }
    
    focusSearch() {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
    
    async refreshData() {
        try {
            this.setLoading(true);
            
            // ページをリロード（実際のAPIがある場合は、データのみ再取得）
            window.location.reload();
            
        } catch (error) {
            console.error('データの更新に失敗:', error);
            this.showError('データの更新に失敗しました。');
        } finally {
            this.setLoading(false);
        }
    }
    
    isNearBottom() {
        return window.innerHeight + window.scrollY >= document.body.offsetHeight - 1000;
    }
    
    loadMoreArticles() {
        if (this.currentPage * this.articlesPerPage < this.filteredArticles.length) {
            this.currentPage++;
            this.renderArticles();
        }
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        const loadingElement = document.getElementById('loading');
        const refreshButton = document.getElementById('refresh-button');
        
        if (loadingElement) {
            loadingElement.style.display = loading ? 'block' : 'none';
        }
        
        if (refreshButton) {
            refreshButton.disabled = loading;
            refreshButton.innerHTML = loading ? 
                '<span class="spinner" style="width: 16px; height: 16px; margin-right: 0.5rem;"></span>更新中...' :
                '🔄 更新';
        }
    }
    
    showError(message) {
        // 簡易エラー表示
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--sentiment-negative);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            z-index: 1000;
            max-width: 300px;
        `;
        errorDiv.textContent = message;
        
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }
    
    updateURL() {
        const params = new URLSearchParams();
        
        const search = this.getInputValue('search-input');
        const source = this.getInputValue('source-filter');
        const sentiment = this.getInputValue('sentiment-filter');
        
        if (search) params.set('search', search);
        if (source) params.set('source', source);
        if (sentiment) params.set('sentiment', sentiment);
        
        const newURL = params.toString() ? 
            `${window.location.pathname}?${params.toString()}` : 
            window.location.pathname;
        
        window.history.replaceState({}, '', newURL);
    }
    
    // ユーティリティ関数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    getInputValue(id) {
        const element = document.getElementById(id);
        return element ? element.value : '';
    }
    
    updateElement(id, content) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = content;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    recordPerformanceMetrics(articleCount) {
        // パフォーマンスメトリクスを記録
        if (performance.mark) {
            performance.mark('articles-rendered');
            
            // 開発環境でのみ詳細ログを出力
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                const renderTime = performance.now();
                console.log(`[Performance] ${articleCount} articles rendered in ${renderTime.toFixed(2)}ms`);
            }
        }
    }
}

// アプリケーション初期化
let app;

document.addEventListener('DOMContentLoaded', () => {
    app = new MarketNewsApp();
});

// グローバル関数（HTMLから呼び出し用）
window.clearFilters = () => {
    if (app) app.clearFilters();
};