from datetime import datetime, timedelta, timezone

from xauusd_assistant.detectors import (
    Candle,
    detect_swings,
    detect_structure_break,
    detect_fvg,
    classify_market_condition,
)


def make_candles(values):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        Candle(
            timestamp=base + timedelta(minutes=i),
            open=value,
            high=value + 1,
            low=value - 1,
            close=value,
        )
        for i, value in enumerate(values)
    ]


def test_detects_swing_high_and_low():
    candles = make_candles([100, 103, 99, 101, 98, 102])
    swings = detect_swings(candles, window=1)
    assert any(item.kind == "HIGH" and item.price == 104 for item in swings)
    assert any(item.kind == "LOW" and item.price == 98 for item in swings)


def test_detects_bullish_structure_break_from_closed_candle():
    candles = make_candles([100, 103, 99, 101, 98, 105])
    event = detect_structure_break(candles, window=1)
    assert event is not None
    assert event.direction == "BULLISH"
    assert event.kind == "BOS"


def test_detects_bullish_fvg():
    candles = make_candles([100, 102, 105])
    gaps = detect_fvg(candles)
    assert len(gaps) == 1
    assert gaps[0].direction == "BULLISH"
    assert gaps[0].low == 101
    assert gaps[0].high == 104


def test_classifies_alternating_breaks_as_whipsaw():
    condition = classify_market_condition(
        structure_break_directions=["BULLISH", "BEARISH", "BULLISH", "BEARISH"]
    )
    assert condition == "WHIPSAW"
