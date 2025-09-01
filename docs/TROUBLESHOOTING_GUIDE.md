# Flash+Pro Market News System - トラブルシューティングガイド

## 一般的な問題と解決方法

### 1. システム起動エラー

#### 症状
```
ModuleNotFoundError: No module named 'xxx'
```

#### 原因と対処法
- **原因**: 依存関係未インストール
- **対処**: `pip install -r requirements.txt`

#### 症状
```
sqlite3.OperationalError: database is locked
```

#### 原因と対処法
- **原因**: データベースファイルロック
- **対処**: プロセス終了後、`.db-wal`, `.db-shm` ファイル削除

### 2. API関連エラー

#### Gemini API エラー
```
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded
```
- **対処**: API使用量確認、時間を置いて再実行

#### Google Drive API エラー
```
HttpError 403: Insufficient Permission
```
- **対処**: サービスアカウント権限確認、共有設定確認

### 3. パフォーマンス問題

#### 処理速度低下
- **症状**: 記事処理が異常に遅い
- **原因**: 大量データ処理、メモリ不足
- **対処**: バッチサイズ削減、メモリ監視

#### メモリ使用量増加
- **症状**: メモリ使用量が継続的に増加
- **原因**: メモリリーク、キャッシュ蓄積
- **対処**: 定期的プロセス再起動、キャッシュクリア

### 4. データ品質問題

#### 重複記事の発生
- **症状**: 同じ記事が複数回処理される
- **原因**: URL正規化不備、重複除去ロジック不備
- **対処**: `cleanup_duplicates.py` 実行

#### 地域・カテゴリ分類精度低下
- **症状**: 分類結果が不適切
- **原因**: キーワード辞書更新不足
- **対処**: キーワード辞書メンテナンス

## ログ解析

### エラーログの場所
- メインログ: `logs/market_news.log`
- エラーログ: `logs/error.log`

### 重要なログパターン
```
ERROR:root:Pro API call failed: <error_message>
WARNING:cost_manager:Monthly cost limit approaching
INFO:article_grouper:Processing 150 articles
```

## 復旧手順

### データベース復旧
1. バックアップファイルから復旧
```bash
cp backup_YYYYMMDD.db market_news.db
```

2. 整合性チェック
```bash
sqlite3 market_news.db "PRAGMA integrity_check;"
```

### 設定ファイル復旧
1. `.env.example` から `.env` 再作成
2. 環境変数値を適切に設定

## 予防保守

### 日次メンテナンス
- [ ] ログローテーション
- [ ] 一時ファイル削除
- [ ] パフォーマンス指標確認

### 週次メンテナンス
- [ ] データベースバックアップ
- [ ] システムアップデート確認
- [ ] 設定ファイル見直し

---
更新日: 2025-08-13
