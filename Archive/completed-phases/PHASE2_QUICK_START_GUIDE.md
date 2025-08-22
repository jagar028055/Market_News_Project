# Phase 2: スマート通知システム クイックスタートガイド

## 🚀 概要

Phase 2で実装されたスマート通知システムを使用して、LINE Flex Messageによる高品質なポッドキャスト通知を配信する方法を説明します。

## 📋 前提条件

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

新しい依存関係:
- `schedule>=1.2.0` (スケジューリング)
- `pillow>=10.0.0` (画像処理)

### 2. LINE Bot設定

1. [LINE Developers Console](https://developers.line.biz/)でMessaging API設定
2. Channel Access Tokenを取得
3. 設定ファイルにトークンを追加

## 🎯 基本的な使用方法

### 1. システム初期化

```python
from src.config.app_config import AppConfig
from src.podcast.integration.smart_notification_manager import SmartNotificationManager
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 設定読み込み
config = AppConfig()

# スマート通知管理システム初期化
manager = SmartNotificationManager(config, logger)

# システム開始
manager.start_system()
```

### 2. 即座通知配信

```python
from datetime import datetime

# エピソード情報
episode_info = {
    'published_at': datetime.now(),
    'file_size_mb': 5.2,
    'article_count': 8,
    'title': 'マーケットニュース 2025年8月14日版'
}

# 記事データ
articles = [
    {
        'title': '日経平均株価が大幅上昇、年内最高値を更新',
        'sentiment_label': 'Positive',
        'summary': '東京株式市場で日経平均株価が前日比500円高で終了...'
    },
    # 他の記事...
]

# 配信オプション
options = {
    'use_flex_message': True,          # Flex Message使用
    'use_images': True,                # 画像アセット使用
    'audio_url': 'https://example.com/podcast/episode.mp3',
    'rss_url': 'https://example.com/podcast/feed.xml'
}

# 即座配信実行
result = manager.send_podcast_notification(episode_info, articles, options)

if result['success']:
    print(f"配信成功: {result['sent_at']}")
else:
    print(f"配信失敗: {result.get('error', 'Unknown error')}")
```

### 3. スケジュール配信

```python
from datetime import datetime, timedelta
from src.podcast.integration.notification_scheduler import NotificationPriority

# スケジュールオプション
schedule_options = {
    'scheduled_time': datetime.now() + timedelta(hours=2),  # 2時間後
    'priority': NotificationPriority.HIGH,                  # 高優先度
    'use_flex_message': True,
    'use_images': True,
    'audio_url': 'https://example.com/podcast/episode.mp3'
}

# スケジュール配信登録
result = manager.schedule_podcast_notification(episode_info, articles, schedule_options)

if result['success']:
    notification_id = result['notification_id']
    scheduled_time = result['scheduled_time']
    print(f"スケジュール登録成功: {notification_id}")
    print(f"配信予定時刻: {scheduled_time}")
    
    # 通知ステータス確認
    status = manager.scheduler.get_notification_status(notification_id)
    print(f"現在のステータス: {status['status']}")
```

### 4. 複数エピソード配信

```python
# 複数エピソードデータ
episodes = [
    {
        'episode_info': episode_info_1,
        'articles': articles_1,
        'options': {'audio_url': 'https://example.com/episode1.mp3'}
    },
    {
        'episode_info': episode_info_2,
        'articles': articles_2,
        'options': {'audio_url': 'https://example.com/episode2.mp3'}
    }
]

# バッチ配信オプション
batch_options = {
    'use_carousel': True,              # カルーセル形式
    'send_interval': 2                 # 2秒間隔（個別送信の場合）
}

# 複数エピソード配信
result = manager.send_multiple_episodes(episodes, batch_options)

print(f"配信方法: {result['method']}")
print(f"成功件数: {result.get('success_count', 0)}")
```

## 🎨 Flex Message カスタマイズ

### カスタムテンプレート作成

```python
from src.podcast.integration.flex_message_templates import FlexMessageTemplates

# カスタムテンプレートクラス
class CustomFlexTemplates(FlexMessageTemplates):
    def __init__(self, logger):
        super().__init__(logger)
        
        # カスタム色設定
        self.colors = {
            'primary': '#FF6B35',      # オレンジ
            'secondary': '#2E3A46',    # ダークブルー
            'accent': '#4ECDC4',       # ターコイズ
            'text_primary': '#2C3E50',
            'text_secondary': '#7F8C8D',
            'background': '#ECF0F1'
        }
        
        # カスタムアイコン
        self.icons = {
            'podcast': '🎧',
            'calendar': '📅',
            'highlight': '⭐',
            'time': '⏰',
            'size': '💿',
            'articles': '📋',
            'listen': '🎵',
            'rss': '📡'
        }

# カスタムテンプレートを使用
custom_templates = CustomFlexTemplates(logger)
manager.line_broadcaster.flex_templates = custom_templates
```

## 🖼️ 画像アセット設定

### カスタム画像設定

```python
from src.podcast.integration.image_asset_manager import ImageAssetManager

# 画像管理システム
image_manager = ImageAssetManager(config, logger)

# カスタム画像サイズ設定
image_manager.image_sizes = {
    'icon': (150, 150),           # アイコンサイズ変更
    'header': (1200, 600),        # ヘッダーサイズ変更
    'thumbnail': (400, 225),      # サムネイルサイズ変更
    'background': (1080, 1080)    # 背景サイズ変更
}

# 特定エピソードの画像生成
thumbnail_url = image_manager.get_or_create_podcast_image(
    episode_info, 
    'thumbnail'
)

if thumbnail_url:
    print(f"サムネイル画像URL: {thumbnail_url}")
```

## ⏰ スケジュール設定

### 最適配信時刻カスタマイズ

```python
# カスタム最適時刻設定
manager.scheduler.optimal_times = [
    "08:00",  # 朝の通勤時間
    "12:30",  # 昼休み
    "17:30",  # 夕方の通勤時間
    "20:00",  # 夕食後
    "22:00"   # 就寝前
]

# 優先度別スケジューリング
urgent_time = manager.scheduler._calculate_optimal_time(NotificationPriority.URGENT)    # 即座
high_time = manager.scheduler._calculate_optimal_time(NotificationPriority.HIGH)        # 次の最適時刻
normal_time = manager.scheduler._calculate_optimal_time(NotificationPriority.NORMAL)    # その後の最適時刻
low_time = manager.scheduler._calculate_optimal_time(NotificationPriority.LOW)          # さらに後
```

## 📊 監視とトラブルシューティング

### システムステータス確認

```python
# 全体ステータス取得
status = manager.get_system_status()

print(f"システム状態: {status['overall_status']}")
print(f"LINE接続状態: {status['components']['line_broadcaster']['connection_status']}")
print(f"スケジューラー状態: {'実行中' if status['components']['scheduler']['scheduler_running'] else '停止中'}")
print(f"画像キャッシュ: {status['components']['image_manager']['valid_entries']}件")
```

### 通知プレビュー

```python
# 配信前のプレビュー確認
preview = manager.get_notification_preview(episode_info, articles)

print(f"推定文字数: {preview['estimated_characters']}")
print(f"センチメント分布: {preview['sentiment_distribution']}")
print(f"画像URL: {list(preview['image_urls'].keys())}")

# テキストメッセージ確認
print("テキストメッセージプレビュー:")
print(preview['text_message'][:200] + "...")
```

### エラーハンドリング

```python
import logging

# 詳細ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('smart_notification.log'),
        logging.StreamHandler()
    ]
)

# エラー時の対処
try:
    result = manager.send_podcast_notification(episode_info, articles)
except Exception as e:
    logger.error(f"配信エラー: {e}")
    
    # フォールバック: テキストメッセージで再試行
    fallback_options = {'use_flex_message': False, 'use_images': False}
    fallback_result = manager.send_podcast_notification(episode_info, articles, fallback_options)
```

## 🔧 設定オプション一覧

### 配信オプション

```python
send_options = {
    # メッセージ形式
    'use_flex_message': True,          # Flex Message使用
    'use_images': True,                # 画像アセット使用
    
    # URL設定
    'audio_url': 'https://...',        # 音声ファイルURL
    'rss_url': 'https://...',          # RSSフィードURL
    
    # フォールバック
    'enable_fallback': True            # エラー時のフォールバック有効
}
```

### スケジュールオプション

```python
schedule_options = {
    # タイミング設定
    'scheduled_time': datetime(...),   # 配信予定時刻（指定時刻）
    'auto_schedule': True,             # 自動スケジューリング
    'priority': NotificationPriority.NORMAL,  # 優先度
    
    # 配信設定
    'use_flex_message': True,
    'use_images': True,
    'audio_url': 'https://...',
    'rss_url': 'https://...'
}
```

## 🧪 テスト実行

```bash
# 統合テスト実行
python test_phase2_smart_notification.py

# ユニットテスト実行
python -m pytest tests/unit/test_smart_notification_system.py -v
```

## 📚 関連ドキュメント

- [Phase 2 実装完了レポート](PHASE2_SMART_NOTIFICATION_COMPLETION_REPORT.md)
- [LINE Flex Message デザインガイド](https://developers.line.biz/ja/docs/messaging-api/flex-message-layout/)
- [ポッドキャスト統合ドキュメント](src/podcast/README.md)

## 🆘 サポート

問題が発生した場合は、以下を確認してください：

1. **依存関係**: `pip install -r requirements.txt`
2. **LINE設定**: Channel Access Tokenが正しく設定されているか
3. **ログ**: `smart_notification.log`でエラー詳細を確認
4. **テスト**: `test_phase2_smart_notification.py`でシステム動作確認

---

**Phase 2 スマート通知システム** により、ポッドキャスト配信の品質とユーザーエンゲージメントが大幅に向上しました。