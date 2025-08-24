# 機能仕様書（ユーザー視点）

## ユースケース
- ウォッチリストの複数銘柄を日次/時間毎に巡回し、PNG/insightsを生成
- ルールYAMLに基づくシグナル抽出とスコアリング
- 簡易バックテスト/最適化の実行とレポート生成
- note/SNS用の画像を自動選定してエクスポート
- 個人用途でTradingViewリストのスクリーンショット保存（任意）

## CLIコマンド（例）
- `chart_analyst fetch --symbol "USDJPY=X" --interval 1h --days 180`
- `chart_analyst analyze --symbol "^GSPC" --tf 1d,4h,1h --rules rules/standard.yaml`
- `chart_analyst plot --symbol "BTCUSDT" --tf 4h --style dark`
- `chart_analyst run --watchlist watchlists/core.yaml --out build/charts/`
- `chart_analyst backtest --symbol "^N225" --tf 1d --rules rules/standard.yaml --start 2010-01-01`
- `chart_analyst optimize --symbol "USDJPY=X" --tf 1h --rule trend_follow_rsi --trials 200`
- `chart_analyst tvshot --watchlist tv/watchlist.yaml --out build/tvshots/`（任意）

## 入出力
- 入力:
  - シンボル/タイムフレーム、期間/開始終了日
  - ルールYAML、最適化パラメータ範囲
- 出力:
  - PNG/HTML、`insights.json`、バックテスト結果（CSV/JSON/PNG）

## 成果物の構造
- `build/charts/YYYYMMDD/<symbol>_<tf>.png`
- `build/charts/YYYYMMDD/<symbol>/<tf>_report.html`（任意）
- `build/charts/YYYYMMDD/<symbol>/insights.json`
- `build/backtests/<symbol>_<tf>/report.json` / `equity_curve.png`

## エラーメッセージ/ログ（要旨）
- データ取得失敗: リトライ/フォールバックの実施と記録
- 指標計算エラー: 欠損/窓長不足の警告
- バックテスト設定不備: 取引時間/コスト未設定の警告
