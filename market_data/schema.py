from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    closed: bool = True

@dataclass(frozen=True)
class TradingViewEvent:
    event: str
    symbol: str
    timeframe: str
    timestamp: datetime
    price: float | None
    candles: tuple[Candle, ...] = ()
    raw: dict[str, Any] | None = None
