# ポッドキャスト機能改善 - 技術仕様書

**Project**: Market News Podcast Enhancement  
**Version**: 1.0  
**Date**: 2025-08-14  
**Author**: Technical Team

---

## 1. システムアーキテクチャ概要

### 1.1 全体アーキテクチャ
```
┌─────────────────────┐    ┌─────────────────────┐
│   User Interface    │    │   LINE Messaging   │
│   (Browser/Mobile)  │    │      API            │
└──────────┬──────────┘    └──────────┬──────────┘
           │                          │
           ▼                          ▼
┌─────────────────────────────────────────────────┐
│              GitHub Pages                      │
│  ┌─────────────────────────────────────────────┤
│  │     Static Web Application                  │
│  │  ┌──────────────┐ ┌──────────────────────┐  │
│  │  │ index.html   │ │ /podcast/index.html  │  │
│  │  │ (Dashboard)  │ │ (Podcast Portal)     │  │
│  │  └──────────────┘ └──────────────────────┘  │
│  └─────────────────────────────────────────────┤
│  │           Static Assets                     │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────────┐    │
│  │  │  CSS    │ │   JS    │ │   Audio     │    │
│  │  │ Files   │ │ Files   │ │   Files     │    │
│  │  └─────────┘ └─────────┘ └─────────────┘    │
│  └─────────────────────────────────────────────┤
│  │              RSS Feed                       │
│  │            (feed.xml)                       │
└─────────────────────────────────────────────────┘
           ▲                          ▲
           │                          │
┌──────────┴──────────┐    ┌──────────┴──────────┐
│   GitHub Actions    │    │   Podcast Generator │
│   (CI/CD Pipeline)  │    │    (Python App)     │
└─────────────────────┘    └─────────────────────┘
```

### 1.2 技術スタック
```yaml
Frontend:
  - HTML5 (Semantic markup)
  - CSS3 (PicoCSS framework + Custom styles)
  - JavaScript ES6+ (Vanilla JS, no framework)
  - Progressive Web App (PWA) features

Backend:
  - Python 3.11+ (Existing podcast generation)
  - GitHub Actions (CI/CD and automation)
  - Static Site Generation

Audio:
  - HTML5 Audio API
  - MP3 format (optimized for web)
  - Streaming support

Messaging:
  - LINE Messaging API
  - Flex Message format
  - Rich media support

Hosting:
  - GitHub Pages (Static hosting)
  - CDN via GitHub's infrastructure
```

## 2. データモデル設計

### 2.1 Episode Data Model
```typescript
interface PodcastEpisode {
  id: string;                    // "episode_20250814_070734"
  title: string;                 // "マーケットニュース 2025年08月14日"
  description: string;           // エピソードの説明
  publishedAt: string;           // ISO 8601 format
  duration: number;              // 秒単位
  fileSize: number;              // バイト単位
  audioUrl: string;              // MP3ファイルのURL
  articles: Article[];           // 含まれる記事情報
  highlights: string[];          // ハイライト情報
  categories: string[];          // カテゴリタグ
  sentiment: 'Positive' | 'Negative' | 'Neutral'; // 全体的なセンチメント
  timestamp: {
    [articleIndex: number]: number; // 各記事の開始秒数
  };
}

interface Article {
  title: string;
  summary: string;
  url: string;
  source: string;
  publishedAt: string;
  sentiment: 'Positive' | 'Negative' | 'Neutral';
  startTime?: number;            // ポッドキャスト内での開始時間（秒）
  endTime?: number;              // ポッドキャスト内での終了時間（秒）
}
```

### 2.2 UI State Management
```typescript
interface PodcastPlayerState {
  currentEpisode: PodcastEpisode | null;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  playbackRate: number;
  isLoading: boolean;
  error: string | null;
}

interface PodcastListState {
  episodes: PodcastEpisode[];
  filteredEpisodes: PodcastEpisode[];
  currentPage: number;
  pageSize: number;
  sortBy: 'date' | 'title' | 'duration';
  sortOrder: 'asc' | 'desc';
  searchQuery: string;
  filterCategory: string;
  isLoading: boolean;
}
```

## 3. API設計

### 3.1 Static Data API (JSON Files)
```
/podcast/
├── episodes.json          # エピソード一覧
├── latest.json           # 最新エピソード情報
└── episode/
    ├── 20250814.json     # 個別エピソード詳細
    └── ...
```

