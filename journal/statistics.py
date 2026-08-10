from collections import Counter
from dataclasses import dataclass
from .models import Setup
@dataclass(frozen=True)
class Summary:
    total: int
    wins: int
    losses: int
    expectancy_r: float

def summarize(records: list[Setup])->Summary:
    values=[r.result_r for r in records if r.result_r is not None]
    return Summary(len(records),sum(x>0 for x in values),sum(x<0 for x in values),sum(values)/len(values) if values else 0.0)
