# 要件定義書（経済指標 新機能）

## 1. 背景/目的
- 無料優先で「速報性のある日次一覧（ライト）」と「重要指標の深掘り（ディープ）」を両立。
- ライトは `investpy` のカレンダーで予想/実績/前回を含む一覧を即時生成。
- ディープは公式API（BLS/BEA/FRED/ECB/ONS/e-Stat 等）の元系列で可視化と短評を作成。

## 2. スコープ
- 対象指標: CPI/コアCPI、雇用統計、失業率、小売売上、GDP、PMI 等（国はUS/EU/UK/JP/CA/AU中心）。
- 対象機能:
  - 昨日発表の経済指標一覧（Markdown/HTML）生成
  - 発表カレンダー（ICS）生成・配布
  - 重要指標の元データ取得・正規化・図版（PNG/SVG）出力
  - サプライズ算出（予想がある場合のみ）と簡易所感
  - note/SNS出力との連携

## 3. 利用者/ユースケース
- 編集者/アナリスト: 日次の俯瞰→注目指標の深掘り→配信素材作成。
- 読者: 一覧で素早く把握→重要指標の見やすいグラフ・所感を閲覧。

## 4. 機能要件（高レベル）
- ライト（日次）
  - investpyで前日分を取得し、国/重要度ごとに整形した一覧を `build/reports/daily_indicators/YYYYMMDD.md` に出力。
  - 予想/実績/前回/重要度/サプライズ（予想ありのみ）を表で表示。
- カレンダー
  - 発表予定を取得し、`build/calendars/economic.ics` として公開用に生成（UTC保持/ローカル表示）。
- ディープ（重要指標）
  - 公式APIから元系列を取得、YoY/MoM/長期推移/2軸チャートを出力。
  - `build/indicators/YYYYMMDD/<series_id>.png` と `insights.json` を生成。

## 5. 非機能要件
- コスト: 無料優先（公的API＋investpy/FMP/Finnhub）。
- 性能: 前日一覧生成は1分以内。深掘り1指標あたり5秒以内（キャッシュ有）。
- 可用性: フォールバック（FMP/Finnhub/機関RSS）を用意、重複照合で品質担保。
- ロギング/監視: 取得/描画/通知を構造化ログ化。失敗時は再試行と通知。

## 6. 制約/前提
- 予測値は外部API由来のみ。自前の機械予測は行わない。
- investpyはスクレイプ系のため、障害時のフォールバックを実装。
- タイムゾーンは内部UTC、表示時に地域TZへ変換。

## 7. 成功指標（KPI）
- 日次一覧の生成成功率>99%、重要指標の深掘り出力の生成時間中央値<5秒。
- 読了率/クリック率の向上、Slack通知のエンゲージメント改善。

## 8. アウトオブスコープ
- 有償コンセンサスデータの利用、完全自動投稿（初期）。

## 9. 実装タスク分解（WBS）

### 9.1 準備/基盤
- ディレクトリ作成: `adapters/`, `reports/`, `scheduler/`, `normalize/`, `render/`, `storage/`, `config/`。
- 設定拡張: `app_config.econ`（対象国、TZ、重要度しきい値、出力先、feature flags）。
- ローカルキャッシュ: Parquet/SQLite の配置規約（`data/series/`, `data/calendar.db`）。

### 9.2 ライト（昨日一覧）
- 実装: `adapters/investpy_calendar.py`（from/to指定で取得、必要列抽出、型正規化）。
- レンダ: `reports/daily_list_renderer.py`（Markdown表、CSVオプション）。
- CLI: `python -m econ daily-list --date YYYY-MM-DD`。
- 受入: `build/reports/daily_indicators/YYYYMMDD.md` が生成、forecast欠損時はsurprise非表示。
- テスト: 正規化ユニットテスト、サンプルデータでのゴールデンMD比較。

### 9.3 カレンダー（ICS）
- 実装: `reports/ics_builder.py`（UID/UTC/VALARM/説明文/カテゴリ実装）。
- 取得: `adapters/investpy_calendar.py`（当日＋7日）、`adapters/fmp_calendar.py`（フォールバック）。
- マージ: 重複イベントの優先順位ルール（investpy > FMP > RSS）。
- 出力: `build/calendars/economic.ics`。
- CLI: `python -m econ build-ics --days 7`。
- テスト: ICS基本検証（必須プロパティ、日付範囲、件数）。

### 9.4 ディープ（重要指標）
- マッピング: `config/indicator_mapping.json`（イベント名→公式 `series_id`/provider の対応表）。
- 取得: `adapters/fred.py`（`get_series(id)`）、`adapters/sdmx.py`（OECD/Eurostat/ONS/e-Stat 等）。
- 正規化: `normalize/mapper.py`（freq/unit/SA統一、YoY/MoM派生）。
- 描画: `render/plots.py`（テンプレ: YoY/MoM/長期/2軸、JPフォント）。
- 所感: `reports/insights.py`（ルールベースの短評、サプライズがある場合のみ触れる）。
- CLI: `python -m econ deep-dive --series <id> --since YYYY-MM-DD`。
- 出力: `build/indicators/YYYYMMDD/<series_id>.png` ＋ `insights.json`。
- テスト: スナップショット（画像差分）、計算テスト（YoY/MoM）。

### 9.5 通知/連携
- 通知: Slack/メール（重要度High、60分前/確報）。`notifiers/` を作成し設定でON/OFF。
- 連携: note/SNS用のMarkdownブロック生成（画像相対パスの検証）。

### 9.6 スケジューラ/運用
- 実装: `scheduler/jobs.py`（前日一覧、当日通知、ICS再生成、差分再取得 T-2〜T+2）。
- 設定: CRON/APS（毎朝06:00 UTC）。
- 監視: 生成成否、所要時間、件数をログ/メトリクスに記録。

### 9.7 ロギング/リトライ/レート制御
- 共通: バックオフ付再試行、構造化ログ、例外ハンドリング指針。
- レート制御: 取得間隔の最小化、連続呼び出し防止（sleep/トークンバケット）。

### 9.8 品質保証/性能
- パフォーマンス目標: ライト<1分、ディープ1指標<5秒（キャッシュ有）。
- 画像品質: 日本語フォント、凡例/単位/ソース表示の有無検査。
- データ品質: 必須列/型のスキーマ検証、NaN/外れ値のガード。

### 9.9 ドキュメント/運用手順
- ドキュメント更新: `docs/econ_specs/`、運用Runbook（障害時フォールバック手順）。
- 環境手順: `.env` テンプレ、APIキー取得手順（FRED/BLS/BEA 等）。

### 9.10 マイルストーン（MVP）
- M1（ライト）: 昨日一覧の生成＋公開（MD/CSV）。
- M2（ICS）: 経済カレンダー配布（ICS生成/購読確認）。
- M3（ディープ1st）: US CPI/コアCPI の図版/所感。
- M4（ディープ拡張）: 雇用/失業/小売/GDP/PMI 追加。
- M5（通知/連携）: Slack通知、note/SNS貼付テンプレ。

### 9.11 Doneの定義（DOD）
- 仕様合致の自動生成物（MD/ICS/PNG/JSON）が再現可能に生成される。
- 必須テスト（ユニット/スナップショット）がCIで通過。
- ログ/設定/Runbookが整備され、鍵はSecrets管理。
- 予想値のない指標に対してサプライズが表示されない。
