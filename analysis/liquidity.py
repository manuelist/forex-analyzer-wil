from dataclasses import dataclass
from market_data.schema import Candle
@dataclass(frozen=True)
class LiquidityEvent:
    kind: str
    level: float
    index: int

def detect_sweep(candles: list[Candle], lookback: int=5) -> LiquidityEvent | None:
    if len(candles)<=lookback: return None
    prior=candles[-lookback-1:-1]; last=candles[-1]
    high=max(c.high for c in prior); low=min(c.low for c in prior)
    if last.high>high and last.close<high: return LiquidityEvent("HIGH_SWEEP_RECLAIM", high, len(candles)-1)
    if last.low<low and last.close>low: return LiquidityEvent("LOW_SWEEP_RECLAIM", low, len(candles)-1)
    return None

def whipsaw_score(candles: list[Candle], lookback: int=6) -> int:
    seq=candles[-lookback:]
    if len(seq)<3: return 0
    changes=[1 if b.close>a.close else -1 if b.close<a.close else 0 for a,b in zip(seq,seq[1:])]
    flips=sum(a*b<0 for a,b in zip(changes,changes[1:]))
    return flips
