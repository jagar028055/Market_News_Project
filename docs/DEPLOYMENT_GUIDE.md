# Market News Project - デプロイメントガイド
## パーソナライゼーション機能完全対応版

**バージョン**: v1.4.0  
**最終更新**: 2025-08-15  
**対応機能**: Flash+Pro + パーソナライゼーション

## 概要

Market News Projectのパーソナライゼーション機能を含む統合システムの本番環境デプロイメント手順書です。

## システム要件

### ハードウェア要件
- CPU: 4コア以上 (パーソナライゼーション処理最適化)
- RAM: 8GB以上 (機械学習・分析処理)
- ディスク: 20GB以上の空き容量 (ユーザーデータ・ログ保存)

### ソフトウェア要件
- Python 3.10以上
- SQLite 3.35以上 (パーソナライゼーションDB対応)
- Git 2.20以上

### 新規依存関係（パーソナライゼーション機能）
```bash
# パーソナライゼーション機能で使用
numpy>=1.24.0  # 数値計算（軽量実装のため最小限）
scipy>=1.10.0  # 統計分析
scikit-learn>=1.3.0  # 機械学習アルゴリズム（オプション）
```

## セットアップ手順

### 1. リポジトリクローン
```bash
git clone <repository-url>
cd Market_News_Project
git checkout Flash+Pro
```

### 2. 仮想環境セットアップ
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows
```

### 3. 依存関係インストール
```bash
pip install -r requirements.txt
```

### 4. 環境変数設定
```bash
cp .env.example .env
# .envファイルを編集し、適切な値を設定
```

### 5. データベース初期化
```bash
python -c "from src.database.database_manager import DatabaseManager; DatabaseManager().init_database()"
```

### 6. 動作確認
```bash
python test_phase4_integration.py
```

## 本番環境固有設定

### Google APIs認証
1. Google Cloud Consoleでプロジェクト作成
2. Gemini API、Drive API、Docs APIを有効化
3. サービスアカウント作成と認証情報ダウンロード
4. 環境変数に認証情報パス設定

### Pro統合要約設定
- 日次実行回数制限: 3回
- 月間コスト上限: $50
- 実行時間帯: 9時、15時、21時（JST）

### ログ設定
- ログレベル: INFO（本番）、DEBUG（開発）
- ログローテーション: 日次、7日間保持

## 監視・メンテナンス

### 日次チェック項目
- [ ] システム稼働状況確認
- [ ] ログエラー確認
- [ ] API使用量確認
- [ ] データベース容量確認

### 週次チェック項目
- [ ] パフォーマンス指標確認
- [ ] バックアップ状況確認
- [ ] セキュリティアップデート確認

## 緊急時対応

### システム停止時
1. ログファイル確認
2. プロセス再起動
3. データベース整合性確認

### API制限到達時
1. 使用量確認
2. 一時的な処理停止
3. 制限解除まで待機

---
更新日: 2025-08-13
バージョン: Flash+Pro Phase 4.3
