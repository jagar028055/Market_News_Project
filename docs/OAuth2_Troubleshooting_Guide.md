# OAuth2 トラブルシューティングガイド

## 🎯 目的
Google OAuth2認証で発生する「フルスコープでのトークンリフレッシュエラー」の解決方法を体系的にまとめます。

---

## 🚨 主要エラーと解決法

### 1. `invalid_scope` エラー

#### 症状
```
❌ フルスコープでのトークンリフレッシュエラー: ('invalid_scope: ...', 'error': 'invalid_scope')
```

#### 原因
- スプレッドシートスコープ(`https://www.googleapis.com/auth/spreadsheets`)が未承認
- 既存のリフレッシュトークンがDrive+Docsスコープのみで生成されている

#### 解決手順
1. **Google Cloud Console設定確認**
   ```bash
   # 詳細手順の確認
   cat docs/Google_Cloud_Console_OAuth2_Setup.md
   ```

2. **新しいトークン生成**
   ```bash
   python scripts/utilities/setup_oauth2.py
   # 選択: 2. 新しいリフレッシュトークンを生成
   ```

3. **GitHubシークレット更新**
   - `GOOGLE_OAUTH2_REFRESH_TOKEN` を新しい値に置換

---

### 2. `invalid_grant` エラー

#### 症状
```
❌ フルスコープでのトークンリフレッシュエラー: ('invalid_grant: Bad Request', 'error': 'invalid_grant')
```

#### 原因
- リフレッシュトークンが失効または取り消し済み
- クライアントIDとシークレットの不一致
- OAuth同意画面の公開状態に問題

#### 解決手順
1. **既存トークン診断**
   ```bash
   python scripts/utilities/setup_oauth2.py
   # 選択: 1. 既存のリフレッシュトークンを診断
   ```

2. **クライアント情報確認**
   - GitHubシークレット `GOOGLE_OAUTH2_CLIENT_ID` と Google Cloud Console の値が一致するか
   - GitHubシークレット `GOOGLE_OAUTH2_CLIENT_SECRET` と Google Cloud Console の値が一致するか

3. **OAuth同意画面の確認**
   - 公開ステータスが「本番」になっているか
   - 「テスト」ステータスの場合は7日でトークンが失効

---

### 3. `unauthorized_client` エラー

#### 症状
```
❌ フルスコープでのトークンリフレッシュエラー: ('unauthorized_client: ...', 'error': 'unauthorized_client')
```

#### 原因
- OAuth Clientの設定問題
- アプリケーション種別の不一致

#### 解決手順
1. **Google Cloud Console でクライアント設定確認**
   - アプリケーション種別: 「デスクトップアプリケーション」
   - 承認済みリダイレクトURI: `http://localhost` が含まれているか

2. **新しいOAuth Clientの作成**（必要に応じて）
   - 既存設定が正しくない場合は新規作成

---

## 🔧 診断・解決ツール

### 1. 既存トークン診断ツール
```bash
# 現在のトークンの状態を詳細診断
python scripts/utilities/setup_oauth2.py

# 選択: 1. 既存のリフレッシュトークンを診断
```

**確認項目:**
- 環境変数の設定状況
- トークンの有効性
- 取得済みスコープの確認

### 2. 新しいトークン生成ツール
```bash
# フルスコープ対応の新しいトークンを生成
python scripts/utilities/setup_oauth2.py

# 選択: 2. 新しいリフレッシュトークンを生成
```

**自動実行内容:**
- スコープ診断
- .env ファイル更新
- GitHub Secrets用の値表示

### 3. ローカル認証テスト
```bash
# OAuth2認証の動作確認
python -c "from gdocs.oauth2_client import test_oauth2_connection; test_oauth2_connection()"
```

---

## 📋 ステップバイステップ解決手順

### Step 1: 現状診断
```bash
# 1. 既存トークンの診断
python scripts/utilities/setup_oauth2.py
# → 選択: 1

# 2. エラー内容の確認
# GitHub Actions のログでエラー詳細を確認
```

### Step 2: Google Cloud Console設定
```bash
# 設定手順の確認
cat docs/Google_Cloud_Console_OAuth2_Setup.md
```

**重要チェックポイント:**
- ✅ OAuth同意画面でスプレッドシートスコープが承認済み
- ✅ OAuth同意画面が「本番」ステータス
- ✅ OAuth Clientが「デスクトップアプリ」で設定済み

### Step 3: 新しいトークン生成
```bash
# フルスコープでトークン再生成
python scripts/utilities/setup_oauth2.py
# → 選択: 2

# スコープ診断結果を確認:
# ✅ Google Drive API: 承認済み
# ✅ Google Docs API: 承認済み  
# ✅ Google Sheets API: 承認済み
```

### Step 4: GitHub設定更新
1. **GitHubリポジトリのSettings → Secrets and variables → Actions**
2. **以下のシークレットを更新:**
   - `GOOGLE_OAUTH2_CLIENT_ID`
   - `GOOGLE_OAUTH2_CLIENT_SECRET`
   - `GOOGLE_OAUTH2_REFRESH_TOKEN`

### Step 5: 動作確認
```bash
# GitHub Actions手動実行
# または定期実行の結果確認
```

---

## 🔍 よくある問題と対処法

### Q1: 「スコープが不足している」と表示される
**A:** Google Cloud Console のOAuth同意画面でスプレッドシートスコープを追加し、新しいトークンを生成してください。

### Q2: 設定を変更したのにエラーが続く
**A:** OAuth設定の反映には最大24時間かかる場合があります。時間をおいて再試行してください。

### Q3: ローカルでは動作するがGitHub Actionsで失敗する
**A:** GitHubシークレットの値とローカル環境の`.env`ファイルの値が一致しているか確認してください。

### Q4: フォールバック機能でドキュメント生成のみ実行される
**A:** これは正常な動作です。スプレッドシート機能は無効化されますが、ドキュメント生成は継続されます。

---

## 📞 サポート情報

### エラーが解決しない場合
1. **ログの詳細確認**: GitHub Actions の実行ログを詳細に確認
2. **環境変数の再確認**: 全ての必要な環境変数が正しく設定されているか
3. **権限の確認**: Google Drive フォルダの共有設定が正しいか

### 追加リソース
- [Google Cloud Console OAuth2 設定手順](./Google_Cloud_Console_OAuth2_Setup.md)
- [OAuth2認証調査レポート](./OAuth2_Auth_Investigation.md)

---

**⚠️ 重要**: トークンの再生成は慎重に行い、古いトークンは適切に無効化してください。セキュリティ上、不要になったトークンは削除することをお勧めします。