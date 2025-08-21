# マーケットニュースシステム 機能仕様書

## 1. システム概要

### 1.1 システム目的
AIを活用したマーケットニュースの収集・要約・分析システムにより、ユーザーに効率的で洞察に富んだ投資情報を提供する。

### 1.2 主要機能
1. **記事一覧表示機能** (Flash要約)
2. **詳細分析機能** (Pro要約)
3. **検索・フィルタリング機能**
4. **統計・ダッシュボード機能**
5. **ナビゲーション・UI機能**

## 2. メインページ機能詳細

### 2.1 記事一覧表示機能

#### 2.1.1 機能概要
- **機能ID**: F-001
- **機能名**: Flash要約一覧表示
- **概要**: 収集した市場ニュース記事のFlash要約を一覧形式で表示

#### 2.1.2 入力
- 外部JSONファイル: `data/articles.json`
- ユーザー操作: ページ読み込み、リフレッシュボタン

#### 2.1.3 処理
1. **データ読み込み**
   ```javascript
   async function loadArticlesData() {
     const response = await fetch('data/articles.json');
     const data = await response.json();
     return data.map(article => ({
       title: article.title,
       url: article.url,
       summary: article.summary,
       source: article.source,
       published_jst: article.published_jst
     }));
   }
   ```

2. **データ変換**
   - 感情分析データの除去
   - 日時フォーマットの正規化
   - エラーデータの除外

3. **表示レンダリング**
   - 記事カードの動的生成
   - レスポンシブレイアウト適用
   - 遅延読み込み対応

#### 2.1.4 出力
- **表示形式**: カード型レイアウト
- **表示項目**:
  - 記事タイトル（リンク付き）
  - Flash要約文（200-300文字）
  - ニュースソース（Bloomberg/Reuters）
  - 公開日時（日本時間）

#### 2.1.5 例外処理
- **ネットワークエラー**: "記事データの読み込みに失敗しました"
- **JSON解析エラー**: "データ形式が正しくありません"
- **空データ**: "現在表示できる記事がありません"

### 2.2 検索・フィルタリング機能

#### 2.2.1 機能概要
- **機能ID**: F-002
- **機能名**: 記事検索・絞り込み
- **概要**: キーワード検索とカテゴリフィルタによる記事絞り込み

#### 2.2.2 検索機能
**入力**:
- 検索キーワード（テキスト入力）
- 検索対象: タイトル、要約文

**処理**:
```javascript
function searchArticles(articles, searchTerm) {
  if (!searchTerm) return articles;
  
  const term = searchTerm.toLowerCase();
  return articles.filter(article => 
    article.title.toLowerCase().includes(term) ||
    article.summary.toLowerCase().includes(term)
  );
}
```

**出力**:
- マッチした記事の一覧
- ヒット件数の表示

#### 2.2.3 フィルタリング機能
**ソースフィルター**:
- オプション: 全て / Reuters / Bloomberg
- 処理: `article.source` による絞り込み

**並び替え機能**:
- 日時（新しい順）- デフォルト
- 日時（古い順）
- ソース順（アルファベット順）

#### 2.2.4 リアルタイム検索
- **デバウンス機能**: 300ms遅延
- **キーボードショートカット**: Ctrl+K で検索フォーカス
- **検索履歴**: LocalStorage保存（将来実装）

### 2.3 統計表示機能

#### 2.3.1 現在実装済み統計
1. **総記事数**
   - 表示: 数値
   - 更新: データ読み込み時に自動計算

2. **最終更新時刻**
   - 表示: "YYYY-MM-DD HH:MM" 形式
   - 計算: 全記事の公開日時の最大値

#### 2.3.2 未実装統計（要実装）
1. **地域分布チャート**
   - 予定表示: 円グラフまたは棒グラフ
   - データソース: 記事内容の地域判定ロジック

2. **カテゴリ分布チャート**
   - 予定表示: 円グラフ
   - データソース: 記事のカテゴリ分類ロジック

## 3. Pro要約ページ機能詳細

### 3.1 詳細分析表示機能

#### 3.1.1 機能概要
- **機能ID**: F-003
- **機能名**: Gemini 2.5 Pro詳細分析
- **概要**: 高度なAI分析による市場洞察の提供

#### 3.1.2 分析セクション構成

