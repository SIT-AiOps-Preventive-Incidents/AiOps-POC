"""/api/v1/incidents - problems, their AI analysis, owner approvals and feedback."""
import asyncio
import time

from fastapi import APIRouter, Response

from .. import agent, db, detector, notify, remediation, repo, servicemap
from .errors import ApiError, not_found
from .schemas import ApprovalIn, FeedbackIn, IncidentPatch

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])
WAITING = ("awaiting_approval", "remediation_failed")


def _get(iid: int) -> dict:
    inc = repo.incident(iid)
    if not inc:
        raise not_found("incident", iid)
    return inc


@router.get("", summary="List incidents (status=open|closed)")
async def list_incidents(status: str | None = None, limit: int = 200):
    if status not in (None, "open", "closed"):
        raise ApiError(400, "status must be 'open' or 'closed'")
    return repo.list_incidents(status, min(limit, 500))


@router.get("/{iid}", summary="Incident with steps, candidates, dry runs, approval and feedback")
async def get_incident(iid: int):
    return _get(iid)


@router.patch("/{iid}", summary="Close an incident")
async def patch_incident(iid: int, body: IncidentPatch):
    inc = _get(iid)
    if inc["status"] in repo.CLOSED:
        raise ApiError(409, f"incident is already {inc['status']}")
    repo.set_incident(iid, status=body.status, resolved_at=time.time())
    return _get(iid)


@router.post("/{iid}/analyses", status_code=202, summary="Run the AI analysis again")
async def reanalyze(iid: int):
    inc = _get(iid)
    if inc["status"] in ("analyzing", "remediating", "verifying"):
        raise ApiError(409, f"cannot re-analyze while {inc['status']}")
    repo.reset_analysis(iid)
    asyncio.create_task(detector._safe_analyze(iid))
    return {"incident_id": iid, "status": "open"}


async def _verify(iid: int, approval_id: int):
    """Re-check the signal after the fix; the 1-minute rate window needs a few chances to come back clean."""
    await asyncio.sleep(db.fsetting("verify_after_s"))
    inc = repo.incident(iid)
    ok, attempts = False, 0
    for attempts in range(1, 6):
        ok = await detector.is_healthy(inc)
        if ok:
            break
        await asyncio.sleep(20)
    repo.record_verification(approval_id, ok, attempts)
    if ok:
        repo.set_incident(iid, status="resolved", resolved_at=time.time())
        detector.clear(inc["kind"], inc["entity"])
    else:
        repo.set_incident(iid, status="remediation_failed")
    await notify.send(iid, "resolved" if ok else "remediation_failed")


@router.post("/{iid}/approvals", status_code=201, summary="Owner approves (fix runs after a pre-flight dry run) or rejects")
async def decide(iid: int, body: ApprovalIn):
    inc = _get(iid)
    if inc["status"] not in WAITING:
        raise ApiError(409, f"incident is '{inc['status']}', not waiting for a decision")
    cands = inc["candidates"]
    cand = next((c for c in cands if c["id"] == body.candidate_id), None) if body.candidate_id else (cands[0] if cands else None)
    if body.candidate_id and not cand:
        raise not_found("candidate", body.candidate_id)

    if body.decision == "reject":
        repo.record_approval(iid, cand and cand["id"], "rejected", body.approver, inc["owner"], body.comment)
        repo.set_incident(iid, status="rejected", resolved_at=time.time())
        await notify.send(iid, "rejected")
        return _get(iid)

    if not body.owner_confirmed:
        raise ApiError(403, f"approval must come from the owner ({inc['owner'] or 'unassigned'})", code="owner_required")
    if not cand:
        raise ApiError(409, "incident has no remediation candidate")
    action = {"type": cand["type"], "params": cand["params"], "label": cand["label"]}
    # Pre-flight: the world may have changed since the agent's dry run - check again before touching anything.
    pre = await remediation.dry_run(action, (await servicemap.build()).get("edges", []))
    pre_id = repo.add_dry_run(cand["id"], "preflight", pre)
    if not pre["ok"]:
        failed = [c for c in pre["checks"] if not c["ok"]]
        raise ApiError(422, "pre-flight dry run failed - nothing was changed", code="preflight_failed",
                       details={"failed_checks": failed, "dry_run_id": pre_id})
    approval_id = repo.record_approval(iid, cand["id"], "approved", body.approver, inc["owner"], body.comment, pre_id)
    repo.set_incident(iid, status="remediating")
    try:
        res = await remediation.execute(action, iid, body.approver)
    except Exception as e:
        res = {"ok": False, "detail": f"{type(e).__name__}: {e}"}
    repo.record_execution(approval_id, res["ok"], res["detail"])
    if cand["type"] == "manual":
        repo.set_incident(iid, status="resolved", resolved_at=time.time())
    elif res["ok"]:
        repo.set_incident(iid, status="verifying")
        asyncio.create_task(_verify(iid, approval_id))
    else:
        repo.set_incident(iid, status="remediation_failed")
    return _get(iid)


@router.put("/{iid}/feedback", summary="Rate the analysis (Improve Score)")
async def put_feedback(iid: int, body: FeedbackIn, response: Response):
    """4-5 stars on a resolved incident saves it as a runbook; low scores lower a reused runbook
    (disabled below 2.5) and become lessons in the next prompt for the same skill."""
    inc = _get(iid)
    repo.save_feedback(iid, body.score, body.rca_correct, body.comment)
    message = "feedback saved"
    if inc["runbook_id"]:
        rb = repo.runbook(inc["runbook_id"])
        if rb and rb["ratings"] >= 2 and (rb["avg_score"] or 0) < 2.5:
            repo.set_runbook(rb["id"], enabled=False)
            message = f"RB-{rb['id']} turned off (average rating below 2.5)"
    elif body.score >= 4 and body.rca_correct and inc["action"] and inc["status"] in ("resolved", "verifying"):
        act = {"type": inc["action"]["type"], "params": inc["action"]["params"]}
        sig = agent.signature(inc["kind"], inc["facts"] or {}, act)
        rid = repo.create_runbook(sig, inc["title"], inc["kind"], inc["skill_id"], inc["root_cause"] or "",
                                  inc["runbook"], act, iid)
        if rid:
            repo.set_incident(iid, runbook_id=rid)
            message = f"saved to incident memory as RB-{rid}"
    return {"incident_id": iid, "message": message, "feedback": {"score": body.score, "rca_correct": body.rca_correct,
                                                                 "comment": body.comment}}
