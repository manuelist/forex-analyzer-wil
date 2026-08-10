# XAUUSD Assistant — TradingView-only, offline-first

Decision-support system for XAUUSD. It does not execute trades, connect to MT5/brokers, or invent market data.

## Architecture

```text
xauusd-assistant/
├── strategy/       YAML rules, risk limits, and states
├── market_data/    TradingView event schema and CSV replay input
├── analysis/       Swings, structure, liquidity, zones, OB, FVG, RR
├── workflow/       State machine, Luna evidence contract, validator
├── notifications/  Alert decisions (delivery remains disabled)
├── journal/        Setup models and statistics
├── src/             Backward-compatible original package foundation
└── tests/           Offline tests
```

## TradingView-only mode

TradingView is the only planned external source. Webhook alerts are event triggers; they do not guarantee complete H4/H1/M15/M5 history. The engine therefore:

- accepts candle batches when present in a webhook payload;
- supports local CSV replay for historical testing;
- returns `WAIT` when required evidence is absent;
- never fabricates prices, levels, confirmations, or risk calculations.

## Safety boundaries

- `execution_enabled: false`
- `broker_connected: false`
- No MT5 or broker credentials
- No autonomous trading
- Paper trading and journaling only
- Telegram delivery must be explicitly enabled after replay validation

## Run tests

```bash
PATH=/data/.local/bin:$PATH pytest -q
```

## Example TradingView payload

```json
{
  "event": "zone_hit",
  "symbol": "TVC:GOLD",
  "timeframe": "H1",
  "timestamp": "2026-01-01T00:00:00Z",
  "price": 2000.0,
  "candles": []
}
```

## Current status

The modular deterministic foundation, event parser, replay loader, state machine, evidence contract, risk validator, alert rules, journal models, and statistics are implemented and tested. Public DNS/HTTPS delivery, TradingView alert creation, and live alert-to-analysis wiring remain deployment tasks.
