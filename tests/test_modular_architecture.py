from datetime import datetime, timezone

from analysis.fvg import detect as detect_fvg
from analysis.liquidity import detect_sweep, whipsaw_score
from analysis.risk_reward import calculate
from analysis.swings import detect as detect_swings
from analysis.structure import classify
from journal.models import Setup
from journal.statistics import summarize
from market_data.schema import Candle
from market_data.tradingview import parse_event
from workflow.process_event import process
from workflow.state_machine import Machine, State
from workflow.validator import validate


def candles(values):
    return [Candle(datetime(2026, 1, 1 + i, tzinfo=timezone.utc), "H1", v - .5, v + 1, v - 1, v) for i, v in enumerate(values)]


def test_tradingview_event_and_candle_batch_are_parsed():
    event = parse_event({"event": "zone_hit", "symbol": "TVC:GOLD", "timeframe": "H1", "timestamp": "2026-01-01T00:00:00Z", "candles": [{"timestamp": "2026-01-01T00:00:00Z", "open": 1, "high": 2, "low": 0, "close": 1.5}]})
    assert event.symbol == "TVC:GOLD"
    assert len(event.candles) == 1


def test_structure_fvg_and_risk_reward():
    cs = candles([1, 2, 3, 4])
    assert classify(cs) == "BULLISH"
    assert detect_swings(cs) == []
    assert calculate(100, 95, 110) == 2.0


def test_liquidity_whipsaw_and_state_machine():
    cs = candles([10, 12, 9, 13, 8, 14, 14.5])
    assert whipsaw_score(cs) >= 2
    assert detect_sweep(cs, lookback=3) is not None
    machine = Machine()
    assert machine.apply("zone_hit") == State.ZONE_HIT
    assert machine.apply("confirmation", whipsaw=True) == State.WHIPSAW


def test_validator_waits_for_missing_evidence_and_daily_lockout():
    assert validate(grade="A+", risk_percent=1, daily_loss_percent=0, rr=2, missing=[]).decision == "A+"
    result = validate(grade="A+", risk_percent=1, daily_loss_percent=2, rr=2, missing=[])
    assert result.decision == "WAIT"
    assert "daily_loss_limit" in result.reasons


def test_processor_returns_wait_without_candles():
    result = process({"event": "zone_hit", "symbol": "TVC:GOLD", "timeframe": "H1", "timestamp": "2026-01-01T00:00:00Z"})
    assert result["decision"] == "WAIT"
    assert "candle_batch" in result["missing"]


def test_statistics():
    records = [
        Setup(datetime.now(timezone.utc), "XAUUSD", "long", "A", "VALID_SETUP", result_r=2),
        Setup(datetime.now(timezone.utc), "XAUUSD", "short", "A", "VALID_SETUP", result_r=-1),
    ]
    summary = summarize(records)
    assert summary.total == 2
    assert summary.expectancy_r == 0.5
