"""Demo data for an empty database, and a one-time import of the old SQLite file."""
import json
import os
import sqlite3
import time

from . import db, repo
from .db import J, T

SQLITE = os.environ.get("LEGACY_SQLITE", "/data/aiops.db")
PLATFORM_HOST = os.environ.get("PLATFORM_HOST", "cp26pt1")

DEMO = [  # service, display, owner, language, kind, containers, admin, entry
    ("edge-firewall", "Edge Firewall", "team-network", "nginx", "network", ["edge-fw"], [], "http://edge-fw:80/api/checkout"),
    ("edge-lb", "Edge Load Balancer", "team-network", "nginx", "network", ["edge-lb"], [], None),
    ("frontend", "Shop Frontend", "team-web", "python", "service", ["frontend-a", "frontend-b"],
     ["http://frontend-a:8000", "http://frontend-b:8000"], None),
    ("checkout", "Checkout Service", "team-orders", "python", "service", ["checkout"], ["http://checkout:8000"], None),
    ("payment", "Payment Service", "team-payments", "python", "service", ["payment"], ["http://payment:8000"], None),
    ("inventory", "Inventory Service", "team-catalog", "python", "service", ["inventory"], ["http://inventory:8000"], None),
]
COMMITS = {"frontend": "9f3c2e1", "checkout": "4b7d0a9", "payment": "c81e5f2", "inventory": "e2a94d7"}


def ensure_demo():
    """Idempotent: creates whatever demo rows are missing."""
    if not repo.host(PLATFORM_HOST):
        repo.upsert_host(PLATFORM_HOST, address="node-exporter:9100", os="Ubuntu 26.04", agent="node_exporter",
                         kind="server", environment="poc", owner="team-platform")
    for svc, disp, owner, lang, kind, conts, admin, entry in DEMO:
        if not repo.service(svc):
            repo.create_service(svc, display_name=disp, kind=kind, source="traced", language=lang, owner=owner,
                                repo=f"gitlab.sit.kmutt.ac.th/shop/{svc}", environment="poc", admin_urls=admin,
                                entry_url=entry, entry_method="POST" if entry else "GET")
        else:
            repo.update_service(svc, admin_urls=admin, entry_url=entry, entry_method="POST" if entry else "GET",
                                language=lang, kind=kind)
        for c in conts:
            repo.ensure_instance(svc, c, host=PLATFORM_HOST, container=c)
        if svc in COMMITS and not repo.deployments(svc, limit=1):
            repo.add_deployment(svc, "1.2.0", COMMITS[svc], "ci-pipeline", "release 1.2.0", ts=time.time() - 6 * 3600)


def _j(v, default):
    if v is None or v == "":
        return default
    try:
        return json.loads(v) if isinstance(v, str) else v
    except ValueError:
        return default