**1. 市場概況分析**
```javascript
function generateMarketOverview(articles) {
  return {
    currentStatus: analyzeMarketStatus(articles),
    majorTrends: identifyTrends(articles),
    geminiInsights: generateInsights(articles)
  };
}
```

**2. 地域別市場分析**
- 対象地域: 北米、欧州、日本、アジア新興国
- 分析内容: 各地域の市場状況、政策動向、見通し

**3. セクター別トレンド分析**
- 対象セクター: テクノロジー、金融、製造業、エネルギー
- 分析内容: セクタートレンド、業績見通し、投資機会

**4. リスク要因分析**
- 地政学的リスク
- 経済政策リスク
- 市場技術的リスク
- 企業固有リスク

**5. 投資機会分析**
- 成長セクター特定
- 割安銘柄候補
- 新興技術分野
- ESG投資機会

**6. 市場予測・展望**
- 短期展望（1-3ヶ月）
- 中期展望（6-12ヶ月）
- 長期展望（1-3年）

#### 3.1.3 データ生成プロセス
1. **記事データ分析**
   - キーワード抽出
   - トレンド検出
   - センチメント分析（除去済み）

2. **AI分析結果統合**
   - 複数記事の相関分析
   - 時系列トレンド分析
   - 予測モデル適用

3. **レポート生成**
   - セクション別コンテンツ生成
   - 視覚的ハイライト追加
   - ユーザーフレンドリーな表現変換

### 3.2 ナビゲーション機能

#### 3.2.1 ページ間遷移
**メインページ → Pro要約ページ**
- トリガー: "📈 詳細分析" リンクのクリック
- 処理: `pro-summary.html` への遷移
- データ: URLパラメータでの状態引き継ぎ（将来実装）

**Pro要約ページ → メインページ**
- トリガー: "← 記事一覧に戻る" リンクのクリック
- 処理: `index.html` への遷移

#### 3.2.2 テーマ切り替え機能
```javascript
function toggleTheme() {
  const html = document.documentElement;
  const themeToggle = document.getElementById('theme-toggle');
  
  if (html.getAttribute('data-theme') === 'dark') {
    html.setAttribute('data-theme', 'light');
    themeToggle.textContent = '🌙';
    localStorage.setItem('theme', 'light');
  } else {
    html.setAttribute('data-theme', 'dark');
    themeToggle.textContent = '☀️';
    localStorage.setItem('theme', 'dark');
  }
}
```

## 4. ユーザーインターフェース仕様

### 4.1 レスポンシブデザイン

#### 4.1.1 ブレークポイント
- **Mobile**: 〜768px
- **Tablet**: 769px〜1024px
- **Desktop**: 1025px〜

#### 4.1.2 レイアウト調整
**Mobile**:
- 1カラムレイアウト
- ヘッダーボタンの縦積み
- タッチフレンドリーなボタンサイズ

**Tablet**:
- 2カラムレイアウト
- サイドバーナビゲーション
- 中間的なフォントサイズ

**Desktop**:
- 3カラムレイアウト
- フルサイズのヘッダー
- ホバーエフェクト

### 4.2 アクセシビリティ対応

#### 4.2.1 キーボードナビゲーション
- **Tab順序**: 論理的な要素順序
- **フォーカス表示**: 明確な視覚的フィードバック
- **ショートカット**: Ctrl+K（検索フォーカス）

#### 4.2.2 スクリーンリーダー対応
- **セマンティックHTML**: 適切なHTML要素使用
- **aria-label**: 説明的なラベル付与
- **alt属性**: 画像の代替テキスト

#### 4.2.3 カラーコントラスト
- **WCAG 2.1 AA準拠**: 4.5:1以上のコントラスト比
- **色盲対応**: 色のみに依存しない情報表現

### 4.3 ローディング状態管理

#### 4.3.1 初期読み込み
```html
<div id="loading" class="loading-indicator">
  <div class="spinner">⏳</div>
  <p>記事を読み込み中...</p>
</div>
```

#### 4.3.2 Pro分析ページ
```html
<div id="loading-pro" class="loading-pro">
  <div class="ai-icon">🧠</div>
  <h3>Gemini 2.5 Pro分析中...</h3>
  <progress></progress>
</div>
```

## 5. エラーハンドリング仕様

### 5.1 エラータイプ別対応

