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

## Durable journal bridge

The Vercel handler always emits sanitized runtime audit metadata. It can optionally forward a signed, sanitized envelope to the local journal bridge when both environment variables are configured:

```text
TRADINGVIEW_JOURNAL_URL=https://<approved-public-https-journal-endpoint>/journal/tradingview
TRADINGVIEW_JOURNAL_SECRET=<private bridge secret>
```

The handler does not request or log either value. Without both variables, the response explicitly reports `journal_status: NOT_CONFIGURED` and `durable_write_verified: false`. A remote HTTP success is reported as `ACCEPTED`, but never treated as proof of durable storage. The local `xauusd_bot.journal_server` verifies the HMAC signature, rejects sensitive fields, deduplicates by `event_id`, and fsyncs an append-only JSONL record. No public tunnel or continuous service is enabled automatically.

## Current status

The modular deterministic foundation, event parser, replay loader, state machine, evidence contract, risk validator, alert rules, journal models, sanitized journal bridge, and statistics are implemented and tested. Public DNS/HTTPS delivery, TradingView alert creation, and the optional Vercel-to-local journal connection remain deployment/configuration tasks.
