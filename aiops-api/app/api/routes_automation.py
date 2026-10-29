"""Automation people write themselves: skills, skill sets, runbooks written by hand, playbooks (rules in automation.py)."""
from fastapi import APIRouter, Response

from .. import automation, automation_store as st
from .errors import ApiError, not_found

router = APIRouter(prefix="/api/v1", tags=["automation"])


def _check(errs: list[str]):
    if errs:
        raise ApiError(422, "; ".join(errs), details={"problems": errs})


@router.get("/automation/catalog", summary="What a skill, runbook or playbook can use: read-only tools, incident kinds, fix types")
async def catalog():
    return {"tools": automation.TOOL_CATALOG, "kinds": automation.KINDS, "fix_types": automation.FIX_TYPES,
            "severities": list(automation.SEVERITY)}


# ---------- skills ----------
@router.post("/skills", status_code=201, summary="Write a skill: incident kinds, read-only tools and instructions")
async def create_skill(body: dict):
    _check(automation.validate_skill(body))
    sid = automation.skill_id(body["name"])
    if st.skill(sid):
        raise ApiError(409, f"a skill named '{body['name']}' already exists")
    st.save_skill(sid, body, builtin=False)
    return {"id": sid}


@router.patch("/skills/{sid}", summary="Change a skill. Built-in ones: on/off and instructions only")
async def patch_skill(sid: str, body: dict):
    cur = st.skill(sid)
    if not cur:
        raise not_found("skill", sid)
    merged = {**cur, **body}
    if cur["builtin"]:
        st.save_skill(sid, {"enabled": bool(merged["enabled"]), "instructions": str(merged.get("instructions") or "")}, builtin=True)
    else:
        _check(automation.validate_skill(merged))
        st.save_skill(sid, merged, builtin=False)
    return st.skill(sid) or {"id": sid}


@router.delete("/skills/{sid}", status_code=204, summary="Delete a skill you wrote")
async def delete_skill(sid: str):
    cur = st.skill(sid)
    if not cur:
        raise not_found("skill", sid)
    if cur["builtin"]:
        raise ApiError(409, "built-in skills cannot be deleted; switch it off instead")
    st.delete_skill(sid)
    return Response(status_code=204)


# ---------- skill sets ----------
@router.get("/skill-sets", summary="Skill sets: which skills investigate which part of the estate")
async def list_sets():
    return st.skill_sets()


@router.post("/skill-sets", status_code=201, summary="Group skills for services or hosts matching a pattern")
async def create_set(body: dict):
    if not str(body.get("name") or "").strip() or not body.get("skills"):
        raise ApiError(422, "a skill set needs a name and at least one skill")
    return st.save_skill_set(body)


@router.patch("/skill-sets/{sid}", summary="Change a skill set")
async def patch_set(sid: int, body: dict):
    cur = next((s for s in st.skill_sets() if s["id"] == sid), None)
    if not cur:
        raise not_found("skill set", sid)
    return st.save_skill_set({**cur, **body}, sid)


@router.delete("/skill-sets/{sid}", status_code=204, summary="Delete a skill set")
async def delete_set(sid: int):
    st.delete_skill_set(sid)
    return Response(status_code=204)


# ---------- runbooks written by hand ----------
@router.post("/runbooks", status_code=201, summary="Write a runbook: kind + service + fix, with its steps")
async def create_runbook(body: dict):
    _check(automation.validate_runbook(body))
    if st.signature_taken(automation.runbook_signature(body)):
        raise ApiError(409, "a runbook for this kind, service and fix already exists; edit that one")
    return {"id": st.create_runbook(body)}


@router.put("/runbooks/{rid}", summary="Edit a runbook's title, cause, match and steps")
async def edit_runbook(rid: int, body: dict):
    _check(automation.validate_runbook(body))
    if st.signature_taken(automation.runbook_signature(body), rid):
        raise ApiError(409, "another runbook already covers this kind, service and fix")
    st.update_runbook(rid, body)
    return {"id": rid}


@router.delete("/runbooks/{rid}", status_code=204, summary="Delete a runbook")
async def delete_runbook(rid: int):
    st.delete_runbook(rid)
    return Response(status_code=204)


# ---------- playbooks ----------
@router.get("/playbooks", summary="Playbooks: what happens when an incident matches")
async def list_playbooks():
    return st.playbooks()


@router.post("/playbooks", status_code=201, summary="Write a playbook: a trigger, an owner team, an escalation")
async def create_playbook(body: dict):
    _check(automation.validate_playbook(body))
    return st.save_playbook(body)


@router.patch("/playbooks/{pid}", summary="Change a playbook")
async def patch_playbook(pid: int, body: dict):
    cur = next((p for p in st.playbooks() if p["id"] == pid), None)
    if not cur:
        raise not_found("playbook", pid)
    merged = {**cur, **body}
    _check(automation.validate_playbook(merged))
    return st.save_playbook(merged, pid)


@router.delete("/playbooks/{pid}", status_code=204, summary="Delete a playbook")
async def delete_playbook(pid: int):
    st.delete_playbook(pid)
    return Response(status_code=204)
