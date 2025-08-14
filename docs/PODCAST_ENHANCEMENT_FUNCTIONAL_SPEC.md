# ポッドキャスト機能改善 - 機能仕様書

**Project**: Market News Podcast Enhancement  
**Version**: 1.0  
**Date**: 2025-08-14  
**Author**: UX/UI Team

---

## 1. 機能概要

### 1.1 機能マップ
```
Market News Podcast Enhancement
├── Phase 1: 統合ダッシュボード
│   ├── メインページ統合
│   ├── 音声プレイヤー
│   ├── エピソード情報表示
│   └── レスポンシブ対応
├── Phase 2: スマート通知
│   ├── LINE Flex Message
│   ├── リッチカード表示
│   ├── アクションボタン
│   └── ハイライト表示
├── Phase 3: 専用ページ
│   ├── エピソード一覧
│   ├── 検索・フィルタ
│   ├── 詳細ページ
│   └── ナビゲーション
└── Phase 4: 購読促進
    ├── 外部アプリ連携
    ├── QRコード生成
    ├── RSS改善
    └── 共有機能
```

## 2. Phase 1: 統合ダッシュボード機能

### 2.1 メインページ統合

#### 2.1.1 レイアウト設計
```
┌─────────────────────────────────────────────────┐
│                  Header                         │
│          📊 Market News Dashboard               │
└─────────────────────────────────────────────────┘
│                 Statistics                      │
│        [Positive] [Negative] [Neutral]         │
└─────────────────────────────────────────────────┘
│            🎙️ PODCAST SECTION                   │ ← 新規追加
│  ┌─────────────────────────────────────────────┐ │
│  │  🔴 最新エピソード                            │ │
│  │  ████████████████████████ 7:23 / 8:45      │ │
│  │  [▶️] [⏸️] [🔊] [⚡] [📱]                     │ │
│  │                                             │ │
│  │  📅 2025年08月14日 16:07 配信                │ │
│  │  📰 3件の記事 • 💾 325KB                     │ │
│  │                                             │ │
│  │  💡 ハイライト:                              │ │
│  │  • 日経平均、3日続伸で年初来高値更新           │ │
│  │  • 米FRB、政策金利を据え置き決定              │ │
│  │  • 原油価格急落、需要懸念で約3%下落            │ │
│  │                                             │ │
│  │  [🎧 ポッドキャストページ] [📡 RSS購読]         │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
│                 News Articles                   │
│                   ...                           │
```

#### 2.1.2 UIコンポーネント仕様

**ポッドキャストセクション**
```html
<section class="podcast-section">
  <header class="podcast-header">
    <h2>🎙️ 最新ポッドキャスト</h2>
    <div class="podcast-status">
      <span class="live-indicator">🔴 最新</span>
    </div>
  </header>
  
  <div class="podcast-player">
    <!-- Audio Player Component -->
  </div>
  
  <div class="podcast-info">
    <!-- Episode Information -->
  </div>
  
  <div class="podcast-actions">
    <!-- Action Buttons -->
  </div>
</section>
```

**音声プレイヤーコンポーネント**
```html
<div class="audio-player" data-episode-id="{episodeId}">
  <div class="progress-container">
    <div class="progress-bar">
      <div class="progress-fill" style="width: 45%"></div>
      <div class="progress-thumb"></div>
    </div>
    <div class="time-display">
      <span class="current-time">3:23</span>
      <span class="separator">/</span>
      <span class="total-time">7:25</span>
    </div>
  </div>
  
  <div class="player-controls">
    <button class="play-pause-btn" aria-label="再生/一時停止">
      <span class="play-icon">▶️</span>
      <span class="pause-icon hidden">⏸️</span>
    </button>
    
    <div class="volume-control">
      <button class="volume-btn" aria-label="音量">🔊</button>
      <input type="range" class="volume-slider" min="0" max="1" step="0.1" value="0.8">
    </div>
    
    <div class="speed-control">
      <button class="speed-btn" data-speed="1.0">1.0x</button>
    </div>
    
    <div class="download-control">
      <a href="{audioUrl}" download class="download-btn" aria-label="ダウンロード">📱</a>
    </div>
  </div>
</div>
```

#### 2.1.3 インタラクション仕様

