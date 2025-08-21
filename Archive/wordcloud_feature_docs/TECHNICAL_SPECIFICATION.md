# 日次ワードクラウド機能 - 技術仕様書

## 🏗️ システム構成

### アーキテクチャ概要
```
Market News Project
├── src/
│   ├── wordcloud/
│   │   ├── __init__.py
│   │   ├── generator.py          # ワードクラウド生成エンジン
│   │   ├── processor.py          # テキスト前処理
│   │   ├── visualizer.py         # 視覚化コンポーネント
│   │   └── config.py             # 設定管理
│   ├── database/
│   │   └── models.py             # WordCloudDataモデル追加
│   └── html/
│       └── html_generator.py     # HTML統合機能拡張
├── assets/
│   ├── css/
│   │   └── wordcloud.css         # 専用スタイル
│   └── fonts/
│       └── NotoSansCJK-Regular.ttf  # 日本語フォント
└── wordcloud_feature_docs/       # 本ドキュメント
```

---

## 🔧 コア技術仕様

### 1. ワードクラウド生成エンジン

#### 1.1 `WordCloudGenerator`クラス
```python
class WordCloudGenerator:
    """
    メインのワードクラウド生成クラス
    """
    
    def __init__(self, config: WordCloudConfig):
        self.config = config
        self.processor = TextProcessor(config)
        self.visualizer = WordCloudVisualizer(config)
        
    def generate_daily_wordcloud(self, articles: List[Dict]) -> WordCloudResult:
        """
        日次ワードクラウド生成のメインメソッド
        
        Args:
            articles: 記事データリスト
            
        Returns:
            WordCloudResult: 生成結果
        """
        
    def _extract_text_content(self, articles: List[Dict]) -> str:
        """記事から本文テキストを抽出"""
        
    def _calculate_word_frequencies(self, text: str) -> Dict[str, int]:
        """単語頻度計算"""
        
    def _apply_financial_weights(self, frequencies: Dict[str, int]) -> Dict[str, int]:
        """金融重要語句の重み付け適用"""
```

#### 1.2 設定仕様
```python
@dataclass
class WordCloudConfig:
    # 画像設定
    width: int = 800
    height: int = 400
    background_color: str = "rgba(0,0,0,0)"
    
    # フォント設定
    font_path: str = "assets/fonts/NotoSansCJK-Regular.ttf"
    max_font_size: int = 100
    min_font_size: int = 20
    
    # 色彩設定
    color_scheme: List[str] = field(default_factory=lambda: [
        "#2E8B57", "#32CD32", "#4682B4", 
        "#6495ED", "#DC143C", "#FF6347"
    ])
    
    # 処理設定
    max_words: int = 100
    relative_scaling: float = 0.5
    min_word_frequency: int = 2
    
    # 日本語処理設定
    mecab_dicdir: Optional[str] = None
    stopwords_file: str = "assets/config/stopwords_japanese.txt"
    
    # 金融重要語句重み
    financial_weights: Dict[str, float] = field(default_factory=lambda: {
        "金利": 3.0, "GDP": 2.5, "インフレ": 2.8,
        "日銀": 3.2, "FRB": 3.0, "ECB": 2.5,
        "株価": 2.8, "円安": 2.5, "ドル": 2.3,
        "決算": 2.2, "業績": 2.0, "投資": 2.4
    })
```

### 2. テキスト前処理システム

#### 2.1 `TextProcessor`クラス
```python
class TextProcessor:
    """
    テキスト前処理専用クラス
    """
    
    def __init__(self, config: WordCloudConfig):
        self.config = config
        self.mecab = MeCab.Tagger(f"-d {config.mecab_dicdir}" if config.mecab_dicdir else "")
        self.stopwords = self._load_stopwords()
        
    def process_articles_text(self, articles: List[Dict]) -> str:
        """記事リストからテキストを処理"""
        
    def _extract_meaningful_words(self, text: str) -> List[str]:
        """形態素解析で意味のある単語を抽出"""
        
    def _filter_words(self, words: List[str]) -> List[str]:
        """ストップワード除去とフィルタリング"""
        
    def _normalize_financial_terms(self, words: List[str]) -> List[str]:
        """金融用語の正規化"""
```

