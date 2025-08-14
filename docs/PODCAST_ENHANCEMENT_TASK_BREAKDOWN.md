# ポッドキャスト機能改善 - 詳細タスクブレイクダウン

**Project**: Market News Podcast Enhancement  
**Version**: 1.0  
**Date**: 2025-08-14  
**Author**: Project Management Team

---

## 📋 プロジェクト全体タスク構成

```
ポッドキャスト機能改善 (100%)
├── Phase 1: 統合ダッシュボード (35%)
├── Phase 2: スマート通知システム (25%)
├── Phase 3: ポッドキャスト専用ページ (30%)
└── Phase 4: 購読促進機能 (10%)
```

---

## 🎯 Phase 1: 統合ダッシュボード機能

**工数見積**: 16-20時間  
**優先度**: 🔴 最高  
**依存関係**: 既存システムのみ

### 1.1 バックエンド実装 (6-8時間)

#### Task 1.1.1: JSON API生成機能実装
**工数**: 3-4時間  
**担当**: Backend Developer

**詳細タスク**:
- [ ] `src/podcast/web/json_generator.py` 作成
- [ ] Episode JSON生成ロジック実装
  - [ ] エピソード基本情報の構造化
  - [ ] 記事情報のタイムスタンプ付き変換
  - [ ] ハイライト情報の抽出・整形
- [ ] `/podcast/latest.json` 生成機能
- [ ] `/podcast/episodes.json` 更新機能
- [ ] エラーハンドリング・バリデーション

**受入基準**:
- [ ] JSON生成がエラーなく動作する
- [ ] 生成されるJSONが仕様に準拠する
- [ ] 既存ワークフローに統合される

**実装ファイル**:
```
src/podcast/web/
├── json_generator.py      # JSON生成クラス
├── data_transformer.py    # データ変換ユーティリティ
└── __init__.py
```

#### Task 1.1.2: PodcastIntegrationManager拡張
**工数**: 2-3時間  
**担当**: Backend Developer

**詳細タスク**:
- [ ] `PodcastIntegrationManager`クラス拡張
- [ ] Web統合機能の呼び出し追加
- [ ] JSON生成処理の統合
- [ ] GitHub Pages デプロイ処理拡張

**実装内容**:
```python
# src/podcast/integration/podcast_integration_manager.py
def broadcast_podcast_to_line(self, podcast_path: str, articles: List[Dict]):
    # 既存処理...
    
    # Web統合機能追加
    if audio_url:
        web_generator = PodcastWebGenerator(self.config, self.logger)
        web_generator.generate_dashboard_data(episode_info, articles, audio_url)
        web_generator.update_episodes_list(episode_info)
```

#### Task 1.1.3: GitHub Actions ワークフロー拡張
**工数**: 1時間  
**担当**: DevOps

**詳細タスク**:
- [ ] `.github/workflows/podcast-broadcast.yml` 修正
- [ ] Web assets 生成ステップ追加
- [ ] JSON ファイルのデプロイ設定
- [ ] デバッグログ追加

**実装内容**:
```yaml
- name: Generate Web Assets
  run: |
    python -c "
    from src.podcast.web.json_generator import PodcastJSONGenerator
    generator = PodcastJSONGenerator()
    generator.generate_all_assets()
    "

- name: Deploy Web Assets
  run: |
    cp -r output/web/* public/
```

### 1.2 フロントエンド実装 (10-12時間)

#### Task 1.2.1: CSS スタイル実装
**工数**: 3-4時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] `assets/css/podcast.css` 作成
- [ ] ポッドキャストセクション基本スタイル
- [ ] 音声プレイヤーコンポーネントスタイル
- [ ] レスポンシブデザイン実装
  - [ ] Mobile (320px-767px)
  - [ ] Tablet (768px-1023px) 
  - [ ] Desktop (1024px+)
- [ ] ダークモード対応
- [ ] アクセシビリティ考慮（フォーカス表示等）

**実装ファイル**:
```
assets/css/
├── podcast.css           # メインスタイル
├── podcast-player.css    # プレイヤー専用スタイル
└── podcast-responsive.css # レスポンシブ対応
```

#### Task 1.2.2: JavaScript 音声プレイヤー実装
**工数**: 4-5時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] `assets/js/podcast/player.js` 作成
- [ ] HTML5 Audio API 統合
  - [ ] 音声ファイル読み込み・再生制御
  - [ ] プログレスバー更新
  - [ ] 音量・再生速度制御
  - [ ] キーボードショートカット対応
- [ ] UI状態管理
  - [ ] 再生/一時停止状態
  - [ ] ローディング状態
  - [ ] エラー状態
- [ ] LocalStorage 設定保存
- [ ] イベントハンドリング

