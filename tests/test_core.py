from datetime import datetime, timezone

from xauusd_assistant.core import (
    Candle,
    EventType,
    SetupGrade,
    SetupState,
    TrendState,
    classify_trend,
    interpret_timeframes,
    RiskPolicy,
    SetupMachine,
)


def candles(closes):
    return [
        Candle(
            timestamp=datetime(2026, 1, index + 1, tzinfo=timezone.utc),
            open=close,
            high=close + 1,
            low=close - 1,
            close=close,
        )
        for index, close in enumerate(closes)
    ]


def test_classifies_bullish_and_bearish_sequences():
    assert classify_trend(candles([100, 101, 103, 104])) is TrendState.BULLISH
    assert classify_trend(candles([104, 103, 101, 100])) is TrendState.BEARISH


def test_mixed_sequence_is_transitioning_not_forced_into_a_trend():
    assert classify_trend(candles([100, 103, 99, 102])) is TrendState.TRANSITIONING


def test_h1_bullish_inside_h4_bearish_is_a_pullback():
    context = interpret_timeframes(
        {
            "H4": TrendState.BEARISH,
            "H1": TrendState.BULLISH,
            "M5": TrendState.BULLISH,
        }
    )
    assert context.macro_regime is TrendState.BEARISH
    assert context.intraday_phase == "PULLBACK"
    assert context.countertrend is True


def test_zone_hit_then_liquidity_sweep_then_confirmation():
    machine = SetupMachine()
    assert machine.state is SetupState.NO_SETUP
    assert machine.apply(EventType.ZONE_APPROACHED).state is SetupState.WATCH
    assert machine.apply(EventType.ZONE_HIT).state is SetupState.ZONE_HIT
    assert machine.apply(EventType.LIQUIDITY_SWEEP).state is SetupState.LIQUIDITY_EVENT
    assert machine.apply(EventType.CONFIRMATION).state is SetupState.CONFIRMATION
    assert machine.apply(EventType.VALIDATED).state is SetupState.VALID_SETUP


def test_whipsaw_forces_wait_and_requires_stabilization():
    machine = SetupMachine()
    machine.apply(EventType.ZONE_HIT)
    result = machine.apply(EventType.WHIPSAW_DETECTED)
    assert result.state is SetupState.WHIPSAW
    assert result.decision == "WAIT"
    assert machine.apply(EventType.STABILIZED).state is SetupState.WATCH


def test_risk_policy_rejects_invalid_grade_risk_and_missing_invalidation():
    policy = RiskPolicy(a_max_risk_percent=0.5, a_plus_max_risk_percent=1.0)
    rejected = policy.validate(
        grade=SetupGrade.A_PLUS,
        risk_percent=1.5,
        invalidation_present=True,
        minimum_rr_met=True,
    )
    assert rejected.decision == "SKIP"
    assert "risk_limit" in rejected.reason_codes

    missing_invalidation = policy.validate(
        grade=SetupGrade.A,
        risk_percent=0.5,
        invalidation_present=False,
        minimum_rr_met=True,
    )
    assert missing_invalidation.decision == "WAIT"
    assert "missing_invalidation" in missing_invalidation.reason_codes


def test_low_quality_setup_is_never_upgraded():
    policy = RiskPolicy()
    result = policy.validate(
        grade=SetupGrade.LOWER_QUALITY,
        risk_percent=0.1,
        invalidation_present=True,
        minimum_rr_met=True,
    )
    assert result.decision == "SKIP"