#### 2.2 日本語処理詳細
```python
# 形態素解析設定
MECAB_POS_FILTERS = [
    "名詞,一般",      # 一般名詞
    "名詞,固有名詞",  # 固有名詞
    "名詞,サ変接続",  # サ変動詞語幹
    "動詞,自立",      # 自立動詞
    "形容詞,自立",    # 自立形容詞
]

# 除外する品詞
EXCLUDE_POS = [
    "助詞", "助動詞", "接続詞", "感動詞", "記号", "フィラー"
]

# 最小文字数
MIN_WORD_LENGTH = 2

# 数字・記号パターン
EXCLUDE_PATTERNS = [
    r'^\d+$',           # 数字のみ
    r'^[a-zA-Z]$',      # 1文字の英字
    r'^[。、]$',        # 句読点
]
```

### 3. 視覚化コンポーネント

#### 3.1 `WordCloudVisualizer`クラス
```python
class WordCloudVisualizer:
    """
    ワードクラウド視覚化専用クラス
    """
    
    def __init__(self, config: WordCloudConfig):
        self.config = config
        
    def create_wordcloud_image(self, word_frequencies: Dict[str, int]) -> str:
        """
        ワードクラウド画像生成
        
        Returns:
            str: base64エンコードされた画像データ
        """
        
    def _color_function(self, word: str, font_size: int, 
                       position: Tuple[int, int], orientation: int, 
                       font_path: str, random_state: int) -> str:
        """カスタムカラー関数"""
        
    def _generate_base64_image(self, wordcloud_obj) -> str:
        """WordCloudオブジェクトからbase64画像生成"""
```

#### 3.2 色彩設計
```python
# 金融テーマ配色パレット
COLOR_PALETTES = {
    "professional": {
        "primary": ["#1E3A8A", "#3B82F6", "#60A5FA"],     # 青系
        "positive": ["#059669", "#10B981", "#34D399"],    # 緑系（上昇）
        "negative": ["#DC2626", "#EF4444", "#F87171"],    # 赤系（下降）
        "neutral": ["#6B7280", "#9CA3AF", "#D1D5DB"]     # グレー系
    }
}

# 重要度による色分け
def get_word_color(word: str, frequency: int, max_frequency: int) -> str:
    """
    単語の重要度に基づく色選択
    
    Args:
        word: 対象単語
        frequency: 出現頻度
        max_frequency: 最大出現頻度
    
    Returns:
        str: HEXカラーコード
    """
```

---

## 🗄️ データベース設計

### 1. 新規テーブル追加

#### 1.1 `wordcloud_data`テーブル
```sql
CREATE TABLE wordcloud_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 画像データ
    image_base64 TEXT NOT NULL,
    image_size_bytes INTEGER,
    
    -- メタデータ
    total_articles INTEGER NOT NULL,
    total_words INTEGER NOT NULL,
    unique_words INTEGER NOT NULL,
    
    -- 処理統計
    generation_time_ms INTEGER,
    memory_usage_mb REAL,
    
    -- 設定情報
    config_version VARCHAR(20),
    
    -- インデックス
    FOREIGN KEY (session_id) REFERENCES scraping_sessions(id),
    INDEX idx_wordcloud_generated (generated_at),
    INDEX idx_wordcloud_session (session_id)
);
```

#### 1.2 `wordcloud_frequencies`テーブル
```sql
CREATE TABLE wordcloud_frequencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wordcloud_data_id INTEGER NOT NULL,
    word VARCHAR(100) NOT NULL,
    frequency INTEGER NOT NULL,
    weight_applied REAL DEFAULT 1.0,
    
    -- インデックス
    FOREIGN KEY (wordcloud_data_id) REFERENCES wordcloud_data(id),
    INDEX idx_word_frequency (word, frequency),
    INDEX idx_wordcloud_word (wordcloud_data_id, word)
);
```

### 2. 既存テーブル拡張

#### 2.1 `scraping_sessions`テーブル拡張
```sql
-- 新規カラム追加
ALTER TABLE scraping_sessions 
ADD COLUMN wordcloud_generated BOOLEAN DEFAULT FALSE;

ALTER TABLE scraping_sessions 
ADD COLUMN wordcloud_generation_time_ms INTEGER;
```

