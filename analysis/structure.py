from market_data.schema import Candle
from .swings import detect

def classify(candles: list[Candle]) -> str:
    if len(candles)<2: return "UNKNOWN"
    up=sum(b.close>a.close for a,b in zip(candles,candles[1:]))
    down=sum(b.close<a.close for a,b in zip(candles,candles[1:]))
    if up and not down: return "BULLISH"
    if down and not up: return "BEARISH"
    if candles[-1].close > candles[0].close and up >= down: return "BULLISH"
    if candles[-1].close < candles[0].close and down >= up: return "BEARISH"
    return "TRANSITIONING"

def break_event(candles: list[Candle]) -> str | None:
    swings=detect(candles)
    if not swings: return None
    last=candles[-1]
    highs=[s.price for s in swings if s.kind=="HIGH"]
    lows=[s.price for s in swings if s.kind=="LOW"]
    if highs and last.close>highs[-1]: return "BOS_UP"
    if lows and last.close<lows[-1]: return "BOS_DOWN"
    return None
