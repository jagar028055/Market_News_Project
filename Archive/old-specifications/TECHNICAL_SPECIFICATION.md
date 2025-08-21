# マーケットニュースシステム 技術仕様書

## 1. システムアーキテクチャ

### 1.1 概要
本システムは静的Webサイトとして構築され、GitHub Pagesでホストされる。クライアントサイドJavaScriptによる動的コンテンツ生成と、JSONファイルによるデータ管理を採用している。

### 1.2 アーキテクチャ図
```
┌─────────────────────────────────────┐
│            クライアント             │
│  ┌─────────────┐ ┌─────────────┐    │
│  │ index.html  │ │pro-summary. │    │
│  │   (メイン)   │ │html(詳細)  │    │
│  └─────────────┘ └─────────────┘    │
│         │                │         │
│  ┌─────────────┐ ┌─────────────┐    │
│  │   app.js    │ │   custom.css│    │
│  │ (メイン制御) │ │  (スタイル) │    │
│  └─────────────┘ └─────────────┘    │
│         │                           │
│  ┌─────────────────────────────┐    │
│  │      data/articles.json     │    │
│  │       (記事データ)          │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
          │
   ┌─────────────┐
   │GitHub Pages │
   │   (CDN)     │
   └─────────────┘
```

### 1.3 技術スタック

#### フロントエンド
- **HTML5**: セマンティックマークアップ
- **CSS3**: PicoCSS + カスタムCSS
- **JavaScript (ES6+)**: 動的機能実装
- **JSON**: データ格納・交換形式

#### ホスティング・インフラ
- **GitHub Pages**: 静的サイトホスティング
- **Git**: バージョン管理
- **GitHub Actions**: CI/CD（オプション）

#### 外部依存
- **PicoCSS v2.0.6**: CSSフレームワーク
- **Google Gemini API**: AI要約生成（開発時）

## 2. ファイル構成

### 2.1 プロジェクト構造
```
Market_News_Project/
├── index.html                 # メインページ
├── pro-summary.html          # Pro要約ページ
├── manifest.json             # PWA設定
├── data/
│   └── articles.json         # 記事データ
├── assets/
│   ├── css/
│   │   └── custom.css        # カスタムスタイル
│   ├── js/
│   │   └── app.js           # メインロジック
│   ├── audio/               # 音声ファイル（Podcast用）
│   └── config/              # 設定ファイル
├── src/                     # Python処理スクリプト
│   ├── core/               # コア機能
│   ├── html/               # HTML生成
│   ├── podcast/            # Podcast機能
│   └── wordcloud/          # ワードクラウド機能
├── tests/                  # テストファイル
└── docs/                   # ドキュメント
```

### 2.2 コアファイル詳細

#### 2.2.1 index.html
- **役割**: システムのメインエントリーポイント
- **機能**: Flash要約一覧、検索・フィルタリング、統計表示
- **サイズ**: 約15KB（95%削減達成）
- **特徴**: レスポンシブデザイン、PWA対応

#### 2.2.2 pro-summary.html
- **役割**: Gemini 2.5 Pro詳細分析ページ
- **機能**: 高度な市場分析、予測、リスク評価
- **サイズ**: 約20KB
- **特徴**: インタラクティブな分析表示

#### 2.2.3 data/articles.json
- **役割**: 記事データの集中管理
- **形式**: JSON配列
- **サイズ**: 約100KB
- **更新**: Python スクリプトによる自動生成

#### 2.2.4 assets/js/app.js
- **役割**: メインページのロジック制御
- **機能**: データ読み込み、フィルタリング、DOM操作
- **サイズ**: 約8KB
- **特徴**: エラーハンドリング、パフォーマンス最適化

## 3. データ設計

### 3.1 記事データスキーマ
```json
{
  "title": "string",           // 記事タイトル
  "url": "string",            // 記事URL
  "summary": "string",        // Flash要約（200-300文字）
  "source": "string",         // ニュースソース ("Reuters"|"Bloomberg")
  "published_jst": "string"   // ISO 8601形式の日本時間
}
```

### 3.2 統計データ構造
```javascript
// 動的計算される統計情報
const stats = {
  totalArticles: number,      // 総記事数
  lastUpdated: Date,          // 最終更新時刻
  sourceDistribution: {       // ソース分布
    "Reuters": number,
    "Bloomberg": number
  },
  regionDistribution: {       // 地域分布（未実装）
    "japan": number,
    "usa": number,
    "europe": number,
    "asia": number,
    "global": number
  }
}
```

### 3.3 ユーザー設定データ
```javascript
// LocalStorageに保存される設定
const userSettings = {
  theme: "light"|"dark",      // テーマ設定
  articlesPerPage: number,    // 表示件数
  defaultSort: string,        // デフォルト並び順
  favoriteFilters: string[]   // お気に入りフィルター
}
```

## 4. API設計

### 4.1 内部API（JavaScript関数）

#### 4.1.1 データ読み込み
```javascript
async loadArticlesData(): Promise<Article[]>
// 記事データをJSONファイルから読み込み
// 戻り値: Article オブジェクトの配列
// エラーハンドリング: ネットワークエラー、JSON解析エラー
```

#### 4.1.2 フィルタリング
```javascript
filterArticles(searchTerm: string, source: string, sort: string): Article[]
// 記事の絞り込みと並び替え
// パラメータ: 検索語、ソース、並び順
// 戻り値: フィルタリング済み記事配列
```

#### 4.1.3 統計計算
```javascript
calculateStats(articles: Article[]): Statistics
// 記事配列から統計情報を計算
// 戻り値: 統計オブジェクト
```

