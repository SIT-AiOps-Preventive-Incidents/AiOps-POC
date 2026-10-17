"""What is normal for this host or service, and is the value now outside it?

Pure functions, no I/O: the detector feeds them history from Prometheus.

Normal is learned per entity and per metric from the same time of day on previous days (a busy shop at 9 pm
looks nothing like 4 am), falling back to the last 24 hours while there is not enough history. The band is
the 5th..95th percentile of those samples, widened by a tolerance so ordinary wobble never alerts.

Each metric has a rule: which direction is a problem (CPU stuck at 90% may be normal for one machine, but the
same machine dropping to 5% means the work stopped), the smallest change worth a person's attention, and an
optional safety limit that always alerts whatever the history says (a full disk breaks things even if it
filled up slowly).
"""
from __future__ import annotations

from dataclasses import dataclass
import time

HOUR = 3600
DAY = 86400


@dataclass(frozen=True)
class Rule:
    up: bool = True             # alert when far above normal
    down: bool = False          # alert when far below normal
    min_delta: float = 0.0      # never alert on a change smaller than this (absolute, metric units)
    min_rel: float = 0.0        # ... or smaller than this fraction of the normal level
    min_value: float = 0.0      # "high" needs at least this value (2% errors, not 0.1%; memory 70%, not 46%)
    min_level: float = 0.0      # "low" only makes sense if normal is at least this busy
    safety: float | None = None  # always alert at or above this, learned or not


RULES = {
    # "higher than usual" only matters once the machine is actually getting full; below these it is shown, not raised
    "cpu": Rule(up=True, down=True, min_delta=20, min_value=50, min_level=30),
    "mem": Rule(up=True, down=True, min_delta=15, min_value=70, min_level=30, safety=97),
    "disk": Rule(up=True, min_delta=8, min_value=80, safety=95),
    "error_rate": Rule(up=True, min_delta=0.02, min_value=0.02, safety=0.20),
    "p95": Rule(up=True, min_delta=100, min_rel=0.5),
    "rps": Rule(up=False, down=True, min_rel=0.6, min_level=0.5),
    # error log lines per minute: at least 5/min and double the usual before it counts
    "log_errors": Rule(up=True, min_delta=5, min_rel=1.0, min_value=5),
    # one container's share of its machine (%)
    "ccpu": Rule(up=True, min_delta=20, min_value=80),
    "cmem": Rule(up=True, min_delta=15, min_value=85, safety=97),
}

# how much of the normal band's width is added as tolerance on each side
SENSITIVITY = {"low": 1.0, "normal": 0.5, "high": 0.25}

MIN_SAME_HOUR = 24   # 2 h of 5-minute samples at this time of day on earlier days
MIN_RECENT = 36      # 3 h of 5-minute samples in the last day
SKIP_RECENT = 1800   # leave out the last 30 min so a problem in progress is not learned as normal


def _pct(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def _hour_gap(a: float, b: float, tz_offset: float) -> float:
    """Distance between two moments' time of day, in hours (0..12)."""
    d = abs(((a + tz_offset) % DAY) - ((b + tz_offset) % DAY)) / HOUR
    return min(d, 24 - d)


def learn(samples: list[tuple[float, float]], now: float | None = None, tz_offset: float = 7 * HOUR,
          exclude: list[tuple[float, float]] = ()) -> dict | None:
    """Normal band from history. samples: [(unix_ts, value)]; `exclude` are (start, end) periods of past
    incidents, which are not normal and must not be learned as such. Returns None while still learning."""
    now = now or time.time()
    past = [(t, v) for t, v in samples
            if v is not None and t < now - SKIP_RECENT and not any(a <= t <= b for a, b in exclude)]
    same_hour = [v for t, v in past if t < now - DAY + HOUR and _hour_gap(t, now, tz_offset) <= 1.0]
    days = len({int((t + tz_offset) // DAY) for t, v in past if t < now - DAY + HOUR and _hour_gap(t, now, tz_offset) <= 1.0})
    if len(same_hour) >= MIN_SAME_HOUR:
        vals, source = same_hour, "same_hour"
    else:
        vals = [v for t, v in past if t >= now - DAY]
        source, days = "last_24h", 1
        if len(vals) < MIN_RECENT:
            return None
    vals = sorted(vals)
    return {"low": _pct(vals, 0.05), "high": _pct(vals, 0.95), "median": _pct(vals, 0.5),
            "samples": len(vals), "source": source, "days": days}


def judge(metric: str, value: float | None, band: dict | None, sensitivity: str = "normal",
          fallback_limit: float | None = None) -> dict:
    """Is `value` abnormal for this entity? Returns {state: ok|high|low|learning, limit_low, limit_high, reason}."""
    rule = RULES[metric]
    if value is None:
        return {"state": "ok", "limit_low": None, "limit_high": None, "reason": "no data"}
    if rule.safety is not None and value >= rule.safety:
        return {"state": "high", "limit_low": None, "limit_high": rule.safety, "reason": "safety"}
    if band is None:  # not enough history yet: the fixed limit from settings, upward only
        if fallback_limit is not None and rule.up and value > fallback_limit and value >= rule.min_value:
            return {"state": "high", "limit_low": None, "limit_high": fallback_limit, "reason": "learning"}
        return {"state": "learning", "limit_low": None, "limit_high": fallback_limit, "reason": "learning"}
    k = SENSITIVITY.get(sensitivity, SENSITIVITY["normal"])
    width = band["high"] - band["low"]
    tol_hi = max(width * k, rule.min_delta, rule.min_rel * band["high"])
    tol_lo = max(width * k, rule.min_delta, rule.min_rel * band["low"])
    limit_high = band["high"] + tol_hi if rule.up else None
    limit_low = band["low"] - tol_lo if (rule.down and band["low"] >= rule.min_level) else None
    if limit_low is not None and limit_low <= 0:
        limit_low = None
    if limit_high is not None and value > limit_high and value >= rule.min_value:
        return {"state": "high", "limit_low": limit_low, "limit_high": limit_high, "reason": "baseline"}
    if limit_low is not None and value < limit_low:
        return {"state": "low", "limit_low": limit_low, "limit_high": limit_high, "reason": "baseline"}
    return {"state": "ok", "limit_low": limit_low, "limit_high": limit_high, "reason": "baseline"}
