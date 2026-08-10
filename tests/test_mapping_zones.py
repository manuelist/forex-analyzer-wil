from datetime import datetime, timezone

from market_data.schema import Candle
from analysis.mapping import build_market_map, phase_for
from analysis.zones import (
    BreakType,
    ZoneKind,
    ZoneStatus,
    detect_zones,
    merge_zones,
    update_zone,
)


def c(i, close, high=None, low=None, tf="H1"):
    return Candle(datetime(2026, 1, 1 + i, tzinfo=timezone.utc), tf, close - .2, high or close + .5, low or close - .5, close)


def test_zone_mapping_detects_and_merges_support_resistance():
    candles = [c(0, 100, 101, 99), c(1, 105, 106, 104), c(2, 100, 101, 99), c(3, 105, 106, 104), c(4, 100, 101, 99)]
    zones = detect_zones(candles, window=1)
    merged = merge_zones(zones)
    assert any(z.kind == ZoneKind.SUPPORT for z in merged)
    assert any(z.kind == ZoneKind.RESISTANCE for z in merged)
    assert all(z.strength >= 1 for z in merged)


def test_zone_lifecycle_distinguishes_wick_break_close_break_and_invalidation():
    zone = detect_zones([c(0, 100, 101, 99), c(1, 105, 106, 104), c(2, 100, 101, 99)], window=1)[0]
    wick = update_zone(zone, c(3, 100, zone.high + 1, zone.low), tolerance=0.0)
    assert wick.last_break == BreakType.WICK
    closed = update_zone(wick, c(4, zone.high + 2, zone.high + 2.5, zone.high + 1), tolerance=0.0)
    assert closed.last_break == BreakType.CLOSE
    assert closed.status == ZoneStatus.INVALID


def test_mapping_interprets_h1_bullish_inside_h4_bearish_as_pullback():
    h4 = [c(i, 110 - i, tf="H4") for i in range(6)]
    h1 = [c(i, 100 + i, tf="H1") for i in range(6)]
    result = build_market_map({"H4": h4, "H1": h1})
    assert result.phase == "PULLBACK"
    assert phase_for("BEARISH", "BULLISH") == "PULLBACK"
    assert result.premium_discount in {"PREMIUM", "DISCOUNT", "EQUILIBRIUM"}


def test_mapping_waits_when_required_timeframe_missing():
    result = build_market_map({"H4": [c(i, 100 + i, tf="H4") for i in range(5)]})
    assert result.phase == "INSUFFICIENT_DATA"
    assert "H1" in result.missing
