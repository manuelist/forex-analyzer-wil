from dataclasses import dataclass
@dataclass(frozen=True)
class Alert:
    severity: str
    title: str
    message: str
    send: bool=False

def make_alert(decision: str, state: str, reason: str)->Alert:
    send=decision in {"A","A+"} and state=="VALID_SETUP"
    return Alert("candidate" if send else "info", f"XAUUSD {decision}", reason, send)
