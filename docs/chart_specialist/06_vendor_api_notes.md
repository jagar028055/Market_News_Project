# ベンダー/APIメモ（IG APIを中心に）

最終更新: 2025-08-24

## IG APIの可用性（結論）
- IG Labs（グローバル）: REST/Streaming APIを提供。Demo口座/Live口座の双方でAPIキー発行して利用可能（地域/口座種別に依存）。
- IG証券（日本）: 公式ヘルプに「APIアクセスは提供しておりません」との記載あり。日本口座ではAPI非対応の可能性が高い。

## 参考リンク
- IG Labs トップ: https://labs.ig.com/
- Getting started: https://labs.ig.com/gettingstarted
- REST APIガイド: https://labs.ig.com/rest-trading-api-guide.html
- FAQ: https://labs.ig.com/faq
- IG International（API案内）: https://www.ig.com/en/trading-platforms/trading-apis/how-to-use-ig-api
- IG証券（日本）ヘルプ: https://www.ig.com/jp/help-and-support/platforms/general-queries/how-can-i-acces-the-ig-api-and-what-can-i-use-it-for

## 口座とAPIキー
- グローバル: My IG からAPIキーを発行（Demo/Live）。利用規約に同意が必要。レート制限あり。
- 日本: 上記ヘルプに基づきAPIは提供していない旨。代替としてデータ取得は `yfinance` / 取引所API、発注連携は他社API（例: IBKR など）を検討。

## 運用上の示唆
- JP居住かつIG証券口座のみ → IG APIは使わず、分析は無料データ/APIで実施。
- 海外IG口座 or Demo → IG Labs APIの学習/試作は可能だが、リージョン規約に従う。

（注）各リンクの内容・提供範囲は将来変更される可能性があります。正式運用前に最新の公式ドキュメントで再確認してください。
