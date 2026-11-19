"""Insights: what the incident history means for the business, each with a number, a sentence, an action and its basis."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import insights  # noqa: E402

DAY, HOUR = 86400.0, 3600.0
NOW = 1_800_000_000.0


def inc(i, entity="checkout", status="resolved", age_d=1.0, open_h=2.0, analysis_s=80, kind="error_rate"):
    det = NOW - age_d * DAY
    return {"id": i, "entity_name": entity, "kind": kind, "status": status, "severity": "major", "detected_at": det,
            "resolved_at": det + open_h * HOUR if status in ("resolved", "closed") else None, "analysis_ms": analysis_s * 1000}


SETTINGS = {"downtime_cost_per_hour": "12000", "manual_rca_minutes": "45", "currency": "THB"}


def by_id(out):
    return {x["id"]: x for x in out}


def test_waiting_fixes_are_the_top_finding_with_their_age_and_a_way_to_act():
    data = [inc(1, status="awaiting_approval", age_d=6), inc(2, status="awaiting_approval", age_d=2), inc(3)]
    out = insights.compute(data, feedback=[], runbook_uses=0, unmonitored_near_problems=0, settings=SETTINGS, now=NOW)
    top = out[0]
    assert top["id"] == "approval_backlog" and top["tone"] == "action"
    assert top["value"] == 2 and "6 days" in top["detail"]
    assert top["action"]["to"] == "/problems"


def test_one_service_behind_a_big_share_of_incidents_is_called_out():
    data = [inc(i, entity="checkout") for i in range(6)] + [inc(10 + i, entity=f"svc{i}") for i in range(4)]
    f = by_id(insights.compute(data, [], 0, 0, SETTINGS, NOW))["repeat_offender"]
    assert f["value"] == "60%" and "checkout" in f["headline"] and f["action"]["to"] == "/services/checkout"


def test_no_repeat_offender_when_incidents_are_spread_out():
    data = [inc(i, entity=f"svc{i}") for i in range(8)]
    assert "repeat_offender" not in by_id(insights.compute(data, [], 0, 0, SETTINGS, NOW))


def test_downtime_cost_uses_the_cost_per_hour_and_says_how_it_was_worked_out():
    data = [inc(1, open_h=2.0), inc(2, open_h=1.0), inc(3, age_d=40, open_h=50)]   # the 40-day-old one is outside 30 days
    f = by_id(insights.compute(data, [], 0, 0, SETTINGS, NOW))["downtime_cost"]
    assert f["value"] == "฿36,000" and "3.0 h" in f["basis"] and "12,000" in f["basis"]


def test_hours_saved_compare_the_ai_with_a_manual_investigation():
    data = [inc(i, analysis_s=60) for i in range(10)]          # 10 x (45 min - 1 min) = 440 min
    f = by_id(insights.compute(data, [], 0, 0, SETTINGS, NOW))["hours_saved"]
    assert f["value"] == "7.3 h" and "45 min" in f["basis"]


def test_coverage_gap_only_when_unmonitored_machines_sit_next_to_a_problem():
    out = by_id(insights.compute([inc(1)], [], 0, 6, SETTINGS, NOW))
    assert out["coverage_gap"]["value"] == 6 and out["coverage_gap"]["action"]["to"] == "/network"
    assert "coverage_gap" not in by_id(insights.compute([inc(1)], [], 0, 0, SETTINGS, NOW))


def test_runbook_reuse_and_rating_nudges():
    out = by_id(insights.compute([inc(i) for i in range(20)], feedback=[{"score": 5, "rca_correct": True}],
                                 runbook_uses=12, unmonitored_near_problems=0, settings=SETTINGS, now=NOW))
    assert out["runbook_reuse"]["value"] == 12
    assert out["rate_more"]["value"] == "1 of 20" and out["rate_more"]["tone"] == "info"


def test_weekly_trend_compares_this_week_with_last():
    data = [inc(i, age_d=1) for i in range(6)] + [inc(10 + i, age_d=9) for i in range(3)]
    f = by_id(insights.compute(data, [], 0, 0, SETTINGS, NOW))["weekly_trend"]
    assert f["value"] == "+100%" and f["tone"] == "bad"


def test_empty_history_gives_one_honest_finding_not_zeros():
    out = insights.compute([], [], 0, 0, SETTINGS, NOW)
    assert [x["id"] for x in out] == ["no_data"]


def test_route_reads_history_and_counts_unmonitored_machines_near_problems(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api import errors, routes_insights

    monkeypatch.setattr(routes_insights, "_history", lambda: ([inc(1, status="awaiting_approval")], [], 3))
    async def near():
        return 4
    monkeypatch.setattr(routes_insights, "_unmonitored_near_problems", near)
    monkeypatch.setattr(routes_insights.db, "settings", lambda: SETTINGS)
    app = FastAPI(); errors.install(app); app.include_router(routes_insights.router)
    body = TestClient(app).get("/api/v1/insights").json()
    ids = [f["id"] for f in body["findings"]]
    assert ids[0] == "approval_backlog" and "coverage_gap" in ids and "runbook_reuse" in ids
    assert body["assumptions"]["downtime_cost_per_hour"] == "12000"


def test_downtime_cost_counts_resolved_incidents_only_and_shortens_big_amounts():
    # a fix still waiting for approval is not an outage being priced (it has its own finding)
    data = [inc(1, open_h=2.0), inc(2, status="awaiting_approval", age_d=10)]
    f = by_id(insights.compute(data, [], 0, 0, SETTINGS, NOW))["downtime_cost"]
    assert f["value"] == "฿24,000" and "1 resolved" in f["detail"]
    big = by_id(insights.compute([inc(i, open_h=100) for i in range(5)], [], 0, 0, SETTINGS, NOW))["downtime_cost"]
    assert big["value"] == "฿6.0M"
