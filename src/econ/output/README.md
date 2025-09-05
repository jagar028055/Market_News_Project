# 経済指標出力・可視化システム

## 🎯 概要

経済指標システムの出力・可視化機能を大幅に強化し、プロフェッショナル向けの高度な分析・ダッシュボード機能を提供します。

## 🚀 実装された機能

### 1. Google Sheets API連携 (`sheets_dashboard.py`)

**機能:**
- リアルタイムデータ更新
- マルチシート構成（サマリー、指標詳細、トレンド分析、相関分析、リスク評価）
- 自動書式設定とチャート埋め込み
- 自動更新スケジュール

**使用方法:**
```python
from src.econ.output import SheetsDashboardManager

# ダッシュボード管理
sheets_manager = SheetsDashboardManager()

# ダッシュボード作成
spreadsheet_id = sheets_manager.create_economic_dashboard(
    indicators, trend_results, "経済指標ダッシュボード"
)

# ダッシュボード更新
sheets_manager.update_dashboard(indicators, trend_results)

# URL取得
dashboard_url = sheets_manager.get_dashboard_url()
```

### 2. 高度なダッシュボード (`advanced_dashboard.py`)

**機能:**
- インタラクティブなPlotlyチャート
- 6つの分析セクション（トレンド、相関、リスク、サプライズ、ボラティリティ、予測精度）
- リアルタイム統計情報
- HTML/PNG/JSON出力

**使用方法:**
```python
from src.econ.output import AdvancedDashboard, DashboardConfig

# ダッシュボード設定
config = DashboardConfig(
    title="経済指標ダッシュボード",
    width=1400,
    height=800,
    save_path=Path("./output/dashboard")
)

# ダッシュボード作成
dashboard = AdvancedDashboard(config)
result = dashboard.create_comprehensive_dashboard(indicators, trend_results)

# HTML出力
html_content = result['html']
```

### 3. リアルタイム更新システム (`realtime_updater.py`)

**機能:**
- 自動データ更新（リアルタイム、時間毎、日次、週次）
- 並行処理による高速更新
- エラーハンドリングとリトライ機能
- Slack通知機能
- コールバック機能

**使用方法:**
```python
from src.econ.output import RealTimeUpdater, UpdateConfig, UpdateFrequency

# 更新設定
config = UpdateConfig(
    frequency=UpdateFrequency.HOURLY,
    update_sheets=True,
    update_dashboard=True,
    notify_on_success=True
)

# 更新システム開始
updater = RealTimeUpdater(config)
updater.start()

# コールバック追加
def on_data_update(indicators, trend_results):
    print(f"データ更新: {len(indicators)}指標")

updater.add_data_update_callback(on_data_update)

# システム停止
updater.stop()
```

### 4. 高度な可視化 (`visualization_enhancer.py`)

**機能:**
- 10種類の高度な可視化
- 統計分析（正規性検定、クラスタリング）
- レジーム検出
- リスクメトリクス分析
- 予測精度分析

**可視化タイプ:**
- トレンド分析
- 相関マトリクス
- ボラティリティサーフェス
- レジーム検出
- 予測精度
- リスクメトリクス
- セクター分析
- 国別比較
- 時系列分解
- 分布分析

**使用方法:**
```python
from src.econ.output import VisualizationEnhancer, VisualizationType

# 可視化エンハンサー
enhancer = VisualizationEnhancer()

# 特定の可視化を作成
viz_types = [
    VisualizationType.TREND_ANALYSIS,
    VisualizationType.CORRELATION_MATRIX,
    VisualizationType.RISK_METRICS
]

results = enhancer.create_advanced_visualizations(
    indicators, trend_results, viz_types
)

# 結果の利用
for viz_type, result in results.items():
    if 'error' not in result:
        html_content = result['html']
        figure = result['figure']
```

## 🎮 統合デモ

### デモ実行

```python
from src.econ.output import EconomicIndicatorsOutputDemo

# デモ実行
demo = EconomicIndicatorsOutputDemo()
results = demo.run_comprehensive_demo()

# 結果確認
print(f"デモステータス: {results['status']}")
print(f"実行時間: {results['duration']:.1f}秒")
print(f"生成URL: {results['urls']}")
print(f"生成ファイル: {results['files']}")
```

### コマンドライン実行

```bash
cd src/econ/output
python demo_integration.py
```

## 📊 出力例

