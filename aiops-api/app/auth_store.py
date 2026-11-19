"""Storage for sign-in and access (rules in auth.py and rbac.py): people, roles, the permission matrix, sessions,
single sign-on settings and an access log of who signed in and who changed what."""
from __future__ import annotations

import json
import logging
import os
import secrets
import time

from . import auth, db, rbac

log = logging.getLogger("radarops.auth")
DATA_DIR = os.environ.get("DATA_DIR", "/data")
SSO_KEYS = ("sso_enabled", "sso_issuer", "sso_client_id", "sso_label", "sso_default_role", "sso_role_rules",
            "sso_allowed_domains", "password_login")
_matrix_cache: dict = {}


# ---------------- first start ----------------
def seed():
    """Built-in roles with their default permissions (only when a role is new, so an admin's ticks survive a
    restart), and a first admin when nobody exists yet."""
    for r in rbac.ROLES:
        new = db.val("INSERT INTO roles(id, label, builtin) VALUES (%s,%s,true) ON CONFLICT (id) DO NOTHING RETURNING id",
                     (r["id"], r["label"]))
        if new:
            for p in rbac.DEFAULT_MATRIX[r["id"]]:
                db.ex("INSERT INTO role_permissions VALUES (%s,%s) ON CONFLICT DO NOTHING", (r["id"], p))
    if not db.val("SELECT count(*) FROM users"):
        email = os.environ.get("RADAROPS_ADMIN_EMAIL", "admin@radarops.local").lower()
        pw = os.environ.get("RADAROPS_ADMIN_PASSWORD") or secrets.token_urlsafe(12)
        db.ex("INSERT INTO users(email, name, role_id, password_hash) VALUES (%s,'Administrator','admin',%s)",
              (email, auth.hash_password(pw)))
        if not os.environ.get("RADAROPS_ADMIN_PASSWORD"):
            path = os.path.join(DATA_DIR, "initial-admin-password")
            try:
                with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
                    f.write(pw + "\n")
                log.warning("first admin %s created; password in %s (change it after signing in)", email, path)
            except OSError:
                log.warning("first admin %s created with password %s (change it after signing in)", email, pw)
        audit(None, "user.bootstrap", {"email": email})
    _matrix_cache.clear()


# ---------------- roles and the matrix ----------------
def roles() -> list[dict]:
    return db.q("""SELECT r.id, r.label, r.builtin, (SELECT count(*) FROM users u WHERE u.role_id=r.id) AS users
                   FROM roles r ORDER BY r.builtin DESC, array_position(ARRAY['admin','management','developer','viewer'], r.id), r.label""")


def matrix() -> dict[str, set[str]]:
    if not _matrix_cache:
        raw = {r["id"]: [] for r in roles()}
        for row in db.q("SELECT role_id, permission FROM role_permissions"):
            raw.setdefault(row["role_id"], []).append(row["permission"])
        _matrix_cache.update(rbac.effective(raw))
    return _matrix_cache


def permissions(role_id: str) -> set[str]:
    return matrix().get(role_id, {"read"})


def save_matrix(m: dict[str, list[str]], actor: dict):
    before = {k: sorted(v) for k, v in matrix().items()}
    with db.tx() as c:
        for role, perms in m.items():
            if role == "admin":
                continue          # locked: an admin keeps everything, or nobody could undo a mistake
            c.execute("DELETE FROM role_permissions WHERE role_id=%s", (role,))
            for p in set(perms) | {"read"}:
                c.execute("INSERT INTO role_permissions VALUES (%s,%s)", (role, p))
    _matrix_cache.clear()
    after = {k: sorted(v) for k, v in matrix().items()}
    changed = {r: {"added": sorted(set(after[r]) - set(before.get(r, []))), "removed": sorted(set(before.get(r, [])) - set(after[r]))}
               for r in after if after[r] != before.get(r)}
    audit(actor, "matrix.change", changed)
    return changed


def create_role(rid: str, label: str, copy_from: str | None, actor: dict):
    with db.tx() as c:
        c.execute("INSERT INTO roles(id, label, builtin) VALUES (%s,%s,false)", (rid, label))
        for p in permissions(copy_from) if copy_from else {"read"}:
            c.execute("INSERT INTO role_permissions VALUES (%s,%s) ON CONFLICT DO NOTHING", (rid, p))
    _matrix_cache.clear()
    audit(actor, "role.create", {"role": rid, "label": label, "copied_from": copy_from})


