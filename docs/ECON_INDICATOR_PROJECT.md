# 経済指標分析プロジェクト（独立ドキュメント）

本ドキュメントは Market News の拡張計画における「経済指標分析スペシャリスト」の独立仕様です。データ取得戦略、スケジュール設計、スキーマ、実装方針、可視化/配信、そして主要プロバイダのコスト比較をまとめます。

---

## 1. 目的と範囲
- 目的: FRED/OECD/IMF/e-Stat 等の公的データと商用APIを組み合わせ、発表カレンダーに同期した可視化・要約・通知を自動化。
- 出力: `build/indicators/YYYYMMDD/<series_id>.png`（図版）と `insights.json`（要約/サプライズ/メタ）。
- 連携: Market_News の note/SNS 出力へ画像/短文洞察を差し込み、配信品質とタイムリー性を強化。

---

## 2. データ取得戦略（investpy以外の手段）
- 主軸: Trading Economics（カレンダー/指標の網羅性、安定API）。
- 補完: FRED（米国の系列粒度/改定履歴）、OECD/IMF/World Bank/Eurostat/e-Stat/BOJ（SDMX、公的データ）。
- 代替（カレンダー系）: Finnhub、Financial Modeling Prep（FMP）をフォールバック候補に。
- investpyの位置づけ: 学習/PoC用途には便利だが、非公式スクレイプ系のため本番は回避推奨（ブロック/仕様変更のリスク）。

### 2.1 追加プロバイダ（公的/無料APIの代表例）
- BLS（米労働統計局）: CPI/雇用等。無料API。https://www.bls.gov/developers/
- BEA（米経済分析局）: GDP/PCE等。無料API。https://www.bea.gov/data/api
- U.S. Census: 小売売上等。無料API。https://www.census.gov/data/developers/data-sets.html
- ECB SDW: 欧州中銀統計データウェアハウス（SDMX）。無料。https://sdw.ecb.europa.eu/
- ONS（英国）: 統計API。無料。https://developer.ons.gov.uk/
- Statistics Canada（StatCan）: API/SDMX。無料。https://www150.statcan.gc.ca/n1/en/type/data
- UN Data（UNSD SDMX）: 国際統計。無料。https://unstats.un.org/
- BIS（国際決済銀行）: 金融統計（SDMX）。無料。https://stats.bis.org/

### 2.2 追加対象 国・機関リスト（優先度案）
- 米国: `FRED` / `BLS` / `BEA` / `U.S. Census`（無料API、発表カレンダーは各機関サイト/RSSで補完）
- 欧州: `ECB SDW` / `Eurostat` / 各国統計局（例: `Destatis` ドイツ、`INSEE` フランス）
- 英国: `ONS`（API）/ `Bank of England`（データポータル）
- 日本: `e-Stat` / `BOJ Time-Series` / `内閣府` 統計ページ（GDP等のCSV配布）
- カナダ: `Statistics Canada`（API/SDMX）
- 豪州: `ABS`（Australian Bureau of Statistics API/SDMX）、`RBA`（統計CSV）
- 国際機関: `OECD` / `IMF` / `World Bank` / `BIS`（SDMX/REST）

---

## 3. 経済カレンダー/スケジュール設計
- 取得方針: Trading Economics（TE）のカレンダーAPIで「当日＋7日」を取得→DB登録＋ICS生成。
- 差分再取得: 改定/遅延対策として T-2〜T+2 の再取得を5〜15分間隔で実行（APScheduler）。
- タイムゾーン: UTCで保存、表示・通知時に `Asia/Tokyo` 等へ変換（夏時間を吸収）。
- ICS出力: `build/calendars/economic.ics` を日次再生成（Google/Apple/Outlook購読用）。
- 通知: 重要度 High（または自前スコア上位）をSlack/メールに60分前通知。実績確定で確報通知。

