from dataclasses import dataclass
from market_data.schema import Candle
@dataclass(frozen=True)
class OrderBlock:
    direction: str
    low: float
    high: float
    index: int

def detect(candles: list[Candle]) -> list[OrderBlock]:
    out=[]
    for i in range(1,len(candles)):
        prev, cur=candles[i-1], candles[i]
        if prev.close<prev.open and cur.close>cur.open and cur.close>prev.high: out.append(OrderBlock("BULLISH",prev.low,prev.high,i-1))
        if prev.close>prev.open and cur.close<cur.open and cur.close<prev.low: out.append(OrderBlock("BEARISH",prev.low,prev.high,i-1))
    return out
