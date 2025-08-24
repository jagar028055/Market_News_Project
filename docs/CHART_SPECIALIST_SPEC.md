# チャートスペシャリスト機能 仕様ドラフト（独立版）

最終更新: 2025-08-24（初版）

## 目的と位置づけ
- 価格データとテクニカル指標から、視認性の高いチャート画像と機械可読な洞察を自動生成。
- 生成物は Market_News の note/SNS 出力へ差し込み、日次運用に耐える品質を目指す。
- 実装は独立ライブラリ（`chart_analyst`）として切り出し、CLI と Python API を提供。

## ご相談内容（要約・原文）
- チャートはPythonで生成。データはどこから引っ張るか（無料希望）
- 例えば、Tradingviewのリストページをスクリーンショットして、定期的に分析する機能は可能か
- チャート分析にあたっては、様々な分析手法があるので、その手法を網羅的に収集する必要がある
- 日足、４時間足、１時間足での分析が可能であれば、なお良い
  ただし、時間足についてはCFDなどほぼ24時間稼働しているデータが必要となる

---

## 結論サマリー（提案）
- 無料データの主軸は `yfinance`（Yahoo Finance）と暗号資産は取引所API（例: Binance）。4時間足は 1時間足からリサンプリングで安定化。
- TradingView スクリーンショット運用は技術的には可能（Playwright）が、ToS/変更耐性の観点で本番は非推奨。数値分析はAPI由来のOHLCVで実施。
- 分析手法は `pandas` + `pandas_ta` を中心に、トレンド/モメンタム/ボラ/出来高/パターン検出を標準化。ルールは `YAML` で宣言的に管理。
- 出力は PNG（`mplfinance`）と HTML（`plotly`）に統一し、テキスト洞察は `insights.json` に保存。日・4H・1H のマルチタイムフレーム対応。

---

## 無料データソース（推奨と補足）
- Yahoo Finance（`yfinance`）
  - 対応: 株式/指数/為替/一部コモディティ。日足、1時間足などに対応。分足は保持期間が短い（例: 1分は直近7日）。
  - 長所: 無料・導入容易。短所: レイテンシ/欠損・間欠的な仕様変更の影響。
  - 4時間足は `1h` を取得して `resample('4H')` で生成。
- Stooq（`pandas_datareader`）
  - 対応: 主に日足。シンプルな代替/バックアップとして利用。
- Alpha Vantage（APIキー必要・無料枠あり）
  - 対応: 株/FX/暗号資産のインターデイ。レート制限（5req/min, 500req/day）に留意。
- Binance 公開API（暗号資産）
  - 対応: 24/7 の 1m〜1d 足。暗号資産の24時間系タイムフレームのベースに最適。
- Oanda Practice API / IG API（任意・口座必要）
  - 対応: FX/CFD の実用的な24時間データ。無料枠は口座前提。将来の堅牢化選択肢。

推奨初期構成:
- 株/指数/為替: `yfinance` を主軸（日・1H）。4H はリサンプリング。
- 暗号資産: 取引所API（例: Binance）で 1H/4H を取得。
- デイリーバックアップ: Stooq。必要時に Alpha Vantage を補完。

注意（ライセンス/ToS）:
- 無料データの再配布・商用利用条件は各提供元に準拠。生成画像の公開は概ね許容されるが、数値そのものの再頒布は避ける方針。

---

## TradingView スクリーンショット案の可否
- 技術面: `playwright` でリストページへ自動ログイン→スクショ取得→`ocr`（任意）でテキスト抽出は可能。
- 運用/法務面: ToSや自動化制限、DOM変更の破壊的影響が大きい。本番の定期分析基盤には非推奨。
- 代替: 公式API系（`yfinance`/取引所API）でデータ取得→HTMLテンプレを `playwright` で画像化すれば、見た目は近い運用が実現可能。

### 補足: 個人用途としてのスクショ機能（将来オプション）
- 位置づけ: 個人利用・参考資料としてのスクショ収集。アルゴリズム分析の入力には使用しない。
- 実装: `chart_analyst tvshot --watchlist tv/watchlist.yaml --out build/tvshots/`（`playwright` 利用）。
- ガードレール:
  - 自動ログイン情報はローカルの `.env` またはOSキーチェーン管理。
  - 取得頻度は低め（例: 1–4回/日）。DOM変更に備えセレクタは疎結合化。
  - 出力はローカルのみ（再配布しない）。

---

## 分析手法カタログ（初期セット）
- トレンド: SMA/EMA、WMA、一目均衡（任意）、トレンドライン自動当て（近似）。
- モメンタム: RSI、Stoch、MACD、ROC、CCI。
- ボラティリティ: ボリンジャーバンド、ATR、標準偏差、HV（任意）。
- 出来高: OBV、MFI、出来高移動平均、出来高急増検知。
- パターン検出: ローソク足（包み足/ピンバー等）、レンジ/ブレイクアウト、ダイバージェンス。
- マルチTF: 1D/4H/1H の合流（例: 上位足トレンド順行＋下位足の押し目反発）。
- スコアリング例: トレンド強度×モメンタム×ボラの合成スコアでランキング。