**再生/一時停止操作**
1. ユーザーが再生ボタンをクリック
2. 音声ファイルのロード開始（ローディング表示）
3. ロード完了後、再生開始
4. プログレスバー更新開始（1秒間隔）
5. 再生ボタン → 一時停止ボタンに変更

**プログレスバー操作**
1. ユーザーがプログレスバーをクリック/ドラッグ
2. クリック位置に応じて再生位置を計算
3. 音声ファイルの再生位置を変更
4. 時間表示を更新

**音量制御**
1. 音量ボタンクリック → 音量スライダー表示/非表示
2. スライダー操作 → リアルタイム音量変更
3. 設定値をLocalStorageに保存

### 2.2 レスポンシブデザイン仕様

#### 2.2.1 ブレイクポイント
```scss
$breakpoints: (
  mobile: 320px,
  tablet: 768px,
  desktop: 1024px,
  wide: 1440px
);
```

#### 2.2.2 レイアウト調整

**モバイル (320px - 767px)**
```css
.podcast-section {
  padding: 1rem;
  margin: 1rem 0;
}

.audio-player {
  flex-direction: column;
  gap: 0.75rem;
}

.player-controls {
  justify-content: space-around;
  flex-wrap: wrap;
}

.podcast-info {
  font-size: 0.9rem;
}

.highlight-list {
  display: none; /* モバイルでは非表示 */
}
```

**タブレット (768px - 1023px)**
```css
.podcast-section {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 1.5rem;
}

.audio-player {
  grid-column: 1 / -1;
}
```

**デスクトップ (1024px+)**
```css
.podcast-section {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2rem;
  padding: 2rem;
}

.highlight-list {
  max-height: 200px;
  overflow-y: auto;
}
```

## 3. Phase 2: スマート通知システム

### 3.1 LINE Flex Message設計

#### 3.1.1 メッセージ構造
```json
{
  "type": "flex",
  "altText": "🎙️ 新しいポッドキャストが配信されました",
  "contents": {
    "type": "bubble",
    "size": "giga",
    "header": {
      "type": "box",
      "layout": "vertical",
      "contents": [
        {
          "type": "text",
          "text": "🎙️ マーケットニュースポッドキャスト",
          "weight": "bold",
          "size": "lg",
          "color": "#1976d2"
        }
      ],
      "backgroundColor": "#f8f9fa",
      "paddingAll": "lg"
    },
    "hero": {
      "type": "image",
      "url": "https://jagar028055.github.io/Market_News_Project/assets/podcast-hero.jpg",
      "size": "full",
      "aspectRatio": "20:13",
      "aspectMode": "cover"
    },
    "body": {
      "type": "box",
      "layout": "vertical",
      "contents": [
        {
          "type": "text",
          "text": "マーケットニュース 2025年08月14日",
          "weight": "bold",
          "size": "xl"
        },
        {
          "type": "box",
          "layout": "baseline",
          "margin": "md",
          "contents": [
            {
              "type": "text",
              "text": "📅",
              "size": "sm",
              "flex": 0
            },
            {
              "type": "text",
              "text": "2025年08月14日 16:07 配信",
              "size": "sm",
              "color": "#666666",
              "margin": "sm",
              "flex": 0
            }
          ]
        },
        {
          "type": "box",
          "layout": "baseline",
          "contents": [
            {
              "type": "text",
              "text": "⏱️",
              "size": "sm",
              "flex": 0
            },
            {
              "type": "text",
              "text": "7分23秒 • 3件の記事",
              "size": "sm",
              "color": "#666666",
              "margin": "sm",
              "flex": 0
            }
          ]
        },
        {
          "type": "separator",
          "margin": "lg"
        },
        {
          "type": "text",
          "text": "💡 本日のハイライト:",
          "weight": "bold",
          "size": "md",
          "margin": "lg"
        },
        {
          "type": "text",
          "text": "• 日経平均、3日続伸で年初来高値更新\n• 米FRB、政策金利を据え置き決定\n• 原油価格急落、需要懸念で約3%下落",
          "size": "sm",
          "color": "#333333",
          "wrap": true,
          "margin": "sm"
        }
      ],
      "paddingAll": "lg"
    },
    "footer": {
      "type": "box",
      "layout": "vertical",
      "contents": [
        {
          "type": "box",
          "layout": "horizontal",
          "contents": [
            {
              "type": "button",
              "style": "primary",
              "height": "sm",
              "action": {
                "type": "uri",
                "uri": "https://jagar028055.github.io/Market_News_Project/podcast/market_news_20250814.mp3"
              },
              "text": "🎧 今すぐ聞く",
              "flex": 2
            },
            {
              "type": "button",
              "style": "secondary",
              "height": "sm",
              "action": {
                "type": "uri",
                "uri": "https://jagar028055.github.io/Market_News_Project/#podcast"
              },
              "text": "📱 サイトで開く",
              "flex": 1,
              "margin": "sm"
            }
          ]
        },
        {
          "type": "box",
          "layout": "horizontal",
          "contents": [
            {
              "type": "button",
              "style": "link",
              "height": "sm",
              "action": {
                "type": "uri",
                "uri": "https://jagar028055.github.io/Market_News_Project/podcast/feed.xml"
              },
              "text": "📡 RSS購読",
              "flex": 1
            },
            {
              "type": "button",
              "style": "link",
              "height": "sm",
              "action": {
                "type": "share",
                "text": "🎙️ 最新のマーケットニュースポッドキャストをチェック！ https://jagar028055.github.io/Market_News_Project/#podcast"
              },
              "text": "📤 共有",
              "flex": 1,
              "margin": "sm"
            }
          ],
          "margin": "sm"
        }
      ],
      "paddingAll": "lg"
    }
  }
}
```

