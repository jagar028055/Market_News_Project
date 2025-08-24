# 要件定義書（チャートスペシャリスト）

最終更新: 2025-08-24 初版

## 目的
- API由来のOHLCVデータとテクニカル指標から、PNG/HTMLチャートと洞察（insights.json）を自動生成し、note/SNS/日次レポートへ差し込む。

## スコープ
- データ取得（無料優先: yfinance、取引所API/Alpha Vantage補完）
- 指標計算（pandas/pandas_ta）
- マルチTF分析（1D/4H/1H: 4Hは1Hリサンプリング）
- PNG/HTML出力と `insights.json` 生成
- バックテスト/パラメータ最適化（初期は backtesting.py + Optuna）
- ルール定義（YAML/DSL）
- 個人用途のTradingViewスクショ（将来オプション、分析入力には非使用）

## 非スコープ（初期）
- 自動売買執行、取引所発注
- 有料データの契約前提の連携（将来検討: Oanda/IGなど）

## 成果物
- 画像: `build/charts/YYYYMMDD/<symbol>_<tf>.png`
- 対話: `build/charts/YYYYMMDD/<symbol>_<tf>.html`（任意）
- 洞察: `build/charts/YYYYMMDD/<symbol>/insights.json`
- 日次レポート添付用のチャート選定とコピー先

## データ要件
- 日足: 10年以上の履歴（銘柄依存）
- 1H: 1〜2年（Yahoo想定）、不足時はBinance等で補完（暗号資産）
- 4H: 1HからOHLCV再構築

## 品質/運用要件
- 欠損/非稼働日の扱いを統一
- レート制限対策とキャッシュ（Parquet）
- 日本語フォント指定、色覚多様性配慮
- 再現性（バージョン/設定/種）

## セキュリティ/法務
- データ提供元ToS順守（数値再配布回避、画像公開中心）
- TradingViewスクショは個人用途・ローカル保存、再配布不可

## 成功基準（MVP）
- 5シンボル×3TFのPNG/insightsを日次生成
- note記事に画像を1〜2枚差し込める体裁
- 簡易バックテストが回り、基本メトリクス（CAGR/MaxDD/勝率）を出力
