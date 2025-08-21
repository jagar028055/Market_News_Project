# -*- coding: utf-8 -*-

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class CostRecord:
    """コスト記録データクラス"""
    timestamp: str
    model_name: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    operation_type: str  # "regional_summary", "global_summary"
    session_id: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CostRecord':
        return cls(**data)


class CostManager:
    """Pro API使用コスト管理クラス"""
    
    # Gemini Pro価格設定（USD per token）
    GEMINI_PRO_PRICING = {
        "gemini-2.5-pro": {
            "input": 0.00000125,   # $0.00000125 per input token
            "output": 0.000005     # $0.000005 per output token
        }
    }
    
    def __init__(self, database_path: str = None):
        """
        初期化
        
        Args:
            database_path (str): コスト管理用データベースファイルパス
        """
        self.logger = logging.getLogger(__name__)
        
        if database_path is None:
            database_path = os.path.join(os.getcwd(), "cost_tracking.db")
        
        self.database_path = database_path
        self._init_database()
    
    def _init_database(self):
        """コスト管理用データベースの初期化"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # コスト記録テーブル作成
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cost_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        model_name TEXT NOT NULL,
                        input_tokens INTEGER NOT NULL,
                        output_tokens INTEGER NOT NULL,
                        cost_usd REAL NOT NULL,
                        operation_type TEXT NOT NULL,
                        session_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # インデックス作成
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON cost_records(timestamp)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_model_operation 
                    ON cost_records(model_name, operation_type)
                ''')
                
                conn.commit()
                self.logger.info(f"コスト管理データベース初期化完了: {self.database_path}")
                
        except Exception as e:
            self.logger.error(f"コスト管理データベース初期化エラー: {e}")
            raise
    
    def estimate_cost(self, model_name: str, input_text: str, 
                      estimated_output_tokens: int = 1000) -> float:
        """
        API使用コストの事前見積もり
        
        Args:
            model_name (str): 使用するモデル名
            input_text (str): 入力テキスト
            estimated_output_tokens (int): 予想出力トークン数
        
        Returns:
            float: 推定コスト（USD）
        """
        if model_name not in self.GEMINI_PRO_PRICING:
            self.logger.warning(f"未知のモデル: {model_name}, デフォルト価格を使用")
            pricing = self.GEMINI_PRO_PRICING["gemini-2.5-pro"]
        else:
            pricing = self.GEMINI_PRO_PRICING[model_name]
        
        # 入力トークン数の推定（大まかに1トークン=4文字として計算）
        input_tokens = len(input_text) // 4
        
        # コスト計算
        input_cost = input_tokens * pricing["input"]
        output_cost = estimated_output_tokens * pricing["output"]
        total_cost = input_cost + output_cost
        
        self.logger.debug(f"コスト見積もり - モデル: {model_name}, "
                         f"入力: {input_tokens}トークン, 出力: {estimated_output_tokens}トークン, "
                         f"合計: ${total_cost:.6f}")
        
        return total_cost
    
    def record_cost(self, model_name: str, input_tokens: int, output_tokens: int, 
                   operation_type: str, session_id: Optional[int] = None) -> float:
        """
        API使用コストを記録
        
        Args:
            model_name (str): 使用したモデル名
            input_tokens (int): 実際の入力トークン数
            output_tokens (int): 実際の出力トークン数
            operation_type (str): 操作タイプ
            session_id (Optional[int]): セッションID
        
        Returns:
            float: 実際のコスト（USD）
        """
        if model_name not in self.GEMINI_PRO_PRICING:
            self.logger.warning(f"未知のモデル: {model_name}, デフォルト価格を使用")
            pricing = self.GEMINI_PRO_PRICING["gemini-2.5-pro"]
        else:
            pricing = self.GEMINI_PRO_PRICING[model_name]
        
        # コスト計算
        input_cost = input_tokens * pricing["input"]
        output_cost = output_tokens * pricing["output"]
        total_cost = input_cost + output_cost
        
        # 記録をデータベースに保存
        timestamp = datetime.utcnow().isoformat()
        
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO cost_records 
                    (timestamp, model_name, input_tokens, output_tokens, cost_usd, operation_type, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, model_name, input_tokens, output_tokens, total_cost, operation_type, session_id))
                
                conn.commit()
                
                self.logger.info(f"コスト記録完了 - モデル: {model_name}, "
                               f"入力: {input_tokens}トークン, 出力: {output_tokens}トークン, "
                               f"コスト: ${total_cost:.6f}, 操作: {operation_type}")
                
        except Exception as e:
            self.logger.error(f"コスト記録エラー: {e}")
            
        return total_cost
    
    def get_monthly_cost(self, year: int = None, month: int = None) -> float:
        """
        月間コストを取得
        
        Args:
            year (int): 対象年（Noneの場合は今年）
            month (int): 対象月（Noneの場合は今月）
        
        Returns:
            float: 月間コスト（USD）
        """
        now = datetime.now()
        target_year = year or now.year
        target_month = month or now.month
        
        # 月の最初と最後の日付
        start_date = datetime(target_year, target_month, 1)
        if target_month == 12:
            end_date = datetime(target_year + 1, 1, 1)
        else:
            end_date = datetime(target_year, target_month + 1, 1)
        
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT SUM(cost_usd) 
                    FROM cost_records 
                    WHERE timestamp >= ? AND timestamp < ?
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                result = cursor.fetchone()
                monthly_cost = result[0] if result[0] is not None else 0.0
                
                self.logger.debug(f"月間コスト取得: {target_year}/{target_month:02d} = ${monthly_cost:.6f}")
                return monthly_cost
                
        except Exception as e:
            self.logger.error(f"月間コスト取得エラー: {e}")
            return 0.0
    
    def get_daily_cost(self, date: datetime = None) -> float:
        """
        日別コストを取得
        
        Args:
            date (datetime): 対象日（Noneの場合は今日）
        
        Returns:
            float: 日別コスト（USD）
        """
        target_date = date or datetime.now()
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT SUM(cost_usd) 
                    FROM cost_records 
                    WHERE timestamp >= ? AND timestamp < ?
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                result = cursor.fetchone()
                daily_cost = result[0] if result[0] is not None else 0.0
                
                return daily_cost
                
        except Exception as e:
            self.logger.error(f"日別コスト取得エラー: {e}")
            return 0.0
    
    def check_cost_limits(self, monthly_limit: float = 50.0, daily_limit: float = 5.0) -> Dict[str, bool]:
        """
        コスト制限チェック
        
        Args:
            monthly_limit (float): 月間制限（USD）
            daily_limit (float): 日間制限（USD）
        
        Returns:
            Dict[str, bool]: 制限チェック結果
        """
        monthly_cost = self.get_monthly_cost()
        daily_cost = self.get_daily_cost()
        
        result = {
            "monthly_ok": monthly_cost < monthly_limit,
            "daily_ok": daily_cost < daily_limit,
            "monthly_usage": monthly_cost,
            "daily_usage": daily_cost,
            "monthly_limit": monthly_limit,
            "daily_limit": daily_limit,
            "monthly_remaining": max(0, monthly_limit - monthly_cost),
            "daily_remaining": max(0, daily_limit - daily_cost)
        }
        
        if not result["monthly_ok"]:
            self.logger.warning(f"月間コスト制限超過: ${monthly_cost:.6f} >= ${monthly_limit:.2f}")
        
        if not result["daily_ok"]:
            self.logger.warning(f"日間コスト制限超過: ${daily_cost:.6f} >= ${daily_limit:.2f}")
        
        return result
    
    def get_cost_statistics(self, days: int = 30) -> Dict[str, any]:
        """
        コスト統計情報を取得
        
        Args:
            days (int): 対象期間（日数）
        
        Returns:
            Dict[str, any]: 統計情報
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # 総コスト
                cursor.execute('''
                    SELECT SUM(cost_usd), COUNT(*), AVG(cost_usd)
                    FROM cost_records 
                    WHERE timestamp >= ?
                ''', (start_date.isoformat(),))
                
                total_cost, total_operations, avg_cost = cursor.fetchone()
                
                # 操作タイプ別統計
                cursor.execute('''
                    SELECT operation_type, SUM(cost_usd), COUNT(*)
                    FROM cost_records 
                    WHERE timestamp >= ?
                    GROUP BY operation_type
                ''', (start_date.isoformat(),))
                
                operation_stats = {}
                for op_type, cost, count in cursor.fetchall():
                    operation_stats[op_type] = {
                        "cost": cost,
                        "count": count,
                        "avg_cost": cost / count if count > 0 else 0
                    }
                
                # モデル別統計
                cursor.execute('''
                    SELECT model_name, SUM(cost_usd), COUNT(*)
                    FROM cost_records 
                    WHERE timestamp >= ?
                    GROUP BY model_name
                ''', (start_date.isoformat(),))
                
                model_stats = {}
                for model, cost, count in cursor.fetchall():
                    model_stats[model] = {
                        "cost": cost,
                        "count": count,
                        "avg_cost": cost / count if count > 0 else 0
                    }
                
                return {
                    "period_days": days,
                    "total_cost": total_cost or 0.0,
                    "total_operations": total_operations or 0,
                    "avg_cost_per_operation": avg_cost or 0.0,
                    "operation_stats": operation_stats,
                    "model_stats": model_stats,
                    "monthly_cost": self.get_monthly_cost(),
                    "daily_cost": self.get_daily_cost()
                }
                
        except Exception as e:
            self.logger.error(f"コスト統計取得エラー: {e}")
            return {}
    
    def export_cost_records(self, start_date: datetime = None, end_date: datetime = None) -> List[CostRecord]:
        """
        コスト記録をエクスポート
        
        Args:
            start_date (datetime): 開始日
            end_date (datetime): 終了日
        
        Returns:
            List[CostRecord]: コスト記録のリスト
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()
        
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, model_name, input_tokens, output_tokens, cost_usd, operation_type, session_id
                    FROM cost_records 
                    WHERE timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp DESC
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                records = []
                for row in cursor.fetchall():
                    record = CostRecord(
                        timestamp=row[0],
                        model_name=row[1],
                        input_tokens=row[2],
                        output_tokens=row[3],
                        cost_usd=row[4],
                        operation_type=row[5],
                        session_id=row[6]
                    )
                    records.append(record)
                
                self.logger.info(f"コスト記録エクスポート完了: {len(records)}件")
                return records
                
        except Exception as e:
            self.logger.error(f"コスト記録エクスポートエラー: {e}")
            return []


def check_pro_cost_limits(config: Dict[str, any] = None) -> bool:
    """
    Pro API使用前のコスト制限チェック
    
    Args:
        config (Dict): 設定（monthly_limit, daily_limitを含む）
    
    Returns:
        bool: 実行可能かどうか
    """
    logger = logging.getLogger(__name__)
    
    if config is None:
        config = {"monthly_limit": 50.0, "daily_limit": 5.0}
    
    try:
        cost_manager = CostManager()
        limits_check = cost_manager.check_cost_limits(
            monthly_limit=config.get("monthly_limit", 50.0),
            daily_limit=config.get("daily_limit", 5.0)
        )
        
        if not limits_check["monthly_ok"]:
            logger.error(f"月間コスト制限に達しています: "
                        f"${limits_check['monthly_usage']:.6f} / ${limits_check['monthly_limit']:.2f}")
            return False
        
        if not limits_check["daily_ok"]:
            logger.error(f"日間コスト制限に達しています: "
                        f"${limits_check['daily_usage']:.6f} / ${limits_check['daily_limit']:.2f}")
            return False
        
        logger.info(f"コスト制限OK - 月間: ${limits_check['monthly_remaining']:.6f}残り, "
                   f"日間: ${limits_check['daily_remaining']:.6f}残り")
        return True
        
    except Exception as e:
        logger.error(f"コスト制限チェックエラー: {e}")
        return False


if __name__ == '__main__':
    # テスト用コード
    logging.basicConfig(level=logging.INFO)
    
    print("=== コスト管理テスト ===")
    
    # コストマネージャー初期化
    cost_manager = CostManager("test_cost_tracking.db")
    
    # テストコスト記録
    test_cost = cost_manager.record_cost(
        model_name="gemini-2.5-pro",
        input_tokens=1500,
        output_tokens=800,
        operation_type="global_summary",
        session_id=123
    )
    print(f"記録されたコスト: ${test_cost:.6f}")
    
    # コスト制限チェック
    limits_check = cost_manager.check_cost_limits(monthly_limit=50.0, daily_limit=5.0)
    print(f"\nコスト制限チェック:")
    print(f"  月間OK: {limits_check['monthly_ok']} (${limits_check['monthly_usage']:.6f} / ${limits_check['monthly_limit']:.2f})")
    print(f"  日間OK: {limits_check['daily_ok']} (${limits_check['daily_usage']:.6f} / ${limits_check['daily_limit']:.2f})")
    
    # 統計情報
    stats = cost_manager.get_cost_statistics(days=7)
    print(f"\n統計情報 (過去7日間):")
    print(f"  総コスト: ${stats['total_cost']:.6f}")
    print(f"  操作回数: {stats['total_operations']}")
    print(f"  平均コスト: ${stats['avg_cost_per_operation']:.6f}")
    
    # テストファイル削除
    import os
    try:
        os.remove("test_cost_tracking.db")
        print("\nテストデータベース削除完了")
    except FileNotFoundError:
        pass