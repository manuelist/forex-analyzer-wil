"""Vercel HTTP entrypoint for TradingView webhook delivery.

This endpoint is deliberately analysis-only. It does not connect to a broker,
MT5, or any other external service.
"""

from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qs, urlsplit


REQUIRED_TIMEFRAMES = ("H4", "H1", "M15", "M5")


def _query_token(path: str) -> str:
    """Return the URL token without logging or otherwise exposing it."""

    values = parse_qs(urlsplit(path).query).get("token", ())
    return values[0] if values else ""


def _authorized(path: str) -> bool:
    supplied = _query_token(path)
    expected = os.environ.get("TRADINGVIEW_WEBHOOK_TOKEN", "")
    # An unset secret must never authorize a request, including an empty token.
    return bool(expected) and hmac.compare_digest(supplied, expected)


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
    return result


def handle_request(method: str, path: str, body: bytes) -> tuple[int, dict[str, Any]]:
    """Pure request handler used by Vercel and the endpoint tests."""

    if method.upper() != "POST":
        return 405, {"error": "method_not_allowed"}

    if not _authorized(path):
        return 401, {"error": "unauthorized"}

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 400, {"error": "invalid_json"}

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
        body = self.rfile.read(max(content_length, 0))
        status, payload = handle_request(self.command, self.path, body)
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