---

## 🌐 HTML統合仕様

### 1. HTMLテンプレート拡張

#### 1.1 ワードクラウドセクション
```html
<!-- wordcloud-section.html -->
<section class="wordcloud-section" id="daily-wordcloud">
    <div class="wordcloud-header">
        <h2 class="section-title">
            <span class="icon">📊</span>
            今日の市場キーワード
        </h2>
        <div class="wordcloud-meta">
            <span class="update-time">更新時刻: {{update_timestamp}}</span>
            <span class="article-count">対象記事: {{article_count}}件</span>
        </div>
    </div>
    
    <div class="wordcloud-container">
        <div class="wordcloud-loading" id="wordcloud-loading">
            <div class="spinner"></div>
            <p>ワードクラウドを生成中...</p>
        </div>
        
        <div class="wordcloud-image-container" id="wordcloud-image">
            <img src="data:image/png;base64,{{wordcloud_base64}}" 
                 alt="市場キーワード分析 - {{word_count}}個のキーワード"
                 class="wordcloud-img">
        </div>
        
        <div class="wordcloud-stats">
            <div class="stat-item">
                <span class="stat-label">総単語数</span>
                <span class="stat-value">{{total_words}}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">ユニーク単語</span>
                <span class="stat-value">{{unique_words}}</span>
            </div>
        </div>
    </div>
</section>
```

#### 1.2 CSS仕様
```css
/* wordcloud.css */
.wordcloud-section {
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 2rem;
    margin: 2rem 0;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.wordcloud-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 1rem;
}

.section-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1e293b;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.wordcloud-container {
    position: relative;
    min-height: 400px;
    display: flex;
    flex-direction: column;
    align-items: center;
}

.wordcloud-img {
    max-width: 100%;
    height: auto;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* レスポンシブ対応 */
@media (max-width: 768px) {
    .wordcloud-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 1rem;
    }
    
    .wordcloud-section {
        padding: 1rem;
    }
}
```

### 2. JavaScript統合

#### 2.1 動的ロード機能
```javascript
// wordcloud-loader.js
class WordCloudLoader {
    constructor() {
        this.loadingElement = document.getElementById('wordcloud-loading');
        this.imageElement = document.getElementById('wordcloud-image');
    }
    
    async loadWordCloud() {
        try {
            this.showLoading();
            
            // サーバーから最新のワードクラウドデータを取得
            const response = await fetch('/api/wordcloud/latest');
            const data = await response.json();
            
            if (data.success) {
                this.displayWordCloud(data.wordcloud);
            } else {
                this.showError(data.error);
            }
            
        } catch (error) {
            this.showError(error.message);
        }
    }
    
    showLoading() {
        this.loadingElement.style.display = 'flex';
        this.imageElement.style.display = 'none';
    }
    
    displayWordCloud(wordcloudData) {
        // 画像とメタデータを表示
        this.loadingElement.style.display = 'none';
        this.imageElement.style.display = 'block';
    }
}
```

---

## 🔄 処理フロー詳細

### 1. メイン処理フロー
```python
def generate_daily_wordcloud_workflow(session_id: int, articles: List[Dict]) -> bool:
    """
    日次ワードクラウド生成の完全なワークフロー
    """
    
    try:
        # 1. 初期化
        generator = WordCloudGenerator(get_wordcloud_config())
        start_time = time.time()
        
        # 2. テキスト前処理
        processed_text = generator.processor.process_articles_text(articles)
        
        # 3. 単語頻度計算
        frequencies = generator._calculate_word_frequencies(processed_text)
        
        # 4. 金融重要語句重み付け
        weighted_frequencies = generator._apply_financial_weights(frequencies)
        
        # 5. ワードクラウド画像生成
        image_base64 = generator.visualizer.create_wordcloud_image(weighted_frequencies)
        
        # 6. データベース保存
        save_result = save_wordcloud_to_db(session_id, {
            'image_base64': image_base64,
            'word_frequencies': weighted_frequencies,
            'generation_time_ms': int((time.time() - start_time) * 1000),
            'total_articles': len(articles)
        })
        
        # 7. HTML更新
        update_html_with_wordcloud(image_base64, get_wordcloud_metadata())
        
        return True
        
    except Exception as e:
        logger.error(f"ワードクラウド生成エラー: {e}")
        return False
```

