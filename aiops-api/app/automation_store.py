"""Storage for user-built automation (rules in automation.py)."""
from . import automation, db


# ---------- skills ----------
def skills() -> list[dict]:
    return db.q("""SELECT s.id, s.name, s.category, s.description, s.builtin, s.enabled, s.kinds, s.instructions,
                   coalesce((SELECT array_agg(tool ORDER BY seq) FROM skill_tools WHERE skill_id=s.id), '{}') AS tools
                   FROM skills s ORDER BY s.builtin DESC, s.name""")


def skill(sid: str) -> dict | None:
    return next((s for s in skills() if s["id"] == sid), None)


def save_skill(sid: str, b: dict, builtin: bool):
    with db.tx() as c:
        if builtin:   # code owns the rest of a built-in skill
            c.execute("UPDATE skills SET enabled=%s, instructions=%s WHERE id=%s", (b.get("enabled", True), b.get("instructions", ""), sid))
            return
        c.execute("""INSERT INTO skills(id, name, category, description, builtin, enabled, kinds, instructions)
                     VALUES (%s,%s,%s,%s,false,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name,
                     category=EXCLUDED.category, description=EXCLUDED.description, enabled=EXCLUDED.enabled,
                     kinds=EXCLUDED.kinds, instructions=EXCLUDED.instructions""",
                  (sid, b["name"].strip(), b.get("category") or "Custom", b.get("description") or "", b.get("enabled", True),
                   b["kinds"], b.get("instructions", "")))
        c.execute("DELETE FROM skill_tools WHERE skill_id=%s", (sid,))
        for i, t in enumerate(b.get("tools") or []):
            c.execute("INSERT INTO skill_tools(skill_id, seq, tool) VALUES (%s,%s,%s)", (sid, i, t))


def delete_skill(sid: str):
    db.ex("UPDATE incidents SET skill_id=NULL WHERE skill_id=%s", (sid,))
    db.ex("UPDATE runbooks SET skill_id=NULL WHERE skill_id=%s", (sid,))
    db.ex("DELETE FROM skills WHERE id=%s AND NOT builtin", (sid,))


# ---------- skill sets ----------
def skill_sets() -> list[dict]:
    return db.q("SELECT * FROM skill_sets ORDER BY name")


def save_skill_set(b: dict, sid: int | None = None) -> dict:
    args = (b["name"].strip(), b.get("scope", ""), b.get("skills") or [], b.get("enabled", True))
    if sid:
        return db.one("UPDATE skill_sets SET name=%s, scope=%s, skills=%s, enabled=%s WHERE id=%s RETURNING *", (*args, sid))
    return db.one("INSERT INTO skill_sets(name, scope, skills, enabled) VALUES (%s,%s,%s,%s) RETURNING *", args)


def delete_skill_set(sid: int):
    db.ex("DELETE FROM skill_sets WHERE id=%s", (sid,))


# ---------- runbooks written by hand ----------
def create_runbook(b: dict) -> int:
    sig = automation.runbook_signature(b)
    with db.tx() as c:
        rid = c.execute("""INSERT INTO runbooks(signature, title, kind, root_cause, action_type, action_params, authored)
                           VALUES (%s,%s,%s,%s,%s,%s,true) RETURNING id""",
                        (sig, b["title"].strip(), b["kind"], b.get("root_cause", ""), b["action_type"],
                         db.J({"service": b["service"].strip()}))).fetchone()["id"]
        for i, st in enumerate([x for x in b["steps"] if str(x).strip()]):
            c.execute("INSERT INTO runbook_steps VALUES (%s,%s,%s)", (rid, i, st.strip()))
    return rid


def update_runbook(rid: int, b: dict):
    with db.tx() as c:
        c.execute("""UPDATE runbooks SET title=%s, root_cause=%s, signature=%s, kind=%s, action_type=%s, action_params=%s,
                     updated_at=now() WHERE id=%s""", (b["title"].strip(), b.get("root_cause", ""), automation.runbook_signature(b),
                                                       b["kind"], b["action_type"], db.J({"service": b["service"].strip()}), rid))
        c.execute("DELETE FROM runbook_steps WHERE runbook_id=%s", (rid,))
        for i, st in enumerate([x for x in b["steps"] if str(x).strip()]):
            c.execute("INSERT INTO runbook_steps VALUES (%s,%s,%s)", (rid, i, st.strip()))


def delete_runbook(rid: int):
    db.ex("UPDATE incidents SET runbook_id=NULL WHERE runbook_id=%s", (rid,))
    db.ex("DELETE FROM runbooks WHERE id=%s", (rid,))


def signature_taken(sig: str, except_id: int | None = None) -> bool:
    return bool(db.val("SELECT 1 FROM runbooks WHERE signature=%s AND id <> coalesce(%s, -1)", (sig, except_id)))


# ---------- playbooks ----------
def playbooks() -> list[dict]:
    return db.q("SELECT *, extract(epoch FROM created_at) AS since FROM playbooks ORDER BY id")


def save_playbook(b: dict, pid: int | None = None) -> dict:
    args = (b["name"].strip(), b.get("enabled", True), db.J(b.get("trigger") or {}), db.J(b.get("actions") or {}))
    if pid:
        return db.one("UPDATE playbooks SET name=%s, enabled=%s, trigger=%s, actions=%s WHERE id=%s RETURNING *", (*args, pid))
    return db.one("INSERT INTO playbooks(name, enabled, trigger, actions) VALUES (%s,%s,%s,%s) RETURNING *", args)


def delete_playbook(pid: int):
    db.ex("DELETE FROM playbooks WHERE id=%s", (pid,))


def count_run(pid: int):
    db.ex("UPDATE playbooks SET runs=runs+1 WHERE id=%s", (pid,))


def escalated() -> set:
    return {(r["incident_id"], r["playbook_id"]) for r in db.q("SELECT incident_id, playbook_id FROM playbook_escalations")}


def mark_escalated(iid: int, pid: int):
    db.ex("INSERT INTO playbook_escalations(incident_id, playbook_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (iid, pid))


def waiting_for_approval() -> list[dict]:
    return db.q("""SELECT id, kind, severity, entity_name AS entity, status, extract(epoch FROM analyzed_at) AS analyzed_at
                   FROM incidents WHERE status='awaiting_approval' AND analyzed_at IS NOT NULL""")
