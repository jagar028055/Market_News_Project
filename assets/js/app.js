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
            this.renderCharts();
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
        this.addEventListenerSafe('region-filter', 'change', () => this.filterArticles());
        this.addEventListenerSafe('category-filter', 'change', () => this.filterArticles());
        
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
            'theme-toggle', 'search-input', 'source-filter',
            'region-filter', 'category-filter', 'refresh-button', 'articles-container', 
            'loading', 'total-articles', 'region-chart', 
            'category-chart', 'last-updated'
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
            console.log('window.articlesData存在確認:', !!window.articlesData);
            console.log('window.articlesDataの型:', typeof window.articlesData);
            console.log('window.articlesDataは配列:', Array.isArray(window.articlesData));
            
            if (window.articlesData && Array.isArray(window.articlesData)) {
                this.articles = window.articlesData;
                console.log(`記事データを読み込みました: ${this.articles.length}件`);
                console.log('サンプル記事データ:', this.articles.slice(0, 2));
                
                // 地域・カテゴリデータの検証
                const regionsFound = new Set();
                const categoriesFound = new Set();
                this.articles.forEach(article => {
                    if (article.region) regionsFound.add(article.region);
                    if (article.category) categoriesFound.add(article.category);
                });
                console.log('発見された地域:', Array.from(regionsFound));
                console.log('発見されたカテゴリ:', Array.from(categoriesFound));
            } else {
                // フォールバック: 現在のHTMLから記事データを抽出
                console.warn('window.articlesDataが見つからないまたは配列ではありません');
                console.log('window.articlesDataの内容:', window.articlesData);
                this.articles = this.extractArticlesFromDOM();
                console.log('DOM抽出後の記事データ:', this.articles.slice(0, 2));
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
                    region: element.dataset.region || 'その他',
                    category: element.dataset.category || 'その他'
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
    
    
    filterArticles() {
        try {
            const searchTerm = this.getInputValue('search-input').toLowerCase();
            const sourceFilter = this.getInputValue('source-filter');
            const regionFilter = this.getInputValue('region-filter');
            const categoryFilter = this.getInputValue('category-filter');
            
            // パフォーマンス最適化: 検索条件が変更されていない場合はスキップ
            const filterKey = `${searchTerm}|${sourceFilter}|${regionFilter}|${categoryFilter}`;
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
                
                if (regionFilter && article.region !== regionFilter) {
                    return false;
                }
                
                if (categoryFilter && article.category !== categoryFilter) {
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
        element.className = 'article-card';
        
        const publishedDate = this.formatDate(article.published_jst);
        
        // 地域とカテゴリーのラベル
        const regionLabels = {
            'japan': '🇯🇵 日本',
            'usa': '🇺🇸 米国',
            'china': '🇨🇳 中国',
            'europe': '🇪🇺 欧州',
            'asia': '🌏 アジア',
            'global': '🌍 グローバル',
            'その他': '🌐 その他'
        };
        
        const categoryLabels = {
            '金融政策': '🏦 金融政策',
            '経済指標': '📊 経済指標',
            '企業業績': '📈 企業業績',
            '政治': '🏛️ 政治',
            '市場動向': '📉 市場動向',
            '国際情勢': '🌏 国際情勢',
            'その他': '📰 その他',
            // 旧カテゴリーとの互換性
            'stock': '📈 株式',
            'bond': '💰 債券',
            'forex': '💱 為替',
            'crypto': '₿ 暗号通貨',
            'commodity': '🛢️ 商品',
            'other': '📰 その他'
        };
        
        const regionLabel = regionLabels[article.region] || '🌐 その他';
        const categoryLabel = categoryLabels[article.category] || '📄 その他';
        
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
                </div>
                <div class="article-meta">
                    <span class="source-badge">[${this.escapeHtml(article.source)}]</span>
                    <span>${publishedDate}</span>
                    <span class="region-badge">${regionLabel}</span>
                    <span class="category-badge">${categoryLabel}</span>
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
        document.getElementById('region-filter').value = '';
        document.getElementById('category-filter').value = '';
        this.filterArticles();
    }
    
    renderStats() {
        this.updateElement('total-articles', this.filteredArticles.length);
        
        // ソース別統計
        const sourceStats = this.getSourceStats();
        this.updateElement('source-breakdown', this.formatSourceStats(sourceStats));
        
        // デバッグログ追加
        console.log('統計データのデバッグ:');
        console.log('記事数:', this.filteredArticles.length);
        console.log('サンプル記事:', this.filteredArticles.slice(0, 3));
        
        // 地域別統計とカテゴリ別統計はrenderCharts()で処理
    }
    
    getSourceStats() {
        const stats = {};
        this.filteredArticles.forEach(article => {
            const source = article.source || 'Unknown';
            stats[source] = (stats[source] || 0) + 1;
        });
        return stats;
    }
    
    
    getRegionStats() {
        const stats = {};
        this.filteredArticles.forEach(article => {
            const region = article.region || 'Unknown';
            stats[region] = (stats[region] || 0) + 1;
        });
        return stats;
    }
    
    getCategoryStats() {
        const stats = {};
        this.filteredArticles.forEach(article => {
            const category = article.category || 'Uncategorized';
            stats[category] = (stats[category] || 0) + 1;
        });
        return stats;
    }
    
    formatSourceStats(stats) {
        return Object.entries(stats)
            .map(([source, count]) => `${source}: ${count}`)
            .join(', ');
    }
    
    
    
    updateRegionChart(stats) {
        const chartContainer = this.domCache['region-chart'];
        if (!chartContainer) {
            console.warn('region-chart element not found');
            return;
        }
        
        const total = Object.values(stats).reduce((sum, count) => sum + count, 0);
        if (total === 0) {
            chartContainer.innerHTML = '<div class="no-data">データなし</div>';
            return;
        }
        
        const chartElement = document.createElement('div');
        chartElement.className = 'region-chart-container';
        
        Object.entries(stats).forEach(([region, count]) => {
            const percentage = ((count / total) * 100).toFixed(1);
            const color = this.getRegionColor(region);
            const icon = this.getRegionIcon(region);
            
            const rowElement = document.createElement('div');
            rowElement.className = 'chart-row';
            rowElement.innerHTML = `
                <span class="chart-label">${icon} ${region}</span>
                <div class="chart-bar-container">
                    <div class="chart-bar" style="width: ${percentage}%; background: ${color};"></div>
                </div>
                <span class="chart-count">${count}</span>
            `;
            chartElement.appendChild(rowElement);
        });
        
        chartContainer.innerHTML = '';
        chartContainer.appendChild(chartElement);
    }
    
    updateCategoryChart(stats) {
        const chartContainer = this.domCache['category-chart'];
        if (!chartContainer) {
            console.warn('category-chart element not found');
            return;
        }
        
        const total = Object.values(stats).reduce((sum, count) => sum + count, 0);
        if (total === 0) {
            chartContainer.innerHTML = '<div class="no-data">データなし</div>';
            return;
        }
        
        const chartElement = document.createElement('div');
        chartElement.className = 'category-chart-container';
        
        Object.entries(stats).forEach(([category, count]) => {
            const percentage = ((count / total) * 100).toFixed(1);
            const color = this.getCategoryColor(category);
            const icon = this.getCategoryIcon(category);
            
            const rowElement = document.createElement('div');
            rowElement.className = 'chart-row';
            rowElement.innerHTML = `
                <span class="chart-label">${icon} ${category}</span>
                <div class="chart-bar-container">
                    <div class="chart-bar" style="width: ${percentage}%; background: ${color};"></div>
                </div>
                <span class="chart-count">${count}</span>
            `;
            chartElement.appendChild(rowElement);
        });
        
        chartContainer.innerHTML = '';
        chartContainer.appendChild(chartElement);
    }
    
    getRegionIcon(region) {
        const icons = {
            'japan': '🇯🇵',
            'usa': '🇺🇸',
            'europe': '🇪🇺',
            'asia': '🌏',
            'global': '🌍',
            'Unknown': '❓'
        };
        return icons[region] || '🌐';
    }
    
    getRegionColor(region) {
        const colors = {
            'japan': '#e74c3c',
            'usa': '#3498db',
            'europe': '#2ecc71',
            'asia': '#f39c12',
            'global': '#9b59b6',
            'Unknown': '#95a5a6'
        };
        return colors[region] || '#6b7280';
    }
    
    getCategoryIcon(category) {
        const icons = {
            'markets': '📈',
            'economy': '💼',
            'corporate': '🏢',
            'technology': '💻',
            'energy': '⚡',
            'politics': '🏛️',
            'Uncategorized': '📄'
        };
        return icons[category] || '📰';
    }
    
    getCategoryColor(category) {
        const colors = {
            'markets': '#e74c3c',
            'economy': '#3498db',
            'corporate': '#2ecc71',
            'technology': '#9b59b6',
            'energy': '#f39c12',
            'politics': '#34495e',
            'Uncategorized': '#95a5a6'
        };
        return colors[category] || '#6b7280';
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
        // 修正: HTMLテンプレートで設定された実行時刻を保持するため、
        // JavaScript側での時刻上書きを無効化
        // これにより、システム実行時刻が正しく表示されるようになります
        console.log('最終更新時刻はHTMLテンプレートで設定された実行時刻を使用します');
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
        
        // 統計チャートも更新（色が変わるため）
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
        
        const region = this.getInputValue('region-filter');
        const category = this.getInputValue('category-filter');
        
        if (search) params.set('search', search);
        if (source) params.set('source', source);
        if (region) params.set('region', region);
        if (category) params.set('category', category);
        
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
    
    // 統計情報を計算
    calculateStats() {
        const regionStats = {};
        const categoryStats = {};
        const sourceStats = {};
        
        // デバッグログを追加
        console.log('統計データのデバッグ:');
        console.log('記事数:', this.filteredArticles.length);
        console.log('サンプル記事:', this.filteredArticles.slice(0, 3));
        
        this.filteredArticles.forEach(article => {
            // 地域統計
            const region = article.region || 'その他';
            regionStats[region] = (regionStats[region] || 0) + 1;
            
            // カテゴリ統計
            const category = article.category || 'その他';
            categoryStats[category] = (categoryStats[category] || 0) + 1;
            
            // ソース統計
            const source = article.source || 'Unknown';
            sourceStats[source] = (sourceStats[source] || 0) + 1;
        });
        
        console.log('地域統計:', regionStats);
        console.log('カテゴリ統計:', categoryStats);
        
        return {
            region: regionStats,
            category: categoryStats,
            source: sourceStats,
            total: this.filteredArticles.length
        };
    }
    
    // 統計情報の表示を更新
    renderStats() {
        try {
            const stats = this.calculateStats();
            
            // 総記事数を更新
            this.updateElement('total-articles', stats.total);
            
            // 地域別統計を更新
            this.updateRegionStats(stats.region);
            
            // カテゴリ別統計を更新
            this.updateCategoryStats(stats.category);
            
            // ソース別統計を更新
            this.updateSourceStats(stats.source);
            
        } catch (error) {
            console.error('統計表示更新エラー:', error);
        }
    }
    
    // 地域別統計の表示を更新
    updateRegionStats(regionStats) {
        const regionList = document.getElementById('region-stats-list');
        if (!regionList) return;
        
        const html = Object.entries(regionStats)
            .sort(([,a], [,b]) => b - a)
            .map(([region, count]) => `
                <div class="stat-item">
                    <span class="region-badge">${this.getRegionDisplayName(region)}</span>
                    <span class="count">${count}件</span>
                </div>
            `).join('');
        
        regionList.innerHTML = html;
    }
    
    // カテゴリ別統計の表示を更新
    updateCategoryStats(categoryStats) {
        const categoryList = document.getElementById('category-stats-list');
        if (!categoryList) return;
        
        const html = Object.entries(categoryStats)
            .sort(([,a], [,b]) => b - a)
            .map(([category, count]) => `
                <div class="stat-item">
                    <span class="category-badge">${category}</span>
                    <span class="count">${count}件</span>
                </div>
            `).join('');
        
        categoryList.innerHTML = html;
    }
    
    // ソース別統計の表示を更新
    updateSourceStats(sourceStats) {
        const sourceList = document.getElementById('source-stats-list');
        if (!sourceList) return;
        
        const html = Object.entries(sourceStats)
            .sort(([,a], [,b]) => b - a)
            .map(([source, count]) => `
                <div class="stat-item">
                    <span class="source-badge">${source}</span>
                    <span class="count">${count}件</span>
                </div>
            `).join('');
        
        sourceList.innerHTML = html;
    }
    
    // チャートを描画
    renderCharts() {
        try {
            const stats = this.calculateStats();
            this.renderRegionChart(stats.region);
            this.renderCategoryChart(stats.category);
            console.log('チャート描画完了 - 地域:', Object.keys(stats.region), 'カテゴリ:', Object.keys(stats.category));
        } catch (error) {
            console.error('チャート描画エラー:', error);
        }
    }
    
    // 地域分布チャートを描画
    renderRegionChart(regionStats) {
        const canvas = document.getElementById('region-chart');
        if (!canvas) {
            console.warn('地域分布チャート用のcanvas要素が見つかりません');
            return;
        }
        
        if (!window.Chart) {
            console.error('Chart.jsライブラリが読み込まれていません');
            return;
        }
        
        try {
            // 既存のチャートがあれば削除
            if (this.regionChart) {
                this.regionChart.destroy();
                this.regionChart = null;
            }
            
            const ctx = canvas.getContext('2d');
            const data = Object.entries(regionStats);
            
            if (data.length === 0) {
                console.info('地域分布データがありません');
                return;
            }
            
            this.regionChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.map(([region]) => this.getRegionDisplayName(region)),
                    datasets: [{
                        data: data.map(([, count]) => count),
                        backgroundColor: [
                            '#FF6384', // 日本 - 赤
                            '#36A2EB', // 米国 - 青  
                            '#FFCE56', // 中国 - 黄
                            '#4BC0C0', // 欧州 - 水色
                            '#9966FF'  // その他 - 紫
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
            console.log('地域分布チャートを正常に描画しました:', regionStats);
        } catch (error) {
            console.error('地域分布チャートの描画中にエラーが発生しました:', error);
            this.handleError('地域分布チャートの描画に失敗', error);
        }
    }
    
    // カテゴリ分布チャートを描画
    renderCategoryChart(categoryStats) {
        const canvas = document.getElementById('category-chart');
        if (!canvas) {
            console.warn('カテゴリ分布チャート用のcanvas要素が見つかりません');
            return;
        }
        
        if (!window.Chart) {
            console.error('Chart.jsライブラリが読み込まれていません');
            return;
        }
        
        try {
            // 既存のチャートがあれば削除
            if (this.categoryChart) {
                this.categoryChart.destroy();
                this.categoryChart = null;
            }
            
            const ctx = canvas.getContext('2d');
            const data = Object.entries(categoryStats);
            
            if (data.length === 0) {
                console.info('カテゴリ分布データがありません');
                return;
            }
            
            this.categoryChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.map(([category]) => category),
                    datasets: [{
                        data: data.map(([, count]) => count),
                        backgroundColor: [
                            '#FF9F40', // 金融政策
                            '#FF6384', // 経済指標  
                            '#36A2EB', // 企業業績
                            '#4BC0C0', // 市場動向
                            '#9966FF', // 地政学
                            '#C9CBCF'  // その他
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
            console.log('カテゴリ分布チャートを正常に描画しました:', categoryStats);
        } catch (error) {
            console.error('カテゴリ分布チャートの描画中にエラーが発生しました:', error);
            this.handleError('カテゴリ分布チャートの描画に失敗', error);
        }
    }
    
    // 地域表示名の取得
    getRegionDisplayName(region) {
        const regionMap = {
            'japan': '🇯🇵 日本',
            'usa': '🇺🇸 米国', 
            'china': '🇨🇳 中国',
            'europe': '🇪🇺 欧州',
            'その他': '🌍 その他'
        };
        return regionMap[region] || region;
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