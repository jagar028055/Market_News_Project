# 10分本番ポッドキャスト配信 プロダクション配信開始ガイド

**対象**: GitHub Actions本番配信開始  
**最終更新**: 2025-08-20  
**実行環境**: GitHub Actions (ubuntu-latest)

## 🚀 配信開始手順

### ステップ1: GitHub Secrets設定 🔑

GitHub リポジトリの **Settings > Secrets and variables > Actions** で以下を設定：

#### 必須シークレット
```bash
# Gemini AI API
GEMINI_API_KEY=<あなたのGemini APIキー>

# Google Cloud (TTS・Drive)
GOOGLE_SERVICE_ACCOUNT_JSON=<サービスアカウントJSON文字列>
GOOGLE_DRIVE_OUTPUT_FOLDER_ID=<Google Drive配信フォルダID>

# LINE通知 (オプション)
LINE_NOTIFY_TOKEN=<LINE Notify トークン>
```

#### 取得方法詳細

**1. Gemini API キー**
```bash
# https://aistudio.google.com/app/apikey
# 1. Google AI Studioにアクセス
# 2. "Create API Key"をクリック
# 3. 生成されたキーをコピー
```

**2. Google Cloud サービスアカウント**
```bash
# Google Cloud Console > IAM > サービスアカウント
# 1. 新しいサービスアカウント作成
# 2. 必要な権限付与:
#    - Cloud Text-to-Speech API 使用権限
#    - Google Drive API 使用権限
# 3. JSONキーをダウンロード
# 4. JSON内容全体を文字列として設定
```

**3. Google Drive フォルダID**
```bash
# Google Drive でポッドキャスト配信用フォルダ作成
# URL: https://drive.google.com/drive/folders/FOLDER_ID
# FOLDER_ID 部分をコピー
```

**4. LINE Notify トークン（オプション）**
```bash
# https://notify-bot.line.me/
# 1. LINEアカウントでログイン
# 2. "マイページ" > "トークンを発行する"
# 3. 通知を送信するトークルームを選択
# 4. 生成されたトークンをコピー
```

### ステップ2: 初回テスト実行 🧪

#### 手動テスト実行
1. GitHubリポジトリの **Actions** タブを開く
2. **"10分本番ポッドキャスト配信"** ワークフローを選択
3. **"Run workflow"** をクリック
4. **テストモード** を `true` に設定
5. **"Run workflow"** で実行開始

#### テスト実行確認項目
- [ ] 依存関係インストール成功
- [ ] 環境変数読み込み成功
- [ ] データベース記事取得成功
- [ ] Gemini台本生成成功
- [ ] TTS音声生成成功（短縮版）
- [ ] LINE通知送信成功（テストモード）

### ステップ3: 本番配信開始 🎯

#### 自動配信スケジュール
```yaml
# 平日朝7:00 JST（22:00 UTC）自動実行
schedule:
  - cron: '0 22 * * SUN-THU'  # 月曜-金曜 朝7:00
```

#### 手動本番実行
1. **Actions** > **"10分本番ポッドキャスト配信"**
2. **"Run workflow"**
3. **強制本番実行** を `true` に設定
4. **テストモード** は `false` のまま
5. 実行開始

### ステップ4: 配信結果確認 📊

#### 成功時の確認項目
- [ ] 10分間音声ファイル生成
- [ ] GitHub Pages配信URL生成
- [ ] RSS フィード更新
- [ ] LINE成功通知受信
- [ ] Google Drive保存確認

#### 配信成果物
```bash
# GitHub Pages
https://<username>.github.io/<repository>/podcast/

# RSS フィード
https://<username>.github.io/<repository>/podcast/rss.xml

# 音声ファイル（例）
https://<username>.github.io/<repository>/podcast/episodes/episode_20250820_070000.mp3
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. 環境変数エラー
```bash
Error: 必須環境変数が設定されていません: ['GEMINI_API_KEY']
```
**解決方法**: GitHub Secrets設定を再確認

#### 2. Google Cloud認証エラー
```bash
Error: Google Cloud authentication failed
```
**解決方法**: 
- サービスアカウントJSON形式確認
- 必要なAPI有効化確認
- 権限設定確認

#### 3. 記事取得失敗
```bash
Error: データベースから記事を取得できませんでした
```
**解決方法**:
- データベース接続確認
- 記事データ存在確認
- 通常のニュース収集システム稼働確認

#### 4. TTS生成失敗
```bash
Error: 音声生成に失敗しました
```
**解決方法**:
- Google Cloud TTS API有効化確認
- 課金設定確認（無料枠超過チェック）
- 台本文字数確認（2600-2800文字）

### ログ確認方法
```bash
# GitHub Actions実行ログ
Actions > ワークフロー実行 > 詳細ログ

# アーティファクト（詳細ログ）
Actions > ワークフロー実行 > Artifacts > podcast-logs-XXX
```

## 📈 運用監視

### 成功メトリクス
- **配信成功率**: 95%以上目標
- **音声品質**: 10分±30秒以内
- **配信時刻**: 平日朝7:00±5分以内
- **応答時間**: 全体処理30分以内

### LINE通知内容例
```bash
# 成功通知
✅ 10分ポッドキャスト配信成功
🕒 実行時刻: 2025-08-20 07:02:15 JST
📻 モード: 本番（自動）
🔗 実行ログ: https://github.com/...

# 失敗通知  
❌ 10分ポッドキャスト配信失敗
🕒 実行時刻: 2025-08-20 07:05:33 JST
📻 モード: 本番（自動）
🔧 確認が必要です
🔗 エラーログ: https://github.com/...
```

### 定期メンテナンス
- **週次**: 配信ログ確認・品質チェック
- **月次**: 使用料確認・最適化検討
- **四半期**: システム改善・機能追加検討

## 🎯 高度な設定オプション

### カスタムスケジュール
```yaml
# 土日も配信したい場合
schedule:
  - cron: '0 22 * * *'  # 毎日朝7:00
```

### 台本モデル変更
```bash
# GitHub Actions手動実行時
--script-model gemini-2.5-pro    # 高品質版
--script-model gemini-2.5-flash  # 高速版
```

### 配信時間調整
```bash
# 5分版
--duration 300

# 15分版  
--duration 900
```

## ✅ 配信開始チェックリスト

### 事前準備
- [ ] GitHub Secrets設定完了
- [ ] Google Cloud API有効化・課金設定
- [ ] LINE Notify設定（オプション）
- [ ] 通常ニュース収集システム稼働中

### テスト実行
- [ ] テストモード成功確認
- [ ] 音声品質確認
- [ ] 配信URL動作確認
- [ ] 通知システム動作確認

### 本番開始
- [ ] 自動スケジュール設定確認
- [ ] 監視・アラート設定
- [ ] エスカレーション手順確認

## 🏆 配信開始完了

**おめでとうございます！** 🎉

10分本番ポッドキャスト配信システムの配信が開始されました。毎平日朝7:00に高品質な金融ニュースポッドキャストが自動配信されます。

**リスナーアクセス方法**:
- **ポッドキャストサイト**: `https://<username>.github.io/<repository>/podcast/`
- **RSSフィード**: `https://<username>.github.io/<repository>/podcast/rss.xml`

ポッドキャストアプリでRSSフィードを登録すれば、自動で新エピソードが配信されます。