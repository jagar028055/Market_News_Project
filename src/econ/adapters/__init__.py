
"""Economic data adapters."""

from .investpy_calendar import InvestpyCalendarAdapter
from .fmp_calendar import FMPCalendarAdapter
from .fred_adapter import FredAdapter
from .ecb_adapter import EcbAdapter

__all__ = [
    'InvestpyCalendarAdapter', 
    'FMPCalendarAdapter',
    'FredAdapter',
    'EcbAdapter'
]