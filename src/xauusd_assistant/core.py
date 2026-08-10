"""Portable, offline-first trading-analysis primitives.

This module deliberately contains no broker, MT5, Telegram, TradingView,
cron, or network integration. It only models supplied candle data and
state/risk decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Iterable, Mapping


class TrendState(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    RANGE = "RANGE"
    TRANSITIONING = "TRANSITIONING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class TrendContext:
    macro_regime: TrendState
    intraday_phase: str
    countertrend: bool
    timeframes: Mapping[str, TrendState]


def classify_trend(candles: Iterable[Candle]) -> TrendState:
    """Classify a supplied close sequence without inventing market data.

    This is intentionally a small baseline detector for Phase 1. It is not a
    complete BOS/CHoCH implementation. Later detectors should provide richer
    evidence while preserving this explicit output vocabulary.
    """
    values = [candle.close for candle in candles]
    if len(values) < 3:
        return TrendState.INSUFFICIENT_DATA

    changes = [right - left for left, right in zip(values, values[1:])]
    if all(change == 0 for change in changes):
        return TrendState.RANGE

    positive = sum(change > 0 for change in changes)
    negative = sum(change < 0 for change in changes)
    net = values[-1] - values[0]

    if positive == len(changes) and net > 0:
        return TrendState.BULLISH
    if negative == len(changes) and net < 0:
        return TrendState.BEARISH
    if positive > negative and net > 0:
        return TrendState.TRANSITIONING
    if negative > positive and net < 0:
        return TrendState.TRANSITIONING
    return TrendState.TRANSITIONING


def interpret_timeframes(timeframes: Mapping[str, TrendState]) -> TrendContext:
    """Interpret timeframe relationships without flattening them into one trend."""
    macro = timeframes.get("H4", TrendState.INSUFFICIENT_DATA)
    h1 = timeframes.get("H1", TrendState.INSUFFICIENT_DATA)

    if macro is TrendState.BEARISH and h1 is TrendState.BULLISH:
        phase, countertrend = "PULLBACK", True
    elif macro is TrendState.BULLISH and h1 is TrendState.BEARISH:
        phase, countertrend = "PULLBACK", True
    elif macro is h1 and macro in (TrendState.BULLISH, TrendState.BEARISH):
        phase, countertrend = "ALIGNED", False
    elif h1 is TrendState.RANGE:
        phase, countertrend = "RANGE", False
    else:
        phase, countertrend = "TRANSITION", False

    return TrendContext(
        macro_regime=macro,
        intraday_phase=phase,
        countertrend=countertrend,
        timeframes=dict(timeframes),
    )


class EventType(str, Enum):
    ZONE_APPROACHED = "ZONE_APPROACHED"
    ZONE_HIT = "ZONE_HIT"
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"
    CONFIRMATION = "CONFIRMATION"
    VALIDATED = "VALIDATED"
    WHIPSAW_DETECTED = "WHIPSAW_DETECTED"
    STABILIZED = "STABILIZED"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


class SetupState(str, Enum):
    NO_SETUP = "NO_SETUP"
    WATCH = "WATCH"
    ZONE_HIT = "ZONE_HIT"
    LIQUIDITY_EVENT = "LIQUIDITY_EVENT"
    CONFIRMATION = "CONFIRMATION"
    VALID_SETUP = "VALID_SETUP"
    WHIPSAW = "WHIPSAW"
    INVALID = "INVALID"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class TransitionResult:
    state: SetupState
    decision: str
    event: EventType


class SetupMachine:
    """Small explicit state machine for offline replay and later integrations."""

    def __init__(self) -> None:
        self.state = SetupState.NO_SETUP

    def apply(self, event: EventType) -> TransitionResult:
        if event is EventType.WHIPSAW_DETECTED:
            self.state = SetupState.WHIPSAW
        elif event is EventType.STABILIZED and self.state is SetupState.WHIPSAW:
            self.state = SetupState.WATCH
        elif event is EventType.ZONE_APPROACHED and self.state is SetupState.NO_SETUP:
            self.state = SetupState.WATCH
        elif event is EventType.ZONE_HIT and self.state in (SetupState.WATCH, SetupState.NO_SETUP):
            self.state = SetupState.ZONE_HIT
        elif event is EventType.LIQUIDITY_SWEEP and self.state is SetupState.ZONE_HIT:
            self.state = SetupState.LIQUIDITY_EVENT
        elif event is EventType.CONFIRMATION and self.state is SetupState.LIQUIDITY_EVENT:
            self.state = SetupState.CONFIRMATION
        elif event is EventType.VALIDATED and self.state is SetupState.CONFIRMATION:
            self.state = SetupState.VALID_SETUP
        elif event is EventType.INVALIDATED:
            self.state = SetupState.INVALID
        elif event is EventType.EXPIRED:
            self.state = SetupState.EXPIRED

        decision = "WAIT" if self.state in {
            SetupState.NO_SETUP,
            SetupState.WATCH,
            SetupState.ZONE_HIT,
            SetupState.LIQUIDITY_EVENT,
            SetupState.CONFIRMATION,
            SetupState.WHIPSAW,
            SetupState.INVALID,
            SetupState.EXPIRED,
        } else "REVIEW"
        return TransitionResult(state=self.state, decision=decision, event=event)


class SetupGrade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    LOWER_QUALITY = "LOWER_QUALITY"


@dataclass(frozen=True)
class RiskDecision:
    decision: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RiskPolicy:
    a_max_risk_percent: float = 0.5
    a_plus_max_risk_percent: float = 1.0

    def validate(
        self,
        *,
        grade: SetupGrade,
        risk_percent: float,
        invalidation_present: bool,
        minimum_rr_met: bool,
    ) -> RiskDecision:
        reasons: list[str] = []
        if grade is SetupGrade.LOWER_QUALITY:
            return RiskDecision("SKIP", ("low_quality",))
        if not invalidation_present:
            reasons.append("missing_invalidation")
        if not minimum_rr_met:
            reasons.append("minimum_rr_not_met")

        limit = (
            self.a_plus_max_risk_percent
            if grade is SetupGrade.A_PLUS
            else self.a_max_risk_percent
        )
        if risk_percent > limit:
            reasons.append("risk_limit")

        if reasons:
            decision = "WAIT" if "risk_limit" not in reasons else "SKIP"
            return RiskDecision(decision, tuple(reasons))
        return RiskDecision("APPROVE")