### 3.2 episodes.json Structure
```json
{
  "version": "1.0",
  "lastUpdated": "2025-08-14T16:07:34+09:00",
  "totalEpisodes": 150,
  "episodes": [
    {
      "id": "episode_20250814_070734",
      "title": "マーケットニュース 2025年08月14日",
      "description": "本日のマーケットニュースポッドキャスト（3件の記事を解説）",
      "publishedAt": "2025-08-14T16:07:34+09:00",
      "duration": 420,
      "fileSize": 333340,
      "audioUrl": "https://jagar028055.github.io/Market_News_Project/podcast/market_news_20250814.mp3",
      "highlights": [
        "日経平均、3日続伸で年初来高値更新",
        "米FRB、政策金利を据え置き決定",
        "原油価格急落、需要懸念で約3%下落"
      ],
      "categories": ["株式", "金利", "商品"],
      "sentiment": "Neutral",
      "articleCount": 3
    }
  ]
}
```

### 3.3 LINE Messaging API Integration
```typescript
interface FlexMessage {
  type: "flex";
  altText: string;
  contents: {
    type: "bubble" | "carousel";
    body: FlexComponent[];
    footer?: FlexComponent[];
  };
}

interface PodcastNotificationMessage {
  type: "flex";
  altText: "新しいポッドキャストエピソードが配信されました";
  contents: {
    type: "bubble";
    hero: {
      type: "image";
      url: string;        // ポッドキャスト画像
      size: "full";
    };
    body: {
      type: "box";
      layout: "vertical";
      contents: [
        // タイトル、説明、ハイライト
      ];
    };
    footer: {
      type: "box";
      layout: "vertical";
      contents: [
        // アクションボタン（再生、あとで聞く、共有）
      ];
    };
  };
}
```

## 4. フロントエンド設計

### 4.1 コンポーネント構造
```
/assets/js/
├── podcast/
│   ├── player.js          # 音声プレイヤー制御
│   ├── episodeList.js     # エピソード一覧
│   ├── search.js          # 検索・フィルタ機能
│   ├── ui.js             # UI制御
│   └── api.js            # データ取得
├── components/
│   ├── audioPlayer.js     # HTML5 Audio API wrapper
│   ├── modal.js          # モーダルダイアログ
│   └── toast.js          # 通知表示
└── utils/
    ├── time.js           # 時間フォーマット
    ├── storage.js        # LocalStorage操作
    └── analytics.js      # 使用状況分析
```

### 4.2 CSS Architecture (BEM + Utility)
```scss
// Base styles
@import 'base/reset';
@import 'base/typography';
@import 'base/colors';

// Components
@import 'components/podcast-player';
@import 'components/episode-card';
@import 'components/search-bar';
@import 'components/filter-tabs';

// Layout
@import 'layout/dashboard';
@import 'layout/podcast-page';
@import 'layout/responsive';

// Utilities
@import 'utilities/spacing';
@import 'utilities/display';
@import 'utilities/accessibility';
```

### 4.3 Progressive Enhancement Strategy
```javascript
// Core functionality (works without JS)
// - Static HTML with audio links
// - Basic CSS styling
// - Progressive enhancement layers

// Enhancement Layer 1: Basic interactivity
// - Click handlers for play/pause
// - Simple UI feedback

// Enhancement Layer 2: Rich features
// - HTML5 Audio API integration
// - Local storage for preferences
// - Search and filtering

// Enhancement Layer 3: Advanced features
// - Service Worker for offline support
// - Push notifications
// - Analytics tracking
```

## 5. バックエンド統合

### 5.1 既存システム拡張
```python
# 新規追加ファイル
src/podcast/web/
├── __init__.py
├── web_generator.py      # Web統合用ファイル生成
├── json_generator.py     # JSON API生成
└── template_engine.py    # HTMLテンプレート生成

# 拡張対象ファイル
src/podcast/integration/podcast_integration_manager.py
src/podcast/publisher/github_pages_publisher.py
```

### 5.2 Web Generator Class
```python
class PodcastWebGenerator:
    """ポッドキャストWeb統合機能"""
    
    def generate_episode_json(self, episode_info: dict, articles: list) -> str:
        """エピソード情報のJSON生成"""
    
    def update_episodes_list(self, new_episode: dict) -> None:
        """エピソード一覧の更新"""
    
    def generate_dashboard_data(self) -> dict:
        """ダッシュボード用データ生成"""
    
    def create_podcast_pages(self) -> None:
        """ポッドキャスト専用ページ生成"""
```

### 5.3 GitHub Actions Integration
```yaml
# .github/workflows/podcast-broadcast.yml 拡張
- name: Generate Web Assets
  run: |
    python -c "
    from src.podcast.web.web_generator import PodcastWebGenerator
    generator = PodcastWebGenerator()
    generator.update_all_web_assets()
    "

- name: Deploy Enhanced Site
  run: |
    # 既存のデプロイ処理 + Web assets
    cp -r podcast_web_assets/* public/
```

## 6. パフォーマンス最適化

### 6.1 音声ファイル最適化
```yaml
Audio Optimization:
  Format: MP3 (128kbps, mono)
  Progressive Download: Supported
  Range Requests: Enabled
  Compression: gzip/brotli for metadata
  
Caching Strategy:
  Audio Files: Cache-Control: max-age=2592000 (30 days)
  Metadata JSON: Cache-Control: max-age=3600 (1 hour)
  Static Assets: Cache-Control: max-age=86400 (1 day)
```

