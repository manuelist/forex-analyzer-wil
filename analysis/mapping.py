"""Multi-timeframe market mapping without hidden or invented data."""
from __future__ import annotations
from dataclasses import dataclass
from analysis.structure import classify
from analysis.zones import Zone, detect_zones, merge_zones
from market_data.schema import Candle

@dataclass(frozen=True)
class MarketMap:
    trends: dict[str, str]
    phase: str
    premium_discount: str
    zones: tuple[Zone, ...]
    missing: tuple[str, ...]

def phase_for(h4: str, h1: str) -> str:
    if h4 == "UNKNOWN" or h1 == "UNKNOWN": return "INSUFFICIENT_DATA"
    if h4 == h1 and h4 in {"BULLISH", "BEARISH"}: return "CONTINUATION"
    if h4 == "BEARISH" and h1 == "BULLISH": return "PULLBACK"
    if h4 == "BULLISH" and h1 == "BEARISH": return "PULLBACK"
    if "TRANSITIONING" in {h4, h1}: return "TRANSITION"
    return "RANGE"

def _pd(h4: list[Candle], reference: float | None) -> str:
    if not h4 or reference is None: return "UNKNOWN"
    low=min(c.low for c in h4); high=max(c.high for c in h4); midpoint=(low+high)/2
    span=high-low
    if span == 0: return "EQUILIBRIUM"
    if reference > midpoint + span*0.05: return "PREMIUM"
    if reference < midpoint - span*0.05: return "DISCOUNT"
    return "EQUILIBRIUM"

def build_market_map(timeframes: dict[str, list[Candle]]) -> MarketMap:
    required=("H4", "H1")
    missing=tuple(tf for tf in required if not timeframes.get(tf))
    trends={tf: classify(cs) if cs else "UNKNOWN" for tf, cs in timeframes.items()}
    h4=trends.get("H4", "UNKNOWN"); h1=trends.get("H1", "UNKNOWN")
    phase="INSUFFICIENT_DATA" if missing else phase_for(h4, h1)
    ref=(timeframes.get("H1") or timeframes.get("H4") or [None])[-1]
    reference=ref.close if ref else None
    zones=[]
    for candles in timeframes.values(): zones.extend(detect_zones(candles))
    return MarketMap(trends, phase, _pd(timeframes.get("H4", []), reference), tuple(merge_zones(zones)), missing)
