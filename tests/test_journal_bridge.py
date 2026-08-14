import json
from datetime import datetime, timezone

from journal.bridge import build_envelope, deliver_envelope


def test_build_envelope_is_sanitized_and_idempotent():
    payload = {
        "event": "zone_hit",
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "timestamp": "2026-08-14T07:59:00Z",
        "price": 4344.95,
        "candles": [{"timeframe": "M15", "close": 4344.95}],
    }
    analysis = {
        "decision": "WAIT",
        "missing": ["H4", "H1", "M15", "M5"],
    }

    first = build_envelope(
        payload,
        analysis,
        audit_id="a" * 64,
        payload_format="JSON",
        received_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )
    second = build_envelope(
        payload,
        analysis,
        audit_id="a" * 64,
        payload_format="JSON",
        received_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )

    assert first == second
    assert first["event_id"] == "a" * 64
    assert first["event_type"] == "ZONE_TOUCH"
    assert first["symbol"] == "XAUUSD"
    assert first["timeframe"] == "M15"
    assert first["decision"] == "WAIT"
    assert first["execution_enabled"] is False
    assert first["order_attempts"] == 0
    assert "price" not in first
    assert "candles" not in first
    assert "payload" not in first


def test_unconfigured_delivery_is_explicitly_not_durable():
    envelope = {"schema_version": 1, "event_id": "b" * 64}

    result = deliver_envelope(envelope, url="", secret="")

    assert result == {
        "status": "NOT_CONFIGURED",
        "accepted": False,
        "durable_write_verified": False,
    }


def test_delivery_posts_signed_sanitized_envelope_without_secrets():
    captured = {}

    class Response:
        status = 202

        def read(self, limit):
            return b"accepted"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data
        captured["signature"] = request.headers["X-webhook-signature"]
        captured["timeout"] = timeout
        return Response()

    envelope = {
        "schema_version": 1,
        "event_id": "c" * 64,
        "event_type": "ZONE_TOUCH",
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "decision": "WAIT",
        "execution_enabled": False,
        "order_attempts": 0,
    }

    result = deliver_envelope(
        envelope,
        url="https://journal.example.test/events",
        secret="bridge-test-secret",
        opener=opener,
    )

    assert result == {
        "status": "ACCEPTED",
        "accepted": True,
        "durable_write_verified": False,
    }
    assert captured["url"] == "https://journal.example.test/events"
    assert captured["timeout"] == 3.0
    assert json.loads(captured["body"]) == envelope
    assert captured["signature"]
    assert "bridge-test-secret" not in captured["body"].decode()
