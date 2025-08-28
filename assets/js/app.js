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
            // 🚨 デバッグ: 初期化開始時の詳細情報
            console.log('🚨 INIT START - Debugging all data sources');
            console.log('🚨 Initial window.articlesData:', window.articlesData?.length || 'NOT FOUND');
            console.log('🚨 Initial window.statisticsData:', window.statisticsData || 'NOT FOUND');
            
            this.loadTheme();
            this.setupEventListeners();
            await this.loadArticles();
            
            // 🚨 デバッグ: 記事読み込み後の状態確認
            console.log('🚨 After loadArticles():');
            console.log('🚨 this.articles.length:', this.articles?.length || 0);
            console.log('🚨 this.filteredArticles.length:', this.filteredArticles?.length || 0);
            console.log('🚨 Sample article data:', this.articles?.[0] || 'NO DATA');
            
            this.renderStats();
            // 🚨 デバッグ: SVGチャート描画前の確認
            console.log('🚨 Before renderCharts():');
            console.log('🚨 SVG rendering mode - no Chart.js dependency');
            console.log('🚨 Region container exists:', !!document.getElementById('region-chart'));
            console.log('🚨 Category container exists:', !!document.getElementById('category-chart'));
            
            this.renderCharts();
            this.renderArticles();
            this.updateLastUpdated();
            this.setupFormEventListeners();
        } catch (error) {
            console.error('🚨 CRITICAL INIT ERROR:', error);
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
            this.renderCharts();
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
            // データベース標準カテゴリ（日本語）
            '金融政策': '🏦 金融政策',
            '経済指標': '📊 経済指標',
            '企業業績': '📈 企業業績',
            '政治': '🏛️ 政治',
            '市場動向': '📉 市場動向',
            '国際情勢': '🌏 国際情勢',
            'その他': '📰 その他',
            // 旧カテゴリーとの後方互換性（廃止予定）
            'stock': '📈 企業業績',
            'bond': '💰 金融政策', 
            'forex': '💱 市場動向',
            'crypto': '₿ 市場動向',
            'commodity': '🛢️ 市場動向',
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
    
    // チャートエラー表示
    showChartError(chartId) {
        // 🚨 デバッグモード: エラー隠蔽を無効化して詳細情報を強制出力
        console.error('🚨 CHART ERROR DETECTED - showChartError() called for:', chartId);
        console.error('🚨 Canvas element:', document.getElementById(chartId));
        console.error('🚨 Chart.js available:', !!window.Chart);
        console.error('🚨 Chart.js version:', window.Chart?.version || 'N/A');
        console.error('🚨 Window statisticsData:', window.statisticsData);
        console.error('🚨 Window articlesData length:', window.articlesData?.length || 0);
        
        // エラー隠蔽を無効化 - 代わりに詳細エラー表示
        const canvas = document.getElementById(chartId);
        if (!canvas) {
            console.error('🚨 CRITICAL: Canvas element not found:', chartId);
            return;
        }
        
        const container = canvas.parentElement;
        if (!container) {
            console.error('🚨 CRITICAL: Canvas container not found for:', chartId);
            return;
        }
        
        // デバッグ用詳細エラー表示（隠蔽しない）
        const errorDiv = document.createElement('div');
        errorDiv.className = 'chart-error-debug';
        errorDiv.style.cssText = `
            display: block;
            padding: 10px;
            background: #ffebee;
            border: 2px solid #f44336;
            border-radius: 4px;
            color: #c62828;
            font-size: 0.8rem;
            font-family: monospace;
        `;
        errorDiv.innerHTML = `
            <strong>🚨 CHART ERROR DEBUG</strong><br>
            Chart ID: ${chartId}<br>
            Chart.js: ${!!window.Chart ? '✅' : '❌'}<br>
            Canvas: ${!!canvas ? '✅' : '❌'}<br>
            StatisticsData: ${!!window.statisticsData ? '✅' : '❌'}<br>
            Error: Check console for details
        `;
        
        // Canvas下に詳細エラー表示を追加（隠蔽しない）
        container.appendChild(errorDiv);
    }
    
    // データなしメッセージ表示
    showNoDataMessage(chartId) {
        // 🚨 デバッグモード: データなし隠蔽を無効化して詳細調査
        console.error('🚨 NO DATA MESSAGE - showNoDataMessage() called for:', chartId);
        console.error('🚨 Statistics Data:', window.statisticsData);
        console.error('🚨 Articles Data:', window.articlesData);
        console.error('🚨 Filtered Articles:', this.filteredArticles?.length || 0);
        
        const canvas = document.getElementById(chartId);
        if (!canvas) {
            console.error('🚨 CRITICAL: Canvas not found in showNoDataMessage:', chartId);
            return;
        }
        
        const container = canvas.parentElement;
        if (!container) {
            console.error('🚨 CRITICAL: Container not found in showNoDataMessage:', chartId);
            return;
        }
        
        // デバッグ用詳細データ不足表示
        const noDataDiv = document.createElement('div');
        noDataDiv.className = 'chart-no-data-debug';
        noDataDiv.style.cssText = `
            display: block;
            padding: 10px;
            background: #fff3e0;
            border: 2px solid #ff9800;
            border-radius: 4px;
            color: #e65100;
            font-size: 0.8rem;
            font-family: monospace;
        `;
        noDataDiv.innerHTML = `
            <strong>🚨 NO DATA DEBUG</strong><br>
            Chart ID: ${chartId}<br>
            Articles: ${window.articlesData?.length || 0}<br>
            Filtered: ${this.filteredArticles?.length || 0}<br>
            Statistics: ${JSON.stringify(window.statisticsData)}<br>
            Issue: No data available for chart
        `;
        
        container.appendChild(noDataDiv);
    }
    
    // 統計情報を計算
    calculateStats() {
        // 🚨 修正: window.statisticsDataを直接使用する
        console.log('🚨 CALCULATE STATS - Using window.statisticsData directly');
        console.log('🚨 window.statisticsData:', window.statisticsData);
        
        if (window.statisticsData) {
            // 既に生成された統計データを使用
            const stats = {
                region: window.statisticsData.region || {},
                category: window.statisticsData.category || {},
                source: window.statisticsData.source || {},
                total: this.filteredArticles?.length || window.articlesData?.length || 0
            };
            
            console.log('🚨 Using pre-generated statistics:', stats);
            return stats;
        }
        
        // フォールバック: 記事データから計算（従来の方式）
        console.log('🚨 Fallback: calculating from articles');
        const regionStats = {};
        const categoryStats = {};
        const sourceStats = {};
        
        const articles = this.filteredArticles || this.articles || [];
        console.log('🚨 Articles for calculation:', articles.length);
        
        articles.forEach(article => {
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
        
        console.log('🚨 Calculated stats - Region:', regionStats);
        console.log('🚨 Calculated stats - Category:', categoryStats);
        
        return {
            region: regionStats,
            category: categoryStats,
            source: sourceStats,
            total: articles.length
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
    
    // チャートを描画（フィルタされた記事に基づく）
    renderCharts() {
        try {
            // 🚨 DEBUG: データソース確認
            const articlesData = this.filteredArticles || this.articles || [];
            console.log('🚨 renderCharts() 開始 - 記事数:', articlesData.length);
            console.log('🚨 サンプル記事:', articlesData[0]);
            
            // 地域統計の計算
            const regionStats = {};
            const categoryStats = {};
            
            articlesData.forEach((article, index) => {
                if (index < 3) console.log(`🚨 記事${index}:`, article.title, article.summary);
                
                const region = this.analyzeRegion(article);
                const category = this.analyzeCategory(article);
                
                console.log(`🚨 記事${index} - 地域: ${region}, カテゴリ: ${category}`);
                
                regionStats[region] = (regionStats[region] || 0) + 1;
                categoryStats[category] = (categoryStats[category] || 0) + 1;
            });
            
            console.log('🚨 最終統計 - 地域:', regionStats);
            console.log('🚨 最終統計 - カテゴリ:', categoryStats);
            
            // チャート描画実行
            this.renderRegionChart(regionStats);
            this.renderCategoryChart(categoryStats);

            // 凡例の描画
            const regionColors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'];
            const categoryColors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'];
            this.generateCustomLegend('region-legend', regionStats, regionColors, (k) => this.getRegionDisplayName(k));
            this.generateCustomLegend('category-legend', categoryStats, categoryColors, (k) => this.getCategoryDisplayName(k));
            
            console.log('✅ チャート描画完了');
        } catch (error) {
            console.error('❌ チャート描画エラー:', error);
            console.error('❌ エラー詳細:', error.stack);
        }
    }
    
    // 地域分布チャートを円グラフで描画
    renderRegionChart(regionStats) {
        const container = document.getElementById('region-chart');
        if (!container) {
            console.error('❌ region-chart要素が見つからない');
            return;
        }
        
        console.log('🎯 地域円グラフ描画開始:', regionStats);
        
        const data = Object.entries(regionStats);
        
        if (data.length === 0) {
            container.innerHTML = '<div style="text-align:center;color:red;padding:2rem;">❌ 地域データが空です</div>';
            return;
        }
        
        // データを件数でソート
        data.sort(([,a], [,b]) => b - a);
        const total = data.reduce((sum, [,count]) => sum + count, 0);
        
        const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF'];
        
        const centerX = 60;
        const centerY = 60;
        const radius = 45;
        
        let svg = `
            <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <style>
                        .pie-slice { transition: all 0.3s ease; cursor: pointer; }
                        .pie-slice:hover { transform: scale(1.02); transform-origin: ${centerX}px ${centerY}px; }
                    </style>
                </defs>
        `;
        
        let currentAngle = -90; // 12時位置から開始
        
        data.forEach(([region, count], index) => {
            if (count === 0) return;
            
            const percentage = (count / total) * 100;
            const sliceAngle = (count / total) * 360;
            const color = colors[index % colors.length];
            const displayName = this.getRegionDisplayName(region);
            
            // 扇形のパス計算
            const startAngle = currentAngle * (Math.PI / 180);
            const endAngle = (currentAngle + sliceAngle) * (Math.PI / 180);
            
            const x1 = centerX + radius * Math.cos(startAngle);
            const y1 = centerY + radius * Math.sin(startAngle);
            const x2 = centerX + radius * Math.cos(endAngle);
            const y2 = centerY + radius * Math.sin(endAngle);
            
            const largeArc = sliceAngle > 180 ? 1 : 0;
            
            const pathData = [
                `M ${centerX} ${centerY}`,
                `L ${x1} ${y1}`,
                `A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`,
                'Z'
            ].join(' ');
            
            svg += `
                <path d="${pathData}" 
                      fill="${color}" 
                      class="pie-slice"
                      opacity="0.9">
                    <title>${displayName}: ${count}件 (${percentage.toFixed(1)}%)</title>
                </path>
            `;
            
            currentAngle += sliceAngle;
        });
        
        svg += '</svg>';
        
        // 凡例を生成
        let legend = '<div class="chart-legend-horizontal">';
        data.forEach(([region, count], index) => {
            if (count === 0) return;
            const percentage = ((count / total) * 100).toFixed(1);
            const displayName = this.getRegionDisplayName(region);
            const color = colors[index % colors.length];
            
            legend += `
                <div class="legend-item">
                    <span class="legend-color" style="background-color: ${color}"></span>
                    <span class="legend-text">${displayName}: ${count}件 (${percentage}%)</span>
                </div>
            `;
        });
        legend += '</div>';
        
        // 全体を統合して挿入
        const fullContent = `
            <div class="pie-chart-container">
                ${svg}
            </div>
            ${legend}
        `;
        
        container.innerHTML = fullContent;
        
        console.log('✅ 地域円グラフ描画完了');
        
        // Top3要約を更新
        this.updateRegionSummary(data);
    }
    
    // カテゴリ分布チャートを円グラフで描画
    renderCategoryChart(categoryStats) {
        const container = document.getElementById('category-chart');
        if (!container) {
            console.error('❌ category-chart要素が見つからない');
            return;
        }
        
        console.log('🎯 カテゴリ円グラフ描画開始:', categoryStats);
        
        const data = Object.entries(categoryStats);
        
        if (data.length === 0) {
            container.innerHTML = '<div style="text-align:center;color:red;padding:2rem;">❌ カテゴリデータが空です</div>';
            return;
        }
        
        // データを件数でソート
        data.sort(([,a], [,b]) => b - a);
        const total = data.reduce((sum, [,count]) => sum + count, 0);
        
        const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF'];
        
        const centerX = 60;
        const centerY = 60;
        const radius = 45;
        
        let svg = `
            <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <style>
                        .pie-slice { transition: all 0.3s ease; cursor: pointer; }
                        .pie-slice:hover { transform: scale(1.02); transform-origin: ${centerX}px ${centerY}px; }
                    </style>
                </defs>
        `;
        
        let currentAngle = -90; // 12時位置から開始
        
        data.forEach(([category, count], index) => {
            if (count === 0) return;
            
            const percentage = (count / total) * 100;
            const sliceAngle = (count / total) * 360;
            const color = colors[index % colors.length];
            const displayName = this.getCategoryDisplayName(category);
            
            // 扇形のパス計算
            const startAngle = currentAngle * (Math.PI / 180);
            const endAngle = (currentAngle + sliceAngle) * (Math.PI / 180);
            
            const x1 = centerX + radius * Math.cos(startAngle);
            const y1 = centerY + radius * Math.sin(startAngle);
            const x2 = centerX + radius * Math.cos(endAngle);
            const y2 = centerY + radius * Math.sin(endAngle);
            
            const largeArc = sliceAngle > 180 ? 1 : 0;
            
            const pathData = [
                `M ${centerX} ${centerY}`,
                `L ${x1} ${y1}`,
                `A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`,
                'Z'
            ].join(' ');
            
            svg += `
                <path d="${pathData}" 
                      fill="${color}" 
                      class="pie-slice"
                      opacity="0.9">
                    <title>${displayName}: ${count}件 (${percentage.toFixed(1)}%)</title>
                </path>
            `;
            
            currentAngle += sliceAngle;
        });
        
        svg += '</svg>';
        
        // 凡例を生成
        let legend = '<div class="chart-legend-horizontal">';
        data.forEach(([category, count], index) => {
            if (count === 0) return;
            const percentage = ((count / total) * 100).toFixed(1);
            const displayName = this.getCategoryDisplayName(category);
            const color = colors[index % colors.length];
            
            legend += `
                <div class="legend-item">
                    <span class="legend-color" style="background-color: ${color}"></span>
                    <span class="legend-text">${displayName}: ${count}件 (${percentage}%)</span>
                </div>
            `;
        });
        legend += '</div>';
        
        // 全体を統合して挿入
        const fullContent = `
            <div class="pie-chart-container">
                ${svg}
            </div>
            ${legend}
        `;
        
        container.innerHTML = fullContent;
        
        console.log('✅ カテゴリ円グラフ描画完了');
        
        // Top3要約を更新
        this.updateCategorySummary(data);
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
    
    // Chart.js読み込み待機（改良版）
    async waitForChartJS() {
        let attempts = 0;
        const maxAttempts = 100; // 10秒間待機に延長
        
        return new Promise((resolve, reject) => {
            const checkChart = () => {
                attempts++;
                if (attempts % 10 === 0) { // 1秒毎にログ出力
                    console.log(`📊 Chart.js読み込み確認 試行 ${attempts}/${maxAttempts} (${attempts/10}秒経過)`);
                }
                
                // より詳細なChart.js確認
                if (window.Chart && typeof window.Chart === 'function' && window.Chart.version) {
                    console.log(`✅ Chart.js読み込み完了 (バージョン: ${window.Chart.version})`);
                    resolve(true);
                } else if (attempts >= maxAttempts) {
                    console.error('❌ Chart.jsライブラリの読み込みに失敗（10秒タイムアウト）');
                    console.log('利用可能なライブラリ:', Object.keys(window).filter(key => key.toLowerCase().includes('chart')));
                    reject(new Error('Chart.js loading timeout after 10 seconds'));
                } else {
                    setTimeout(checkChart, 100);
                }
            };
            
            // 即座にチェック開始
            checkChart();
        });
    }
    
    // 地域表示名の取得
    getRegionDisplayName(region) {
        const regionMap = {
            'japan': '🇯🇵 日本',
            'usa': '🇺🇸 米国', 
            'china': '🇨🇳 中国',
            'europe': '🇪🇺 欧州',
            'asia': '🌏 アジア',
            'その他': '🌍 その他',
            'other': '🌍 その他',
            'global': '🌍 グローバル'
        };
        return regionMap[region] || region;
    }

    // カテゴリ表示名の取得
    getCategoryDisplayName(category) {
        const categoryMap = {
            'stock': '📈 株式',
            'bond': '📊 債券',
            'forex': '💱 為替',
            'crypto': '₿ 暗号通貨',
            'commodity': '🛢️ 商品',
            'other': '📰 その他'
        };
        return categoryMap[category] || category;
    }

    // カスタム凡例を生成
    generateCustomLegend(containerId, stats, colors, getDisplayName) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const data = Object.entries(stats);
        const total = data.reduce((sum, [, count]) => sum + count, 0);

        if (total === 0) {
            container.innerHTML = '<div class="legend-item"><span class="legend-label">データなし</span></div>';
            return;
        }

        const legendHTML = data
            .sort(([,a], [,b]) => b - a) // 件数順でソート
            .map(([key, count], index) => {
                const percentage = ((count / total) * 100).toFixed(1);
                const displayName = getDisplayName(key);
                const color = colors[index % colors.length];
                
                return `
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: ${color}"></div>
                        <span class="legend-label">${displayName}</span>
                        <span class="legend-value">${count}件<br>${percentage}%</span>
                    </div>
                `;
            }).join('');

        container.innerHTML = legendHTML;
    }

    // フォームイベントリスナー設定
    setupFormEventListeners() {
        // 検索機能
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.filterAndRenderArticles();
            }, this.config.debounceDelay));
        }
        
        // フィルター機能
        const sourceFilter = document.getElementById('source-filter');
        const regionFilter = document.getElementById('region-filter');
        const sortFilter = document.getElementById('sort-filter');
        
        if (sourceFilter) {
            sourceFilter.addEventListener('change', () => this.filterAndRenderArticles());
        }
        if (regionFilter) {
            regionFilter.addEventListener('change', () => this.filterAndRenderArticles());
        }
        if (sortFilter) {
            sortFilter.addEventListener('change', () => this.filterAndRenderArticles());
        }
        
        console.log('✅ フォームイベントリスナー設定完了');
    }

    // フィルタリングとチャート更新
    filterAndRenderArticles() {
        try {
            const searchTerm = document.getElementById('search-input')?.value.toLowerCase() || '';
            const sourceFilter = document.getElementById('source-filter')?.value || '';
            const regionFilter = document.getElementById('region-filter')?.value || '';
            const sortFilter = document.getElementById('sort-filter')?.value || 'date-desc';
            
            // フィルタリング
            this.filteredArticles = this.articles.filter(article => {
                const matchesSearch = !searchTerm || 
                    article.title.toLowerCase().includes(searchTerm) || 
                    (article.summary && article.summary.toLowerCase().includes(searchTerm));
                
                const matchesSource = !sourceFilter || article.source === sourceFilter;
                
                const matchesRegion = !regionFilter || this.analyzeRegion(article) === regionFilter;
                
                return matchesSearch && matchesSource && matchesRegion;
            });
            
            // ソート
            if (sortFilter === 'date-desc') {
                this.filteredArticles.sort((a, b) => new Date(b.published_jst) - new Date(a.published_jst));
            } else if (sortFilter === 'date-asc') {
                this.filteredArticles.sort((a, b) => new Date(a.published_jst) - new Date(b.published_jst));
            } else if (sortFilter === 'source') {
                this.filteredArticles.sort((a, b) => a.source.localeCompare(b.source));
            }
            
            // 記事表示を更新
            this.currentPage = 1;
            this.renderArticles();
            
            // チャートを更新
            this.renderCharts();
            
            console.log(`🔍 フィルター結果: ${this.filteredArticles.length}件 / ${this.articles.length}件`);
            
        } catch (error) {
            console.error('フィルタリングエラー:', error);
            this.handleError('フィルタリング処理に失敗', error);
        }
    }

    // 地域分析
    analyzeRegion(article) {
        const content = ((article.title || '') + ' ' + (article.summary || '')).toLowerCase();
        
        if (content.includes('日本') || content.includes('japan') || content.includes('東京') || content.includes('円') || content.includes('日銀')) {
            return 'japan';
        }
        if (content.includes('米国') || content.includes('america') || content.includes('usa') || content.includes('ドル') || content.includes('fed') || content.includes('フェド')) {
            return 'usa';
        }
        if (content.includes('欧州') || content.includes('europe') || content.includes('ユーロ') || content.includes('eu') || content.includes('ドイツ')) {
            return 'europe';
        }
        if (content.includes('中国') || content.includes('china') || content.includes('アジア') || content.includes('asia')) {
            return 'asia';
        }
        return 'global';
    }

    // カテゴリ分析
    analyzeCategory(article) {
        const content = ((article.title || '') + ' ' + (article.summary || '')).toLowerCase();
        
        if (content.includes('株') || content.includes('株式') || content.includes('株価') || content.includes('テスラ') || content.includes('企業')) {
            return 'stock';
        }
        if (content.includes('債券') || content.includes('金利') || content.includes('利回り') || content.includes('fed') || content.includes('日銀')) {
            return 'bond';
        }
        if (content.includes('為替') || content.includes('ドル') || content.includes('円') || content.includes('ユーロ') || content.includes('外為')) {
            return 'forex';
        }
        if (content.includes('暗号') || content.includes('仮想通貨') || content.includes('ビットコイン') || content.includes('crypto')) {
            return 'crypto';
        }
        if (content.includes('商品') || content.includes('原油') || content.includes('金') || content.includes('commodity')) {
            return 'commodity';
        }
        return 'other';
    }

    // デバウンス機能
    debounce(func, delay) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Top3要約更新 - 地域
    updateRegionSummary(data) {
        const summaryElement = document.getElementById('region-summary');
        if (!summaryElement || data.length === 0) return;
        
        const total = data.reduce((sum, [,count]) => sum + count, 0);
        const top3 = data.slice(0, 3).map(([region, count]) => {
            const percentage = ((count / total) * 100).toFixed(1);
            const displayName = this.getRegionDisplayName(region).replace(/🌍|🇯🇵|🇺🇸|🇪🇺|🌏/g, '').trim();
            return `${displayName}${percentage}%`;
        });
        
        summaryElement.textContent = top3.join(' / ');
    }

    // Top3要約更新 - カテゴリ
    updateCategorySummary(data) {
        const summaryElement = document.getElementById('category-summary');
        if (!summaryElement || data.length === 0) return;
        
        const total = data.reduce((sum, [,count]) => sum + count, 0);
        const top3 = data.slice(0, 3).map(([category, count]) => {
            const percentage = ((count / total) * 100).toFixed(1);
            const displayName = this.getCategoryDisplayName(category);
            return `${displayName}${percentage}%`;
        });
        
        summaryElement.textContent = top3.join(' / ');
    }
}

