"""/api/v1/insights: what the incident history means for the business (see app/insights.py)."""
import time

from fastapi import APIRouter

from .. import db, insights

router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


def _history():
    incidents = db.q("SELECT id, entity_name, kind, status, severity, detected_at, resolved_at, analysis_ms FROM incidents")
    feedback = db.q("SELECT score, rca_correct FROM feedback")
    uses = db.val("SELECT coalesce(sum(uses), 0) FROM runbooks WHERE enabled") or 0
    return incidents, feedback, int(uses)


async def _unmonitored_near_problems() -> int:
    from .. import fleet, health, netseg
    segments, neighbors, hosts = netseg.load()
    problem_hosts = {h["name"] for h in await health.hosts_health() if h["status"] in ("problem", "down")}
    return sum(1 for r in fleet.recommend(segments, neighbors, hosts, problem_hosts) if any("active problem" in x for x in r["reasons"]))


@router.get("", summary="Findings from the incident history, each with its number, meaning, action and basis")
async def get_insights():
    incidents, feedback, uses = _history()
    s = db.settings()
    try:
        near = await _unmonitored_near_problems()
    except Exception:
        near = 0
    findings = insights.compute(incidents, feedback, uses, near, s, time.time())
    return {"findings": findings, "assumptions": {k: s.get(k) for k in ("downtime_cost_per_hour", "manual_rca_minutes", "currency")}}
