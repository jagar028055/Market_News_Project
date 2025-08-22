"""
A/Bテスト管理システム

このモジュールは配信メッセージのA/Bテスト実行と結果分析を提供します。
"""

import uuid
import sqlite3
import logging
import datetime
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import statistics
from .analytics_engine import AnalyticsEngine
from .metrics_collector import MetricsCollector


class TestStatus(Enum):
    """テストステータス"""

    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TestType(Enum):
    """テストタイプ"""

    MESSAGE_CONTENT = "message_content"
    MESSAGE_FORMAT = "message_format"
    DELIVERY_TIME = "delivery_time"
    IMAGE_VARIANT = "image_variant"


@dataclass
class TestVariant:
    """テストバリアント"""

    variant_id: str
    variant_name: str
    variant_config: Dict[str, Any]
    allocated_percentage: float
    participant_count: int = 0


@dataclass
class ABTest:
    """A/Bテスト定義"""

    test_id: str
    test_name: str
    test_type: TestType
    description: str
    variants: List[TestVariant]
    start_time: datetime.datetime
    end_time: datetime.datetime
    status: TestStatus
    success_metric: str
    minimum_sample_size: int
    metadata: Dict[str, Any]


@dataclass
class TestResult:
    """テスト結果"""

    test_id: str
    variant_id: str
    participant_count: int
    success_count: int
    success_rate: float
    avg_engagement_score: float
    statistical_significance: Optional[float]


