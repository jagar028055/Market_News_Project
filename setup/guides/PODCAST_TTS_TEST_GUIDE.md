# Google Cloud TTS ポッドキャスト機能テストガイド

## 実装概要

Google Cloud Text-to-Speech APIを使用したポッドキャスト機能のテスト実装が完了しました。

### 主な変更点

1. **依存関係追加**: `google-cloud-texttospeech>=2.16.0`
2. **TTS実装更新**: `gemini_tts_engine.py` → Google Cloud TTS API対応
3. **テストモード実装**: 短縮版音声生成・配信スキップ機能
4. **GitHub Actions対応**: 認証環境変数設定

## テスト実行手順

### 1. 基本接続テスト

```bash
# Google Cloud認証情報を環境変数に設定
export GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type":"service_account",...}'
# または
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# 基本接続テスト実行
python test_tts_connection.py
```

**期待される結果**:
- Google Cloud TTS client initialized successfully
- 音声合成成功メッセージ
- `test_output.mp3` ファイルが生成される

### 2. 短縮版ポッドキャストテスト

```bash
# 短縮版ポッドキャスト生成テスト
python test_short_podcast.py
```

**期待される結果**:
- 約30秒〜1分の音声ファイル生成
- ファイルサイズ: 数十KB〜数百KB
- `short_podcast_YYYYMMDD_HHMMSS.mp3` ファイルが生成される

### 3. GitHub Actions統合テスト（ローカル）

```bash
# GitHub Actions相当の処理をローカルで実行
python test_github_actions_integration.py
```

**期待される結果**:
- standalone_podcast_main.py が正常実行
- `output/podcast/test_market_news_YYYYMMDD_HHMMSS.mp3` ファイル生成
- 配信処理はスキップされる（テストモード）

### 4. GitHub Actions実際のテスト

#### 4.1 手動実行テスト

1. GitHub リポジトリの Actions タブへ移動
2. "Daily Podcast Broadcast" ワークフローを選択
3. "Run workflow" をクリック
4. 以下の設定で実行:
   - `force_run`: true
   - `test_mode`: true
   - `weekdays_only`: false

#### 4.2 必要なGitHub Secrets

以下のシークレットが設定されている必要があります:

```
GOOGLE_APPLICATION_CREDENTIALS_JSON  # Google Cloud サービスアカウント認証情報
GEMINI_API_KEY                      # Gemini API キー
LINE_CHANNEL_ACCESS_TOKEN           # LINE Bot アクセストークン
LINE_CHANNEL_SECRET                 # LINE Bot チャンネルシークレット
GOOGLE_OAUTH2_CLIENT_ID             # Google OAuth2 クライアントID
GOOGLE_OAUTH2_CLIENT_SECRET         # Google OAuth2 クライアントシークレット
GOOGLE_OAUTH2_REFRESH_TOKEN         # Google OAuth2 リフレッシュトークン
PODCAST_RSS_BASE_URL               # ポッドキャストRSSベースURL
PODCAST_AUTHOR_NAME                # ポッドキャスト作者名
PODCAST_AUTHOR_EMAIL               # ポッドキャスト作者メール
```

## 音声品質設定

### デフォルト設定 (`gemini_tts_engine.py`)

```python
DEFAULT_VOICE_CONFIG = {
    "voice_name": "ja-JP-Neural2-D",    # 日本語女性音声
    "speaking_rate": 1.0,               # 通常の速度
    "pitch": 0.0,                      # 標準ピッチ
    "volume_gain_db": 0.0,             # 音量調整なし
    "audio_encoding": "MP3",           # MP3出力
    "sample_rate_hertz": 44100         # 高品質サンプリングレート
}
```

### カスタマイズ例

```python
# より速い読み上げ
voice_config = {"speaking_rate": 1.2}

# 少し高いピッチ
voice_config = {"pitch": 2.0}

# 音量を少し上げる
voice_config = {"volume_gain_db": 3.0}
```

## トラブルシューティング

### 認証エラー

```
ValueError: Google Cloud TTS client initialization failed
```

**解決方法**:
1. `GOOGLE_APPLICATION_CREDENTIALS_JSON` 環境変数を確認
2. サービスアカウントに Text-to-Speech API 権限があることを確認
3. Google Cloud プロジェクトで Text-to-Speech API が有効になっていることを確認

### 音声合成エラー

```
セグメント合成エラー: 403 Forbidden
```

**解決方法**:
1. Google Cloud プロジェクトの請求が有効になっていることを確認
2. Text-to-Speech API の利用制限を確認
3. サービスアカウントの権限を確認

### ファイル生成されない

```
音声データが生成されませんでした
```

**解決方法**:
1. `output/podcast` ディレクトリの書き込み権限を確認
2. 台本テキストが適切であることを確認
3. ログでエラーメッセージを確認

## 費用概算

Google Cloud Text-to-Speech API の費用（2024年価格）:

- **Standard voices**: $4.00 per 1 million characters
- **Neural2 voices**: $16.00 per 1 million characters

**日次ポッドキャスト想定**:
- 台本文字数: 約1,000文字/日
- 月間文字数: 約30,000文字
- 月間費用: Neural2使用時 約$0.48

## 次のステップ

1. **本格運用設定**: `PODCAST_TEST_MODE=false` での動作確認
2. **LINE配信テスト**: 実際のLINE Bot配信確認
3. **RSS配信設定**: GitHub Pages での RSS フィード公開
4. **監視設定**: エラー通知・コスト監視機能追加

## 参考リンク

- [Google Cloud Text-to-Speech API Documentation](https://cloud.google.com/text-to-speech/docs)
- [GitHub Actions Secrets設定](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [LINE Bot API Documentation](https://developers.line.biz/en/docs/)