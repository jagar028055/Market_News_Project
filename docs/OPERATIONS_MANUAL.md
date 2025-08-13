# Flash+Pro Market News System - 運用マニュアル

## 日常運用

### 1. システム起動
```bash
cd Market_News_Project
source venv/bin/activate
python main.py
```

### 2. ログ監視
```bash
tail -f logs/market_news.log
```

### 3. パフォーマンス確認
```bash
python performance_optimizer.py
```

## Pro統合要約機能

### 手動実行
```bash
python -c "
from ai_pro_summarizer import ProSummarizer
from cost_manager import CostManager
# 手動実行コード
"
```

### 実行条件確認
- 記事数: 10件以上
- 日次実行回数: 3回以下
- 月間コスト: $50以下

## データベース管理

### バックアップ
```bash
sqlite3 market_news.db ".backup backup_$(date +%Y%m%d).db"
```

### クリーンアップ
```bash
python cleanup_duplicates.py
```

## トラブルシューティング

### よくある問題

#### 1. Gemini API エラー
- 原因: APIキー未設定、制限超過
- 対処: 環境変数確認、使用量確認

#### 2. Google Drive接続エラー
- 原因: 認証情報不正、権限不足
- 対処: 認証情報再設定、権限確認

#### 3. メモリ不足エラー
- 原因: 大量記事処理、メモリリーク
- 対処: バッチサイズ削減、プロセス再起動

---
更新日: {datetime.now().strftime('%Y-%m-%d')}