class ABTestManager:
    """A/Bテスト管理システム"""

    def __init__(self, analytics_engine: Optional[AnalyticsEngine] = None):
        self.analytics = analytics_engine or AnalyticsEngine()
        self.logger = logging.getLogger(__name__)
        self._init_test_database()

    def _init_test_database(self):
        """A/Bテスト用データベース初期化"""
        with sqlite3.connect(self.analytics.db_path) as conn:
            # A/Bテスト定義テーブル
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ab_tests (
                    test_id TEXT PRIMARY KEY,
                    test_name TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    description TEXT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    status TEXT NOT NULL,
                    success_metric TEXT NOT NULL,
                    minimum_sample_size INTEGER NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # テストバリアントテーブル
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_variants (
                    variant_id TEXT PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    variant_name TEXT NOT NULL,
                    variant_config TEXT NOT NULL,
                    allocated_percentage REAL NOT NULL,
                    participant_count INTEGER DEFAULT 0,
                    FOREIGN KEY (test_id) REFERENCES ab_tests(test_id)
                )
            """
            )

            # テスト参加者テーブル
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_participants (
                    participant_id TEXT PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    variant_id TEXT NOT NULL,
                    user_id TEXT,
                    episode_id TEXT NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (test_id) REFERENCES ab_tests(test_id),
                    FOREIGN KEY (variant_id) REFERENCES test_variants(variant_id)
                )
            """
            )

            # テスト結果テーブル
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_results (
                    result_id TEXT PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    variant_id TEXT NOT NULL,
                    participant_count INTEGER NOT NULL,
                    success_count INTEGER NOT NULL,
                    success_rate REAL NOT NULL,
                    avg_engagement_score REAL NOT NULL,
                    statistical_significance REAL,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (test_id) REFERENCES ab_tests(test_id),
                    FOREIGN KEY (variant_id) REFERENCES test_variants(variant_id)
                )
            """
            )

            # インデックス作成
            conn.execute("CREATE INDEX IF NOT EXISTS idx_test_status ON ab_tests(status)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_participants ON test_participants(test_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results ON test_results(test_id)")

    def create_test(
        self,
        test_name: str,
        test_type: TestType,
        variants: List[Dict[str, Any]],
        description: str = "",
        duration_days: int = 7,
        success_metric: str = "engagement_rate",
        minimum_sample_size: int = 100,
    ) -> str:
        """A/Bテスト作成"""
        test_id = str(uuid.uuid4())
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(days=duration_days)

        try:
            # バリアント作成
            test_variants = []
            total_percentage = 0

            for i, variant_config in enumerate(variants):
                variant_id = str(uuid.uuid4())
                percentage = variant_config.get("percentage", 100 / len(variants))
                total_percentage += percentage

                test_variants.append(
                    TestVariant(
                        variant_id=variant_id,
                        variant_name=variant_config.get("name", f"Variant {chr(65+i)}"),
                        variant_config=variant_config.get("config", {}),
                        allocated_percentage=percentage,
                    )
                )

            if abs(total_percentage - 100) > 0.1:
                raise ValueError(f"バリアント配分の合計が100%ではありません: {total_percentage}%")

            # データベースに保存
            with sqlite3.connect(self.analytics.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO ab_tests 
                    (test_id, test_name, test_type, description, start_time, end_time, 
                     status, success_metric, minimum_sample_size, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        test_id,
                        test_name,
                        test_type.value,
                        description,
                        start_time.isoformat(),
                        end_time.isoformat(),
                        TestStatus.DRAFT.value,
                        success_metric,
                        minimum_sample_size,
                        json.dumps({"created_by": "system"}),
                    ),
                )

                for variant in test_variants:
                    conn.execute(
                        """
                        INSERT INTO test_variants
                        (variant_id, test_id, variant_name, variant_config, allocated_percentage)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            variant.variant_id,
                            test_id,
                            variant.variant_name,
                            json.dumps(variant.variant_config),
                            variant.allocated_percentage,
                        ),
                    )

            self.logger.info(f"A/Bテスト作成: {test_id} - {test_name}")
            return test_id

        except Exception as e:
            self.logger.error(f"A/Bテスト作成エラー: {e}")
            raise

    def start_test(self, test_id: str) -> bool:
        """A/Bテスト開始"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                # テスト存在確認
                test_exists = conn.execute(
                    """
                    SELECT COUNT(*) FROM ab_tests WHERE test_id = ? AND status = 'draft'
                """,
                    (test_id,),
                ).fetchone()[0]

                if not test_exists:
                    self.logger.warning(f"開始可能なテストが見つかりません: {test_id}")
                    return False

                # ステータス更新
                conn.execute(
                    """
                    UPDATE ab_tests SET status = 'running' WHERE test_id = ?
                """,
                    (test_id,),
                )

                self.logger.info(f"A/Bテスト開始: {test_id}")
                return True

        except Exception as e:
            self.logger.error(f"A/Bテスト開始エラー: {e}")
            return False

    def assign_user_to_variant(self, test_id: str, user_id: str, episode_id: str) -> Optional[str]:
        """ユーザーをバリアントに割り当て"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                # 実行中のテスト確認
                test_info = conn.execute(
                    """
                    SELECT test_name, status, end_time FROM ab_tests WHERE test_id = ?
                """,
                    (test_id,),
                ).fetchone()

                if not test_info or test_info[1] != "running":
                    return None

                # テスト終了確認
                if datetime.datetime.now() > datetime.datetime.fromisoformat(test_info[2]):
                    self._complete_test(test_id)
                    return None

                # 既存の割り当て確認
                existing_assignment = conn.execute(
                    """
                    SELECT variant_id FROM test_participants 
                    WHERE test_id = ? AND user_id = ?
                """,
                    (test_id, user_id),
                ).fetchone()

                if existing_assignment:
                    return existing_assignment[0]

                # バリアント取得
                variants = conn.execute(
                    """
                    SELECT variant_id, allocated_percentage 
                    FROM test_variants WHERE test_id = ?
                    ORDER BY allocated_percentage DESC
                """,
                    (test_id,),
                ).fetchall()

                # ランダム割り当て
                random_value = random.uniform(0, 100)
                cumulative_percentage = 0
                selected_variant = None

                for variant_id, percentage in variants:
                    cumulative_percentage += percentage
                    if random_value <= cumulative_percentage:
                        selected_variant = variant_id
                        break

                if not selected_variant:
                    selected_variant = variants[0][0]  # フォールバック

                # 参加者記録
                participant_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO test_participants 
                    (participant_id, test_id, variant_id, user_id, episode_id)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (participant_id, test_id, selected_variant, user_id, episode_id),
                )

                # バリアント参加者数更新
                conn.execute(
                    """
                    UPDATE test_variants 
                    SET participant_count = participant_count + 1 
                    WHERE variant_id = ?
                """,
                    (selected_variant,),
                )

                self.logger.info(f"ユーザー割り当て: {user_id} -> {selected_variant}")
                return selected_variant

        except Exception as e:
            self.logger.error(f"バリアント割り当てエラー: {e}")
            return None

    def get_variant_config(self, test_id: str, variant_id: str) -> Optional[Dict[str, Any]]:
        """バリアント設定取得"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                config_data = conn.execute(
                    """
                    SELECT variant_config FROM test_variants 
                    WHERE test_id = ? AND variant_id = ?
                """,
                    (test_id, variant_id),
                ).fetchone()

                if config_data:
                    return json.loads(config_data[0])
                return None

        except Exception as e:
            self.logger.error(f"バリアント設定取得エラー: {e}")
            return None

    def complete_test(self, test_id: str) -> bool:
        """A/Bテスト完了"""
        try:
            return self._complete_test(test_id)
        except Exception as e:
            self.logger.error(f"A/Bテスト完了エラー: {e}")
            return False

    def _complete_test(self, test_id: str) -> bool:
        """内部：A/Bテスト完了処理"""
        with sqlite3.connect(self.analytics.db_path) as conn:
            # テスト結果計算
            self._calculate_test_results(test_id)

            # ステータス更新
            conn.execute(
                """
                UPDATE ab_tests SET status = 'completed' WHERE test_id = ?
            """,
                (test_id,),
            )

            self.logger.info(f"A/Bテスト完了: {test_id}")
            return True

    def _calculate_test_results(self, test_id: str):
        """テスト結果計算"""
        with sqlite3.connect(self.analytics.db_path) as conn:
            # バリアント別統計
            variants = conn.execute(
                """
                SELECT variant_id, variant_name 
                FROM test_variants WHERE test_id = ?
            """,
                (test_id,),
            ).fetchall()

            test_results = []
            for variant_id, variant_name in variants:
                # 参加者統計
                participant_stats = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as participant_count,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM test_participants 
                    WHERE test_id = ? AND variant_id = ?
                """,
                    (test_id, variant_id),
                ).fetchone()

                participant_count = participant_stats[0]

                if participant_count == 0:
                    continue

                # エンゲージメント統計（参加者のエピソードに対する行動）
                engagement_stats = conn.execute(
                    """
                    SELECT 
                        COUNT(DISTINCT ee.user_id) as engaged_users,
                        AVG(CASE WHEN ee.event_type = 'click' THEN 2
                                WHEN ee.event_type = 'share' THEN 3  
                                WHEN ee.event_type = 'subscribe' THEN 5
                                ELSE 1 END) as avg_engagement_score
                    FROM test_participants tp
                    JOIN engagement_events ee ON tp.user_id = ee.user_id AND tp.episode_id = ee.episode_id
                    WHERE tp.test_id = ? AND tp.variant_id = ?
                """,
                    (test_id, variant_id),
                ).fetchone()

                engaged_users = engagement_stats[0] or 0
                avg_engagement_score = engagement_stats[1] or 0.0
                success_rate = (engaged_users / participant_count) * 100

                # 結果保存
                result_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO test_results 
                    (result_id, test_id, variant_id, participant_count, success_count,
                     success_rate, avg_engagement_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        result_id,
                        test_id,
                        variant_id,
                        participant_count,
                        engaged_users,
                        success_rate,
                        avg_engagement_score,
                    ),
                )

                test_results.append(
                    TestResult(
                        test_id=test_id,
                        variant_id=variant_id,
                        participant_count=participant_count,
                        success_count=engaged_users,
                        success_rate=success_rate,
                        avg_engagement_score=avg_engagement_score,
                        statistical_significance=None,
                    )
                )

            # 統計的有意性計算
            self._calculate_statistical_significance(test_id, test_results)

    def _calculate_statistical_significance(self, test_id: str, results: List[TestResult]):
        """統計的有意性計算（簡易版）"""
        if len(results) < 2:
            return

        try:
            # 最も成績の良い2つのバリアントを比較
            results_sorted = sorted(results, key=lambda x: x.success_rate, reverse=True)
            best_result = results_sorted[0]
            second_result = results_sorted[1]

            # Z検定による有意性計算（簡易版）
            p1 = best_result.success_rate / 100
            p2 = second_result.success_rate / 100
            n1 = best_result.participant_count
            n2 = second_result.participant_count

            if n1 < 30 or n2 < 30:  # サンプルサイズが小さい場合はスキップ
                return

            # プールされた比率
            p_pool = (best_result.success_count + second_result.success_count) / (n1 + n2)

            # 標準誤差
            se = (p_pool * (1 - p_pool) * (1 / n1 + 1 / n2)) ** 0.5

            if se == 0:
                return

            # Z値
            z_score = abs(p1 - p2) / se

            # p値推定（簡易版）
            if z_score >= 2.58:
                p_value = 0.01  # 99% 信頼
            elif z_score >= 1.96:
                p_value = 0.05  # 95% 信頼
            elif z_score >= 1.64:
                p_value = 0.10  # 90% 信頼
            else:
                p_value = 0.50  # 有意差なし

            # 結果更新
            with sqlite3.connect(self.analytics.db_path) as conn:
                conn.execute(
                    """
                    UPDATE test_results 
                    SET statistical_significance = ? 
                    WHERE test_id = ? AND variant_id = ?
                """,
                    (p_value, test_id, best_result.variant_id),
                )

        except Exception as e:
            self.logger.error(f"統計的有意性計算エラー: {e}")

    def get_test_results(self, test_id: str) -> Dict[str, Any]:
        """テスト結果取得"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                # テスト情報
                test_info = conn.execute(
                    """
                    SELECT test_name, test_type, description, status, start_time, end_time
                    FROM ab_tests WHERE test_id = ?
                """,
                    (test_id,),
                ).fetchone()

                if not test_info:
                    return {}

                # バリアント結果
                results = conn.execute(
                    """
                    SELECT 
                        tv.variant_name,
                        tr.variant_id,
                        tr.participant_count,
                        tr.success_count,
                        tr.success_rate,
                        tr.avg_engagement_score,
                        tr.statistical_significance
                    FROM test_results tr
                    JOIN test_variants tv ON tr.variant_id = tv.variant_id
                    WHERE tr.test_id = ?
                    ORDER BY tr.success_rate DESC
                """,
                    (test_id,),
                ).fetchall()

                variant_results = []
                for row in results:
                    variant_results.append(
                        {
                            "variant_name": row[0],
                            "variant_id": row[1],
                            "participant_count": row[2],
                            "success_count": row[3],
                            "success_rate": row[4],
                            "avg_engagement_score": row[5],
                            "statistical_significance": row[6],
                            "is_winner": row == results[0] if results else False,
                        }
                    )

                return {
                    "test_id": test_id,
                    "test_name": test_info[0],
                    "test_type": test_info[1],
                    "description": test_info[2],
                    "status": test_info[3],
                    "start_time": test_info[4],
                    "end_time": test_info[5],
                    "variant_results": variant_results,
                    "total_participants": sum(r["participant_count"] for r in variant_results),
                    "analysis_date": datetime.datetime.now().isoformat(),
                }

        except Exception as e:
            self.logger.error(f"テスト結果取得エラー: {e}")
            return {}

    def get_active_tests(self) -> List[Dict[str, Any]]:
        """実行中テスト一覧取得"""
        try:
            with sqlite3.connect(self.analytics.db_path) as conn:
                tests = conn.execute(
                    """
                    SELECT test_id, test_name, test_type, start_time, end_time
                    FROM ab_tests 
                    WHERE status = 'running'
                    ORDER BY start_time DESC
                """
                ).fetchall()

                return [
                    {
                        "test_id": test[0],
                        "test_name": test[1],
                        "test_type": test[2],
                        "start_time": test[3],
                        "end_time": test[4],
                    }
                    for test in tests
                ]

        except Exception as e:
            self.logger.error(f"アクティブテスト取得エラー: {e}")
            return []
