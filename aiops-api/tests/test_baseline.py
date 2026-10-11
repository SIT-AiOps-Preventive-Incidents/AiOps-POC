"""Unit tests for app/baseline.py (pure, no DB). Run: python -m pytest aiops-api/tests"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.baseline import DAY, HOUR, judge, learn  # noqa: E402

NOW = 1_800_000_000.0  # fixed clock


def history(level, days=3, step=300, spread=2.0, recent_level=None):
    """5-minute samples for `days` days, around `level`, with a small sawtooth wobble."""
    out = []
    t = NOW - days * DAY
    i = 0
    while t < NOW:
        lv = recent_level if (recent_level is not None and t > NOW - 1800) else level
        out.append((t, lv + (i % 5 - 2) * spread / 2))
        t += step
        i += 1
    return out


def test_learning_until_there_is_history():
    assert learn([(NOW - 600, 50.0)], now=NOW) is None


def test_same_hour_of_earlier_days_is_preferred():
    b = learn(history(88), now=NOW)
    assert b["source"] == "same_hour" and b["days"] >= 2
    assert 85 <= b["low"] <= b["high"] <= 91


def test_falls_back_to_last_day_when_young():
    b = learn(history(40, days=0.5), now=NOW)
    assert b["source"] == "last_24h"


def test_a_problem_in_progress_is_not_learned_as_normal():
    b = learn(history(88, recent_level=5), now=NOW)
    assert b["low"] > 80


def test_past_incidents_are_not_learned_as_normal():
    # errors were 0% except during demo incidents at this hour on earlier days, when they hit 50%
    samples = [(t, 0.5 if (NOW - t) % DAY < 1800 else 0.0) for t, _ in history(0)]
    windows = [(NOW - d * DAY - 1800, NOW - d * DAY + 1800) for d in (1, 2, 3)]
    assert learn(samples, now=NOW)["high"] > 0.2                       # learned the incidents as normal...
    b = learn(samples, now=NOW, exclude=windows)
    assert b["high"] == 0.0 and judge("error_rate", 0.25, b)["state"] == "high"   # ...unless they are left out


def test_more_memory_than_usual_but_plenty_left_is_not_raised():
    # seen on cp26pt1: memory 27% -> 46% when the AI model was loaded; unusual, but nothing to wake anyone for
    b = learn(history(27, spread=2), now=NOW)
    assert judge("mem", 46, b)["state"] == "ok"
    assert judge("mem", 85, b)["state"] == "high"
    assert judge("cpu", 45, learn(history(4, spread=1), now=NOW))["state"] == "ok"
    assert judge("disk", 60, learn(history(38, spread=0.2), now=NOW))["state"] == "ok"


def test_busy_machine_at_90_percent_is_normal():
    b = learn(history(88), now=NOW)
    assert judge("cpu", 91, b)["state"] == "ok"


def test_busy_machine_dropping_to_5_percent_is_abnormal():
    b = learn(history(88), now=NOW)
    assert judge("cpu", 5, b)["state"] == "low"


def test_quiet_machine_dropping_further_is_not_alerted():
    b = learn(history(8), now=NOW)
    assert judge("cpu", 0, b)["state"] == "ok"


def test_quiet_machine_jumping_up_is_abnormal():
    b = learn(history(10), now=NOW)
    assert judge("cpu", 70, b)["state"] == "high"
    assert judge("cpu", 25, b)["state"] == "ok"  # less than the 20-point minimum change


def test_full_disk_alerts_even_if_it_grew_slowly():
    b = learn(history(94, spread=0.2), now=NOW)
    r = judge("disk", 96, b)
    assert r["state"] == "high" and r["reason"] == "safety"


def test_small_error_rate_noise_is_ignored():
    b = learn(history(0.0, spread=0.0), now=NOW)
    assert judge("error_rate", 0.01, b)["state"] == "ok"
    assert judge("error_rate", 0.25, b)["state"] == "high"


def test_service_with_usual_errors_is_judged_against_its_own_normal():
    b = learn(history(0.08, spread=0.01), now=NOW)  # this service always fails ~8%
    assert judge("error_rate", 0.09, b)["state"] == "ok"
    assert judge("error_rate", 0.16, b)["state"] == "high"


def test_traffic_dying_is_abnormal_but_quiet_service_is_not():
    busy = learn(history(6.0, spread=0.5), now=NOW)
    assert judge("rps", 0.3, busy)["state"] == "low"
    quiet = learn(history(0.2, spread=0.05), now=NOW)
    assert judge("rps", 0.0, quiet)["state"] == "ok"


def test_sensitivity_changes_the_tolerance():
    b = learn(history(50, spread=20), now=NOW)  # normal 30..70: a wide band, so sensitivity decides
    lo = judge("cpu", 95, b, "low")["state"]
    hi = judge("cpu", 95, b, "high")["state"]
    assert (lo, hi) == ("ok", "high")


def test_while_learning_the_fixed_limit_still_protects():
    assert judge("cpu", 95, None, fallback_limit=70)["state"] == "high"
    assert judge("cpu", 40, None, fallback_limit=70)["state"] == "learning"


def test_time_of_day_matters():
    # busy in the evening (21:00 local), idle at night: at 21:00 the evening level is normal
    samples = []
    t = NOW - 3 * DAY
    while t < NOW:
        local_hour = ((t + 7 * HOUR) % DAY) / HOUR
        samples.append((t, 80.0 if 20 <= local_hour <= 22 else 10.0))
        t += 300
    evening = NOW - ((NOW + 7 * HOUR) % DAY) + 21 * HOUR
    b = learn(samples, now=evening)
    assert b["source"] == "same_hour" and b["median"] >= 70
    assert judge("cpu", 82, b)["state"] == "ok"
