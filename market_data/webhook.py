from __future__ import annotations
import hashlib, hmac, json
from typing import Any
from ingest.evidence import evidence_from_payload
from journal.store import JournalStore

def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    expected=hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

def process_webhook(payload: dict[str,Any], journal: JournalStore) -> dict[str,Any]:
    evidence=evidence_from_payload(payload)
    decision="WAIT" if evidence.missing else "WATCH"
    event_id=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    stored=journal.record(event_id, "tradingview", payload, decision)
    return {"event_id": event_id, "stored": stored, "decision": decision, "confidence": evidence.confidence, "missing": list(evidence.missing)}