### 3.1 無料優先の構成（カレンダー）
- 第1候補: `investpy` のカレンダーで長期ヒストリーを取得（過去〜将来の予定、Forecast/Previous付き）。取得結果はローカルDBにキャッシュし、名称→公式系列IDのマッピングを保持。
- 第2候補: FMPの `economic_calendar`（無料枠）でフォールバック取得（estimate/previousを併用）。
- 併用候補: 一部機関の公式リリーススケジュール（BLS/BEA/ECB/ONS 等）はRSS/ICS/CSVを提供している場合があるため、該当機関のみ直取り込みして精度を高める。
- 注意: investpyはスクレイプ系のため障害に備え、フォールバック（FMP/Finnhub/機関RSS）を常に有効化。重要イベントは重複ソースで照合し、差分を解決するルールを用意。

### 3.2 市場予想（コンセンサス）の扱い
- 入手優先順位（無料中心）:
  1) investpy（カレンダー経由）: Forecast/Previousをそのまま利用。
  2) FMP/Finnhub のカレンダーAPI: `estimate`/`forecast` が付随する場合は採用。
- 有償の選択肢（参考）: Trading Economics の Forecast、Refinitiv/Bloomberg/Econoday/Consensus Economics など。本プロジェクトでは原則非採用（無料優先）。
 - 方針: 予測値は外部API由来のみ使用。自前の機械予測は行わない（欠損時はサプライズ算出をスキップ）。
 - サプライズ算出: `surprise = actual - forecast`、`surprise_ratio = (actual - forecast) / abs(forecast)`、分布に基づく `z_score`（forecastが存在する場合のみ計算）。

### 3.3 取得期間（長期）と品質方針
- investpyは過去カレンダーデータの取得が可能なため、長期ヒストリーの構築に適する。取得後はDBに保存し、イベント名・国・カテゴリの正規化を実施。
- 長期ヒストリーが必要な場合、機関の過去リリースCSV/HTMLをスクレイプせず、可能な限り公式が提供するファイル/APIを優先（BLS/BEA/ONS/ABSなど）。

サンプル（TEカレンダー→ICS）:
```python
import tradingeconomics as te
from ics import Calendar, Event
from datetime import datetime, timedelta

te.login('YOUR_API_KEY')
events = te.getCalendar(
    initDate=datetime.utcnow().date(),
    endDate=(datetime.utcnow()+timedelta(days=7)).date()
)

cal = Calendar()
for ev in events:
    # ev例: {'Country','Category','Event','Date','Reference','Importance','Actual','Forecast','Previous',...}
    dt = datetime.fromisoformat(ev['Date'].replace('Z','+00:00'))
    e = Event()
    e.name = f"{ev['Event']} ({ev['Country']})"
    e.begin = dt
    e.description = f"Imp:{ev.get('Importance')} F:{ev.get('Forecast')} P:{ev.get('Previous')}"
    cal.events.add(e)

with open('build/calendars/economic.ics', 'w') as f:
    f.writelines(cal)
```

### 3.4 二段構成（ライト/ディープ）の運用フロー
- ライト出力（速報・簡易）:
  - 生成物: 「昨日発表された経済指標一覧」（Markdown/HTML）。国、指標名、重要度、予想/実績/前回、サプライズ（予想がある場合）。
  - 取得元: `investpy` を優先（Forecast/Previous/Actualが揃いやすい）。
  - 保存先: `build/reports/daily_indicators/YYYYMMDD.md`。
  - 用途: SNS/noteの素材、日次の俯瞰、人的確認用。
- ディープ出力（精査・分析）:
  - 対象: ライト出力で重要・サプライズ大の指標（例: CPI、雇用、PMI、GDP）。
  - 取得元: 公式API（BLS/BEA/FRED/ECB/ONS 等）から元系列を取得し、YoY/MoM/長期推移/2軸などの図版を作成。
  - 出力: `build/indicators/YYYYMMDD/<series_id>.png` と `insights.json` を作成し、note/SNSへ差し込み。

