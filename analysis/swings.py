from dataclasses import dataclass
from market_data.schema import Candle
@dataclass(frozen=True)
class Swing:
    index: int
    kind: str
    price: float

def detect(candles: list[Candle], window: int = 1) -> list[Swing]:
    result=[]
    for i in range(window, len(candles)-window):
        c=candles[i]; before=candles[i-window:i]; after=candles[i+1:i+window+1]
        if c.high > max(x.high for x in before+after): result.append(Swing(i,"HIGH",c.high))
        if c.low < min(x.low for x in before+after): result.append(Swing(i,"LOW",c.low))
    return result
