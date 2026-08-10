"""Strict normalization for future webhook/data-provider events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


_SYMBOL_MAP = {"TVC:GOLD": "XAUUSD", "FX:EURUSD": "EURUSD"}


@dataclass(frozen=True)
class NormalizedEvent:
    event_type: str
    instrument: str
    source_symbol: str
    timeframe: str
    timestamp: datetime
    payload: Mapping[str, object]


def normalize_event(payload: Mapping[str, object], *, allowed_symbols: set[str]) -> NormalizedEvent:
    required = ("event", "symbol", "timeframe", "timestamp")
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    source_symbol = str(payload["symbol"])
    if source_symbol not in allowed_symbols:
        raise ValueError(f"symbol not allowed: {source_symbol}")
    if source_symbol not in _SYMBOL_MAP:
        raise ValueError(f"unsupported symbol: {source_symbol}")

    try:
        timestamp = datetime.fromisoformat(str(payload["timestamp"]))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must include timezone")

    event_type = str(payload["event"]).upper().replace("-", "_")
    if event_type == "ZONE_HIT":
        normalized_type = event_type
    elif event_type in {"LIQUIDITY_SWEEP", "CONFIRMATION", "INVALIDATED"}:
        normalized_type = event_type
    else:
        raise ValueError(f"unsupported event: {event_type}")

    return NormalizedEvent(
        event_type=normalized_type,
        instrument=_SYMBOL_MAP[source_symbol],
        source_symbol=source_symbol,
        timeframe=str(payload["timeframe"]).upper(),
        timestamp=timestamp,
        payload=dict(payload),
    )
