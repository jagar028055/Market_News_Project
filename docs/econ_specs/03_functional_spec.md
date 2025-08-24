# 機能仕様書（経済指標 新機能）

## 1. 機能一覧
- F1: 昨日発表の経済指標一覧の生成（ライト）
- F2: 発表カレンダー（ICS）の生成
- F3: 重要指標の深掘り図版/所感の生成（ディープ）
- F4: サプライズ算出（予想がある場合）
- F5: note/SNS連携用のアセット出力

## 2. F1 昨日発表一覧（ライト）
- 入力: `investpy` カレンダー（from=昨日, to=昨日）
- 処理: 必要列抽出→型正規化→国/重要度ソート→サプライズ計算（forecast有のみ）
- 出力: `build/reports/daily_indicators/YYYYMMDD.md`
- 受入基準:
  - 生成が成功し、表に country/indicator/importance/actual/forecast/previous/date/time が揃う。
  - forecast欠損時にサプライズ列が空欄になる。

## 3. F2 発表カレンダー（ICS）
- 入力: カレンダー（当日＋7日）
- 処理: Event名/開始時刻（UTC）/重要度をICSへ成形
- 出力: `build/calendars/economic.ics`
- 受入基準:
  - 標準的なカレンダーアプリで購読できる。
  - 重要度Highのイベントが正しく登録されている。

## 4. F3 ディープ（重要指標）
- 入力: 公式API（BLS/BEA/FRED/ECB/ONS/e-Stat 等）
- 処理: 正規化（freq/unit/SA）→ 派生指標（YoY/MoM）→ 図版テンプレへ描画 → 簡易所感生成（ルールベース）
- 出力: `build/indicators/YYYYMMDD/<series_id>.png` / `insights.json`
- 受入基準:
  - 図版にタイトル/単位/凡例/期間/データソースが表示される。
  - JSONに series_id/period/actual/previous/forecast(optional)/surprise(optional) を含む。

## 5. F4 サプライズ算出
- 入力: actual/forecast
- 処理: `surprise = actual - forecast`、`surprise_ratio = (actual - forecast)/abs(forecast)`、`z_score`（履歴分布ベース、forecast有のみ）
- 出力: テーブル列、insights.jsonに格納
- 受入基準: forecastが存在しない場合は算出しない。

## 6. F5 連携アセット
- 出力: 画像（PNG/SVG）、Markdownブロック（note貼付用）、SNS画像（任意）
- 受入基準: 画像パス/相対参照が機能し、レイアウト崩れがない。

## 7. CLI/スクリプトI/F（想定）
- `python -m econ daily-list --date YYYY-MM-DD`
- `python -m econ build-ics --days 7`
- `python -m econ deep-dive --series US.CPI.ALL.SA.INDEX --since 2015-01-01`

## 8. 設定
- `app_config.econ.countries = ["US","EU","UK","JP","CA","AU"]`
- `app_config.econ.importance_threshold = "High"`
- `app_config.econ.timezone_display = "Asia/Tokyo"`

## 9. ログ/監視
- info: 取得件数/所要時間、warn: 欠損/フォールバック、error: 失敗詳細
- メトリクス: 生成時間、成功率、サプライズ算出率

