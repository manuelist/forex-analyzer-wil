import json
from pathlib import Path

from ingest.evidence import evidence_from_payload
from ingest.screenshots import archive_screenshot
from journal.store import JournalStore
from market_data.webhook import process_webhook, verify_signature


def test_screenshot_archival_is_content_addressed(tmp_path):
    source = tmp_path / "chart.png"
    source.write_bytes(b"fake-image")
    first = archive_screenshot(source, tmp_path / "archive", symbol="TVC:GOLD", timeframe="H1")
    second = archive_screenshot(source, tmp_path / "archive", symbol="TVC:GOLD", timeframe="H1")
    assert first.path == second.path
    assert Path(first.path).exists()
    assert Path(first.path + ".json").exists()


def test_incomplete_chart_evidence_is_wait():
    evidence = evidence_from_payload({
        "symbol": "TVC:GOLD",
        "timestamp": "2026-01-01T00:00:00Z",
        "candles": [{"timestamp": "2026-01-01T00:00:00Z", "timeframe": "H1", "open": 1, "high": 2, "low": 0, "close": 1}]
    })
    assert evidence.confidence == "INSUFFICIENT"
    assert "H4" in evidence.missing


def test_webhook_is_signed_and_deduplicated(tmp_path):
    secret = "test-secret"
    body = b'{"event":"zone_hit"}'
    import hashlib, hmac
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body, signature, secret)
    journal = JournalStore(tmp_path / "journal.sqlite")
    payload = {"event": "zone_hit", "symbol": "TVC:GOLD", "timestamp": "2026-01-01T00:00:00Z", "candles": []}
    first = process_webhook(payload, journal)
    second = process_webhook(payload, journal)
    assert first["stored"] is True
    assert second["stored"] is False
    assert first["decision"] == "WAIT"
    assert journal.count() == 1
