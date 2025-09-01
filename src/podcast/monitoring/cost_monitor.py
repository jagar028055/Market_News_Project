"""TTS使用量とコスト監視機能"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path
from dataclasses import dataclass, asdict

from ...config.app_config import AppConfig


logger = logging.getLogger(__name__)


@dataclass
class TTSUsageRecord:
    """TTS使用記録"""

    timestamp: datetime
    character_count: int
    model_name: str
    estimated_cost: float
    episode_id: Optional[str] = None
    processing_stage: Optional[str] = None


@dataclass
class CostSummary:
    """コストサマリー"""

    current_month_total: float
    current_day_total: float
    tts_character_count: int
    estimated_remaining_budget: float
    days_remaining_in_month: int
    average_daily_cost: float
    projected_month_end_cost: float


class CostMonitor:
    """TTS使用量とコスト監視クラス"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.podcast_config = config.podcast

        # コスト設定
        self.monthly_limit = self.podcast_config.monthly_cost_limit  # $10
        self.tts_cost_per_character = 0.000016  # Gemini TTS料金（仮）

        # 使用記録保存パス
        self.usage_log_path = Path(self.podcast_config.cost_monitor_dir) / "tts_usage.json"
        self.usage_log_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用記録ロード
        self.usage_records = self._load_usage_records()

    def track_tts_usage(
        self,
        character_count: int,
        model_name: str = "gemini-tts",
        episode_id: Optional[str] = None,
        processing_stage: Optional[str] = None,
    ) -> None:
        """TTS使用量を記録

        Args:
            character_count: 処理文字数
            model_name: 使用モデル名
            episode_id: エピソードID
            processing_stage: 処理段階
        """
        try:
            estimated_cost = character_count * self.tts_cost_per_character

            usage_record = TTSUsageRecord(
                timestamp=datetime.now(),
                character_count=character_count,
                model_name=model_name,
                estimated_cost=estimated_cost,
                episode_id=episode_id,
                processing_stage=processing_stage,
            )

            self.usage_records.append(usage_record)
            self._save_usage_records()

            logger.info(f"TTS usage tracked: {character_count} chars, ${estimated_cost:.4f}")

            # コスト警告チェック
            self._check_cost_warnings()

        except Exception as e:
            logger.error(f"TTS usage tracking failed: {e}")

    def get_current_month_costs(self) -> Dict[str, float]:
        """今月のコスト使用状況を取得"""
        try:
            now = datetime.now()
            month_start = datetime(now.year, now.month, 1)

            monthly_records = [
                record for record in self.usage_records if record.timestamp >= month_start
            ]

            total_cost = sum(record.estimated_cost for record in monthly_records)
            total_characters = sum(record.character_count for record in monthly_records)

            return {
                "total": total_cost,
                "characters": total_characters,
                "records_count": len(monthly_records),
                "remaining_budget": max(0, self.monthly_limit - total_cost),
            }

        except Exception as e:
            logger.error(f"Current month costs calculation failed: {e}")
            return {
                "total": 0,
                "characters": 0,
                "records_count": 0,
                "remaining_budget": self.monthly_limit,
            }

    def get_current_day_costs(self) -> Dict[str, float]:
        """今日のコスト使用状況を取得"""
        try:
            today = datetime.now().date()

            daily_records = [
                record for record in self.usage_records if record.timestamp.date() == today
            ]

            total_cost = sum(record.estimated_cost for record in daily_records)
            total_characters = sum(record.character_count for record in daily_records)

            return {
                "total": total_cost,
                "characters": total_characters,
                "records_count": len(daily_records),
            }

        except Exception as e:
            logger.error(f"Current day costs calculation failed: {e}")
            return {"total": 0, "characters": 0, "records_count": 0}

    def estimate_episode_cost(self, estimated_characters: Optional[int] = None) -> float:
        """エピソード生成の予想コストを計算

        Args:
            estimated_characters: 予想文字数（Noneの場合は過去の平均を使用）

        Returns:
            float: 予想コスト
        """
        try:
            if estimated_characters is None:
                # 過去のエピソードの平均文字数を使用
                estimated_characters = self._get_average_episode_characters()

            estimated_cost = estimated_characters * self.tts_cost_per_character

            # マージンを追加（20%）
            estimated_cost *= 1.2

            return estimated_cost

        except Exception as e:
            logger.error(f"Episode cost estimation failed: {e}")
            return 1.0  # デフォルト値

    def _get_average_episode_characters(self) -> int:
        """過去のエピソードの平均文字数を取得"""
        try:
            episode_records = [
                record for record in self.usage_records if record.episode_id is not None
            ]

            if not episode_records:
                # デフォルト値（設定の目標文字数の中央値）
                target_min, target_max = self.podcast_config.target_character_count
                return (target_min + target_max) // 2

            # エピソード別の文字数合計を計算
            episode_chars = {}
            for record in episode_records:
                if record.episode_id not in episode_chars:
                    episode_chars[record.episode_id] = 0
                episode_chars[record.episode_id] += record.character_count

            if episode_chars:
                return int(sum(episode_chars.values()) / len(episode_chars))
            else:
                target_min, target_max = self.podcast_config.target_character_count
                return (target_min + target_max) // 2

        except Exception as e:
            logger.error(f"Average episode characters calculation failed: {e}")
            return 2600  # デフォルト値

    def get_cost_summary(self) -> CostSummary:
        """詳細なコストサマリーを取得"""
        try:
            monthly_costs = self.get_current_month_costs()
            daily_costs = self.get_current_day_costs()

            now = datetime.now()
            days_in_month = (datetime(now.year, now.month + 1, 1) - timedelta(days=1)).day
            days_remaining = days_in_month - now.day + 1

            # 平均日次コスト計算
            days_elapsed = now.day
            average_daily_cost = monthly_costs["total"] / max(1, days_elapsed)

            # 月末予想コスト
            projected_month_end_cost = average_daily_cost * days_in_month

            return CostSummary(
                current_month_total=monthly_costs["total"],
                current_day_total=daily_costs["total"],
                tts_character_count=monthly_costs["characters"],
                estimated_remaining_budget=monthly_costs["remaining_budget"],
                days_remaining_in_month=days_remaining,
                average_daily_cost=average_daily_cost,
                projected_month_end_cost=projected_month_end_cost,
            )

        except Exception as e:
            logger.error(f"Cost summary calculation failed: {e}")
            return CostSummary(
                current_month_total=0.0,
                current_day_total=0.0,
                tts_character_count=0,
                estimated_remaining_budget=self.monthly_limit,
                days_remaining_in_month=30,
                average_daily_cost=0.0,
                projected_month_end_cost=0.0,
            )

    def _check_cost_warnings(self) -> None:
        """コスト警告チェック"""
        try:
            monthly_costs = self.get_current_month_costs()
            cost_summary = self.get_cost_summary()

            # 月間制限の90%に達した場合
            if monthly_costs["total"] >= self.monthly_limit * 0.9:
                logger.warning(
                    f"Cost approaching monthly limit: ${monthly_costs['total']:.2f} / ${self.monthly_limit:.2f}"
                )

            # 月末予想コストが制限を超える場合
            if cost_summary.projected_month_end_cost > self.monthly_limit:
                logger.warning(
                    f"Projected month-end cost exceeds limit: ${cost_summary.projected_month_end_cost:.2f}"
                )

            # 1日の使用量が異常に高い場合
            daily_costs = self.get_current_day_costs()
            expected_daily_limit = self.monthly_limit / 30  # 月間を30日で割った値
            if daily_costs["total"] > expected_daily_limit * 2:
                logger.warning(f"Daily cost unusually high: ${daily_costs['total']:.2f}")

        except Exception as e:
            logger.error(f"Cost warning check failed: {e}")

    def cleanup_old_records(self, months: int = 3) -> None:
        """古い使用記録をクリーンアップ

        Args:
            months: 保持期間（月数）
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=months * 30)

            old_count = len(self.usage_records)
            self.usage_records = [
                record for record in self.usage_records if record.timestamp > cutoff_date
            ]
            new_count = len(self.usage_records)

            if old_count != new_count:
                self._save_usage_records()
                logger.info(f"Cleaned up {old_count - new_count} old usage records")

        except Exception as e:
            logger.error(f"Usage records cleanup failed: {e}")

    def get_usage_trend(self, days: int = 30) -> Dict:
        """使用量トレンド分析

        Args:
            days: 分析期間（日数）

        Returns:
            Dict: トレンド情報
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_records = [
                record for record in self.usage_records if record.timestamp > cutoff_date
            ]

            if not recent_records:
                return {"trend": "no_data"}

            # 日別集計
            daily_costs = {}
            for record in recent_records:
                date_key = record.timestamp.date()
                if date_key not in daily_costs:
                    daily_costs[date_key] = 0
                daily_costs[date_key] += record.estimated_cost

            # トレンド計算（簡易実装）
            sorted_dates = sorted(daily_costs.keys())
            if len(sorted_dates) >= 7:
                recent_avg = sum(daily_costs[date] for date in sorted_dates[-7:]) / 7
                previous_avg = sum(daily_costs[date] for date in sorted_dates[-14:-7]) / 7

                if recent_avg > previous_avg * 1.1:
                    trend = "increasing"
                elif recent_avg < previous_avg * 0.9:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"

            return {
                "trend": trend,
                "daily_costs": {str(k): v for k, v in daily_costs.items()},
                "total_records": len(recent_records),
                "total_cost": sum(record.estimated_cost for record in recent_records),
            }

        except Exception as e:
            logger.error(f"Usage trend analysis failed: {e}")
            return {"trend": "error"}

    def _load_usage_records(self) -> List[TTSUsageRecord]:
        """使用記録をファイルから読み込み"""
        try:
            if not self.usage_log_path.exists():
                return []

            with open(self.usage_log_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            records = []
            for record_data in data:
                # datetime文字列をdatetimeオブジェクトに変換
                record_data["timestamp"] = datetime.fromisoformat(record_data["timestamp"])
                records.append(TTSUsageRecord(**record_data))

            logger.info(f"Loaded {len(records)} usage records")
            return records

        except Exception as e:
            logger.error(f"Usage records loading failed: {e}")
            return []

    def _save_usage_records(self) -> None:
        """使用記録をファイルに保存"""
        try:
            data = []
            for record in self.usage_records:
                record_dict = asdict(record)
                # datetimeオブジェクトを文字列に変換
                record_dict["timestamp"] = record.timestamp.isoformat()
                data.append(record_dict)

            with open(self.usage_log_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Usage records saving failed: {e}")

    def export_usage_report(self, month: Optional[int] = None, year: Optional[int] = None) -> Dict:
        """使用量レポート出力

        Args:
            month: 月（Noneの場合は今月）
            year: 年（Noneの場合は今年）

        Returns:
            Dict: レポートデータ
        """
        try:
            now = datetime.now()
            target_month = month or now.month
            target_year = year or now.year

            month_start = datetime(target_year, target_month, 1)
            if target_month == 12:
                month_end = datetime(target_year + 1, 1, 1) - timedelta(seconds=1)
            else:
                month_end = datetime(target_year, target_month + 1, 1) - timedelta(seconds=1)

            month_records = [
                record
                for record in self.usage_records
                if month_start <= record.timestamp <= month_end
            ]

            report = {
                "period": f"{target_year}-{target_month:02d}",
                "total_cost": sum(record.estimated_cost for record in month_records),
                "total_characters": sum(record.character_count for record in month_records),
                "total_records": len(month_records),
                "episodes_processed": len(set(r.episode_id for r in month_records if r.episode_id)),
                "average_cost_per_episode": 0,
                "daily_breakdown": {},
            }

            if report["episodes_processed"] > 0:
                report["average_cost_per_episode"] = (
                    report["total_cost"] / report["episodes_processed"]
                )

            # 日別内訳
            for record in month_records:
                date_key = record.timestamp.strftime("%Y-%m-%d")
                if date_key not in report["daily_breakdown"]:
                    report["daily_breakdown"][date_key] = {"cost": 0, "characters": 0, "records": 0}
                report["daily_breakdown"][date_key]["cost"] += record.estimated_cost
                report["daily_breakdown"][date_key]["characters"] += record.character_count
                report["daily_breakdown"][date_key]["records"] += 1

            return report

        except Exception as e:
            logger.error(f"Usage report export failed: {e}")
            return {"error": str(e)}
