from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from market_data.schema import Candle
from market_data.tradingview import candle_from_mapping, _time

@dataclass(frozen=True)
class ChartEvidence:
    symbol: str
    captured_at: datetime
    timeframes_present: tuple[str, ...]
    candles: tuple[Candle, ...]
    observations: tuple[str, ...]
    confidence: str
    missing: tuple[str, ...]

def evidence_from_payload(payload: dict[str, Any]) -> ChartEvidence:
    candles=tuple(candle_from_mapping(c, str(c.get("timeframe", payload.get("timeframe", "")))) for c in payload.get("candles", []))
    required=("H4", "H1", "M15", "M5")
    present=tuple(sorted({c.timeframe for c in candles}))
    missing=tuple(tf for tf in required if tf not in present)
    confidence="SUFFICIENT" if not missing else "INSUFFICIENT"
    return ChartEvidence(str(payload.get("symbol", "UNKNOWN")), _time(payload.get("captured_at", payload.get("timestamp"))), present, candles, tuple(str(x) for x in payload.get("observations", [])), confidence, missing)
