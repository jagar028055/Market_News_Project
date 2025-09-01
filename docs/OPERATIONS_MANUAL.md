# Market News Project - 統合運用マニュアル
## パーソナライゼーション機能対応版

**バージョン**: v1.4.0  
**最終更新**: 2025-08-15  
**対応機能**: Flash+Pro + パーソナライゼーション

---

## 🚀 パーソナライゼーション機能運用

### 1. ユーザー管理操作

#### ユーザープロファイル管理
```bash
# ユーザープロファイル確認
python -c "
from src.personalization.user_optimizer import UserOptimizer
optimizer = UserOptimizer()
profile = optimizer.get_user_profile('user_001')
print(f'ユーザー: {profile.user_id}, エンゲージメント: {profile.engagement_score}')
"

# 全ユーザーの分析データ一覧取得
python -c "
from src.personalization.user_optimizer import UserOptimizer
import sqlite3
optimizer = UserOptimizer()
with sqlite3.connect('user_profiles.db') as conn:
    cursor = conn.execute('SELECT user_id, engagement_score FROM user_profiles ORDER BY engagement_score DESC LIMIT 10')
    for row in cursor.fetchall():
        print(f'User: {row[0]}, Score: {row[1]:.3f}')
"
```

#### セグメンテーション状況確認
```bash
# セグメント分布確認
python -c "
from src.personalization.user_segmentation import DynamicUserSegmentation
segmentation = DynamicUserSegmentation()
metrics = segmentation.calculate_segmentation_metrics()
print(f'総ユーザー数: {metrics.total_users}')
print(f'アクティブセグメント数: {metrics.total_segments}')
print(f'品質スコア: {metrics.quality_score:.3f}')
"

# 特定セグメントのユーザー一覧
python -c "
from src.personalization.user_segmentation import DynamicUserSegmentation
segmentation = DynamicUserSegmentation()
users = segmentation.get_segment_users('power_users')
print(f'パワーユーザー: {len(users)}名')
for user in users[:5]:
    print(f'  - {user}')
"
```

### 2. 予測分析・モニタリング

#### 予測精度確認
```bash
# エンゲージメント予測の実行
python -c "
from src.personalization.predictive_analytics import PredictiveAnalytics
import json
analytics = PredictiveAnalytics()

# テストユーザーの予測実行
test_interactions = [
    {'timestamp': '2025-08-15T09:00:00', 'action_type': 'view', 'session_duration': 120},
    {'timestamp': '2025-08-15T18:30:00', 'action_type': 'share', 'session_duration': 60}
]

prediction = analytics.predict_user_engagement('test_user', test_interactions)
print(f'予測エンゲージメント: {prediction.predicted_value:.3f}')
print(f'信頼度: {prediction.confidence_level:.3f}')
"

# チャーンリスク高ユーザーの検出
python -c "
from src.personalization.predictive_analytics import PredictiveAnalytics
import sqlite3
analytics = PredictiveAnalytics()

# 高リスクユーザー（閾値: 0.7以上）の検出例
print('チャーンリスク高ユーザーの監視（実装例）:')
print('- 3日以上アクセスなし')
print('- エンゲージメント継続低下')  
print('- セッション時間短縮傾向')
"
```

### 3. 配信タイミング最適化

#### 最適配信時間の確認・調整
```bash
# ユーザー別最適配信時間確認
python -c "
from src.personalization.timing_optimizer import IntelligentTimingOptimizer
optimizer = IntelligentTimingOptimizer()

# テストユーザーの分析データ取得
analytics_data = optimizer.get_user_timing_analytics('test_user')
print('配信タイミング分析結果:')
if analytics_data['latest_optimal_timing']:
    timing = analytics_data['latest_optimal_timing']
    print(f'推奨時間: {timing[\"recommended_time\"]}')
    print(f'信頼度: {timing[\"confidence_score\"]}')
    print(f'戦略: {timing[\"strategy\"]}')
"

# 配信パフォーマンス確認
python -c "
from src.personalization.timing_optimizer import IntelligentTimingOptimizer
import sqlite3
optimizer = IntelligentTimingOptimizer()

with sqlite3.connect('timing_optimizer.db') as conn:
    cursor = conn.execute('''
        SELECT time_slot, AVG(engagement_rate), AVG(response_rate), COUNT(*) as samples
        FROM timing_metrics 
        GROUP BY time_slot 
        ORDER BY AVG(engagement_rate) DESC
        LIMIT 5
    ''')
    print('時間帯別エンゲージメント上位5位:')
    for row in cursor.fetchall():
        print(f'{row[0]}: エンゲージメント{row[1]:.3f}, レスポンス率{row[2]:.3f} ({row[3]}件)')
"
```

---

## 📊 日常運用（基本機能）

### 1. システム起動
```bash
cd Market_News_Project
source venv/bin/activate
python main.py
```

### 2. ログ監視
```bash
tail -f logs/market_news.log
```

### 3. パフォーマンス確認
```bash
python performance_optimizer.py
```

## Pro統合要約機能

### 手動実行
```bash
python -c "
from ai_pro_summarizer import ProSummarizer
from cost_manager import CostManager
# 手動実行コード
"
```

### 実行条件確認
- 記事数: 10件以上
- 日次実行回数: 3回以下
- 月間コスト: $50以下

## データベース管理

### バックアップ
```bash
sqlite3 market_news.db ".backup backup_$(date +%Y%m%d).db"
```

### クリーンアップ
```bash
python cleanup_duplicates.py
```

## トラブルシューティング

### よくある問題

#### 1. Gemini API エラー
- 原因: APIキー未設定、制限超過
- 対処: 環境変数確認、使用量確認

#### 2. Google Drive接続エラー
- 原因: 認証情報不正、権限不足
- 対処: 認証情報再設定、権限確認

#### 3. メモリ不足エラー
- 原因: 大量記事処理、メモリリーク
- 対処: バッチサイズ削減、プロセス再起動

---
更新日: {datetime.now().strftime('%Y-%m-%d')}
