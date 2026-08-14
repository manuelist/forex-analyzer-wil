from __future__ import annotations

import hashlib
import hmac
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlsplit


MAX_ENVELOPE_BYTES = 16 * 1024


def _canonical_event_type(payload: dict[str, Any]) -> str | None:
    raw = payload.get("event_type", payload.get("event"))
    if not isinstance(raw, str) or not raw.strip():
        return None
    aliases = {
        "zone_hit": "ZONE_TOUCH",
        "zone_touch": "ZONE_TOUCH",
        "bar_close": "BAR_CLOSE",
        "context_update": "CONTEXT_UPDATE",
    }
    key = raw.strip().lower()
    return aliases.get(key, key.upper())


def _canonical_symbol(payload: dict[str, Any]) -> str | None:
    symbol = payload.get("symbol")
    if symbol == "TVC:GOLD":
        return "XAUUSD"
    return symbol if symbol == "XAUUSD" else None


def build_envelope(
    payload: dict[str, Any],
    analysis: dict[str, Any],
    *,
    audit_id: str,
    payload_format: str,
    received_at: datetime | None = None,
) -> dict[str, Any]:
    received_at = received_at or datetime.now(timezone.utc)
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise ValueError("received_at must include timezone")
    envelope = {
        "schema_version": 1,
        "event_id": audit_id,
        "source": "tradingview",
        "event_type": _canonical_event_type(payload),
        "symbol": _canonical_symbol(payload),
        "timeframe": str(payload["timeframe"]).upper() if isinstance(payload.get("timeframe"), str) else None,
        "timestamp": payload.get("timestamp") if isinstance(payload.get("timestamp"), str) else None,
        "received_at": received_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload_format": payload_format,
        "decision": analysis.get("decision", "WAIT"),
        "missing": [str(value) for value in analysis.get("missing", [])],
        "execution_enabled": False,
        "order_attempts": 0,
    }
    return envelope


def _validate_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("journal URL must be HTTPS without query or fragment")


def _signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def deliver_envelope(
    envelope: dict[str, Any],
    *,
    url: str,
    secret: str,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    """Optionally deliver a sanitized envelope; never claims remote durability."""

    if not url or not secret:
        return {"status": "NOT_CONFIGURED", "accepted": False, "durable_write_verified": False}
    try:
        _validate_url(url)
        body = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(body) > MAX_ENVELOPE_BYTES:
            raise ValueError("journal envelope too large")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
                "X-Webhook-Signature": _signature(body, secret),
            },
        )
        with opener(request, timeout=3.0) as response:
            status = int(response.status)
            response.read(4096)
        if 200 <= status < 300:
            return {"status": "ACCEPTED", "accepted": True, "durable_write_verified": False}
        return {"status": "REJECTED", "accepted": False, "durable_write_verified": False}
    except (OSError, ValueError, urllib.error.URLError, TimeoutError):
        return {"status": "ERROR", "accepted": False, "durable_write_verified": False}
