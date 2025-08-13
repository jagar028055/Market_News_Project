# Flash+Pro Market News System - パフォーマンス監視ガイド

## 監視対象指標

### 1. システムパフォーマンス
- CPU使用率
- メモリ使用量
- ディスク容量
- 処理時間

### 2. API使用状況
- Gemini API呼び出し回数
- API応答時間
- エラー率
- コスト使用量

### 3. データ品質
- 記事処理件数
- 重複記事率
- 分類精度
- エラー発生率

## 監視ツール

### パフォーマンス測定
```bash
python performance_optimizer.py
```

### コスト監視
```bash
python -c "
from cost_manager import CostManager
cm = CostManager()
print(cm.get_monthly_usage())
"
```

### システム統計
```bash
python -c "
from optimized_article_grouper import OptimizedArticleGrouper
oag = OptimizedArticleGrouper()
print(oag.get_cache_stats())
"
```

## アラート設定

### 閾値設定
- CPU使用率: 80%以上で警告
- メモリ使用量: 90%以上で警告
- 月間API コスト: $45以上で警告
- エラー率: 5%以上で警告

### 通知方法
- ログファイルアラート
- システム通知
- メール通知（設定時）

## ダッシュボード

### KPI監視項目
1. **処理効率**
   - 1時間あたりの記事処理数
   - 平均処理時間
   - エラー率

2. **リソース使用量**
   - CPU・メモリ使用量トレンド
   - ディスク使用量
   - ネットワーク使用量

3. **品質指標**
   - 記事分類精度
   - 重複除去率
   - 要約品質スコア

## レポート生成

### 日次レポート
```bash
python -c "
import json
from datetime import datetime

# 日次統計の収集と出力
report = {
    'date': datetime.now().date().isoformat(),
    'articles_processed': 0,
    'api_calls': 0,
    'errors': 0,
    'cost': 0.0
}
print(json.dumps(report, indent=2))
"
```

### 週次レポート
- パフォーマンストレンド分析
- コスト使用量サマリー
- システム健全性評価

## 最適化推奨事項

### パフォーマンス改善
1. キャッシュサイズの調整
2. バッチ処理サイズの最適化
3. データベースインデックスの追加

### コスト最適化
1. API呼び出し頻度の調整
2. 不要な処理の削減
3. 効率的なプロンプト設計

---
更新日: 2025-08-13
