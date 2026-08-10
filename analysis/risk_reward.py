def calculate(entry: float, stop: float, target: float) -> float:
    risk=abs(entry-stop)
    return 0.0 if risk==0 else abs(target-entry)/risk
