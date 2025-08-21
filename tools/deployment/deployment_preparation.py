#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Phase 4.3: 本番環境デプロイ準備とドキュメント整備
Flash+Proシステムの本番デプロイメント完全準備
"""

import os
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import subprocess
import sqlite3

class DeploymentPreparation:
    """本番デプロイメント準備クラス"""
    
    def __init__(self, project_root: str = "."):
        """初期化"""
        self.project_root = Path(project_root)
        self.deployment_report = {
            "timestamp": datetime.now().isoformat(),
            "branch": "Flash+Pro",
            "phase": "4.3",
            "checks": {},
            "documentation": {},
            "configuration": {},
            "warnings": [],
            "errors": []
        }
    
    def check_project_structure(self) -> bool:
        """プロジェクト構造の検証"""
        print("=== プロジェクト構造検証 ===")
        
        required_files = [
            "main.py",
            "requirements.txt",
            "pytest.ini",
            "ai_pro_summarizer.py",
            "article_grouper.py",
            "cost_manager.py",
            "optimized_article_grouper.py",
            "src/config/app_config.py",
            "src/database/models.py",
            "src/html/html_generator.py"
        ]
        
        required_dirs = [
            "src/",
            "src/config/",
            "src/database/",
            "src/html/",
            "tests/",
            "assets/",
            "assets/css/",
            "assets/js/"
        ]
        
        missing_files = []
        missing_dirs = []
        
        # ファイルチェック
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
                print(f"   ❌ {file_path}: 未存在")
            else:
                print(f"   ✅ {file_path}: 存在")
        
        # ディレクトリチェック
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
                print(f"   ❌ {dir_path}: 未存在")
            else:
                print(f"   ✅ {dir_path}: 存在")
        
        structure_ok = len(missing_files) == 0 and len(missing_dirs) == 0
        
        self.deployment_report["checks"]["project_structure"] = {
            "status": "pass" if structure_ok else "fail",
            "missing_files": missing_files,
            "missing_dirs": missing_dirs
        }
        
        if not structure_ok:
            self.deployment_report["errors"].append("必須ファイル・ディレクトリが不足")
        
        return structure_ok
    
    def check_dependencies(self) -> bool:
        """依存関係の検証"""
        print("=== 依存関係検証 ===")
        
        requirements_file = self.project_root / "requirements.txt"
        if not requirements_file.exists():
            print("   ❌ requirements.txt が存在しません")
            self.deployment_report["errors"].append("requirements.txt 未存在")
            return False
        
        try:
            with open(requirements_file, 'r', encoding='utf-8') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            print(f"   ✅ requirements.txt: {len(requirements)}個の依存関係")
            
            # 重要な依存関係のチェック
            critical_deps = [
                'google-generativeai',
                'google-api-python-client',
                'sqlalchemy',
                'pydantic',
                'pytest'
            ]
            
            missing_critical = []
            for dep in critical_deps:
                if not any(dep in req for req in requirements):
                    missing_critical.append(dep)
            
            if missing_critical:
                print(f"   ⚠️  重要な依存関係が不足: {missing_critical}")
                self.deployment_report["warnings"].append(f"重要な依存関係不足: {missing_critical}")
            else:
                print("   ✅ 重要な依存関係: すべて存在")
            
            self.deployment_report["checks"]["dependencies"] = {
                "status": "pass" if not missing_critical else "warning",
                "total_dependencies": len(requirements),
                "missing_critical": missing_critical
            }
            
            return True
            
        except Exception as e:
            print(f"   ❌ 依存関係チェックエラー: {e}")
            self.deployment_report["errors"].append(f"依存関係チェックエラー: {e}")
            return False
    
    def check_configuration(self) -> bool:
        """設定ファイルの検証"""
        print("=== 設定ファイル検証 ===")
        
        config_checks = []
        
        # 環境変数設定例ファイルの確認
        env_example = self.project_root / ".env.example"
        if env_example.exists():
            print("   ✅ .env.example: 存在")
            config_checks.append("env_example_exists")
        else:
            print("   ⚠️  .env.example: 未存在（推奨）")
            self.deployment_report["warnings"].append(".env.example ファイル未存在")
        
        # 設定ファイルのサンプル作成
        if not env_example.exists():
            self._create_env_example()
            print("   ✅ .env.example: 自動生成完了")
        
        # データベース設定の確認
        db_config_exists = (self.project_root / "src" / "database" / "models.py").exists()
        if db_config_exists:
            print("   ✅ データベース設定: 存在")
            config_checks.append("database_config_exists")
        
        # HTML テンプレート設定の確認
        html_config_exists = (self.project_root / "src" / "html").exists()
        if html_config_exists:
            print("   ✅ HTMLテンプレート設定: 存在")
            config_checks.append("html_config_exists")
        
        self.deployment_report["checks"]["configuration"] = {
            "status": "pass",
            "checks_passed": config_checks
        }
        
        return True
    
    def _create_env_example(self):
        """環境変数設定例ファイルの作成"""
        env_example_content = '''# Flash+Pro Market News Project - 環境変数設定例

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Google Drive & Docs API
GOOGLE_CREDENTIALS_FILE=path/to/your/google_credentials.json
GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id

# データベース設定
DATABASE_URL=sqlite:///market_news.db

# Pro統合要約設定
PRO_INTEGRATION_ENABLED=true
PRO_MAX_DAILY_EXECUTIONS=3
PRO_COST_LIMIT_MONTHLY=50.0

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=logs/market_news.log

# スクレイピング設定
SCRAPING_HOURS_LIMIT=24
SCRAPING_RETRY_COUNT=3

# HTML出力設定
HTML_OUTPUT_DIR=output/
HTML_TEMPLATE_DIR=templates/

# 本番環境設定
PRODUCTION_MODE=false
DEBUG_MODE=false
'''
        
        env_example_path = self.project_root / ".env.example"
        with open(env_example_path, 'w', encoding='utf-8') as f:
            f.write(env_example_content)
    
    def generate_deployment_docs(self) -> bool:
        """デプロイメントドキュメントの生成"""
        print("=== デプロイメントドキュメント生成 ===")
        
        docs_dir = self.project_root / "docs"
        docs_dir.mkdir(exist_ok=True)
        
        # 1. デプロイメントガイド
        self._create_deployment_guide(docs_dir)
        print("   ✅ デプロイメントガイド: 生成完了")
        
        # 2. 運用マニュアル
        self._create_operations_manual(docs_dir)
        print("   ✅ 運用マニュアル: 生成完了")
        
        # 3. API仕様書
        self._create_api_specification(docs_dir)
        print("   ✅ API仕様書: 生成完了")
        
        # 4. トラブルシューティングガイド
        self._create_troubleshooting_guide(docs_dir)
        print("   ✅ トラブルシューティングガイド: 生成完了")
        
        # 5. パフォーマンス監視ガイド
        self._create_monitoring_guide(docs_dir)
        print("   ✅ パフォーマンス監視ガイド: 生成完了")
        
        self.deployment_report["documentation"] = {
            "deployment_guide": True,
            "operations_manual": True,
            "api_specification": True,
            "troubleshooting_guide": True,
            "monitoring_guide": True
        }
        
        return True
    
    def _create_deployment_guide(self, docs_dir: Path):
        """デプロイメントガイドの作成"""
        content = '''# Flash+Pro Market News System - デプロイメントガイド

## 概要

Flash+Proブランチのマーケットニュース分析システムの本番環境デプロイメント手順書です。

## システム要件

### ハードウェア要件
- CPU: 2コア以上
- RAM: 4GB以上
- ディスク: 10GB以上の空き容量

### ソフトウェア要件
- Python 3.10以上
- SQLite 3.35以上
- Git 2.20以上

## セットアップ手順

### 1. リポジトリクローン
```bash
git clone <repository-url>
cd Market_News_Project
git checkout Flash+Pro
```

### 2. 仮想環境セットアップ
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\\Scripts\\activate  # Windows
```

### 3. 依存関係インストール
```bash
pip install -r requirements.txt
```

### 4. 環境変数設定
```bash
cp .env.example .env
# .envファイルを編集し、適切な値を設定
```

### 5. データベース初期化
```bash
python -c "from src.database.database_manager import DatabaseManager; DatabaseManager().init_database()"
```

### 6. 動作確認
```bash
python test_phase4_integration.py
```

## 本番環境固有設定

### Google APIs認証
1. Google Cloud Consoleでプロジェクト作成
2. Gemini API、Drive API、Docs APIを有効化
3. サービスアカウント作成と認証情報ダウンロード
4. 環境変数に認証情報パス設定

### Pro統合要約設定
- 日次実行回数制限: 3回
- 月間コスト上限: $50
- 実行時間帯: 9時、15時、21時（JST）

### ログ設定
- ログレベル: INFO（本番）、DEBUG（開発）
- ログローテーション: 日次、7日間保持

## 監視・メンテナンス

### 日次チェック項目
- [ ] システム稼働状況確認
- [ ] ログエラー確認
- [ ] API使用量確認
- [ ] データベース容量確認

### 週次チェック項目
- [ ] パフォーマンス指標確認
- [ ] バックアップ状況確認
- [ ] セキュリティアップデート確認

## 緊急時対応

### システム停止時
1. ログファイル確認
2. プロセス再起動
3. データベース整合性確認

### API制限到達時
1. 使用量確認
2. 一時的な処理停止
3. 制限解除まで待機

---
更新日: {date}
バージョン: Flash+Pro Phase 4.3
'''.format(date=datetime.now().strftime('%Y-%m-%d'))
        
        with open(docs_dir / "DEPLOYMENT_GUIDE.md", 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_operations_manual(self, docs_dir: Path):
        """運用マニュアルの作成"""
        content = '''# Flash+Pro Market News System - 運用マニュアル

## 日常運用

### 1. システム起動
```bash
cd Market_News_Project
source venv/bin/activate
python main.py
```

### 2. ログ監視
```bash
tail -f logs/market_news.log
```

### 3. パフォーマンス確認
```bash
python performance_optimizer.py
```

## Pro統合要約機能

### 手動実行
```bash
python -c "
from ai_pro_summarizer import ProSummarizer
from cost_manager import CostManager
# 手動実行コード
"
```

### 実行条件確認
- 記事数: 10件以上
- 日次実行回数: 3回以下
- 月間コスト: $50以下

## データベース管理

### バックアップ
```bash
sqlite3 market_news.db ".backup backup_$(date +%Y%m%d).db"
```

### クリーンアップ
```bash
python cleanup_duplicates.py
```

## トラブルシューティング

### よくある問題

#### 1. Gemini API エラー
- 原因: APIキー未設定、制限超過
- 対処: 環境変数確認、使用量確認

#### 2. Google Drive接続エラー
- 原因: 認証情報不正、権限不足
- 対処: 認証情報再設定、権限確認

#### 3. メモリ不足エラー
- 原因: 大量記事処理、メモリリーク
- 対処: バッチサイズ削減、プロセス再起動

---
更新日: {datetime.now().strftime('%Y-%m-%d')}
'''
        
        with open(docs_dir / "OPERATIONS_MANUAL.md", 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_api_specification(self, docs_dir: Path):
        """API仕様書の作成"""
        content = f'''# Flash+Pro Market News System - API仕様書

## コアAPI

### ProSummarizer API

#### 地域別要約生成
```python
from ai_pro_summarizer import ProSummarizer

summarizer = ProSummarizer(api_key="your_api_key")
regional_summaries = summarizer.generate_regional_summaries(grouped_articles)
```

**入力:**
- grouped_articles: Dict[str, List[Dict]] - 地域別グループ化された記事

**出力:**
- Dict[str, Dict] - 地域別要約結果

#### 全体要約生成
```python
global_summary = summarizer.generate_global_summary(all_articles, regional_summaries)
```

### ArticleGrouper API

#### 地域別グループ化
```python
from article_grouper import ArticleGrouper

grouper = ArticleGrouper()
grouped = grouper.group_articles_by_region(articles)
```

### CostManager API

#### コスト見積もり
```python
from cost_manager import CostManager

cost_manager = CostManager()
estimated_cost = cost_manager.estimate_cost(model_name, input_text, output_tokens)
```

## データ形式

### 記事データ形式
- title: 記事タイトル
- body: 記事本文  
- source: 情報源
- url: 記事URL
- published_at: 公開日時
- region: 地域分類
- category: カテゴリ分類

### 要約結果形式
- global_summary: 全体市況要約
- regional_summaries: 地域別要約辞書
- metadata: メタデータ（記事数など）

---
更新日: {datetime.now().strftime('%Y-%m-%d')}
'''
        
        with open(docs_dir / "API_SPECIFICATION.md", 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_troubleshooting_guide(self, docs_dir: Path):
        """トラブルシューティングガイドの作成"""
        content = f'''# Flash+Pro Market News System - トラブルシューティングガイド

## 一般的な問題と解決方法

### 1. システム起動エラー

#### 症状
```
ModuleNotFoundError: No module named 'xxx'
```

#### 原因と対処法
- **原因**: 依存関係未インストール
- **対処**: `pip install -r requirements.txt`

#### 症状
```
sqlite3.OperationalError: database is locked
```

#### 原因と対処法
- **原因**: データベースファイルロック
- **対処**: プロセス終了後、`.db-wal`, `.db-shm` ファイル削除

### 2. API関連エラー

#### Gemini API エラー
```
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded
```
- **対処**: API使用量確認、時間を置いて再実行

#### Google Drive API エラー
```
HttpError 403: Insufficient Permission
```
- **対処**: サービスアカウント権限確認、共有設定確認

### 3. パフォーマンス問題

#### 処理速度低下
- **症状**: 記事処理が異常に遅い
- **原因**: 大量データ処理、メモリ不足
- **対処**: バッチサイズ削減、メモリ監視

#### メモリ使用量増加
- **症状**: メモリ使用量が継続的に増加
- **原因**: メモリリーク、キャッシュ蓄積
- **対処**: 定期的プロセス再起動、キャッシュクリア

### 4. データ品質問題

#### 重複記事の発生
- **症状**: 同じ記事が複数回処理される
- **原因**: URL正規化不備、重複除去ロジック不備
- **対処**: `cleanup_duplicates.py` 実行

#### 地域・カテゴリ分類精度低下
- **症状**: 分類結果が不適切
- **原因**: キーワード辞書更新不足
- **対処**: キーワード辞書メンテナンス

## ログ解析

### エラーログの場所
- メインログ: `logs/market_news.log`
- エラーログ: `logs/error.log`

### 重要なログパターン
```
ERROR:root:Pro API call failed: <error_message>
WARNING:cost_manager:Monthly cost limit approaching
INFO:article_grouper:Processing 150 articles
```

## 復旧手順

### データベース復旧
1. バックアップファイルから復旧
```bash
cp backup_YYYYMMDD.db market_news.db
```

2. 整合性チェック
```bash
sqlite3 market_news.db "PRAGMA integrity_check;"
```

### 設定ファイル復旧
1. `.env.example` から `.env` 再作成
2. 環境変数値を適切に設定

## 予防保守

### 日次メンテナンス
- [ ] ログローテーション
- [ ] 一時ファイル削除
- [ ] パフォーマンス指標確認

### 週次メンテナンス
- [ ] データベースバックアップ
- [ ] システムアップデート確認
- [ ] 設定ファイル見直し

---
更新日: {datetime.now().strftime('%Y-%m-%d')}
'''
        
        with open(docs_dir / "TROUBLESHOOTING_GUIDE.md", 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_monitoring_guide(self, docs_dir: Path):
        """パフォーマンス監視ガイドの作成"""
        content = f'''# Flash+Pro Market News System - パフォーマンス監視ガイド

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
report = {{
    'date': datetime.now().date().isoformat(),
    'articles_processed': 0,
    'api_calls': 0,
    'errors': 0,
    'cost': 0.0
}}
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
更新日: {datetime.now().strftime('%Y-%m-%d')}
'''
        
        with open(docs_dir / "MONITORING_GUIDE.md", 'w', encoding='utf-8') as f:
            f.write(content)
    
    def create_deployment_checklist(self) -> bool:
        """デプロイメントチェックリスト生成"""
        print("=== デプロイメントチェックリスト生成 ===")
        
        checklist = {
            "pre_deployment": {
                "code_review": False,
                "unit_tests": False,
                "integration_tests": False,
                "performance_tests": False,
                "security_review": False
            },
            "deployment": {
                "backup_creation": False,
                "environment_setup": False,
                "database_migration": False,
                "configuration_verification": False,
                "service_deployment": False
            },
            "post_deployment": {
                "smoke_tests": False,
                "monitoring_setup": False,
                "log_verification": False,
                "performance_verification": False,
                "rollback_plan": False
            }
        }
        
        checklist_file = self.project_root / "DEPLOYMENT_CHECKLIST.md"
        with open(checklist_file, 'w', encoding='utf-8') as f:
            f.write("# Flash+Pro Market News System - デプロイメントチェックリスト\n\n")
            f.write(f"作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"ブランチ: Flash+Pro\n\n")
            
            for phase, items in checklist.items():
                f.write(f"## {phase.replace('_', ' ').title()}\n\n")
                for item, status in items.items():
                    checkbox = "☑️" if status else "☐"
                    f.write(f"- {checkbox} {item.replace('_', ' ').title()}\n")
                f.write("\n")
        
        print("   ✅ デプロイメントチェックリスト: 生成完了")
        return True
    
    def generate_final_report(self) -> Dict[str, Any]:
        """最終デプロイメントレポート生成"""
        print("=" * 60)
        print("Flash+Pro Phase 4.3: 本番デプロイ準備完了レポート")
        print("=" * 60)
        print(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"ブランチ: Flash+Pro")
        print()
        
        # 全体的な準備状況評価
        total_checks = len(self.deployment_report["checks"])
        passed_checks = sum(1 for check in self.deployment_report["checks"].values() 
                           if check.get("status") == "pass")
        
        readiness_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        print("準備状況サマリー:")
        print(f"  チェック項目: {passed_checks}/{total_checks} 完了")
        print(f"  準備度スコア: {readiness_score:.1f}%")
        print()
        
        # 詳細結果
        print("詳細チェック結果:")
        for check_name, result in self.deployment_report["checks"].items():
            status_icon = "✅" if result["status"] == "pass" else ("⚠️" if result["status"] == "warning" else "❌")
            print(f"  {status_icon} {check_name}: {result['status']}")
        print()
        
        # ドキュメント生成状況
        print("ドキュメント生成状況:")
        doc_count = sum(1 for status in self.deployment_report["documentation"].values() if status)
        total_docs = len(self.deployment_report["documentation"])
        print(f"  生成完了: {doc_count}/{total_docs}個")
        print()
        
        # 警告・エラー
        if self.deployment_report["warnings"]:
            print("⚠️  警告:")
            for warning in self.deployment_report["warnings"]:
                print(f"  - {warning}")
            print()
        
        if self.deployment_report["errors"]:
            print("❌ エラー:")
            for error in self.deployment_report["errors"]:
                print(f"  - {error}")
            print()
        
        # 最終判定
        if readiness_score >= 90 and not self.deployment_report["errors"]:
            print("✅ デプロイ準備完了: 本番環境へのデプロイが可能です")
            deployment_ready = True
        elif readiness_score >= 75:
            print("⚠️  デプロイ準備ほぼ完了: 軽微な修正後にデプロイ可能")
            deployment_ready = True
        else:
            print("❌ デプロイ準備未完了: 追加の作業が必要です")
            deployment_ready = False
        
        # レポートファイル保存
        report_file = self.project_root / f"deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.deployment_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 詳細レポート: {report_file}")
        
        return {
            "ready": deployment_ready,
            "score": readiness_score,
            "report_file": str(report_file)
        }

def main():
    """メインデプロイ準備実行"""
    print("Flash+Pro Phase 4.3: 本番デプロイメント準備開始")
    print("=" * 60)
    
    deployment_prep = DeploymentPreparation()
    
    # 各準備ステップ実行
    success_steps = 0
    total_steps = 5
    
    if deployment_prep.check_project_structure():
        success_steps += 1
    print()
    
    if deployment_prep.check_dependencies():
        success_steps += 1
    print()
    
    if deployment_prep.check_configuration():
        success_steps += 1
    print()
    
    if deployment_prep.generate_deployment_docs():
        success_steps += 1
    print()
    
    if deployment_prep.create_deployment_checklist():
        success_steps += 1
    print()
    
    # 最終レポート生成
    final_report = deployment_prep.generate_final_report()
    
    return final_report["ready"]

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nデプロイ準備中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n予期しないエラー: {e}")
        sys.exit(1)