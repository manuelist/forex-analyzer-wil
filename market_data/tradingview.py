from __future__ import annotations
import csv, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .schema import Candle, TradingViewEvent

def _time(value: Any) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

def candle_from_mapping(row: dict[str, Any], timeframe: str) -> Candle:
    return Candle(_time(row["timestamp"] if "timestamp" in row else row["time"]), timeframe, float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]), float(row["volume"]) if row.get("volume") not in (None, "") else None, bool(row.get("closed", True)))

def parse_event(payload: dict[str, Any]) -> TradingViewEvent:
    candles = tuple(candle_from_mapping(c, str(payload.get("timeframe", ""))) for c in payload.get("candles", []))
    return TradingViewEvent(str(payload["event"]), str(payload["symbol"]), str(payload["timeframe"]), _time(payload["timestamp"]), float(payload["price"]) if payload.get("price") is not None else None, candles, payload)

def load_csv(path: str | Path, timeframe: str) -> list[Candle]:
    with Path(path).open(newline="") as fh:
        return [candle_from_mapping(row, timeframe) for row in csv.DictReader(fh)]

def parse_json(text: str) -> TradingViewEvent:
    return parse_event(json.loads(text))