#### 3.1.2 アクションボタン仕様

**今すぐ聞くボタン**
- Action: URI
- Target: 音声ファイル直接リンク
- Behavior: デフォルトメディアプレイヤーで開く

**サイトで開くボタン**
- Action: URI
- Target: メインページのポッドキャストセクション
- Behavior: WebView/ブラウザで開く

**RSS購読ボタン**
- Action: URI
- Target: feed.xml
- Behavior: ポッドキャストアプリ候補表示

**共有ボタン**
- Action: Share
- Content: テキスト + URL
- Behavior: LINE/SNSネイティブ共有

### 3.2 通知タイミング制御

#### 3.2.1 配信ロジック
```python
class SmartNotificationManager:
    def should_send_notification(self, episode_info: dict) -> bool:
        """通知送信の判定"""
        
        # 基本条件チェック
        if not self._is_valid_episode(episode_info):
            return False
            
        # 時間帯制御（7:00-22:00 JST）
        current_hour = datetime.now(timezone('Asia/Tokyo')).hour
        if not (7 <= current_hour <= 22):
            return False
            
        # 重複配信防止
        if self._is_already_sent(episode_info['id']):
            return False
            
        # 品質チェック（最低再生時間: 3分）
        if episode_info.get('duration', 0) < 180:
            return False
            
        return True
    
    def create_flex_message(self, episode_info: dict, articles: list) -> dict:
        """Flex Messageの生成"""
        # 上記JSON構造に従ってメッセージ生成
        pass
```

## 4. Phase 3: ポッドキャスト専用ページ

### 4.1 ページ構造設計

#### 4.1.1 URL構造
```
/podcast/                    # ポッドキャスト一覧
/podcast/episode/{id}        # 個別エピソード
/podcast/category/{category} # カテゴリ別
/podcast/search?q={query}    # 検索結果
```

#### 4.1.2 ナビゲーション設計
```html
<nav class="podcast-nav">
  <div class="nav-header">
    <h1>🎙️ ポッドキャストアーカイブ</h1>
    <a href="/" class="back-link">← ダッシュボードに戻る</a>
  </div>
  
  <div class="nav-controls">
    <div class="search-container">
      <input type="search" 
             placeholder="エピソードを検索..." 
             class="search-input"
             id="episode-search">
      <button class="search-btn">🔍</button>
    </div>
    
    <div class="filter-tabs">
      <button class="filter-tab active" data-filter="all">全て</button>
      <button class="filter-tab" data-filter="positive">上昇</button>
      <button class="filter-tab" data-filter="negative">下落</button>
      <button class="filter-tab" data-filter="neutral">中立</button>
    </div>
    
    <div class="sort-controls">
      <select class="sort-select">
        <option value="date-desc">新しい順</option>
        <option value="date-asc">古い順</option>
        <option value="duration-desc">長い順</option>
        <option value="duration-asc">短い順</option>
      </select>
    </div>
  </div>
</nav>
```