**API設計**:
```javascript
class PodcastPlayer {
  constructor(containerId, options = {})
  load(audioUrl, episodeData)
  play()
  pause()
  seek(time)
  setVolume(volume)
  setPlaybackRate(rate)
  destroy()
}
```

#### Task 1.2.3: データ取得・表示機能実装
**工数**: 2-3時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] `assets/js/podcast/api.js` 作成
- [ ] 最新エピソード情報取得
- [ ] エピソードデータの表示
- [ ] エラーハンドリング・フォールバック
- [ ] ローディング状態管理
- [ ] キャッシュ機能（Optional）

**実装内容**:
```javascript
// API client
class PodcastAPI {
  async getLatestEpisode()
  async getEpisodeList(page = 1, limit = 10)
  async getEpisodeDetails(episodeId)
}

// UI controller  
class PodcastDashboard {
  init()
  loadLatestEpisode()
  renderEpisodeInfo(episode)
  showError(message)
  showLoading(isLoading)
}
```

#### Task 1.2.4: index.html 統合実装
**工数**: 1時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] `index.html` にポッドキャストセクション追加
- [ ] HTML構造の実装
- [ ] CSS・JavaScript読み込み設定
- [ ] 既存デザインとの調和確認

**実装位置**:
```html
<!-- 統計セクションの後に追加 -->
<section class="podcast-section" id="podcast">
  <!-- ポッドキャストコンテンツ -->
</section>
```

---

## 🔔 Phase 2: スマート通知システム

**工数見積**: 8-10時間  
**優先度**: 🟡 高  
**依存関係**: Phase 1のJSON API

### 2.1 LINE Flex Message実装 (6-7時間)

#### Task 2.1.1: FlexMessage テンプレート作成
**工数**: 3-4時間  
**担当**: Backend Developer

**詳細タスク**:
- [ ] `src/podcast/integration/message_templates.py` 作成
- [ ] Flex Message JSON構造定義
- [ ] 動的データ埋め込み機能
- [ ] メッセージカスタマイズオプション
- [ ] デバッグ・プレビュー機能

**実装クラス**:
```python
class PodcastFlexMessageTemplate:
    def create_episode_notification(self, episode_info: dict, articles: list) -> dict
    def create_highlight_carousel(self, highlights: list) -> dict
    def create_action_buttons(self, audio_url: str, web_url: str) -> dict
    def validate_message_size(self, message: dict) -> bool
```

#### Task 2.1.2: LineBroadcaster クラス拡張
**工数**: 2-3時間  
**担当**: Backend Developer

**詳細タスク**:
- [ ] `LineBroadcaster` クラス修正
- [ ] Flex Message対応
- [ ] 既存テキストメッセージからの移行
- [ ] エラーハンドリング強化
- [ ] 送信結果のログ改善

**修正内容**:
```python
# src/podcast/integration/line_broadcaster.py
def broadcast_podcast_notification(self, episode_info, articles, audio_url):
    # テキストメッセージ → Flex Messageに変更
    flex_message = self.message_templates.create_episode_notification(
        episode_info, articles
    )
    return self._send_flex_message(flex_message)
```

#### Task 2.1.3: 画像アセット準備
**工数**: 1時間  
**担当**: Designer/Frontend Developer

**詳細タスク**:
- [ ] ポッドキャスト用ヒーロー画像作成
- [ ] 各種アイコン・ボタン画像作成
- [ ] 最適化・圧縮処理
- [ ] GitHub Pages配信設定

**アセットファイル**:
```
assets/images/podcast/
├── hero-image.jpg         # 1200x630px
├── hero-image-mobile.jpg  # 800x450px  
├── app-icons/
│   ├── apple-podcasts.svg
│   ├── spotify.svg
│   └── google-podcasts.svg
└── fallback-image.jpg     # エラー時のフォールバック
```

### 2.2 通知最適化機能 (2-3時間)

#### Task 2.2.1: 通知タイミング制御
**工数**: 1-2時間  
**担当**: Backend Developer

**詳細タスク**:
- [ ] `SmartNotificationManager` クラス作成
- [ ] 時間帯制御ロジック実装
- [ ] 重複送信防止機能
- [ ] 品質チェック機能

**実装ロジック**:
```python
class SmartNotificationManager:
    def should_send_notification(self, episode_info) -> bool
    def is_appropriate_time(self) -> bool
    def is_quality_sufficient(self, episode_info) -> bool
    def record_notification_sent(self, episode_id) -> None
```

#### Task 2.2.2: A/Bテスト基盤（Optional）
**工数**: 1時間  
**担当**: Backend Developer

**詳細タスク**:
- [ ] メッセージバリエーション管理
- [ ] 送信結果トラッキング
- [ ] 効果測定機能

