from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import Any

class JournalStore:
    def __init__(self, path: str | Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY, received_at TEXT NOT NULL, source TEXT NOT NULL, payload TEXT NOT NULL, decision TEXT NOT NULL)")
            db.commit()
    def record(self, event_id: str, source: str, payload: dict[str,Any], decision: str) -> bool:
        with sqlite3.connect(self.path) as db:
            cur=db.execute("INSERT OR IGNORE INTO events VALUES (?, datetime('now'), ?, ?, ?)", (event_id, source, json.dumps(payload, sort_keys=True), decision))
            db.commit(); return cur.rowcount == 1
    def count(self) -> int:
        with sqlite3.connect(self.path) as db: return int(db.execute("SELECT COUNT(*) FROM events").fetchone()[0])