def migrate_sqlite() -> bool:
    """Copy the v1/v2 SQLite data (apps, hosts, deployments, incidents with their JSON blobs, runbooks,
    notifications, settings) into the normalized schema. Runs once, then renames the file."""
    if not os.path.exists(SQLITE) or db.val("SELECT count(*) FROM incidents"):
        return False
    src = sqlite3.connect(SQLITE)
    src.row_factory = sqlite3.Row
    rows = lambda t: [dict(r) for r in src.execute(f"SELECT * FROM {t}")]  # noqa: E731

    for k, v in ((r["key"], r["value"]) for r in rows("settings")):
        if k in db.DEFAULT_SETTINGS:
            db.set_setting(k, v)
    for h in rows("hosts"):
        agent = h.get("agent") or ("node_exporter" if (h["address"] or "").startswith("node-exporter") else "aiops-agent")
        repo.upsert_host(h["name"], address=h["address"] or "", os=h["os"] or "", agent=agent,
                         kind=h.get("kind") or "server", environment=h["environment"] or "production",
                         owner=h.get("owner") or "team-platform")
    for a in rows("apps"):
        if repo.service(a["service_name"]):
            continue
        conts = [c.strip() for c in (a["container"] or "").split(",") if c.strip()]
        admin = [u.strip() for u in (a["admin_url"] or "").split(",") if u.strip()]
        repo.create_service(a["service_name"], display_name=a["name"], kind=a.get("kind") or "service",
                            source="manual", language=a["language"], owner=a.get("owner") or a["team"],
                            repo=a["repo"] or "", environment=a["environment"] or "production", admin_urls=admin)
        for c in conts:
            repo.ensure_instance(a["service_name"], c, host=PLATFORM_HOST, container=c)
    for d in rows("deployments"):
        try:
            repo.add_deployment(d["service"], d["version"], d["commit_hash"], d["author"] or "", d["message"] or "",
                                d["profile"] or "healthy", ts=d["ts"])
        except KeyError:
            pass

    for i in rows("incidents"):
        sig, facts = _j(i["signal"], {}), _j(i["facts"], {})
        etype = i["entity_type"]
        sid = db.val("SELECT id FROM services WHERE service_name=%s", (i["entity"],)) if etype == "service" else None
        hid = db.val("SELECT id FROM hosts WHERE name=%s", (i["entity"],)) if etype == "host" else None
        db.ex("""INSERT INTO incidents(id, title, kind, severity, status, entity_type, service_id, host_id, entity_name,
                 owner_team_id, signal, facts, skill_id, skill_reason, path, root_cause, summary, confidence, llm_model,
                 llm_ok, analysis_ms, started_at, detected_at, analyzed_at, resolved_at)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
              (i["id"], i["title"], i["kind"], i["severity"] if i["severity"] in ("critical", "major") else "minor",
               i["status"], etype, sid, hid, i["entity"], repo.team_id(i.get("owner")), J(sig), J(facts),
               i["skill"], i["skill_reason"], i["path"], i["root_cause"], i["summary"], i["confidence"], i["llm_model"],
               None if i["llm_ok"] is None else bool(i["llm_ok"]), i["analysis_ms"], T(i["started_at"] or i["detected_at"]),
               T(i["detected_at"]), T(i["analyzed_at"]), T(i["resolved_at"])))
        for svc in sig.get("affected", []):
            repo.add_affected(i["id"], svc)
        for n, e in enumerate(_j(i.get("evidence"), [])):
            db.ex("INSERT INTO incident_evidence VALUES (%s,%s,%s)", (i["id"], n, e))
        for n, e in enumerate(_j(i.get("runbook"), [])):
            db.ex("INSERT INTO incident_runbook_steps VALUES (%s,%s,%s)", (i["id"], n, str(e)))
        for n, st in enumerate(_j(i["steps"], [])):
            data = {k: v for k, v in st.items() if k not in ("ts", "kind", "title", "detail", "ms")}
            db.ex("""INSERT INTO agent_steps(incident_id, seq, kind, title, detail, data, duration_ms, created_at)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                  (i["id"], n, st.get("kind", "info"), st.get("title", ""), st.get("detail"), J(data), st.get("ms"),
                   T(st.get("ts") or i["detected_at"])))
        cand_ids = {}
        for rank, c in enumerate(_j(i["candidates"], []) or ([_j(i["action"], None)] if i["action"] else [])):
            if not c:
                continue
            cid = db.val("""INSERT INTO remediation_candidates(incident_id, rank, action_type, params, label)
                            VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                         (i["id"], rank, c["type"], J(c.get("params", {})), c.get("label") or c["type"]))
            cand_ids[json.dumps([c["type"], c.get("params", {})], sort_keys=True)] = cid
            if c.get("dry_run"):
                repo.add_dry_run(cid, "proposal", {**c["dry_run"], "ts": c["dry_run"].get("ts") or i["analyzed_at"]})
        ex = _j(i["execution"], None)
        if ex:
            act = ex.get("action") or _j(i["action"], {}) or {}
            cid = cand_ids.get(json.dumps([act.get("type"), act.get("params", {})], sort_keys=True))
            pre = repo.add_dry_run(cid, "preflight", {**ex["preflight"], "ts": ex["preflight"].get("ts")}) \
                if cid and ex.get("preflight") else None
            aid = db.val("""INSERT INTO approvals(incident_id, candidate_id, decision, approver, owner_team_id, comment,
                            preflight_id, decided_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                         (i["id"], cid, "rejected" if ex.get("rejected") else "approved", ex.get("approver") or "unknown",
                          repo.team_id(ex.get("owner") or i.get("owner")), ex.get("comment") or "", pre, T(ex.get("ts"))))
            if ex.get("result"):
                v = ex.get("verification") or {}
                db.ex("""INSERT INTO executions(approval_id, ok, detail, executed_at, verified, verify_attempts, verified_at)
                         VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                      (aid, ex["result"]["ok"], ex["result"].get("detail", ""), T(ex.get("ts")), v.get("healthy"),
                       v.get("attempts"), T(v.get("ts"))))
        if i["score"]:
            repo.save_feedback(i["id"], i["score"], bool(i["rca_correct"] if i["rca_correct"] is not None else 1),
                               i["feedback"] or "")

    for r in rows("runbooks"):
        act = _j(r["action"], {"type": "manual", "params": {}})
        rid = repo.create_runbook(r["signature"], r["title"], r["kind"], r["skill"], r["root_cause"] or "",
                                  _j(r["runbook"], []), act, r["source_incident"])
        if rid:
            db.ex("UPDATE runbooks SET uses=%s, enabled=%s WHERE id=%s", (r["uses"], bool(r["enabled"]), rid))
            old_ids = [i["id"] for i in rows("incidents") if i["runbook_id"] == r["id"]]
            if old_ids:
                db.ex("UPDATE incidents SET runbook_id=%s WHERE id = ANY(%s)", (rid, old_ids))
    for n in rows("notifications"):
        db.ex("INSERT INTO notifications(incident_id, channel, event, status, payload, sent_at) VALUES (%s,%s,%s,%s,%s,%s)",
              (n["incident_id"] or None, n["channel"], n["event"], n["status"], J(_j(n["payload"], {})), T(n["ts"])))
    db.ex("SELECT setval('incidents_id_seq', (SELECT COALESCE(max(id), 1) FROM incidents))")
    src.close()
    os.rename(SQLITE, SQLITE + ".migrated")
    return True