---

## 📱 Phase 3: ポッドキャスト専用ページ

**工数見積**: 14-18時間  
**優先度**: 🟢 中  
**依存関係**: Phase 1のJSON API、Phase 2の画像アセット

### 3.1 ページ構造・ナビゲーション (4-5時間)

#### Task 3.1.1: 専用ページHTML作成
**工数**: 2-3時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] `podcast/index.html` 作成
- [ ] ナビゲーション構造実装
- [ ] 検索・フィルタUI実装
- [ ] ページネーション準備
- [ ] SEO最適化（meta tags等）

**HTML構造**:
```html
<!DOCTYPE html>
<html>
<head>
  <title>ポッドキャストアーカイブ - Market News</title>
  <!-- SEO meta tags -->
</head>
<body>
  <nav class="podcast-nav"></nav>
  <main class="podcast-main">
    <div class="podcast-filters"></div>
    <div class="podcast-list"></div>
    <div class="podcast-pagination"></div>
  </main>
</body>
</html>
```

#### Task 3.1.2: CSS レイアウト実装
**工数**: 2時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] `assets/css/podcast-page.css` 作成
- [ ] グリッドレイアウト実装
- [ ] カードデザイン実装
- [ ] フィルタ・検索UIスタイル
- [ ] レスポンシブ対応

### 3.2 データ表示・操作機能 (6-8時間)

#### Task 3.2.1: エピソード一覧表示機能
**工数**: 3-4時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] `assets/js/podcast/episodeList.js` 作成
- [ ] エピソードデータの取得・表示
- [ ] 無限スクロール/ページネーション
- [ ] 遅延読み込み（Lazy Loading）
- [ ] カード形式表示の実装

**実装クラス**:
```javascript
class EpisodeList {
  constructor(containerId)
  async loadEpisodes(page = 1, filters = {})
  renderEpisode(episode)
  showLoading()
  hideLoading()
  handleError(error)
}
```

#### Task 3.2.2: 検索・フィルタ機能
**工数**: 2-3時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] `assets/js/podcast/search.js` 作成
- [ ] テキスト検索機能
- [ ] カテゴリフィルタ
- [ ] 日付範囲フィルタ
- [ ] ソート機能（日付、長さ）
- [ ] URL状態管理（検索結果共有用）

#### Task 3.2.3: 個別エピソード詳細ページ
**工数**: 1時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] 動的ページ生成（JavaScript）
- [ ] エピソード詳細情報表示
- [ ] チャプター機能（Optional）
- [ ] 関連エピソード表示

### 3.3 高度な機能 (4-5時間)

#### Task 3.3.1: ブックマーク機能
**工数**: 2-3時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] LocalStorage使用のブックマーク機能
- [ ] ブックマーク状態の表示
- [ ] ブックマーク一覧ページ
- [ ] エクスポート・インポート機能

#### Task 3.3.2: 共有機能
**工数**: 1-2時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] ネイティブ共有API利用
- [ ] ソーシャルメディア共有
- [ ] URL共有（エピソード直リンク）
- [ ] 共有テキストのカスタマイズ

---

## 🔗 Phase 4: 購読促進機能

**工数見積**: 4-6時間  
**優先度**: 🔵 低  
**依存関係**: Phase 1-3完了後

### 4.1 外部プラットフォーム連携 (2-3時間)

#### Task 4.1.1: ポッドキャストアプリリンク実装
**工数**: 1-2時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] 主要プラットフォームURL生成
- [ ] アプリ検出・自動リダイレクト
- [ ] フォールバック処理

**対応プラットフォーム**:
- Apple Podcasts
- Spotify  
- Google Podcasts
- Pocket Casts

#### Task 4.1.2: QRコード生成機能
**工数**: 1時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] QRコード生成ライブラリ統合
- [ ] 動的QRコード生成
- [ ] モバイル最適化

### 4.2 RSS配信改善 (2-3時間)

#### Task 4.2.1: RSS品質改善
**工数**: 1-2時間  
**担当**: Backend Developer

**詳細タスク**:
- [ ] RSS仕様完全準拠
- [ ] iTunes Podcast仕様対応
- [ ] 画像・メタデータ充実
- [ ] 検証ツール対応

#### Task 4.2.2: 購読促進UI
**工数**: 1時間  
**担当**: Frontend Developer

**詳細タスク**:
- [ ] RSS購読ボタン
- [ ] 購読手順ガイド
- [ ] モバイル対応説明

---

## 📅 実装スケジュール詳細

### Week 1: 基盤構築

