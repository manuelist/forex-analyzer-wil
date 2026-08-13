"""Vercel HTTP entrypoint for TradingView webhook delivery.

This endpoint is deliberately analysis-only. It does not connect to a broker,
MT5, or any other external service.
"""

from __future__ import annotations

import hmac
import json
import math
import os
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qs, urlsplit


REQUIRED_TIMEFRAMES = ("H4", "H1", "M15", "M5")
ALLOWED_SYMBOLS = frozenset({"TVC:GOLD", "XAUUSD"})
MAX_BODY_BYTES = 64 * 1024
MAX_TIMESTAMP_AGE = timedelta(minutes=5)
MAX_FUTURE_SKEW = timedelta(minutes=1)


def _query_token(path: str) -> str:
    """Return the URL token without logging or otherwise exposing it."""

    values = parse_qs(urlsplit(path).query).get("token", ())
    return values[0] if values else ""


def _authorized(path: str) -> bool:
    supplied = _query_token(path)
    expected = os.environ.get("TRADINGVIEW_WEBHOOK_TOKEN", "")
    # An unset secret must never authorize a request, including an empty token.
    return bool(expected) and hmac.compare_digest(supplied, expected)


def _is_plain_text(content_type: str) -> bool:
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "text/plain"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: Any) -> datetime:
    """Parse a webhook timestamp into an aware UTC datetime."""

    if isinstance(value, bool):
        raise ValueError("timestamp must be ISO-8601 or a Unix timestamp")

    if isinstance(value, (int, float)):
        try:
            finite = math.isfinite(value)
        except OverflowError as exc:
            raise ValueError("timestamp must be finite") from exc
        if not finite:
            raise ValueError("timestamp must be finite")
        try:
            return datetime.fromtimestamp(value, timezone.utc)
        except (OverflowError, OSError, ValueError) as exc:
            raise ValueError("timestamp is out of range") from exc

    if not isinstance(value, str):
        raise ValueError("timestamp must be ISO-8601 or a Unix timestamp")

    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return timestamp.astimezone(timezone.utc)


def _validate_payload(payload: Any) -> tuple[bool, str | None]:
    if not isinstance(payload, dict):
        return False, "invalid_payload"

    if payload.get("symbol") not in ALLOWED_SYMBOLS:
        return False, "unsupported_symbol"

    if "timestamp" not in payload:
        return True, None

    try:
        timestamp = _parse_timestamp(payload["timestamp"])
    except ValueError:
        return False, "invalid_timestamp"

    now = _utc_now()
    if timestamp - now > MAX_FUTURE_SKEW or now - timestamp > MAX_TIMESTAMP_AGE:
        return False, "stale_timestamp"

    return True, None


def _missing_timeframes(payload: dict[str, Any]) -> list[str]:
    candles = payload.get("candles", ())
    if not isinstance(candles, list):
        candles = ()

    fallback_timeframe = payload.get("timeframe")
    present: set[str] = set()
    for candle in candles:
        if not isinstance(candle, dict):
            continue
        timeframe = candle.get("timeframe", fallback_timeframe)
        if timeframe is not None:
            present.add(str(timeframe).upper())

    return [timeframe for timeframe in REQUIRED_TIMEFRAMES if timeframe not in present]


def _analysis_response(payload: Any) -> dict[str, Any]:
    """Build a safe acknowledgement from supplied JSON only."""

    if not isinstance(payload, dict):
        payload = {}

    missing = _missing_timeframes(payload)
    if missing:
        return {
            "decision": "WAIT",
            "execution_enabled": False,
            "order_attempts": 0,
            "missing": missing,
        }

    # Use the existing offline processor when a complete candle batch is
    # supplied. The fallback remains WAIT and never fabricates evidence.
    try:
        from workflow.process_event import process

        result = process(payload)
        if not isinstance(result, dict):
            result = {}
    except (KeyError, TypeError, ValueError, OverflowError):
        result = {"decision": "WAIT", "missing": []}

    result["execution_enabled"] = False
    result["order_attempts"] = 0
    return result


def handle_request(
    method: str,
    path: str,
    body: bytes,
    content_type: str = "application/json",
) -> tuple[int, dict[str, Any]]:
    """Pure request handler used by Vercel and the endpoint tests."""

    if method.upper() != "POST":
        return 405, {"error": "method_not_allowed"}

    if not _authorized(path):
        return 401, {"error": "unauthorized"}

    if len(body) > MAX_BODY_BYTES:
        return 413, {"error": "request_too_large"}

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        # TradingView uses text/plain for alert messages that are not valid
        # JSON. Acknowledge those deliveries safely, but do not analyze or
        # infer an actionable signal from unstructured text.
        if _is_plain_text(content_type):
            return 200, _analysis_response({})
        return 400, {"error": "invalid_json"}

    valid, error = _validate_payload(payload)
    if not valid:
        return 400, {"error": error}

    return 200, _analysis_response(payload)


class handler(BaseHTTPRequestHandler):
    """Standard Vercel Python serverless-function entrypoint."""

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(encoded)

    def _dispatch(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except (TypeError, ValueError):
            content_length = 0

        if content_length > MAX_BODY_BYTES:
            self._send_json(413, {"error": "request_too_large"})
            return

        body = self.rfile.read(max(content_length, 0))
        status, payload = handle_request(
            self.command,
            self.path,
            body,
            self.headers.get("Content-Type", ""),
        )
        self._send_json(status, payload)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self._dispatch()

    def _method_not_allowed(self) -> None:
        self._send_json(405, {"error": "method_not_allowed"})

    def do_GET(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_HEAD(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_PUT(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_PATCH(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_DELETE(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_CONNECT(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_TRACE(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def __getattr__(self, name: str) -> Any:
        # BaseHTTPRequestHandler otherwise returns 501 for an unknown HTTP
        # verb. Vercel should expose the endpoint as POST-only and return 405.
        if name.startswith("do_"):
            return self._method_not_allowed
        raise AttributeError(name)
