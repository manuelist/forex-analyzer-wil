from __future__ import annotations
import hashlib, json, shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

@dataclass(frozen=True)
class ArchivedScreenshot:
    path: str
    sha256: str
    received_at: str
    symbol: str | None
    timeframe: str | None

def archive_screenshot(source: str | Path, archive_dir: str | Path, *, symbol: str | None=None, timeframe: str | None=None) -> ArchivedScreenshot:
    source=Path(source); archive=Path(archive_dir); archive.mkdir(parents=True, exist_ok=True)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    suffix=source.suffix.lower() or ".bin"
    target=archive / f"{digest[:16]}{suffix}"
    if not target.exists(): shutil.copy2(source, target)
    received=datetime.now(timezone.utc).isoformat()
    record=ArchivedScreenshot(str(target), digest, received, symbol, timeframe)
    (target.with_suffix(target.suffix+".json")).write_text(json.dumps(asdict(record), indent=2))
    return record
