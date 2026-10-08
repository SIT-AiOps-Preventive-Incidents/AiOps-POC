"""Everything else under /api/v1: overview, deployments, runbooks, skills, teams, notifications, settings,
demo scenarios and the platform's own health."""
import os
import random

import httpx
from fastapi import APIRouter, Response

from .. import db, detector, health, llm, notify, remediation, repo
from .. import telemetry as tm
from .errors import ApiError, not_found
from .schemas import DeploymentIn, RunbookPatch

router = APIRouter(prefix="/api/v1")
GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3001")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8080")
OTLP_PUBLIC = os.environ.get("OTLP_PUBLIC_URL") or PUBLIC_URL.rsplit(":", 1)[0] + ":4318"


# ---------------- overview & platform health ----------------
@router.get("/overview", tags=["overview"], summary="Everything the home page needs in one call")
async def overview():
    services = await health.services_health(("service", "network"))
    discovered = await health.services_health(("process", "external"))
    hosts = await health.hosts_health()
    open_ = repo.list_incidents("open", 50)
    return {"services": services, "discovered": discovered, "hosts": hosts, "open_problems": open_,
            "kpi": repo.kpis(), "detector": detector.LAST_RUN, "llm": await llm.status(),
            "grafana_url": GRAFANA_URL, "otlp_endpoint": OTLP_PUBLIC, "public_url": PUBLIC_URL}


@router.get("/health", tags=["overview"], summary="Liveness of the platform's dependencies")
async def platform_health(response: Response):
    checks = {"database": False, "prometheus": False, "llm": False}
    try:
        checks["database"] = db.val("SELECT 1") == 1
    except Exception:
        pass
    checks["prometheus"] = (await tm.prom_value("vector(1)")) == 1
    checks["llm"] = (await llm.status()).get("up", False)
    if not all(checks.values()):
        response.status_code = 503
    return {"ok": all(checks.values()), "checks": checks}


# ---------------- deployments ----------------
BAD_PROFILES = {
    "payment": {"error_rate": 0.45,
                "error_msg": "TypeError: 'NoneType' object is not subscriptable at discount.py:42 in apply_member_discount()"},
    "inventory": {"error_rate": 0.4, "error_msg": "KeyError: 'warehouse_id' at stock.py:88 in reserve_items()"},
    "checkout": {"error_rate": 0.4, "error_msg": "ValueError: invalid shipping zone 'TH-99' at shipping.py:17"},
    "frontend": {"error_rate": 0.3, "error_msg": "TemplateError: undefined variable 'promo_banner'"},
}


@router.get("/deployments", tags=["deployments"], summary="Recent deployments")
async def list_deployments(service: str | None = None, limit: int = 100):
    return repo.deployments(service, limit=min(limit, 500))


@router.post("/deployments", status_code=201, tags=["deployments"], summary="Called by CI after a deploy")
async def create_deployment(body: DeploymentIn):
    if not repo.service(body.service):
        raise not_found("service", body.service)
    did = repo.add_deployment(body.service, body.version, body.commit, body.author, body.message, body.profile or "healthy")
    warning = None
    if remediation.admin_urls(body.service):  # demo apps also switch version at runtime
        state = {"version": body.version, "commit": body.commit, "profile": body.profile or "healthy", "error_rate": 0,
                 "error_msg": ""}
        if body.profile == "bad":
            state.update(BAD_PROFILES.get(body.service, BAD_PROFILES["payment"]))
        try:
            await remediation.set_app_state(body.service, state)
        except Exception as e:
            warning = f"recorded, but could not reach the service: {e}"
    return {"id": did, "service": body.service, "version": body.version, "commit": body.commit, "warning": warning}


# ---------------- AI: runbooks, skills ----------------
@router.get("/runbooks", tags=["ai"], summary="Incident memory")
async def list_runbooks():
    return repo.list_runbooks()


@router.patch("/runbooks/{rid}", tags=["ai"], summary="Turn a runbook on or off")
async def patch_runbook(rid: int, body: RunbookPatch):
    if not repo.runbook(rid):
        raise not_found("runbook", rid)
    repo.set_runbook(rid, enabled=body.enabled)
    return repo.runbook(rid)