実装スタック:
- 計算: `pandas`, `numpy`, `pandas_ta`（`ta-lib` はネイティブ依存のため初期は回避）。
- 描画（静的）: `mplfinance`（PNG出力、注釈/イベント対応）。
- 描画（対話）: `plotly`（HTML出力、ホバー/ズーム）。

---

## タイムフレーム方針（1D/4H/1H）
- 1D（日足）: すべてのアセットで標準対応。
- 1H（1時間足）: `yfinance`/Binance ともに対応（保持期間に注意）。
- 4H（4時間足）: 1H からリサンプリング（OHLCV再構築: O=最初, H=max, L=min, C=最後, V=合計）。
- 24時間系の要件: FX/暗号資産は24/7データでカバー。CFDは将来的に Oanda/IG 連携で堅牢化。

---

## 生成物とディレクトリ
- 画像: `build/charts/YYYYMMDD/<symbol>_<tf>.png`（`tf` は `1d|4h|1h`）。
- 対話: `build/charts/YYYYMMDD/<symbol>_<tf>.html`（任意）。
- 洞察: `build/charts/YYYYMMDD/<symbol>/insights.json`（数値指標・スコア・所感下書き）。

---

## ルール定義（YAML例）
```yaml
name: standard_v1
signals:
  - id: trend_follow_rsi
    tf: [1d, 4h, 1h]
    when:
      - ema(1d, 50) > ema(1d, 200)
      - rsi(4h, 14) > 55
      - close(1h) > bb_mid(1h, 20)
    action: long_bias
    note: 上位足順行＋下位足押し目の順張りサイン
  - id: mean_reversion_bb
    tf: [4h]
    when:
      - close(4h) < bb_low(4h, 20)
      - rsi(4h, 14) < 35
    action: watch_rebound
    note: バンド拡張からの戻り狙い
```

---

## 簡易API/CLI仕様（案）
- 取得: `chart_analyst fetch --symbol "^GSPC" --interval 1h --days 120`
- 解析: `chart_analyst analyze --symbol "USDJPY=X" --tf 1h,4h,1d --rules rules/standard.yaml`
- 描画: `chart_analyst plot --symbol "BTCUSDT" --tf 4h --style dark`
- 一括: `chart_analyst run --watchlist watchlists/core.yaml --out build/charts/` 

戻り値（例）:
```json
{
  "symbol": "USDJPY=X",
  "asof": "2025-08-24T09:00:00Z",
  "scores": {"trend": 0.7, "momentum": 0.5, "volatility": 0.3},
  "signals": [
    {"id": "trend_follow_rsi", "tf": "4h", "state": "active"}
  ],
  "notes": "日足で上昇基調継続、4Hで押し目反発の兆候。"
}
```

---

## キャッシュ/永続化
- フォーマット: Parquet（`data/ohlcv/<symbol>/<tf>.parquet`）。`pyarrow` を使用。
- 更新: 直近 N 日のみAPIから差分取得→ローカルで統合。欠損は前後の取引日で補完（必要最小限）。
- レート制限: シンボルと間隔ごとにスロットリング。`APScheduler` で分散実行。

---

## バックテスト対応（重要）
- エンジン候補: `backtesting.py`（簡潔）/ `vectorbt`（高速・多銘柄向き）。初期は `backtesting.py` を採用、将来 `vectorbt` を追加。
- 期間上限（目安・データ源依存）:
  - 日足: Yahooは銘柄により10〜70年（例: `^GSPC`は1950年代〜）。
  - 1時間足: Yahooは概ね1〜2年程度が目安（シンボル差あり）。
  - 4時間足: 1時間足からのリサンプリング→同期間相当。
  - 1分足: Yahooは直近約7日。取引所API（Binance等）は上場以降の全期間が入手可能。
  - FX/CFD: 無料で長期の高頻度は限定的。将来 Oanda/IG API（口座前提）で数年〜の取得を検討。
- 実務設計:
  - 手数料/スリッページ/取引時間帯をモデル化（`fee_bps`, `slippage_bps`, `session_calendar`）。
  - ウォークフォワード検証（Train→Validate→Roll）と時系列CVで過学習を抑制。
  - 指標は事前計算・キャッシュして試行回数を最適化。
- CLI例:
  - `chart_analyst backtest --symbol "USDJPY=X" --tf 1h --rules rules/standard.yaml --start 2020-01-01 --end 2024-12-31 --fee-bps 1 --slippage-bps 2`
  - `chart_analyst optimize --symbol "^GSPC" --tf 1d --rule trend_follow_rsi --params ema_fast=10..30 ema_slow=100..250 rsi=20..40 --trials 200`
