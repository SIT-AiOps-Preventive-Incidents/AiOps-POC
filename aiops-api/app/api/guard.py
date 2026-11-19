"""The access check in front of every request: which permission the call needs (rbac.route_permission), whether
there is a live session, and whether the person's role has that permission. Agents' own calls and the sign-in page
pass without a session; everything else answers 401 (sign in) or 403 (your role cannot)."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .. import auth, auth_store as st, rbac
from .errors import body

LABEL = {p["id"]: p["label"] for p in rbac.PERMISSIONS}


def install(app: FastAPI):
    @app.middleware("http")
    async def _guard(request: Request, call_next):
        need = rbac.route_permission(request.method, request.url.path)
        if need in (rbac.PUBLIC, rbac.MACHINE):
            return await call_next(request)
        u = st.session_user(request.cookies.get(auth.COOKIE))
        if not u:
            return JSONResponse(body("unauthorized", "sign in to continue"), status_code=401)
        perms = st.permissions(u["role"])
        if not rbac.allowed(perms, need):
            return JSONResponse(body("forbidden", f"your role ({u['role_label']}) does not allow: {LABEL.get(need, need)}",
                                     {"need": need, "role": u["role"]}), status_code=403)
        request.state.user = {**u, "permissions": perms}
        return await call_next(request)


def current_user(request: Request) -> dict | None:
    return getattr(request.state, "user", None)
