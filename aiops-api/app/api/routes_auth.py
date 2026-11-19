"""Signing in and who may do what: password sign-in, single sign-on (OpenID Connect), your own session, and for
admins the people, the roles and the permission matrix (rules in auth.py and rbac.py)."""
import os
import re
import secrets
import time
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from .. import auth, auth_store as st, rbac
from .errors import ApiError, not_found
from .guard import current_user

router = APIRouter(prefix="/api/v1", tags=["access"])
THROTTLE = auth.Throttle()
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_meta_cache: dict = {}
# The address people reach RadarOps at over https (e.g. https://cp26pt1.sit.kmutt.ac.th:8443). Providers such as Google
# only send people back to an https address, so the redirect URL is built from this when it is set.
REDIRECT_BASE = os.environ.get("SSO_REDIRECT_BASE", "").rstrip("/")


def _check(errs: list[str]):
    if errs:
        raise ApiError(422, "; ".join(errs), details={"problems": errs})


def _client(request: Request) -> tuple[str, str]:
    return (request.client.host if request.client else ""), request.headers.get("user-agent", "")


def _set_cookie(request: Request, response: Response, token: str):
    https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(auth.COOKIE, token, max_age=auth.SESSION_HOURS * 3600, httponly=True, samesite="lax",
                        secure=https, path="/")


def _me(u: dict) -> dict:
    perms = st.permissions(u["role"])
    return {"id": u["id"], "email": u["email"], "name": u["name"], "role": u["role"], "role_label": u["role_label"],
            "via": u.get("via"), "has_password": u.get("has_password", False),
            "permissions": sorted(perms)}


# ---------------- signing in ----------------
@router.get("/auth/providers", summary="What the sign-in page offers (no session needed)")
async def providers():
    s = st.sso_settings()
    return {"password": s["password_login"], "sso": {"enabled": s["sso_enabled"], "label": s["sso_label"]}}


@router.post("/auth/login", summary="Sign in with email and password")
async def login(body: dict, request: Request, response: Response):
    if not st.sso_settings()["password_login"]:
        raise ApiError(403, "password sign-in is switched off; use single sign-on")
    email = str(body.get("email") or "").strip().lower()
    now = time.time()
    if THROTTLE.blocked(email, now):
        raise ApiError(429, "too many wrong passwords; try again in a few minutes", code="locked")
    u = st.user_by_email(email)
    if not u or not u["active"] or not auth.verify_password(str(body.get("password") or ""), u["password_hash"] or ""):
        THROTTLE.fail(email, now)
        st.audit({"email": email}, "login.fail", {})
        raise ApiError(401, "email or password is not right")
    THROTTLE.succeed(email)
    ip, ua = _client(request)
    _set_cookie(request, response, st.start_session(u["id"], "password", ip, ua))
    st.audit(u, "login", {"via": "password", "ip": ip})
    return _me({**u, "role": u["role_id"], "role_label": (st.role(u["role_id"]) or {}).get("label", u["role_id"]),
                "via": "password", "has_password": True})


@router.post("/auth/logout", status_code=204, summary="Sign out")
async def logout(request: Request):
    tok = request.cookies.get(auth.COOKIE)
    if tok:
        st.end_session(tok)
    st.audit(current_user(request), "logout", {})
    r = Response(status_code=204)
    r.delete_cookie(auth.COOKIE, path="/")
    return r


@router.get("/auth/me", summary="Who is signed in and what their role allows")
async def me(request: Request):
    return _me(current_user(request))


@router.patch("/auth/me", summary="Change your own name or password")
async def update_me(body: dict, request: Request):
    u = current_user(request)
    b = {}
    if "name" in body and str(body["name"]).strip():
        b["name"] = str(body["name"]).strip()
    if body.get("password"):
        full = st.user_by_email(u["email"])
        if full.get("password_hash") and not auth.verify_password(str(body.get("current_password") or ""), full["password_hash"]):
            raise ApiError(403, "your current password is not right")
        _check(auth.password_problems(body["password"]))
        b["password"] = body["password"]
    st.update_user(u["id"], b, u)
    if b.get("password"):    # the change ended every session; keep this one going
        tok = st.start_session(u["id"], u.get("via") or "password", *_client(request))
        resp = Response(status_code=200)
        _set_cookie(request, resp, tok)
        return resp
    return {"ok": True}


# ---------------- single sign-on ----------------
async def discover(issuer: str) -> dict:
    hit = _meta_cache.get(issuer)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(issuer.rstrip("/") + "/.well-known/openid-configuration")
        r.raise_for_status()
        meta = r.json()
    _meta_cache[issuer] = (time.time(), meta)
    return meta


