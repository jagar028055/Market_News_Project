# Market News 拡張ロードマップ（ドラフト）

本ドキュメントは、現行のニュース収集・要約・公開基盤を中核に、配信チャネル拡張（SNS画像、note記事）と、別プロジェクトとしての専門アナリティクス（チャート分析／経済指標分析）を体系化するための作業計画です。ここにメモ・ToDo・決定事項を集約し、短いサイクルで磨き込みます。

---

## 0. 現状スナップショット（把握）
- 収集: `scrapers`（Reuters/Bloomberg）で記事取得、時間範囲は動的制御。
- 要約: Geminiベースの個別要約＋統合要約（Pro統合要約、コスト監視あり）。
- 保管: `src/database`（記事・AI分析・統合要約・セッション管理）。
- 出力: 
  - Web: `src/html` 経由で `index.html` 生成
  - Docs: Google Drive/Docs（全文上書き＋日次要約）と Sheets（記事・API使用量ログ）
- 運用: ロギング/監視、クリーンアップ、パフォーマンス計測、テスト基盤。

---

## 1. 全体アーキテクチャ（拡張設計）
- コンテンツ・オーケストレーター: 既存の `NewsProcessor` の成果物（記事、AI要約、統合要約、指標値）を、以下のマルチ出力へ分配。
  - Web HTML（既存）
  - Google Docs/Sheets（既存拡張）
  - SNS画像（新規）
  - note用Markdown（新規）
- レンダラー分離: `renderers/` 層を新設し、`html_renderer` / `image_renderer` / `markdown_renderer` に責務分割。
- アセット管理: `assets/templates/` にテンプレ群（HTML/CSS、SNS画像キャンバス、note章構成など）を配置。
- 出力ディレクトリ規約: 
  - SNS画像: `build/social/YYYYMMDD/`（`news_01_16x9.png` 等）
  - note記事: `build/note/YYYYMMDD.md`
- フィーチャートグル: `src/config/app_config.py` に `feature_flags` を追加（例: `enable_social_images`, `enable_note_md`）。

---

## 2. SNS投稿用 画像レポート生成フロー（新規）
- ゴール: X/Instagram向けの視認性の高い日次画像を自動生成（複数サイズ）。
- 出力仕様（初期）:
  - 16:9（X向け）、1:1（IG投稿）、9:16（Stories）
  - 余白・ブランドカラー・ロゴ、日付、主要トピック3〜5件、指標/センチメント/ワードクラウドのいずれかを添付
- 入力データ: 統合要約（要点）、記事ランキング（ソース/時刻/感情）、任意の簡易グラフ（ワードクラウド/市場ヒート）
- 実装方針（選択肢）:
  1) HTMLテンプレ＋ヘッドレスScreenshot（Playwright）
     - メリット: デザイン柔軟・CSSで高速試作、複数解像度の再利用が容易
  2) PIL/Matplotlib 直描画
     - メリット: 依存軽量、ローカルレンダリングが堅牢
  → 初期は 1) を推奨（テンプレ刷新が速い）。
- 自動投稿（任意）:
  - X API（Elevated必要）/ FB Graph経由（IG）をオプション化。初期は「自動生成のみ、手動投稿」で安定化。
- 成果物/配置: `build/social/YYYYMMDD/` に各サイズを保存。生成ログは `logs/` に集約。
- タスク（MVP）:
  - [ ] `assets/templates/social/` にHTML/CSSテンプレ作成（3サイズ）
  - [ ] `renderers/image_renderer.py` を新規実装（PlaywrightでSS生成）
  - [ ] `NewsProcessor` からレンダリング呼び出し（feature flag）
  - [ ] サンプル画像の自動生成ジョブ（ローカル/CI）
  - [ ] 品質チェック: 文字切れ/改行/色コントラスト/日本語フォント

---

