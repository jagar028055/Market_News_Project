# Google Cloud Console OAuth2 設定手順書

## 🎯 目的
スプレッドシート機能追加に伴う「フルスコープでのトークンリフレッシュエラー」を解決するため、Google Cloud ConsoleでOAuth2設定を確認・更新します。

## 📋 必要なスコープ
```
https://www.googleapis.com/auth/drive
https://www.googleapis.com/auth/documents  
https://www.googleapis.com/auth/spreadsheets
```

## 🔧 設定手順

### Step 1: Google Cloud Console にアクセス
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを選択（Market News Project関連）

### Step 2: OAuth 同意画面の確認・更新

#### 2.1 同意画面への移動
1. 左メニュー → 「APIとサービス」 → 「OAuth同意画面」

#### 2.2 スコープの確認・追加
1. 「編集」ボタンをクリック
2. 「スコープ」セクションに移動
3. 「スコープを追加または削除」をクリック
4. 以下のスコープが含まれているかチェック：
   - ✅ `https://www.googleapis.com/auth/drive` - Google Drive API
   - ✅ `https://www.googleapis.com/auth/documents` - Google Docs API  
   - ✅ `https://www.googleapis.com/auth/spreadsheets` - Google Sheets API

#### 2.3 スコープが不足している場合の追加手順
1. 「スコープを追加」をクリック
2. 検索ボックスに `spreadsheets` と入力
3. 「Google Sheets API」を選択
4. `https://www.googleapis.com/auth/spreadsheets` を追加
5. 「更新」をクリック

#### 2.4 公開ステータスの確認
- **推奨**: 「本番」ステータス（External users利用可能）
- **避ける**: 「テスト」ステータス（7日でトークン失効）

### Step 3: OAuth Client の確認

#### 3.1 認証情報ページへ移動
1. 左メニュー → 「APIとサービス」 → 「認証情報」

#### 3.2 OAuth 2.0 クライアント ID の確認
1. 「OAuth 2.0 クライアント ID」セクションを確認
2. 使用中のクライアントをクリック

#### 3.3 設定の確認事項
- **アプリケーションの種類**: デスクトップアプリ
- **承認済みのリダイレクトURI**: `http://localhost` が含まれているか
- **クライアントID**: GitHubシークレット`GOOGLE_OAUTH2_CLIENT_ID`と一致するか
- **クライアントシークレット**: GitHubシークレット`GOOGLE_OAUTH2_CLIENT_SECRET`と一致するか

### Step 4: API の有効化確認

#### 4.1 APIライブラリページへ移動
1. 左メニュー → 「APIとサービス」 → 「ライブラリ」

#### 4.2 必要なAPIの有効化確認
以下のAPIが有効になっているかチェック：
- ✅ Google Drive API
- ✅ Google Docs API  
- ✅ Google Sheets API

#### 4.3 無効になっている場合の有効化
1. 対象APIを検索
2. 「有効にする」をクリック

## 🚨 よくある問題と解決策

### 問題1: `invalid_grant` エラー
**原因**: リフレッシュトークンとクライアント情報の不一致
**解決策**: 
1. クライアントIDとシークレットの再確認
2. 新しいリフレッシュトークンの生成

### 問題2: `invalid_scope` エラー  
**原因**: スプレッドシートスコープが未承認
**解決策**:
1. OAuth同意画面でスプレッドシートスコープを追加
2. 新しいリフレッシュトークンの生成

### 問題3: `access_denied` エラー
**原因**: テストユーザーとして登録されていない（テストモードの場合）
**解決策**:
1. OAuth同意画面を「本番」に変更、または
2. テストユーザーとしてアカウントを追加

## 📝 次のステップ

設定確認・更新後：
1. `setup_oauth2.py` でフルスコープトークンを再生成
2. GitHub シークレット `GOOGLE_OAUTH2_REFRESH_TOKEN` を更新
3. GitHub Actions での動作テスト

## 🔍 トラブルシューティング

設定後もエラーが続く場合：
1. ブラウザキャッシュをクリア
2. 異なるブラウザで認証を試行
3. OAuth同意画面の「本番」への変更を確認
4. 24時間後に再試行（設定反映の待機）

---

**⚠️ 重要**: OAuth同意画面の変更は反映に時間がかかる場合があります。設定変更後、24時間程度の待機が必要な場合があります。