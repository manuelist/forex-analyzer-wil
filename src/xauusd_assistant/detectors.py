"""Deterministic candle detectors; no network or broker dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Swing:
    index: int
    kind: str
    price: float
    timestamp: datetime


@dataclass(frozen=True)
class StructureEvent:
    kind: str
    direction: str
    index: int
    broken_price: float
    timestamp: datetime


@dataclass(frozen=True)
class FairValueGap:
    direction: str
    index: int
    low: float
    high: float
    timestamp: datetime


def _as_list(candles: Iterable[Candle]) -> list[Candle]:
    return list(candles)


def detect_swings(candles: Iterable[Candle], *, window: int = 2) -> list[Swing]:
    values = _as_list(candles)
    if window < 1 or len(values) < (window * 2 + 1):
        return []
    result: list[Swing] = []
    for index in range(window, len(values) - window):
        current = values[index]
        left = values[index - window:index]
        right = values[index + 1:index + window + 1]
        if current.high > max(candle.high for candle in (*left, *right)):
            result.append(Swing(index, "HIGH", current.high, current.timestamp))
        if current.low < min(candle.low for candle in (*left, *right)):
            result.append(Swing(index, "LOW", current.low, current.timestamp))
    return result


def detect_structure_break(
    candles: Iterable[Candle], *, window: int = 2
) -> StructureEvent | None:
    values = _as_list(candles)
    if len(values) < (window * 2 + 2):
        return None
    swings = detect_swings(values[:-1], window=window)
    if not swings:
        return None
    last = values[-1]
    highs = [s for s in swings if s.kind == "HIGH"]
    lows = [s for s in swings if s.kind == "LOW"]
    if highs and last.close > highs[-1].price:
        return StructureEvent("BOS", "BULLISH", len(values) - 1, highs[-1].price, last.timestamp)
    if lows and last.close < lows[-1].price:
        return StructureEvent("BOS", "BEARISH", len(values) - 1, lows[-1].price, last.timestamp)
    return None


def detect_fvg(candles: Iterable[Candle]) -> list[FairValueGap]:
    values = _as_list(candles)
    gaps: list[FairValueGap] = []
    for index in range(2, len(values)):
        first, _, third = values[index - 2:index + 1]
        if third.low > first.high:
            gaps.append(FairValueGap("BULLISH", index, first.high, third.low, third.timestamp))
        elif third.high < first.low:
            gaps.append(FairValueGap("BEARISH", index, third.high, first.low, third.timestamp))
    return gaps


def classify_market_condition(*, structure_break_directions: Sequence[str]) -> str:
    directions = list(structure_break_directions)
    if len(directions) < 3:
        return "INSUFFICIENT_EVENTS"
    if len(set(directions[-4:])) > 1 and directions[-4:] in (["BULLISH", "BEARISH", "BULLISH", "BEARISH"], ["BEARISH", "BULLISH", "BEARISH", "BULLISH"]):
        return "WHIPSAW"
    if directions[-1] == directions[-2] == directions[-3]:
        return "DIRECTIONAL"
    return "TRANSITIONING"