def rename_role(rid: str, label: str, actor: dict):
    db.ex("UPDATE roles SET label=%s WHERE id=%s", (label, rid))
    audit(actor, "role.rename", {"role": rid, "label": label})


def delete_role(rid: str, actor: dict):
    db.ex("DELETE FROM roles WHERE id=%s AND NOT builtin", (rid,))
    _matrix_cache.clear()
    audit(actor, "role.delete", {"role": rid})


def role(rid: str) -> dict | None:
    return next((r for r in roles() if r["id"] == rid), None)


# ---------------- people ----------------
_USER = """SELECT u.id, u.email, u.name, u.role_id AS role, r.label AS role_label, u.active, u.sso_subject IS NOT NULL AS sso,
           u.password_hash IS NOT NULL AS has_password, extract(epoch FROM u.created_at) AS created_at,
           extract(epoch FROM u.last_login_at) AS last_login_at FROM users u JOIN roles r ON r.id=u.role_id"""


def users() -> list[dict]:
    return db.q(_USER + " ORDER BY u.active DESC, u.name")


def user(uid: int) -> dict | None:
    return db.one(_USER + " WHERE u.id=%s", (uid,))


def user_by_email(email: str) -> dict | None:
    return db.one("SELECT * FROM users WHERE email=%s", (email.lower().strip(),))


def active_admins(except_id: int | None = None) -> int:
    return db.val("SELECT count(*) FROM users WHERE role_id='admin' AND active AND id <> coalesce(%s, -1)", (except_id,))


def create_user(email: str, name: str, role_id: str, password: str | None, actor: dict) -> int:
    uid = db.val("""INSERT INTO users(email, name, role_id, password_hash) VALUES (%s,%s,%s,%s) RETURNING id""",
                 (email.lower().strip(), name.strip() or email.split("@")[0], role_id,
                  auth.hash_password(password) if password else None))
    audit(actor, "user.create", {"email": email, "role": role_id, "password": bool(password)})
    return uid


def update_user(uid: int, b: dict, actor: dict):
    cols, args = [], []
    for k in ("name", "active"):
        if k in b:
            cols.append(f"{k}=%s"); args.append(b[k])
    if "role" in b:
        cols.append("role_id=%s"); args.append(b["role"])
    if b.get("password"):
        cols.append("password_hash=%s"); args.append(auth.hash_password(b["password"]))
    if cols:
        db.ex(f"UPDATE users SET {', '.join(cols)} WHERE id=%s", (*args, uid))
    if b.get("password") or b.get("active") is False or "role" in b:
        db.ex("DELETE FROM sessions WHERE user_id=%s", (uid,))     # a new password, role or a block applies now
    audit(actor, "user.update", {"user": uid, **{k: ("***" if k == "password" else v) for k, v in b.items()}})


def delete_user(uid: int, actor: dict):
    u = user(uid)
    db.ex("DELETE FROM users WHERE id=%s", (uid,))
    audit(actor, "user.delete", {"user": uid, "email": u and u["email"]})


# ---------------- sessions ----------------
def start_session(uid: int, via: str, ip: str, ua: str) -> str:
    tok, h = auth.new_token()
    now = time.time()
    db.ex("""INSERT INTO sessions(token_hash, user_id, expires_at, ip, user_agent, via)
             VALUES (%s,%s,to_timestamp(%s),%s,%s,%s)""", (h, uid, now + auth.SESSION_HOURS * 3600, ip, ua[:300], via))
    db.ex("UPDATE users SET last_login_at=now() WHERE id=%s", (uid,))
    db.ex("DELETE FROM sessions WHERE expires_at < now()")
    return tok


def session_user(token: str | None) -> dict | None:
    if not token:
        return None
    return db.one("""SELECT u.id, u.email, u.name, u.role_id AS role, r.label AS role_label, s.via, s.token_hash,
                     u.password_hash IS NOT NULL AS has_password
                     FROM sessions s JOIN users u ON u.id=s.user_id JOIN roles r ON r.id=u.role_id
                     WHERE s.token_hash=%s AND s.expires_at > now() AND u.active""", (auth.digest(token),))


def end_session(token: str):
    db.ex("DELETE FROM sessions WHERE token_hash=%s", (auth.digest(token),))


