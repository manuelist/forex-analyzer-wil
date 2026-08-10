from dataclasses import dataclass
from datetime import datetime
@dataclass(frozen=True)
class Setup:
    timestamp: datetime
    instrument: str
    direction: str
    grade: str
    state: str
    entry: float | None=None
    stop: float | None=None
    target: float | None=None
    result_r: float | None=None
    notes: str=""
