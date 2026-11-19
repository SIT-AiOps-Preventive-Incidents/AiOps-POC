"""Sign-in: passwords, sessions, lockout, and single sign-on over OpenID Connect.

  password   scrypt with a fresh salt per password; only the hash is stored.
  session    a random token in an HttpOnly cookie; the database keeps only its SHA-256, so a leaked table cannot be
             replayed. Sessions end after SESSION_HOURS or on sign-out.
  lockout    LIMIT wrong passwords for one account within WINDOW_S lock that account until the window passes.
  SSO        Authorization Code flow with PKCE against any OpenID Connect provider (Microsoft Entra ID, Google,
             Keycloak, Dex ...). The id_token's signature, issuer, audience, expiry and nonce are all checked. A person
             is matched by the provider's subject; their role comes from a group/role claim rule, else the default.

Pure: no database, no network (auth_store.py and routes_auth.py do those).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from urllib.parse import urlencode

import jwt

SESSION_HOURS = 12
MIN_PASSWORD = 10
COOKIE = "radarops_session"
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}


class AuthError(Exception):
    pass


# ---------------- passwords ----------------
def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, dklen=32, **_SCRYPT)
    return "scrypt${n}${r}${p}${s}${h}".format(**_SCRYPT, s=salt.hex(), h=h.hex())


def verify_password(pw: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, h = (stored or "").split("$")
        if algo != "scrypt":
            return False
        got = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), dklen=32, n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(got.hex(), h)
    except (ValueError, TypeError):
        return False


def password_problems(pw: str | None) -> list[str]:
    if not pw or len(pw) < MIN_PASSWORD:
        return [f"a password needs at least {MIN_PASSWORD} characters"]
    return []


# ---------------- sessions ----------------
def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    tok = secrets.token_urlsafe(32)
    return tok, digest(tok)


def session_alive(s: dict, now: float) -> bool:
    return now < float(s["expires_at"])


class Throttle:
    """Wrong passwords per account. In memory: a restart forgets them, which only ever unlocks early."""
    LIMIT, WINDOW_S = 5, 600

    def __init__(self):
        self._fails: dict[str, list[float]] = {}

    def _recent(self, key: str, now: float) -> list[float]:
        xs = [t for t in self._fails.get(key, []) if now - t < self.WINDOW_S]
        self._fails[key] = xs
        return xs

    def blocked(self, key: str, now: float) -> bool:
        return len(self._recent(key.lower(), now)) >= self.LIMIT

    def fail(self, key: str, now: float):
        self._recent(key.lower(), now).append(now)

    def succeed(self, key: str):
        self._fails.pop(key.lower(), None)


# ---------------- single sign-on ----------------
def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def authorize_url(meta: dict, client_id: str, redirect_uri: str, state: str, nonce: str, challenge: str,
                  scope: str = "openid email profile") -> str:
    q = {"response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri, "scope": scope, "state": state,
         "nonce": nonce, "code_challenge": challenge, "code_challenge_method": "S256"}
    return f"{meta['authorization_endpoint']}?{urlencode(q)}"


def verify_id_token(token: str, jwks: dict, issuer: str, client_id: str, nonce: str) -> dict:
    try:
        kid = jwt.get_unverified_header(token).get("kid")
        keys = [k for k in jwks.get("keys", []) if not kid or k.get("kid") == kid]
        if not keys:
            raise AuthError("the provider's signing key was not found")
        key = jwt.PyJWK(keys[0]).key
        claims = jwt.decode(token, key, algorithms=["RS256", "ES256", "PS256"], audience=client_id,
                            issuer=issuer, leeway=60,
                            options={"require": ["exp", "iat", "iss", "aud", "sub"]})
    except AuthError:
        raise
    except jwt.PyJWTError as e:
        raise AuthError(f"the sign-in token was not accepted: {e}") from e
    if not hmac.compare_digest(str(claims.get("nonce") or ""), nonce):
        raise AuthError("the sign-in token was not issued for this sign-in (nonce)")
    return claims


def identity(claims: dict) -> dict:
    email = claims.get("email") or claims.get("preferred_username") or claims.get("upn") or ""
    return {"subject": str(claims["sub"]), "email": email.lower(), "name": claims.get("name") or email.split("@")[0],
            "verified": claims.get("email_verified", True) is not False}


def role_for(claims: dict, rules: list[dict], default: str) -> str:
    for r in rules:
        v = claims.get(r.get("claim") or "groups")
        values = v if isinstance(v, list) else [v] if v is not None else []
        if str(r.get("value")) in (str(x) for x in values):
            return r["role"]
    return default


def domain_allowed(email: str, domains: str) -> bool:
    allowed = [d.strip().lower().lstrip("@") for d in (domains or "").split(",") if d.strip()]
    if not allowed:
        return True
    host = email.lower().rsplit("@", 1)[-1]
    return any(host == d or host.endswith("." + d) for d in allowed)
