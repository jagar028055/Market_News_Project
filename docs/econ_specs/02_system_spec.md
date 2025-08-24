# システム仕様書（経済指標 新機能）

## 1. 全体アーキテクチャ
- 二段構成:
  - ライト: `adapters/investpy_calendar.py` → `reports/daily_list_renderer.py` → `build/reports/daily_indicators/YYYYMMDD.md`
  - ディープ: `adapters/{fred,sdmx}.py` → `normalize/mapper.py` → `render/plots.py` → `build/indicators/YYYYMMDD/`
- カレンダー: `scheduler/jobs.py` が前日一覧生成、当日通知、ICS再生成を管理。

## 2. データソース/API
- ライト: `investpy`（Forecast/Previous/Actual/Importance付きのイベント取得）
- フォールバック: `FMP`/`Finnhub` のカレンダーAPI、機関別RSS/ICS。
- ディープ: BLS/BEA/FRED/ECB/ONS/e-Stat/Eurostat/OECD/IMF/WorldBank（無料API/SDMX）。
- 予測値: 外部API由来のみ使用。欠損時はサプライズ計算スキップ。

## 3. 出力物/配置
- ライト: `build/reports/daily_indicators/YYYYMMDD.md`
- カレンダー: `build/calendars/economic.ics`
- ディープ: `build/indicators/YYYYMMDD/<series_id>.png` と `insights.json`

## 4. データモデル（要約）
- calendar_event: id, title, country, importance, scheduled_time_utc, actual, forecast, previous, source
- series: series_id, title, provider, freq, seasonal_adj, unit
- release: series_id, period, release_time_utc, actual, forecast, previous, revised_from, source_url

## 5. グラフ仕様（提案）
- CPI系: YoY折れ線（景気後退網掛け）、MoM棒グラフ（±0強調）、政策金利との2軸。
- 雇用系: 非農業部門雇用者数の前月差（棒）＋失業率（線、右軸）。
- 小売売上: MoM棒＋3ヶ月移動平均線、前年同月比の参考線。
- GDP: 実質成長率（前期比年率）の棒、寄与度スタック（任意）。
- PMI: 50ライン基準、サブコンポーネント（新規受注/雇用）の帯。
- サプライズ: 予想vs実績の散布（過去n回）、zスコアのヒートマップ（国×指標）。

## 6. 経済スケジュール表（提案）
- 列: Date/Time(ローカル)/Country/Indicator/Imp/Forecast/Previous/Actual/Surprise/Source
- 表示:
  - 重要度Highはハイライト、国旗アイコン（テキスト環境では国コード）。
  - 予想欠損はSurprise非表示。時刻未定は“—”。
  - 1日1ページのMD/HTML、週次リストも生成（オプション）。
- 生成: ライトでMD生成→note/SNS素材化、ICSは購読用。

## 7. スケジューラ/バッチ
- 前日一覧: 毎朝 06:00 UTC に生成。
- 当日通知: 発表60分前にリマインド、実績確定で確報（重要度Highのみ）。
- ICS: 日次再生成＋T-2〜T+2 の差分再取得。

## 8. エラーハンドリング/フォールバック
- 取得失敗時: 退避ソース（FMP/Finnhub/RSS）を順次試行。重複は優先順位でマージ。
- 欠損: 予想が無い場合はSurprise計算をスキップ（UIは空欄）。
- レート制御: バックオフ/再試行、ローカルキャッシュ（Parquet/SQLite）。

## 9. セキュリティ/設定
- APIキーは `.env`/Secrets。リポ直書き禁止。
- 設定: `app_config` に出力先/タイムゾーン/国別対象/重要度しきい値。

## 10. 品質/テスト
- スナップショット: 図版の画像差分テスト。
- データ: スキーマ検証（必須列/型）、欠損/外れ値のガード。
- パフォーマンス: 前日一覧生成1分以内、ディープ1指標5秒以内（キャッシュ）。