### 4.2 エピソードカード設計

#### 4.2.1 カードレイアウト
```html
<article class="episode-card" data-episode-id="{episodeId}">
  <div class="episode-header">
    <div class="episode-meta">
      <span class="episode-date">2025年08月14日</span>
      <span class="episode-duration">7:23</span>
      <span class="episode-sentiment sentiment-neutral">中立</span>
    </div>
    <button class="episode-bookmark" aria-label="ブックマーク">🔖</button>
  </div>
  
  <div class="episode-content">
    <h3 class="episode-title">マーケットニュース 2025年08月14日</h3>
    <p class="episode-description">本日のマーケットニュースポッドキャスト（3件の記事を解説）</p>
    
    <div class="episode-highlights">
      <h4>ハイライト:</h4>
      <ul>
        <li>日経平均、3日続伸で年初来高値更新</li>
        <li>米FRB、政策金利を据え置き決定</li>
        <li>原油価格急落、需要懸念で約3%下落</li>
      </ul>
    </div>
    
    <div class="episode-tags">
      <span class="tag">株式</span>
      <span class="tag">金利</span>
      <span class="tag">商品</span>
    </div>
  </div>
  
  <div class="episode-actions">
    <button class="play-btn primary" data-audio-url="{audioUrl}">
      ▶️ 再生
    </button>
    <a href="{audioUrl}" download class="download-btn">
      📱 ダウンロード
    </a>
    <button class="share-btn">
      📤 共有
    </button>
    <a href="/podcast/episode/{episodeId}" class="details-btn">
      詳細 →
    </a>
  </div>
</article>
```

### 4.3 詳細ページ設計

#### 4.3.1 ページレイアウト
```html
<main class="episode-detail">
  <header class="episode-hero">
    <div class="hero-content">
      <div class="breadcrumb">
        <a href="/">ホーム</a> > 
        <a href="/podcast/">ポッドキャスト</a> > 
        <span>2025年08月14日</span>
      </div>
      
      <h1 class="episode-title">マーケットニュース 2025年08月14日</h1>
      
      <div class="episode-stats">
        <span class="stat">📅 2025年08月14日 16:07</span>
        <span class="stat">⏱️ 7分23秒</span>
        <span class="stat">📰 3件の記事</span>
        <span class="stat">💾 325KB</span>
      </div>
    </div>
    
    <div class="hero-player">
      <!-- Audio Player Component -->
    </div>
  </header>
  
  <div class="episode-body">
    <aside class="episode-sidebar">
      <div class="chapter-list">
        <h3>チャプター</h3>
        <ol>
          <li><a href="#" data-time="0">オープニング</a> <span>0:00</span></li>
          <li><a href="#" data-time="30">日経平均の動向</a> <span>0:30</span></li>
          <li><a href="#" data-time="180">米FRB政策金利</a> <span>3:00</span></li>
          <li><a href="#" data-time="360">原油価格急落</a> <span>6:00</span></li>
          <li><a href="#" data-time="420">まとめ</a> <span>7:00</span></li>
        </ol>
      </div>
      
      <div class="related-episodes">
        <h3>関連エピソード</h3>
        <!-- Related episode cards -->
      </div>
    </aside>
    
    <article class="episode-main">
      <div class="episode-description">
        <h2>エピソード概要</h2>
        <p>本日のマーケットニュースポッドキャストでは、3件の重要なニュースを解説します...</p>
      </div>
      
      <div class="covered-articles">
        <h2>取り上げた記事</h2>
        <div class="article-list">
          <article class="article-summary">
            <h3>日経平均、3日続伸で年初来高値更新</h3>
            <div class="article-meta">
              <span class="source">経済ニュース</span>
              <span class="timestamp">0:30 - 3:00</span>
              <span class="sentiment positive">上昇</span>
            </div>
            <p class="article-summary-text">東京株式市場で日経平均株価が3営業日続伸し...</p>
            <a href="#" class="article-link">元記事を読む →</a>
          </article>
          <!-- 他の記事... -->
        </div>
      </div>
      
      <div class="episode-transcript">
        <h2>トランスクリプト</h2>
        <div class="transcript-content">
          <p data-time="0">皆さん、おはようございます。本日のマーケットニュースポッドキャストを始めさせていただきます。</p>
          <p data-time="15">まず最初に、日経平均の動向について解説いたします...</p>
          <!-- 全文... -->
        </div>
      </div>
    </article>
  </div>
</main>
```