async def exchange_code(meta: dict, code: str, redirect_uri: str, verifier: str, client_id: str, secret: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(meta["token_endpoint"], data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri, "code_verifier": verifier,
            "client_id": client_id, "client_secret": secret})
        if r.status_code >= 400:
            raise auth.AuthError(f"the provider refused the sign-in code (HTTP {r.status_code})")
        return r.json()


async def fetch_jwks(meta: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(meta["jwks_uri"])
        r.raise_for_status()
        return r.json()


def _redirect_uri(request: Request) -> str:
    return (REDIRECT_BASE or str(request.base_url).rstrip("/")) + "/api/v1/auth/sso/callback"


def _back_to_login(msg: str) -> RedirectResponse:
    return RedirectResponse("/#/login?error=" + quote(msg[:200]), status_code=302)


@router.get("/auth/sso/start", summary="Go to the single sign-on provider")
async def sso_start(request: Request):
    s = st.sso_settings()
    if not s["sso_enabled"] or not s["sso_issuer"]:
        return _back_to_login("single sign-on is not set up")
    try:
        meta = await discover(s["sso_issuer"])
    except Exception:
        return _back_to_login("the sign-on provider cannot be reached")
    state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    verifier, challenge = auth.pkce()
    st.remember_sso(state, nonce, verifier)
    return RedirectResponse(auth.authorize_url(meta, s["sso_client_id"], _redirect_uri(request), state, nonce, challenge),
                            status_code=302)


@router.get("/auth/sso/callback", summary="Where the provider sends the person back")
async def sso_callback(request: Request, state: str = "", code: str = "", error: str = "", error_description: str = ""):
    if error:
        return _back_to_login(error_description or error)
    pending = st.take_sso(state) if state else None
    if not pending:
        return _back_to_login("this sign-in link has expired; start again")
    s = st.sso_settings()
    try:
        meta = await discover(s["sso_issuer"])
        tokens = await exchange_code(meta, code, _redirect_uri(request), pending["verifier"], s["sso_client_id"], st.sso_secret())
        claims = auth.verify_id_token(tokens.get("id_token") or "", await fetch_jwks(meta), meta.get("issuer") or s["sso_issuer"],
                                      s["sso_client_id"], pending["nonce"])
        who = auth.identity(claims)
        if not auth.domain_allowed(who["email"], s["sso_allowed_domains"]):
            raise auth.AuthError(f"{who['email'] or 'this account'} is not from an allowed email domain")
        role = auth.role_for(claims, s["sso_role_rules"], "") or None
        u = st.sso_user(meta.get("issuer") or s["sso_issuer"], who, role, s["sso_default_role"])
        if not u.get("active", True):
            raise auth.AuthError("this account is blocked; ask an admin")
    except auth.AuthError as e:
        st.audit({"email": "sso"}, "login.fail", {"via": "sso", "reason": str(e)})
        return _back_to_login(str(e))
    except Exception as e:
        return _back_to_login(f"single sign-on failed: {type(e).__name__}")
    ip, ua = _client(request)
    resp = RedirectResponse("/#/", status_code=302)
    _set_cookie(request, resp, st.start_session(u["id"], "sso", ip, ua))
    st.audit({"email": u["email"]}, "login", {"via": "sso", "ip": ip})
    return resp


@router.get("/auth/sso", summary="Single sign-on settings (the client secret is never returned)")
async def get_sso(request: Request):
    return {**st.sso_settings(), "redirect_uri": _redirect_uri(request)}


@router.patch("/auth/sso", summary="Change single sign-on settings")
async def patch_sso(body: dict, request: Request):
    known = {r["id"] for r in st.roles()}
    errs = []
    if "sso_default_role" in body and body["sso_default_role"] not in known:
        errs.append(f"unknown role '{body['sso_default_role']}'")
    for r in body.get("sso_role_rules") or []:
        if r.get("role") not in known:
            errs.append(f"unknown role '{r.get('role')}' in a group rule")
        if not str(r.get("value") or "").strip():
            errs.append("a group rule needs the value to match")
    if body.get("sso_issuer") and not re.match(r"^https?://", body["sso_issuer"]):
        errs.append("the issuer must be a URL starting with https://")
    _check(errs)
    merged = {**st.sso_settings(), **body}
    if body.get("password_login") is False:
        sso_admins = [u for u in st.users() if u["role"] == "admin" and u["active"] and u.get("sso")]
        if not merged["sso_enabled"] or not sso_admins:
            raise ApiError(409, "keep password sign-in on until single sign-on works and an admin has signed in with it")
    st.save_sso(body, current_user(request))
    return {**st.sso_settings(), "redirect_uri": _redirect_uri(request)}


@router.post("/auth/sso/test", summary="Check the provider answers at its issuer URL")
async def test_sso(body: dict):
    issuer = str(body.get("sso_issuer") or st.sso_settings()["sso_issuer"])
    try:
        meta = await discover(issuer)
    except Exception as e:
        raise ApiError(422, f"no OpenID Connect provider answered at {issuer}: {type(e).__name__}")
    return {"ok": True, "issuer": meta.get("issuer"), "authorization_endpoint": meta.get("authorization_endpoint")}


@router.get("/auth/log", summary="Recent sign-ins and access changes")
async def get_log():
    return st.access_log()


# ---------------- people ----------------
@router.get("/users", summary="Everyone who can sign in")
async def list_users():
    return st.users()


@router.post("/users", status_code=201, summary="Add a person (with a password, or invited for single sign-on)")
async def create_user(body: dict, request: Request):
    email = str(body.get("email") or "").strip().lower()
    errs = [] if EMAIL.match(email) else ["a valid email is required"]
    if not st.role(body.get("role") or ""):
        errs.append(f"unknown role '{body.get('role')}'")
    if body.get("password"):
        errs += auth.password_problems(body["password"])
    _check(errs)
    if st.user_by_email(email):
        raise ApiError(409, f"{email} already has an account")
    uid = st.create_user(email, str(body.get("name") or ""), body["role"], body.get("password") or None, current_user(request))
    return st.user(uid)


@router.patch("/users/{uid}", summary="Change a person's name, role, password, or block them")
async def update_user(uid: int, body: dict, request: Request):
    me_ = current_user(request)
    u = st.user(uid)
    if not u:
        raise not_found("user", uid)
    if "role" in body and not st.role(body["role"]):
        raise ApiError(422, f"unknown role '{body['role']}'")
    if body.get("password"):
        _check(auth.password_problems(body["password"]))
    losing_admin = u["role"] == "admin" and (body.get("role", "admin") != "admin" or body.get("active") is False)
    if losing_admin and uid == me_["id"]:
        raise ApiError(409, "you cannot take admin away from yourself; ask another admin")
    if losing_admin and st.active_admins(except_id=uid) < 1:
        raise ApiError(409, "this is the last admin; make someone else admin first")
    st.update_user(uid, {k: body[k] for k in ("name", "role", "active", "password") if k in body}, me_)
    return st.user(uid)


@router.delete("/users/{uid}", status_code=204, summary="Remove a person")
async def delete_user(uid: int, request: Request):
    me_ = current_user(request)
    u = st.user(uid)
    if not u:
        raise not_found("user", uid)
    if uid == me_["id"]:
        raise ApiError(409, "you cannot remove yourself")
    if u["role"] == "admin" and st.active_admins(except_id=uid) < 1:
        raise ApiError(409, "this is the last admin")
    st.delete_user(uid, me_)
    return Response(status_code=204)


# ---------------- roles and the matrix ----------------
def _matrix_view() -> dict:
    m = st.matrix()
    return {"groups": rbac.GROUPS, "permissions": rbac.PERMISSIONS, "roles": st.roles(),
            "matrix": {r: sorted(p) for r, p in m.items()}, "locked": ["admin"]}


@router.get("/roles", summary="Roles, permissions and the matrix between them")
async def get_roles():
    return _matrix_view()


@router.put("/roles/matrix", summary="Save the ticks of the permission matrix")
async def put_matrix(body: dict, request: Request):
    m = body.get("matrix") or {}
    _check(rbac.validate_matrix(m, {r["id"] for r in st.roles()}))
    st.save_matrix(m, current_user(request))
    return _matrix_view()


@router.post("/roles", status_code=201, summary="Add a role, optionally copying another role's ticks")
async def create_role(body: dict, request: Request):
    _check(rbac.validate_role(body))
    rid = rbac.role_id(body["label"])
    if st.role(rid):
        raise ApiError(409, f"a role called '{body['label']}' already exists")
    if body.get("copy_from") and not st.role(body["copy_from"]):
        raise ApiError(422, f"unknown role '{body['copy_from']}'")
    st.create_role(rid, body["label"].strip(), body.get("copy_from"), current_user(request))
    return {"id": rid}


@router.patch("/roles/{rid}", summary="Rename a role")
async def rename_role(rid: str, body: dict, request: Request):
    if not st.role(rid):
        raise not_found("role", rid)
    _check(rbac.validate_role(body))
    st.rename_role(rid, body["label"].strip(), current_user(request))
    return st.role(rid)


@router.delete("/roles/{rid}", status_code=204, summary="Remove a role nobody has")
async def delete_role(rid: str, request: Request):
    r = st.role(rid)
    if not r:
        raise not_found("role", rid)
    if r["builtin"]:
        raise ApiError(409, "built-in roles cannot be removed")
    if r.get("users"):
        raise ApiError(409, f"{r['users']} people have this role; move them first")
    st.delete_role(rid, current_user(request))
    return Response(status_code=204)