## 3. note投稿用 文章生成フロー（新規）
- ゴール: noteにそのまま貼れるMarkdown本文と画像挿入案内を日次生成。
- 記事構成（初期テンプレ）:
  1) タイトル（例: 「今日のマーケット要点と注目トピック」）
  2) リード（100〜200字）
  3) 今日の3ポイント（箇条書き）
  4) 市場概況（統合要約の整形）
  5) 注目トピック（記事3〜5件：要約＋所感）
  6) チャート/図版（SNS画像 or チャート専門モジュールのPNG）
  7) まとめと翌日の注目
- 実装方針:
  - `renderers/markdown_renderer.py` でMarkdown生成（YAML Front Matter任意）
  - 画像は `build/social/YYYYMMDD/` と `build/charts/YYYYMMDD/` への相対パス参照
- 自動投稿:
  - note公式APIは限定的。初期は「生成→編集者がコピペ・画像添付」で運用
  - 将来的に Playwright で半自動投稿（別スクリプト、Secrets/2FAポリシー審議）
- 成果物/配置: `build/note/YYYYMMDD.md`
- タスク（MVP）:
  - [ ] テンプレ文面とセクション定義（`assets/templates/note/post.md.j2`）
  - [ ] `markdown_renderer.py` 実装（Jinja2）
  - [ ] `NewsProcessor` 統合（feature flag）
  - [ ] 出力の体裁チェック（見出し・リスト・改行）

---

## 4. 別プロジェクト: チャート分析スペシャリスト（グラフ作成含む）
- 目的: 価格データ/テクニカル指標から視覚レポートと簡易コメントを自動生成。
- データ: Yahoo Finance（`yfinance`）/ Alpha Vantage / FMP など。キャッシュ（Parquet/SQLite）。
- 指標: SMA/EMA/RSI/MACD/BB、出来高、期間切替（日/週）
- グラフ: `mplfinance`/`plotly`、テーマ統一、注釈（マーカー/イベント）
- AIコメント: 直近の動き＋背景（ニュース連携）を300〜500字で生成
- I/F: `chart_analyst` ライブラリ（別リポ）として、CLIとPython APIを提供
  - 出力: `build/charts/YYYYMMDD/<symbol>_daily.png`＋`insights.json`
- 典型ユース: Market_News のnote/SNS出力に画像/洞察を差し込む
- リポ構成（提案）:
  - `src/chart_analyst/data/`（取得・前処理）
  - `src/chart_analyst/indicators/`
  - `src/chart_analyst/plot/`
  - `src/chart_analyst/insights/`（LLMプロンプト）
  - `cli.py` / `config.yaml` / `tests/`
- タスク:
  - [ ] シンボル最小セットでMVP（`^GSPC`, `^NDX`, `USDJPY=X`, `N225`）
  - [ ] OHLC取得＋キャッシュ
  - [ ] 2〜3種の指標オーバーレイ
  - [ ] PNG出力の体裁（日本語フォント）
  - [ ] 簡易コメント生成

---

## 5. 別プロジェクト: 経済指標分析スペシャリスト（グラフ作成含む）
- 目的: FRED/OECD/IMF/e-Stat 等の指標を収集・正規化・可視化し、発表日連動の解説を生成。
- データ: FRED API（景気・物価・金利）優先、次にOECD/IMF。ID・頻度・季節調整の正規化。
- グラフ: YoY/MoM、長期トレンド、複合軸（例: CPIと政策金利）
- 発表トリガ: 発表カレンダー取り込み→新着時にレンダリング/要約を実行
- I/F: `econ_indicator_analyst`（別リポ）。
  - 出力: `build/indicators/YYYYMMDD/<series_id>.png`＋`insights.json`
- タスク:
  - [ ] FRED最小セット（CPI, Core CPI, Unemployment, Fed Funds）
  - [ ] 取得・正規化・欠損処理
  - [ ] 基本チャートテンプレ
  - [ ] 新着検知→自動出力
  - [ ] 簡易要約（背景/市場インプリケーション）