### 4.2 外部API依存

#### 4.2.1 PicoCSS CDN
```
https://cdn.jsdelivr.net/npm/@picocss/pico@2.0.6/css/pico.min.css
```

#### 4.2.2 Gemini API（開発時のみ）
- Pro要約生成時に使用
- 静的サイトでは事前生成済みコンテンツを使用

## 5. パフォーマンス設計

### 5.1 読み込み最適化
- **HTMLファイルサイズ**: 15KB（従来の93%削減）
- **JSONデータ遅延読み込み**: 初期表示高速化
- **CSS/JSの最小化**: 開発時の圧縮・最適化
- **CDN活用**: PicoCSSの外部CDN利用

### 5.2 レンダリング最適化
- **仮想DOM不使用**: 軽量なDOM操作
- **デバウンス機能**: 検索入力の最適化
- **遅延実行**: 統計計算の最適化
- **メモリ管理**: 不要なオブジェクトの解放

### 5.3 キャッシュ戦略
```javascript
// ブラウザキャッシュ設定
const cacheHeaders = {
  'Cache-Control': 'public, max-age=3600',  // 1時間キャッシュ
  'ETag': 'auto-generated',                 // ETag による更新確認
}
```

## 6. セキュリティ設計

### 6.1 フロントエンドセキュリティ
- **XSS対策**: textContent 使用、innerHTML 制限
- **CSP設定**: Content Security Policy 実装
- **HTTPS強制**: GitHub Pages デフォルト対応

### 6.2 データセキュリティ
- **入力検証**: ユーザー入力の適切なエスケープ
- **外部リンク**: rel="noopener noreferrer" 設定
- **機密データなし**: 個人情報の非保存

### 6.3 CSP設定例
```html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; 
               script-src 'self' 'unsafe-inline';">
```

## 7. エラーハンドリング設計

### 7.1 エラータイプ分類
- **ネットワークエラー**: JSON読み込み失敗
- **データエラー**: JSON解析失敗、不正な形式
- **UIエラー**: DOM操作失敗、要素不存在
- **ユーザーエラー**: 無効な検索条件

### 7.2 エラー処理戦略
```javascript
// グローバルエラーハンドラー
window.addEventListener('error', (event) => {
  console.error('Application Error:', event.error);
  showUserFriendlyError(event.error);
});

// Promise エラーハンドリング
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled Promise Rejection:', event.reason);
  event.preventDefault();
});
```

### 7.3 ユーザーへのエラー表示
- **非侵入的**: トーストメッセージ、インライン表示
- **具体的**: エラーの原因と解決方法を明示
- **回復可能**: リトライボタン、代替手段の提供

## 8. モニタリング・ログ設計

### 8.1 クライアントサイドログ
```javascript
// ログレベル
const LOG_LEVELS = {
  ERROR: 'error',
  WARN: 'warn', 
  INFO: 'info',
  DEBUG: 'debug'
};

// ログ出力
function log(level, message, data = null) {
  const timestamp = new Date().toISOString();
  console[level](`[${timestamp}] ${message}`, data);
}
```

### 8.2 パフォーマンス監視
```javascript
// 読み込み時間測定
performance.mark('data-load-start');
await loadArticlesData();
performance.mark('data-load-end');
performance.measure('data-load-time', 'data-load-start', 'data-load-end');
```

### 8.3 ユーザー行動分析
- **ページビュー**: ページ遷移の追跡
- **検索クエリ**: 検索パターンの分析
- **滞在時間**: ユーザーエンゲージメント測定
- **エラー率**: システム品質の監視

## 9. デプロイメント設計

### 9.1 GitHub Pages設定
```yaml
# _config.yml (必要に応じて)
plugins:
  - jekyll-sitemap
  - jekyll-feed

# GitHub Actions ワークフロー例
name: Deploy to GitHub Pages
on:
  push:
    branches: [ main ]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./
```

### 9.2 ビルドプロセス
1. **ファイル検証**: HTML/CSS/JS構文チェック
2. **JSON検証**: 記事データの整合性確認
3. **パフォーマンステスト**: 読み込み速度の測定
4. **クロスブラウザテスト**: 対応ブラウザでの動作確認

### 9.3 ロールバック戦略
- **Git履歴**: コミット単位での巻き戻し
- **ブランチ戦略**: feature → main の段階的マージ
- **緊急対応**: hotfix ブランチでの即座修正

## 10. 拡張性設計

### 10.1 モジュール化
```javascript
// 機能別モジュール分離
const ArticleManager = {
  load: async () => {},
  filter: () => {},
  display: () => {}
};

const StatisticsManager = {
  calculate: () => {},
  render: () => {}
};

const UIManager = {
  showLoading: () => {},
  hideLoading: () => {},
  showError: () => {}
};
```

### 10.2 設定の外部化
```javascript
// config.js
const APP_CONFIG = {
  DATA_URL: 'data/articles.json',
  MAX_ARTICLES: 1000,
  DEBOUNCE_DELAY: 300,
  RETRY_ATTEMPTS: 3,
  CACHE_DURATION: 3600000 // 1時間
};
```

### 10.3 プラグイン対応設計
```javascript
// プラグインシステム（将来拡張）
const PluginManager = {
  plugins: [],
  register: (plugin) => {},
  execute: (hook, data) => {},
  hooks: ['beforeLoad', 'afterLoad', 'beforeRender', 'afterRender']
};
```

---

**文書管理情報**
- 作成日: 2025年8月15日
- バージョン: 1.0
- 更新日: 2025年8月15日
- 承認者: 技術リード
- 次回レビュー予定: 2025年9月15日