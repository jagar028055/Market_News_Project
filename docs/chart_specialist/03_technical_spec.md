# 技術仕様書（アーキテクチャ/データ/バックテスト/AI）

## アーキテクチャ
- ライブラリ: `chart_analyst`（別リポ想定）
- 構成: `data/`（取得/キャッシュ）`indicators/` `rules/` `plot/` `insights/` `backtesting/` `cli.py`
- 出力: `build/charts/YYYYMMDD/` `build/backtests/`

## データ取得
- 優先: `yfinance`（株/指数/為替）。不足時に `pandas_datareader`(Stooq)・`Alpha Vantage`（無料枠）
- 暗号資産: 取引所API（例: Binance）。
- 1H→4H: `resample('4H')` でOHLCV再構築。
- キャッシュ: Parquet（`data/ohlcv/<symbol>/<tf>.parquet`）。差分更新。

## 指標/ルール
- 計算: `pandas_ta` を優先（`ta-lib`は任意）。
- 代表指標: SMA/EMA/RSI/MACD/BB/ATR/OBV/MFI。
- ルール: YAML/DSLで宣言 → セーフな式評価器で判定。多TF合流可。

## 可視化
- `mplfinance`（PNG）、`plotly`（HTML）。
- テーマ統一、日本語フォント、注釈API。

## バックテスト
- エンジン: `backtesting.py`（初期）→`vectorbt`（将来オプション）。
- 期間目安（データ源依存）:
  - 1D: 10〜70年（`^GSPC`など長期）
  - 1H: 1〜2年（Yahoo）。4Hは同等。
  - 1m: Yahoo約7日。Binanceは上場以降。
- 設定: `fee_bps`/`slippage_bps`/`session_calendar`、ウォークフォワード/時系列CV。
- 出力: `build/backtests/<symbol>_<tf>/report.json`, `equity_curve.png`。

## AI/ML最適化
- LLMでルール提案→自動バックテスト→改善プロンプトの反復。
- パラメータ最適化: `Optuna` ベイズ最適化（多目的最適化）。
- 時系列学習（任意）: LightGBM/XGBoostで確率推定。リーク防止・確定足のみ評価。

## TradingViewスクショ（任意）
- `playwright`で取得。個人用途・ローカル保存のみ。認証情報は安全管理。

## エラーハンドリング/品質
- 欠損/非稼働日、レート制限、フォールバック、画像品質基準、再現性管理。

## セキュリティ/法務
- 提供元ToS順守。数値再配布回避。画像公開中心。