サンプル（investpyで昨日の一覧→Markdown）:
```python
import investpy
import pandas as pd
from datetime import datetime, timedelta

yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%d/%m/%Y')
df = investpy.news.economic_calendar(from_date=yesterday, to_date=yesterday)

# 主要列の整形
cols = ['country', 'event', 'importance', 'actual', 'forecast', 'previous', 'date', 'time']
df = df[cols].rename(columns={'event':'indicator'})

def to_md_table(pdf: pd.DataFrame) -> str:
    header = '| Country | Indicator | Imp | Actual | Forecast | Previous | Date | Time |\n|---|---|---|---|---|---|---|---|'
    rows = ['| ' + ' | '.join(str(pdf.iloc[i,j]) if pd.notna(pdf.iloc[i,j]) else '' for j in range(len(pdf.columns))) + ' |' for i in range(len(pdf))]
    return '\n'.join([header] + rows)

md = f"# 経済指標一覧（{yesterday}）\n\n" + to_md_table(df)
out = f"build/reports/daily_indicators/{datetime.utcnow().strftime('%Y%m%d')}.md"
import os; os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'w') as f:
    f.write(md)
```

---

## 4. 指標データ取得と正規化
- 正規化スキーマ:
  - series: `series_id`（機関ID＋地域＋調整法の正規化）、`title`、`provider`、`freq`（M/Q/W/D）、`seasonal_adj`、`unit`。
  - release: `series_id`、`period`（例: 2024-07）、`release_time_utc`、`actual`、`forecast`、`previous`、`revised_from`、`source_url`、`vintage`。
  - calendar: `event_id`、`title`、`country`、`importance`、`scheduled_time_utc`、`related_series_id`、`status`（scheduled/reported/revised）。
- 重要度スコア: 提供値（Importance）と自前の市場影響度スコアを併用。重複/夜間イベント補正。
- 欠損/改定: `release_revision` を別レコードとして保持。実測値の後追い訂正に対応。

サンプル（FRED系列→Parquet格納）:
```python
from fredapi import Fred
import pandas as pd

fred = Fred(api_key='YOUR_FRED_KEY')
raw = fred.get_series('CPIAUCSL')  # 米CPI総合（季節調整済、指数）
df = raw.rename('value').to_frame()
df.index.name = 'date'
df['series_id'] = 'US.CPI.ALL.SA.INDEX'
df['provider'] = 'FRED'
df.to_parquet('data/series/US.CPI.ALL.SA.INDEX.parquet')
```

---

## 5. 実装アーキテクチャ
- `adapters/`:
  - `trading_economics.py`: 指標/カレンダー取得。レート制御・再試行・差分取得。
  - `fred.py`: シリーズ取得（`fredapi`）。IDマッピングで `series_id` を正規化。
  - `sdmx.py`: OECD/IMF/Eurostat/e-Stat/BOJ 向け共通実装（`pandasdmx`）。
  - `investpy_fallback.py`: 非公式。障害時限定の補完（任意）。
- `normalize/mapper.py`: 単位換算、季節調整フラグ統一、頻度の標準化（M/Q/W/D）。
- `storage/`: Parquet（系列）＋SQLite/Postgres（カレンダー/リリース）。
- `scheduler/`: APScheduler でジョブ管理（カレンダー差分、当日発表、改定チェック）。
- `render/plots.py`: YoY/MoM、長期、2軸、改定注記の図版テンプレ。
- `reports/insights.py`: サプライズ度、zスコア、過去分布、簡易所感の自動生成。

---

## 6. 可視化・配信（見せ方）
- ダッシュボード: 今週の主な発表、サプライズヒートマップ、国/テーマ別フィルタ、改定履歴トラッカー。
- 記事連携: 発表直後に関連ニュース3本を自動添付し、1枚画像＋短文まとめを生成。
- グラフィック: 1) 長期推移＋景気後退網掛け、2) 予想/実績の散布図（サプライズ分布）、3) 政策金利とインフレの2軸。
- 通知: 前日夕方のまとめ、60分前リマインド、確報通知。ICS購読リンクを併記。
- note用: 月次テーマ別まとめ（インフレ・雇用・製造業）と「指標の見方」定型テンプレ。

---

## 7. コスト比較（表／一次情報リンク、最終確認日: 2025-08-23）
注: 価格やレート制限は変更されうるため、必ず公式を再確認してください。

