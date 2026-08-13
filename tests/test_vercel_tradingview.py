import json
from datetime import datetime, timedelta, timezone

from api.tradingview import handle_request


TOKEN = "unit-test-token-only"


def request(method="POST", body=None, token=TOKEN, content_type="application/json"):
    if body is None:
        body = {"event": "zone_hit", "symbol": "TVC:GOLD", "candles": []}
    raw_body = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    return handle_request(
        method,
        f"/api/tradingview?token={token}",
        raw_body,
        content_type,
    )


def test_valid_token_returns_success(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_TOKEN", TOKEN)

    status, response = request()

    assert status == 200
    assert response["decision"] == "WAIT"
    assert response["execution_enabled"] is False
    assert response["order_attempts"] == 0


def test_invalid_token_returns_401(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_TOKEN", TOKEN)

    status, response = request(token="wrong-token")

    assert status == 401
    assert response == {"error": "unauthorized"}


def test_invalid_json_returns_400(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_TOKEN", TOKEN)

    status, response = request(body=b"not-json")

    assert status == 400
    assert response == {"error": "invalid_json"}


def test_plain_text_tradingview_alert_is_acknowledged_as_wait(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_TOKEN", TOKEN)

    status, response = request(
        body=b"TVC:GOLD crossed the alert level",
        content_type="text/plain; charset=utf-8",
    )

    assert status == 200
    assert response["decision"] == "WAIT"
    assert response["execution_enabled"] is False
    assert response["order_attempts"] == 0


def test_request_body_is_bounded(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_TOKEN", TOKEN)

    status, response = request(body=b"x" * (64 * 1024 + 1))

    assert status == 413
    assert response == {"error": "request_too_large"}


def test_only_xauusd_symbols_are_accepted(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_TOKEN", TOKEN)

    status, response = request(body={"event": "zone_hit", "symbol": "FX:EURUSD"})

    assert status == 400
    assert response == {"error": "unsupported_symbol"}


def test_timestamp_must_include_timezone(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_TOKEN", TOKEN)
    monkeypatch.setattr(
        "api.tradingview._utc_now",
        lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    status, response = request(
        body={
            "event": "zone_hit",
            "symbol": "XAUUSD",
            "timestamp": "2026-01-01T00:00:00",
        }
    )

    assert status == 400
    assert response == {"error": "invalid_timestamp"}


def test_stale_timestamp_is_rejected(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_TOKEN", TOKEN)
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("api.tradingview._utc_now", lambda: now)

    status, response = request(
        body={
            "event": "zone_hit",
            "symbol": "XAUUSD",
            "timestamp": (now - timedelta(minutes=6)).isoformat(),
        }
    )

    assert status == 400
    assert response == {"error": "stale_timestamp"}


def test_unsupported_method_returns_405(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_TOKEN", TOKEN)

    status, response = request(method="GET")

    assert status == 405
    assert response == {"error": "method_not_allowed"}


def test_missing_candle_history_returns_wait(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_TOKEN", TOKEN)

    status, response = request(body={"event": "zone_hit", "symbol": "TVC:GOLD"})

    assert status == 200
    assert response["decision"] == "WAIT"
    assert response["missing"] == ["H4", "H1", "M15", "M5"]


def test_execution_remains_disabled(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_TOKEN", TOKEN)

    status, response = request()

    assert status == 200
    assert response["execution_enabled"] is False