## 5. Phase 4: 購読促進機能

### 5.1 外部アプリ連携

#### 5.1.1 対応プラットフォーム
```html
<div class="subscription-options">
  <h3>ポッドキャストアプリで聞く</h3>
  <div class="platform-links">
    <a href="https://podcasts.apple.com/subscribe?url={rssFeedUrl}" 
       class="platform-link apple-podcasts">
      <img src="/assets/icons/apple-podcasts.svg" alt="Apple Podcasts">
      <span>Apple Podcasts</span>
    </a>
    
    <a href="https://open.spotify.com/show/{showId}" 
       class="platform-link spotify">
      <img src="/assets/icons/spotify.svg" alt="Spotify">
      <span>Spotify</span>
    </a>
    
    <a href="https://www.google.com/podcasts?feed={rssFeedUrl}" 
       class="platform-link google-podcasts">
      <img src="/assets/icons/google-podcasts.svg" alt="Google Podcasts">
      <span>Google Podcasts</span>
    </a>
    
    <a href="https://pca.st/subscribe?url={rssFeedUrl}" 
       class="platform-link pocket-casts">
      <img src="/assets/icons/pocket-casts.svg" alt="Pocket Casts">
      <span>Pocket Casts</span>
    </a>
  </div>
</div>
```

### 5.2 QRコード生成機能

#### 5.2.1 QRコード実装
```html
<div class="qr-subscription">
  <h4>📱 スマートフォンで購読</h4>
  <div class="qr-container">
    <canvas id="qr-code" width="200" height="200"></canvas>
    <p>QRコードをスキャンして<br>スマートフォンで購読</p>
  </div>
</div>

<script>
// QR Code generation using qrcode.js
function generateQRCode(text, elementId) {
  QRCode.toCanvas(document.getElementById(elementId), text, {
    width: 200,
    margin: 2,
    color: {
      dark: '#1976d2',
      light: '#ffffff'
    }
  });
}

// RSS FeedのQRコード生成
generateQRCode(
  'https://jagar028055.github.io/Market_News_Project/podcast/feed.xml',
  'qr-code'
);
</script>
```

## 6. アクセシビリティ仕様

### 6.1 WCAG 2.1準拠

#### 6.1.1 キーボードナビゲーション
```javascript
// 音声プレイヤーのキーボード操作
const keyboardHandlers = {
  'Space': (e) => {
    e.preventDefault();
    togglePlayPause();
  },
  'ArrowLeft': (e) => {
    e.preventDefault();
    seekBackward(10); // 10秒戻る
  },
  'ArrowRight': (e) => {
    e.preventDefault();
    seekForward(10); // 10秒進む
  },
  'ArrowUp': (e) => {
    e.preventDefault();
    increaseVolume(0.1);
  },
  'ArrowDown': (e) => {
    e.preventDefault();
    decreaseVolume(0.1);
  }
};

document.addEventListener('keydown', (e) => {
  if (e.target.matches('.audio-player, .audio-player *')) {
    const handler = keyboardHandlers[e.code];
    if (handler) handler(e);
  }
});
```

#### 6.1.2 スクリーンリーダー対応
```html
<!-- ARIA属性の適切な使用 -->
<div class="audio-player" 
     role="region" 
     aria-label="音声プレイヤー">
  
  <div class="progress-container">
    <div class="progress-bar" 
         role="slider" 
         aria-label="再生位置"
         aria-valuemin="0" 
         aria-valuemax="100" 
         aria-valuenow="45"
         aria-valuetext="7分23秒中3分15秒再生済み"
         tabindex="0">
    </div>
  </div>
  
  <button class="play-pause-btn" 
          aria-label="再生"
          aria-describedby="play-status">
    <span id="play-status" class="sr-only">一時停止中</span>
  </button>
  
  <div class="volume-control">
    <label for="volume-slider" class="sr-only">音量調整</label>
    <input type="range" 
           id="volume-slider"
           class="volume-slider" 
           min="0" 
           max="1" 
           step="0.1" 
           value="0.8"
           aria-label="音量: 80%">
  </div>
</div>
```

### 6.2 カラーアクセシビリティ

