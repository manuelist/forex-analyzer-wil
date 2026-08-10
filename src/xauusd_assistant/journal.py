"""SQLite journal with no broker or network integration."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SetupRecord:
    setup_id: str
    timestamp: datetime
    instrument: str
    account: str
    status: str
    grade: str
    notes: str = ""


class Journal:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS setup_records (
                    setup_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    account TEXT NOT NULL,
                    status TEXT NOT NULL,
                    grade TEXT NOT NULL,
                    notes TEXT NOT NULL
                )
                """
            )

    def record(self, record: SetupRecord) -> None:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO setup_records
                (setup_id, timestamp, instrument, account, status, grade, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.setup_id,
                    record.timestamp.isoformat(),
                    record.instrument,
                    record.account,
                    record.status,
                    record.grade,
                    record.notes,
                ),
            )

    def list_records(self) -> list[SetupRecord]:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                "SELECT setup_id, timestamp, instrument, account, status, grade, notes "
                "FROM setup_records ORDER BY timestamp"
            ).fetchall()
        return [
            SetupRecord(
                setup_id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                instrument=row[2],
                account=row[3],
                status=row[4],
                grade=row[5],
                notes=row[6],
            )
            for row in rows
        ]