### 6.2 Frontend Optimization
```javascript
// Lazy loading strategy
const lazyLoadEpisodes = () => {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        loadEpisodeDetails(entry.target.dataset.episodeId);
      }
    });
  });
  
  document.querySelectorAll('[data-episode-id]')
    .forEach(el => observer.observe(el));
};

// Resource preloading
const preloadCriticalResources = () => {
  const link = document.createElement('link');
  link.rel = 'preload';
  link.href = '/podcast/latest.json';
  link.as = 'fetch';
  document.head.appendChild(link);
};
```

## 7. セキュリティ仕様

### 7.1 Content Security Policy
```http
Content-Security-Policy: 
  default-src 'self';
  script-src 'self' 'unsafe-inline';
  style-src 'self' 'unsafe-inline' cdn.jsdelivr.net;
  img-src 'self' data: https:;
  media-src 'self' https://jagar028055.github.io;
  connect-src 'self' https://api.line.me;
```

### 7.2 データ保護
```javascript
// No personal data collection
// Local storage only for preferences
const ALLOWED_STORAGE_KEYS = [
  'podcast_volume',
  'podcast_playback_rate',
  'podcast_theme_preference',
  'podcast_last_played'
];

const sanitizeUserInput = (input) => {
  return input.replace(/[<>]/g, '').trim();
};
```

## 8. 監視・分析

### 8.1 Analytics Implementation
```javascript
// プライバシーに配慮した匿名分析
const analytics = {
  trackEvent(category, action, label = null) {
    // GitHub Pages環境での軽量分析
    const event = {
      category,
      action,
      label,
      timestamp: Date.now(),
      // 個人情報は含まない
    };
    
    // Local aggregation and periodic reporting
    this.aggregateEvent(event);
  },
  
  trackPlay(episodeId) {
    this.trackEvent('podcast', 'play', episodeId);
  },
  
  trackComplete(episodeId, duration) {
    this.trackEvent('podcast', 'complete', episodeId);
  }
};
```

### 8.2 Error Monitoring
```javascript
// エラートラッキング
window.addEventListener('error', (event) => {
  const errorInfo = {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    timestamp: Date.now()
  };
  
  // ローカル保存（個人情報なし）
  console.error('Podcast Error:', errorInfo);
});

// Audio-specific error handling
const handleAudioError = (audio, episodeId) => {
  audio.addEventListener('error', (e) => {
    const errorType = [
      'MEDIA_ERR_ABORTED',
      'MEDIA_ERR_NETWORK', 
      'MEDIA_ERR_DECODE',
      'MEDIA_ERR_SRC_NOT_SUPPORTED'
    ][audio.error.code - 1] || 'UNKNOWN_ERROR';
    
    console.error(`Audio Error (${episodeId}):`, errorType);
  });
};
```

## 9. 運用・保守

### 9.1 自動化された品質チェック
```yaml
# .github/workflows/quality-check.yml
name: Podcast Quality Check
on:
  pull_request:
    paths: ['src/podcast/**', 'assets/**']

jobs:
  quality-check:
    steps:
      - name: Audio file validation
        run: |
          python scripts/validate_audio_files.py
          
      - name: HTML validation
        run: |
          npm install -g html-validate
          html-validate index.html podcast/index.html
          
      - name: Accessibility check
        run: |
          npm install -g pa11y
          pa11y http://localhost:3000
```

### 9.2 Performance Monitoring
```javascript
// Core Web Vitals tracking
const measurePerformance = () => {
  // Largest Contentful Paint
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    const lastEntry = entries[entries.length - 1];
    console.log('LCP:', lastEntry.startTime);
  }).observe({entryTypes: ['largest-contentful-paint']});
  
  // First Input Delay
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    entries.forEach((entry) => {
      console.log('FID:', entry.processingStart - entry.startTime);
    });
  }).observe({entryTypes: ['first-input']});
};
```

## 10. 配備・リリース戦略

### 10.1 段階的ロールアウト
```yaml
Deployment Strategy:
  Phase 1: Feature flag による段階的有効化
    - 10% users (test group)
    - Monitor performance and errors
    
  Phase 2: Full deployment
    - 100% users
    - Complete monitoring
    
Rollback Strategy:
  - Git revert capability
  - Feature flag disable
  - Static fallback pages
```

### 10.2 バージョン管理
```json
{
  "version": "1.0.0",
  "apiVersion": "1",
  "compatibility": {
    "minimumBrowsers": {
      "chrome": "90",
      "firefox": "88",
      "safari": "14",
      "edge": "90"
    }
  }
}
```

---

**承認者**: Technical Lead  
**最終更新**: 2025-08-14  
**次回レビュー**: 実装開始前