### 2. エラーハンドリング
```python
class WordCloudError(Exception):
    """ワードクラウド関連の例外"""
    pass

class TextProcessingError(WordCloudError):
    """テキスト処理エラー"""
    pass

class ImageGenerationError(WordCloudError):
    """画像生成エラー"""
    pass

def handle_wordcloud_error(error: Exception, fallback_action: str = "display_default"):
    """
    ワードクラウド生成エラーの統一ハンドリング
    """
    
    if isinstance(error, TextProcessingError):
        # テキスト処理エラーの場合: 簡易版で再試行
        logger.warning("テキスト処理エラー - 簡易版で再実行")
        return generate_simple_wordcloud()
        
    elif isinstance(error, ImageGenerationError):
        # 画像生成エラーの場合: デフォルト画像表示
        logger.error("画像生成エラー - デフォルト画像を表示")
        return get_default_wordcloud_image()
        
    else:
        # その他のエラー: フォールバック処理
        logger.error(f"予期しないエラー: {error}")
        return execute_fallback_action(fallback_action)
```

---

## ⚡ パフォーマンス最適化

### 1. メモリ管理
```python
# 大量記事処理時のメモリ最適化
def process_articles_batch(articles: List[Dict], batch_size: int = 100):
    """
    記事を分割処理してメモリ使用量を制限
    """
    
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        yield process_article_batch(batch)
        
        # メモリ使用量監視
        if psutil.virtual_memory().percent > 80:
            gc.collect()  # ガベージコレクション実行
```

### 2. キャッシュ戦略
```python
from functools import lru_cache

@lru_cache(maxsize=10)
def get_stopwords_cache(lang: str = 'japanese') -> Set[str]:
    """ストップワードリストのキャッシュ"""
    return load_stopwords_file(f"assets/config/stopwords_{lang}.txt")

@lru_cache(maxsize=5)
def get_mecab_instance(dicdir: Optional[str] = None) -> MeCab.Tagger:
    """MeCabインスタンスのキャッシュ"""
    return MeCab.Tagger(f"-d {dicdir}" if dicdir else "")
```

---

## 🧪 テスト仕様

### 1. ユニットテスト
```python
# tests/test_wordcloud_generator.py
class TestWordCloudGenerator:
    
    def test_generate_daily_wordcloud_success(self):
        """正常なワードクラウド生成テスト"""
        
    def test_japanese_text_processing(self):
        """日本語テキスト処理テスト"""
        
    def test_financial_weights_application(self):
        """金融重要語句重み付けテスト"""
        
    def test_image_generation_base64(self):
        """base64画像生成テスト"""
        
    def test_error_handling(self):
        """エラーハンドリングテスト"""
```

### 2. 統合テスト
```python
# tests/test_wordcloud_integration.py
class TestWordCloudIntegration:
    
    def test_end_to_end_generation(self):
        """記事投入からHTML表示までの統合テスト"""
        
    def test_database_integration(self):
        """データベース連携テスト"""
        
    def test_html_integration(self):
        """HTML統合テスト"""
```

---

## 📦 デプロイメント仕様

### 1. 依存関係インストール
```bash
# requirements.txt 追加分
pip install wordcloud>=1.9.2
pip install mecab-python3>=1.0.6
pip install pillow>=10.0.0
```

### 2. 設定ファイル配置
```bash
# フォント配置
mkdir -p assets/fonts/
# NotoSansCJK-Regular.ttf を配置

# ストップワード配置  
mkdir -p assets/config/
# stopwords_japanese.txt を配置
```

### 3. 環境変数設定
```bash
# .env 追加設定
WORDCLOUD_ENABLED=true
WORDCLOUD_FONT_PATH=assets/fonts/NotoSansCJK-Regular.ttf
MECAB_DICDIR=/usr/local/lib/mecab/dic/mecab-ipadic-neologd
```