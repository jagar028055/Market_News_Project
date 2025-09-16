# Supabase連携修正ガイド

## 📋 修正内容サマリー

GitHubアクションでのSupabase連携を完全に修正するために、以下の変更を実施しました。

### ✅ 実施済み修正

1. **依存関係の修正**
   - `requirements.txt`に`supabase>=2.0.0`と`sentence-transformers>=2.2.0`を追加
   - コメントアウトされていたパッケージを有効化

2. **GitHubアクション環境変数の追加**
   - `main.yml`にSupabase関連の環境変数を追加:
     ```yaml
     SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
     SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
     SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
     SUPABASE_ENABLED: 'true'
     SUPABASE_BUCKET: 'market-news-archive'
     ```

3. **データベーススキーマの修正**
   - `chunks`テーブルに不足していたカラムを追加:
     - `category`, `region`, `source`, `url`, `chunk_no`
   - RLSポリシーを改善（サービスロールとアノニマスアクセス対応）

4. **テストスクリプトの作成**
   - `scripts/test_supabase_integration.py`でSupabase連携をテスト
   - GitHubアクションにテストステップを追加

## 🔧 必要な手動設定

### 1. GitHub Secretsの設定

GitHubリポジトリのSettings > Secrets and variables > Actionsで以下を設定:

```
SUPABASE_URL: https://your-project.supabase.co
SUPABASE_ANON_KEY: your-anon-key
SUPABASE_SERVICE_ROLE_KEY: your-service-role-key
```

### 2. Supabaseデータベースの更新

SupabaseダッシュボードのSQL Editorで以下を実行:

```sql
-- 更新されたスキーマファイルを実行
-- scripts/supabase_rag_setup.sql
```

### 3. ストレージバケットの確認

SupabaseダッシュボードのStorageで以下を確認:
- バケット名: `market-news-archive`
- 公開設定: `false` (プライベート)
- RLSポリシーが適用されているか

## 🧪 テスト方法

### ローカルテスト

```bash
# 環境変数設定
export SUPABASE_URL="your-url"
export SUPABASE_ANON_KEY="your-key"
export SUPABASE_SERVICE_ROLE_KEY="your-service-key"
export SUPABASE_ENABLED="true"

# テスト実行
python scripts/test_supabase_integration.py
```

### GitHubアクションでのテスト

1. リポジトリにプッシュ
2. Actions タブでワークフロー実行を確認
3. "Test Supabase Integration"ステップの結果を確認

## 📊 期待される結果

### 成功時のログ

```
🔧 Supabase連携テスト開始
✅ Supabase設定確認成功
✅ Supabase接続テスト成功
✅ Supabase操作テスト成功
🎉 Supabase連携テスト: 全て成功!
```

### 失敗時の対処

1. **設定エラー**: GitHub Secretsの確認
2. **接続エラー**: Supabase URLとAPIキーの確認
3. **権限エラー**: RLSポリシーの確認
4. **スキーマエラー**: データベーススキーマの再実行

## 🚀 次のステップ

1. **本番環境でのテスト**: GitHubアクションの手動実行
2. **RAG機能の活用**: 記事のアーカイブと検索機能のテスト
3. **監視設定**: Supabase使用量とエラーログの監視
4. **パフォーマンス最適化**: インデックスとクエリの最適化

## 📞 トラブルシューティング

### よくある問題

1. **"No module named 'supabase'"**
   - `pip install -r requirements.txt`を実行

2. **"new row violates row-level security policy"**
   - SupabaseダッシュボードでRLSポリシーを確認
   - サービスロールキーが正しく設定されているか確認

3. **"Could not find the 'category' column"**
   - データベーススキーマを再実行
   - `scripts/supabase_rag_setup.sql`をSupabaseで実行

4. **GitHubアクションで環境変数が未設定**
   - リポジトリのSecrets設定を確認
   - 環境変数名のスペルミスを確認

---

**修正完了日**: 2025年1月12日  
**修正者**: AI Assistant  
**テスト状況**: 準備完了（手動テスト待ち）
