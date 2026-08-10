import json

from api.tradingview import handle_request


TOKEN = "unit-test-token-only"


def request(method="POST", body=None, token=TOKEN):
    if body is None:
        body = {"event": "zone_hit", "symbol": "TVC:GOLD", "candles": []}
    raw_body = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    return handle_request(method, f"/api/tradingview?token={token}", raw_body)


def test_valid_token_returns_success(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_TOKEN", TOKEN)

    status, response = request()

    assert status == 200
    assert response["decision"] == "WAIT"


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