**Day 1-2**: Phase 1 バックエンド
- Task 1.1.1: JSON API生成機能 (Day 1)
- Task 1.1.2: PodcastIntegrationManager拡張 (Day 2 午前)
- Task 1.1.3: GitHub Actions拡張 (Day 2 午後)

**Day 3-5**: Phase 1 フロントエンド
- Task 1.2.1: CSS スタイル実装 (Day 3)
- Task 1.2.2: JavaScript 音声プレイヤー (Day 4-5 午前)
- Task 1.2.3: データ取得・表示機能 (Day 5 午後)
- Task 1.2.4: index.html 統合 (Day 5 夕方)

### Week 2: 通知・専用ページ

**Day 6-7**: Phase 2 スマート通知
- Task 2.1.1: FlexMessage テンプレート (Day 6)
- Task 2.1.2: LineBroadcaster拡張 (Day 7 午前)
- Task 2.1.3: 画像アセット準備 (Day 7 午後)

**Day 8-10**: Phase 3 専用ページ
- Task 3.1.1-3.1.2: ページ構造・CSS (Day 8)
- Task 3.2.1: エピソード一覧 (Day 9)
- Task 3.2.2-3.2.3: 検索・詳細ページ (Day 10)

### Week 3: 高度機能・購読促進

**Day 11-12**: Phase 3 高度機能
- Task 3.3.1: ブックマーク機能 (Day 11)
- Task 3.3.2: 共有機能 (Day 12)

**Day 13-14**: Phase 4 購読促進
- Task 4.1.1-4.1.2: 外部連携・QR (Day 13)
- Task 4.2.1-4.2.2: RSS改善 (Day 14)

**Day 15**: 統合テスト・バグ修正

---

## 🧪 テスト・品質保証

### テスト段階別タスク

#### 単体テスト
**工数**: 各実装タスクの20%  
**担当**: 各開発者

- [ ] JavaScript関数のユニットテスト
- [ ] Python クラス・メソッドのテスト
- [ ] CSS レスポンシブテスト

#### 統合テスト  
**工数**: 2-3時間  
**担当**: Lead Developer

- [ ] フロント・バックエンド連携テスト
- [ ] 外部API（LINE、GitHub Pages）連携テスト
- [ ] クロスブラウザテスト

#### ユーザビリティテスト
**工数**: 2時間  
**担当**: UX Designer + 外部テスター

- [ ] 実ユーザーによる操作テスト
- [ ] アクセシビリティチェック
- [ ] パフォーマンステスト

---

## 🎯 完了基準・検収項目

### Phase 1完了基準
- [ ] メインページにポッドキャストセクションが統合表示される
- [ ] 音声プレイヤーで最新エピソードが再生可能
- [ ] モバイル・デスクトップで正常動作
- [ ] 音声コントロール（再生・停止・音量・シーク）が全て機能
- [ ] エピソード情報（タイトル・時間・ハイライト）が正確に表示
- [ ] ページ読み込み時間が3秒以内

### Phase 2完了基準
- [ ] LINE通知がFlexMessage形式で送信される
- [ ] カード形式でエピソード情報が美しく表示される
- [ ] 「今すぐ聞く」「サイトで開く」ボタンが正常動作
- [ ] ハイライト情報が適切に3件表示される
- [ ] 共有・RSS購読ボタンが機能する

### Phase 3完了基準
- [ ] 専用ページ（/podcast/）でエピソード一覧が表示される
- [ ] 検索・フィルタ機能が正常動作する
- [ ] 個別エピソード詳細が表示される
- [ ] ページ遷移がスムーズ（1秒以内）
- [ ] 遅延読み込みが正常動作する

### Phase 4完了基準
- [ ] 主要ポッドキャストアプリリンクが正常動作
- [ ] QRコード生成・表示が機能する
- [ ] RSS配信が改善され、ポッドキャストアプリで購読可能
- [ ] 共有機能が各プラットフォームで動作する

---

## 🚨 リスク管理・対策

### 技術リスク

#### High Risk: ブラウザ音声互換性
**対策**: 
- フォールバック実装（ダウンロードリンク）
- 主要ブラウザでの事前テスト
- ポリフィル利用検討

#### Medium Risk: GitHub Pages容量制限
**対策**:
- 音声ファイル最適化
- 古いファイル自動削除機能
- CDN移行準備

### 工数リスク

#### High Risk: フロントエンド複雑性
**対策**:
- 段階的実装（MVP → 拡張）
- 外部ライブラリ活用
- コード再利用促進

#### Medium Risk: デザイン調整時間
**対策**:
- 事前モックアップ作成
- デザイナーとの密な連携
- ユーザーフィードバック早期収集

---

**承認者**: Project Manager  
**最終更新**: 2025-08-14  
**次回レビュー**: Week 1完了後