#### 6.2.1 カラーパレット（WCAG AA準拠）
```scss
$colors: (
  // Primary colors (4.5:1 contrast ratio)
  primary: #1976d2,      // Blue
  primary-text: #ffffff,  // White on primary
  
  // Semantic colors
  positive: #2e7d32,     // Green
  negative: #d32f2f,     // Red  
  neutral: #455a64,      // Blue Grey
  warning: #f57c00,      // Orange
  
  // Text colors
  text-primary: #212121,    // Dark Grey (7:1 ratio)
  text-secondary: #757575,  // Medium Grey (4.5:1 ratio)
  text-hint: #9e9e9e,       // Light Grey (3:1 ratio for large text)
  
  // Background colors
  background: #ffffff,
  surface: #f5f5f5,
  divider: #e0e0e0
);
```

## 7. パフォーマンス仕様

### 7.1 読み込み最適化

#### 7.1.1 画像最適化
```html
<!-- レスポンシブ画像 -->
<picture>
  <source media="(max-width: 768px)" 
          srcset="/assets/podcast-hero-mobile.webp">
  <source media="(min-width: 769px)" 
          srcset="/assets/podcast-hero-desktop.webp">
  <img src="/assets/podcast-hero-fallback.jpg" 
       alt="ポッドキャストイメージ" 
       loading="lazy">
</picture>
```

#### 7.1.2 JavaScript最適化
```javascript
// 遅延読み込み
const lazyLoadComponents = () => {
  // Intersection Observer for episode cards
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        loadEpisodeCard(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, {
    rootMargin: '50px'
  });
  
  document.querySelectorAll('.episode-card')
    .forEach(card => observer.observe(card));
};

// Audio preloading strategy
const preloadStrategy = {
  preloadLatest: true,      // 最新エピソードは事前読み込み
  preloadOnHover: true,     // ホバー時に音声メタデータ読み込み
  maxPreloadCount: 3        // 同時読み込み上限
};
```

## 8. エラーハンドリング仕様

### 8.1 音声再生エラー

#### 8.1.1 エラータイプ別対応
```javascript
const audioErrorHandler = {
  MEDIA_ERR_ABORTED: {
    message: '再生が中断されました',
    action: 'retry',
    userMessage: '再生を再試行してください'
  },
  MEDIA_ERR_NETWORK: {
    message: 'ネットワークエラー',
    action: 'retry',
    userMessage: 'ネットワーク接続を確認してください'
  },
  MEDIA_ERR_DECODE: {
    message: '音声ファイルの読み込みエラー',
    action: 'fallback',
    userMessage: 'ダウンロードリンクをお試しください'
  },
  MEDIA_ERR_SRC_NOT_SUPPORTED: {
    message: '未対応の音声形式',
    action: 'fallback', 
    userMessage: 'お使いのブラウザでは再生できません'
  }
};

const handleAudioError = (audio, episodeId) => {
  const errorType = Object.keys(audioErrorHandler)[audio.error.code - 1];
  const errorConfig = audioErrorHandler[errorType];
  
  showErrorNotification(errorConfig.userMessage);
  
  if (errorConfig.action === 'retry') {
    showRetryButton(episodeId);
  } else if (errorConfig.action === 'fallback') {
    showDownloadFallback(episodeId);
  }
};
```

### 8.2 データ読み込みエラー

#### 8.2.1 フォールバック機能
```javascript
const dataFallback = {
  async loadEpisodeData(episodeId) {
    try {
      // Primary: JSON API
      return await fetch(`/podcast/episode/${episodeId}.json`);
    } catch (error) {
      try {
        // Fallback 1: Main episodes list
        const episodes = await fetch('/podcast/episodes.json');
        return episodes.find(ep => ep.id === episodeId);
      } catch (fallbackError) {
        // Fallback 2: Static fallback data
        return this.getStaticFallback(episodeId);
      }
    }
  },
  
  getStaticFallback(episodeId) {
    return {
      id: episodeId,
      title: 'エピソードタイトル',
      description: 'エピソードの詳細情報を読み込めませんでした',
      audioUrl: null,
      error: 'データの読み込みに失敗しました'
    };
  }
};
```

---

**承認者**: UX/UI Lead  
**最終更新**: 2025-08-14  
**次回レビュー**: 実装完了後