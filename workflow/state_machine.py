from enum import Enum
from dataclasses import dataclass
class State(str,Enum):
    NO_SETUP="NO_SETUP"; WATCH="WATCH"; ZONE_HIT="ZONE_HIT"; LIQUIDITY_EVENT="LIQUIDITY_EVENT"; CONFIRMATION="CONFIRMATION"; VALID_SETUP="VALID_SETUP"; WHIPSAW="WHIPSAW"; INVALID="INVALID"; EXPIRED="EXPIRED"; COOLDOWN="COOLDOWN"
@dataclass
class Machine:
    state: State=State.NO_SETUP
    def apply(self,event: str, whipsaw: bool=False)->State:
        if whipsaw: self.state=State.WHIPSAW
        elif event=="zone_hit": self.state=State.ZONE_HIT
        elif event in ("liquidity_sweep","liquidity_event"): self.state=State.LIQUIDITY_EVENT
        elif event in ("confirmation","confirmed"): self.state=State.CONFIRMATION
        elif event in ("valid","valid_setup"): self.state=State.VALID_SETUP
        elif event in ("invalid","invalidated"): self.state=State.INVALID
        elif event in ("expired",): self.state=State.EXPIRED
        elif event in ("cooldown",): self.state=State.COOLDOWN
        elif event in ("watch",): self.state=State.WATCH
        return self.state
