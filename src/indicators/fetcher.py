# -*- coding: utf-8 -*-

"""
主要指標フェッチャー（Stooqを利用）

出力フォーマット（例）:
[
  {"name":"日経平均","value":"42,828.79","change":"+520.65","pct":"+1.23%"},
  {"name":"TOPIX","value":"3,089.78","change":"+28.98","pct":"+0.95%"},
]
"""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from typing import List, Dict, Optional
import requests


STOOQ_URL = "https://stooq.com/q/l/"


@dataclass
class Symbol:
    code: str
    label: str
    fmt: str = ",.2f"


SYMBOLS: List[Symbol] = [
    Symbol("^nkx", "日経平均", ",.2f"),
    Symbol("^tpx", "TOPIX", ",.2f"),
    Symbol("^spx", "S&P500", ",.2f"),
    Symbol("^ndx", "NASDAQ100", ",.2f"),
    Symbol("usdjpy", "USD/JPY", ",.3f"),
    Symbol("cl.f", "WTI原油", ",.2f"),
    Symbol("xauusd", "金(XAU/USD)", ",.2f"),
]


def _fmt(val: float, fmt: str) -> str:
    return format(val, fmt)


def _sign(val: float) -> str:
    if val > 0:
        return "+"
    if val < 0:
        return "-"
    return ""


def fetch_indicators() -> List[Dict[str, str]]:
    data = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for sym in SYMBOLS:
        params = {
            "s": sym.code,
            "f": "sd2t2ohlcvn",
            "h": "",
            "e": "csv",
        }
        r = requests.get(STOOQ_URL, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        try:
            row = next(reader)
        except StopIteration:
            row = {}
        close = _to_float(row.get("Close"))
        if close is None or _is_nd(row.get("Date")):
            # データなし
            data.append({
                "name": sym.label,
                "value": "—",
                "change": "—",
                "pct": "—",
            })
            continue

        # 前日終値比（取得できなければ当日始値比）
        prev_close = _fetch_prev_close(sym.code)
        if prev_close is not None and prev_close != 0:
            ch = close - prev_close
            pct = (ch / prev_close) * 100
        else:
            open_ = _to_float(row.get("Open")) or 0.0
            ch = close - open_
            pct = (ch / open_) * 100 if open_ != 0 else 0.0
        sign = _sign(ch)

        value_s = _fmt(close, sym.fmt)
        change_s = f"{sign}{_fmt(abs(ch), sym.fmt)}"
        pct_s = f"{sign}{_fmt(abs(pct), ',.2f')}%"

        # 通貨ペア/コモディティ向けの小数調整は fmt で対応済み
        data.append({
            "name": sym.label,
            "value": value_s,
            "change": change_s,
            "pct": pct_s,
        })

    return data


def _to_float(x):
    try:
        return float(x)
    except Exception:
        return None


def _is_nd(x: str | None) -> bool:
    return (x or "").strip().upper() in {"N/D", "ND", ""}


def _fetch_prev_close(symbol: str) -> Optional[float]:
    """Stooqの日次CSVから前日終値を取得。失敗時はNone。"""
    try:
        url = "https://stooq.com/q/d/l/"
        params = {"s": symbol, "i": "d"}
        r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        rows = [row for row in reader if not _is_nd(row.get("Date"))]
        if len(rows) < 2:
            return None
        prev = rows[-2]
        return _to_float(prev.get("Close"))
    except Exception:
        return None
