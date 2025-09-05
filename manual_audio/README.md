# NotebookLM 手動音声配信システム

## 📁 ディレクトリ構造

```
manual_audio/
├── upload/           # ここにNotebookLMの音声ファイルを配置
├── processed/        # 処理済みファイルの保管場所（自動管理）
└── README.md         # このファイル
```

## 🎯 使用手順

### 1. NotebookLMで音声生成
1. NotebookLMで市場ニュースのポッドキャストを生成
2. 生成された音声ファイルをダウンロード

### 2. ファイル命名・配置
1. ダウンロードしたファイルを以下の命名規則でリネーム：
   ```
   notebooklm_YYYYMMDD.mp3
   ```
   例: `notebooklm_20250830.mp3`

2. リネームしたファイルを `manual_audio/upload/` ディレクトリに配置

### 3. GitHubにコミット・プッシュ
```bash
git add manual_audio/upload/notebooklm_YYYYMMDD.mp3
git commit -m "feat: NotebookLM音声アップロード - YYYY-MM-DD"
git push
```

### 4. 自動処理の確認
- GitHub Actionsが自動で配信処理を実行
- 処理完了後、音声ファイルはGitHub Pagesで配信開始
- RSSフィードに自動追加
- LINE通知が送信される（設定されている場合）

## 📋 ファイル命名規則

### 推奨命名パターン
- `notebooklm_YYYYMMDD.mp3` - 基本パターン
- `notebooklm_20250830_morning.mp3` - 時間帯指定
- `notebooklm_20250830_special.mp3` - 特別版

### 日付の取得方法
- ファイル名から自動抽出（YYYYMMDD形式）
- 抽出できない場合はファイルのアップロード日時を使用

## ⚠️ 注意事項

### ファイル要件
- **形式**: MP3ファイルのみ対応
- **サイズ**: 最大50MB（GitHub制限）
- **長さ**: 特に制限なし（推奨: 5-30分）

### アップロード時の注意
- 同日の既存ファイルは上書きされます
- アップロード後は自動で `processed/` に移動されます
- 処理中のファイル削除は避けてください

## 🔧 トラブルシューティング

### よくある問題

**Q: ファイルをアップロードしても処理されない**
A: 以下を確認：
- ファイル名が命名規則に従っているか
- MP3形式であるか
- GitHub Actionsが有効になっているか

**Q: 音声が配信されない**
A: GitHub Actionsのログを確認：
- https://github.com/あなたのユーザー名/Market_News_Project/actions

**Q: RSSに反映されない**
A: 処理には数分かかることがあります。しばらく待ってから確認してください。

## 📊 処理状況の確認方法

### 1. GitHub Actions
- リポジトリの「Actions」タブでワークフロー実行状況を確認
- エラーが発生した場合はログで詳細を確認

### 2. 配信確認
- GitHub Pages: `https://あなたのユーザー名.github.io/Market_News_Project/podcast/`
- RSSフィード: `https://あなたのユーザー名.github.io/Market_News_Project/podcast/feed.xml`

### 3. ファイル移動確認
- 処理完了後、ファイルが `upload/` から `processed/` に移動される
- `processed/` 内のファイル作成時刻で処理完了時刻を確認可能

## 🚀 高度な使い方

### バッチアップロード
複数ファイルを一度にアップロード可能：
```bash
git add manual_audio/upload/*.mp3
git commit -m "feat: 複数日分のNotebookLM音声をバッチアップロード"
git push
```

### カスタムメタデータ
ファイル名に追加情報を含めることで自動タグ付け：
- `_morning` - 朝のニュース
- `_evening` - 夕方のニュース
- `_special` - 特別版
- `_weekly` - 週間まとめ

例: `notebooklm_20250830_morning.mp3`

## 📞 サポート

問題が発生した場合は：
1. GitHub Actionsのログを確認
2. ファイル命名規則を再確認
3. 必要に応じてGitHub Issueを作成

---

**最終更新**: 2025-08-30
**バージョン**: 1.0