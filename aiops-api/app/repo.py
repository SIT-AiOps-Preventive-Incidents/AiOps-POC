"""Repository layer: every SQL statement the app runs, grouped by aggregate.

Callers get plain dicts shaped for the API (epoch-second timestamps, names instead of ids).
"""
import time

from . import db
from .db import J, T

# =====================================================================================
# teams
# =====================================================================================
def team_id(name: str | None) -> int | None:
    name = (name or "").strip()
    if not name:
        return None
    db.ex("INSERT INTO teams(name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (name,))
    return db.val("SELECT id FROM teams WHERE name=%s", (name,))


def list_teams() -> list[dict]:
    return db.q("SELECT t.id, t.name, t.contact, "
                "(SELECT count(*) FROM services s WHERE s.team_id=t.id) AS services, "
                "(SELECT count(*) FROM hosts h WHERE h.team_id=t.id) AS hosts FROM teams t ORDER BY t.name")


# =====================================================================================
# services
# =====================================================================================
_SVC = """SELECT s.*, t.name AS owner,
  COALESCE((SELECT array_agg(DISTINCT h.name) FROM service_instances i JOIN hosts h ON h.id=i.host_id
            WHERE i.service_id=s.id), '{}') AS hosts,
  COALESCE((SELECT json_agg(json_build_object('name', i.name, 'host', h.name, 'container', i.container,
                                              'pid', i.pid, 'port', i.port, 'last_seen', i.last_seen) ORDER BY i.name)
            FROM service_instances i LEFT JOIN hosts h ON h.id=i.host_id WHERE i.service_id=s.id), '[]') AS instances
FROM services s LEFT JOIN teams t ON t.id=s.team_id"""


def _svc(r: dict | None) -> dict | None:
    if r:
        for i in r.get("instances") or []:
            if isinstance(i.get("last_seen"), str):
                try:
                    import datetime as dt
                    i["last_seen"] = dt.datetime.fromisoformat(i["last_seen"]).timestamp()
                except ValueError:
                    pass
    return r


def service(name: str) -> dict | None:
    return _svc(db.one(_SVC + " WHERE s.service_name=%s", (name,)))


def service_by_id(sid: int) -> dict | None:
    return _svc(db.one(_SVC + " WHERE s.id=%s", (sid,)))


def list_services(kinds: tuple = ("service", "network", "process")) -> list[dict]:
    return [_svc(r) for r in db.q(_SVC + " WHERE s.kind = ANY(%s) ORDER BY s.kind DESC, s.service_name", (list(kinds),))]


def create_service(service_name: str, display_name: str = "", kind: str = "service", source: str = "manual",
                   language: str | None = None, owner: str | None = None, repo: str = "", environment: str = "production",
                   admin_urls: list | None = None, entry_url: str | None = None, entry_method: str = "GET") -> dict:
    db.ex("""INSERT INTO services(service_name, display_name, kind, source, language, team_id, repo, environment,
             admin_urls, entry_url, entry_method) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
          (service_name, display_name or service_name, kind, source, language, team_id(owner), repo, environment,
           admin_urls or [], entry_url, entry_method))
    return service(service_name)


_SVC_FIELDS = {"display_name", "kind", "source", "language", "repo", "environment", "admin_urls", "entry_url", "entry_method"}


def update_service(name: str, **fields) -> dict | None:
    if "owner" in fields:
        fields["team_id"] = team_id(fields.pop("owner"))
    cols = {k: v for k, v in fields.items() if k in _SVC_FIELDS | {"team_id"}}
    if cols:
        sets = ", ".join(f"{k}=%s" for k in cols)
        db.ex(f"UPDATE services SET {sets} WHERE service_name=%s", (*cols.values(), name))
    return service(name)


def delete_service(name: str) -> bool:
    return db.val("DELETE FROM services WHERE service_name=%s RETURNING id", (name,)) is not None


def ensure_instance(service_name: str, name: str, host: str | None = None, container: str | None = None,
                    pid: int | None = None, port: int | None = None):
    sid = db.val("SELECT id FROM services WHERE service_name=%s", (service_name,))
    hid = db.val("SELECT id FROM hosts WHERE name=%s", (host,)) if host else None
    if sid:
        db.ex("""INSERT INTO service_instances(service_id, host_id, name, container, pid, port, last_seen)
                 VALUES (%s,%s,%s,%s,%s,%s, now())
                 ON CONFLICT (service_id, name) DO UPDATE SET host_id=COALESCE(EXCLUDED.host_id, service_instances.host_id),
                   container=COALESCE(EXCLUDED.container, service_instances.container),
                   pid=EXCLUDED.pid, port=EXCLUDED.port, last_seen=now()""",
              (sid, hid, name, container, pid, port))


def containers_of(service_name: str) -> list[str]:
    rows = db.q("""SELECT i.container FROM service_instances i JOIN services s ON s.id=i.service_id
                   WHERE s.service_name=%s AND i.container IS NOT NULL ORDER BY i.name""", (service_name,))
    return [r["container"] for r in rows] or [service_name]


def admin_urls(service_name: str) -> list[str]:
    return db.val("SELECT admin_urls FROM services WHERE service_name=%s", (service_name,)) or []


# =====================================================================================
# hosts
# =====================================================================================
_HOST = "SELECT h.*, t.name AS owner FROM hosts h LEFT JOIN teams t ON t.id=h.team_id"


def host(name: str) -> dict | None:
    return db.one(_HOST + " WHERE h.name=%s", (name,))


def list_hosts() -> list[dict]:
    return db.q(_HOST + " ORDER BY h.name")


def upsert_host(name: str, **f) -> dict:
    owner = f.pop("owner", None)
    tid = team_id(owner) if owner else None
    cols = {k: v for k, v in f.items() if k in {"address", "os", "arch", "agent", "kind", "environment", "ip_addresses"}}
    existing = host(name)
    if existing:
        if cols:
            db.ex(f"UPDATE hosts SET {', '.join(f'{k}=%s' for k in cols)} WHERE name=%s", (*cols.values(), name))
        if tid:
            db.ex("UPDATE hosts SET team_id=%s WHERE name=%s", (tid, name))
    else:
        cols["team_id"] = tid or team_id("team-platform")
        names = ", ".join(["name", *cols])
        db.ex(f"INSERT INTO hosts({names}) VALUES ({', '.join(['%s'] * (len(cols) + 1))})", (name, *cols.values()))
    return host(name)


def delete_host(name: str) -> bool:
    return db.val("DELETE FROM hosts WHERE name=%s RETURNING id", (name,)) is not None


def host_agent(name: str) -> str:
    return db.val("SELECT agent FROM hosts WHERE name=%s", (name,)) or "node_exporter"


# =====================================================================================
# deployments
# =====================================================================================
def add_deployment(service_name: str, version: str, commit: str, author: str = "", message: str = "",
                   profile: str = "healthy", ts: float | None = None) -> int:
    sid = db.val("SELECT id FROM services WHERE service_name=%s", (service_name,))
    if not sid:
        raise KeyError(service_name)
    return db.val("""INSERT INTO deployments(service_id, version, commit_hash, author, message, profile, deployed_at)
                     VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                  (sid, version, commit, author, message, profile, T(ts or time.time())))


_DEP = """SELECT d.id, s.service_name AS service, d.version, d.commit_hash, d.author, d.message, d.profile,
          d.deployed_at AS ts FROM deployments d JOIN services s ON s.id=d.service_id"""


def deployments(service_name: str | None = None, since: float | None = None, limit: int = 100) -> list[dict]:
    where, args = [], []
    if service_name:
        where.append("s.service_name=%s"); args.append(service_name)
    if since:
        where.append("d.deployed_at >= %s"); args.append(T(since))
    sql = _DEP + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY d.deployed_at DESC LIMIT %s"
    return db.q(sql, (*args, limit))


# =====================================================================================
# skills
# =====================================================================================
def seed_skills(skills: dict):
    for k, s in skills.items():
        db.ex("""INSERT INTO skills(id, name, category, description) VALUES (%s,%s,%s,%s)
                 ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, category=EXCLUDED.category,
                 description=EXCLUDED.description""", (k, s["name"], s["category"], s["description"]))
        db.ex("DELETE FROM skill_tools WHERE skill_id=%s", (k,))
        for i, t in enumerate(s["tools"]):
            db.ex("INSERT INTO skill_tools(skill_id, seq, tool) VALUES (%s,%s,%s)", (k, i, t))


def skill_stats() -> list[dict]:
    return db.q("""SELECT sk.id, sk.name, sk.category, sk.description,
        (SELECT array_agg(tool ORDER BY seq) FROM skill_tools WHERE skill_id=sk.id) AS tools,
        count(i.id) AS runs, round(avg(f.score)::numeric, 2) AS avg_score,
        round((avg(CASE WHEN f.rca_correct THEN 1 ELSE 0 END) FILTER (WHERE f.id IS NOT NULL))::numeric, 2) AS accuracy,
        round((avg(i.analysis_ms) / 1000.0)::numeric, 1) AS avg_analysis_s
      FROM skills sk LEFT JOIN incidents i ON i.skill_id=sk.id LEFT JOIN feedback f ON f.incident_id=i.id
      GROUP BY sk.id ORDER BY sk.category, sk.name""")


def lessons(skill_id: str) -> list[str]:
    return [r["comment"] for r in db.q("""SELECT f.comment FROM feedback f JOIN incidents i ON i.id=f.incident_id
             WHERE i.skill_id=%s AND f.score <= 3 AND f.comment <> '' ORDER BY f.created_at DESC LIMIT 3""", (skill_id,))]


# =====================================================================================
# incidents
# =====================================================================================
_INC = """SELECT i.*, t.name AS owner, s.service_name AS service, h.name AS host, i.entity_name AS entity,
  f.score, f.rca_correct, f.comment AS feedback
FROM incidents i LEFT JOIN teams t ON t.id=i.owner_team_id LEFT JOIN services s ON s.id=i.service_id
LEFT JOIN hosts h ON h.id=i.host_id LEFT JOIN feedback f ON f.incident_id=i.id"""
CLOSED = ("resolved", "rejected", "closed")


def create_incident(title: str, kind: str, severity: str, entity_type: str, entity: str, signal: dict,
                    started_at: float, owner: str | None = None) -> int:
    sid = db.val("SELECT id FROM services WHERE service_name=%s", (entity,)) if entity_type == "service" else None
    hid = db.val("SELECT id FROM hosts WHERE name=%s", (entity,)) if entity_type == "host" else None
    return db.val("""INSERT INTO incidents(title, kind, severity, status, entity_type, service_id, host_id, entity_name,
                     owner_team_id, signal, started_at) VALUES (%s,%s,%s,'open',%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                  (title, kind, severity, entity_type, sid, hid, entity, team_id(owner), J(signal), T(started_at)))


_INC_FIELDS = {"title", "status", "skill_id", "skill_reason", "path", "root_cause", "summary", "confidence", "llm_model",
               "llm_ok", "analysis_ms", "runbook_id", "facts", "signal"}
_INC_TS = {"analyzed_at", "resolved_at"}


def set_incident(iid: int, **f):
    if "owner" in f:
        f["owner_team_id"] = team_id(f.pop("owner"))
    cols, args = [], []
    for k, v in f.items():
        if k in _INC_FIELDS | {"owner_team_id"}:
            cols.append(f"{k}=%s"); args.append(J(v) if k in ("facts", "signal") else v)
        elif k in _INC_TS:
            cols.append(f"{k}=%s"); args.append(T(v))
    if cols:
        db.ex(f"UPDATE incidents SET {', '.join(cols)} WHERE id=%s", (*args, iid))


def incident_row(iid: int) -> dict | None:
    return db.one(_INC + " WHERE i.id=%s", (iid,))


def open_incident(entity: str, kind: str) -> dict | None:
    return db.one(_INC + " WHERE i.entity_name=%s AND i.kind=%s AND i.status <> ALL(%s) ORDER BY i.id DESC LIMIT 1",
                  (entity, kind, list(CLOSED)))


def related_incident(kind: str, since: float) -> dict | None:
    return db.one(_INC + " WHERE i.kind=%s AND i.status <> ALL(%s) AND i.detected_at > %s ORDER BY i.id DESC LIMIT 1",
                  (kind, list(CLOSED), T(since)))


def add_affected(iid: int, service_name: str):
    sid = db.val("SELECT id FROM services WHERE service_name=%s", (service_name,))
    if sid:
        db.ex("INSERT INTO incident_affected_services VALUES (%s,%s) ON CONFLICT DO NOTHING", (iid, sid))


def list_incidents(status: str | None = None, limit: int = 200) -> list[dict]:
    where = ""
    if status == "open":
        where = " WHERE i.status <> ALL(%s)"
    elif status == "closed":
        where = " WHERE i.status = ANY(%s)"
    sql = f"""SELECT x.*, c.label AS action_label, c.action_type FROM ({_INC}{where}) x
              LEFT JOIN remediation_candidates c ON c.incident_id=x.id AND c.rank=0
              ORDER BY x.id DESC LIMIT %s"""
    rows = db.q(sql, ((list(CLOSED), limit) if where else (limit,)))
    for r in rows:
        r.pop("facts", None)
    return rows


# ---- agent steps ----
def add_step(iid: int, kind: str, title: str, detail: str | None = None, data: dict | None = None,
             duration_ms: int | None = None) -> int:
    return db.val("""INSERT INTO agent_steps(incident_id, seq, kind, title, detail, data, duration_ms)
                     VALUES (%s, COALESCE((SELECT max(seq)+1 FROM agent_steps WHERE incident_id=%s), 0), %s,%s,%s,%s,%s)
                     RETURNING id""", (iid, iid, kind, title, detail, J(data or {}), duration_ms))


def update_step(step_id: int, data: dict | None = None, detail: str | None = None, duration_ms: int | None = None):
    db.ex("""UPDATE agent_steps SET data = data || %s, detail=COALESCE(%s, detail),
             duration_ms=COALESCE(%s, duration_ms) WHERE id=%s""", (J(data or {}), detail, duration_ms, step_id))


def reset_analysis(iid: int):
    with db.tx() as c:
        for t in ("agent_steps", "incident_evidence", "incident_runbook_steps", "remediation_candidates"):
            c.execute(f"DELETE FROM {t} WHERE incident_id=%s", (iid,))
        c.execute("""UPDATE incidents SET status='open', root_cause=NULL, summary=NULL, confidence=NULL, path=NULL,
                     analyzed_at=NULL, facts='{}' WHERE id=%s""", (iid,))


# ---- candidates & dry runs ----
def add_dry_run(candidate_id: int, phase: str, dr: dict) -> int:
    with db.tx() as c:
        did = c.execute("INSERT INTO dry_runs(candidate_id, phase, ok, impact, ran_at) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                        (candidate_id, phase, dr["ok"], dr.get("impact", ""), T(dr.get("ts")))).fetchone()["id"]
        for i, ch in enumerate(dr.get("checks", [])):
            c.execute("INSERT INTO dry_run_checks VALUES (%s,%s,%s,%s,%s)", (did, i, ch["name"], ch["ok"], ch.get("detail", "")))
        for i, ch in enumerate(dr.get("changes", [])):
            c.execute("INSERT INTO dry_run_changes VALUES (%s,%s,%s)", (did, i, ch))
    return did


def dry_run(did: int | None) -> dict | None:
    if not did:
        return None
    d = db.one("SELECT id, phase, ok, impact, ran_at AS ts FROM dry_runs WHERE id=%s", (did,))
    if d:
        d["checks"] = db.q("SELECT name, ok, detail FROM dry_run_checks WHERE dry_run_id=%s ORDER BY seq", (did,))
        d["changes"] = [r["change"] for r in db.q("SELECT change FROM dry_run_changes WHERE dry_run_id=%s ORDER BY seq", (did,))]
    return d


def candidates(iid: int) -> list[dict]:
    rows = db.q("""SELECT c.id, c.rank, c.action_type AS type, c.params, c.label,
                   (SELECT id FROM dry_runs d WHERE d.candidate_id=c.id AND d.phase='proposal' ORDER BY id DESC LIMIT 1) AS dr
                   FROM remediation_candidates c WHERE c.incident_id=%s ORDER BY c.rank""", (iid,))
    for r in rows:
        r["dry_run"] = dry_run(r.pop("dr"))
    return rows


def save_analysis(iid: int, fields: dict, evidence: list[str], runbook: list[str], cands: list[dict]):
    """Persist one finished analysis: incident fields, evidence, runbook and candidates with their dry runs."""
    with db.tx() as c:
        for t in ("incident_evidence", "incident_runbook_steps", "remediation_candidates"):
            c.execute(f"DELETE FROM {t} WHERE incident_id=%s", (iid,))
        for i, e in enumerate(evidence):
            c.execute("INSERT INTO incident_evidence VALUES (%s,%s,%s)", (iid, i, e))
        for i, s in enumerate(runbook):
            c.execute("INSERT INTO incident_runbook_steps VALUES (%s,%s,%s)", (iid, i, s))
        ids = []
        for rank, cd in enumerate(cands):
            ids.append(c.execute("""INSERT INTO remediation_candidates(incident_id, rank, action_type, params, label)
                                    VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                                 (iid, rank, cd["type"], J(cd.get("params", {})), cd["label"])).fetchone()["id"])
    for cid, cd in zip(ids, cands):
        if cd.get("dry_run"):
            add_dry_run(cid, "proposal", cd["dry_run"])
    set_incident(iid, **fields)


