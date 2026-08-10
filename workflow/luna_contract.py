from dataclasses import asdict, dataclass
from typing import Any
@dataclass(frozen=True)
class Evidence:
    instrument: str
    timeframe_context: dict[str,str]
    events: list[str]
    risk_reward: float | None
    missing: list[str]
    state: str

def build_prompt(e: Evidence) -> str:
    data=asdict(e)
    return ("Evaluate only the supplied evidence. Do not invent prices, candles, "
            "levels, confirmations, or risk. If evidence is incomplete, return WAIT. "
            f"Evidence JSON: {data}")

def response_contract() -> dict[str,Any]:
    return {"decision":"WAIT|WATCH|A|A+|SKIP","reason":"string","missing_evidence":[]}