### 5.1 データ取得ソース比較（investpy以外の選択肢）
- Trading Economics: 世界各国の指標と経済カレンダー。`tradingeconomics` Pythonクライアント有、APIキー要。指標・国・頻度の網羅性が高く、カレンダーも提供（推奨）。
- Finnhub: 経済カレンダー/指標あり。`finnhub-python`。無料枠は制限強め、用途はカレンダー中心。
- Financial Modeling Prep: `economic_calendar` と主要指標API。`fmp-python`。無料枠あり、精度/網羅性はTEに劣る。
- FRED: 米国に強い。`fredapi`。系列粒度・改定履歴が安定。カレンダーは米国中心で自作が必要。
- OECD/IMF/World Bank/Eurostat/e-Stat/BOJ: 公的データ（SDMX/REST）。`pandasdmx`/`wbdata` 等で取得。網羅性◎だがカレンダー別途。
- investpy（参考）: Investing.comスクレイプ系。保守状況のブレやブロックのリスク。学習/試作には可、本番はAPI系の併用推奨。

結論: 「網羅的な取得＋カレンダー運用」を両立するなら Trading Economics を主軸に、米国詳細は FRED、各機関API（OECD/IMF/World Bank/e-Stat）を補完に回す構成が最適。

### 5.2 カレンダー/スケジュール設計
- 取得方針: まずTEのカレンダーAPIで「今後7日＋当日」を取得し、`ics` 生成とDB登録を同時に実施。補完に Finnhub/FMP をフォールバック（差分マージ）。
- タイムゾーン: すべてUTCで保持し、表示/通知時に `Asia/Tokyo` 等へ変換。夏時間差異を吸収。
- 改定/遅延: 直近T-2〜T+2日を再取得し、`actual/forecast/previous/revised` を上書き（`release_revision` を別レコード保持）。
- ICS出力: `build/calendars/economic.ics` を日次再生成。Google/Apple/Outlookに購読可能。
- 通知: 重要度 High（または自定義スコア）をSlack/メールに60分前通知。APSchedulerで5分間隔の差分チェック。

サンプル（TEカレンダー→ICS）:
```python
import tradingeconomics as te
from ics import Calendar, Event
from datetime import datetime, timedelta, timezone

te.login('YOUR_API_KEY')
events = te.getCalendar(initDate=datetime.utcnow().date(), endDate=(datetime.utcnow()+timedelta(days=7)).date())

cal = Calendar()
for ev in events:
    # ev: {'Country','Category','Event','Date','Reference','Importance','Actual','Forecast','Previous',...}
    dt = datetime.fromisoformat(ev['Date'].replace('Z','+00:00'))
    e = Event()
    e.name = f"{ev['Event']} ({ev['Country']})"
    e.begin = dt
    detail = f"Imp:{ev.get('Importance')} F:{ev.get('Forecast')} P:{ev.get('Previous')}"
    e.description = detail
    cal.events.add(e)

with open('build/calendars/economic.ics', 'w') as f:
    f.writelines(cal)
```

### 5.3 正規化スキーマ（Series/Release/Calendar）
- series: `series_id`（機関ID＋地域＋調整法の正規化）、`title`、`provider`、`freq`（M/Q/W/D）、`seasonal_adj`、`unit`。
- release: `series_id`、`period`（例: 2024-07）、`release_time_utc`、`actual`、`forecast`、`previous`、`revised_from`、`source_url`、`vintage`。
- calendar: `event_id`、`title`、`country`、`importance`、`scheduled_time_utc`、`related_series_id`（複数可）、`status`（scheduled/reported/revised）。
- 重要度スコア: `importance_raw`（提供値）＋自前スコア（市場影響度、夜間/重複イベント補正）を別カラムに保持。

### 5.4 実装アーキテクチャ（モジュール分割）
- `adapters/`:
  - `trading_economics.py`: 指標/カレンダー取得。レート制御と再試行。
  - `fred.py`: シリーズ取得（`fredapi`）。IDマッピング表で`series_id`正規化。
  - `sdmx.py`: OECD/IMF/Eurostat/e-Stat/BOJ向けの共通SDMX取得。
  - `investpy_fallback.py`: 非公式。障害時限定の補完（任意）。
