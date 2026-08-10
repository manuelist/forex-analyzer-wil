from dataclasses import dataclass
@dataclass(frozen=True)
class Validation:
    decision: str
    reasons: tuple[str,...]

def validate(*, grade: str, risk_percent: float, daily_loss_percent: float, rr: float | None, missing: list[str], execution_enabled: bool=False)->Validation:
    reasons=[]
    if missing: reasons.append("missing_evidence")
    if daily_loss_percent>=2.0: reasons.append("daily_loss_limit")
    if rr is not None and rr<1.5: reasons.append("low_reward_risk")
    maxrisk=1.0 if grade=="A+" else 0.5 if grade=="A" else 0.0
    if risk_percent>maxrisk: reasons.append("risk_exceeds_grade")
    if execution_enabled: reasons.append("execution_must_remain_disabled")
    return Validation("WAIT" if reasons else grade, tuple(reasons))
