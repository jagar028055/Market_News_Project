# Google Cloud Text-to-Speech API 有効化手順書

## 🔍 問題の詳細

**現状**:
- サービスアカウント: `podcast-tts@gemini-api-in-vscode.iam.gserviceaccount.com`
- 使用プロジェクトID: `1072034849655`
- エラー: `Cloud Text-to-Speech API has not been used in project 1072034849655 before or it is disabled`

**必要な対応**: プロジェクト `1072034849655` でText-to-Speech APIを有効化する

## 🚀 解決手順

### ステップ1: Google Cloud Console へアクセス

1. 以下のリンクをブラウザで開く:
   ```
   https://console.developers.google.com/apis/api/texttospeech.googleapis.com/overview?project=1072034849655
   ```

2. Google アカウントでログイン（サービスアカウントを作成したアカウント）

### ステップ2: Text-to-Speech API を有効化

1. **「API を有効にする」** ボタンをクリック
2. 有効化処理が完了するまで待機（通常1-2分）
3. 「API が有効になりました」メッセージを確認

### ステップ3: サービスアカウントの権限確認

1. Google Cloud Console で **「IAM」** ページに移動:
   ```
   https://console.cloud.google.com/iam-admin/iam?project=1072034849655
   ```

2. `podcast-tts@gemini-api-in-vscode.iam.gserviceaccount.com` を検索

3. 以下の権限が付与されているか確認:
   - `Cloud Text-to-Speech User` (roles/texttospeech.user)
   - または `Editor` (roles/editor)
   - または `Owner` (roles/owner)

4. 権限が不足している場合:
   - サービスアカウント名をクリック
   - **「権限を編集」** → **「別のロールを追加」**
   - `Cloud Text-to-Speech User` を選択して保存

### ステップ4: 有効化の確認

APIを有効化後、以下のコマンドでテスト実行:

```bash
# GitHub Actions でのテスト実行
gh workflow run "Daily Podcast Broadcast" --ref feature/google-cloud-tts-test -f test_mode=true -f force_run=true
```

**期待される結果**:
- ✅ Google Cloud TTS client initialized successfully
- ✅ セグメント合成成功（403エラーなし）
- ✅ 実際のGoogle TTSで音声生成

## 🛠 代替手順（上記手順で解決しない場合）

### オプションA: 直接プロジェクト管理画面から有効化

1. Google Cloud Console のプロジェクト選択画面に移動:
   ```
   https://console.cloud.google.com/home?project=1072034849655
   ```

2. 左側メニュー「APIとサービス」→「ライブラリ」をクリック

3. 検索バーで「Text-to-Speech」を検索

4. 「Cloud Text-to-Speech API」を選択

5. 「有効にする」をクリック

### オプションB: gcloud CLI を使用（上級者向け）

```bash
# プロジェクト設定
gcloud config set project 1072034849655

# APIを有効化
gcloud services enable texttospeech.googleapis.com

# 有効化確認
gcloud services list --enabled --filter="texttospeech"
```

## 🔧 トラブルシューティング

### 問題1: プロジェクトにアクセスできない

**原因**: サービスアカウントを作成したGoogleアカウントでログインしていない

**解決法**: 
1. 正しいGoogleアカウントでログイン
2. または、プロジェクトの所有者から管理者権限を付与してもらう

### 問題2: APIを有効化してもエラーが継続

**原因**: APIの有効化反映に時間がかかっている

**解決法**:
1. 5-10分待ってから再実行
2. ブラウザのキャッシュをクリア
3. 違うブラウザ・シークレットモードで再試行

### 問題3: サービスアカウントが見つからない

**原因**: サービスアカウントが別のプロジェクトに作成されている

**解決法**:
1. 既存のサービスアカウントを `1072034849655` プロジェクトに移行
2. または、`1072034849655` プロジェクトで新しいサービスアカウントを作成

## 📊 費用について

**Text-to-Speech API の料金**:
- Neural2 voices: $16.00 per 1 million characters
- Standard voices: $4.00 per 1 million characters

**推定月額費用**（日次1000文字の場合）:
- Neural2: 約$0.48/月
- Standard: 約$0.12/月

## ✅ 完了確認チェックリスト

- [ ] Google Cloud Console でText-to-Speech APIが「有効」表示
- [ ] サービスアカウントに適切な権限が付与
- [ ] GitHub Actionsでテストモード実行成功
- [ ] エラーログに403エラーが出ない
- [ ] 実際の音声ファイルが生成される

## 🎯 次のステップ

API有効化後の推奨作業:

1. **本格運用モード設定**:
   - `PODCAST_TEST_MODE=false` での実行確認
   - 音声品質・長さの調整

2. **監視・運用設定**:
   - コスト監視アラート設定
   - エラー通知設定

3. **配信機能統合**:
   - LINE Bot配信テスト
   - RSS フィード公開確認

---

**重要**: このガイドの手順完了後、Issue #4 のコメントに結果を報告してください。