- `normalize/mapper.py`: プロバイダ→共通スキーマ変換、単位換算、季節調整フラグ統一。
- `storage/`: Parquet（系列）＋SQLite/Postgres（カレンダー/リリース）。
- `scheduler/`: APSchedulerで「カレンダー差分」「当日発表のリリース取得」「改定チェック」。
- `render/plots.py`: PNG/SVGテンプレ。YoY/MoM、長期トレンド、2軸、改定注記。
- `reports/insights.py`: サプライズ度＝(実績−予想)/予想乖離、過去分布からzスコア→コメント生成。

サンプル（FRED系列取得→正規化格納）:
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

### 5.5 見せ方（UI/レポート/通知）
- ダッシュボード: 「今週の主な発表」「サプライズヒートマップ」「国・テーマ別フィルタ」「改定履歴トラッカー」。
- 記事連携: 発表直後に関連ニュース3本を自動添付（既存News基盤から検索）し、1枚画像/短文まとめを生成。
- グラフィック: 1) 長期推移＋景気後退網掛け、2) 予想/実績の散布図（サプライズ分布）、3) 政策金利とインフレの2軸。
- 告知: 重要イベントの「前日夕方のまとめ」と「60分前リマインド」をSlack/メール。ICS購読を案内。
- note用: 月次テーマ別まとめ（インフレ・雇用・製造業）、指標別の「見方」と市場含意を定型テンプレで差し込み。

### 5.6 MVP/スケジュール（具体タスク）
- Week 1: TEカレンダー→ICS/DB、FRED 4系列の取得・正規化・基本チャート。
- Week 2: サプライズ算出と自動要約、Slack通知、ダッシュボード簡易版（Streamlit）。
- Week 3: OECD/IMF/World Bank/e-Statの優先系列を追加、改定検知、画像テンプレ整備。
- Week 4: 運用硬化（レート制御/リトライ/監視）、note月次レポの自動ドラフト。

### 5.7 採用判断メモ（investpyの使いどころ）
- 強み: Investing.com準拠の網羅的イベント名・重要度ラベル。学習・PoCでは便利。
- 課題: 公式APIではないため、サイト側の変更/ブロックに弱い。安定運用と再現性の観点で本番は回避推奨。
- 方針: 本番は TE/FRED/公的APIを主軸。investpyは短期の補完・比較検証に限定。


---

## 6. 横断テーマ（品質/運用）
- 設定管理: `app_config.py` に feature flags と出力仕様（サイズ/フォント/保存先）。
- デザイン: `assets/brand/` にカラー/ロゴ/フォント、`assets/templates/` にJinja2/HTML/CSS。
- 性能/コスト: スクショはバッチ化、LLMはトークン上限・要約粒度を制御、使用量をSheetsに継続記録。
- テスト: レンダラーはスナップショットテスト（画像差分）＋テンプレLint（必須要素の存在）。
- セキュリティ: 認証情報は `.env`/Secrets、headlessログイン自動化はオプション外出し。

---

## 7. マイルストーン（案）
- M1: SNS画像MVP（16:9のみ、主要3トピック） 3日
- M2: note Markdown MVP（画像外部参照、手動投稿） 2日
- M3: チャート分析MVP（4シンボル、PNG出力） 5日
- M4: 経済指標MVP（FRED 4系列、PNG出力） 5日
- M5: 統合運用（スケジュール実行、品質監視） 3日

---

## 8. ディスカッション/決めたいこと
- ターゲットSNS: X/IG/LinkedIn（初期はXのみ？）
- ブランド/デザイン方針: 色/フォント/ロゴの指定有無
- note記事の筆致とトーン: どの程度主観コメントを許容？
- 外部プロジェクトの分離度: サブモジュール運用 or 完全独立？
- 自動投稿の範囲: どこまで自動化し、どこを手動確認にする？

---

