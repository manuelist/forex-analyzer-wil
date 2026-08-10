from __future__ import annotations
import json
import sys
from market_data.tradingview import parse_event
from analysis.liquidity import detect_sweep, whipsaw_score
from analysis.structure import classify
from workflow.state_machine import Machine
from workflow.validator import validate


def process(payload: dict) -> dict:
    event = parse_event(payload)
    result = {"symbol": event.symbol, "timeframe": event.timeframe, "event": event.event, "decision": "WAIT", "state": "NO_SETUP", "evidence": [], "missing": []}
    if event.symbol not in {"TVC:GOLD", "XAUUSD"}:
        result["missing"].append("supported_XAUUSD_symbol")
        return result
    if not event.candles:
        result["missing"].append("candle_batch")
        result["reason"] = "TradingView event has no candle batch; no structure confirmation is claimed."
        return result
    candles = list(event.candles)
    result["evidence"].append(f"structure:{classify(candles)}")
    machine = Machine()
    sweep = detect_sweep(candles)
    if sweep:
        result["evidence"].append(f"liquidity:{sweep.kind}")
    state = machine.apply(event.event, whipsaw=whipsaw_score(candles) >= 3)
    result["state"] = state.value
    validation = validate(grade="WAIT", risk_percent=0, daily_loss_percent=0, rr=None, missing=[])
    result["decision"] = validation.decision
    return result


def main() -> None:
    payload = json.load(sys.stdin)
    print(json.dumps(process(payload), sort_keys=True))

if __name__ == "__main__":
    main()
