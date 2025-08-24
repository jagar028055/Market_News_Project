# UIラフ／ワイヤーフレーム（経済指標 新機能）

本書は、ライト（昨日一覧）とディープ（指標深掘り）を中心に、グラフ提案・スケジュール表仕様・画面構成をテキストワイヤーで示します。

---

## 1. デザイン原則
- 情報密度は中〜高。重要度/サプライズを視覚的に強調。
- 予想が無い場合はサプライズUIを隠す（列非表示/空欄）。
- モバイルでは列を折りたたみ、重要列を優先表示。
- 配色はコントラスト比AA以上。色覚多様性に配慮（赤緑の単独依存を避ける）。

---

## 2. 画面A：昨日の経済指標一覧（ライト）

```
+-----------------------------------------------------------------------------------+
| 昨日の経済指標一覧 [YYYY-MM-DD]   TZ: Asia/Tokyo  [日付← →]  [CSV] [MD] [コピー]     |
| [国] US EU UK JP CA AU  [重要度] All High  [検索:__________]   [予想欠損を除外]   |
+-----------------------------------------------------------------------------------+
| Country | Indicator                       | Time | Imp | Forecast | Previous | Actual | Surprise | Src |
| US      | CPI (YoY)                       | 21:30| H   | 3.1%     | 3.3%     | 3.0%   | -0.1pp   | BLS |
| JP      | 機械受注 (MoM)                  | 08:50| M   | 0.8%     | -1.2%    | 1.1%   | +0.3pp   | CABI|
| EU      | HICP Core (YoY)                 | 19:00| H   | 2.8%     | 2.9%     | 2.7%   | -0.1pp   | Euro|
| ...                                                                                  |
+-----------------------------------------------------------------------------------+
Legend: Surprise は forecastが存在する場合のみ。Srcは一次情報へのリンク（BLS/BEA等）
```

- 操作:
  - 重要度 High のみのトグル、国フィルタ、テキスト検索。
  - 出力: CSV/Markdownコピー。
- 表示差分:
  - Surpriseは色チップ（負:青、正:橙）。0ライン付近は淡色。
  - 予想欠損の行はSurprise列を空欄に。

---

## 3. 画面B：指標の深掘り（ディープ）

```
US: CPI (All Items, SA)   [YoY] [MoM] [Long-term] [2-axis: CPI+FFR]      [PNG] [CSV]
Meta: Provider FRED | Freq M | Unit Index(1982-84=100) | SA Yes | Since 1970-01
-------------------------------------------------------------------------------
|                                 グラフ領域                                   |
|  - YoY: 折れ線 + 景気後退網掛け                                             |
|  - MoM: 棒（±0強調）                                                       |
|  - 2軸: CPI（左軸）と政策金利（右軸）                                       |
-------------------------------------------------------------------------------
サマリ: Actual 3.0% | Forecast 3.1% | Previous 3.3% | Surprise -0.1pp | z -0.42
注記: 直近3ヶ月の改定は軽微。前年比はベース効果で鈍化。エネルギー寄与低下。
[関連ニュース 3件] Market_Newsから自動抽出 → タイトル/時刻/リンク
```

- チャート切り替え: YoY/MoM/Long-term/2軸。ツールチップで値を表示。
- ダウンロード: PNG/CSVを提供。凡例・単位・ソースを明記。
- 関連ニュース: 内製News基盤からキーワード一致で3件表示。

---

## 4. 画面C：ダッシュボード（任意/将来）

```
[Surprise Heatmap]  （行=国、列=指標） 値= zスコア  カラーバー: 青(-) 0 灰 橙(+)
[Upcoming Timeline]  今日〜7日: 発表イベント（重要度Highを強調）
[Top Movers]         Surprise |Δz| の大きい上位N件、前回比較の矢印
[Filters]            国/指標/重要度/期間
```

- 用途: 俯瞰と優先度付け。ライト/ディープの入口。

---

## 5. グラフ仕様（詳細提案）
- 共通:
  - 日本語フォント埋め込み、軸/凡例のフォントサイズ一貫。
  - タイトルに期間・単位・季節調整・データソースを明示。
- 指標別:
  - CPI: YoY折れ線＋景気後退網掛け、MoM棒（±0線）、政策金利2軸。
  - 雇用統計: NFP前月差の棒＋失業率（右軸）折れ線。
  - 小売売上: MoM棒＋3MMA線、YoY折れ線（副図）。
  - GDP: 前期比年率棒、寄与度スタック（消費/設備/在庫）（任意）。
  - PMI: 50基準線、サブ指数（新規受注/雇用）を細線で重ねる。
  - サプライズ: 散布図（時系列、予想vs実績）とヒストグラム（過去分布）。

---

## 6. 経済スケジュール表（仕様）
- カラム: `date_local` `time_local` `date_utc` `country` `indicator` `importance` `forecast` `previous` `actual` `source`
- 並び替え: `importance desc, time_local asc`
- 表示ルール:
  - `forecast` 欄がNaNの行は `surprise` 非表示。
  - `source` には一次情報URL（BLS/BEA/ECB/ONS等）を可能なら付与。
- ICS仕様:
  - UID: `econ-{country}-{indicator}-{YYYYMMDDThhmmZ}`
  - DTSTART/DTEND: UTC。All-dayは使わず、未定時刻は 00:00Z として説明欄に「時刻未定」。
  - DESCRIPTION: `Forecast/Previous/SourceURL` を含める。
  - CATEGORIES: `Economics,{country},{importance}`
  - 重要イベントは `VALARM` 60分前を付与（任意）。

---

## 7. コンポーネント/状態
- フィルタバー: 国トグル、重要度トグル、検索、TZ切替（UTC/ローカル）。
- テーブル: 仮想リストで高速描画、列幅固定。スマホはカード表示に切替。
- 状態: Loading/Empty/Error/No-Forecast（Surprise非表示）。

---

## 8. スタイル/アクセシビリティ
- カラー: ブランド基調＋青(負)・橙(正)のサプライズ配色。
- フォント: Noto Sans JP、等幅は UIに未使用。
- キーボード操作: Tab移動、Enterでトグル。
- スクリーンリーダ: テーブル列に `aria-label`、グラフは代替テキストを添付。

---

## 9. 出力と連携
- ライト: `build/reports/daily_indicators/YYYYMMDD.md` を生成し、note下書きに流用。
- ディープ: PNG/JSONを note/SNS に貼付。関連ニュース3件を併記。
- ICS: `build/calendars/economic.ics` を配布。

---

## 10. 実装メモ
- プロット: `matplotlib/mplfinance/plotly` のいずれか。初期は `matplotlib` で固定テンプレ。
- フラグ: `feature_flags.econ_daily_list` と `econ_deep_dive` を追加。
- フォールバック: investpy失敗時は FMP/Finnhub/RSS。差分解決は `source_priority` 設定に従う。

