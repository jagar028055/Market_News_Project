# ポッドキャスト機能セットアップタスク

このドキュメントは、自動ポッドキャスト生成システムを実際に動作させるために必要な準備・設定・運用タスクをまとめています。

## 📋 Phase 1: 基本動作確認

### 1.1 API・サービスアカウント準備

#### 1.1.1 Google AI Studio (Gemini API) 設定
- [x] 既存のGemini APIキーを確認（記事要約に使用しているものを再利用）
- [ ] API使用量制限を確認（月額制限設定）

#### 1.1.2 LINE Developers Console 設定
- [x] [LINE Developers Console](https://developers.line.biz/) にアクセス
- [x] LINEアカウントでログイン
- [x] 新しいプロバイダーを作成（既存がない場合）
- [x] Messaging API チャンネルを作成
  - [x] チャンネル名: 「マーケットニュース」
  - [x] チャンネル説明: 「AIが生成する毎日のマーケットニュース」
  - [x] 大業種・小業種を選択
- [x] Channel Access Token (長期) を発行
- [x] Channel Secret を確認・コピー
- [x] Webhook設定が無効になっていることを確認（通常は初期状態で無効）
- [x] ブロードキャスト機能の利用可能性を確認（新規チャンネルは自動的に利用可能、フリープランで月1,000通まで無料）

#### 1.1.3 GitHub Pages 基本設定
- [x] GitHubリポジトリの Settings > Pages にアクセス
- [x] Source を "Deploy from a branch" (gh-pages) に設定済み
- [ ] カスタムドメイン設定（オプション）
- [x] HTTPS の強制を有効化
- [x] 公開範囲の確認（Public/Private）

### 1.2 ローカル環境準備

#### 1.2.1 依存関係インストール
- [x] Python 3.11+ の確認 (Python 3.13.5 利用可能)
```bash
python3 --version  # 3.13.5確認済み
```

- [x] 仮想環境の作成とアクティベート
```bash
python3 -m venv venv
source venv/bin/activate
```

- [x] 必要なパッケージのインストール
```bash
pip install feedgen pydub psutil pytest-cov isort
```

- [x] システム依存関係のインストール
  - [x] **macOS**: `brew install ffmpeg` (完了)
  - [ ] **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
  - [ ] **Windows**: [FFmpeg公式サイト](https://ffmpeg.org/download.html)からダウンロード・インストール

#### 1.2.2 環境変数設定ファイル作成
- [x] `.env.podcast.example` を `.env.podcast` にコピー（既に作成済み）
```bash
cp .env.podcast.example .env.podcast
```

- [x] `.env.podcast` ファイルを編集
  - [x] `GEMINI_API_KEY=your_actual_api_key`
  - [x] `LINE_CHANNEL_ACCESS_TOKEN=your_actual_token`
  - [x] `LINE_CHANNEL_SECRET=your_actual_secret`
  - [x] `PODCAST_RSS_BASE_URL=https://jagar028055.github.io/Market_News_Project`
  - [x] `PODCAST_AUTHOR_NAME=Your Name`
  - [x] `PODCAST_AUTHOR_EMAIL=your-email@example.com`

### 1.3 基本音声アセット準備

#### 1.3.1 音声ファイル配置ディレクトリ作成
- [ ] `assets/audio/` ディレクトリの存在確認
- [ ] 必要に応じてディレクトリ作成
```bash
mkdir -p assets/audio
```

#### 1.3.2 テスト用音声ファイル準備
**初期テスト用（無音ファイルでOK）:**
- [ ] `assets/audio/intro_jingle.mp3` - オープニング（3-5秒）
- [ ] `assets/audio/outro_jingle.mp3` - エンディング（3-5秒）
- [ ] `assets/audio/background_music.mp3` - BGM（10分以上）
- [ ] `assets/audio/segment_transition.mp3` - セグメント移行音（1-2秒）

**無音ファイル生成コマンド例:**
```bash
# 3秒の無音ファイル（intro用）
ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 3 -c:a mp3 assets/audio/intro_jingle.mp3

# 3秒の無音ファイル（outro用）
ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 3 -c:a mp3 assets/audio/outro_jingle.mp3

# 10分の無音ファイル（BGM用）
ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 600 -c:a mp3 assets/audio/background_music.mp3

# 1秒の無音ファイル（transition用）
ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 1 -c:a mp3 assets/audio/segment_transition.mp3
```

### 1.4 基本動作テスト

#### 1.4.1 API接続テスト
- [ ] Gemini API接続テスト
```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env.podcast')
import google.generativeai as genai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content('Hello, this is a test.')
print('API Test Success:', response.text[:50])
"
```

#### 1.4.2 ユニットテスト実行
- [ ] 台本生成機能テスト
```bash
python -m pytest tests/unit/test_script_generator.py -v
```

- [ ] TTS音声合成機能テスト
```bash
python -m pytest tests/unit/test_tts_engine.py -v
```

- [ ] 音声処理機能テスト
```bash
python -m pytest tests/unit/test_audio_processor.py -v
```

- [ ] RSS生成機能テスト
```bash
python -m pytest tests/unit/test_rss_generator.py -v
```

- [ ] LINE配信機能テスト
```bash
python -m pytest tests/unit/test_line_broadcaster.py -v
```

#### 1.4.3 統合テスト実行
- [ ] ポッドキャスト統合テスト
```bash
python -m pytest tests/integration/test_podcast_integration.py -v
```

- [ ] テストカバレッジ確認
```bash
python -m pytest tests/ --cov=src/podcast --cov-report=html
```

#### 1.4.4 手動実行テスト
- [ ] ポッドキャスト機能の手動実行
```bash
python podcast_main.py
```

- [ ] エラーログの確認
- [ ] 生成されたファイルの確認
- [ ] 処理時間の測定

## 📋 Phase 2: 配信機能設定

### 2.1 GitHub Secrets 設定

#### 2.1.1 必須Secrets追加
GitHubリポジトリの Settings > Secrets and variables > Actions で以下を追加:

**既存（ニュース機能用）:**
- [ ] `GEMINI_API_KEY` - Gemini API キー
- [ ] `GOOGLE_SERVICE_ACCOUNT_JSON` - Google サービスアカウントJSON
- [ ] `GOOGLE_DRIVE_OUTPUT_FOLDER_ID` - Google Drive 出力フォルダID

**新規（ポッドキャスト機能用）:**
- [ ] `ENABLE_PODCAST_GENERATION` - `true`
- [ ] `LINE_CHANNEL_ACCESS_TOKEN` - LINE チャンネルアクセストークン
- [ ] `LINE_CHANNEL_SECRET` - LINE チャンネルシークレット
- [ ] `PODCAST_RSS_BASE_URL` - GitHub PagesのURL
- [ ] `PODCAST_AUTHOR_NAME` - 著者名
- [ ] `PODCAST_AUTHOR_EMAIL` - 著者メールアドレス

**オプション設定:**
- [ ] `PODCAST_RSS_TITLE` - ポッドキャストタイトル
- [ ] `PODCAST_RSS_DESCRIPTION` - ポッドキャスト説明
- [ ] `PODCAST_MONTHLY_COST_LIMIT` - 月額コスト制限（デフォルト: 10.0）
- [ ] `PODCAST_TARGET_DURATION_MINUTES` - 目標再生時間（デフォルト: 10.0）
- [ ] `PODCAST_MAX_FILE_SIZE_MB` - 最大ファイルサイズ（デフォルト: 15）

#### 2.1.2 Secrets設定確認
- [ ] 全ての必須Secretsが設定されていることを確認
- [ ] Secretsの値に不正な文字（改行、スペース等）が含まれていないことを確認
- [ ] APIキーの有効性を確認

### 2.2 LINE Bot 詳細設定

#### 2.2.1 LINE Bot基本設定
- [ ] Bot情報の設定
  - [ ] Bot名: 「マーケットニュース」
  - [ ] 説明文: 「毎日のマーケットニュースをポッドキャストでお届け」
  - [ ] プロフィール画像の設定（オプション）
- [ ] 応答設定
  - [ ] 応答メッセージ: 無効
  - [ ] Webhook: 無効（ブロードキャストのみ使用）
- [ ] 友だち追加時の設定
  - [ ] あいさつメッセージの設定
  - [ ] 友だち追加時メッセージの設定

#### 2.2.2 LINE Bot テスト
- [ ] LINE公式アカウントを友だち追加
- [ ] 手動でテストメッセージ送信
```bash
# テスト用スクリプト実行
python -c "
from src.podcast.publisher import LINEBroadcaster
config = {'channel_access_token': 'your_token', 'test_mode': True, 'test_user_ids': ['your_user_id']}
broadcaster = LINEBroadcaster(config)
print('Connection test:', broadcaster.test_connection())
"
```

### 2.3 GitHub Actions ワークフロー確認

#### 2.3.1 ワークフロー設定確認
- [ ] `.github/workflows/main.yml` の内容確認
- [ ] ポッドキャスト関連の環境変数が正しく設定されていることを確認
- [ ] スケジュール設定の確認（毎日22:00 UTC = JST 07:00）
- [ ] タイムアウト設定の確認（20分）

#### 2.3.2 手動ワークフロー実行テスト
- [ ] GitHub Actions タブで手動実行
- [ ] `enable_podcast` を `true` に設定して実行
- [ ] 実行ログの確認
- [ ] エラーの有無確認
- [ ] 生成されたアーティファクトの確認

### 2.4 GitHub Pages 配信テスト

#### 2.4.1 Pages設定確認
- [ ] GitHub Pages が有効になっていることを確認
- [ ] カスタムドメインの動作確認（設定している場合）
- [ ] HTTPS証明書の有効性確認

#### 2.4.2 RSS配信テスト
- [ ] RSSフィードファイルの生成確認
- [ ] RSSフィードのアクセス確認
  - [ ] `https://your-username.github.io/your-repo/podcast/feed.xml`
- [ ] RSSフィードの妥当性確認
  - [ ] [W3C Feed Validator](https://validator.w3.org/feed/) でチェック
- [ ] ポッドキャストアプリでの購読テスト
  - [ ] Apple Podcasts
  - [ ] Spotify
  - [ ] Google Podcasts

## 📋 Phase 3: 本格運用準備

### 3.1 高品質音声アセット準備

#### 3.1.1 CC-BYライセンス音声素材調達
**推奨サイト:**
- [ ] [Freesound.org](https://freesound.org/) - CC-BYライセンス音源
- [ ] [Zapsplat](https://www.zapsplat.com/) - 要登録、商用利用可
- [ ] [YouTube Audio Library](https://www.youtube.com/audiolibrary/) - 著作権フリー
- [ ] [Pixabay Music](https://pixabay.com/music/) - 著作権フリー

#### 3.1.2 音声ファイル要件
**オープニングジングル (`intro_jingle.mp3`):**
- [ ] 長さ: 3-5秒
- [ ] 形式: MP3, 44.1kHz, ステレオ
- [ ] 内容: 明るく、ニュース番組らしい雰囲気
- [ ] 音量: -16 LUFS程度

**エンディングジングル (`outro_jingle.mp3`):**
- [ ] 長さ: 3-5秒
- [ ] 形式: MP3, 44.1kHz, ステレオ
- [ ] 内容: 締めくくりに適した落ち着いた雰囲気
- [ ] 音量: -16 LUFS程度

**バックグラウンドミュージック (`background_music.mp3`):**
- [ ] 長さ: 10分以上（ループ可能）
- [ ] 形式: MP3, 44.1kHz, ステレオ
- [ ] 内容: 控えめで、話し声を邪魔しない
- [ ] 音量: -30 LUFS程度（メイン音声より低く）

**セグメント移行音 (`segment_transition.mp3`):**
- [ ] 長さ: 1-2秒
- [ ] 形式: MP3, 44.1kHz, ステレオ
- [ ] 内容: 短いチャイム音やトランジション音
- [ ] 音量: -20 LUFS程度

#### 3.1.3 ライセンス管理
- [ ] 各音声ファイルのライセンス情報を記録
- [ ] クレジット情報をYAMLファイルに記載
```yaml
# assets/audio/credits.yaml
credits:
  intro_jingle:
    title: "News Intro"
    author: "Artist Name"
    source: "Freesound.org"
    license: "CC-BY 4.0"
    url: "https://freesound.org/s/123456/"
  outro_jingle:
    title: "News Outro"
    author: "Artist Name"
    source: "Freesound.org"
    license: "CC-BY 4.0"
    url: "https://freesound.org/s/123457/"
  background_music:
    title: "Ambient News Background"
    author: "Artist Name"
    source: "Pixabay"
    license: "Pixabay License"
    url: "https://pixabay.com/music/id-123456/"
  segment_transition:
    title: "Transition Chime"
    author: "Artist Name"
    source: "Zapsplat"
    license: "Standard License"
    url: "https://zapsplat.com/sound/123456/"
```

### 3.2 本番環境動作確認

#### 3.2.1 エンドツーエンドテスト
- [ ] 完全なポッドキャスト生成フローの実行
- [ ] 各段階での出力ファイル確認
  - [ ] 台本ファイル
  - [ ] TTS音声ファイル
  - [ ] 処理済み音声ファイル
  - [ ] RSSフィードファイル
- [ ] 処理時間の測定（15分以内）
- [ ] メモリ使用量の確認
- [ ] ディスク使用量の確認

#### 3.2.2 品質確認
- [ ] 生成された音声の品質確認
  - [ ] 音量レベル（-16 LUFS）
  - [ ] ファイルサイズ（15MB以下）
  - [ ] 再生時間（9.5-10分）
- [ ] 台本の品質確認
  - [ ] 文字数（2400-2800文字）
  - [ ] 対話の自然さ
  - [ ] 発音修正の適用
- [ ] RSSフィードの品質確認
  - [ ] メタデータの正確性
  - [ ] クレジット情報の表示
  - [ ] ポッドキャストアプリでの表示

#### 3.2.3 エラーハンドリング確認
- [ ] ニュース収集失敗時の動作
- [ ] TTS API制限時の動作
- [ ] 音声処理エラー時の動作
- [ ] 配信失敗時の動作
- [ ] コスト制限超過時の動作

### 3.3 監視・アラート設定

#### 3.3.1 コスト監視
- [ ] 月間コスト制限の設定確認
- [ ] コスト使用量の日次確認体制
- [ ] コストアラートの設定
- [ ] 使用量レポートの定期確認

#### 3.3.2 動作監視
- [ ] GitHub Actions実行結果の監視
- [ ] エラーログの定期確認
- [ ] 配信成功率の監視
- [ ] 音声品質の定期チェック

#### 3.3.3 ユーザーフィードバック収集
- [ ] LINE Bot経由でのフィードバック収集機能
- [ ] ポッドキャストアプリでのレビュー監視
- [ ] 配信統計の確認（ダウンロード数等）

## 📋 Phase 4: 運用・保守

### 4.1 日次運用タスク

#### 4.1.1 毎日の確認事項
- [ ] ポッドキャスト生成の成功/失敗確認
- [ ] GitHub Actions実行ログの確認
- [ ] エラーの有無確認
- [ ] 生成された音声の品質確認
- [ ] RSS配信の成功確認
- [ ] LINE配信の成功確認

#### 4.1.2 問題発生時の対応
- [ ] エラーログの詳細分析
- [ ] 問題の原因特定
- [ ] 緊急時の手動実行
- [ ] ユーザーへの状況報告（必要に応じて）

### 4.2 週次運用タスク

#### 4.2.1 パフォーマンス確認
- [ ] 処理時間の推移確認
- [ ] メモリ使用量の推移確認
- [ ] ファイルサイズの推移確認
- [ ] エラー率の推移確認

#### 4.2.2 品質確認
- [ ] 生成された台本の品質レビュー
- [ ] 音声品質の確認
- [ ] ユーザーフィードバックの確認
- [ ] 配信統計の確認

### 4.3 月次運用タスク

#### 4.3.1 コスト分析
- [ ] 月間コスト使用量の分析
- [ ] 予算との比較
- [ ] コスト最適化の検討
- [ ] 次月の予算計画

#### 4.3.2 機能改善検討
- [ ] ユーザーフィードバックの分析
- [ ] 新機能の検討
- [ ] 既存機能の改善点洗い出し
- [ ] 技術的負債の確認

### 4.4 保守・アップデート

#### 4.4.1 依存関係の更新
- [ ] Pythonパッケージの更新確認
- [ ] セキュリティアップデートの適用
- [ ] 非推奨機能の置き換え

#### 4.4.2 バックアップ・復旧
- [ ] 設定ファイルのバックアップ
- [ ] 音声アセットのバックアップ
- [ ] 過去エピソードのアーカイブ
- [ ] 復旧手順の確認・テスト

## 🚨 緊急時対応

### 緊急停止手順
- [ ] GitHub Actions ワークフローの無効化
- [ ] `ENABLE_PODCAST_GENERATION=false` の設定
- [ ] 緊急メンテナンス通知の検討

### 復旧手順
- [ ] 問題の原因特定
- [ ] 修正の実装
- [ ] テスト環境での動作確認
- [ ] 段階的な復旧実行
- [ ] 正常動作の確認

---

## ✅ 完了チェックリスト

### Phase 1 完了確認
- [ ] 全てのAPI・サービスアカウントが準備完了
- [ ] ローカル環境でのテストが全て成功
- [ ] 基本的な音声アセットが配置完了

### Phase 2 完了確認
- [ ] GitHub Secretsが全て設定完了
- [ ] LINE Bot が正常動作
- [ ] GitHub Actions が正常実行
- [ ] RSS配信が正常動作

### Phase 3 完了確認
- [ ] 高品質音声アセットが準備完了
- [ ] 本番環境での動作確認完了
- [ ] 監視・アラート体制が整備完了

### Phase 4 完了確認
- [ ] 運用体制が確立
- [ ] 保守手順が整備完了
- [ ] 緊急時対応手順が確認完了

---

**最終確認日:** ___________  
**確認者:** ___________  
**運用開始日:** ___________