## 9. 次アクション（提案）
- [ ] M1着手: `assets/templates/social/` と `renderers/image_renderer.py` のスケルトン追加
- [ ] M2着手: `assets/templates/note/post.md.j2` と `renderers/markdown_renderer.py`
- [ ] 設定: `app_config` に feature flags と出力先の追記
- [ ] 短期レビュー: 生成サンプル3種をSlack/Driveに共有→修正

（このドラフトは随時更新します。要望・アイデアはこのmdに追記してください）

---

## 10. 追加アイデア集（自由メモ）
- 週間・月間ハイライト版（Best 10ニュース＋テーマ別まとめ）
- ニュースレター配信（メール/SendGrid）とRSS強化（要約＋画像）
- LINE/Slack/Telegram通知に画像サムネを添付（閲覧率向上）
- パーソナライズ配信（カテゴリ/銘柄ウォッチリスト）
- 過去要約の検索/RAG（ベクトルDB）で「同様事例」提示
- KPIダッシュボード（生成数・投稿CTR・読了率）
- 読者フィードバック収集（簡易アンケート→要約品質改善に反映）

---

## 11. 過去要約アーカイブ/RAG戦略（詳細）

### 現状と課題
- 保存: Google Docsに日次サマリー、全文上書きドキュメント。DBにも記事・AI要約は30日程度保持（クリーンアップ）。
- 課題: 30日超の削除設定で長期横断検索が困難。Google Docsは全文検索/構造化検索が弱く、RAGに不向き。

### 方針（提案）
1) 保持方針の変更: 基本「削除しない」。古いものは「アーカイブ」へ移し、常時参照可能に。
2) データ正規化して保存: 日次の「統合要約」「個別要約」をJSON/Markdownで構造化保存（Drive or Supabase Storage）。
3) RAG向けベクター索引: 要約テキストをチャンク化→埋め込み→ベクターDBに保存（メタデータ付）。

### 保存オプション比較
- Google Driveのみ: 運用が簡単/コスト低。検索が弱い。RAGは別インデックス必須。
- SQLite + FAISS/Chroma（ローカル）: セットアップ容易。共有/スケールが弱い。
- Supabase（推奨）: Postgres + pgvector + Storage。RLSやAPI、拡張性が高い。少コストで運用可能。

### 推奨アーキテクチャ（Supabase案）
- ストレージ: `storage://market-news-archive/YYYY/MM/DD/` に `daily_summary.md` と `corpus.json`（構造化）を保存。
- データベース（pgvector）: `documents`（日次単位）と `chunks`（要約断片）テーブル。`chunks` に `embedding vector`、`date`、`region`、`category`、`source`、`sentiment` などのメタデータ付与。
- 埋め込みモデル: 初期はローカル/OSS（`sentence-transformers/all-MiniLM-L6-v2`）か、Google Embeddings（利用可能なら）。コスト/速度で選択可能に。

### ETL/RAGフロー
1) Extract: 実行セッション終了時に、DBから個別要約＋統合要約を取得。
2) Transform: チャンク分割（400–800字、オーバーラップ10–20%）、メタデータ付与（日時/地域/カテゴリ/ソース/URL）。
3) Embed: 埋め込み生成（バッチ化し再試行/レート制御）。
4) Load: SupabaseにUpsert（`documents`/`chunks`）。原文JSON/MDはStorageへ保存。
5) Query: Top-k類似検索＋メタデータフィルタ（期間/地域/カテゴリ）で返却。必要に応じて再ランキング。

### Googleドキュメントの有効活用
- バックリンク保持: 各チャンクに該当Google DocのURLと見出しアンカーをメタデータ保持→検索結果から該当箇所へジャンプ。
- 既存資産の移行: 過去DocをAPIで抽出→Markdown/JSONへ正規化→一括埋め込み→インデックス作成。

