"""Deterministic support/resistance zone mapping and lifecycle."""
from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum
from market_data.schema import Candle

class ZoneKind(str, Enum):
    SUPPORT = "SUPPORT"
    RESISTANCE = "RESISTANCE"
    RANGE = "RANGE"

class ZoneStatus(str, Enum):
    ACTIVE = "ACTIVE"
    TESTED = "TESTED"
    INVALID = "INVALID"

class BreakType(str, Enum):
    NONE = "NONE"
    WICK = "WICK"
    CLOSE = "CLOSE"

@dataclass(frozen=True)
class Zone:
    kind: ZoneKind
    low: float
    high: float
    source_index: int
    touches: int = 0
    strength: int = 1
    status: ZoneStatus = ZoneStatus.ACTIVE
    last_break: BreakType = BreakType.NONE
    retests: int = 0

    @property
    def midpoint(self) -> float:
        return (self.low + self.high) / 2

def _zone(kind: ZoneKind, candle: Candle, index: int) -> Zone:
    return Zone(kind, candle.low, candle.high, index)

def detect_zones(candles: list[Candle], window: int = 1) -> list[Zone]:
    if len(candles) < 2 * window + 1:
        return []
    found: list[Zone] = []
    for i in range(window, len(candles) - window):
        current = candles[i]
        before = candles[i-window:i]
        after = candles[i+1:i+window+1]
        if current.low <= min(x.low for x in before + after):
            found.append(_zone(ZoneKind.SUPPORT, current, i))
        if current.high >= max(x.high for x in before + after):
            found.append(_zone(ZoneKind.RESISTANCE, current, i))
    return found

def merge_zones(zones: list[Zone], tolerance: float = 0.001) -> list[Zone]:
    result: list[Zone] = []
    for zone in sorted(zones, key=lambda z: (z.kind.value, z.low, z.high)):
        merged = False
        for i, existing in enumerate(result):
            overlap = zone.low <= existing.high * (1 + tolerance) and zone.high >= existing.low * (1 - tolerance)
            if existing.kind == zone.kind and overlap:
                result[i] = replace(existing, low=min(existing.low, zone.low), high=max(existing.high, zone.high), touches=existing.touches + zone.touches + 1, strength=existing.strength + zone.strength)
                merged = True
                break
        if not merged:
            result.append(zone)
    return sorted(result, key=lambda z: z.low)

def update_zone(zone: Zone, candle: Candle, tolerance: float = 0.0) -> Zone:
    if zone.status == ZoneStatus.INVALID:
        return zone
    if zone.kind == ZoneKind.RESISTANCE:
        wicked = candle.high > zone.high * (1 + tolerance) and candle.close <= zone.high
        closed = candle.close > zone.high * (1 + tolerance)
    elif zone.kind == ZoneKind.SUPPORT:
        wicked = candle.low < zone.low * (1 - tolerance) and candle.close >= zone.low
        closed = candle.close < zone.low * (1 - tolerance)
    else:
        wicked = closed = False
    if closed:
        return replace(zone, status=ZoneStatus.INVALID, last_break=BreakType.CLOSE)
    if wicked:
        return replace(zone, status=ZoneStatus.TESTED, last_break=BreakType.WICK, touches=zone.touches + 1, retests=zone.retests + 1)
    inside = zone.low <= candle.close <= zone.high
    if inside:
        return replace(zone, status=ZoneStatus.TESTED, touches=zone.touches + 1, retests=zone.retests + 1)
    return zone

def zone_contains(zone: Zone, price: float) -> bool:
    return zone.low <= price <= zone.high
