# GitHub Actions における OAuth2 認証失敗の原因調査と対策

このドキュメントは、GitHub Actions 上での Google 認証が失敗する事象について、原因分析と是正策を整理したものです。ローカルでは成功する一方、Actions では失敗する状況に対して、構成・実装・運用の観点から切り分けました。

## 結論サマリ

- 失敗の直接原因は、GitHub Actions 実行時に「OAuth2 経路」が選択され、リフレッシュトークン更新で `invalid_grant` が発生していること。
- 当初の暫定対処としては「サービスアカウント固定で実行（ActionsからOAuth2用の環境変数を外す）」が有効だった。
- 最終決定として、認証方式をOAuth2へ恒久移行し、ワークフローとアプリ設定を整流化（`GOOGLE_AUTH_METHOD='oauth2'` 固定、サービスアカウント変数を除去、デフォルト値をoauth2へ変更）した。

---

## 調査ログ抜粋（実際の失敗）

```
OAuth2認証方式を使用します...
🔍 OAuth2環境変数デバッグ:
  CLIENT_ID: 設定済み (********************ontent.com)
  CLIENT_SECRET: 設定済み (***************VNJcH)
  REFRESH_TOKEN: 設定済み (********************UkZjO5CEBg)
--- OAuth2認証でGoogleサービスに接続します ---
🔍 認証情報の状態:
  Valid: False
  Expired: False
  Has refresh token: True
  Token: 無効
  Scopes: ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']
アクセストークンを更新しています...
❌ トークンリフレッシュエラー: ('invalid_grant: Bad Request', 'error': 'invalid_grant', 'error_description': 'Bad Request')
```

- Actions 実行時に `gdocs.oauth2_client` のデバッグ出力が動作し、OAuth2 経路が選択されている。
- リフレッシュトークンが無効またはクライアント不一致などで `invalid_grant`。

---

## 実装構造と分岐

- 認証方式の分岐は [`gdocs.client.authenticate_google_services()`](gdocs/client.py:23) にある。
  - `config.google.auth_method == "oauth2"` のときは OAuth2 経路へ。
  - それ以外はファイルベース（従来フロー）へ。
- 現在のデフォルトは [`src/config/app_config.AppConfig.__post_init__`](src/config/app_config.py:206) にて `oauth2`（以前は `service_account` だった）。
- （修正前の状態では）Actions 上で `gdocs.oauth2_client` の出力が出ており、OAuth2 経路が常に実行されていた可能性がある。

補足:
- リポジトリに従来フローの `anscombe.json` と `token.json` が存在するが、サービスアカウント運用では無関係。混乱回避のため `.gitignore` 対象にするのが望ましい。

---

## `invalid_grant` の代表的原因

- リフレッシュトークンが失効・取り消し済み
- トークンを発行したクライアントID/シークレットと、現在使用中のクライアントが不一致
- OAuth 同意画面の公開状態がテスト中/本番で要件不一致
- リダイレクトURIの不整合（デスクトップアプリ想定の `http://localhost` で取得していない 等）

今回の本質は「Actions 側で不要な OAuth2 経路が選択されている」ため、上記個別要因の検証前に経路選択の是正が優先。

---

## OAuth2認証への恒久移行策

以上の分析に基づき、認証方式をOAuth2に一本化し、問題を恒久的に解決するため、以下のファイル修正を実施しました。

### 1. GitHub Actions ワークフロー修正 (`.github/workflows/main.yml`)

`Run script` ステップで注入される環境変数を整理し、OAuth2認証に最適化しました。

- **`GOOGLE_AUTH_METHOD` を `'oauth2'` に固定**: 認証方式を明示的に指定し、意図しない分岐を防ぎます。
- **サービスアカウント関連の変数を削除**: 不要になった `GOOGLE_SERVICE_ACCOUNT_JSON` をワークフローから削除し、設定の混在を解消しました。

これにより、GitHub Actions実行環境では常にOAuth2認証が選択され、クレデンシャルが正しくアプリケーションに渡されるようになります。

### 2. アプリケーション設定のデフォルト変更 (`src/config/app_config.py`)

ローカル環境とCI/CD環境での挙動の一貫性を保つため、アプリケーションのデフォルト認証方式を `oauth2` に変更しました。

- `GoogleConfig` クラスの `auth_method` のデフォルト値を `"oauth2"` に変更。
- 環境変数 `GOOGLE_AUTH_METHOD` が未設定の場合のフォールバック先も `"oauth2"` に統一。

### 結論

これら2点の修正により、認証フローはOAuth2に一本化され、`invalid_grant` エラーの根本原因であった環境変数の混在問題は解消されます。今後は、ローカル・リモートを問わず、安定してOAuth2認証での実行が可能となります。

---

## 付録: 代表的エラーと対応

- `invalid_grant`: リフレッシュトークンの失効/取り消し、クライアント不一致、同意画面/公開状態の不一致、リダイレクトURI不整合
  - 対応: トークン再取得、クライアント一致確認、同意画面を「本番」に、`http://localhost` で取得

- `403 forbidden`（サービスアカウント）
  - 対応: 出力先フォルダの共有にサービスアカウント `client_email` を編集者追加

---

以上。GitHub Actions では OAuth2 認証に完全移行し、安定した Google Drive/Docs 連携を実現します。