# ---- approvals / executions ----
def record_approval(iid: int, candidate_id: int | None, decision: str, approver: str, owner: str | None,
                    comment: str = "", preflight_id: int | None = None) -> int:
    return db.val("""INSERT INTO approvals(incident_id, candidate_id, decision, approver, owner_team_id, comment, preflight_id)
                     VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                  (iid, candidate_id, decision, approver, team_id(owner), comment, preflight_id))


def record_execution(approval_id: int, ok: bool, detail: str) -> int:
    return db.val("INSERT INTO executions(approval_id, ok, detail) VALUES (%s,%s,%s) RETURNING id", (approval_id, ok, detail))


def record_verification(approval_id: int, healthy: bool, attempts: int):
    db.ex("UPDATE executions SET verified=%s, verify_attempts=%s, verified_at=now() WHERE approval_id=%s",
          (healthy, attempts, approval_id))


def latest_approval(iid: int) -> dict | None:
    a = db.one("""SELECT a.id, a.decision, a.approver, t.name AS owner, a.comment, a.decided_at, a.candidate_id,
                  a.preflight_id, e.ok AS exec_ok, e.detail AS exec_detail, e.executed_at, e.verified, e.verify_attempts,
                  e.verified_at FROM approvals a LEFT JOIN teams t ON t.id=a.owner_team_id
                  LEFT JOIN executions e ON e.approval_id=a.id WHERE a.incident_id=%s ORDER BY a.id DESC LIMIT 1""", (iid,))
    if not a:
        return None
    a["preflight"] = dry_run(a.pop("preflight_id"))
    a["execution"] = None if a["exec_ok"] is None else {
        "ok": a.pop("exec_ok"), "detail": a.pop("exec_detail"), "executed_at": a.pop("executed_at"),
        "verified": a.pop("verified"), "verify_attempts": a.pop("verify_attempts"), "verified_at": a.pop("verified_at")}
    for k in ("exec_ok", "exec_detail", "executed_at", "verified", "verify_attempts", "verified_at"):
        a.pop(k, None)
    return a


def incident(iid: int) -> dict | None:
    """Full incident aggregate for the detail page and for the agent."""
    inc = incident_row(iid)
    if not inc:
        return None
    inc["affected"] = [r["service_name"] for r in db.q("""SELECT s.service_name FROM incident_affected_services a
                        JOIN services s ON s.id=a.service_id WHERE a.incident_id=%s ORDER BY 1""", (iid,))]
    inc["evidence"] = [r["text"] for r in db.q("SELECT text FROM incident_evidence WHERE incident_id=%s ORDER BY seq", (iid,))]
    inc["runbook"] = [r["text"] for r in db.q("SELECT text FROM incident_runbook_steps WHERE incident_id=%s ORDER BY seq", (iid,))]
    inc["steps"] = db.q("""SELECT id, seq, kind, title, detail, data, duration_ms, created_at AS ts FROM agent_steps
                           WHERE incident_id=%s ORDER BY seq""", (iid,))
    inc["candidates"] = candidates(iid)
    inc["approval"] = latest_approval(iid)
    chosen = next((c for c in inc["candidates"] if inc["approval"] and c["id"] == inc["approval"]["candidate_id"]), None)
    inc["action"] = chosen or (inc["candidates"][0] if inc["candidates"] else None)
    inc["notifications"] = db.q("SELECT id, event, status, sent_at AS ts FROM notifications WHERE incident_id=%s ORDER BY id", (iid,))
    return inc


def save_feedback(iid: int, score: int, rca_correct: bool, comment: str):
    db.ex("""INSERT INTO feedback(incident_id, score, rca_correct, comment) VALUES (%s,%s,%s,%s)
             ON CONFLICT (incident_id) DO UPDATE SET score=EXCLUDED.score, rca_correct=EXCLUDED.rca_correct,
             comment=EXCLUDED.comment, created_at=now()""", (iid, score, rca_correct, comment))


def kpis() -> dict:
    r = db.one("""SELECT count(*) FILTER (WHERE status <> ALL(%s)) AS open,
        count(*) AS total, count(*) FILTER (WHERE status='awaiting_approval') AS awaiting_approval,
        avg(extract(epoch FROM detected_at - started_at)) AS mttd_s,
        avg(extract(epoch FROM analyzed_at - detected_at)) AS mtta_s,
        avg(extract(epoch FROM resolved_at - detected_at)) FILTER (WHERE status='resolved') AS mttr_s FROM incidents""",
               (list(CLOSED),))
    r["avg_score"] = db.val("SELECT round(avg(score)::numeric, 1) FROM feedback")
    return {k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()}


# =====================================================================================
# runbooks
# =====================================================================================
_RB = """SELECT r.*, (SELECT array_agg(text ORDER BY seq) FROM runbook_steps WHERE runbook_id=r.id) AS steps,
  (SELECT round(avg(f.score)::numeric, 2) FROM feedback f JOIN incidents i ON i.id=f.incident_id
   WHERE i.runbook_id=r.id) AS avg_score,
  (SELECT count(*) FROM feedback f JOIN incidents i ON i.id=f.incident_id WHERE i.runbook_id=r.id) AS ratings
FROM runbooks r"""


def runbook_by_signature(sig: str) -> dict | None:
    return db.one(_RB + " WHERE r.signature=%s AND r.enabled", (sig,))


def runbook(rid: int) -> dict | None:
    return db.one(_RB + " WHERE r.id=%s", (rid,))


def list_runbooks() -> list[dict]:
    return db.q(_RB + " ORDER BY r.id DESC")


def create_runbook(sig: str, title: str, kind: str, skill_id: str | None, root_cause: str, steps: list[str],
                   action: dict, source_incident: int) -> int | None:
    if db.val("SELECT id FROM runbooks WHERE signature=%s", (sig,)):
        return None
    with db.tx() as c:
        rid = c.execute("""INSERT INTO runbooks(signature, title, kind, skill_id, root_cause, action_type, action_params,
                           source_incident_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (sig, title, kind, skill_id, root_cause, action["type"], J(action.get("params", {})),
                         source_incident)).fetchone()["id"]
        for i, s in enumerate(steps):
            c.execute("INSERT INTO runbook_steps VALUES (%s,%s,%s)", (rid, i, s))
    return rid


def set_runbook(rid: int, **f):
    if "enabled" in f:
        db.ex("UPDATE runbooks SET enabled=%s, updated_at=now() WHERE id=%s", (bool(f["enabled"]), rid))
    if f.get("use"):
        db.ex("UPDATE runbooks SET uses=uses+1, updated_at=now() WHERE id=%s", (rid,))


# =====================================================================================
# notifications
# =====================================================================================
def add_notification(iid: int | None, event: str, status: str, payload: dict, channel: str = "teams"):
    db.ex("INSERT INTO notifications(incident_id, channel, event, status, payload) VALUES (%s,%s,%s,%s,%s)",
          (iid if iid else None, channel, event, status, J(payload)))


def list_notifications(limit: int = 100) -> list[dict]:
    return db.q("SELECT id, sent_at AS ts, channel, incident_id, event, status FROM notifications ORDER BY id DESC LIMIT %s",
                (limit,))


# =====================================================================================
# discovered topology (host agent inventory)
# =====================================================================================
def upsert_connection(src: str, dst: str, observed_by: str | None):
    s = db.val("SELECT id FROM services WHERE service_name=%s", (src,))
    d = db.val("SELECT id FROM services WHERE service_name=%s", (dst,))
    h = db.val("SELECT id FROM hosts WHERE name=%s", (observed_by,)) if observed_by else None
    if s and d and s != d:
        db.ex("""INSERT INTO connections(src_service_id, dst_service_id, observed_by) VALUES (%s,%s,%s)
                 ON CONFLICT (src_service_id, dst_service_id) DO UPDATE SET samples=connections.samples+1, last_seen=now()""",
              (s, d, h))


def discovered_edges(max_age_s: int = 600) -> list[dict]:
    return db.q("""SELECT a.service_name AS "from", b.service_name AS "to", c.samples, c.last_seen
                   FROM connections c JOIN services a ON a.id=c.src_service_id JOIN services b ON b.id=c.dst_service_id
                   WHERE c.last_seen > now() - make_interval(secs => %s)""", (max_age_s,))


def open_problem_targets() -> list[dict]:
    """Open incidents with the entity and the service/instance their recommended fix targets (for map badges)."""
    return db.q("""SELECT i.id, i.entity_name AS entity, c.params FROM incidents i
                   LEFT JOIN remediation_candidates c ON c.incident_id=i.id AND c.rank=0
                   WHERE i.status <> ALL(%s) ORDER BY i.id""", (list(CLOSED),))
