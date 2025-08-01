# データベースアーキテクチャガイド
## Market News Aggregator のデータベース設計と処理フロー

### 📋 目次
1. [概要](#概要)
2. [問題の経緯](#問題の経緯)
3. [データベース設計](#データベース設計)
4. [処理フローの変遷](#処理フローの変遷)
5. [技術的改善点](#技術的改善点)
6. [実装の詳細](#実装の詳細)

---

## 📖 概要

このガイドでは、Market News Aggregatorプロジェクトにおけるデータベースアーキテクチャの設計思想と、記事重複問題を解決するまでの経緯を初心者にもわかりやすく説明します。

### プロジェクトの目的
- 複数のニュースサイト（Reuters、Bloomberg）から自動で記事を収集
- AIで記事の要約と感情分析を実行
- HTMLページで整理された形で表示

---

## 🔍 問題の経緯

### 初期の問題: 記事重複表示

**問題の症状:**
- HTMLページに過去のすべての記事が累積して表示される
- 新しい記事だけでなく、前回実行時の記事も重複して表示
- ページが膨大な記事数になってしまう

**原因の特定プロセス:**

1. **最初の仮説**: HTMLファイルの上書き問題
   - 結果: HTMLファイルは正しく上書きされていた

2. **第二の仮説**: ブラウザキャッシュ問題  
   - 結果: キャッシュ無効化しても問題継続

3. **真の原因発見**: データベース活用不足
   - **問題**: 毎回スクレイピングした全記事をHTMLに出力
   - **問題**: データベースの重複チェック機能を活用していない
   - **問題**: 過去の記事との区別ができていない

---

## 🗄️ データベース設計

### テーブル構造

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    articles     │    │   ai_analysis   │    │scraping_sessions│
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ id (主キー)      │◄──┤ article_id      │    │ id (主キー)      │
│ url             │    │ summary         │    │ started_at      │
│ url_hash        │    │ sentiment_label │    │ completed_at    │
│ title           │    │ sentiment_score │    │ status          │
│ body            │    │ analyzed_at     │    │ articles_found  │
│ source          │    │ model_version   │    │ articles_processed│
│ category        │    └─────────────────┘    │ error_details   │
│ published_at    │                           └─────────────────┘
│ created_at      │
│ content_hash    │
└─────────────────┘
```

### テーブルの役割

#### 1. `articles` テーブル
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    url_hash TEXT UNIQUE NOT NULL,  -- 重複チェック用
    title TEXT NOT NULL,
    body TEXT,
    source TEXT NOT NULL,
    category TEXT,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_hash TEXT  -- 内容の重複チェック用
);
```

**役割**: すべての記事の基本情報を保存
- `url_hash`: URLの重複チェック（同じ記事の重複登録を防ぐ）
- `content_hash`: 記事内容の重複チェック（異なるURLでも同じ内容の記事を検出）

#### 2. `ai_analysis` テーブル
```sql
CREATE TABLE ai_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    summary TEXT,
    sentiment_label TEXT,
    sentiment_score REAL,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_version TEXT,
    processing_time_ms INTEGER,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);
```

**役割**: AI分析結果を保存
- 記事とは別テーブルで管理（正規化）
- 分析の再実行や履歴管理が可能

#### 3. `scraping_sessions` テーブル
```sql
CREATE TABLE scraping_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT,
    articles_found INTEGER,
    articles_processed INTEGER,
    error_details TEXT
);
```

**役割**: 各実行セッションの管理
- 実行ごとの統計情報を記録
- エラー追跡とデバッグ支援

---

## 🔄 処理フローの変遷

### Before: 旧処理フロー（問題あり）

```
スクレイピング → AI処理 → 全記事をHTMLに出力
     ↓
データベースは単純な保存のみ
重複チェックなし
過去記事との区別なし
```

**問題点:**
- 毎回すべての記事をHTMLに含める
- データベースの重複チェック機能を活用せず
- 新旧記事の区別ができない

### After: 新処理フロー（DB中心設計）

```
1. スクレイピング（記事収集）
   ↓
2. データベース保存（重複チェック付き）
   ├─ URL重複チェック
   ├─ 内容重複チェック  
   └─ 新規記事のみIDを返却
   ↓
3. 新規記事のみAI処理
   ↓
4. 未処理記事のAI処理（過去の記事も含む）
   ↓
5. 24時間以内の全記事を取得してHTML生成
```

**改善点:**
- データベースが処理の中心
- 重複を自動で排除
- 新規記事のみをAI処理（効率化）
- 適切な期間の記事のみを表示

---

## 🛠️ 技術的改善点

### 1. 重複排除システム

#### URL重複チェック
```python
def save_article(self, article_data):
    normalized_url = self.url_normalizer.normalize_url(article_data['url'])
    url_hash = hashlib.sha256(normalized_url.encode('utf-8')).hexdigest()
    
    existing = session.query(Article).filter_by(url_hash=url_hash).first()
    if existing:
        return existing.id, False  # 既存記事
    
    # 新規記事として保存
    return new_article_id, True
```

#### 内容重複チェック
```python
if article_data.get('body'):
    content_hash = self.content_deduplicator.generate_content_hash(article_data['body'])
```

### 2. セッション管理システム

```python
def start_scraping_session(self) -> int:
    """各実行の開始を記録"""
    scraping_session = ScrapingSession()
    session.add(scraping_session)
    session.flush()
    return scraping_session.id

def complete_scraping_session(self, session_id: int, status: str):
    """実行完了を記録"""
    session = self.get_session_by_id(session_id)
    session.completed_at = datetime.utcnow()
    session.status = status
```

### 3. 段階的AI処理

```python
# 1. 新規記事のAI処理
def process_new_articles_with_ai(self, new_article_ids):
    # 新規記事のみを並列処理

# 2. 未処理記事のAI処理  
def process_recent_articles_without_ai(self):
    # 24時間以内でAI分析がない記事を処理
```

---

## 📋 実装の詳細

### データベース初期化

```python
# src/database/models.py
class Article(Base):
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    url_hash = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    # ... その他のカラム
    
    # リレーション定義
    ai_analysis = relationship("AIAnalysis", back_populates="article")
```

### 重複チェック付き保存

```python
# src/database/database_manager.py
def save_article(self, article_data) -> Tuple[Optional[int], bool]:
    """
    記事保存（重複チェック付き）
    
    Returns:
        (記事ID, 新規作成フラグ)
    """
    with self.get_session() as session:
        # URL重複チェック
        normalized_url = self.url_normalizer.normalize_url(article_data['url'])
        url_hash = hashlib.sha256(normalized_url.encode('utf-8')).hexdigest()
        
        existing = session.query(Article).filter_by(url_hash=url_hash).first()
        if existing:
            return existing.id, False
        
        # 新規記事として保存
        article = Article(
            url=article_data['url'],
            url_hash=url_hash,
            title=article_data['title'],
            # ... その他のフィールド
        )
        
        session.add(article)
        session.flush()
        return article.id, True
```

### HTML生成の改善

```python
# src/core/news_processor.py
def generate_final_html(self):
    """24時間以内の全記事（AI分析済み）を取得してHTML生成"""
    
    # データベースから適切な記事を取得
    recent_articles = self.db_manager.get_recent_articles_all(
        hours=self.config.scraping.hours_limit
    )
    
    # HTMLジェネレーター用にデータ変換
    articles_for_html = []
    for article in recent_articles:
        analysis = article.ai_analysis[0] if article.ai_analysis else None
        articles_for_html.append({
            "title": article.title,
            "url": article.url,
            "summary": analysis.summary if analysis else "要約はありません。",
            "source": article.source,
            "sentiment_label": analysis.sentiment_label if analysis else "N/A",
            "sentiment_score": analysis.sentiment_score if analysis else 0.0,
        })
    
    self.html_generator.generate_html_file(articles_for_html, "index.html")
```

---

## 🎯 学習ポイント

### 1. データベース設計の重要性
- **正規化**: 関連データを適切なテーブルに分割
- **インデックス**: 検索性能向上のためのurl_hash
- **外部キー**: データの整合性を保証

### 2. 重複処理戦略
- **URL正規化**: 同じ記事の異なるURLを統一
- **ハッシュ化**: 高速な重複チェック
- **段階的チェック**: URL → 内容の順で効率化

### 3. エラーハンドリング
- **DetachedInstanceError**: SQLAlchemyセッション管理
- **トランザクション**: データの整合性保証
- **リトライ機構**: 一時的な障害への対応

### 4. 性能最適化
- **並列処理**: AI分析の高速化
- **Eager Loading**: N+1問題の回避
- **セッション管理**: メモリ効率の向上

---

## 🔧 トラブルシューティング

### よくある問題と解決策

#### 1. DetachedInstanceError
**原因**: SQLAlchemyオブジェクトがセッションから切り離された
**解決**: 
```python
# eager loadingで関連データを事前取得
articles = session.query(Article).options(
    joinedload(Article.ai_analysis)
).all()

# セッションから明示的に切り離し
for article in articles:
    session.expunge(article)
```

#### 2. 記事が表示されない
**原因**: AI分析が完了していない記事は表示対象外
**解決**: 
```python
# AI分析の有無に関わらず記事を取得
def get_recent_articles_all(self, hours=24):
    return session.query(Article).outerjoin(AIAnalysis).filter(
        Article.published_at >= cutoff_time
    ).all()
```

#### 3. 重複記事の登録
**原因**: URL正規化が不完全
**解決**: 
```python
def normalize_url(self, url):
    # クエリパラメータ除去
    # プロトコル統一
    # 末尾スラッシュ除去
    return normalized_url
```

---

## 📈 今後の拡張ポイント

### 1. スケーラビリティ向上
- データベースの分割（シャーディング）
- キャッシュシステムの導入
- 非同期処理の拡張

### 2. 機能追加
- 記事カテゴリの自動分類
- 関連記事の推薦機能
- ユーザー設定による表示カスタマイズ

### 3. 監視・運用
- データベース性能監視
- 異常検知システム
- 自動バックアップ機能

---

このガイドを通じて、データベース中心のアーキテクチャ設計の重要性と、段階的な問題解決プロセスを理解していただけたでしょうか。データベースは単なるデータ保存場所ではなく、アプリケーション全体の設計思想を決定する重要な要素です。