#### 5.1.1 ネットワークエラー
**発生条件**: JSONファイル読み込み失敗
**表示内容**:
```html
<div class="error-message">
  <h3>⚠️ 通信エラー</h3>
  <p>記事データの読み込みに失敗しました。</p>
  <button onclick="location.reload()">再試行</button>
</div>
```

#### 5.1.2 データエラー
**発生条件**: JSON解析失敗、データ形式不正
**表示内容**:
```html
<div class="error-message">
  <h3>⚠️ データエラー</h3>
  <p>データ形式に問題があります。管理者に連絡してください。</p>
</div>
```

#### 5.1.3 空データエラー
**発生条件**: 有効な記事データが0件
**表示内容**:
```html
<div class="no-articles">
  <h3>📄 記事なし</h3>
  <p>現在表示できる記事がありません。</p>
</div>
```

### 5.2 エラー復旧機能

#### 5.2.1 自動リトライ
```javascript
async function loadWithRetry(url, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url);
      if (response.ok) return response;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
}
```

#### 5.2.2 フォールバック機能
- **キャッシュデータ**: LocalStorage からの代替データ読み込み
- **最小機能**: エラー時でも基本機能は維持
- **グレースフルデグラデーション**: 段階的機能縮退

## 6. パフォーマンス要件

### 6.1 読み込み性能

#### 6.1.1 初期読み込み
- **目標**: 3秒以内の初期表示
- **測定指標**: First Contentful Paint (FCP)
- **最適化手法**:
  - HTMLファイルサイズ削減（15KB以下）
  - 重要なCSS/JSの優先読み込み
  - 画像遅延読み込み

#### 6.1.2 動的読み込み
- **目標**: 1秒以内のデータ更新
- **測定指標**: Time to Interactive (TTI)
- **最適化手法**:
  - JSONファイルのgzip圧縮
  - ブラウザキャッシュ活用
  - 不要なDOM操作削減

### 6.2 実行時性能

#### 6.2.1 検索・フィルタリング
- **目標**: 500ms以内の応答
- **最適化手法**:
  - デバウンス機能（300ms）
  - インデックス化検索
  - 仮想スクロール（将来実装）

#### 6.2.2 メモリ使用量
- **目標**: 50MB以下のメモリ使用
- **最適化手法**:
  - 不要なオブジェクト参照の解除
  - イベントリスナーの適切な削除
  - 大量データの分割処理

## 7. セキュリティ仕様

### 7.1 入力検証

#### 7.1.1 検索入力
```javascript
function sanitizeSearchInput(input) {
  // HTML特殊文字のエスケープ
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}
```

#### 7.1.2 URL検証
```javascript
function isValidArticleUrl(url) {
  try {
    const parsedUrl = new URL(url);
    return ['https://jp.reuters.com', 'https://www.bloomberg.co.jp']
      .some(domain => parsedUrl.href.startsWith(domain));
  } catch {
    return false;
  }
}
```

### 7.2 XSS対策

#### 7.2.1 DOM操作
```javascript
// 安全なDOM操作の例
function createArticleElement(article) {
  const element = document.createElement('article');
  element.className = 'article-card';
  
  // textContent使用でXSS防止
  const title = document.createElement('h3');
  title.textContent = article.title;
  
  const summary = document.createElement('p');
  summary.textContent = article.summary;
  
  element.appendChild(title);
  element.appendChild(summary);
  return element;
}
```

### 7.3 外部リンク対策
```html
<!-- セキュアな外部リンク -->
<a href="{{ article.url }}" 
   target="_blank" 
   rel="noopener noreferrer">
  {{ article.title }}
</a>
```

## 8. 国際化・多言語対応

### 8.1 現在の言語設定
- **プライマリ言語**: 日本語
- **文字エンコーディング**: UTF-8
- **タイムゾーン**: JST (Japan Standard Time)

### 8.2 将来の多言語対応設計
```javascript
// 国際化対応設計例
const i18n = {
  ja: {
    'loading': '読み込み中...',
    'search_placeholder': 'キーワードで検索...',
    'no_articles': '記事が見つかりません'
  },
  en: {
    'loading': 'Loading...',
    'search_placeholder': 'Search by keyword...',
    'no_articles': 'No articles found'
  }
};
```

---

**文書管理情報**
- 作成日: 2025年8月15日
- バージョン: 1.0
- 承認者: プロダクトマネージャー
- 次回レビュー予定: 2025年9月15日