| Provider | Region | Data/Scope | Pricing | Rate limit | Calendar/Forecast | Notes | Link |
|---|---|---|---|---|---|---|---|
| Trading Economics | Global | Indicators + Calendar | 要問い合わせ | 契約による | 両方あり（Forecastは独自） | 網羅性高、無料構築の主旨とは非整合 | https://tradingeconomics.com/api/pricing.aspx |
| FRED | US | Macro time series | 無料 | 制限あり（数値非公開） | Calendar: なし | 米国系列に強い | https://fred.stlouisfed.org/docs/api/ |
| OECD | OECD | SDMX-JSON datasets | 無料 | 慣習上の制限 | Calendar: なし | 正規化要 | https://data.oecd.org/api/ |
| IMF | Global | SDMX datasets | 無料 | 慣習上の制限 | Calendar: なし | 国際マクロ | https://data.imf.org/en/Resource-Pages/IMF-API |
| World Bank | Global | Indicators API | 無料 | 慣習上の制限 | Calendar: なし | オープンデータ | https://data.worldbank.org/ |
| Eurostat | EU | SDMX datasets | 無料 | 無料と明記 | Calendar: なし | EU統計の中核 | https://ec.europa.eu/eurostat/ |
| e-Stat | JP | Government statistics | 無料（登録） | 慣習上の制限 | Calendar: 限定 | 日本統計 | https://www.e-stat.go.jp/api/ |
| BLS | US | CPI/Employment | 無料（登録） | 慣習上の制限 | Release calendar: あり | 一次ソース | https://www.bls.gov/developers/ |
| BEA | US | GDP/PCE | 無料（登録） | 慣習上の制限 | Release calendar: あり | 一次ソース | https://www.bea.gov/data/api |
| U.S. Census | US | Retail etc. | 無料（登録） | 慣習上の制限 | Release calendar: あり | 月次統計など | https://www.census.gov/data/developers/ |
| ECB SDW | EU | Monetary/Prices/Credit | 無料 | 慣習上の制限 | Calendar: なし | SDMX | https://sdw.ecb.europa.eu/ |
| ONS | UK | UK statistics | 無料 | 慣習上の制限 | Release calendar: あり | APIあり | https://developer.ons.gov.uk/ |
| Statistics Canada | CA | Canada statistics | 無料 | 慣習上の制限 | Release calendar: あり | SDMX/JSON | https://www150.statcan.gc.ca/ |
| ABS | AU | Australia statistics | 無料 | 慣習上の制限 | Release calendar: あり | SDMX/CSV | https://www.abs.gov.au/ |
| KOSIS | KR | Korea statistics | 無料（登録） | 慣習上の制限 | Release calendar: あり | API | https://kosis.kr/ |
| SingStat | SG | Singapore statistics | 無料 | 慣習上の制限 | Release calendar: あり | API | https://www.singstat.gov.sg/ |
| Finnhub | Global | Economic calendar etc. | 無料枠＋有料 | プラン依存 | Calendar: あり、Forecast: 一部 | フォールバック候補 | https://finnhub.io/pricing |
| FMP | Global | Economic calendar etc. | 無料枠＋有料 | プラン依存 | Calendar/estimate あり | 低コスト代替 | https://site.financialmodelingprep.com/developer/docs/pricing |
| investpy | Global | Investing.com由来 | 無料（lib） | なし | Calendar/Forecast あり | 非公式（スクレイプ系） | https://github.com/alvarobartt/investpy |

【TCO観点（概算）】
- 無料構成（推奨）: 公的API＋`investpy`/FMP/Finnhubでカレンダー、API料金$0。インフラ$0〜$10/月相当。
- 低コスト構成: FMP/Finnhubの有料プラン併用で$30〜$100/月＋インフラ$10〜$30/月。
- 企業向け: TE契約で網羅一元化（価格は要見積）。

---

## 8. MVPスケジュール（4週間）
- Week 1: TEカレンダー→ICS/DB、FRED 4系列（CPI, Core CPI, Unemployment, Fed Funds）の取得・正規化・基本チャート。
- Week 2: サプライズ算出と自動要約、Slack通知、ダッシュボード簡易版（Streamlit）。
- Week 3: OECD/IMF/World Bank/e-Stat の優先系列を追加、改定検知、画像テンプレ整備。
- Week 4: 運用硬化（レート制御/リトライ/監視）、note月次レポの自動ドラフト。