@router.get("/skills", tags=["ai"], summary="Skills with usage and rating")
async def list_skills():
    out = []
    for s in repo.skill_stats():
        out.append({**s, "lessons": repo.lessons(s["id"])})
    return out


# ---------------- teams & notifications ----------------
@router.get("/teams", tags=["teams"], summary="Owner teams")
async def list_teams():
    return repo.list_teams()


@router.get("/notifications", tags=["notifications"], summary="Messages sent to Microsoft Teams")
async def list_notifications(limit: int = 100):
    return repo.list_notifications(min(limit, 500))


@router.post("/notifications/test", status_code=201, tags=["notifications"], summary="Send a test card to Teams")
async def test_notification():
    fake = {"id": 0, "title": "Test notification from AIOps One", "entity_type": "service", "entity": "demo",
            "severity": "minor", "status": "test", "owner": "-"}
    await notify.send(fake, "detected")
    return repo.list_notifications(1)[0]


# ---------------- settings ----------------
@router.get("/settings", tags=["settings"])
async def get_settings():
    return {"settings": db.settings(), "llm": await llm.status(), "public_url": PUBLIC_URL, "grafana_url": GRAFANA_URL,
            "otlp_endpoint": OTLP_PUBLIC}


@router.patch("/settings", tags=["settings"], summary="Change one or more settings")
async def patch_settings(body: dict):
    unknown = [k for k in body if k not in db.DEFAULT_SETTINGS]
    if unknown:
        raise ApiError(422, "unknown setting", details={"keys": unknown})
    for k, v in body.items():
        db.set_setting(k, v)
    return db.settings()


# ---------------- demo scenarios ----------------
SCENARIOS = ["bad_deploy", "instance_fault", "slow_db", "cpu_hog", "brute_force", "reset"]


async def _post(url: str, body: dict):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(url, json=body)
        r.raise_for_status()
        return r.json()


@router.get("/scenarios", tags=["demo"])
async def list_scenarios():
    return SCENARIOS


@router.post("/scenarios/{scenario}/runs", status_code=202, tags=["demo"], summary="Inject a fault (or reset)")
async def run_scenario(scenario: str):
    if scenario not in SCENARIOS:
        raise not_found("scenario", scenario)
    if scenario == "bad_deploy":
        return await create_deployment(DeploymentIn(service="payment", version="1.3.0", commit="%07x" % random.randrange(16**7),
                                                    author="dev-somchai", message="feat(payment): apply member discount at charge time",
                                                    profile="bad"))
    if scenario == "slow_db":
        await remediation.set_app_state("inventory", {
            "latency_ms": 1600, "latency_msg": "slow query: SELECT * FROM stock WHERE sku=$1 took {ms}ms - "
                                               "connection pool exhausted (20/20 in use, 37 waiting)"})
    elif scenario == "cpu_hog":
        await _post("http://payment:8000/admin/cpu", {"seconds": 600, "workers": 3})
    elif scenario == "brute_force":
        await _post("http://loadgen:8000/admin/attack", {"seconds": 240, "ip": "203.0.113.77"})
    elif scenario == "instance_fault":
        await _post("http://frontend-b:8000/admin/state", {
            "error_rate": 0.5, "error_msg": "RedisTimeoutError: session cache unreachable from frontend-b "
                                            "(connection pool stuck after network blip)"})
    elif scenario == "reset":
        with open(remediation.BLOCKLIST, "w") as f:
            f.write("# managed by AIOps remediation (owner-approved block_ip actions)\n")
        await tm.container_exec(remediation.FW_CONTAINER, ["nginx", "-s", "reload"])
        for s in repo.list_services(("service",)):
            if s["admin_urls"]:
                try:
                    await remediation.set_app_state(s["service_name"], {"error_rate": 0, "error_msg": "", "latency_ms": 0,
                                                                        "latency_msg": "", "blocked_ips": []})
                except Exception:
                    pass
        try:
            await _post("http://loadgen:8000/admin/attack", {"seconds": 0})
        except Exception:
            pass
    return {"scenario": scenario, "status": "started" if scenario != "reset" else "reset"}