- 指標/評価軸: 勝率、CAGR、MaxDD、Sharpe/Sortino、Calmar、Profit Factor、Exposure、トレード数、Regime別成績。

---

## AI/機械学習による戦略探索（提案）
- LLM提案＋自動検証:
  - 入力: 可用データ範囲、対象アセット、リスク制約、既存ルール群。
  - 出力: ルール候補（YAML/DSL）と合理性メモをLLMが生成→自動でバックテスト→メトリクスが閾値未満なら改善プロンプトで反復。
- パラメータ最適化: `Optuna` によるベイズ最適化。目的関数は多目的（例: 最大化CAGR、制約: MaxDD<=X%、トレード数>=N）。
- 時系列学習（任意）:
  - 特徴量: 指標値、レジームラベル（トレンド/レンジ）、ボラ指標、出来高比率。
  - 手法: ツリーモデル（LightGBM/XGBoost）で売買確率推定→閾値でエントリ。リーク防止のため厳格な遅延処理。
- ガードレール:
  - 未来情報の混入防止（`shift`/`ffill`管理、終値確定ベース）。
  - 取引コスト/滑り/約定制約を常時適用。
  - テストは未観測期間・未観測銘柄で外部妥当性を確認。

---

## エラーハンドリング/品質
- 欠損・非稼働日の穴: 取引カレンダー非依存のインデックスはリサンプリングで吸収。指数/FX/暗号で挙動が異なる点に注意。
- yfinance の仕様変更: バックアップ経路（Stooq/Alpha Vantage）をスイッチ可能にして緩和。
- 画像品質: 日本語フォント同梱/指定、色覚多様性に配慮したパレット、注釈の重なり回避。

---

## MVP範囲（2週間想定）
- データ: `^GSPC`, `^NDX`, `USDJPY=X`, `^N225`, `BTCUSDT`（Binance）の 1D/1H/4H。
- 指標: SMA/EMA/RSI/MACD/BB、出来高移動平均。
- 出力: PNG と `insights.json`。note/SNS への差し込みを想定した体裁。
- 運用: 日次/時間毎のジョブ（`APScheduler`）、エラーログ/簡易リトライ。

---

## 実装タスク（チェックリスト）
- [ ] データ層: `yfinance`/Binance コネクタ + Parquet キャッシュ
- [ ] リサンプリング: 1H→4H のOHLCV再構築ユーティリティ
- [ ] 指標層: `pandas_ta` ラッパー（欠損/窓長の扱い統一）
- [ ] ルール評価: YAML→式パーサ（安全評価）と多TF合流
- [ ] 可視化: `mplfinance` テーマ、注釈API、PNG出力
- [ ] 洞察: スコア集計→`insights.json` 生成（300–500字の下書きは任意）
- [ ] CLI: `fetch`/`analyze`/`plot`/`run` のスケルトン
- [ ] スケジューラ: `APScheduler` でウォッチリスト巡回
- [ ] ドキュメント: 使い方とテンプレ（`docs/`）

---

## フォルダ構成（案）
```
chart_analyst/
  src/chart_analyst/
    data/        # 取得/キャッシュ/リサンプリング
    indicators/  # 指標計算
    rules/       # YAML→評価
    plot/        # 画像/HTML描画
    insights/    # スコア/テキスト生成
  data/ohlcv/
  build/charts/
  rules/
  cli.py
  config.yaml
  tests/
```

---

## サンプル（yfinance→4Hへリサンプリング→PNG出力）
```python
import yfinance as yf
import pandas as pd
import mplfinance as mpf

sym = "USDJPY=X"
df = yf.download(sym, period="120d", interval="1h", progress=False)
# yfinanceは列名が"Open","High","Low","Close","Volume"

# 4時間足へリサンプリング（OHLCV再構築）
df_4h = pd.DataFrame()
df_4h['Open'] = df['Open'].resample('4H').first()
df_4h['High'] = df['High'].resample('4H').max()
df_4h['Low'] = df['Low'].resample('4H').min()
df_4h['Close'] = df['Close'].resample('4H').last()
df_4h['Volume'] = df['Volume'].resample('4H').sum()
df_4h.dropna(inplace=True)

# 簡易描画
mpf.plot(df_4h.tail(200), type='candle', volume=True,
         style='yahoo', savefig=dict(fname='build/charts/sample_usdjpy_4h.png', dpi=150))
```

---

## リスクと今後の拡張
- yfinance 依存リスク: 代替経路（Alpha Vantage/Stooq）を同一I/Fで差し替え可能に実装。
- 24時間系の堅牢化: Oanda/IG APIをオプション実装（口座/トークン管理ポリシー要）。
- アラート: しきい値/パターン検出時に Slack/メール通知（任意）。
- バックテスト: `backtesting.py` などと連携し、ルール妥当性の検証を将来追加。
- UI: `Streamlit` でウォッチリスト閲覧・手動トリガを提供（任意）。

---

以上。実装に着手する場合は、MVPチェックリスト順で進めます。