---

## 9. セキュリティ/運用
- Secrets: APIキー（TE/FRED）は `.env`/Secrets 管理。リポへ直書き禁止。
- レート制御: バックオフ/再試行、差分取得、ローカルキャッシュ（Parquet/SQLite）。
- ロギング: 取得/描画/通知の各段階で構造化ログ、失敗時のリトライ/アラート。
- 監視: 主要ジョブのSLA（カレンダー更新、発表当日取得、改定検知）を可視化。

---

## 10. 次アクション
- APIキー: `FRED` ほか公的API（BLS/BEA/Census/ECB/ONS 等）。TEは任意。
- スケルトン作成:
  - `adapters/investpy_calendar.py`（ライト用）
  - `adapters/fmp_calendar.py`（フォールバック）
  - `adapters/fred.py` / `adapters/sdmx.py`（ディープ用）
  - `scheduler/jobs.py`（昨日一覧生成、当日通知）
  - `render/plots.py`（ディープ用チャート）
- ストレージ: Parquet（系列）＋SQLite/Postgres（カレンダー/リリース）。
- 優先実装順: ライト（日次一覧）→ ディープ（公式データの図版）→ 通知/連携。

---

（補足）本ドキュメントは `docs/CONTENT_EXPANSION_ROADMAP.md` のセクション5を詳細化した独立版です。

---

## 付録A: 無料優先アーキテクチャの指針（まとめ）
- カレンダー: `investpy` を主（長期ヒストリー/Forecast含む）。フォールバックに FMP/Finnhub、機関別RSS/ICSを併用。
- 実測データ: 公式API（BLS/BEA/FRED/Census/ECB/ONS/StatCan/OECD/IMF/World Bank/Eurostat/e-Stat）。
- 予想データ: 外部API由来（investpy/FMP/Finnhub）のみ使用。予想が無い場合はサプライズ算出をスキップ。
- サプライズ評価: forecastがあるもののみ `zスコア` を算出し配信。

---

## 付録B: 予測モデルの具体化（無料運用向け）
- 目的: 無料でコンセンサスが得られない指標に対し、暫定予測（機械予測）を生成し、サプライズ比較を可能にする。
- 対象変数: 指標ごとに `target` を定義（例: CPIのYoY、雇用者数の前月差、失業率の水準）。
- 変換/前処理: 季節調整済み系列の優先、対数差分（近似成長率）、祝日効果なし前提。欠損は前方補間禁止、直近観測までで学習。
- ベースライン: Seasonal Naive（前年同月）、移動平均（3/6/12）、前月値。これを常時併記して過学習を抑止。
- 統計モデル: `SARIMA`（探索は小さく制限）、`ETS`（指数平滑）、`STL + ETS`。短中期で堅牢。
- 回帰/機械学習: `Ridge/Lasso/ElasticNet` にラグ特徴（t-1..t-12）＋外生変数（PMI/エネルギー価格/為替/失業保険申請/PPI等）。木系は `LightGBM`（少特徴で軽量）。
- 特徴量例:
  - CPI: エネルギー価格（Brent/WTI）、食品指数、為替（USDJPY/EURUSD）、PPI、輸入物価、PMI価格指数。
  - 雇用統計: 失業保険新規申請、求人（JOLTS）、PMI雇用指数。
  - 小売売上: ガソリン価格、消費者信頼感。
- 学習設計: ローリングウィンドウ（3〜10年）、時系列CV（expanding）でハイパラ選択。`MAE/MAPE/RMSE/MASE` を評価、単純予測より悪化するモデルは不採用。
- 予測区間: 残差ブートストラップで予測区間（lower/upper）を算出し、図版に帯表示。
- 運用ルール: 外部コンセンサス取得時は機械予測を置換。公開物には「機械予測」バッジとモデル種別を明記。
- 実装I/F: `models/simple_forecast.py` に `forecast(series, exog=None, horizon=1, method="auto") -> {point, lower, upper, model, metrics}` を実装。
- 監視: 週次バックテストで過去3/6/12か月の誤差を可視化。劣化時はベースラインへフォールバック。