// アプリケーション初期化
let app;

// より確実な初期化処理
function initializeApp() {
    console.log('🚀 アプリケーション初期化開始');
    console.log('DOMContentLoaded状態:', document.readyState);
    
    if (app) {
        console.log('⚠️ アプリケーションは既に初期化済み');
        return;
    }
    
    try {
        app = new MarketNewsApp();
        window.app = app; // グローバル参照も設定
        console.log('✅ MarketNewsApp初期化完了');
    } catch (error) {
        console.error('❌ アプリケーション初期化エラー:', error);
    }
}

// 複数の初期化タイミングでサポート
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    // DOM既に読み込み済みの場合は即座に実行
    setTimeout(initializeApp, 100);
}

// フォールバック: window.onloadでも実行
window.addEventListener('load', () => {
    if (!app) {
        console.log('🔄 フォールバック初期化実行');
        setTimeout(initializeApp, 500);
    }
});

// グローバル関数（HTMLから呼び出し用）
window.clearFilters = () => {
    if (app) app.clearFilters();
};

// モーダル関数
window.openChartModal = (type) => {
    const modal = document.getElementById('chart-modal');
    const title = document.getElementById('modal-title');
    const chartContainer = document.getElementById('modal-chart');
    const legendContainer = document.getElementById('modal-legend');
    const summaryContainer = document.getElementById('modal-summary');
    
    if (!modal || !app) return;
    
    // タイトル設定
    title.textContent = type === 'region' ? '地域分布 - 詳細表示' : 'カテゴリ分布 - 詳細表示';
    
    // 元のチャートをコピー
    const sourceChart = document.getElementById(`${type}-chart`);
    const sourceLegend = document.getElementById(`${type}-legend`);
    const sourceSummary = document.getElementById(`${type}-summary`);
    
    if (sourceChart) {
        // チャートをコピーしてモーダル用の大型フォントを適用
        let chartContent = sourceChart.innerHTML;
        
        // SVG内のフォントサイズを大型化
        chartContent = chartContent.replace(/font-size:\s*36px/g, 'font-size: 40px');
        chartContent = chartContent.replace(/font-size:\s*32px/g, 'font-size: 36px');
        
        chartContainer.innerHTML = chartContent;
    }
    if (sourceLegend) {
        legendContainer.innerHTML = sourceLegend.innerHTML;
    }
    if (sourceSummary) {
        summaryContainer.innerHTML = `
            <div class="chart-summary-title">Top3${type === 'region' ? '地域' : 'カテゴリ'}</div>
            <p class="chart-summary-text">${sourceSummary.textContent}</p>
        `;
    }
    
    // モーダル表示
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
};

window.closeChartModal = () => {
    const modal = document.getElementById('chart-modal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
};

// ESCキーでモーダルを閉じる
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        window.closeChartModal();
    }
});
