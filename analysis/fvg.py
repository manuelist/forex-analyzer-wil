from dataclasses import dataclass
from market_data.schema import Candle
@dataclass(frozen=True)
class FVG:
    direction: str
    low: float
    high: float
    index: int

def detect(candles: list[Candle]) -> list[FVG]:
    out=[]
    for i in range(2,len(candles)):
        a,b,c=candles[i-2:i+1]
        if c.low>a.high: out.append(FVG("BULLISH",a.high,c.low,i))
        if c.high<a.low: out.append(FVG("BEARISH",c.high,a.low,i))
    return out