# ---------------- single sign-on ----------------
def sso_settings() -> dict:
    s = {k: db.setting(k) for k in SSO_KEYS}
    s["sso_enabled"] = s["sso_enabled"] == "1"
    s["password_login"] = s["password_login"] != "0"
    s["sso_default_role"] = s["sso_default_role"] or "viewer"
    s["sso_label"] = s["sso_label"] or "Sign in with SSO"
    try:
        s["sso_role_rules"] = json.loads(s["sso_role_rules"] or "[]")
    except ValueError:
        s["sso_role_rules"] = []
    s["has_secret"] = bool(db.setting("sso_client_secret"))
    return s


def save_sso(b: dict, actor: dict):
    from .cloud import seal    # same sealing key as cloud credentials, kept in /data
    for k, v in b.items():
        if k == "sso_client_secret":
            if v:
                db.set_setting(k, seal({"secret": v}))
        elif k in ("sso_enabled", "password_login"):
            db.set_setting(k, "1" if v else "0")
        elif k == "sso_role_rules":
            db.set_setting(k, json.dumps(v))
        elif k in SSO_KEYS:
            db.set_setting(k, str(v).strip())
    audit(actor, "sso.change", {k: ("***" if "secret" in k else v) for k, v in b.items()})


def sso_secret() -> str:
    from .cloud import unseal
    raw = db.setting("sso_client_secret")
    return unseal(raw)["secret"] if raw else ""


def remember_sso(state: str, nonce: str, verifier: str):
    db.ex("DELETE FROM sso_pending WHERE created_at < now() - interval '10 minutes'")
    db.ex("INSERT INTO sso_pending(state, nonce, verifier) VALUES (%s,%s,%s)", (state, nonce, verifier))


def take_sso(state: str) -> dict | None:
    return db.one("""DELETE FROM sso_pending WHERE state=%s AND created_at > now() - interval '10 minutes'
                     RETURNING nonce, verifier""", (state,))


def sso_user(issuer: str, who: dict, role: str | None, default_role: str) -> dict:
    """The person behind a verified id_token: matched by the provider's subject, else by an invited email (which
    links it), else created with the default role. A role rule that matches moves them to that role."""
    u = db.one("SELECT * FROM users WHERE sso_issuer=%s AND sso_subject=%s", (issuer, who["subject"]))
    if not u and who["email"]:
        taken = db.one("SELECT * FROM users WHERE email=%s", (who["email"],))
        if taken and taken["sso_subject"] is not None:
            raise auth.AuthError("this email already belongs to another single sign-on account; ask an admin")
        if taken and not who.get("verified", True):
            raise auth.AuthError("the provider has not verified this email, so it cannot be linked to an account")
        if taken:
            db.ex("UPDATE users SET sso_issuer=%s, sso_subject=%s WHERE id=%s", (issuer, who["subject"], taken["id"]))
            audit({"email": who["email"]}, "user.sso_link", {"user": taken["id"]})
            u = {**taken, "sso_issuer": issuer, "sso_subject": who["subject"]}
    if not u:
        uid = db.val("""INSERT INTO users(email, name, role_id, sso_issuer, sso_subject) VALUES (%s,%s,%s,%s,%s)
                        RETURNING id""", (who["email"] or f"{who['subject']}@sso", who["name"], role or default_role,
                                          issuer, who["subject"]))
        audit({"email": who["email"]}, "user.sso_join", {"role": role or default_role})
        return db.one("SELECT * FROM users WHERE id=%s", (uid,))
    if role and role != u["role_id"]:
        db.ex("UPDATE users SET role_id=%s WHERE id=%s", (role, u["id"]))
        audit({"email": who["email"]}, "user.sso_role", {"from": u["role_id"], "to": role})
        u["role_id"] = role
    return u


# ---------------- access log ----------------
def audit(actor: dict | None, action: str, detail: dict):
    db.ex("INSERT INTO access_log(actor, action, detail) VALUES (%s,%s,%s)",
          ((actor or {}).get("email") or "system", action, db.J(detail)))


def access_log(limit: int = 100) -> list[dict]:
    return db.q("SELECT id, extract(epoch FROM ts) AS ts, actor, action, detail FROM access_log ORDER BY id DESC LIMIT %s",
                (limit,))