### Google Sheets ダッシュボード
- **サマリーシート**: 全体統計、注目指標、更新情報
- **指標詳細シート**: 全指標の詳細データ
- **トレンド分析シート**: トレンド情報とパターン
- **相関分析シート**: 指標間の相関マトリクス
- **リスク評価シート**: リスク要因と対策

### 高度なダッシュボード
- **インタラクティブチャート**: ズーム、フィルタ、ホバー情報
- **リアルタイム統計**: 自動更新される統計情報
- **レスポンシブデザイン**: デスクトップ・モバイル対応

### 高度な可視化
- **トレンド分析**: トレンド強度分布、信頼度分析
- **相関マトリクス**: クラスタリング分析付き
- **ボラティリティサーフェス**: 3D可視化
- **レジーム検出**: 市場レジームの自動検出
- **予測精度**: 予測vs実際値の詳細分析
- **リスクメトリクス**: 多角的リスク評価

## ⚙️ 設定

### 環境変数

```bash
# Google API認証
GOOGLE_AUTH_METHOD=oauth2
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REFRESH_TOKEN=your_refresh_token

# 通知設定
ECON_SLACK_WEBHOOK_URL=your_webhook_url
ECON_SLACK_CHANNEL=#market-news

# 出力設定
ECON_OUTPUT_DIR=./build
ECON_DAILY_LIST_ENABLED=true
ECON_CALENDAR_ENABLED=true
```

### 設定ファイル

```python
from src.econ.config.settings import EconConfig

# 設定カスタマイズ
config = EconConfig()
config.output.output_base_dir = "./custom_output"
config.targets.target_countries = ["US", "EU", "JP"]
config.schedule.daily_generation_hour = 6
```

## 🔧 カスタマイズ

### カスタム可視化

```python
from src.econ.output import VisualizationEnhancer, VisualizationConfig

# カスタム設定
config = VisualizationConfig(
    width=1600,
    height=1000,
    color_palette=['#FF6B6B', '#4ECDC4', '#45B7D1'],
    output_format=['html', 'png', 'pdf']
)

enhancer = VisualizationEnhancer(config)
```

### カスタムダッシュボード

```python
from src.econ.output import AdvancedDashboard, DashboardConfig

# カスタムレイアウト
config = DashboardConfig(
    rows=4,
    cols=2,
    subplot_titles=[
        "カスタム分析1", "カスタム分析2",
        "カスタム分析3", "カスタム分析4",
        "カスタム分析5", "カスタム分析6",
        "カスタム分析7", "カスタム分析8"
    ]
)

dashboard = AdvancedDashboard(config)
```

## 📈 パフォーマンス

### 最適化設定

```python
# 並行処理設定
update_config = UpdateConfig(
    concurrent_updates=True,
    max_concurrent=10
)

# キャッシュ設定
econ_config = EconConfig()
econ_config.cache.enabled = True
econ_config.cache.calendar_cache_hours = 6
econ_config.cache.series_cache_hours = 24
```

### メモリ管理

- 大量データ処理時のチャンク処理
- 自動メモリクリーンアップ
- 効率的なデータ構造使用

## 🚨 エラーハンドリング

### 自動リトライ

```python
update_config = UpdateConfig(
    max_retries=3,
    retry_delay=30
)
```

### エラー通知

```python
# Slack通知
update_config = UpdateConfig(
    notify_on_error=True,
    notification_channels=["slack"]
)
```

## 📚 API リファレンス

### 主要クラス

- `SheetsDashboardManager`: Google Sheets連携管理
- `AdvancedDashboard`: 高度なダッシュボード生成
- `RealTimeUpdater`: リアルタイム更新システム
- `VisualizationEnhancer`: 高度な可視化生成
- `EconomicIndicatorsOutputDemo`: 統合デモ

### 主要設定クラス

- `DashboardConfig`: ダッシュボード設定
- `UpdateConfig`: 更新システム設定
- `VisualizationConfig`: 可視化設定

## 🔄 更新履歴

### v1.0.0 (2024-01-XX)
- Google Sheets API連携実装
- 高度なダッシュボード機能
- リアルタイム更新システム
- 高度な可視化機能
- 統合デモシステム

## 🤝 貢献

1. 機能追加・改善の提案
2. バグレポート
3. ドキュメント改善
4. テストケース追加

## 📄 ライセンス

このプロジェクトは既存の経済指標システムの一部として提供されています。

---

**注意**: 本システムは既存の経済指標システムと統合されており、独立して動作させる場合は適切な設定とデータソースが必要です。
