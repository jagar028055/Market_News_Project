"""
Economic Indicators Data Processor
経済指標データプロセッサ

簡易的なデータプロセッサ
"""

from typing import Optional, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass


class TrendDirection(Enum):
    """トレンド方向"""
    UP = "上昇"
    DOWN = "下降" 
    FLAT = "横ばい"
    VOLATILE = "不安定"
    UNKNOWN = "不明"


@dataclass
class ProcessedIndicator:
    """処理済み指標"""
    original_event: Any
    historical_data: Optional[Any] = None
    data_quality_score: float = 0.0
    mom_change: float = 0.0
    yoy_change: float = 0.0
    z_score: float = 0.0
    trend_direction: TrendDirection = TrendDirection.UNKNOWN
    volatility_index: float = 0.0