### 保持/ガバナンス
- Retention: 既定は「保持」。容量逼迫時は「古いベクターは冷温保存へ」「原文は圧縮」などの多層化。
- コスト: Embedding生成は日次バッチ、トークン/文字数上限で制御。Sheetsに継続記録（既存の使用量トラッキングに統合）。
- 品質: 定期的に重複・低品質チャンクを再圧縮。検索のPrecision/Recallを簡易ABで測定。

### 実装タスク（MVP）
- [ ] 保持ポリシーの合意: 「基本保持」「削除ではなくアーカイブ」へ方針変更
- [ ] スキーマ設計: Supabase `documents`/`chunks`（pgvector128/768）、インデックス、RLS
- [ ] エクスポート: `scripts/export_corpus.py`（DB→JSON/MD、Drive/Storageへ）
- [ ] 埋め込み: `src/rag/embedding_pipeline.py`（チャンク/埋め込み/Upsert）
- [ ] 検索API/CLI: `src/rag/query_service.py` と `scripts/rag_query.py`（例: `--since 2024-01-01 --region japan`）
- [ ] 既存データ移行: Google Docsから日次要約を抽出→一括投入

### 代替ミニマム（Supabase不採用の場合）
- SQLite + Chroma/FAISSをローカル同梱。`build/rag_index/` にDB/メタデータを置く。
- 将来移行しやすい抽象I/F（`VectorStore`プロトコル）を用意。

### 設定変更（提案）
- `app_config.py`:
  - `retention_policy`: `keep` | `archive` | `delete`（初期は`keep`）
  - `rag.enabled`: true/false、`rag.backend`: `supabase` | `local`
  - `rag.chunk_size`/`rag.chunk_overlap`/`rag.model`
- CI/運用: 生成後に ETL→埋め込み→インデックス作成までを1バッチに。

---

## 12. Supabase Free 前提の構成（実装指針）

### 目的と制約
- 目的: 無料枠で安定運用しつつ、RAG検索と長期アーカイブを実現。
- 制約: DB/Storage/帯域の無料枠内に収める。DBサイズは軽量化、画像は当面外部配信を優先。

### 設計の要点（Free最適化）
- ベクター次元を圧縮: `vector(384)` を採用（768の半分でDBフットプリント削減）。
- DBには「要約テキスト＋最小メタデータ＋埋め込み」のみを保存。原文/フル構造はStorageにJSON/MDで保存。
- インデックスは `ivfflat (vector_cosine_ops)` を使用（listsは100程度）。
- 画像は当面Supabase Storageに置かない（GitHub PagesやDrive共有）。
- しきい値監視: DB/Storage使用量が増えたら「古いチャンクを冷温化（Parquet/JSONをStorageに退避）」し、DBは最新nヶ月のみのベクターを保持。

### スキーマ/DDL（初期）
- 追加ファイル: `scripts/migrations/supabase_free_init.sql`（DB拡張・テーブル・インデックス・検索関数）
- 主要方針:
  - `documents`: 日次単位のメタ＋Storageパス
  - `chunks`: チャンク・メタ・embedding(384)
  - `search_chunks(...)`: 類似検索を簡便に叩けるSQL関数

### ストレージ規約
- Storage: `market-news-archive/YYYY/MM/DD/` に `daily_summary.md` と `corpus.json`
- DB: `documents` は `storage_path` と `url` を保持（バックリンク）

### パイプライン（Free）
1) Export: DB→JSON/MDをStorageへ（テキスト主体）
2) Chunk/Embed: OSS埋め込み（MiniLM-384）で生成（APIコストゼロ）
3) Upsert: `documents/chunks` に投入、`ivfflat`を再構築（必要時）
4) Monitor: DB/StorageサイズをSheetsへ記録、しきい値超過で冷温化

### 実装タスク
- [ ] `scripts/migrations/supabase_free_init.sql` をデプロイ（SQLエディタ or CLI）
- [ ] ETL/Embed/UpsertスクリプトのMVP
- [ ] 使用量監視ジョブをSheetsに統合
- [ ] 冷温化ポリシー（最新nヶ月のみベクター保持）
