"""
Economic Indicators Trend Analyzer
経済指標トレンド分析器

簡易的なトレンド分析器
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass


class TrendType(Enum):
    """トレンドタイプ"""
    BULL = "強気"  # 強い上昇トレンド
    BEAR = "弱気"  # 強い下降トレンド
    SIDEWAYS = "横ばい"  # 横ばいトレンド
    VOLATILE = "変動激しい"  # 高ボラティリティ
    CYCLE = "循環的"  # 循環パターン
    BREAKOUT = "ブレイクアウト"  # レンジブレイク
    REVERSAL = "反転"  # トレンド反転


class PatternType(Enum):
    """パターンタイプ"""
    HEAD_SHOULDERS = "三尊"
    DOUBLE_TOP = "ダブルトップ"
    DOUBLE_BOTTOM = "ダブルボトム"
    TRIANGLE = "三角持ち合い"
    CHANNEL = "チャネル"
    SUPPORT_RESISTANCE = "サポート・レジスタンス"
    NONE = "パターンなし"


@dataclass
class TrendResult:
    """トレンド分析結果"""
    trend_type: TrendType
    confidence_level: float
    pattern_type: PatternType
    pattern_confidence: float
    slope: float
    r_squared: float
    support_levels: List[float]
    resistance_levels: List[float]
    breakout_probability: float
    reversal_probability: float
