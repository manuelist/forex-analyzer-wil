from datetime import datetime, timezone

from xauusd_assistant.journal import Journal, SetupRecord


def test_journal_persists_setup_records(tmp_path):
    journal = Journal(tmp_path / "journal.sqlite3")
    journal.initialize()
    record = SetupRecord(
        setup_id="setup-1",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        instrument="XAUUSD",
        account="propfirm",
        status="WAIT",
        grade="NONE",
        notes="Waiting for M5 confirmation",
    )
    journal.record(record)
    rows = journal.list_records()
    assert len(rows) == 1
    assert rows[0].setup_id == "setup-1"
    assert rows[0].account == "propfirm"


def test_event_payload_rejects_unknown_symbols():
    from xauusd_assistant.events import normalize_event

    event = normalize_event(
        {
            "event": "zone_hit",
            "symbol": "TVC:GOLD",
            "timeframe": "H1",
            "timestamp": "2026-01-01T00:00:00+00:00",
        },
        allowed_symbols={"TVC:GOLD"},
    )
    assert event.instrument == "XAUUSD"
    assert event.event_type == "ZONE_HIT"
